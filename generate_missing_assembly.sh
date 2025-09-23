#!/bin/bash

# Script to generate missing assembly files for existing benchmark results
# This script can be run to add assembly analysis to previously collected benchmark data

set -euo pipefail

# Color output
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

# Function to map criterion baseline names to actual CPU targets
map_target_name() {
    local baseline_name="$1"
    case "$baseline_name" in
        "default")
            echo "generic"  # Use generic instead of default
            ;;
        *)
            echo "$baseline_name"  # native, x86-64-v2, x86-64-v3, x86-64-v4
            ;;
    esac
}

# Function to generate assembly for a specific implementation
generate_assembly_for_impl() {
    local benchmark_name="$1"
    local baseline_target="$2"
    local output_dir="$3"

    # Map baseline name to actual CPU target
    local cpu_target=$(map_target_name "$baseline_target")

    log_info "Generating assembly for $benchmark_name with baseline $baseline_target (CPU target: $cpu_target)..."

    # Clean previous artifacts to ensure fresh compilation
    rm -rf target/release/deps/${benchmark_name}*
    find target/release/deps/ -name "${benchmark_name}-*" -delete 2>/dev/null || true

    mkdir -p "$output_dir"

    # Compile with assembly output using the mapped CPU target
    local compile_cmd="cargo rustc --bench $benchmark_name --release -- -C target-cpu=$cpu_target --emit asm"

    if $compile_cmd > "$output_dir/compilation.log" 2>&1; then
        # Find the generated assembly file - look for the specific pattern
        local asm_file=$(find target/release/deps/ -name "${benchmark_name}-*.s" -type f 2>/dev/null | head -1)

        if [ -n "$asm_file" ] && [ -f "$asm_file" ]; then
            # Copy the assembly file
            cp "$asm_file" "$output_dir/complete_benchmark.s"

            # Verify it's actually assembly (not a script!)
            if head -1 "$output_dir/complete_benchmark.s" | grep -q "\.file\|\.text\|\.section"; then
                log_success "Assembly generated for $benchmark_name/$baseline_target (CPU: $cpu_target) - $(du -sh "$output_dir/complete_benchmark.s" | cut -f1)"
            else
                log_error "Generated file is not assembly code for $benchmark_name/$baseline_target"
                rm -f "$output_dir/complete_benchmark.s"
                return 1
            fi

            # Clean up the temporary assembly file
            rm -f "$asm_file"
            return 0
        else
            log_warning "No assembly file found for $benchmark_name/$baseline_target"
            return 1
        fi
    else
        log_error "Failed to compile $benchmark_name for target $cpu_target (baseline: $baseline_target)"
        echo "Compilation failed for $benchmark_name/$baseline_target (CPU: $cpu_target)" >> "$output_dir/compilation.log"
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
    local instructions_json="["
    for i in "${!detected_instructions[@]}"; do
        if [ $i -gt 0 ]; then
            instructions_json+=","
        fi
        instructions_json+="\"${detected_instructions[i]}\""
    done
    instructions_json+="]"

    cat > "$output_file" << EOF
{
  "analysis_time": "$(date -Iseconds)",
  "benchmark": "$benchmark_name",
  "target": "$target",
  "simd_detected": $simd_detected,
  "detected_instructions": $instructions_json,
  "assembly_file": "$(basename "$asm_file")",
  "analysis_method": "grep_pattern_matching"
}
EOF
}

# Function to check if a target has benchmark results
has_benchmark_results() {
    local run_dir="$1"
    local target="$2"

    if [ -d "$run_dir/raw-results/criterion" ]; then
        # Look for directories that match the target name exactly
        find "$run_dir/raw-results/criterion" -type d -name "$target" -exec test -f {}/estimates.json \; 2>/dev/null
    else
        return 1
    fi
}

