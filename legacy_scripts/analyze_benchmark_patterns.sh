#!/bin/bash

# Analyze Benchmark Patterns Script
# This script compiles benchmarks and analyzes the assembly to identify different
# implementation patterns within the same binary, correlating them with performance.

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

# Target configurations
declare -A TARGET_CONFIGS=(
    ["default"]=""
    ["native"]="-C target-cpu=native"
    ["native-avx2"]="-C target-cpu=native -C target-feature=+avx2,+avx,+sse4.2,+ssse3,+sse3,+sse2"
)

# Implementation patterns to look for
declare -A PATTERNS=(
    # Portable SIMD patterns - separate checks for each component
    ["portable_simd_16_compare"]="vpcmpeqb.*%xmm"
    ["portable_simd_16_mask"]="vpmovmskb.*%xmm"
    ["portable_simd_32_compare"]="vpcmpeqb.*%ymm"
    ["portable_simd_32_mask"]="vpmovmskb.*%ymm"
    ["portable_simd_64_pattern"]="shlq.*\$32.*orq"

    # SIMD bit manipulation (from BitmaskIterator)
    ["simd_bitmask_ops"]="tzcnt[ql].*btr[ql]"

    # Auto-vectorization patterns
    ["auto_vector_sse"]="movdqu.*pcmpeqb"
    ["auto_vector_avx"]="vmovdqu.*vpcmpeqb"

    # Optimized library patterns (memchr)
    ["memchr_opt"]="rep.*scas|pcmpistri|pcmpistr"

    # Scalar optimization patterns
    ["scalar_unrolled"]="cmpb.*jne.*cmpb.*jne.*cmpb.*jne"
    ["scalar_64bit"]="movq.*cmpq"
    ["scalar_basic"]="movzbl.*cmpb.*jne"

    # String operation patterns
    ["string_ops"]="rep\s+(movs|stos|scas)"
    ["bit_manipulation"]="bsf|bsr|tzcnt|popcnt"
)

