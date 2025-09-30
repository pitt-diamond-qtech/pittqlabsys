# Lab PC Testing Guide for Enhanced Parameter Validation

## Overview
This guide explains how to test the new parameter validation and GUI feedback features on the lab PC with real hardware.

## What's Ready for Testing

### ✅ Core Features Implemented
- **Enhanced Device Class**: `validate_parameter()` with pint units support
- **Parameter Feedback**: `update_and_get()` returns actual vs requested values
- **GUI Integration**: Visual feedback (colored backgrounds) and text box corrections
- **Mock Hardware**: Available for testing without real hardware

### ✅ GUI Features
- **Visual Feedback**: 
  - Green background: Parameter set successfully
  - Yellow background: Parameter clamped to valid range
  - Red background: Hardware error
- **Text Box Correction**: Shows actual hardware values when different from requested
- **Popup Notifications**: Critical hardware errors only (to avoid clutter)

## Testing Steps

### 1. Pull Latest Changes
```bash
# On lab PC
cd /path/to/pittqlabsys
git fetch origin
git checkout feature/parameter-validation-feedback
git pull origin feature/parameter-validation-feedback
```

### 2. Activate Virtual Environment
```bash
# Make sure venv is activated
source venv/bin/activate  # Linux
# or
venv\Scripts\activate     # Windows
```

### 3. Test with Mock Hardware First
```bash
# Test the validation system without real hardware
python examples/test_validation_features.py

# Test SG384 validation refactor
python examples/test_sg384_validation_refactor.py

# Test mock hardware for GUI
python examples/test_gui_with_validation.py
```

### 4. Test with Real Hardware
```bash
# Test with real hardware (will use actual devices)
python examples/test_validation_features.py --real-hardware

# Launch GUI with real hardware
python src/View/windows_and_widgets/main_window.py
```

## What to Test

### Parameter Validation Scenarios
1. **Valid Parameters**: Should show green background
2. **Out-of-Range Parameters**: Should show yellow background and clamp values
3. **Invalid Units**: Should show error messages
4. **Hardware Errors**: Should show red background and popup

### GUI Behavior
1. **Text Box Updates**: When hardware returns different values than requested
2. **Visual Feedback**: Background colors should change based on validation results
3. **Popup Notifications**: Should only appear for critical hardware errors
4. **Log Messages**: Should appear in console for all parameter changes

## Expected Behavior

### Stage Device Testing
- Try setting position to 15.0mm (should clamp to 10.0mm max)
- Try setting position to 50.0mm (should show hardware error)
- Try setting speed to 15.0 mm/s (should clamp to 10.0 mm/s max)

### RF Generator Testing
- Try setting frequency to 8.0 GHz (should clamp to 6.0 GHz max)
- Try setting power to 25.0 mW (should clamp to 20.0 mW max)
- Try setting frequency with different units (MHz, kHz, etc.)

## Troubleshooting

### If GUI Doesn't Launch
- Check PyQt5 installation: `pip list | grep PyQt5`
- Check virtual environment is activated
- Check for import errors in console

### If Validation Doesn't Work
- Check that devices have `validate_parameter()` method
- Check that devices have `get_parameter_ranges()` method
- Check console for error messages

### If Visual Feedback Doesn't Appear
- Check that `_set_item_visual_feedback()` is being called
- Check that `_show_parameter_notification()` is working
- Check console for GUI error messages

## Files to Check

### Core Implementation
- `src/core/device.py` - Enhanced Device class
- `src/View/windows_and_widgets/main_window.py` - GUI integration
- `src/Controller/sg384.py` - SG384 validation refactor

### Test Files
- `examples/test_validation_features.py` - Core validation testing
- `examples/test_gui_with_validation.py` - GUI testing with mocks
- `tests/test_device_units_validation.py` - Comprehensive unit tests

### Mock Hardware
- `src/Controller/__init__.py` - MockSG384Generator with validation
- `examples/mock_hardware_for_gui_testing.py` - Additional mock devices

## Next Steps After Testing

1. **Report Issues**: Note any problems with real hardware
2. **Performance**: Check if validation adds noticeable delay
3. **User Experience**: Verify visual feedback is clear and helpful
4. **Edge Cases**: Test with extreme values and unusual units

## Notes

- The system is designed to be backward compatible
- Old devices without validation methods will still work
- Mock hardware is available for testing without real devices
- All changes are in the `feature/parameter-validation-feedback` branch
