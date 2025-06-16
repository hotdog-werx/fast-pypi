#!/bin/bash

# Function to wait for server
wait_for_server() {
    local url=$1
    local timeout=${2:-10}
    local interval=${3:-0.1}
    local start_time=$(date +%s)
    
    while true; do
        current_time=$(date +%s)
        if [ $((current_time - start_time)) -ge "$timeout" ]; then
            return 1
        fi
        
        if curl -s -f -H "User-Agent: Mozilla/5.0" "$url" >/dev/null 2>&1; then
            return 0
        fi
        
        sleep "$interval"
    done
}

# Function to start the demo app
start_demo_app() {
    local test_dir=$1
    
    export FAST_PYPI_LOCALFS_ROOT_PATH="$test_dir/fast-pypi-localfs"
    mkdir -p "$FAST_PYPI_LOCALFS_ROOT_PATH"

    uv run python -m tests.e2e.demo_app > "$test_dir/server.log" 2>&1 &
    echo $!  # Return the server PID
}

# Function to cleanup server and test directory
setup_cleanup() {
    local test_dir=$1
    local server_pid=$2

    cleanup() {
        local test_dir=$1
        local server_pid=$2

        if [ -n "${server_pid:-}" ]; then
            pkill -P "$server_pid" || true
            kill "$server_pid" || true
            wait "$server_pid" 2>/dev/null || true
        fi
        rm -rf "$test_dir"
    }
    trap "cleanup $test_dir $server_pid" EXIT
}
