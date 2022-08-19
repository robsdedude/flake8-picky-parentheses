import tokenize
try:
    # Python 3.8+
    from importlib import metadata
except ImportError:
    import importlib_metadata as metadata
from typing import (
    Any,
    Generator,
    List,
    Tuple,
    Type,
)

from ._util import find_parens_coords


class PluginBracketsPosition:
    name = __name__
    version = metadata.version("flake8_picky_parentheses")

    def __init__(self, tree, read_lines, file_tokens):
        self.source_code_lines = list(read_lines())
        self.file_tokens = list(file_tokens)
        # all parentheses coordinates
        self.all_parens_coords = find_parens_coords(self.file_tokens)
        self.problems: List[Tuple[int, int, str]] = []

    def run(self) -> Generator[Tuple[int, int, str, Type[Any]], None, None]:
        if not self.all_parens_coords:
            return
        self.check_brackets_position()
        for line, col, msg in self.problems:
            yield line, col, msg, type(self)

    def first_in_line(self, cords):
        return all(
            self.source_code_lines[cords[0] - 1][col] in (" ", "\t")
            for col in range(cords[1])
        )

    def last_in_line(self, cords):
        line = self.source_code_lines[cords[0] - 1]
        return all(
            line[col] in (" ", "\t", "\n")
            for col in range(cords[1] + 1, len(line))
        )

    def get_line_indentation(self, cords_open):
        line_tokens = (
            token for token in self.file_tokens
            if token.start[0] == cords_open[0]
        )
        for token in line_tokens:
            if token.type == tokenize.INDENT:
                continue
            return token.start[1]
        raise AssertionError("This should never happen")

    def check_brackets_position(self):
        parens_cords_sorted = sorted(self.all_parens_coords,
                                     key=lambda x: x.token_indexes[0])
        for cords_idx, cords in enumerate(parens_cords_sorted):
            cords_open, cords_close = cords[0], cords[3]
            if cords_open[0] == cords_close[0]:
                # opening and closing brackets in the same line
                continue
            if not self.last_in_line(cords_open):
                continue
            if not self.first_in_line(cords_close):
                self.problems.append((
                    cords_open[0], cords_open[1],
                    "BRA001: Opening bracket is last, but closing is not "
                    "on new line"
                ))
                continue
            # check if the closing bracket has the same indentation as the
            # line with the opening bracket
            if cords_close[1] != self.get_line_indentation(cords_open):
                self.problems.append((
                    cords_close[0], cords_close[1],
                    "BRA001: Closing bracket has different indentation than "
                    "the line with the opening bracket"
                ))

            # if lines ends with `[({`, there should be a line that starts
            # with `]})` (matching closing brackets)
            for offset, prev_cords in enumerate(
                reversed(parens_cords_sorted[:cords_idx])
            ):
                offset += 1
                prev_cord_open_token_idx = prev_cords.token_indexes[0]
                prev_cord_close_token_idx = prev_cords.token_indexes[1]
                cord_open_token_idx = cords.token_indexes[0]
                cord_close_token_idx = cords.token_indexes[1]
                is_opening_sequence = \
                    prev_cord_open_token_idx == cord_open_token_idx - offset
                is_closing_sequence = \
                    prev_cord_close_token_idx == cord_close_token_idx + offset
                if is_opening_sequence and not is_closing_sequence:
                    self.problems.append((
                        cords[0][0], cords[0][1],
                        "BRA001: Consecutive opening brackets at the end of "
                        "the line must have consecutive closing brackets."
                    ))

        # if there is a closing bracket on after a new line, this line should
        # only contain: operators and comments
        for cords in self.all_parens_coords:
            _, token_idx_end = cords.token_indexes
            close_cords = cords.close
            if not self.first_in_line(close_cords):
                continue
            if (
                token_idx_end < len(self.file_tokens) - 1
                and self.file_tokens[token_idx_end + 1].type == tokenize.NAME
                # and self.file_tokens[token_idx_end + 1].string == "as"
                # and self.file_tokens[token_idx_end + 2].type == tokenize.NAME
                # and self.file_tokens[token_idx_end + 3].type == tokenize.OP
                # and self.file_tokens[token_idx_end + 3].string == ":"
            ):
                # the next token is probably a keyword
                break
            for token in self.file_tokens[token_idx_end:]:
                if token.type in (tokenize.NL, tokenize.NEWLINE):
                    # reached the next line, all cool
                    break
                if token.type not in (tokenize.OP, tokenize.COMMENT):
                    self.problems.append((
                        close_cords[0], close_cords[1],
                        "BRA001: Only operators and comments are allowed "
                        "after a closing bracket on a new line"
                    ))
                    break
