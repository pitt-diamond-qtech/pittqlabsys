"""
Tests for Role-Based Experiment System

This module tests the role-based experiment system to ensure it works correctly
with different hardware configurations.

Author: Gurudev Dutt <gdutt@pitt.edu>
Created: 2024
License: GPL v2
"""

import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from typing import Dict, Any

from src.core.device_roles import (
    device_role_manager, get_device_for_role, get_available_devices_for_role,
    MicrowaveGeneratorRole, DataAcquisitionRole, ScannerRole
)
from src.core.role_based_experiment import RoleBasedExperiment
from src.core.experiment_config import (
    experiment_config_manager, create_experiment_from_config
)


class MockMicrowaveGenerator:
    """Mock microwave generator for testing."""
    
    def __init__(self):
        self.settings = {
            'frequency': 2.87e9,
            'power': -10.0,
            'phase': 0.0,
            'amplitude': 1.0,
            'connection_type': 'GPIB',
            'visa_resource': 'GPIB0::1::INSTR'
        }
    
    def set_frequency(self, freq):
        self.settings['frequency'] = freq
    
    def set_power(self, power):
        self.settings['power'] = power
    
    def set_phase(self, phase):
        self.settings['phase'] = phase
    
    def output_on(self):
        pass
    
    def output_off(self):
        pass
    
    def enable_modulation(self):
        pass
    
    def disable_modulation(self):
        pass
    
    def set_modulation_type(self, mod_type):
        pass
    
    def set_modulation_depth(self, depth):
        pass


class MockDataAcquisition:
    """Mock data acquisition device for testing."""
    
    def __init__(self):
        self.settings = {
            'integration_time': 0.1,
            'trigger_mode': 'internal'
        }
    
    def update(self, settings):
        self.settings.update(settings)
    
    def start_process(self):
        pass
    
    def stop_process(self):
        pass


class MockScanner:
    """Mock scanner device for testing."""
    
    def __init__(self):
        self.settings = {
            'x_pos': 0.0,
            'y_pos': 0.0,
            'z_pos': 0.0
        }
    
    def update(self, settings):
        self.settings.update(settings)
    
    def get_position(self):
        return (self.settings['x_pos'], self.settings['y_pos'], self.settings['z_pos'])
    
    def set_position(self, x, y, z):
        self.settings['x_pos'] = x
        self.settings['y_pos'] = y
        self.settings['z_pos'] = z


class TestRoleBasedExperiment(RoleBasedExperiment):
    """Test experiment class for role-based testing."""
    
    _REQUIRED_DEVICE_ROLES = {
        'microwave': 'microwave_generator',
        'daq': 'data_acquisition',
        'scanner': 'scanner'
    }
    
    _DEFAULT_DEVICE_TYPES = {
        'microwave': 'mock_microwave',
        'daq': 'mock_daq',
        'scanner': 'mock_scanner'
    }
    
    def __init__(self, name=None, settings=None, devices=None, sub_experiments=None,
                 log_function=None, data_path=None, device_config=None):
        """Initialize the test experiment."""
        super().__init__(name, settings, devices, sub_experiments, log_function, data_path, device_config)
    
    def _function(self):
        """Simple test function."""
        microwave = self.devices['microwave']['instance']
        daq = self.devices['daq']['instance']
        scanner = self.devices.get('scanner', {}).get('instance')
        
        # Test microwave operations
        microwave.set_frequency(2.87e9)
        microwave.set_power(-10.0)
        microwave.output_on()
        
        # Test DAQ operations
        daq.update({'integration_time': 0.1})
        daq.start_process()
        daq.stop_process()
        
        # Test scanner operations (if available)
        if scanner:
            scanner.set_position(1.0, 2.0, 0.0)
        
        return True


