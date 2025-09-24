"""
# Metadata Collection for Benchfind Orchestration

This module handles the collection of comprehensive system and build metadata
that accompanies our benchmark results. The goal is to capture enough context
about the execution environment that we can meaningfully compare results
across different systems, time periods, and software versions.

## The Metadata Problem

When we run benchmarks, we're not just measuring code performance - we're
measuring the interaction between:

1. **The source code** being benchmarked
2. **The compiler** that translates it to assembly
3. **The CPU** that executes the assembly
4. **The operating system** that schedules and manages execution
5. **The system state** at the time of measurement

Without capturing this context, benchmark results become difficult to interpret
and impossible to reproduce. A performance regression might be due to a code
change, a compiler update, a system configuration change, or even thermal
throttling.

## Our Approach: Comprehensive Context Capture

Rather than guessing what metadata might be useful later, we capture everything
we can reasonably collect about the execution environment. This includes:

- **System hardware**: CPU model, features, memory, architecture
- **Software environment**: OS version, kernel, installed packages
- **Build context**: Compiler versions, git state, source code hashes
- **Execution context**: System load, temperature, power state (when available)

The metadata is structured as JSON documents that can be easily processed by
analysis tools, compared across runs, and archived for long-term studies.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import hashlib
import json
import os
import platform
import subprocess
import sys

import psutil
import git
from pydantic import BaseModel, Field, validator


class SystemInfo(BaseModel):
    """
    ## System Hardware and OS Information

    This captures the fundamental hardware and operating system characteristics
    that affect benchmark performance. We focus on information that's likely
    to impact CPU-intensive workloads with SIMD instructions.

    ### Design Notes

    - All string fields are normalized to avoid parsing issues later
    - Memory values are in consistent units (bytes) for easy comparison
    - CPU feature detection works across platforms (Linux /proc/cpuinfo, macOS sysctl)
    - Unknown values are explicitly marked rather than omitted
    """

    # Collection metadata
    collection_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    hostname: str = Field(default_factory=lambda: platform.node().lower())

    # Operating system information
    os_name: str = Field(default_factory=lambda: platform.system())
    os_release: str = Field(default_factory=lambda: platform.release())
    os_version: str = Field(default_factory=lambda: platform.version())
    os_machine: str = Field(default_factory=lambda: platform.machine())
    os_processor: str = Field(default_factory=lambda: platform.processor())

    # Linux-specific distribution info (empty on other platforms)
    distribution_id: Optional[str] = None
    distribution_version: Optional[str] = None

    # CPU information
    cpu_model: Optional[str] = None
    cpu_cores_physical: Optional[int] = None
    cpu_cores_logical: Optional[int] = None
    cpu_architecture: str = Field(default_factory=lambda: platform.machine())
    cpu_features: List[str] = Field(default_factory=list)
    cpu_max_frequency_mhz: Optional[float] = None

    # Memory information
    memory_total_bytes: Optional[int] = None
    memory_available_bytes: Optional[int] = None

    # Python environment
    python_version: str = Field(default_factory=lambda: sys.version)
    python_executable: str = Field(default_factory=lambda: sys.executable)

    @validator('hostname', pre=True)
    def sanitize_hostname(cls, v):
        """Ensure hostname is safe for use in filenames."""
        if not v:
            return "unknown"
        # Replace any problematic characters with underscores
        import re
        return re.sub(r'[^a-z0-9._-]', '_', v.lower())


class BuildInfo(BaseModel):
    """
    ## Build Environment Information

    This captures everything about the compilation environment that might
    affect benchmark results. Since we're testing across different RUSTFLAGS
    configurations, it's crucial to record exactly which compiler was used
    and what the build context looked like.

    ### Rust Compiler Information

    We record both the version string and the detailed verbose output because:
    - Version strings are human-readable and good for quick comparison
    - Verbose output contains technical details like LLVM version and target info
    - Different Rust versions can generate dramatically different SIMD code

    ### Git Repository State

    We track the exact source code state because:
    - Even small changes can affect optimization decisions
    - Clean vs. dirty working directory affects reproducibility
    - Branch and commit info helps correlate results with development history
    """

    # Collection metadata
    collection_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Rust toolchain information
    rustc_version: Optional[str] = None
    rustc_verbose_info: Dict[str, str] = Field(default_factory=dict)
    cargo_version: Optional[str] = None

    # Git repository state
    git_commit_hash: Optional[str] = None
    git_branch: Optional[str] = None
    git_is_clean: Optional[bool] = None
    git_status_summary: List[str] = Field(default_factory=list)
    git_remote_url: Optional[str] = None

    # Build environment
    rust_target_triple: Optional[str] = None
    cargo_target_dir: Optional[str] = None

    # Environment variables that affect builds
    relevant_env_vars: Dict[str, str] = Field(default_factory=dict)


class SourceHashes(BaseModel):
    """
    ## Source Code Fingerprinting

    To determine when benchmark results can be reused, we need to know when
    the source code that affects benchmarks has changed. This model captures
    cryptographic hashes of all files that could impact benchmark results.

    ### Incremental Hash Strategy

    Rather than hashing the entire repository (which includes docs, tests, etc.),
    we focus on the specific files that affect benchmark compilation:

    - `src/lib.rs` and other source files: The code being benchmarked
    - `benches/*.rs`: The benchmark definitions themselves
    - `Cargo.toml`: Dependencies and compilation flags
    - `Cargo.lock`: Exact dependency versions (when present)

    ### Combined Hash

    We also compute a combined hash of all benchmark-relevant content.
    This single value can be used to uniquely identify a "benchmark state"
    for caching and result organization.
    """

    # Collection metadata
    collection_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Individual file hashes
    individual_files: Dict[str, str] = Field(default_factory=dict)

    # Combined hash of all benchmark-relevant content
    combined_hash: Optional[str] = None

    # Hash algorithm used (for future compatibility)
    hash_algorithm: str = "sha256"


class ExecutionContext(BaseModel):
    """
    ## Runtime Execution Context

    This captures the system state at the time benchmarks are executed.
    While we can't control all environmental factors, recording them helps
    us understand result variance and identify anomalous runs.

    ### System Load Information

    High system load can affect benchmark timing through:
    - CPU scheduling competition
    - Memory pressure affecting cache behavior
    - Thermal throttling from other processes

    ### Resource Availability

    Available memory and CPU state can impact:
    - Whether the system can sustain peak performance
    - Benchmark process priority and scheduling
    - Background service interference
    """

    # Collection metadata
    collection_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # System load and resource usage
    cpu_percent_current: Optional[float] = None
    cpu_percent_1min: Optional[float] = None
    memory_percent_used: Optional[float] = None

    # Process information
    benchmark_process_priority: Optional[int] = None

    # Thermal state (when available)
    cpu_temperature_celsius: Optional[float] = None

    # Power state (when available)
    power_source: Optional[str] = None  # "battery", "ac", "unknown"
    battery_percent: Optional[float] = None


class MetadataCollector:
    """
    ## Comprehensive Metadata Collection Orchestration

    This class coordinates the collection of all metadata types and provides
    a clean interface for the benchmarking system to capture execution context.

    ### Usage Pattern

    The typical usage is to create a collector, gather metadata, and then
    serialize it for storage alongside benchmark results:

    ```python
    collector = MetadataCollector(rust_project_path=Path("rust_project"))
    metadata = collector.collect_all()

    # Store metadata with results
    metadata.save_json(results_dir / "metadata")
    ```

    ### Error Handling Philosophy

    Metadata collection should never prevent benchmarks from running.
    If we can't collect some piece of information (e.g., git info when
    not in a git repository), we record that fact but continue with
    partial metadata rather than failing entirely.
    """

    def __init__(self, rust_project_path: Path):
        """
        Initialize the metadata collector.

        Args:
            rust_project_path: Path to the Rust project being benchmarked
        """
        self.rust_project_path = Path(rust_project_path).resolve()
        self._git_repo: Optional[git.Repo] = None

    def collect_system_info(self) -> SystemInfo:
        """
        ## Collect System Hardware and OS Information

        This gathers comprehensive information about the hardware and operating
        system that will execute our benchmarks. We try multiple approaches
        for each piece of information to work across different platforms.
        """
        info = SystemInfo()

        try:
            # Try to get more detailed CPU information
            info.cpu_model = self._get_cpu_model()
            info.cpu_features = self._get_cpu_features()
            info.cpu_max_frequency_mhz = self._get_cpu_max_frequency()

            # Get core counts
            info.cpu_cores_physical = psutil.cpu_count(logical=False)
            info.cpu_cores_logical = psutil.cpu_count(logical=True)

            # Get memory information
            memory = psutil.virtual_memory()
            info.memory_total_bytes = memory.total
            info.memory_available_bytes = memory.available

            # Get Linux distribution info if available
            if platform.system().lower() == 'linux':
                dist_info = self._get_linux_distribution_info()
                info.distribution_id = dist_info.get('id')
                info.distribution_version = dist_info.get('version')

        except Exception as e:
            # Log but don't fail - partial system info is better than none
            print(f"Warning: Could not collect complete system info: {e}")

        return info

    def collect_build_info(self) -> BuildInfo:
        """
        ## Collect Build Environment Information

        This captures the Rust toolchain and git repository state that will
        affect benchmark compilation and results.
        """
        info = BuildInfo()

        try:
            # Get Rust toolchain information
            info.rustc_version = self._get_rustc_version()
            info.rustc_verbose_info = self._get_rustc_verbose_info()
            info.cargo_version = self._get_cargo_version()
            info.rust_target_triple = self._get_rust_target_triple()

            # Get git repository information
            git_info = self._get_git_info()
            if git_info:
                info.git_commit_hash = git_info.get('commit_hash')
                info.git_branch = git_info.get('branch')
                info.git_is_clean = git_info.get('is_clean')
                info.git_status_summary = git_info.get('status_summary', [])
                info.git_remote_url = git_info.get('remote_url')

            # Capture relevant environment variables
            info.relevant_env_vars = self._get_relevant_env_vars()

            # Get cargo target directory
            info.cargo_target_dir = self._get_cargo_target_dir()

        except Exception as e:
            print(f"Warning: Could not collect complete build info: {e}")

        return info

    def collect_source_hashes(self) -> SourceHashes:
        """
        ## Collect Source Code Hashes

        This computes cryptographic hashes of all source files that could
        affect benchmark results, allowing us to detect when results can
        be reused and when re-benchmarking is necessary.
        """
        hashes = SourceHashes()

        try:
            # Define files that affect benchmark results
            benchmark_relevant_files = [
                "src/lib.rs",
                "Cargo.toml",
                "Cargo.lock",  # May not exist
            ]

            # Add all benchmark files
            benches_dir = self.rust_project_path / "benches"
            if benches_dir.exists():
                for bench_file in benches_dir.glob("*.rs"):
                    benchmark_relevant_files.append(f"benches/{bench_file.name}")

            # Add all source files in src/
            src_dir = self.rust_project_path / "src"
            if src_dir.exists():
                for src_file in src_dir.rglob("*.rs"):
                    rel_path = src_file.relative_to(self.rust_project_path)
                    benchmark_relevant_files.append(str(rel_path))

            # Compute individual file hashes
            file_contents = []
            for rel_path in benchmark_relevant_files:
                full_path = self.rust_project_path / rel_path
                if full_path.exists():
                    try:
                        content = full_path.read_bytes()
                        file_hash = hashlib.sha256(content).hexdigest()
                        hashes.individual_files[rel_path] = file_hash
                        file_contents.append(content)
                    except (OSError, IOError) as e:
                        print(f"Warning: Could not hash {rel_path}: {e}")
                        hashes.individual_files[rel_path] = f"error: {e}"

            # Compute combined hash
            if file_contents:
                combined_content = b"".join(file_contents)
                hashes.combined_hash = hashlib.sha256(combined_content).hexdigest()[:16]

        except Exception as e:
            print(f"Warning: Could not collect complete source hashes: {e}")

        return hashes

    def collect_execution_context(self) -> ExecutionContext:
        """
        ## Collect Runtime Execution Context

        This captures the current system state that might affect benchmark
        performance, such as CPU load and available resources.
        """
        context = ExecutionContext()

        try:
            # Get current CPU usage
            context.cpu_percent_current = psutil.cpu_percent(interval=1.0)

            # Get system load averages (Unix-like systems)
            if hasattr(os, 'getloadavg'):
                load_avg = os.getloadavg()
                context.cpu_percent_1min = (load_avg[0] / psutil.cpu_count()) * 100

            # Get memory usage
            memory = psutil.virtual_memory()
            context.memory_percent_used = memory.percent

            # Get current process info
            current_process = psutil.Process()
            if hasattr(current_process, 'nice'):
                context.benchmark_process_priority = current_process.nice()

            # Try to get thermal information (platform-specific)
            context.cpu_temperature_celsius = self._get_cpu_temperature()

            # Try to get power information
            power_info = self._get_power_info()
            if power_info:
                context.power_source = power_info.get('source')
                context.battery_percent = power_info.get('battery_percent')

        except Exception as e:
            print(f"Warning: Could not collect complete execution context: {e}")

        return context

    def collect_all(self) -> 'ComprehensiveMetadata':
        """
        ## Collect All Metadata Types

        This is the main entry point for metadata collection. It gathers
        all types of metadata and returns them in a structured format.
        """
        return ComprehensiveMetadata(
            system_info=self.collect_system_info(),
            build_info=self.collect_build_info(),
            source_hashes=self.collect_source_hashes(),
            execution_context=self.collect_execution_context()
        )

    # Private helper methods for platform-specific information gathering

    def _get_cpu_model(self) -> Optional[str]:
        """Get detailed CPU model information."""
        try:
            if platform.system().lower() == 'linux':
                with open('/proc/cpuinfo', 'r') as f:
                    for line in f:
                        if line.startswith('model name'):
                            return line.split(':', 1)[1].strip()
            elif platform.system().lower() == 'darwin':
                result = subprocess.run(['sysctl', '-n', 'machdep.cpu.brand_string'],
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    return result.stdout.strip()
        except Exception:
            pass

        return None

    def _get_cpu_features(self) -> List[str]:
        """Get list of CPU features/flags."""
        features = []

        try:
            if platform.system().lower() == 'linux':
                with open('/proc/cpuinfo', 'r') as f:
                    for line in f:
                        if line.startswith('flags') or line.startswith('Features'):
                            feature_line = line.split(':', 1)[1].strip() if ':' in line else line
                            features = feature_line.split()
                            break
            elif platform.system().lower() == 'darwin':
                # macOS doesn't expose CPU flags as easily, but we can try sysctl
                result = subprocess.run(['sysctl', 'machdep.cpu.features'],
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    feature_line = result.stdout.split(':', 1)[1].strip()
                    features = feature_line.split()
        except Exception:
            pass

        return features

    def _get_cpu_max_frequency(self) -> Optional[float]:
        """Get maximum CPU frequency in MHz."""
        try:
            cpu_freq = psutil.cpu_freq()
            if cpu_freq:
                return cpu_freq.max
        except Exception:
            pass

        return None

    def _get_linux_distribution_info(self) -> Dict[str, Optional[str]]:
        """Get Linux distribution information."""
        info = {'id': None, 'version': None}

        try:
            # Try /etc/os-release first (most modern distributions)
            os_release_path = Path('/etc/os-release')
            if os_release_path.exists():
                os_release = {}
                with open(os_release_path, 'r') as f:
                    for line in f:
                        if '=' in line:
                            key, value = line.strip().split('=', 1)
                            os_release[key] = value.strip('"')

                info['id'] = os_release.get('ID')
                info['version'] = os_release.get('VERSION_ID')

        except Exception:
            pass

        return info

    def _get_rustc_version(self) -> Optional[str]:
        """Get rustc version string."""
        try:
            result = subprocess.run(['rustc', '--version'],
                                  capture_output=True, text=True, timeout=10,
                                  cwd=self.rust_project_path)
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass

        return None

    def _get_rustc_verbose_info(self) -> Dict[str, str]:
        """Get detailed rustc version information."""
        info = {}

        try:
            result = subprocess.run(['rustc', '--version', '--verbose'],
                                  capture_output=True, text=True, timeout=10,
                                  cwd=self.rust_project_path)
            if result.returncode == 0:
                for line in result.stdout.split('\n')[1:]:  # Skip first line
                    if ':' in line:
                        key, value = line.strip().split(':', 1)
                        info[key.strip()] = value.strip()
        except Exception:
            pass

        return info

    def _get_cargo_version(self) -> Optional[str]:
        """Get cargo version string."""
        try:
            result = subprocess.run(['cargo', '--version'],
                                  capture_output=True, text=True, timeout=10,
                                  cwd=self.rust_project_path)
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass

        return None

    def _get_rust_target_triple(self) -> Optional[str]:
        """Get the default Rust target triple."""
        try:
            # This is available in rustc verbose output
            verbose_info = self._get_rustc_verbose_info()
            return verbose_info.get('host')
        except Exception:
            pass

        return None

    @property
    def git_repo(self) -> Optional[git.Repo]:
        """Get git repository object, cached."""
        if self._git_repo is None:
            try:
                # Look for git repo starting from rust project and going up
                search_path = self.rust_project_path
                while search_path.parent != search_path:  # Not at filesystem root
                    if (search_path / '.git').exists():
                        self._git_repo = git.Repo(search_path)
                        break
                    search_path = search_path.parent
            except Exception:
                pass

        return self._git_repo

    def _get_git_info(self) -> Optional[Dict[str, Any]]:
        """Get git repository information."""
        repo = self.git_repo
        if not repo:
            return None

        info = {}

        try:
            # Get current commit
            info['commit_hash'] = repo.head.commit.hexsha

            # Get current branch
            try:
                info['branch'] = repo.active_branch.name
            except Exception:
                info['branch'] = 'detached'

            # Check if working directory is clean
            info['is_clean'] = not repo.is_dirty()

            # Get status summary
            if repo.is_dirty():
                status_summary = []
                if repo.index.diff(None):
                    status_summary.append('modified files')
                if repo.untracked_files:
                    status_summary.append('untracked files')
                if repo.index.diff('HEAD'):
                    status_summary.append('staged changes')
                info['status_summary'] = status_summary
            else:
                info['status_summary'] = ['clean']

            # Get remote URL (if available)
            try:
                if repo.remotes:
                    info['remote_url'] = list(repo.remotes[0].urls)[0]
            except Exception:
                pass

        except Exception:
            pass

        return info

    def _get_relevant_env_vars(self) -> Dict[str, str]:
        """Get environment variables that affect Rust builds."""
        relevant_vars = [
            'RUSTFLAGS', 'CARGO_TARGET_DIR', 'RUST_BACKTRACE',
            'CC', 'CXX', 'AR', 'LINKER',
            'PATH', 'LD_LIBRARY_PATH', 'DYLD_LIBRARY_PATH'
        ]

        env_vars = {}
        for var in relevant_vars:
            value = os.environ.get(var)
            if value is not None:
                env_vars[var] = value

        return env_vars

    def _get_cargo_target_dir(self) -> Optional[str]:
        """Get the cargo target directory."""
        try:
            # First check environment variable
            if 'CARGO_TARGET_DIR' in os.environ:
                return os.environ['CARGO_TARGET_DIR']

            # Then check if there's a target dir in the project
            target_dir = self.rust_project_path / 'target'
            if target_dir.exists():
                return str(target_dir)

        except Exception:
            pass

        return None

    def _get_cpu_temperature(self) -> Optional[float]:
        """Get CPU temperature if available."""
        try:
            # This is very platform-specific and may not work everywhere
            if hasattr(psutil, 'sensors_temperatures'):
                temps = psutil.sensors_temperatures()
                if 'coretemp' in temps:
                    # Intel CPU temperature
                    return temps['coretemp'][0].current
                elif 'k8temp' in temps or 'k10temp' in temps:
                    # AMD CPU temperature
                    sensor = 'k10temp' if 'k10temp' in temps else 'k8temp'
                    return temps[sensor][0].current
        except Exception:
            pass

        return None

    def _get_power_info(self) -> Optional[Dict[str, Any]]:
        """Get power source and battery information."""
        try:
            if hasattr(psutil, 'sensors_battery'):
                battery = psutil.sensors_battery()
                if battery:
                    return {
                        'source': 'ac' if battery.power_plugged else 'battery',
                        'battery_percent': battery.percent
                    }
                else:
                    # No battery detected, assume AC power
                    return {'source': 'ac', 'battery_percent': None}
        except Exception:
            pass

        return None


class ComprehensiveMetadata(BaseModel):
    """
    ## Complete Metadata Package

    This brings together all types of metadata into a single structure
    that can be easily serialized, stored, and analyzed alongside
    benchmark results.

    ### Usage with Results Storage

    This metadata package is designed to be stored as JSON alongside
    benchmark results, providing complete context for later analysis:

    ```python
    metadata = collector.collect_all()

    # Save as structured JSON files
    metadata.save_json(results_dir / "metadata")

    # Or save as single comprehensive file
    with open(results_dir / "comprehensive_metadata.json", "w") as f:
        json.dump(metadata.dict(), f, indent=2, default=str)
    ```
    """

    system_info: SystemInfo
    build_info: BuildInfo
    source_hashes: SourceHashes
    execution_context: ExecutionContext

    # Overall collection metadata
    collection_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata_version: str = "1.0.0"

    def save_json(self, base_dir: Path) -> None:
        """
        ## Save Metadata as Structured JSON Files

        Save each metadata type as a separate JSON file in the specified
        directory. This makes it easy for analysis tools to load just
        the metadata they need.
        """
        base_dir = Path(base_dir)
        base_dir.mkdir(parents=True, exist_ok=True)

        # Save each metadata type separately
        with open(base_dir / "system-info.json", "w") as f:
            json.dump(self.system_info.dict(), f, indent=2, default=str)

        with open(base_dir / "build-info.json", "w") as f:
            json.dump(self.build_info.dict(), f, indent=2, default=str)

        with open(base_dir / "source-hashes.json", "w") as f:
            json.dump(self.source_hashes.dict(), f, indent=2, default=str)

        with open(base_dir / "execution-context.json", "w") as f:
            json.dump(self.execution_context.dict(), f, indent=2, default=str)

        # Save comprehensive metadata
        with open(base_dir / "comprehensive.json", "w") as f:
            json.dump(self.dict(), f, indent=2, default=str)

    @classmethod
    def load_json(cls, base_dir: Path) -> 'ComprehensiveMetadata':
        """
        ## Load Metadata from JSON Files

        Load a complete metadata package from a directory containing
        the structured JSON files created by save_json().
        """
        base_dir = Path(base_dir)

        # Try to load comprehensive file first
        comprehensive_file = base_dir / "comprehensive.json"
        if comprehensive_file.exists():
            with open(comprehensive_file, "r") as f:
                data = json.load(f)
            return cls.parse_obj(data)

        # Otherwise load individual files
        with open(base_dir / "system-info.json", "r") as f:
            system_info = SystemInfo.parse_obj(json.load(f))

        with open(base_dir / "build-info.json", "r") as f:
            build_info = BuildInfo.parse_obj(json.load(f))

        with open(base_dir / "source-hashes.json", "r") as f:
            source_hashes = SourceHashes.parse_obj(json.load(f))

        with open(base_dir / "execution-context.json", "r") as f:
            execution_context = ExecutionContext.parse_obj(json.load(f))

        return cls(
            system_info=system_info,
            build_info=build_info,
            source_hashes=source_hashes,
            execution_context=execution_context
        )

    def get_run_identifier(self) -> str:
        """
        ## Generate Unique Run Identifier

        Create a unique identifier for this benchmark run based on
        the metadata. This identifier can be used for organizing
        results and detecting when re-runs are necessary.

        Format: {hostname}_{source_hash}_{rustc_version}
        """
        # Sanitize hostname
        hostname = self.system_info.hostname or "unknown"
        hostname = hostname.lower().replace(".", "_").replace("-", "_")

        # Get short source hash
        source_hash = (self.source_hashes.combined_hash or "unknown")[:8]

        # Get rustc version (extract version number from full string)
        rustc_version = "unknown"
        if self.build_info.rustc_version:
            import re
            match = re.search(r'rustc (\S+)', self.build_info.rustc_version)
            if match:
                rustc_version = match.group(1).replace('.', '_').replace('-', '_')

        return f"{hostname}_{source_hash}_{rustc_version}"

    def should_rerun_benchmarks(self, previous_metadata: 'ComprehensiveMetadata') -> bool:
        """
        ## Determine if Benchmarks Need Re-running

        Compare this metadata with previous run metadata to determine
        if benchmark results can be reused or if re-running is necessary.

        We require re-runs when:
        - Source code has changed (different combined hash)
        - Rust compiler version has changed
        - Different system architecture

        We allow reuse when only system load or execution context differs.
        """
        # Source code changes always require re-run
        if (self.source_hashes.combined_hash !=
            previous_metadata.source_hashes.combined_hash):
            return True

        # Compiler version changes require re-run
        if (self.build_info.rustc_version !=
            previous_metadata.build_info.rustc_version):
            return True

        # Different system architecture requires re-run
        if (self.system_info.cpu_architecture !=
            previous_metadata.system_info.cpu_architecture):
            return True

        # Same system, same source, same compiler - can reuse
        return False


# Convenience functions for common usage patterns

def collect_metadata(rust_project_path: Path) -> ComprehensiveMetadata:
    """
    ## Convenience Function for Complete Metadata Collection

    This is the simplest way to collect comprehensive metadata for a benchmark run.
    It creates a collector, gathers all metadata types, and returns the complete
    metadata package.

    Args:
        rust_project_path: Path to the Rust project being benchmarked

    Returns:
        Complete metadata package ready for storage

    Example:
        ```python
        metadata = collect_metadata(Path("rust_project"))
        metadata.save_json(results_dir / "metadata")
        ```
    """
    collector = MetadataCollector(rust_project_path)
    return collector.collect_all()


def quick_system_check() -> Dict[str, Any]:
    """
    ## Quick System Compatibility Check

    Perform a fast check of system capabilities that might affect benchmark
    success. This can be used to warn users about potential issues before
    starting long benchmark runs.

    Returns:
        Dictionary with system info and compatibility warnings
    """
    info = {"warnings": [], "system": {}}

    try:
        # Check available memory
        memory = psutil.virtual_memory()
        info["system"]["memory_gb"] = memory.total // (1024**3)

        if memory.available < 1024**3:  # Less than 1GB available
            info["warnings"].append("Low available memory may affect benchmark timing")

        # Check CPU cores
        cores = psutil.cpu_count(logical=True)
        info["system"]["cpu_cores"] = cores

        if cores < 2:
            info["warnings"].append("Single-core system may have unstable benchmark timing")

        # Check system load
        if hasattr(os, 'getloadavg'):
            load = os.getloadavg()[0]
            info["system"]["load_average_1min"] = load

            if load > cores:
                info["warnings"].append("High system load may affect benchmark accuracy")

        # Check for Rust toolchain
        try:
            result = subprocess.run(['rustc', '--version'],
                                  capture_output=True, timeout=5)
            if result.returncode == 0:
                info["system"]["rustc_available"] = True
            else:
                info["warnings"].append("Rust compiler not found or not working")
        except Exception:
            info["warnings"].append("Cannot execute rustc command")

    except Exception as e:
        info["warnings"].append(f"System check failed: {e}")

    return info


def format_metadata_summary(metadata: ComprehensiveMetadata) -> str:
    """
    ## Format Human-Readable Metadata Summary

    Create a concise, human-readable summary of the metadata for logging
    and progress reporting during benchmark runs.

    Args:
        metadata: Complete metadata package

    Returns:
        Multi-line string with formatted summary
    """
    lines = []

    # System summary
    lines.append("=== System Information ===")
    lines.append(f"Hostname: {metadata.system_info.hostname}")
    lines.append(f"OS: {metadata.system_info.os_name} {metadata.system_info.os_release}")

    if metadata.system_info.cpu_model:
        lines.append(f"CPU: {metadata.system_info.cpu_model}")

    if metadata.system_info.cpu_cores_physical:
        lines.append(f"Cores: {metadata.system_info.cpu_cores_physical} physical, "
                    f"{metadata.system_info.cpu_cores_logical} logical")

    if metadata.system_info.memory_total_bytes:
        memory_gb = metadata.system_info.memory_total_bytes // (1024**3)
        lines.append(f"Memory: {memory_gb} GB")

    # Build information
    lines.append("\n=== Build Information ===")
    if metadata.build_info.rustc_version:
        lines.append(f"Rust: {metadata.build_info.rustc_version}")

    if metadata.build_info.git_commit_hash:
        short_hash = metadata.build_info.git_commit_hash[:8]
        branch = metadata.build_info.git_branch or "unknown"
        clean = "clean" if metadata.build_info.git_is_clean else "dirty"
        lines.append(f"Git: {branch} @ {short_hash} ({clean})")

    # Source and execution context
    lines.append("\n=== Benchmark Context ===")
    if metadata.source_hashes.combined_hash:
        lines.append(f"Source hash: {metadata.source_hashes.combined_hash}")

    lines.append(f"Run ID: {metadata.get_run_identifier()}")

    if metadata.execution_context.cpu_percent_current:
        lines.append(f"CPU load: {metadata.execution_context.cpu_percent_current:.1f}%")

    return "\n".join(lines)
