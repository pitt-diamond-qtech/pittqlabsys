# AWG520 Arbitrary Waveform Generator

This directory contains comprehensive tests and examples for the Tektronix AWG520 arbitrary waveform generator, including laser control functionality via CH1 Marker 2 and integration with the hardware connection system.

## Overview

The AWG520 is a high-performance arbitrary waveform generator that provides:
- Two independent channels with 10-bit resolution
- Marker outputs for triggering and control
- SCPI command interface over TCP/IP
- File transfer capabilities via FTP
- Enhanced sequence mode for complex waveform generation
- **NEW**: Hardware connection mapping and calibration system

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

### Hardware Connection System
**NEW**: Configurable hardware connection mapping and calibration:
- **Connection Templates**: Pre-configured connection maps for common setups
- **Calibration Delays**: Automatic compensation for hardware timing delays
- **Connection Validation**: Verify required connections for experiment types
- **Cross-lab Compatibility**: Easy deployment to different lab environments

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

### Configuration Files
- **`src/Controller/awg520_connection.template.json`**: Default connection template for hardware mapping
- **`src/Model/experiments/{experiment}_connection.json`**: Experiment-specific connection files
- **`config.sample.json`**: Device configuration template with AWG520 settings

## Quick Start

### 1. Device Configuration Setup

**Copy the sample configuration:**
```bash
cp config.sample.json config.json
```

**Edit `config.json` for your lab:**
```json
{
  "devices": {
    "awg520": {
      "class": "AWG520Device",
      "filepath": "src/Controller/awg520.py",
      "settings": {
        "ip_address": "192.168.1.100",  # Your AWG520 IP
        "scpi_port": 4000,
        "ftp_port": 21,
        "ftp_user": "usr",
        "ftp_pass": "pw",
        "seq_file": "scan.seq",
        "enable_iq": false
      }
    }
  }
}
```

### 2. Hardware Connection Setup

**For general AWG520 usage:**
```bash
# Use the setup script
python src/Controller/setup_awg520_connections.py

# Or manually copy the template
cp src/Controller/awg520_connection.template.json src/Controller/awg520_connection.json
```

**For experiment-specific setups:**
- Each experiment can have its own connection file
- Example: `src/Model/experiments/odmr_pulsed_connection.json`
- Experiments automatically use their specific connection files

**Customize for your lab:**
- Update connection descriptions to match your hardware
- Measure and set calibration delays
- Verify physical connections match the map

**Example connection customization:**
```json
{
  "channels": {
    "1": {
      "connection": "IQ_modulator_I_input",
      "calibration_delays": ["iq_delay"],
      "description": "Microwave I quadrature input to IQ modulator"
    }
  },
  "markers": {
    "ch1_marker2": {
      "connection": "laser_switch",
      "calibration_delays": ["laser_delay"],
      "description": "Laser on/off control signal"
    }
  },
  "calibration_delays": {
    "laser_delay": 45.0,  # Your measured value
    "iq_delay": 28.0,     # Your measured value
    "units": "ns"
  }
}
```

### 3. Running Unit Tests (No Hardware Required)
```bash
# Run all AWG520 tests
python -m pytest tests/test_awg520.py -v

# Run specific test categories
python -m pytest tests/test_awg520.py::TestAWG520Driver -v
python -m pytest tests/test_awg520.py::TestAWG520LaserControl -v
python -m pytest tests/test_awg520.py::TestAWG520Device -v
```

### 4. Running Hardware Tests (Real Hardware Required)

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

### 5. Running the Example Script
```bash
# Default connection (from config.json)
python examples/awg520_example.py

# Custom IP address
python examples/awg520_example.py --ip-address 192.168.1.100

# Custom connection settings
python examples/awg520_example.py --ip-address 192.168.1.100 --scpi-port 4000 --ftp-port 21
```

## Hardware Connection System

### Overview
The AWG520 now integrates with a comprehensive hardware connection system that provides:
- **Configurable connection mapping** for channels and markers
- **Automatic calibration delay compensation** for accurate timing
- **Connection validation** for different experiment types
- **Cross-lab compatibility** through template-based configuration

### Connection File Structure

**Template vs. Active Files:**
- **`awg520_connection.template.json`** - Template file (tracked in git)
- **`awg520_connection.json`** - Active connection file (NOT tracked, lab-specific)

**Setup Process:**
1. **Copy template to active file**
2. **Customize for your lab** (connections, delays, descriptions)
3. **Reference in config** (optional, for advanced setups)

### Connection Mapping Examples

**Channel Connections:**
```json
"channels": {
  "1": {
    "connection": "IQ_modulator_I_input",
    "type": "analog",
    "calibration_delays": ["iq_delay"],
    "description": "Microwave I quadrature input to IQ modulator",
    "voltage_range": "±1V",
    "impedance": "50Ω"
  },
  "2": {
    "connection": "IQ_modulator_Q_input",
    "type": "analog",
    "calibration_delays": ["iq_delay"],
    "description": "Microwave Q quadrature input to IQ modulator",
    "voltage_range": "±1V",
    "impedance": "50Ω"
  }
}
```

**Marker Connections:**
```json
"markers": {
  "ch1_marker2": {
    "connection": "laser_switch",
    "type": "digital",
    "calibration_delays": ["laser_delay"],
    "description": "Laser on/off control signal",
    "voltage": "3.3V",
    "impedance": "50Ω"
  },
  "ch2_marker2": {
    "connection": "counter_trigger",
    "type": "digital",
    "calibration_delays": ["counter_delay"],
    "description": "Counter/DAQ trigger signal",
    "voltage": "3.3V",
    "impedance": "50Ω"
  }
}
```

