# Configuration Files Guide

This document explains the configuration files used in the PittQLabSys project and their purposes.

## Overview

The project uses modern Python configuration standards with `pyproject.toml` as the central configuration file, supplemented by specific configuration files for different tools.

## Configuration Files

### 1. `pyproject.toml` (Primary Configuration)

**Purpose**: Central configuration file for all Python tools and build system.

**What it configures**:
- **Build system**: Project metadata, dependencies, build requirements
- **Testing**: pytest configuration, markers, test discovery
- **Code quality**: flake8 (linting), mypy (type checking)
- **Documentation**: Sphinx settings
- **Coverage**: Coverage.py settings

**Key sections**:
```toml
[project]
name = "pittqlabsys"
version = "1.0.0"
# ... project metadata

[tool.pytest.ini_options]
# pytest configuration
minversion = "6.0"
addopts = "-ra -q --strict-markers --strict-config"
markers = [
    "hardware: marks tests that require hardware",
    "slow: marks tests as slow",
    # ... other markers
]

[tool.flake8]
# Code linting configuration
max-line-length = 88
extend-ignore = ["E203", "W503"]

[tool.mypy]
# Type checking configuration
python_version = "3.8"
disallow_untyped_defs = true
# ... other mypy settings

[tool.coverage.run]
# Coverage configuration
source = ["src"]
omit = ["*/tests/*", "*/venv/*"]

[tool.sphinx]
# Documentation configuration
project = "AQuISS"
extensions = ["sphinx.ext.autodoc", "sphinx_rtd_theme"]
```

### 2. `tests/conftest.py` (Test Configuration)

**Purpose**: Pytest configuration and shared test fixtures.

**What it contains**:
- **Matplotlib backend**: Sets non-interactive backend to prevent GUI windows
- **Shared fixtures**: Common test fixtures used across multiple test files
- **Test configuration**: Any pytest-specific setup

**Key content**:
```python
import matplotlib
matplotlib.use("Agg")  # non-interactive, no window pops up

# Shared fixtures can be added here
@pytest.fixture
def common_test_data():
    # ... fixture implementation
    pass
```

### 3. `requirements.txt` (Dependencies)

**Purpose**: Lists Python package dependencies for the project.

**Usage**:
```bash
pip install -r requirements.txt
```

### 4. `pytest.ini` (Legacy - Removed)

**Status**: ❌ **REMOVED** - Migrated to `pyproject.toml`

**Why removed**:
- `pyproject.toml` is the modern Python standard (PEP 518)
- Single configuration file for all tools
- Better integration with modern Python tooling
- More comprehensive configuration options

## Configuration Priority

When multiple configuration files exist, tools follow this priority order:

1. **`pyproject.toml`** (highest priority - modern standard)
2. **`pytest.ini`** (legacy, but still supported)
3. **`tox.ini`** (if pytest section exists)
4. **`setup.cfg`** (if pytest section exists)

## Migration from pytest.ini to pyproject.toml

### What was migrated:

**From `pytest.ini`:**
```ini
[pytest]
addopts = --strict-markers
markers =
    run_this: mark a test to be run
    slow: marks tests as slow
    integration: marks tests as integration tests
    hardware: marks tests that require hardware
    gui: marks tests that require GUI
filterwarnings =
    ignore:.*U.*mode is deprecated:DeprecationWarning
```

**To `pyproject.toml`:**
```toml
[tool.pytest.ini_options]
addopts = "-ra -q --strict-markers --strict-config"
markers = [
    "run_this: mark a test to be run",
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: marks tests as integration tests",
    "hardware: marks tests that require hardware",
    "gui: marks tests that require GUI",
]
filterwarnings = [
    "ignore:.*U.*mode is deprecated:DeprecationWarning",
]
```

## Benefits of pyproject.toml

### ✅ **Advantages:**
- **Single source of truth**: All configuration in one file
- **Modern standard**: PEP 518 compliant
- **Better tool integration**: Works seamlessly with modern Python tools
- **Comprehensive**: Can configure multiple tools in one place
- **Future-proof**: Industry standard moving forward

### 🔧 **Tools Configured:**
- **pytest**: Testing framework
- **coverage**: Code coverage measurement
- **flake8**: Code linting
- **mypy**: Type checking
- **sphinx**: Documentation generation
- **build**: Package building

## Usage Examples

### Running Tests
```bash
# Run all tests except hardware tests
pytest -m "not hardware"

# Run only hardware tests (when SG384 is connected)
pytest tests/test_sg384_hardware.py -m hardware -v

# Run with coverage
pytest --cov=src/Controller/sg384 tests/test_sg384.py
```

### Code Quality
```bash
# Linting
flake8 src/

# Type checking
mypy src/

# All quality checks
flake8 src/ && mypy src/
```

### Documentation
```bash
# Build documentation
sphinx-build -b html docs/ docs/_build/html
```

## Troubleshooting

### Configuration Not Working
1. **Check file location**: Ensure `pyproject.toml` is in the project root
2. **Verify syntax**: Use a TOML validator to check syntax
3. **Check tool version**: Ensure tools support `pyproject.toml` configuration

### Pytest Issues
1. **Markers not recognized**: Check `[tool.pytest.ini_options]` section
2. **Configuration ignored**: Ensure no `pytest.ini` file exists
3. **Import errors**: Check `testpaths` and `python_files` settings

### Coverage Issues
1. **No data collected**: Check `[tool.coverage.run]` source paths
2. **Wrong files included**: Verify `omit` patterns
3. **HTML not generated**: Check `[tool.coverage.report]` settings

## Best Practices

1. **Keep it centralized**: Use `pyproject.toml` for all tool configuration
2. **Document settings**: Add comments explaining non-obvious configurations
3. **Version control**: Include all configuration files in version control
4. **Test configuration**: Verify configuration works in CI/CD pipeline
5. **Keep it simple**: Avoid overly complex configuration patterns 