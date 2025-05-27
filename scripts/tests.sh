#!/bin/bash
set -euxo pipefail

uv run coverage run \
    --concurrency 'thread,greenlet' \
    --source fast_pypi -m pytest -vv .

uv run coverage report -m --fail-under "${COVERAGE_FAIL_UNDER:-100}"