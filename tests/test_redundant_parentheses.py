import ast
from pathlib import Path
import re
import sys
import tokenize
from typing import Set

import pytest

from flake8_picky_parentheses import PluginRedundantParentheses


@pytest.fixture
def plugin():
    def run(s: str) -> Set[str]:
        lines = s.splitlines(keepends=True)

        line_iter = iter(lines)
        file_tokens = list(tokenize.generate_tokens(lambda: next(line_iter)))
        tree = ast.parse(s)
        plugin_ = PluginRedundantParentheses(tree, file_tokens, lines)
        problems = plugin_.run()
        return {f"{line}:{col + 1} {msg}" for line, col, msg, _ in problems}

    return run


def test_foo(plugin):
    assert plugin("a = (1)\n")


def _ws_generator():
    return "", " ", "\t", "   ", "\t\t", "\t "


def test_multi_line_condition(plugin):
    s = """if (foo
            == bar):
        ...
    """
    assert not plugin(s)


# GOOD (use parentheses for tuple literal)
def test_tuple_literal_1(plugin):
    s = """a = ("a",)
    """
    assert not plugin(s)


# GOOD (use parentheses for tuple literal)
def test_tuple_literal_2(plugin):
    s = """a = ("a", "b")
    """
    assert not plugin(s)


# GOOD (use parentheses for tuple literal)
def test_tuple_literal_3(plugin):
    s = """a = (\\
    "a", "b")
    """
    assert not plugin(s)


def test_tuple_literal_4(plugin):
    s = """((a,))
    """
    res = plugin(s)
    assert len(res) == 1
    assert next(iter(res)).startswith("1:1 ")


# GOOD (parens for tuple literal are optional)
def test_parens_for_tuple_literal(plugin):
    s = """(a,)  # GOOD
    """
    assert not plugin(s)


def test_mixed_with_tuple_literal_5(plugin):
    s = """(1 + 2)  # BAD
(a,)  # GOOD
    """
    res = plugin(s)
    assert len(res) == 1
    assert next(iter(res)).startswith("1:1 ")


def test_mixed_with_tuple_literal_6(plugin):
    s = """(a,)  # GOOD
(1 + 2)  # BAD
    """
    res = plugin(s)
    assert len(res) == 1
    assert next(iter(res)).startswith("2:1 ")


# GOOD (use parentheses for tuple literal)
def test_nested_tuple_literal_1(plugin):
    s = """a = ("a", ("b", "c"))
    """
    assert not plugin(s)


# BAD (redundant parentheses around the whole expression)
def test_nested_tuple_literal_2(plugin):
    s = """(a + (1, 2))"""
    res = plugin(s)
    assert len(res) == 1
    assert next(iter(res)).startswith("1:1 ")


# BAD (one pair of parentheses for tuple literal is enough)
def test_multi_parens_tuple_literal_1(plugin):
    s = """a = (("a", "b"))
    """
    res = plugin(s)
    assert len(res) == 1
    assert next(iter(res)).startswith("1:5 ")


# BAD (one pair of parentheses for tuple literal is enough)
def test_multi_parens_tuple_literal_2(plugin):
    s = """a = ((
        "a", "b"
    ))
    """
    res = plugin(s)
    assert len(res) == 1
    assert next(iter(res)).startswith("1:5 ")


# GOOD (parentheses for tuple literal are optional)
def test_tuple_literal_optional_1(plugin):
    s = """a = "a",
    """
    assert not plugin(s)


# GOOD (parentheses for tuple literal are optional)
def test_tuple_literal_optional_2(plugin):
    s = """a = "a", "b"
    """
    assert not plugin(s)


# GOOD (parentheses for tuple literal are optional)
def test_tuple_literal_optional_3(plugin):
    s = """"a", (1, 2)"""
    assert not plugin(s)


# GOOD (parentheses for tuple literal are optional)
def test_tuple_literal_unpacking(plugin):
    s = """a, b = "a", "b"
c = ((d + e))
    """
    res = plugin(s)
    assert len(res) == 1


# BAD (redundant parentheses for unpacking)
def test_ugly_multiline_unpacking(plugin):
    s = """(
a, b\\
) = 1, 2"""
    assert len(plugin(s)) == 1


# GOOD (unpacking with line break)
def test_multiline_unpacking_implicit_tuple_literal(plugin):
    s = """(
a, b
) = 1, 2"""
    assert not plugin(s)


# GOOD (unpacking with line break)
def test_multiline_unpacking_explicit_tuple_literal(plugin):
    s = """(
a, b
) = (1, 2)"""
    assert not plugin(s)


# GOOD (parentheses for tuple literal are optional)
def test_tuple_literal_unpacking_in_if(plugin):
    s = """if foo:
        a, b = "a", "b"
    """
    assert len(plugin(s)) == 0


# BAD (parentheses for tuple literal are optional)
def test_unpacking_in_if_redundant_parens_around_condition(plugin):
    s = """if (foo):
        a, b = "a", "b"
    """
    assert len(plugin(s)) == 1


# GOOD (parentheses are redundant, but can help readability)
def test_bin_op_example_1(plugin):
    s = """a = (1 + 2) % 3
    """
    assert not plugin(s)


# GOOD (parentheses are necessary)
def test_bin_op_example_2(plugin):
    s = """a = 1 + (2 % 3)
    """
    assert not plugin(s)


