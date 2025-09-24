"""
# Results Storage and Management for Benchfind Orchestration

This module provides comprehensive storage management for benchmark results,
including intelligent caching, structured organization, and cross-run indexing.
The storage system is designed to handle large volumes of benchmark data while
avoiding expensive re-runs and supporting collaborative analysis workflows.

## The Storage Challenge

Benchmark results present several storage challenges:

1. **Volume**: Complete benchmark runs can generate gigabytes of data
2. **Deduplication**: Avoid re-running expensive benchmarks when unchanged
3. **Organization**: Structure data to support analysis across systems/time
4. **Integrity**: Ensure results are complete and uncorrupted
5. **Portability**: Enable sharing results between systems and collaborators

## Our Approach: Structured Result Organization

Rather than ad-hoc storage, we use a deterministic organization scheme:

- **Run Identification**: Unique IDs based on system, source, and compiler
- **Structured Directories**: Consistent layout for metadata, results, and analysis
- **Intelligent Caching**: Skip expensive operations when results are current
- **Index Management**: Global index for efficient cross-run queries
- **Data Lifecycle**: Policies for cleanup, archiving, and long-term storage

## Design Philosophy

### **Deterministic Organization**
Same inputs always produce the same storage location, enabling reliable caching
and result sharing between team members.

### **Preserve Everything Important**
We err on the side of keeping too much data rather than losing something that
might be valuable for analysis later.

### **Fail Fast on Storage Issues**
Storage problems usually indicate serious system issues, so we fail fast
rather than silently losing data.

### **Support Future Analysis**
The storage format should support analysis tools we haven't built yet,
including statistical analysis, regression detection, and performance comparison.
"""

import hashlib
import json
import os
import platform
import shutil
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Union, Tuple
import logging

from .config import Config, ConfigurationLoader
from .metadata import SystemInfo, BuildInfo, ExecutionContext, ComprehensiveMetadata


logger = logging.getLogger(__name__)


