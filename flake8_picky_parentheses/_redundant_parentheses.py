import ast
import tokenize
from textwrap import dedent
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

from ._util import find_parens_coords


class PluginRedundantParentheses:
    name = __name__
    version = metadata.version("flake8_picky_parentheses")

    def __init__(self, tree: ast.AST, read_lines, file_tokens):
        self.source_code = "".join(read_lines())
        self.file_tokens = list(file_tokens)
        self.file_tokens_nn = [token for token in self.file_tokens
                               if token.type != tokenize.NL]
        self.tree = tree
        self.dump_tree = ast.dump(tree)

        current_line = 0
        self.logic_lines = []
        self.logic_lines_num = []
        self.logic_lines_trees = []
        lines = self.source_code.split("\n")
        while current_line <= len(lines) - 2:
            checked_code, current_line, logic_line_tree = separate_logic_lines(
                                                          lines,
                                                          self.file_tokens,
                                                          self.dump_tree,
                                                          current_line
            )
            self.logic_lines.append(checked_code)
            self.logic_lines_num.append(current_line)
            self.logic_lines_trees.append(logic_line_tree)

        # all parentheses coordinates
        self.all_parens_coords = find_parens_coords(self.file_tokens)
        # filter to only keep parentheses that are not strictly necessary
        self.parens_coords = [
            coords
            for coords in self.all_parens_coords
            if tree_without_parens_unchanged(self.logic_lines_trees,
                                             coords,
                                             self.logic_lines,
                                             self.logic_lines_num,)
        ]
        self.exceptions = []
        self.problems: List[Tuple[int, int, str]] = []

    def run(self) -> Generator[Tuple[int, int, str, Type[Any]], None, None]:
        if not self.parens_coords:
            return
        self.check()
        for line, col, msg in self.problems:
            yield line, col, msg, type(self)

    @staticmethod
    def _node_in_parens(node, parens_coords):
        open_, _, _, close, _ = parens_coords
        node_start = (node.lineno, node.col_offset)
        return close > node_start > open_

    @staticmethod
    def _check_parens_is_tuple(node, parens_coords):
        if sys.version_info >= (3, 8):
            return parens_coords[0] == (node.lineno, node.col_offset)
        else:
            # in Python 3.7 the parentheses are not considered part of the
            # tuple node
            return PluginRedundantParentheses._node_in_parens(
                node, parens_coords
            )

    def checked_parentheses(self, coords):
        if coords in self.exceptions or coords[0] in self.problems:
            return True
        return False

    def check(self) -> None:
        msg = "PAR001: Too many parentheses"
        # exceptions made for parentheses that are not strictly necessary
        # but help readability
        special_ops_pair_exceptions = (
            ast.BinOp, ast.BoolOp, ast.UnaryOp, ast.Compare, ast.Await
        )
        for node in ast.walk(self.tree):
            breaker = None
            if isinstance(node, ast.Slice):
                for child in ast.iter_child_nodes(node):
                    for coords in self.parens_coords:
                        if self.checked_parentheses(coords):
                            continue
                        if ((coords.open[0], coords.open[1] + 1)
                                == (child.lineno, child.col_offset)
                           and isinstance(child, special_ops_pair_exceptions)):
                            breaker = 1
                            self.exceptions.append(coords)
                    if breaker:
                        break
            if isinstance(node, special_ops_pair_exceptions):
                for child in ast.iter_child_nodes(node):
                    if not isinstance(child, special_ops_pair_exceptions):
                        continue
                    for coords in self.parens_coords:
                        if (self.checked_parentheses(coords)
                                or self._node_in_parens(node, coords)):
                            continue
                        if self._node_in_parens(child, coords):
                            self.exceptions.append(coords)
                            breaker = 1
                            break
                    if breaker:
                        break

            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if not isinstance(target, ast.Tuple):
                        continue
                    for elts in target.elts:
                        tuple_coords = (target.lineno, target.col_offset)
                        elts_coords = (elts.lineno, elts.col_offset)
                        if tuple_coords > elts_coords:
                            continue
                        for coords in self.parens_coords:
                            if self.checked_parentheses(coords):
                                continue
                            if (coords[0][1] <= tuple_coords[1]
                               and coords[0][0] == tuple_coords[0]):
                                self.exceptions.append(coords)
                                breaker = 1
                                break
                        if not any(
                            self.file_tokens_nn[token].start == elts_coords
                            and self.file_tokens_nn[token - 1].string == "("
                            for token in range(len(self.file_tokens_nn))
                        ):
                            break
                        self.problems.append((
                            node.lineno, node.col_offset,
                            "PAR002: Dont use parentheses for "
                            "unpacking"
                        ))
                        break
                    if breaker:
                        break

            if isinstance(node, ast.Tuple):
                for coords in self.parens_coords:
                    if self.checked_parentheses(coords):
                        continue
                    if self._check_parens_is_tuple(node, coords):
                        self.exceptions.append(coords)
                        break

            if isinstance(node, ast.comprehension):
                for coords in self.parens_coords:
                    if self.checked_parentheses(coords):
                        continue
                    for child in node.ifs:
                        if not self._node_in_parens(child, coords):
                            break
                        if coords.open[0] != coords.close[0]:
                            self.exceptions.append(coords)
                            breaker = 1
                            break
                    if breaker:
                        break

        for coords in self.parens_coords:
            if coords in self.exceptions:
                continue
            self.problems.append((*coords[0], msg))


