# Copyright Rouven Bauer
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from __future__ import annotations

import tokenize
import typing as t

from ._meta import version
from ._util import find_parens_coords

if t.TYPE_CHECKING:
    from argparse import Namespace

    from flake8.options.manager import OptionManager
    from flake8.style_guide import DecisionEngine

    from ._util import ParensCords


class PluginBracketsPosition:
    name = __name__
    version = version
    _decision_engine: t.ClassVar[DecisionEngine | None] = None
    _enabled: t.ClassVar[dict[str, bool]] = {}

    all_parens_coords: list[ParensCords]

    def __init__(self, tree, read_lines, file_tokens):
        self.source_code_lines = list(read_lines())
        self.file_tokens = list(file_tokens)
        # all parentheses coordinates
        self.all_parens_coords = find_parens_coords(self.file_tokens)
        self.problems: list[tuple[int, int, str]] = []

    def run(self) -> t.Generator[tuple[int, int, str, t.Type], None, None]:
        if not self.all_parens_coords:
            return
        self.check_brackets_position()
        for line, col, msg in self.problems:
            yield line, col, msg, type(self)

    @classmethod
    def parse_options(
        cls,
        option_manager: OptionManager,
        options: Namespace,
        args: list[str],
    ) -> None:
        from flake8.style_guide import DecisionEngine

        cls._decision_engine = DecisionEngine(options)

    @classmethod
    def rules_enabled(cls, *codes: str) -> bool:
        from flake8.style_guide import Decision

        def rule_enabled(code: str) -> bool:
            if cls._decision_engine is None:
                return True

            enabled = cls._enabled.get(code, None)
            if enabled is None:
                decision = cls._decision_engine.make_decision(code)
                enabled = decision == Decision.Selected
                cls._enabled[code] = enabled

            return enabled

        return all(rule_enabled(code) for code in codes)

    def first_in_line(self, cords: tuple[int, int]) -> bool:
        return all(
            self.source_code_lines[cords[0] - 1][col] in (" ", "\t")
            for col in range(cords[1])
        )

    def last_in_line(self, cords: ParensCords) -> bool:
        end = [tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE]
        open_token_idx = cords.token_indexes[0]
        next_token = self.file_tokens[open_token_idx + 1]
        return next_token.type in end

    def get_line_indentation(
        self,
        coords_open: tuple[int, int],
    ) -> tuple[int, int]:
        line_tokens = (
            token for token in self.file_tokens
            if token.start[0] == coords_open[0]
        )
        for token in line_tokens:
            if token.type == tokenize.INDENT:
                continue
            return token.start[1]
        raise AssertionError("This should never happen")

    def check_brackets_position(self) -> None:
        if self.rules_enabled("PAR101", "PAR102", "PAR103"):
            self._check_par101_to_103()
        if self.rules_enabled("PAR104"):
            self._check_par104()

    def _check_par101_to_103(self) -> None:
        parens_coords_sorted = sorted(self.all_parens_coords,
                                      key=lambda x: x.token_indexes[0])
        for cords_idx, coords in enumerate(parens_coords_sorted):
            coords_open, coords_close = coords[0], coords[3]
            if coords_open[0] == coords_close[0]:
                # opening and closing brackets in the same line
                continue
            if not self.last_in_line(coords):
                continue
            if not self.first_in_line(coords_close):
                self.problems.append((
                    coords_open[0], coords_open[1],
                    "PAR101: Opening bracket is last, but closing is not "
                    "on new line"
                ))
                continue
            # check if the closing bracket has the same indentation as the
            # line with the opening bracket
            if coords_close[1] != self.get_line_indentation(coords_open):
                count = 0
                while (self.file_tokens[coords.token_indexes[0] - count]
                       .start[0]
                        == self.file_tokens[coords.token_indexes[0]].start[0]):
                    count += 1
                if (self.file_tokens[coords.token_indexes[0] - count].type
                        == tokenize.STRING):
                    break
                self.problems.append((
                    coords_close[0], coords_close[1],
                    "PAR102: Closing bracket has different indentation than "
                    "the line with the opening bracket"
                ))

            # if lines ends with `[({`, there should be a line that starts
            # with `]})` (matching closing brackets)
            if not self.rules_enabled("PAR103"):
                continue
            for offset, prev_coords in enumerate(
                reversed(parens_coords_sorted[:cords_idx])
            ):
                offset += 1
                prev_coord_open_token_idx = prev_coords.token_indexes[0]
                prev_coord_close_token_idx = prev_coords.token_indexes[1]
                coord_open_token_idx = coords.token_indexes[0]
                coord_close_token_idx = coords.token_indexes[1]
                is_opening_sequence = \
                    prev_coord_open_token_idx == coord_open_token_idx - offset
                is_closing_sequence = \
                    prev_coord_close_token_idx == coord_close_token_idx \
                    + offset
                if is_opening_sequence and not is_closing_sequence:
                    self.problems.append((
                        coords[0][0], coords[0][1],
                        "PAR103: Consecutive opening brackets at the end of "
                        "the line must have consecutive closing brackets."
                    ))

    def _check_par104(self) -> None:
        # if there is a closing bracket on after a new line, this line should
        # only contain: operators and comments
        for coords in self.all_parens_coords:
            if coords[0] in self.problems:
                continue
            breaker = None
            _, token_idx_end = coords.token_indexes
            close_coords = coords.close
            if not self.first_in_line(close_coords):
                continue
            if self.file_tokens[token_idx_end - 1].type == tokenize.NL:
                token = token_idx_end
                try:
                    if (
                        token_idx_end < len(self.file_tokens) - 1
                        and self.file_tokens[token_idx_end + 1].type
                            in (tokenize.NAME, tokenize.OP)
                    ):
                        if self.file_tokens[token_idx_end + 1].string == ".":
                            continue
                        while (self.file_tokens[token].type != tokenize.NL
                               or self.file_tokens[token].type
                               != tokenize.NEWLINE):
                            if (self.file_tokens[token - 1].string == ":"
                                    and self.file_tokens[token].type
                                    in (tokenize.NEWLINE, tokenize.NL)):
                                # the next token is probably a keyword
                                breaker = 1
                                break
                            token += 1
                except IndexError:
                    pass
            for token in self.file_tokens[token_idx_end:]:
                if token.type in (tokenize.NL, tokenize.NEWLINE):
                    # reached the next line, all cool
                    break
                if (token.type not in (tokenize.OP, tokenize.COMMENT)
                        and breaker != 1):
                    self.problems.append((
                        close_coords[0], close_coords[1],
                        "PAR104: Only operators and comments are allowed "
                        "after a closing bracket on a new line"
                    ))
                    break