@dataclass
class RunIdentifier:
    """
    ## Unique Run Identification

    Represents a unique benchmark run based on the three key factors that
    determine whether results can be reused:
    1. **hostname**: The system where benchmarks were run
    2. **source_hash**: Hash of benchmark-relevant source code
    3. **rustc_version**: Rust compiler version (affects code generation)
    """
    hostname: str
    source_hash: str
    rustc_version: str

    @property
    def run_id(self) -> str:
        """Get the complete run identifier string"""
        return f"{self.hostname}_{self.source_hash}_{self.rustc_version}"

    @classmethod
    def from_current_system(cls, config: Config, project_root: Path) -> 'RunIdentifier':
        """Create run identifier for current system and source state"""
        hostname = cls._sanitize_hostname(platform.node())
        source_hash = cls._calculate_source_hash(config, project_root)
        rustc_version = cls._get_rustc_version()

        return cls(
            hostname=hostname,
            source_hash=source_hash,
            rustc_version=rustc_version
        )

    @staticmethod
    def _sanitize_hostname(hostname: str) -> str:
        """Sanitize hostname for use in filesystem paths"""
        # Get config for sanitization rules
        config = ConfigurationLoader().load_storage_config()

        sanitized = hostname.lower()

        # Replace problematic characters
        for char in config.get('run_identification', {}).get('sanitization', {}).get('replace_chars', '.-'):
            sanitized = sanitized.replace(char, '_')

        # Remove non-alphanumeric characters except underscores
        if config.get('run_identification', {}).get('sanitization', {}).get('remove_special', True):
            sanitized = ''.join(c for c in sanitized if c.isalnum() or c == '_')

        # Truncate if too long
        max_length = config.get('run_identification', {}).get('hostname_max_length', 20)
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]

        return sanitized

    @staticmethod
    def _calculate_source_hash(config: Config, project_root: Path) -> str:
        """Calculate hash of benchmark-relevant source files"""
        hasher = hashlib.sha256()

        # Get source files from config
        storage_config = ConfigurationLoader().load_storage_config()
        source_files = storage_config.get('run_identification', {}).get('source_files', [
            'src/lib.rs',
            'benches/bench_newlines.rs',
            'benches/bench_csv.rs',
            'Cargo.toml'
        ])

        # Hash each file in deterministic order
        for relative_path in sorted(source_files):
            file_path = project_root / relative_path
            if file_path.exists():
                # Add file path to hash for disambiguation
                hasher.update(f"FILE:{relative_path}\n".encode())

                # Add file content
                try:
                    with open(file_path, 'rb') as f:
                        hasher.update(f.read())
                except IOError as e:
                    logger.warning(f"Could not read {file_path} for hashing: {e}")
                    # Add placeholder to ensure hash changes if file becomes unreadable
                    hasher.update(f"UNREADABLE:{relative_path}\n".encode())
            else:
                logger.warning(f"Source file {file_path} not found for hashing")
                # Add placeholder for missing files
                hasher.update(f"MISSING:{relative_path}\n".encode())

        # Return first 8 characters of hex digest
        hash_length = storage_config.get('run_identification', {}).get('source_hash_length', 8)
        return hasher.hexdigest()[:hash_length]

    @staticmethod
    def _get_rustc_version() -> str:
        """Get sanitized Rust compiler version"""
        try:
            import subprocess
            result = subprocess.run(['rustc', '--version'], capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                # Extract version from output like "rustc 1.75.0-nightly (hash date)"
                version_line = result.stdout.strip()
                # Extract just the version part
                if ' ' in version_line:
                    version_part = version_line.split(' ')[1]
                    # Sanitize for filesystem use
                    sanitized = version_part.replace('.', '_').replace('-', '_')
                    return sanitized
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            pass

        # Fallback if rustc is not available or fails
        logger.warning("Could not determine rustc version, using 'unknown'")
        return "unknown"


@dataclass
class StorageLayout:
    """
    ## Storage Directory Layout

    Represents the directory structure for a benchmark run, providing
    typed access to all the expected paths and files.
    """
    run_dir: Path
    metadata_dir: Path
    raw_results_dir: Path
    assembly_extracts_dir: Path
    logs_dir: Path

    @classmethod
    def from_run_id(cls, config: Config, run_id: str) -> 'StorageLayout':
        """Create storage layout for a given run ID"""
        storage_config = ConfigurationLoader().load_storage_config()

        # Get base paths from config
        runs_dir = Path(storage_config.get('paths', {}).get('runs_dir', 'results/runs'))
        run_dir = runs_dir / run_id

        return cls(
            run_dir=run_dir,
            metadata_dir=run_dir / "metadata",
            raw_results_dir=run_dir / "raw-results",
            assembly_extracts_dir=run_dir / "assembly_extracts",
            logs_dir=run_dir / "logs"
        )

    def ensure_directories(self) -> None:
        """Create all required directories"""
        for directory in [self.run_dir, self.metadata_dir, self.raw_results_dir,
                         self.assembly_extracts_dir, self.logs_dir]:
            directory.mkdir(parents=True, exist_ok=True)

    def get_metadata_file(self, filename: str) -> Path:
        """Get path to a metadata file"""
        return self.metadata_dir / filename

    def get_target_assembly_dir(self, target_name: str) -> Path:
        """Get assembly directory for a specific target"""
        return self.assembly_extracts_dir / target_name

    def get_log_file(self, filename: str) -> Path:
        """Get path to a log file"""
        return self.logs_dir / filename


@dataclass
class RunIndex:
    """
    ## Global Run Index

    Maintains an index of all benchmark runs for efficient querying
    and analysis across multiple runs.
    """
    runs: List[Dict[str, Any]] = field(default_factory=list)
    last_updated: str = ""
    schema_version: str = "1.0.0"
    description: str = "Index of all benchmark runs collected by the orchestration system"

    @classmethod
    def load(cls, index_path: Path) -> 'RunIndex':
        """Load existing index or create new one"""
        if index_path.exists():
            try:
                with open(index_path, 'r') as f:
                    data = json.load(f)
                return cls(
                    runs=data.get('runs', []),
                    last_updated=data.get('last_updated', ''),
                    schema_version=data.get('schema_version', '1.0.0'),
                    description=data.get('description', cls.description)
                )
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Could not load index from {index_path}: {e}")
                # Create backup of corrupted index
                backup_path = index_path.with_suffix('.backup')
                if index_path.exists():
                    shutil.copy2(index_path, backup_path)
                    logger.info(f"Backed up corrupted index to {backup_path}")

        return cls()

    def save(self, index_path: Path) -> None:
        """Save index to disk with backup"""
        # Create backup if index exists and it's been a while since last backup
        if index_path.exists():
            should_backup = False
            current_time = time.time()

            # Check if we should create a backup (only if no recent backup exists)
            backup_glob_pattern = f"{index_path.stem}.backup.*"
            existing_backups = sorted(index_path.parent.glob(backup_glob_pattern),
                                    key=lambda x: x.stat().st_mtime, reverse=True)

            if not existing_backups:
                # No backups exist, create one
                should_backup = True
            else:
                # Only backup if the most recent backup is more than 5 minutes old
                latest_backup_time = existing_backups[0].stat().st_mtime
                if current_time - latest_backup_time > 300:  # 5 minutes
                    should_backup = True

            if should_backup:
                backup_path = index_path.with_suffix(f'.backup.{int(current_time)}')
                shutil.copy2(index_path, backup_path)

                # Cleanup old backups (keep last 5)
                backups = sorted(index_path.parent.glob(backup_glob_pattern),
                               key=lambda x: x.stat().st_mtime)
                if len(backups) > 5:
                    for old_backup in backups[:-5]:
                        try:
                            old_backup.unlink()
                        except OSError:
                            pass  # Ignore if file doesn't exist or can't be deleted

        # Save current index
        self.last_updated = datetime.now(timezone.utc).isoformat()
        data = {
            'runs': self.runs,
            'last_updated': self.last_updated,
            'schema_version': self.schema_version,
            'description': self.description
        }

        # Write atomically via temporary file
        temp_path = index_path.with_suffix('.tmp')
        try:
            with open(temp_path, 'w') as f:
                json.dump(data, f, indent=2)
            temp_path.replace(index_path)
        except Exception:
            if temp_path.exists():
                temp_path.unlink()
            raise

    def add_run(self, run_id: str, hostname: str, source_hash: str, rustc_version: str,
                status: str = "in_progress", targets_completed: Optional[List[str]] = None,
                benchmarks_completed: Optional[List[str]] = None) -> None:
        """Add or update a run in the index"""

        # Find existing entry
        existing_entry = None
        for entry in self.runs:
            if entry.get('run_id') == run_id:
                existing_entry = entry
                break

        if existing_entry:
            # Update existing entry in place (preserve original timestamp)
            existing_entry.update({
                'status': status,
                'targets_completed': targets_completed or existing_entry.get('targets_completed', []),
                'benchmarks_completed': benchmarks_completed or existing_entry.get('benchmarks_completed', [])
            })
        else:
            # Create new entry with current timestamp
            timestamp = datetime.now(timezone.utc).isoformat()
            self.runs.append({
                'run_id': run_id,
                'timestamp': timestamp,
                'hostname': hostname,
                'source_hash': source_hash,
                'rustc_version': rustc_version,
                'status': status,
                'targets_completed': targets_completed or [],
                'benchmarks_completed': benchmarks_completed or []
            })

        # Sort by timestamp (newest first)
        self.runs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get run information by ID"""
        for run in self.runs:
            if run.get('run_id') == run_id:
                return run
        return None

    def find_runs(self, hostname: Optional[str] = None, source_hash: Optional[str] = None,
                  rustc_version: Optional[str] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Find runs matching criteria"""
        results = []
        for run in self.runs:
            if hostname and run.get('hostname') != hostname:
                continue
            if source_hash and run.get('source_hash') != source_hash:
                continue
            if rustc_version and run.get('rustc_version') != rustc_version:
                continue
            if status and run.get('status') != status:
                continue
            results.append(run)
        return results


class ResultsStorage:
    """
    ## Results Storage Manager

    High-level interface for storing and retrieving benchmark results.
    Handles caching logic, data organization, and index management.
    """

    def __init__(self, config: Config, project_root: Path):
        self.config = config
        self.project_root = project_root
        self.storage_config = ConfigurationLoader().load_storage_config()

        # Initialize paths
        self.results_base = Path(self.storage_config.get('paths', {}).get('results_base', 'results'))
        self.runs_dir = Path(self.storage_config.get('paths', {}).get('runs_dir', 'results/runs'))
        self.index_path = Path(self.storage_config.get('paths', {}).get('index_file', 'results/index.json'))

        # Ensure base directories exist
        self.results_base.mkdir(parents=True, exist_ok=True)
        self.runs_dir.mkdir(parents=True, exist_ok=True)

        # Load index
        self.index = RunIndex.load(self.index_path)

    def get_current_run_id(self) -> RunIdentifier:
        """Get run identifier for current system and source state"""
        return RunIdentifier.from_current_system(self.config, self.project_root)

    def get_storage_layout(self, run_id: Union[str, RunIdentifier]) -> StorageLayout:
        """Get storage layout for a run"""
        if isinstance(run_id, RunIdentifier):
            run_id_str = run_id.run_id
        else:
            run_id_str = run_id

        return StorageLayout.from_run_id(self.config, run_id_str)

    def check_existing_results(self, run_id: RunIdentifier, targets: List[str]) -> Tuple[Set[str], Set[str]]:
        """
        Check which targets already have results.
        Returns (targets_with_results, targets_needing_runs)
        """
        layout = self.get_storage_layout(run_id)
        targets_with_results = set()

        if layout.run_dir.exists():
            # Check for benchmark results
            criterion_dir = layout.raw_results_dir / "criterion"
            if criterion_dir.exists():
                # Look for completed benchmark results
                # This is a simplified check - we could make it more sophisticated
                for target in targets:
                    target_assembly_dir = layout.get_target_assembly_dir(target)
                    if target_assembly_dir.exists() and list(target_assembly_dir.glob("*.json")):
                        targets_with_results.add(target)

        targets_needing_runs = set(targets) - targets_with_results
        return targets_with_results, targets_needing_runs

    def should_skip_benchmark(self, run_id: RunIdentifier, target: str) -> bool:
        """Check if we should skip benchmarking for a target based on caching policy"""
        caching_config = self.storage_config.get('caching', {})

        if not caching_config.get('skip_benchmark_if_exists', True):
            return False

        layout = self.get_storage_layout(run_id)
        target_assembly_dir = layout.get_target_assembly_dir(target)

        # Check if results exist and are complete
        if not target_assembly_dir.exists():
            return False

        # Look for key result files
        analysis_file = target_assembly_dir / "simd-analysis.json"
        metadata_file = target_assembly_dir / "extraction-metadata.json"

        if not (analysis_file.exists() and metadata_file.exists()):
            return False

        # Check cache age if configured
        max_age_days = caching_config.get('max_cache_age_days', 90)
        if max_age_days > 0:
            age_days = (time.time() - analysis_file.stat().st_mtime) / (24 * 3600)
            if age_days > max_age_days:
                logger.info(f"Cache for {run_id.run_id}/{target} is {age_days:.1f} days old (max {max_age_days})")
                return False

        return True

    def start_run(self, run_id: RunIdentifier, targets: List[str], benchmarks: List[str]) -> StorageLayout:
        """Initialize storage for a new benchmark run"""
        layout = self.get_storage_layout(run_id)
        layout.ensure_directories()

        # Update index
        self.index.add_run(
            run_id=run_id.run_id,
            hostname=run_id.hostname,
            source_hash=run_id.source_hash,
            rustc_version=run_id.rustc_version,
            status="in_progress",
            targets_completed=[],
            benchmarks_completed=[]
        )
        self._save_index()

        logger.info(f"Initialized storage for run {run_id.run_id}")
        return layout

    def store_metadata(self, layout: StorageLayout, system_info: SystemInfo,
                      build_info: BuildInfo, execution_context: ExecutionContext,
                      source_hash: str) -> None:
        """Store all metadata for a run"""

        # Store system info
        system_file = layout.get_metadata_file("system-info.json")
        with open(system_file, 'w') as f:
            json.dump(system_info.dict(), f, indent=2, default=str)

        # Store build info
        build_file = layout.get_metadata_file("build-info.json")
        with open(build_file, 'w') as f:
            json.dump(build_info.dict(), f, indent=2, default=str)

        # Store execution context as run config
        run_file = layout.get_metadata_file("run-config.json")
        with open(run_file, 'w') as f:
            json.dump(execution_context.dict(), f, indent=2, default=str)

        # Store source hashes
        source_hashes = {
            'individual_files': {},
            'combined_hash': source_hash,
            'calculation_timestamp': datetime.now(timezone.utc).isoformat()
        }

        # Calculate individual file hashes
        storage_config = ConfigurationLoader().load_storage_config()
        source_files = storage_config.get('run_identification', {}).get('source_files', [])

        for relative_path in source_files:
            file_path = self.project_root / relative_path
            if file_path.exists():
                try:
                    with open(file_path, 'rb') as f:
                        file_hash = hashlib.sha256(f.read()).hexdigest()
                    source_hashes['individual_files'][relative_path] = file_hash
                except IOError:
                    source_hashes['individual_files'][relative_path] = None

        hashes_file = layout.get_metadata_file("source-hashes.json")
        with open(hashes_file, 'w') as f:
            json.dump(source_hashes, f, indent=2)

    def copy_benchmark_results(self, layout: StorageLayout, rust_target_dir: Path) -> None:
        """Copy benchmark results from Rust target directory"""
        criterion_source = rust_target_dir / "criterion"
        criterion_dest = layout.raw_results_dir / "criterion"

        if not criterion_source.exists():
            logger.warning(f"No criterion results found in {criterion_source}")
            return

        # Get exclusion patterns
        exclude_patterns = self.storage_config.get('data_extraction', {}).get('criterion_results', {}).get('exclude_patterns', [
            "**/*.html", "**/report/**", "**/.criterion/**"
        ])

        self._copy_directory_with_exclusions(criterion_source, criterion_dest, exclude_patterns)
        logger.info(f"Copied benchmark results to {criterion_dest}")

    def store_assembly_analysis(self, layout: StorageLayout, target: str,
                              analysis_data: Dict[str, Any],
                              assembly_files: Optional[Dict[str, str]] = None) -> None:
        """Store assembly analysis results for a target"""
        target_dir = layout.get_target_assembly_dir(target)
        target_dir.mkdir(parents=True, exist_ok=True)

        # Store SIMD analysis
        analysis_file = target_dir / "simd-analysis.json"
        with open(analysis_file, 'w') as f:
            json.dump(analysis_data, f, indent=2)

        # Store extraction metadata
        metadata = {
            'target': target,
            'extraction_timestamp': datetime.now(timezone.utc).isoformat(),
            'analysis_version': '1.0.0',
            'files_extracted': list(assembly_files.keys()) if assembly_files else []
        }

        metadata_file = target_dir / "extraction-metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)

        # Store assembly files if provided
        if assembly_files:
            for filename, content in assembly_files.items():
                assembly_file = target_dir / filename
                with open(assembly_file, 'w') as f:
                    f.write(content)

        logger.info(f"Stored assembly analysis for target {target}")

    def complete_run(self, run_id: RunIdentifier, targets_completed: List[str],
                    benchmarks_completed: List[str], success: bool = True) -> None:
        """Mark a run as completed and update index"""
        status = "completed" if success else "failed"

        self.index.add_run(
            run_id=run_id.run_id,
            hostname=run_id.hostname,
            source_hash=run_id.source_hash,
            rustc_version=run_id.rustc_version,
            status=status,
            targets_completed=targets_completed,
            benchmarks_completed=benchmarks_completed
        )
        self._save_index()

        logger.info(f"Completed run {run_id.run_id} with status: {status}")

    def cleanup_incomplete_runs(self) -> None:
        """Clean up runs that were interrupted"""
        if not self.storage_config.get('caching', {}).get('auto_cleanup_incomplete_runs', True):
            return

        # Find runs marked as in_progress
        incomplete_runs = self.index.find_runs(status="in_progress")

        for run_info in incomplete_runs:
            run_id = run_info['run_id']
            layout = self.get_storage_layout(run_id)

            # Check if run directory exists and has any content
            if layout.run_dir.exists():
                # Check if it looks like it was actually interrupted vs just started
                has_results = any([
                    layout.raw_results_dir.exists() and list(layout.raw_results_dir.rglob("*.json")),
                    layout.assembly_extracts_dir.exists() and list(layout.assembly_extracts_dir.rglob("*.json"))
                ])

                if has_results:
                    # Mark as failed rather than deleting
                    self.index.add_run(
                        run_id=run_id,
                        hostname=run_info['hostname'],
                        source_hash=run_info['source_hash'],
                        rustc_version=run_info['rustc_version'],
                        status="interrupted",
                        targets_completed=run_info.get('targets_completed', []),
                        benchmarks_completed=run_info.get('benchmarks_completed', [])
                    )
                    logger.info(f"Marked interrupted run {run_id} as 'interrupted'")
                else:
                    # Remove empty/just-started run
                    if layout.run_dir.exists():
                        shutil.rmtree(layout.run_dir)
                    self.index.runs = [r for r in self.index.runs if r.get('run_id') != run_id]
                    logger.info(f"Cleaned up empty run directory for {run_id}")

        self._save_index()

    def get_storage_statistics(self) -> Dict[str, Any]:
        """Get statistics about stored results"""
        stats = {
            'total_runs': len(self.index.runs),
            'completed_runs': len(self.index.find_runs(status="completed")),
            'failed_runs': len(self.index.find_runs(status="failed")),
            'in_progress_runs': len(self.index.find_runs(status="in_progress")),
            'storage_size_gb': 0.0,
            'oldest_run': None,
            'newest_run': None
        }

        # Calculate storage size
        if self.results_base.exists():
            total_size = sum(f.stat().st_size for f in self.results_base.rglob('*') if f.is_file())
            stats['storage_size_gb'] = total_size / (1024**3)

        # Find oldest and newest runs
        if self.index.runs:
            sorted_runs = sorted(self.index.runs, key=lambda x: x.get('timestamp', ''))
            stats['oldest_run'] = sorted_runs[0].get('timestamp')
            stats['newest_run'] = sorted_runs[-1].get('timestamp')

        return stats

    def _copy_directory_with_exclusions(self, source: Path, dest: Path, exclude_patterns: List[str]) -> None:
        """Copy directory while excluding certain patterns"""
        import fnmatch

        def should_exclude(path: Path) -> bool:
            path_str = str(path)
            for pattern in exclude_patterns:
                if fnmatch.fnmatch(path_str, pattern) or fnmatch.fnmatch(path.name, pattern):
                    return True
            return False

        dest.mkdir(parents=True, exist_ok=True)

        for item in source.rglob('*'):
            if should_exclude(item):
                continue

            relative_path = item.relative_to(source)
            dest_path = dest / relative_path

            if item.is_dir():
                dest_path.mkdir(parents=True, exist_ok=True)
            elif item.is_file():
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, dest_path)

    def list_runs(self) -> List[RunIdentifier]:
        """
        List all stored benchmark runs.

        Returns:
            List of RunIdentifier objects for all stored runs (deduplicated by run_id)
        """
        # Deduplicate by run_id, keeping the latest timestamp for each
        unique_runs = {}

        for run_info in self.index.runs:
            try:
                run_id_str = run_info['run_id']
                timestamp_str = run_info['timestamp']

                # If we haven't seen this run_id, or this entry is newer, keep it
                if run_id_str not in unique_runs:
                    unique_runs[run_id_str] = run_info
                else:
                    # Compare timestamps and keep the newer one
                    existing_timestamp = unique_runs[run_id_str]['timestamp']
                    if timestamp_str > existing_timestamp:
                        unique_runs[run_id_str] = run_info

            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"Skipping invalid run entry during deduplication: {e}")
                continue

        # Convert to RunIdentifier objects
        runs = []
        for run_info in unique_runs.values():
            try:
                run_id = RunIdentifier(
                    hostname=run_info['hostname'],
                    source_hash=run_info['source_hash'],
                    rustc_version=run_info['rustc_version']
                )
                # Add additional attributes from index
                run_id.timestamp = datetime.fromisoformat(run_info['timestamp'].replace('Z', '+00:00'))
                run_id.status = run_info.get('status', 'unknown')
                run_id.targets = run_info.get('targets_completed', [])
                runs.append(run_id)
            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"Skipping invalid run entry: {e}")
                continue

        return runs

    def deduplicate_index(self) -> Dict[str, int]:
        """
        Clean up duplicate entries in the index, keeping only the latest entry for each run_id.

        This fixes the issue where the same run_id was getting multiple timestamp entries
        due to the old add_run implementation that recreated entries instead of updating them.

        Returns:
            Dictionary with cleanup statistics
        """
        logger.info("Deduplicating index entries...")

        original_count = len(self.index.runs)
        unique_runs = {}

        # Group by run_id and keep the latest timestamp for each
        for run_info in self.index.runs:
            try:
                run_id_str = run_info['run_id']
                timestamp_str = run_info['timestamp']

                if run_id_str not in unique_runs:
                    unique_runs[run_id_str] = run_info
                else:
                    # Compare timestamps and keep the newer one
                    existing_timestamp = unique_runs[run_id_str]['timestamp']
                    if timestamp_str > existing_timestamp:
                        unique_runs[run_id_str] = run_info

            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"Skipping malformed run entry during deduplication: {e}")
                continue

        # Replace the runs list with deduplicated entries
        self.index.runs = list(unique_runs.values())

        # Sort by timestamp (newest first)
        self.index.runs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

        # Save the cleaned index
        self.index.save(self.index_path)

        cleaned_count = len(self.index.runs)
        removed_count = original_count - cleaned_count

        logger.info(f"Index deduplication completed: {original_count} → {cleaned_count} entries ({removed_count} duplicates removed)")

        return {
            'original_count': original_count,
            'cleaned_count': cleaned_count,
            'duplicates_removed': removed_count
        }

    def _save_index(self) -> None:
        """Save the index to disk"""
        try:
            self.index.save(self.index_path)
        except Exception as e:
            logger.error(f"Failed to save index: {e}")
            raise
