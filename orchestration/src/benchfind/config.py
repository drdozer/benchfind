"""
# Configuration Management for Benchfind Orchestration

This module provides a clean API for loading and accessing configuration data
from external YAML files. Rather than hardcoding data structures in Python,
we externalize all configuration to documented YAML files that can be easily
modified and version controlled.

## The Configuration Philosophy

Configuration should be:
1. **External**: Data lives in YAML files, not Python code
2. **Documented**: Each configuration file explains its purpose and structure
3. **Validated**: We validate loaded configuration against expected schemas
4. **Flexible**: Easy to override for different environments or use cases
5. **Discoverable**: Configuration structure should be introspectable

## Configuration Architecture

We organize configuration into orthogonal concerns:
- `targets.yaml`: Compilation targets and SIMD progression
- `benchmarks.yaml`: Benchmark suites and execution parameters
- `execution.yaml`: Timeouts, resource limits, and runtime settings

This separation allows us to modify one aspect (e.g., adding a new target)
without affecting others (e.g., benchmark definitions).

## Loading Strategy

Configuration is loaded lazily and cached to avoid filesystem overhead.
We validate the structure on load and provide helpful error messages
for common configuration mistakes.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
import os

import yaml
from pydantic import BaseModel, Field, validator, root_validator

# Get the path to the config directory relative to this module
CONFIG_DIR = Path(__file__).parent.parent.parent / "config"


class TargetDefinition(BaseModel):
    """
    ## Benchmark Target Configuration

    A target represents a specific compilation configuration for benchmarking.
    This is loaded from targets.yaml and validated to ensure all required
    fields are present and sensible.

    ### Design Notes

    Unlike the previous hardcoded approach, targets are now purely data-driven.
    The instruction_set field is descriptive rather than an enum, allowing
    for easier extension without code changes.
    """

    name: str
    instruction_set: str
    rustflags: Optional[str] = None
    description: str
    cpu_features: List[str] = Field(default_factory=list)
    expected_on_modern_cpu: bool = True
    expected_simd_instructions: List[str] = Field(default_factory=list)
    performance_expectation: str = "unknown"

    @validator('name')
    def validate_name(cls, v):
        """Ensure target name is filesystem-safe."""
        if not v or not v.strip():
            raise ValueError("Target name cannot be empty")
        # Check for filesystem-unsafe characters
        unsafe_chars = set('<>:"/\\|?*')
        if any(char in unsafe_chars for char in v):
            raise ValueError(f"Target name contains unsafe characters: {v}")
        return v.strip()

    @validator('rustflags', pre=True)
    def normalize_rustflags(cls, v):
        """Normalize rustflags - empty string becomes None."""
        if v is not None and not v.strip():
            return None
        return v

    def get_env_vars(self) -> Dict[str, str]:
        """
        ## Environment Variables for Benchmark Execution

        Convert this target configuration into the environment variables
        needed for `cargo bench`. This translates our YAML configuration
        into the runtime environment that Rust toolchain expects.
        """
        env = {}
        if self.rustflags:
            env['RUSTFLAGS'] = self.rustflags
        return env

    def is_likely_supported(self) -> bool:
        """
        ## Platform Compatibility Check

        Attempt to determine if this target is likely to work on the current CPU.
        This is a best-effort check for user experience - we'll still attempt
        the benchmark even if we think it might fail.

        Returns:
            True if the target is likely supported, False otherwise
        """
        if not self.cpu_features:
            return True

        # On Linux, check /proc/cpuinfo for CPU features
        try:
            with open('/proc/cpuinfo', 'r') as f:
                cpu_info = f.read().lower()

            # Look for CPU features in the flags line
            for line in cpu_info.split('\n'):
                if line.startswith('flags') or line.startswith('Features'):
                    flags = line.split(':', 1)[1].strip() if ':' in line else line
                    return all(feature.lower() in flags
                             for feature in self.cpu_features)

        except (OSError, FileNotFoundError):
            # Can't read CPU info, fall back to expectation
            pass

        return self.expected_on_modern_cpu


class BenchmarkSuite(BaseModel):
    """
    ## Benchmark Suite Configuration

    Represents a single benchmark suite (corresponding to a benches/*.rs file).
    This captures both the technical details and the analysis context for
    each type of performance test we run.

    ### Future Evolution

    Currently loaded from benchmarks.yaml, but the long-term goal is to
    introspect this information directly from the Rust benchmark code.
    The YAML structure is designed to match what we'd extract automatically.
    """

    name: str
    description: str
    focus_area: str
    data_characteristics: List[str] = Field(default_factory=list)
    benchmark_groups: List[Dict[str, Any]] = Field(default_factory=list)
    expected_variance: str = "medium"
    analysis_notes: str = ""

    @validator('name')
    def validate_benchmark_name(cls, v):
        """Ensure benchmark name matches expected patterns."""
        if not v.startswith('bench_'):
            raise ValueError(f"Benchmark name should start with 'bench_': {v}")
        return v


class ExecutionConfig(BaseModel):
    """
    ## Execution Runtime Configuration

    Controls how benchmarks are executed, including timeouts, resource limits,
    and error handling. This configuration affects the orchestration behavior
    but not the benchmark results themselves.

    ### Resource Management Philosophy

    We aim to be a good citizen of the system while getting reliable results:
    - Don't monopolize system resources
    - Provide reasonable timeouts to prevent hangs
    - Handle expected failures gracefully
    - Give users feedback on long-running operations
    """

    # Timing configuration
    measurement_time_seconds: int = 15
    warm_up_time_seconds: int = 3
    sample_sizes: Dict[str, int] = Field(default_factory=lambda: {"default": 100})

    # Timeout configuration
    single_benchmark_run: int = 1800
    target_compilation: int = 600
    comprehensive_run: int = 28800

    # Resource limits
    max_cpu_usage_percent: int = 95
    max_memory_usage_percent: int = 80
    min_free_disk_gb: int = 5

    # Error handling
    max_retries: int = 2
    continue_on_target_failure: bool = True
    expect_avx512_failures: bool = True

    # Caching behavior
    skip_existing_results: bool = True
    check_source_hash: bool = True
    max_cache_age_days: int = 30


class ProjectPaths(BaseModel):
    """
    ## Project Directory Structure

    Centralizes path management for the benchmarking system. Paths can be
    overridden via environment variables or direct configuration for
    different deployment scenarios.

    ### Path Resolution Strategy

    1. Check environment variables for overrides
    2. Use relative paths from project structure
    3. Validate that critical paths exist and are usable
    4. Provide helpful error messages for common misconfigurations
    """

    # Core project directories
    project_root: Path = Field(default_factory=lambda: Path.cwd())
    rust_project: Path = Field(default_factory=lambda: Path.cwd() / "rust_project")
    orchestration: Path = Field(default_factory=lambda: Path.cwd() / "orchestration")
    results: Path = Field(default_factory=lambda: Path.cwd() / "results")
    legacy_scripts: Path = Field(default_factory=lambda: Path.cwd() / "legacy_scripts")

    @validator('*', pre=True)
    def resolve_paths(cls, v):
        """Ensure all paths are resolved to absolute paths."""
        if isinstance(v, (str, Path)):
            return Path(v).resolve()
        return v

    @classmethod
    def from_env(cls) -> "ProjectPaths":
        """
        ## Create Paths from Environment Variables

        Allow path overrides via environment variables for CI/CD and
        different deployment scenarios.

        Environment variables:
        - BENCHFIND_PROJECT_ROOT: Root directory of the project
        - BENCHFIND_RUST_PROJECT: Rust project directory
        - BENCHFIND_RESULTS_DIR: Results storage directory
        """
        kwargs = {}

        if project_root := os.getenv('BENCHFIND_PROJECT_ROOT'):
            root_path = Path(project_root)
            kwargs['project_root'] = root_path
            # Derive other paths from project root if not explicitly set
            if not os.getenv('BENCHFIND_RUST_PROJECT'):
                kwargs['rust_project'] = root_path / "rust_project"
            if not os.getenv('BENCHFIND_RESULTS_DIR'):
                kwargs['results'] = root_path / "results"

        if rust_project := os.getenv('BENCHFIND_RUST_PROJECT'):
            kwargs['rust_project'] = Path(rust_project)

        if results_dir := os.getenv('BENCHFIND_RESULTS_DIR'):
            kwargs['results'] = Path(results_dir)

        return cls(**kwargs)

    def validate_critical_paths(self) -> List[str]:
        """
        ## Validate Critical Paths

        Check that essential paths exist and are accessible. Returns a list
        of error messages for any problems found.

        This validation helps catch configuration issues early rather than
        failing mysteriously during benchmark execution.
        """
        errors = []

        # Rust project must exist and look valid
        if not self.rust_project.exists():
            errors.append(f"Rust project directory not found: {self.rust_project}")
        elif not (self.rust_project / "Cargo.toml").exists():
            errors.append(f"Cargo.toml not found in: {self.rust_project}")
        elif not (self.rust_project / "src").exists():
            errors.append(f"src/ directory not found in: {self.rust_project}")

        # Results directory should be creatable
        try:
            self.results.mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError) as e:
            errors.append(f"Cannot create results directory {self.results}: {e}")

        return errors


class ConfigurationLoader:
    """
    ## Configuration File Loader

    Handles loading, parsing, and validation of YAML configuration files.
    Provides caching to avoid repeated filesystem access and helpful error
    messages when configuration files are malformed or missing.

    ### Error Handling Philosophy

    Configuration loading should provide clear, actionable error messages:
    - Tell users exactly which file failed to load
    - Explain what was wrong with the file content
    - Suggest how to fix common problems
    - Provide context about where the configuration system looks for files
    """

    def __init__(self, config_dir: Path = CONFIG_DIR):
        """
        Initialize the configuration loader.

        Args:
            config_dir: Directory containing YAML configuration files
        """
        self.config_dir = Path(config_dir)
        self._cache: Dict[str, Any] = {}

    def _load_yaml_file(self, filename: str) -> Dict[str, Any]:
        """
        Load and parse a YAML file with error handling.

        Args:
            filename: Name of the YAML file (without path)

        Returns:
            Parsed YAML content as a dictionary

        Raises:
            FileNotFoundError: If the configuration file doesn't exist
            ValueError: If the YAML file is malformed
        """
        if filename in self._cache:
            return self._cache[filename]

        file_path = self.config_dir / filename

        if not file_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {file_path}\n"
                f"Expected configuration files in: {self.config_dir}\n"
                f"Available files: {list(self.config_dir.glob('*.yaml'))}"
            )

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = yaml.safe_load(f)

            if content is None:
                raise ValueError(f"Configuration file is empty: {file_path}")

            self._cache[filename] = content
            return content

        except yaml.YAMLError as e:
            raise ValueError(
                f"Invalid YAML in configuration file {file_path}:\n{e}"
            )
        except Exception as e:
            raise ValueError(
                f"Failed to load configuration file {file_path}: {e}"
            )

    def load_targets(self) -> Dict[str, TargetDefinition]:
        """
        ## Load Target Definitions

        Load and validate all target configurations from targets.yaml.
        Returns a dictionary mapping target names to TargetDefinition objects.

        Raises:
            ValueError: If target configuration is invalid or malformed
        """
        config = self._load_yaml_file("targets.yaml")

        if 'targets' not in config:
            raise ValueError("targets.yaml must contain a 'targets' section")

        targets = {}
        for name, target_data in config['targets'].items():
            try:
                # Ensure the name matches the key
                target_data['name'] = name
                targets[name] = TargetDefinition.parse_obj(target_data)
            except Exception as e:
                raise ValueError(f"Invalid target definition '{name}': {e}")

        if not targets:
            raise ValueError("No valid targets found in targets.yaml")

        return targets

    def get_all_targets(self) -> List[TargetDefinition]:
        """
        ## Get All Target Definitions

        Get all available target definitions as a list of TargetDefinition objects.
        This is a convenience method that returns the values from load_targets().

        Returns:
            List of TargetDefinition objects
        """
        targets_dict = self.load_targets()
        return list(targets_dict.values())

    def get_target_group(self, group_name: str) -> List[TargetDefinition]:
        """
        ## Get Target Group as TargetDefinition Objects

        Get a predefined group of targets and return them as TargetDefinition objects.
        This resolves the target names in the group to actual target configurations.

        Args:
            group_name: Name of the target group ('development', 'comprehensive', 'all', etc.)

        Returns:
            List of TargetDefinition objects for the specified group

        Raises:
            ValueError: If the target group doesn't exist or contains invalid targets
        """
        target_groups = self.load_target_groups()
        targets_dict = self.load_targets()

        if group_name == "all":
            return list(targets_dict.values())

        if group_name not in target_groups:
            available_groups = list(target_groups.keys()) + ["all"]
            raise ValueError(f"Unknown target group '{group_name}'. Available groups: {available_groups}")

        target_names = target_groups[group_name]
        result = []

        for name in target_names:
            if name not in targets_dict:
                raise ValueError(f"Target '{name}' in group '{group_name}' not found in target definitions")
            result.append(targets_dict[name])

        return result

    def load_target_groups(self) -> Dict[str, List[str]]:
        """
        ## Load Target Groups

        Load predefined target groups from targets.yaml for common usage patterns.
        These groups allow easy selection of target subsets for different scenarios.

        Returns:
            Dictionary mapping group names to lists of target names
        """
        config = self._load_yaml_file("targets.yaml")
        return config.get('target_groups', {})

    def load_benchmark_suites(self) -> Dict[str, BenchmarkSuite]:
        """
        ## Load Benchmark Suite Definitions

        Load and validate benchmark suite configurations from benchmarks.yaml.
        Returns a dictionary mapping suite names to BenchmarkSuite objects.
        """
        config = self._load_yaml_file("benchmarks.yaml")

        if 'benchmark_suites' not in config:
            raise ValueError("benchmarks.yaml must contain a 'benchmark_suites' section")

        suites = {}
        for name, suite_data in config['benchmark_suites'].items():
            try:
                suite_data['name'] = name
                suites[name] = BenchmarkSuite.parse_obj(suite_data)
            except Exception as e:
                raise ValueError(f"Invalid benchmark suite definition '{name}': {e}")

        return suites

    def load_execution_config(self) -> ExecutionConfig:
        """
        ## Load Execution Configuration

        Load execution parameters from execution.yaml and merge with any
        environment variable overrides.

        Returns:
            Validated execution configuration object
        """
        config = self._load_yaml_file("execution.yaml")

        # Extract the main configuration sections
        execution_data = {}

        # Merge timing configuration
        if 'timing' in config:
            execution_data.update(config['timing'])

        # Merge timeout configuration
        if 'timeouts' in config:
            execution_data.update(config['timeouts'])

        # Merge resource configuration
        if 'resources' in config:
            execution_data.update(config['resources'])

        # Merge error handling configuration
        if 'error_handling' in config:
            execution_data.update(config['error_handling'])

        # Merge caching configuration
        if 'caching' in config:
            execution_data.update(config['caching'])

        # Apply environment variable overrides
        if measurement_time := os.getenv('BENCHFIND_MEASUREMENT_TIME'):
            execution_data['measurement_time_seconds'] = int(measurement_time)

        if skip_existing := os.getenv('BENCHFIND_SKIP_EXISTING'):
            execution_data['skip_existing_results'] = skip_existing.lower() in ('true', '1', 'yes')

        return ExecutionConfig.parse_obj(execution_data)

    def load_instruction_patterns(self) -> Dict[str, Any]:
        """
        ## Load Instruction Pattern Definitions

        Load instruction classification patterns from instructions.yaml.
        These patterns are used by the assembly analysis system for SIMD
        detection and instruction classification.

        Returns:
            Dictionary with instruction patterns and classification rules
        """
        return self._load_yaml_file("instructions.yaml")

    def get_instruction_sets(self) -> Set[str]:
        """
        ## Discover Available Instruction Sets

        Extract the set of instruction sets from target definitions.
        This replaces the hardcoded InstructionSet enum with data-driven discovery.

        Returns:
            Set of instruction set names found in target definitions
        """
        targets = self.load_targets()
        return {target.instruction_set for target in targets.values()}

    def load_storage_config(self) -> Dict[str, Any]:
        """
        ## Load Storage Configuration

        Load storage configuration from storage.yaml.
        This defines how results are organized, stored, and managed.

        Returns:
            Dictionary with storage configuration settings
        """
        return self._load_yaml_file("storage.yaml")


class Config(BaseModel):
    """
    ## Main Configuration Object

    Brings together all configuration aspects into a single, validated object
    that serves as the authoritative source of configuration for the entire
    benchmarking system.

    ### Usage Pattern

    The Config object should be created once at application startup and
    passed to components that need configuration information:

    ```python
    config = Config.from_defaults()
    runner = BenchmarkRunner(config)
    results = runner.run_comprehensive()
    ```

    ### Validation Strategy

    All configuration is validated at load time rather than at use time.
    This catches configuration problems early and provides clear error
    messages when something is wrong.
    """

    # Core configuration components
    paths: ProjectPaths
    targets: Dict[str, TargetDefinition]
    benchmark_suites: Dict[str, BenchmarkSuite]
    execution: ExecutionConfig

    # Computed properties
    target_groups: Dict[str, List[str]] = Field(default_factory=dict)
    available_instruction_sets: Set[str] = Field(default_factory=set)
    instruction_patterns: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        """Pydantic configuration."""
        arbitrary_types_allowed = True

    @classmethod
    def from_defaults(cls, config_dir: Optional[Path] = None) -> "Config":
        """
        ## Create Configuration with Default Settings

        Load configuration from YAML files in the default configuration directory.
        This is the primary way to create a Config object for normal usage.

        Args:
            config_dir: Optional override for configuration directory location

        Returns:
            Fully configured Config object

        Example:
            ```python
            config = Config.from_defaults()
            # Configuration is loaded from orchestration/config/*.yaml
            ```
        """
        loader = ConfigurationLoader(config_dir or CONFIG_DIR)

        # Load paths from environment if available
        paths = ProjectPaths.from_env()

        # Load all configuration components
        targets = loader.load_targets()
        target_groups = loader.load_target_groups()
        benchmark_suites = loader.load_benchmark_suites()
        execution = loader.load_execution_config()
        instruction_patterns = loader.load_instruction_patterns()

        # Discover instruction sets from targets
        instruction_sets = loader.get_instruction_sets()

        return cls(
            paths=paths,
            targets=targets,
            benchmark_suites=benchmark_suites,
            execution=execution,
            target_groups=target_groups,
            available_instruction_sets=instruction_sets,
            instruction_patterns=instruction_patterns
        )

    @classmethod
    def from_files(cls, targets_file: Path, benchmarks_file: Path,
                   execution_file: Path) -> "Config":
        """
        ## Create Configuration from Specific Files

        Load configuration from explicitly specified YAML files.
        Useful for testing or when using non-standard configuration locations.

        Args:
            targets_file: Path to targets YAML file
            benchmarks_file: Path to benchmarks YAML file
            execution_file: Path to execution YAML file

        Returns:
            Configured Config object
        """
        # This would be implemented to load from specific files
        # For now, fall back to default loading
        return cls.from_defaults()

    def get_target(self, name: str) -> Optional[TargetDefinition]:
        """Get a specific target definition by name."""
        return self.targets.get(name)

    def get_target_group(self, group_name: str) -> List[str]:
        """
        ## Get Target Group

        Retrieve a predefined group of targets by name. Common groups include:
        - 'all': All available targets
        - 'production': Targets suitable for production analysis
        - 'development': Fast targets for development iteration
        - 'simd_progression': Targets that show SIMD capability progression

        Args:
            group_name: Name of the target group

        Returns:
            List of target names in the group, empty list if group not found
        """
        return self.target_groups.get(group_name, [])

    def get_benchmark_suite(self, name: str) -> Optional[BenchmarkSuite]:
        """Get a specific benchmark suite definition by name."""
        return self.benchmark_suites.get(name)

    def validate_setup(self) -> List[str]:
        """
        ## Validate Complete Configuration

        Perform comprehensive validation of the entire configuration to ensure
        the system is ready to run benchmarks. This includes path validation,
        configuration consistency checks, and system compatibility verification.

        Returns:
            List of error messages for any problems found, empty list if valid
        """
        errors = []

        # Validate paths
        errors.extend(self.paths.validate_critical_paths())

        # Validate that we have targets and benchmarks
        if not self.targets:
            errors.append("No benchmark targets configured")

        if not self.benchmark_suites:
            errors.append("No benchmark suites configured")

        # Validate target group references
        for group_name, target_names in self.target_groups.items():
            for target_name in target_names:
                if target_name not in self.targets:
                    errors.append(f"Target group '{group_name}' references unknown target '{target_name}'")

        # Validate execution configuration
        if self.execution.measurement_time_seconds < 1:
            errors.append("Measurement time must be at least 1 second")

        return errors

    def get_enabled_targets(self, group: Optional[str] = None) -> List[str]:
        """
        ## Get List of Enabled Targets

        Get the names of targets that should be benchmarked. Can optionally
        filter by a target group for specific use cases.

        Args:
            group: Optional target group name to filter by

        Returns:
            List of target names to benchmark
        """
        if group:
            return self.get_target_group(group)
        return list(self.targets.keys())


# Convenience functions for common usage patterns

def load_default_config() -> Config:
    """Load configuration using default settings and file locations."""
    return Config.from_defaults()


def validate_config_directory(config_dir: Path = CONFIG_DIR) -> List[str]:
    """
    ## Validate Configuration Directory

    Check that a configuration directory contains all required files and
    that they're syntactically valid YAML.

    Args:
        config_dir: Directory to validate

    Returns:
        List of validation errors, empty if directory is valid
    """
    errors = []
    required_files = ["targets.yaml", "benchmarks.yaml", "execution.yaml", "instructions.yaml"]

    for filename in required_files:
        file_path = config_dir / filename
        if not file_path.exists():
            errors.append(f"Missing required configuration file: {file_path}")
        else:
            try:
                with open(file_path, 'r') as f:
                    yaml.safe_load(f)
            except yaml.YAMLError as e:
                errors.append(f"Invalid YAML in {filename}: {e}")
            except Exception as e:
                errors.append(f"Cannot read {filename}: {e}")

    return errors


def get_available_target_groups() -> List[str]:
    """
    ## Get Available Target Groups

    Return the names of all available target groups defined in the configuration.
    Useful for CLI help text and validation.

    Returns:
        List of available target group names
    """
    try:
        loader = ConfigurationLoader()
        target_groups = loader.load_target_groups()
        return list(target_groups.keys())
    except Exception:
        return []


def get_available_instruction_sets() -> List[str]:
    """
    ## Get Available Instruction Sets

    Return the list of instruction sets found in target definitions.
    This replaces the hardcoded enum with dynamic discovery.

    Returns:
        List of instruction set names found in configuration
    """
    try:
        loader = ConfigurationLoader()
        return sorted(loader.get_instruction_sets())
    except Exception:
        return []
