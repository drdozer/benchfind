# Benchmark Results Data Collection System

This directory contains the comprehensive benchmark results collected by the `run_comprehensive_benchmarks.sh` script. The data is organized to support detailed performance analysis across different hardware configurations, compiler versions, and source code changes.

## Directory Structure

```
results/
├── runs/                           # Individual benchmark runs
│   └── {hostname}_{source-hash}_{rustc-version}/
│       ├── metadata/               # Environment and build metadata
│       │   ├── system-info.json   # Hardware, OS, environment details
│       │   ├── build-info.json    # Rust compiler, git information
│       │   ├── source-hashes.json # Source file checksums
│       │   └── run-config.json    # Benchmark configuration
│       ├── raw-results/            # Raw benchmark output
│       │   └── criterion/          # Complete Criterion benchmark data
│       ├── assembly/               # Generated assembly code
│       │   ├── bench_newlines/
│       │   │   └── {target}/       # per-target assembly
│       │   │       ├── complete_benchmark.s
│       │   │       ├── compilation.log
│       │   │       └── simd-analysis.json
│       │   └── bench_csv/
│       │       └── {target}/
│       └── logs/                   # Execution logs
│           ├── benchmark-run.log
│           ├── benchmark-execution.log
│           └── errors.log
├── index.json                      # Index of all runs
└── schema/                         # Documentation and schemas
    └── README.md
```

## Run Identification

Each benchmark run is uniquely identified by a folder name consisting of three components:

- **Hostname**: Sanitized system hostname (lowercase, special chars replaced with underscores)
- **Source Hash**: 8-character hash of benchmark-relevant source files:
  - `src/lib.rs`
  - `benches/bench_newlines.rs`
  - `benches/bench_csv.rs`  
  - `Cargo.toml`
- **Rustc Version**: Sanitized Rust compiler version (dots and dashes replaced with underscores)

### Example Run Folder Names

- `mycomputer_a1b2c3d4_1_75_0_nightly`
- `server01_f5e6d7c8_1_74_1`
- `laptop_9z8y7x6w_1_76_0_beta`

## Data Collection Strategy

### Metadata Files

**system-info.json**: Complete system information including:
- CPU model, cores, features (SSE, AVX levels)
- Memory configuration
- OS version and distribution
- Hardware architecture

**build-info.json**: Build environment details:
- Complete Rust compiler version information
- Git commit hash and repository status
- Target architecture information

**source-hashes.json**: Individual file checksums plus combined hash:
- SHA256 of each source file
- Combined hash used for run identification
- Cargo.lock hash (if present)

**run-config.json**: Benchmark configuration:
- Target architectures tested
- Measurement parameters
- Sample sizes per benchmark

### Assembly and SIMD Analysis

For each benchmark/target combination, the system generates:

- **complete_benchmark.s**: Full assembly output for the benchmark
- **compilation.log**: Compiler output and any warnings/errors
- **simd-analysis.json**: Automated SIMD instruction detection results

The SIMD analysis searches for common vectorization patterns including:
- Register usage (xmm, ymm, zmm)
- SIMD arithmetic instructions
- Vector comparison operations
- Data movement instructions

### Raw Results

The complete Criterion benchmark output is preserved in `raw-results/criterion/` to enable future reprocessing with different analysis methods.

## Usage

### Running Benchmarks

```bash
# Run comprehensive benchmark collection
./run_comprehensive_benchmarks.sh
```

The script will:
1. Check if results already exist for current source code + compiler
2. Skip execution if results are current
3. Otherwise, collect complete benchmark data
4. Update the run index

### Checking Existing Results

```bash
# List all runs
ls results/runs/

# Check what configurations have been tested
cat results/index.json
```

### Force Re-run

```bash
# Delete existing results to force re-run
rm -rf results/runs/{hostname}_{hash}_{version}

# Then run again
./run_comprehensive_benchmarks.sh
```

## Analysis Considerations

### Comparing Results

When comparing benchmark results across runs, consider:

- **Source Code Changes**: Different source hashes indicate code changes
- **Compiler Versions**: Different rustc versions may generate different optimizations
- **Hardware Differences**: CPU features affect SIMD generation and performance
- **System Load**: Background processes can affect benchmark timing

### Statistical Validity

- **Sample Sizes**: Newline benchmarks use 50 samples, CSV benchmarks use 100
- **Measurement Time**: All benchmarks run for 15 seconds per configuration
- **Multiple Targets**: Each run tests 5 different compilation targets

### Assembly Analysis

The generated assembly files enable:
- Verification of SIMD instruction generation
- Understanding optimization differences between targets
- Debugging performance anomalies
- Comparing compiler output across versions

## Git Integration

This results directory is designed to be committed to git, enabling:
- Collaborative benchmark collection across different systems
- Historical tracking of performance changes
- Comparison of results across different hardware configurations

### Recommended Workflow

1. Run benchmarks on your system
2. Review generated results for completeness
3. Commit new results to git:
   ```bash
   git add results/
   git commit -m "Add benchmark results for {hostname} {rustc_version}"
   ```

## Future Analysis

The collected data supports various analysis approaches:

- **Performance Regression Detection**: Track performance across source changes
- **Hardware Optimization Analysis**: Compare SIMD generation across CPU targets
- **Compiler Evolution**: Track optimization improvements across rustc versions
- **Statistical Analysis**: Detailed performance distributions and confidence intervals

All necessary metadata is captured to enable unforeseen future analysis requirements.