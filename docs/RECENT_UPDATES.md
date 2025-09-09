# Recent Updates and Bug Fixes

This document tracks recent updates, bug fixes, and improvements to the AQuISS system.

## Version 1.1.0 - Lab PC Compatibility and Path Configuration

### 🐛 Bug Fixes

#### 1. Module Import Errors
- **Fixed**: `ModuleNotFoundError: No module named 'sequence'` during experiment export
- **Cause**: Incorrect relative imports in `src/Model/channels.py`
- **Solution**: Updated imports to use relative paths (`from .sequence import Sequence`)

#### 2. SG384 Device Configuration
- **Fixed**: `KeyError: 'connection_timeout'` in GUI device tree widget
- **Cause**: SG384 device class was missing inherited parameters from base class
- **Solution**: Implemented proper parameter inheritance pattern using `_get_base_settings()`

#### 3. Experiment Loading Errors
- **Fixed**: `ModuleNotFoundError: The path in the .aq file to this package is not valid`
- **Cause**: Windows-style backslashes in saved JSON files not handled properly
- **Solution**: Enhanced `module_name_from_path()` with proper path normalization

#### 4. Hardcoded Path Issues
- **Fixed**: Experiments using hardcoded C: drive paths instead of configured D: drive
- **Cause**: Experiments used `Path.home()` instead of configured data folder
- **Solution**: Created helper functions and updated 4 experiments to use configurable paths

### ✨ New Features

#### 1. Configurable Data Paths
- **Added**: `get_configured_data_folder()` and `get_configured_confocal_scans_folder()` helper functions
- **Benefit**: Experiments now respect lab-specific data folder configuration
- **Usage**: Automatically used by confocal scan experiments for 3D scan folder paths

#### 2. Device Parameter Inheritance
- **Added**: `_get_base_settings()` helper method to Device base class
- **Benefit**: Prevents parameter inheritance issues in device subclasses
- **Usage**: Recommended pattern for all device subclasses

#### 3. Git Configuration Management
- **Fixed**: `src/config.json` was being tracked by git (should be user-specific)
- **Solution**: Removed from git tracking, added to `.gitignore`
- **Benefit**: Lab PCs can now pull changes without config conflicts

### 🔧 Technical Improvements

#### 1. Enhanced Path Normalization
```python
# Before: Failed with Windows backslashes
module_name_from_path("src\\Model\\experiments\\odmr_pulsed.py")

# After: Handles both Unix and Windows paths
module_name_from_path("src\\Model\\experiments\\odmr_pulsed.py")  # ✅ Works
module_name_from_path("src/Model/experiments/odmr_pulsed.py")     # ✅ Works
```

#### 2. Parameter Inheritance Pattern
```python
# Before: Manual parameter copying (error-prone)
class SG384Generator(MicrowaveGeneratorBase):
    _DEFAULT_SETTINGS = Parameter([
        Parameter('connection_type', 'LAN', ['LAN','GPIB','RS232'], 'Transport type'),
        Parameter('ip_address', '192.168.2.217', str, 'IP for LAN'),
        # ... manually copied all base parameters
    ])

# After: Automatic inheritance (robust)
class SG384Generator(MicrowaveGeneratorBase):
    _DEFAULT_SETTINGS = Parameter(
        MicrowaveGeneratorBase._get_base_settings() + [
        Parameter('ip_address', '192.168.2.217', str, 'IP for LAN'),  # Override
        # ... only device-specific parameters
    ])
```

#### 3. Configurable Path System
```python
# Before: Hardcoded paths
Parameter('folderpath', str(Path.home() / 'Experiments' / 'AQuISS_default_save_location' / 'confocal_scans'), str, 'folder location')

# After: Configurable paths
Parameter('folderpath', str(get_configured_confocal_scans_folder()), str, 'folder location')
```

#### 4. Enhanced Base Experiment Class
```python
# Before: Manual path management in each experiment
self.output_dir = Path("odmr_pulsed_output")
self.output_dir.mkdir(exist_ok=True)

# After: Automatic path management via base class
self.output_dir = self.get_output_dir("odmr_pulsed_output")  # Uses configured data folder
```

