# Device Development Guide

This guide explains how to create new device drivers for AQuISS.

> **📚 Documentation Index**: For a complete overview of all documentation, see [README.md](README.md)

## Related Guides

- **[Development Guide](DEVELOPMENT_GUIDE.md)** - General development practices and standards
- **[Experiment Development Guide](EXPERIMENT_DEVELOPMENT.md)** - Creating scientific experiments
- **[Recent Updates](RECENT_UPDATES.md)** - Latest bug fixes and new features

## Overview

Device drivers in AQuISS provide a standardized interface for controlling hardware instruments. All devices inherit from the base `Device` class and implement a common interface.

## Device Class Structure

### Required Components

1. **Class Definition**: Inherit from `Device`
2. **Default Settings**: Define `_DEFAULT_SETTINGS` (see inheritance patterns below)
3. **Probes**: Define `_PROBES` for readable values
4. **Required Methods**: Implement `update()`, `read_probes()`, `is_connected`

### Parameter Inheritance Patterns

When creating device subclasses, especially those that inherit from intermediate base classes (like `MicrowaveGeneratorBase`), you should use the inheritance pattern to ensure all parent parameters are included:

```python
class MyDevice(MicrowaveGeneratorBase):
    _DEFAULT_SETTINGS = Parameter(
        # Inherit all base class settings and add device-specific ones
        MicrowaveGeneratorBase._get_base_settings() + [
        # Device-specific overrides (these will override base class defaults)
        Parameter('ip_address', '192.168.1.100', str, 'IP for LAN'),
        # Device-specific settings
        Parameter('my_specific_param', 42, int, 'My device-specific parameter'),
        # ... more device-specific parameters
    ])
```

**Why use this pattern?**
- **Prevents KeyError**: Ensures all parent class parameters are inherited
- **Maintains compatibility**: GUI and other components expect all base parameters
- **Future-proof**: Automatically includes new parameters added to base classes
- **Self-documenting**: Makes inheritance explicit and clear

### Parameter List Concatenation Pattern

The `Parameter` class supports a powerful pattern for combining multiple parameter lists using list concatenation. This pattern was implemented in the original codebase but was refined through 3 phases of improvements (see `PARAMETER_CLASS_SUMMARY.md` and `PARAMETER_CLASS_ANALYSIS.md`).

**How it works:**
```python
class MyDevice(MicrowaveGeneratorBase):
    _DEFAULT_SETTINGS = Parameter(
        # Concatenate base class parameters with device-specific parameters
        MicrowaveGeneratorBase._get_base_settings() + [
        # Device-specific parameters
        Parameter('device_specific_param', 42, int, 'My parameter'),
        Parameter('another_param', 'value', str, 'Another parameter'),
        # ... more parameters
    ])
```

**Key behavior:**
- The `Parameter` constructor **flattens** the list of `Parameter` objects into a single `Parameter` object
- Each `Parameter` object in the list is processed and its individual parameters are extracted
- All parameters end up in the final `Parameter` object at the same level
- This is **not** a nested structure - it's a flattened collection

**Example of what happens internally:**
```python
# Input: List of Parameter objects
base_params = [Parameter('freq', 1e9, float, 'Frequency'), Parameter('power', -10, float, 'Power')]
device_params = [Parameter('custom', 42, int, 'Custom')]

# Concatenation
all_params = base_params + device_params  # [Parameter('freq', ...), Parameter('power', ...), Parameter('custom', ...)]

# Parameter constructor flattens this into:
result = Parameter(all_params)
# Result contains: {'freq': 1e9, 'power': -10, 'custom': 42}
# NOT: {'freq': 1e9, 'power': -10, 'custom': {'custom': 42}}
```

**Why this pattern is powerful:**
- **Composable**: Easy to combine parameters from multiple sources
- **Maintainable**: Base class changes automatically propagate
- **Flexible**: Can add, remove, or override parameters easily
- **Type-safe**: All parameters maintain their validation and metadata
- **Performance**: Efficient flattening without deep nesting

