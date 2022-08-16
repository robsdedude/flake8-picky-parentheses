import ast
try:
    # Python 3.8+
    from importlib import metadata
except ImportError:
    import importlib_metadata as metadata
import sys
from typing import (
    Any,
    Generator,
    List,
    Tuple,
    Type,
)


class Plugin:
    name = __name__
    version = metadata.version("flake8_redundant_parentheses")

    def __init__(self, tree: ast.AST, read_lines, file_tokens):
        self.source_code_by_lines = list(read_lines())
        self.source_code = "".join(read_lines())
        self.file_token = list(file_tokens)
        self.tree = tree
        self.dump_tree = ast.dump(tree)
        # all parentheses coordinates
        self.all_parens_coords = find_parens_coords(self.file_token)
        # filter to only keep parentheses that are not strictly necessary
        self.parens_coords = [
            coords
            for coords in self.all_parens_coords
            if tree_without_parens_unchanged(self.source_code,
                                             self.dump_tree, coords)
        ]
        self.recheck_list = []
        for cords in self.all_parens_coords:
            if cords not in self.parens_coords:
                self.recheck_list.append(cords)
        self.problems: List[Tuple[int, int, str]] = []

    def run(self) -> Generator[Tuple[int, int, str, Type[Any]], None, None]:
        self.check_parentheses_in_funcs()
        if not self.parens_coords and not self.problems:
            return
        if self.parens_coords:
            self.check()
        for line, col, msg in self.problems:
            yield line, col, msg, type(self)

    @staticmethod
    def _node_in_parens(node, parens_coords):
        open_, _, _, close = parens_coords
        node_start = (node.lineno, node.col_offset)
        return close > node_start > open_

    @staticmethod
    def _check_parens_is_tuple(node, parens_coords):
        if sys.version_info >= (3, 8):
            return parens_coords[0] == (node.lineno, node.col_offset)
        else:
            # in Python 3.7 the parentheses are not considered part of the
            # tuple node
            return Plugin._node_in_parens(node, parens_coords)

    @staticmethod
    def _first_in_line(cords, source_code):
        for symb in source_code[cords[0] - 1]:
            if symb == " " or symb == "\t":
                continue
            elif symb == ")" or symb == "(" or symb == "]" or symb == "[" or symb == "}" or symb == "{":
                return True
            else:
                return False

    @staticmethod
    def _last_in_line(cords, source_code):
        for symb in reversed(source_code[cords[0] - 1]):
            if symb == " " or symb == ":" or symb == "\n":
                continue
            elif symb == ")" or symb == "(" or symb == "]" or symb == "[" or symb == "}" or symb == "{":
                return True
            else:
                return False

    def _adges_of_node(self, node):
        end_lineno = 0
        end_col_offset = 0
        for child in ast.iter_child_nodes(node):
            end_lineno_, end_col_offset_ = self._adges_of_node(child)
            if end_lineno_ > end_lineno:
                end_lineno, end_col_offset = end_lineno_, end_col_offset_
            try:
                if child.lineno > end_lineno:
                    end_lineno = child.lineno
                    end_col_offset = child.col_offset
            except AttributeError:
                continue
        return end_lineno, end_col_offset

    def check_parentheses_in_funcs(self) -> None:
        exeption = []
        for node in ast.walk(self.tree):
            for cords in self.recheck_list:
                try:
                    if cords[0][0] == node.lineno and cords not in exeption:
                        end_lineno, end_col_offset = self._adges_of_node(node)
                        if end_lineno - node.lineno > 0 and not (node.lineno, node.col_offset) > cords[0]:
                            if (self._last_in_line(cords[0], self.source_code_by_lines)
                                    and not self._first_in_line(cords[3], self.source_code_by_lines)):
                                self.problems.append((
                                    cords[0][0], cords[0][1],
                                    "PAR003: Opening bracket is last, but closing is not on new line"
                                ))
                                continue
                            if (self._last_in_line(cords[0], self.source_code_by_lines)
                                    and self._first_in_line(cords[3], self.source_code_by_lines)
                                    and node.col_offset != cords[3][1]):
                                self.problems.append((
                                    cords[0][0], cords[0][1],
                                    "PAR003: Closing is on new line but indentation mismatch"
                                ))
                                continue
                            exeption.append(cords)

                except AttributeError:
                    continue

    def check(self) -> None:
        msg = "PAR001: Too many parentheses"
        # exceptions made for parentheses that are not strictly necessary
        # but help readability
        exceptions = []
        special_ops_pair_exceptions = (
            ast.BinOp, ast.BoolOp, ast.UnaryOp, ast.Compare, ast.Await
        )
        for node in ast.walk(self.tree):
            if isinstance(node, special_ops_pair_exceptions):
                for child in ast.iter_child_nodes(node):
                    if not isinstance(child, special_ops_pair_exceptions):
                        continue
                    for coords in self.parens_coords:
                        if self._node_in_parens(node, coords):
                            break
                        if self._node_in_parens(child, coords):
                            exceptions.append(coords)
                            break

            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if not isinstance(target, ast.Tuple):
                        continue
                    for elts in target.elts:
                        tuple_coords = (target.lineno, target.col_offset)
                        elts_coords = (elts.lineno, elts.col_offset)
                        if tuple_coords <= elts_coords:
                            for coords in self.parens_coords:
                                if coords[0] <= tuple_coords:
                                    exceptions.append(coords)
                                    break
                            self.problems.append((
                                node.lineno, node.col_offset,
                                "PAR002: Dont use parentheses for "
                                "unpacking"
                            ))
                        break

            if isinstance(node, ast.Tuple):
                for coords in self.parens_coords:
                    if self._check_parens_is_tuple(node, coords):
                        exceptions.append(coords)
                        break

        for coords in self.parens_coords:
            if coords in exceptions:
                continue
            self.problems.append((*coords[0], msg))


