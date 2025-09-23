#!/bin/bash

# Extract find_all Assembly for Single Target
# This script compiles the library for a specific target and extracts
# only the relevant FindNeedleInHaystack::find_all implementations

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

# Function to map baseline names to CPU targets
map_target_name() {
    local baseline_name="$1"
    case "$baseline_name" in
        "default")
            echo "generic"
            ;;
        *)
            echo "$baseline_name"
            ;;
    esac
}

# Function to get RUSTFLAGS for target
get_rustflags() {
    local target="$1"
    case "$target" in
        "default")
            echo ""
            ;;
        "native")
            echo "-C target-cpu=native"
            ;;
        "native-sse2")
            echo "-C target-cpu=native -C target-feature=+sse2"
            ;;
        "native-sse4")
            echo "-C target-cpu=native -C target-feature=+sse4.2,+ssse3,+sse3,+sse2"
            ;;
        "native-avx")
            echo "-C target-cpu=native -C target-feature=+avx,+sse4.2,+ssse3,+sse3,+sse2"
            ;;
        "native-avx2")
            echo "-C target-cpu=native -C target-feature=+avx2,+avx,+sse4.2,+ssse3,+sse3,+sse2"
            ;;
        "native-avx512")
            echo "-C target-cpu=native -C target-feature=+avx512f,+avx512bw,+avx2,+avx,+sse4.2,+ssse3,+sse3,+sse2"
            ;;
        *)
            echo ""
            ;;
    esac
}

# Function to extract a single function from assembly
extract_function() {
    local asm_file="$1"
    local function_name="$2"
    local output_file="$3"

    # Find the function start
    local start_line=$(grep -n "^$function_name:$" "$asm_file" | cut -d: -f1)

    if [ -z "$start_line" ]; then
        log_warning "Function $function_name not found in assembly"
        return 1
    fi

    # Look for .size directive which marks the actual end of the function
    local end_line=$(tail -n +$((start_line + 1)) "$asm_file" | grep -n "^\.size.*$function_name" | head -1 | cut -d: -f1)

    if [ -n "$end_line" ]; then
        end_line=$((start_line + end_line - 1))
    else
        # If no .size found, look for next function or section
        end_line=$(tail -n +$((start_line + 1)) "$asm_file" | grep -n "^_ZN.*:$\|^\.section" | head -1 | cut -d: -f1)
        if [ -n "$end_line" ]; then
            end_line=$((start_line + end_line - 1))
        else
            end_line=$(wc -l < "$asm_file")
        fi
    fi

    # Extract the function
    sed -n "${start_line},${end_line}p" "$asm_file" > "$output_file"

    log_success "Extracted $function_name (lines $start_line-$end_line, $(wc -l < "$output_file") lines)"
    return 0
}

