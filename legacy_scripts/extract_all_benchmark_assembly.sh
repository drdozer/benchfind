#!/bin/bash

# Extract All Benchmark Assembly Script
# This script extracts assembly for all FindNeedleInHaystack implementations from benchmark code,
# organized by implementation type to enable performance vs assembly correlation analysis.

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

# FindNeedleInHaystack implementations
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

# Benchmark names
BENCHMARKS=("bench_newlines" "bench_csv")

# Function to extract benchmark functions for a specific implementation
extract_implementation_functions() {
    local asm_file="$1"
    local benchmark_name="$2"
    local target_name="$3"
    local output_dir="$4"

    log_info "Extracting functions for all implementations in $benchmark_name on $target_name..."

    # Create implementation-specific directories
    for impl in "${IMPLEMENTATIONS[@]}"; do
        mkdir -p "$output_dir/$impl"
    done

    # Get all function symbols from the assembly
    local all_symbols=$(grep "^_ZN.*:$" "$asm_file" | sed 's/:$//' | sort | uniq)
    local total_functions=$(echo "$all_symbols" | wc -l)

    log_info "Found $total_functions total functions in assembly"

    # Function patterns that indicate benchmark execution
    local benchmark_patterns=(
        "criterion.*bencher.*iter"
        "bench_with_finder.*closure"
        "bench_lines_with_finder.*closure"
        "bench_large_texts"
        "bench_lines_iterators"
    )

    # Track extraction results
    declare -A implementation_counts
    local total_extracted=0

    # Initialize counters
    for impl in "${IMPLEMENTATIONS[@]}"; do
        implementation_counts[$impl]=0
    done

    # Extract functions for each implementation
    while IFS= read -r symbol; do
        if [ -n "$symbol" ]; then
            # Check if this is a benchmark-related function
            local is_benchmark=false
            for pattern in "${benchmark_patterns[@]}"; do
                if echo "$symbol" | grep -Eq "$pattern"; then
                    is_benchmark=true
                    break
                fi
            done

            # Also include any function that might contain our implementation logic
            if echo "$symbol" | grep -Eq "find_all|Iterator.*next|flat_map.*closure|BitmaskIterator"; then
                is_benchmark=true
            fi

            if [ "$is_benchmark" = true ]; then
                # Try to determine which implementation this function relates to
                local target_impl=""

                # Look for implementation-specific patterns in symbol or nearby context
                for impl in "${IMPLEMENTATIONS[@]}"; do
                    if echo "$symbol" | grep -q "$impl"; then
                        target_impl="$impl"
                        break
                    fi
                done

                # If we can't determine from symbol, extract to a general category
                if [ -z "$target_impl" ]; then
                    target_impl="general"
                    mkdir -p "$output_dir/$target_impl"
                fi

                # Extract the function
                local start_line=$(grep -n "^${symbol}:" "$asm_file" | cut -d: -f1)
                if [ -n "$start_line" ]; then
                    local end_line=$(tail -n +$((start_line + 1)) "$asm_file" | grep -n "^[[:alnum:]_]\+:" | head -1 | cut -d: -f1)
                    if [ -n "$end_line" ]; then
                        end_line=$((start_line + end_line - 1))
                    else
                        end_line=$(wc -l < "$asm_file")
                    fi

                    # Create output file
                    local func_count=${implementation_counts[$target_impl]}
                    local output_file="$output_dir/$target_impl/function_${func_count}.s"

                    # Extract the function
                    sed -n "${start_line},${end_line}p" "$asm_file" > "$output_file"

                    # Add header with metadata
                    local temp_file=$(mktemp)
                    cat > "$temp_file" << EOF
# Benchmark Function Extract
# Implementation: $target_impl
# Benchmark: $benchmark_name
# Target: $target_name
# Symbol: $symbol
# Assembly lines: $start_line-$end_line
# Extracted: $(date -Iseconds)

EOF
                    cat "$output_file" >> "$temp_file"
                    mv "$temp_file" "$output_file"

                    # Update counters
                    ((implementation_counts[$target_impl]++))
                    ((total_extracted++))
                fi
            fi
        fi
    done <<< "$all_symbols"

    # Create summary for this benchmark/target combination
    local summary_file="$output_dir/extraction_summary.txt"
    cat > "$summary_file" << EOF
Benchmark Assembly Extraction Summary
Benchmark: $benchmark_name
Target: $target_name
Generated: $(date -Iseconds)

Total Functions Extracted: $total_extracted

By Implementation:
EOF

    for impl in "${IMPLEMENTATIONS[@]}" "general"; do
        if [ "${implementation_counts[$impl]:-0}" -gt 0 ]; then
            echo "- $impl: ${implementation_counts[$impl]} functions" >> "$summary_file"
        fi
    done

    log_success "Extracted $total_extracted functions across ${#implementation_counts[@]} categories"
    return 0
}

