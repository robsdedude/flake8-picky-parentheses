Changelog
=========

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
