# AWG520 Arbitrary Waveform Generator

This directory contains comprehensive tests and examples for the Tektronix AWG520 arbitrary waveform generator, including laser control functionality via CH1 Marker 2.

## Overview

The AWG520 is a high-performance arbitrary waveform generator that provides:
- Two independent channels with 10-bit resolution
- Marker outputs for triggering and control
- SCPI command interface over TCP/IP
- File transfer capabilities via FTP
- Enhanced sequence mode for complex waveform generation

## Key Features

### Laser Control via CH1 Marker 2
The AWG520 driver includes specialized functions for controlling a laser using CH1 Marker 2:
- **Laser ON**: Sets CH1 Marker 2 voltage to 2V
- **Laser OFF**: Sets CH1 Marker 2 voltage to 0V
- **Custom Voltage**: Set arbitrary voltage levels for fine control
- **Status Monitoring**: Check current laser state and voltage levels

### Function Generator and IQ Modulation
The AWG520 includes built-in function generators for generating standard waveforms:
- **Single Channel**: Generate sine, square, triangle, ramp, noise, or DC on individual channels
- **I/Q Modulation**: Generate sine and cosine waves with 90° phase difference for quadrature modulation
- **Frequency Range**: Support for Hz, kHz, MHz, and GHz frequencies
- **Voltage Control**: Adjustable output voltage levels
- **Phase Control**: Configurable phase offsets

### Marker Control
Comprehensive control over all marker outputs:
- **CH1 Marker 1**: General purpose marker output
- **CH1 Marker 2**: Laser control (primary function)
- **CH2 Marker 1**: General purpose marker output
- **CH2 Marker 2**: General purpose marker output

## Files

### Tests
- **`tests/test_awg520.py`**: Comprehensive test suite covering all AWG520 functionality
  - Unit tests for SCPI communication
  - Mock tests for file operations
  - Hardware integration tests (when device is available)
  - Laser control function tests
  - Marker voltage control tests

### Examples
- **`examples/awg520_example.py`**: Complete demonstration script
  - Basic SCPI communication
  - Clock configuration
  - Sequence control
  - File operations
  - Laser control demonstration
  - Device status monitoring

## Quick Start

### Running Unit Tests (No Hardware Required)
```bash
# Run all AWG520 tests
python -m pytest tests/test_awg520.py -v

# Run specific test categories
python -m pytest tests/test_awg520.py::TestAWG520Driver -v
python -m pytest tests/test_awg520.py::TestAWG520LaserControl -v
python -m pytest tests/test_awg520.py::TestAWG520Device -v
```

### Running Hardware Tests (Real Hardware Required)

**On macOS/Linux:**
```bash
# Set environment variable and run hardware tests
export RUN_HARDWARE_TESTS=1
python -m pytest tests/test_awg520.py::TestAWG520Hardware -v

# Or run all tests including hardware
export RUN_HARDWARE_TESTS=1
python -m pytest tests/test_awg520.py -v
```

**On Windows Command Prompt:**
```cmd
# Set environment variable and run hardware tests
set RUN_HARDWARE_TESTS=1
python -m pytest tests/test_awg520.py::TestAWG520Hardware -v

# Or run all tests including hardware
set RUN_HARDWARE_TESTS=1
python -m pytest tests/test_awg520.py -v
```

**On Windows PowerShell:**
```powershell
# Set environment variable and run hardware tests
$env:RUN_HARDWARE_TESTS=1
python -m pytest tests/test_awg520.py::TestAWG520Hardware -v

# Or run all tests including hardware
$env:RUN_HARDWARE_TESTS=1
python -m pytest tests/test_awg520.py -v
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

### Running the Example Script
```bash
# Default connection (172.17.39.2:4000)
python examples/awg520_example.py

# Custom IP address
python examples/awg520_example.py --ip-address 192.168.1.100

# Custom connection settings
python examples/awg520_example.py --ip-address 192.168.1.100 --scpi-port 4000 --ftp-port 21
```

## Connection Settings

### Default Configuration
- **IP Address**: 172.17.39.2
- **SCPI Port**: 4000
- **FTP Port**: 21
- **Username**: usr
- **Password**: pw

### Custom Configuration
You can override any connection parameter using command-line arguments:
```bash
python examples/awg520_example.py \
    --ip-address 192.168.1.100 \
    --scpi-port 4000 \
    --ftp-port 21 \
    --ftp-user custom_user \
    --ftp-pass custom_pass
