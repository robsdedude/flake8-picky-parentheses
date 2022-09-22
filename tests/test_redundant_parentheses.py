import ast
import sys
import tokenize
from typing import Set

import pytest

from flake8_picky_parentheses import PluginRedundantParentheses


@pytest.fixture(params=[True, False])
def plugin(request):
    use_run = request.param

    def run(s: str) -> Set[str]:
        lines = s.splitlines(keepends=True)

        def read_lines():
            return lines

        line_iter = iter(lines)
        file_tokens = list(tokenize.generate_tokens(lambda: next(line_iter)))
        tree = ast.parse(s)
        plugin = PluginRedundantParentheses(tree, read_lines, file_tokens)
        if use_run:
            problems = plugin.run()
        else:
            plugin.check()
            problems = (
                (line, col, msg, type(plugin))
                for line, col, msg in plugin.problems
            )
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
def test_nested_tuple_literal(plugin):
    s = """a = ("a", ("b", "c"))
    """
    assert not plugin(s)


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
def test_tuple_literal_unpacking(plugin):
    s = """a, b = "a", "b"
c = ((d + e))
    """
    res = plugin(s)
    assert len(res) == 2


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


# BAD (don't use parentheses for unpacking)
@pytest.mark.parametrize("ws1", _ws_generator())
@pytest.mark.parametrize("ws2", _ws_generator())
@pytest.mark.parametrize("ws3", _ws_generator())
@pytest.mark.parametrize("ws4", _ws_generator())
def test_unpacking(plugin, ws1, ws2, ws3, ws4):
    s = f"""({ws1}a{ws2},{ws3}){ws4}= ["a"]
    """
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
    assert len(plugin(s)) == 2


# BAD (function call with extra parentheses around expression)
def test_function_call_redundant_parens_2(plugin):
    s = """foo((1 + 2))
    """
    assert len(plugin(s)) == 2


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


# GOOD
# def test_multi_line_list(plugin):
# (we can't have just list in program without another functions)
#     s = """[
#         1
#         + 2,
#         3
#     ]
#     """
#     assert not plugin(s)


# BAD
# def test_multi_line_list_unnecessary_parens_1(plugin):
# (we can't have just list in program without another functions)
#     s = """[
#         (1
#          + 2),
#         3
#     ]
#     """
#     assert len(plugin(s)) == 1


# BAD
# def test_multi_line_list_unnecessary_parens_2(plugin):
# (we can't have just list in program without another functions)
#     s = """[
#         (
#             1
#             + 2
#         ),
#         3
#     ]
#     """
#     assert len(plugin(s)) == 1


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


BIN_OPS = ("**", "*", "@", "/", "//", "%", "+", "-", "<<",
           ">>", "&", "^", "|", "in", "is", "is not", "<",
           "<=", ">", ">=", "!=", "==", "and", "or")
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


MULTI_LINE_ALTERATION = (
    # (function, makes it bad)
    (_id, 0),
    (_make_multi_line, 0),
    (_make_multi_line_extra_parens_1, 2),
    (_make_multi_line_extra_parens_2, 1),
)


@pytest.mark.parametrize("op", UNARY_OPS)
@pytest.mark.parametrize("alteration", MULTI_LINE_ALTERATION)
def test_superfluous_parentheses_after_mono_op(plugin, op, alteration):
    alteration_func, introduced_flakes = alteration
    s = f"foo = {op} (bar) \n"
    s = alteration_func(s)
    assert len(plugin(s)) == 1 + introduced_flakes


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
    s = f"foo = (foo {op} bar) \n"
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


# GOOD (redundant in slice, but help readability)
def test_parens_in_slice_1(plugin):
    s = """foo[i:(i + 1)]
"""
    assert not plugin(s)


# GOOD (redundant in slice, but help readability)
def test_parens_in_slice_2(plugin):
    s = """foo[(i - 1):i]
"""
    assert not plugin(s)


# GOOD (redundant in slice but help readability)
def test_parens_in_slice_3(plugin):
    s = """foo[i:(-1)]
"""
    assert not plugin(s)


# GOOD ()
def test_parens_in_slice_4(plugin):
    s = """foo[i:-1]
"""
    assert not plugin(s)


# BAD (redundant in slice and don't help readability)
def test_parens_in_slice_5(plugin):
    s = """foo[(0):i]
"""
    assert len(plugin(s)) == 1


# GOOD (redundant in comprehension, but help readability)
@pytest.mark.parametrize("comprehension_type", (
    "()", "[]", "{}",
))
def test_if_with_parens_in_comprehension(plugin, comprehension_type):
    s = f"""{comprehension_type[0]}
    x
    for x in range(10)""" + " " + f"""
    if (some_super_mega_looooooooooooooooooooooooooooooooooooong_thing
        or some_other_super_mega_looooooooooooooooooooooong_thing)
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
