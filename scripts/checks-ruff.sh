#!/bin/bash
set -euxo pipefail

ruff format --check fast_pypi
ruff format --check tests

ruff check fast_pypi
ruff check tests