# GOOD (parentheses might be redundant, but can help readability)
def test_bin_op_example_3(plugin):
    s = """a = 1 + (2 and 3)
    """
    assert not plugin(s)


# GOOD (parentheses might be redundant, but can help readability)
def test_bin_op_example_4(plugin):
    s = """a = (1 + 2) and 3
    """
    assert not plugin(s)


# GOOD (parentheses might be redundant, but can help readability)
def test_bin_op_example_5(plugin):
    s = """a = 1 and (2 + 3)
    """
    assert not plugin(s)


# GOOD (parentheses might be redundant, but can help readability)
def test_bin_op_example_6(plugin):
    s = """a = (1 and 2) + 3
    """
    assert not plugin(s)


# GOOD (parentheses are redundant, but can help readability)
def test_bin_op_example_7(plugin):
    s = """a = foo or (bar and baz)
    """
    assert not plugin(s)


# GOOD with ugly spaces (parentheses are redundant, but can help readability)
def test_bin_op_example_8(plugin):
    s = """a = (   1 /   2)   /3
    """
    assert not plugin(s)


# BAD (parentheses are redundant and can't help readability)
def test_bin_op_example_unnecessary_parens(plugin):
    s = """a = (foo or bar and baz)
    """
    assert len(plugin(s)) == 1


# GOOD (parentheses are redundant and can help readability)
def test_multi_line_bin_op_example_unnecessary_parens(plugin):
    # OK, please don't judge me for this incredibly ugly code...
    # I need to make a point here.
    s = """a = foo + (\\
bar * baz)
    """
    assert not plugin(s)


@pytest.mark.parametrize("flake", [True, False])
def test_with_comment(plugin, flake):
    s = """
def foo():
    # a nice comment
    ...
    # another nice comment
    %s
"""
    if flake:
        s = s % "a = (1)"
    else:
        s = s % "a = 1"
    assert len(plugin(s)) == flake


def test_only_comment(plugin):
    s = """# ()"""
    assert not plugin(s)


@pytest.mark.parametrize(("string_start", "string_end"), (
    ("'", "'"),
    ('"', '"'),
    ("'''", "'''"),
    ('"""', '"""'),
    ("'''\n", "\n'''"),
    ('"""\n', '\n"""'),
))
@pytest.mark.parametrize("nest", [True, False])
def test_in_string(plugin, string_start, string_end, nest):
    s = f"{string_start}(){string_end}"
    if nest:
        s = f"def foo():\n    {s}"
    assert not plugin(s)


@pytest.mark.parametrize(("string_start", "string_end"), (
    ("'''", "'''"),
    ('"""', '"""'),
))
def test_in_string_nested_properly(plugin, string_start, string_end):
    s = f"""\
def foo():
    {string_start}
    ()
    {string_end}
"""
    assert not plugin(s)


# BAD (don't use parentheses for unpacking)
@pytest.mark.parametrize("ws1", _ws_generator())
@pytest.mark.parametrize("ws2", _ws_generator())
@pytest.mark.parametrize("ws3", _ws_generator())
@pytest.mark.parametrize("ws4", _ws_generator())
def test_unpacking(plugin, ws1, ws2, ws3, ws4):
    s = f"""({ws1}a{ws2},{ws3}){ws4}= ["a"]
    """
    assert len(plugin(s)) == 1


def test_simple_unpacking(plugin):
    s = """(a,) = ["a"]"""
    assert len(plugin(s)) == 1


# BAD (don't use parentheses for unpacking, even with leading white space)
@pytest.mark.parametrize("ws", _ws_generator())
def test_unpacking_with_white_space(plugin, ws):
    s = f"""({ws}a,)=["a"]
    """
    assert len(plugin(s)) == 1


# BAD (don't use parentheses when already using \ for line continuation)
def test_call_chain_escaped_line_break_1(plugin):
    s = """(\\
foo\\
).bar(baz)
    """
    assert len(plugin(s)) == 1


# BAD (don't use parentheses when already using \ for line continuation)
def test_call_chain_escaped_line_break_2(plugin):
    s = """(   \\
    foo   \\
    )  .  bar   (   baz   )
    """
    if sys.version_info >= (3, 10):
        assert not plugin(s)
    else:
        assert len(plugin(s)) == 1


# BAD (redundant parentheses)
def test_parentheses_delimit_names(plugin):
    s = """(a)and(b)
    """
    assert len(plugin(s)) == 2


# BAD (don't use parentheses for one-line expressions)
def test_one_line_condition(plugin):
    s = """if (foo == bar):
        a + b
    """
    assert len(plugin(s)) == 1


# BAD (don't use parentheses for one-line expressions)
def test_one_line_expression_1(plugin):
    s = """a = (foo == bar)
    """
    assert len(plugin(s)) == 1


# BAD (don't use parentheses for one-line expressions)
def test_one_line_expression_2(plugin):
    s = """a = (foo.bar())
    """
    assert len(plugin(s)) == 1


# GOOD (function call)
def test_function_call(plugin):
    s = """foo("a")
    """
    assert not plugin(s)


# BAD (function call with extra parentheses)
def test_function_call_redundant_parens_1(plugin):
    s = """foo(("a"))
    """
    assert len(plugin(s)) == 1


# BAD (function call with extra parentheses around expression)
def test_function_call_redundant_parens_2(plugin):
    s = """foo((1 + 2))
    """
    assert len(plugin(s)) == 1


# BAD
def test_function_call_redundant_parens_3(plugin):
    s = """foo((1 + 2), 3)
    """
    assert len(plugin(s)) == 1


