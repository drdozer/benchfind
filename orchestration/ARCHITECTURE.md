# Benchfind Orchestration System Architecture

## Overview

The Benchfind orchestration system is a Python-based replacement for legacy bash scripts that provides systematic Rust benchmarking with comprehensive SIMD analysis. The system is designed around **deterministic result caching**, **configuration-driven behavior**, and **structured data organization**.

## High-Level Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   User CLI      │    │  Configuration  │    │   Rust Project  │
│   Interface     │────│     System      │────│   (Benchmarks)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌─────────────────┐              │
         └──────────────│ Orchestration   │──────────────┘
                        │     Core        │
                        └─────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│    Metadata     │    │   Benchmark     │    │    Assembly     │
│   Collection    │    │   Execution     │    │    Analysis     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                        ┌─────────────────┐
                        │  Results        │
                        │  Storage        │
                        └─────────────────┘
```

## Core Principles

### 1. **Deterministic Caching**
Results are uniquely identified by:
```
RunID = (hostname, source_hash, rustc_version)
```
- Same inputs always produce same storage location
- Enables intelligent cache reuse across runs
- Supports collaborative result sharing

### 2. **Configuration-Driven Design**
All behavior externalized to YAML files:
- **No hardcoded values** in Python code
- **Single source of truth** for targets, paths, policies
- **Environment-agnostic** configuration management

### 3. **Progressive SIMD Testing**
Seven compilation targets test SIMD capability progression:
```
default → native → SSE2 → SSE4 → AVX → AVX2 → AVX512
```

## Component Architecture

### CLI Interface (`cli.py`)
- **Primary user interface** using Click framework
- **Command routing** to appropriate orchestration modules
- **Progress reporting** with Rich terminal formatting
- **Error handling** with user-friendly messages

Key Commands:
- `benchfind quick` - Development iteration
- `benchfind comprehensive` - Full benchmark suite
- `benchfind analyze` - Results analysis
- `benchfind config` - Configuration management
- `benchfind manage` - Storage operations

### Configuration System (`config.py`)
- **YAML-based configuration** management
- **Target definitions** with RUSTFLAGS and descriptions
- **Execution parameters** (timeouts, measurement times)
- **Storage policies** (caching, cleanup, organization)

Configuration Files:
```
config/
├── targets.yaml        # Compilation target definitions
├── execution.yaml      # Benchmark parameters and timeouts
├── storage.yaml        # Results organization and caching
├── benchmarks.yaml     # Benchmark suite definitions
└── instructions.yaml   # SIMD instruction patterns
```

### Benchmark Execution (`benchmark.py`)
- **Real cargo bench execution** with target-specific RUSTFLAGS
- **Progress tracking** and timeout management
- **Error capture** and reporting
- **Result aggregation** across targets

Execution Flow:
1. **Environment Setup** - Set RUSTFLAGS for target
2. **Compilation** - `cargo bench` with timeout
3. **Result Capture** - Parse Criterion output
4. **Storage** - Save structured results

### Metadata Collection (`metadata.py`)
- **System information** (CPU, memory, OS)
- **Build environment** (Rust version, git state)
- **Source tracking** (file hashes, change detection)
- **Execution context** (timestamps, configuration)

Metadata Types:
- `SystemInfo` - Hardware and OS details
- `BuildInfo` - Compiler and git information
- `SourceHashes` - File integrity tracking
- `ExecutionContext` - Runtime parameters

### Assembly Analysis (`assembly.py`)
- **Assembly generation** from compiled benchmarks
- **SIMD instruction detection** using pattern matching
- **Function extraction** for focused analysis
- **Performance categorization** (SSE/AVX/AVX-512)

Analysis Pipeline:
1. **Compilation** - Generate assembly with cargo
2. **Parsing** - Extract function boundaries and instructions
3. **Classification** - Identify SIMD instruction types
4. **Reporting** - Generate analysis summaries

### Storage System (`storage.py`)
- **Deterministic organization** based on run identifiers
- **Intelligent caching** to avoid expensive re-runs
- **Index management** for cross-run queries
- **Data lifecycle** policies for cleanup

Storage Layout:
```
results/runs/{hostname}_{source-hash}_{rustc-version}/
├── metadata/           # System and build context
├── raw-results/        # Criterion benchmark output
├── assembly_extracts/  # Per-target assembly analysis
└── logs/              # Execution logs and diagnostics
```

## Data Flow

### 1. **Initialization**
```
User Command → CLI Parser → Configuration Loader → Environment Validation
```

### 2. **Run Planning**
```
Target Selection → Cache Check → Run ID Generation → Storage Layout
```

### 3. **Benchmark Execution**
```
For each target:
  Environment Setup → Cargo Compilation → Benchmark Execution → Result Collection