OP_TOKEN_CODE = 54 if sys.version_info >= (3, 8) else 53


def find_parens_coords(token):
    # return parentheses paris in the form
    # (
    #   (open_line, open_col),
    #   open_end_col,
    #   replacement,
    #   (close_line, close_col)
    # )
    open_list = ["[", "{", "("]
    close_list = ["]", "}", ")"]
    opening_stack = []
    parentheses_pairs = []
    last_line = -1
    for i in range(len(token)):
        first_in_line = last_line != token[i].start[0]
        last_line = token[i].end[0]
        if token[i].type == OP_TOKEN_CODE:
            if token[i].string in open_list:
                if not first_in_line:
                    opening_stack.append([token[i].start, token[i].end[1],
                                          " ", token[i].string])
                    continue
                if token[i + 1].start[0] == token[i].end[0]:
                    opening_stack.append([token[i].start,
                                          token[i + 1].start[1], "",
                                          token[i].string])
                    continue
                # there is only this opening parenthesis on this line
                opening_stack.append([token[i].start, len(token[i].line) - 2,
                                      "", token[i].string])

            if token[i].string in close_list:
                opening = opening_stack.pop()
                assert (open_list.index(opening[3])
                        == close_list.index(token[i].string))
                parentheses_pairs.append(
                    [*opening[0:3], token[i].start]
                )

    return parentheses_pairs


def tree_without_parens_unchanged(source_code, start_tree, parens_coords):
    """Check if parentheses are redundant.

    Replace a pair of parentheses with a blank string and check if the
    resulting AST is still the same.
    """
    open_, space, replacement, close = parens_coords
    lines = source_code.split("\n")
    lines[open_[0] - 1] = (lines[open_[0] - 1][:open_[1]]
                           + replacement
                           + lines[open_[0] - 1][space:])
    shift = 0
    if open_[0] == close[0]:
        shift -= (space - open_[1]) - len(replacement)
    lines[close[0] - 1] = (lines[close[0] - 1][:close[1] + shift]
                           + " " + lines[close[0] - 1][close[1] + 1 + shift:])
    code_without_parens = "\n".join(lines)
    try:
        tree = ast.parse(code_without_parens)
    except (ValueError, SyntaxError):
        return False
    return ast.dump(tree) == start_tree
