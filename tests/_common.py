import re


def no_lint(lints):
    return not lints


def some_lint(lints):
    return lints


def n_lints(lints, n):
    return len(lints) == n


def lint_codes(lints, codes):
    lint_codes_ = sorted(re.match(r"\d+:\d+ (PAR\d+): .*", lint).group(1)
                         for lint in lints)
    codes = sorted(codes)
    return lint_codes_ == codes
