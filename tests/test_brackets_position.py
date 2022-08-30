import io
import tokenize
from typing import Set

import pytest

from flake8_picky_parentheses import PluginBracketsPosition


@pytest.fixture(params=[True, False])
def plugin(request):
    use_run = request.param

    def run(s: str) -> Set[str]:
        def read_lines():
            return s.splitlines(keepends=True)

        file_tokens = tokenize.tokenize(io.BytesIO(s.encode("utf-8")).readline)
        plugin = PluginBracketsPosition(None, read_lines, file_tokens)
        if use_run:
            problems = plugin.run()
        else:
            plugin.check_brackets_position()
            problems = [
                (line, col, msg, type(plugin))
                for line, col, msg in plugin.problems
            ]
        return {f"{line}:{col + 1} {msg}" for line, col, msg, _ in problems}

    return run


# GOOD (use parentheses for line continuation)
def test_parentheses_in_if_on_new_line(plugin):
    s = """if (
a == b
):
    c + d
    """
    assert not plugin(s)


# BAD (use parentheses in both case of line continuation)
def test_parentheses_in_if_only_with_second_new_line(plugin):
    s = """if ( a == b
):
    c + d
    """
    assert not plugin(s)


# BAD (use parentheses in both case of line continuation)
def test_parentheses_in_if_only_with_first_new_line(plugin):
    s = """if (
a == b):
    c + d
    """
    assert plugin(s)


# BAD (don't put the if body on the same line, m'kay?)
def test_if_body_on_new_line_after_multi_line_condition(plugin):
    s = """if (
a == b
): c + d
    """
    assert plugin(s)


# BAD (use parentheses in both case of line continuation)
def test_parentheses_in_if_with_trailing_tab_only_with_first_new_line(plugin):
    s = """if (\t\t
a == b):
    c + d
    """
    assert plugin(s)


# BAD (use parentheses in both case of line continuation)
def test_parentheses_if_with_trailing_space_only_with_first_new_line(plugin):
    s = """if (  
a == b):
    c + d
    """
    assert plugin(s)


# GOOD (have all brackets on the same line)
def test_list_in_one_line(plugin):
    s = """a = [1, 2, 3]"""
    assert not plugin(s)


# GOOD
# (when the opening bracket is the last thing on a line, the matching closing
# bracket is the first thing on a new line that matches the indentation of the
# line with the opening bracket)
def test_list_with_enters_line(plugin):
    s = """a = [
1, 2, 3
]"""
    assert not plugin(s)


# BAD (opening bracket is last, but closing is not on new line)
def test_list_with_only_one_enter_line(plugin):
    s = """a = [
1, 2, 3]"""
    assert plugin(s)


# BAD
# (opening bracket is last, closing is on new line but indentation mismatch)
def test_list_mismatch_line(plugin):
    s = """a = [
1, 2, 3
    ]"""
    assert plugin(s)


# GOOD (opening bracket is not last, so we don't care about the closing one)
def test_list_open_bracket_not_last(plugin):
    s = """a = [1, 2, 3
]"""
    assert not plugin(s)


# GOOD (opening bracket is not last, so we don't care about the closing one)
def test_list_open_bracket_not_last_2(plugin):
    s = """a = [1, 2, 3
    ]"""
    assert not plugin(s)


# (pretty much the same rules apply for multiple brackets)

# GOOD (have all brackets on the same line)
def test_nested_list(plugin):
    s = """a = [[1, 2, 3], [4, 5, 6]]"""
    assert not plugin(s)


# GOOD
def test_nested_list_with_enters(plugin):
    s = """a = [
[1, 2, 3], [4, 5, 6]
]"""
    assert not plugin(s)


# GOOD
def test_nested_list_with_enters_2(plugin):
    s = """a = [
[1, 2, 3],
[4, 5, 6]
]"""
    assert not plugin(s)


# GOOD
def test_nested_list_with_enters_3(plugin):
    s = """a = [[
1, 2, 3
]]"""
    assert not plugin(s)


# GOOD
def test_nested_list_with_enters_4(plugin):
    s = """a = [
    [
        1, 2, 3
    ],
    [
        4, 5, 6
    ]
]"""
    assert not plugin(s)


