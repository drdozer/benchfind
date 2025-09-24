"""
# Shared Utilities for Benchfind Scripts

This module contains common functionality used across multiple scripts and CLI
commands to eliminate code duplication and ensure consistent behavior.

## The DRY Principle

The scripts were duplicating significant amounts of code including:
- Project root detection logic
- Import path setup
- Argument parsing patterns
- Error handling structures
- Target resolution logic
- Console initialization

This utilities module consolidates these common patterns into reusable functions.
"""

import sys
import argparse
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable, TypeVar

T = TypeVar('T')

# Import path setup - this needs to happen before other benchfind imports
def setup_import_paths() -> Path:
    """
    Set up Python import paths for benchfind modules.

    This handles the common pattern of adding the src directory to sys.path
    so that benchfind modules can be imported from scripts.

    Returns:
        Path to the src directory that was added to sys.path
    """
    script_dir = Path(__file__).parent
    src_dir = script_dir.parent.parent / "src" if script_dir.name != "src" else script_dir.parent

    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    return src_dir


def find_project_root(start_path: Optional[Path] = None) -> Path:
    """
    Find the project root directory by looking for benchfind project structure.

    This handles multiple project layouts:
    - Direct Cargo.toml (legacy structure)
    - benchfind/rust_project/Cargo.toml structure
    - Running from orchestration directory

    Args:
        start_path: Optional starting path (defaults to current directory)

    Returns:
        Path to the Rust project root (directory containing Cargo.toml)

    Raises:
        RuntimeError: If project root cannot be found
    """
    current = (start_path or Path.cwd()).resolve()

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

    raise RuntimeError(
        "Could not find project root. Please run from the benchfind project directory.\n"
        "Looking for either:\n"
        "  - A directory containing Cargo.toml\n"
        "  - A rust_project/ subdirectory containing Cargo.toml"
    )


