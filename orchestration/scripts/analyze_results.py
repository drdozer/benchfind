#!/usr/bin/env python3
"""
Results Analysis Script

This script provides comprehensive analysis of stored benchmark results,
including performance comparisons, SIMD detection summaries, and trend analysis.

It can analyze individual runs, compare across runs, or provide aggregate statistics
across all stored results.
"""

import sys
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

# Set up import paths and get common utilities
script_dir = Path(__file__).parent
src_dir = script_dir.parent / "src"
sys.path.insert(0, str(src_dir))

from benchfind.utils import (
    setup_script_environment,
    create_standard_argument_parser,
    handle_common_exceptions,
    create_progress_context
)

try:
    from benchfind.config import ConfigurationLoader
    from benchfind.storage import ResultsStorage
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.tree import Tree
    import pandas as pd
    import numpy as np
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Please ensure the benchfind package is installed and dependencies are available")
    sys.exit(1)


def parse_arguments():
    import argparse
    """Parse command line arguments."""
    parser = create_standard_argument_parser(
        description="Analyze stored benchmark results",
        epilog="""
Examples:
  %(prog)s --list                        # List all available runs
  %(prog)s --latest                      # Analyze the most recent run
  %(prog)s --run-id hostname_abc123_1.70 # Analyze specific run
  %(prog)s --compare --runs 3            # Compare last 3 runs
  %(prog)s --export-csv results.csv      # Export results to CSV
  %(prog)s --simd-summary                # Show SIMD detection summary
        """
    )

    # Action selection (mutually exclusive)
    action_group = parser.add_mutually_exclusive_group(required=True)
    action_group.add_argument(
        "--list",
        action="store_true",
        help="List all available benchmark runs"
    )

    action_group.add_argument(
        "--latest",
        action="store_true",
        help="Analyze the most recent benchmark run"
    )

    action_group.add_argument(
        "--run-id",
        type=str,
        help="Analyze specific run by ID"
    )

    action_group.add_argument(
        "--compare",
        action="store_true",
        help="Compare multiple runs"
    )

    action_group.add_argument(
        "--simd-summary",
        action="store_true",
        help="Show SIMD detection summary across all runs"
    )

    # Options for comparison
    parser.add_argument(
        "--runs",
        type=int,
        default=2,
        help="Number of recent runs to compare (default: 2)"
    )

    parser.add_argument(
        "--export-csv",
        type=str,
        help="Export results to CSV file"
    )

    parser.add_argument(
        "--export-json",
        type=str,
        help="Export results to JSON file"
    )

    parser.add_argument(
        "--format",
        choices=["table", "json", "csv"],
        default="table",
        help="Output format (default: table)"
    )

    return parser.parse_args()


def list_runs(storage, console) -> None:
    """List all available benchmark runs."""
    runs = storage.list_runs()

    if not runs:
        console.print("[yellow]No benchmark runs found[/yellow]")
        return

    table = Table(title=f"Available Benchmark Runs ({len(runs)} total)")
    table.add_column("Run ID", style="cyan")
    table.add_column("Timestamp", style="blue")
    table.add_column("Hostname", style="green")
    table.add_column("Rustc Version", style="yellow")
    table.add_column("Targets", justify="right")
    table.add_column("Size", justify="right")

    for run in sorted(runs, key=lambda x: x.timestamp, reverse=True):
        # Get additional details
        targets_count = len(run.targets) if hasattr(run, 'targets') and run.targets else "?"

        # Calculate directory size
        run_dir = storage.get_run_directory(run.run_id)
        size_mb = 0
        if run_dir.exists():
            try:
                size_bytes = sum(f.stat().st_size for f in run_dir.rglob('*') if f.is_file())
                size_mb = size_bytes / (1024 * 1024)
            except:
                size_mb = 0

        table.add_row(
            run.run_id,
            run.timestamp.strftime("%Y-%m-%d %H:%M"),
            run.hostname,
            run.rustc_version.replace("_", "."),
            str(targets_count),
            f"{size_mb:.1f}MB"
        )

    console.print(table)


