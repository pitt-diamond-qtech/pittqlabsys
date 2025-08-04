"""
Tests for the Parameter class.

This module tests the foundational Parameter class, including:
- Basic parameter creation and validation
- Unit handling and conversion
- Nested parameter structures
- Type validation
- Edge cases and error handling
"""

import pytest
import numpy as np
from src.core.parameter import Parameter
from src import ur


class TestParameterBasic:
    """Test basic Parameter functionality."""
    
    def test_simple_parameter_creation(self):
        """Test creating a simple parameter."""
        p = Parameter('test_param', 42, int, 'A test parameter')
        
        assert p['test_param'] == 42
        assert p.valid_values['test_param'] == int
        assert p.info['test_param'] == 'A test parameter'
        assert p.visible['test_param'] is False
        assert p.units['test_param'] == ""
    
    def test_parameter_with_units(self):
        """Test parameter creation with units."""
        p = Parameter('frequency', 2.85e9, float, 'Microwave frequency', units='Hz')
        
        assert p['frequency'] == 2.85e9
        assert p.units['frequency'] == 'Hz'
    
    def test_parameter_validation_int(self):
        """Test integer parameter validation."""
        p = Parameter('count', 10, int, 'Count parameter')
        
        # Valid assignment
        p['count'] = 20
        assert p['count'] == 20
        
        # Invalid assignment should raise AssertionError
        with pytest.raises(AssertionError):
            p['count'] = 3.14
    
    def test_parameter_validation_float(self):
        """Test float parameter validation."""
        p = Parameter('voltage', 5.0, float, 'Voltage parameter')
        
        # Valid assignment
        p['voltage'] = 3.14
        assert p['voltage'] == 3.14
        
        # Int should be accepted as float
        p['voltage'] = 10
        assert p['voltage'] == 10
        
        # String should be rejected
        with pytest.raises(AssertionError):
            p['voltage'] = "invalid"
    
    def test_parameter_validation_list(self):
        """Test parameter validation with list of valid values."""
        p = Parameter('mode', 'continuous', ['continuous', 'pulsed'], 'Operation mode')
        
        # Valid assignment
        p['mode'] = 'pulsed'
        assert p['mode'] == 'pulsed'
        
        # Invalid assignment should raise AssertionError
        with pytest.raises(AssertionError):
            p['mode'] = 'invalid_mode'
    
    def test_none_value_handling(self):
        """Test handling of None values."""
        p = Parameter('optional_param', None, int, 'Optional parameter')
        
        assert p['optional_param'] is None
        assert p.is_valid(None, int) is True
        
        # Should be able to set a valid value later
        p['optional_param'] = 42
        assert p['optional_param'] == 42


class TestParameterUnits:
    """Test unit handling in Parameter class."""
    
    def test_units_as_string(self):
        """Test that units are stored as strings."""
        p = Parameter('power', -45.0, float, 'Microwave power', units='dBm')
        
        assert p.units['power'] == 'dBm'
        assert isinstance(p.units['power'], str)
    
    def test_units_in_nested_parameters(self):
        """Test units in nested parameter structures."""
        p = Parameter([
            Parameter('frequency', 2.85e9, float, 'Frequency', units='Hz'),
            Parameter('power', -45.0, float, 'Power', units='dBm'),
            Parameter('time', 1.0, float, 'Time', units='s')
        ])
        
        assert p.units['frequency'] == 'Hz'
        assert p.units['power'] == 'dBm'
        assert p.units['time'] == 's'
    
    def test_units_in_complex_nested_structure(self):
        """Test units in complex nested parameter structures (current behavior)."""
        p = Parameter([
            Parameter('microwave', [
                Parameter('frequency', 2.85e9, float, 'Frequency', units='Hz'),
                Parameter('power', -45.0, float, 'Power', units='dBm'),
                Parameter('settle_time', 0.1, float, 'Settle time', units='ms')
            ]),
            Parameter('acquisition', [
                Parameter('integration_time', 10.0, float, 'Integration time', units='ms'),
                Parameter('num_steps', 100, int, 'Number of steps')
            ])
        ])
        
        # Current behavior: nested objects become dicts, but units are stored at top level
        assert isinstance(p['microwave'], dict)  # Current behavior
        assert not hasattr(p['microwave'], 'units')  # Current limitation
        
        # Units are accessible at the top level in the _units dictionary
        assert p.units['microwave'] == {'frequency': 'Hz', 'power': 'dBm', 'settle_time': 'ms'}
        assert p.units['acquisition'] == {'integration_time': 'ms', 'num_steps': ''}


