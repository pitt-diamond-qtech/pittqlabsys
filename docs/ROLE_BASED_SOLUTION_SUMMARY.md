# Role-Based Experiment Solution: Complete Implementation Summary

## Problem Solved

You asked: *"Can we brainstorm making this code more portable across different experiments that use different devices for microwave, data acquisition and scanning?"*

The current issue was that experiments had hardcoded device classes:

```python
# Current Problem - Hardcoded Devices
class ODMRExperiment(Experiment):
    _DEVICES = {
        'microwave': SG384Generator,  # Hardcoded to specific device
        'adwin': ADwinGold,           # Hardcoded to specific device  
        'nanodrive': MCLNanoDrive     # Hardcoded to specific device
    }
```

This made experiments:
- **Non-portable** between labs with different hardware
- **Tightly coupled** to specific device implementations
- **Difficult to maintain** when supporting multiple hardware configurations

## Solution Implemented: Role-Based Device Selection

We've implemented a complete role-based system that makes experiments hardware-agnostic and portable.

### 1. Device Roles System (`src/core/device_roles.py`)

**Core Concept**: Define abstract interfaces for device capabilities rather than specific device classes.

```python
class MicrowaveGeneratorRole(DeviceRole):
    def get_required_methods(self) -> List[str]:
        return [
            'set_frequency', 'set_power', 'set_phase',
            'output_on', 'output_off', 'enable_modulation',
            'disable_modulation', 'set_modulation_type', 'set_modulation_depth'
        ]
    
    def get_required_parameters(self) -> List[str]:
        return ['frequency', 'power', 'phase', 'amplitude', 'connection_type', 'visa_resource']
```

**Device Role Manager**: Manages which device classes can fulfill which roles:

```python
# Register devices for roles
device_role_manager.register_device_for_role('microwave_generator', 'sg384', SG384Generator)
device_role_manager.register_device_for_role('microwave_generator', 'windfreak_synth_usbii', WindfreakSynthUSBII)
device_role_manager.register_device_for_role('data_acquisition', 'adwin', ADwinGold)
device_role_manager.register_device_for_role('data_acquisition', 'nidaq', NIDAQ)
```

### 2. Role-Based Experiment Base Class (`src/core/role_based_experiment.py`)

**Core Concept**: Experiments specify required roles rather than specific devices.

```python
class RoleBasedExperiment(Experiment):
    # Define required device roles (hardware-agnostic)
    _REQUIRED_DEVICE_ROLES = {
        'microwave': 'microwave_generator',
        'daq': 'data_acquisition', 
        'scanner': 'scanner'
    }
    
    # Default device types (can be overridden by configuration)
    _DEFAULT_DEVICE_TYPES = {
        'microwave': 'sg384',
        'daq': 'adwin',
        'scanner': 'nanodrive'
    }
```

### 3. Configuration System (`src/core/experiment_config.py`)

**Core Concept**: Device selection specified in configuration files, not code.

```json
{
    "experiment_name": "odmr_experiment",
    "device_config": {
        "microwave": "sg384",
        "daq": "adwin", 
        "scanner": "nanodrive"
    },
    "settings": {
        "frequency_range": {
            "start": 2.7e9,
            "stop": 3.0e9,
            "steps": 100
        }
    }
}
```

### 4. Example Role-Based ODMR Experiment (`src/Model/experiments/odmr_experiment_role_based.py`)

**Core Concept**: Same experiment code works with any hardware configuration.

```python
class RoleBasedODMRExperiment(RoleBasedExperiment):
    def _function(self):
        # Access devices by role name (hardware-agnostic)
        microwave = self.devices['microwave']['instance']
        daq = self.devices['daq']['instance']
        scanner = self.devices.get('scanner', {}).get('instance')
        
        # Use role-based interface - works with any device implementing the role
        microwave.set_frequency(2.87e9)
        microwave.set_power(-10.0)
        microwave.output_on()
        
        # Same code works with SG384, Windfreak, or any other microwave generator!
```

## Key Benefits Achieved

### 1. **Hardware Portability**

**Before**: Different labs needed different experiment code
```python
# Pitt Lab version
class ODMRExperiment(Experiment):
    _DEVICES = {'microwave': SG384Generator, 'daq': ADwinGold}

# MIT Lab version  
class ODMRExperiment(Experiment):
    _DEVICES = {'microwave': WindfreakSynthUSBII, 'daq': NIDAQ}
```

**After**: Same experiment code works everywhere
```python
# Same code, different configurations
experiment1 = RoleBasedODMRExperiment(device_config={'microwave': 'sg384', 'daq': 'adwin'})
experiment2 = RoleBasedODMRExperiment(device_config={'microwave': 'windfreak_synth_usbii', 'daq': 'nidaq'})
```

### 2. **Configuration-Driven Selection**

