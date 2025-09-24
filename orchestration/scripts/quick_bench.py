#!/usr/bin/env python3
"""
Quick Benchmarking Script

This script provides fast benchmarking for development iteration, focusing on
speed over comprehensive data collection. It's designed to quickly test changes
during development without the overhead of full metadata collection and analysis.

This replaces the legacy bench_all.sh bash script with a maintainable Python
implementation optimized for development workflows.
"""

import sys
from pathlib import Path

# Set up import paths and get common utilities
script_dir = Path(__file__).parent
src_dir = script_dir.parent / "src"
sys.path.insert(0, str(src_dir))

from benchfind.utils import (
    setup_script_environment,
    resolve_targets,
    create_standard_argument_parser,
    handle_common_exceptions,
    create_progress_context
)

try:
    from benchfind.config import ConfigurationLoader
    from benchfind.benchmark import QuickBenchmarkRunner
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Please ensure the benchfind package is installed and dependencies are available")
    sys.exit(1)


def parse_arguments():
    import argparse
    """Parse command line arguments."""
    parser = create_standard_argument_parser(
        description="Run quick benchmarks for development iteration",
        epilog="""
Examples:
  %(prog)s                           # Run development targets (native, avx2)
  %(prog)s --targets all             # Run all available targets
  %(prog)s --targets native,avx2     # Run specific targets
  %(prog)s --measurement-time 5      # Use 5 second measurement time for speed
  %(prog)s --skip-existing           # Skip targets that already have results
        """
    )

    parser.add_argument(
        "--targets",
        type=str,
        default="development",
        help="Target group or comma-separated list of targets (default: development)"
    )

    parser.add_argument(
        "--measurement-time",
        type=int,
        default=5,
        help="Measurement time per benchmark in seconds (default: 5)"
    )

    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip targets that already have benchmark results"
    )

    parser.add_argument(
        "--show-progress",
        action="store_true",
        help="Show detailed progress information"
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=1800,
        help="Timeout for individual benchmark runs in seconds (default: 1800)"
    )

    return parser.parse_args()


def validate_quick_environment(console, project_root: Path) -> bool:
    """Quick validation that the environment is ready for benchmarking."""
    from benchfind.utils import validate_rust_environment

    errors = validate_rust_environment(project_root)

    if errors:
        for error in errors:
            console.print(f"[red]❌ {error}[/red]")
        return False

    return True


def resolve_quick_targets(target_spec: str, config_loader, console) -> list:
    """Resolve target specification to list of target definitions."""

    # Use the common resolve_targets function
    from benchfind.utils import resolve_targets
    return resolve_targets(target_spec, config_loader, console)


def check_existing_results(targets: list, project_root: Path, console) -> tuple:
    """Check which targets already have results and return (existing, missing)."""
    criterion_dir = project_root / "target" / "criterion"

    if not criterion_dir.exists():
        return [], targets

    existing_targets = []
    missing_targets = []

    for target in targets:
        # Look for evidence that this target has been run
        # Check for baseline directories with estimates.json files
        has_results = False

        for benchmark_group in criterion_dir.iterdir():
            if benchmark_group.is_dir():
                baseline_dir = benchmark_group / target.name
                if baseline_dir.exists() and (baseline_dir / "estimates.json").exists():
                    has_results = True
                    break

        if has_results:
            existing_targets.append(target)
        else:
            missing_targets.append(target)

    return existing_targets, missing_targets


def print_benchmark_plan(targets: list, args, console):
    """Print the benchmark execution plan."""

    table = Table(title="Quick Benchmark Plan")
    table.add_column("Target", style="cyan")
    table.add_column("RUSTFLAGS", style="yellow")
    table.add_column("Description", style="green")

    for target in targets:
        rustflags = getattr(target, 'rustflags', '') or 'default'
        description = getattr(target, 'description', 'No description')
        table.add_row(target.name, rustflags, description)

    console.print()
    console.print(table)

    # Print configuration summary
    config_text = Text()
    config_text.append(f"Measurement time: {args.measurement_time}s per benchmark\n")
    config_text.append(f"Timeout: {args.timeout}s per target\n")
    config_text.append(f"Skip existing: {'Yes' if args.skip_existing else 'No'}\n")
    config_text.append(f"Show progress: {'Yes' if args.show_progress else 'No'}")

    console.print(Panel(
        config_text,
        title="Configuration",
        border_style="blue"
    ))


@handle_common_exceptions
def main() -> int:
    """Main entry point."""
    # Parse arguments
    args = parse_arguments()

    # Initialize environment
    console, project_root, config_loader = setup_script_environment(
        "Quick Benchmark Suite",
        validate_environment=True
    )

    # Resolve targets
    try:
        targets = resolve_quick_targets(args.targets, config_loader, console)
        if not targets:
            return 1
    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        return 1

        # Check existing results if requested
        if args.skip_existing:
            existing_targets, targets = check_existing_results(targets, project_root, console)
            if existing_targets:
                console.print(f"[yellow]⚠️  Skipping {len(existing_targets)} targets with existing results[/yellow]")
                for target in existing_targets:
                    console.print(f"  - {target.name}")

            if not targets:
                console.print("[green]✅ All targets already have results - nothing to do[/green]")
                return 0

        # Show benchmark plan
        print_benchmark_plan(targets, args, console)

        # Prepare execution configuration
        execution_config = config_loader.load_execution_config()
        execution_config['measurement_time_seconds'] = args.measurement_time
        execution_config['single_benchmark_run']['timeout_seconds'] = args.timeout

        # Initialize and run quick benchmarks
        console.print("\n[blue]🚀 Starting quick benchmark execution...[/blue]")

        runner = QuickBenchmarkRunner(
            config=execution_config,
            console=console
        )

        if args.show_progress:
            with create_progress_context(console, "Quick Benchmarks") as progress:
                main_task = progress.add_task("Quick Benchmarks", total=len(targets))

                results = []
                for i, target in enumerate(targets):
                    progress.update(main_task, description=f"Running {target.name}")
                    result = runner.run_single_target(target, project_root)
                    results.append(result)
                    progress.advance(main_task)
        else:
            results = []
            for i, target in enumerate(targets):
                console.print(f"\n[blue]⚡ Running target {i+1}/{len(targets)}: {target.name}[/blue]")
                result = runner.run_single_target(target, project_root)
                results.append(result)

        # Print results summary
        console.print("\n" + "="*60)
        console.print("[bold]Quick Benchmark Results[/bold]")
        console.print("="*60)

        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]

        # Results table
        table = Table()
        table.add_column("Target", style="cyan")
        table.add_column("Status", style="bold")
        table.add_column("Duration", justify="right")
        table.add_column("Notes")

        for result in results:
            if result.success:
                status = "[green]✅ Success[/green]"
                duration = f"{result.duration:.1f}s" if hasattr(result, 'duration') else "N/A"
                notes = "Completed successfully"
            else:
                status = "[red]❌ Failed[/red]"
                duration = "N/A"
                notes = result.error_message if hasattr(result, 'error_message') else "Unknown error"

            table.add_row(result.target.name, status, duration, notes)

        console.print()
        console.print(table)

        # Summary
        summary_text = Text()
        summary_text.append(f"✅ Successful: {len(successful)}\n", style="green")
        if failed:
            summary_text.append(f"❌ Failed: {len(failed)}\n", style="red")
        summary_text.append(f"⏱️  Total time: {sum(getattr(r, 'duration', 0) for r in results):.1f}s", style="blue")

        console.print(Panel(
            summary_text,
            title="Summary",
            border_style="green" if not failed else "yellow"
        ))

        if failed and args.verbose:
            console.print("\n[red]Failed target details:[/red]")
            for result in failed:
                console.print(f"  {result.target.name}: {getattr(result, 'error_message', 'Unknown error')}")

        return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