```

## Laser Control Functions

### Basic Laser Control
```python
from src.Controller.awg520 import AWG520Driver

# Connect to AWG520
driver = AWG520Driver('192.168.1.100')

# Turn laser ON (sets CH1 Marker 2 to 5V)
driver.set_ch1_marker2_laser_on()

# Turn laser OFF (sets CH1 Marker 2 to 0V)
driver.set_ch1_marker2_laser_off()

# Check laser status
is_on = driver.is_ch1_marker2_laser_on()
```

### Custom Voltage Control
```python
# Set custom voltage levels
driver.set_ch1_marker2_voltage(3.3)  # Same low/high voltage
driver.set_ch1_marker2_voltage(2.5, 5.0)  # Different low/high voltages

# Get current voltage levels
low_v, high_v = driver.get_ch1_marker2_voltage()
```

### Function Generator and IQ Modulation
```python
# Basic function generator setup
driver.set_function_generator(1, 'SIN', '10MHz', 2.0, 0.0, True)
driver.set_function_generator(2, 'SIN', '10MHz', 2.0, 90.0, True)

# Get function generator status
status = driver.get_function_generator_status(1)

# I/Q modulation (convenience functions)
driver.enable_iq_modulation('10MHz', 2.0)
driver.disable_iq_modulation()

# MW control with I/Q modulation
driver.mw_on_sb10MHz(enable_iq=True)
driver.mw_off_sb10MHz(enable_iq=True)
```

### Device Wrapper Usage
```python
from src.Controller.awg520 import AWG520Device

# Create device instance
device = AWG520Device(settings={
    'ip_address': '192.168.1.100',
    'scpi_port': 4000,
    'ftp_port': 21,
    'ftp_user': 'usr',
    'ftp_pass': 'pw'
})

# Use high-level methods
device.laser_on()
device.laser_off()
device.set_laser_voltage(3.3)
is_on = device.is_laser_on()
```

## Marker Control Functions

### All Marker Outputs
```python
# CH1 Marker 1
driver.set_ch1_marker1_voltage(2.0)
low_v, high_v = driver.get_ch1_marker1_voltage()

# CH1 Marker 2 (Laser Control)
driver.set_ch1_marker2_voltage(5.0)
low_v, high_v = driver.get_ch1_marker2_voltage()

# CH2 Marker 1
driver.set_ch2_marker1_voltage(3.0)
low_v, high_v = driver.get_ch2_marker1_voltage()

# CH2 Marker 2
driver.set_ch2_marker2_voltage(4.0)
low_v, high_v = driver.get_ch2_marker2_voltage()
```

## SCPI Commands

### Clock Configuration
```python
# Set clock source
driver.set_clock_external()      # AWGC:CLOC:SOUR EXT
driver.set_clock_internal()      # AWGC:CLOC:SOUR INT

# Set reference clock
driver.set_ref_clock_external()  # SOUR1/2:ROSC:SOUR EXT
driver.set_ref_clock_internal()  # SOUR1/2:ROSC:SOUR INT

# Enhanced run mode
driver.set_enhanced_run_mode()   # AWGC:RMOD ENH
```

### Sequence Control
```python
# Basic control
driver.run()                     # AWGC:RUN
driver.stop()                    # AWGC:STOP
driver.trigger()                 # *TRG
driver.event()                   # AWGC:EVEN

# Advanced control
driver.jump(5)                   # AWGC:EVEN:SOFT 5
```

### Marker Voltage Control
```python
# Set marker voltages
driver.send_command('SOUR1:MARK2:VOLT:LOW 5.0')
driver.send_command('SOUR1:MARK2:VOLT:HIGH 5.0')

# Query marker voltages
low_v = driver.send_command('SOUR1:MARK2:VOLT:LOW?', query=True)
high_v = driver.send_command('SOUR1:MARK2:VOLT:HIGH?', query=True)
```

### Function Generator Control
```python
# Set function generator parameters
driver.send_command('AWGC:FG1:FUNC SIN')
driver.send_command('AWGC:FG1:FREQ 10MHz')
driver.send_command('AWGC:FG1:VOLT 2.0')
driver.send_command('AWGC:FG1:PHAS 0DEG')

