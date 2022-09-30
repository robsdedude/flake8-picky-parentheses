from __future__ import annotations

a =   1 \
      + 2

"""
abc
def
"""

import ast
from dataclasses import dataclass
import re
import sys
from textwrap import dedent
import tokenize
import typing as t

from ._meta import version
from ._util import find_parens_coords

if ((

    t.TYPE_CHECKING
)):
    from ._util import ParensCords


LOGICAL_LINE_STRIP_NL_RE = re.compile(
    r"^((?:\s*\n)*)((?:.|\n)*?)((?:\n\s*)*)$"
)
LOGICAL_LINE_STRIP_WS_RE = re.compile(r"^(\s*)((?:.|\n)*)$")

AST_FIX_PREFIXES = {
    "else": "if True:\n   pass\n",
    "except": "try:\n   pass\n",
    "finally": "try:\n   pass\n",
}


IGNORED_TYPES_FOR_PARENS = {
    tokenize.NL,
    tokenize.COMMENT,
    # tokenize.INDENT,
    # tokenize.DEDENT,
    # tokenize.ENDMARKER,
}


class LogicalLine:
    def __init__(
        self,
        line: str,
        line_offset: int,
        tokens: t.Tuple[tokenize.TokenInfo] = None,
        column_offset: int = 0
    ):
        self.line = line
        self.line_offset = line_offset
        self.column_offset = column_offset
        self._tokens = tokens

    @property
    def tokens(self):
        if self._tokens is None:
            lines = self.line.splitlines(keepends=True)
            line_iter = iter(lines)
            self._tokens = tuple(
                tokenize.generate_tokens(lambda: next(line_iter))
            )
        return self._tokens


@dataclass
class ProblemRewrite:
    pos: t.Tuple[int, int]
    replacement: t.Optional[str]


