# Device Configuration System

## Overview

The new device configuration system allows you to configure all your lab hardware in a single `config.json` file. This eliminates the need for hardcoded device settings and makes your experiments truly cross-lab compatible.

## Benefits

- **Cross-lab compatibility**: Same experiments work in different labs
- **Easy maintenance**: Change IP addresses, COM ports, etc. in config, not code
- **Centralized configuration**: All device settings in one place
- **No more hardcoded settings**: Devices automatically load with correct parameters

## How It Works

1. **GUI Startup**: When the GUI starts, it automatically loads devices from `config.json`
2. **Device Instantiation**: Devices are created with their specific settings from config
3. **Export Tool**: Uses the GUI's pre-loaded devices for experiment conversion
4. **Cross-lab**: Different labs can have different `config.json` files

## Configuration Format

### Basic Structure

```json
{
    "devices": {
        "device_name": {
            "class": "DeviceClassName",
            "filepath": "src/Controller/device_file.py",
            "settings": {
                "parameter1": "value1",
                "parameter2": "value2"
            }
        }
    }
}
```

### Example Configurations

#### SG384 Microwave Generator

```json
"sg384": {
    "class": "SG384Generator",
    "filepath": "src/Controller/sg384.py",
    "settings": {
        "ip_address": "192.168.2.217",
        "port": 5025,
        "timeout": 5.0
    }
}
```

#### ADwin Device

```json
"adwin": {
    "class": "AdwinGoldDevice",
    "filepath": "src/Controller/adwin_gold.py",
    "settings": {
        "board_number": 1
    }
}
```

#### NanoDrive

```json
"nanodrive": {
    "class": "MCLNanoDrive",
    "filepath": "src/Controller/nanodrive.py",
    "settings": {
        "serial_port": "COM3"
    }
}
```

## Setup Instructions

### 1. Copy Sample Config

```bash
cp config.sample.json config.json
```

### 2. Modify for Your Lab

Edit `config.json` and update:
- IP addresses for network devices
- COM ports for serial devices
- Board numbers for ADwin devices
- Any other device-specific parameters

### 3. Test Device Loading

Start the GUI and check the console output:
```
🔧 Loading 3 devices from config...
  🔧 Loading device: sg384
  ✅ Successfully loaded: sg384
  🔧 Loading device: adwin
  ✅ Successfully loaded: adwin
  🔧 Loading device: nanodrive
  ✅ Successfully loaded: nanodrive
✅ Device loading complete. Loaded: 3, Failed: 0
```

## Device Parameters

### Common Parameters

- **Network devices**: `ip_address`, `port`, `timeout`
- **Serial devices**: `serial_port`, `baud_rate`
- **ADwin devices**: `board_number`
- **All devices**: `name` (optional, defaults to device name in config)

### Device-Specific Parameters

Each device class may have additional parameters. Check the device class documentation or source code for available options.

## Troubleshooting

### Device Loading Fails

1. **Check file paths**: Ensure `filepath` points to correct Python file
2. **Check class names**: Ensure `class` matches the actual class name in the file
3. **Check imports**: Ensure the device module can be imported
4. **Check settings**: Ensure device-specific settings are valid

### Common Errors

- **ImportError**: Check filepath and class name
- **AttributeError**: Check if class name exists in module
- **TypeError**: Check if device class inherits from Device
- **ConnectionError**: Check device-specific settings (IP, COM port, etc.)

## Migration from Old System

### Before (Hardcoded)

```python
# Old way - hardcoded in device classes
class SG384Generator(Device):
    _DEFAULT_SETTINGS = {
        'ip_address': '192.168.2.217',  # Hardcoded!
        'port': 5025
    }
```

### After (Configurable)

```python
# New way - configurable via config.json
class SG384Generator(Device):
    _DEFAULT_SETTINGS = {
        'ip_address': 'localhost',  # Default fallback
        'port': 5025
    }
    
    def __init__(self, name=None, settings=None):
        super().__init__(name, settings)
        # Settings from config.json override defaults
```

## Advanced Features

### Dynamic Device Loading

The system automatically:
- Loads devices at GUI startup
- Provides devices to experiments
- Handles device failures gracefully
- Logs all device operations

### Configuration Validation

- Checks file paths exist
- Validates class names
- Ensures device inheritance
- Reports detailed error messages

## Future Enhancements

- **Role-based device specification**: Experiments specify device capabilities, not concrete classes
- **Device factory pattern**: Dynamic device instantiation based on configuration
- **Hardware capability detection**: Automatic detection of available hardware
- **Configuration templates**: Pre-built configs for common lab setups

## Support

For issues or questions:
1. Check the console output for detailed error messages
2. Verify your `config.json` format matches the examples
3. Ensure device files are in the correct locations
4. Check that device classes inherit from the Device base class
