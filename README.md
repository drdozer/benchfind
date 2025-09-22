# Benchmarks to test various ways of scanning a byte-array for a single value

This crate is a benchmark of various ways to scan byte arrays for all occurrences of a target character.
It should not be used as production code.
As compilation varies by platform and rustc args, you may get very different results in one context vs another.
Proceed with caution.

## Purpose

This project benchmarks different approaches to byte scanning operations, which are fundamental to many string parsing tasks. The goal is to understand how different implementations perform and whether the Rust compiler generates SIMD instructions for various approaches.

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

## Extended Benchmarking and SIMD Detection

### Multi-Target Benchmarking

The `bench_all.sh` script runs benchmarks against multiple CPU targets:
- `default` - default Rust target
- `native` - native CPU optimization
- `x86-64-v2` - SSE instruction set level
- `x86-64-v3` - AVX/AVX2 instruction set level  
- `x86-64-v4` - AVX-512 instruction set level

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

### Testing the Data Collection System

To verify the data collection system works correctly:

```bash
./test_data_collection.sh
```

## Results Structure

The comprehensive benchmarking system stores results in `results/runs/` with the following structure:

```
results/runs/{hostname}_{source-hash}_{rustc-version}/
├── metadata/           # System, build, and source information
├── raw-results/        # Complete Criterion benchmark data
├── assembly/           # Generated assembly code per implementation
├── logs/              # Execution logs and error reports
```

Each run is uniquely identified by:
- **Hostname**: The system where benchmarks were run
- **Source Hash**: Hash of benchmark-relevant source files
- **Rustc Version**: The Rust compiler version used

Results are automatically organized to support cross-system analysis and performance tracking over time.