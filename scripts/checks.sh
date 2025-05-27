#!/bin/bash
set -euxo pipefail

ruff format --check fast_pypi
ruff format --check tests

ruff check fast_pypi
ruff check tests

basedpyright fast_pypi
basedpyright tests

./scripts/tests.sh