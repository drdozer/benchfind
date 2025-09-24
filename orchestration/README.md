# Benchfind Orchestration

A Python-based orchestration system for systematic Rust benchmarking with comprehensive SIMD analysis and metadata collection.

## Overview

This package replaces the legacy bash scripts with a maintainable, well-documented Python system that:

- **Orchestrates multi-target benchmarking** across 7 progressive CPU instruction sets
- **Collects comprehensive metadata** (system info, build environment, git state)
- **Analyzes assembly output** for SIMD instruction detection
- **Manages structured results storage** with deduplication and indexing
- **Provides extensible foundation** for future analysis tools

## Project Structure

```
orchestration/
├── src/benchfind/           # Core library modules
│   ├── config.py           # Target definitions and configuration
│   ├── metadata.py         # System and build metadata collection
│   ├── benchmark.py        # Benchmark execution orchestration
│   ├── assembly.py         # Assembly generation and SIMD analysis
│   ├── storage.py          # Results storage and indexing
│   └── cli.py              # Command-line interface
├── scripts/                # High-level orchestration scripts
│   ├── run_comprehensive.py
│   ├── quick_bench.py
│   └── analyze_results.py
└── .venv/                  # Virtual environment (moved here)
```

## Setup

### 1. Activate Virtual Environment

```bash
cd orchestration
source .venv/bin/activate
```

### 2. Install Dependencies

```bash
# Install core dependencies
pip install -r requirements.txt

# Or install in development mode with all extras
pip install -e ".[dev,analysis]"
```

### 3. Verify Installation

```bash
# Check that benchfind CLI is available
benchfind --help
```

## Quick Start

### Run Comprehensive Benchmarks

```bash
# Full system with metadata collection and SIMD analysis
benchfind comprehensive

# With force rebuild options
benchfind comprehensive --force-rebuild-benchmarks
benchfind comprehensive --force-rebuild-results
```

### Quick Iteration Benchmarks

```bash
# Fast benchmarking for development iteration
benchfind quick --targets native,native-avx2

# Skip existing results for faster iteration
benchfind quick --skip-existing
```

### Analyze Results

```bash
# Analyze stored benchmark results
benchfind analyze --latest
benchfind analyze --run-id hostname_hash_version
benchfind analyze --simd-summary
```

## Target Configurations

The system tests across 7 progressive CPU instruction sets:

1. **`default`** - Generic x86-64 (baseline, no SIMD)
2. **`native`** - Host CPU optimization (conservative SIMD)
3. **`native-sse2`** - Host CPU + explicit SSE2
4. **`native-sse4`** - Host CPU + SSE4.2, SSSE3, SSE3, SSE2
5. **`native-avx`** - Host CPU + AVX + all SSE
6. **`native-avx2`** - Host CPU + AVX2 + AVX + all SSE
7. **`native-avx512`** - Host CPU + AVX-512 + all previous

## Key Features

### Intelligent Caching
- Automatically skips expensive re-runs when source code and compiler haven't changed
- Uses content hashing to detect meaningful changes
- Only triggers rebuilds when benchmark-relevant files are modified

### Comprehensive Metadata
- **System Information**: CPU model, features, memory, OS details
- **Build Information**: Rust compiler version, git status, compilation flags
- **Source Tracking**: Individual file hashes, dependency versions
- **Execution Logs**: Complete output, timing, error reports

### SIMD Analysis
- Automatic detection of SIMD instructions in generated assembly
- Progressive analysis across instruction set levels
- Machine and human-readable reports

### Structured Storage
Results are organized as:
```
../results/runs/{hostname}_{source-hash}_{rustc-version}/
├── metadata/           # System, build, and source information
├── raw-results/        # Complete Criterion benchmark data
├── assembly_extracts/  # Focused function implementations per target
└── logs/              # Execution logs and error reports
```

## Development

### Code Style
This project uses modern Python tooling:
- **Black** for code formatting
- **isort** for import sorting
- **mypy** for type checking
- **pytest** for testing

### Running Tests
```bash
pytest
pytest --cov=benchfind  # With coverage
```

### Type Checking
```bash
mypy src/
```

### Code Formatting
```bash
black src/ scripts/
isort src/ scripts/
```

## Architecture Philosophy

This system follows **semi-literate programming** principles:

1. **Clear Intent**: Each module documents its purpose and approach
2. **Minimal Duplication**: Shared utilities eliminate repetitive code
3. **Composable Design**: Modules can be used independently or together
4. **Extensible Foundation**: Designed for future analysis and visualization tools

## Migration from Legacy Scripts

The Python system replaces these bash scripts:

- `run_comprehensive_benchmarks.sh` → `scripts/run_comprehensive.py`
- `bench_all.sh` → `benchfind.benchmark` module
- `check_simd.sh` → `benchfind.assembly` module
- Various extraction scripts → `benchfind.storage` module

## Future Analysis Support

The structured data format enables:

- **Performance regression detection** across source modifications
- **Hardware optimization analysis** comparing SIMD generation
- **Compiler evolution tracking** across rustc versions
- **Cross-system comparisons** analyzing different hardware
- **Statistical analysis** with detailed performance distributions

## Contributing

1. Follow the established code style (Black + isort)
2. Add type hints to all new code
3. Include tests for new functionality
4. Update documentation for user-facing changes

## License

This project is licensed under the MIT License - see the LICENSE file for details.