# GOOD
def test_function_call_redundant_parens_for_readability(plugin):
    s = """foo((1 + 2) + 3, 4)
    """
    assert not plugin(s)


@pytest.mark.parametrize(
    "body", ("def bar():\n    pass", "class Bar:\n    pass")
)
def test_decorator(plugin, body):
    s = f"""\
@foo
{body}
"""
    assert not plugin(s)


@pytest.mark.parametrize(
    "body", ("def bar():\n    pass", "class Bar:\n    pass")
)
@pytest.mark.parametrize("flake", [True, False])
def test_decorator_call(plugin, body, flake):
    arg = "(1)" if flake else ""
    s = f"""\
@foo({arg})
{body}
"""
    assert len(plugin(s)) == flake


# BAD
def test_function_call_unnecessary_multi_line_parens(plugin):
    s = """foo(
    (1 + 2) + 3,
    (4
       + 5)
)
"""
    res = plugin(s)
    assert len(res) == 1
    assert next(iter(res)).startswith("3:5 ")


# GOOD (function call with tuple literal)
def test_function_call_with_tuple(plugin):
    s = """foo(("a",))
    """
    assert not plugin(s)


# GOOD (method call)
def test_method_call(plugin):
    s = """foo.bar("a")
    """
    assert not plugin(s)


# GOOD (use parentheses for line continuation)
def test_multi_line_parens_1(plugin):
    s = """a = ("abc"
         "def")
    """
    assert not plugin(s)


# GOOD (use parentheses for line continuation)
def test_multi_line_parens_2(plugin):
    s = """a = (
        "abc"
        "def"
)
"""
    assert not plugin(s)


# BAD (parentheses are redundant and can't help readability)
def test_unnecessary_parens(plugin):
    s = """a = ("a")
    """
    assert len(plugin(s)) == 1


# BAD (one pair of parenthesis is enough)
def test_bin_op_example_double_parens_1(plugin):
    s = """a = 1 * ((2 + 3))
    """
    res = plugin(s)
    assert len(res) == 1
    msg = next(iter(res))
    assert msg.startswith("1:9 ") or msg.startswith("1:10 ")


# BAD (one pair of parenthesis is enough)
def test_bin_op_example_double_parens_2(plugin):
    s = """a = ((1 * 2)) + 3
    """
    assert len(plugin(s)) == 1


# BAD (one pair of parenthesis is enough)
def test_bin_op_example_double_parens_3(plugin):
    s = """a = 1 + ((2 * 3))
    """
    assert len(plugin(s)) == 1


# BAD (one pair of parenthesis is enough)
def test_bin_op_example_double_parens_4(plugin):
    s = """a = ((1 + 2)) * 3
    """
    assert len(plugin(s)) == 1


# BAD (redundant parenthesis around 1)
def test_redundant_parens_around_tuple(plugin):
    s = """a = ((1),)
    """
    assert len(plugin(s)) == 1


# GOOD (generator comprehension)
def test_generator_comprehension(plugin):
    s = """a = (foo for foo in bar)
    """
    assert not plugin(s)


# BAD
def test_unary_op_example_1(plugin):
    s = """a = not (b)
    """
    assert len(plugin(s)) == 1


# BAD
def test_unary_op_example_2(plugin):
    s = """a = (not b)
    """
    assert len(plugin(s)) == 1


# GOOD (parentheses might be redundant, but can help readability)
def test_mixed_op_example_1(plugin):
    s = """a = not (1 + 2)
    """
    assert not plugin(s)


# GOOD (parentheses might be redundant, but can help readability)
def test_mixed_op_example_2(plugin):
    s = """a = (not 1) + 2
    """
    assert not plugin(s)


# GOOD (parentheses might be redundant, but can help readability)
def test_mixed_op_example_3(plugin):
    s = """a = not 1 + 2
    """
    assert not plugin(s)


# BAD (two redundant parentheses)
def test_wildly_nested_parens(plugin):
    s = """a = 1 + (2 + (3) + (4))
    """
    res = plugin(s)
    assert len(res) == 2
    positions = set(msg.split(" ")[0] for msg in res)
    assert positions == {"1:14", "1:20"}


def test_mixture_of_good_and_bad(plugin):
    s = """a = (1 + 2) * 3  # GOOD
b = 1 + (2) + 3  # BAD
c = 1 + (2 + 3)  # GOOD
d = (1) + (2) + 3  # BAD
    """
    res = plugin(s)
    assert len(res) == 3
    positions = set(msg.split(" ")[0] for msg in res)
    assert positions == {"2:9", "4:5", "4:11"}


@pytest.mark.parametrize(("expr", "problems"), (
    ("a = 1 + 2 if foo else 3", 0),
    ("a = (1 + 2) if foo else 3", 0),
    ("a = 1 + (2 if foo else 3)", 0),
    ("a = (2 if foo else 3)", 1),
))
def test_if_expr(plugin, expr, problems):
    assert len(plugin(expr)) == problems


BIN_OPS = (
    "**", "*", "@", "/", "//", "%", "+", "-", "<<", ">>", "&", "^", "|", "in",
    "not in", "is", "is not", "<", "<=", ">", ">=", "!=", "==", "and", "or",
    "if baz else"  # not strictly a bin op, but expected to be handled equally
)
UNARY_OPS = ("not", "+", "-", "~", "await")


def _id(s):
    return s


