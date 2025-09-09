# SG384 Microwave Generator Tests and Examples

This directory contains comprehensive tests and examples for the Stanford Research Systems SG384 microwave generator, focusing on frequency control, power management, and internal phase continuous sweep generation.

## Overview

The SG384 is a high-performance microwave generator capable of:
- **Frequency Range**: 1 MHz to 4 GHz
- **Power Range**: -110 to +16.5 dBm
- **Phase Control**: 0° to 360°
- **Internal Sweep**: Phase continuous frequency sweeping
- **Modulation**: AM, FM, Phase, and Pulse modulation
- **Connections**: LAN, GPIB, and RS232

## Recent Updates

### Parameter Inheritance (v1.1.0)

The SG384 device now properly inherits all parameters from its base class `MicrowaveGeneratorBase`, including:
- `connection_timeout`: Connection timeout for LAN connections (default: 10.0 seconds)
- `socket_timeout`: Socket timeout for send/receive operations (default: 5.0 seconds)

This fixes GUI display issues and ensures all device parameters are available for configuration.

### Configuration

The SG384 device can be configured in `config.json`:

```json
{
    "devices": {
        "sg384": {
            "class": "SG384Generator",
            "filepath": "src/Controller/sg384.py",
            "settings": {
                "ip_address": "192.168.2.217",
                "port": 5025,
                "connection_timeout": 10.0,
                "socket_timeout": 5.0
            }
        }
    }
}
```

## Files

### Test Files
- **`tests/test_sg384_enhanced.py`** - Enhanced hardware tests with real SG384 device
- **`tests/test_sg384_example.py`** - Unit tests for the example script (no hardware required)
- **`tests/test_sg384.py`** - Existing unit tests with mocked SG384
- **`tests/test_sg384_hardware.py`** - Existing hardware integration tests

### Example Files
- **`examples/sg384_example.py`** - Comprehensive demonstration script
- **`examples/sg384_data/`** - Output directory for generated data and plots

## Quick Start

### 1. Run Unit Tests (No Hardware Required)

```bash
# Activate virtual environment
source venv/bin/activate

# Run unit tests for the example script
pytest tests/test_sg384_example.py -v

# Run existing SG384 unit tests
pytest tests/test_sg384.py -v
```

### 2. Run Hardware Tests (SG384 Device Required)

**On macOS/Linux:**
```bash
# Set environment variable and run enhanced hardware tests
export RUN_HARDWARE_TESTS=1
python -m pytest tests/test_sg384_enhanced.py -v

# Run existing hardware tests
export RUN_HARDWARE_TESTS=1
python -m pytest tests/test_sg384_hardware.py -v

# Run all hardware tests
export RUN_HARDWARE_TESTS=1
python -m pytest -m hardware -v
```

**On Windows Command Prompt:**
```cmd
# Set environment variable and run enhanced hardware tests
set RUN_HARDWARE_TESTS=1
python -m pytest tests/test_sg384_enhanced.py -v

# Run existing hardware tests
set RUN_HARDWARE_TESTS=1
python -m pytest tests/test_sg384_hardware.py -v

# Run all hardware tests
set RUN_HARDWARE_TESTS=1
python -m pytest -m hardware -v
```

**On Windows PowerShell:**
```powershell
# Set environment variable and run enhanced hardware tests
$env:RUN_HARDWARE_TESTS=1
python -m pytest tests/test_sg384_enhanced.py -v

# Run existing hardware tests
$env:RUN_HARDWARE_TESTS=1
python -m pytest tests/test_sg384_hardware.py -v

# Run all hardware tests
$env:RUN_HARDWARE_TESTS=1
python -m pytest -m hardware -v
```

**Note:** The environment variable only affects the current terminal session. Hardware tests are skipped by default to prevent timeouts when no hardware is connected.

## Hardware Test Configuration

### Environment Variable System

The test suite uses an environment variable `RUN_HARDWARE_TESTS` to control whether hardware tests are executed:

- **Default behavior**: Hardware tests are automatically skipped to prevent timeouts
- **With hardware**: Set `RUN_HARDWARE_TESTS=1` to enable hardware tests
- **Cross-platform**: Works on macOS, Linux, and Windows

### Why This System?

- **Prevents timeouts**: No more waiting for hardware that isn't connected
- **Faster development**: Unit tests run quickly without hardware dependencies
- **Flexible testing**: Easy to switch between unit tests and hardware tests
- **CI/CD friendly**: Automated builds can run unit tests without hardware

### Quick Reference Card

