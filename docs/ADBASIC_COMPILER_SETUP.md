# ADbasic Compiler Setup Guide

This document explains how to set up the ADbasic compiler integration for the PittQLabSys project on macOS, enabling on-the-fly compilation of ADbasic (.bas) files to ADwin binary (.TB*) files.

## Overview

The ADbasic compiler integration allows you to:
- Compile ADbasic source files directly from Python
- Automatically load compiled files into the ADwin
- Eliminate the need for manual compilation steps
- Work seamlessly across different systems
- **NEW**: Manage ADwin licenses for full functionality

## Prerequisites

- macOS system (tested on macOS 12+)
- Homebrew installed
- Python virtual environment with the project dependencies
- ADwin hardware (optional for testing)
- **NEW**: ADwin license (optional, but recommended for full functionality)

## Installation Steps

### 1. Install Wine

The ADbasic compiler is a Windows executable, so we need Wine to run it on macOS:

```bash
# Install Wine using Homebrew
brew install --cask wine-stable

# If prompted, install Rosetta 2 (required for Intel-based Wine on Apple Silicon)
softwareupdate --install-rosetta --agree-to-license
```

### 2. Download ADwin Compiler

1. Download the ADwin Linux package from the ADwin website
2. Extract the package:
   ```bash
   cd ~/Downloads
   tar -xzf ADwin-linux_6.0.37.tar.gz
   tar -xzf adwin-compiler-6.0.37.tar.gz
   ```

### 3. Set Up ADwin Directory

```bash
# Create ADwin installation directory
mkdir -p ~/adwin

# Copy compiler files
cp -r adwin-compiler-6.0.37/* ~/adwin/
```

### 4. Configure Wine

```bash
# Remove old Wine prefix if it exists
rm -rf ~/.wine32-adwin

# Create new Wine prefix for ADwin
export WINEARCH=win64
export WINEPREFIX=$HOME/.wine64-adwin
winecfg
```

### 5. Create Modified Compiler Script

The original `adbasic` script expects a system-wide configuration file. We create a modified version that uses environment variables:

```bash
cd ~/adwin/bin
cp adbasic adbasic-mac
chmod +x adbasic-mac
```

Edit `~/adwin/bin/adbasic-mac` to use environment variables instead of the system file:

```bash
#!/bin/bash

export WINEARCH=win64
export WINEPREFIX=$HOME/.wine64-adwin

# Use environment variable if set, otherwise try to read from file
if [ -n "$ADWINDIR" ]; then
    echo "Using ADWINDIR from environment: $ADWINDIR"
elif [ -r /etc/adwin/ADWINDIR ]; then
    ADWINDIR=`cat /etc/adwin/ADWINDIR`
    echo "Using ADWINDIR from file: $ADWINDIR"
else
    echo "ADWINDIR not set and file /etc/adwin/ADWINDIR not found - please set ADWINDIR environment variable"
    exit 2
fi

# ... rest of the original script content ...
```

### 6. Set Up License (Optional but Recommended)

**NEW**: The compiler now supports license management for full functionality:

```bash
# Create a license template
python -c "from src.core.adbasic_compiler import create_license_template; create_license_template()"

# Edit the template with your license information
nano src/Controller/adwin_license_template.json
```

The license file should contain:
```json
{
  "license_key": "YOUR_ACTUAL_LICENSE_KEY",
  "device_type": "ADwin Gold II",
  "device_id": "YOUR_DEVICE_ID",
  "expiration_date": "YYYY-MM-DD",
  "features": [
    "ADbasic_compiler",
    "TiCO_compiler",
    "real_time_processing"
  ],
  "notes": "Your license notes"
}
```

**License File Locations** (searched in order):
1. `~/.adwin_license.json` (recommended for security)
2. `~/adwin_license.json`
3. `~/adwin/license.json`
4. `adwin_license.json` (current directory)
5. `src/Controller/adwin_license.json` (project directory)

## Python Integration

### 1. ADbasic Compiler Module

The project includes `src/core/adbasic_compiler.py` which provides:

- `ADbasicCompiler` class for managing compilation
- `compile_adbasic_file()` function for single file compilation
- `compile_adbasic_directory()` function for batch compilation
- **NEW**: License management and validation
- Automatic process number detection
- License error handling

### 2. ADwin Controller Integration

The `src/Controller/adwin.py` file has been enhanced with:

- `compile_and_load_process()` method
- `compile_and_load_directory()` method
- **NEW**: `check_license_status()` method
- Automatic compilation and loading workflow
- License-aware compilation

### 3. ADwin Helper Functions

The project includes `src/core/adwin_helpers.py` which provides:

- Helper functions for setting up ADwin processes
- Functions for reading ADwin data
- Support for different experiment types (ODMR, sweep, FM)
- Centralized binary file path management

## Usage Examples

### Basic Compilation

```python
from src.core.adbasic_compiler import compile_adbasic_file

# Compile a single file
compiled_file = compile_adbasic_file('path/to/file.bas', verbose=True)
print(f"Compiled to: {compiled_file}")
```

### ADwin Integration

```python
from src.Controller.adwin_gold import AdwinGoldDevice

# Initialize ADwin
adwin = AdwinGoldDevice()

# Check license status
license_status = adwin.check_license_status()
print(f"License status: {license_status['status']}")

# Compile and load a single file
compiled_file = adwin.compile_and_load_process(
   'path/to/file.bas',
   process_number=1,
   auto_start=True
)

# Compile and load all files in a directory
results = adwin.compile_and_load_directory('path/to/adbasic/directory/')
```

### License-Aware Compilation