# Function to extract all find_all implementations from assembly file
extract_find_all_implementations() {
    local asm_file="$1"
    local output_dir="$2"
    local target_name="$3"

    log_info "Extracting find_all implementations for target $target_name..."

    # Create output directory
    mkdir -p "$output_dir"

    # Find all FindNeedleInHaystack::find_all function symbols
    local function_symbols=$(grep "^_ZN.*FindNeedleInHaystack.*find_all.*:$" "$asm_file" | sed 's/:$//' | sort | uniq)

    if [ -z "$function_symbols" ]; then
        log_warning "No find_all implementations found in assembly for $target_name"
        return 1
    fi

    local extracted_count=0
    local function_summary="$output_dir/functions_summary.txt"

    cat > "$function_summary" << EOF
Find All Implementations Assembly Extract - Target: $target_name
Generated: $(date -Iseconds)
Source Assembly: $(basename "$asm_file")

Functions Extracted:
EOF

    # Extract each function
    while IFS= read -r symbol; do
        # Determine implementation type from symbol
        local impl_type="unknown"
        if echo "$symbol" | grep -q "FindAllMemchrCrate"; then
            impl_type="memchr_crate"
        elif echo "$symbol" | grep -q "FindAllIterating"; then
            impl_type="iterating"
        elif echo "$symbol" | grep -q "FindAllViaU16"; then
            impl_type="via_u16"
        elif echo "$symbol" | grep -q "FindAllViaU32"; then
            impl_type="via_u32"
        elif echo "$symbol" | grep -q "FindAllViaU64"; then
            impl_type="via_u64"
        elif echo "$symbol" | grep -q "FindAllViaSimd16"; then
            impl_type="via_simd16"
        elif echo "$symbol" | grep -q "FindAllViaSimd32"; then
            impl_type="via_simd32"
        elif echo "$symbol" | grep -q "FindAllViaSimd64"; then
            impl_type="via_simd64"
        fi

        local output_file="$output_dir/${impl_type}_find_all.s"

        if extract_function "$asm_file" "$symbol" "$output_file"; then
            ((extracted_count++))

            # Add to summary
            echo "- $impl_type: $output_file" >> "$function_summary"
            echo "  Symbol: $symbol" >> "$function_summary"
            echo "  Size: $(wc -l < "$output_file") lines, $(du -sh "$output_file" | cut -f1)" >> "$function_summary"
            echo "" >> "$function_summary"

            # Add header to assembly file
            local temp_file=$(mktemp)
            cat > "$temp_file" << EOF
# FindNeedleInHaystack Implementation: $impl_type
# Target: $target_name
# Symbol: $symbol
# Extracted: $(date -Iseconds)

EOF
            cat "$output_file" >> "$temp_file"
            mv "$temp_file" "$output_file"
        fi
    done <<< "$function_symbols"

    echo "Total functions extracted: $extracted_count" >> "$function_summary"

    log_success "Extracted $extracted_count find_all implementations for $target_name"
    return 0
}

