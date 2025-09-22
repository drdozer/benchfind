#!/bin/bash

# Comprehensive Benchmarking Data Collection Script
# This script orchestrates complete benchmark data collection including:
# - System and build metadata collection
# - Benchmark execution with proper result organization
# - Assembly generation and SIMD analysis
# - Structured data storage for future analysis

set -euo pipefail

# Configuration
RESULTS_DIR="results"
SCHEMA_DIR="$RESULTS_DIR/schema"

# Color output for better UX
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to calculate source hash from benchmark-relevant files
calculate_source_hash() {
    local temp_file=$(mktemp)

    # Concatenate the content of files that affect benchmark results
    {
        echo "=== src/lib.rs ==="
        cat src/lib.rs
        echo "=== benches/bench_newlines.rs ==="
        cat benches/bench_newlines.rs
        echo "=== benches/bench_csv.rs ==="
        cat benches/bench_csv.rs
        echo "=== Cargo.toml ==="
        cat Cargo.toml
    } > "$temp_file"

    local hash=$(sha256sum "$temp_file" | cut -c1-8)
    rm "$temp_file"
    echo "$hash"
}

# Function to get sanitized rustc version
get_rustc_version() {
    rustc --version | sed 's/rustc \([^ ]*\).*/\1/' | tr '.' '_' | tr '-' '_'
}

# Function to get sanitized hostname
get_hostname() {
    hostname | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/_/g'
}

# Function to collect system information
collect_system_info() {
    local output_file="$1"

    log_info "Collecting system information..."

    cat > "$output_file" << EOF
{
  "collection_time": "$(date -Iseconds)",
  "hostname": "$(hostname)",
  "os": {
    "name": "$(uname -s)",
    "release": "$(uname -r)",
    "version": "$(uname -v)",
    "machine": "$(uname -m)",
    "processor": "$(uname -p)",
    "distribution": "$(if [ -f /etc/os-release ]; then source /etc/os-release && echo "$ID $VERSION_ID"; else echo "unknown"; fi)"
  },
  "cpu": {
    "model": "$(if [ -f /proc/cpuinfo ]; then grep 'model name' /proc/cpuinfo | head -1 | cut -d: -f2 | sed 's/^ *//'; else echo "unknown"; fi)",
    "cores": "$(nproc)",
    "architecture": "$(uname -m)",
    "features": "$(if [ -f /proc/cpuinfo ]; then grep 'flags' /proc/cpuinfo | head -1 | cut -d: -f2; else echo "unknown"; fi)"
  },
  "memory": {
    "total_kb": "$(if [ -f /proc/meminfo ]; then grep 'MemTotal' /proc/meminfo | awk '{print $2}'; else echo "unknown"; fi)",
    "available_kb": "$(if [ -f /proc/meminfo ]; then grep 'MemAvailable' /proc/meminfo | awk '{print $2}'; else echo "unknown"; fi)"
  },
  "environment": {
    "shell": "$SHELL",
    "user": "$USER",
    "pwd": "$PWD"
  }
}
EOF
}

# Function to collect build information
collect_build_info() {
    local output_file="$1"

    log_info "Collecting build information..."

    cat > "$output_file" << EOF
{
  "collection_time": "$(date -Iseconds)",
  "rust": {
    "rustc_version": "$(rustc --version)",
    "rustc_verbose": $(rustc --version --verbose | tail -n +2 | sed 's/^/    "/' | sed 's/: /": "/' | sed 's/$/",/' | sed '$ s/,$//' | (echo '{'; cat; echo '}')),
    "cargo_version": "$(cargo --version)"
  },
  "git": {
    "commit_hash": "$(git rev-parse HEAD)",
    "branch": "$(git rev-parse --abbrev-ref HEAD)",
    "status_clean": $(if [ -z "$(git status --porcelain)" ]; then echo "true"; else echo "false"; fi),
    "status_output": "$(git status --porcelain | sed 's/"/\\"/g')"
  },
  "target": {
    "default": "$(rustc --version --verbose | grep 'host:' | cut -d' ' -f2)"
  }
}
EOF
}

# Function to collect source file hashes
collect_source_hashes() {
    local output_file="$1"

    log_info "Collecting source file hashes..."

    cat > "$output_file" << EOF
{
  "collection_time": "$(date -Iseconds)",
  "files": {
    "src/lib.rs": "$(sha256sum src/lib.rs | cut -d' ' -f1)",
    "benches/bench_newlines.rs": "$(sha256sum benches/bench_newlines.rs | cut -d' ' -f1)",
    "benches/bench_csv.rs": "$(sha256sum benches/bench_csv.rs | cut -d' ' -f1)",
    "Cargo.toml": "$(sha256sum Cargo.toml | cut -d' ' -f1)",
    "Cargo.lock": "$(if [ -f Cargo.lock ]; then sha256sum Cargo.lock | cut -d' ' -f1; else echo 'null'; fi)"
  },
  "combined_hash": "$(calculate_source_hash)"
}
EOF
}

