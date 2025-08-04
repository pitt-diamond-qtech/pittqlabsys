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
from src.core.parameter import Parameter, ValidationError
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
        """Test units in complex nested parameter structures (fixed behavior)."""
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
        
        # Fixed: nested objects are now Parameter objects
        assert isinstance(p['microwave'], Parameter)  # Now a Parameter object
        assert hasattr(p['microwave'], 'units')  # Units are accessible
        
        # Units are accessible directly in nested Parameter objects
        assert p['microwave'].units['frequency'] == 'Hz'
        assert p['microwave'].units['power'] == 'dBm'
        assert p['microwave'].units['settle_time'] == 'ms'
        assert p['acquisition'].units['integration_time'] == 'ms'
        assert p['acquisition'].units['num_steps'] == ''


class TestParameterNested:
    """Test nested parameter structures."""
    
    def test_nested_parameter_creation(self):
        """Test creating nested parameters (fixed behavior)."""
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
        
        # Fixed: nested objects are now Parameter objects
        assert isinstance(p['device1'], Parameter)  # Now a Parameter object
        assert hasattr(p['device1'], 'units')  # Units are accessible
        assert p['device1'].units['param2'] == 'V'  # Units work correctly
    
    def test_nested_parameter_validation(self):
        """Test validation in nested parameters (fixed behavior)."""
        p = Parameter([
            Parameter('device', [
                Parameter('count', 5, int, 'Count parameter'),
                Parameter('mode', 'auto', ['auto', 'manual'], 'Mode parameter')
            ])
        ])
        
        # Valid nested assignment
        p['device']['count'] = 10
        assert p['device']['count'] == 10
        
        # Fixed: validation now works in nested structures
        with pytest.raises(AssertionError):
            p['device']['count'] = 3.14  # Should fail and does
        
        with pytest.raises(AssertionError):
            p['device']['mode'] = 'invalid'  # Should fail and does
    
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
        """Test Parameter with pint unit objects (Phase 2 enhancement)."""
        from src import ur
        
        # Test pint Quantity support
        p = Parameter('frequency', 2.85e9 * ur.Hz, float, 'Frequency')
        assert p.is_pint_quantity()
        assert p['frequency'].magnitude == 2.85e9
        assert p['frequency'].units == ur.Hz
    
    def test_unit_conversion_methods(self):
        """Test unit conversion functionality."""
        from src import ur
        
        # Create parameter with pint Quantity
        p = Parameter('frequency', 2.85e9 * ur.Hz, float, 'Frequency')
        
        # Test get_value_in_units
        freq_ghz = p.get_value_in_units('GHz')
        assert freq_ghz.magnitude == 2.85
        assert freq_ghz.units == ur.GHz
        
        freq_mhz = p.get_value_in_units('MHz')
        assert freq_mhz.magnitude == 2850.0
        assert freq_mhz.units == ur.MHz
    
    def test_set_value_with_units(self):
        """Test setting values with units."""
        from src import ur
        
        p = Parameter('frequency', 2.85e9 * ur.Hz, float, 'Frequency')
        
        # Set value with units
        p.set_value_with_units(2.9, 'GHz')
        assert p['frequency'].magnitude == 2.9
        assert p['frequency'].units == ur.GHz
    
    def test_convert_units(self):
        """Test converting units in place."""
        from src import ur
        
        p = Parameter('frequency', 2.85e9 * ur.Hz, float, 'Frequency')
        
        # Convert to GHz in place
        p.convert_units('GHz')
        assert p['frequency'].magnitude == 2.85
        assert p['frequency'].units == ur.GHz
    
    def test_get_unit_info(self):
        """Test getting detailed unit information."""
        from src import ur
        
        p = Parameter('frequency', 2.85e9 * ur.Hz, float, 'Frequency')
        
        info = p.get_unit_info()
        assert info['is_pint_quantity'] is True
        assert info['magnitude'] == 2.85e9
        assert info['units'] == ur.Hz
        assert info['units_string'] == 'hertz'
        assert 'time' in info['dimensionality']  # Frequency has 1/[time] dimensionality
    
    def test_validate_units(self):
        """Test unit validation."""
        from src import ur
        
        p = Parameter('frequency', 2.85e9 * ur.Hz, float, 'Frequency')
        
        # Test compatible units
        assert p.validate_units('Hz', 'GHz') is True
        assert p.validate_units('Hz', 'MHz') is True
        
        # Test incompatible units
        with pytest.raises(ValueError):
            p.validate_units('Hz', 'kg')
    
    def test_get_compatible_units(self):
        """Test getting compatible units."""
        from src import ur
        
        p = Parameter('frequency', 2.85e9 * ur.Hz, float, 'Frequency')
        
        compatible_units = p.get_compatible_units()
        assert 'Hz' in compatible_units
        # Note: The get_compatible_units method finds units with same dimensionality
        # but may not include all expected units due to pint's unit registry
        assert len(compatible_units) > 0
    
    def test_backward_compatibility_with_string_units(self):
        """Test that string-based units still work."""
        p = Parameter('frequency', 2.85e9, float, 'Frequency', units='Hz')
        
        # Should not be a pint quantity
        assert not p.is_pint_quantity()
        
        # Should return original value for get_value_in_units
        assert p.get_value_in_units('GHz') == 2.85e9
        
        # Should have string unit info
        info = p.get_unit_info()
        assert info['is_pint_quantity'] is False
        assert info['units_string'] == 'Hz'
    
    def test_nested_pint_quantities(self):
        """Test pint quantities in nested Parameter structures."""
        from src import ur
        
        p = Parameter([
            Parameter('microwave', [
                Parameter('frequency', 2.85e9 * ur.Hz, float, 'Frequency'),
                Parameter('power', -45.0, float, 'Power', units='dBm')  # Use string units for dBm
            ])
        ])
        
        # Test nested pint quantities
        assert p['microwave'].is_pint_quantity('frequency')
        assert not p['microwave'].is_pint_quantity('power')  # power uses string units, not pint
        
        # Test unit conversion in nested structure
        freq_ghz = p['microwave'].get_value_in_units('GHz', 'frequency')
        assert freq_ghz.magnitude == 2.85
        assert freq_ghz.units == ur.GHz
    
    def test_mixed_pint_and_string_units(self):
        """Test mixing pint quantities and string units."""
        from src import ur
        
        p = Parameter([
            Parameter('microwave', [
                Parameter('frequency', 2.85e9 * ur.Hz, float, 'Frequency'),
                Parameter('enable_output', True, bool, 'Enable output')
            ])
        ])
        
        # Test mixed types
        assert p['microwave'].is_pint_quantity('frequency')
        assert not p['microwave'].is_pint_quantity('enable_output')
        
        # Test unit conversion only works for pint quantities
        freq_ghz = p['microwave'].get_value_in_units('GHz', 'frequency')
        assert freq_ghz.magnitude == 2.85
        
        # Non-pint quantity should return original value
        result = p['microwave'].get_value_in_units('invalid', 'enable_output')
        assert result is True


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
        
        # Test units (fixed behavior)
        # Units are now accessible directly in nested Parameter objects
        assert p['sweep_parameters'].units['start_frequency'] == 'Hz'
        assert p['sweep_parameters'].units['stop_frequency'] == 'Hz'
        assert p['sweep_parameters'].units['sweep_sensitivity'] == 'Hz/V'
        assert p['sweep_parameters'].units['max_sweep_rate'] == 'Hz'
        assert p['microwave'].units['power'] == 'dBm'
        assert p['microwave'].units['enable_output'] == ''
        assert p['acquisition'].units['integration_time'] == 'ms'
        assert p['acquisition'].units['settle_time'] == 'ms'
        assert p['acquisition'].units['num_steps'] == ''
        assert p['acquisition'].units['bidirectional'] == ''
        
        # Test validation (fixed behavior)
        p['sweep_parameters']['start_frequency'] = 2.8e9
        assert p['sweep_parameters']['start_frequency'] == 2.8e9
        
        # Fixed: validation now works in nested structures
        with pytest.raises(AssertionError):
            p['sweep_parameters']['start_frequency'] = "invalid"  # Should fail and does
    
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
        
        # Fixed: validation now works in nested structures
        with pytest.raises(AssertionError):
            p['SG384']['sweep_mode'] = 'invalid_mode'  # Should fail and does


