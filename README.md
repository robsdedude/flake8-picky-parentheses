Picky Parentheses
=================

Picky Parentheses is a [flake8](https://github.com/pycqa/flake8) plugin that
nitpicks all things parentheses, brackets and braces.
The plugin has two components:
 1. A checker that warns about redundant parentheses (with some exceptions).
 2. A checker for parentheses, brackets, and braces alignment.
    This component is very opinionated but has its own error codes so you can
    easily disable it.


## Table of Contents

 * [Installation and Usage](#installation-and-usage)
 * [Error Codes](#error-codes)
 * [Details and Exceptions](#details-and-exceptions)
 * [Additional Notes](#additional-notes)


## Installation and Usage
This is a plugin for `flake8`. It supports Python 3.7 - 3.10.  
Refer to the documentation of `flake8` on how to run it on your code:
https://flake8.pycqa.org/en/latest/

Two common options are to either install the plugin and then run `flake8`:
```bash
pip install flake8-picky-parentheses

flake8 '<path/to/your/code>'
```

Or to let `flake8` fetch the plugin for you (requires `flake8 >= 5.0.0`):
```bash
flake8 --require-plugins flake8-picky-parentheses '<path/to/your/code>'
```

If you only want to run this plugin and bypass any other `flake8` checks, you
can use the `--select` option:
```bash
flake8 [other options] --select='PAR0,PAR1' '<path/to/your/code>'
```

Where `PAR0` is the code for the redundant parentheses checker and `PAR1` is
the code for the parentheses alignment checker.

If you, in turn want to disable the opinionated parentheses alignment checker,
you can use the `--ignore` or `--extend-ignore` option:
```bash
flake8 [other options] --extend-ignore='PAR1' '<path/to/your/code>'
```


## Error Codes
These are the error codes which you can get using this plugin:

| Code                | Brief Descritption                                                     |
|---------------------|------------------------------------------------------------------------|
| [`PAR0xx`](#par0xx) | [Group] Redundant parentheses                                          |
| [`PAR001`](#par001) | Redundant parentheses (general)                                        |
| [`PAR002`](#par002) | Parenteheses used for tuple unpacking                                  |
|                     |                                                                        |
| [`PAR1xx`](#par1xx) | [Group] (Opinioinated) parentheses, brackets, braces not well-alinged  |
| [`PAR101`](#par101) | Opening bracket at the end the line, closing bracket not on a new line |
| [`PAR102`](#par102) | Closing bracket on a new line, but indentation missmatch               |

### `PAR0xx`
These are the error codes for the redundant parentheses checker.
#### `PAR001`
It means that you use redundant parentheses, and they do not help readability.
For example:
```python
# BAD
a = (("a", "b"))
```
#### `PAR002`
It means that you use parentheses for an unpacking expression. For example:
```python
# BAD
(a,) = "b"
```

#### `PAR1xx`
These are the error codes for the opinionated alignment checker.
#### `PAR101`
It means that the opening bracket is last in its line, but closing one is not
on a new line. For example:
```python
# BAD
if (
        a == b):
    c + d

# GOOD
if (
    a == b
):
    c + d

# BAD
a = [
    1, 2,
    3, 4]

# GOOD
a = [
    1, 2,
    3, 4
]

# GOOD
a = [1, 2,
     3, 4]
```
#### `PAR102`
It means that closing bracket is on new line, but there is a indentation
mismatch. For example:
```python
# BAD
if (
    a == b
        ):
    c + d

# GOOD
if (
    a == b
):
    c + d

# BAD
a = [
    1, 2,
    3, 4
    ]

# GOOD
a = [
    1, 2,
    3, 4
]
```


## Details and Exceptions

The redundant parentheses checker uses Python's `tokenize` and `ast` module to
try to remove each pair of parentheses and see if the code still compiles and
yields the same AST (i.e., is semantically equivalent).
If it does, a flake (lint error) is reported. However, there are two notable
exceptions to this rule:
 1. Parentheses for tuple literals
 2. A single pair or parentheses in expressions to highlight operator
    precedence.
    Even if these parentheses are redundant, they help to divide parts of
    expressions and show sequence of actions.
 3. Parts of slices
 4. Multi-line `if`s in comprehensions.
 5. Multi-line keyword arguments or argument defaults.

Exception type 1:
```python
a = ("a",)     # GOOD
a = "a",       # GOOD
a = ("a")      # BAD
a = (("a"),)   # BAD
a = (("a",))   # BAD
foo(("a",))    # GOOD
foo("a",)      # BAD
```

Exception type 2:
```python
a = (1 + 2) + 3     # GOOD
a = (1 + 2) % 3     # GOOD
a = 1 and (2 + 3)   # GOOD
a = (1 / 2) * 3     # GOOD
a = not (1 + 2)     # GOOD
a = (not 1) + 2     # GOOD
a = (1 + 2)         # BAD
a = 1 + (2)         # BAD
a = ((not 1)) + 2   # BAD
```

Exception type 3:
```python
foo[(1 + 2):10]    # GOOD
foo[1:(1 + 2)]     # GOOD
foo[1:5:(1 + 1)]   # GOOD
foo[:(-bar)]       # GOOD
foo[(1):]          # BAD
foo[:(1)]          # BAD
```

Exception type 4:
```python
# GOOD
a = (
    b for b in c
    if (
        some_thing == other_thing
        or whatever_but_long
    )
)

# GOOD
a = [
    b for b in c
    if (b
        in d)
]

# BAD
a = (
    b for b in c
    if (b in d)
)
```

Exception type 5:
```python
# GOOD
foo(bar=(a
         in b))

# BAD
foo(bar=(a in b))

# GOOD
def foo(bar=(a
             is b)):
    ...

# BAD
def foo(bar=(a is b)):
    ...
```

## Additional Notes

This plugin was developed to improve the code quality of Neo4j Python projects.