def _make_multi_line(s):
    assert s.startswith("foo = ")
    return f"foo = (\n    {s[6:]}\n)"


def _make_multi_line_extra_parens_1(s):
    assert s.startswith("foo = ")
    return f"foo = ((\n    {s[6:]}\n))"


def _make_multi_line_extra_parens_2(s):
    assert s.startswith("foo = ")
    return f"foo = (\n    ({s[6:]})\n)"


def _make_multi_line_extra_parens_3(s):
    assert s.startswith("foo = ")
    return f"foo = (\n(\n{s[6:]}\n)\n)"


MULTI_LINE_ALTERATION = (
    # (function, makes it bad)
    (_id, 0),
    (_make_multi_line, 0),
    (_make_multi_line_extra_parens_1, 1),
    (_make_multi_line_extra_parens_2, 1),
    (_make_multi_line_extra_parens_3, 1),
)


@pytest.mark.parametrize("op", UNARY_OPS)
@pytest.mark.parametrize("alteration", MULTI_LINE_ALTERATION)
def test_superfluous_parentheses_after_unary_op(plugin, op, alteration):
    alteration_func, introduced_flakes = alteration
    s = f"foo = {op} (bar) \n"
    s = alteration_func(s)
    assert len(plugin(s)) == 1 + introduced_flakes


def test_double_line_continuation(plugin):
    s = """(
(
1
)
)
"""
    assert len(plugin(s)) == 1


@pytest.mark.parametrize("op", UNARY_OPS)
@pytest.mark.parametrize("op2", BIN_OPS + UNARY_OPS)
@pytest.mark.parametrize("alteration", MULTI_LINE_ALTERATION)
def test_superfluous_but_helping_parentheses_after_mono_op(
    plugin, op, op2, alteration
):
    alteration_func, introduced_flakes = alteration
    if op2 in UNARY_OPS:
        expression = f"{op2} bar"
    else:
        expression = f"foo {op2} bar"
    s = f"foo = {op} ({expression})"
    s = alteration_func(s)
    assert len(plugin(s)) == introduced_flakes


@pytest.mark.parametrize("op", BIN_OPS)
@pytest.mark.parametrize("alteration", MULTI_LINE_ALTERATION)
def test_superfluous_parentheses_around_bin_op(plugin, op, alteration):
    alteration_func, introduced_flakes = alteration
    s = f"foo = {{a: (foo {op} bar)}} \n"
    s = alteration_func(s)
    assert len(plugin(s)) == 1 + introduced_flakes


@pytest.mark.parametrize("op1", BIN_OPS)
@pytest.mark.parametrize("op2", BIN_OPS)
@pytest.mark.parametrize("parens_first", (True, False))
@pytest.mark.parametrize("alteration", MULTI_LINE_ALTERATION)
def test_superfluous_but_helping_parentheses_around_bin_op(
    plugin, op1, op2, parens_first, alteration
):
    alteration_func, introduced_flakes = alteration
    parent_expr = f"(foo {op1} bar)"
    if parens_first:
        s = f"foo = {parent_expr} {op2} baz"
    else:
        s = f"foo = baz {op2} {parent_expr}"
    s = alteration_func(s)
    assert len(plugin(s)) == introduced_flakes


@pytest.mark.parametrize("op1", BIN_OPS)
@pytest.mark.parametrize("op2", BIN_OPS)
@pytest.mark.parametrize("parens_first", (True, False))
@pytest.mark.parametrize("alteration", MULTI_LINE_ALTERATION)
def test_double_superfluous_but_helping_parentheses_around_bin_op(
    plugin, op1, op2, parens_first, alteration
):
    alteration_func, introduced_flakes = alteration
    parent_expr = f"((foo {op1} bar))"
    if parens_first:
        s = f"foo = {parent_expr} {op2} baz \n"
    else:
        s = f"foo = baz {op2} {parent_expr} \n"
    s = alteration_func(s)
    assert len(plugin(s)) == 1 + introduced_flakes


def _slice_in_tuple(s, tuple_, unpack):
    start = end = ""
    if tuple_ == "implicit":
        start = "a, "
    elif tuple_ == "explicit":
        start, end = "(a, ", ")"
    start += "*" if unpack else ""
    return s.format(start, end)


# GOOD (redundant in slice, but help readability)
@pytest.mark.parametrize(("tuple_", "unpack"), (
    ("no", False),
    ("implicit", False),
    ("implicit", True),
    ("explicit", False),
    ("explicit", True),
))
def test_parens_in_slice_1(plugin, tuple_, unpack):
    s = """{}foo[i:(i + 1)]{}
"""
    s = _slice_in_tuple(s, tuple_, unpack)
    assert not plugin(s)


# GOOD (redundant in slice, but help readability)
@pytest.mark.parametrize(("tuple_", "unpack"), (
    ("no", False),
    ("implicit", False),
    ("implicit", True),
    ("explicit", False),
    ("explicit", True),
))
def test_parens_in_slice_2(plugin, tuple_, unpack):
    s = """{}foo[(-1):i]{}
"""
    s = _slice_in_tuple(s, tuple_, unpack)
    assert not plugin(s)


# GOOD (redundant in slice, but help readability)
@pytest.mark.parametrize(("tuple_", "unpack"), (
    ("no", False),
    ("implicit", False),
    ("implicit", True),
    ("explicit", False),
    ("explicit", True),
))
def test_parens_in_slice_2_no_end(plugin, tuple_, unpack):
    s = """{}foo[(-1):]{}
"""
    s = _slice_in_tuple(s, tuple_, unpack)
    assert not plugin(s)


