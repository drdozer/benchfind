#!/usr/bin/env python3
"""
Comprehensive Benchmarking Script

This script orchestrates complete benchmark data collection including:
- System and build metadata collection
- Benchmark execution with proper result organization
- Assembly generation and SIMD analysis
- Structured data storage for future analysis

This replaces the legacy run_comprehensive_benchmarks.sh bash script with
a maintainable Python implementation.
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
    from benchfind.storage import ResultsStorage
    from benchfind.metadata import MetadataCollector
    from benchfind.benchmark import ComprehensiveBenchmarkRunner
    from benchfind.assembly import AssemblyAnalyzer
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Please ensure the benchfind package is installed and dependencies are available")
    sys.exit(1)


def parse_arguments():
    import argparse
    """Parse command line arguments."""
    parser = create_standard_argument_parser(
        description="Run comprehensive benchmarks with metadata collection and SIMD analysis",
        epilog="""
Examples:
  %(prog)s                           # Run all targets with default settings
  %(prog)s --targets native,avx2     # Run only specific targets
  %(prog)s --force-rerun             # Force rerun even if results exist
  %(prog)s --skip-assembly           # Skip assembly generation and analysis
  %(prog)s --measurement-time 30     # Use 30 second measurement time
        """
    )

    parser.add_argument(
        "--targets",
        type=str,
        help="Comma-separated list of targets to run (default: comprehensive group)"
    )

    parser.add_argument(
        "--force-rerun",
        action="store_true",
        help="Force rerun even if results already exist for this configuration"
    )

    parser.add_argument(
        "--skip-assembly",
        action="store_true",
        help="Skip assembly generation and SIMD analysis"
    )

    parser.add_argument(
        "--measurement-time",
        type=int,
        help="Override measurement time per benchmark in seconds"
    )

    return parser.parse_args()


def validate_environment(console: Console, project_root: Path) -> bool:
    """Validate that the environment is ready for benchmarking."""
    console.print("\n[blue]🔍 Validating environment...[/blue]")

    from benchfind.utils import validate_rust_environment
    errors = validate_rust_environment(project_root)

    if errors:
        console.print(f"[red]❌ Environment validation failed:[/red]")
        for error in errors:
            console.print(f"  - {error}")
        return False

    console.print("[green]✅ Environment validation passed[/green]")
    return True


@handle_common_exceptions
def main() -> int:
    """Main entry point."""
    # Parse arguments
    args = parse_arguments()

    # Initialize environment
    console, project_root, config_loader = setup_script_environment(
        "Comprehensive Benchmark Suite",
        validate_environment=True
    )

    # Initialize storage system
    storage_config = config_loader.load_storage_config()
    storage = ResultsStorage(storage_config, project_root)

    # Resolve targets
    try:
        targets = resolve_targets(args.targets or "comprehensive", config_loader, console)
    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        return 1

    console.print(f"[green]✅ Loaded {len(targets)} target configurations[/green]")

    # Check if results already exist
    run_id = storage.get_current_run_id()
    console.print(f"[blue]🔍 Run ID:[/blue] {run_id}")

    if storage.run_exists(run_id) and not args.force_rerun:
        console.print(Panel(
            "[yellow]Results already exist for this configuration[/yellow]\n\n"
            f"Run ID: {run_id}\n"
            f"Results directory: {storage.get_run_directory(run_id)}\n\n"
            "Use --force-rerun to override, or modify source code to generate a new run ID.",
            title="Skipping Benchmark Run",
            border_style="yellow"
        ))
        return 0

    # Show run plan
    console.print(Panel(
        f"[bold]Comprehensive Benchmark Plan[/bold]\n\n"
        f"Run ID: {run_id}\n"
        f"Targets: {', '.join(t.name for t in targets)}\n"
        f"Assembly analysis: {'Disabled' if args.skip_assembly else 'Enabled'}\n"
        f"Force rerun: {'Yes' if args.force_rerun else 'No'}\n"
        f"Measurement time: {args.measurement_time or 'Default'}s",
        title="Benchmark Configuration",
        border_style="blue"
    ))

    if args.dry_run:
        console.print("[yellow]🔍 Dry run completed - no benchmarks executed[/yellow]")
        return 0

    # Initialize components
    console.print("\n[blue]🚀 Starting comprehensive benchmark execution...[/blue]")

    # Collect metadata
    metadata_collector = MetadataCollector(project_root)
    metadata = metadata_collector.collect_all_metadata()

    # Initialize benchmark runner
    execution_config = config_loader.load_execution_config()
    if args.measurement_time:
        execution_config['measurement_time_seconds'] = args.measurement_time

    runner = ComprehensiveBenchmarkRunner(
        targets=targets,
        config=execution_config,
        console=console
    )

    # Start the run
    run_layout = storage.start_run(run_id, targets, metadata)

    # Execute benchmarks
    console.print(f"\n[blue]⚡ Executing benchmarks for {len(targets)} targets...[/blue]")
    results = runner.run_all_benchmarks(metadata, storage)

    # Generate assembly analysis if requested
    if not args.skip_assembly:
        console.print("\n[blue]🔬 Generating assembly analysis...[/blue]")

        assembly_analyzer = AssemblyAnalyzer(
            config=config_loader.load_assembly_config(),
            console=console
        )

        with create_progress_context(console, "Assembly analysis") as progress:
            analysis_task = progress.add_task("Analyzing targets...", total=len(targets))

            for target in targets:
                progress.update(analysis_task, description=f"Analyzing {target.name}")
                if target.name in [r.target.name for r in results if r.success]:
                    assembly_dir = run_layout.get_assembly_dir(target.name)
                    try:
                        assembly_analyzer.generate_and_analyze_target(
                            target,
                            assembly_dir,
                            project_root
                        )
                        console.print(f"[green]✅ Assembly analysis completed for {target.name}[/green]")
                    except Exception as e:
                        console.print(f"[yellow]⚠️  Assembly analysis failed for {target.name}: {e}[/yellow]")
                progress.advance(analysis_task)

    # Finalize run
    storage.finalize_run(run_id, targets, metadata)

    # Print summary
    successful = len([r for r in results if r.success])
    failed = len([r for r in results if not r.success])

    summary_text = Text()
    summary_text.append("Comprehensive benchmark completed!\n\n", style="bold green")
    summary_text.append(f"✅ Successful targets: {successful}\n", style="green")
    if failed > 0:
        summary_text.append(f"❌ Failed targets: {failed}\n", style="red")
    summary_text.append(f"📁 Results stored in: {run_layout.run_dir}\n", style="blue")
    summary_text.append(f"🔍 Run ID: {run_id}", style="blue")

    console.print(Panel(
        summary_text,
        title="Benchmark Summary",
        border_style="green" if failed == 0 else "yellow"
    ))

    return 0 if failed == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
