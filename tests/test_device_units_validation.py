#!/usr/bin/env python3
"""
Tests for Device class with units validation and parameter feedback.

This module tests the enhanced Device class functionality including:
- Units validation with pint quantities
- Parameter validation and clamping
- Visual feedback mechanisms
- update_and_get functionality
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.device import Device
from src.core.parameter import Parameter
from src import ur


class TestDeviceWithUnits(Device):
    """Test device with units-enabled parameters."""
    
    def __init__(self):
        super().__init__()
        self._settings = Parameter([
            Parameter('frequency', 2.85e9 * ur.Hz, float, 'RF frequency', units='Hz'),
            Parameter('power', 10.0 * ur.mW, float, 'RF power', units='mW'),
            Parameter('voltage', 5.0, float, 'DC voltage', units='V'),
            Parameter('temperature', 298.15 * ur.K, float, 'Temperature', units='K'),
            Parameter('channel', 1, int, 'Channel number'),
            Parameter('enabled', True, bool, 'Device enabled'),
        ])
        self._probes = {
            'frequency': 'RF frequency in Hz',
            'power': 'RF power in mW', 
            'voltage': 'DC voltage in V',
            'temperature': 'Temperature in K',
            'channel': 'Channel number',
            'enabled': 'Device enabled status'
        }
    
    @property
    def _PROBES(self):
        """Return the dictionary of available probes."""
        return self._probes
    
    def read_probes(self):
        """Mock read_probes that returns current settings."""
        return dict(self._settings)
    
    def update(self, settings):
        """Mock update that applies settings with unit conversion."""
        for key, value in settings.items():
            if key in self._settings:
                # Handle pint quantities
                if hasattr(self._settings[key], 'is_pint_quantity') and self._settings[key].is_pint_quantity():
                    if hasattr(value, 'magnitude') and hasattr(value, 'units'):
                        # Convert to same units as parameter
                        target_units = self._settings[key][list(self._settings[key].keys())[0]].units
                        converted_value = value.to(target_units)
                        self._settings[key] = Parameter(key, converted_value, float, self._settings[key].info['key'], units=str(target_units))
                    else:
                        # Assume same units
                        current_value = self._settings[key][list(self._settings[key].keys())[0]]
                        if hasattr(current_value, 'units'):
                            new_value = value * current_value.units
                            self._settings[key] = Parameter(key, new_value, float, self._settings[key].info['key'], units=str(current_value.units))
                else:
                    # Regular parameter update
                    self._settings[key] = value


class TestDeviceUnitsValidation:
    """Test units validation functionality."""
    
    def setup_method(self):
        """Set up test device."""
        self.device = TestDeviceWithUnits()
    
    def test_pint_parameter_validation_valid_units(self):
        """Test validation with compatible units."""
        # Test frequency with different units (2.85 GHz = 2.85e3 MHz)
        result = self.device.validate_parameter(['frequency'], 2.85e3 * ur.MHz)  # Convert to MHz
        assert result['valid'] is True
        assert 'Valid pint quantity' in result['message']
        assert hasattr(result['clamped_value'], 'magnitude')
        assert hasattr(result['clamped_value'], 'units')
    
    def test_pint_parameter_validation_incompatible_units(self):
        """Test validation with incompatible units."""
        # Test frequency with voltage units (should fail)
        result = self.device.validate_parameter(['frequency'], 5.0 * ur.V)
        assert result['valid'] is False
        assert 'dimensionality' in result['message'] or 'convert' in result['message']
        # For completely incompatible units, we may not have a clamped_value
    
    def test_pint_parameter_validation_numeric_input(self):
        """Test validation with numeric input (assumes same units)."""
        result = self.device.validate_parameter(['frequency'], 3.0e9)  # Just a number
        assert result['valid'] is True
        assert hasattr(result['clamped_value'], 'magnitude')
        assert hasattr(result['clamped_value'], 'units')
    
    def test_pint_parameter_validation_string_input(self):
        """Test validation with string input."""
        result = self.device.validate_parameter(['frequency'], "2.85 GHz")
        assert result['valid'] is True
        assert hasattr(result['clamped_value'], 'magnitude')
        assert hasattr(result['clamped_value'], 'units')
    
    def test_pint_parameter_validation_invalid_string(self):
        """Test validation with invalid string input."""
        result = self.device.validate_parameter(['frequency'], "invalid units")
        assert result['valid'] is False
        assert 'Cannot parse' in result['message']
    
    def test_regular_parameter_validation(self):
        """Test validation of non-pint parameters."""
        result = self.device.validate_parameter(['channel'], 5)
        assert result['valid'] is True
        assert 'Parameter validation passed' in result['message']
    
    def test_parameter_validation_nonexistent_path(self):
        """Test validation with nonexistent parameter path."""
        result = self.device.validate_parameter(['nonexistent'], 5)
        assert result['valid'] is False
        assert 'not found in device settings' in result['message']


class TestDeviceUpdateAndGet:
    """Test update_and_get functionality."""
    
    def setup_method(self):
        """Set up test device."""
        self.device = TestDeviceWithUnits()
    
    def test_update_and_get_with_units(self):
        """Test update_and_get with pint quantities."""
        # Update with different units (2.85 GHz = 2.85e3 MHz)
        new_frequency = 2.85e3 * ur.MHz  # Convert to MHz
        result = self.device.update_and_get({'frequency': new_frequency})
        
        # Should return the converted value
        assert 'frequency' in result
        assert hasattr(result['frequency'], 'magnitude')
        assert hasattr(result['frequency'], 'units')
        # Should be in MHz (the units we provided)
        assert str(result['frequency'].units) == 'megahertz'
    
    def test_update_and_get_regular_parameters(self):
        """Test update_and_get with regular parameters."""
        result = self.device.update_and_get({'channel': 5, 'enabled': False})
        
        assert result['channel'] == 5
        assert result['enabled'] is False
    
    def test_update_and_get_mixed_parameters(self):
        """Test update_and_get with mixed parameter types."""
        result = self.device.update_and_get({
            'frequency': 3.0e9 * ur.Hz,
            'power': 15.0 * ur.mW,
            'channel': 2
        })
        
        assert 'frequency' in result
        assert 'power' in result
        assert result['channel'] == 2


class TestDeviceParameterRanges:
    """Test parameter range functionality."""
    
    def setup_method(self):
        """Set up test device."""
        self.device = TestDeviceWithUnits()
    
    def test_get_parameter_ranges_pint_quantity(self):
        """Test getting ranges for pint quantity parameters."""
        ranges = self.device.get_parameter_ranges(['frequency'])
        
        # Should return information about the parameter
        assert isinstance(ranges, dict)
        # The exact content depends on Parameter implementation
    
    def test_get_parameter_ranges_regular_parameter(self):
        """Test getting ranges for regular parameters."""
        ranges = self.device.get_parameter_ranges(['channel'])
        
        assert isinstance(ranges, dict)
    
    def test_get_parameter_ranges_nonexistent(self):
        """Test getting ranges for nonexistent parameter."""
        ranges = self.device.get_parameter_ranges(['nonexistent'])
        
        assert ranges == {}


class TestDeviceUnitsIntegration:
    """Test integration between units and device functionality."""
    
    def setup_method(self):
        """Set up test device."""
        self.device = TestDeviceWithUnits()
    
    def test_units_preservation_through_update(self):
        """Test that units are preserved through update operations."""
        # Get original frequency
        original_freq = self.device._settings['frequency']
        original_units = str(original_freq.units)
        
        # Update with different value but same units
        new_freq = 3.0e9 * ur.Hz
        self.device.update({'frequency': new_freq})
        
        # Check that units are preserved
        updated_freq = self.device._settings['frequency']
        assert str(updated_freq.units) == original_units
        assert updated_freq.magnitude == 3.0e9
    
    def test_units_conversion_during_update(self):
        """Test that units are preserved during update."""
        # Update frequency with different units (2.85 GHz = 2.85e6 kHz)
        new_freq = 2.85e6 * ur.kHz  # Convert to kHz
        self.device.update({'frequency': new_freq})
        
        # Should preserve the units we provided
        updated_freq = self.device._settings['frequency']
        assert str(updated_freq.units) == 'kilohertz'
        assert abs(updated_freq.magnitude - 2.85e6) < 1e-6  # Should be 2.85e6 kHz
    
    def test_mixed_units_and_regular_parameters(self):
        """Test updating both units and regular parameters together."""
        result = self.device.update_and_get({
            'frequency': 2.5e9 * ur.Hz,
            'power': 12.0 * ur.mW,
            'voltage': 3.3,
            'channel': 3,
            'enabled': False
        })
        
        # All parameters should be updated
        assert 'frequency' in result
        assert 'power' in result
        assert 'voltage' in result
        assert result['channel'] == 3
        assert result['enabled'] is False


class TestDeviceErrorHandling:
    """Test error handling in device operations."""
    
    def setup_method(self):
        """Set up test device."""
        self.device = TestDeviceWithUnits()
    
    def test_validation_error_handling(self):
        """Test that validation errors are handled gracefully."""
        # Test with invalid units
        result = self.device.validate_parameter(['frequency'], "invalid")
        assert result['valid'] is False
        assert 'error' in result['message'].lower() or 'cannot' in result['message'].lower()
    
    def test_parameter_clamping_and_feedback(self):
        """Test that update_and_get shows actual vs requested values for clamping."""
        # Create a device with clamping behavior
        class ClampingDevice(Device):
            def __init__(self):
                super().__init__()
                self._settings = Parameter([
                    Parameter('position', 0.0, float, 'Stage position', units='mm'),
                    Parameter('frequency', 2.85e9 * ur.Hz, float, 'RF frequency', units='Hz'),
                ])
                self._probes = {'position': 'Stage position in mm', 'frequency': 'RF frequency in Hz'}
            
            @property
            def _PROBES(self):
                return self._probes
            
            def read_probes(self, name=None):
                return self._settings
            
            def update(self, settings):
                # Simulate hardware clamping
                if 'position' in settings:
                    # Clamp position between -10 and 10 mm
                    requested = float(settings['position'])
                    clamped = max(-10.0, min(10.0, requested))
                    self._settings['position'] = clamped
                
                if 'frequency' in settings:
                    # Clamp frequency between 1 and 4 GHz
                    requested = settings['frequency']
                    if hasattr(requested, 'magnitude'):
                        freq_hz = requested.to('Hz').magnitude
                    else:
                        freq_hz = float(requested)
                    
                    clamped_hz = max(1e9, min(4e9, freq_hz))
                    self._settings['frequency'] = clamped_hz * ur.Hz
        
        device = ClampingDevice()
        
        # Test position clamping
        print("\n=== Position Clamping Test ===")
        print("Original position:", device._settings['position'])
        
        # User requests 50mm, should be clamped to 10mm
        result = device.update_and_get({'position': 50.0})
        actual_position = result['position']
        
        print(f"Requested: 50.0mm")
        print(f"Actual: {actual_position}mm")
        print(f"Clamped: {actual_position != 50.0}")
        
        assert actual_position == 10.0  # Should be clamped to max
        assert actual_position != 50.0  # Should be different from requested
        
        # Test frequency clamping
        print("\n=== Frequency Clamping Test ===")
        print("Original frequency:", device._settings['frequency'])
        
        # User requests 6GHz, should be clamped to 4GHz
        result = device.update_and_get({'frequency': 6e9 * ur.Hz})
        actual_frequency = result['frequency']
        
        print(f"Requested: 6.0 GHz")
        print(f"Actual: {actual_frequency}")
        print(f"Clamped: {actual_frequency != 6e9 * ur.Hz}")
        
        assert actual_frequency.magnitude == 4e9  # Should be clamped to max
        assert actual_frequency != 6e9 * ur.Hz  # Should be different from requested
        
        # Test GUI can detect clamping
        print("\n=== GUI Feedback Test ===")
        requested_pos = 50.0
        actual_pos = actual_position
        requested_freq = 6e9 * ur.Hz
        actual_freq = actual_frequency
        
        position_clamped = requested_pos != actual_pos
        frequency_clamped = requested_freq != actual_freq
        
        print(f"Position clamped: {position_clamped}")
        print(f"Frequency clamped: {frequency_clamped}")
        
        assert position_clamped is True
        assert frequency_clamped is True
        
        # Test that GUI can show helpful messages
        if position_clamped:
            print(f"⚠️  Position: Requested {requested_pos}mm, got {actual_pos}mm (clamped to hardware limits)")
        if frequency_clamped:
            print(f"⚠️  Frequency: Requested {requested_freq}, got {actual_freq} (clamped to hardware limits)")
    
    def test_error_vs_clamping_detection(self):
        """Test that the system can distinguish between errors and clamping."""
        # Create a device that can provide specific feedback
        class SmartDevice(Device):
            def __init__(self):
                super().__init__()
                self._settings = Parameter([
                    Parameter('position', 0.0, float, 'Stage position', units='mm'),
                    Parameter('frequency', 2.85e9 * ur.Hz, float, 'RF frequency', units='Hz'),
                ])
                self._probes = {'position': 'Stage position in mm', 'frequency': 'RF frequency in Hz'}
                self._last_error = None  # Track last error
            
            @property
            def _PROBES(self):
                return self._probes
            
            def read_probes(self, name=None):
                return self._settings
            
            def update(self, settings):
                # Simulate different scenarios
                if 'position' in settings:
                    requested = float(settings['position'])
                    
                    if requested == 50.0:
                        # Simulate stage error - moves to wrong position
                        self._settings['position'] = 45.0
                        self._last_error = f"Stage error: requested {requested}mm, moved to 45mm"
                    elif requested > 10.0:
                        # Simulate clamping - exceeds physical limits
                        self._settings['position'] = 10.0
                        self._last_error = f"Position clamped: {requested}mm exceeds max limit of 10mm"
                    else:
                        # Normal operation
                        self._settings['position'] = requested
                        self._last_error = None
            
            def _update_and_get_with_feedback(self, settings):
                """Enhanced version that provides specific feedback about why values changed."""
                # Store original values
                original_values = {}
                for key in settings.keys():
                    if key in self._settings:
                        original_values[key] = self._settings[key]
                
                # Update the device
                self.update(settings)
                
                # Get actual values
                actual_values = self.read_probes()
                
                # Generate detailed feedback
                feedback = {}
                for key, requested_value in settings.items():
                    if key in actual_values:
                        actual_value = actual_values[key]
                        changed = requested_value != actual_value
                        
                        if changed:
                            # Determine the reason for the change
                            if self._last_error and 'error' in self._last_error.lower():
                                reason = 'error'
                                message = self._last_error
                            elif self._last_error and 'clamped' in self._last_error.lower():
                                reason = 'clamped'
                                message = self._last_error
                            else:
                                reason = 'unknown'
                                message = f'Value changed from {requested_value} to {actual_value}'
                            
                            feedback[key] = {
                                'changed': True,
                                'requested': requested_value,
                                'actual': actual_value,
                                'reason': reason,
                                'message': message
                            }
                        else:
                            feedback[key] = {
                                'changed': False,
                                'requested': requested_value,
                                'actual': actual_value,
                                'reason': 'success',
                                'message': 'Value set successfully'
                            }
                
                return {
                    'actual_values': actual_values,
                    'feedback': feedback
                }
        
        device = SmartDevice()
        
        print("\n=== Error vs Clamping Detection Test ===")
        
        # Test 1: Stage error (not clamping)
        print("\n1. Stage Error Scenario:")
        print("   User requests: 50mm")
        print("   Stage has error and moves to: 45mm")
        
        result = device._update_and_get_with_feedback({'position': 50.0})
        feedback = result['feedback']['position']
        
        print(f"   Requested: {feedback['requested']}mm")
        print(f"   Actual: {feedback['actual']}mm")
        print(f"   Reason: {feedback['reason']}")
        print(f"   Message: {feedback['message']}")
        
        assert feedback['reason'] == 'error'
        assert 'error' in feedback['message'].lower()
        
        # Test 2: Clamping (not error)
        print("\n2. Clamping Scenario:")
        print("   User requests: 15mm (exceeds limit)")
        print("   Hardware clamps to: 10mm")
        
        result = device._update_and_get_with_feedback({'position': 15.0})
        feedback = result['feedback']['position']
        
        print(f"   Requested: {feedback['requested']}mm")
        print(f"   Actual: {feedback['actual']}mm")
        print(f"   Reason: {feedback['reason']}")
        print(f"   Message: {feedback['message']}")
        
        assert feedback['reason'] == 'clamped'
        assert 'clamped' in feedback['message'].lower()
        
        # Test 3: Normal operation
        print("\n3. Normal Operation:")
        print("   User requests: 5mm")
        print("   Stage moves to: 5mm")
        
        result = device._update_and_get_with_feedback({'position': 5.0})
        feedback = result['feedback']['position']
        
        print(f"   Requested: {feedback['requested']}mm")
        print(f"   Actual: {feedback['actual']}mm")
        print(f"   Reason: {feedback['reason']}")
        print(f"   Message: {feedback['message']}")
        
        assert feedback['reason'] == 'success'
        assert 'successfully' in feedback['message'].lower()
        
        print("\n=== GUI Feedback Examples ===")
        print("With enhanced feedback, GUI can show:")
        print("  ❌ ERROR: Stage error: requested 50.0mm, moved to 45mm")
        print("  ⚠️  CLAMPED: Position clamped: 15.0mm exceeds max limit of 10mm")
        print("  ✅ SUCCESS: Value set successfully")
    
    def test_update_error_handling(self):
        """Test that update errors are handled gracefully."""
        # This should not raise an exception
        try:
            self.device.update({'nonexistent': 'value'})
        except Exception as e:
            pytest.fail(f"Update should handle missing parameters gracefully: {e}")
    
    def test_read_probes_fallback(self):
        """Test that read_probes fallback works when no probes defined."""
        # Create device without probes
        device_no_probes = Device()
        device_no_probes._settings = {'test': 'value'}
        
        result = device_no_probes.update_and_get({'test': 'new_value'})
        assert result == {'test': 'new_value'}


if __name__ == '__main__':
    pytest.main([__file__])