# Function to analyze all implementations for vectorization
analyze_all_implementations() {
    local base_dir="$1"
    local benchmark_name="$2"
    local target_name="$3"

    log_info "Analyzing vectorization across all implementations..."

    # Comprehensive instruction patterns
    local vector_patterns=(
        # SIMD registers
        "xmm" "ymm" "zmm"
        # Vector compare (what portable SIMD generates)
        "vpcmpeqb" "vpcmpeqw" "vpcmpeqd" "vpcmpeqq"
        "pcmpeqb" "pcmpeqw" "pcmpeqd" "pcmpeqq"
        # Vector mask operations
        "vpmovmskb" "pmovmskb"
        # Vector moves
        "vmovdqu" "vmovdqa" "movdqu" "movdqa"
        # Auto-vectorization indicators
        "rep movs" "rep stos"
        # Vector arithmetic
        "vpaddb" "paddb" "vpsubb" "psubb"
        # Vector logical
        "vpand" "pand" "vpor" "por" "vpxor" "pxor"
        # AVX2/AVX512
        "vzeroupper" "vpbroadcast"
    )

    # Scalar optimization patterns
    local scalar_patterns=(
        # Unrolled loops
        "movzbl.*,%e[a-z]x.*movzbl.*,%e[a-z]x.*movzbl.*,%e[a-z]x"
        # 64-bit operations
        "movq" "cmpq" "addq" "subq"
        # 32-bit operations
        "movl" "cmpl" "addl" "subl"
        # Branch patterns
        "jne" "je" "jmp" "cmp"
        # Memory access patterns
        "\\(%r[a-z0-9]+\\)" "\\[%r[a-z0-9]+\\]"
    )

    local analysis_file="$base_dir/vectorization_analysis.txt"

    cat > "$analysis_file" << EOF
Vectorization Analysis Report
Benchmark: $benchmark_name
Target: $target_name
Generated: $(date -Iseconds)

Implementation Analysis:
========================

EOF

    # Analyze each implementation
    for impl in "${IMPLEMENTATIONS[@]}" "general"; do
        local impl_dir="$base_dir/$impl"
        if [ -d "$impl_dir" ]; then
            echo "Implementation: $impl" >> "$analysis_file"
            echo "----------------------------------------" >> "$analysis_file"

            local function_count=$(ls "$impl_dir"/*.s 2>/dev/null | wc -l)
            echo "Functions extracted: $function_count" >> "$analysis_file"

            if [ $function_count -gt 0 ]; then
                # Check for vectorization
                local vector_detected=false
                local vector_instructions=()

                for pattern in "${vector_patterns[@]}"; do
                    local count=$(grep -Eich "\\b$pattern\\b" "$impl_dir"/*.s 2>/dev/null || echo "0")
                    if [ $count -gt 0 ]; then
                        vector_detected=true
                        vector_instructions+=("$pattern: $count")
                    fi
                done

                if [ "$vector_detected" = true ]; then
                    echo "✓ VECTORIZATION DETECTED" >> "$analysis_file"
                    echo "Vector instructions found:" >> "$analysis_file"
                    for instr in "${vector_instructions[@]}"; do
                        echo "  - $instr" >> "$analysis_file"
                    done

                    # Special analysis for our portable SIMD implementations
                    if [[ "$impl" == *"Simd"* ]]; then
                        local vpcmpeqb=$(grep -Eich "\\bvpcmpeqb\\b" "$impl_dir"/*.s 2>/dev/null || echo "0")
                        local vpmovmskb=$(grep -Eich "\\bvpmovmskb\\b" "$impl_dir"/*.s 2>/dev/null || echo "0")
                        if [ $vpcmpeqb -gt 0 ] && [ $vpmovmskb -gt 0 ]; then
                            echo "  ✓ Portable SIMD core operations present (compare+mask)" >> "$analysis_file"
                        fi
                    fi
                else
                    echo "✗ No vectorization detected" >> "$analysis_file"

                    # Analyze scalar optimization patterns
                    echo "Scalar optimization patterns:" >> "$analysis_file"
                    local scalar_found=false

                    # Check for loop unrolling indicators
                    local rep_count=$(grep -ich "rep " "$impl_dir"/*.s 2>/dev/null || echo "0")
                    if [ $rep_count -gt 0 ]; then
                        echo "  - String operations (rep): $rep_count" >> "$analysis_file"
                        scalar_found=true
                    fi

                    # Check for 64-bit operations (indicates some optimization)
                    local movq_count=$(grep -ich "movq" "$impl_dir"/*.s 2>/dev/null || echo "0")
                    if [ $movq_count -gt 5 ]; then  # Arbitrary threshold
                        echo "  - 64-bit operations: $movq_count" >> "$analysis_file"
                        scalar_found=true
                    fi

                    if [ "$scalar_found" = false ]; then
                        echo "  - Basic scalar implementation" >> "$analysis_file"
                    fi
                fi

                # Function size analysis (complexity indicator)
                local avg_size=$(find "$impl_dir" -name "*.s" -exec wc -l {} \; | awk '{sum+=$1; count++} END {if(count>0) print int(sum/count); else print 0}')
                echo "Average function size: $avg_size lines" >> "$analysis_file"

            else
                echo "No functions extracted for this implementation" >> "$analysis_file"
            fi

            echo "" >> "$analysis_file"
        fi
    done

    # Overall summary
    cat >> "$analysis_file" << EOF

Summary:
========
EOF

    local vectorized_count=0
    local total_impls=0

    for impl in "${IMPLEMENTATIONS[@]}"; do
        local impl_dir="$base_dir/$impl"
        if [ -d "$impl_dir" ] && [ $(ls "$impl_dir"/*.s 2>/dev/null | wc -l) -gt 0 ]; then
            ((total_impls++))
            local has_vector=$(grep -Eq "xmm|ymm|zmm|vpcmpeq|vmov" "$impl_dir"/*.s 2>/dev/null && echo "true" || echo "false")
            if [ "$has_vector" = "true" ]; then
                ((vectorized_count++))
            fi
        fi
    done

    echo "Implementations with extracted functions: $total_impls" >> "$analysis_file"
    echo "Implementations showing vectorization: $vectorized_count" >> "$analysis_file"

    if [ $total_impls -gt 0 ]; then
        local vectorization_rate=$(echo "scale=1; $vectorized_count * 100 / $total_impls" | bc -l 2>/dev/null || echo "0")
        echo "Vectorization rate: $vectorization_rate%" >> "$analysis_file"
    fi

    echo "" >> "$analysis_file"
    echo "Expected vectorization patterns:" >> "$analysis_file"
    echo "- FindAllIterating: Likely scalar (basic iteration)" >> "$analysis_file"
    echo "- FindAllMemchrCrate: Likely vectorized (optimized library)" >> "$analysis_file"
    echo "- FindAllViaU16/U32/U64: May show some vectorization depending on compiler" >> "$analysis_file"
    echo "- FindAllViaSimd16/32/64: Should show explicit SIMD instructions" >> "$analysis_file"

    log_success "Vectorization analysis complete: $vectorized_count/$total_impls implementations vectorized"
}

# Function to compile and extract for one benchmark/target combination
process_benchmark_target() {
    local benchmark_name="$1"
    local target_name="$2"
    local rustflags="$3"
    local output_dir="$4"

    log_info "Processing: $benchmark_name on $target_name"

    # Clean previous artifacts
    cargo clean --release > /dev/null 2>&1 || true

    # Set RUSTFLAGS if provided
    if [ -n "$rustflags" ]; then
        export RUSTFLAGS="$rustflags"
    else
        unset RUSTFLAGS 2>/dev/null || true
    fi

    # Compile benchmark with assembly output
    if ! cargo rustc --bench "$benchmark_name" --release -- --emit asm > /dev/null 2>&1; then
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
    log_success "Assembly generated: $asm_size"

    # Copy full assembly for reference
    cp "$asm_file" "$output_dir/full_assembly.s"

    # Extract implementation-specific functions
    if extract_implementation_functions "$asm_file" "$benchmark_name" "$target_name" "$output_dir"; then
        # Run comprehensive analysis
        analyze_all_implementations "$output_dir" "$benchmark_name" "$target_name"
        log_success "Successfully processed $benchmark_name on $target_name"
        return 0
    else
        log_error "Failed to extract functions for $benchmark_name on $target_name"
        return 1
    fi

    # Clean up environment
    unset RUSTFLAGS 2>/dev/null || true
}

# Main execution
main() {
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local base_output_dir="results/complete_benchmark_assembly/$timestamp"

    log_info "Starting comprehensive benchmark assembly extraction..."
    log_info "Output directory: $base_output_dir"
    log_info "Will extract assembly for ${#IMPLEMENTATIONS[@]} implementations across ${#TARGET_CONFIGS[@]} targets"

    mkdir -p "$base_output_dir"

    local total_combinations=$((${#TARGET_CONFIGS[@]} * ${#BENCHMARKS[@]}))
    local successful=0
    local failed=0
    local current=0

    # Process each target configuration
    for target_name in "${!TARGET_CONFIGS[@]}"; do
        local rustflags="${TARGET_CONFIGS[$target_name]}"

        log_info "=== TARGET: $target_name ==="
        if [ -n "$rustflags" ]; then
            log_info "RUSTFLAGS: $rustflags"
        else
            log_info "RUSTFLAGS: (default)"
        fi

        # Process each benchmark for this target
        for benchmark_name in "${BENCHMARKS[@]}"; do
            ((current++))
            local progress="[$current/$total_combinations]"

            log_info "$progress Processing $benchmark_name..."

            local output_dir="$base_output_dir/$target_name/$benchmark_name"
            mkdir -p "$output_dir"

            if process_benchmark_target "$benchmark_name" "$target_name" "$rustflags" "$output_dir"; then
                ((successful++))
            else
                ((failed++))
            fi

            echo ""
        done
    done

    # Generate master summary
    local master_summary="$base_output_dir/master_summary.txt"
    cat > "$master_summary" << EOF
Complete Benchmark Assembly Extraction Report
Generated: $(date -Iseconds)

Configuration:
- Implementations tracked: ${#IMPLEMENTATIONS[@]} (${IMPLEMENTATIONS[*]})
- Target configurations: ${#TARGET_CONFIGS[@]} (${!TARGET_CONFIGS[*]})
- Benchmarks: ${#BENCHMARKS[@]} (${BENCHMARKS[*]})
- Total combinations: $total_combinations

Results:
- Successful extractions: $successful
- Failed extractions: $failed
- Success rate: $([ $total_combinations -gt 0 ] && echo "scale=1; $successful * 100 / $total_combinations" | bc -l || echo "0")%

Directory Structure:
$base_output_dir/
├── <target>/
│   ├── <benchmark>/
│   │   ├── <implementation>/
│   │   │   └── function_*.s
│   │   ├── full_assembly.s
│   │   ├── extraction_summary.txt
│   │   └── vectorization_analysis.txt

Usage:
- Compare implementations: diff $base_output_dir/<target>/<benchmark>/<impl1>/ $base_output_dir/<target>/<benchmark>/<impl2>/
- View vectorization analysis: cat $base_output_dir/<target>/<benchmark>/vectorization_analysis.txt
- Search for specific instructions: grep -r "vpcmpeqb" $base_output_dir/
- Find all vectorized implementations: grep -r "VECTORIZATION DETECTED" $base_output_dir/

Analysis Commands:
- Find SIMD usage: find $base_output_dir -name "vectorization_analysis.txt" -exec grep -l "VECTORIZATION DETECTED" {} \;
- Compare target effects: diff $base_output_dir/default/<benchmark>/vectorization_analysis.txt $base_output_dir/native-avx2/<benchmark>/vectorization_analysis.txt
- Implementation comparison: for impl in ${IMPLEMENTATIONS[*]}; do echo "=== \$impl ==="; find $base_output_dir -path "*/\$impl/function_*.s" | head -1 | xargs grep -E "vpcmpeqb|movq|rep" | wc -l; done
EOF

    log_success "Master extraction complete!"
    log_success "Results: $successful/$total_combinations successful"
    log_success "Output directory: $base_output_dir"

    if [ $successful -gt 0 ]; then
        echo ""
        log_info "Quick Analysis:"

        # Count implementations with vectorization across all targets
        local vectorized_files=$(find "$base_output_dir" -name "vectorization_analysis.txt" -exec grep -l "VECTORIZATION DETECTED" {} \; | wc -l)
        log_info "Files showing vectorization: $vectorized_files"

        # Show which implementations commonly get vectorized
        log_info "Vectorization by implementation:"
        for impl in "${IMPLEMENTATIONS[@]}"; do
            local impl_vector_count=$(find "$base_output_dir" -path "*/$impl/*" -name "function_*.s" -exec grep -l "xmm\|ymm\|vpcmpeq" {} \; 2>/dev/null | wc -l)
            local impl_total_count=$(find "$base_output_dir" -path "*/$impl/*" -name "function_*.s" 2>/dev/null | wc -l)
            if [ $impl_total_count -gt 0 ]; then
                log_info "  $impl: $impl_vector_count/$impl_total_count extracts show vectorization"
            fi
        done

        echo ""
        log_info "To explore results:"
        log_info "1. View master summary: cat $base_output_dir/master_summary.txt"
        log_info "2. Compare implementations: ls $base_output_dir/native-avx2/bench_newlines/"
        log_info "3. Analyze vectorization: find $base_output_dir -name 'vectorization_analysis.txt' -exec head -20 {} \;"
        log_info "4. Find SIMD functions: grep -r 'vpcmpeqb' $base_output_dir/ | head -5"
    fi

    return $([[ $successful -gt 0 ]] && echo 0 || echo 1)
}

# Check dependencies
if ! command -v bc >/dev/null 2>&1; then
    log_warning "bc calculator not found. Some percentage calculations may not work."
fi

# Run main function
main "$@"
