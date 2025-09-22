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

To run all benchmarks with SIMD detection:

```bash
./bench_all.sh
```

The output includes benchmark results and SIMD instruction detection reports for each CPU target.