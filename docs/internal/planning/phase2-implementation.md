# Phase 2 Implementation Plan: Add Pint Integration to Parameter Class

## Overview
Phase 2 focuses on adding pint unit registry integration to the Parameter class, enabling automatic unit conversion and better unit handling.

## Key Features to Add

### 1. Support for Pint Quantity Objects
**Goal**: Allow Parameter values to be pint Quantity objects with automatic unit conversion.

```python
# Current: units are just strings
p = Parameter('frequency', 2.85e9, float, 'Frequency', units='Hz')

# Phase 2: support pint Quantity objects
from src import ur
p = Parameter('frequency', 2.85e9 * ur.Hz, float, 'Frequency')
```

### 2. Automatic Unit Conversion Methods
**Goal**: Add methods to convert parameter values between different units.

```python
# Get value in different units
freq_ghz = p.get_value_in_units('GHz')
freq_mhz = p.get_value_in_units('MHz')

# Set value with units
p.set_value_with_units(2.9, 'GHz')
```

### 3. Unit Validation and Compatibility
**Goal**: Ensure units are compatible and provide clear error messages.

```python
# Validate unit compatibility
p.validate_units('Hz', 'GHz')  # Should pass
p.validate_units('Hz', 'kg')   # Should fail
```

### 4. Enhanced Unit Access
**Goal**: Provide better unit information and conversion utilities.

```python
# Get unit information
p.get_unit_info()  # Returns unit object, magnitude, etc.
p.is_pint_quantity()  # Check if value is a pint Quantity
```

## Implementation Strategy

### Step 1: Add Pint Quantity Support
- Modify `__init__` to detect pint Quantity objects
- Store original units and magnitude separately
- Maintain backward compatibility with string units

### Step 2: Add Unit Conversion Methods
- `get_value_in_units(target_units)`: Convert to target units
- `set_value_with_units(value, units)`: Set value with units
- `convert_units(target_units)`: Convert in place

### Step 3: Add Unit Validation
- `validate_units(unit1, unit2)`: Check unit compatibility
- `get_unit_info()`: Get detailed unit information
- `is_pint_quantity()`: Check if value is pint Quantity

### Step 4: Update Tests
- Add tests for pint Quantity support
- Add tests for unit conversion
- Add tests for unit validation
- Ensure backward compatibility

## Detailed Implementation Plan

### 1. Enhanced Parameter Class
```python
class Parameter(dict):
    def __init__(self, name, value=None, valid_values=None, info=None, visible=False, units=None):
        # ... existing initialization ...
        
        # Handle pint units
        self._pint_quantity = False
        self._original_units = None
        self._original_magnitude = None
        
        if hasattr(value, 'magnitude') and hasattr(value, 'units'):
            # Value is a pint Quantity
            self._pint_quantity = True
            self._original_units = value.units
            self._original_magnitude = value.magnitude
```

### 2. Unit Conversion Methods
```python
def get_value_in_units(self, target_units):
    """Get parameter value converted to target units."""
    
def set_value_with_units(self, value, units=None):
    """Set parameter value with units."""
    
def convert_units(self, target_units):
    """Convert parameter value to target units in place."""
    
def is_pint_quantity(self):
    """Check if parameter value is a pint Quantity."""
    
def get_unit_info(self):
    """Get detailed unit information."""
```

### 3. Unit Validation Methods
```python
def validate_units(self, unit1, unit2):
    """Validate that two units are compatible."""
    
def get_compatible_units(self):
    """Get list of compatible units for this parameter."""
```

## Testing Strategy

### New Functionality Tests
- Test pint Quantity creation and access
- Test unit conversion methods
- Test unit validation
- Test error handling for incompatible units

### Backward Compatibility Tests
- Ensure existing string-based units still work
- Ensure existing parameter access patterns work
- Ensure validation still works with string units

### Integration Tests
- Test with real experiment configurations
- Test unit conversion in nested structures
- Test performance with large parameter sets

## Success Criteria

1. **Pint Quantity Support**
   ```python
   p = Parameter('freq', 2.85e9 * ur.Hz, float, 'Frequency')
   assert p.is_pint_quantity()  # Should be True
   ```

2. **Unit Conversion**
   ```python
   freq_ghz = p.get_value_in_units('GHz')
   assert freq_ghz.magnitude == 2.85  # Should work
   ```

3. **Unit Validation**
   ```python
   p.validate_units('Hz', 'GHz')  # Should pass
   p.validate_units('Hz', 'kg')   # Should raise error
   ```

4. **Backward Compatibility**
   - All existing code continues to work
   - String-based units still function
   - No breaking changes to public API

## Implementation Order

1. **Add pint Quantity detection and storage**
2. **Implement unit conversion methods**
3. **Add unit validation methods**
4. **Update tests for new functionality**
5. **Test backward compatibility**
6. **Document new features**

## Risk Mitigation

1. **Backward Compatibility**: Maintain all existing functionality
2. **Performance**: Ensure unit conversion doesn't impact performance
3. **Error Handling**: Provide clear error messages for unit issues
4. **Documentation**: Document all new features and usage patterns

## Future Enhancements (Phase 3)

1. **Caching**: Cache unit conversions for performance
2. **Serialization**: JSON serialization with unit preservation
3. **GUI Integration**: Unit-aware GUI widgets
4. **Validation Rules**: More sophisticated validation (ranges, etc.) 