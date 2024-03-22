from __future__ import annotations

import ast
from dataclasses import dataclass
import sys
import tokenize
import typing as t

from ._meta import version
from ._util import find_parens_coords

if t.TYPE_CHECKING:
    from ._util import ParensCords


AST_FIX_PREFIXES = {
    "else": "if True:\n   pass\n",
    "elif": "if True:\n   pass\n",
    "except": "try:\n   pass\n",
    "finally": "try:\n   pass\n",
    "case": "match _:\n    ",
}

AST_FIX_SPECIAL_BODIES = {
    "match": "\n    case _:\n        pass",
}

IGNORED_TYPES_FOR_PARENS = {
    tokenize.NL,
    tokenize.COMMENT,
}

LOGICAL_LINE_STRIPPED_TYPES = {
    tokenize.NEWLINE, tokenize.NL, tokenize.COMMENT,
    tokenize.INDENT, tokenize.DEDENT, tokenize.ENDMARKER
}


class LogicalLine:
    def __init__(
        self,
        line: str,
        line_offset: int,
        tokens: t.Optional[t.Tuple[tokenize.TokenInfo]] = None,
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

    def __repr__(self):
        return f"<LogicalLine L{self.line_offset + 1} {self.line!r}>"


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

    @staticmethod
    def _get_logical_lines(lines, tokens):
        prev_end_line = 0
        for token in tokens:
            if token.type == tokenize.NEWLINE:
                yield LogicalLine(
                    "".join(lines[prev_end_line:token.start[0]]),
                    prev_end_line,
                )
                prev_end_line = token.start[0]

    def run(
        self
    ) -> t.Generator[t.Tuple[int, int, str, t.Type[t.Any]], None, None]:
        logical_lines = self._get_logical_lines(self.lines, self.file_tokens)
        problems = self._check(logical_lines, self.tree, self.file_tokens)
        for line, col, msg in problems:
            yield line, col, msg, type(self)

    @classmethod
    def _check(cls, logical_lines, tree, file_tokens):
        raw_problems = cls._get_raw_problems(logical_lines)
        yield from cls._rewrite_problems(raw_problems, tree, file_tokens)

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
            for line, column, msg in cls._check_logical_line(logical_line):
                if line == 1:
                    column += logical_line.column_offset
                line += logical_line.line_offset
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
        first_relevant_token = next(
            token for token in logical_line.tokens
            if token.type not in LOGICAL_LINE_STRIPPED_TYPES
        )
        last_relevant_token = next(
            token for token in reversed(logical_line.tokens)
            if token.type not in LOGICAL_LINE_STRIPPED_TYPES
        )
        split_lines = logical_line.line.splitlines()
        start = first_relevant_token.start[0] - 1
        end = last_relevant_token.end[0] - 1
        split_lines = split_lines[start:(end + 1)]
        line_offset = logical_line.line_offset + start
        start = first_relevant_token.start[1]
        end = last_relevant_token.end[1]
        if len(split_lines) == 1:
            split_lines[0] = split_lines[0][start:(end + 1)]
        else:
            split_lines[0] = split_lines[0][start:]
            split_lines[-1] = split_lines[-1][:(end + 1)]
        column_offset = logical_line.column_offset + start
        return LogicalLine(
            line="\n".join(split_lines),
            line_offset=line_offset,
            column_offset=column_offset
        )

    @staticmethod
    def _pad_logical_line(logical_line):
        tokens = logical_line.tokens
        if not tokens:
            return logical_line
        needs_body = logical_line.line.rstrip().endswith(":")
        is_decorator = logical_line.line.lstrip().startswith("@")
        ast_fix_prefix = AST_FIX_PREFIXES.get(tokens[0].string)
        if not (needs_body or is_decorator or ast_fix_prefix):
            return logical_line

        line = logical_line.line
        line_offset = logical_line.line_offset
        column_offset = logical_line.column_offset
        if is_decorator:
            line += "\ndef f():"
            needs_body = True
        if needs_body:
            keyword = line.strip().split()[0]
            line += AST_FIX_SPECIAL_BODIES.get(keyword, "\n    pass")
        if ast_fix_prefix:
            extra_indent = ast_fix_prefix.rsplit("\n", 1)[-1]
            if extra_indent.strip():
                extra_indent = ""  # contains not only whitespace
            if extra_indent:
                line = "\n".join(extra_indent + s for s in line.split("\n"))
                column_offset -= len(extra_indent)
                ast_fix_prefix = ast_fix_prefix[:-len(extra_indent)]
            line = ast_fix_prefix + line
            line_offset -= ast_fix_prefix.count("\n")
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
            ast.BinOp, ast.BoolOp, ast.UnaryOp, ast.Compare, ast.Await,
            ast.IfExp
        )
        comprehension_exceptions = (
            ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp
        )
        nodes = list(cls._nodes_with_pos_and_parents(tree))
        nodes.sort(key=lambda x: (x[1], len(x[3])))

        yield from cls._tuple_exceptions(sorted_parens_coords, nodes, tokens)

        nodes_idx = 0
        last_exception_node = None
        rewrite_buffer = None
        for parens_coord in sorted_parens_coords:
            node, pos, end, parents = nodes[nodes_idx]
            while not cls._node_in_parens(
                parens_coord, node, pos, end, tokens
            ):
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
                and isinstance(parents[0], (ast.Slice, ast.Starred))
                and isinstance(node, special_ops_pair_exceptions)
            ):
                rewrite_buffer = ProblemRewrite(parens_coord.open_, None)
                last_exception_node = node
                continue
            if (
                parents
                and isinstance(parents[0], comprehension_exceptions)
                and isinstance(node, special_ops_pair_exceptions)
                and node in (getattr(parents[0], attr, None)
                             for attr in ("elt", "key", "value"))
            ):
                rewrite_buffer = ProblemRewrite(parens_coord.open_, None)
                last_exception_node = node
                continue
            if (
                parents
                and isinstance(parents[0], special_ops_pair_exceptions)
                and isinstance(node, special_ops_pair_exceptions)
            ):
                rewrite_buffer = ProblemRewrite(parens_coord.open_, None)
                last_exception_node = node
                continue
            if (
                parents
                and isinstance(parents[0], ast.keyword)
                and parents[0].arg is None
                and isinstance(node, special_ops_pair_exceptions)
            ):
                rewrite_buffer = ProblemRewrite(parens_coord.open_, None)
                last_exception_node = node
                continue
            if (
                isinstance(node, ast.Tuple)
                and parents
                and isinstance(parents[0], ast.Assign)
                and node in parents[0].targets
            ):
                rewrite_buffer = ProblemRewrite(
                    parens_coord.open_,
                    "PAR002: Dont use parentheses for unpacking"
                )
                last_exception_node = node
                continue
            if (
                parents
                and isinstance(parents[0], ast.comprehension)
                and (node in parents[0].ifs or node == parents[0].iter)
                and (parens_coord.open_[0] != pos[0] or pos[0] != end[0])
            ):
                rewrite_buffer = ProblemRewrite(parens_coord.open_, None)
                last_exception_node = node
                continue
            if (
                parents
                and isinstance(parents[0], ast.keyword)
                and (parens_coord.open_[0] != pos[0] or pos[0] != end[0])
            ):
                rewrite_buffer = ProblemRewrite(parens_coord.open_, None)
                last_exception_node = node
                continue
            if (
                parents
                and isinstance(parents[0], ast.arguments)
                and node in parents[0].defaults
                and (parens_coord.open_[0] != pos[0] or pos[0] != end[0])
            ):
                rewrite_buffer = ProblemRewrite(parens_coord.open_, None)
                last_exception_node = node
                continue
            if (
                sys.version_info >= (3, 10)
                and isinstance(node, ast.MatchSequence)
            ):
                rewrite_buffer = ProblemRewrite(parens_coord.open_, None)
                last_exception_node = node
                continue
            if (
                parents
                and isinstance(parents[0], (ast.Tuple, ast.List))
                and isinstance(node, ast.Str)
            ):
                tokens_slice = slice(parens_coord.token_indexes[0] + 1,
                                     parens_coord.token_indexes[1])
                string_tokens = [
                    token for token in tokens[tokens_slice]
                    if token.type == tokenize.STRING
                ]
                if string_tokens[0].start[0] != string_tokens[-1].start[0]:
                    rewrite_buffer = ProblemRewrite(parens_coord.open_, None)
                    last_exception_node = node
                    continue

        if rewrite_buffer is not None:
            yield rewrite_buffer

    @classmethod
    def _tuple_exceptions(cls, sorted_parens_coords, sorted_nodes, tokens):
        # Tuples need extra care, because the parentheses are not included
        # in the ast position (unless necessary) in Python 3.7
        # BUT, they are included in Python 3.8+
        tokens = [token for token in tokens
                  if token.type not in IGNORED_TYPES_FOR_PARENS]
        tokens_idx = 0
        parens_coord_idx = 0
        for node, pos, _, _ in sorted_nodes:
            if not isinstance(node, ast.Tuple):
                continue
            if sys.version_info >= (3, 8):
                while tokens[tokens_idx].start <= pos:
                    tokens_idx += 1
            else:
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
        for _, value in ast.iter_fields(node):
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
            yield node, pos, cls._node_end(node, end), parents

    @staticmethod
    def _node_pos(node, default):
        if not hasattr(node, "lineno") or not hasattr(node, "col_offset"):
            return default
        return node.lineno, node.col_offset

    @staticmethod
    def _node_end(node, default):
        if (
            not hasattr(node, "end_lineno")
            or not hasattr(node, "end_col_offset")
        ):
            return default
        return node.end_lineno, node.end_col_offset

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
    def _node_in_parens(parens_coord, node, pos, end, tokens):
        open_, _, _, close, _ = parens_coord
        close = close[0], close[1] + 1
        if (
            isinstance(node, ast.Tuple)
            and sys.version_info < (3, 8)
        ):
            # Python 3.7 does not include the redundant parentheses of tuples
            return open_ < pos <= end < close
        return open_ <= pos <= end <= close
