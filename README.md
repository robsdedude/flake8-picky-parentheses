![Neo4j_logo](https://dist.neo4j.com/wp-content/uploads/20210423072428/neo4j-logo-2020-1.svg)

<h2 align="center"> Redundant parentheses checker</h2>

## Installation and Usage

### Installation

To download latest version of program, use:

```sh
https://github.com/robsdedude/flake8-redundant-parentheses.git
```

### Usage

After downloading program from GitHub you can boot it on your code and if 
you have syntax mistakes in it, you will get  PAR error.

## Examples

Program will not complain about first two lines, because in first case 
parentheses are redundant, but helps readability and in second case we just 
don't have parentheses. In next three lines there are examples where 
parentheses are redundant and can not help readability.

```sh
a = ("a",)     #GOOD
a = "a",       #GOOD
a = ("a")      #BAD
a = (("a"),)   #BAD
a = (("a",))   #BAD
foo(("a",))    #GOOD
foo("a",)      #BAD
```

In code there is an exception for parentheses in mathematical and logical
constructs if parentheses are not needed, but they help, to divide parts 
of algorithm and show sequence of actions.

```sh
#ALL GOOD
a = (1 + 2) % 3
a = 1 and (2 + 3)
a = (1 / 2) * 3
a = not (1 + 2)
a = (not 1) + 2
```
