#!/usr/bin/env bash
set -e

ROOT=$(dirname "$0")/..
DIST="${ROOT}/dist"

function get_version
{
    python -c "from flake8_picky_parentheses._meta import version; print(version)"
}

function set_version
{
    sed -i 's/^version = .*/version = "'$1'"/g' flake8_picky_parentheses/_meta.py
}

function check_file
{
    FILE=$1
    echo -n "Checking file $(basename ${FILE})... "
    if [ -f "${FILE}" ]
    then
        echo "OK"
    else
        echo "missing"
        STATUS=1
    fi
}

function set_metadata_and_setup
{
    VERSION="$1"; shift

    cd ${ROOT}

    # Capture original package metadata
    ORIGINAL_VERSION=$(get_version)
    echo "Source code originally configured for package ${ORIGINAL_VERSION}"
    echo "----------------------------------------"
    grep "version\s\+=" flake8_picky_parentheses/_meta.py
    echo "----------------------------------------"

    function cleanup() {
      # Reset to original package metadata
      set_version "${ORIGINAL_VERSION}"
      echo "Source code reconfigured back to original package ${ORIGINAL_VERSION}"
      echo "----------------------------------------"
      grep "version\s\+=" flake8_picky_parentheses/_meta.py
      echo "----------------------------------------"
    }
    trap cleanup EXIT

    # Temporarily override package metadata
    set_version "${VERSION}"
    echo "Source code reconfigured for package ${VERSION}"
    echo "----------------------------------------"
    grep "version\s\+=" flake8_picky_parentheses/_meta.py
    echo "----------------------------------------"

    # Create source distribution
    find . -name *.pyc -delete
    rm -rf ${ROOT}/*.egg-info 2> /dev/null
    python setup.py $*
    check_file "${DIST}/flake8-picky-parentheses-${VERSION}.tar.gz"

  trap - EXIT
  cleanup
}

function setup
{
    ARGS="$*"
    rm -rf ${DIST} 2> /dev/null
    set_metadata_and_setup ${ARGS}
}