**Lab-Specific Configurations**:
```python
# Pitt Lab config
pitt_config = {
    'device_config': {
        'microwave': 'sg384',
        'daq': 'adwin',
        'scanner': 'nanodrive'
    }
}

# MIT Lab config
mit_config = {
    'device_config': {
        'microwave': 'windfreak_synth_usbii',
        'daq': 'nidaq',
        'scanner': 'galvo_scanner'
    }
}

# Same experiment, different hardware
pitt_experiment = create_experiment_from_config(RoleBasedODMRExperiment, 'odmr_experiment', lab_name='pitt_lab')
mit_experiment = create_experiment_from_config(RoleBasedODMRExperiment, 'odmr_experiment', lab_name='mit_lab')
```

### 3. **Easy Testing and Development**

**Mock Devices for Testing**:
```python
# Test with mock devices
experiment = RoleBasedODMRExperiment(
    device_config={
        'microwave': 'mock_microwave',
        'daq': 'mock_daq',
        'scanner': 'mock_scanner'
    }
)
```

### 4. **Extensibility**

**Adding New Devices**: Just implement the role interface and register:
```python
class NewMicrowaveGenerator(Device):
    def set_frequency(self, freq): ...
    def set_power(self, power): ...
    # ... implement all required methods

# Register for role
device_role_manager.register_device_for_role('microwave_generator', 'new_device', NewMicrowaveGenerator)

# Use immediately in existing experiments
experiment = RoleBasedODMRExperiment(device_config={'microwave': 'new_device'})
```

## Migration Path

### Converting Existing Experiments

1. **Change Base Class**:
```python
# Before
class ODMRExperiment(Experiment):

# After  
class RoleBasedODMRExperiment(RoleBasedExperiment):
```

2. **Replace Device Definitions**:
```python
# Before
_DEVICES = {
    'microwave': SG384Generator,
    'adwin': ADwinGold,
    'nanodrive': MCLNanoDrive
}

# After
_REQUIRED_DEVICE_ROLES = {
    'microwave': 'microwave_generator',
    'daq': 'data_acquisition',
    'scanner': 'scanner'
}
```

3. **Update Device Access**:
```python
# Before
self.microwave.set_frequency(2.87e9)

# After
microwave = self.devices['microwave']['instance']
microwave.set_frequency(2.87e9)
```

## Testing and Validation

We've created comprehensive tests (`tests/test_role_based_experiments.py`) that demonstrate:

- **Device Role Validation**: Ensures devices implement required interfaces
- **Configuration Loading**: Tests configuration-driven device selection
- **Hardware Portability**: Verifies same experiment works with different hardware
- **Mock Device Testing**: Shows how to test without real hardware

## Files Created/Modified

### New Files:
1. `src/core/device_roles.py` - Device role definitions and management
2. `src/core/role_based_experiment.py` - Role-based experiment base class
3. `src/core/experiment_config.py` - Configuration management system
4. `src/Model/experiments/odmr_experiment_role_based.py` - Example role-based experiment
5. `tests/test_role_based_experiments.py` - Comprehensive test suite
6. `docs/ROLE_BASED_EXPERIMENTS.md` - Detailed documentation
7. `docs/ROLE_BASED_SOLUTION_SUMMARY.md` - This summary

### Key Features:
- **4 Device Roles**: Microwave Generator, Data Acquisition, Scanner, Pulse Generator
- **8 Device Types**: SG384, Windfreak, ADwin, NI-DAQ, NanoDrive, etc.
- **Configuration System**: JSON-based device selection
- **Lab-Specific Configs**: Support for different lab hardware setups
- **Validation**: Runtime validation of device capabilities
- **Testing**: Mock device support for testing

## Usage Examples

### Basic Usage:
```python
# Create experiment with default hardware
experiment = RoleBasedODMRExperiment(name="ODMR_Default")

# Create experiment with custom hardware
experiment = RoleBasedODMRExperiment(
    name="ODMR_Custom",
    device_config={
        'microwave': 'windfreak_synth_usbii',
        'daq': 'nidaq',
        'scanner': 'nanodrive'
    }
)
```

### Configuration-Based Usage:
```python
# Load from configuration file
experiment = create_experiment_from_config(
    RoleBasedODMRExperiment,
    'odmr_experiment',
    lab_name='pitt_lab'
)
```

### Testing Usage:
```python
# Test with mock devices
experiment = RoleBasedODMRExperiment(
    device_config={
        'microwave': 'mock_microwave',
        'daq': 'mock_daq',
        'scanner': 'mock_scanner'
    }
)
result = experiment._function()  # Works without real hardware
```

## Conclusion

This role-based system transforms AQuISS from a hardware-specific system to a truly portable, configurable laboratory automation platform. The same experiment code now works with:

- **Different microwave generators** (SG384, Windfreak, etc.)
- **Different DAQ systems** (ADwin, NI-DAQ, etc.)  
- **Different scanners** (NanoDrive, Galvo, etc.)
- **Any combination** of the above

**Key Achievement**: Experiments are now **hardware-agnostic** and **portable** across different laboratory setups, exactly as you requested. The system maintains backward compatibility while providing a clear migration path for existing experiments. 