# Function to process a single run directory
process_run_directory() {
    local run_dir="$1"
    local run_name=$(basename "$run_dir")

    log_info "Processing run: $run_name"

    if [ ! -f "$run_dir/metadata/run-config.json" ]; then
        log_warning "Skipping $run_name - no run config found"
        return
    fi

    local targets=("default" "native" "x86-64-v2" "x86-64-v3" "x86-64-v4")
    local benchmarks=("bench_newlines" "bench_csv")

    local generated_count=0
    local failed_count=0
    local skipped_count=0

    for benchmark in "${benchmarks[@]}"; do
        for target in "${targets[@]}"; do
            local assembly_dir="$run_dir/assembly/$benchmark/$target"
            local simd_file="$assembly_dir/simd-analysis.json"

            # Skip if assembly already exists and is valid
            if [ -f "$assembly_dir/complete_benchmark.s" ] && [ -f "$simd_file" ] && [ -s "$assembly_dir/complete_benchmark.s" ]; then
                if head -1 "$assembly_dir/complete_benchmark.s" | grep -q "\.file\|\.text\|\.section"; then
                    log_info "Valid assembly already exists for $benchmark/$target - skipping"
                    ((skipped_count++))
                    continue
                else
                    log_warning "Invalid assembly file found for $benchmark/$target - regenerating"
                    rm -f "$assembly_dir/complete_benchmark.s" "$simd_file"
                fi
            fi

            # Check if we have benchmark results for this target
            if ! has_benchmark_results "$run_dir" "$target"; then
                log_warning "No benchmark results for $benchmark/$target - skipping"
                ((skipped_count++))
                continue
            fi

            # Generate assembly
            if generate_assembly_for_impl "$benchmark" "$target" "$assembly_dir"; then
                # Run SIMD analysis
                if run_simd_analysis "$benchmark" "$target" "$assembly_dir" "$simd_file"; then
                    ((generated_count++))
                    log_success "Completed $benchmark/$target with SIMD analysis"
                else
                    log_warning "SIMD analysis failed for $benchmark/$target"
                    ((generated_count++))  # Still count as generated since assembly worked
                fi
            else
                log_error "Assembly generation failed for $benchmark/$target"
                ((failed_count++))
            fi
        done
    done

    log_success "Run $run_name completed: $generated_count generated, $skipped_count skipped, $failed_count failed"
}

# Main execution function
main() {
    local target_run=""

    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --run)
                target_run="$2"
                shift 2
                ;;
            --help|-h)
                echo "Usage: $0 [--run RUN_NAME]"
                echo ""
                echo "Generate missing assembly files for existing benchmark results."
                echo ""
                echo "Options:"
                echo "  --run RUN_NAME    Process only the specified run (e.g., hostname_hash_version)"
                echo "  --help, -h        Show this help message"
                echo ""
                echo "Examples:"
                echo "  $0                           # Process all runs"
                echo "  $0 --run myhost_abc123_1_75  # Process specific run"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done

    log_info "Starting assembly generation for existing benchmark results..."

    # Verify we're in the right directory
    if [ ! -f "Cargo.toml" ] || [ ! -f "src/lib.rs" ]; then
        log_error "Must be run from the root of the benchfind project"
        exit 1
    fi

    if [ ! -d "results/runs" ]; then
        log_error "No results/runs directory found - no existing results to process"
        exit 1
    fi

    local total_runs=0
    local processed_runs=0

    # Process runs
    if [ -n "$target_run" ]; then
        # Process specific run
        local run_path="results/runs/$target_run"
        if [ -d "$run_path" ]; then
            process_run_directory "$run_path"
            processed_runs=1
            total_runs=1
        else
            log_error "Run not found: $target_run"
            exit 1
        fi
    else
        # Process all runs
        for run_dir in results/runs/*/; do
            if [ -d "$run_dir" ]; then
                ((total_runs++))
                process_run_directory "$run_dir"
                ((processed_runs++))
            fi
        done
    fi

    echo ""
    log_success "Assembly generation completed!"
    log_info "Processed $processed_runs of $total_runs runs"
    log_info "Assembly files are stored in results/runs/*/assembly/"
}

# Script entry point
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi
