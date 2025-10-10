# Device Validation Implementation Checklist

## 🎯 **Priority Order for Implementation**

### 1. **MCLNanoDrive** (High Priority)
**File**: `src/Controller/nanodrive.py`  
**Why**: Most commonly used device, position parameters critical

**Parameters to Validate**:
- [ ] `x_pos`, `y_pos`, `z_pos` - Position limits
- [ ] `read_rate`, `load_rate` - Rate limits (positive values)
- [ ] `num_datapoints` - Positive integer
- [ ] `serial` - Valid serial number format

**Implementation Template**:
```python
def validate_parameter(self, path, value):
    """Validate MCLNanoDrive parameters"""
    param_name = path[-1] if path else None
    
    if param_name in ['x_pos', 'y_pos', 'z_pos']:
        # Get device-specific position limits
        min_pos, max_pos = self.get_position_limits(param_name)
        if value < min_pos or value > max_pos:
            clamped_value = max(min_pos, min(max_pos, value))
            return {
                'valid': False,
                'message': f'{param_name} position {value:.3f} μm out of range [{min_pos:.3f}, {max_pos:.3f}], clamped to {clamped_value:.3f}',
                'clamped_value': clamped_value
            }
    
    elif param_name in ['read_rate', 'load_rate']:
        if value <= 0:
            return {
                'valid': False,
                'message': f'{param_name} must be positive',
                'clamped_value': 0.1  # Minimum valid rate
            }
    
    elif param_name == 'num_datapoints':
        if not isinstance(value, int) or value <= 0:
            clamped_value = max(1, int(value))
            return {
                'valid': False,
                'message': f'{param_name} must be positive integer, clamped to {clamped_value}',
                'clamped_value': clamped_value
            }
    
    return {'valid': True, 'message': 'MCLNanoDrive parameter validation passed'}
```

### 2. **AdwinGoldDevice** (Medium Priority)
**File**: `src/Controller/adwin_gold.py`  
**Why**: Process timing parameters important for experiments

**Parameters to Validate**:
- [ ] `delay` - Non-negative time values
- [ ] Process parameters - Valid ranges
- [ ] Process states - Valid boolean values

**Implementation Template**:
```python
def validate_parameter(self, path, value):
    """Validate AdwinGoldDevice parameters"""
    param_name = path[-1] if path else None
    
    if param_name == 'delay':
        if value < 0:
            return {
                'valid': False,
                'message': 'Delay must be non-negative',
                'clamped_value': 0
            }
    
    elif 'process_' in param_name and 'delay' in path:
        if value < 0:
            return {
                'valid': False,
                'message': f'Process delay must be non-negative',
                'clamped_value': 0
            }
    
    return {'valid': True, 'message': 'AdwinGoldDevice parameter validation passed'}
```

### 3. **AWG520Device** (Medium Priority)
**File**: `src/Controller/awg520.py`  
**Why**: Network parameters need validation

**Parameters to Validate**:
- [ ] `ip_address` - Valid IP format
- [ ] `scpi_port`, `ftp_port` - Valid port ranges (1-65535)
- [ ] `seq_file` - Valid file extension
- [ ] `enable_iq` - Boolean validation

**Implementation Template**:
```python
def validate_parameter(self, path, value):
    """Validate AWG520Device parameters"""
    param_name = path[-1] if path else None
    
    if param_name == 'ip_address':
        if not self._is_valid_ip(value):
            return {
                'valid': False,
                'message': f'Invalid IP address format: {value}'
            }
    
    elif param_name in ['scpi_port', 'ftp_port']:
        if not isinstance(value, int) or value < 1 or value > 65535:
            clamped_value = max(1, min(65535, int(value)))
            return {
                'valid': False,
                'message': f'Port must be between 1-65535, clamped to {clamped_value}',
                'clamped_value': clamped_value
            }
    
    elif param_name == 'seq_file':
        if not value.endswith('.seq'):
            return {
                'valid': False,
                'message': 'Sequence file must have .seq extension'
            }
    
    return {'valid': True, 'message': 'AWG520Device parameter validation passed'}

def _is_valid_ip(self, ip):
    """Check if IP address is valid"""
    try:
        parts = ip.split('.')
        if len(parts) != 4:
            return False
        for part in parts:
            if not 0 <= int(part) <= 255:
                return False
        return True
    except:
        return False
```

### 4. **MUXControlDevice** (Lower Priority)
**File**: `src/Controller/mux_control.py`  
**Why**: Serial communication parameters

**Parameters to Validate**:
- [ ] `port` - Valid COM port format (COM1-COM99)
- [ ] `baudrate` - Valid baud rate values
- [ ] `timeout` - Positive timeout values

**Implementation Template**:
```python
def validate_parameter(self, path, value):
    """Validate MUXControlDevice parameters"""
    param_name = path[-1] if path else None
    
    if param_name == 'port':
        if not value.startswith('COM') or not value[3:].isdigit():
            return {
                'valid': False,
                'message': f'Invalid COM port format: {value}. Use COM1-COM99'
            }
    
    elif param_name == 'baudrate':
        valid_rates = [9600, 19200, 38400, 57600, 115200]
        if value not in valid_rates:
            return {
                'valid': False,
                'message': f'Invalid baud rate: {value}. Valid rates: {valid_rates}'
            }
    
    elif param_name == 'timeout':
        if value <= 0:
            return {
                'valid': False,
                'message': 'Timeout must be positive',
                'clamped_value': 1000
            }
    
    return {'valid': True, 'message': 'MUXControlDevice parameter validation passed'}
```

## 🧪 **Testing Strategy**

### For Each Device
1. **Unit Tests**: Test validation method directly
2. **Integration Tests**: Test with GUI delegate
3. **Edge Cases**: Boundary values, invalid inputs
4. **Visual Feedback**: Verify orange/green/red backgrounds

### Test Template
```python
def test_device_validation():
    device = DeviceClass()
    
    # Test valid values
    result = device.validate_parameter(['param'], valid_value)
    assert result['valid'] == True
    
    # Test clamped values
    result = device.validate_parameter(['param'], out_of_range_value)
    assert result['valid'] == False
    assert 'clamped_value' in result
    
    # Test invalid values
    result = device.validate_parameter(['param'], invalid_value)
    assert result['valid'] == False
    assert 'clamped_value' not in result
```

## 📋 **Implementation Checklist**

### For Each Device:
- [ ] Add `validate_parameter(path, value)` method
- [ ] Define parameter ranges and limits
- [ ] Implement clamping logic where appropriate
- [ ] Add clear, user-friendly error messages
- [ ] Write unit tests
- [ ] Test with GUI delegate
- [ ] Verify visual feedback works
- [ ] Update device documentation

### Global Tasks:
- [ ] Update device base class documentation
- [ ] Add validation examples to device templates
- [ ] Create validation testing framework
- [ ] Update GUI documentation

## 🎯 **Success Criteria**

- [ ] All devices have `validate_parameter` method
- [ ] All parameters have appropriate validation
- [ ] Visual feedback works for all devices
- [ ] Comprehensive test coverage
- [ ] Clear error messages for users
- [ ] Documentation updated

---

**Next Steps**: Start with MCLNanoDrive implementation, then move to AdwinGoldDevice.
