.EXPORT_ALL_VARIABLES:
SHELL := /bin/bash

uv-update:
	uv lock --upgrade

uv-install:
	uv sync --group dev --all-extras --locked

tests:
	uv run coverage run \
        --concurrency 'thread,greenlet' \
        --source "packages/python/fast_pypi" -m pytest -vv packages/python && \
    uv run coverage report -m --fail-under "${COVERAGE_FAIL_UNDER:-100}"

local-dev:
	uv run python -m local_dev
