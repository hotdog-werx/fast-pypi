#!/bin/bash
set -euxo pipefail

# Source common functions
# shellcheck source=./test-e2e-common.sh
. "$(dirname "$0")/test-e2e-common.sh"

# Create temp directory for test
TEST_DIR=$(mktemp -d)

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
    cp -r "tests/e2e/publishable_templates/example_package_uv" "$pkg_dir"
    
    # Find GNU sed and replace template variables
    SED=$(find_sed) || exit 1
    "$SED" -i "s/{{package_name}}/$pkg_name/g" "$pkg_dir/pyproject.toml"
    "$SED" -i "s/{{package_version}}/$pkg_version/g" "$pkg_dir/src/version.py"

    # Build and publish the package
    uv --project "$pkg_dir" build

    uv --project "$pkg_dir" publish \
        --publish-url http://localhost:8100/fast-pypi/upload/ \
        --username hot \
        --password dog \
        "$pkg_dir/dist/*"
done

# Verify the published versions
versions_json=$(uv run pip index versions example-package \
    --index-url http://hot:dog@localhost:8100/fast-pypi/simple/ \
    --json --pre)

# Check if jq is available
if ! command -v jq >/dev/null 2>&1; then
    echo "jq is required but not installed. Please install it first."
    exit 1
fi

# Check if we got all versions using jq
published_versions=$(echo "$versions_json" | jq -r '.versions[]')
expected_versions=("0.1.0" "0.2.0" "0.2.0a1")

for version in "${expected_versions[@]}"; do
    if ! echo "$published_versions" | grep -q "^$version\$"; then
        echo "Missing version: $version"
        echo "Found versions: $published_versions"
        exit 1
    fi
done

# Create a new project and install the package
project_dir="$TEST_DIR/test-project"
mkdir -p "$project_dir"

# Verify the package was installed correctly
(
    cd "$project_dir" || exit 1

    # Initialize new project and install package
    uv init . --name test-project

    uv add example-package==0.2.0 \
        --index http://hot:dog@localhost:8100/fast-pypi/simple/ \
        --no-cache

    # Use jq to check installed package version
    installed_json=$(uv pip list --format=json)
    
    if ! command -v jq >/dev/null 2>&1; then
        echo "jq is required but not installed. Please install it first."
        exit 1
    fi

    installed_version=$(echo "$installed_json" | jq -r '.[] | select(.name=="example-package") | .version')
    
    if [ "$installed_version" != "0.2.0" ]; then
        echo "Package not installed correctly. Found version: ${installed_version:-not found}"
        exit 1
    fi
)

echo "All tests passed successfully!"
