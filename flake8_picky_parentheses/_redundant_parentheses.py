from __future__ import annotations

import ast
import sys
from textwrap import dedent
import tokenize
import typing as t

from ._meta import version
from ._util import find_parens_coords

if t.TYPE_CHECKING:
    from ._util import ParensCords


class PluginRedundantParentheses:
    name = __name__
    version = version

    def __init__(
        self,
        tree: ast.AST,
        read_lines: t.Callable[[], t.List[str]],
        file_tokens: t.Iterable[tokenize.TokenInfo],
    ) -> None:
        self.source_code = "".join(read_lines())
        self.file_tokens = list(file_tokens)
        self.file_tokens_nn = [token for token in self.file_tokens
                               if token.type != tokenize.NL]
        self.tree = tree
        self.dump_tree = ast.dump(tree)
        lines = self.source_code.split("\n")
        self.all_logic_line = all_logical_lines(self.file_tokens)

        if self.source_code and not self.source_code.isspace():
            (
                self.logic_lines, self.logic_lines_num, self.logic_lines_trees,
                self.logic_line_move
            ) = separate_logic_lines(lines, self.dump_tree,
                                     self.all_logic_line)

        # all parentheses coordinates
        self.all_parens_coords = find_parens_coords(self.file_tokens)
        # filter to only keep parentheses that are not strictly necessary
        self.parens_coords = [
            coords
            for coords in self.all_parens_coords
            if tree_without_parens_unchanged(self.logic_lines_trees,
                                             coords,
                                             self.logic_lines,
                                             self.logic_lines_num,
                                             self.logic_line_move)
        ]
        self.exceptions: t.List[ParensCords] = []
        self.problems: t.List[t.Tuple[int, int, str]] = []

    def run(
        self
    ) -> t.Generator[t.Tuple[int, int, str, t.Type[t.Any]], None, None]:
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

    def checked_parentheses(self, coords) -> bool:
        return coords in self.exceptions or coords[0] in self.problems

    def check(self) -> None:
        msg = "PAR001: Too many parentheses"
        # exceptions made for parentheses that are not strictly necessary
        # but help readability
        special_ops_pair_exceptions = (
            ast.BinOp, ast.BoolOp, ast.UnaryOp, ast.Compare, ast.Await
        )
        for node in ast.walk(self.tree):
            breaker = False
            if isinstance(node, ast.Slice):
                for child in ast.iter_child_nodes(node):
                    for coords in self.parens_coords:
                        if self.checked_parentheses(coords):
                            continue
                        if ((coords.open_[0], coords.open_[1] + 1)
                                == (child.lineno, child.col_offset)
                                and isinstance(child,
                                               special_ops_pair_exceptions)):
                            breaker = True
                            self.exceptions.append(coords)
                    if breaker:
                        break
            elif isinstance(node, special_ops_pair_exceptions):
                for child in ast.iter_child_nodes(node):
                    if not isinstance(child, special_ops_pair_exceptions):
                        continue
                    for coords in self.parens_coords:
                        if (self.checked_parentheses(coords)
                                or self._node_in_parens(node, coords)):
                            continue
                        if self._node_in_parens(child, coords):
                            self.exceptions.append(coords)
                            breaker = True
                            break
                    if breaker:
                        break

            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if not isinstance(target, ast.Tuple):
                        continue
                    if not target.elts:
                        continue
                    elt = target.elts[0]
                    elt_coords = (elt.lineno, elt.col_offset)
                    matching_parens = None
                    for coords in self.parens_coords:
                        if self.checked_parentheses(coords):
                            continue
                        if self._node_in_parens(elt, coords):
                            matching_parens = coords
                            break
                    if not matching_parens:
                        continue
                    if not any(
                        self.file_tokens_nn[token].start == elt_coords
                        and self.file_tokens_nn[token - 1].string
                        == "("
                        for token in range(len(self.file_tokens_nn))
                    ):
                        break
                    self.problems.append((
                        node.lineno, node.col_offset,
                        "PAR002: Dont use parentheses for "
                        "unpacking"
                    ))
                    # no need to treat them again later
                    self.exceptions.append(matching_parens)
                    break

            elif isinstance(node, ast.Tuple):
                for coords in self.parens_coords:
                    if self.checked_parentheses(coords):
                        continue
                    if self._check_parens_is_tuple(node, coords):
                        self.exceptions.append(coords)
                        break

            elif isinstance(node, ast.comprehension):
                for coords in self.parens_coords:
                    if self.checked_parentheses(coords):
                        continue
                    for child in node.ifs:
                        if not self._node_in_parens(child, coords):
                            break
                        if coords.open_[0] != coords.close[0]:
                            self.exceptions.append(coords)
                            breaker = True
                            break
                    if breaker:
                        break

        for coords in self.parens_coords:
            if coords in self.exceptions:
                continue
            self.problems.append((*coords[0], msg))


def all_logical_lines(file_tokens):
    res = []
    if not file_tokens:
        return res
    start_line = 0
    for token in file_tokens:
        if token.type == tokenize.NEWLINE:
            end_line = token.start[0]
            res.append((start_line, end_line))
            start_line = end_line

    return res


def build_tree(code_to_check, start_trees):
    try:
        tree = ast.parse(dedent(code_to_check))
    except (ValueError, SyntaxError):
        return False
    new_dump_tree = ast.dump(tree)

    assert len(tree.body) == 1
    node = tree.body[0]
    if sys.version_info >= (3, 8):
        start_offset = 24
        end_offset = 64 if isinstance(node, ast.ClassDef) else 43
    else:
        start_offset = 13
        end_offset = 36 if isinstance(node, ast.ClassDef) else 17
    end_offset = len(new_dump_tree) - end_offset
    tree_to_check = new_dump_tree[start_offset:][:end_offset]

    return any(tree_to_check in dump_tree
               for dump_tree in start_trees)


def separate_logic_lines(source_code, start_tree, all_logic_lines):
    logic_lines = []
    logic_lines_num = []
    logic_lines_trees = []
    code_to_check = []
    logic_line_move = []
    checked_lines = 0
    prev_moved = 0
    for logic_line in all_logic_lines:
        for counter in range(logic_line[0], logic_line[1]):
            code_to_check.append(source_code[counter])
        for line_num in range(len(code_to_check)):
            if line_num < checked_lines or code_to_check[line_num] == "":
                continue
            code_to_check, checked_lines, prev_moved = delete_tabs(
                code_to_check, line_num, prev_moved
            )
            break

        str_code_to_check = "\n".join(code_to_check)
        if not build_tree(str_code_to_check, [start_tree]):
            continue
        logic_line_tree = ast.dump(ast.parse(str_code_to_check))
        logic_lines.append(str_code_to_check)
        logic_lines_num.append(logic_line[1])
        logic_lines_trees.append(logic_line_tree)
        logic_line_move.append(prev_moved)
        code_to_check = []
        checked_lines = 0
        prev_moved = 0
    return logic_lines, logic_lines_num, logic_lines_trees, logic_line_move


def delete_tabs(line, line_num, prev_moved):
    moved_counter = 0
    changed = None
    if prev_moved == 0:
        for num in range(len(line[line_num])):
            if line[line_num][num] != " ":
                break
            moved_counter += 1

    else:
        moved_counter = prev_moved
    for delete in range(0, moved_counter):
        for lines in range(line_num, len(line)):
            if not line[lines].startswith(" "):
                moved_counter = delete
                break
            line[lines] = line[lines][1:]
            changed = moved_counter
    if changed:
        return line, len(line), moved_counter
    else:
        return line, 0, 0


def tree_without_parens_unchanged(logic_line_trees, parens_coords, logic_lines,
                                  logic_lines_num, logic_line_move):
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
        idx_open_line = open_[0] - move_lines - 1
        split_line[idx_open_line] = (
            split_line[idx_open_line][:open_[1] - logic_line_move[lines]]
            + replacement
            + split_line[idx_open_line][space - logic_line_move[lines]:]
        )
        shift = 0
        if open_[0] == close[0]:
            shift -= (space - open_[1]) - len(replacement)
        idx_close_line = close[0] - move_lines - 1
        shifted_close_col = close[1] + shift - logic_line_move[lines]
        split_line[idx_close_line] = (
            split_line[idx_close_line][:shifted_close_col]
            + " "
            + split_line[idx_close_line][shifted_close_col + 1:]
        )
        patched_line = "\n".join(split_line)
        return build_tree(patched_line, logic_line_trees)