def all_logical_lines(file_tokens):
    res = []
    pair = []
    for i in range(len(file_tokens)):
        if file_tokens[i].type in (tokenize.NEWLINE, tokenize.ENCODING):
            pair.append(i)
            if len(pair) == 2:
                res.append((file_tokens[pair[0]].start[0],
                            file_tokens[pair[1]].start[0]))
                pair = [pair[1]]
    return res


def build_tree(code_to_check, start_tree):
    try:
        tree = ast.parse(dedent(code_to_check))
        tree = ast.dump(tree)
        if sys.version_info >= (3, 8):
            tree_to_check = tree[24:][:(len(tree[24:]) - 19)]
        else:
            tree_to_check = tree[13:][:(len(tree) - 15)]
    except (ValueError, SyntaxError):
        return False
    if type(start_tree) is list:
        for dump_tree in start_tree:
            if tree_to_check in str(dump_tree):
                return True
    else:
        return tree_to_check in start_tree
    return False


def separate_logic_lines(source_code, file_tokens, start_tree, current_line):
    all_logic_lines = all_logical_lines(file_tokens)
    code_to_check = []
    for num in range(len(all_logic_lines)):
        if all_logic_lines[num][0] >= current_line:
            for counter in range(all_logic_lines[num][0],
                                 all_logic_lines[num][1]):
                code_to_check.append(source_code[counter])
            str_code_to_check = "\n".join(code_to_check)
            if build_tree(str_code_to_check, start_tree):
                logic_line_tree = ast.dump(ast.parse(str_code_to_check))
                return (str_code_to_check, all_logic_lines[num][1],
                        logic_line_tree)
            else:
                continue


def tree_without_parens_unchanged(start_tree, parens_coords, logic_lines,
                                  logic_lines_num):
    """Check if parentheses are redundant.

    Replace a pair of parentheses with a blank string and check if the
    resulting AST is still the same.
    """
    open_, space, replacement, close, _ = parens_coords

    move_lines = 0

    for lines in range(len(logic_lines)):
        if parens_coords[3][0] > logic_lines_num[lines]:
            continue
        if logic_lines_num[lines - 1] <= parens_coords[3][0]:
            move_lines = logic_lines_num[lines - 1]
        split_line = logic_lines[lines].split("\n")
        split_line[open_[0] - move_lines - 1] = (
                split_line[open_[0] - move_lines - 1][:open_[1]] + replacement
                + split_line[open_[0] - move_lines - 1][space:]
        )
        shift = 0
        if open_[0] == close[0]:
            shift -= (space - open_[1]) - len(replacement)
        split_line[close[0] - move_lines - 1] = (
                split_line[close[0] - move_lines - 1][:close[1] + shift] + " "
                + split_line[close[0] - move_lines - 1][close[1] + 1 + shift:]
        )
        random_line = "\n".join(split_line)
        return build_tree(random_line, start_tree)