@pytest.fixture
def setup_mock_devices():
    """Setup mock devices for testing."""
    # Register mock devices with the role manager
    device_role_manager.register_device_for_role(
        'microwave_generator', 'mock_microwave', MockMicrowaveGenerator
    )
    device_role_manager.register_device_for_role(
        'data_acquisition', 'mock_daq', MockDataAcquisition
    )
    device_role_manager.register_device_for_role(
        'scanner', 'mock_scanner', MockScanner
    )
    
    yield
    
    # Cleanup (in a real implementation, you might want to clear registrations)


class TestDeviceRoles:
    """Test device role functionality."""
    
    def test_microwave_generator_role(self):
        """Test microwave generator role requirements."""
        role = MicrowaveGeneratorRole()
        
        required_methods = role.get_required_methods()
        assert 'set_frequency' in required_methods
        assert 'set_power' in required_methods
        assert 'output_on' in required_methods
        assert 'output_off' in required_methods
        
        required_params = role.get_required_parameters()
        assert 'frequency' in required_params
        assert 'power' in required_params
        assert 'connection_type' in required_params
    
    def test_data_acquisition_role(self):
        """Test data acquisition role requirements."""
        role = DataAcquisitionRole()
        
        required_methods = role.get_required_methods()
        assert 'update' in required_methods
        assert 'start_process' in required_methods
        assert 'stop_process' in required_methods
        
        required_params = role.get_required_parameters()
        assert 'integration_time' in required_params
        assert 'trigger_mode' in required_params
    
    def test_scanner_role(self):
        """Test scanner role requirements."""
        role = ScannerRole()
        
        required_methods = role.get_required_methods()
        assert 'update' in required_methods
        assert 'get_position' in required_methods
        assert 'set_position' in required_methods
        
        required_params = role.get_required_parameters()
        assert 'x_pos' in required_params
        assert 'y_pos' in required_params
        assert 'z_pos' in required_params


class TestDeviceRoleManager:
    """Test device role manager functionality."""
    
    def test_register_device_for_role(self, setup_mock_devices):
        """Test device registration for roles."""
        # Test that mock devices are registered
        microwave_devices = device_role_manager.get_devices_for_role('microwave_generator')
        assert 'mock_microwave' in microwave_devices
        
        daq_devices = device_role_manager.get_devices_for_role('data_acquisition')
        assert 'mock_daq' in daq_devices
        
        scanner_devices = device_role_manager.get_devices_for_role('scanner')
        assert 'mock_scanner' in scanner_devices
    
    def test_validate_device_for_role(self, setup_mock_devices):
        """Test device validation for roles."""
        # Create mock device instances
        microwave = MockMicrowaveGenerator()
        daq = MockDataAcquisition()
        scanner = MockScanner()
        
        # Test validation
        assert device_role_manager.validate_device_for_role(microwave, 'microwave_generator')
        assert device_role_manager.validate_device_for_role(daq, 'data_acquisition')
        assert device_role_manager.validate_device_for_role(scanner, 'scanner')
        
        # Test invalid device
        invalid_device = MagicMock()
        assert not device_role_manager.validate_device_for_role(invalid_device, 'microwave_generator')
    
    def test_create_device_for_role(self, setup_mock_devices):
        """Test device creation for roles."""
        # Create devices through role manager
        microwave = device_role_manager.create_device_for_role('microwave_generator', 'mock_microwave')
        daq = device_role_manager.create_device_for_role('data_acquisition', 'mock_daq')
        scanner = device_role_manager.create_device_for_role('scanner', 'mock_scanner')
        
        # Verify device types
        assert isinstance(microwave, MockMicrowaveGenerator)
        assert isinstance(daq, MockDataAcquisition)
        assert isinstance(scanner, MockScanner)
        
        # Test invalid role/device combination
        with pytest.raises(ValueError):
            device_role_manager.create_device_for_role('invalid_role', 'mock_microwave')
        
        with pytest.raises(ValueError):
            device_role_manager.create_device_for_role('microwave_generator', 'invalid_device')


