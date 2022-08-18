import io
import tokenize
from typing import Set

from flake8_picky_parentheses import PluginBracketsPosition

import pytest


def _results(s: str) -> Set[str]:
    def read_lines():
        return s.splitlines(keepends=True)

    file_tokens = tokenize.tokenize(io.BytesIO(s.encode("utf-8")).readline)
    plugin = PluginBracketsPosition(None, read_lines, file_tokens)
    return {f"{line}:{col + 1} {msg}" for line, col, msg, _ in plugin.run()}


# GOOD (use parentheses for line continuation)
def test_parentheses_in_if_on_new_line():
    s = """if (
a == b
): c + d
    """
    assert not _results(s)


# BAD (use parentheses in both case of line continuation)
def test_parentheses_in_if_only_with_second_new_line():
    s = """if ( a == b
): c + d
    """
    assert not _results(s)


# BAD (use parentheses in both case of line continuation)
def test_parentheses_in_if_only_with_first_new_line():
    s = """if (
a == b): c + d
    """
    assert _results(s)


# GOOD (have all brackets on the same line)
def test_list_in_one_line():
    s = """a = [1, 2, 3]"""
    assert not _results(s)


# GOOD
# (when the opening bracket is the last thing on a line, the matching closing
# bracket is the first thing on a new line that matches the indentation of the
# line with the opening bracket)
def test_list_with_enters_line():
    s = """a = [
1, 2, 3
]"""
    assert not _results(s)


# BAD (opening bracket is last, but closing is not on new line)
def test_list_with_only_one_enter_line():
    s = """a = [
1, 2, 3]"""
    assert _results(s)


# BAD
# (opening bracket is last, closing is on new line but indentation mismatch)
def test_list_mismatch_line():
    s = """a = [
1, 2, 3
    ]"""
    assert _results(s)


# GOOD (opening bracket is not last, so we don't care about the closing one)
def test_list_open_bracket_not_last():
    s = """a = [1, 2, 3
]"""
    assert not _results(s)


# GOOD (opening bracket is not last, so we don't care about the closing one)
def test_list_open_bracket_not_last_2():
    s = """a = [1, 2, 3
    ]"""
    assert not _results(s)


# (pretty much the same rules apply for multiple brackets)

# GOOD (have all brackets on the same line)
def test_nested_list():
    s = """a = [[1, 2, 3], [4, 5, 6]]"""
    assert not _results(s)


# GOOD
def test_nested_list_with_enters():
    s = """a = [
[1, 2, 3], [4, 5, 6]
]"""
    assert not _results(s)


# GOOD
def test_nested_list_with_enters_2():
    s = """a = [
[1, 2, 3],
[4, 5, 6]
]"""
    assert not _results(s)


# GOOD
def test_nested_list_with_enters_3():
    s = """a = [[
1, 2, 3
]]"""
    assert not _results(s)


# GOOD
def test_nested_list_with_enters_4():
    s = """a = [
    [
        1, 2, 3
    ],
    [
        4, 5, 6
    ]
]"""
    assert not _results(s)


# BAD
# (opening bracket is last, closing is on new line but indentation mismatch)
def test_nested_list_mismatch():
    s = """a = [
    [
        1, 2, 3
    ],
    [
        4, 5, 6
    ]
  ]"""
    assert _results(s)


# BAD
# (opening bracket is last, closing is on new line but indentation mismatch)
def test_nested_list_mismatch_2():
    s = """a = [
    [
        1, 2, 3
      ],
    [
        4, 5, 6
    ]
]"""
    assert _results(s)


# BAD
# (opening bracket is last, closing is on new line but indentation mismatch)
def test_nested_list_mismatch_3():
    s = """a = [
    [
        1, 2, 3
    ],
    [
        4, 5, 6
     ]
]"""
    assert _results(s)


# BAD (if you have a closing bracket on a new line, don't open a new bracket)
def test_nested_list_mismatch_4():
    s = """a = [[
    1, 2, 3
], [
    4, 5, 6
]]"""
    assert _results(s)


# BAD
# (1. if you have a closing bracket on a new line, don't open a new bracket
#  2. the first closing bracket's indentation is a missmatch)
def test_combine_two_faults():
    s = """a = [[
    1, 2, 3
    ], [
    4, 5, 6
]]"""
    assert _results(s)


# BAD
# (all opening brackets that are consecutive on the same line are on the same
# line should also have all closing brackets on the same line)
def test_brackets_on_diff_lines():
    s = """a = [[
    1, 2, 3
]
]"""
    assert _results(s)


def test_dict_in_one_line():
    s = """a = {1, 2, 3}"""
    assert not _results(s)