```

### 4. **Analysis & Storage**
```
Assembly Generation → SIMD Analysis → Result Storage → Index Update
```

## Key Interfaces

### RunIdentifier
```python
@dataclass
class RunIdentifier:
    hostname: str           # System where benchmarks run
    source_hash: str        # Hash of benchmark-relevant source files
    rustc_version: str      # Compiler version identifier
    
    @property
    def run_id(self) -> str:
        return f"{hostname}_{source_hash}_{rustc_version}"
```

### TargetDefinition
```python
@dataclass
class TargetDefinition:
    name: str                           # Target identifier (e.g., "native-avx2")
    rustflags: Optional[str]            # Compilation flags
    description: str                    # Human-readable description
    expected_simd_instructions: List[str]  # Expected SIMD patterns
```

### StorageLayout
```python
@dataclass
class StorageLayout:
    run_dir: Path                       # Base directory for this run
    metadata_dir: Path                  # System/build metadata
    raw_results_dir: Path               # Criterion benchmark data
    assembly_extracts_dir: Path        # Per-target assembly analysis
    logs_dir: Path                      # Execution logs
```

## Caching Strategy

### Cache Levels
1. **Python Results Cache** - Structured benchmark results storage
2. **Rust Compilation Cache** - Target directory and Criterion baselines
3. **Assembly Analysis Cache** - Generated assembly and SIMD analysis

### Cache Control Flags
- `--force-rebuild-results` - Bypass Python results cache only
- `--force-rebuild-benchmarks` - Clean Rust target and force fresh compilation

### Cache Keys
```python
# Primary cache key
cache_key = (source_hash, rustc_version, target_config)

# Cache validation
if cache_hit(cache_key) and not force_rebuild:
    return cached_results
else:
    execute_fresh_benchmarks()
```

## Error Handling Philosophy

### Fail-Fast Principles
- **Configuration errors** → Immediate failure with helpful message
- **Environment issues** → Early detection with fix suggestions
- **Storage corruption** → Automatic backup and recovery

### Graceful Degradation
- **Optional dependencies** → Continue with reduced functionality
- **Unsupported targets** → Skip target, continue with others
- **Partial failures** → Complete successful targets, report failures

### User-Friendly Reporting
- **Rich terminal output** with colors and formatting
- **Specific error messages** with actionable fix suggestions
- **Progress tracking** for long-running operations

## Extension Points

### Adding New Targets
1. Add target definition to `config/targets.yaml`
2. Define RUSTFLAGS and expected SIMD instructions
3. Target automatically available in CLI

### Adding New Analysis
1. Extend `assembly.py` with new instruction patterns
2. Add patterns to `config/instructions.yaml`
3. Analysis automatically integrated into results

### Adding New Commands
1. Add Click command to `cli.py`
2. Implement orchestration logic
3. Integrate with existing storage and configuration systems

## Performance Characteristics

### Benchmark Execution Time
- **~15 minutes per target** for comprehensive benchmarks
- **~90 minutes total** for all 7 targets
- **Parallelized within** each target (Criterion + Rust compilation)
- **Sequential across** targets (for measurement accuracy)

### Storage Requirements
- **~100MB per run** including assembly analysis
- **Intelligent deduplication** via deterministic run IDs
- **Configurable cleanup** policies for old results

### Memory Usage
- **Streaming processing** for large assembly files
- **Lazy loading** of configuration and metadata
- **Bounded memory** usage regardless of result history

## Security Considerations

### Subprocess Execution
- **Controlled command execution** with explicit arguments
- **Environment isolation** per target
- **Timeout protection** against runaway processes

### File System Access
- **Project-relative paths** only
- **No absolute path operations** outside project
- **Atomic file operations** to prevent corruption

### Data Validation
- **Input sanitization** for all user-provided data
- **Path validation** to prevent directory traversal
- **Configuration validation** against expected schemas

## Future Architecture Considerations

### Scalability
- **Multi-system orchestration** for cross-platform analysis
- **Result aggregation** from distributed benchmark runs
- **Centralized storage** options for team collaboration

### Extensibility
- **Plugin architecture** for custom analysis modules
- **API endpoints** for programmatic access
- **Integration hooks** for CI/CD systems

### Observability
- **Structured logging** with configurable levels
- **Metrics collection** for performance monitoring
- **Health checks** for system validation

This architecture provides a solid foundation for systematic Rust benchmarking while maintaining flexibility for future enhancements and collaborative development workflows.