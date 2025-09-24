"""
Tests for the storage module.

This module tests the core functionality of the results storage system,
including run identification, storage layout, and basic operations.
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from benchfind.config import Config, ConfigurationLoader
from benchfind.storage import RunIdentifier, StorageLayout, RunIndex, ResultsStorage
from benchfind.metadata import SystemInfo, BuildInfo, ExecutionContext


class TestRunIdentifier(unittest.TestCase):
    """Test run identification and naming logic"""

    def test_sanitize_hostname(self):
        """Test hostname sanitization"""
        test_cases = [
            ("my-computer.local", "my_computer_local"),
            ("SERVER-01", "server_01"),
            ("test@host", "test_host"),
            ("very-long-hostname-that-exceeds-limits", "very_long_hostname_t"),  # Truncated
        ]

        for input_hostname, expected in test_cases:
            with self.subTest(hostname=input_hostname):
                result = RunIdentifier._sanitize_hostname(input_hostname)
                self.assertEqual(result, expected)

    @patch('subprocess.run')
    def test_get_rustc_version(self, mock_run):
        """Test Rust compiler version extraction"""
        # Mock successful rustc --version output
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "rustc 1.75.0-nightly (hash 2023-12-01)"
        mock_run.return_value = mock_result

        version = RunIdentifier._get_rustc_version()
        self.assertEqual(version, "1_75_0_nightly")

    @patch('subprocess.run')
    def test_get_rustc_version_fallback(self, mock_run):
        """Test fallback when rustc is not available"""
        mock_run.side_effect = FileNotFoundError()

        version = RunIdentifier._get_rustc_version()
        self.assertEqual(version, "unknown")

    def test_calculate_source_hash(self):
        """Test source file hash calculation"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)

            # Create mock source files
            (project_root / "src").mkdir()
            (project_root / "src" / "lib.rs").write_text("fn main() {}")

            (project_root / "benches").mkdir()
            (project_root / "benches" / "bench_newlines.rs").write_text("// benchmark")
            (project_root / "benches" / "bench_csv.rs").write_text("// csv benchmark")

            (project_root / "Cargo.toml").write_text("[package]\nname = 'test'")

            # Mock config
            config = MagicMock()

            # Calculate hash
            source_hash = RunIdentifier._calculate_source_hash(config, project_root)

            # Should be 8 characters
            self.assertEqual(len(source_hash), 8)
            self.assertTrue(all(c in '0123456789abcdef' for c in source_hash))

    def test_run_id_property(self):
        """Test run ID construction"""
        run_id = RunIdentifier("testhost", "abc12345", "1_75_0")
        self.assertEqual(run_id.run_id, "testhost_abc12345_1_75_0")


class TestStorageLayout(unittest.TestCase):
    """Test storage directory layout"""

    def test_from_run_id(self):
        """Test storage layout creation from run ID"""
        config = MagicMock()
        run_id = "testhost_abc12345_1_75_0"

        layout = StorageLayout.from_run_id(config, run_id)

        # Check that all paths are properly constructed
        self.assertEqual(layout.run_dir.name, run_id)
        self.assertEqual(layout.metadata_dir.name, "metadata")
        self.assertEqual(layout.raw_results_dir.name, "raw-results")
        self.assertEqual(layout.assembly_extracts_dir.name, "assembly_extracts")
        self.assertEqual(layout.logs_dir.name, "logs")

    def test_ensure_directories(self):
        """Test directory creation"""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir) / "test_run"

            layout = StorageLayout(
                run_dir=base_path,
                metadata_dir=base_path / "metadata",
                raw_results_dir=base_path / "raw-results",
                assembly_extracts_dir=base_path / "assembly_extracts",
                logs_dir=base_path / "logs"
            )

            # Ensure directories
            layout.ensure_directories()

            # Check all directories were created
            self.assertTrue(layout.run_dir.exists())
            self.assertTrue(layout.metadata_dir.exists())
            self.assertTrue(layout.raw_results_dir.exists())
            self.assertTrue(layout.assembly_extracts_dir.exists())
            self.assertTrue(layout.logs_dir.exists())

    def test_helper_methods(self):
        """Test path helper methods"""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir) / "test_run"

            layout = StorageLayout(
                run_dir=base_path,
                metadata_dir=base_path / "metadata",
                raw_results_dir=base_path / "raw-results",
                assembly_extracts_dir=base_path / "assembly_extracts",
                logs_dir=base_path / "logs"
            )

            # Test metadata file path
            metadata_file = layout.get_metadata_file("system-info.json")
            self.assertEqual(metadata_file, base_path / "metadata" / "system-info.json")

            # Test target assembly directory
            target_dir = layout.get_target_assembly_dir("native-avx2")
            self.assertEqual(target_dir, base_path / "assembly_extracts" / "native-avx2")

            # Test log file path
            log_file = layout.get_log_file("benchmark.log")
            self.assertEqual(log_file, base_path / "logs" / "benchmark.log")


class TestRunIndex(unittest.TestCase):
    """Test run indexing functionality"""

    def test_empty_index(self):
        """Test creating empty index"""
        index = RunIndex()
        self.assertEqual(len(index.runs), 0)
        self.assertEqual(index.schema_version, "1.0.0")

    def test_add_run(self):
        """Test adding runs to index"""
        index = RunIndex()

        index.add_run("test_run_1", "host1", "abc123", "1_75_0", "completed", ["target1"], ["bench1"])

        self.assertEqual(len(index.runs), 1)
        run = index.runs[0]
        self.assertEqual(run['run_id'], "test_run_1")
        self.assertEqual(run['hostname'], "host1")
        self.assertEqual(run['status'], "completed")

    def test_find_runs(self):
        """Test run search functionality"""
        index = RunIndex()

        # Add multiple runs
        index.add_run("run1", "host1", "abc123", "1_75_0", "completed")
        index.add_run("run2", "host2", "def456", "1_75_0", "failed")
        index.add_run("run3", "host1", "abc123", "1_76_0", "completed")

        # Test filtering by hostname
        host1_runs = index.find_runs(hostname="host1")
        self.assertEqual(len(host1_runs), 2)

        # Test filtering by status
        completed_runs = index.find_runs(status="completed")
        self.assertEqual(len(completed_runs), 2)

        # Test filtering by multiple criteria
        specific_runs = index.find_runs(hostname="host1", status="completed")
        self.assertEqual(len(specific_runs), 2)

    def test_update_existing_run(self):
        """Test updating an existing run"""
        index = RunIndex()

        # Add initial run
        index.add_run("test_run", "host1", "abc123", "1_75_0", "in_progress")
        self.assertEqual(len(index.runs), 1)
        self.assertEqual(index.runs[0]['status'], "in_progress")

        # Update the same run
        index.add_run("test_run", "host1", "abc123", "1_75_0", "completed", ["target1"])
        self.assertEqual(len(index.runs), 1)  # Should still be just one run
        self.assertEqual(index.runs[0]['status'], "completed")
        self.assertEqual(index.runs[0]['targets_completed'], ["target1"])

    def test_save_and_load(self):
        """Test index persistence"""
        with tempfile.TemporaryDirectory() as temp_dir:
            index_path = Path(temp_dir) / "index.json"

            # Create and populate index
            index = RunIndex()
            index.add_run("test_run", "host1", "abc123", "1_75_0", "completed")

            # Save index
            index.save(index_path)
            self.assertTrue(index_path.exists())

            # Load index
            loaded_index = RunIndex.load(index_path)
            self.assertEqual(len(loaded_index.runs), 1)
            self.assertEqual(loaded_index.runs[0]['run_id'], "test_run")

    def test_load_missing_index(self):
        """Test loading non-existent index"""
        with tempfile.TemporaryDirectory() as temp_dir:
            index_path = Path(temp_dir) / "missing.json"

            # Should create empty index
            index = RunIndex.load(index_path)
            self.assertEqual(len(index.runs), 0)


class TestResultsStorage(unittest.TestCase):
    """Test high-level storage operations"""

    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.project_root = Path(self.temp_dir)

        # Create mock project structure
        (self.project_root / "src").mkdir()
        (self.project_root / "src" / "lib.rs").write_text("fn main() {}")
        (self.project_root / "benches").mkdir()
        (self.project_root / "benches" / "bench_newlines.rs").write_text("// benchmark")
        (self.project_root / "benches" / "bench_csv.rs").write_text("// csv benchmark")
        (self.project_root / "Cargo.toml").write_text("[package]\nname = 'test'")

    def tearDown(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_init_storage(self):
        """Test storage initialization"""
        config = MagicMock()

        with patch.object(ConfigurationLoader, 'load_storage_config') as mock_load:
            mock_load.return_value = {
                'paths': {
                    'results_base': 'results',
                    'runs_dir': 'results/runs',
                    'index_file': 'results/index.json'
                }
            }

            storage = ResultsStorage(config, self.project_root)

            # Check that directories are created
            self.assertTrue(storage.results_base.exists())
            self.assertTrue(storage.runs_dir.exists())

    def test_get_storage_statistics(self):
        """Test storage statistics calculation"""
        config = MagicMock()

        with patch.object(ConfigurationLoader, 'load_storage_config') as mock_load:
            mock_load.return_value = {
                'paths': {
                    'results_base': f'{self.temp_dir}/results',
                    'runs_dir': f'{self.temp_dir}/results/runs',
                    'index_file': f'{self.temp_dir}/results/index.json'
                }
            }

            storage = ResultsStorage(config, self.project_root)

            # Add some test runs to index
            storage.index.add_run("run1", "host1", "abc123", "1_75_0", "completed")
            storage.index.add_run("run2", "host2", "def456", "1_75_0", "failed")

            stats = storage.get_storage_statistics()

            self.assertEqual(stats['total_runs'], 2)
            self.assertEqual(stats['completed_runs'], 1)
            self.assertEqual(stats['failed_runs'], 1)
            self.assertEqual(stats['in_progress_runs'], 0)


class TestConfigIntegration(unittest.TestCase):
    """Test integration with configuration system"""

    def test_load_storage_config(self):
        """Test that storage configuration can be loaded"""
        # This tests that our storage.yaml is valid
        loader = ConfigurationLoader()

        try:
            config = loader.load_storage_config()

            # Check that key sections exist
            self.assertIn('paths', config)
            self.assertIn('run_identification', config)
            self.assertIn('caching', config)
            self.assertIn('data_extraction', config)

            # Check that paths are defined
            paths = config['paths']
            self.assertIn('results_base', paths)
            self.assertIn('runs_dir', paths)
            self.assertIn('index_file', paths)

        except FileNotFoundError:
            self.fail("storage.yaml configuration file not found")
        except Exception as e:
            self.fail(f"Failed to load storage configuration: {e}")


if __name__ == '__main__':
    unittest.main()
