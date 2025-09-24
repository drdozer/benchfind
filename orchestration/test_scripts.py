#!/usr/bin/env python3
"""
Test script to validate basic functionality of the benchfind orchestration system.
"""

import sys
import traceback
from pathlib import Path

# Add src to path
script_dir = Path(__file__).parent
src_dir = script_dir / "src"
sys.path.insert(0, str(src_dir))

def test_imports():
    """Test that all modules can be imported."""
    print("Testing module imports...")

    try:
        from benchfind.config import ConfigurationLoader
        print("✅ Config module imported successfully")
    except Exception as e:
        print(f"❌ Config module import failed: {e}")
        return False

    try:
        from benchfind.storage import ResultsStorage
        print("✅ Storage module imported successfully")
    except Exception as e:
        print(f"❌ Storage module import failed: {e}")
        return False

    try:
        from benchfind.metadata import MetadataCollector
        print("✅ Metadata module imported successfully")
    except Exception as e:
        print(f"❌ Metadata module import failed: {e}")
        return False

    try:
        from benchfind.benchmark import QuickBenchmarkRunner, ComprehensiveBenchmarkRunner
        print("✅ Benchmark module imported successfully")
    except Exception as e:
        print(f"❌ Benchmark module import failed: {e}")
        traceback.print_exc()
        return False

    try:
        from benchfind.assembly import AssemblyAnalyzer
        print("✅ Assembly module imported successfully")
    except Exception as e:
        print(f"❌ Assembly module import failed: {e}")
        return False

    return True

def test_script_imports():
    """Test that scripts can be imported."""
    print("\nTesting script imports...")

    scripts_dir = script_dir / "scripts"
    sys.path.insert(0, str(scripts_dir))

    try:
        import quick_bench
        print("✅ Quick bench script imported successfully")
    except Exception as e:
        print(f"❌ Quick bench script import failed: {e}")
        return False

    try:
        import run_comprehensive
        print("✅ Comprehensive script imported successfully")
    except Exception as e:
        print(f"❌ Comprehensive script import failed: {e}")
        return False

    try:
        import analyze_results
        print("✅ Analysis script imported successfully")
    except Exception as e:
        print(f"❌ Analysis script import failed: {e}")
        return False

    return True

def test_config_loading():
    """Test configuration loading."""
    print("\nTesting configuration loading...")

    try:
        from benchfind.config import ConfigurationLoader
        config = ConfigurationLoader()

        # Test loading storage config
        storage_config = config.load_storage_config()
        print("✅ Storage config loaded successfully")

        # Test loading targets
        targets = config.get_all_targets()
        print(f"✅ Loaded {len(targets)} targets")

        # Test loading execution config
        exec_config = config.load_execution_config()
        print("✅ Execution config loaded successfully")

        return True
    except Exception as e:
        print(f"❌ Configuration loading failed: {e}")
        traceback.print_exc()
        return False

def test_basic_functionality():
    """Test basic functionality without running benchmarks."""
    print("\nTesting basic functionality...")

    try:
        from benchfind.config import ConfigurationLoader
        from benchfind.storage import ResultsStorage

        # Find project root (should be in benchfind/)
        project_root = script_dir.parent
        if not (project_root / "rust_project" / "Cargo.toml").exists():
            print(f"⚠️  Rust project not found at expected location: {project_root / 'rust_project'}")
            # Try alternative location
            if (project_root / "Cargo.toml").exists():
                project_root = project_root
                print(f"✅ Found Rust project at: {project_root}")
            else:
                print("❌ Could not find Rust project Cargo.toml")
                return False
        else:
            project_root = project_root / "rust_project"
            print(f"✅ Found Rust project at: {project_root}")

        # Initialize storage
        config = ConfigurationLoader()
        storage_config = config.load_storage_config()
        storage = ResultsStorage(storage_config, project_root)
        print("✅ Storage initialized successfully")

        # Test run ID generation
        run_id = storage.get_current_run_id()
        print(f"✅ Generated run ID: {run_id}")

        # Test listing runs (should be empty initially)
        runs = storage.list_runs()
        print(f"✅ Listed {len(runs)} existing runs")

        return True
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("Benchfind Orchestration System - Basic Tests")
    print("=" * 50)

    tests_passed = 0
    total_tests = 0

    # Test module imports
    total_tests += 1
    if test_imports():
        tests_passed += 1

    # Test script imports
    total_tests += 1
    if test_script_imports():
        tests_passed += 1

    # Test configuration loading
    total_tests += 1
    if test_config_loading():
        tests_passed += 1

    # Test basic functionality
    total_tests += 1
    if test_basic_functionality():
        tests_passed += 1

    print(f"\n{'=' * 50}")
    print(f"Test Results: {tests_passed}/{total_tests} tests passed")

    if tests_passed == total_tests:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
