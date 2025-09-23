#!/bin/bash

# Cleanup script to remove large Criterion report directories while preserving essential data
# This script removes HTML reports, SVGs, and other visualization files that are not needed
# for downstream analysis, keeping only the JSON files with actual benchmark data

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

# Function to calculate directory size
get_dir_size() {
    local dir="$1"
    if [ -d "$dir" ]; then
        du -sh "$dir" 2>/dev/null | cut -f1
    else
        echo "0K"
    fi
}

# Function to clean up report directories
cleanup_reports() {
    log_info "Scanning for Criterion report directories to remove..."

    local total_removed=0
    local total_size_before=0
    local total_size_after=0

    # Find all report directories
    if [ -d "results" ]; then
        total_size_before=$(du -sh results 2>/dev/null | cut -f1)

        log_info "Current results directory size: $total_size_before"

        # Find and remove report directories
        local report_dirs=()
        while IFS= read -r -d '' dir; do
            report_dirs+=("$dir")
        done < <(find results -type d -name "report" -print0 2>/dev/null)

        if [ ${#report_dirs[@]} -eq 0 ]; then
            log_info "No report directories found to clean up"
            return 0
        fi

        log_info "Found ${#report_dirs[@]} report directories to remove"

        for dir in "${report_dirs[@]}"; do
            local dir_size=$(get_dir_size "$dir")
            if [ -d "$dir" ]; then
                log_info "Removing report directory: $dir ($dir_size)"
                rm -rf "$dir"
                ((total_removed++))
            fi
        done

        total_size_after=$(du -sh results 2>/dev/null | cut -f1)

        log_success "Cleanup completed!"
        log_success "Removed $total_removed report directories"
        log_success "Results size: $total_size_before → $total_size_after"
    else
        log_info "No results directory found - nothing to clean up"
    fi
}

# Function to show what would be preserved
show_preserved_files() {
    log_info "Essential files that are preserved:"

    if [ -d "results" ]; then
        # Show JSON files
        local json_count=$(find results -name "*.json" -type f | wc -l)
        log_info "  - $json_count JSON files (benchmark data, metadata)"

        # Show logs
        local log_count=$(find results -path "*/logs/*" -type f | wc -l)
        log_info "  - $log_count log files"

        # Show assembly files
        local asm_count=$(find results -name "*.s" -type f | wc -l)
        log_info "  - $asm_count assembly files"

        # Show SIMD analysis
        local simd_count=$(find results -name "simd-analysis.json" -type f | wc -l)
        log_info "  - $simd_count SIMD analysis files"
    fi
}

# Function to update .gitignore to prevent future report commits
update_gitignore() {
    log_info "Updating .gitignore to exclude Criterion reports..."

    local gitignore_entry="# Exclude large Criterion report directories (HTML, SVG, CSS, JS)
/results/runs/*/raw-results/criterion/*/report/
/results/runs/*/raw-results/criterion/*/*/report/"

    if ! grep -q "Criterion report directories" .gitignore 2>/dev/null; then
        echo "" >> .gitignore
        echo "$gitignore_entry" >> .gitignore
        log_success "Added Criterion report exclusions to .gitignore"
    else
        log_info ".gitignore already contains Criterion report exclusions"
    fi
}

# Function to create a summary of what's kept vs removed
create_cleanup_summary() {
    local summary_file="results/cleanup_summary.txt"

    cat > "$summary_file" << EOF
Criterion Results Cleanup Summary
Generated: $(date -Iseconds)

REMOVED (not needed for analysis):
- HTML report files
- SVG visualization files
- CSS and JavaScript assets
- Interactive web reports
- Plot images and charts

PRESERVED (essential for analysis):
- estimates.json - Performance measurements and confidence intervals
- sample.json - Raw sample data points
- benchmark.json - Benchmark configuration metadata
- tukey.json - Statistical analysis results
- All metadata files (system-info.json, build-info.json, etc.)
- All assembly files and SIMD analysis
- All execution logs

The preserved files contain all numerical data needed for:
- Performance analysis and comparison
- Statistical processing
- Trend analysis over time
- Cross-system comparisons
- Assembly and SIMD instruction analysis

The removed files were only used for human-friendly web visualization
and can be regenerated from the preserved data if needed.
EOF

    log_success "Created cleanup summary: $summary_file"
}

# Main execution function
main() {
    log_info "Starting Criterion results cleanup..."
    echo "================================================================="

    # Verify we're in the right directory
    if [ ! -f "Cargo.toml" ] || [ ! -f "src/lib.rs" ]; then
        log_error "Must be run from the root of the benchfind project"
        exit 1
    fi

    # Show what will be preserved
    show_preserved_files
    echo ""

    # Perform cleanup
    cleanup_reports
    echo ""

    # Update gitignore
    update_gitignore
    echo ""

    # Create summary
    create_cleanup_summary

    echo "================================================================="
    log_success "Cleanup completed successfully!"
    log_info "The results directory now contains only essential benchmark data"
    log_info "Future benchmark runs will automatically exclude report directories"
}

# Script entry point
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi
