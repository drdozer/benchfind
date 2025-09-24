# Development Guide

## Overview

This guide provides comprehensive information for developers who want to extend, modify, or contribute to the Benchfind orchestration system. It covers common development tasks, architectural patterns, and best practices.

## Development Environment Setup

### Prerequisites

1. **Python 3.11+** with virtual environment support
2. **Rust nightly toolchain** for benchmark execution
3. **Git** for version control and metadata collection

### Initial Setup

```bash
# Clone and setup the project
cd benchfind/orchestration
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Install in development mode
pip install -e ".[dev,analysis]"

# Verify installation
benchfind --help
```

### Development Dependencies

```bash
# Code quality tools
pip install black isort mypy pytest pytest-cov

# Optional analysis tools  
pip install pandas numpy matplotlib jupyter
```

## Project Structure

```
orchestration/
├── src/benchfind/           # Core library modules
│   ├── __init__.py         # Package initialization
│   ├── cli.py              # Command-line interface (Click-based)
│   ├── config.py           # YAML configuration management
│   ├── storage.py          # Results storage and indexing
│   ├── metadata.py         # System/build metadata collection
│   ├── benchmark.py        # Benchmark execution orchestration
│   ├── assembly.py         # Assembly analysis and SIMD detection
│   └── utils.py            # Shared utilities and helpers
├── config/                 # YAML configuration files
│   ├── targets.yaml        # Compilation target definitions
│   ├── execution.yaml      # Benchmark execution parameters
│   ├── storage.yaml        # Results storage configuration
│   ├── benchmarks.yaml     # Benchmark suite definitions
│   └── instructions.yaml   # SIMD instruction patterns
├── scripts/                # High-level orchestration scripts
└── tests/                  # Test suite
```

## Common Development Tasks

### Adding a New Compilation Target

1. **Define the target in `config/targets.yaml`:**

```yaml
targets:
  my-new-target:
    rustflags: "-C target-cpu=native -C target-feature=+my-feature"
    description: "Description of what this target tests"
    cpu_features:
      - "my-feature"
      - "prerequisite-feature"
    expected_on_modern_cpu: true
    expected_simd_instructions:
      - "new_instruction_pattern"
      - "related_pattern"
    performance_expectation: "high"
```

2. **Add to target groups (optional):**

```yaml
target_groups:
  my_group:
    - default
    - native  
    - my-new-target
```

3. **Test the target:**

```bash
benchfind config targets  # Verify target appears
benchfind quick --targets my-new-target  # Test execution
```

### Adding New SIMD Instruction Patterns

1. **Update `config/instructions.yaml`:**

```yaml
simd_patterns:
  avx512_new:
    - "vnew512.*"
    - "vmypattern.*"
  
instruction_categories:
  AVX512_NEW:
    patterns:
      - avx512_new
    description: "New AVX-512 instruction family"
```

2. **The assembly analyzer will automatically detect these patterns**

### Extending the CLI Interface

#### Adding a New Command

```python
# In src/benchfind/cli.py

@main.command()
@click.option('--my-option', help='Description of option')
@pass_context
def my_command(ctx: CliContext, my_option: Optional[str]):
    """Description of what this command does"""
    ctx.ensure_initialized()
    
    # Command implementation
    console.print("Executing my command...")
    
    # Use existing modules
    targets = ctx.config.get_all_targets()
    # ... implementation logic
```

#### Adding a New Subcommand Group

```python
@main.group()
def my_group():
    """Description of command group"""
    pass

@my_group.command()
@pass_context  
def sub_command(ctx: CliContext):
    """Subcommand implementation"""
    # Implementation
```

### Extending Metadata Collection

#### Adding New System Information

```python
# In src/benchfind/metadata.py

class SystemInfo(BaseModel):
    # Existing fields...
    my_new_field: Optional[str] = None

class MetadataCollector:
    def collect_system_info(self) -> SystemInfo:
        # Existing collection logic...
        
        # Add new information
        my_data = self._collect_my_data()
        
        return SystemInfo(
            # Existing fields...
            my_new_field=my_data
        )
    
    def _collect_my_data(self) -> Optional[str]:
        """Collect new type of system information"""
        try:
            # Implementation to gather data
            return collected_data
        except Exception as e:
            logger.warning(f"Could not collect my_data: {e}")
            return None
```

#### Adding New Metadata Types

```python
class MyMetadata(BaseModel):
    """New category of metadata"""
    field1: str
    field2: Optional[int] = None
    collection_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ComprehensiveMetadata(BaseModel):
    # Existing fields...
    my_metadata: MyMetadata
```

### Adding New Analysis Capabilities

#### Extending Assembly Analysis