**Historical context:**
This pattern was implemented in the original codebase (2020-07-27) but had some issues with nested structures and validation that were addressed through 3 phases of improvements:
1. **Phase 1**: Fixed core nested parameter creation and validation
2. **Phase 2**: Enhanced unit functionality and pint integration  
3. **Phase 3**: Performance improvements and advanced features

The pattern is now robust and widely used throughout the codebase for device parameter inheritance.

### Path Management

The base `Experiment` class provides robust path management with sensible defaults:

```python
# Get configured output directory for this experiment
output_dir = self.get_output_dir()  # Uses configured data folder + experiment name

# Get output directory with subfolder
output_dir = self.get_output_dir("subfolder")  # data_folder/experiment_name/subfolder

# Get config file path (tries experiment dir first, then project root)
config_path = self.get_config_path("my_config.json")
```

**Key Features:**
- **Automatic**: All experiments get configurable paths by default
- **Safe**: Handles special characters, empty names, and filesystem issues
- **Consistent**: Same path structure across all experiments
- **Flexible**: Can still customize per experiment if needed
- **Future-proof**: New experiments automatically get proper path handling

**Path Normalization:**
- Special characters (`/`, `\`, `*`, `?`, etc.) are replaced with underscores
- Empty experiment names fall back to class name
- All paths are created automatically if they don't exist
- Cross-platform compatible (handles Windows/macOS/Linux differences)

**Customization Examples:**
```python
class MyCustomExperiment(Experiment):
    def get_output_dir(self, subfolder=None):
        """Override to add custom logic."""
        # Call parent method for basic functionality
        base_dir = super().get_output_dir(subfolder)
        
        # Add custom logic
        if self.settings.get('use_timestamp', False):
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            return base_dir / f"run_{timestamp}"
        
        return base_dir
    
    def get_special_data_path(self):
        """Custom method for experiment-specific needs."""
        # Use base method as foundation
        base_dir = self.get_output_dir()
        
        # Add experiment-specific logic
        return base_dir / "special_data" / f"version_{self.settings.get('version', '1.0')}"
```

**Migration Strategy:**
- **Existing experiments**: No changes required - continue working as before
- **New experiments**: Get benefits automatically by inheriting from base class
- **Gradual adoption**: Can migrate existing experiments over time
- **Backward compatible**: Existing path handling still works

### Design Philosophy: Foundation + Flexibility

The enhanced base experiment class follows a **foundation + flexibility** approach:

**Base Class Provides:**
- **Sensible defaults** for common use cases
- **Robust path handling** (special characters, empty names, etc.)
- **Configurable paths** that respect the system configuration
- **Consistent behavior** across all experiments

**Individual Experiments Can:**
- **Override** the path methods if they need custom logic
- **Extend** the base functionality for specific needs
- **Use their own** path handling entirely if required
- **Mix and match** - use base methods for some paths, custom for others

**Benefits:**
- **Consistency**: Most experiments get good defaults
- **Flexibility**: Can customize when needed
- **Maintainability**: Common logic centralized
- **Gradual adoption**: No forced changes
- **Future-proof**: Easy to enhance base class

### Experiment Development

When creating new experiments, inherit from the base `Experiment` class to get automatic path management:

```python
from src.core import Experiment, Parameter

class MyNewExperiment(Experiment):
    """
    Description of what this experiment does.
    """
    
    _DEFAULT_SETTINGS = [
        Parameter('param1', 42, int, 'Description of parameter 1'),
        Parameter('param2', 'hello', str, 'Description of parameter 2'),
        # ... more parameters
    ]
    
    _DEVICES = {
        'device1': 'device1',  # Required devices
        'device2': 'device2',
    }
    
    _EXPERIMENTS = {}  # Sub-experiments if any
    
    def __init__(self, devices, experiments=None, name=None, settings=None, log_function=None, data_path=None):
        super().__init__(name, settings=settings, sub_experiments=experiments, 
                        devices=devices, log_function=log_function, data_path=data_path)
        
        # Get device instances
        self.device1 = self.devices['device1']['instance']
        self.device2 = self.devices['device2']['instance']
    
    def _function(self):
        """Main experiment logic."""
        # Use automatic path management
        output_dir = self.get_output_dir()
        config_path = self.get_config_path()
        
        # Your experiment logic here
        pass
```

**Key Benefits:**
- **Automatic path handling**: No need to manually manage output directories
- **Configurable paths**: Respects system configuration automatically
- **Safe file operations**: Handles edge cases and special characters
- **Consistent structure**: All experiments follow the same path patterns

### Example Template

```python
from src.core import Device, Parameter
from typing import Dict, Any, Optional

class MyDevice(Device):
    """
    Description of what this device does.
    
    This device controls [specific hardware] and provides [specific functionality].
    """
    
    _DEFAULT_SETTINGS = [
        Parameter('frequency', 1e9, float, 'Frequency in Hz'),
        Parameter('power', 0.0, float, 'Power in dBm'),
        Parameter('output_enabled', False, bool, 'Enable/disable output'),
        Parameter('advanced_settings', [
            Parameter('mode', 'continuous', ['continuous', 'pulsed'], 'Operation mode'),
            Parameter('pulse_width', 1e-6, float, 'Pulse width in seconds')
        ])
    ]
    
    _PROBES = {
        'temperature': 'Device temperature in Celsius',
        'status': 'Device status string',
        'error_code': 'Last error code from device',
        'output_power': 'Current output power in dBm'
    }
    
    def __init__(self, name: Optional[str] = None, settings: Optional[Dict[str, Any]] = None):
        """
        Initialize the device.
        
        Args:
            name: Optional device name
            settings: Optional initial settings
        """
        super().__init__(name, settings)
        self._is_connected = False
        self._device_handle = None
        
    def connect(self) -> bool:
        """
        Establish connection to the device.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Implement device-specific connection logic
            # self._device_handle = device_connection_function()
            self._is_connected = True
            return True
        except Exception as e:
            self.log(f"Connection failed: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from the device."""
        if self._device_handle:
            # Implement device-specific disconnection logic
            pass
        self._is_connected = False
        self._device_handle = None
    
    def update(self, settings: Dict[str, Any]):
        """
        Update device settings.
        
        Args:
            settings: Dictionary of settings to update
        """
        Device.update(self, settings)
        
        for key, value in settings.items():
            if key == 'frequency':
                self._set_frequency(value)
            elif key == 'power':
                self._set_power(value)
            elif key == 'output_enabled':
                self._set_output_enabled(value)
    
    def read_probes(self, key: str) -> Any:
        """
        Read a probe value from the device.
        
        Args:
            key: Probe name to read
            
        Returns:
            The probe value
            
        Raises:
            ValueError: If probe key is not recognized
        """
        if key not in self._PROBES:
            raise ValueError(f"Unknown probe: {key}")
        
        if not self._is_connected:
            return None
            
        if key == 'temperature':
            return self._read_temperature()
        elif key == 'status':
            return self._read_status()
        elif key == 'error_code':
            return self._read_error_code()
        elif key == 'output_power':
            return self._read_output_power()
    
    @property
    def is_connected(self) -> bool:
        """Check if device is connected and responsive."""
        return self._is_connected and self._check_device_health()
    
    # Device-specific private methods
    def _set_frequency(self, freq: float):
        """Set device frequency."""
        if self._is_connected:
            # Implement frequency setting logic
            pass
    
    def _set_power(self, power: float):
        """Set device power."""
        if self._is_connected:
            # Implement power setting logic
            pass
    
    def _set_output_enabled(self, enabled: bool):
        """Enable/disable device output."""
        if self._is_connected:
            # Implement output control logic
            pass
    
    def _read_temperature(self) -> float:
        """Read device temperature."""
        # Implement temperature reading logic
        return 25.0  # Placeholder
    
    def _read_status(self) -> str:
        """Read device status."""
        # Implement status reading logic
        return "OK"  # Placeholder
    
    def _read_error_code(self) -> int:
        """Read device error code."""
        # Implement error code reading logic
        return 0  # Placeholder
    
    def _read_output_power(self) -> float:
        """Read current output power."""
        # Implement power reading logic
        return self.settings['power']  # Placeholder
    
    def _check_device_health(self) -> bool:
        """Check if device is responding properly."""
        # Implement health check logic
        return True  # Placeholder
```

## Parameter Types

### Basic Parameters

```python
Parameter('name', default_value, type, description)
```

### Parameter with Units

```python
Parameter('frequency', 1e9, float, 'Frequency', units='Hz')
```

### Parameter with Choices

```python
Parameter('mode', 'continuous', ['continuous', 'pulsed'], 'Operation mode')
```

### Nested Parameters

```python
Parameter('advanced_settings', [
    Parameter('sub_param1', 1.0, float, 'Sub-parameter 1'),
    Parameter('sub_param2', 'value', str, 'Sub-parameter 2')
])
```

## Best Practices

### 1. Error Handling

Always implement proper error handling:

```python
def update(self, settings):
    try:
        Device.update(self, settings)
        # Update logic
    except Exception as e:
        self.log(f"Update failed: {e}")
        raise
```

### 2. Connection Management

Implement robust connection handling:

```python
def connect(self):
    if self._is_connected:
        return True
    
    try:
        # Connection logic
        self._is_connected = True
        return True
    except Exception as e:
        self.log(f"Connection failed: {e}")
        return False
```

### 3. Resource Cleanup

Always clean up resources:

```python
def disconnect(self):
    try:
        # Disconnection logic
        pass
    finally:
        self._is_connected = False
        self._device_handle = None
```

### 4. Logging

Use the built-in logging system:

```python
def some_method(self):
    self.log("Starting operation")
    # Operation logic
    self.log("Operation completed")
```

## Testing Your Device

Create a test file in the `tests/` directory:

```python
import pytest
from src.Controller.my_device import MyDevice

class TestMyDevice:
    def setup_method(self):
        self.device = MyDevice()
    
    def test_initialization(self):
        assert self.device.name == "MyDevice"
        assert self.device.settings['frequency'] == 1e9
    
    def test_connection(self):
        # Test connection logic
        pass
    
    def test_update(self):
        # Test parameter updates
        pass
    
    def test_probes(self):
        # Test probe reading
        pass
```

## Registering Your Device

Add your device to the device registry in `src/Controller/__init__.py`:

```python
from .my_device import MyDevice

_DEVICE_REGISTRY = {
    # ... existing devices ...
    "my_device": MyDevice,
}
```

## Common Patterns

### 1. Hardware Communication

```python
import serial
import pyvisa

class SerialDevice(Device):
    def connect(self):
        try:
            self._serial = serial.Serial(self.settings['port'], 
                                       self.settings['baudrate'])
            return True
        except Exception as e:
            self.log(f"Serial connection failed: {e}")
            return False
```

### 2. VISA Communication

```python
import pyvisa

class VISADevice(Device):
    def connect(self):
        try:
            rm = pyvisa.ResourceManager()
            self._device = rm.open_resource(self.settings['address'])
            return True
        except Exception as e:
            self.log(f"VISA connection failed: {e}")
            return False
```

### 3. Thread-Safe Operations

```python
from threading import Lock

class ThreadSafeDevice(Device):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._lock = Lock()
    
    def update(self, settings):
        with self._lock:
            super().update(settings)
```

## Troubleshooting

### Common Issues

1. **Connection Timeouts**: Implement timeout handling
2. **Resource Conflicts**: Use proper resource management
3. **Thread Safety**: Use locks for multi-threaded access
4. **Error Recovery**: Implement automatic reconnection

### Debugging Tips

1. Use the logging system extensively
2. Test with hardware simulation when possible
3. Implement comprehensive error messages
4. Use unit tests to verify functionality

## Resources

- [Device Base Class Documentation](../src/core/device.py)
- [Parameter Class Documentation](../src/core/parameter.py)
- [Example Device Implementation](../src/Controller/example_device.py)
- [Testing Framework Documentation](../tests/) 