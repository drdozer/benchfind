"""
Benchfind Orchestration: Systematic Rust benchmarking with SIMD analysis.

This package provides a Python-based orchestration system for running comprehensive
Rust benchmarks across multiple CPU instruction sets, collecting detailed metadata,
analyzing assembly output for SIMD instruction generation, and storing results in
a structured format for future analysis.

Key modules:
- config: Target definitions and configuration management
- metadata: System and build environment metadata collection
- benchmark: Benchmark execution orchestration
- assembly: Assembly generation and SIMD analysis
- storage: Results storage, indexing, and retrieval
- cli: Command-line interface

Usage:
    from benchfind import BenchmarkRunner, Config

    config = Config.from_defaults()
    runner = BenchmarkRunner(config)
    results = runner.run_comprehensive()
"""

__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

# Core public API - will be populated as modules are implemented
__all__ = [
    "__version__",
    # Configuration system
    "Config",
    "TargetDefinition",
    "BenchmarkSuite",
    "load_default_config",
    # Metadata system
    "MetadataCollector",
    "ComprehensiveMetadata",
    "collect_metadata",
    # Future components
    "BenchmarkRunner",
    "AssemblyAnalyzer",
    "ResultsStorage",
]

# Import core classes when they're implemented
# Configuration system is now implemented
try:
    from .config import Config, TargetDefinition, BenchmarkSuite, load_default_config
    from .metadata import MetadataCollector, ComprehensiveMetadata, collect_metadata
except ImportError as e:
    # If imports fail during development, provide None placeholders
    Config = None
    TargetDefinition = None
    BenchmarkSuite = None
    load_default_config = None
    MetadataCollector = None
    ComprehensiveMetadata = None
    collect_metadata = None

# Not yet implemented - will be added as we build them
try:
    from .benchmark import BenchmarkRunner
except ImportError:
    BenchmarkRunner = None

try:
    from .assembly import AssemblyAnalyzer
except ImportError:
    AssemblyAnalyzer = None

try:
    from .storage import ResultsStorage
except ImportError:
    ResultsStorage = None