| Platform | Command | Description |
|----------|---------|-------------|
| **macOS/Linux** | `export RUN_HARDWARE_TESTS=1` | Enable hardware tests |
| **Windows CMD** | `set RUN_HARDWARE_TESTS=1` | Enable hardware tests |
| **Windows PowerShell** | `$env:RUN_HARDWARE_TESTS=1` | Enable hardware tests |
| **All platforms** | `unset RUN_HARDWARE_TESTS` | Disable hardware tests (macOS/Linux) |
| **Windows CMD** | `set RUN_HARDWARE_TESTS=` | Disable hardware tests |
| **Windows PowerShell** | `Remove-Item Env:RUN_HARDWARE_TESTS` | Disable hardware tests |

### 3. Run Example Script (SG384 Device Required)

```bash
# LAN connection (default)
python examples/sg384_example.py --ip-address 169.254.146.198 --port 5025

# GPIB connection
python examples/sg384_example.py --connection-type GPIB --visa-resource "GPIB0::20::INSTR"

# RS232 connection
python examples/sg384_example.py --connection-type RS232 --visa-resource "ASRL9::INSTR"
```

## Enhanced Hardware Tests

The `tests/test_sg384_enhanced.py` file provides comprehensive testing of:

### Basic Functionality
- **Connection Test** - Device identification and communication
- **Frequency Range Validation** - Testing across 1 MHz to 4 GHz
- **Power Range Validation** - Testing from -110 to +16.5 dBm
- **Phase Control** - 0° to 360° phase setting

### Advanced Features
- **Phase Continuous Sweep** - Internal sweep generation and monitoring
- **Frequency Sweep with Power Control** - Sweep while maintaining power stability
- **Rapid Frequency Changes** - Dynamic frequency hopping performance
- **Power Ramping** - Gradual power changes for sensitive applications
- **Sweep Parameter Validation** - Hardware-specific parameter limits
- **Device Probes** - Real-time monitoring capabilities

### Safety and Cleanup
- **Cleanup and Safety** - Automatic device reset to safe state
- **Output Control** - RF output enable/disable testing
- **Sweep Control** - Start/stop sweep functionality

## Example Script Features

The `examples/sg384_example.py` script demonstrates:

### 1. Basic Operation Demonstration
- **Frequency Control**: Test frequencies from 1 GHz to 3.5 GHz
- **Power Control**: Test power levels from -20 to +10 dBm
- **Phase Control**: Test phase settings from 0° to 360°

### 2. Sweep Generation Demonstration
- **Internal Sweep**: Configure and run internal phase continuous sweep
- **Real-time Monitoring**: Monitor frequency and power during sweep
- **Data Collection**: Collect sweep data for analysis
- **Automatic Plotting**: Generate PNG plots of sweep results

### 3. Power Ramping Demonstration
- **Gradual Changes**: Ramp power from -20 to 0 dBm in 2 dB steps
- **Performance Analysis**: Measure power accuracy and settling time
- **Data Logging**: Record all power measurements

### 4. Frequency Hopping Demonstration
- **Dynamic Changes**: Rapid frequency changes for dynamic applications
- **Timing Analysis**: Measure frequency change response time
- **Pattern Testing**: Test complex frequency hopping patterns

## Data Output

The example script generates several types of output files:

### Data Files
- **NPZ Files**: NumPy compressed arrays for data analysis
- **CSV Files**: Comma-separated values for spreadsheet analysis
- **Summary Files**: Parameter summaries and metadata

### Plot Files
- **PNG Images**: High-resolution plots for documentation
- **Sweep Plots**: Frequency vs. time and power vs. time
- **Customizable**: Easy to modify plot appearance and save formats

### Output Directory Structure
```
examples/sg384_data/
├── sg384_sweep_YYYYMMDD_HHMMSS.csv          # Sweep data
├── sg384_sweep_YYYYMMDD_HHMMSS_summary.csv  # Sweep parameters
├── sg384_sweep_YYYYMMDD_HHMMSS.npz          # Compressed sweep data
├── sg384_sweep_plot_YYYYMMDD_HHMMSS.png     # Sweep visualization
├── sg384_power_ramp_YYYYMMDD_HHMMSS.csv     # Power ramping data
└── sg384_frequency_hop_YYYYMMDD_HHMMSS.csv  # Frequency hopping data
```

## Configuration

### Connection Settings

#### LAN Connection (Recommended)
```python
settings = {
    'connection_type': 'LAN',
    'ip_address': '169.254.146.198',  # Your SG384 IP address
    'port': 5025                      # Default SG384 port
}
```

#### GPIB Connection
```python
settings = {
    'connection_type': 'GPIB',
    'visa_resource': 'GPIB0::20::INSTR'  # Your GPIB address
}
```

#### RS232 Connection
```python
settings = {
    'connection_type': 'RS232',
    'visa_resource': 'ASRL9::INSTR',     # Your serial port
    'baud_rate': 115200                  # Communication speed
}
```