def analyze_single_run(storage, run_id: str, console, verbose: bool = False) -> Optional[Dict]:
    """Analyze a single benchmark run."""
    if not storage.run_exists(run_id):
        console.print(f"[red]❌ Run not found: {run_id}[/red]")
        return None

    console.print(f"[blue]🔍 Analyzing run: {run_id}[/blue]")

    run_dir = storage.get_run_directory(run_id)

    # Load metadata
    metadata = {}
    metadata_dir = run_dir / "metadata"
    if metadata_dir.exists():
        for meta_file in metadata_dir.glob("*.json"):
            try:
                with open(meta_file) as f:
                    metadata[meta_file.stem] = json.load(f)
            except Exception as e:
                if verbose:
                    console.print(f"[yellow]⚠️  Could not load {meta_file}: {e}[/yellow]")

    # Show system information
    if "system-info" in metadata:
        sys_info = metadata["system-info"]

        info_table = Table(title="System Information")
        info_table.add_column("Property", style="cyan")
        info_table.add_column("Value", style="white")

        info_table.add_row("Hostname", sys_info.get("hostname", "Unknown"))
        info_table.add_row("OS", f"{sys_info.get('os', {}).get('name', 'Unknown')} {sys_info.get('os', {}).get('release', '')}")
        info_table.add_row("CPU", sys_info.get("cpu", {}).get("model", "Unknown"))
        info_table.add_row("Cores", str(sys_info.get("cpu", {}).get("cores", "Unknown")))

        memory_gb = "Unknown"
        if sys_info.get("memory", {}).get("total_kb"):
            try:
                memory_gb = f"{int(sys_info['memory']['total_kb']) / 1024 / 1024:.1f} GB"
            except:
                pass
        info_table.add_row("Memory", memory_gb)

        console.print(info_table)

    # Show build information
    if "build-info" in metadata:
        build_info = metadata["build-info"]

        build_table = Table(title="Build Information")
        build_table.add_column("Property", style="cyan")
        build_table.add_column("Value", style="white")

        build_table.add_row("Rustc Version", build_info.get("rust", {}).get("rustc_version", "Unknown"))
        build_table.add_row("Git Branch", build_info.get("git", {}).get("branch", "Unknown"))
        build_table.add_row("Git Commit", build_info.get("git", {}).get("commit_hash", "Unknown")[:12])
        build_table.add_row("Status Clean", "Yes" if build_info.get("git", {}).get("status_clean") else "No")

        console.print(build_table)

    # Analyze benchmark results
    raw_results_dir = run_dir / "raw-results" / "criterion"
    benchmark_data = {}

    if raw_results_dir.exists():
        console.print("\n[blue]📊 Benchmark Results Analysis[/blue]")

        # Parse Criterion results
        for benchmark_group in raw_results_dir.iterdir():
            if benchmark_group.is_dir():
                group_name = benchmark_group.name
                benchmark_data[group_name] = {}

                for target_dir in benchmark_group.iterdir():
                    if target_dir.is_dir() and (target_dir / "estimates.json").exists():
                        try:
                            with open(target_dir / "estimates.json") as f:
                                estimates = json.load(f)
                                benchmark_data[group_name][target_dir.name] = estimates
                        except Exception as e:
                            if verbose:
                                console.print(f"[yellow]⚠️  Could not load estimates for {target_dir}: {e}[/yellow]")

        # Display results in tables
        for group_name, targets in benchmark_data.items():
            if targets:
                table = Table(title=f"Benchmark Group: {group_name}")
                table.add_column("Target", style="cyan")
                table.add_column("Mean (ns)", justify="right", style="green")
                table.add_column("Std Dev (ns)", justify="right", style="yellow")
                table.add_column("Median (ns)", justify="right", style="blue")

                for target_name, estimates in targets.items():
                    mean_ns = estimates.get("mean", {}).get("point_estimate", 0)
                    std_dev_ns = estimates.get("std_dev", {}).get("point_estimate", 0)
                    median_ns = estimates.get("median", {}).get("point_estimate", 0)

                    table.add_row(
                        target_name,
                        f"{mean_ns:,.0f}",
                        f"{std_dev_ns:,.0f}",
                        f"{median_ns:,.0f}"
                    )

                console.print(table)

    # Analyze SIMD detection
    assembly_dir = run_dir / "assembly_extracts"
    simd_results = {}

    if assembly_dir.exists():
        console.print("\n[blue]🔬 SIMD Analysis[/blue]")

        for target_dir in assembly_dir.iterdir():
            if target_dir.is_dir():
                simd_file = target_dir / "simd_analysis.json"
                if simd_file.exists():
                    try:
                        with open(simd_file) as f:
                            simd_data = json.load(f)
                            simd_results[target_dir.name] = simd_data
                    except Exception as e:
                        if verbose:
                            console.print(f"[yellow]⚠️  Could not load SIMD analysis for {target_dir}: {e}[/yellow]")

        if simd_results:
            simd_table = Table(title="SIMD Instruction Detection")
            simd_table.add_column("Target", style="cyan")
            simd_table.add_column("SIMD Detected", style="bold")
            simd_table.add_column("Instruction Count", justify="right")
            simd_table.add_column("Primary Instructions", style="yellow")

            for target_name, simd_data in simd_results.items():
                detected = simd_data.get("simd_detected", False)
                instructions = simd_data.get("detected_instructions", [])

                status = "[green]✅ Yes[/green]" if detected else "[red]❌ No[/red]"
                count = str(len(instructions))
                primary = ", ".join(instructions[:3]) + ("..." if len(instructions) > 3 else "")

                simd_table.add_row(target_name, status, count, primary)

            console.print(simd_table)

    return {
        "run_id": run_id,
        "metadata": metadata,
        "benchmark_data": benchmark_data,
        "simd_results": simd_results
    }


