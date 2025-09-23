#!/bin/bash

# Extract Benchmark SIMD Assembly Script
# This script compiles the benchmarks for each target configuration and extracts
# the actual benchmark loop functions where SIMD operations occur when iterators
# are consumed, rather than just the iterator setup code.

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

# Target configurations matching bench_all.sh
declare -A TARGET_CONFIGS=(
    ["default"]=""
    ["native"]="-C target-cpu=native"
    ["native-sse2"]="-C target-cpu=native -C target-feature=+sse2"
    ["native-sse4"]="-C target-cpu=native -C target-feature=+sse4.2,+ssse3,+sse3,+sse2"
    ["native-avx"]="-C target-cpu=native -C target-feature=+avx,+sse4.2,+ssse3,+sse3,+sse2"
    ["native-avx2"]="-C target-cpu=native -C target-feature=+avx2,+avx,+sse4.2,+ssse3,+sse3,+sse2"
    ["native-avx512"]="-C target-cpu=native -C target-feature=+avx512f,+avx512bw,+avx2,+avx,+sse4.2,+ssse3,+sse3,+sse2"
)

# Benchmark names
BENCHMARKS=("bench_newlines" "bench_csv")

# Function to extract a specific function from assembly file
extract_function() {
    local asm_file="$1"
    local symbol="$2"
    local output_file="$3"

    # Find the start line of the function
    local start_line=$(grep -n "^${symbol}:" "$asm_file" | cut -d: -f1)

    if [ -z "$start_line" ]; then
        return 1
    fi

    # Find the end line (next function or end of file)
    local end_line=$(tail -n +$((start_line + 1)) "$asm_file" | grep -n "^[[:alnum:]_]\+:" | head -1 | cut -d: -f1)

    if [ -n "$end_line" ]; then
        end_line=$((start_line + end_line - 1))
    else
        end_line=$(wc -l < "$asm_file")
    fi

    # Extract the function
    sed -n "${start_line},${end_line}p" "$asm_file" > "$output_file"

    return 0
}

# Function to compile benchmark and extract assembly
compile_benchmark_with_assembly() {
    local benchmark_name="$1"
    local target_name="$2"
    local rustflags="$3"
    local output_dir="$4"

    log_info "Compiling benchmark $benchmark_name for target $target_name..."

    # Clean previous artifacts
    cargo clean --release > /dev/null 2>&1 || true

    # Set RUSTFLAGS if provided
    local compile_env=""
    if [ -n "$rustflags" ]; then
        export RUSTFLAGS="$rustflags"
        compile_env="RUSTFLAGS='$rustflags'"
    else
        unset RUSTFLAGS 2>/dev/null || true
    fi

    # Compile benchmark with assembly output
    local compile_cmd="cargo rustc --bench $benchmark_name --release -- --emit asm"

    if ! eval $compile_cmd > /dev/null 2>&1; then
        log_error "Failed to compile $benchmark_name for $target_name"
        return 1
    fi

    # Find the generated assembly file
    local asm_file=$(find target/release/deps -name "${benchmark_name}-*.s" | head -1)

    if [ ! -f "$asm_file" ]; then
        log_error "Assembly file not found for $benchmark_name"
        return 1
    fi

    local asm_size=$(du -sh "$asm_file" | cut -f1)
    log_success "Compilation successful for $benchmark_name ($asm_size assembly)"

    echo "$asm_file"

    # Clean up environment
    unset RUSTFLAGS 2>/dev/null || true
}