**New Methods Added:**
- `get_output_dir(subfolder=None)` - Creates configurable output directories
- `get_config_path(config_name="config.json")` - Finds config files with fallback logic

**Key Features:**
- **Automatic**: All experiments get configurable paths by default
- **Safe**: Handles special characters, empty names, and filesystem issues
- **Flexible**: Can still customize per experiment if needed
- **Consistent**: Same path structure across all experiments

**Comprehensive Testing:**
- **26 tests** covering all functionality and edge cases
- **Path management** tests with mocking and real filesystem
- **Error handling** tests for invalid inputs
- **Integration tests** for real-world scenarios
- **All tests passing** ✅

### 📋 Updated Experiments

The following experiments now use configurable data paths:
- `NanodriveAdwinConfocalScanFast`
- `NanodriveAdwinConfocalScanSlow` 
- `ConfocalScan_Fast` (in confocal.py)
- `ConfocalScan_Slow` (in confocal.py)

### 🧪 Testing

#### New Test Coverage
- **Device Inheritance Tests**: `tests/test_device_inheritance.py` (13 tests)
- **Path Helper Tests**: `tests/test_helper_functions_paths.py` (5 tests)
- **All tests passing**: ✅ 18/18 tests pass

#### Test Categories
- Parameter inheritance validation
- Path configuration functionality
- Backward compatibility verification
- Edge case handling

### 📚 Documentation Updates

#### Updated Files
- `docs/DEVICE_DEVELOPMENT.md` - Added parameter inheritance patterns
- `docs/DEVICE_CONFIGURATION.md` - Added path configuration section
- `docs/README_SG384.md` - Added recent updates and configuration info

#### New Documentation
- `docs/RECENT_UPDATES.md` - This file, tracking all recent changes

### 🚀 Migration Guide

#### For Lab PCs
1. **Pull latest changes**: `git pull origin dutt-features`
2. **Update config**: Ensure `config.json` has `paths` section (see `config.sample.json`)
3. **Test experiments**: Verify 3D scan folder paths show D: drive instead of C: drive

#### For Developers
1. **Use inheritance pattern**: For new device classes, use `BaseClass._get_base_settings() + [...]`
2. **Use path helpers**: For experiments, use `get_configured_data_folder()` instead of hardcoded paths
3. **Run tests**: Ensure `pytest tests/test_device_inheritance.py` passes

### 🔍 Troubleshooting

#### Common Issues
1. **KeyError in GUI**: Ensure device classes use proper inheritance pattern
2. **Wrong data paths**: Check `config.json` has correct `paths` section
3. **Import errors**: Verify relative imports are used in Model classes
4. **Git conflicts**: `src/config.json` should not be tracked by git

#### Verification Commands
```bash
# Check inheritance works
python -c "from src.Controller.sg384 import SG384Generator; print('connection_timeout' in SG384Generator._DEFAULT_SETTINGS.keys())"

# Check path helpers work
python -c "from src.core.helper_functions import get_configured_data_folder; print(get_configured_data_folder())"

# Run tests
pytest tests/test_device_inheritance.py tests/test_helper_functions_paths.py -v
```

## Parameter List Concatenation Pattern Documentation

**Issue**: The powerful Parameter list concatenation pattern was not well documented, leading to confusion about its behavior and historical context.

**Solution**: Added comprehensive documentation to `DEVICE_DEVELOPMENT.md` explaining:
- How the pattern works (flattening behavior)
- Why it's powerful (composability, maintainability)
- Historical context (original 2020 implementation, 3-phase improvements)
- Internal mechanics and examples

**Key insight**: The `Parameter` class constructor flattens lists of `Parameter` objects into a single `Parameter` object, making it perfect for device parameter inheritance patterns like:

```python
_DEFAULT_SETTINGS = Parameter(
    MicrowaveGeneratorBase._get_base_settings() + [
        # Device-specific parameters...
    ]
)
```

This pattern was always supported but had issues that were fixed through the 3-phase Parameter class improvements documented in `PARAMETER_CLASS_SUMMARY.md` and `PARAMETER_CLASS_ANALYSIS.md`.

---

*Last updated: September 2025*