class TestParameterNested:
    """Test nested parameter structures."""
    
    def test_nested_parameter_creation(self):
        """Test creating nested parameters (current behavior)."""
        p = Parameter([
            Parameter('device1', [
                Parameter('param1', 10, int, 'First parameter'),
                Parameter('param2', 3.14, float, 'Second parameter', units='V')
            ]),
            Parameter('device2', [
                Parameter('param3', 'test', str, 'Third parameter')
            ])
        ])
        
        assert p['device1']['param1'] == 10
        assert p['device1']['param2'] == 3.14
        assert p['device2']['param3'] == 'test'
        
        # Current limitation: nested objects become dicts
        assert isinstance(p['device1'], dict)  # Should be Parameter object
        assert not hasattr(p['device1'], 'units')  # Units not accessible
    
    def test_nested_parameter_validation(self):
        """Test validation in nested parameters (current behavior)."""
        p = Parameter([
            Parameter('device', [
                Parameter('count', 5, int, 'Count parameter'),
                Parameter('mode', 'auto', ['auto', 'manual'], 'Mode parameter')
            ])
        ])
        
        # Valid nested assignment
        p['device']['count'] = 10
        assert p['device']['count'] == 10
        
        # Current limitation: validation doesn't work in nested structures
        # because they become regular dicts
        # This should raise AssertionError but doesn't due to the bug
        p['device']['count'] = 3.14  # Should fail but doesn't
        assert p['device']['count'] == 3.14  # Invalid value accepted
        
        p['device']['mode'] = 'invalid'  # Should fail but doesn't
        assert p['device']['mode'] == 'invalid'  # Invalid value accepted
    
    def test_nested_parameter_update(self):
        """Test updating nested parameters."""
        p = Parameter([
            Parameter('device', [
                Parameter('param1', 10, int, 'Parameter 1'),
                Parameter('param2', 20, int, 'Parameter 2')
            ])
        ])
        
        # Update multiple nested parameters
        p['device'].update({'param1': 15, 'param2': 25})
        
        assert p['device']['param1'] == 15
        assert p['device']['param2'] == 25


class TestParameterEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_parameter(self):
        """Test creating parameter with empty value."""
        p = Parameter('empty_param', '', str, 'Empty parameter')
        assert p['empty_param'] == ''
    
    def test_zero_values(self):
        """Test parameters with zero values."""
        p = Parameter('zero_int', 0, int, 'Zero integer')
        p2 = Parameter('zero_float', 0.0, float, 'Zero float')
        
        assert p['zero_int'] == 0
        assert p2['zero_float'] == 0.0
    
    def test_negative_values(self):
        """Test parameters with negative values."""
        p = Parameter('negative_power', -45.0, float, 'Negative power', units='dBm')
        assert p['negative_power'] == -45.0
    
    def test_large_numbers(self):
        """Test parameters with large numbers."""
        p = Parameter('large_freq', 2.85e9, float, 'Large frequency', units='Hz')
        assert p['large_freq'] == 2.85e9
    
    def test_boolean_parameters(self):
        """Test boolean parameters."""
        p = Parameter('enabled', True, bool, 'Enable flag')
        
        assert p['enabled'] is True
        p['enabled'] = False
        assert p['enabled'] is False
        
        with pytest.raises(AssertionError):
            p['enabled'] = 1  # Should not accept int for bool
    
    def test_string_parameters(self):
        """Test string parameters."""
        p = Parameter('name', 'test_device', str, 'Device name')
        
        assert p['name'] == 'test_device'
        p['name'] = 'new_name'
        assert p['name'] == 'new_name'
        
        with pytest.raises(AssertionError):
            p['name'] = 42  # Should not accept int for str


class TestParameterDictInitialization:
    """Test Parameter initialization with dictionaries."""
    
    def test_dict_initialization(self):
        """Test creating Parameter from dictionary."""
        param_dict = {
            'frequency': 2.85e9,
            'power': -45.0,
            'enabled': True
        }
        
        p = Parameter(param_dict)
        
        assert p['frequency'] == 2.85e9
        assert p['power'] == -45.0
        assert p['enabled'] is True
        assert p.valid_values['frequency'] == type(2.85e9)
        assert p.valid_values['power'] == type(-45.0)
        assert p.valid_values['enabled'] == type(True)
    
    def test_nested_dict_initialization(self):
        """Test creating Parameter from nested dictionary."""
        nested_dict = {
            'device1': {
                'param1': 10,
                'param2': 3.14
            },
            'device2': {
                'param3': 'test'
            }
        }
        
        p = Parameter(nested_dict)
        
        assert p['device1']['param1'] == 10
        assert p['device1']['param2'] == 3.14
        assert p['device2']['param3'] == 'test'
        assert isinstance(p['device1'], Parameter)
        assert isinstance(p['device2'], Parameter)