# Function to collect run configuration
collect_run_config() {
    local output_file="$1"

    log_info "Collecting run configuration..."

    cat > "$output_file" << EOF
{
  "collection_time": "$(date -Iseconds)",
  "targets": [
    "default",
    "native",
    "x86-64-v2",
    "x86-64-v3",
    "x86-64-v4"
  ],
  "benchmarks": [
    "bench_newlines",
    "bench_csv"
  ],
  "measurement_time_seconds": 15,
  "sample_sizes": {
    "bench_newlines": 50,
    "bench_csv": 100
  },
  "script_version": "1.0.0"
}
EOF
}

# Function to generate assembly for a specific implementation
generate_assembly_for_impl() {
    local benchmark_name="$1"
    local target="$2"
    local output_dir="$3"

    log_info "Generating assembly for $benchmark_name with target $target..."

    # Clean previous artifacts
    rm -rf target/release/deps/${benchmark_name}*.s
    rm -rf target/release/deps/${benchmark_name}*.o
    rm -rf target/release/deps/lib${benchmark_name}*.rlib
    rm -rf target/release/deps/lib${benchmark_name}*.rmeta
    find target/release/deps/ -name "${benchmark_name}-*.s" -delete 2>/dev/null || true
    find target/release/deps/ -name "${benchmark_name}-*.o" -delete 2>/dev/null || true

    mkdir -p "$output_dir"

    # Compile with assembly output
    local compile_cmd="cargo rustc --bench $benchmark_name --release -- -C target-cpu=$target --emit asm"

    if $compile_cmd > "$output_dir/compilation.log" 2>&1; then
        # Find the generated assembly file
        local asm_file=$(find target/release/deps/ -name "${benchmark_name}*.s" -type f -print0 | xargs -0 ls -t | head -n 1)

        if [ -n "$asm_file" ] && [ -f "$asm_file" ]; then
            cp "$asm_file" "$output_dir/complete_benchmark.s"
            log_success "Assembly generated for $benchmark_name/$target"
        else
            log_warning "No assembly file found for $benchmark_name/$target"
        fi

        # Clean up
        rm -f "$asm_file"
    else
        log_error "Failed to compile $benchmark_name for target $target"
        return 1
    fi
}

# Function to run SIMD analysis
run_simd_analysis() {
    local benchmark_name="$1"
    local target="$2"
    local assembly_dir="$3"
    local output_file="$4"

    log_info "Running SIMD analysis for $benchmark_name/$target..."

    local asm_file="$assembly_dir/complete_benchmark.s"

    if [ ! -f "$asm_file" ]; then
        log_warning "No assembly file found for SIMD analysis: $asm_file"
        echo '{"error": "No assembly file available", "simd_detected": false}' > "$output_file"
        return 1
    fi

    # SIMD patterns to search for
    local simd_patterns=(
        "xmm" "ymm" "zmm"
        "movdqa" "vmovdqa" "movaps" "vmovaps"
        "paddb" "vpaddb" "paddw" "vpaddw" "paddd" "vpaddd" "paddq" "vpaddq"
        "psubb" "vpsubb" "psubw" "vpsubw" "psubd" "vpsubd" "psubq" "vpsubq"
        "pmullw" "vpmullw" "pmulld" "vpmulld"
        "pand" "vpand" "por" "vpor" "pxor" "vpxor"
        "pavgb" "vpavgb" "pavgw" "vpavgw"
        "pcmpgtb" "vpcmpgtb" "pcmpgtw" "vpcmpgtw" "pcmpgtd" "vpcmpgtd" "pcmpgtq" "vpcmpgtq"
        "pshufb" "vpshufb"
        "pslldq" "vpslldq" "psllw" "vpsllw" "pslld" "vpslld" "psllq" "vpsllq"
        "psrldq" "vpsrldq" "psrlw" "vpsrlw" "psrld" "vpsrld" "psrlq" "vpsrlq"
    )

    local grep_pattern=$(IFS="|"; echo "${simd_patterns[*]}")
    local simd_detected=false
    local detected_instructions=()

    if grep -Eiq "$grep_pattern" "$asm_file"; then
        simd_detected=true

        # Collect specific instructions found
        for pattern in "${simd_patterns[@]}"; do
            if grep -Eiq "$pattern" "$asm_file"; then
                detected_instructions+=("$pattern")
            fi
        done
    fi

    # Generate JSON output
    cat > "$output_file" << EOF
{
  "analysis_time": "$(date -Iseconds)",
  "benchmark": "$benchmark_name",
  "target": "$target",
  "simd_detected": $simd_detected,
  "detected_instructions": $(printf '%s\n' "${detected_instructions[@]}" | jq -R . | jq -s .),
  "assembly_file": "$(basename "$asm_file")",
  "analysis_method": "grep_pattern_matching"
}
EOF
}

# Function to copy criterion results
copy_criterion_results() {
    local run_dir="$1"

    log_info "Copying raw Criterion results..."

    local raw_results_dir="$run_dir/raw-results"
    mkdir -p "$raw_results_dir"

    if [ -d "target/criterion" ]; then
        cp -r target/criterion "$raw_results_dir/"
        log_success "Criterion results copied"
    else
        log_warning "No Criterion results found to copy"
    fi
}