### Safety Parameters
The scripts automatically set safe parameters:
- **Default Frequency**: 2.5 GHz
- **Default Power**: -20 dBm (low power)
- **Default Phase**: 0°
- **Output**: Disabled during testing
- **Sweep**: Stopped after demonstrations

## Troubleshooting

### Common Issues

#### Connection Problems
- **LAN**: Check IP address and port, ensure SG384 is on the network
- **GPIB**: Verify VISA drivers and GPIB address
- **RS232**: Check COM port and baud rate settings

#### Test Failures
- **Frequency Accuracy**: Verify SG384 calibration
- **Power Accuracy**: Check power meter calibration
- **Sweep Issues**: Ensure sweep parameters are within device limits

#### Import Errors
- Activate virtual environment: `source venv/bin/activate`
- Install dependencies: `pip install -r requirements.txt`
- Check Python path: Ensure `src/` directory is accessible

### Debug Mode
Enable verbose output for debugging:
```bash
# Verbose test output
pytest tests/test_sg384_enhanced.py -m hardware -v -s

# Verbose example script
python examples/sg384_example.py --ip-address 192.168.1.100 --port 5025 -v
```

## Performance Characteristics

### Typical Performance
- **Frequency Setting**: < 1 ms settling time
- **Power Setting**: < 10 ms settling time
- **Phase Setting**: < 1 ms settling time
- **Sweep Rate**: Up to 100 MHz/s (device dependent)
- **Frequency Accuracy**: ±1 ppm (typical)
- **Power Accuracy**: ±0.5 dB (typical)

### Limitations
- **Maximum Sweep Rate**: Limited by device specifications
- **Frequency Range**: 1 MHz to 4 GHz (hardware limit)
- **Power Range**: -110 to +16.5 dBm (hardware limit)
- **Phase Resolution**: 0.1° (typical)

## Planned Improvements

### Modulation Depth Validation System

The SG384 implementation is planned to include a comprehensive modulation depth validation system:

#### **Context-Aware SCPI Mapping**
- **AM Modulation**: `ADEP` command for depth (0-100%)
- **FM Modulation**: `FDEV` command for frequency deviation (Hz)
- **Phase Modulation**: `PDEV` command for phase deviation (0-360°)

#### **Type-Specific Validation**
- **AM Depth**: 0.0% to 100.0% (percentage)
- **FM Deviation**: 0 Hz to max allowed by instrument (typically 100 MHz)
- **PM Deviation**: 0° to 360° (degrees)

#### **Implementation Benefits**
- **Prevents invalid commands** being sent to hardware
- **User-friendly error messages** with context
- **Automatic SCPI command selection** based on modulation type
- **Consistent validation** across all modulation types

#### **Example Usage**
```python
# The system will automatically:
# 1. Detect modulation type (AM/FM/PM)
# 2. Validate depth value against type-specific limits
# 3. Select appropriate SCPI command (ADEP/FDEV/PDEV)
# 4. Send validated command to hardware

sg384.set_modulation_type('AM')
sg384.set_modulation_depth(50.0)  # 50% AM depth → ADEP 50.0
```

### Current Status
- ✅ **SCPI_MAPPINGS** implemented (replacing hardcoded commands)
- ✅ **Phase stepping logic** with 360° limit validation
- ✅ **Proper output channel mapping** (BNC vs RF)
- 🔄 **Modulation depth validation** - planned for next phase

## Integration with Experiments

The SG384 can be integrated with other experiment classes:

```python
from src.Controller.sg384 import SG384Generator
from src.Model.experiments.odmr_experiment import ODMRExperiment

# Create SG384 instance
sg384 = SG384Generator(settings={
    'connection_type': 'LAN',
    'ip_address': '169.254.146.198',
    'port': 5025
})

# Use in ODMR experiment
experiment = ODMRExperiment(devices={'mw_generator': sg384})
```

## Contributing

When adding new tests or examples:

1. **Follow pytest conventions** - Use descriptive test names and fixtures
2. **Include hardware markers** - Mark hardware tests with `@pytest.mark.hardware`
3. **Add safety measures** - Always include cleanup and safety tests
4. **Document parameters** - Include expected ranges and tolerances
5. **Test edge cases** - Include boundary condition testing

## References

- [SG384 Manual](https://www.thinksrs.com/products/sg384.html)
- [SCPI Command Reference](https://www.thinksrs.com/downloads/PDFs/Manuals/SG384m.pdf)
- [PyVISA Documentation](https://pyvisa.readthedocs.io/)
- [Pytest Documentation](https://docs.pytest.org/)

## License

This code is part of the pittqlabsys project and follows the same licensing terms. 