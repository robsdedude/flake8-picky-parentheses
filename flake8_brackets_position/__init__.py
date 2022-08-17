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

BRACKETS_LIST = ["{", "[", "(", "}", "]", ")"]


class Plugin_for_brackets_position:
    name = __name__
    version = metadata.version("flake8_redundant_parentheses")

    def __init__(self,  tree: ast.AST, read_lines, file_tokens):
        self.source_code_by_lines = list(read_lines())
        self.file_token = list(file_tokens)
        # all parentheses coordinates
        self.all_parens_coords = find_parens_coords(self.file_token)
        self.problems: List[Tuple[int, int, str]] = []

    def run(self) -> Generator[Tuple[int, int, str, Type[Any]], None, None]:
        if not self.all_parens_coords:
            return
        self.check_brackets_in_func()
        for line, col, msg in self.problems:
            yield line, col, msg, type(self)

    @staticmethod
    def _first_in_line(cords, source_code):
        for num in range(len(source_code[cords[0] - 1])):
            if source_code[cords[0] - 1][num] == " " or source_code[cords[0] - 1][num] == "\t":
                continue
            elif source_code[cords[0] - 1][num] in BRACKETS_LIST and cords[1] == num:
                return True
            else:
                return False

    @staticmethod
    def _last_in_line(cords, source_code):
        revers_code = list(reversed(source_code[cords[0] - 1]))
        for num in range(len(source_code[cords[0] - 1])):
            if revers_code[num] == " " or revers_code[num] == ":" or revers_code[num] == "\n":
                continue
            elif revers_code[num] in BRACKETS_LIST and len(revers_code) - cords[1] - 1 == num:
                return True
            else:
                return False

    def check_brackets_in_func(self):
        for cords in self.all_parens_coords:
            if cords[0][0] != cords[3][0]:
                if not self._last_in_line(cords[0], self.source_code_by_lines):
                    continue
                if not self._first_in_line(cords[3], self.source_code_by_lines):
                    self.problems.append((
                        cords[0][0], cords[0][1],
                        "BRA001: Opening bracket is last, but closing is not on new line"
                    ))
                    continue
                for num in range(len(self.file_token)):
                    if self.file_token[num].start != cords[0]:
                        continue
                    i = 1
                    a = 1
                    while self.file_token[num - i + 1].type == tokenize.OP:
                        if self.file_token[num - i].type == 1:
                            if (self.file_token[num - 1].string in BRACKETS_LIST
                               and self.source_code_by_lines[cords[3][0] - 1][cords[3][1] + 1] not in BRACKETS_LIST):
                                self.problems.append((
                                    cords[0][0], cords[0][1],
                                    "BRA002: Closing is on new line but indentation mismatch"
                                ))
                                break
                            elif self.file_token[num - i].start[1] != cords[3][1]:
                                self.problems.append((
                                    cords[0][0], cords[0][1],
                                    "BRA002: Closing is on new line but indentation mismatch"
                                ))
                                break
                            a += 1
                        i += 1
                    if cords[0][1] != cords[3][1] and a == 1:
                        self.problems.append((
                            cords[0][0], cords[0][1],
                            "BRA002: Closing is on new line but indentation mismatch"
                        ))
                        break


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
        if token[i].type == tokenize.OP:
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
