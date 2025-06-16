#!/bin/bash
set -euxo pipefail

# Source common functions
# shellcheck source=./test-e2e-common.sh
. "$(dirname "$0")/test-e2e-common.sh"

# Create temp directory for test
TEST_DIR=$(mktemp -d)

echo "TEST_DIR=$TEST_DIR"

# Find uv executable and start server
SERVER_PID=$(start_demo_app "$TEST_DIR")
setup_cleanup "$TEST_DIR" "$SERVER_PID"

# Wait for server to be ready
if ! wait_for_server "http://localhost:8100/healthz" 10 0.1; then
    echo "Server failed to start. Server log:"
    cat "$TEST_DIR/server.log"
    exit 1
fi

# Package versions to test
declare -a versions=(
    "example-package 0.1.0"
    "example-package 0.2.0"
    "example-package 0.2.0a1"
    "other-package 0.1.0"
)

# For each version, create, build and publish the package
for version in "${versions[@]}"; do
    read -r pkg_name pkg_version <<< "$version"
    
    # Create package from template
    pkg_dir="$TEST_DIR/$pkg_name-$pkg_version"
    cp -r "tests/e2e/publishable_templates/example_package_poetry" "$pkg_dir"
    
    # Find GNU sed and replace template variables
    SED=$(find_sed) || exit 1
    "$SED" -i "s/{{package_name}}/$pkg_name/g" "$pkg_dir/pyproject.toml"
    "$SED" -i "s/{{package_version}}/$pkg_version/g" "$pkg_dir/pyproject.toml"
    "$SED" -i "s/{{package_version}}/$pkg_version/g" "$pkg_dir/src/version.py"

    # Build the package
    poetry build --project "$pkg_dir"

    # Configure and publish to local PyPI
    poetry --project "$pkg_dir" config repositories.fastpypi http://hot:dog@localhost:8100/fast-pypi/upload/
    POETRY_HTTP_BASIC_FASTPYPI_USERNAME=hot \
    POETRY_HTTP_BASIC_FASTPYPI_PASSWORD=dog \
    poetry --project "$pkg_dir" publish --repository fastpypi
done

# Verify the published versions
versions_json=$(uv run pip index versions example-package \
    --index-url http://hot:dog@localhost:8100/fast-pypi/simple/ \
    --json --pre)

# Check if we got all versions
if ! echo "$versions_json" | grep -q '"0.1.0"' || \
   ! echo "$versions_json" | grep -q '"0.2.0"' || \
   ! echo "$versions_json" | grep -q '"0.2.0a1"'; then
    echo "Missing expected versions"
    exit 1
fi

# Create a new project and install the package
project_dir="$TEST_DIR/test-project"
mkdir -p "$project_dir"

(
    cd "$project_dir" || exit 1

    # Initialize new poetry project
    poetry init \
        --name=test-project \
        --description="" \
        --author="" \
        --no-interaction

    # Configure source and install package
    poetry source add fastpypi http://localhost:8100/fast-pypi/simple/

    export POETRY_HTTP_BASIC_REPO=
    export POETRY_HTTP_BASIC_FASTPYPI_USERNAME=hot
    export POETRY_HTTP_BASIC_FASTPYPI_PASSWORD=dog
    poetry add example-package==0.2.0 --source fastpypi

    # Verify installation
    installed_packages=$(poetry show)

    if ! echo "$installed_packages" | grep -q "example-package 0.2.0"; then
        echo "Package not installed correctly"
        exit 1
    fi
)

echo "All tests passed successfully!"

