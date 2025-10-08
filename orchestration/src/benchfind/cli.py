"""
# Command-Line Interface for Benchfind Orchestration

This module provides a comprehensive CLI for the benchfind orchestration system,
replacing the legacy bash scripts with a unified, well-structured command interface.
The CLI integrates with all orchestration modules and provides both high-level
workflows and granular control over individual operations.

## Design Philosophy

### **Unified Interface**
Instead of multiple bash scripts with inconsistent interfaces, we provide a single
`benchfind` command with subcommands for different operations. This follows the
pattern of modern tools like `git`, `docker`, and `cargo`.

### **Progressive Complexity**
Commands are organized from simple to complex:
- `benchfind quick` - Fast iteration during development
- `benchfind comprehensive` - Full benchmark suite with all analysis
- `benchfind analyze` - Post-hoc analysis of existing results
- `benchfind manage` - Storage and housekeeping operations

### **Rich Output**
Using the Rich library for beautiful, informative output with progress bars,
syntax highlighting, and structured information display.

### **Configuration Integration**
All CLI behavior is driven by the YAML configuration files, with command-line
options for common overrides and development needs.

## Command Structure

```
benchfind
├── quick           # Fast benchmarking for development iteration
├── comprehensive   # Complete benchmark suite with full analysis
├── analyze         # Analysis of existing results
├── manage          # Storage management and housekeeping
├── config          # Configuration management and validation
└── info            # System information and diagnostics
```

## Usage Examples

```bash
# Quick development iteration
benchfind quick --targets native,native-avx2

# Full comprehensive run
benchfind comprehensive --all-targets

# Analyze latest results
benchfind analyze --latest --format json

# Clean up old results
benchfind manage cleanup --older-than 30d

# Validate configuration
benchfind config validate
```
"""

import sys
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
import subprocess
import json
from datetime import datetime, timezone

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Confirm
from rich.text import Text
from rich import print as rprint

try:
    from .config import Config, ConfigurationLoader
    from .storage import ResultsStorage, RunIdentifier
    from .metadata import MetadataCollector
    from .benchmark import BenchmarkOrchestrator, run_comprehensive_benchmarks
except ImportError:
    # Handle standalone usage
    import sys
    from pathlib import Path

    # Add parent directory to path for standalone usage
    current_dir = Path(__file__).parent
    sys.path.insert(0, str(current_dir))

    from config import Config, ConfigurationLoader
    from storage import ResultsStorage, RunIdentifier
    from metadata import MetadataCollector
    from benchmark import BenchmarkOrchestrator, run_comprehensive_benchmarks


# Initialize Rich console for beautiful output
console = Console()


class CliContext:
    """
    ## CLI Context Management

    Stores shared state and configuration across CLI commands.
    This follows Click's pattern for passing context between commands.
    """

    def __init__(self):
        self.config: Optional[Config] = None
        self.storage: Optional[ResultsStorage] = None
        self.project_root: Optional[Path] = None
        self.verbose: bool = False
        self.dry_run: bool = False

    def ensure_initialized(self):
        """Ensure config and storage are initialized"""
        if self.project_root is None:
            self.project_root = self.find_project_root()

        if self.config is None:
            self.config = ConfigurationLoader()

        if self.storage is None:
            storage_config = self.config.load_storage_config()
            self.storage = ResultsStorage(storage_config, self.project_root)

    def find_project_root(self) -> Path:
        """Find the project root directory by looking for benchfind project structure."""
        current = Path.cwd().resolve()

        # Look for benchfind project structure
        while current != current.parent:
            # Check for direct Cargo.toml (legacy structure)
            if (current / "Cargo.toml").exists():
                return current

            # Check for benchfind project structure with rust_project subdirectory
            rust_project = current / "rust_project"
            if rust_project.exists() and (rust_project / "Cargo.toml").exists():
                return rust_project

            # Check if we're in orchestration directory, look for ../rust_project
            if current.name == "orchestration":
                parent_rust_project = current.parent / "rust_project"
                if parent_rust_project.exists() and (parent_rust_project / "Cargo.toml").exists():
                    return parent_rust_project

            current = current.parent

        raise click.ClickException(
            "Could not find project root. Please run from the benchfind project directory."
        )


pass_context = click.make_pass_decorator(CliContext, ensure=True)


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.option('--dry-run', is_flag=True, help='Show what would be done without executing')
@click.pass_context
def main(ctx: click.Context, verbose: bool, dry_run: bool):
    """
    Benchfind Orchestration - Systematic Rust benchmarking with SIMD analysis

    This tool replaces the legacy bash scripts with a unified Python-based
    orchestration system for comprehensive benchmark data collection.
    """
    ctx.ensure_object(CliContext)
    ctx.obj.verbose = verbose
    ctx.obj.dry_run = dry_run

    if verbose:
        console.print("[dim]Verbose mode enabled[/dim]")
    if dry_run:
        console.print("[yellow]Dry run mode - no changes will be made[/yellow]")


@main.command()
@click.option('--targets', '-t', help='Comma-separated list of targets (default: development set)')
@click.option('--benchmarks', '-b', help='Comma-separated list of benchmarks (default: all)')
@click.option('--measurement-time', type=int, help='Measurement time per benchmark in seconds')
@click.option('--skip-analysis', is_flag=True, help='Skip assembly analysis (faster)')
@pass_context
def quick(ctx: CliContext, targets: Optional[str], benchmarks: Optional[str],
          measurement_time: Optional[int], skip_analysis: bool):
    """
    Quick benchmarking for development iteration

    Runs a subset of targets with shorter measurement times for rapid feedback
    during development. Results are cached to avoid re-running unchanged code.

    Examples:
      benchfind quick                           # Use development defaults
      benchfind quick -t native,native-avx2    # Specific targets
      benchfind quick --measurement-time 5     # Faster measurements
    """
    ctx.ensure_initialized()

    try:
        # Parse targets
        if targets:
            target_list = [t.strip() for t in targets.split(',')]
        else:
            # Use development defaults from config
            try:
                target_objects = ctx.config.get_target_group('development')
                target_list = [t.name for t in target_objects] if target_objects else ['default', 'native']
            except ValueError:
                # Fallback if development group doesn't exist
                target_list = ['default', 'native']

        console.print(f"[bold]Quick Benchmark Run[/bold]")
        console.print(f"Targets: {', '.join(target_list)}")

        # Get current run identifier
        run_id = ctx.storage.get_current_run_id()
        console.print(f"Run ID: [cyan]{run_id.run_id}[/cyan]")

        # Check what needs to be run
        cached_targets, targets_to_run = ctx.storage.check_existing_results(run_id, target_list)

        if cached_targets:
            console.print(f"[green]Cached results available for: {', '.join(cached_targets)}[/green]")

        if targets_to_run:
            console.print(f"[yellow]Need to run: {', '.join(targets_to_run)}[/yellow]")

            if not ctx.dry_run:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TaskProgressColumn(),
                    console=console
                ) as progress:
                    task = progress.add_task("Running benchmarks...", total=len(targets_to_run))

                    for target in targets_to_run:
                        progress.update(task, description=f"Benchmarking {target}")
                        # This would integrate with the benchmark module
                        # For now, we'll simulate with a delay
                        import time
                        time.sleep(0.5)  # Simulate work
                        progress.advance(task)
        else:
            console.print("[green]All results are cached and up to date![/green]")

        # Show summary
        _show_run_summary(ctx, run_id, target_list)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        if ctx.verbose:
            console.print_exception()
        sys.exit(1)


@main.command()
@click.option('--all-targets', is_flag=True, help='Run all available targets')
@click.option('--targets', '-t', help='Comma-separated list of targets')
@click.option('--skip-existing', is_flag=True, help='Skip targets with existing results')
@click.option('--force-rebuild-results', is_flag=True, help='Force rebuild even if Python results storage exists')
@click.option('--force-rebuild-benchmarks', is_flag=True, help='Force rebuild benchmarks by cleaning Rust target directory')
@pass_context
def comprehensive(ctx: CliContext, all_targets: bool, targets: Optional[str],
                 skip_existing: bool, force_rebuild_results: bool, force_rebuild_benchmarks: bool):
    """
    Comprehensive benchmark suite with full analysis

    Runs the complete benchmark suite across all or specified targets,
    collecting full metadata, assembly analysis, and SIMD detection.
    This replaces the legacy run_comprehensive_benchmarks.sh script.

    Examples:
      benchfind comprehensive --all-targets                  # Run everything
      benchfind comprehensive -t native,avx2                 # Specific targets
      benchfind comprehensive --skip-existing                # Only run missing targets
      benchfind comprehensive --force-rebuild-results        # Ignore Python cache
      benchfind comprehensive --force-rebuild-benchmarks     # Clean Rust target and rerun
    """
    ctx.ensure_initialized()

    try:
        # Determine target list
        if all_targets:
            all_target_configs = ctx.config.get_target_group('all')
            target_list = [t.name for t in all_target_configs] if all_target_configs else []
        elif targets:
            target_list = [t.strip() for t in targets.split(',')]
        else:
            # Default to production targets
            prod_targets = ctx.config.get_target_group('production')
            target_list = [t.name for t in prod_targets] if prod_targets else ['default', 'native', 'native-avx2']

        if not target_list:
            raise click.ClickException("No targets specified")

        console.print(Panel.fit(
            f"[bold]Comprehensive Benchmark Suite[/bold]\n"
            f"Targets: {', '.join(target_list)}\n"
            f"Estimated time: {len(target_list) * 15} minutes",
            title="Benchmark Run"
        ))

        # Get run information
        run_id = ctx.storage.get_current_run_id()
        console.print(f"Run ID: [cyan]{run_id.run_id}[/cyan]")

        # Check existing results (unless force rebuild results is enabled)
        if force_rebuild_results:
            console.print("[yellow]Force rebuild results enabled - ignoring Python result cache[/yellow]")
            # Skip cache check, run all requested targets
            cached_targets, targets_to_run = set(), set(target_list)
        else:
            cached_targets, targets_to_run = ctx.storage.check_existing_results(run_id, target_list)

        if skip_existing and cached_targets:
            console.print(f"[yellow]Skipping cached targets: {', '.join(cached_targets)}[/yellow]")
            target_list = list(targets_to_run)
        elif force_rebuild_results:
            target_list = target_list  # Run all requested targets

        if force_rebuild_benchmarks:
            console.print("[yellow]Force rebuild benchmarks enabled - will clean Rust target directory[/yellow]")
            target_list = target_list  # Run all requested targets

            # Clean the Rust target directory to force fresh compilation and benchmarks
            console.print("[dim]Cleaning Rust target directory...[/dim]")
            import subprocess
            try:
                result = subprocess.run(
                    ["cargo", "clean"],
                    cwd=ctx.project_root,
                    capture_output=True,
                    text=True,
                    check=True
                )
                console.print("[green]✓[/green] Rust target directory cleaned")
            except subprocess.CalledProcessError as e:
                console.print(f"[yellow]Warning: Failed to clean target directory: {e}[/yellow]")
                console.print("[dim]Continuing anyway...[/dim]")
            except FileNotFoundError:
                console.print("[yellow]Warning: cargo command not found[/yellow]")

        if not target_list:
            raise click.ClickException("No targets specified")

        console.print(Panel.fit(
            f"[bold]Comprehensive Benchmark Suite[/bold]\n"
            f"Targets: {', '.join(target_list)}\n"
            f"Force rebuild results: {force_rebuild_results}\n"
            f"Force rebuild benchmarks: {force_rebuild_benchmarks}",
            title="🎯 Benchmarking Configuration"
        ))

        if not ctx.dry_run:
            # Create proper Config object for BenchmarkOrchestrator
            console.print("[dim]Loading configuration...[/dim]")
            from .config import Config
            config = Config.from_defaults()

            console.print("[dim]Initializing benchmark orchestrator...[/dim]")
            orchestrator = BenchmarkOrchestrator(config)

            # Run comprehensive benchmarks
            session = orchestrator.run_comprehensive()

            # Show results summary
            console.print(f"\n[bold]Benchmark Session Complete[/bold]")
            console.print(f"Session ID: [cyan]{session.session_id}[/cyan]")
            console.print(f"Duration: {session.duration_seconds:.1f}s")
            console.print(f"Success Rate: {session.success_rate:.1f}%")

            if session.successful_targets > 0:
                console.print(f"[green]✓ {session.successful_targets} targets completed successfully[/green]")
            if session.cached_targets > 0:
                console.print(f"[blue]📋 {session.cached_targets} targets used cached results[/blue]")
            if session.failed_targets > 0:
                console.print(f"[red]✗ {session.failed_targets} targets failed[/red]")
        else:
            console.print(f"[dim]Dry run: would benchmark {len(target_list)} targets[/dim]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        if ctx.verbose:
            console.print_exception()
        sys.exit(1)


@main.command()
@click.option('--run-id', help='Specific run ID to analyze')
@click.option('--latest', is_flag=True, help='Analyze the most recent run')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json', 'csv']),
              default='table', help='Output format')
@click.option('--output', '-o', type=click.Path(), help='Output file (default: stdout)')
@click.option('--targets', help='Comma-separated list of targets to include')
@pass_context
def analyze(ctx: CliContext, run_id: Optional[str], latest: bool, output_format: str,
           output: Optional[str], targets: Optional[str]):
    """
    Analyze benchmark results

    Provides analysis and reporting of benchmark results, including performance
    comparisons, SIMD effectiveness, and trend analysis across runs.

    Examples:
      benchfind analyze --latest                    # Analyze most recent run
      benchfind analyze --run-id host_abc123_1.75   # Specific run
      benchfind analyze --format json -o results.json # Export to JSON
    """
    ctx.ensure_initialized()

    try:
        # Determine which run to analyze
        if latest:
            # Find the most recent run
            stats = ctx.storage.get_storage_statistics()
            if stats['total_runs'] == 0:
                raise click.ClickException("No benchmark runs found")

            # Get the most recent completed run
            recent_runs = ctx.storage.index.find_runs(status='completed')
            if not recent_runs:
                raise click.ClickException("No completed runs found")

            target_run = recent_runs[0]  # Already sorted by timestamp, newest first
            run_id = target_run['run_id']
        elif run_id:
            target_run = ctx.storage.index.get_run(run_id)
            if not target_run:
                raise click.ClickException(f"Run {run_id} not found")
        else:
            # Show available runs and let user choose
            _show_available_runs(ctx)
            return

        console.print(f"[bold]Analyzing run: [cyan]{run_id}[/cyan][/bold]")

        # Load run data
        layout = ctx.storage.get_storage_layout(run_id)
        if not layout.run_dir.exists():
            raise click.ClickException(f"Run directory not found: {layout.run_dir}")

        # Parse target filter
        target_filter = None
        if targets:
            target_filter = set(t.strip() for t in targets.split(','))

        # Analyze based on format
        if output_format == 'table':
            _show_analysis_table(layout, target_filter)
        elif output_format == 'json':
            analysis_data = _generate_analysis_json(layout, target_filter)
            if output:
                with open(output, 'w') as f:
                    json.dump(analysis_data, f, indent=2)
                console.print(f"[green]Analysis exported to {output}[/green]")
            else:
                console.print_json(data=analysis_data)
        elif output_format == 'csv':
            _export_analysis_csv(layout, target_filter, output)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        if ctx.verbose:
            console.print_exception()
        sys.exit(1)


@main.group()
def manage():
    """Storage management and housekeeping operations"""
    pass


@manage.command()
@click.option('--older-than', help='Clean up runs older than specified time (e.g., 30d, 3m)')
@click.option('--failed-only', is_flag=True, help='Only clean up failed runs')
@click.option('--dry-run', is_flag=True, help='Show what would be cleaned without doing it')
@pass_context
def cleanup(ctx: CliContext, older_than: Optional[str], failed_only: bool, dry_run: bool):
    """Clean up old benchmark results"""
    ctx.ensure_initialized()

    console.print("[bold]Storage Cleanup[/bold]")

    # Show current storage statistics
    stats = ctx.storage.get_storage_statistics()
    console.print(f"Total runs: {stats['total_runs']}")
    console.print(f"Storage size: {stats['storage_size_gb']:.2f} GB")

    # Clean up incomplete runs
    if not dry_run:
        ctx.storage.cleanup_incomplete_runs()
        console.print("[green]Cleaned up incomplete runs[/green]")
    else:
        console.print("[dim]Would clean up incomplete runs[/dim]")


@manage.command()
@pass_context
def stats(ctx: CliContext):
    """Show storage statistics"""
    ctx.ensure_initialized()

    stats = ctx.storage.get_storage_statistics()

    table = Table(title="Storage Statistics")
    table.add_column("Metric", style="bold")
    table.add_column("Value", style="cyan")

    table.add_row("Total Runs", str(stats['total_runs']))
    table.add_row("Completed Runs", str(stats['completed_runs']))
    table.add_row("Failed Runs", str(stats['failed_runs']))
    table.add_row("In Progress", str(stats['in_progress_runs']))
    table.add_row("Storage Size", f"{stats['storage_size_gb']:.2f} GB")

    if stats['oldest_run']:
        table.add_row("Oldest Run", stats['oldest_run'])
    if stats['newest_run']:
        table.add_row("Newest Run", stats['newest_run'])

    console.print(table)


@manage.command()
@click.argument('run_id', required=True)
@click.option('--force', is_flag=True, help='Skip confirmation prompt')
@click.option('--dry-run', is_flag=True, help='Show what would be removed without doing it')
@pass_context
def remove(ctx: CliContext, run_id: str, force: bool, dry_run: bool):
    """Remove a benchmark run by ID"""
    ctx.ensure_initialized()

    # Check if the run exists
    run_info = ctx.storage.index.get_run(run_id)
    if not run_info:
        console.print(f"[red]Error: Run '{run_id}' not found[/red]")
        return

    # Show run information
    console.print(f"[bold]Run to remove: {run_id}[/bold]")
    console.print(f"Timestamp: {run_info.get('timestamp', 'Unknown')}")
    console.print(f"Status: {run_info.get('status', 'unknown')}")
    console.print(f"Hostname: {run_info.get('hostname', 'Unknown')}")

    targets = run_info.get('targets_completed', [])
    benchmarks = run_info.get('benchmarks_completed', [])
    console.print(f"Targets: {', '.join(targets) if targets else 'None'}")
    console.print(f"Benchmarks: {', '.join(benchmarks) if benchmarks else 'None'}")

    # Get storage layout to check what files exist
    layout = ctx.storage.get_storage_layout(run_id)
    storage_size = 0
    if layout.run_dir.exists():
        storage_size = sum(f.stat().st_size for f in layout.run_dir.rglob('*') if f.is_file())
        storage_size_mb = storage_size / (1024 * 1024)
        console.print(f"Storage used: {storage_size_mb:.2f} MB")
    else:
        console.print("Storage used: 0 MB (directory not found)")

    if dry_run:
        console.print("\n[yellow]DRY RUN - Would remove:[/yellow]")
        if layout.run_dir.exists():
            console.print(f"- Directory: {layout.run_dir}")
            console.print(f"- All subdirectories and files")
        console.print(f"- Index entry for run '{run_id}'")
        return

    # Confirmation unless --force is used
    if not force:
        console.print("\n[yellow]This will permanently delete all data for this run.[/yellow]")
        if not Confirm.ask("Are you sure you want to continue?"):
            console.print("Cancelled.")
            return

    # Remove the run directory
    if layout.run_dir.exists():
        import shutil
        try:
            shutil.rmtree(layout.run_dir)
            console.print(f"[green]Removed directory: {layout.run_dir}[/green]")
        except Exception as e:
            console.print(f"[red]Error removing directory: {e}[/red]")
            return

    # Remove from index
    ctx.storage.index.runs = [r for r in ctx.storage.index.runs if r.get('run_id') != run_id]
    ctx.storage.index.last_updated = datetime.now(timezone.utc).isoformat()
    ctx.storage._save_index()

    console.print(f"[green]Successfully removed run '{run_id}' from index[/green]")

    # Show summary
    if storage_size > 0:
        console.print(f"[dim]Freed {storage_size_mb:.2f} MB of storage space[/dim]")


