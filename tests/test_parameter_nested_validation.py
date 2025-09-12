#!/usr/bin/env python3
"""
Test for nested parameter validation when loading experiments.

This test specifically covers the case where valid_values is a list of Parameter
objects but the value is a dictionary (common when loading from .aqs files).
"""

import pytest
import sys
import os

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.core.parameter import Parameter


class TestParameterNestedValidation:
    """Test nested parameter validation logic."""
    
    def test_dict_value_with_list_valid_values(self):
        """Test validation when value is dict but valid_values is list of Parameters."""
        # Create a list of Parameter objects (like frequency_range)
        valid_values = [
            Parameter('start', 2.7e9, float, 'Start frequency in Hz', units='Hz'),
            Parameter('stop', 3.0e9, float, 'Stop frequency in Hz', units='Hz')
        ]
        
        # Test valid dictionary value
        valid_value = {'start': 2.7e9, 'stop': 3.0e9}
        assert Parameter.is_valid(valid_value, valid_values) == True
        
        # Test with different valid values
        valid_value2 = {'start': 2.5e9, 'stop': 3.2e9}
        assert Parameter.is_valid(valid_value2, valid_values) == True
        
        # Test with missing key (should be invalid)
        invalid_value1 = {'start': 2.7e9}  # missing 'stop'
        assert Parameter.is_valid(invalid_value1, valid_values) == False
        
        # Test with extra key (should be invalid)
        invalid_value2 = {'start': 2.7e9, 'stop': 3.0e9, 'extra': 1.0}
        assert Parameter.is_valid(invalid_value2, valid_values) == False
        
        # Test with wrong type
        invalid_value3 = {'start': '2.7e9', 'stop': 3.0e9}  # string instead of float
        assert Parameter.is_valid(invalid_value3, valid_values) == False
    
    def test_dict_value_with_dict_valid_values(self):
        """Test that existing dict-to-dict validation still works."""
        valid_values = {
            'start': float,
            'stop': float
        }
        
        valid_value = {'start': 2.7e9, 'stop': 3.0e9}
        assert Parameter.is_valid(valid_value, valid_values) == True
        
        invalid_value = {'start': 2.7e9}  # missing 'stop'
        assert Parameter.is_valid(invalid_value, valid_values) == False
    
    def test_nested_parameter_validation(self):
        """Test validation with more complex nested parameters."""
        # Create nested parameters like in ODMRSweepContinuousExperiment
        valid_values = [
            Parameter('microwave', [
                Parameter('power', -10.0, float, 'Power in dBm'),
                Parameter('step_freq', 1e6, float, 'Step frequency in Hz')
            ]),
            Parameter('acquisition', [
                Parameter('integration_time', 0.001, float, 'Integration time in s'),
                Parameter('averages', 10, int, 'Number of averages')
            ])
        ]
        
        # Test valid nested dictionary
        valid_value = {
            'microwave': {'power': -5.0, 'step_freq': 2e6},
            'acquisition': {'integration_time': 0.002, 'averages': 5}
        }
        assert Parameter.is_valid(valid_value, valid_values) == True
        
        # Test with missing nested key
        invalid_value = {
            'microwave': {'power': -5.0},  # missing 'step_freq'
            'acquisition': {'integration_time': 0.002, 'averages': 5}
        }
        assert Parameter.is_valid(invalid_value, valid_values) == False
    
    def test_edge_cases(self):
        """Test edge cases for the new validation logic."""
        valid_values = [
            Parameter('start', 2.7e9, float, 'Start frequency in Hz'),
            Parameter('stop', 3.0e9, float, 'Stop frequency in Hz')
        ]
        
        # Test with empty dictionary
        assert Parameter.is_valid({}, valid_values) == False
        
        # Test with None value
        assert Parameter.is_valid(None, valid_values) == False
        
        # Test with non-dict value
        assert Parameter.is_valid("not a dict", valid_values) == False
        
        # Test with empty valid_values list
        assert Parameter.is_valid({'start': 2.7e9, 'stop': 3.0e9}, []) == True  # Should pass if no validation rules
    
    def test_parameter_name_matching(self):
        """Test that parameter names are correctly matched."""
        valid_values = [
            Parameter('frequency_start', 2.7e9, float, 'Start frequency'),
            Parameter('frequency_stop', 3.0e9, float, 'Stop frequency')
        ]
        
        # Test with correct parameter names
        valid_value = {'frequency_start': 2.7e9, 'frequency_stop': 3.0e9}
        assert Parameter.is_valid(valid_value, valid_values) == True
        
        # Test with wrong parameter names
        invalid_value = {'start': 2.7e9, 'stop': 3.0e9}  # wrong names
        assert Parameter.is_valid(invalid_value, valid_values) == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
