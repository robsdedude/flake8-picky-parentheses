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

from ._util import (
    CLOSE_LIST,
    find_parens_coords,
    OPEN_LIST,
)


class PluginBracketsPosition:
    name = __name__
    version = metadata.version("flake8_picky_parentheses")

    def __init__(self, tree, read_lines, file_tokens):
        self.source_code_lines = list(read_lines())
        self.file_token = list(file_tokens)
        # all parentheses coordinates
        self.all_parens_coords = find_parens_coords(self.file_token)
        self.problems: List[Tuple[int, int, str]] = []

    def run(self) -> Generator[Tuple[int, int, str, Type[Any]], None, None]:
        if not self.all_parens_coords:
            return
        self.check_brackets_position()
        for line, col, msg in self.problems:
            yield line, col, msg, type(self)

    @staticmethod
    def first_in_line(cords, source_code):
        return all(
            source_code[cords[0] - 1][col] in (" ", "\t")
            for col in range(cords[1])
        )

    @staticmethod
    def last_in_line(cords, source_code):
        line = source_code[cords[0] - 1]
        return all(
            line[col] in (" ", "\t", "\n")
            for col in range(cords[1] + 1, len(line))
        )

    def check_brackets_position(self):
        for cords in self.all_parens_coords:
            if cords[0][0] == cords[3][0]:
                # opening and closing brackets in the same line
                continue
            if not self.last_in_line(cords[0], self.source_code_lines):
                continue
            if not self.first_in_line(cords[3], self.source_code_lines):
                self.problems.append((
                    cords[0][0], cords[0][1],
                    "BRA001: Opening bracket is last, but closing is not "
                    "on new line"
                ))
                continue
            for num in range(len(self.file_token)):
                if self.file_token[num].start != cords[0]:
                    continue
                i = 1
                a = 1
                while self.file_token[num - i + 1].type == tokenize.OP:
                    if self.file_token[num - i].type == tokenize.NAME:
                        if (self.file_token[num - 1].string
                                in OPEN_LIST
                           and self.source_code_lines
                                [cords[3][0] - 1][cords[3][1] + 1]
                                not in CLOSE_LIST):
                            self.problems.append((
                                cords[0][0], cords[0][1],
                                "BRA002: Closing is on new line but "
                                "indentation mismatch"
                            ))
                            break
                        elif 0 != cords[3][1]:
                            self.problems.append((
                                cords[0][0], cords[0][1],
                                "BRA002: Closing is on new line but "
                                "indentation mismatch"
                            ))
                            break
                        a += 1
                    i += 1
                if cords[0][1] != cords[3][1] and a == 1:
                    self.problems.append((
                        cords[0][0], cords[0][1],
                        "BRA002: Closing is on new line but indentation "
                        "mismatch"
                    ))
                    break