@manage.command()
@click.option('--keep', default=5, help='Number of backup files to keep (default: 5)')
@click.option('--dry-run', is_flag=True, help='Show what would be removed without doing it')
@click.option('--force', is_flag=True, help='Skip confirmation prompt')
@pass_context
def cleanup_backups(ctx: CliContext, keep: int, dry_run: bool, force: bool):
    """Clean up excessive index backup files"""
    ctx.ensure_initialized()

    # Find all backup files and sort by timestamp in filename
    backup_pattern = f"{ctx.storage.index_path.stem}.backup.*"
    all_backups = list(ctx.storage.index_path.parent.glob(backup_pattern))

    def get_backup_timestamp(backup_file):
        try:
            # Extract timestamp from filename like "index.backup.1234567890"
            return int(backup_file.name.split('.')[-1])
        except (ValueError, IndexError):
            # Fallback to file modification time if filename parsing fails
            return int(backup_file.stat().st_mtime)

    backup_files = sorted(all_backups, key=get_backup_timestamp, reverse=True)

    if not backup_files:
        console.print("[green]No backup files found[/green]")
        return

    console.print(f"[bold]Found {len(backup_files)} backup files[/bold]")

    if len(backup_files) <= keep:
        console.print(f"[green]Only {len(backup_files)} backups exist (keeping {keep}), no cleanup needed[/green]")
        return

    files_to_remove = backup_files[keep:]
    total_size = sum(f.stat().st_size for f in files_to_remove)
    total_size_mb = total_size / (1024 * 1024)

    console.print(f"Will keep {keep} most recent backups:")
    for i, backup in enumerate(backup_files[:keep]):
        timestamp = backup.name.split('.')[-1]
        try:
            import datetime
            dt = datetime.datetime.fromtimestamp(int(timestamp))
            console.print(f"  {i+1}. {backup.name} ({dt.strftime('%Y-%m-%d %H:%M:%S')})")
        except (ValueError, OSError):
            console.print(f"  {i+1}. {backup.name}")

    console.print(f"\n[yellow]Will remove {len(files_to_remove)} old backup files ({total_size_mb:.2f} MB)[/yellow]")

    if dry_run:
        console.print("\n[yellow]DRY RUN - Would remove:[/yellow]")
        for backup in files_to_remove:
            console.print(f"  - {backup.name}")
        return

    if not force and not Confirm.ask(f"Remove {len(files_to_remove)} old backup files?"):
        console.print("Cancelled.")
        return

    # Remove the old backup files
    removed_count = 0
    for backup in files_to_remove:
        try:
            backup.unlink()
            removed_count += 1
        except OSError as e:
            console.print(f"[red]Error removing {backup.name}: {e}[/red]")

    console.print(f"[green]Successfully removed {removed_count} backup files, freed {total_size_mb:.2f} MB[/green]")


@manage.command()
@click.option('--dry-run', is_flag=True, help='Show what would be done without doing it')
@pass_context
def deduplicate_index(ctx: CliContext, dry_run: bool):
    """Clean up duplicate index entries"""
    ctx.ensure_initialized()

    console.print("[bold]Index Deduplication[/bold]")

    if dry_run:
        # Count duplicates without fixing them
        runs_by_id = {}
        for run_info in ctx.storage.index.runs:
            run_id = run_info.get('run_id')
            if run_id:
                runs_by_id.setdefault(run_id, []).append(run_info)

        total_runs = len(ctx.storage.index.runs)
        unique_runs = len(runs_by_id)
        duplicates = total_runs - unique_runs

        console.print(f"Current index entries: {total_runs}")
        console.print(f"Unique run IDs: {unique_runs}")
        console.print(f"Duplicate entries: {duplicates}")

        if duplicates > 0:
            console.print("\n[yellow]Duplicates found for run IDs:[/yellow]")
            for run_id, entries in runs_by_id.items():
                if len(entries) > 1:
                    console.print(f"  {run_id}: {len(entries)} entries")
    else:
        # Actually deduplicate
        stats = ctx.storage.deduplicate_index()
        console.print(f"[green]Deduplication completed[/green]")
        console.print(f"Original entries: {stats['original_count']}")
        console.print(f"Cleaned entries: {stats['cleaned_count']}")
        console.print(f"Duplicates removed: {stats['duplicates_removed']}")


@main.group()
def config():
    """Configuration management and validation"""
    pass


@config.command()
@pass_context
def validate(ctx: CliContext):
    """Validate all configuration files"""
    console.print("[bold]Validating Configuration[/bold]")

    loader = ConfigurationLoader()
    errors = []

    # Test each config file
    config_files = [
        ('targets.yaml', loader.load_targets),
        ('benchmarks.yaml', loader.load_benchmark_suites),
        ('execution.yaml', loader.load_execution_config),
        ('storage.yaml', loader.load_storage_config),
        ('instructions.yaml', loader.load_instruction_patterns),
    ]

    for filename, load_func in config_files:
        try:
            load_func()
            console.print(f"[green]✓[/green] {filename}")
        except Exception as e:
            console.print(f"[red]✗[/red] {filename}: {e}")
            errors.append(f"{filename}: {e}")

    if errors:
        console.print(f"\n[red]Found {len(errors)} configuration errors[/red]")
        sys.exit(1)
    else:
        console.print("\n[green]All configuration files are valid[/green]")


