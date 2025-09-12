# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] - 2025-01-11

### Added
- **Mock Data Generation System**: Complete mock data generation for GUI testing without hardware
  - `src/tools/generate_mock_data.py`: Mock data generators for ODMR and confocal experiments
  - `examples/mock_data_experiment.py`: Loadable experiment for generating mock data
  - `examples/test_gui_with_mock_data.py`: GUI testing utilities
- **Enhanced Parameter Validation**: Improved nested parameter validation in `src/core/parameter.py`
- **Experiment Iterator Fixes**: Fixed `TypeError` issues in `src/core/experiment_iterator.py`
- **Path Resolution Fixes**: Fixed import-time path evaluation issues in confocal experiments

### Changed
- **ODMR Sweep Continuous**: Updated parameter structure to use `step_freq` instead of `sweep_rate`
- **Logging System**: Standardized logging across experiments using `self.log()` instead of `self.logger`
- **GUI Dataset Functionality**: Fixed "send to Datasets" button functionality

### Fixed
- **Critical Bug**: `TypeError: __init__() got an unexpected keyword argument 'devices'` in experiment iterators
- **Critical Bug**: `AssertionError` in parameter validation for nested parameters
- **Path Bug**: Confocal experiments creating data directories in wrong location
- **GUI Bug**: Dataset tree not populating after experiment completion

### Testing Status

#### ✅ **Fully Tested and Working**
- Confocal scanning (`nanodrive_adwin_confocal_scan_fast.py`)
- SG384 microwave generator communication
- Parameter validation system
- Mock data generation
- GUI dataset functionality
- Basic experiment loading and execution

#### ⚠️ **Partially Tested**
- ODMR sweep continuous (parameter structure fixed, limited hardware testing)
- Experiment iterator functionality (core fixes tested, advanced features not fully tested)

#### ❌ **Untested/Experimental**
- Pulsed ODMR experiments
- AWG520 integration
- Advanced experiment iterator features
- Multi-variable scans
- Some deprecated experiment classes

### Breaking Changes
- **ODMR Sweep Continuous**: Parameter `sweep_rate` renamed to `step_freq`
  - Existing `.aqs` files need manual update: change `"sweep_rate"` to `"step_freq"`
- **Parameter Validation**: Stricter validation for nested parameters

### Migration Guide
1. **For ODMR Sweep Continuous experiments**:
   - Open your `.aqs` file in a text editor
   - Find `"sweep_rate": <value>` in the microwave section
   - Replace with `"step_freq": <value>`
   - Save the file

2. **For new experiments**:
   - Use the new parameter structure with `step_freq`
   - The system will automatically calculate `sweep_rate` from `step_freq`, `integration_time`, and `settle_time`

### Known Issues
- Some deprecated experiment classes may show warnings
- MUX controller connection may fail on systems without COM3 (gracefully handled)
- Some advanced experiment iterator features need additional testing

### Contributors
- @gurudevdutt: Core fixes, mock data system, parameter validation improvements
