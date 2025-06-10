#!/bin/bash
set -euxo pipefail

uv run basedpyright fast_pypi
uv run basedpyright tests