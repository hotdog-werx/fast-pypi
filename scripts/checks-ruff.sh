#!/bin/bash
set -euxo pipefail

uv run ruff format --check fast_pypi
uv run ruff format --check tests

uv run ruff check fast_pypi
uv run ruff check tests