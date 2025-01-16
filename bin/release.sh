#!/usr/bin/env bash
set -e

ROOT=$(dirname "$0")/..
SCRIPT=$(basename "$0")
TWINE_ARGS="--verbose"

if [ "$1" == "--real" ]
then
    shift
else
    TWINE_ARGS="${TWINE_ARGS} --repository testpypi"
fi

VERSION="$1"
if [ "${VERSION}" == "" ]
then
    echo "usage: ${SCRIPT} VERSION"
    exit 1
else
    source "${ROOT}/bin/dist-functions.sh"
    twine upload ${TWINE_ARGS} \
        "${DIST}/flake8_picky_parentheses-${VERSION}.tar.gz" \
        "${DIST}/flake8_picky_parentheses-${VERSION}-py3-none-any.whl"
fi
