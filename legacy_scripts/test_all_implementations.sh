#!/bin/bash

# Test All Implementations Assembly Extraction Script
# Tests extraction for all implementations on a single target to validate approach

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

# Test configuration
TARGET_NAME="native-avx2"
RUSTFLAGS="-C target-cpu=native -C target-feature=+avx2,+avx,+sse4.2,+ssse3,+sse3,+sse2"
BENCHMARK="bench_newlines"

# FindNeedleInHaystack implementations to track
declare -a IMPLEMENTATIONS=(
    "FindAllIterating"
    "FindAllMemchrCrate"
    "FindAllViaU16"
    "FindAllViaU32"
    "FindAllViaU64"
    "FindAllViaSimd16"
    "FindAllViaSimd32"
    "FindAllViaSimd64"
)

main() {
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local output_dir="results/test_all_implementations/$timestamp"

    log_info "Testing all implementations assembly extraction..."
    log_info "Target: $TARGET_NAME"
    log_info "Benchmark: $BENCHMARK"
    log_info "Output: $output_dir"

    mkdir -p "$output_dir"

    # Step 1: Compile benchmark
    log_info "Step 1: Compiling benchmark with assembly output..."
    cargo clean --release > /dev/null 2>&1 || true

    export RUSTFLAGS="$RUSTFLAGS"

    if ! cargo rustc --bench "$BENCHMARK" --release -- --emit asm > /dev/null 2>&1; then
        log_error "Failed to compile benchmark"
        exit 1
    fi

    # Step 2: Find assembly file
    local asm_file=$(find target/release/deps -name "${BENCHMARK}-*.s" | head -1)
    if [ ! -f "$asm_file" ]; then
        log_error "Assembly file not found"
        exit 1
    fi

    local asm_size=$(du -sh "$asm_file" | cut -f1)
    log_success "Assembly file: $asm_file ($asm_size)"

    # Step 3: Copy full assembly
    cp "$asm_file" "$output_dir/full_assembly.s"

    # Step 4: Find all function symbols
    log_info "Step 2: Analyzing function symbols..."
    grep "^_ZN.*:$" "$asm_file" | sed 's/:$//' > "$output_dir/all_symbols.txt"
    local total_symbols=$(wc -l < "$output_dir/all_symbols.txt")
    log_success "Found $total_symbols function symbols"

    # Step 5: Extract benchmark-related functions
    log_info "Step 3: Extracting benchmark functions..."

    # Look for criterion benchmark functions and anything that might contain our logic
    grep -E "criterion.*iter|bench.*finder|find_all|Iterator.*next" "$output_dir/all_symbols.txt" > "$output_dir/benchmark_symbols.txt" || true
    local benchmark_symbols=$(wc -l < "$output_dir/benchmark_symbols.txt" 2>/dev/null || echo "0")
    log_success "Found $benchmark_symbols benchmark-related symbols"

    # Step 6: Create implementation directories and extract functions
    log_info "Step 4: Organizing by implementation..."

    for impl in "${IMPLEMENTATIONS[@]}"; do
        mkdir -p "$output_dir/$impl"
    done
    mkdir -p "$output_dir/general"

    # Extract a few key functions that contain our implementation logic
    local extracted_functions=0

    # Function to extract a single function
    extract_function() {
        local symbol="$1"
        local target_dir="$2"
        local func_num="$3"

        local start_line=$(grep -n "^${symbol}:" "$asm_file" | cut -d: -f1)
        if [ -n "$start_line" ]; then
            local end_line=$(tail -n +$((start_line + 1)) "$asm_file" | grep -n "^[[:alnum:]_]\+:" | head -1 | cut -d: -f1)
            if [ -n "$end_line" ]; then
                end_line=$((start_line + end_line - 1))
            else
                end_line=$(wc -l < "$asm_file")
            fi

            local output_file="$target_dir/function_${func_num}.s"

            # Add header and extract
            cat > "$output_file" << EOF
# Function: $symbol
# Lines: $start_line-$end_line
# Implementation context: $(echo "$symbol" | grep -oE "FindAll[A-Za-z0-9]+" || echo "Unknown")
# Extracted: $(date -Iseconds)

EOF
            sed -n "${start_line},${end_line}p" "$asm_file" >> "$output_file"

            return 0
        else
            return 1
        fi
    }

    # Process all benchmark symbols and try to categorize them
    local func_counter=0
    while IFS= read -r symbol; do
        if [ -n "$symbol" ]; then
            # Try to determine which implementation this relates to
            local target_impl=""

            for impl in "${IMPLEMENTATIONS[@]}"; do
                if echo "$symbol" | grep -q "$impl"; then
                    target_impl="$impl"
                    break
                fi
            done

            # If no specific implementation found, put in general
            if [ -z "$target_impl" ]; then
                target_impl="general"
            fi

            if extract_function "$symbol" "$output_dir/$target_impl" "$func_counter"; then
                ((extracted_functions++))
                ((func_counter++))
            fi
        fi
    done < "$output_dir/benchmark_symbols.txt"

    # Also extract some main criterion functions that contain the actual benchmark loops
    log_info "Step 5: Looking for main benchmark execution functions..."

    # Look for the main iter functions where actual work happens
    local main_bench_symbols=$(grep "criterion.*bencher.*iter\|Bencher.*iter" "$output_dir/all_symbols.txt" | head -5)

    while IFS= read -r symbol; do
        if [ -n "$symbol" ]; then
            if extract_function "$symbol" "$output_dir/general" "$func_counter"; then
                ((extracted_functions++))
                ((func_counter++))
            fi
        fi
    done <<< "$main_bench_symbols"

    log_success "Extracted $extracted_functions functions total"

    # Step 7: Analyze each implementation
    log_info "Step 6: Analyzing implementations for vectorization..."

    local analysis_file="$output_dir/implementation_analysis.txt"
    cat > "$analysis_file" << EOF
Implementation Analysis Report
Target: $TARGET_NAME
Benchmark: $BENCHMARK
Generated: $(date -Iseconds)

Per-Implementation Analysis:
============================

EOF

    local implementations_found=0
    local vectorized_implementations=0

    for impl in "${IMPLEMENTATIONS[@]}" "general"; do
        local impl_dir="$output_dir/$impl"
        local function_count=$(ls "$impl_dir"/*.s 2>/dev/null | wc -l || echo "0")

        echo "Implementation: $impl" >> "$analysis_file"
        echo "Functions extracted: $function_count" >> "$analysis_file"

        if [ $function_count -gt 0 ]; then
            ((implementations_found++))

            # Check for vectorization indicators
            local has_vector=false
            local vector_details=""

            # SIMD register usage
            local xmm_count=$(grep -Eich "\\bxmm[0-9]" "$impl_dir"/*.s 2>/dev/null || echo "0")
            local ymm_count=$(grep -Eich "\\bymm[0-9]" "$impl_dir"/*.s 2>/dev/null || echo "0")

            # Core SIMD instructions our code should generate
            local vpcmpeqb_count=$(grep -Eich "\\bvpcmpeqb\\b" "$impl_dir"/*.s 2>/dev/null || echo "0")
            local vpmovmskb_count=$(grep -Eich "\\bvpmovmskb\\b" "$impl_dir"/*.s 2>/dev/null || echo "0")

            # Other vectorization
            local vmovdqu_count=$(grep -Eich "\\bvmovdqu\\b" "$impl_dir"/*.s 2>/dev/null || echo "0")
            local rep_count=$(grep -Eich "\\brep\\b" "$impl_dir"/*.s 2>/dev/null || echo "0")

            if [ $xmm_count -gt 0 ] || [ $ymm_count -gt 0 ] || [ $vpcmpeqb_count -gt 0 ] || [ $vmovdqu_count -gt 0 ]; then
                has_vector=true
                ((vectorized_implementations++))
                vector_details="xmm:$xmm_count, ymm:$ymm_count, vpcmpeqb:$vpcmpeqb_count, vpmovmskb:$vpmovmskb_count, vmovdqu:$vmovdqu_count"
            fi

            if [ "$has_vector" = true ]; then
                echo "✓ VECTORIZATION DETECTED" >> "$analysis_file"
                echo "  Details: $vector_details" >> "$analysis_file"

                # Special analysis for expected SIMD implementations
                if [[ "$impl" == *"Simd"* ]]; then
                    if [ $vpcmpeqb_count -gt 0 ] && [ $vpmovmskb_count -gt 0 ]; then
                        echo "  ✓ Expected portable SIMD operations present" >> "$analysis_file"
                    else
                        echo "  ⚠ Portable SIMD implementation but core ops not detected" >> "$analysis_file"
                    fi
                elif [[ "$impl" == "FindAllMemchrCrate" ]]; then
                    echo "  ✓ Expected vectorization in optimized memchr library" >> "$analysis_file"
                else
                    echo "  ⚠ Unexpected vectorization (compiler auto-vectorization?)" >> "$analysis_file"
                fi
            else
                echo "✗ No vectorization detected" >> "$analysis_file"

                if [ $rep_count -gt 0 ]; then
                    echo "  - Uses string operations (rep): $rep_count" >> "$analysis_file"
                else
                    echo "  - Basic scalar implementation" >> "$analysis_file"
                fi
            fi

            # Function size analysis
            local avg_lines=$(find "$impl_dir" -name "*.s" -exec wc -l {} \; 2>/dev/null | awk '{sum+=$1; count++} END {if(count>0) print int(sum/count); else print 0}')
            echo "Average function size: $avg_lines lines" >> "$analysis_file"

        else
            echo "No functions extracted" >> "$analysis_file"
        fi

        echo "" >> "$analysis_file"
    done

    # Overall summary
    cat >> "$analysis_file" << EOF
Summary:
========
Total implementations with functions: $implementations_found
Implementations showing vectorization: $vectorized_implementations
Vectorization rate: $([ $implementations_found -gt 0 ] && echo "scale=1; $vectorized_implementations * 100 / $implementations_found" | bc -l 2>/dev/null || echo "0")%

Expected Results:
- FindAllIterating: Should be scalar (basic byte-by-byte iteration)
- FindAllMemchrCrate: Should be vectorized (optimized library)
- FindAllViaU16/U32/U64: May be vectorized depending on compiler optimizations
- FindAllViaSimd16/32/64: Should show explicit SIMD instructions

Quick Verification Commands:
- Check for SIMD in a specific impl: grep -E "xmm|ymm|vpcmpeq" $output_dir/FindAllViaSimd16/*.s
- Compare implementations: ls -la $output_dir/*/
- Find all SIMD usage: grep -r "vpcmpeqb" $output_dir/
EOF

    # Step 8: Generate final summary
    local summary_file="$output_dir/summary.txt"
    cat > "$summary_file" << EOF
Test All Implementations Extraction Results
Target: $TARGET_NAME
Benchmark: $BENCHMARK
Generated: $(date -Iseconds)

Results:
- Total function symbols: $total_symbols
- Benchmark symbols: $benchmark_symbols
- Functions extracted: $extracted_functions
- Implementations with functions: $implementations_found
- Vectorized implementations: $vectorized_implementations

Files Created:
- full_assembly.s (complete assembly, $asm_size)
- all_symbols.txt (all function symbols)
- benchmark_symbols.txt (benchmark-related symbols)
- implementation_analysis.txt (vectorization analysis)
- <implementation>/ directories with function_*.s files

Key Findings:
EOF

    # Add key findings
    for impl in "${IMPLEMENTATIONS[@]}"; do
        local impl_dir="$output_dir/$impl"
        local function_count=$(ls "$impl_dir"/*.s 2>/dev/null | wc -l || echo "0")
        if [ $function_count -gt 0 ]; then
            local has_simd=$(grep -q "vpcmpeqb\|xmm\|ymm" "$impl_dir"/*.s 2>/dev/null && echo "SIMD" || echo "scalar")
            echo "- $impl: $function_count functions, $has_simd" >> "$summary_file"
        fi
    done

    log_success "Test complete!"
    log_success "Results in: $output_dir"

    if [ $implementations_found -gt 0 ]; then
        echo ""
        log_info "Quick Results:"
        log_info "- $implementations_found implementations had extractable functions"
        log_info "- $vectorized_implementations implementations show vectorization"

        # Show some concrete examples
        if [ -f "$output_dir/FindAllViaSimd16/function_0.s" ]; then
            local simd16_has_vpcmpeqb=$(grep -c "vpcmpeqb" "$output_dir/FindAllViaSimd16/function_0.s" 2>/dev/null || echo "0")
            log_info "- FindAllViaSimd16: $simd16_has_vpcmpeqb vpcmpeqb instructions found"
        fi

        if [ -f "$output_dir/FindAllIterating/function_0.s" ]; then
            local iterating_has_vector=$(grep -c "xmm\|ymm" "$output_dir/FindAllIterating/function_0.s" 2>/dev/null || echo "0")
            log_info "- FindAllIterating: $iterating_has_vector vector register uses"
        fi

        echo ""
        log_info "To examine results:"
        log_info "1. View analysis: cat $output_dir/implementation_analysis.txt"
        log_info "2. Compare implementations: ls $output_dir/*/function_*.s"
        log_info "3. Find SIMD usage: grep -r 'vpcmpeqb' $output_dir/"
        log_info "4. Check specific impl: head -50 $output_dir/FindAllViaSimd16/function_0.s"

    else
        log_warning "No implementation functions were successfully extracted."
        log_warning "This might indicate the extraction patterns need adjustment."
    fi
}

main "$@"
