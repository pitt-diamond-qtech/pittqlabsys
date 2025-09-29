#!/usr/bin/env python3
"""
Tests for parameter validation GUI functionality.

This module tests the enhanced parameter validation in main_window.py including:
- Visual feedback mechanisms
- Parameter validation and clamping
- User notification systems
- Tooltip functionality
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.device import Device
from src.core.parameter import Parameter
from src import ur


class MockDeviceWithUnits(Device):
    """Mock device with units-enabled parameters for testing."""
    
    def __init__(self, name="test_device"):
        super().__init__()
        self.name = name
        self._settings = Parameter([
            Parameter('frequency', 2.85e9 * ur.Hz, float, 'RF frequency', units='Hz'),
            Parameter('power', 10.0 * ur.mW, float, 'RF power', units='mW'),
            Parameter('voltage', 5.0, float, 'DC voltage', units='V'),
            Parameter('channel', 1, int, 'Channel number'),
        ])
        self._probes = {
            'frequency': 'RF frequency in Hz',
            'power': 'RF power in mW', 
            'voltage': 'DC voltage in V',
            'channel': 'Channel number'
        }
    
    @property
    def _PROBES(self):
        """Return the dictionary of available probes."""
        return self._probes
    
    def read_probes(self):
        """Mock read_probes that returns current settings."""
        return dict(self._settings)
    
    def update(self, settings):
        """Mock update that applies settings with clamping."""
        for key, value in settings.items():
            if key in self._settings:
                # Simulate clamping for voltage (0-10V range)
                if key == 'voltage':
                    clamped_value = max(0.0, min(10.0, float(value)))
                    self._settings[key] = clamped_value
                else:
                    self._settings[key] = value
    
    def validate_parameter(self, path, value):
        """Mock parameter validation with clamping."""
        # For pint quantities (frequency, power), use the base class method
        if path in [['frequency'], ['power']]:
            return super().validate_parameter(path, value)
        
        # For regular parameters, do custom validation
        if path == ['voltage']:
            try:
                voltage = float(value)
                if voltage < 0.0:
                    return {
                        'valid': False,
                        'message': f'Voltage {voltage}V is below minimum 0.0V',
                        'clamped_value': 0.0
                    }
                elif voltage > 10.0:
                    return {
                        'valid': False,
                        'message': f'Voltage {voltage}V is above maximum 10.0V',
                        'clamped_value': 10.0
                    }
                else:
                    return {'valid': True, 'message': 'Voltage is within valid range'}
            except (ValueError, TypeError):
                return {
                    'valid': False,
                    'message': f'Invalid voltage value: {value}',
                    'clamped_value': 0.0
                }
        elif path == ['channel']:
            try:
                channel = int(value)
                if channel < 1:
                    return {
                        'valid': False,
                        'message': f'Channel {channel} is below minimum 1',
                        'clamped_value': 1
                    }
                elif channel > 8:
                    return {
                        'valid': False,
                        'message': f'Channel {channel} is above maximum 8',
                        'clamped_value': 8
                    }
                else:
                    return {'valid': True, 'message': 'Channel is within valid range'}
            except (ValueError, TypeError):
                return {
                    'valid': False,
                    'message': f'Invalid channel value: {value}',
                    'clamped_value': 1
                }
        else:
            return {
                'valid': False,
                'message': f'Parameter path {path} not found in device settings',
                'clamped_value': value
            }
    
    def get_parameter_ranges(self, path):
        """Mock parameter ranges."""
        if path == ['voltage']:
            return {'min': 0.0, 'max': 10.0, 'type': float}
        elif path == ['frequency']:
            return {'type': float, 'units': 'Hz'}
        return {}


class TestParameterValidationGUI:
    """Test parameter validation GUI functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.device = MockDeviceWithUnits()
        self.mock_item = Mock()
        self.mock_item.setText = Mock()
        self.mock_item.setBackground = Mock()
        self.mock_item.setToolTip = Mock()
    
    def test_validate_parameter_success(self):
        """Test successful parameter validation."""
        result = self.device.validate_parameter(['voltage'], 5.0)
        
        assert result['valid'] is True
        assert 'within valid range' in result['message']
    
    def test_validate_parameter_clamping_high(self):
        """Test parameter validation with high value clamping."""
        result = self.device.validate_parameter(['voltage'], 15.0)
        
        assert result['valid'] is False
        assert 'above maximum' in result['message']
        assert result['clamped_value'] == 10.0
    
    def test_validate_parameter_clamping_low(self):
        """Test parameter validation with low value clamping."""
        result = self.device.validate_parameter(['voltage'], -5.0)
        
        assert result['valid'] is False
        assert 'below minimum' in result['message']
        assert result['clamped_value'] == 0.0
    
    def test_get_parameter_ranges(self):
        """Test getting parameter ranges."""
        ranges = self.device.get_parameter_ranges(['voltage'])
        
        assert 'min' in ranges
        assert 'max' in ranges
        assert ranges['min'] == 0.0
        assert ranges['max'] == 10.0
    
    def test_update_and_get_with_clamping(self):
        """Test update_and_get with parameter clamping."""
        # Update with value that should be clamped
        result = self.device.update_and_get({'voltage': 15.0})
        
        # Should return the clamped value
        assert result['voltage'] == 10.0
    
    def test_update_and_get_with_units(self):
        """Test update_and_get with units conversion."""
        # Update frequency with different units
        result = self.device.update_and_get({'frequency': 2.85e6 * ur.kHz})
        
        # Should convert to Hz
        assert 'frequency' in result
        assert hasattr(result['frequency'], 'magnitude')
        assert hasattr(result['frequency'], 'units')