```python
# In src/benchfind/assembly.py

class AssemblyAnalyzer:
    def analyze_my_pattern(self, assembly_content: str) -> Dict[str, Any]:
        """Analyze assembly for new pattern type"""
        
        patterns = self.config.get('my_patterns', [])
        results = {
            'pattern_detected': False,
            'occurrences': 0,
            'locations': []
        }
        
        for line_num, line in enumerate(assembly_content.split('\n')):
            for pattern in patterns:
                if re.search(pattern, line):
                    results['pattern_detected'] = True
                    results['occurrences'] += 1
                    results['locations'].append(line_num)
        
        return results
```

### Extending Configuration System

#### Adding New Configuration Files

1. **Create new YAML file in `config/`:**

```yaml
# config/my_config.yaml
my_settings:
  param1: "value1"
  param2: 42
  param_list:
    - "item1"
    - "item2"

categories:
  category1:
    setting: "value"
```

2. **Add loader method to `config.py`:**

```python
class ConfigurationLoader:
    def load_my_config(self) -> Dict[str, Any]:
        """Load my configuration settings"""
        return self._load_yaml_file("my_config.yaml")
```

3. **Use in other modules:**

```python
config_loader = ConfigurationLoader()
my_settings = config_loader.load_my_config()
param1 = my_settings['my_settings']['param1']
```

### Custom Storage Extensions

#### Adding New Result Types

```python
# In src/benchfind/storage.py

class MyResultType(BaseModel):
    """New type of analysis result"""
    analysis_name: str
    results: Dict[str, Any]
    timestamp: datetime
    
class StorageLayout:
    def get_my_results_dir(self) -> Path:
        """Get directory for my custom results"""
        my_dir = self.run_dir / "my_analysis"
        my_dir.mkdir(parents=True, exist_ok=True)
        return my_dir

class ResultsStorage:
    def store_my_results(self, layout: StorageLayout, results: MyResultType) -> None:
        """Store custom analysis results"""
        results_file = layout.get_my_results_dir() / "analysis.json"
        with open(results_file, 'w') as f:
            json.dump(results.dict(), f, indent=2, default=str)
```

## Testing

### Writing Unit Tests

```python
# In tests/test_my_module.py

import pytest
from benchfind.my_module import MyClass

class TestMyClass:
    def test_basic_functionality(self):
        """Test basic functionality of my class"""
        instance = MyClass()
        result = instance.my_method("test_input")
        assert result == expected_output
    
    def test_error_handling(self):
        """Test error handling"""
        instance = MyClass()
        with pytest.raises(ValueError):
            instance.my_method(invalid_input)
    
    @pytest.fixture
    def sample_data(self):
        """Provide test data"""
        return {"key": "value"}
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=benchfind

# Run specific test file
pytest tests/test_my_module.py

# Run tests matching pattern
pytest -k "test_my_pattern"
```

### Integration Testing

```python
# Test CLI commands end-to-end
def test_cli_integration(tmp_path, monkeypatch):
    """Test CLI command integration"""
    monkeypatch.chdir(tmp_path)
    
    # Setup test environment
    create_test_project(tmp_path)
    
    # Test CLI command
    runner = CliRunner()
    result = runner.invoke(cli, ['my-command', '--option', 'value'])
    
    assert result.exit_code == 0
    assert "expected output" in result.output
```

## Code Style and Quality

### Formatting and Linting

```bash
# Format code
black src/ scripts/ tests/
isort src/ scripts/ tests/

# Type checking  
mypy src/

# Linting
flake8 src/ scripts/ tests/
```

### Code Style Guidelines

1. **Use type hints** for all function parameters and return values
2. **Follow PEP 8** naming conventions
3. **Write docstrings** for public functions and classes  
4. **Use Pydantic models** for structured data
5. **Handle errors gracefully** with informative messages
6. **Use logging** instead of print statements

### Example Code Style

```python
from typing import Optional, List, Dict, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class MyClass:
    """
    Description of what this class does.
    
    Args:
        param1: Description of parameter
        param2: Optional parameter description
    """
    
    def __init__(self, param1: str, param2: Optional[int] = None):
        self.param1 = param1
        self.param2 = param2 or 0
    
    def process_data(self, data: List[Dict[str, Any]]) -> Optional[str]:
        """
        Process input data and return result.
        
        Args:
            data: List of data dictionaries to process
            
        Returns:
            Processed result or None if processing failed
            
        Raises:
            ValueError: If data is invalid
        """
        try:
            # Implementation logic
            result = self._internal_processing(data)
            logger.info(f"Processed {len(data)} items successfully")
            return result
        except Exception as e:
            logger.error(f"Processing failed: {e}")
            return None
    
    def _internal_processing(self, data: List[Dict[str, Any]]) -> str:
        """Internal processing logic (private method)"""
        # Implementation
        pass
```

## Configuration Best Practices

### YAML Configuration Design