### Calibration Delays

**Purpose:** Calibration delays compensate for hardware timing differences to ensure pulses arrive at experiments at the intended times.

**Example:**
```json
"calibration_delays": {
  "laser_delay": 50.0,
  "mw_delay": 25.0,
  "iq_delay": 30.0,
  "counter_delay": 15.0,
  "units": "ns",
  "notes": "Delays represent time to shift events BACKWARD so they arrive at experiment at intended time"
}
```

**How It Works:**
- **User specifies:** Laser at 300ns
- **Hardware delay:** 50ns
- **Calibrated timing:** Laser at 250ns (300ns - 50ns)
- **Result:** Laser arrives at experiment at 300ns

### Experiment Type Validation

**Define experiment requirements:**
```json
"experiment_types": {
  "odmr": {
    "description": "ODMR experiment using IQ modulator and laser",
    "required_connections": ["ch1", "ch2", "ch1_marker2", "ch2_marker2"],
    "optional_connections": ["ch1_marker1", "ch2_marker1"]
  },
  "rabi": {
    "description": "Rabi oscillation experiment",
    "required_connections": ["ch1", "ch2", "ch1_marker2", "ch2_marker2"],
    "optional_connections": ["ch1_marker1", "ch2_marker1"]
  }
}
```

**Validate connections before experiments:**
```python
from src.Model.hardware_calibrator import HardwareCalibrator

calibrator = HardwareCalibrator(
    connection_file="src/Controller/awg520_connection.json",
    config_file="config.json"
)

# Validate connections for specific experiment types
result = calibrator.validate_connections("odmr")
print(f"Required: {result['required']}")
print(f"Available: {result['available']}")
print(f"Missing: {result['missing']}")

if result['missing']:
    print(f"⚠️  Missing connections: {result['missing']}")
else:
    print(f"✅ All required connections available")
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

## Hardware Calibration Integration

### Using HardwareCalibrator with AWG520

**Basic Setup:**
```python
from src.Model.hardware_calibrator import HardwareCalibrator
from src.Model.sequence import Sequence
from src.Model.pulses import GaussianPulse

# Create calibrator
calibrator = HardwareCalibrator(
    connection_file="src/Controller/awg520_connection.json",
    config_file="config.json"
)

# Create a sequence
seq = Sequence(2000)
pi2_pulse = GaussianPulse("pi_2_pulse", 100, sigma=25, amplitude=1.0)
laser_pulse = SquarePulse("laser_pulse", 200, amplitude=1.0)

seq.add_pulse(0, pi2_pulse)      # Microwave pulse at 0ns
seq.add_pulse(300, laser_pulse)   # Laser pulse at 300ns

# Apply hardware calibration
calibrated_seq = calibrator.calibrate_sequence(seq, sample_rate=1e9)

# Pulses are now shifted backward to compensate for delays
```

**Connection Validation:**
```python
# Validate connections for specific experiment types
result = calibrator.validate_connections("odmr")
print(f"Required: {result['required']}")
print(f"Available: {result['available']}")
print(f"Missing: {result['missing']}")

if result['missing']:
    print(f"⚠️  Missing connections: {result['missing']}")
else:
    print(f"✅ All required connections available")
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

#### Connection Template Issues
- Verify `awg520_connection.json` exists and is valid JSON
- Check that connection names match your physical setup
- Ensure calibration delays are measured and set correctly
- Validate connections before running experiments

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

## Complete Setup Workflow

### 1. Initial Setup
```bash
# Copy configuration templates
cp config.sample.json config.json
cp src/Controller/awg520_connection.template.json src/Controller/awg520_connection.json

# Edit config.json with your AWG520 IP address
# Edit awg520_connection.json with your lab's connections
```

### 2. Hardware Calibration
```bash
# Measure hardware delays with oscilloscope
# Update calibration_delays in awg520_connection.json
# Verify physical connections match connection map
```

### 3. Validation
```bash
# Test connection validation
python -c "
from src.Model.hardware_calibrator import HardwareCalibrator
calibrator = HardwareCalibrator('src/Controller/awg520_connection.json')
result = calibrator.validate_connections('odmr')
print(f'Validation result: {result}')
"
```

### 4. Testing
```bash
# Run unit tests
python -m pytest tests/test_awg520.py -v

# Run hardware tests (if hardware available)
export RUN_HARDWARE_TESTS=1
python -m pytest tests/test_awg520.py::TestAWG520Hardware -v

# Run example script
python examples/awg520_example.py
```

### 5. Production Use
```bash
# Start GUI (devices will load automatically from config.json)
python run_gui.py

# Use in experiments with automatic calibration
from src.Model.hardware_calibrator import HardwareCalibrator
calibrator = HardwareCalibrator()
calibrated_seq = calibrator.calibrate_sequence(my_sequence)
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

## Related Documentation

### Core Documentation
- **[Hardware Connection System](HARDWARE_CONNECTION_SYSTEM.md)** - Complete connection system documentation
- **[AWG520 + ADwin Testing](AWG520_ADWIN_TESTING.md)** - Hardware testing procedures
- **[Device Configuration](DEVICE_CONFIGURATION.md)** - Device configuration system

### Device Development
- **[Device Development](DEVICE_DEVELOPMENT.md)** - General device development guide
- **[Configuration Files](CONFIGURATION_FILES.md)** - Configuration file management
- **[Testing with Mock](TESTING_WITH_MOCK.md)** - Mock testing strategies

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