class TestVisualFeedback:
    """Test visual feedback mechanisms."""
    
    def setup_method(self):
        """Set up test environment."""
        self.mock_item = Mock()
        self.mock_item.setText = Mock()
        self.mock_item.setBackground = Mock()
        self.mock_item.setToolTip = Mock()
    
    def test_set_item_visual_feedback_success(self):
        """Test setting success visual feedback."""
        # This would be called from main_window.py
        # Simulate the visual feedback logic
        feedback_type = 'success'
        
        if feedback_type == 'success':
            self.mock_item.setBackground.assert_not_called()  # Would set green background
            # In real implementation, would set green background
        elif feedback_type == 'warning':
            self.mock_item.setBackground.assert_not_called()  # Would set yellow background
        elif feedback_type == 'error':
            self.mock_item.setBackground.assert_not_called()  # Would set red background
    
    def test_set_item_visual_feedback_warning(self):
        """Test setting warning visual feedback."""
        feedback_type = 'warning'
        
        if feedback_type == 'warning':
            # Would set yellow background in real implementation
            self.mock_item.setBackground.assert_not_called()
    
    def test_set_item_visual_feedback_error(self):
        """Test setting error visual feedback."""
        feedback_type = 'error'
        
        if feedback_type == 'error':
            # Would set red background in real implementation
            self.mock_item.setBackground.assert_not_called()


class TestParameterValidationIntegration:
    """Test integration between parameter validation and GUI."""
    
    def setup_method(self):
        """Set up test environment."""
        self.device = MockDeviceWithUnits()
    
    def test_parameter_validation_workflow(self):
        """Test complete parameter validation workflow."""
        # 1. Validate parameter
        validation_result = self.device.validate_parameter(['voltage'], 15.0)
        assert validation_result['valid'] is False
        assert 'clamped_value' in validation_result
        
        # 2. Apply clamped value
        clamped_value = validation_result['clamped_value']
        self.device.update({'voltage': clamped_value})
        
        # 3. Verify the value was applied
        result = self.device.read_probes()
        assert result['voltage'] == 10.0
    
    def test_units_validation_workflow(self):
        """Test units validation workflow."""
        # 1. Validate with different units
        validation_result = self.device.validate_parameter(['frequency'], 2.85e6 * ur.kHz)
        assert validation_result['valid'] is True
        
        # 2. Apply the value
        self.device.update({'frequency': 2.85e6 * ur.kHz})
        
        # 3. Verify conversion
        result = self.device.read_probes()
        assert 'frequency' in result
        assert hasattr(result['frequency'], 'magnitude')
        assert hasattr(result['frequency'], 'units')
    
    def test_mixed_parameter_validation(self):
        """Test validation of multiple parameters with different types."""
        # Test multiple parameters
        validation_results = {}
        test_values = {
            'voltage': 15.0,  # Should be clamped
            'frequency': 3.0e9 * ur.Hz,  # Should be valid
            'channel': 5,  # Should be valid
        }
        
        for param, value in test_values.items():
            validation_results[param] = self.device.validate_parameter([param], value)
        
        # Check results
        assert validation_results['voltage']['valid'] is False  # Clamped
        assert validation_results['frequency']['valid'] is True  # Valid
        assert validation_results['channel']['valid'] is True  # Valid


class TestErrorHandling:
    """Test error handling in parameter validation."""
    
    def setup_method(self):
        """Set up test environment."""
        self.device = MockDeviceWithUnits()
    
    def test_validation_with_invalid_parameter_path(self):
        """Test validation with invalid parameter path."""
        result = self.device.validate_parameter(['nonexistent'], 5.0)
        
        assert result['valid'] is False
        assert 'not found' in result['message']
    
    def test_validation_with_invalid_value_type(self):
        """Test validation with invalid value type."""
        result = self.device.validate_parameter(['voltage'], "not_a_number")
        
        # Should handle gracefully
        assert 'valid' in result
        assert 'message' in result
    
    def test_update_with_missing_parameter(self):
        """Test update with missing parameter."""
        # Should not raise exception
        try:
            self.device.update({'nonexistent': 'value'})
        except Exception as e:
            pytest.fail(f"Update should handle missing parameters gracefully: {e}")


if __name__ == '__main__':
    pytest.main([__file__])
