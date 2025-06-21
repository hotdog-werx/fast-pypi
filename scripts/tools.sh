#!/bin/bash
set -euxo pipefail

uv tool install "ruff==0.11.13"

uv tool install "poethepoet==0.35.0"

# For testing
uv tool install "poetry==2.1.3"
uv tool install "pip==25.1.1"