# Function to analyze assembly for implementation patterns
analyze_assembly_patterns() {
    local asm_file="$1"
    local target_name="$2"
    local output_dir="$3"

    log_info "Analyzing implementation patterns in assembly..."

    local pattern_file="$output_dir/pattern_analysis.txt"
    local detail_file="$output_dir/pattern_details.txt"

    cat > "$pattern_file" << EOF
Assembly Pattern Analysis
Target: $target_name
Assembly file: $(basename "$asm_file")
Size: $(du -sh "$asm_file" | cut -f1)
Generated: $(date -Iseconds)

Pattern Detection Results:
=========================

EOF

    cat > "$detail_file" << EOF
Detailed Pattern Matches
Target: $target_name
Generated: $(date -Iseconds)

EOF

    local patterns_found=0
    local total_patterns=${#PATTERNS[@]}

    # Analyze each pattern
    for pattern_name in "${!PATTERNS[@]}"; do
        local pattern="${PATTERNS[$pattern_name]}"
        local matches=0
        local match_lines=""

        # Search for pattern in assembly
        if match_lines=$(grep -En "$pattern" "$asm_file" 2>/dev/null); then
            matches=$(echo "$match_lines" | wc -l)
            ((patterns_found++))

            echo "✓ $pattern_name: $matches matches" >> "$pattern_file"

            # Add details to detail file
            echo "=== $pattern_name ===" >> "$detail_file"
            echo "Pattern: $pattern" >> "$detail_file"
            echo "Matches: $matches" >> "$detail_file"
            echo "" >> "$detail_file"

            # Show first few matches with context
            echo "$match_lines" | head -5 | while IFS= read -r line; do
                local line_num=$(echo "$line" | cut -d: -f1)
                local match_line=$(echo "$line" | cut -d: -f2-)
                echo "Line $line_num: $match_line" >> "$detail_file"

                # Get context around the match
                sed -n "$((line_num-2)),$((line_num+2))p" "$asm_file" >> "$detail_file"
                echo "---" >> "$detail_file"
            done
            echo "" >> "$detail_file"

        else
            echo "✗ $pattern_name: no matches" >> "$pattern_file"
        fi
    done

    # Overall statistics
    local total_functions=$(grep -c "^_ZN.*:$" "$asm_file" || echo "0")
    local simd_functions=$(grep -l "xmm\|ymm\|zmm" "$asm_file" >/dev/null 2>&1 && grep -c "xmm\|ymm\|zmm" "$asm_file" || echo "0")

    cat >> "$pattern_file" << EOF

Assembly Statistics:
===================
Total functions: $total_functions
SIMD instruction occurrences: $simd_functions
Patterns detected: $patterns_found/$total_patterns

Implementation Classification:
============================
EOF

    # Classify the overall assembly based on patterns found
    local classification="unknown"
    local confidence="low"

    # Check for portable SIMD - look for the actual patterns we generate
    if grep -q "vpcmpeqb.*%xmm\|vpcmpeqb.*%ymm" "$asm_file" 2>/dev/null &&
       grep -q "vpmovmskb" "$asm_file" 2>/dev/null &&
       grep -q "tzcnt" "$asm_file" 2>/dev/null; then
        classification="portable_simd"
        confidence="high"
        echo "Primary implementation: Portable SIMD (explicit SIMD operations with bitmask processing)" >> "$pattern_file"
    elif grep -q "pcmpistri\|pcmpistr\|rep.*scas" "$asm_file" 2>/dev/null; then
        classification="optimized_library"
        confidence="high"
        echo "Primary implementation: Optimized library (memchr-like patterns)" >> "$pattern_file"
    elif grep -q "movdqu\|vmovdqu" "$asm_file" 2>/dev/null; then
        classification="auto_vectorized"
        confidence="medium"
        echo "Primary implementation: Auto-vectorized scalar code" >> "$pattern_file"
    elif grep -q "rep\s\+movs\|rep\s\+stos" "$asm_file" 2>/dev/null; then
        classification="string_optimized"
        confidence="medium"
        echo "Primary implementation: String operation optimized" >> "$pattern_file"
    else
        classification="scalar"
        confidence="medium"
        echo "Primary implementation: Scalar (no vectorization detected)" >> "$pattern_file"
    fi

    echo "Confidence: $confidence" >> "$pattern_file"

    # Performance predictions based on patterns
    cat >> "$pattern_file" << EOF

Performance Expectations:
========================
Based on detected patterns:

EOF

    case "$classification" in
        "portable_simd")
            echo "- Should show excellent performance on vectorized workloads" >> "$pattern_file"
            echo "- Performance scales with SIMD width (16-byte vs 32-byte vs 64-byte)" >> "$pattern_file"
            echo "- Uses explicit vpcmpeqb + vpmovmskb + tzcnt pattern" >> "$pattern_file"
            echo "- Expect consistent performance across different data patterns" >> "$pattern_file"
            ;;
        "optimized_library")
            echo "- Should show excellent performance, potentially better than manual SIMD" >> "$pattern_file"
            echo "- Likely uses advanced CPU features and optimized algorithms" >> "$pattern_file"
            echo "- Performance may vary based on data characteristics" >> "$pattern_file"
            ;;
        "auto_vectorized")
            echo "- Performance depends on compiler's vectorization success" >> "$pattern_file"
            echo "- May be inconsistent across different data patterns" >> "$pattern_file"
            echo "- Generally good but may not match hand-optimized SIMD" >> "$pattern_file"
            ;;
        "scalar")
            echo "- Basic scalar performance, likely the baseline" >> "$pattern_file"
            echo "- Performance limited by single-byte processing" >> "$pattern_file"
            echo "- Should be consistently slower than vectorized approaches" >> "$pattern_file"
            ;;
    esac

    echo "" >> "$pattern_file"
    echo "Files created:" >> "$pattern_file"
    echo "- pattern_analysis.txt (this file)" >> "$pattern_file"
    echo "- pattern_details.txt (detailed matches with context)" >> "$pattern_file"
    echo "- assembly_excerpt.txt (key sections)" >> "$pattern_file"

    # Create assembly excerpt with key sections
    local excerpt_file="$output_dir/assembly_excerpt.txt"
    cat > "$excerpt_file" << EOF
