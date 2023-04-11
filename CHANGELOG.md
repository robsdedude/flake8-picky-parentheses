Changelog
=========

## NEXT
***
**⭐ New**
* Separate PAR101 codes into PAR101, PAR102, PAR103, PAR104 ([#30](https://github.com/robsdedude/flake8-picky-parentheses/pull/30); contribution by cyyc1)


## 0.4.0
***
**⭐ New**
* Add support for Python 3.11 ([#28](https://github.com/robsdedude/flake8-picky-parentheses/pull/28))


## 0.3.2
***
**🔧 Fixes**
* Fix exception for parentheses in slices under Python 3.9+ ([#26](https://github.com/robsdedude/flake8-picky-parentheses/pull/26)).


## 0.3.1
***
**🔧 Fixes**
* Improve exceptions for redundant parentheses in multi-line cases + clarify documentation in that area ([#25](https://github.com/robsdedude/flake8-picky-parentheses/pull/25)).


## 0.3.0
***
**⭐ New**
* Expanded exception for redundant parentheses that help to highlight operator precedence to also include unpacking arguments (`*`, and `**`) before function arguments ([#23](https://github.com/robsdedude/flake8-picky-parentheses/pull/23)).
* Add exception for parentheses around multi-line `for` parts in comprehensions ([#23](https://github.com/robsdedude/flake8-picky-parentheses/pull/23)).

**🔧 Fixes**
* Python 3.10: fix `match`/`case` statements ([#24](https://github.com/robsdedude/flake8-picky-parentheses/pull/24)).


## 0.2.0
***
**♻ Rework of `PAR0xx` ([#22](https://github.com/robsdedude/flake8-picky-parentheses/pull/20))**
* Improved documentation around exceptions to the rules.
* Added exception for multiline keyword arguments and argument default values.
* Rewrite of the redundant parentheses checker (`PAR0xx`) to increase reliability, stability and performance.


## 0.1.2
***
**🔧 Fixes**
* Fix false positives caused by detecting logical lines incorrectly
  ([#20](https://github.com/robsdedude/flake8-picky-parentheses/pull/20)).
* Fix false positives in classes in Python 3.7
  ([#20](https://github.com/robsdedude/flake8-picky-parentheses/pull/20)).


## 0.1.1
***
**🔧 Fixes**
* Fix complaining about necessary parentheses in multi-line unpacking
  assignments
  ([#16](https://github.com/robsdedude/flake8-picky-parentheses/pull/16)).
* Fix not complaining about misaligned parentheses, brackets, braces when the
  opening line ends on a comment
  ([#18](https://github.com/robsdedude/flake8-picky-parentheses/pull/18)).


## 0.1.0
***
**🎉 Initial release**
