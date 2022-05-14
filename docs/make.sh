#!/usr/bin/env bash

SOURCE_ROOT="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"/..

# Please check the folder python3.9 and get the corrected one.
PYTHONPATH="${PYTHONPATH}:${SOURCE_ROOT}:${SOURCE_ROOT}/.venv/lib/python3.9/site-packages" sphinx-build -b html source build