class PluginRedundantParentheses:
    name = __name__
    version = version

    def __init__(
        self,
        tree: ast.AST,
        # read_lines: t.Callable[[], t.List[str]],
        file_tokens: t.Iterable[tokenize.TokenInfo],
        # next_logical_line,
        # build_logical_line_tokens,
        lines: t.List[str],

        # logical_line: t.List[LogicalLine],
    ) -> None:
        self.tree = tree
        self.file_tokens = list(file_tokens)
        self.lines = lines
        self.logical_lines = list(
            self.get_logical_lines(self.lines, self.file_tokens)
        )
        self.problems = []
        return
        # comments, logical, mapping = build_logical_line_tokens()
        # next_logical_line()
        # print(logical_line, next_logical_line)
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
            if tree_without_parens_unchanged(
                self.logic_lines_trees, coords, self.logic_lines,
                self.logic_lines_num, self.logic_line_move
            )
        ]
        self.exceptions: t.List[ParensCords] = []
        self.problems: t.List[t.Tuple[int, int, str]] = []

    @staticmethod
    def get_logical_lines(lines, tokens):
        # if not lines:
        #     return []
        # current_logical_line = ""
        # logical_lines = []
        # line_idx = 0
        # prev_end = None
        # for token in tokens:
        #     if prev_end is not None and prev_end > token.end:
        #         continue
        #     if token.type == tokenize.NEWLINE:
        #         current_logical_line += lines[line_idx]
        #         logical_lines.append(
        #             LogicalLine(current_logical_line, line_idx)
        #         )
        #         current_logical_line = ""
        #         line_idx += 1
        #     elif token.type == tokenize.NL:
        #         current_logical_line += lines[line_idx]
        #         line_idx += 1
        #     prev_end = token.end
        # return logical_lines

        # current_logical_line = ""
        # current_logical_line_offset = None
        # prev_end_line, prev_end_column = 1, 0
        # logical_lines = []
        # for token in tokens:
        #     start_line, start_column = token.start
        #     if current_logical_line and prev_end_line == start_line:
        #         current_logical_line += \
        #             " " * (start_column - prev_end_column)
        #     current_logical_line += token.string
        #     prev_end_line, prev_end_column = token.end
        #     if current_logical_line_offset is None:
        #         current_logical_line_offset = token.start[0] - 1
        #     if token.type == tokenize.NEWLINE:
        #         logical_lines.append(
        #             LogicalLine(current_logical_line,
        #                         current_logical_line_offset)
        #         )
        #         current_logical_line = ""
        #         current_logical_line_offset = None
        # return logical_lines

        prev_end_line = 0
        logical_line_tokens: t.List[tokenize.TokenInfo] = []
        for token in tokens:
            logical_line_tokens.append(token)
            if token.type == tokenize.NEWLINE:
                yield LogicalLine(
                    "".join(lines[prev_end_line:token.start[0]]),
                    prev_end_line,
                    tuple(logical_line_tokens)
                )
                logical_line_tokens = []
                prev_end_line = token.start[0]

    def run(
        self
    ) -> t.Generator[t.Tuple[int, int, str, t.Type[t.Any]], None, None]:
        self.check()
        for line, col, msg in self.problems:
            yield line, col, msg, type(self)

    def check(self):
        raw_problems = self._get_raw_problems(self.logical_lines)
        self.problems = self._rewrite_problems(raw_problems, self.tree,
                                               self.file_tokens)

    @classmethod
    def _get_raw_problems(cls, logical_lines):
        for logical_line in logical_lines:
            if not any(
                token.type == tokenize.OP and token.string == "("
                for token in logical_line.tokens
            ):
                continue
            logical_line = cls._strip_logical_line(logical_line)
            logical_line = cls._pad_logical_line(logical_line)
            cls._check_logical_line(logical_line)
            for line, column, msg in cls._check_logical_line(logical_line):
                line += logical_line.line_offset
                column += logical_line.column_offset
                yield line, column, msg

    @classmethod
    def _rewrite_problems(cls, raw_problems, tree, file_tokens):
        parens_coords = find_parens_coords(file_tokens)
        raw_problems = list(raw_problems)
        raw_problems_pos = set((line, column)
                               for line, column, _ in raw_problems)
        problem_coords = [
            parens_coord
            for parens_coord in parens_coords
            if parens_coord.open_ in raw_problems_pos
        ]
        rewrites_by_pos: t.Dict[t.Tuple[int, int], ProblemRewrite] = {
            rewrite.pos: rewrite
            for rewrite in cls._get_rewrites(problem_coords, tree, file_tokens)
        }
        # raw_problems = list(raw_problems)
        for raw_problem in raw_problems:
            line, column, msg = raw_problem
            rewrite = rewrites_by_pos.get((line, column), None)
            if rewrite is None:
                yield raw_problem
                continue
            if rewrite.replacement is None:
                continue
            yield line, column, rewrite.replacement

    @staticmethod
    def _strip_logical_line(logical_line):
        match = LOGICAL_LINE_STRIP_NL_RE.match(logical_line.line)
        assert match
        groups = match.groups()
        extra_line_offset = 0
        assert len(groups) == 3
        stripped_line = groups[1]
        assert stripped_line is not None
        if groups[0]:
            extra_line_offset = groups[0].count("\n")
        match = LOGICAL_LINE_STRIP_WS_RE.match(stripped_line)
        assert match
        groups = match.groups()
        assert len(groups) == 2
        extra_column_offset = 0
        if groups[0]:
            extra_column_offset = len(groups[0])
        stripped_line = groups[1]
        assert stripped_line is not None
        return LogicalLine(
            line=stripped_line,
            line_offset=logical_line.line_offset + extra_line_offset,
            column_offset=extra_column_offset
        )

    @staticmethod
    def _pad_logical_line(logical_line):
        tokens = logical_line.tokens
        assert tokens

        if not tokens or tokens[0].type != tokenize.NAME:
            return logical_line

        line = logical_line.line
        line_offset = logical_line.line_offset
        column_offset = logical_line.column_offset
        needs_body = logical_line.line.rstrip().endswith(":")
        is_decorator = logical_line.line.lstrip().startswith("@")
        if is_decorator:
            line += "\ndef f():"
            needs_body = True
        if needs_body:
            line += "\n    pass"
        ast_fix_prefix = AST_FIX_PREFIXES.get(tokens[0].string)
        if ast_fix_prefix:
            line = ast_fix_prefix + line
            line_offset += ast_fix_prefix.count("\n")
            column_offset += len(ast_fix_prefix.rsplit("\n", 1)[-1])
        return LogicalLine(
            line=line,
            line_offset=line_offset,
            column_offset=column_offset
        )

    @classmethod
    def _check_logical_line(cls, logical_line):
        parens_coords = find_parens_coords(logical_line.tokens)
        tree = ast.parse(logical_line.line)
        for parens_coord in parens_coords:
            if not cls._parens_check_optional(logical_line, tree,
                                              parens_coord):
                continue
            yield (*parens_coord.open_, "PAR001: Redundant parentheses")

    @classmethod
    def _parens_check_optional(cls, logical_line, tree, parens_coord):
        line_without_parens = cls._remove_parens(logical_line, parens_coord)
        try:
            tree_without_parens = ast.parse(line_without_parens)
        except (ValueError, SyntaxError):
            return False
        return ast.dump(tree) == ast.dump(tree_without_parens)

    @staticmethod
    def _remove_parens(logical_line, parens_coord):
        open_, space, replacement, close, _ = parens_coord
        physical_lines = logical_line.line.splitlines(keepends=True)

        idx_open_line = open_[0] - 1
        physical_lines[idx_open_line] = (
            physical_lines[idx_open_line][:open_[1]]
            + replacement
            + physical_lines[idx_open_line][space:]
        )
        shift = 0
        if open_[0] == close[0]:
            shift -= (space - open_[1]) - len(replacement)
        idx_close_line = close[0] - 1
        shifted_close_col = close[1] + shift
        physical_lines[idx_close_line] = (
            physical_lines[idx_close_line][:shifted_close_col]
            + " "
            + physical_lines[idx_close_line][shifted_close_col + 1:]
        )
        return "".join(physical_lines)

    @classmethod
    def _get_rewrites(
        cls, parens_coords: t.List[ParensCords], tree, tokens
    ) -> t.Generator[ProblemRewrite, None, None]:
        # exceptions made for parentheses that are not strictly necessary
        # but help readability
        if not parens_coords:
            return
        parens_coords = sorted(parens_coords, key=lambda x: x.token_indexes[0])
        yield from cls._get_exceptions_for_neighboring_parens(parens_coords,
                                                              tokens)
        yield from cls._get_exceptions_from_ast(parens_coords, tree, tokens)

    @classmethod
    def _get_exceptions_from_ast(cls, sorted_parens_coords, tree, tokens):
        special_ops_pair_exceptions = (
            ast.BinOp, ast.BoolOp, ast.UnaryOp, ast.Compare, ast.Await
        )
        nodes = list(cls._nodes_with_pos_and_parents(tree))
        nodes.sort(key=lambda x: (x[1], len(x[3])))

        yield from cls._tuple_exceptions(sorted_parens_coords, nodes, tokens)

        nodes_idx = 0
        last_exception_node = None
        rewrite_buffer = None
        for parens_coord_idx, parens_coord in enumerate(sorted_parens_coords):
            # node, pos, parents = nodes[nodes_idx]
            # while pos < parens_coord.open_:
            #     nodes_idx += 1
            #     if nodes_idx >= len(nodes):
            #         return
            #     node, pos, parents = nodes[nodes_idx]
            # descending = True
            # while descending and pos <= parens_coord.close:
            #     # if not cls._node_in_parens(node, parens_coord):
            #     #     continue
            #     # Make sure not to treat the same node again.
            #     # Max. one exception per node.
            #     if parents and isinstance(parents[0], ast.Slice):
            #         yield ProblemRewrite(parens_coord.open_, None)
            #     elif (
            #         parents
            #         and isinstance(parents[0], special_ops_pair_exceptions)
            #         and isinstance(node, special_ops_pair_exceptions)
            #     ):
            #         yield ProblemRewrite(parens_coord.open_, None)
            #     elif isinstance(node, ast.Tuple):
            #         if (
            #             parents
            #             and isinstance(parents[0], ast.Assign)
            #             and node in parents[0].targets
            #         ):
            #             yield ProblemRewrite(
            #                 parens_coord.open_,
            #                 "PAR002: Dont use parentheses for unpacking"
            #             )
            #         else:
            #             yield ProblemRewrite(parens_coord.open_, None)
            #     # TODO: comprehension.ifs
            #     # Make sure not to treat the same node again.
            #     # Max. one exception per node.
            #     nodes_idx += 1
            #     if nodes_idx >= len(nodes):
            #         return
            #     previous_parents = parents
            #     node, pos, parents = nodes[nodes_idx]
            #     descending = (
            #         previous_parents == parents[-len(previous_parents):]
            #     )

            node, pos, end, parents = nodes[nodes_idx]
            while not cls._node_in_parens(parens_coord, pos, end):
                nodes_idx += 1
                if nodes_idx >= len(nodes):
                    return
                node, pos, end, parents = nodes[nodes_idx]
            if rewrite_buffer is not None and last_exception_node is not node:
                # moved to the next node => emmit the exception
                yield rewrite_buffer
                rewrite_buffer = None

            # if last_exception_node == node:
            #     # Make sure not to treat the same node again.
            #     # Max. one exception per node.
            #     continue
            if (
                parents
                and isinstance(parents[0], ast.Slice)
                and isinstance(node, special_ops_pair_exceptions)
            ):
                rewrite_buffer = ProblemRewrite(parens_coord.open_, None)
                last_exception_node = node
            elif (
                parents
                and isinstance(parents[0], special_ops_pair_exceptions)
                and isinstance(node, special_ops_pair_exceptions)
            ):
                rewrite_buffer = ProblemRewrite(parens_coord.open_, None)
                last_exception_node = node
            elif isinstance(node, ast.Tuple):
                if (
                    parents
                    and isinstance(parents[0], ast.Assign)
                    and node in parents[0].targets
                ):
                    rewrite_buffer = ProblemRewrite(
                        parens_coord.open_,
                        "PAR002: Dont use parentheses for unpacking"
                    )
                    last_exception_node = node
            # TODO: comprehension.ifse
            # Make sure not to treat the same node again.
            # Max. one exception per node.
            # nodes_idx += 1
            # if nodes_idx >= len(nodes):
            #     return
            # node, pos, end, parents = nodes[nodes_idx]
        if rewrite_buffer is not None:
            yield rewrite_buffer

    @classmethod
    def _tuple_exceptions(cls, sorted_parens_coords, sorted_nodes, tokens):
        # Tuples need extra care, because the parentheses are not included
        # in the ast position (unless necessary)
        tokens = [token for token in tokens
                  if token.type not in IGNORED_TYPES_FOR_PARENS]
        tokens_idx = 0
        parens_coord_idx = 0
        for node, pos, end, parents in sorted_nodes:
            if not isinstance(node, ast.Tuple):
                continue
            while tokens[tokens_idx].start < pos:
                tokens_idx += 1
            if not tokens_idx:
                continue
            prev_token_pos = tokens[tokens_idx - 1].start
            parens_coord = sorted_parens_coords[parens_coord_idx]
            while parens_coord.open_ < prev_token_pos:
                parens_coord_idx += 1
                if parens_coord_idx >= len(sorted_parens_coords):
                    return
                parens_coord = sorted_parens_coords[parens_coord_idx]
            if parens_coord.open_ == prev_token_pos:
                yield ProblemRewrite(parens_coord.open_, None)

                    # for node in ast.walk(tree):
        #     breaker = False
        #     if isinstance(node, ast.Slice):
        #         for child in ast.iter_child_nodes(node):
        #             for coords in sorted_parens_coords:
        #                 if self.checked_parentheses(coords):
        #                     continue
        #                 if ((coords.open_[0], coords.open_[1] + 1)
        #                     == (child.lineno, child.col_offset)
        #                     and isinstance(child,
        #                                    special_ops_pair_exceptions)):
        #                     breaker = True
        #                     self.exceptions.append(coords)
        #             if breaker:
        #                 break
        #     elif isinstance(node, special_ops_pair_exceptions):
        #         for child in ast.iter_child_nodes(node):
        #             if not isinstance(child, special_ops_pair_exceptions):
        #                 continue
        #             for coords in sorted_parens_coords:
        #                 if (self.checked_parentheses(coords)
        #                     or self._node_in_parens(node, coords)):
        #                     continue
        #                 if self._node_in_parens(child, coords):
        #                     self.exceptions.append(coords)
        #                     breaker = True
        #                     break
        #             if breaker:
        #                 break
        #
        #     elif isinstance(node, ast.Assign):
        #         for target in node.targets:
        #             if not isinstance(target, ast.Tuple):
        #                 continue
        #             if not target.elts:
        #                 continue
        #             elt = target.elts[0]
        #             elt_coords = (elt.lineno, elt.col_offset)
        #             matching_parens = None
        #             for coords in sorted_parens_coords:
        #                 if self.checked_parentheses(coords):
        #                     continue
        #                 if self._node_in_parens(elt, coords):
        #                     matching_parens = coords
        #                     break
        #             if not matching_parens:
        #                 continue
        #             if not any(
        #                 self.file_tokens_nn[token].start == elt_coords
        #                 and self.file_tokens_nn[token - 1].string
        #                 == "("
        #                 for token in range(len(self.file_tokens_nn))
        #             ):
        #                 break
        #             self.problems.append((
        #                 node.lineno, node.col_offset,
        #                 "PAR002: Dont use parentheses for "
        #                 "unpacking"
        #             ))
        #             # no need to treat them again later
        #             self.exceptions.append(matching_parens)
        #             break
        #
        #     elif isinstance(node, ast.Tuple):
        #         for coords in sorted_parens_coords:
        #             if self.checked_parentheses(coords):
        #                 continue
        #             if self._check_parens_is_tuple(node, coords):
        #                 self.exceptions.append(coords)
        #                 break
        #
        #     elif isinstance(node, ast.comprehension):
        #         for coords in sorted_parens_coords:
        #             if self.checked_parentheses(coords):
        #                 continue
        #             for child in node.ifs:
        #                 if not self._node_in_parens(child, coords):
        #                     break
        #                 if coords.open_[0] != coords.close[0]:
        #                     self.exceptions.append(coords)
        #                     breaker = True
        #                     break
        #             if breaker:
        #                 break

    @classmethod
    def _nodes_with_pos_and_parents(cls, node, parents=()):
        pos = cls._node_pos(node, None)
        end = (0, 0) if pos is None else pos
        child_parents = (node, *parents)
        for field, value in ast.iter_fields(node):
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, ast.AST):
                        for child in cls._nodes_with_pos_and_parents(
                            item, child_parents
                        ):
                            yield child
                            end = max(end, child[2])
            elif isinstance(value, ast.AST):
                for child in cls._nodes_with_pos_and_parents(
                    value, child_parents
                ):
                    yield child
                    end = max(end, child[2])

        if pos is not None:
            yield node, pos, end, parents

    @staticmethod
    def _node_pos(node, default):
        if not hasattr(node, "lineno") or not hasattr(node, "col_offset"):
            return default
        return node.lineno, node.col_offset

    @staticmethod
    def _get_exceptions_for_neighboring_parens(sorted_optional_parens_coords,
                                               tokens):
        if len(sorted_optional_parens_coords) < 2:
            return
        coords2 = sorted_optional_parens_coords[0]
        coords_are_neighboring = prev_were_neighboring = False
        idx = 1
        while idx < len(sorted_optional_parens_coords):
            coords1 = coords2
            coords2 = sorted_optional_parens_coords[idx]
            open_start = coords1.token_indexes[0] + 1
            open_end = coords2.token_indexes[0]
            close_start = coords2.token_indexes[1] + 1
            close_end = coords1.token_indexes[1]
            tokens_between = (tokens[open_start:open_end]
                              + tokens[close_start:close_end])
            if not open_start <= open_end < close_start <= close_end:
                coords_are_neighboring = False
            else:
                coords_are_neighboring = all(
                    token.type in IGNORED_TYPES_FOR_PARENS
                    for token in tokens_between
                )
            if not coords_are_neighboring and prev_were_neighboring:
                yield ProblemRewrite(coords1.open_, None)
            prev_were_neighboring = coords_are_neighboring
            idx += 1
        if coords_are_neighboring:
            yield ProblemRewrite(coords2.open_, None)

    @staticmethod
    def _node_in_parens(parens_coord, pos, end):
        open_, _, _, close, _ = parens_coord
        return open_ <= pos <= end <= close

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

    def check_(self) -> None:
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
        end_offset = 36 if isinstance(node, ast.ClassDef) else 16
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
            if (line_num < checked_lines
                    or code_to_check[line_num].strip() == ""):
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
        return line, len(line), moved_counter + 1
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

    line_num_idx = next(
        idx for idx in range(len(logic_lines))
        if parens_coords[3][0] <= logic_lines_num[idx]
    )

    if logic_lines_num[line_num_idx - 1] <= parens_coords[3][0]:
        move_lines = logic_lines_num[line_num_idx - 1]
    split_line = logic_lines[line_num_idx].split("\n")
    idx_open_line = open_[0] - move_lines - 1
    split_line[idx_open_line] = (
        split_line[idx_open_line][:open_[1] - logic_line_move[line_num_idx]]
        + replacement
        + split_line[idx_open_line][space - logic_line_move[line_num_idx]:]
    )
    shift = 0
    if open_[0] == close[0]:
        shift -= (space - open_[1]) - len(replacement)
    idx_close_line = close[0] - move_lines - 1
    shifted_close_col = close[1] + shift - logic_line_move[line_num_idx]
    split_line[idx_close_line] = (
        split_line[idx_close_line][:shifted_close_col]
        + " "
        + split_line[idx_close_line][shifted_close_col + 1:]
    )
    patched_line = "\n".join(split_line)
    return build_tree(patched_line, logic_line_trees)
