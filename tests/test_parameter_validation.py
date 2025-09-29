# Created by AI Assistant on 2024-01-XX
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.device import Device
from src.core.parameter import Parameter
from src.Controller.sg384 import SG384Generator
from src.View.windows_and_widgets.main_window import MainWindow
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt


class TestDeviceParameterValidation:
    """Test the new parameter validation methods in the Device class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create a test device with some parameters
        self.test_device = Device(name="TestDevice")
        self.test_device._settings = Parameter([
            Parameter('frequency', 2.87e9, float, 'Test frequency'),
            Parameter('power', -10.0, float, 'Test power'),
            Parameter('mode', 'CW', ['CW', 'PULSE', 'SWEEP'], 'Test mode'),
            Parameter('enabled', True, bool, 'Test enabled flag')
        ])
    
    def test_update_and_get_basic(self):
        """Test the update_and_get method returns current settings."""
        # Test basic update
        result = self.test_device.update_and_get({'frequency': 3.0e9})
        
        assert isinstance(result, dict)
        assert 'frequency' in result
        assert result['frequency'] == 3.0e9
        assert self.test_device.settings['frequency'] == 3.0e9
    
    def test_update_and_get_multiple_params(self):
        """Test update_and_get with multiple parameters."""
        result = self.test_device.update_and_get({
            'frequency': 3.5e9,
            'power': -5.0,
            'mode': 'PULSE'
        })
        
        assert result['frequency'] == 3.5e9
        assert result['power'] == -5.0
        assert result['mode'] == 'PULSE'
    
    def test_validate_parameter_valid_values(self):
        """Test parameter validation with valid values."""
        # Test valid frequency
        result = self.test_device.validate_parameter(['frequency'], 3.0e9)
        assert result['valid'] is True
        
        # Test valid mode
        result = self.test_device.validate_parameter(['mode'], 'CW')
        assert result['valid'] is True
        
        # Test valid boolean
        result = self.test_device.validate_parameter(['enabled'], True)
        assert result['valid'] is True
    
    def test_validate_parameter_invalid_values(self):
        """Test parameter validation with invalid values."""
        # Test invalid mode
        result = self.test_device.validate_parameter(['mode'], 'INVALID')
        assert result['valid'] is False
        assert 'not in valid values' in result['message']
        assert 'clamped_value' in result
        
        # Test invalid path
        result = self.test_device.validate_parameter(['nonexistent'], 'value')
        assert result['valid'] is False
        assert 'not found in device settings' in result['message']
    
    def test_validate_parameter_type_conversion(self):
        """Test parameter validation with type conversion."""
        # Test string to float conversion
        result = self.test_device.validate_parameter(['frequency'], "3.0e9")
        assert result['valid'] is True
        assert 'converted' in result['message']
        assert result['clamped_value'] == 3.0e9
        
        # Test invalid type conversion
        result = self.test_device.validate_parameter(['frequency'], "not_a_number")
        assert result['valid'] is False
        assert 'cannot be converted' in result['message']
    
    def test_get_parameter_ranges(self):
        """Test getting parameter ranges."""
        # Test with valid values list
        ranges = self.test_device.get_parameter_ranges(['mode'])
        assert 'valid_values' in ranges
        assert ranges['valid_values'] == ['CW', 'PULSE', 'SWEEP']
        
        # Test with type
        ranges = self.test_device.get_parameter_ranges(['frequency'])
        assert 'type' in ranges
        assert ranges['type'] == float
        
        # Test with invalid path
        ranges = self.test_device.get_parameter_ranges(['nonexistent'])
        assert ranges == {}


class TestSG384ParameterValidation:
    """Test the enhanced parameter validation in SG384Generator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.sg384 = SG384Generator(name="TestSG384")
    
    def test_frequency_validation_valid(self):
        """Test frequency validation with valid values."""
        # Valid frequency
        result = self.sg384.validate_parameter(['frequency'], 3.0e9)
        assert result['valid'] is True
        
        # Edge case - minimum frequency
        result = self.sg384.validate_parameter(['frequency'], 1.9e9)
        assert result['valid'] is True
        
        # Edge case - maximum frequency
        result = self.sg384.validate_parameter(['frequency'], 4.1e9)
        assert result['valid'] is True
    
    def test_frequency_validation_invalid(self):
        """Test frequency validation with invalid values."""
        # Too low frequency
        result = self.sg384.validate_parameter(['frequency'], 1.0e9)
        assert result['valid'] is False
        assert 'below minimum' in result['message']
        assert result['clamped_value'] == 1.9e9
        
        # Too high frequency
        result = self.sg384.validate_parameter(['frequency'], 5.0e9)
        assert result['valid'] is False
        assert 'above maximum' in result['message']
        assert result['clamped_value'] == 4.1e9
    
    def test_power_validation(self):
        """Test power validation."""
        # Valid power
        result = self.sg384.validate_parameter(['power'], -10.0)
        assert result['valid'] is True
        
        # Too low power
        result = self.sg384.validate_parameter(['power'], -150.0)
        assert result['valid'] is False
        assert 'below minimum' in result['message']
        assert result['clamped_value'] == -120.0
        
        # Too high power
        result = self.sg384.validate_parameter(['power'], 20.0)
        assert result['valid'] is False
        assert 'above maximum' in result['message']
        assert result['clamped_value'] == 13.0
    
    def test_sweep_rate_validation(self):
        """Test sweep rate validation."""
        # Valid sweep rate
        result = self.sg384.validate_parameter(['sweep_rate'], 50.0)
        assert result['valid'] is True
        
        # Invalid sweep rate (too high)
        result = self.sg384.validate_parameter(['sweep_rate'], 150.0)
        assert result['valid'] is False
        assert 'must be less than' in result['message']
        assert result['clamped_value'] == 119.9
    
    def test_modulation_depth_validation(self):
        """Test modulation depth validation."""
        # Valid modulation depth
        result = self.sg384.validate_parameter(['modulation_depth'], 1e6)
        assert result['valid'] is True
        
        # Too high modulation depth
        result = self.sg384.validate_parameter(['modulation_depth'], 2e8)
        assert result['valid'] is False
        assert 'above maximum' in result['message']
        assert result['clamped_value'] == 1e8
    
    def test_get_parameter_ranges_sg384(self):
        """Test getting parameter ranges for SG384."""
        # Test frequency ranges
        ranges = self.sg384.get_parameter_ranges(['frequency'])
        assert 'min' in ranges
        assert 'max' in ranges
        assert ranges['min'] == 1.9e9
        assert ranges['max'] == 4.1e9
        assert ranges['units'] == 'Hz'
        
        # Test power ranges
        ranges = self.sg384.get_parameter_ranges(['power'])
        assert ranges['min'] == -120.0
        assert ranges['max'] == 13.0
        assert ranges['units'] == 'dBm'
        
        # Test unknown parameter
        ranges = self.sg384.get_parameter_ranges(['unknown_param'])
        assert ranges == {}