class TestRoleBasedExperiment:
    """Test role-based experiment functionality."""
    
    def test_experiment_initialization(self, setup_mock_devices):
        """Test role-based experiment initialization."""
        # Test with default device configuration
        experiment = TestRoleBasedExperiment(name="Test_Experiment")
        
        # Verify devices are created
        assert 'microwave' in experiment.devices
        assert 'daq' in experiment.devices
        assert 'scanner' in experiment.devices
        
        # Verify device instances
        assert isinstance(experiment.devices['microwave']['instance'], MockMicrowaveGenerator)
        assert isinstance(experiment.devices['daq']['instance'], MockDataAcquisition)
        assert isinstance(experiment.devices['scanner']['instance'], MockScanner)
        
        # Verify device metadata
        assert experiment.devices['microwave']['type'] == 'mock_microwave'
        assert experiment.devices['microwave']['role'] == 'microwave_generator'
    
    def test_custom_device_configuration(self, setup_mock_devices):
        """Test experiment with custom device configuration."""
        custom_config = {
            'microwave': 'mock_microwave',
            'daq': 'mock_daq',
            'scanner': 'mock_scanner'
        }
        
        experiment = TestRoleBasedExperiment(
            name="Test_Experiment",
            device_config=custom_config
        )
        
        # Verify custom configuration is used
        assert experiment.devices['microwave']['type'] == 'mock_microwave'
        assert experiment.devices['daq']['type'] == 'mock_daq'
        assert experiment.devices['scanner']['type'] == 'mock_scanner'
    
    def test_experiment_execution(self, setup_mock_devices):
        """Test role-based experiment execution."""
        experiment = TestRoleBasedExperiment(name="Test_Experiment")
        
        # Execute experiment
        result = experiment._function()
        
        # Verify execution completed
        assert result is True
        
        # Verify device interactions occurred
        microwave = experiment.devices['microwave']['instance']
        assert microwave.settings['frequency'] == 2.87e9
        assert microwave.settings['power'] == -10.0
        
        daq = experiment.devices['daq']['instance']
        assert daq.settings['integration_time'] == 0.1
    
    def test_device_role_info(self, setup_mock_devices):
        """Test device role information retrieval."""
        experiment = TestRoleBasedExperiment(name="Test_Experiment")
        
        role_info = experiment.get_device_role_info()
        
        # Verify role information
        assert 'microwave' in role_info
        assert role_info['microwave']['required_role'] == 'microwave_generator'
        assert 'mock_microwave' in role_info['microwave']['available_types']
        assert role_info['microwave']['default_type'] == 'mock_microwave'
    
    def test_device_config_validation(self, setup_mock_devices):
        """Test device configuration validation."""
        experiment = TestRoleBasedExperiment(name="Test_Experiment")
        
        # Valid configuration
        valid_config = {
            'microwave': 'mock_microwave',
            'daq': 'mock_daq',
            'scanner': 'mock_scanner'
        }
        assert experiment.validate_device_config(valid_config)
        
        # Invalid configuration - missing required role
        invalid_config = {
            'microwave': 'mock_microwave',
            'daq': 'mock_daq'
            # Missing 'scanner'
        }
        assert not experiment.validate_device_config(invalid_config)
        
        # Invalid configuration - unknown device type
        invalid_config2 = {
            'microwave': 'unknown_device',
            'daq': 'mock_daq',
            'scanner': 'mock_scanner'
        }
        assert not experiment.validate_device_config(invalid_config2)


