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
        for cords in self.all_parens_coords:
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

        # if two brackets start on same line (after one another)
        # they need to end on the same line
        parens_cords_sorted = sorted(self.all_parens_coords,
                                     key=lambda x: x[0])
        for cords1, cords2 in zip(parens_cords_sorted[:-1],
                                  parens_cords_sorted[1:]):
            if cords1[3] < cords2[0]:
                # not nested
                continue
            if (cords1[0][0] == cords2[0][0]
                    and cords1[3][0] != cords2[3][0]):
                self.problems.append((
                    cords1[0][0], cords1[0][1],
                    "BRA001: Opening bracket on one line, but closing on "
                    "different lines"
                ))

        # if there is a closing bracket on after a new line, this line should
        # only contain: operators and comments
        for cords in self.all_parens_coords:
            _, token_idx_end = cords.token_indexes
            close_cords = cords.close
            if not self.first_in_line(close_cords):
                continue
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
