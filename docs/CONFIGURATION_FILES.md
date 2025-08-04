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

---

# AQuISS Configuration Files

## Overview

The AQuISS system uses a hierarchical configuration file structure to manage different aspects of the laboratory setup. This section explains the purpose and structure of each AQuISS-specific configuration file.

## Configuration File Hierarchy

### 1. `src/config.json` - Main Configuration File
**Location**: `src/config.json` (in project root)  
**Purpose**: Main configuration file with path overrides and default settings  
**Content**: Static configuration that defines the basic structure of the system

```json
{
    "gui_settings": {
        "data_folder": "",
        "probes_folder": "",
        "device_folder": "",
        "experiments_folder": "",
        "probes_log_folder": "",
        "gui_settings": ""
    },
    "gui_settings_hidden": {
        "experiments_source_folder": "",
        "experiment_source_folder": ""
    },
    "experiments_hidden_parameters": {},
    "devices": {},
    "experiments": {},
    "probes": {}
}
```

### 2. `src/View/gui_config.json` - GUI Settings
**Location**: `src/View/gui_config.json` (in project source)  
**Purpose**: GUI-specific settings and metadata  
**Content**: Simple GUI metadata like last save path

```json
{
    "last_save_path": "C:\\Users\\Duttlab\\Experiments\\AQuISS_default_save_location\\workspace_config.json"
}
```

### 3. `workspace_config.json` - Runtime Workspace Configuration
**Location**: `~/Experiments/AQuISS_default_save_location/workspace_config.json` (user data folder)  
**Purpose**: Complete workspace state including devices, experiments, probes, and GUI settings  
**Content**: Dynamic configuration created and modified during runtime

```json
{
    "gui_settings": {
        "data_folder": "/path/to/data",
        "probes_folder": "/path/to/probes",
        "device_folder": "/path/to/devices",
        "experiments_folder": "/path/to/experiments",
        "probes_log_folder": "/path/to/logs",
        "gui_settings": "/path/to/workspace_config.json"
    },
    "gui_settings_hidden": {
        "experiments_source_folder": "/path/to/source",
        "experiment_source_folder": "/path/to/experiment/source"
    },
    "experiments_hidden_parameters": {
        "NV_Locations": {
            "point": {"x": false, "y": false},
            "execution_time": false
        }
    },
    "devices": {
        "device_name": {
            "class": "DeviceClass",
            "filepath": "/path/to/device.py",
            "settings": {...}
        }
    },
    "experiments": {
        "experiment_name": {
            "class": "ExperimentClass",
            "filepath": "/path/to/experiment.py",
            "settings": {...}
        }
    },
    "probes": {
        "device_name": "probe1,probe2,probe3"
    }
}
```

## File Extension Evolution

### Historical Context
- **Original Mistake**: The system initially used `.aqs` extension for JSON files
- **Problem**: This caused confusion as `.aqs` files are actually JSON files
- **Solution**: Implemented hybrid approach with `.json` as default, `.aqs` for backward compatibility

### Current Approach
- **New files**: Saved as `.json` by default
- **Existing files**: Can still be loaded and saved as `.aqs` if needed
- **Backward compatibility**: Both formats are supported seamlessly

## How Configuration Files Are Used

### 1. System Startup
1. **Load main config**: `src/config.json` provides default paths and structure
2. **Resolve paths**: `config_paths.py` merges defaults with any overrides
3. **Load GUI config**: `src/View/gui_config.json` provides GUI-specific settings
4. **Load workspace**: If exists, `workspace_config.json` restores previous session state

### 2. Runtime Operations
- **Device loading**: Devices are loaded from `workspace_config.json`
- **Experiment loading**: Experiments are loaded from `workspace_config.json`
- **Probe configuration**: Probes are configured from `workspace_config.json`
- **GUI state**: GUI settings are maintained in `workspace_config.json`

### 3. Saving Configuration
- **Manual save**: User clicks "Save Workspace Configuration" button
- **Automatic save**: System may save configuration on exit
- **File format**: Defaults to `.json`, supports `.aqs` for backward compatibility

## Configuration File Creation

### `workspace_config.json` Creation
The `workspace_config.json` file is created when:

1. **User action**: Click "Save Workspace Configuration" in GUI
2. **Trigger**: `btn_save_gui.triggered.connect(self.btn_clicked)`
3. **Method**: `MainWindow.save_config(filepath)`
4. **Content**: Gathers complete workspace state:
   - Device states and settings
   - Experiment configurations
   - Probe definitions
   - GUI settings
   - Hidden parameters