# Function to extract benchmark functions
extract_benchmark_functions() {
    local asm_file="$1"
    local benchmark_name="$2"
    local target_name="$3"
    local output_dir="$4"

    log_info "Extracting benchmark functions for $benchmark_name on $target_name..."

    # Create output directory
    mkdir -p "$output_dir"

    # Find benchmark-related function symbols
    # Look for closures in bench_with_finder and bench_lines_with_finder
    local function_patterns=(
        "bench_with_finder.*closure"
        "bench_lines_with_finder.*closure"
        "bench_large_texts"
        "bench_lines_iterators"
        "find_all.*Iterator.*next"
        "flat_map.*closure"
        "BitmaskIterator.*next"
        # Look for specific FindAll implementation calls
        "FindAllViaSimd16.*find_all"
        "FindAllViaSimd32.*find_all"
        "FindAllViaSimd64.*find_all"
        # Look for SIMD-related iterator implementations
        "as_simd.*Iterator"
        "simd_eq"
        "to_bitmask"
    )

    local extracted_count=0
    local function_summary="$output_dir/benchmark_functions_summary.txt"

    cat > "$function_summary" << EOF
Benchmark SIMD Assembly Extract - Target: $target_name, Benchmark: $benchmark_name
Generated: $(date -Iseconds)
Source Assembly: $(basename "$asm_file")

Functions Extracted:
EOF

    # Get all function symbols from the assembly
    local all_symbols=$(grep "^_ZN.*:$" "$asm_file" | sed 's/:$//' | sort | uniq)

    # Extract functions matching our patterns
    while IFS= read -r symbol; do
        local should_extract=false
        local function_type="unknown"

        # Check if this symbol matches any of our patterns
        for pattern in "${function_patterns[@]}"; do
            if echo "$symbol" | grep -Eq "$pattern"; then
                should_extract=true
                function_type="$pattern"
                break
            fi
        done

        # Also extract any function that contains benchmark-related terms
        if echo "$symbol" | grep -Eq "bench.*finder|criterion.*iter|black_box"; then
            should_extract=true
            function_type="benchmark_related"
        fi

        if [ "$should_extract" = true ]; then
            # Demangle the symbol to get readable name
            local demangled_name=""
            if command -v rustfilt >/dev/null 2>&1; then
                demangled_name=$(echo "$symbol" | rustfilt 2>/dev/null || echo "$symbol")
            else
                demangled_name="$symbol"
            fi

            # Create a safe filename
            local safe_name=$(echo "$function_type" | sed 's/[^a-zA-Z0-9_]/_/g')
            local output_file="$output_dir/${safe_name}_${extracted_count}.s"

            if extract_function "$asm_file" "$symbol" "$output_file"; then
                ((extracted_count++))

                # Add to summary
                echo "- Function $extracted_count: $output_file" >> "$function_summary"
                echo "  Type: $function_type" >> "$function_summary"
                echo "  Symbol: $symbol" >> "$function_summary"
                echo "  Demangled: $demangled_name" >> "$function_summary"
                echo "  Size: $(wc -l < "$output_file") lines, $(du -sh "$output_file" | cut -f1)" >> "$function_summary"
                echo "" >> "$function_summary"

                # Add header to assembly file
                local temp_file=$(mktemp)
                cat > "$temp_file" << EOF
# Benchmark Function: $function_type
# Benchmark: $benchmark_name
# Target: $target_name
# Symbol: $symbol
# Demangled: $demangled_name
# Extracted: $(date -Iseconds)

EOF
                cat "$output_file" >> "$temp_file"
                mv "$temp_file" "$output_file"
            fi
        fi
    done <<< "$all_symbols"

    # Also extract the main benchmark functions directly
    local main_benchmark_symbols=$(echo "$all_symbols" | grep -E "bench_large_texts|bench_lines_iterators")

    while IFS= read -r symbol; do
        if [ -n "$symbol" ]; then
            local demangled_name=""
            if command -v rustfilt >/dev/null 2>&1; then
                demangled_name=$(echo "$symbol" | rustfilt 2>/dev/null || echo "$symbol")
            else
                demangled_name="$symbol"
            fi

            local output_file="$output_dir/main_benchmark_${extracted_count}.s"

            if extract_function "$asm_file" "$symbol" "$output_file"; then
                ((extracted_count++))

                echo "- Main Benchmark Function: $output_file" >> "$function_summary"
                echo "  Symbol: $symbol" >> "$function_summary"
                echo "  Demangled: $demangled_name" >> "$function_summary"
                echo "  Size: $(wc -l < "$output_file") lines, $(du -sh "$output_file" | cut -f1)" >> "$function_summary"
                echo "" >> "$function_summary"

                # Add header
                local temp_file=$(mktemp)
                cat > "$temp_file" << EOF
# Main Benchmark Function
# Benchmark: $benchmark_name
# Target: $target_name
# Symbol: $symbol
# Demangled: $demangled_name
# Extracted: $(date -Iseconds)

EOF
                cat "$output_file" >> "$temp_file"
                mv "$temp_file" "$output_file"
            fi
        fi
    done <<< "$main_benchmark_symbols"

    echo "Total functions extracted: $extracted_count" >> "$function_summary"

    if [ $extracted_count -gt 0 ]; then
        log_success "Extracted $extracted_count benchmark functions for $benchmark_name on $target_name"
        return 0
    else
        log_warning "No benchmark functions found for $benchmark_name on $target_name"
        return 1
    fi
}

