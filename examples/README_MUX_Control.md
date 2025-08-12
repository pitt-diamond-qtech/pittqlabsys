# MUX Control Device

## Overview

The MUX Control Device is an Arduino-based trigger multiplexer controller that allows switching between three different trigger sources:

1. **Confocal trigger** - from MCL nanodrive
2. **ODMR trigger** - from PTS Arduino controller  
3. **Pulsed ESR trigger** - from AWG (Arbitrary Waveform Generator)

This device is essential for experiments that require switching between different measurement modes without manually reconfiguring hardware connections.

## Architecture

The MUX Control Device follows the project's device architecture patterns:

- **Inherits from `Device`** base class
- **Uses `Parameter` objects** for configuration
- **Implements probe system** for status monitoring
- **Provides both new and legacy interfaces** for backward compatibility

## Files

### Core Device
- **`src/Controller/mux_control.py`**: Main device implementation
  - `MUXControlDevice`: New device class with full functionality
  - `MUXControl`: Legacy class for backward compatibility

### Tests
- **`tests/test_mux_control.py`**: Comprehensive test suite
  - Unit tests with mocking
  - Hardware tests with automatic skipping
  - Legacy compatibility tests

### Examples
- **`examples/mux_control_example.py`**: Demonstration script
  - Connection management
  - Trigger selection demonstration
  - Sequence running
  - Error handling
- **`src/Controller/arduino/mux_control.ino`**: Arduino firmware
  - Complete Arduino sketch for 74HC4051 multiplexer control
  - Ready to upload to Arduino board

## Features

### Core Functionality
- **Serial Communication**: VISA-based communication with Arduino
- **Trigger Selection**: Switch between confocal, ODMR, and pulsed ESR triggers
- **Status Monitoring**: Real-time status and connection monitoring
- **Error Handling**: Robust error handling for communication issues
- **Hardware Information**: Detailed hardware mapping and Arduino firmware details
- **Connection Testing**: Test Arduino communication and get initialization messages

### Device Integration
- **Settings Management**: Configurable port, baudrate, and timeout
- **Probe System**: Status, port, and connection status probes
- **Auto-reconnection**: Automatic reconnection on port changes
- **Resource Cleanup**: Proper cleanup of VISA resources

### Backward Compatibility
- **Legacy Interface**: Maintains original `MUXControl` class interface
- **Same Methods**: `run()`, `close()` methods work as before
- **Easy Migration**: Drop-in replacement for existing code

## Quick Start

### Running Unit Tests (No Hardware Required)

```bash
# Run all MUX control tests
python -m pytest tests/test_mux_control.py -v

# Run specific test categories
python -m pytest tests/test_mux_control.py::TestMUXControlDevice -v
python -m pytest tests/test_mux_control.py::TestMUXControlLegacy -v
python -m pytest tests/test_mux_control.py::TestMUXControlHardware -v
```

### Running Hardware Tests (Real Hardware Required)

**On macOS/Linux:**
```bash
# Set environment variable and run hardware tests
export RUN_HARDWARE_TESTS=1
python -m pytest tests/test_mux_control.py::TestMUXControlHardware -v
```

**On Windows Command Prompt:**
```cmd
# Set environment variable and run hardware tests
set RUN_HARDWARE_TESTS=1
python -m pytest tests/test_mux_control.py::TestMUXControlHardware -v
```

**On Windows PowerShell:**
```powershell
# Set environment variable and run hardware tests
$env:RUN_HARDWARE_TESTS=1
python -m pytest tests/test_mux_control.py::TestMUXControlHardware -v
```

### Running the Example Script

```bash
# Use default COM3 port
python examples/mux_control_example.py

# Use custom port
python examples/mux_control_example.py --port COM5

# Use custom settings
python examples/mux_control_example.py --port COM4 --baudrate 115200 --timeout 10000

# Enable verbose logging
python examples/mux_control_example.py --verbose
```

## Usage Examples

### Basic Usage (New Interface)

```python
from src.Controller.mux_control import MUXControlDevice

# Create device with custom settings
settings = {
    'port': 'COM3',
    'baudrate': 9600,
    'timeout': 5000,
    'auto_connect': True
}

mux = MUXControlDevice(settings=settings)

# Select trigger sources
mux.select_trigger('confocal')    # Select confocal trigger
mux.select_trigger('odmr')       # Select ODMR trigger  
mux.select_trigger('pulsed')      # Select pulsed ESR trigger

# Check status
current = mux.get_current_selection()
probes = mux.read_probes()

# Get hardware information
hw_map = mux.get_hardware_mapping()
arduino_info = mux.get_arduino_info()

# Test connection
test_result = mux.test_connection()

# Cleanup
mux.cleanup()
```

### Legacy Usage (Backward Compatibility)

```python
from src.Controller.mux_control import MUXControl

# Use the old interface
mux = MUXControl('COM3')

# Select triggers (returns 0 on success, -1 on failure)
result = mux.run('confocal')  # Select confocal
result = mux.run('odmr')     # Select ODMR
result = mux.run('pulsed')    # Select pulsed ESR

# Close connection
mux.close()
```

### Integration with Experiments

```python
from src.Controller.mux_control import MUXControlDevice

class MyExperiment:
    def __init__(self):
        self.mux = MUXControlDevice({
            'port': 'COM3',
            'auto_connect': True
        })
    
    def run_confocal_scan(self):
        self.mux.select_trigger('confocal')
        # ... run confocal experiment
    
    def run_odmr(self):
        self.mux.select_trigger('odmr')
        # ... run ODMR experiment
    
    def run_pulsed_esr(self):
        self.mux.select_trigger('pulsed')
        # ... run pulsed ESR experiment
    
    def cleanup(self):
        self.mux.cleanup()
```

