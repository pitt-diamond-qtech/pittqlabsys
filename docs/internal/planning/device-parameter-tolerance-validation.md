# Device Parameter Tolerance and Validation System

## 🎯 **Overview**

This document outlines the comprehensive implementation plan for the Device Parameter Tolerance and Validation System, which ensures device values are within acceptable ranges and provides honest feedback about actual vs requested values.

## 🚨 **Problem Statement**

**Current Issue**: The system only shows green "success" even when devices report different actual values than requested, providing misleading feedback to users.

**Example**:
- User requests: 50.0 μm
- Device reports: 49.5 μm  
- Current: Shows green "success" (misleading!)
- Needed: Shows yellow "device_different" with honest feedback

## 🎯 **Goals**

1. **Honest Reporting**: Show both requested and actual values
2. **Tolerance Checking**: Validate parameters against device-specific tolerances
3. **Visual Feedback**: Clear visual indicators for different validation states
4. **Configuration**: Flexible tolerance settings per device and parameter
5. **User Experience**: Intuitive feedback that helps users understand device behavior

## 🏗️ **Architecture Design**

### **Configuration Structure**

Add `tolerance_settings` section to device JSON configs:

```json
{
    "devices": {
        "sg384": {
            "class": "SG384Generator",
            "filepath": "src/Controller/sg384.py",
            "settings": { /* existing settings */ },
            "tolerance_settings": {
                "frequency": {
                    "tolerance_percent": 0.1,
                    "tolerance_absolute": 1000,
                    "validation_enabled": true,
                    "warning_threshold": 0.05
                },
                "power": {
                    "tolerance_percent": 2.0,
                    "tolerance_absolute": 0.5,
                    "validation_enabled": true,
                    "warning_threshold": 1.0
                }
            }
        }
    }
}
```

### **Base Framework Components**

#### **1. Enhanced Parameter Class**
```python
class Parameter(dict):
    def __init__(self, name, value=None, valid_values=None, info=None, visible=False, units=None,
                 min_value=None, max_value=None, pattern=None, validator=None,
                 tolerance_percent=None, tolerance_absolute=None, validation_enabled=True):
        # ... existing parameters ...
        self._tolerance_percent = tolerance_percent
        self._tolerance_absolute = tolerance_absolute
        self._validation_enabled = validation_enabled
```

#### **2. Enhanced Device Class**
```python
class Device:
    def validate_parameter_tolerance(self, parameter_name, target_value, actual_value):
        """
        Validate if actual device value is within tolerance of target value.
        
        Args:
            parameter_name: Name of the parameter being validated
            target_value: The value we tried to set
            actual_value: The value the device actually has
            
        Returns:
            dict: Validation result with 'valid', 'within_tolerance', 'deviation', etc.
        """
        
    def check_all_parameters_tolerance(self):
        """
        Check all device parameters against their tolerance settings.
        Returns a comprehensive validation report.
        """
        
    def load_tolerance_settings(self):
        """
        Load tolerance settings from device configuration.
        """
```

#### **3. GUI Integration**
```python
# New visual states in NumberClampDelegate
VALIDATION_STATES = {
    'valid': 'green',
    'invalid': 'red', 
    'device_different': 'yellow',  # NEW: Within tolerance but different
    'warning': 'orange'            # NEW: Near tolerance limit
}
```

## 📋 **Implementation Plan**

### **Phase 1: Configuration System** (Week 1)
**Goal**: Set up tolerance configuration structure

**Tasks**:
- [ ] Design `tolerance_settings` JSON structure
- [ ] Update `config.sample.json` with example tolerance settings
- [ ] Update `src/config.template.json` with tolerance template
- [ ] Create tolerance configuration validation system
- [ ] Add tolerance loading to device initialization

**Files**:
- `config.sample.json`
- `src/config.template.json`
- `src/core/device.py` (tolerance loading)

### **Phase 2: Base Framework** (Week 1-2)
**Goal**: Implement core tolerance validation logic

**Tasks**:
- [ ] Extend `Parameter` class with tolerance support
- [ ] Add `validate_parameter_tolerance()` to base `Device` class
- [ ] Add `check_all_parameters_tolerance()` to base `Device` class
- [ ] Implement tolerance comparison logic (percentage and absolute)
- [ ] Add tolerance settings loading to device initialization

**Files**:
- `src/core/parameter.py`
- `src/core/device.py`

### **Phase 3: Device Integration** (Week 2)
**Goal**: Integrate tolerance validation with specific devices

**Tasks**:
- [ ] Update SG384 device with tolerance validation
- [ ] Update AWG520 device with tolerance validation
- [ ] Update Nanodrive device with tolerance validation
- [ ] Add actual value checking using `device.update_and_get()`
- [ ] Test tolerance validation with real devices

**Files**:
- `src/Controller/sg384.py`
- `src/Controller/awg520.py`
- `src/Controller/nanodrive.py`
- Other device implementations

### **Phase 4: GUI Integration** (Week 2-3)
**Goal**: Add visual feedback for tolerance validation

**Tasks**:
- [ ] Add `'device_different'` visual state to NumberClampDelegate
- [ ] Add `'warning'` visual state for near-tolerance values
- [ ] Update feedback messages to show requested vs actual values
- [ ] Add tolerance information to GUI history
- [ ] Implement warning thresholds for near-tolerance values

