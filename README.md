
<h2 align="center"> Redundant parentheses checker</h2>

## Installation and Usage

### Installation

To download latest version of program, use:

```sh
https://github.com/robsdedude/flake8-redundant-parentheses.git
```


### Usage
This plugin works with flake8. Full documentation how to run it:

```sh
https://flake8.pycqa.org/en/latest/
```


After downloading program from GitHub you can boot it on your code and if 
you have syntax mistakes in it, you will get PAR ot BRA error.

## Examples

There are four error codes which you can get using this plugin:

PAR001: means that you use redundant parentheses, and they do not help 
readability  
```
# BAD
a = (("a", "b"))
```   
PAR002: means that you use parentheses for unpacking tuple  
``` 
# BAD
(a,) = "b"
```  
BRA001: means that opening bracket is last in its line, but closing is not on
new line
```
# BAD
if (
a == b): c + d
```
BRA002: means that closing bracket is on new line, but there is mismatch of 
indentation
```
# BAD
if (
a == b
        ): c + d
```

Program will not complain about first two lines, because in first case 
parentheses are redundant, but helps readability and in second case we just 
don't have parentheses. In next three lines there are examples where 
parentheses are redundant and can not help readability.

```sh
a = ("a",)     # GOOD
a = "a",       # GOOD
a = ("a")      # BAD
a = (("a"),)   # BAD
a = (("a",))   # BAD
foo(("a",))    # GOOD
foo("a",)      # BAD
```

In code there is an exception for parentheses in mathematical and logical
constructs if parentheses are not needed, but they help, to divide parts 
of algorithm and show sequence of actions.

```sh
# ALL GOOD
a = (1 + 2) + 3
a = (1 + 2) % 3
a = 1 and (2 + 3)
a = (1 / 2) * 3
a = not (1 + 2)
a = (not 1) + 2
```
### Additional information

Plugin was developed to improve the code quality of NEO4J Python projects.