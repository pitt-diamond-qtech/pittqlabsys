# Hardware Connection System

## Overview

The hardware connection system provides a configurable way to map physical hardware connections to AWG channels and markers, and to apply calibration delays to ensure accurate timing in experiments.

## Architecture

```
User Sequence (ideal timing)
    ↓
SequenceBuilder (creates sequences)
    ↓
HardwareCalibrator (applies delays)
    ↓
AWG520SequenceOptimizer (hardware-specific)
    ↓
AWG520 (physical device)
```

## Connection File Structure

### Template vs. Active Files

- **`awg520_connection.template.json`** - Template file (tracked in git)
- **`awg520_connection.json`** - Active connection file (NOT tracked, lab-specific)

### File Setup Process

1. **Copy template to active file:**
   ```bash
   cp src/Controller/awg520_connection.template.json src/Controller/awg520_connection.json
   ```

2. **Customize for your lab:**
   - Update connection descriptions
   - Measure and set calibration delays
   - Verify physical connections match

3. **Reference in config:**
   ```json
   // config.lab.json
   {
     "awg520": {
       "connection_map": "src/Controller/awg520_connection.json"
     }
   }
   ```

## Connection File Format

### Channels Section
```json
"channels": {
  "1": {
    "connection": "IQ_modulator_I_input",
    "type": "analog",
    "calibration_delays": ["iq_delay"],
    "description": "Microwave I quadrature input to IQ modulator",
    "voltage_range": "±1V",
    "impedance": "50Ω"
  }
}
```

### Markers Section
```json
"markers": {
  "ch1_marker2": {
    "connection": "laser_switch",
    "type": "digital",
    "calibration_delays": ["laser_delay"],
    "description": "Laser on/off control signal",
    "voltage": "3.3V",
    "impedance": "50Ω"
  }
}
```

### Calibration Delays
```json
"calibration_delays": {
  "laser_delay": 50.0,
  "mw_delay": 25.0,
  "iq_delay": 30.0,
  "counter_delay": 15.0,
  "units": "ns",
  "notes": "Delays shift events BACKWARD to ensure arrival at intended time"
}
```

### Experiment Types
```json
"experiment_types": {
  "odmr": {
    "description": "ODMR experiment using IQ modulator and laser",
    "required_connections": ["ch1", "ch2", "ch1_marker2", "ch2_marker2"],
    "optional_connections": ["ch1_marker1", "ch2_marker1"]
  }
}
```

## Usage Examples

### Basic HardwareCalibrator Usage

```python
from src.Model.hardware_calibrator import HardwareCalibrator

# Option 1: Direct file paths
calibrator = HardwareCalibrator(
    connection_file="src/Controller/awg520_connection.json",
    config_file="config.lab.json"
)

# Option 2: Load from config only
calibrator = HardwareCalibrator(
    config_file="config.lab.json"  # Will auto-load connection file
)

# Option 3: Use defaults (for testing/development)
calibrator = HardwareCalibrator()
```

### Applying Calibration

```python
from src.Model.sequence import Sequence
from src.Model.pulses import GaussianPulse

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

### Connection Validation

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

## Calibration Process

### 1. Measure Hardware Delays
- **Laser Delay**: Time from laser trigger to actual laser output
- **Microwave Delay**: Time from AWG output to experiment
- **Counter Delay**: Time from counter trigger to actual counting
- **IQ Delay**: Time from AWG to IQ modulator output

### 2. Apply Delays
The system automatically shifts pulses backward in time:
- **Original timing**: User specifies ideal arrival times
- **Calibrated timing**: Pulses are shifted backward by delay amount
- **Result**: Pulses arrive at experiment at user-specified times

### 3. Example Timeline
```
User specifies: Laser at 300ns
Hardware delay: 50ns
Calibrated: Laser at 250ns (300ns - 50ns)
Result: Laser arrives at experiment at 300ns
```

## Configuration Integration

### config.lab.json Example
```json
{
  "awg520": {
    "ip_address": "192.168.1.100",
    "connection_map": "src/Controller/awg520_connection.json",
    "calibration_delays": {
      "laser_delay": 45.0,  # Lab-specific measured values
      "iq_delay": 28.0,
      "counter_delay": 12.0
    }
  }
}
```

### Environment-Specific Setup
- **Development**: Use default values or minimal config
- **Lab A**: Custom connection map and delays
- **Lab B**: Different connection map and delays
- **Production**: Full calibration and validation

## Best Practices

### 1. Connection File Management
- Keep templates in version control
- Never commit active connection files
- Document lab-specific modifications
- Use descriptive connection names

### 2. Calibration
- Measure delays with oscilloscope when possible
- Document measurement conditions
- Recalibrate after hardware changes
- Validate with known experiments

### 3. Validation
- Always validate connections before experiments
- Check required vs. optional connections
- Test with simple sequences first
- Monitor for timing issues

## Troubleshooting

### Common Issues

1. **Missing Connection File**
   ```
   FileNotFoundError: [Errno 2] No such file or directory: 'awg520_connection.json'
   ```
   **Solution**: Copy template and customize for your lab

2. **Invalid JSON Format**
   ```
   json.JSONDecodeError: Expecting ',' delimiter
   ```
   **Solution**: Validate JSON syntax, check for missing commas

3. **Missing Calibration Delays**
   ```
   KeyError: 'laser_delay'
   ```
   **Solution**: Add missing delays to connection file

4. **Connection Validation Failures**
   ```
   Missing connections: ['ch1_marker2']
   ```
   **Solution**: Update connection map or modify experiment requirements

### Debug Mode
```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Get calibration summary
summary = calibrator.get_calibration_summary()
print(f"Connection file: {summary['connection_file']}")
print(f"Total connections: {summary['total_connections']}")
```

## Extending the System

### Adding New Device Types
1. Create new connection template
2. Update HardwareCalibrator to handle device type
3. Add device-specific validation logic
4. Update documentation

### Adding New Experiment Types
1. Define required connections
2. Add to experiment_types section
3. Update validation logic
4. Test with real experiments

### Custom Calibration Methods
1. Extend HardwareCalibrator class
2. Override calibrate_sequence method
3. Implement custom delay logic
4. Add configuration options

## Related Documentation

- [Sequence Language and Pipeline](SEQUENCE_LANGUAGE_AND_PIPELINE.md)
- [AWG520 Device Development](DEVICE_DEVELOPMENT.md)
- [Configuration Files](CONFIGURATION_FILES.md)
- [Testing with Mock](TESTING_WITH_MOCK.md)