**Files**:
- `src/View/windows_and_widgets/widgets.py`
- `src/View/windows_and_widgets/main_window.py`

### **Phase 5: Testing and Refinement** (Week 3)
**Goal**: Comprehensive testing and user experience refinement

**Tasks**:
- [ ] Test with various device types and parameters
- [ ] Refine tolerance thresholds based on real device behavior
- [ ] Add comprehensive error handling
- [ ] Update documentation
- [ ] User testing and feedback integration

## 🔧 **Technical Details**

### **Tolerance Calculation Logic**

```python
def calculate_tolerance_deviation(self, target_value, actual_value, tolerance_percent=None, tolerance_absolute=None):
    """
    Calculate if actual value is within tolerance of target value.
    
    Returns:
        dict: {
            'within_tolerance': bool,
            'deviation_percent': float,
            'deviation_absolute': float,
            'tolerance_exceeded': bool,
            'warning_threshold_exceeded': bool
        }
    """
    deviation_absolute = abs(actual_value - target_value)
    deviation_percent = (deviation_absolute / abs(target_value)) * 100 if target_value != 0 else 0
    
    within_tolerance = True
    tolerance_exceeded = False
    warning_threshold_exceeded = False
    
    if tolerance_percent is not None:
        if deviation_percent > tolerance_percent:
            within_tolerance = False
            tolerance_exceeded = True
        elif deviation_percent > tolerance_percent * 0.8:  # Warning at 80% of tolerance
            warning_threshold_exceeded = True
    
    if tolerance_absolute is not None:
        if deviation_absolute > tolerance_absolute:
            within_tolerance = False
            tolerance_exceeded = True
        elif deviation_absolute > tolerance_absolute * 0.8:  # Warning at 80% of tolerance
            warning_threshold_exceeded = True
    
    return {
        'within_tolerance': within_tolerance,
        'deviation_percent': deviation_percent,
        'deviation_absolute': deviation_absolute,
        'tolerance_exceeded': tolerance_exceeded,
        'warning_threshold_exceeded': warning_threshold_exceeded
    }
```

### **Validation Flow**

1. **User Input**: User sets parameter value
2. **Validation**: Standard parameter validation (existing)
3. **Device Update**: Apply value to hardware device
4. **Actual Value Check**: Call `device.update_and_get()` to get real device value
5. **Tolerance Check**: Compare target vs actual using tolerance settings
6. **Visual Feedback**: Set appropriate visual state based on validation result
7. **User Feedback**: Show detailed message about requested vs actual values

### **Visual States**

| State | Color | Description | When Used |
|-------|-------|-------------|-----------|
| `valid` | Green | Parameter is valid and device value matches | Target = Actual |
| `device_different` | Yellow | Device value differs but within tolerance | Target ≠ Actual, within tolerance |
| `warning` | Orange | Near tolerance limit | Within tolerance but close to limit |
| `invalid` | Red | Parameter invalid or tolerance exceeded | Validation failed or tolerance exceeded |

## 🎨 **User Experience**

### **Feedback Messages**

**Within Tolerance**:
- "Parameter set successfully. Requested: 50.0 μm, Device: 49.5 μm (within 1% tolerance)"

**Warning (Near Tolerance)**:
- "Parameter set with warning. Requested: 50.0 μm, Device: 49.8 μm (near 1% tolerance limit)"

**Tolerance Exceeded**:
- "Parameter set but tolerance exceeded. Requested: 50.0 μm, Device: 49.0 μm (exceeds 1% tolerance)"

### **GUI History Integration**

Add tolerance information to parameter history:
- Show both requested and actual values
- Display tolerance status
- Include deviation percentages
- Color-code based on validation state

## 🧪 **Testing Strategy**

### **Unit Tests**
- Tolerance calculation logic
- Parameter validation with tolerances
- Device tolerance loading
- GUI visual state updates

### **Integration Tests**
- End-to-end parameter setting with tolerance checking
- Multiple device types with different tolerance settings
- GUI feedback integration
- Error handling scenarios

### **Device-Specific Tests**
- SG384 frequency and power tolerance
- AWG520 amplitude and timing tolerance
- Nanodrive position tolerance
- Edge cases and boundary conditions

## 📊 **Success Metrics**

1. **Accuracy**: All device values properly validated against tolerances
2. **User Experience**: Clear, honest feedback about device behavior
3. **Reliability**: Consistent tolerance checking across all device types
4. **Performance**: Minimal impact on parameter setting speed
5. **Maintainability**: Easy to configure tolerances for new devices

## 🔄 **Future Enhancements**

1. **Adaptive Tolerances**: Learn from device behavior to adjust tolerances
2. **Tolerance Calibration**: Automatic tolerance determination based on device characteristics
3. **Advanced Analytics**: Track device accuracy over time
4. **Custom Validation Rules**: Device-specific validation logic
5. **Tolerance Templates**: Pre-configured tolerance sets for common device types

---

**Last Updated**: December 2024  
**Status**: Planning Phase  
**Priority**: High  
**Estimated Effort**: 3 weeks