# GOOD
# (when the opening bracket is the last thing on a line, the matching closing
# bracket is the first thing on a new line that matches the indentation of the
# line with the opening bracket)
def test_dict_with_enters_line():
    s = """a = {
1, 2, 3
}"""
    assert not _results(s)


# BAD (opening bracket is last, but closing is not on new line)
def test_dict_with_only_one_enter_line():
    s = """a = {
1, 2, 3}"""
    assert _results(s)


# BAD
# (opening bracket is last, closing is on new line but indentation mismatch)
def test_dict_mismatch_line():
    s = """a = {
1, 2, 3
    }"""
    assert _results(s)


# GOOD (opening bracket is not last, so we don't care about the closing one)
def test_dict_open_bracket_not_last():
    s = """a = {1, 2, 3
}"""
    assert not _results(s)


# GOOD (opening bracket is not last, so we don't care about the closing one)
def test_dict_open_bracket_not_last_2():
    s = """a = {1, 2, 3
    }"""
    assert not _results(s)


# (pretty much the same rules apply for multiple brackets)

# GOOD (have all brackets on the same line)
def test_nested_dict():
    s = """a = {{1, 2, 3}, {4, 5, 6}}"""
    assert not _results(s)


# GOOD
def test_nested_dict_with_enters():
    s = """a = {
{1, 2, 3}, {4, 5, 6}
}"""
    assert not _results(s)


# GOOD
def test_nested_dict_with_enters_2():
    s = """a = {
{1, 2, 3},
{4, 5, 6}
}"""
    assert not _results(s)


# GOOD
def test_nested_dict_with_enters_3():
    s = """a = {{
1, 2, 3
}}"""
    assert not _results(s)


def test_dict_brackets_on_diff_lines():
    s = """a = {{
    1, 2, 3
}
}"""
    assert _results(s)


def test_tuple_in_one_line():
    s = """a = (1, 2, 3)"""
    assert not _results(s)


# GOOD
# (when the opening bracket is the last thing on a line, the matching closing
# bracket is the first thing on a new line that matches the indentation of the
# line with the opening bracket)
def test_tuple_with_enters_line():
    s = """a = (
1, 2, 3
)"""
    assert not _results(s)


# BAD (opening bracket is last, but closing is not on new line)
def test_tuple_with_only_one_enter_line():
    s = """a = (
1, 2, 3)"""
    assert _results(s)


# BAD
# (opening bracket is last, closing is on new line but indentation mismatch)
def test_tuple_mismatch_line():
    s = """a = (
1, 2, 3
    )"""
    assert _results(s)


# GOOD (opening bracket is not last, so we don't care about the closing one)
def test_tuple_open_bracket_not_last():
    s = """a = (1, 2, 3
)"""
    assert not _results(s)


# GOOD (opening bracket is not last, so we don't care about the closing one)
def test_tuple_open_bracket_not_last_2():
    s = """a = (1, 2, 3
    )"""
    assert not _results(s)


# (pretty much the same rules apply for multiple brackets)

# GOOD (have all brackets on the same line)
def test_nested_tuple():
    s = """a = ((1, 2, 3), (4, 5, 6))"""
    assert not _results(s)


# GOOD
def test_nested_tuple_with_enters():
    s = """a = (
(1, 2, 3), (4, 5, 6)
)"""
    assert not _results(s)


# GOOD
def test_nested_tuple_with_enters_2():
    s = """a = (
(1, 2, 3),
(4, 5, 6)
)"""
    assert not _results(s)


# GOOD
def test_nested_tuple_with_enters_3():
    s = """a = ((
1, 2, 3
))"""
    assert not _results(s)


def test_parentheses_in_while_on_new_line():
    s = """while (
a == b
): c + d
    """
    assert not _results(s)


# BAD (use parentheses in both case of line continuation)
def test_parentheses_in_while_only_with_second_new_line():
    s = """while ( a == b
): c + d
    """
    assert not _results(s)


# BAD (use parentheses in both case of line continuation)
def test_parentheses_in_while_only_with_first_new_line():
    s = """while (
a == b): c + d
    """
    assert _results(s)


def test_import():
    s = """from c import (a, b)"""
    assert not _results(s)


def test_import_in_three_lines():
    s = """from c import (
    a, b
)"""
    assert not _results(s)


def test_ok_import_in_two_lines():
    s = """from c import (a, b
)"""
    assert not _results(s)


def test_bad_import_in_two_lines():
    s = """from c import (
    a, b)"""
    assert _results(s)


def test_simple_with():
    s = """with foo as bar:"""
    assert not _results(s)


def test_with_two_args():
    s = """with (foo as bar, baz as foobar):"""
    assert not _results(s)