Key Assembly Sections
Target: $target_name
Generated: $(date -Iseconds)

EOF

    # Extract key sections based on found patterns
    if grep -q "vpcmpeqb" "$asm_file" 2>/dev/null; then
        echo "=== SIMD Comparison Sections ===" >> "$excerpt_file"
        grep -B 5 -A 10 "vpcmpeqb" "$asm_file" | head -100 >> "$excerpt_file"
        echo "" >> "$excerpt_file"

        echo "=== SIMD Bitmask Processing ===" >> "$excerpt_file"
        grep -B 3 -A 5 "tzcnt.*btr" "$asm_file" | head -30 >> "$excerpt_file"
        echo "" >> "$excerpt_file"
    fi

    if grep -q "rep.*scas" "$asm_file" 2>/dev/null; then
        echo "=== String Operation Sections ===" >> "$excerpt_file"
        grep -B 5 -A 10 "rep.*scas" "$asm_file" | head -50 >> "$excerpt_file"
        echo "" >> "$excerpt_file"
    fi

    if grep -q "pcmpistr" "$asm_file" 2>/dev/null; then
        echo "=== String Instruction Sections ===" >> "$excerpt_file"
        grep -B 5 -A 10 "pcmpistr" "$asm_file" | head -50 >> "$excerpt_file"
        echo "" >> "$excerpt_file"
    fi

    # If no special patterns, show some general sections
    if [ "$classification" = "scalar" ]; then
        echo "=== General Loop Sections ===" >> "$excerpt_file"
        grep -B 3 -A 7 "cmpb.*jne" "$asm_file" | head -30 >> "$excerpt_file"
    fi

    log_success "Pattern analysis complete: $patterns_found patterns found, classified as '$classification'"

    # Return classification for summary
    echo "$classification"
}

# Function to process one benchmark/target combination
process_benchmark() {
    local benchmark_name="$1"
    local target_name="$2"
    local rustflags="$3"
    local base_output_dir="$4"

    local output_dir="$base_output_dir/$target_name"
    mkdir -p "$output_dir"

    log_info "=== Processing $benchmark_name with $target_name ==="

    # Clean and compile
    cargo clean --release > /dev/null 2>&1 || true

    if [ -n "$rustflags" ]; then
        export RUSTFLAGS="$rustflags"
        log_info "RUSTFLAGS: $rustflags"
    else
        unset RUSTFLAGS 2>/dev/null || true
        log_info "RUSTFLAGS: (default)"
    fi

    # Compile with assembly
    if ! cargo rustc --bench "$benchmark_name" --release -- --emit asm > /dev/null 2>&1; then
        log_error "Failed to compile $benchmark_name"
        return 1
    fi

    # Find assembly file
    local asm_file=$(find target/release/deps -name "${benchmark_name}-*.s" | head -1)
    if [ ! -f "$asm_file" ]; then
        log_error "Assembly file not found"
        return 1
    fi

    local asm_size=$(du -sh "$asm_file" | cut -f1)
    log_success "Compiled successfully ($asm_size assembly)"

    # Copy assembly
    cp "$asm_file" "$output_dir/benchmark_assembly.s"

    # Analyze patterns
    local classification=$(analyze_assembly_patterns "$asm_file" "$target_name" "$output_dir")

    # Create summary for this target
    cat > "$output_dir/target_summary.txt" << EOF
Target Summary: $target_name
Benchmark: $benchmark_name
Generated: $(date -Iseconds)

Configuration:
- RUSTFLAGS: ${rustflags:-"(default)"}
- Assembly size: $asm_size
- Classification: $classification

Key Files:
- benchmark_assembly.s (full assembly)
- pattern_analysis.txt (pattern detection results)
- pattern_details.txt (detailed pattern matches)
- assembly_excerpt.txt (key assembly sections)

Quick Analysis Commands:
- View patterns: cat pattern_analysis.txt
- Find SIMD: grep -E "vpcmpeqb|vpmovmskb" benchmark_assembly.s
- Count vector ops: grep -c "xmm\|ymm" benchmark_assembly.s
- Compare targets: diff ../other_target/pattern_analysis.txt pattern_analysis.txt
EOF

    echo "$classification"

    unset RUSTFLAGS 2>/dev/null || true
}

