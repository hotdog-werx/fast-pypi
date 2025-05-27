.EXPORT_ALL_VARIABLES:
SHELL := /bin/bash

uv-update:
	uv lock --upgrade

uv-install:
	uv sync --group dev --all-extras --locked

checks:
	./scripts/checks.sh

tests:
	./scripts/tests.sh

local-dev:
	uv run python scripts/local_dev