### Code Flow
```python
# 1. User clicks "Save Workspace Configuration" button
btn_save_gui.triggered.connect(self.btn_clicked)

# 2. File dialog opens (supports both .json and .aqs)
filepath, _ = QtWidgets.QFileDialog.getSaveFileName(
    self, 'Save workspace configuration to file', 
    self.config_filepath, 
    filter='*.json;*.aqs'
)

# 3. save_config() method is called
self.save_config(filepath)

# 4. The method gathers all workspace state and saves it
def save_config(self, filepath):
    # Gathers device states, experiment states, probe states
    # Merges with existing config
    # Saves as atomic JSON file
```

## Path Resolution

### Default Paths
```python
HOME = Path.home()
DEFAULT_BASE = HOME / "Experiments" / "AQuISS_default_save_location"

_DEFAULTS = {
    "data_folder":        DEFAULT_BASE / "data",
    "probes_folder":      DEFAULT_BASE / "probes_auto_generated",
    "device_folder":      DEFAULT_BASE / "devices_auto_generated",
    "experiments_folder": DEFAULT_BASE / "experiments_auto_generated",
    "probes_log_folder":  DEFAULT_BASE / "aqs_tmp",
    "gui_settings":       DEFAULT_BASE / "workspace_config.json",
}
```

### Path Override
Users can override default paths by creating a custom `src/config.json` with path overrides:

```json
{
    "paths": {
        "data_folder": "/custom/data/path",
        "experiments_folder": "/custom/experiments/path"
    }
}
```

## File Format Support

### JSON Format (Primary)
- **Extension**: `.json`
- **Format**: Standard JSON
- **Usage**: Default format for new files
- **Advantages**: Standard, widely supported, human-readable

### AQS Format (Legacy)
- **Extension**: `.aqs`
- **Format**: JSON with `.aqs` extension
- **Usage**: Backward compatibility for existing files
- **Support**: Can be loaded and saved, but new files default to `.json`

### Loading Logic
```python
def load_aqs_file(file_name):
    """
    Loads a .aqs or .json file into a dictionary
    Supports both JSON and YAML formats for backward compatibility
    """
    with open(file_name, 'r') as infile:
        content = infile.read().strip()
        
    # Try JSON first (new format)
    try:
        import json
        return json.loads(content)
    except json.JSONDecodeError:
        # Fall back to YAML (old format)
        try:
            import yaml
            return yaml.safe_load(content)
        except Exception as e:
            raise ValueError(f"File {file_name} is neither valid JSON nor YAML: {e}")
```

## AQuISS Configuration Best Practices

### 1. File Naming
- Use `.json` extension for new files
- Keep `.aqs` extension only for existing files that need backward compatibility
- Use descriptive names that indicate the content (e.g., `workspace_config.json`)

### 2. Configuration Management
- **Main config**: Keep `src/config.json` simple with only essential overrides
- **GUI config**: Use `src/View/gui_config.json` for GUI-specific settings only
- **Workspace config**: Let `workspace_config.json` handle runtime state

### 3. Version Control
- **Include**: `src/config.json`, `src/View/gui_config.json`
- **Exclude**: `workspace_config.json` (runtime-generated)
- **Reason**: Workspace config contains user-specific paths and runtime state

### 4. Migration
- **Existing `.aqs` files**: Can continue to be used
- **New files**: Should use `.json` extension
- **Gradual transition**: No need to convert existing files immediately

## AQuISS Configuration Troubleshooting

### Common Issues

1. **File not found errors**
   - Check that `src/config.json` exists and is valid JSON
   - Verify that user has write permissions to the data folder

2. **Configuration not loading**
   - Ensure `workspace_config.json` is valid JSON
   - Check that all referenced device/experiment files exist

3. **Path resolution issues**
   - Verify that `src/config.json` has correct path overrides
   - Check that the user's home directory is accessible

### Debugging
- Enable debug logging to see which configuration files are being loaded
- Check the startup message for resolved paths
- Verify file permissions and existence

## Summary

The AQuISS configuration system provides a flexible, hierarchical approach to managing laboratory settings:

- **Static configuration**: `src/config.json` for project defaults
- **GUI settings**: `src/View/gui_config.json` for interface preferences  
- **Runtime state**: `workspace_config.json` for complete workspace state
- **Format support**: Both `.json` (primary) and `.aqs` (legacy) formats
- **Backward compatibility**: Existing `.aqs` files continue to work

This structure ensures that the system can be easily configured for different laboratory setups while maintaining compatibility with existing configurations. 