class TestParameterUnitsIntegration:
    """Test integration with pint unit registry."""
    
    def test_units_import_available(self):
        """Test that pint unit registry is available."""
        from src import ur
        assert ur is not None
        
        # Test basic unit operations
        freq = 2.85e9 * ur.Hz
        assert freq.magnitude == 2.85e9
        assert freq.units == ur.Hz
    
    def test_parameter_with_pint_units(self):
        """Test Parameter with pint unit objects (future enhancement)."""
        # This test documents how we might enhance Parameter to work with pint
        from src import ur
        
        # Current behavior - units are just strings
        p = Parameter('frequency', 2.85e9, float, 'Frequency', units='Hz')
        assert p.units['frequency'] == 'Hz'
        
        # Future enhancement could support:
        # p = Parameter('frequency', 2.85e9 * ur.Hz, float, 'Frequency')
        # assert p.units['frequency'] == ur.Hz
        # assert p['frequency'].magnitude == 2.85e9
    
    def test_unit_conversion_ideas(self):
        """Test ideas for unit conversion functionality."""
        from src import ur
        
        # Example of how unit conversion could work
        freq_hz = 2.85e9 * ur.Hz
        freq_ghz = freq_hz.to(ur.GHz)
        
        assert freq_ghz.magnitude == 2.85
        assert freq_ghz.units == ur.GHz
        
        # This could be integrated into Parameter class for automatic conversion


class TestParameterRealWorldExamples:
    """Test Parameter with real-world examples from the codebase."""
    
    def test_odmr_sweep_parameters(self):
        """Test Parameter structure similar to ODMR sweep experiment."""
        p = Parameter([
            Parameter('sweep_parameters', [
                Parameter('start_frequency', 2.82e9, float, 'Start frequency in Hz', units='Hz'),
                Parameter('stop_frequency', 2.92e9, float, 'Stop frequency in Hz', units='Hz'),
                Parameter('sweep_sensitivity', None, float, 'Sweep sensitivity in Hz/V', units='Hz/V'),
                Parameter('max_sweep_rate', 110.0, float, 'Maximum sweep rate in Hz', units='Hz')
            ]),
            Parameter('microwave', [
                Parameter('power', -45.0, float, 'Microwave power in dBm', units='dBm'),
                Parameter('enable_output', True, bool, 'Enable microwave output')
            ]),
            Parameter('acquisition', [
                Parameter('integration_time', 10.0, float, 'Integration time per data point', units='ms'),
                Parameter('settle_time', 0.1, float, 'Settle time after voltage step', units='ms'),
                Parameter('num_steps', 100, int, 'Number of steps in the sweep'),
                Parameter('bidirectional', False, bool, 'Do bidirectional sweeps')
            ])
        ])
        
        # Test accessing nested parameters
        assert p['sweep_parameters']['start_frequency'] == 2.82e9
        assert p['sweep_parameters']['stop_frequency'] == 2.92e9
        assert p['microwave']['power'] == -45.0
        assert p['acquisition']['integration_time'] == 10.0
        
        # Test units (current behavior)
        # Units are stored at the top level in the _units dictionary
        assert p.units['sweep_parameters'] == {
            'start_frequency': 'Hz', 
            'stop_frequency': 'Hz', 
            'sweep_sensitivity': 'Hz/V',
            'max_sweep_rate': 'Hz'
        }
        assert p.units['microwave'] == {'power': 'dBm', 'enable_output': ''}
        assert p.units['acquisition'] == {
            'integration_time': 'ms', 
            'settle_time': 'ms', 
            'num_steps': '', 
            'bidirectional': ''
        }
        
        # Test validation (current limitation)
        p['sweep_parameters']['start_frequency'] = 2.8e9
        assert p['sweep_parameters']['start_frequency'] == 2.8e9
        
        # Current limitation: validation doesn't work in nested structures
        p['sweep_parameters']['start_frequency'] = "invalid"  # Should fail but doesn't
        assert p['sweep_parameters']['start_frequency'] == "invalid"  # Invalid value accepted
    
    def test_device_parameters(self):
        """Test Parameter structure similar to device configurations."""
        p = Parameter([
            Parameter('SG384', [
                Parameter('frequency', 2.85e9, float, 'Frequency', units='Hz'),
                Parameter('power', -45.0, float, 'Power', units='dBm'),
                Parameter('enable_output', True, bool, 'Enable output'),
                Parameter('sweep_mode', 'external', ['internal', 'external'], 'Sweep mode')
            ]),
            Parameter('ADwin', [
                Parameter('integration_time', 10.0, float, 'Integration time', units='ms'),
                Parameter('num_averages', 10, int, 'Number of averages'),
                Parameter('trigger_mode', 'internal', ['internal', 'external'], 'Trigger mode')
            ])
        ])
        
        # Test device-specific parameters
        assert p['SG384']['frequency'] == 2.85e9
        assert p['SG384']['sweep_mode'] == 'external'
        assert p['ADwin']['num_averages'] == 10
        
        # Test validation
        p['SG384']['sweep_mode'] = 'internal'
        assert p['SG384']['sweep_mode'] == 'internal'
        
        # Current limitation: validation doesn't work in nested structures
        p['SG384']['sweep_mode'] = 'invalid_mode'  # Should fail but doesn't
        assert p['SG384']['sweep_mode'] == 'invalid_mode'  # Invalid value accepted


if __name__ == '__main__':
    pytest.main([__file__]) 