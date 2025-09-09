# Device Configuration System

## Overview

The new device configuration system allows you to configure all your lab hardware in a single `config.json` file. This eliminates the need for hardcoded device settings and makes your experiments truly cross-lab compatible.

## File Structure

The system uses a simplified, clean structure:

- **`config.sample.json`** - Easy-to-copy sample configuration with all devices (production/lab use)
- **`src/config.dev.template.json`** - Development machine configuration (mock devices, no hardware)
- **`src/config.template.json`** - Base template with all device configurations and Windows paths

**No more confusing multiple templates!** Just copy the appropriate file and modify for your environment.

## Benefits

- **Cross-lab compatibility**: Same experiments work in different labs
- **Easy maintenance**: Change IP addresses, COM ports, etc. in config, not code
- **Centralized configuration**: All device settings in one place
- **No more hardcoded settings**: Devices automatically load with correct parameters
- **Configurable data paths**: Experiments use configured data folders instead of hardcoded paths

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

#### AWG520 Arbitrary Waveform Generator

```json
"awg520": {
    "class": "AWG520Device",
    "filepath": "src/Controller/awg520.py",
    "settings": {
        "ip_address": "172.17.39.2",
        "scpi_port": 4000,
        "ftp_port": 21,
        "ftp_user": "usr",
        "ftp_pass": "pw",
        "seq_file": "scan.seq",
        "enable_iq": false
    }
}
```

#### MUX Control (Arduino-based Trigger Multiplexer)

```json
"mux_control": {
    "class": "MUXControlDevice",
    "filepath": "src/Controller/mux_control.py",
    "settings": {
        "port": "COM3",
        "baudrate": 9600,
        "timeout": 5000,
        "auto_connect": true
    }
}
```

## Setup Instructions

### 1. Copy Sample Config

```bash
# For production/lab use:
cp config.sample.json config.json

# For development use:
cp src/config.dev.template.json config.json
```

### 2. Modify for Your Lab

Edit `config.json` and update:
- IP addresses for network devices
- COM ports for serial devices
- Board numbers for ADwin devices
- Any other device-specific parameters

**Note**: The base template includes Windows-specific paths (`D:/Duttlab/Experiments/...`). 
For other operating systems, the GUI will automatically detect and adjust paths.

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
- **Serial devices**: `serial_port`, `baudrate`, `timeout`
- **ADwin devices**: `board_number`
- **AWG devices**: `scpi_port`, `ftp_port`, `ftp_user`, `ftp_pass`, `seq_file`
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

## Path Configuration

### Data Folder Configuration

Experiments now use configurable data paths instead of hardcoded paths. This ensures cross-platform compatibility and allows different labs to use different drive letters or folder structures.

#### Configuration Structure

Add a `paths` section to your `config.json`:

```json
{
    "paths": {
        "data_folder": "D:/Duttlab/Experiments/AQuISS_default_save_location/data",
        "probes_folder": "D:/Duttlab/Experiments/AQuISS_default_save_location/probes_auto_generated",
        "device_folder": "D:/Duttlab/Experiments/AQuISS_default_save_location/devices_auto_generated",
        "experiments_folder": "D:/Duttlab/Experiments/AQuISS_default_save_location/experiments_auto_generated",
        "probes_log_folder": "D:/Duttlab/Experiments/AQuISS_default_save_location/aqs_tmp",
        "workspace_config_dir": "D:/Duttlab/Experiments/AQuISS_default_save_location/workspace_configs"
    }
}
```

#### Helper Functions

The system provides helper functions to access configured paths:

```python
from src.core.helper_functions import get_configured_data_folder, get_configured_confocal_scans_folder

# Get the configured data folder
data_folder = get_configured_data_folder()
# Returns: Path("D:/Duttlab/Experiments/AQuISS_default_save_location/data")

# Get confocal scans subfolder
confocal_folder = get_configured_confocal_scans_folder()
# Returns: Path("D:/Duttlab/Experiments/AQuISS_default_save_location/data/confocal_scans")
```

#### Experiment Integration

Experiments automatically use configured paths:

```python
# In experiment classes
Parameter('3D_scan',
    [Parameter('enable', False, bool, 'T/F to enable 3D scan'),
     Parameter('folderpath', str(get_configured_confocal_scans_folder()), str, 
               'folder location to save images at each z-value')])
```

#### Fallback Behavior

If `config.json` is missing or doesn't contain the `paths` section, the system falls back to:
- **Default data folder**: `~/Experiments/AQuISS_default_save_location/data`
- **Default confocal folder**: `~/Experiments/AQuISS_default_save_location/data/confocal_scans`

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
