"""
Test cases for device inheritance patterns and parameter merging.

Tests the _get_base_settings() helper method and ensures that subclasses
properly inherit all base class parameters without breaking existing functionality.
"""

import pytest
from unittest.mock import Mock, patch

from src.core.device import Device
from src.core.parameter import Parameter
from src.Controller.mw_generator_base import MicrowaveGeneratorBase
from src.Controller.sg384 import SG384Generator


class TestDeviceInheritance:
    """Test cases for device inheritance patterns."""
    
    def test_device_get_base_settings(self):
        """Test that Device._get_base_settings() returns correct parameters."""
        base_settings = Device._get_base_settings()
        
        # Should return a list of Parameter objects
        assert isinstance(base_settings, list)
        assert len(base_settings) > 0
        assert all(isinstance(param, Parameter) for param in base_settings)
        
        # Should include the default parameter
        param_names = [param.name for param in base_settings]
        assert "default" in param_names
    
    def test_microwave_generator_base_inheritance(self):
        """Test that MicrowaveGeneratorBase properly inherits from Device."""
        # Test that MicrowaveGeneratorBase has its own parameters
        base_params = set(MicrowaveGeneratorBase._DEFAULT_SETTINGS.keys())
        assert len(base_params) > 0
        
        # Should have connection-related parameters
        expected_params = {
            'connection_type', 'ip_address', 'port', 'connection_timeout', 
            'socket_timeout', 'visa_resource', 'baud_rate', 'frequency', 
            'power', 'phase', 'amplitude'
        }
        assert expected_params.issubset(base_params)
    
    def test_sg384_inheritance_from_base(self):
        """Test that SG384 properly inherits all base class parameters."""
        # Get parameters from both classes
        base_params = set(MicrowaveGeneratorBase._DEFAULT_SETTINGS.keys())
        sg384_params = set(SG384Generator._DEFAULT_SETTINGS.keys())
        
        # SG384 should have all base class parameters
        assert base_params.issubset(sg384_params), f"Missing base parameters: {base_params - sg384_params}"
        
        # SG384 should have additional specific parameters
        sg384_specific = sg384_params - base_params
        assert len(sg384_specific) > 0, "SG384 should have device-specific parameters"
        
        # Should have the critical parameters we fixed
        assert 'connection_timeout' in sg384_params
        assert 'socket_timeout' in sg384_params
        assert 'ip_address' in sg384_params  # This should be overridden
    
    def test_sg384_parameter_values(self):
        """Test that SG384 parameter values are correct."""
        sg384_params = SG384Generator._DEFAULT_SETTINGS
        
        # Test that critical parameters have correct values
        assert sg384_params['connection_timeout'] == 10.0
        assert sg384_params['socket_timeout'] == 5.0
        assert sg384_params['ip_address'] == '192.168.2.217'  # Overridden value
        assert sg384_params['port'] == 5025
        assert sg384_params['connection_type'] == 'LAN'
    
    def test_parameter_merging_approach(self):
        """Test that the parameter merging approach works correctly."""
        # Test the helper method from MicrowaveGeneratorBase
        base_settings = MicrowaveGeneratorBase._get_base_settings()
        
        # Should return a list of Parameter objects
        assert isinstance(base_settings, list)
        assert len(base_settings) > 0
        
        # Each should be a Parameter object with correct attributes
        for param in base_settings:
            assert isinstance(param, Parameter)
            assert hasattr(param, 'name')
            # Parameter objects use 'values' not 'value'
            assert hasattr(param, 'values')
    
    def test_sg384_has_all_required_parameters(self):
        """Test that SG384 has all parameters required for GUI display."""
        sg384_params = SG384Generator._DEFAULT_SETTINGS
        
        # These are the parameters that were causing KeyError in GUI
        required_params = [
            'connection_timeout', 'socket_timeout', 'connection_type',
            'ip_address', 'port', 'frequency', 'power', 'phase', 'amplitude'
        ]
        
        for param in required_params:
            assert param in sg384_params, f"Missing required parameter: {param}"
    
    def test_parameter_override_behavior(self):
        """Test that parameter overrides work correctly."""
        sg384_params = SG384Generator._DEFAULT_SETTINGS
        
        # SG384 should override ip_address from base class
        assert sg384_params['ip_address'] == '192.168.2.217'
        
        # But should inherit other base values
        assert sg384_params['connection_timeout'] == 10.0  # From base
        assert sg384_params['socket_timeout'] == 5.0  # From base
        assert sg384_params['port'] == 5025  # From base
    
    def test_no_parameter_duplication(self):
        """Test that parameters are not duplicated in the merged settings."""
        sg384_params = SG384Generator._DEFAULT_SETTINGS
        
        # Check that each parameter appears only once
        param_names = list(sg384_params.keys())
        assert len(param_names) == len(set(param_names)), "Duplicate parameters found"
    
    def test_inheritance_chain_integrity(self):
        """Test that the entire inheritance chain works correctly."""
        # Test Device -> MicrowaveGeneratorBase -> SG384
        device_params = set(Device._DEFAULT_SETTINGS.keys())
        base_params = set(MicrowaveGeneratorBase._DEFAULT_SETTINGS.keys())
        sg384_params = set(SG384Generator._DEFAULT_SETTINGS.keys())
        
        # Each level should have more parameters than the previous
        assert len(base_params) > len(device_params)
        assert len(sg384_params) > len(base_params)
        
        # SG384 should have all parameters from MicrowaveGeneratorBase
        # (Device's "default" parameter is not inherited by design)
        assert base_params.issubset(sg384_params)
    
    def test_parameter_types_and_validation(self):
        """Test that parameter types and validation are preserved."""
        sg384_params = SG384Generator._DEFAULT_SETTINGS
        
        # Test that parameter types are correct
        assert isinstance(sg384_params['connection_timeout'], float)
        assert isinstance(sg384_params['socket_timeout'], float)
        assert isinstance(sg384_params['ip_address'], str)
        assert isinstance(sg384_params['port'], int)
        assert isinstance(sg384_params['enable_output'], bool)
    
    def test_backward_compatibility(self):
        """Test that existing functionality is not broken."""
        # Test that we can still access parameters the old way
        sg384_params = SG384Generator._DEFAULT_SETTINGS
        
        # These should work without errors
        assert sg384_params['frequency'] == 1e9
        assert sg384_params['power'] == -10.0
        assert sg384_params['phase'] == 0.0
        
        # Test that parameter validation still works
        assert sg384_params.valid_values['connection_type'] == ['LAN','GPIB','RS232']
        assert sg384_params.info['connection_timeout'] == 'Connection timeout in seconds for LAN connections'


class TestDeviceInheritanceEdgeCases:
    """Test edge cases for device inheritance."""
    
    def test_empty_base_settings(self):
        """Test behavior with empty base settings."""
        # Create a minimal device class
        class MinimalDevice(Device):
            _DEFAULT_SETTINGS = Parameter([])
        
        base_settings = MinimalDevice._get_base_settings()
        assert isinstance(base_settings, list)
        assert len(base_settings) == 0
    
    def test_single_parameter_inheritance(self):
        """Test inheritance with single parameter."""
        class SingleParamDevice(Device):
            _DEFAULT_SETTINGS = Parameter([
                Parameter('test_param', 42, int, 'Test parameter')
            ])
        
        base_settings = SingleParamDevice._get_base_settings()
        assert len(base_settings) == 1
        assert base_settings[0].name == 'test_param'
        # Parameter objects use 'values' not 'value'
        assert base_settings[0]['test_param'] == 42


if __name__ == "__main__":
    pytest.main([__file__])
