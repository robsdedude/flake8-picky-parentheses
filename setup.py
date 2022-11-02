#!/usr/bin/env python

from setuptools import setup

from flake8_picky_parentheses import __version__ as version

with open("README.md", "r") as fd:
    long_description = fd.read()


install_requires = [
    "flake8>=3.7",
]

github_project_url = "https://github.com/robsdedude/flake8-picky-parentheses"

setup(
    name="flake8-picky-parentheses",
    version=version,
    description="flake8 plugin to nitpick about parenthesis, brackets, "
                "and braces",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Ivan Prychantovskyi, Rouven Bauer",
    url=github_project_url,
    project_urls={
        "Issue Tracker": f"{github_project_url}/issues",
        "Source Code": github_project_url,
        "Changelog": f"{github_project_url}/blob/master/CHANGELOG.md",
    },
    download_url="https://pypi.python.org/pypi/flake8-picky-parentheses",
    packages=["flake8_picky_parentheses"],
    entry_points={
        "flake8.extension": [
            "PAR0 = flake8_picky_parentheses:PluginRedundantParentheses",
            "PAR1 = flake8_picky_parentheses:PluginBracketsPosition"
        ],
    },
    classifiers=[
        "Framework :: Flake8",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
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
