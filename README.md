# Benchmarks to test various ways of scanning a byte-array for a single value

This crate is a benchmark of various ways to scan byte arrays for all occurrences of a target character.
It should not be used as production code.
As compilation varies by platform and rustc args, you may get very different results in one context vs another.
Proceed with caution.

## Purpose

This project benchmarks different approaches to byte scanning operations, which are fundamental to many string parsing tasks. The goal is to understand how different implementations perform and whether the Rust compiler generates SIMD instructions for various approaches across different CPU instruction set levels.

## Installation & Prerequisites

### Installing Rust and Nightly Toolchain

If you don't already have Rust installed:

1. **Install Rustup** (Rust toolchain installer):
   ```bash
   curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
   source ~/.cargo/env
   ```

2. **Install Rust Nightly** (required for portable SIMD features):
   ```bash
   rustup install nightly
   rustup default nightly
   ```

3. **Verify Installation**:
   ```bash
   rustc --version  # Should show nightly version
   cargo --version
   ```

### Project Setup

```bash
git clone <repository-url>
cd benchfind
cargo check  # Verify project compiles
```

## Implementations Benchmarked

This project compares the following byte scanning strategies:

* **Naive iteration** - iterator-based enumerate/map/filter chain
* **memchr crate** - optimized library implementation
* **Chunked processing** - fetching bytes via u16, u32, u64 alignment
* **Portable SIMD** - using Rust's portable SIMD with 16, 32, 64 byte lanes

## Benchmark Workloads

The benchmarks test these implementations across different use cases:

* **Newline scanning** - finding newlines in large text files and line iteration
* **CSV parsing** - parsing CSV files using different strategies

## Implementation Details

For SIMD operations, this crate uses Rust's portable SIMD API, which compiles on all platforms but will emit SIMD instructions when the target supports them. The code uses standard Rust library features without direct intrinsics or hand-crafted assembly.

## CSV Parsing Strategies

The CSV benchmarks test two different parsing approaches:

* **Nested parsing** - first identifies lines, then finds commas within each line slice
* **Flat parsing** - maintains separate iterators for newlines and commas, advancing them in coordination

## Progressive SIMD Target Testing

### Multi-Target Benchmarking

The benchmarking system tests across **7 progressive CPU targets** to analyze SIMD instruction generation:

1. **`default`** - Generic x86-64 (baseline, no SIMD expected)
2. **`native`** - Host CPU optimization (conservative SIMD)
3. **`native-sse2`** - Host CPU + explicit SSE2 features
4. **`native-sse4`** - Host CPU + SSE4.2, SSSE3, SSE3, SSE2
5. **`native-avx`** - Host CPU + AVX + all SSE features
6. **`native-avx2`** - Host CPU + AVX2 + AVX + all SSE features
7. **`native-avx512`** - Host CPU + AVX-512 + all previous features

This progressive approach reveals how explicit SIMD feature enablement affects code generation, since Rust's conservative defaults don't automatically enable CPU features even when using `target-cpu=native`.

### Automated SIMD Detection

The `check_simd.sh` script automatically analyzes generated assembly code after each benchmark run:

1. Compiles benchmarks with assembly output enabled
2. Searches for common SIMD instruction mnemonics
3. Reports whether SIMD instructions were detected for each target

## Usage

### Quick Benchmarking

To run benchmarks with basic SIMD detection:

```bash
./bench_all.sh
```

### Comprehensive Data Collection

For complete benchmark data collection with metadata, assembly analysis, and structured results storage:

```bash
./run_comprehensive_benchmarks.sh
```

This comprehensive system:
- Collects complete system and build environment metadata
- Generates assembly code for each implementation/target combination
- Performs detailed SIMD instruction analysis
- Stores all results in a structured format for future analysis
- Automatically skips runs if results already exist for the current source code and compiler version
- Provides progress feedback and timing estimates during long runs

### Testing the Data Collection System

To verify the data collection system works correctly:

```bash
./test_data_collection.sh
```

## Assembly Analysis

### Focused Function Extraction

