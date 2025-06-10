#!/bin/bash
set -euxo pipefail

./scripts/checks-ruff.sh
./scri;ts/checks-pyright.sh
./scripts/checks-tests.sh