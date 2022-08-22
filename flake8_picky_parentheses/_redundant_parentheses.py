import ast
import tokenize
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
        self.source_code_by_lines = list(read_lines())
        self.source_code = "".join(read_lines())
        self.file_tokens = list(file_tokens)
        self.file_tokens_nn = [token for token in self.file_tokens
                               if token.type != tokenize.NL]
        self.tree = tree
        self.dump_tree = ast.dump(tree)
        # all parentheses coordinates
        self.all_parens_coords = find_parens_coords(self.file_tokens)
        # filter to only keep parentheses that are not strictly necessary
        self.parens_coords = [
            coords
            for coords in self.all_parens_coords
            if tree_without_parens_unchanged(self.source_code,
                                             self.dump_tree, coords)
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

    def checked_parentheses(self, cords):
        if cords in self.exceptions or cords[0] in self.problems:
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
                    for cords in self.parens_coords:
                        if self.checked_parentheses(cords):
                            continue
                        if ((cords.open[0], cords.open[1] + 1)
                                == (child.lineno, child.col_offset)
                           and isinstance(child, special_ops_pair_exceptions)):
                            breaker = 1
                            self.exceptions.append(cords)
                    if breaker:
                        break
            if isinstance(node, special_ops_pair_exceptions):
                for child in ast.iter_child_nodes(node):
                    if not isinstance(child, special_ops_pair_exceptions):
                        continue
                    for coords in self.parens_coords:
                        if self.checked_parentheses(coords):
                            continue
                        if self._node_in_parens(node, coords):
                            break
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
                for cords in self.parens_coords:
                    if self.checked_parentheses(cords):
                        continue
                    for child in node.ifs:
                        if not self._node_in_parens(child, cords):
                            break
                        if cords.open[0] != cords.close[0]:
                            self.exceptions.append(cords)
                            breaker = 1
                            break
                    if breaker:
                        break

        for coords in self.parens_coords:
            if coords in self.exceptions:
                continue
            self.problems.append((*coords[0], msg))


def tree_without_parens_unchanged(source_code, start_tree, parens_coords):
    """Check if parentheses are redundant.

    Replace a pair of parentheses with a blank string and check if the
    resulting AST is still the same.
    """
    open_, space, replacement, close, _ = parens_coords
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
