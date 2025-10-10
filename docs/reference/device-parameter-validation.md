# Device Parameter Validation System

## Overview

The parameter validation system provides real-time feedback to users when they input parameter values in the GUI. This system ensures that all device parameters are validated consistently and provides clear visual feedback (orange for clamped values, green for success, red for errors).

## Architecture

### Core Components

1. **`Device.validate_parameter(path, value)`** - Core validation method
2. **`NumberClampDelegate`** - GUI delegate that handles validation and visual feedback
3. **Visual Feedback System** - Orange/green/red backgrounds with auto-clear
4. **GUI History** - Logs validation results for user reference

### Validation Flow

```
User Input → NumberClampDelegate → Device.validate_parameter() → Visual Feedback → GUI History
```

## Device Implementation Requirements

### Required Method: `validate_parameter(path, value)`

**Every device must implement this method** to participate in the validation system.

#### Method Signature
```python
def validate_parameter(self, path, value):
    """
    Validate a parameter value and return validation result.
    
    Args:
        path (list): Path to the parameter (e.g., ['frequency', 'sweep_center'])
        value: The value to validate
        
    Returns:
        dict: Validation result with keys:
            - 'valid' (bool): Whether the value is valid
            - 'message' (str): Human-readable message
            - 'clamped_value' (optional): If value was clamped, the clamped value
    """
```

#### Return Format Examples

**Valid Value:**
```python
{
    'valid': True,
    'message': 'Parameter validation passed'
}
```

**Clamped Value:**
```python
{
    'valid': False,
    'message': 'Frequency 6.100 GHz above maximum 4.100 GHz',
    'clamped_value': 4100000000.0
}
```

**Invalid Value (no clamping possible):**
```python
{
    'valid': False,
    'message': 'Invalid parameter value: must be positive'
}
```

## Implementation Status

### ✅ **Implemented Devices**
- **SG384Generator** (`src/Controller/sg384.py`)
  - Frequency clamping (max 4.1 GHz)
  - Power clamping (max +13 dBm)
  - Comprehensive parameter validation

### 🔄 **Devices Needing Implementation**

#### **MCLNanoDrive** (`src/Controller/nanodrive.py`)
**Parameters to validate:**
- `x_pos`, `y_pos`, `z_pos`: Position limits
- `read_rate`, `load_rate`: Rate limits
- `num_datapoints`: Positive integer validation

**Implementation needed:**
```python
def validate_parameter(self, path, value):
    param_name = path[-1] if path else None
    
    if param_name in ['x_pos', 'y_pos', 'z_pos']:
        # Check position limits (device-specific)
        if value < self.min_position or value > self.max_position:
            clamped_value = max(self.min_position, min(self.max_position, value))
            return {
                'valid': False,
                'message': f'Position {value} out of range, clamped to {clamped_value}',
                'clamped_value': clamped_value
            }
    
    elif param_name in ['read_rate', 'load_rate']:
        # Check rate limits
        if value <= 0:
            return {
                'valid': False,
                'message': 'Rate must be positive'
            }
    
    return {'valid': True, 'message': 'Parameter validation passed'}
```

#### **AdwinGoldDevice** (`src/Controller/adwin_gold.py`)
**Parameters to validate:**
- `delay`: Positive time values
- Process parameters: Valid ranges

**Implementation needed:**
```python
def validate_parameter(self, path, value):
    param_name = path[-1] if path else None
    
    if param_name == 'delay':
        if value < 0:
            return {
                'valid': False,
                'message': 'Delay must be non-negative',
                'clamped_value': 0
            }
    
    return {'valid': True, 'message': 'Parameter validation passed'}
```

#### **AWG520Device** (`src/Controller/awg520.py`)
**Parameters to validate:**
- `ip_address`: Valid IP format
- `scpi_port`, `ftp_port`: Valid port ranges
- `seq_file`: Valid file format

#### **MUXControlDevice** (`src/Controller/mux_control.py`)
**Parameters to validate:**
- `port`: Valid COM port format
- `baudrate`: Valid baud rate values
- `timeout`: Positive timeout values

## Implementation Guidelines

### 1. **Parameter Range Definition**
Define clear ranges for each parameter:
```python
# In device __init__ or as class attributes
self.parameter_ranges = {
    'frequency': {'min': 1e6, 'max': 4.1e9},  # 1 MHz to 4.1 GHz
    'power': {'min': -20, 'max': 13},        # -20 to +13 dBm
    'phase': {'min': 0, 'max': 360}          # 0 to 360 degrees
}
```

### 2. **Clamping Strategy**
- **Clamp to nearest valid value** when possible
- **Provide clear messages** about what was clamped
- **Use appropriate units** in messages (GHz instead of Hz)

### 3. **Error Handling**
- **Graceful degradation** for validation failures
- **Informative error messages** for users
- **Logging** for debugging

### 4. **Testing**
- **Unit tests** for each validation method
- **Edge case testing** (boundary values, invalid inputs)
- **Integration testing** with GUI

## Testing Strategy

### Unit Tests
```python
def test_device_validation():
    device = SG384Generator()
    
    # Test valid value
    result = device.validate_parameter(['frequency'], 1e9)
    assert result['valid'] == True
    
    # Test clamped value
    result = device.validate_parameter(['frequency'], 5e9)
    assert result['valid'] == False
    assert result['clamped_value'] == 4.1e9
    
    # Test invalid value
    result = device.validate_parameter(['frequency'], -1e9)
    assert result['valid'] == False
    assert 'clamped_value' not in result
```

### Integration Tests
- Test with GUI delegate
- Test visual feedback
- Test GUI history logging

## Migration Plan

### Phase 1: Core Infrastructure ✅
- [x] Implement `NumberClampDelegate`
- [x] Add visual feedback system
- [x] Implement SG384 validation

### Phase 2: Device Implementation
- [ ] Implement MCLNanoDrive validation
- [ ] Implement AdwinGoldDevice validation
- [ ] Implement AWG520Device validation
- [ ] Implement MUXControlDevice validation

### Phase 3: Testing & Polish
- [ ] Add comprehensive unit tests
- [ ] Add integration tests
- [ ] Update documentation
- [ ] Performance optimization

## Benefits

### For Users
- **Immediate feedback** on parameter validity
- **Clear visual indicators** (colors) for different states
- **Automatic clamping** prevents invalid values
- **Transparent operation** - users see what happened

### For Developers
- **Consistent validation** across all devices
- **Centralized validation logic** in each device
- **Easy to extend** for new devices
- **Comprehensive testing** framework

## Future Enhancements

### Tolerance System
- Device-specific tolerance handling
- Smart "device_different" detection
- Configurable tolerance levels

### Unit Parsing
- Support for unit-aware input (GHz, MHz, etc.)
- Automatic unit conversion
- Context-sensitive validation

### Advanced Validation
- Cross-parameter validation
- Dependency checking
- Real-time hardware validation

---

**Last Updated**: October 10, 2025  
**Status**: Active Development  
**Priority**: High - Required for all devices