# Function to update index
update_index() {
    local run_folder="$1"
    local index_file="$RESULTS_DIR/index.json"

    log_info "Updating index..."

    # Create index if it doesn't exist
    if [ ! -f "$index_file" ]; then
        echo '{"runs": [], "last_updated": ""}' > "$index_file"
    fi

    # Create entry for this run
    local entry=$(cat << EOF
{
  "run_id": "$run_folder",
  "timestamp": "$(date -Iseconds)",
  "hostname": "$(get_hostname)",
  "source_hash": "$(calculate_source_hash)",
  "rustc_version": "$(get_rustc_version)"
}
EOF
)

    # Add entry to index (using jq if available, otherwise append manually)
    if command -v jq >/dev/null 2>&1; then
        local temp_index=$(mktemp)
        jq --argjson entry "$entry" '.runs += [$entry] | .last_updated = "'"$(date -Iseconds)"'"' "$index_file" > "$temp_index"
        mv "$temp_index" "$index_file"
    else
        log_warning "jq not available, index update skipped"
    fi
}

# Function to create schema files
create_schemas() {
    log_info "Creating schema files..."

    mkdir -p "$SCHEMA_DIR"

    # Create README for schema
    cat > "$SCHEMA_DIR/README.md" << 'EOF'
# Results Schema Documentation

This directory contains JSON schema definitions for the benchmark result data structure.

## Files

- `metadata-schema.json` - Schema for metadata files
- `results-schema.json` - Schema for processed benchmark results
- `README.md` - This documentation file

## Usage

These schemas can be used to validate the JSON files generated by the benchmark system.
EOF

    log_success "Schema documentation created"
}

# Main execution function
main() {
    log_info "Starting comprehensive benchmark data collection..."

    # Verify we're in the right directory
    if [ ! -f "Cargo.toml" ] || [ ! -f "src/lib.rs" ]; then
        log_error "Must be run from the root of the benchfind project"
        exit 1
    fi

    # Calculate identifiers
    local hostname=$(get_hostname)
    local source_hash=$(calculate_source_hash)
    local rustc_version=$(get_rustc_version)
    local run_folder="${hostname}_${source_hash}_${rustc_version}"
    local run_dir="$RESULTS_DIR/runs/$run_folder"

    log_info "Run configuration:"
    log_info "  Hostname: $hostname"
    log_info "  Source hash: $source_hash"
    log_info "  Rustc version: $rustc_version"
    log_info "  Run folder: $run_folder"

    # Check if results already exist
    if [ -d "$run_dir" ]; then
        log_success "Results already exist for this configuration: $run_dir"
        log_info "To force re-run, delete the directory: rm -rf '$run_dir'"
        exit 0
    fi

    # Create directory structure
    log_info "Creating directory structure..."
    mkdir -p "$run_dir"/{metadata,raw-results,assembly/{bench_newlines,bench_csv},logs}

    # Create schemas
    create_schemas

    # Collect metadata
    collect_system_info "$run_dir/metadata/system-info.json"
    collect_build_info "$run_dir/metadata/build-info.json"
    collect_source_hashes "$run_dir/metadata/source-hashes.json"
    collect_run_config "$run_dir/metadata/run-config.json"

    # Start logging
    local main_log="$run_dir/logs/benchmark-run.log"
    exec > >(tee -a "$main_log") 2>&1

    log_info "All output is now being logged to: $main_log"

    # Run benchmarks using the existing script
    log_info "Starting benchmark execution..."
    local benchmark_start_time=$(date +%s)

    if ./bench_all.sh 2>&1 | tee -a "$run_dir/logs/benchmark-execution.log"; then
        local benchmark_end_time=$(date +%s)
        local duration=$((benchmark_end_time - benchmark_start_time))
        log_success "Benchmarks completed in ${duration}s"

        # Copy criterion results
        copy_criterion_results "$run_dir"

        # Generate assembly and SIMD analysis for each benchmark/target combination
        local targets=("default" "native" "x86-64-v2" "x86-64-v3" "x86-64-v4")
        local benchmarks=("bench_newlines" "bench_csv")

        for benchmark in "${benchmarks[@]}"; do
            for target in "${targets[@]}"; do
                local assembly_dir="$run_dir/assembly/$benchmark/$target"

                # Only generate assembly if the benchmark actually ran for this target
                if find target/criterion -path "*$target*" -name "estimates.json" 2>/dev/null | grep -q .; then
                    if generate_assembly_for_impl "$benchmark" "$target" "$assembly_dir"; then
                        run_simd_analysis "$benchmark" "$target" "$assembly_dir" "$assembly_dir/simd-analysis.json"
                    fi
                else
                    log_warning "Skipping assembly generation for $benchmark/$target - no benchmark results found"
                fi
            done
        done

        # Update index
        update_index "$run_folder"

        log_success "Comprehensive benchmark data collection completed!"
        log_info "Results stored in: $run_dir"

    else
        log_error "Benchmark execution failed"
        echo "$(date -Iseconds): Benchmark execution failed" >> "$run_dir/logs/errors.log"
        exit 1
    fi
}

# Script entry point
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi
