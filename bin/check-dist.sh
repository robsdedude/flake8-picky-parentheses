#!/usr/bin/env bash
set -e

ROOT=$(dirname "$0")/..
SCRIPT=$(basename "$0")
DIST="${ROOT}/dist"

VERSION="$1"
if [ "${VERSION}" == "" ]
then
    echo "usage: ${SCRIPT} VERSION"
    exit 1
else
    source "${ROOT}/bin/dist-functions"
    check_file "${DIST}/flake8-picky-parentheses-${VERSION}.tar.gz"
fi