```python
from src.core.adbasic_compiler import ADbasicCompiler

# Initialize with specific license file
compiler = ADbasicCompiler(license_file='~/my_license.json')

# Check license status
if compiler.has_valid_license():
    print("Full functionality available")
    license_info = compiler.get_license_info()
    print(f"Device: {license_info['device_type']}")
else:
    print("Limited functionality (license warnings expected)")

# Compile with license
compiled_file = compiler.compile_file('file.bas', apply_license=True)
```

### Standalone Compiler

```python
from src.core.adbasic_compiler import ADbasicCompiler

compiler = ADbasicCompiler()

# Check if compiler is working
if compiler.check_compiler():
    print("Compiler is ready")

# Compile with custom settings
compiled_file = compiler.compile_file(
    source_file='file.bas',
    output_dir='output/',
    process_number=2,
    verbose=True
)
```

## Testing

Run the test script to verify the setup:

```bash
# Activate virtual environment
source venv/bin/activate

# Run the test
python test_adwin_compile.py
```

The test script will:
1. Verify the compiler is working
2. Test license management functionality
3. Test license file usage
4. Test single file compilation
5. Test directory compilation
6. Test ADwin integration (if hardware is available)

## License Management

### License Benefits

With a valid license, you get:
- Full compilation without warnings
- Access to all compiler features
- No license error messages
- Complete binary file generation

### License Setup

1. **Get your license information** from ADwin (device ID, license key, etc.)
2. **Create license template**:
   ```bash
   python -c "from src.core.adbasic_compiler import create_license_template; create_license_template()"
   ```
3. **Edit the template** with your actual license information
4. **Place the license file** in one of the supported locations
5. **Test the license**:
   ```python
   from src.Controller.adwin_gold import AdwinGoldDevice
   adwin = AdwinGoldDevice()
   status = adwin.check_license_status()
   print(status['status'])
   ```

### License File Format

```json
{
  "license_key": "YOUR_LICENSE_KEY_HERE",
  "device_type": "ADwin Gold II",
  "device_id": "YOUR_DEVICE_ID_HERE",
  "expiration_date": "YYYY-MM-DD",
  "features": [
    "ADbasic_compiler",
    "TiCO_compiler",
    "real_time_processing"
  ],
  "notes": "Optional notes about your license"
}
```

## Troubleshooting

### Common Issues

1. **Wine not found**
   ```bash
   brew install --cask wine-stable
   ```

2. **Permission denied on Wine**
   ```bash
   sudo xattr -rd com.apple.quarantine /Applications/Wine\ Stable.app
   ```

3. **License errors**
   - These are expected without a valid ADwin license
   - The compiler still works for testing purposes
   - Contact ADwin for a license if needed for production

4. **ADwin library not found**
   - This is expected if no ADwin hardware is connected
   - The compilation will still work for testing

5. **License file not found**
   - Check that the license file is in one of the supported locations
   - Verify the JSON format is correct
   - Ensure all required fields are present

### Environment Variables

The following environment variables are used:

- `ADWINDIR`: Path to ADwin installation (default: `~/adwin`)
- `WINEARCH`: Wine architecture (set to `win64`)
- `WINEPREFIX`: Wine prefix directory (set to `~/.wine64-adwin`)

## File Structure

```
~/adwin/
├── bin/
│   ├── adbasic-mac          # Modified compiler script
│   ├── ADbasicCompiler.exe  # Windows compiler executable
│   └── ...
├── share/
└── ...

src/
├── core/
│   ├── adbasic_compiler.py  # Python wrapper with license support
│   └── adwin_helpers.py     # ADwin helper functions for experiments
└── Controller/
    └── adwin.py            # Enhanced ADwin controller

~/.adwin_license.json       # License file (recommended location)
```

## Architecture Notes

### Why ADwin Modules Are in `src/core/`

The ADwin-related modules (`adbasic_compiler.py` and `adwin_helpers.py`) are intentionally placed in `src/core/` rather than `src/Controller/` for several architectural reasons:

1. **Cross-cutting Concerns**: These modules are used by multiple experiments across different modules, not just controllers
2. **Avoiding Circular Imports**: Experiments import from `core/`, controllers import from `Controller/` - this prevents circular dependency issues
3. **Foundational Utilities**: They provide foundational ADwin abstractions that bridge hardware and experiment logic
4. **Stable API**: Experiments depend on these functions, so they need a stable location

### Import Hierarchy
```
src/core/ (foundational utilities)
    ↓
src/Controller/ (hardware drivers)
    ↓  
src/Model/experiments/ (experiment logic)
```

This structure follows the principle of "keep cross-cutting concerns in core" and provides a clean separation of concerns while avoiding import complexity.

## Benefits

1. **Automation**: No more manual compilation steps
2. **Cross-platform**: Works on macOS with Wine
3. **Integration**: Seamless Python workflow
4. **Error handling**: Graceful handling of license and hardware issues
5. **Flexibility**: Support for single files and batch compilation
6. **License Management**: Full control over ADwin licensing
7. **Security**: License files can be stored securely
8. **Clean Architecture**: Proper separation of concerns without circular dependencies

## Future Enhancements

- Support for other operating systems (Linux, Windows)
- Integration with IDE plugins
- Automatic dependency management
- Real-time compilation monitoring
- License renewal notifications
- Multi-device license support

## Support

For issues related to:
- ADwin hardware: Contact ADwin support
- Wine setup: Check Wine documentation
- Python integration: Check project documentation
- License issues: Contact ADwin for licensing
- License file format: Check the template and documentation

## License

This integration is part of the PittQLabSys project. The ADbasic compiler itself is proprietary software from ADwin. 