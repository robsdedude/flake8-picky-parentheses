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
    source "${ROOT}/bin/dist-functions.sh"
    check_file "${DIST}/flake8_picky_parentheses-${VERSION}.tar.gz"
    check_file "${DIST}/flake8_picky_parentheses-${VERSION}-py3-none-any.whl"
fi
