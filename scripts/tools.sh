#!/bin/bash
set -euxo pipefail

uv tool install "ruff>=0.11.13,<1"

uv tool install "poethepoet>=0.35.0,<1"

# For testing
uv tool install "poetry"
uv tool install "pip"