The system can extract individual `find_all` method implementations (instead of full 19MB benchmark files):

```bash
# Extract for specific existing run
./extract_find_all_assembly.sh --run hostname_sourcehash_rustcversion

# Extract for single target to custom location  
./extract_single_target.sh --target native-avx2 --output results/assembly/native-avx2
```

### What Gets Extracted

Each target extraction produces:
- **Individual assembly files** (~60 lines each): `via_simd32_find_all.s`, `via_u64_find_all.s`, etc.
- **SIMD analysis reports**: Machine and human-readable SIMD instruction detection
- **Function summaries**: Line counts, sizes, and extraction metadata
- **Complete library assembly**: Full assembly for reference

## Results Structure

The comprehensive benchmarking system stores results in `results/runs/` with the following structure:

```
results/runs/{hostname}_{source-hash}_{rustc-version}/
├── metadata/           # System, build, and source information
├── raw-results/        # Complete Criterion benchmark data (without HTML reports)
├── assembly_extracts/  # Focused find_all implementations per target
│   ├── default/
│   ├── native/
│   ├── native-sse2/
│   ├── native-sse4/
│   ├── native-avx/
│   ├── native-avx2/
│   └── native-avx512/
└── logs/              # Execution logs and error reports
```

Each run is uniquely identified by:
- **Hostname**: The system where benchmarks were run
- **Source Hash**: Hash of benchmark-relevant source files (src/lib.rs, benches/, Cargo.toml)
- **Rustc Version**: The Rust compiler version used

## Data Collection Features

### Intelligent Caching
- Automatically skips expensive re-runs when source code and compiler haven't changed
- Only benchmarks that affect results trigger new data collection
- Touching documentation or scripts won't trigger unnecessary rebuilds

### Comprehensive Metadata
- **System Information**: CPU model, features, memory, OS details
- **Build Information**: Rust compiler version, git status, compilation flags
- **Source Tracking**: Individual file hashes, dependency versions
- **Execution Logs**: Complete output, timing, error reports

### Fault Tolerance
- Graceful handling of unsupported CPU targets (e.g., AVX-512 on older CPUs)
- Comprehensive error reporting and continuation logic
- Progress feedback during long benchmark runs
- Detailed execution summary with success/failure counts

## Space Efficiency

The system automatically excludes large, non-essential files:
- **Skips HTML reports**: Removes Criterion's web visualization files (~41MB saved)
- **Focused assembly**: Extracts only core function implementations (~60 lines vs 19MB files)
- **Smart compression**: Stores essential data while maintaining full analysis capability

## Collaborative Workflow

Results are automatically organized to support cross-system analysis:

```bash
# On each system:
./run_comprehensive_benchmarks.sh
git add results/
git commit -m "Add benchmark results for system_name"

# Results from all systems accumulate in results/runs/
```

## Future Analysis Support

The collected data enables various analysis approaches:

- **Performance Regression Detection**: Track performance across source modifications
- **Hardware Optimization Analysis**: Compare SIMD generation across CPU targets  
- **Compiler Evolution Tracking**: Monitor optimization improvements across rustc versions
- **Cross-System Comparisons**: Analyze performance characteristics across different hardware
- **Statistical Analysis**: Detailed performance distributions and confidence intervals

All necessary metadata is captured to enable unforeseen future analysis requirements.

## Files Overview

### Core Scripts
- **`bench_all.sh`** - Progressive target benchmarking with error handling
- **`check_simd.sh`** - Assembly analysis and SIMD instruction detection
- **`run_comprehensive_benchmarks.sh`** - Complete data collection orchestration

### Assembly Analysis
- **`extract_find_all_assembly.sh`** - Focused function extraction for all targets
- **`extract_single_target.sh`** - Single target assembly extraction
- **`test_data_collection.sh`** - System validation and testing

### Results Management
- **`cleanup_results.sh`** - Remove large non-essential files from results
- **`results/`** - Structured storage for all benchmark data and analysis

The system is designed for both individual development and collaborative multi-system performance analysis.