# GOOD (redundant in slice but help readability)
@pytest.mark.parametrize(("tuple_", "unpack"), (
    ("no", False),
    ("implicit", False),
    ("implicit", True),
    ("explicit", False),
    ("explicit", True),
))
def test_parens_in_slice_3(plugin, tuple_, unpack):
    s = """{}foo[i:(-1)]{}
"""
    s = _slice_in_tuple(s, tuple_, unpack)
    assert not plugin(s)


# GOOD (redundant in slice but help readability)
@pytest.mark.parametrize(("tuple_", "unpack"), (
    ("no", False),
    ("implicit", False),
    ("implicit", True),
    ("explicit", False),
    ("explicit", True),
))
def test_parens_in_slice_3_no_start(plugin, tuple_, unpack):
    s = """{}foo[:(-1)]{}
"""
    s = _slice_in_tuple(s, tuple_, unpack)
    assert not plugin(s)


# GOOD ()
@pytest.mark.parametrize(("tuple_", "unpack"), (
    ("no", False),
    ("implicit", False),
    ("implicit", True),
    ("explicit", False),
    ("explicit", True),
))
def test_parens_in_slice_4(plugin, tuple_, unpack):
    s = """{}foo[i:-1]{}
"""
    s = _slice_in_tuple(s, tuple_, unpack)
    assert not plugin(s)


# BAD (redundant in slice and don't help readability)
@pytest.mark.parametrize(("tuple_", "unpack"), (
    ("no", False),
    ("implicit", False),
    ("implicit", True),
    ("explicit", False),
    ("explicit", True),
))
def test_parens_in_slice_5(plugin, tuple_, unpack):
    s = """{}foo[(0):i]{}
"""
    s = _slice_in_tuple(s, tuple_, unpack)
    assert len(plugin(s)) == 1


# GOOD (redundant in slice, but help readability)
@pytest.mark.parametrize(("tuple_", "unpack"), (
    ("no", False),
    ("implicit", False),
    ("implicit", True),
    ("explicit", False),
    ("explicit", True),
))
def test_parens_in_slice_6(plugin, tuple_, unpack):
    s = """{}foo[i: (i + 1) ]{}
"""
    s = _slice_in_tuple(s, tuple_, unpack)
    assert not plugin(s)


# GOOD (redundant in slice, but help readability)
@pytest.mark.parametrize(("tuple_", "unpack"), (
    ("no", False),
    ("implicit", False),
    ("implicit", True),
    ("explicit", False),
    ("explicit", True),
))
def test_parens_in_slice_7(plugin, tuple_, unpack):
    s = """{}foo[i:( i + 1 )]{}
"""
    s = _slice_in_tuple(s, tuple_, unpack)
    assert not plugin(s)


# BAD (on pair would've been enough)
@pytest.mark.parametrize(("tuple_", "unpack"), (
    ("no", False),
    ("implicit", False),
    ("implicit", True),
    ("explicit", False),
    ("explicit", True),
))
def test_parens_in_slice_8(plugin, tuple_, unpack):
    s = """{}foo[((i - 1)):i]{}
"""
    s = _slice_in_tuple(s, tuple_, unpack)
    assert plugin(s)


# GOOD (redundant in slice but help readability)
@pytest.mark.parametrize(("tuple_", "unpack"), (
    ("no", False),
    ("implicit", False),
    ("implicit", True),
    ("explicit", False),
    ("explicit", True),
))
def test_parens_in_slice_9(plugin, tuple_, unpack):
    s = """{}foo[:i:(-1)]{}
"""
    s = _slice_in_tuple(s, tuple_, unpack)
    assert not plugin(s)


# GOOD (redundant in slice but help readability)
@pytest.mark.parametrize(("tuple_", "unpack"), (
    ("no", False),
    ("implicit", False),
    ("implicit", True),
    ("explicit", False),
    ("explicit", True),
))
def test_parens_in_indented_slice(plugin, tuple_, unpack):
    s = """\
def foo():
    a = {}a[s:(e + 1)]{}
"""
    s = _slice_in_tuple(s, tuple_, unpack)
    assert not plugin(s)


def test_(plugin):
    s = "a, b[(-1):]"
    assert not plugin(s)


# GOOD (redundant in comprehension, but help readability of multi-line if)
@pytest.mark.parametrize("comprehension_type", (
    "()", "[]", "{}",
))
def test_multi_line_if_with_parens_in_comprehension(plugin,
                                                    comprehension_type):
    s = f"""{comprehension_type[0]}
    x
    for x in range(10)""" + " " + f"""
    if (some_super_mega_looooooooooooooooooooooooooooooooooooong_thing
        or some_other_super_mega_looooooooooooooooooooooong_thing)
{comprehension_type[1]}
"""
    assert not plugin(s)


# BAD (redundant in comprehension and don't help readability of single-line if)
@pytest.mark.parametrize("comprehension_type", (
    "()", "[]", "{}",
))
@pytest.mark.parametrize("expr", ("foo", "foobar or baz"))
def test_single_line_if_with_parens_in_comprehension(
    plugin, comprehension_type, expr
):
    s = f"""{comprehension_type[0]}
    x
    for x in range(10)""" + " " + f"""
    if ({expr})
{comprehension_type[1]}
"""
    assert len(plugin(s)) == 1


