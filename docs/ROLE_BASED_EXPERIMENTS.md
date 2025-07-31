# Role-Based Experiments: Making AQuISS Hardware-Agnostic

## Overview

The role-based experiment system is designed to make AQuISS experiments portable across different laboratory setups with different hardware configurations. Instead of hardcoding specific device classes in experiments, this system uses device roles and configuration-driven device selection.

## Problem Statement

### Current Issues with Hardcoded Devices

1. **Tight Coupling**: Experiments are tightly coupled to specific device implementations
2. **Limited Portability**: Moving experiments between labs requires code changes
3. **Maintenance Overhead**: Supporting multiple hardware configurations requires multiple experiment versions
4. **Configuration vs. Code**: Device selection is in code rather than configuration

### Example of Current Problem

```python
# Current approach - hardcoded devices
class ODMRExperiment(Experiment):
    _DEVICES = {
        'microwave': SG384Generator,  # Hardcoded to specific device
        'adwin': ADwinGold,           # Hardcoded to specific device
        'nanodrive': MCLNanoDrive     # Hardcoded to specific device
    }
```

This means:
- If a lab has a Windfreak SynthUSBII instead of SG384, the experiment won't work
- If a lab uses NI-DAQ instead of ADwin, the experiment needs modification
- Sharing experiments between labs requires code changes

## Solution: Role-Based Device Selection

### Core Concepts

1. **Device Roles**: Abstract interfaces that define what a device can do
2. **Role-Based Experiments**: Experiments that specify required roles rather than specific devices
3. **Configuration-Driven Selection**: Device selection specified in configuration files
4. **Hardware-Agnostic Code**: Experiment logic that works with any device implementing the required role

### Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Experiment    │    │  Device Roles    │    │  Device Config  │
│                 │    │                  │    │                 │
│ - microwave     │───▶│ - microwave_gen  │◀───│ - sg384         │
│ - daq           │    │ - data_acq       │    │ - windfreak     │
│ - scanner       │    │ - scanner        │    │ - adwin         │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Implementation

### 1. Device Roles (`src/core/device_roles.py`)

Device roles define abstract interfaces for different types of devices:

```python
class MicrowaveGeneratorRole(DeviceRole):
    def get_required_methods(self) -> List[str]:
        return [
            'set_frequency',
            'set_power', 
            'set_phase',
            'output_on',
            'output_off',
            'enable_modulation',
            'disable_modulation',
            'set_modulation_type',
            'set_modulation_depth'
        ]
    
    def get_required_parameters(self) -> List[str]:
        return [
            'frequency',
            'power',
            'phase',
            'amplitude',
            'connection_type',
            'visa_resource'
        ]
```

### 2. Role-Based Experiment Base Class (`src/core/role_based_experiment.py`)

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

Configuration files specify which devices to use for each role:

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

## Usage Examples

### Creating a Role-Based Experiment

```python
from src.core.role_based_experiment import RoleBasedExperiment

class RoleBasedODMRExperiment(RoleBasedExperiment):
    _REQUIRED_DEVICE_ROLES = {
        'microwave': 'microwave_generator',
        'daq': 'data_acquisition',
        'scanner': 'scanner'
    }
    
    _DEFAULT_DEVICE_TYPES = {
        'microwave': 'sg384',
        'daq': 'adwin',
        'scanner': 'nanodrive'
    }
    
    def _function(self):
        # Access devices by role name
        microwave = self.devices['microwave']['instance']
        daq = self.devices['daq']['instance']
        scanner = self.devices.get('scanner', {}).get('instance')
        
        # Use hardware-agnostic interface
        microwave.set_frequency(2.87e9)
        microwave.set_power(-10.0)
        microwave.output_on()
        
        # Same code works with any device implementing the role!
```

### Using Different Hardware Configurations

```python
# Default configuration (SG384 + ADwin + NanoDrive)
experiment1 = RoleBasedODMRExperiment(
    name="ODMR_Default",
    device_config=None  # Uses defaults
)

# Different microwave generator
experiment2 = RoleBasedODMRExperiment(
    name="ODMR_Windfreak",
    device_config={
        'microwave': 'windfreak_synth_usbii',  # Different microwave
        'daq': 'adwin',
        'scanner': 'nanodrive'
    }
)

# Different DAQ
experiment3 = RoleBasedODMRExperiment(
    name="ODMR_NIDAQ",
    device_config={
        'microwave': 'sg384',
        'daq': 'nidaq',  # Different DAQ
        'scanner': 'nanodrive'
    }
)

# All three use the same experiment code!
```

### Lab-Specific Configuration

