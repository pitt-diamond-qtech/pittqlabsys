# Role-Based Devices Architecture

## Overview

This document outlines the current device management system, its limitations, and proposes a future role-based device factory architecture for the PittQLabSys project.

## Current System Analysis

### What We Have (Device Registry)

The current system has a **device registry** in `src/Controller/__init__.py`, but it's not actively used:

```python
_DEVICE_REGISTRY = {
    "awg520": AWG520Device, 
    "sg384": SG384Generator,
    "windfreak_synth_usbii": WindfreakSynthUSBII,
    "nanodrive": MCLNanoDrive,
    "adwin": AdwinGoldDevice,
    "pulseblaster": PulseBlaster,
    # ... etc
}

def create_device(kind: str, **kwargs):
    cls = _DEVICE_REGISTRY.get(kind.lower())
    if cls is None:
        raise ValueError(f"Unknown device type: {kind}")
    return cls(**kwargs)
```

**Important Note:** The `create_device` function exists but is **never called anywhere** in the codebase. This is more of an unused device class catalog than an active factory pattern.

### Current Experiment Device Specification

Experiments currently specify devices using concrete device classes:

```python
_DEVICES = {
    'microwave': SG384Generator,  # Specific class
    'awg': AWG520Device,         # Specific class
    'adwin': AdwinGoldDevice,    # Specific class
}
```

## Current System Limitations

### 1. Hardcoded Hardware Configuration

**Problem:** Hardware connection details are embedded within device classes:
- IP addresses (e.g., `192.168.2.217` for SG384)
- COM ports (e.g., `COM3` for Arduino devices)
- Network ports (e.g., `5025` for SG384)
- VISA resource strings

**Impact:** 
- Users cannot easily change hardware connections
- Lab PC COM port changes require code modifications
- Different lab setups require different code branches

### 2. Tight Coupling Between Experiments and Device Classes

**Problem:** Experiments are directly coupled to specific device implementations:
- Changing from SG384 to Windfreak requires experiment code changes
- Device-specific features are hardcoded in experiments
- Limited flexibility for hardware upgrades

### 3. Configuration Scattered Across Codebase

**Problem:** Hardware settings are distributed across:
- Device class default parameters
- Experiment device specifications
- Mock device configurations
- Test fixtures

## Future Architecture: Role-Based Device Factory

### Concept

Transform the current device registry into a **role-based system** where:

1. **Experiments specify device roles** (capabilities, not classes)
2. **Configuration files map roles to concrete devices**
3. **Device factory instantiates appropriate devices** based on config
4. **Hardware connection details** are centralized in JSON config files

### Proposed Structure

#### 1. Role-Based Device Specification

```python
# Instead of concrete classes
_DEVICES = {
    'microwave': 'microwave_generator',     # Role/capability
    'awg': 'arbitrary_waveform_generator', # Role/capability
    'adwin': 'data_acquisition',           # Role/capability
}
```

#### 2. Configuration-Driven Device Mapping

```json
// config.json or workspace_config.json
{
  "devices": {
    "microwave_generator": {
      "class": "SG384Generator",
      "connection": {
        "type": "LAN",
        "ip_address": "192.168.2.217",
        "port": 5025
      }
    },
    "arbitrary_waveform_generator": {
      "class": "AWG520Device",
      "connection": {
        "type": "LAN",
        "ip_address": "192.168.2.100",
        "port": 4000
      }
    }
  }
}
```

#### 3. Enhanced Device Factory

```python
class RoleBasedDeviceFactory:
    def create_device(self, role: str, config: dict):
        device_spec = config['devices'][role]
        device_class = self._get_device_class(device_spec['class'])
        connection_settings = device_spec['connection']
        return device_class(settings=connection_settings)
```

## Hardware Agnosticism Reality Check

### Why Complete Hardware Agnosticism is Impossible

Experiments **cannot be completely hardware-agnostic** due to fundamental hardware constraints:

#### 1. Triggering Mechanisms are Hardware-Specific

- **AWG520 Enhanced Run Mode** vs **Triggered Mode**
- **ADwin as Master** vs **AWG520 as Master**
- **Different sequence optimization strategies** for each mode
- **Hardware wiring determines** which device controls timing

#### 2. Data Collection Patterns Depend on Connections

- **How devices are physically wired** together
- **Which device controls synchronization**
- **Memory optimization strategies** vary by control architecture
- **Sequence file formats** depend on trigger mode