## Configuration

### Default Settings

```python
_DEFAULT_SETTINGS = Parameter([
    Parameter('port', 'COM3', str, 'Serial port for Arduino connection'),
    Parameter('baudrate', 9600, int, 'Serial baudrate'),
    Parameter('timeout', 5000, int, 'Serial timeout in milliseconds'),
    Parameter('auto_connect', True, bool, 'Automatically connect on initialization'),
])
```

### Available Probes

```python
_PROBES = {
    'status': 'Current MUX selection status',
    'port': 'Current serial port',
    'connected': 'Connection status to Arduino',
}
```

## Hardware Requirements

### Arduino Setup
- **Arduino Board**: Any Arduino-compatible board (Uno, Nano, Mega, etc.)
- **Firmware**: Custom firmware that responds to commands '1', '2', '3'
- **Connection**: USB-to-serial connection to host computer

### Multiplexer Hardware
- **Chip**: 74HC4051 8-Channel Multiplexer Breakout
- **Arduino Pin Connections**:
  - Pin 2 → S0 (Select line 0)
  - Pin 3 → S1 (Select line 1)  
  - Pin 4 → S2 (Select line 2)
  - Pin 5 → Z (Common I/O line)
- **Power**: 5V and GND from Arduino
- **Jumper**: JP1 closed (VEE connected to GND)

### Arduino Firmware
The complete Arduino firmware is provided in `src/Controller/arduino/mux_control.ino`. This sketch:

- Responds to commands `1`, `2`, `3` for trigger selection
- Sends "Input is in range" for valid commands and "Input out of range" for invalid ones
- Automatically initializes all select pins to LOW (Y0 selected by default)
- Sends initialization message: "Initialized...Enter 1 for Confocal, 2 for ODMR, or 3 for Pulsed."

**To upload the firmware:**
1. Open `mux_control.ino` in Arduino IDE
2. Select your Arduino board and port
3. Upload the sketch
4. Open Serial Monitor at 9600 baud to test communication

**Key Features:**
- Uses 74HC4051 multiplexer with Arduino pins 2, 3, 4 for selection
- Pin 5 (Z) is the common I/O line
- Binary encoding for efficient pin control
- Robust input validation with newline termination
- Commands: 1=confocal, 2=ODMR, 3=pulsed
- Commands: 1=confocal, 2=ODMR, 3=pulsed

## Error Handling

### Common Issues

1. **Port Not Found**
   - Check if Arduino is connected
   - Verify correct port name (COM3, /dev/ttyUSB0, etc.)
   - Ensure Arduino drivers are installed

2. **Communication Errors**
   - Check baudrate matches Arduino firmware
   - Verify Arduino is not in use by another program
   - Check USB cable and connections

3. **Permission Errors**
   - On Linux/macOS, ensure user has access to serial ports
   - May need to add user to `dialout` group (Linux)

### Debugging

```python
# Enable verbose logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Check connection status
if mux.is_connected:
    print("Device connected")
    print(f"Current selection: {mux.get_current_selection()}")
else:
    print("Device not connected")

# Read all probes
probes = mux.read_probes()
print(f"All probes: {probes}")
```

## Integration with Other Devices

### MCL Nanodrive (Confocal)
```python
# The MUX controller switches the trigger source for the MCL nanodrive
# When 'confocal' is selected, the nanodrive trigger is active
mux.select_trigger('confocal')
# Now run confocal scan experiment
```

### PTS Arduino (ODMR)
```python
# When 'odmr' is selected, the PTS Arduino trigger is active
mux.select_trigger('odmr')
# Now run ODMR experiment
```

### AWG (Pulsed ESR)
```python
# When 'pulsed' is selected, the AWG trigger is active
mux.select_trigger('pulsed')
# Now run pulsed ESR experiment
```

## Safety Features

- **Automatic Return**: Example script returns to confocal trigger after demonstrations
- **Error Recovery**: Graceful handling of communication errors
- **Resource Cleanup**: Automatic cleanup of VISA resources
- **Status Monitoring**: Real-time monitoring of device state

## Performance Considerations

- **Serial Communication**: Typical response time < 100ms
- **Trigger Switching**: Hardware switching time depends on multiplexer chip
- **Connection Overhead**: VISA connection establishment takes ~1-2 seconds
- **Resource Usage**: Minimal memory and CPU usage

## Troubleshooting

### Connection Issues
1. Verify Arduino is powered and connected
2. Check port name in Device Manager (Windows) or `ls /dev/tty*` (Linux/macOS)
3. Ensure no other program is using the serial port
4. Try different baudrates if communication is unstable

### Trigger Selection Issues
1. Verify Arduino firmware is correct
2. Check multiplexer chip connections
3. Monitor serial communication with Arduino IDE Serial Monitor
4. Ensure trigger outputs are properly connected to target devices

### Integration Issues
1. Check that trigger signals are compatible with target devices
2. Verify timing requirements are met
3. Ensure proper grounding between devices
4. Check for signal interference or noise

## Future Enhancements

- **Multiple Port Support**: Control multiple MUX controllers
- **Advanced Triggering**: Complex trigger sequences and timing
- **Network Control**: Remote control over network
- **Configuration Storage**: Save/load trigger configurations
- **Event Logging**: Detailed logging of all trigger changes
- **Safety Interlocks**: Hardware safety features for critical experiments 