class TestParameterPhase3Features:
    """Test Phase 3 features: caching, serialization, enhanced validation, and GUI integration."""
    
    def test_caching_system(self):
        """Test the caching system for unit conversions."""
        from src import ur
        
        p = Parameter('frequency', 2.85e9 * ur.Hz, float, 'Frequency')
        
        # First call should cache the result
        freq_ghz_1 = p.get_value_in_units('GHz')
        
        # Second call should use cached result
        freq_ghz_2 = p.get_value_in_units('GHz')
        
        assert freq_ghz_1 == freq_ghz_2
        assert freq_ghz_1.magnitude == 2.85
        
        # Check cache stats
        stats = p.get_cache_stats()
        assert stats['conversion_cache_size'] > 0
        assert stats['max_cache_size'] == 100
    
    def test_cache_clear(self):
        """Test cache clearing functionality."""
        from src import ur
        
        p = Parameter('frequency', 2.85e9 * ur.Hz, float, 'Frequency')
        
        # Populate cache
        p.get_value_in_units('GHz')
        p.get_value_in_units('MHz')
        
        # Clear cache
        p.clear_cache()
        
        stats = p.get_cache_stats()
        assert stats['conversion_cache_size'] == 0
        assert stats['validation_cache_size'] == 0
    
    def test_json_serialization_pint_quantity(self):
        """Test JSON serialization with pint quantities."""
        from src import ur
        
        p = Parameter('frequency', 2.85e9 * ur.Hz, float, 'Frequency')
        
        # Serialize
        json_data = p.to_json()
        
        # Check structure
        assert 'frequency' in json_data
        assert json_data['frequency']['pint_quantity'] is True
        assert json_data['frequency']['value'] == 2.85e9
        assert json_data['frequency']['units'] == 'hertz'
        
        # Deserialize
        p2 = Parameter.from_json(json_data)
        
        # Check restoration
        assert p2['frequency'] == p['frequency']
        assert p2.is_pint_quantity('frequency')
        assert p2['frequency'].magnitude == 2.85e9
        assert p2['frequency'].units == ur.Hz
    
    def test_json_serialization_string_units(self):
        """Test JSON serialization with string units."""
        p = Parameter('voltage', 5.0, float, 'Voltage', units='V')
        
        # Serialize
        json_data = p.to_json()
        
        # Check structure
        assert 'voltage' in json_data
        assert json_data['voltage']['pint_quantity'] is False
        assert json_data['voltage']['value'] == 5.0
        assert json_data['voltage']['units'] == 'V'
        
        # Deserialize
        p2 = Parameter.from_json(json_data)
        
        # Check restoration
        assert p2['voltage'] == p['voltage']
        assert not p2.is_pint_quantity('voltage')
        assert p2.units['voltage'] == 'V'
    
    def test_json_serialization_nested_parameters(self):
        """Test JSON serialization with nested parameters."""
        from src import ur
        
        p = Parameter([
            Parameter('microwave', [
                Parameter('frequency', 2.85e9 * ur.Hz, float, 'Frequency'),
                Parameter('power', -45.0, float, 'Power', units='dBm')
            ])
        ])
        
        # Serialize
        json_data = p.to_json()
        
        # Check nested structure
        assert 'microwave' in json_data
        assert 'frequency' in json_data['microwave']
        assert 'power' in json_data['microwave']
        
        # Deserialize
        p2 = Parameter.from_json(json_data)
        
        # Check restoration
        assert p2['microwave']['frequency'] == p['microwave']['frequency']
        assert p2['microwave']['power'] == p['microwave']['power']
    
    def test_range_validation(self):
        """Test range validation functionality."""
        p = Parameter('voltage', 5.0, float, 'Voltage', min_value=0.0, max_value=10.0)
        
        # Valid assignments
        p['voltage'] = 3.0  # Should work
        p['voltage'] = 7.0  # Should work
        
        # Invalid assignments
        with pytest.raises(ValidationError):
            p['voltage'] = -1.0  # Below minimum
        
        with pytest.raises(ValidationError):
            p['voltage'] = 15.0  # Above maximum
    
    def test_pattern_validation(self):
        """Test pattern validation functionality."""
        p = Parameter('filename', 'data.txt', str, 'Filename', 
                     pattern=r'^[a-zA-Z0-9_]+\.txt$')
        
        # Valid assignments
        p['filename'] = 'experiment.txt'  # Should work
        p['filename'] = 'data_123.txt'    # Should work
        
        # Invalid assignments
        with pytest.raises(ValidationError):
            p['filename'] = 'data.csv'  # Wrong extension
        
        with pytest.raises(ValidationError):
            p['filename'] = 'data file.txt'  # Contains space
    
    def test_custom_validation(self):
        """Test custom validation functionality."""
        def validate_frequency(value):
            return 1e6 <= value <= 10e9
        
        p = Parameter('frequency', 2.85e9, float, 'Frequency', validator=validate_frequency)
        
        # Valid assignments
        p['frequency'] = 5e9  # Should work
        
        # Invalid assignments
        with pytest.raises(ValidationError):
            p['frequency'] = 0.5e6  # Below minimum
        
        with pytest.raises(ValidationError):
            p['frequency'] = 15e9  # Above maximum
    
    def test_validation_caching(self):
        """Test that validation results are cached."""
        p = Parameter('voltage', 5.0, float, 'Voltage', min_value=0.0, max_value=10.0)
        
        # First validation should populate cache
        p['voltage'] = 3.0
        
        # Second validation should use cache
        p['voltage'] = 3.0
        
        stats = p.get_cache_stats()
        assert stats['validation_cache_size'] > 0
    

    
    def test_backward_compatibility_phase3(self):
        """Test that Phase 3 features don't break existing functionality."""
        # Test that existing parameter creation still works
        p = Parameter('test', 42, int, 'Test parameter')
        assert p['test'] == 42
        
        # Test that existing validation still works
        with pytest.raises(AssertionError):
            p['test'] = "invalid_string"
        
        # Test that existing units still work
        p2 = Parameter('voltage', 5.0, float, 'Voltage', units='V')
        assert p2.units['voltage'] == 'V'
    
    def test_mixed_validation_rules(self):
        """Test combining multiple validation rules."""
        def validate_positive(value):
            return value > 0
        
        p = Parameter('value', 5.0, float, 'Value', 
                     min_value=0.0, max_value=10.0, validator=validate_positive)
        
        # Valid assignments
        p['value'] = 3.0  # Within range and positive
        
        # Invalid assignments
        with pytest.raises(ValidationError):
            p['value'] = -1.0  # Negative (fails custom validator)
        
        with pytest.raises(ValidationError):
            p['value'] = 15.0  # Above maximum (fails range validation)
    
    def test_validation_error_messages(self):
        """Test that validation errors provide clear messages."""
        p = Parameter('voltage', 5.0, float, 'Voltage', min_value=0.0, max_value=10.0)
        
        try:
            p['voltage'] = 15.0
            assert False, "Should have raised ValidationError"
        except ValidationError as e:
            assert "above maximum" in str(e)
            assert "15.0" in str(e)
            assert "10.0" in str(e)
    
    def test_cache_lru_behavior(self):
        """Test that cache implements LRU behavior."""
        from src import ur
        
        p = Parameter('frequency', 2.85e9 * ur.Hz, float, 'Frequency')
        
        # Set small cache size for testing
        p._cache_max_size = 2
        
        # Populate cache
        p.get_value_in_units('GHz')
        p.get_value_in_units('MHz')
        
        # Add one more to trigger LRU
        p.get_value_in_units('kHz')
        
        # Check cache size
        stats = p.get_cache_stats()
        assert stats['conversion_cache_size'] <= 2


if __name__ == '__main__':
    pytest.main([__file__]) 