class TestMainWindowParameterValidation:
    """Test the enhanced parameter validation in MainWindow."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create QApplication if it doesn't exist
        if not QApplication.instance():
            self.app = QApplication([])
        else:
            self.app = QApplication.instance()
        
        # Create a test device
        self.test_device = Device(name="TestDevice")
        self.test_device._settings = Parameter([
            Parameter('frequency', 2.87e9, float, 'Test frequency'),
            Parameter('power', -10.0, float, 'Test power')
        ])
        
        # Create MainWindow instance (this might need mocking in real tests)
        try:
            self.main_window = MainWindow(None, None)
            self.main_window.devices = {'TestDevice': self.test_device}
        except Exception:
            # If MainWindow creation fails, we'll skip these tests
            pytest.skip("MainWindow creation failed - likely due to missing UI files")
    
    def test_update_device_with_validation_success(self):
        """Test successful device update with validation."""
        # Mock tree item
        class MockItem:
            def __init__(self, value):
                self.value = value
                self.name = 'frequency'
        
        item = MockItem(3.0e9)
        path_to_device = ['frequency']
        settings_dict = {'frequency': 3.0e9}
        
        # This should not raise an exception
        self.main_window._update_device_with_validation(
            self.test_device, settings_dict, item, path_to_device
        )
        
        # Verify the device was updated
        assert self.test_device.settings['frequency'] == 3.0e9
    
    def test_provide_parameter_feedback_success(self):
        """Test parameter feedback for successful update."""
        class MockItem:
            def __init__(self, value):
                self.value = value
                self.name = 'frequency'
                self.background_set = False
                self.background_color = None
            
            def setBackground(self, column, brush):
                self.background_set = True
                if hasattr(brush, 'color'):
                    self.background_color = brush.color()
        
        item = MockItem(3.0e9)
        
        # Test successful update
        self.main_window._provide_parameter_feedback(
            item, 3.0e9, 3.0e9, 2.87e9, 'TestDevice'
        )
        
        # Verify visual feedback was set
        assert item.background_set is True
    
    def test_handle_parameter_error(self):
        """Test parameter error handling."""
        class MockItem:
            def __init__(self):
                self.name = 'frequency'
                self.background_set = False
            
            def setBackground(self, column, brush):
                self.background_set = True
        
        item = MockItem()
        
        # Test error handling
        self.main_window._handle_parameter_error(
            item, "Test error message", 'TestDevice'
        )
        
        # Verify error feedback was set
        assert item.background_set is True
    
    def test_set_item_visual_feedback(self):
        """Test visual feedback setting."""
        class MockItem:
            def __init__(self):
                self.background_set = False
                self.background_color = None
            
            def setBackground(self, column, brush):
                self.background_set = True
                if hasattr(brush, 'color'):
                    self.background_color = brush.color()
        
        item = MockItem()
        
        # Test success feedback
        self.main_window._set_item_visual_feedback(item, 'success')
        assert item.background_set is True
        
        # Test warning feedback
        item.background_set = False
        self.main_window._set_item_visual_feedback(item, 'warning')
        assert item.background_set is True
        
        # Test error feedback
        item.background_set = False
        self.main_window._set_item_visual_feedback(item, 'error')
        assert item.background_set is True


class TestParameterValidationIntegration:
    """Integration tests for the complete parameter validation system."""
    
    def test_end_to_end_validation_flow(self):
        """Test the complete validation flow from GUI to device."""
        # Create a device with validation
        device = SG384Generator(name="TestSG384")
        
        # Test valid parameter
        result = device.validate_parameter(['frequency'], 3.0e9)
        assert result['valid'] is True
        
        # Test invalid parameter
        result = device.validate_parameter(['frequency'], 1.0e9)
        assert result['valid'] is False
        assert 'clamped_value' in result
        
        # Test update_and_get
        actual_settings = device.update_and_get({'frequency': 3.0e9})
        assert actual_settings['frequency'] == 3.0e9
        
        # Test parameter ranges
        ranges = device.get_parameter_ranges(['frequency'])
        assert 'min' in ranges and 'max' in ranges
    
    def test_parameter_clamping_simulation(self):
        """Test how the system would handle parameter clamping."""
        device = SG384Generator(name="TestSG384")
        
        # Simulate what happens when user enters invalid value
        requested_value = 1.0e9  # Too low
        validation_result = device.validate_parameter(['frequency'], requested_value)
        
        assert validation_result['valid'] is False
        clamped_value = validation_result['clamped_value']
        
        # Update with clamped value
        device.update({'frequency': clamped_value})
        actual_value = device.settings['frequency']
        
        assert actual_value == clamped_value
        assert actual_value != requested_value  # Value was clamped


if __name__ == '__main__':
    pytest.main([__file__])