# Function to run SIMD analysis on extracted functions
analyze_simd_in_benchmark_functions() {
    local functions_dir="$1"
    local benchmark_name="$2"
    local target_name="$3"

    log_info "Running SIMD analysis on benchmark functions for $benchmark_name on $target_name..."

    # Comprehensive SIMD patterns including the ones we actually generate
    local simd_patterns=(
        # Vector registers
        "xmm" "ymm" "zmm"
        # Vector compare instructions (key ones our code generates)
        "vpcmpeqb" "vpcmpeqw" "vpcmpeqd" "vpcmpeqq"
        "pcmpeqb" "pcmpeqw" "pcmpeqd" "pcmpeqq"
        # Vector mask operations (key ones our code generates)
        "vpmovmskb" "pmovmskb"
        # Vector moves
        "movdqa" "vmovdqa" "movaps" "vmovaps" "movdqu" "vmovdqu"
        # Vector arithmetic
        "paddb" "vpaddb" "paddw" "vpaddw" "paddd" "vpaddd" "paddq" "vpaddq"
        "psubb" "vpsubb" "psubw" "vpsubw" "psubd" "vpsubd" "psubq" "vpsubq"
        # Vector logical
        "pand" "vpand" "por" "vpor" "pxor" "vpxor"
        # Vector shifts
        "pslldq" "vpslldq" "psllw" "vpsllw" "pslld" "vpslld" "psllq" "vpsllq"
        "psrldq" "vpsrldq" "psrlw" "vpsrlw" "psrld" "vpsrld" "psrlq" "vpsrlq"
        # Vector shuffle/broadcast
        "pshufb" "vpshufb" "vpbroadcastb" "vpbroadcastw" "vpbroadcastd"
        # AVX2/AVX512 specific
        "vzeroupper" "vzeroall"
    )

    local grep_pattern=$(IFS="|"; echo "${simd_patterns[*]}")
    local analysis_file="$functions_dir/simd_analysis.json"
    local analysis_summary="$functions_dir/simd_summary.txt"

    cat > "$analysis_summary" << EOF
SIMD Analysis Summary - Benchmark: $benchmark_name, Target: $target_name
Generated: $(date -Iseconds)

Function-by-Function SIMD Detection:
EOF

    local total_functions=0
    local simd_functions=0

    # Analyze each extracted function
    for asm_file in "$functions_dir"/*.s; do
        if [ ! -f "$asm_file" ] || [[ "$(basename "$asm_file")" == "*.s" ]]; then
            continue
        fi

        ((total_functions++))

        local function_name=$(basename "$asm_file" .s)
        local simd_detected=false
        local detected_instructions=()

        # Check for SIMD instructions
        if grep -Eiq "$grep_pattern" "$asm_file"; then
            simd_detected=true
            ((simd_functions++))

            # Collect specific instructions found
            for pattern in "${simd_patterns[@]}"; do
                if grep -Eiq "\\b$pattern\\b" "$asm_file"; then
                    detected_instructions+=("$pattern")
                fi
            done
        fi

        # Add to summary
        echo "- $function_name: $([ "$simd_detected" = true ] && echo "✓ SIMD DETECTED" || echo "✗ No SIMD")" >> "$analysis_summary"

        if [ "$simd_detected" = true ]; then
            echo "  Instructions found: ${detected_instructions[*]}" >> "$analysis_summary"

            # Count occurrences of key instructions
            local vpcmpeqb_count=$(grep -Eic "\\bvpcmpeqb\\b" "$asm_file" || echo "0")
            local vpmovmskb_count=$(grep -Eic "\\bvpmovmskb\\b" "$asm_file" || echo "0")

            if [ "$vpcmpeqb_count" -gt 0 ] || [ "$vpmovmskb_count" -gt 0 ]; then
                echo "  Core SIMD operations: vpcmpeqb($vpcmpeqb_count), vpmovmskb($vpmovmskb_count)" >> "$analysis_summary"
            fi
        fi
        echo "" >> "$analysis_summary"
    done

    cat >> "$analysis_summary" << EOF

SUMMARY:
- Total functions analyzed: $total_functions
- Functions with SIMD instructions: $simd_functions
- SIMD detection rate: $([ $total_functions -gt 0 ] && echo "scale=1; $simd_functions * 100 / $total_functions" | bc -l || echo "0")%

Key findings:
$([ $simd_functions -gt 0 ] && echo "✓ SIMD instructions detected in benchmark code" || echo "✗ No SIMD instructions found")
$(grep -l "vpcmpeqb\|vpmovmskb" "$functions_dir"/*.s 2>/dev/null | wc -l | xargs -I {} echo "- {} functions contain core portable SIMD operations")
EOF

    log_success "SIMD analysis complete: $simd_functions/$total_functions functions contain SIMD instructions"
    return 0
}

# Main execution
main() {
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local base_output_dir="results/benchmark_simd_extracts/$timestamp"

    log_info "Starting benchmark SIMD assembly extraction..."
    log_info "Output directory: $base_output_dir"

    # Ensure output directory exists
    mkdir -p "$base_output_dir"

    local total_processed=0
    local total_successful=0

    # Process each target configuration
    for target_name in "${!TARGET_CONFIGS[@]}"; do
        local rustflags="${TARGET_CONFIGS[$target_name]}"
        local target_output_dir="$base_output_dir/$target_name"

        log_info "Processing target: $target_name"
        if [ -n "$rustflags" ]; then
            log_info "Using RUSTFLAGS: $rustflags"
        fi

        mkdir -p "$target_output_dir"

        # Process each benchmark
        for benchmark_name in "${BENCHMARKS[@]}"; do
            ((total_processed++))

            local benchmark_output_dir="$target_output_dir/$benchmark_name"
            mkdir -p "$benchmark_output_dir"

            log_info "Compiling and extracting: $benchmark_name for $target_name"

            # Compile benchmark with assembly output
            local asm_file=$(compile_benchmark_with_assembly "$benchmark_name" "$target_name" "$rustflags" "$benchmark_output_dir")

            if [ $? -eq 0 ] && [ -f "$asm_file" ]; then
                # Extract benchmark functions
                if extract_benchmark_functions "$asm_file" "$benchmark_name" "$target_name" "$benchmark_output_dir"; then
                    # Run SIMD analysis
                    analyze_simd_in_benchmark_functions "$benchmark_output_dir" "$benchmark_name" "$target_name"
                    ((total_successful++))
                    log_success "Successfully processed $benchmark_name for $target_name"
                else
                    log_warning "Failed to extract functions for $benchmark_name on $target_name"
                fi
            else
                log_error "Failed to compile $benchmark_name for $target_name"
            fi

            echo ""
        done
    done

    # Final summary
    cat > "$base_output_dir/extraction_summary.txt" << EOF
Benchmark SIMD Assembly Extraction Summary
Generated: $(date -Iseconds)

Configuration:
- Targets processed: ${#TARGET_CONFIGS[@]}
- Benchmarks per target: ${#BENCHMARKS[@]}
- Total combinations: $total_processed
- Successful extractions: $total_successful

Results available in: $base_output_dir

To view SIMD analysis for a specific target/benchmark:
cat $base_output_dir/<target>/<benchmark>/simd_summary.txt

To view extracted assembly:
ls $base_output_dir/<target>/<benchmark>/*.s
EOF

    log_success "Benchmark SIMD extraction complete!"
    log_success "Processed $total_successful/$total_processed target/benchmark combinations"
    log_success "Results in: $base_output_dir"

    if [ $total_successful -gt 0 ]; then
        echo ""
        log_info "Quick check - searching for SIMD instructions across all extracts:"
        local simd_files=$(find "$base_output_dir" -name "*.s" -exec grep -l "vpcmpeqb\|vpmovmskb" {} \; | wc -l)
        log_info "Found $simd_files files containing core SIMD instructions (vpcmpeqb/vpmovmskb)"

        if [ $simd_files -gt 0 ]; then
            echo ""
            log_success "✓ SIMD instructions successfully detected in benchmark assembly!"
            log_info "Example files with SIMD:"
            find "$base_output_dir" -name "*.s" -exec grep -l "vpcmpeqb\|vpmovmskb" {} \; | head -3 | while read file; do
                echo "  - $file"
            done
        else
            log_warning "No core SIMD instructions found. This might indicate:"
            log_warning "1. Functions are being optimized away or inlined differently"
            log_warning "2. Target CPU doesn't support the expected SIMD features"
            log_warning "3. Different instruction patterns are being generated"
        fi
    fi
}

# Run main function
main "$@"
