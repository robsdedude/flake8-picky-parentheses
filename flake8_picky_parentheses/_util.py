from collections import namedtuple
import tokenize

OPEN_LIST = ["[", "{", "("]
CLOSE_LIST = ["]", "}", ")"]


ParensCords = namedtuple("ParensCords", [
    "open", "open_end_col", "replacement", "close", "token_indexes"
])


def find_parens_coords(token):
    # return parentheses paris in the form
    # (
    #   (open_line, open_col),
    #   open_end_col,
    #   replacement,
    #   (close_line, close_col)
    # )
    opening_stack = []
    parentheses_pairs = []
    last_line = -1
    for i in range(len(token)):
        first_in_line = last_line != token[i].start[0]
        last_line = token[i].end[0]
        if token[i].type == tokenize.OP:
            if token[i].string in OPEN_LIST:
                if not first_in_line:
                    opening_stack.append([token[i].start, token[i].end[1],
                                          " ", token[i].string, i])
                    continue
                if token[i + 1].start[0] == token[i].end[0]:
                    opening_stack.append([token[i].start,
                                          token[i + 1].start[1], "",
                                          token[i].string, i])
                    continue
                # there is only this opening parenthesis on this line
                opening_stack.append([token[i].start, len(token[i].line) - 2,
                                      "", token[i].string, i])

            if token[i].string in CLOSE_LIST:
                opening = opening_stack.pop()
                assert (OPEN_LIST.index(opening[3])
                        == CLOSE_LIST.index(token[i].string))
                token_indexes = [opening[4], i]
                parentheses_pairs.append(
                    ParensCords(*opening[0:3], token[i].start, token_indexes)
                )

    return parentheses_pairs
