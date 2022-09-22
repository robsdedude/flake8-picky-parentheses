How tow Contribute
==================

## Report Bugs
If you find any bugs, please report them in the
[issue tracker](https://github.com/robsdedude/flake8-picky-parentheses/issues)
of this repository.


## Contribute Code
As you may have noticed, this project is an opinionated, nitpicky linter
plugin. Likewise opinionated and nitpicky are we when it comes to code style of
contributions. Please make sure you install the pre-commit hooks that will then
run linters and more before every commit. That way, you won't even be able to
commit code that doesn't adhere to our code style.

Installation:
```bash
pip install pre-commit
pre-commit install
```

If you want to run the checks without committing, you can run
```bash
pre-commit run --all-files
```

Should you want to commit without running the checks, you can use
```bash
git commit --no-verify
```
Think twice why you'd want to do that ;).
