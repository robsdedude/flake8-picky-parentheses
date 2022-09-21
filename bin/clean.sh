#!/usr/bin/env bash

ROOT=$(dirname "$0")

find -name __pycache__ -delete
find -name *.py[co] -delete
find -name *.so -delete

rm -rf ${ROOT}/build ${ROOT}/dist ${ROOT}/docs/build ${ROOT}/*.egg-info ${ROOT}/.coverage ${ROOT}/.tox ${ROOT}/.cache ${ROOT}/.pytest_cache ${ROOT}/.benchmarks
