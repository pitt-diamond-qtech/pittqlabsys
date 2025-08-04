# Hardware Tests for SG384 Microwave Generator

This document explains how to use the hardware integration tests for the SG384 microwave generator.

## Overview

The hardware tests in `tests/test_sg384_hardware.py` are designed to test the actual SG384 device when it's connected to your system. These tests use pytest markers to control when they run.

## Test Configuration

### Connection Settings

Before running hardware tests, you need to configure the connection settings in the test file:

```python
settings = {
    'connection_type': 'LAN',  # or 'GPIB' or 'RS232'
    'ip_address': '169.254.146.198',  # Modify for your SG384 IP
    'port': 5025,  # Modify for your SG384 port
    # For GPIB: 'visa_resource': 'GPIB0::20::INSTR'
    # For RS232: 'visa_resource': 'ASRL9::INSTR'
}
```

**Important**: Update these settings to match your SG384 configuration.

## Running Tests

### When SG384 is NOT connected (default)

To run all tests EXCEPT hardware tests:
```bash
pytest -m "not hardware"
```

To run only the regular unit tests:
```bash
pytest tests/test_sg384.py
```

### When SG384 IS connected

To run ONLY the hardware tests:
```bash
pytest tests/test_sg384_hardware.py -m hardware -v
```

To run ALL tests including hardware:
```bash
pytest -v
```

## Available Hardware Tests

The hardware tests cover:

1. **Connection Test** - Verifies device identification
2. **Frequency Setting** - Tests setting and reading frequency (2.5 GHz)
3. **Power Setting** - Tests setting and reading power (-10 dBm)
4. **Phase Setting** - Tests setting and reading phase (45°)
5. **Output Control** - Tests enabling/disabling RF output
6. **Modulation Settings** - Tests modulation type and function settings
7. **Mapping Functions** - Tests that mapping dictionaries work with real hardware
8. **Read Probes** - Tests reading probe values from hardware
9. **Update Method** - Tests the update method with real hardware
10. **Error Handling** - Tests error handling with invalid parameters

## Safety Notes

⚠️ **Important Safety Considerations**:

- The hardware tests will **enable the RF output** during testing
- Tests use frequencies around 2.5-3.0 GHz
- Power levels are set to -10 to -5 dBm (low power)
- Always ensure your setup can handle these parameters safely
- The tests include small delays to allow the device to settle

## Troubleshooting

### Tests hang/timeout
- Check your SG384 IP address and port settings
- Ensure the SG384 is powered on and connected to the network
- Verify firewall settings allow the connection

### Connection refused errors
- Check if the SG384 is accessible on the specified IP/port
- Try pinging the device IP address
- Verify VISA drivers are installed (for GPIB/RS232 connections)

### Import errors
- Ensure the virtual environment is activated: `source venv/bin/activate`
- Check that all dependencies are installed: `pip install -r requirements.txt`

## Example Usage

```bash
# Activate virtual environment
source venv/bin/activate

# Run all tests except hardware (safe for development)
pytest -m "not hardware" -v

# When SG384 is connected, run hardware tests
pytest tests/test_sg384_hardware.py -m hardware -v

# Run specific hardware test
pytest tests/test_sg384_hardware.py::test_sg384_frequency_setting -v
```

## Test Output

When hardware tests run successfully, you'll see output like:
```
✓ Connected to SG384: Stanford Research Systems,SG384,12345,1.0.0
✓ Frequency probe: 2.500 GHz
✓ Amplitude probe: -10.0 dBm
✓ Phase probe: 45.0°
```

When hardware tests are skipped (no device connected), you'll see:
```
10 deselected
``` 