# BAD (redundant in comprehension and don't help readability of single-line if)
@pytest.mark.parametrize("comprehension_type", (
    "()", "[]", "{}",
))
@pytest.mark.parametrize("expr", ("foo", "foobar or baz"))
def test_practically_single_line_if_with_parens_in_comprehension(
    plugin, comprehension_type, expr
):
    s = f"""{comprehension_type[0]}
    x
    for x in range(10)""" + " " + f"""
    if ({expr}
    )
{comprehension_type[1]}
"""
    assert len(plugin(s)) == 1


# GOOD (redundant in comprehension, but help readability of multi-line if)
@pytest.mark.parametrize("comprehension_type", (
    "()", "[]", "{}",
))
@pytest.mark.parametrize("expr", ("foo", "foobar or baz"))
def test_continuation_if_with_parens_in_comprehension(
    plugin, comprehension_type, expr
):
    s = f"""{comprehension_type[0]}
    x
    for x in range(10)""" + " " + f"""
    if (
        {expr}
    )
{comprehension_type[1]}
"""
    assert not plugin(s)


# GOOD (redundant in comprehension, but help readability of multi-line in)
@pytest.mark.parametrize("comprehension_type", (
    "()", "[]", "{}",
))
def test_multi_line_in_with_parens_in_comprehension(plugin,
                                                    comprehension_type):
    s = f"""{comprehension_type[0]}
    x
    for x in (set(a)
              - set(b))
{comprehension_type[1]}
"""
    assert not plugin(s)


# BAD (redundant in comprehension and don't help readability of single-line in)
@pytest.mark.parametrize("comprehension_type", (
    "()", "[]", "{}",
))
@pytest.mark.parametrize("expr", ("a", "set(a) - set(b)"))
def test_single_line_in_with_parens_in_comprehension(
    plugin, comprehension_type, expr
):
    s = f"""{comprehension_type[0]}
    x
    for x in ({expr})
{comprehension_type[1]}
"""
    assert len(plugin(s)) == 1


# BAD (redundant in comprehension and don't help readability of single-line in)
@pytest.mark.parametrize("comprehension_type", (
    "()", "[]", "{}",
))
@pytest.mark.parametrize("expr", ("a", "set(a) - set(b)"))
def test_practically_single_line_in_with_parens_in_comprehension(
    plugin, comprehension_type, expr
):
    s = f"""{comprehension_type[0]}
    x
    for x in ({expr}
    )
{comprehension_type[1]}
"""
    assert len(plugin(s)) == 1


# GOOD
@pytest.mark.parametrize("comprehension_type", (
    "()", "[]", "{}",
))
@pytest.mark.parametrize("expr", ("a", "set(a) - set(b)"))
def test_continuation_in_with_parens_in_comprehension(
    plugin, comprehension_type, expr
):
    s = f"""{comprehension_type[0]}
    x
    for x in (
        {expr}
    )
{comprehension_type[1]}
"""
    assert not plugin(s)


def test_empty(plugin):
    s = """


"""
    assert not plugin(s)


@pytest.mark.parametrize("beginning_ws", (True, False))
def test_two_functions(plugin, beginning_ws):
    s = """def foo():
    pass
""" + "    " + """
def bar():
    pass
"""
    if beginning_ws:
        s = "\n" + s
    assert not plugin(s)


# GOOD
def test_function_call_with_empty_line_in_method(plugin):
    s = """class Foo:
    def __init__(self):
        ...

    def build_driver_and_backend(self):
        foo(
            bar

        )
"""
    assert not plugin(s)


EXCEPT_STATEMENTS = (
    "except:",
    "except Foo:",
    "except Foo as e:",
    "except (Foo,):",
    "except (Foo,) as e:",
    "except (Foo, Bar):",
    "except (Foo, Bar) as e:",
    *(
        () if sys.version_info < (3, 11) else (
            # "except*:",  # invalid syntax
            "except* Foo:",
            "except* Foo as e:",
            "except* (Foo,):",
            "except* (Foo,) as e:",
            "except* (Foo, Bar):",
            "except* (Foo, Bar) as e:"
        )
    ),
)


@pytest.mark.parametrize("mistake_pos", (0, 1, 2))
@pytest.mark.parametrize("except_", EXCEPT_STATEMENTS)
def test_try_except(plugin, mistake_pos, except_):
    s = """try:
    %%s
%s
    %%s
""" % except_
    substitutes = ["a = 1"] * 2
    if mistake_pos:
        substitutes[mistake_pos - 1] = "a = (1)"
    s = s % tuple(substitutes)
    assert len(plugin(s)) == bool(mistake_pos)


@pytest.mark.parametrize("mistake_pos", (0, 1, 2, 3))
@pytest.mark.parametrize("except_", EXCEPT_STATEMENTS)
def test_try_except_finally(plugin, mistake_pos, except_):
    s = """try:
    %%s
%s
    %%s
finally:
    %%s
""" % except_
    substitutes = ["a = 1"] * 3
    if mistake_pos:
        substitutes[mistake_pos - 1] = "a = (1)"
    s = s % tuple(substitutes)
    assert len(plugin(s)) == bool(mistake_pos)


@pytest.mark.parametrize("mistake_pos", (0, 1, 2, 3))
@pytest.mark.parametrize("except_", EXCEPT_STATEMENTS)
def test_try_except_else(plugin, mistake_pos, except_):
    s = """try:
    %%s
%s
    %%s
else:
    %%s
""" % except_
    substitutes = ["a = 1"] * 3
    if mistake_pos:
        substitutes[mistake_pos - 1] = "a = (1)"
    s = s % tuple(substitutes)
    assert len(plugin(s)) == bool(mistake_pos)


@pytest.mark.parametrize("mistake_pos", (0, 1, 2, 3))
@pytest.mark.parametrize("except_", EXCEPT_STATEMENTS)
def test_try_except_else_finally(plugin, mistake_pos, except_):
    s = """try:
    %%s
%s
    %%s
else:
    %%s
finally:
    %%s
""" % except_
    substitutes = ["a = 1"] * 4
    if mistake_pos:
        substitutes[mistake_pos - 1] = "a = (1)"
    s = s % tuple(substitutes)
    assert len(plugin(s)) == bool(mistake_pos)


@pytest.mark.parametrize("except_", (
    except_.replace("(", "((").replace(")", "))")
    for except_ in EXCEPT_STATEMENTS if "(" in except_
))
def test_redundant_parens_in_except(plugin, except_):
    s = """\
try:
    a = 1
%s
    a = 2
""" % except_
    assert len(plugin(s)) == 1


@pytest.mark.parametrize(
    ("mistake_pos", "elif_count", "else_"),
    (
        (pos, elif_count, False)
        for elif_count in range(1, 3)
        for else_ in (True, False)
        for pos in range(3 - else_ + elif_count * 2)
    )
)
def test_if_elif_else(plugin, mistake_pos, elif_count, else_):
    s = "if %s:\n    %s\n"
    for _ in range(elif_count):
        s += "elif %s:\n    %s\n"
    if else_:
        s += "else:\n    %s\n"
    substitutes = ["foo"] * (2 + elif_count * 2 + else_)
    if mistake_pos:
        substitutes[mistake_pos - 1] = "(foo)"
    s = s % tuple(substitutes)
    assert len(plugin(s)) == bool(mistake_pos)


def test_multi_line_if(plugin):
    s = """if (
    a
    or b
):
    foo()
elif (
    c
    or d
):
    bar
"""
    assert not plugin(s)


@pytest.mark.skipif(sys.version_info < (3, 10), reason="Python 3.10+ only")
@pytest.mark.parametrize(("case_", "case_problem_columns"), (
    ("a", {}),
    ("(a)", {0}),
    ("a,", {}),
    ("(a,)", {}),
    ("[a]", {}),
    ("a, b", {}),
    ("(a, b)", {}),
    ("[a, b]", {}),
    ("([a, b])", {0}),
    ("[(a, b)]", {}),
    ("((a))", {0}),
    ("((a,))", {0}),
    ("((a,),)", {}),
    ("(a, (b))", {4}),
    ("(a, (b, c))", {}),
    ("(a, ((b, c)))", {4}),
))
@pytest.mark.parametrize(("match", "match_problem_columns"), (
    ("foo", {}),
    ("(foo)", {0}),
    ("foo + bar + baz", {}),
    ("(foo + bar) + baz", {}),
    ("(foo + bar + baz)", {0}),
))
def test_match_case(plugin, case_, case_problem_columns,
                    match, match_problem_columns):
    s = f"""match {match}:
    case {case_}:
        ...
"""
    print(s)
    problems = {re.match(r"^(\d+):(\d+) (\w+)", problem).groups()
                for problem in plugin(s)}
    assert problems == (
        {
            ("1", str(7 + column), "PAR001")
            for column in match_problem_columns
        } | {
            ("2", str(10 + column), "PAR001")
            for column in case_problem_columns
        }
    )


@pytest.mark.skipif(sys.version_info < (3, 10), reason="Python 3.10+ only")
def test_match_2_case(plugin):
    s = """match foo:
    case a:
        ...
    case b:
        ...
"""
    assert not plugin(s)


def test_multi_line_keyword_in_call(plugin):
    s = """def foo():
    return bar(
        a=b,
        c=(a
           is b)
    )"""
    assert len(plugin(s)) == 0


@pytest.mark.parametrize("expr", ("a", "a is b"))
def test_single_line_keyword_in_call(plugin, expr):
    s = f"""def foo():
    return bar(
        a=b,
        c=({expr})
    )"""
    assert len(plugin(s)) == 1


@pytest.mark.parametrize("expr", ("a", "a is b"))
def test_practically_single_line_keyword_in_call(plugin, expr):
    s = f"""def foo():
    return bar(
        a=b,
        c=({expr}
        )
    )"""
    assert len(plugin(s)) == 1


@pytest.mark.parametrize("expr", ("a", "a is b"))
def test_continuation_keyword_in_call(plugin, expr):
    s = f"""def foo():
    return bar(
        a=b,
        c=(
            {expr}
        )
    )"""
    assert not plugin(s)


def test_multi_line_keyword_in_decorator_call(plugin):
    s = """\
@baz(
    a=b,
    c=(a
       is b)
)
def foo():
    pass
"""
    assert len(plugin(s)) == 0


@pytest.mark.parametrize("expr", ("a", "a in b"))
def test_single_line_keyword_in_decorator_call(plugin, expr):
    s = f"""\
@baz(
    a=b,
    c=({expr})
)
def foo():
    pass
"""
    assert len(plugin(s)) == 1


@pytest.mark.parametrize("expr", ("a", "a in b"))
def test_practically_single_line_keyword_in_decorator_call(plugin, expr):
    s = f"""\
@baz(
    a=b,
    c=({expr}
    )
)
def foo():
    pass
"""
    assert len(plugin(s)) == 1