# Function to run SIMD analysis on extracted functions
analyze_simd_in_functions() {
    local functions_dir="$1"
    local target_name="$2"

    log_info "Running SIMD analysis on extracted functions for $target_name..."

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
    local analysis_file="$functions_dir/simd_analysis.json"
    local analysis_summary="$functions_dir/simd_summary.txt"

    # Initialize analysis results
    local analysis_results=()

    cat > "$analysis_summary" << EOF
SIMD Analysis Summary - Target: $target_name
Generated: $(date -Iseconds)

Function-by-Function SIMD Detection:
EOF

    # Analyze each extracted function
    for asm_file in "$functions_dir"/*.s; do
        if [ ! -f "$asm_file" ] || [[ "$(basename "$asm_file")" == "*.s" ]]; then
            continue
        fi

        local function_name=$(basename "$asm_file" .s)
        local simd_detected=false
        local detected_instructions=()

        # Check for SIMD instructions
        if grep -Eiq "$grep_pattern" "$asm_file"; then
            simd_detected=true

            # Collect specific instructions found
            for pattern in "${simd_patterns[@]}"; do
                if grep -Eiq "$pattern" "$asm_file"; then
                    detected_instructions+=("$pattern")
                fi
            done
        fi

        # Add to summary
        echo "- $function_name: $([ "$simd_detected" = true ] && echo "✓ SIMD DETECTED" || echo "✗ No SIMD")" >> "$analysis_summary"
        if [ "$simd_detected" = true ]; then
            echo "  Instructions: ${detected_instructions[*]}" >> "$analysis_summary"
        fi
        echo "" >> "$analysis_summary"

        # Build JSON entry
        local instructions_json="["
        for i in "${!detected_instructions[@]}"; do
            if [ $i -gt 0 ]; then
                instructions_json+=","
            fi
            instructions_json+="\"${detected_instructions[i]}\""
        done
        instructions_json+="]"

        analysis_results+=("{
  \"function\": \"$function_name\",
  \"simd_detected\": $simd_detected,
  \"detected_instructions\": $instructions_json,
  \"assembly_file\": \"$(basename "$asm_file")\"
}")
    done

    # Generate JSON analysis file
    cat > "$analysis_file" << EOF
{
  "analysis_time": "$(date -Iseconds)",
  "target": "$target_name",
  "analysis_method": "grep_pattern_matching",
  "functions": [
$(IFS=','; echo "${analysis_results[*]}")
  ]
}
EOF

    local simd_count=$(grep -c "\"simd_detected\": true" "$analysis_file" 2>/dev/null || echo "0")
    local total_count=${#analysis_results[@]}

    echo "Summary: $simd_count of $total_count functions contain SIMD instructions" >> "$analysis_summary"

    log_success "SIMD analysis complete: $simd_count/$total_count functions contain SIMD instructions"
}

# Main execution function
main() {
    local target=""
    local output_dir=""

    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --target)
                target="$2"
                shift 2
                ;;
            --output)
                output_dir="$2"
                shift 2
                ;;
            --help|-h)
                cat << EOF
Usage: $0 --target TARGET --output OUTPUT_DIR

Extract FindNeedleInHaystack::find_all implementations for a single target.

Options:
  --target TARGET    Target to process (default, native, native-sse2, native-sse4, native-avx, native-avx2, native-avx512)
  --output DIR       Output directory
  --help, -h         Show this help message

Examples:
  $0 --target native --output results/assembly/native
  $0 --target native-avx2 --output results/assembly/native-avx2
  $0 --target native-avx512 --output results/assembly/native-avx512
EOF
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done

    # Validate arguments
    if [ -z "$target" ] || [ -z "$output_dir" ]; then
        log_error "Both --target and --output are required"
        echo "Use --help for usage information"
        exit 1
    fi

    log_info "Starting find_all assembly extraction for target: $target"
    log_info "Output directory: $output_dir"

    # Verify we're in the right directory
    if [ ! -f "Cargo.toml" ] || [ ! -f "src/lib.rs" ]; then
        log_error "Must be run from the root of the benchfind project"
        exit 1
    fi

    # Map target name for compilation
    local cpu_target=$(map_target_name "$target")
    local rustflags=$(get_rustflags "$target")

    # Set up environment
    if [ -n "$rustflags" ]; then
        export RUSTFLAGS="$rustflags"
        log_info "Using RUSTFLAGS: $rustflags"
    else
        unset RUSTFLAGS || true
        log_info "Using default RUSTFLAGS"
    fi

    # Create output directory
    mkdir -p "$output_dir"

    # Clean benchfind artifacts for fresh compilation
    log_info "Cleaning benchfind artifacts for fresh compilation..."
    rm -rf target/release/deps/benchfind-*
    rm -rf target/release/deps/libbenchfind-*

    # Compile library with assembly output
    local compile_cmd="cargo rustc --lib --release -- -C target-cpu=$cpu_target --emit asm"
    local compile_log="$output_dir/compilation.log"

    log_info "Compiling: $compile_cmd"

    if $compile_cmd > "$compile_log" 2>&1; then
        log_success "Compilation successful for $target"

        # Find the generated library assembly file
        local asm_file=$(find target/release/deps/ -name "benchfind-*.s" -type f -print 2>/dev/null | head -1)

        if [ -n "$asm_file" ] && [ -f "$asm_file" ]; then
            local asm_size=$(du -sh "$asm_file" | cut -f1)
            log_info "Found assembly file: $asm_file ($asm_size)"

            # Copy assembly file to output directory for reference
            cp "$asm_file" "$output_dir/full_library.s"

            # Extract find_all implementations
            if extract_find_all_implementations "$asm_file" "$output_dir" "$target"; then
                # Run SIMD analysis
                analyze_simd_in_functions "$output_dir" "$target"

                # Clean up assembly file after successful extraction
                rm -f "$asm_file"

                log_success "Target $target processing complete"
                exit 0
            else
                log_error "Failed to extract implementations for $target"
                exit 1
            fi
        else
            log_error "No assembly file generated for $target"
            exit 1
        fi
    else
        log_error "Compilation failed for $target"
        cat "$compile_log"
        exit 1
    fi
}

# Script entry point
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi
