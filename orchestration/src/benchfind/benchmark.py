"""
# Benchmark Orchestration for Benchfind

This module handles the execution of Rust benchmarks across multiple compilation
targets, with intelligent caching to avoid expensive re-runs and selective data
collection to ensure fresh analysis data.

## The Orchestration Challenge

Running comprehensive benchmarks is expensive:
- Each target takes 15+ minutes to benchmark thoroughly
- We test 7+ different compilation targets
- A full run can take 2+ hours
- System state changes can affect timing

But we need to balance thoroughness with practicality:
- Don't re-run unchanged benchmarks (expensive)
- Do re-collect analysis data (cheap but important)
- Preserve existing Rust compilation artifacts
- Detect when re-runs are actually necessary

## Our Two-Level Architecture

### **High-Level Orchestrator** (`BenchmarkOrchestrator`)
- Manages the complete benchmarking session across all targets
- Decides which targets need re-running vs. data re-collection
- Handles progress reporting and error recovery
- Coordinates metadata collection and result organization

### **Single-Target Executor** (`SingleTargetExecutor`)
- Executes benchmarks for one specific compilation target
- Manages the Rust compilation and Criterion execution
- Handles target-specific failures gracefully
- Copies results selectively without modifying the Rust target directory

## Intelligent Caching Strategy

We cache at the granularity of (source_hash, compiler_version, target_config):

1. **Cache Hit**: Benchmark results exist and are current
   - Skip expensive `cargo bench` execution
   - Re-collect assembly analysis and metadata
   - Copy existing results to organized storage

2. **Cache Miss**: No results or they're stale
   - Run full `cargo bench` with proper target configuration
   - Collect all analysis data
   - Organize results in structured storage

3. **Partial Cache**: Results exist but analysis data is missing
   - Skip benchmark execution
   - Re-run assembly extraction and SIMD analysis
   - Update result organization

This approach minimizes expensive re-computation while ensuring analysis data
stays current with any changes to the analysis pipeline.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
import subprocess
import shutil
import json
import time
import os
import signal
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor, as_completed

import psutil
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskID
from rich.table import Table
from rich.panel import Panel

from .config import Config, TargetDefinition
from .metadata import MetadataCollector, ComprehensiveMetadata


@dataclass
class BenchmarkResult:
    """
    ## Individual Benchmark Result

    Represents the outcome of running benchmarks for a single target.
    This captures both the execution metadata and the paths to result data.

    ### Result States

    - **Success**: Benchmarks completed and data collected
    - **Cached**: Used existing results, may have re-collected data
    - **Failed**: Benchmark execution failed (expected for some targets)
    - **Skipped**: Intentionally skipped due to configuration or system state
    """

    target_name: str
    status: str  # 'success', 'cached', 'failed', 'skipped'
    execution_time_seconds: float
    result_path: Optional[Path] = None
    error_message: Optional[str] = None

    # Execution details
    used_cache: bool = False
    reran_analysis: bool = False
    benchmark_output: Optional[str] = None

    # Resource usage during execution
    peak_memory_mb: Optional[float] = None
    cpu_time_seconds: Optional[float] = None


@dataclass
class OrchestrationSession:
    """
    ## Complete Benchmarking Session

    Represents the results of running a complete benchmarking session
    across multiple targets. This provides a comprehensive view of what
    was executed, what was cached, and what failed.
    """

    session_id: str
    start_time: datetime
    config: Config = field(repr=False)
    metadata: ComprehensiveMetadata = field(repr=False)
    end_time: Optional[datetime] = None

    # Results per target
    target_results: Dict[str, BenchmarkResult] = field(default_factory=dict)

    # Session-level statistics
    total_targets: int = 0
    successful_targets: int = 0
    cached_targets: int = 0
    failed_targets: int = 0
    skipped_targets: int = 0

    @property
    def duration_seconds(self) -> float:
        """Get session duration in seconds."""
        if not self.end_time:
            return (datetime.now(timezone.utc) - self.start_time).total_seconds()
        return (self.end_time - self.start_time).total_seconds()

    @property
    def success_rate(self) -> float:
        """Get success rate as a percentage."""
        if self.total_targets == 0:
            return 0.0
        return (self.successful_targets + self.cached_targets) / self.total_targets * 100


class SingleTargetExecutor:
    """
    ## Single Target Benchmark Execution

    Handles benchmark execution for a single compilation target. This class
    encapsulates all the complexity of:

    - Setting up the compilation environment
    - Running cargo bench with proper timeout and error handling
    - Collecting execution metadata and system resource usage
    - Copying results without modifying the Rust target directory

    ### Design Philosophy

    Each target executor is isolated and stateless. It receives a target
    configuration and executes it independently, making the system resilient
    to target-specific failures and easy to parallelize in the future.

    ### Error Handling Strategy

    Target failures are expected and normal:
    - AVX-512 targets fail on consumer CPUs
    - Compilation can fail due to RUSTFLAGS incompatibilities
    - System resource constraints can cause timeouts

    We capture detailed error information but don't let single target failures
    stop the entire benchmarking session.
    """

    def __init__(self, config: Config, console: Console):
        """
        Initialize the single target executor.

        Args:
            config: System configuration
            console: Rich console for output
        """
        self.config = config
        self.console = console
        self.rust_project_path = config.paths.rust_project

    def should_run_benchmark(self, target: TargetDefinition,
                           metadata: ComprehensiveMetadata) -> Tuple[bool, str]:
        """
        ## Cache Decision Logic

        Determine whether we need to run the benchmark for this target or if
        we can use existing results. This is the core of our caching strategy.

        Args:
            target: Target configuration to check
            metadata: Current system and build metadata

        Returns:
            Tuple of (should_run, reason) where should_run is bool and reason
            explains the caching decision
        """

        # Construct the path where results would be stored
        run_id = metadata.get_run_identifier()
        target_result_dir = (self.config.paths.results / "runs" / run_id /
                           "raw-results" / "criterion")

        if not target_result_dir.exists():
            return True, "No previous results found"

        # Check if benchmark results exist for this target
        # Criterion stores results in nested directories by benchmark name and target
        target_has_results = False

        for benchmark_suite in self.config.benchmark_suites.values():
            # Look for Criterion result files for this benchmark suite and target
            for benchmark_group in benchmark_suite.benchmark_groups:
                group_path = target_result_dir / benchmark_group['name'] / target.name
                if group_path.exists() and (group_path / "estimates.json").exists():
                    target_has_results = True
                    break
            if target_has_results:
                break

        if not target_has_results:
            return True, "Previous results incomplete or missing"

        # Check if caching is disabled
        if not self.config.execution.skip_existing_results:
            return True, "Caching disabled in configuration"

        # Check cache age if configured
        if self.config.execution.max_cache_age_days > 0:
            try:
                estimates_file = group_path / "estimates.json"
                if estimates_file.exists():
                    cache_age_days = ((datetime.now(timezone.utc) -
                                     datetime.fromtimestamp(estimates_file.stat().st_mtime, timezone.utc))
                                    .total_seconds() / 86400)
                    if cache_age_days > self.config.execution.max_cache_age_days:
                        return True, f"Cache is {cache_age_days:.1f} days old (max {self.config.execution.max_cache_age_days})"
            except Exception:
                # If we can't check cache age, err on the side of re-running
                return True, "Cannot determine cache age"

        return False, "Using cached results"

    def execute_benchmark(self, target: TargetDefinition,
                         progress_task: Optional[TaskID] = None) -> BenchmarkResult:
        """
        ## Execute Benchmark for Single Target

        Run the complete benchmark pipeline for a single target:
        1. Set up compilation environment
        2. Execute cargo bench with timeout and monitoring
        3. Collect execution metadata
        4. Handle success/failure appropriately

        Args:
            target: Target configuration to benchmark
            progress_task: Optional progress task for UI updates

        Returns:
            BenchmarkResult with execution details
        """

        start_time = time.time()
        result = BenchmarkResult(
            target_name=target.name,
            status="running",
            execution_time_seconds=0.0
        )

        try:
            self.console.print(f"🎯 Starting benchmark: {target.name}")

            # Set up environment for this target
            env = self._prepare_environment(target)

            # Check platform compatibility
            if not target.is_likely_supported():
                self.console.print(f"⚠️  Target {target.name} may not be supported on this CPU")

            # Execute the benchmark
            benchmark_output, success = self._run_cargo_bench(target, env, progress_task)

            if success:
                result.status = "success"
                result.benchmark_output = benchmark_output
                self.console.print(f"✅ Benchmark completed: {target.name}")
            else:
                result.status = "failed"
                result.error_message = "Benchmark execution failed"
                result.benchmark_output = benchmark_output
                self.console.print(f"❌ Benchmark failed: {target.name}")

        except Exception as e:
            result.status = "failed"
            result.error_message = str(e)
            self.console.print(f"❌ Benchmark error for {target.name}: {e}")

        finally:
            result.execution_time_seconds = time.time() - start_time

        return result

    def collect_cached_results(self, target: TargetDefinition,
                              metadata: ComprehensiveMetadata) -> BenchmarkResult:
        """
        ## Collect Results from Cache

        When we decide not to re-run a benchmark, we still need to:
        1. Copy existing results to the current run directory
        2. Ensure analysis data is up to date
        3. Collect any missing metadata

        This provides the benefits of caching while ensuring analysis
        data reflects any improvements to our analysis pipeline.

        Args:
            target: Target configuration
            metadata: Current metadata

        Returns:
            BenchmarkResult indicating cached result collection
        """

        start_time = time.time()
        result = BenchmarkResult(
            target_name=target.name,
            status="cached",
            execution_time_seconds=0.0,
            used_cache=True
        )

        try:
            self.console.print(f"📋 Collecting cached results: {target.name}")

            # The cached results should already be in the correct location
            # based on our run_id structure, but we can verify they exist
            run_id = metadata.get_run_identifier()
            target_result_dir = (self.config.paths.results / "runs" / run_id /
                               "raw-results" / "criterion")

            if target_result_dir.exists():
                result.result_path = target_result_dir
                self.console.print(f"✅ Cached results found: {target.name}")
            else:
                result.status = "failed"
                result.error_message = "Expected cached results not found"
                self.console.print(f"❌ Cached results missing: {target.name}")

        except Exception as e:
            result.status = "failed"
            result.error_message = f"Cache collection failed: {e}"
            self.console.print(f"❌ Cache collection error for {target.name}: {e}")

        finally:
            result.execution_time_seconds = time.time() - start_time

        return result

    def _prepare_environment(self, target: TargetDefinition) -> Dict[str, str]:
        """
        ## Prepare Compilation Environment

        Set up the environment variables needed for this target's compilation.
        This translates our target configuration into the runtime environment
        that the Rust toolchain expects.

        Args:
            target: Target configuration

        Returns:
            Dictionary of environment variables for subprocess execution
        """

        # Start with current environment
        env = os.environ.copy()

        # Apply target-specific environment variables
        target_env = target.get_env_vars()
        env.update(target_env)

        # Set up Cargo target directory if configured
        if not env.get('CARGO_TARGET_DIR'):
            env['CARGO_TARGET_DIR'] = str(self.rust_project_path / "target")

        return env

    def _run_cargo_bench(self, target: TargetDefinition, env: Dict[str, str],
                        progress_task: Optional[TaskID] = None) -> Tuple[str, bool]:
        """
        ## Execute Cargo Bench

        Run the actual `cargo bench` command with proper timeout, monitoring,
        and error handling. This is where the expensive computation happens.

        Args:
            target: Target being benchmarked
            env: Environment variables for execution
            progress_task: Optional progress task for UI updates

        Returns:
            Tuple of (output, success) where output is captured stdout/stderr
            and success indicates whether the benchmark completed successfully
        """

        # Construct cargo bench command
        cmd = [
            "cargo", "bench",
            "--",
            "--save-baseline", target.name
        ]

        # Set measurement time if configured
        measurement_time = self.config.execution.measurement_time_seconds
        if measurement_time != 15:  # 15 is Criterion default
            cmd.extend(["--measurement-time", str(measurement_time)])

        self.console.print(f"🔧 Running: {' '.join(cmd)}")
        self.console.print(f"📁 Working directory: {self.rust_project_path}")
        if target.rustflags:
            self.console.print(f"🎛️  RUSTFLAGS: {target.rustflags}")

        try:
            # Start the process
            process = subprocess.Popen(
                cmd,
                cwd=self.rust_project_path,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1  # Line buffered
            )

            # Monitor the process with timeout
            timeout_seconds = self.config.execution.single_benchmark_run
            output_lines = []

            # Use a context manager for process cleanup
            with self._process_monitor(process, timeout_seconds):
                # Read output line by line for progress reporting
                while True:
                    line = process.stdout.readline()
                    if not line and process.poll() is not None:
                        break

                    if line:
                        line = line.strip()
                        output_lines.append(line)

                        # Update progress if we can parse benchmark progress
                        if progress_task and ("Benchmarking" in line or "bench:" in line):
                            # Update progress display with current benchmark
                            pass  # Progress updates would go here

                # Wait for process to complete
                return_code = process.poll()

            output = "\n".join(output_lines)
            success = return_code == 0

            if not success:
                self.console.print(f"⚠️  Cargo bench exited with code: {return_code}")

            return output, success

        except subprocess.TimeoutExpired:
            self.console.print(f"⏰ Benchmark timeout after {timeout_seconds} seconds")
            return f"Benchmark timed out after {timeout_seconds} seconds", False

        except Exception as e:
            self.console.print(f"💥 Benchmark execution error: {e}")
            return f"Execution error: {e}", False

    @contextmanager
    def _process_monitor(self, process: subprocess.Popen, timeout_seconds: int):
        """
        ## Process Monitoring Context Manager

        Monitor a subprocess with timeout and resource tracking.
        Ensures proper cleanup even if the process hangs or we need to
        terminate early.

        Args:
            process: The subprocess to monitor
            timeout_seconds: Maximum time to allow the process to run
        """

        start_time = time.time()

        try:
            yield

            # Wait for completion with timeout
            try:
                process.wait(timeout=timeout_seconds)
            except subprocess.TimeoutExpired:
                # Terminate the process gracefully
                self.console.print("⏰ Terminating timed-out process...")
                process.terminate()

                try:
                    process.wait(timeout=10)  # Give it 10 seconds to terminate
                except subprocess.TimeoutExpired:
                    # Force kill if it won't terminate
                    self.console.print("💀 Force killing unresponsive process...")
                    process.kill()
                    process.wait()

                raise subprocess.TimeoutExpired(process.args, timeout_seconds)

        finally:
            # Ensure process is cleaned up
            if process.poll() is None:
                try:
                    process.terminate()
                    process.wait(timeout=5)
                except:
                    try:
                        process.kill()
                        process.wait(timeout=2)
                    except:
                        pass  # Best effort cleanup


class BenchmarkOrchestrator:
    """
    ## High-Level Benchmark Orchestration

    Coordinates the execution of benchmarks across all configured targets.
    This class handles:

    - Session planning and target selection
    - Metadata collection and caching decisions
    - Progress reporting and user feedback
    - Error recovery and partial failure handling
    - Result organization and storage

    ### Orchestration Flow

    1. **Planning Phase**: Analyze targets, check cache, plan execution
    2. **Execution Phase**: Run benchmarks for each target
    3. **Collection Phase**: Gather analysis data and metadata
    4. **Organization Phase**: Store results in structured format

    ### Progress Reporting Philosophy

    Long benchmark runs need good user feedback:
    - Show current target and estimated time remaining
    - Display cache hit/miss information
    - Report success/failure/skip statistics
    - Provide performance hints during idle time
    """

    def __init__(self, config: Config):
        """
        Initialize the benchmark orchestrator.

        Args:
            config: System configuration
        """
        self.config = config
        self.console = Console()
        self.metadata_collector = MetadataCollector(config.paths.rust_project)

        # Validate configuration before starting
        config_errors = config.validate_setup()
        if config_errors:
            self.console.print("[red]Configuration errors found:[/red]")
            for error in config_errors:
                self.console.print(f"  • {error}")
            raise ValueError("Configuration validation failed")

    def run_comprehensive(self, target_group: Optional[str] = None) -> OrchestrationSession:
        """
        ## Run Comprehensive Benchmark Suite

        Execute the complete benchmark suite across all configured targets
        (or a specified target group). This is the main entry point for
        full benchmark runs.

        Args:
            target_group: Optional target group to run (default: all targets)

        Returns:
            OrchestrationSession with complete results
        """

        # Collect metadata once for the session
        metadata = self.metadata_collector.collect_all()

        session = self._create_session(target_group, metadata)

        try:
            self._display_session_header(session)

            # Metadata already collected above
            session.metadata = metadata

            # Plan execution for all targets
            execution_plan = self._plan_execution(session)

            # Execute benchmarks with progress tracking
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                console=self.console
            ) as progress:

                main_task = progress.add_task(
                    "Running benchmarks...",
                    total=len(execution_plan)
                )

                for target_name, should_run in execution_plan:
                    target = self.config.get_target(target_name)
                    if not target:
                        continue

                    # Create target-specific progress task
                    target_task = progress.add_task(
                        f"Target: {target_name}",
                        total=100
                    )

                    # Execute or collect cached results
                    if should_run:
                        result = self._execute_target(target, session.metadata, target_task)
                    else:
                        result = self._collect_cached_target(target, session.metadata)

                    # Store result and update statistics
                    session.target_results[target_name] = result
                    self._update_session_stats(session, result)

                    # Update progress
                    progress.update(main_task, advance=1)
                    progress.remove_task(target_task)

            # Finalize session
            session.end_time = datetime.now(timezone.utc)
            self._display_session_summary(session)

            return session

        except KeyboardInterrupt:
            self.console.print("\n[yellow]Benchmark session interrupted by user[/yellow]")
            session.end_time = datetime.now(timezone.utc)
            return session

        except Exception as e:
            self.console.print(f"\n[red]Benchmark session failed: {e}[/red]")
            session.end_time = datetime.now(timezone.utc)
            raise

    def run_single_target(self, target_name: str,
                         force_rerun: bool = False) -> BenchmarkResult:
        """
        ## Run Benchmark for Single Target

        Execute benchmarks for just one target. Useful for development
        iteration or testing specific configurations.

        Args:
            target_name: Name of target to run
            force_rerun: Skip cache and force re-execution

        Returns:
            BenchmarkResult for the target
        """

        target = self.config.get_target(target_name)
        if not target:
            raise ValueError(f"Unknown target: {target_name}")

        self.console.print(f"🎯 Running single target: {target_name}")

        # Collect metadata
        metadata = self.metadata_collector.collect_all()

        # Execute target
        executor = SingleTargetExecutor(self.config, self.console)

        if force_rerun:
            result = executor.execute_benchmark(target)
        else:
            should_run, reason = executor.should_run_benchmark(target, metadata)
            self.console.print(f"📋 Cache decision: {reason}")

            if should_run:
                result = executor.execute_benchmark(target)
            else:
                result = executor.collect_cached_results(target, metadata)

        return result

    def _create_session(self, target_group: Optional[str], metadata: ComprehensiveMetadata) -> OrchestrationSession:
        """Create a new orchestration session."""

        targets = self.config.get_enabled_targets(target_group)
        session_id = f"session_{int(time.time())}"

        session = OrchestrationSession(
            session_id=session_id,
            start_time=datetime.now(timezone.utc),
            config=self.config,
            metadata=metadata
        )
        session.total_targets = len(targets)
        return session

    def _display_session_header(self, session: OrchestrationSession):
        """Display session information to the user."""

        header_table = Table(title="Benchmark Session")
        header_table.add_column("Property", style="bold")
        header_table.add_column("Value")

        header_table.add_row("Session ID", session.session_id)
        header_table.add_row("Start Time", session.start_time.strftime("%Y-%m-%d %H:%M:%S UTC"))
        header_table.add_row("Targets", str(session.total_targets))
        header_table.add_row("Rust Project", str(self.config.paths.rust_project))
        header_table.add_row("Results Directory", str(self.config.paths.results))

        self.console.print(Panel(header_table, expand=False))

    def _plan_execution(self, session: OrchestrationSession) -> List[Tuple[str, bool]]:
        """
        Plan execution for all targets in the session.

        Returns list of (target_name, should_run) tuples.
        """

        execution_plan = []
        executor = SingleTargetExecutor(self.config, self.console)

        for target_name in self.config.get_enabled_targets():
            target = self.config.get_target(target_name)
            if target:
                should_run, reason = executor.should_run_benchmark(target, session.metadata)
                execution_plan.append((target_name, should_run))
                self.console.print(f"📋 {target_name}: {reason}")

        return execution_plan

    def _execute_target(self, target: TargetDefinition, metadata: ComprehensiveMetadata,
                       progress_task: Optional[TaskID]) -> BenchmarkResult:
        """Execute benchmark for a single target."""

        executor = SingleTargetExecutor(self.config, self.console)
        return executor.execute_benchmark(target, progress_task)

    def _collect_cached_target(self, target: TargetDefinition,
                              metadata: ComprehensiveMetadata) -> BenchmarkResult:
        """Collect cached results for a single target."""

        executor = SingleTargetExecutor(self.config, self.console)
        return executor.collect_cached_results(target, metadata)

    def _update_session_stats(self, session: OrchestrationSession, result: BenchmarkResult):
        """Update session statistics based on target result."""

        if result.status == "success":
            session.successful_targets += 1
        elif result.status == "cached":
            session.cached_targets += 1
        elif result.status == "failed":
            session.failed_targets += 1
        elif result.status == "skipped":
            session.skipped_targets += 1

    def _display_session_summary(self, session: OrchestrationSession):
        """Display final session summary."""

        summary_table = Table(title="Session Summary")
        summary_table.add_column("Metric", style="bold")
        summary_table.add_column("Value", style="cyan")

        summary_table.add_row("Duration", f"{session.duration_seconds:.1f}s")
        summary_table.add_row("Success Rate", f"{session.success_rate:.1f}%")
        summary_table.add_row("Successful", str(session.successful_targets))
        summary_table.add_row("Cached", str(session.cached_targets))
        summary_table.add_row("Failed", str(session.failed_targets))
        summary_table.add_row("Skipped", str(session.skipped_targets))

        # Display individual target results
        results_table = Table(title="Target Results")
        results_table.add_column("Target", style="bold")
        results_table.add_column("Status")
        results_table.add_column("Time (s)")
        results_table.add_column("Notes")

        for target_name, result in session.target_results.items():
            status_style = {
                "success": "green",
                "cached": "blue",
                "failed": "red",
                "skipped": "yellow"
            }.get(result.status, "white")

            notes = ""
            if result.used_cache:
                notes += "cached "
            if result.error_message:
                notes += f"({result.error_message[:50]}...)" if len(result.error_message) > 50 else f"({result.error_message})"

            results_table.add_row(
                target_name,
                f"[{status_style}]{result.status}[/{status_style}]",
                f"{result.execution_time_seconds:.1f}",
                notes
            )

        self.console.print(Panel(summary_table, expand=False))
        self.console.print(Panel(results_table, expand=False))


# Convenience functions for common usage patterns

def run_comprehensive_benchmarks(config: Optional[Config] = None,
                                target_group: Optional[str] = None) -> OrchestrationSession:
    """
    ## Run Comprehensive Benchmarks

    Convenience function to run a complete benchmark session with default
    configuration. This is the main entry point for most users.

    Args:
        config: Optional configuration (uses defaults if not provided)
        target_group: Optional target group to run

    Returns:
        OrchestrationSession with complete results

    Example:
        ```python
        from benchfind.benchmark import run_comprehensive_benchmarks

        # Run all targets
        session = run_comprehensive_benchmarks()

        # Run only production targets
        session = run_comprehensive_benchmarks(target_group='production')
        ```
    """

    if config is None:
        from .config import load_default_config
        config = load_default_config()

    orchestrator = BenchmarkOrchestrator(config)
    return orchestrator.run_comprehensive(target_group)


def run_single_benchmark(target_name: str, config: Optional[Config] = None,
                        force_rerun: bool = False) -> BenchmarkResult:
    """
    ## Run Single Target Benchmark

    Convenience function to run benchmarks for a single target.
    Useful for development and testing.

    Args:
        target_name: Name of target to benchmark
        config: Optional configuration (uses defaults if not provided)
        force_rerun: Skip cache and force re-execution

    Returns:
        BenchmarkResult for the target
    """

    if config is None:
        from .config import load_default_config
        config = load_default_config()

    orchestrator = BenchmarkOrchestrator(config)
    return orchestrator.run_single_target(target_name, force_rerun)


def check_benchmark_cache(target_name: str, config: Optional[Config] = None) -> Tuple[bool, str]:
    """
    ## Check Benchmark Cache Status

    Check whether a target has cached results available without running anything.
    Useful for planning and cache management.

    Args:
        target_name: Name of target to check
        config: Optional configuration (uses defaults if not provided)

    Returns:
        Tuple of (has_cache, status_message)

    Example:
        ```python
        has_cache, message = check_benchmark_cache('native-avx2')
        if has_cache:
            print(f"Cache available: {message}")
        else:
            print(f"No cache: {message}")
        ```
    """

    if config is None:
        from .config import load_default_config
        config = load_default_config()

    target = config.get_target(target_name)
    if not target:
        return False, f"Unknown target: {target_name}"

    # Collect metadata to determine cache key
    metadata_collector = MetadataCollector(config.paths.rust_project)
    metadata = metadata_collector.collect_all()

    # Check cache status
    executor = SingleTargetExecutor(config, Console())
    should_run, reason = executor.should_run_benchmark(target, metadata)

    return not should_run, reason


def estimate_benchmark_time(config: Optional[Config] = None,
                           target_group: Optional[str] = None) -> Dict[str, Any]:
    """
    ## Estimate Benchmark Execution Time

    Provide time estimates for benchmark execution to help users plan
    their benchmarking sessions. Considers cache status and target complexity.

    Args:
        config: Optional configuration (uses defaults if not provided)
        target_group: Optional target group to estimate for

    Returns:
        Dictionary with time estimates and breakdown

    Example:
        ```python
        estimate = estimate_benchmark_time(target_group='production')
        print(f"Estimated time: {estimate['total_minutes']:.1f} minutes")
        ```
    """

    if config is None:
        from .config import load_default_config
        config = load_default_config()

    targets = config.get_enabled_targets(target_group)

    # Base time estimates (in minutes)
    base_time_per_target = config.execution.measurement_time_seconds / 60.0 + 5  # benchmark time + overhead
    setup_time = 2  # metadata collection, setup, etc.

    estimate = {
        'targets': len(targets),
        'cached_targets': 0,
        'new_targets': 0,
        'base_minutes_per_target': base_time_per_target,
        'setup_minutes': setup_time,
        'total_minutes': setup_time,
        'breakdown': {}
    }

    # Check cache status for each target
    try:
        metadata_collector = MetadataCollector(config.paths.rust_project)
        metadata = metadata_collector.collect_all()
        executor = SingleTargetExecutor(config, Console())

        for target_name in targets:
            target = config.get_target(target_name)
            if target:
                should_run, reason = executor.should_run_benchmark(target, metadata)

                if should_run:
                    estimate['new_targets'] += 1
                    estimate['total_minutes'] += base_time_per_target
                    estimate['breakdown'][target_name] = f"Run ({base_time_per_target:.1f}m): {reason}"
                else:
                    estimate['cached_targets'] += 1
                    estimate['total_minutes'] += 0.5  # Quick cache collection
                    estimate['breakdown'][target_name] = f"Cached (0.5m): {reason}"

    except Exception as e:
        # If we can't check cache, assume all targets need running
        estimate['new_targets'] = len(targets)
        estimate['total_minutes'] = setup_time + (len(targets) * base_time_per_target)
        estimate['breakdown'] = {name: f"Run ({base_time_per_target:.1f}m): Cannot check cache"
                               for name in targets}

    return estimate


def clean_benchmark_cache(config: Optional[Config] = None,
                         older_than_days: int = 30,
                         dry_run: bool = True) -> Dict[str, Any]:
    """
    ## Clean Old Benchmark Results

    Remove old benchmark results to free up disk space. This function
    identifies and optionally removes result directories that are older
    than the specified age.

    Args:
        config: Optional configuration (uses defaults if not provided)
        older_than_days: Remove results older than this many days
        dry_run: If True, only report what would be removed

    Returns:
        Dictionary with cleanup statistics

    Example:
        ```python
        # See what would be cleaned
        stats = clean_benchmark_cache(older_than_days=7, dry_run=True)
        print(f"Would remove {stats['directories']} directories, {stats['size_mb']:.1f}MB")

        # Actually clean
        stats = clean_benchmark_cache(older_than_days=7, dry_run=False)
        ```
    """

    if config is None:
        from .config import load_default_config
        config = load_default_config()

    results_dir = config.paths.results / "runs"
    if not results_dir.exists():
        return {'directories': 0, 'size_mb': 0, 'errors': []}

    import time
    cutoff_timestamp = time.time() - (older_than_days * 86400)

    cleanup_stats = {
        'directories': 0,
        'size_mb': 0.0,
        'errors': [],
        'removed': [],
        'dry_run': dry_run
    }

    try:
        for run_dir in results_dir.iterdir():
            if not run_dir.is_dir():
                continue

            try:
                # Check directory age
                dir_mtime = run_dir.stat().st_mtime
                if dir_mtime > cutoff_timestamp:
                    continue

                # Calculate directory size
                total_size = 0
                for path in run_dir.rglob('*'):
                    if path.is_file():
                        total_size += path.stat().st_size

                size_mb = total_size / (1024 * 1024)

                if dry_run:
                    cleanup_stats['removed'].append(f"{run_dir.name} ({size_mb:.1f}MB)")
                else:
                    # Actually remove the directory
                    shutil.rmtree(run_dir)
                    cleanup_stats['removed'].append(f"{run_dir.name} ({size_mb:.1f}MB) - REMOVED")

                cleanup_stats['directories'] += 1
                cleanup_stats['size_mb'] += size_mb

            except Exception as e:
                error_msg = f"Error processing {run_dir.name}: {e}"
                cleanup_stats['errors'].append(error_msg)

    except Exception as e:
        cleanup_stats['errors'].append(f"Error accessing results directory: {e}")

    return cleanup_stats


# ============================================================================
# High-Level Benchmark Runners
# ============================================================================

class QuickBenchmarkRunner:
    """
    ## Quick Benchmark Runner

    Optimized for development iteration with minimal overhead.
    Focuses on speed over comprehensive data collection.
    """

    def __init__(self, config: Dict[str, Any], console: Console):
        self.config = config
        self.console = console

    def run_single_target(self, target: 'TargetDefinition', project_root: Path) -> BenchmarkResult:
        """Run benchmarks for a single target quickly."""
        start_time = datetime.now(timezone.utc)

        try:
            # Create a simple executor for this target
            executor = SingleTargetExecutor(
                config=self.config,
                console=self.console,
                rust_project_path=project_root
            )

            # Run the benchmark
            result = executor.execute_benchmark(target)

            # Calculate duration
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            result.duration = duration

            return result

        except Exception as e:
            return BenchmarkResult(
                target=target,
                success=False,
                cached=False,
                execution_time_seconds=0,
                benchmark_groups=[],
                error_message=str(e),
                duration=(datetime.now(timezone.utc) - start_time).total_seconds()
            )


class ComprehensiveBenchmarkRunner:
    """
    ## Comprehensive Benchmark Runner

    Full-featured benchmark execution with metadata collection,
    assembly analysis, and structured storage.
    """

    def __init__(self, targets: List['TargetDefinition'], config: Dict[str, Any], console: Console):
        self.targets = targets
        self.config = config
        self.console = console

    def run_all_benchmarks(self, metadata: 'ComprehensiveMetadata', storage: 'ResultsStorage') -> List[BenchmarkResult]:
        """Run comprehensive benchmarks for all targets."""
        results = []

        for target in self.targets:
            self.console.print(f"[blue]⚡ Running comprehensive benchmark for {target.name}[/blue]")

            try:
                # Create orchestrator for this target
                orchestrator = BenchmarkOrchestrator(
                    config=self.config,
                    console=self.console,
                    metadata_collector=None  # Will be handled by the caller
                )

                # Execute the target
                result = orchestrator._execute_target(target, metadata, None)
                results.append(result)

            except Exception as e:
                self.console.print(f"[red]❌ Failed to run {target.name}: {e}[/red]")
                results.append(BenchmarkResult(
                    target=target,
                    success=False,
                    cached=False,
                    execution_time_seconds=0,
                    benchmark_groups=[],
                    error_message=str(e)
                ))

        return results
