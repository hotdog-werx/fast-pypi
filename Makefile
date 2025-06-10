.EXPORT_ALL_VARIABLES:
SHELL := /bin/bash

.PHONY: all uv-update uv-install checks tests local-dev

uv-update:
	uv lock --upgrade

uv-install:
	uv sync --group dev --all-extras --locked

checks:
	./scripts/checks.sh

checks-ruff:
	./scripts/checks-ruff.sh

checks-pyright:
	./scripts/checks-pyright.sh

tests:
	./scripts/tests.sh

local-dev:
	uv run python scripts/local_dev