@config.command()
@click.argument('section', required=False)
@pass_context
def show(ctx: CliContext, section: Optional[str]):
    """Show configuration values"""
    ctx.ensure_initialized()

    loader = ConfigurationLoader()

    # Define available sections
    available_sections = {
        'targets': 'Compilation targets and SIMD instruction sets',
        'target-groups': 'Predefined target groups for different scenarios',
        'execution': 'Benchmark execution parameters and timeouts',
        'storage': 'Results storage paths and caching policies',
        'instructions': 'SIMD instruction patterns for analysis'
    }

    if section:
        if section not in available_sections:
            console.print(f"[red]Unknown section: {section}[/red]")
            console.print(f"Available sections: {', '.join(available_sections.keys())}")
            return

        console.print(f"[bold]Configuration: {section}[/bold]\n")

        if section == 'targets':
            targets = loader.get_all_targets()
            table = Table(title="Available Compilation Targets")
            table.add_column("Name", style="cyan")
            table.add_column("RUSTFLAGS", style="yellow")
            table.add_column("Expected SIMD", style="green")
            table.add_column("Description")

            for target in targets:
                rustflags = getattr(target, 'rustflags', '') or 'default'
                expected_simd = ', '.join(getattr(target, 'expected_simd_instructions', [])[:3])
                if not expected_simd:
                    expected_simd = 'None'
                elif len(getattr(target, 'expected_simd_instructions', [])) > 3:
                    expected_simd += '...'

                description = getattr(target, 'description', 'No description')[:50]
                if len(getattr(target, 'description', '')) > 50:
                    description += '...'

                table.add_row(target.name, rustflags, expected_simd, description)
            console.print(table)

        elif section == 'target-groups':
            groups = loader.load_target_groups()
            table = Table(title="Target Groups")
            table.add_column("Group", style="cyan")
            table.add_column("Targets", style="green")
            table.add_column("Description")

            group_descriptions = {
                'development': 'Fast targets for development iteration',
                'comprehensive': 'Complete SIMD progression testing',
                'production': 'Targets suitable for production analysis',
                'all': 'All available compilation targets'
            }

            for group, targets in groups.items():
                desc = group_descriptions.get(group, 'Custom target group')
                table.add_row(group, ', '.join(targets), desc)
            console.print(table)

        elif section == 'execution':
            exec_config = loader.load_execution_config()
            table = Table(title="Execution Parameters")
            table.add_column("Parameter", style="cyan")
            table.add_column("Value", style="green")
            table.add_column("Description")

            # Handle both dict and object formats
            def get_config_value(config, key, default=None):
                if hasattr(config, key):
                    return getattr(config, key, default)
                elif isinstance(config, dict):
                    return config.get(key, default)
                return default

            config_items = [
                ('measurement_time_seconds', get_config_value(exec_config, 'measurement_time_seconds'), 'Time spent measuring each benchmark'),
                ('warm_up_time_seconds', get_config_value(exec_config, 'warm_up_time_seconds'), 'Warm-up time before measurements'),
                ('timeout_seconds', get_config_value(get_config_value(exec_config, 'single_benchmark_run', {}), 'timeout_seconds'), 'Maximum time per benchmark run'),
                ('max_cache_age_days', get_config_value(exec_config, 'max_cache_age_days'), 'Maximum age for cached results')
            ]

            for param, value, desc in config_items:
                if value is not None:
                    table.add_row(param, str(value), desc)
            console.print(table)

        elif section == 'storage':
            storage_config = loader.load_storage_config()
            table = Table(title="Storage Configuration")
            table.add_column("Setting", style="cyan")
            table.add_column("Value", style="green")
            table.add_column("Description")

            paths = storage_config.get('paths', {})
            caching = storage_config.get('caching', {})

            storage_items = [
                ('results_base', paths.get('results_base'), 'Base directory for all results'),
                ('runs_dir', paths.get('runs_dir'), 'Directory for individual run results'),
                ('index_file', paths.get('index_file'), 'Global index of all runs'),
                ('skip_if_exists', caching.get('skip_benchmark_if_exists'), 'Skip benchmarks if results exist'),
                ('auto_cleanup', caching.get('auto_cleanup_incomplete_runs'), 'Automatically clean incomplete runs')
            ]

            for setting, value, desc in storage_items:
                if value is not None:
                    table.add_row(setting, str(value), desc)
            console.print(table)

        elif section == 'instructions':
            console.print("SIMD instruction patterns loaded from config/instructions.yaml")
            console.print("These patterns are used to detect SIMD usage in generated assembly code.")
            console.print("\nFor detailed patterns, examine the instructions.yaml file directly.")

    else:
        # Show comprehensive overview
        console.print("[bold]Configuration Overview[/bold]\n")

        # Available sections
        sections_table = Table(title="Available Configuration Sections")
        sections_table.add_column("Section", style="cyan")
        sections_table.add_column("Description", style="green")

        for section_name, description in available_sections.items():
            sections_table.add_row(section_name, description)

        console.print(sections_table)
        console.print(f"\nUse [cyan]benchfind config show <section>[/cyan] for detailed information")

        # Quick summary
        console.print("\n[bold]Quick Summary:[/bold]")
        try:
            targets = loader.get_all_targets()
            console.print(f"• {len(targets)} compilation targets configured")

            groups = loader.load_target_groups()
            console.print(f"• {len(groups)} target groups defined")

            exec_config = loader.load_execution_config()
            if hasattr(exec_config, 'measurement_time_seconds'):
                measurement_time = exec_config.measurement_time_seconds
            elif isinstance(exec_config, dict):
                measurement_time = exec_config.get('measurement_time_seconds', 'unknown')
            else:
                measurement_time = 'unknown'
            console.print(f"• {measurement_time}s default measurement time")

        except Exception as e:
            console.print(f"[yellow]Could not load configuration summary: {e}[/yellow]")