def validate_rust_environment(project_root: Path) -> List[str]:
    """
    Validate that the Rust environment is set up correctly for benchmarking.

    Args:
        project_root: Path to the Rust project root

    Returns:
        List of validation error messages (empty if all checks pass)
    """
    errors = []

    # Check for required files
    required_files = [
        "Cargo.toml",
        "src/lib.rs",
        "benches/bench_newlines.rs",
        "benches/bench_csv.rs"
    ]

    for file_path in required_files:
        if not (project_root / file_path).exists():
            errors.append(f"Missing required file: {file_path}")

    # Check for Rust toolchain
    import subprocess
    try:
        result = subprocess.run(
            ["cargo", "--version"],
            capture_output=True,
            text=True,
            check=True
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        errors.append("Cargo not found or not working")

    try:
        result = subprocess.run(
            ["rustc", "--version"],
            capture_output=True,
            text=True,
            check=True
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        errors.append("Rustc not found or not working")

    return errors


def create_console():
    """
    Create and configure a Rich console for consistent output formatting.

    Returns:
        Rich Console instance, or a fallback console if Rich is not available
    """
    try:
        from rich.console import Console
        return Console()
    except ImportError:
        # Fallback console for environments without rich
        class FallbackConsole:
            def print(self, *args, **kwargs):
                # Convert rich markup to plain text (basic implementation)
                text = ' '.join(str(arg) for arg in args)
                # Remove basic rich markup
                import re
                text = re.sub(r'\[/?[^\]]*\]', '', text)
                print(text)

            def print_exception(self):
                import traceback
                traceback.print_exc()

        return FallbackConsole()


def resolve_targets(target_spec: Optional[str], config_loader, console=None) -> List:
    """
    Resolve target specification to a list of target definitions.

    This handles the common pattern of resolving target specifications:
    - None or empty -> use development group
    - Group name -> resolve to group targets
    - Comma-separated list -> resolve individual targets

    Args:
        target_spec: Target specification string
        config_loader: ConfigurationLoader instance
        console: Optional console for output

    Returns:
        List of TargetDefinition objects

    Raises:
        ValueError: If target specification is invalid
    """
    if console is None:
        console = create_console()

    # Default to development group if no spec provided
    if not target_spec:
        try:
            targets = config_loader.get_target_group('development')
            console.print(f"Using development targets: {len(targets)} targets")
            return targets
        except ValueError:
            # Fallback to basic targets if development group doesn't exist
            console.print("Development group not found, using default targets")
            return [
                target for target in config_loader.get_all_targets()
                if target.name in ['default', 'native']
            ]

    # Check if it's a predefined group
    group_names = ['development', 'comprehensive', 'all', 'production']
    if target_spec.lower() in group_names:
        try:
            targets = config_loader.get_target_group(target_spec.lower())
            console.print(f"Using target group '{target_spec}': {len(targets)} targets")
            return targets
        except ValueError as e:
            raise ValueError(f"Target group '{target_spec}' not found: {e}")

    # Parse as comma-separated list
    target_names = [name.strip() for name in target_spec.split(",")]
    available_targets = config_loader.get_all_targets()
    available_names = [t.name for t in available_targets]

    targets = []
    for name in target_names:
        if name not in available_names:
            raise ValueError(f"Unknown target: {name}. Available: {', '.join(available_names)}")
        targets.extend([t for t in available_targets if t.name == name])

    console.print(f"Using specified targets: {len(targets)} targets")
    return targets


def create_standard_argument_parser(
    description: str,
    epilog: Optional[str] = None
) -> argparse.ArgumentParser:
    """
    Create a standardized argument parser with common options.

    Args:
        description: Description for the command
        epilog: Optional epilog with usage examples

    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=epilog
    )

    # Add common arguments
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without actually executing"
    )

    return parser


def handle_common_exceptions(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator to handle common exceptions in a consistent way.

    This provides standardized error handling for:
    - KeyboardInterrupt (Ctrl+C)
    - FileNotFoundError
    - PermissionError
    - Generic exceptions with optional verbose output
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except KeyboardInterrupt:
            console = create_console()
            console.print("\n⚠️  Interrupted by user")
            return 130
        except FileNotFoundError as e:
            console = create_console()
            console.print(f"❌ File not found: {e}")
            return 1
        except PermissionError as e:
            console = create_console()
            console.print(f"❌ Permission denied: {e}")
            return 1
        except Exception as e:
            console = create_console()
            console.print(f"❌ Error: {e}")

            # Check if verbose mode is enabled (look for --verbose in sys.argv)
            if "--verbose" in sys.argv or "-v" in sys.argv:
                console.print_exception()
            return 1

    return wrapper


def initialize_benchfind_environment() -> Dict[str, Any]:
    """
    Initialize the benchfind environment with all common setup.

    This is a convenience function that handles:
    - Import path setup
    - Project root detection
    - Environment validation
    - Configuration loading
    - Console creation

    Returns:
        Dictionary containing initialized components:
        - 'project_root': Path to project root
        - 'console': Rich console instance
        - 'config_loader': ConfigurationLoader instance
        - 'validation_errors': List of validation errors (if any)
    """
    # Set up imports
    setup_import_paths()

    # Import benchfind modules (after path setup)
    from benchfind.config import ConfigurationLoader

    # Find project root
    project_root = find_project_root()

    # Create console
    console = create_console()

    # Validate environment
    validation_errors = validate_rust_environment(project_root)

    # Load configuration
    config_loader = ConfigurationLoader()

    return {
        'project_root': project_root,
        'console': console,
        'config_loader': config_loader,
        'validation_errors': validation_errors
    }


def print_environment_info(env: Dict[str, Any]) -> None:
    """
    Print environment information in a standardized format.

    Args:
        env: Environment dictionary from initialize_benchfind_environment()
    """
    console = env['console']
    project_root = env['project_root']
    validation_errors = env['validation_errors']

    console.print(f"📁 Project root: {project_root}")

    if validation_errors:
        console.print("⚠️  Environment validation issues:")
        for error in validation_errors:
            console.print(f"  - {error}")
    else:
        console.print("✅ Environment validation passed")


def create_progress_context(console, description: str = "Processing"):
    """
    Create a Rich progress context for consistent progress reporting.

    Args:
        console: Rich console instance
        description: Default task description

    Returns:
        Rich Progress context manager
    """
    try:
        from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        )
    except ImportError:
        # Fallback for environments without rich
        class FallbackProgress:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def add_task(self, description, total=None):
                print(f"Starting: {description}")
                return 1
            def update(self, task_id, **kwargs):
                if 'description' in kwargs:
                    print(f"Progress: {kwargs['description']}")
            def advance(self, task_id, advance=1):
                pass

        return FallbackProgress()


# Convenience function for scripts to get everything they need
def setup_script_environment(
    description: str,
    validate_environment: bool = True
) -> tuple:
    """
    Complete setup for a benchfind script.

    This is the most convenient function for scripts to use - it handles
    all the common setup and returns everything needed.

    Args:
        description: Script description for logging
        validate_environment: Whether to validate the Rust environment

    Returns:
        Tuple of (console, project_root, config_loader, args) where args
        is None (scripts should handle their own argument parsing)

    Raises:
        SystemExit: If environment validation fails and validate_environment=True
    """
    env = initialize_benchfind_environment()

    console = env['console']
    project_root = env['project_root']
    config_loader = env['config_loader']
    validation_errors = env['validation_errors']

    console.print(f"🚀 {description}")
    print_environment_info(env)

    if validate_environment and validation_errors:
        console.print("❌ Environment validation failed")
        sys.exit(1)

    return console, project_root, config_loader
