from __future__ import annotations

import ast
from dataclasses import dataclass
import re
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
        file_tokens: t.Iterable[tokenize.TokenInfo],
        lines: t.List[str],
    ) -> None:
        self.tree = tree
        self.file_tokens = list(file_tokens)
        self.lines = lines
        self.logical_lines = list(
            self.get_logical_lines(self.lines, self.file_tokens)
        )
        self.problems: t.Iterable[t.Tuple[int, int, str]] = []

    @staticmethod
    def get_logical_lines(lines, tokens):
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
            elif (
                parents
                and isinstance(parents[0], ast.comprehension)
                and node in parents[0].ifs
                and parens_coord.open_[0] != parens_coord.close[0]
            ):
                rewrite_buffer = ProblemRewrite(parens_coord.open_, None)
                last_exception_node = node

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