@pytest.mark.parametrize("expr", ("a", "a in b"))
def test_continuation_keyword_in_decorator_call(plugin, expr):
    s = f"""\
@baz(
    a=b,
    c=(
        {expr}
    )
)
def foo():
    pass
"""
    assert not plugin(s)


def test_multi_line_keyword_in_def(plugin):
    s = """\
def foo(a=(1
           + 2)):
    bar
"""
    assert len(plugin(s)) == 0


def test_multi_line_keyword_with_annotation_in_def(plugin):
    s = """\
def foo(a: int = (1
                  + 2)):
    bar
"""
    assert len(plugin(s)) == 0


@pytest.mark.parametrize("type_annotation", ("", ": int "))
@pytest.mark.parametrize("expr", ("1", "1 + 2"))
def test_single_line_keyword_in_def(plugin, type_annotation, expr):
    s = f"""\
def foo(a{type_annotation}=({expr})):
    bar
"""
    assert len(plugin(s)) == 1


@pytest.mark.parametrize("type_annotation", ("", ": int "))
@pytest.mark.parametrize("expr", ("1", "1 + 2"))
def test_practically_single_line_keyword_in_def(plugin, type_annotation, expr):
    s = f"""\
def foo(
    a{type_annotation}=({expr}
    )
):
    bar
"""
    assert len(plugin(s)) == 1


@pytest.mark.parametrize("type_annotation", ("", ": int "))
@pytest.mark.parametrize("expr", ("1", "1 + 2"))
def test_continuation_keyword_in_def(plugin, type_annotation, expr):
    s = f"""\
def foo(
    a{type_annotation}=(
        {expr}
    )
):
    bar
"""
    assert not plugin(s)


@pytest.mark.parametrize("path", (
    path
    for path in (
        Path(__file__).parent / ".." / "flake8_picky_parentheses"
    ).iterdir()
    if path.is_file()
))
def test_run_on_ourself(plugin, path):
    s = path.read_text()
    assert not plugin(s)


@pytest.mark.parametrize("mistake_pos", range(4))
def test_two_methods(plugin, mistake_pos):
    s = """class Foo:
    def bar(self):
        %s
    def baz(self):
        %s
        %s
"""
    substitutes = ["a = 1"] * 3
    if mistake_pos:
        substitutes[mistake_pos - 1] = "a = (1)"
    s = s % tuple(substitutes)
    assert len(plugin(s)) == bool(mistake_pos)


@pytest.mark.parametrize("mistake_pos", range(2))
@pytest.mark.parametrize("doc_str_delimiter", ('"""', "'''"))
def test_two_methods_and_function_walk_into_a_bar(plugin, mistake_pos,
                                                  doc_str_delimiter):
    s = f"""class Foo:
    def bar(self):
        ...
    def bar(self):
        {doc_str_delimiter}
        It's a docstring.
        {doc_str_delimiter}
        ...
%s
"""
    substitutes = ["foo()"]
    if mistake_pos:
        substitutes[mistake_pos - 1] = "foo((1))"
    s = s % tuple(substitutes)
    assert len(plugin(s)) >= bool(mistake_pos)


@pytest.mark.parametrize("mistake_pos", range(4))
@pytest.mark.parametrize("doc_str_delimiter", ('"""', "'''"))
def test_methods_and_if(plugin, mistake_pos, doc_str_delimiter):
    s = f"""class Foo:
    def bar(self):
        %s
    def baz(self):
        {doc_str_delimiter}
        A docstring.
        {doc_str_delimiter}
        if whatever:
            %s
"""
    substitutes = ["a = 1"] * 2
    if mistake_pos:
        substitutes[mistake_pos - 2] = "a = (1)"
    s = s % tuple(substitutes)
    assert len(plugin(s)) >= bool(mistake_pos)


# Allow parentheses in unpacking arguments if argument
@pytest.mark.parametrize(("args", "problems"), (
    ("a", 1),
    ("a or b", 0),
    ("a + b", 0),
    ("a if b else c", 0),
))
def test_args_unpacking(plugin, args, problems):
    s = f"foo(*({args}))"
    assert len(plugin(s)) == problems


@pytest.mark.parametrize(("kwargs", "problems"), (
    ("a", 1),
    ("a or b", 0),
    ("a + b", 0),
    ("a if b else c", 0),
))
def test_kwargs_unpacking(plugin, kwargs, problems):
    s = f"foo(**({kwargs}))"
    assert len(plugin(s)) == problems


@pytest.mark.parametrize("dict_", (
    """{
    "bar": ("baz"
            "az")
}""",
    """{
    "bar": (a
            + b)
}""",
    """{
    "bar": (
        "baz"
        "az"
    )
}""",
    """{
    "bar": (
        a
        + b
    )
}""",
))
def test_multi_line_dict_value_with_parens(plugin, dict_):
    s = f"foo = {dict_}"
    assert len(plugin(s)) == 1


@pytest.mark.parametrize("dict_", (
    """{
    "bar": "baz"
           "az"
}""",
    """{
    "bar": a
           + b
}""",
    """{
    "bar":
        "baz"
        "az"
}""",
    """{
    "bar":
        a
        + b
}""",
))
def test_multi_line_dict_value_without_parens(plugin, dict_):
    s = f"foo = {dict_}"
    assert not plugin(s)