# GOOD
def test_nested_list_addition_1(plugin):
    s = """a = [
    [1]
    + [
        2
    ]
]"""
    assert not plugin(s)


# BAD
def test_nested_list_addition_2(plugin):
    s = """a = [
    [1]
    + [
        2
     ]
]"""
    assert plugin(s)


# BAD
# (opening bracket is last, closing is on new line but indentation mismatch)
def test_nested_list_mismatch(plugin):
    s = """a = [
    [
        1, 2, 3
    ],
    [
        4, 5, 6
    ]
  ]"""
    assert plugin(s)


# BAD
# (opening bracket is last, closing is on new line but indentation mismatch)
def test_nested_list_mismatch_2(plugin):
    s = """a = [
    [
        1, 2, 3
      ],
    [
        4, 5, 6
    ]
]"""
    assert plugin(s)


# BAD
# (opening bracket is last, closing is on new line but indentation mismatch)
def test_nested_list_mismatch_3(plugin):
    s = """a = [
    [
        1, 2, 3
    ],
    [
        4, 5, 6
     ]
]"""
    assert plugin(s)


# BAD
# (consecutive opening brackets at the end of the line must have consecutive
#  closing brackets)
def test_nested_list_mismatch_4(plugin):
    s = """a = [[
    1, 2, 3
], [
    4, 5, 6
]]"""
    assert plugin(s)


# BAD (only OPs and comments  after a closing bracket on a new line)
def test_nested_list_mismatch_5(plugin):
    s = """a = [[
    1, 2, 3
], [4, 5, 6]]"""
    messages = plugin(s)
    assert len(messages) == 2
    messages = sorted(list(messages))
    assert messages[0].startswith("1:6")
    assert messages[1].startswith("3:1")


# BAD (the first closing bracket's indentation is a missmatch)
def test_combine_two_faults(plugin):
    s = """a = [[
    1, 2, 3
    ], [
    4, 5, 6
]]"""
    assert plugin(s)


# BAD
# (all opening brackets that are consecutive on the same line are on the same
# line should also have all closing brackets on the same line)
def test_brackets_on_diff_lines_1(plugin):
    s = """a = [[
    1, 2, 3
]
]"""
    assert plugin(s)


# BAD
# (all opening brackets that are consecutive on the same line are on the same
# line should also have all closing brackets on the same line)
def test_brackets_on_diff_lines_2(plugin):
    s = """a = {[[
    1, 2, 3
]
]}"""
    assert plugin(s)


# BAD
# (all opening brackets that are consecutive on the same line are on the same
# line should also have all closing brackets on the same line)
def test_brackets_on_diff_lines_3(plugin):
    s = """a = {[[
    1, 2, 3
]]
}"""
    assert plugin(s)


# GOOD
# (starting on the same line should end on the same line)
def test_brackets_on_same_lines(plugin):
    s = """a = [1, [
    2, 3
]]
"""
    assert not plugin(s)


# GOOD
# (plugin only checks brackets that end lines)
def test_brackets_on_different_lines_1(plugin):
    s = """a = [1, [
    2, 3
]
]
"""
    assert not plugin(s)


# GOOD
# (plugin only checks brackets that end lines)
def test_brackets_on_different_lines_2(plugin):
    s = """a = [1, [
    2, 3
]]
"""
    assert not plugin(s)


def test_dict_in_one_line(plugin):
    s = """a = {1, 2, 3}"""
    assert not plugin(s)


# GOOD
# (when the opening bracket is the last thing on a line, the matching closing
# bracket is the first thing on a new line that matches the indentation of the
# line with the opening bracket)
def test_dict_with_enters_line(plugin):
    s = """a = {
1, 2, 3
}"""
    assert not plugin(s)


# BAD (opening bracket is last, but closing is not on new line)
def test_dict_with_only_one_enter_line(plugin):
    s = """a = {
1, 2, 3}"""
    assert plugin(s)


# BAD
# (opening bracket is last, closing is on new line but indentation mismatch)
def test_dict_mismatch_line(plugin):
    s = """a = {
1, 2, 3
    }"""
    assert plugin(s)


# GOOD (opening bracket is not last, so we don't care about the closing one)
def test_dict_open_bracket_not_last(plugin):
    s = """a = {1, 2, 3
}"""
    assert not plugin(s)


