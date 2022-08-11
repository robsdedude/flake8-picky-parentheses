![Neo4j_logo](https://dist.neo4j.com/wp-content/uploads/20210423072428/neo4j-logo-2020-1.svg)

<h2 align="center"> Redundant parentheses checker</h2>

## Installation and Usage

### Installation

`IDK)`

### Usage

`Rouven help`

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