def compare_runs(storage, num_runs: int, console) -> None:
    """Compare multiple benchmark runs."""
    runs = storage.list_runs()

    if len(runs) < num_runs:
        console.print(f"[red]❌ Only {len(runs)} runs available, cannot compare {num_runs}[/red]")
        return

    # Get the most recent runs
    recent_runs = sorted(runs, key=lambda x: x.timestamp, reverse=True)[:num_runs]

    console.print(f"[blue]🔍 Comparing {num_runs} most recent runs[/blue]")

    # Show comparison overview
    comparison_table = Table(title="Run Comparison Overview")
    comparison_table.add_column("Run ID", style="cyan")
    comparison_table.add_column("Timestamp", style="blue")
    comparison_table.add_column("Rustc Version", style="yellow")
    comparison_table.add_column("Source Hash", style="green")

    for run in recent_runs:
        comparison_table.add_row(
            run.run_id,
            run.timestamp.strftime("%Y-%m-%d %H:%M"),
            run.rustc_version.replace("_", "."),
            run.source_hash
        )

    console.print(comparison_table)

    # For detailed comparison, we'd need to analyze performance differences
    console.print("\n[yellow]📊 Detailed performance comparison not yet implemented[/yellow]")
    console.print("This would show performance changes between runs, regression detection, etc.")


def simd_summary(storage, console) -> None:
    """Show SIMD detection summary across all runs."""
    runs = storage.list_runs()

    if not runs:
        console.print("[yellow]No benchmark runs found[/yellow]")
        return

    console.print(f"[blue]🔬 SIMD Detection Summary ({len(runs)} runs)[/blue]")

    # Collect SIMD data from all runs
    simd_by_target = {}

    for run in runs:
        run_dir = storage.get_run_directory(run.run_id)
        assembly_dir = run_dir / "assembly_extracts"

        if assembly_dir.exists():
            for target_dir in assembly_dir.iterdir():
                if target_dir.is_dir():
                    simd_file = target_dir / "simd_analysis.json"
                    if simd_file.exists():
                        try:
                            with open(simd_file) as f:
                                simd_data = json.load(f)
                                target_name = target_dir.name

                                if target_name not in simd_by_target:
                                    simd_by_target[target_name] = {
                                        "total_runs": 0,
                                        "simd_detected": 0,
                                        "instructions": set()
                                    }

                                simd_by_target[target_name]["total_runs"] += 1
                                if simd_data.get("simd_detected", False):
                                    simd_by_target[target_name]["simd_detected"] += 1
                                    instructions = simd_data.get("detected_instructions", [])
                                    simd_by_target[target_name]["instructions"].update(instructions)

                        except Exception:
                            pass

    if not simd_by_target:
        console.print("[yellow]No SIMD analysis data found[/yellow]")
        return

    # Display summary table
    summary_table = Table(title="SIMD Detection Summary by Target")
    summary_table.add_column("Target", style="cyan")
    summary_table.add_column("Detection Rate", justify="right", style="bold")
    summary_table.add_column("Runs", justify="right")
    summary_table.add_column("Unique Instructions", justify="right")
    summary_table.add_column("Common Instructions", style="yellow")

    for target_name, data in sorted(simd_by_target.items()):
        detection_rate = data["simd_detected"] / data["total_runs"] * 100
        rate_style = "green" if detection_rate > 80 else "yellow" if detection_rate > 20 else "red"

        common_instructions = list(data["instructions"])[:5]
        common_str = ", ".join(common_instructions) + ("..." if len(data["instructions"]) > 5 else "")

        summary_table.add_row(
            target_name,
            f"[{rate_style}]{detection_rate:.1f}%[/{rate_style}]",
            f"{data['simd_detected']}/{data['total_runs']}",
            str(len(data["instructions"])),
            common_str
        )

    console.print(summary_table)


def export_results(storage, export_file: str, format_type: str, console) -> None:
    """Export results to file."""
    console.print(f"[blue]📤 Exporting results to {export_file} ({format_type})[/blue]")

    # This is a placeholder - would need to implement actual export logic
    console.print("[yellow]Export functionality not yet implemented[/yellow]")


@handle_common_exceptions
def main() -> int:
    """Main entry point."""
    # Parse arguments
    args = parse_arguments()

    # Initialize environment
    console, project_root, config_loader = setup_script_environment(
        "Benchmark Results Analysis",
        validate_environment=False  # Analysis doesn't need full Rust environment
    )

    # Initialize storage
    storage_config = config_loader.load_storage_config()
    storage = ResultsStorage(storage_config, project_root)

    # Execute requested action
    if args.list:
        list_runs(storage, console)

    elif args.latest:
        runs = storage.list_runs()
        if not runs:
            console.print("[yellow]No benchmark runs found[/yellow]")
            return 1

        latest_run = max(runs, key=lambda x: x.timestamp)
        analyze_single_run(storage, latest_run.run_id, console, args.verbose)

    elif args.run_id:
        result = analyze_single_run(storage, args.run_id, console, args.verbose)
        if not result:
            return 1

    elif args.compare:
        compare_runs(storage, args.runs, console)

    elif args.simd_summary:
        simd_summary(storage, console)

    # Handle exports
    if args.export_csv:
        export_results(storage, args.export_csv, "csv", console)

    if args.export_json:
        export_results(storage, args.export_json, "json", console)

    return 0


if __name__ == "__main__":
    sys.exit(main())