# GOOD (opening bracket is not last, so we don't care about the closing one)
def test_dict_open_bracket_not_last_2(plugin):
    s = """a = {1, 2, 3
    }"""
    assert not plugin(s)


# (pretty much the same rules apply for multiple brackets)

# GOOD (have all brackets on the same line)
def test_nested_dict(plugin):
    s = """a = {{1, 2, 3}, {4, 5, 6}}"""
    assert not plugin(s)


# GOOD
def test_nested_dict_with_enters(plugin):
    s = """a = {
{1, 2, 3}, {4, 5, 6}
}"""
    assert not plugin(s)


# GOOD
def test_nested_dict_with_enters_2(plugin):
    s = """a = {
{1, 2, 3},
{4, 5, 6}
}"""
    assert not plugin(s)


# GOOD
def test_nested_dict_with_enters_3(plugin):
    s = """a = {{
1, 2, 3
}}"""
    assert not plugin(s)


def test_dict_brackets_on_diff_lines(plugin):
    s = """a = {{
    1, 2, 3
}
}"""
    assert plugin(s)


def test_tuple_in_one_line(plugin):
    s = """a = (1, 2, 3)"""
    assert not plugin(s)


# GOOD
# (when the opening bracket is the last thing on a line, the matching closing
# bracket is the first thing on a new line that matches the indentation of the
# line with the opening bracket)
def test_tuple_with_enters_line(plugin):
    s = """a = (
1, 2, 3
)"""
    assert not plugin(s)


# BAD (opening bracket is last, but closing is not on new line)
def test_tuple_with_only_one_enter_line(plugin):
    s = """a = (
1, 2, 3)"""
    assert plugin(s)


# BAD
# (opening bracket is last, closing is on new line but indentation mismatch)
def test_tuple_mismatch_line(plugin):
    s = """a = (
1, 2, 3
    )"""
    assert plugin(s)


# GOOD (opening bracket is not last, so we don't care about the closing one)
def test_tuple_open_bracket_not_last(plugin):
    s = """a = (1, 2, 3
)"""
    assert not plugin(s)


# GOOD (opening bracket is not last, so we don't care about the closing one)
def test_tuple_open_bracket_not_last_2(plugin):
    s = """a = (1, 2, 3
    )"""
    assert not plugin(s)


# (pretty much the same rules apply for multiple brackets)

# GOOD (have all brackets on the same line)
def test_nested_tuple(plugin):
    s = """a = ((1, 2, 3), (4, 5, 6))"""
    assert not plugin(s)


# GOOD
def test_nested_tuple_with_enters(plugin):
    s = """a = (
(1, 2, 3), (4, 5, 6)
)"""
    assert not plugin(s)


# GOOD
def test_nested_tuple_with_enters_2(plugin):
    s = """a = (
(1, 2, 3),
(4, 5, 6)
)"""
    assert not plugin(s)


# GOOD
def test_nested_tuple_with_enters_3(plugin):
    s = """a = ((
1, 2, 3
))"""
    assert not plugin(s)


def test_parentheses_in_while_on_new_line(plugin):
    s = """while (
a == b
):
    c + d
    """
    assert not plugin(s)


# BAD (use parentheses in both case of line continuation)
def test_parentheses_in_while_only_with_second_new_line(plugin):
    s = """while ( a == b
):
    c + d
    """
    assert not plugin(s)


# BAD (use parentheses in both case of line continuation)
def test_parentheses_in_while_only_with_first_new_line(plugin):
    s = """while (
a == b):
    c + d
    """
    assert plugin(s)


def test_import(plugin):
    s = """from c import (a, b)"""
    assert not plugin(s)


def test_import_in_three_lines(plugin):
    s = """from c import (
    a, b
)"""
    assert not plugin(s)


def test_ok_import_in_two_lines(plugin):
    s = """from c import (a, b
)"""
    assert not plugin(s)


def test_bad_import_in_two_lines(plugin):
    s = """from c import (
    a, b)"""
    assert plugin(s)


def test_simple_with(plugin):
    s = """with foo as bar:
    pass
"""
    assert not plugin(s)