```python
from src.core.experiment_config import create_experiment_from_config

# Pitt Lab configuration
pitt_config = {
    'device_config': {
        'microwave': 'sg384',
        'daq': 'adwin',
        'scanner': 'nanodrive'
    }
}

# MIT Lab configuration
mit_config = {
    'device_config': {
        'microwave': 'windfreak_synth_usbii',
        'daq': 'nidaq',
        'scanner': 'galvo_scanner'
    }
}

# Create experiments with lab-specific configurations
pitt_experiment = create_experiment_from_config(
    RoleBasedODMRExperiment, 
    'odmr_experiment',
    lab_name='pitt_lab'
)

mit_experiment = create_experiment_from_config(
    RoleBasedODMRExperiment, 
    'odmr_experiment',
    lab_name='mit_lab'
)
```

## Benefits

### 1. Hardware Portability

- **Same Code, Different Hardware**: Experiments work with any device implementing the required role
- **Easy Migration**: Moving experiments between labs requires only configuration changes
- **Hardware Independence**: Experiment logic is decoupled from specific device implementations

### 2. Configuration Management

- **Lab-Specific Configs**: Each lab can have its own device configuration
- **Easy Testing**: Can easily switch between different device types for testing
- **Version Control**: Device configurations can be version-controlled separately from code

### 3. Maintainability

- **Single Codebase**: One experiment implementation works for all hardware configurations
- **Reduced Duplication**: No need for multiple versions of the same experiment
- **Easier Updates**: Bug fixes and improvements benefit all hardware configurations

### 4. Extensibility

- **New Devices**: Adding new devices only requires implementing the role interface
- **New Roles**: New device roles can be added without changing existing experiments
- **Plugin Architecture**: Device implementations can be added as plugins

## Migration Guide

### Converting Existing Experiments

1. **Identify Device Roles**: Determine what roles your experiment needs
2. **Update Base Class**: Change from `Experiment` to `RoleBasedExperiment`
3. **Define Required Roles**: Specify `_REQUIRED_DEVICE_ROLES`
4. **Update Device Access**: Change from hardcoded device access to role-based access
5. **Create Configuration**: Generate configuration files for different labs

### Example Migration

**Before (Hardcoded)**:
```python
class ODMRExperiment(Experiment):
    _DEVICES = {
        'microwave': SG384Generator,
        'adwin': ADwinGold,
        'nanodrive': MCLNanoDrive
    }
    
    def _function(self):
        self.microwave.set_frequency(2.87e9)  # Direct access
```

**After (Role-Based)**:
```python
class RoleBasedODMRExperiment(RoleBasedExperiment):
    _REQUIRED_DEVICE_ROLES = {
        'microwave': 'microwave_generator',
        'daq': 'data_acquisition',
        'scanner': 'scanner'
    }
    
    def _function(self):
        microwave = self.devices['microwave']['instance']  # Role-based access
        microwave.set_frequency(2.87e9)
```

## Best Practices

### 1. Role Design

- **Keep Roles Focused**: Each role should have a clear, single responsibility
- **Define Clear Interfaces**: Specify exactly what methods and parameters are required
- **Version Roles**: Consider versioning role interfaces for backward compatibility

### 2. Device Implementation

- **Implement All Required Methods**: Ensure devices implement all methods defined by their role
- **Provide Meaningful Defaults**: Implement sensible defaults for optional parameters
- **Handle Errors Gracefully**: Devices should handle errors without crashing experiments

### 3. Configuration Management

- **Use Descriptive Names**: Use clear, descriptive names for device types
- **Document Configurations**: Include documentation in configuration files
- **Validate Configurations**: Always validate configurations before use

### 4. Testing

- **Test with Multiple Devices**: Test experiments with different device implementations
- **Mock Devices**: Use mock devices for unit testing
- **Configuration Testing**: Test with different configuration combinations

## Future Enhancements

### 1. Dynamic Role Discovery

- **Auto-Detection**: Automatically detect available devices and their roles
- **Hot-Swapping**: Allow devices to be swapped during runtime
- **Device Health Monitoring**: Monitor device health and suggest alternatives

### 2. Advanced Configuration

- **Hierarchical Configs**: Support nested configuration inheritance
- **Environment Variables**: Use environment variables for sensitive configuration
- **Remote Configuration**: Load configurations from remote sources

### 3. Role Validation

- **Runtime Validation**: Validate device capabilities at runtime
- **Performance Monitoring**: Monitor device performance and suggest optimizations
- **Compatibility Checking**: Check device compatibility before experiment execution

## Conclusion

The role-based experiment system provides a powerful foundation for making AQuISS experiments hardware-agnostic and portable. By separating device selection from experiment logic, this system enables:

- **Easy sharing** of experiments between labs
- **Flexible hardware** configurations
- **Reduced maintenance** overhead
- **Better testing** capabilities
- **Future extensibility**

This approach transforms AQuISS from a system tied to specific hardware to a truly portable, configurable laboratory automation platform. 