@config.command()
@click.option('--group', help='Show specific target group')
@pass_context
def targets(ctx: CliContext, group: Optional[str]):
    """List available compilation targets"""
    ctx.ensure_initialized()

    loader = ConfigurationLoader()

    if group:
        try:
            targets = loader.get_target_group(group)
            console.print(f"[bold]Target Group: {group}[/bold]")
        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            return
    else:
        targets = loader.get_all_targets()
        console.print("[bold]All Available Targets[/bold]")

    table = Table()
    table.add_column("Name", style="cyan")
    table.add_column("RUSTFLAGS", style="yellow")
    table.add_column("Description", style="green")

    for target in targets:
        rustflags = getattr(target, 'rustflags', '') or 'default'
        description = getattr(target, 'description', 'No description')
        table.add_row(target.name, rustflags, description)

    console.print(table)


@main.command()
@pass_context
def info(ctx: CliContext):
    """Show system information and diagnostics"""
    ctx.ensure_initialized()

    # Project information
    console.print(Panel.fit(
        f"[bold]Project Root:[/bold] {ctx.project_root}\n"
        f"[bold]Storage Location:[/bold] {ctx.storage.results_base}\n"
        f"[bold]Config Directory:[/bold] {Path(__file__).parent.parent.parent / 'config'}",
        title="Project Information"
    ))

    # System information
    import platform
    console.print(Panel.fit(
        f"[bold]OS:[/bold] {platform.system()} {platform.release()}\n"
        f"[bold]Python:[/bold] {platform.python_version()}\n"
        f"[bold]Architecture:[/bold] {platform.machine()}",
        title="System Information"
    ))

    # Rust information
    try:
        result = subprocess.run(['rustc', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            rust_version = result.stdout.strip()
        else:
            rust_version = "Not available"
    except FileNotFoundError:
        rust_version = "Not installed"

    console.print(Panel.fit(
        f"[bold]Rust Compiler:[/bold] {rust_version}",
        title="Build Environment"
    ))


# Helper functions

# Legacy simple benchmark execution function - kept for reference but no longer used
def _execute_target_benchmark(progress: Progress, target: 'TargetDefinition', project_root: Path):
    """
    DEPRECATED: This function is replaced by the proper BenchmarkOrchestrator.

    The comprehensive command now uses BenchmarkOrchestrator which includes:
    - Proper data collection and storage
    - Assembly analysis and SIMD detection
    - Result organization in structured directories
    - Intelligent caching and error handling

    This function only ran cargo bench without collecting or storing the results,
    which is why users saw empty directories in their run folders.
    """
    console.print("[yellow]Warning: Using deprecated _execute_target_benchmark function[/yellow]")
    console.print("[yellow]Please use BenchmarkOrchestrator for complete data collection[/yellow]")

    import subprocess
    import os
    from datetime import datetime, timezone

    # Create a simple result class to return
    class BenchmarkResult:
        def __init__(self, target, success=True, error_message=None):
            self.target = target
            self.success = success
            self.error_message = error_message
            self.execution_time = 0

    subtask = progress.add_task(f"  Compiling {target.name}", total=3)

    try:
        # Prepare environment with target-specific RUSTFLAGS
        env = os.environ.copy()
        if hasattr(target, 'rustflags') and target.rustflags:
            env['RUSTFLAGS'] = target.rustflags
            progress.update(subtask, description=f"  Compiling {target.name} (RUSTFLAGS: {target.rustflags})")
        else:
            progress.update(subtask, description=f"  Compiling {target.name} (default flags)")

        progress.advance(subtask)

        # Execute cargo bench with target-specific baseline
        progress.update(subtask, description=f"  Benchmarking {target.name}")

        start_time = datetime.now()

        # Run cargo bench (without baseline for now, as it may not be supported)
        result = subprocess.run(
            ["cargo", "bench"],
            cwd=project_root,
            env=env,
            capture_output=True,
            text=True,
            timeout=1800  # 30 minute timeout per target
        )

        progress.advance(subtask)

        if result.returncode != 0:
            error_msg = f"cargo bench failed with exit code {result.returncode}"
            if result.stderr:
                error_msg += f": {result.stderr[:200]}..."
            return BenchmarkResult(target, success=False, error_message=error_msg)

        # Analysis phase (placeholder for now)
        progress.update(subtask, description=f"  Analyzing {target.name}")
        progress.advance(subtask)

        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()

        result = BenchmarkResult(target, success=True)
        result.execution_time = execution_time
        return result

    except subprocess.TimeoutExpired:
        return BenchmarkResult(target, success=False, error_message="Benchmark timed out after 30 minutes")
    except subprocess.CalledProcessError as e:
        return BenchmarkResult(target, success=False, error_message=f"Subprocess error: {e}")
    except Exception as e:
        return BenchmarkResult(target, success=False, error_message=f"Unexpected error: {e}")

    progress.remove_task(subtask)


def _show_run_summary(ctx: CliContext, run_id: RunIdentifier, targets: List[str]):
    """Show summary of a benchmark run"""
    layout = ctx.storage.get_storage_layout(run_id)

    table = Table(title="Run Summary")
    table.add_column("Target", style="bold")
    table.add_column("Status", style="green")
    table.add_column("Results Available")

    for target in targets:
        target_dir = layout.get_target_assembly_dir(target)
        if target_dir.exists():
            status = "✓ Complete"
            results = "Assembly + Analysis"
        else:
            status = "⏳ Cached"
            results = "Benchmark data"

        table.add_row(target, status, results)

    console.print(table)


def _show_comprehensive_summary(completed: List[str], failed: List[str], run_id: RunIdentifier):
    """Show summary of comprehensive benchmark run"""
    if completed:
        console.print(f"\n[green]✓ Successfully completed {len(completed)} targets[/green]")
        for target in completed:
            console.print(f"  • {target}")

    if failed:
        console.print(f"\n[red]✗ Failed {len(failed)} targets[/red]")
        for target in failed:
            console.print(f"  • {target}")

    console.print(f"\n[bold]Run ID:[/bold] [cyan]{run_id.run_id}[/cyan]")
    console.print("[dim]Use 'benchfind analyze --latest' to view detailed results[/dim]")


def _show_available_runs(ctx: CliContext):
    """Show available benchmark runs"""
    recent_runs = ctx.storage.index.runs[:10]  # Show last 10 runs

    if not recent_runs:
        console.print("No benchmark runs found")
        return

    table = Table(title="Recent Benchmark Runs")
    table.add_column("Run ID", style="cyan")
    table.add_column("Timestamp")
    table.add_column("Status", style="green")
    table.add_column("Targets")

    for run in recent_runs:
        targets_str = ', '.join(run.get('targets_completed', []))
        if len(targets_str) > 30:
            targets_str = targets_str[:27] + "..."

        table.add_row(
            run['run_id'],
            run.get('timestamp', 'Unknown')[:19],  # Just date/time part
            run.get('status', 'unknown'),
            targets_str
        )

    console.print(table)
    console.print("\n[dim]Use 'benchfind analyze --run-id <ID>' to analyze a specific run[/dim]")


def _show_analysis_table(layout, target_filter):
    """Show analysis results as a table"""
    console.print("[bold]Benchmark Analysis[/bold]")
    console.print("[dim]Note: Full analysis integration pending - showing mock data[/dim]")

    table = Table()
    table.add_column("Target", style="bold")
    table.add_column("Benchmark", style="cyan")
    table.add_column("Implementation")
    table.add_column("Throughput", justify="right")
    table.add_column("SIMD Instructions")

    # Mock data for demonstration
    targets = ["default", "native", "native-avx2"]
    benchmarks = ["bench_newlines", "bench_csv"]
    implementations = ["via_iter", "via_memchr", "via_simd32"]

    for target in targets:
        if target_filter and target not in target_filter:
            continue

        for benchmark in benchmarks:
            for impl in implementations:
                throughput = f"{hash(target + impl) % 1000 + 500} MB/s"
                simd = "✓" if "simd" in impl and target != "default" else "✗"
                table.add_row(target, benchmark, impl, throughput, simd)

    console.print(table)


def _generate_analysis_json(layout, target_filter) -> Dict[str, Any]:
    """Generate analysis data in JSON format"""
    return {
        "run_info": {
            "run_id": layout.run_dir.name,
            "analysis_timestamp": datetime.now(timezone.utc).isoformat()
        },
        "summary": {
            "targets_analyzed": 3,
            "benchmarks_analyzed": 2,
            "implementations_analyzed": 8
        },
        "note": "Full analysis integration pending"
    }


def _export_analysis_csv(layout, target_filter, output_path):
    """Export analysis results to CSV"""
    if output_path:
        console.print(f"[green]Would export CSV to {output_path}[/green]")
    else:
        console.print("[green]Would export CSV to stdout[/green]")
    console.print("[dim]CSV export implementation pending[/dim]")


if __name__ == '__main__':
    main()