def test_simple_with_multi_line_1(plugin):
    s = """with foo(
    a, b, c
) as bar:
    pass
"""
    assert not plugin(s)


def test_simple_with_multi_line_2(plugin):
    s = """with foobar({
    k1: v1,
    k2: v2
}) as baz:
    pass
"""
    assert not plugin(s)


def test_with_two_args(plugin):
    s = """with (foo as bar, baz as foobar):"""
    assert not plugin(s)


# GOOD
def test_with_two_args_multi_line(plugin):
    s = """with (
    foo as bar,
    baz as foobar
):"""
    assert not plugin(s)


# BAD
def test_with_two_args_multi_line_misaligned_close_1(plugin):
    s = """with (
    foo as bar,
    baz as foobar
    ):"""
    assert plugin(s)


# BAD
def test_with_two_args_multi_line_misaligned_close_2(plugin):
    s = """with (
    foo as bar,
    baz as foobar):"""
    assert plugin(s)


# GOOD
def test_function_args_line_break(plugin):
    s = """zip(parens_cords_sorted[:-1],
   parens_cords_sorted[1:])
"""
    assert not plugin(s)


# if there is a closing bracket on after a new line, this line should only
# contain: operators and comments

# GOOD (only other operators on the line after closing parenthesis)
def test_nested_new_lines_1(plugin):
    s = """@pytest.mark.parametrize(
    ("test_config", "expected_failure", "expected_failure_message"),
    (
        (
            {"trust": 1}, ConfigurationError, "The config setting `trust`"
        ), (  # hello world!
            {"trust": True}, ConfigurationError, "The config setting `trust`"
        ), (
            {"trust": None}, ConfigurationError, "The config setting `trust`"
        ),
    )
)
"""
    assert not plugin(s)


# GOOD (only other operators on the line after closing parenthesis)
def test_nested_new_lines_2(plugin):
    s = """@pytest.mark.parametrize(
    ("test_config", "expected_failure", "expected_failure_message"),
    (
        (
            {"trust": 1}, ConfigurationError, "The config setting `trust`"
        ), 
        (
            {"trust": True}, ConfigurationError, "The config setting `trust`"
        ), 
        (
            {"trust": None}, ConfigurationError, "The config setting `trust`"
        ),
    )
)
"""
    assert not plugin(s)


# GOOD (only other operators on the line after closing parenthesis)
def test_nested_new_lines_3(plugin):
    s = """@pytest.mark.parametrize(
    ("test_config", "expected_failure", "expected_failure_message"),
    (
        (
            {"trust": 1}, ConfigurationError, "The config setting `trust`"
        ) + (
            {"trust": True}, ConfigurationError, "The config setting `trust`"
        ), 
        (
            {"trust": None}, ConfigurationError, "The config setting `trust`"
        ),
    )
)
"""
    assert not plugin(s)


# BAD (another tuple on the line after closing parenthesis)
def test_nested_new_lines_4(plugin):
    s = """@pytest.mark.parametrize(
    ("test_config", "expected_failure", "expected_failure_message"),
    (
        (
            {"trust": 1}, ConfigurationError, "The config setting `trust`"
        ), ({"trust": True}, ConfigurationError, "The config setting `trust`"),
        (
            {"trust": None}, ConfigurationError, "The config setting `trust`"
        ),
    )
)
"""
    messages = plugin(s)
    assert len(messages) == 1
    assert list(messages)[0].startswith("6:9")


# GOOD
def test_indentation_after_multi_line_string(plugin):
    s = '''script = """
!: BOLT 4.3
{}{}
S: SUCCESS
""".format(
    "!: ALLOW RESTART\n" if restarting else "",
    "!: ALLOW CONCURRENT\n" if concurrent else "",
)
'''
    assert not plugin(s)


# GOOD
def test_indentation_after_multi_line_string_in_block(plugin):
    s = '''if foo:
    script = """
    !: BOLT 4.3
    {}{}
    S: SUCCESS
    """.format(
        "!: ALLOW RESTART\n" if restarting else "",
        "!: ALLOW CONCURRENT\n" if concurrent else "",
    )
'''
    assert not plugin(s)


# GOOD
def test_method_chaining(plugin):
    s = """foo.bar(
    baz
).foobar()"""
    assert not plugin(s)