# Query function generator parameters
function = driver.send_command('AWGC:FG1:FUNC?', query=True)
frequency = driver.send_command('AWGC:FG1:FREQ?', query=True)
voltage = driver.send_command('AWGC:FG1:VOLT?', query=True)
phase = driver.send_command('AWGC:FG1:PHAS?', query=True)
```

## File Operations

### FTP File Management
```python
# List files
files = driver.list_files()

# Upload file
success = driver.upload_file('local_file.wfm', 'remote_file.wfm')

# Download file
success = driver.download_file('remote_file.wfm', 'local_file.wfm')

# Delete file
success = driver.delete_file('remote_file.wfm')
```

### Sequence Setup
```python
# Complete sequence setup
driver.setup_sequence('sequence.seq', enable_iq=True)
# This includes:
# - Clock configuration
# - Enhanced run mode
# - File loading
# - Voltage settings
# - Output configuration
```

## Safety Features

### Automatic Cleanup
The example script includes automatic cleanup to ensure the device is left in a safe state:
- Stops any running sequences
- Turns off the laser
- Sets safe marker voltages
- Closes connections properly

### Laser Safety
- Laser control functions include appropriate delays
- Voltage verification after setting
- Automatic laser shutdown on cleanup
- Status monitoring for verification

## Error Handling

### Connection Failures
- Graceful handling of network timeouts
- FTP connection retry logic
- SCPI command error reporting
- Comprehensive logging

### Hardware Errors
- Voltage setting verification
- Status checking after operations
- Fallback to safe states
- Error reporting and recovery

## Performance Considerations

### Timing
- SCPI commands include 50ms delays for stability
- FTP operations are asynchronous
- Sequence setup includes appropriate delays
- Real-time monitoring with minimal overhead

### Memory Management
- Efficient file handling
- Proper cleanup of resources
- Memory-efficient data structures
- Garbage collection optimization

## Troubleshooting

### Common Issues

#### Connection Problems
- Verify IP address and network connectivity
- Check firewall settings for ports 4000 and 21
- Ensure AWG520 is powered on and networked
- Verify FTP credentials

#### Laser Control Issues
- Check marker voltage settings
- Verify CH1 Marker 2 connections
- Monitor voltage levels with multimeter
- Check laser power supply requirements

#### SCPI Command Failures
- Verify device is in correct mode
- Check for error messages in device logs
- Ensure commands are sent in correct sequence
- Verify device supports requested commands

### Debug Mode
Enable debug logging for detailed troubleshooting:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Integration with Experiments

### Using in Experiment Classes
```python
from src.Controller.awg520 import AWG520Device

class MyExperiment:
    def __init__(self):
        self.awg = AWG520Device(settings={...})
    
    def setup_laser(self):
        self.awg.laser_on()
    
    def cleanup(self):
        self.awg.laser_off()
        self.awg.cleanup()
```

### Marker Synchronization
```python
# Synchronize markers with analog outputs
driver.setup_sequence('experiment.seq')
driver.run()

# Control laser timing
driver.set_ch1_marker2_voltage(5.0)  # Laser ON
time.sleep(1.0)                       # Wait
driver.set_ch1_marker2_voltage(0.0)  # Laser OFF
```

## Future Enhancements

### Planned Features
- Waveform generation and upload
- Advanced sequence programming
- Real-time parameter adjustment
- Integration with other experiment devices
- Automated calibration routines

### Extension Points
- Custom marker control algorithms
- Advanced timing synchronization
- Multi-device coordination
- Data logging and analysis
- Remote monitoring capabilities

## Support and Documentation

### Additional Resources
- Tektronix AWG520 User Manual
- SCPI Command Reference
- Network Configuration Guide
- Troubleshooting Guide

### Contributing
- Report bugs and issues
- Suggest new features
- Submit test improvements
- Share experiment configurations

## License

This software is provided under the GNU General Public License v2.0 or later. See the LICENSE file for details. 