#### 3. Device Modes Affect Experiment Behavior

- **AWG520 sequence structure** changes based on trigger mode
- **ADwin counting protocols** depend on trigger source
- **Memory usage patterns** vary by operational mode

### What CAN Be Made Hardware-Agnostic

- **Device identity** (IP addresses, COM ports)
- **Device models** (SG384 vs Windfreak vs other microwave generators)
- **Connection types** (LAN vs GPIB vs USB)
- **Basic device capabilities** (frequency range, power output)

## Migration Strategy

### Phase 1: Current Branch (dutt-features)
- **Debug existing experiments** and devices on lab PC
- **Fix import errors** and hardware connection issues
- **Ensure current system works** reliably

### Phase 2: Configuration Externalization
- **Move hardware config to JSON files**
- **Update device classes** to read config at instantiation
- **Keep existing device registry** and experiment structure
- **Minimal code changes** to experiments
- **Improve test infrastructure** to eliminate environment variable dependencies
  - Replace `RUN_HARDWARE_TESTS=1` with dynamic hardware detection
  - Implement pytest fixtures for automatic test skipping
  - Add command-line options for explicit test control
  - Support configuration files for test behavior

### Phase 3: Role-Based Implementation (dutt-role-based)
- **Implement role-based device specification**
- **Enhance device factory** for role mapping
- **Update experiments** to use roles instead of classes
- **Maintain backward compatibility** during transition

## Benefits of Role-Based Approach

### 1. User Maintainability
- **Hardware changes** require only config file edits
- **No code modifications** for COM port changes
- **Easy hardware upgrades** and replacements

### 2. Lab Flexibility
- **Different lab setups** can use different config files
- **Hardware sharing** between experiments
- **Easy device substitution** (e.g., SG384 → Windfreak)

### 3. Development Efficiency
- **Mock devices** automatically configured
- **Testing** with different hardware configurations
- **CI/CD** with configurable device setups

### 4. Experiment Portability
- **Experiments work** across different lab setups
- **Hardware requirements** clearly specified as roles
- **Easier collaboration** between research groups

## Implementation Considerations

### 1. Backward Compatibility
- **Existing experiments** should continue to work
- **Gradual migration** from class-based to role-based
- **Fallback mechanisms** for missing roles

### 2. Test Infrastructure Improvements
- **Replace environment variables** (e.g., `RUN_HARDWARE_TESTS=1`) with better alternatives
- **Implement dynamic test skipping** based on hardware availability
- **Use pytest fixtures** for automatic hardware detection
- **Add command-line options** for explicit test control
- **Configuration file support** for test behavior customization

**Current Problem:** Tests use environment variables like `RUN_HARDWARE_TESTS=1` which are:
- **Platform-dependent** (awkward on Windows)
- **Hard to remember** and maintain
- **Inflexible** for complex test selection logic

**Proposed Solutions:**
1. **Dynamic Hardware Detection** - Tests automatically skip if hardware unavailable
2. **Command Line Arguments** - `pytest --run-hardware --features sg384,awg520`
3. **Configuration Files** - `test_config.json` for test behavior settings
4. **Pytest Fixtures** - Automatic hardware availability checking

### 2. Configuration Management
- **Environment-specific configs** (lab vs development)
- **Config validation** and error handling
- **Default configurations** for common setups

### 3. Error Handling
- **Clear error messages** for missing devices
- **Graceful degradation** when hardware unavailable
- **User-friendly troubleshooting** guides

### 4. Performance
- **Device instantiation** should remain fast
- **Config caching** for frequently accessed settings
- **Lazy loading** of device connections

## Conclusion

The current system is simpler than initially described - it's a **device class catalog** rather than an active factory pattern. The main improvements needed are:

1. **Externalize hardware configuration** from device classes
2. **Implement an actual device factory** for role-based mapping
3. **Maintain the current experiment structure** while adding flexibility

This approach allows us to:
- **Keep the simple device class structure** that works
- **Add a factory pattern** where none currently exists
- **Maintain backward compatibility** during transition
- **Create a more maintainable** system for lab users

The role-based approach is not about making experiments completely hardware-agnostic, but about making hardware configuration more flexible and user-editable while preserving the operational behavior that experiments depend on. Since there's no existing factory pattern to replace, we can implement the role-based system as a new capability rather than a major refactoring.
