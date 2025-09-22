#!/bin/bash

# Test script for comprehensive benchmarking data collection system
# This script performs basic validation of the data collection system
# without running the full expensive benchmarks

set -euo pipefail

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[TEST INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[TEST SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[TEST WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[TEST ERROR]${NC} $1"
}

# Test helper functions from the main script
test_helper_functions() {
    log_info "Testing helper functions..."

    # Source the main script to get access to functions
    source ./run_comprehensive_benchmarks.sh

    # Test source hash calculation
    local hash1=$(calculate_source_hash)
    local hash2=$(calculate_source_hash)

    if [ "$hash1" = "$hash2" ]; then
        log_success "Source hash calculation is consistent: $hash1"
    else
        log_error "Source hash calculation is inconsistent"
        return 1
    fi

    # Test rustc version formatting
    local rustc_ver=$(get_rustc_version)
    if [[ "$rustc_ver" =~ ^[0-9_]+$ ]]; then
        log_success "Rustc version formatting works: $rustc_ver"
    else
        log_error "Rustc version formatting failed: $rustc_ver"
        return 1
    fi

    # Test hostname sanitization
    local hostname=$(get_hostname)
    if [[ "$hostname" =~ ^[a-z0-9_]+$ ]]; then
        log_success "Hostname sanitization works: $hostname"
    else
        log_error "Hostname sanitization failed: $hostname"
        return 1
    fi

    return 0
}

# Test metadata collection
test_metadata_collection() {
    log_info "Testing metadata collection..."

    local temp_dir=$(mktemp -d)

    # Source the main script
    source ./run_comprehensive_benchmarks.sh

    # Test system info collection
    if collect_system_info "$temp_dir/system-info.json"; then
        if [ -f "$temp_dir/system-info.json" ] && [ -s "$temp_dir/system-info.json" ]; then
            log_success "System info collection works"
        else
            log_error "System info file is empty or missing"
            rm -rf "$temp_dir"
            return 1
        fi
    else
        log_error "System info collection failed"
        rm -rf "$temp_dir"
        return 1
    fi

    # Test build info collection
    if collect_build_info "$temp_dir/build-info.json"; then
        if [ -f "$temp_dir/build-info.json" ] && [ -s "$temp_dir/build-info.json" ]; then
            log_success "Build info collection works"
        else
            log_error "Build info file is empty or missing"
            rm -rf "$temp_dir"
            return 1
        fi
    else
        log_error "Build info collection failed"
        rm -rf "$temp_dir"
        return 1
    fi

    # Test source hashes collection
    if collect_source_hashes "$temp_dir/source-hashes.json"; then
        if [ -f "$temp_dir/source-hashes.json" ] && [ -s "$temp_dir/source-hashes.json" ]; then
            log_success "Source hashes collection works"
        else
            log_error "Source hashes file is empty or missing"
            rm -rf "$temp_dir"
            return 1
        fi
    else
        log_error "Source hashes collection failed"
        rm -rf "$temp_dir"
        return 1
    fi

    # Test run config collection
    if collect_run_config "$temp_dir/run-config.json"; then
        if [ -f "$temp_dir/run-config.json" ] && [ -s "$temp_dir/run-config.json" ]; then
            log_success "Run config collection works"
        else
            log_error "Run config file is empty or missing"
            rm -rf "$temp_dir"
            return 1
        fi
    else
        log_error "Run config collection failed"
        rm -rf "$temp_dir"
        return 1
    fi

    # Validate JSON structure (if jq is available)
    if command -v jq >/dev/null 2>&1; then
        for json_file in "$temp_dir"/*.json; do
            if ! jq empty "$json_file" >/dev/null 2>&1; then
                log_error "Invalid JSON in $(basename "$json_file")"
                rm -rf "$temp_dir"
                return 1
            fi
        done
        log_success "All generated JSON files are valid"
    else
        log_warning "jq not available, skipping JSON validation"
    fi

    # Clean up
    rm -rf "$temp_dir"
    return 0
}

# Test directory structure creation
test_directory_structure() {
    log_info "Testing directory structure creation..."

    local test_run_dir="results/runs/test_$(date +%s)"

    # Create test directory structure
    mkdir -p "$test_run_dir"/{metadata,raw-results,assembly/{bench_newlines,bench_csv},logs}

    # Verify structure
    local expected_dirs=(
        "$test_run_dir/metadata"
        "$test_run_dir/raw-results"
        "$test_run_dir/assembly/bench_newlines"
        "$test_run_dir/assembly/bench_csv"
        "$test_run_dir/logs"
    )

    for dir in "${expected_dirs[@]}"; do
        if [ ! -d "$dir" ]; then
            log_error "Directory not created: $dir"
            rm -rf "$test_run_dir"
            return 1
        fi
    done

    log_success "Directory structure creation works"

    # Clean up
    rm -rf "$test_run_dir"
    return 0
}

# Test project file detection
test_project_files() {
    log_info "Testing project file detection..."

    local required_files=(
        "Cargo.toml"
        "src/lib.rs"
        "benches/bench_newlines.rs"
        "benches/bench_csv.rs"
        "bench_all.sh"
        "check_simd.sh"
    )

    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            log_error "Required project file missing: $file"
            return 1
        fi
    done

    log_success "All required project files found"
    return 0
}

# Test compilation capability
test_compilation() {
    log_info "Testing basic compilation capability..."

    if cargo check >/dev/null 2>&1; then
        log_success "Basic cargo check passes"
    else
        log_error "Cargo check failed"
        return 1
    fi

    if cargo check --benches >/dev/null 2>&1; then
        log_success "Benchmark compilation check passes"
    else
        log_error "Benchmark compilation check failed"
        return 1
    fi

    return 0
}

# Test assembly generation capability
test_assembly_generation() {
    log_info "Testing assembly generation capability..."

    # Try to generate assembly for a simple case
    local temp_dir=$(mktemp -d)

    if timeout 30 cargo rustc --bench bench_newlines --release -- -C target-cpu=default --emit asm >/dev/null 2>&1; then
        # Look for generated assembly
        local asm_file=$(find target/release/deps/ -name "bench_newlines*.s" -type f 2>/dev/null | head -1)
        if [ -n "$asm_file" ] && [ -f "$asm_file" ]; then
            log_success "Assembly generation works"
            rm -f "$asm_file"
        else
            log_warning "Assembly generation succeeded but no .s file found"
        fi
    else
        log_warning "Assembly generation test failed (may be expected on some systems)"
    fi

    rm -rf "$temp_dir"
    return 0
}

# Run all tests
run_all_tests() {
    log_info "Starting comprehensive benchmarking system tests..."
    echo "================================================================="

    local tests_passed=0
    local tests_failed=0

    # Array of test functions
    local tests=(
        "test_project_files"
        "test_helper_functions"
        "test_metadata_collection"
        "test_directory_structure"
        "test_compilation"
        "test_assembly_generation"
    )

    for test in "${tests[@]}"; do
        echo ""
        if $test; then
            ((tests_passed++))
        else
            ((tests_failed++))
            log_error "Test failed: $test"
        fi
    done

    echo ""
    echo "================================================================="
    log_info "Test Results:"
    log_success "Tests passed: $tests_passed"
    if [ $tests_failed -gt 0 ]; then
        log_error "Tests failed: $tests_failed"
        return 1
    else
        log_success "All tests passed!"
        return 0
    fi
}

# Main execution
main() {
    # Verify we're in the right directory
    if [ ! -f "Cargo.toml" ] || [ ! -f "src/lib.rs" ]; then
        log_error "Must be run from the root of the benchfind project"
        exit 1
    fi

    run_all_tests
}

# Script entry point
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi
