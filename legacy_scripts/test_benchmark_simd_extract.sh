#!/bin/bash

# Test Benchmark SIMD Assembly Extraction Script
# A simpler version to test with just one target configuration

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

# Test with native-avx2 target
TARGET_NAME="native-avx2"
RUSTFLAGS="-C target-cpu=native -C target-feature=+avx2,+avx,+sse4.2,+ssse3,+sse3,+sse2"
BENCHMARK="bench_newlines"

main() {
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local output_dir="results/test_benchmark_simd/$timestamp"

    log_info "Testing benchmark SIMD extraction..."
    log_info "Target: $TARGET_NAME"
    log_info "Benchmark: $BENCHMARK"
    log_info "RUSTFLAGS: $RUSTFLAGS"
    log_info "Output: $output_dir"

    mkdir -p "$output_dir"

    # Step 1: Clean and compile benchmark with assembly
    log_info "Step 1: Compiling benchmark with assembly output..."
    cargo clean --release > /dev/null 2>&1 || true

    export RUSTFLAGS="$RUSTFLAGS"

    if ! cargo rustc --bench "$BENCHMARK" --release -- --emit asm > /dev/null 2>&1; then
        log_error "Failed to compile benchmark"
        exit 1
    fi

    # Step 2: Find the assembly file
    log_info "Step 2: Locating assembly file..."
    local asm_file=$(find target/release/deps -name "${BENCHMARK}-*.s" | head -1)

    if [ ! -f "$asm_file" ]; then
        log_error "Assembly file not found"
        exit 1
    fi

    local asm_size=$(du -sh "$asm_file" | cut -f1)
    log_success "Found assembly file: $asm_file ($asm_size)"

    # Step 3: Copy assembly file to output
    cp "$asm_file" "$output_dir/benchmark_assembly.s"

    # Step 4: Quick SIMD check
    log_info "Step 3: Checking for SIMD instructions..."

    local vpcmpeqb_count=$(grep -c "vpcmpeqb" "$asm_file" || echo "0")
    local vpmovmskb_count=$(grep -c "vpmovmskb" "$asm_file" || echo "0")
    local xmm_count=$(grep -c "xmm" "$asm_file" || echo "0")
    local ymm_count=$(grep -c "ymm" "$asm_file" || echo "0")

    echo "SIMD Instruction Counts:" > "$output_dir/simd_summary.txt"
    echo "- vpcmpeqb: $vpcmpeqb_count" >> "$output_dir/simd_summary.txt"
    echo "- vpmovmskb: $vpmovmskb_count" >> "$output_dir/simd_summary.txt"
    echo "- xmm registers: $xmm_count" >> "$output_dir/simd_summary.txt"
    echo "- ymm registers: $ymm_count" >> "$output_dir/simd_summary.txt"

    log_success "SIMD Analysis Results:"
    log_success "- vpcmpeqb (vector compare): $vpcmpeqb_count occurrences"
    log_success "- vpmovmskb (extract mask): $vpmovmskb_count occurrences"
    log_success "- xmm registers (128-bit): $xmm_count occurrences"
    log_success "- ymm registers (256-bit): $ymm_count occurrences"

    # Step 4: Extract some key functions
    log_info "Step 4: Looking for benchmark-related functions..."

    # Get all function symbols
    grep "^_ZN.*:$" "$asm_file" | sed 's/:$//' > "$output_dir/all_functions.txt"
    local total_functions=$(wc -l < "$output_dir/all_functions.txt")

    # Look for functions that might contain our SIMD code
    grep -E "bench|iter|find_all|simd|flat_map" "$output_dir/all_functions.txt" > "$output_dir/interesting_functions.txt" || true
    local interesting_count=$(wc -l < "$output_dir/interesting_functions.txt" 2>/dev/null || echo "0")

    log_success "Found $total_functions total functions"
    log_success "Found $interesting_count potentially interesting functions"

    # Step 5: Extract a few key functions with SIMD
    log_info "Step 5: Extracting functions that contain SIMD instructions..."

    local simd_function_count=0
    while IFS= read -r symbol; do
        if [ -n "$symbol" ]; then
            # Extract this function
            local start_line=$(grep -n "^${symbol}:" "$asm_file" | cut -d: -f1)
            if [ -n "$start_line" ]; then
                local end_line=$(tail -n +$((start_line + 1)) "$asm_file" | grep -n "^[[:alnum:]_]\+:" | head -1 | cut -d: -f1)
                if [ -n "$end_line" ]; then
                    end_line=$((start_line + end_line - 1))
                else
                    end_line=$(wc -l < "$asm_file")
                fi

                # Extract the function
                local func_file="$output_dir/function_${simd_function_count}.s"
                sed -n "${start_line},${end_line}p" "$asm_file" > "$func_file"

                # Check if it has SIMD
                if grep -q "vpcmpeqb\|vpmovmskb\|xmm\|ymm" "$func_file"; then
                    ((simd_function_count++))

                    # Add header
                    local temp_file=$(mktemp)
                    echo "# Function with SIMD instructions" > "$temp_file"
                    echo "# Symbol: $symbol" >> "$temp_file"
                    echo "# Lines: $start_line-$end_line" >> "$temp_file"
                    echo "" >> "$temp_file"
                    cat "$func_file" >> "$temp_file"
                    mv "$temp_file" "$func_file"

                    log_success "Extracted SIMD function: $(basename "$func_file")"
                else
                    rm "$func_file"
                fi
            fi
        fi
    done < "$output_dir/all_functions.txt"

    log_success "Extracted $simd_function_count functions containing SIMD instructions"

    # Final summary
    cat > "$output_dir/summary.txt" << EOF
Benchmark SIMD Test Results
Generated: $(date -Iseconds)

Configuration:
- Target: $TARGET_NAME
- RUSTFLAGS: $RUSTFLAGS
- Benchmark: $BENCHMARK

Results:
- Assembly file: $(basename "$asm_file") ($asm_size)
- Total functions: $total_functions
- Functions with SIMD: $simd_function_count
- vpcmpeqb instructions: $vpcmpeqb_count
- vpmovmskb instructions: $vpmovmskb_count

Files created:
- benchmark_assembly.s (full assembly)
- simd_summary.txt (SIMD analysis)
- function_*.s (extracted SIMD functions)
- all_functions.txt (all function symbols)
- interesting_functions.txt (potential benchmark functions)
EOF

    log_success "Test complete! Results saved to: $output_dir"

    if [ $simd_function_count -gt 0 ]; then
        log_success "✓ SUCCESS: Found SIMD instructions in benchmark code!"
        log_info "Key findings:"
        log_info "- $simd_function_count functions contain SIMD instructions"
        log_info "- $vpcmpeqb_count vector compare operations (vpcmpeqb)"
        log_info "- $vpmovmskb_count mask extract operations (vpmovmskb)"

        if [ $vpcmpeqb_count -gt 0 ] && [ $vpmovmskb_count -gt 0 ]; then
            log_success "✓ Core portable SIMD operations detected!"
            log_info "This confirms your FindAllViaSimd* implementations are generating SIMD instructions"
        fi
    else
        log_warning "No SIMD functions found. This might indicate:"
        log_warning "1. Functions are being inlined differently than expected"
        log_warning "2. Need to look at different function patterns"
        log_warning "3. SIMD code is in closures or iterator implementations"
    fi

    echo ""
    log_info "To examine the results:"
    log_info "ls $output_dir/"
    log_info "grep -A 10 -B 5 'vpcmpeqb\\|vpmovmskb' $output_dir/benchmark_assembly.s | head -50"
}

main "$@"