1. **Use descriptive keys** that clearly indicate purpose
2. **Provide default values** for optional settings
3. **Group related settings** under common parent keys
4. **Include comments** explaining complex configurations
5. **Use consistent naming** conventions across files

```yaml
# Good configuration example
benchmark_execution:
  # Time spent measuring each benchmark (seconds)
  measurement_time_seconds: 15
  
  # Warm-up period before measurements (seconds)
  warm_up_time_seconds: 3
  
  # Timeout for individual benchmark runs
  timeout_seconds: 1800
  
  # Sample sizes for different benchmark types
  sample_sizes:
    default: 100
    long_running: 50
    quick: 200
```

### Configuration Validation

```python
class MyConfigModel(BaseModel):
    """Pydantic model for configuration validation"""
    
    required_field: str
    optional_field: Optional[int] = 42
    list_field: List[str] = Field(default_factory=list)
    
    @validator('required_field')
    def validate_required_field(cls, v):
        if not v or not v.strip():
            raise ValueError('required_field cannot be empty')
        return v.strip()
    
    @root_validator
    def validate_configuration(cls, values):
        # Cross-field validation
        if values.get('optional_field', 0) < 0:
            raise ValueError('optional_field must be non-negative')
        return values
```

## Error Handling Patterns

### Graceful Error Handling

```python
def robust_operation(input_data: str) -> Optional[str]:
    """Example of robust error handling"""
    try:
        # Main operation logic
        result = risky_operation(input_data)
        return result
    except SpecificError as e:
        # Handle specific expected errors
        logger.warning(f"Expected error occurred: {e}")
        return None
    except Exception as e:
        # Handle unexpected errors
        logger.error(f"Unexpected error in robust_operation: {e}")
        return None
```

### User-Friendly CLI Error Messages

```python
@click.command()
def my_command():
    try:
        # Command logic
        pass
    except FileNotFoundError:
        click.echo("Error: Required file not found. Please check your project setup.")
        sys.exit(1)
    except ValueError as e:
        click.echo(f"Error: Invalid input - {e}")
        sys.exit(1) 
    except Exception as e:
        click.echo(f"Unexpected error: {e}")
        click.echo("Please report this issue with the full error message.")
        sys.exit(1)
```

## Performance Considerations

### Memory Usage

1. **Use generators** for large data processing
2. **Stream file processing** instead of loading entire files
3. **Clean up resources** explicitly when needed

```python
def process_large_file(file_path: Path) -> Generator[str, None, None]:
    """Process large file without loading it entirely into memory"""
    with open(file_path, 'r') as f:
        for line in f:
            yield process_line(line)
```

### Subprocess Management

```python
def run_cargo_command(args: List[str], timeout: int = 300) -> subprocess.CompletedProcess:
    """Run cargo command with proper resource management"""
    try:
        result = subprocess.run(
            ['cargo'] + args,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=True
        )
        return result
    except subprocess.TimeoutExpired:
        logger.error(f"Command timed out after {timeout} seconds")
        raise
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with exit code {e.returncode}: {e.stderr}")
        raise
```

## Debugging and Troubleshooting

### Logging Configuration

```python
import logging
import sys

def setup_logging(verbose: bool = False) -> None:
    """Configure logging for the application"""
    level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('benchfind.log')
        ]
    )
```

### Debug Mode Support

```python
class DebugContext:
    """Context manager for debug operations"""
    
    def __init__(self, enabled: bool = False):
        self.enabled = enabled
    
    def __enter__(self):
        if self.enabled:
            logger.setLevel(logging.DEBUG)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.enabled and exc_type:
            logger.debug(f"Exception in debug context: {exc_val}")
```

## Release and Deployment

### Version Management

1. **Update version** in `pyproject.toml`
2. **Update CHANGELOG.md** with new features and fixes
3. **Tag release** in Git
4. **Update documentation** to reflect changes

### Dependency Management

```bash
# Update requirements
pip-compile requirements.in
pip-compile dev-requirements.in

# Check for security issues
pip-audit

# Update all dependencies (carefully)
pip-compile --upgrade requirements.in
```

## Contributing Guidelines

### Pull Request Process

1. **Create feature branch** from main
2. **Implement changes** with tests
3. **Run full test suite** and linting
4. **Update documentation** if needed
5. **Submit PR** with clear description

### Commit Message Format

```
type(scope): brief description

Longer description if needed, explaining the why and what changed.

Fixes #issue-number
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

## Future Architecture Considerations

### Scalability Improvements

- **Parallel benchmark execution** across multiple machines
- **Result aggregation** from distributed runs
- **Database storage** for large-scale result management

### Integration Opportunities

- **CI/CD integration** for automated benchmarking
- **Performance regression detection** in development workflows
- **Web interface** for result visualization and comparison

This development guide provides the foundation for extending and maintaining the Benchfind orchestration system. For specific implementation questions, refer to the existing codebase and architecture documentation.