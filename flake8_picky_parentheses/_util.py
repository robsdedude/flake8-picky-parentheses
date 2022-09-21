import tokenize
import typing as t

OPEN_LIST = ["[", "{", "("]
CLOSE_LIST = ["]", "}", ")"]


class ParensCords(t.NamedTuple):
    open_: t.Tuple[int, int]
    open_end_col: int
    replacement: str
    close: t.Tuple[int, int]
    token_indexes: t.Tuple[int, int]


def find_parens_coords(
    tokens: t.List[tokenize.TokenInfo]
) -> t.List[ParensCords]:
    # return parentheses paris in the form
    # (
    #   (open_line, open_col),
    #   open_end_col,
    #   replacement,
    #   (close_line, close_col)
    # )
    opening_stack: t.List[t.Tuple[t.Tuple[int, int], int, str, str, int]] = []
    parentheses_pairs = []
    last_line = -1
    for i in range(len(tokens)):
        first_in_line = last_line != tokens[i].start[0]
        last_line = tokens[i].end[0]
        if tokens[i].type == tokenize.OP:
            if tokens[i].string in OPEN_LIST:
                if not first_in_line:
                    opening_stack.append((tokens[i].start, tokens[i].end[1],
                                          " ", tokens[i].string, i))
                    continue
                if tokens[i + 1].start[0] == tokens[i].end[0]:
                    opening_stack.append((tokens[i].start,
                                          tokens[i + 1].start[1], "",
                                          tokens[i].string, i))
                    continue
                # there is only this opening parenthesis on this line
                opening_stack.append((tokens[i].start, len(tokens[i].line) - 2,
                                      "", tokens[i].string, i))

            if tokens[i].string in CLOSE_LIST:
                opening = opening_stack.pop()
                assert (OPEN_LIST.index(opening[3])
                        == CLOSE_LIST.index(tokens[i].string))
                token_indexes = (opening[4], i)
                parentheses_pairs.append(
                    ParensCords(*opening[0:3], tokens[i].start, token_indexes)
                )

    return parentheses_pairs