class TestExperimentConfiguration:
    """Test experiment configuration system."""
    
    def test_configuration_loading(self, setup_mock_devices, tmp_path):
        """Test experiment configuration loading."""
        # Create temporary config directory
        config_dir = tmp_path / 'config' / 'experiments'
        config_dir.mkdir(parents=True)
        
        # Create test configuration
        test_config = {
            'experiment_name': 'test_experiment',
            'device_config': {
                'microwave': 'mock_microwave',
                'daq': 'mock_daq',
                'scanner': 'mock_scanner'
            },
            'settings': {
                'test_setting': 'test_value'
            }
        }
        
        # Save configuration
        config_path = config_dir / 'test_experiment_config.json'
        import json
        with open(config_path, 'w') as f:
            json.dump(test_config, f)
        
        # Create config manager with temporary directory
        config_manager = experiment_config_manager.__class__(config_dir)
        
        # Load configuration
        loaded_config = config_manager.load_experiment_config('test_experiment')
        
        # Verify configuration
        assert loaded_config['experiment_name'] == 'test_experiment'
        assert loaded_config['device_config']['microwave'] == 'mock_microwave'
        assert loaded_config['settings']['test_setting'] == 'test_value'
    
    def test_default_configuration(self, setup_mock_devices):
        """Test default configuration generation."""
        # Test default config for ODMR experiment
        default_config = experiment_config_manager.get_default_config('odmr_experiment')
        
        assert 'device_config' in default_config
        assert 'settings' in default_config
        assert default_config['device_config']['microwave'] == 'sg384'
        assert default_config['device_config']['daq'] == 'adwin'
    
    def test_experiment_creation_from_config(self, setup_mock_devices):
        """Test experiment creation from configuration."""
        # Create test configuration
        test_config = {
            'device_config': {
                'microwave': 'mock_microwave',
                'daq': 'mock_daq',
                'scanner': 'mock_scanner'
            },
            'settings': {
                'test_setting': 'test_value'
            }
        }
        
        # Mock configuration loading
        with patch('src.core.experiment_config.load_experiment_config', return_value=test_config):
            experiment = create_experiment_from_config(
                TestRoleBasedExperiment,
                'test_experiment'
            )
        
        # Verify experiment is created with correct configuration
        assert isinstance(experiment, TestRoleBasedExperiment)
        assert experiment.devices['microwave']['type'] == 'mock_microwave'
        assert experiment.devices['daq']['type'] == 'mock_daq'
        assert experiment.devices['scanner']['type'] == 'mock_scanner'


class TestHardwarePortability:
    """Test hardware portability features."""
    
    def test_same_experiment_different_hardware(self, setup_mock_devices):
        """Test that the same experiment works with different hardware configurations."""
        
        # Configuration 1: Default hardware
        experiment1 = TestRoleBasedExperiment(
            name="Test_Default",
            device_config=None  # Uses defaults
        )
        
        # Configuration 2: Different hardware (same roles, different implementations)
        experiment2 = TestRoleBasedExperiment(
            name="Test_Custom",
            device_config={
                'microwave': 'mock_microwave',
                'daq': 'mock_daq',
                'scanner': 'mock_scanner'
            }
        )
        
        # Both experiments should work identically
        result1 = experiment1._function()
        result2 = experiment2._function()
        
        assert result1 is True
        assert result2 is True
        
        # Both should have the same device interactions
        microwave1 = experiment1.devices['microwave']['instance']
        microwave2 = experiment2.devices['microwave']['instance']
        
        assert microwave1.settings['frequency'] == microwave2.settings['frequency']
        assert microwave1.settings['power'] == microwave2.settings['power']
    
    def test_optional_devices(self, setup_mock_devices):
        """Test experiments with optional devices."""
        # Create experiment without scanner
        experiment = TestRoleBasedExperiment(
            name="Test_No_Scanner",
            device_config={
                'microwave': 'mock_microwave',
                'daq': 'mock_daq'
                # No scanner specified
            }
        )
        
        # Experiment should still work
        result = experiment._function()
        assert result is True
        
        # Scanner should be None
        assert experiment.devices.get('scanner') is None


if __name__ == "__main__":
    # Run demonstration
    print("Testing Role-Based Experiment System...")
    
    # Setup mock devices
    setup_mock_devices()
    
    # Test basic functionality
    experiment = TestRoleBasedExperiment(name="Demo_Experiment")
    print(f"Created experiment with devices: {list(experiment.devices.keys())}")
    
    # Test execution
    result = experiment._function()
    print(f"Experiment execution result: {result}")
    
    # Test role information
    role_info = experiment.get_device_role_info()
    print(f"Device role info: {role_info}")
    
    print("All tests completed successfully!") 