# Main function
main() {
    local benchmark="${1:-bench_newlines}"
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local output_dir="results/pattern_analysis/$benchmark/$timestamp"

    log_info "Starting benchmark pattern analysis..."
    log_info "Benchmark: $benchmark"
    log_info "Output directory: $output_dir"

    mkdir -p "$output_dir"

    local results_summary="$output_dir/analysis_summary.txt"
    cat > "$results_summary" << EOF
Benchmark Pattern Analysis Summary
Benchmark: $benchmark
Generated: $(date -Iseconds)

Target Analysis Results:
=======================

EOF

    local successful=0
    local total=${#TARGET_CONFIGS[@]}

    # Process each target
    declare -A target_classifications

    for target_name in "${!TARGET_CONFIGS[@]}"; do
        local rustflags="${TARGET_CONFIGS[$target_name]}"

        local classification=$(process_benchmark "$benchmark" "$target_name" "$rustflags" "$output_dir")

        if [ $? -eq 0 ]; then
            ((successful++))
            target_classifications["$target_name"]="$classification"
            echo "$target_name: $classification" >> "$results_summary"
        else
            echo "$target_name: FAILED" >> "$results_summary"
        fi

        echo ""
    done

    # Final comparison
    cat >> "$results_summary" << EOF

Comparison Analysis:
==================
Successful targets: $successful/$total

Implementation patterns by target:
EOF

    for target in "${!target_classifications[@]}"; do
        echo "- $target: ${target_classifications[$target]}" >> "$results_summary"
    done

    cat >> "$results_summary" << EOF

Expected Performance Order (best to worst):
1. optimized_library (memchr-like optimizations)
2. portable_simd (explicit SIMD with good implementations)
3. auto_vectorized (compiler auto-vectorization)
4. string_optimized (rep string operations)
5. scalar (basic byte-by-byte processing)

Analysis Files:
- This summary: analysis_summary.txt
- Per target: <target>/pattern_analysis.txt
- Assembly: <target>/benchmark_assembly.s
- Details: <target>/pattern_details.txt

Correlation Commands:
- Compare all targets: for t in */; do echo "=== \$t ==="; cat "\$t/pattern_analysis.txt" | grep "Primary implementation"; done
- Find best SIMD target: grep -r "portable_simd" */pattern_analysis.txt
- Performance prediction: cat */pattern_analysis.txt | grep -A 10 "Performance Expectations"
EOF

    log_success "Pattern analysis complete!"
    log_success "Analyzed $successful/$total targets successfully"
    log_success "Results in: $output_dir"

    if [ $successful -gt 0 ]; then
        echo ""
        log_info "Quick Results:"
        for target in "${!target_classifications[@]}"; do
            log_info "- $target: ${target_classifications[$target]}"
        done

        echo ""
        log_info "To explore results:"
        log_info "1. View summary: cat $output_dir/analysis_summary.txt"
        log_info "2. Compare targets: ls $output_dir/*/pattern_analysis.txt"
        log_info "3. Find SIMD details: grep -r 'vpcmpeqb' $output_dir/"
        log_info "4. Check classifications: grep 'Primary implementation' $output_dir/*/pattern_analysis.txt"
    fi

    return $([[ $successful -gt 0 ]] && echo 0 || echo 1)
}

# Check if benchmark name provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 [benchmark_name]"
    echo "Available benchmarks: bench_newlines, bench_csv"
    echo "Example: $0 bench_newlines"
    echo ""
fi

main "$@"
