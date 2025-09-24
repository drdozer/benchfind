#!/usr/bin/env python3
"""
Benchfind CLI Entry Point

This script provides the main command-line interface for benchfind orchestration,
routing to the appropriate sub-commands and handling global configuration.
"""

import sys
import argparse
from pathlib import Path
from typing import List, Optional

# Add the parent directory to sys.path so we can import benchfind modules
script_dir = Path(__file__).parent
src_dir = script_dir.parent / "src"
sys.path.insert(0, str(src_dir))

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Please ensure the benchfind package is installed and dependencies are available")
    sys.exit(1)


def create_main_parser() -> argparse.ArgumentParser:
    """Create the main argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        prog="benchfind",
        description="Benchfind orchestration system for systematic Rust benchmarking",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  benchfind quick                        # Quick benchmarks for development
  benchfind comprehensive                # Full benchmarks with metadata
  benchfind analyze --latest             # Analyze most recent results
  benchfind config validate              # Validate configuration files
  benchfind manage cleanup --older-than 30d  # Cleanup old results
        """
    )

    parser.add_argument(
        "--version",
        action="version",
        version="benchfind 1.0.0"
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output"
    )

    # Create subcommands
    subparsers = parser.add_subparsers(
        dest="command",
        help="Available commands",
        metavar="COMMAND"
    )

    # Quick benchmarking command
    quick_parser = subparsers.add_parser(
        "quick",
        help="Run quick benchmarks for development iteration",
        description="Fast benchmarking optimized for development workflows"
    )
    quick_parser.add_argument("--targets", help="Target group or comma-separated list")
    quick_parser.add_argument("--measurement-time", type=int, default=5, help="Measurement time in seconds")
    quick_parser.add_argument("--skip-existing", action="store_true", help="Skip targets with existing results")
    quick_parser.add_argument("--show-progress", action="store_true", help="Show detailed progress")

    # Comprehensive benchmarking command
    comp_parser = subparsers.add_parser(
        "comprehensive",
        help="Run comprehensive benchmarks with full metadata collection",
        description="Complete benchmark suite with metadata, assembly analysis, and SIMD detection"
    )
    comp_parser.add_argument("--targets", help="Comma-separated list of targets")
    comp_parser.add_argument("--force-rerun", action="store_true", help="Force rerun even if results exist")
    comp_parser.add_argument("--skip-assembly", action="store_true", help="Skip assembly analysis")
    comp_parser.add_argument("--measurement-time", type=int, help="Measurement time in seconds")
    comp_parser.add_argument("--dry-run", action="store_true", help="Show plan without executing")

    # Analysis command
    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Analyze stored benchmark results",
        description="Examine and compare benchmark results"
    )
    analyze_group = analyze_parser.add_mutually_exclusive_group(required=True)
    analyze_group.add_argument("--list", action="store_true", help="List all available runs")
    analyze_group.add_argument("--latest", action="store_true", help="Analyze most recent run")
    analyze_group.add_argument("--run-id", help="Analyze specific run")
    analyze_group.add_argument("--compare", action="store_true", help="Compare multiple runs")
    analyze_group.add_argument("--simd-summary", action="store_true", help="SIMD detection summary")
    analyze_parser.add_argument("--runs", type=int, default=2, help="Number of runs to compare")
    analyze_parser.add_argument("--export-csv", help="Export to CSV file")
    analyze_parser.add_argument("--export-json", help="Export to JSON file")

    # Configuration command
    config_parser = subparsers.add_parser(
        "config",
        help="Configuration management",
        description="Validate and manage configuration files"
    )
    config_subparsers = config_parser.add_subparsers(dest="config_action")
    config_subparsers.add_parser("validate", help="Validate all configuration files")
    config_subparsers.add_parser("show", help="Show current configuration")

    targets_parser = config_subparsers.add_parser("targets", help="List available targets")
    targets_parser.add_argument("--group", help="Show specific target group")

    # Management command
    manage_parser = subparsers.add_parser(
        "manage",
        help="System management operations",
        description="Cleanup, maintenance, and administrative operations"
    )
    manage_subparsers = manage_parser.add_subparsers(dest="manage_action")

    cleanup_parser = manage_subparsers.add_parser("cleanup", help="Cleanup old results")
    cleanup_parser.add_argument("--older-than", help="Remove results older than (e.g., 30d, 1w)")
    cleanup_parser.add_argument("--dry-run", action="store_true", help="Show what would be cleaned")

    manage_subparsers.add_parser("stats", help="Show storage statistics")

    return parser


def handle_quick_command(args, console: Console) -> int:
    """Handle quick benchmarking command."""
    try:
        from scripts.quick_bench import main as quick_main

        # Convert args to sys.argv format for the subscript
        quick_args = ["quick_bench.py"]
        if args.targets:
            quick_args.extend(["--targets", args.targets])
        if args.measurement_time != 5:
            quick_args.extend(["--measurement-time", str(args.measurement_time)])
        if args.skip_existing:
            quick_args.append("--skip-existing")
        if args.show_progress:
            quick_args.append("--show-progress")
        if args.verbose:
            quick_args.append("--verbose")

        # Temporarily replace sys.argv
        original_argv = sys.argv
        sys.argv = quick_args
        try:
            return quick_main()
        finally:
            sys.argv = original_argv

    except ImportError:
        console.print("[red]❌ Quick benchmark module not available[/red]")
        return 1


def handle_comprehensive_command(args, console: Console) -> int:
    """Handle comprehensive benchmarking command."""
    try:
        from scripts.run_comprehensive import main as comp_main

        # Convert args to sys.argv format for the subscript
        comp_args = ["run_comprehensive.py"]
        if args.targets:
            comp_args.extend(["--targets", args.targets])
        if args.force_rerun:
            comp_args.append("--force-rerun")
        if args.skip_assembly:
            comp_args.append("--skip-assembly")
        if args.measurement_time:
            comp_args.extend(["--measurement-time", str(args.measurement_time)])
        if args.dry_run:
            comp_args.append("--dry-run")
        if args.verbose:
            comp_args.append("--verbose")

        # Temporarily replace sys.argv
        original_argv = sys.argv
        sys.argv = comp_args
        try:
            return comp_main()
        finally:
            sys.argv = original_argv

    except ImportError:
        console.print("[red]❌ Comprehensive benchmark module not available[/red]")
        return 1


def handle_analyze_command(args, console: Console) -> int:
    """Handle analysis command."""
    try:
        from scripts.analyze_results import main as analyze_main

        # Convert args to sys.argv format for the subscript
        analyze_args = ["analyze_results.py"]
        if args.list:
            analyze_args.append("--list")
        elif args.latest:
            analyze_args.append("--latest")
        elif args.run_id:
            analyze_args.extend(["--run-id", args.run_id])
        elif args.compare:
            analyze_args.append("--compare")
        elif args.simd_summary:
            analyze_args.append("--simd-summary")

        if hasattr(args, 'runs') and args.runs != 2:
            analyze_args.extend(["--runs", str(args.runs)])
        if hasattr(args, 'export_csv') and args.export_csv:
            analyze_args.extend(["--export-csv", args.export_csv])
        if hasattr(args, 'export_json') and args.export_json:
            analyze_args.extend(["--export-json", args.export_json])
        if args.verbose:
            analyze_args.append("--verbose")

        # Temporarily replace sys.argv
        original_argv = sys.argv
        sys.argv = analyze_args
        try:
            return analyze_main()
        finally:
            sys.argv = original_argv

    except ImportError:
        console.print("[red]❌ Analysis module not available[/red]")
        return 1


def handle_config_command(args, console: Console) -> int:
    """Handle configuration command."""
    if not args.config_action:
        console.print("[yellow]No configuration action specified[/yellow]")
        return 1

    try:
        from benchfind.config import ConfigurationLoader
        config_loader = ConfigurationLoader()

        if args.config_action == "validate":
            console.print("[blue]🔍 Validating configuration files...[/blue]")
            try:
                # Load all configurations to validate them
                config_loader.load_storage_config()
                config_loader.load_execution_config()
                config_loader.get_all_targets()
                console.print("[green]✅ All configuration files are valid[/green]")
                return 0
            except Exception as e:
                console.print(f"[red]❌ Configuration validation failed: {e}[/red]")
                return 1

        elif args.config_action == "show":
            console.print("[blue]📋 Current Configuration[/blue]")
            console.print("[yellow]Configuration display not yet implemented[/yellow]")
            return 0

        elif args.config_action == "targets":
            console.print("[blue]🎯 Available Targets[/blue]")
            targets = config_loader.get_all_targets()

            from rich.table import Table
            table = Table(title="Available Targets")
            table.add_column("Name", style="cyan")
            table.add_column("RUSTFLAGS", style="yellow")
            table.add_column("Description", style="green")

            for target in targets:
                rustflags = getattr(target, 'rustflags', '') or 'default'
                description = getattr(target, 'description', 'No description')
                table.add_row(target.name, rustflags, description)

            console.print(table)
            return 0

    except ImportError:
        console.print("[red]❌ Configuration module not available[/red]")
        return 1


def handle_manage_command(args, console: Console) -> int:
    """Handle management command."""
    if not args.manage_action:
        console.print("[yellow]No management action specified[/yellow]")
        return 1

    console.print(f"[yellow]Management action '{args.manage_action}' not yet implemented[/yellow]")
    return 0


def main() -> int:
    """Main CLI entry point."""
    console = Console()

    try:
        # Parse arguments
        parser = create_main_parser()
        args = parser.parse_args()

        # Show header
        if not args.command:
            console.print(Panel(
                "[bold blue]Benchfind Orchestration System[/bold blue]\n\n"
                "Systematic Rust benchmarking with comprehensive analysis\n"
                "Use --help to see available commands",
                title="Welcome to Benchfind",
                border_style="blue"
            ))
            parser.print_help()
            return 0

        # Route to appropriate command handler
        if args.command == "quick":
            return handle_quick_command(args, console)
        elif args.command == "comprehensive":
            return handle_comprehensive_command(args, console)
        elif args.command == "analyze":
            return handle_analyze_command(args, console)
        elif args.command == "config":
            return handle_config_command(args, console)
        elif args.command == "manage":
            return handle_manage_command(args, console)
        else:
            console.print(f"[red]❌ Unknown command: {args.command}[/red]")
            return 1

    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Interrupted by user[/yellow]")
        return 130
    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]")
        if args.verbose:
            console.print_exception()
        return 1


if __name__ == "__main__":
    sys.exit(main())
