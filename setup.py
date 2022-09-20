#!/usr/bin/env python

from setuptools import setup

with open("README.md", "r") as fd:
    long_description = fd.read()


install_requires = [
    "flake8>=3.7",
    'importlib-metadata>=0.9;python_version<"3.8"',
]


setup(
    name="flake8_picky_parentheses",
    version="0.1.0",
    description="flake8 plugin to detect redundant parenthesis",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Ivan Prychantovskyi, Rouven Bauer",
    url="https://github.com/robsdedude/flake8-redundant-parentheses",
    packages=["flake8_picky_parentheses"],
    entry_points={
        "flake8.extension": [
            "PAR0 = flake8_picky_parentheses:PluginRedundantParentheses",
            "BRA0 = flake8_picky_parentheses:PluginBracketsPosition"
        ],
    },
    classifiers=[
        "Framework :: Flake8",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7"
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Software Development :: Quality Assurance",
    ],
    license="Apache License 2.0",
    keywords="flake8, plugin, redundant, superfluous, extraneous, "
             "unnecessary, parentheses, parenthesis, parens, brackets, "
             "linter, linting, codestyle, code style",
    install_requires=install_requires,
    python_requires=">=3.7",
)
