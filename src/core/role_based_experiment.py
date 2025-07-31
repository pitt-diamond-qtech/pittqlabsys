"""
Role-Based Experiment Base Class

This module provides a base experiment class that uses role-based device selection,
making experiments hardware-agnostic and portable across different lab setups.

Author: Gurudev Dutt <gdutt@pitt.edu>
Created: 2024
License: GPL v2
"""

from typing import Dict, List, Any, Optional, Type
from src.core.experiment import Experiment
from src.core.device import Device
from src.core.device_roles import device_role_manager, get_device_for_role, get_available_devices_for_role


class RoleBasedExperiment(Experiment):
    """
    Base experiment class that uses role-based device selection.
    
    Instead of hardcoding specific device classes, experiments define required
    device roles and let configuration specify which device implements each role.
    """
    
    # Define required device roles for this experiment
    # Override this in subclasses to specify required roles
    _REQUIRED_DEVICE_ROLES = {
        # Example:
        # 'microwave': 'microwave_generator',
        # 'daq': 'data_acquisition',
        # 'scanner': 'scanner'
    }
    
    # Default device types for each role (can be overridden by configuration)
    _DEFAULT_DEVICE_TYPES = {
        # Example:
        # 'microwave': 'sg384',
        # 'daq': 'adwin',
        # 'scanner': 'nanodrive'
    }
    
    def __init__(self, name=None, settings=None, devices=None, sub_experiments=None, 
                 log_function=None, data_path=None, device_config=None):
        """
        Initialize the role-based experiment.
        
        Args:
            name: Experiment name
            settings: Experiment settings
            devices: Dictionary of device instances (if provided, overrides role-based selection)
            sub_experiments: Dictionary of sub-experiment instances
            log_function: Logging function
            data_path: Data storage path
            device_config: Configuration specifying which device types to use for each role
                          Format: {'microwave': 'sg384', 'daq': 'adwin', ...}
        """
        # If devices are provided directly, use them (backward compatibility)
        if devices is not None:
            super().__init__(name, settings, devices, sub_experiments, log_function, data_path)
            return
        
        # Use role-based device selection
        if device_config is None:
            device_config = self._DEFAULT_DEVICE_TYPES
        
        # Create devices based on roles and configuration
        created_devices = self._create_devices_from_roles(device_config)
        
        # Initialize with created devices
        super().__init__(name, settings, created_devices, sub_experiments, log_function, data_path)
    
    def _create_devices_from_roles(self, device_config: Dict[str, str]) -> Dict[str, Dict[str, Any]]:
        """
        Create device instances based on role requirements and device configuration.
        
        Args:
            device_config: Dictionary mapping role names to device types
            
        Returns:
            Dictionary of device instances in the format expected by Experiment base class
        """
        devices = {}
        
        for role_name, device_type in device_config.items():
            if role_name not in self._REQUIRED_DEVICE_ROLES:
                raise ValueError(f"Unknown role '{role_name}' in device configuration")
            
            required_role = self._REQUIRED_DEVICE_ROLES[role_name]
            
            # Create device instance
            try:
                device_instance = get_device_for_role(required_role, device_type)
                devices[role_name] = {
                    'instance': device_instance,
                    'type': device_type,
                    'role': required_role
                }
            except Exception as e:
                raise ValueError(f"Failed to create device for role '{role_name}' "
                               f"(type: {device_type}, role: {required_role}): {e}")
        
        return devices
    
    @property
    def _DEVICES(self):
        """
        Override to return empty dict since we handle device creation in __init__.
        This maintains compatibility with the Experiment base class.
        """
        return {}
    
    @property
    def _EXPERIMENTS(self):
        """
        Override to return empty dict since we handle sub-experiments in __init__.
        This maintains compatibility with the Experiment base class.
        """
        return {}
    
    def get_available_device_types_for_role(self, role: str) -> List[str]:
        """
        Get available device types for a specific role.
        
        Args:
            role: Device role name
            
        Returns:
            List of available device types for the role
        """
        if role not in self._REQUIRED_DEVICE_ROLES:
            return []
        
        required_role = self._REQUIRED_DEVICE_ROLES[role]
        return get_available_devices_for_role(required_role)
    
    def get_device_role_info(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about device roles and available types.
        
        Returns:
            Dictionary with role information
        """
        info = {}
        for role_name, required_role in self._REQUIRED_DEVICE_ROLES.items():
            available_types = self.get_available_device_types_for_role(role_name)
            default_type = self._DEFAULT_DEVICE_TYPES.get(role_name, available_types[0] if available_types else None)
            
            info[role_name] = {
                'required_role': required_role,
                'available_types': available_types,
                'default_type': default_type
            }
        
        return info
    
    def validate_device_config(self, device_config: Dict[str, str]) -> bool:
        """
        Validate that a device configuration is valid for this experiment.
        
        Args:
            device_config: Device configuration to validate
            
        Returns:
            True if configuration is valid
        """
        try:
            # Check that all required roles are specified
            for role_name in self._REQUIRED_DEVICE_ROLES:
                if role_name not in device_config:
                    return False
            
            # Check that specified device types are available for their roles
            for role_name, device_type in device_config.items():
                if role_name not in self._REQUIRED_DEVICE_ROLES:
                    return False
                
                available_types = self.get_available_device_types_for_role(role_name)
                if device_type not in available_types:
                    return False
            
            return True
        except Exception:
            return False
    
    def get_device_config_template(self) -> Dict[str, str]:
        """
        Get a template device configuration with default device types.
        
        Returns:
            Template device configuration
        """
        config = {}
        for role_name in self._REQUIRED_DEVICE_ROLES:
            default_type = self._DEFAULT_DEVICE_TYPES.get(role_name)
            if default_type:
                config[role_name] = default_type
            else:
                # Use first available type as default
                available_types = self.get_available_device_types_for_role(role_name)
                config[role_name] = available_types[0] if available_types else 'unknown'
        
        return config


# Example usage and documentation
class ExampleRoleBasedExperiment(RoleBasedExperiment):
    """
    Example experiment showing how to use role-based device selection.
    """
    
    _REQUIRED_DEVICE_ROLES = {
        'microwave': 'microwave_generator',
        'daq': 'data_acquisition',
        'scanner': 'scanner'
    }
    
    _DEFAULT_DEVICE_TYPES = {
        'microwave': 'sg384',
        'daq': 'adwin',
        'scanner': 'nanodrive'
    }
    
    def _function(self):
        """Example experiment function."""
        # Access devices by role name
        microwave = self.devices['microwave']['instance']
        daq = self.devices['daq']['instance']
        scanner = self.devices['scanner']['instance']
        
        # Use devices through their role interface
        microwave.set_frequency(2.87e9)
        microwave.set_power(-10.0)
        microwave.output_on()
        
        # The experiment code is now hardware-agnostic!
        # It works with any device that implements the required role interface 