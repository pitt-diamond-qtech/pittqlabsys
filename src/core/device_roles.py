"""
Device Role Management System

This module provides a role-based approach to device selection, making experiments
hardware-agnostic by defining device roles rather than specific device classes.

Author: Gurudev Dutt <gdutt@pitt.edu>
Created: 2024
License: GPL v2
"""

from typing import Dict, List, Type, Optional, Any
from abc import ABC, abstractmethod
from src.core.device import Device


class DeviceRole(ABC):
    """Abstract base class for device roles."""
    
    @abstractmethod
    def get_required_methods(self) -> List[str]:
        """Return list of methods that devices implementing this role must have."""
        pass
    
    @abstractmethod
    def get_required_parameters(self) -> List[str]:
        """Return list of parameters that devices implementing this role must have."""
        pass


class MicrowaveGeneratorRole(DeviceRole):
    """Role for microwave generators."""
    
    def get_required_methods(self) -> List[str]:
        return [
            'set_frequency',
            'set_power', 
            'set_phase',
            'output_on',
            'output_off',
            'enable_modulation',
            'disable_modulation',
            'set_modulation_type',
            'set_modulation_depth'
        ]
    
    def get_required_parameters(self) -> List[str]:
        return [
            'frequency',
            'power',
            'phase',
            'amplitude',
            'connection_type',
            'visa_resource'
        ]


class DataAcquisitionRole(DeviceRole):
    """Role for data acquisition devices."""
    
    def get_required_methods(self) -> List[str]:
        return [
            'update',
            'stop_process',
            'start_process'
        ]
    
    def get_required_parameters(self) -> List[str]:
        return [
            'integration_time',
            'trigger_mode'
        ]


class ScannerRole(DeviceRole):
    """Role for scanning devices (e.g., galvo scanners, nanopositioners)."""
    
    def get_required_methods(self) -> List[str]:
        return [
            'update',
            'get_position',
            'set_position'
        ]
    
    def get_required_parameters(self) -> List[str]:
        return [
            'x_pos',
            'y_pos',
            'z_pos'
        ]


class PulseGeneratorRole(DeviceRole):
    """Role for pulse generators."""
    
    def get_required_methods(self) -> List[str]:
        return [
            'set_pulse_duration',
            'set_repetition_rate',
            'start_sequence',
            'stop_sequence'
        ]
    
    def get_required_parameters(self) -> List[str]:
        return [
            'pulse_duration',
            'repetition_rate',
            'sequence_mode'
        ]


# Registry of device roles
DEVICE_ROLES = {
    'microwave_generator': MicrowaveGeneratorRole(),
    'data_acquisition': DataAcquisitionRole(),
    'scanner': ScannerRole(),
    'pulse_generator': PulseGeneratorRole()
}


class DeviceRoleManager:
    """Manages device role assignments and validation."""
    
    def __init__(self):
        self._role_to_device_map: Dict[str, Dict[str, Type[Device]]] = {}
        self._device_to_role_map: Dict[str, str] = {}
    
    def register_device_for_role(self, role: str, device_type: str, device_class: Type[Device]):
        """Register a device class for a specific role."""
        if role not in DEVICE_ROLES:
            raise ValueError(f"Unknown device role: {role}")
        
        if role not in self._role_to_device_map:
            self._role_to_device_map[role] = {}
        
        self._role_to_device_map[role][device_type] = device_class
        self._device_to_role_map[device_type] = role
    
    def get_devices_for_role(self, role: str) -> Dict[str, Type[Device]]:
        """Get all device classes that can fulfill a given role."""
        return self._role_to_device_map.get(role, {})
    
    def get_role_for_device(self, device_type: str) -> Optional[str]:
        """Get the role that a device type can fulfill."""
        return self._device_to_role_map.get(device_type)
    
    def validate_device_for_role(self, device_instance: Device, role: str) -> bool:
        """Validate that a device instance can fulfill a given role."""
        if role not in DEVICE_ROLES:
            return False
        
        role_definition = DEVICE_ROLES[role]
        
        # Check required methods
        for method_name in role_definition.get_required_methods():
            if not hasattr(device_instance, method_name):
                return False
        
        # Check required parameters
        for param_name in role_definition.get_required_parameters():
            if not hasattr(device_instance, 'settings') or param_name not in device_instance.settings:
                return False
        
        return True
    
    def create_device_for_role(self, role: str, device_type: str, **kwargs) -> Device:
        """Create a device instance for a given role and type."""
        if role not in self._role_to_device_map:
            raise ValueError(f"No devices registered for role: {role}")
        
        if device_type not in self._role_to_device_map[role]:
            raise ValueError(f"Device type {device_type} not registered for role {role}")
        
        device_class = self._role_to_device_map[role][device_type]
        device_instance = device_class(**kwargs)
        
        # Validate the device
        if not self.validate_device_for_role(device_instance, role):
            raise ValueError(f"Device {device_type} does not fulfill role {role} requirements")
        
        return device_instance


# Global device role manager instance
device_role_manager = DeviceRoleManager()


def register_device_roles():
    """Register all available devices with their appropriate roles."""
    from src.Controller import (
        SG384Generator, WindfreakSynthUSBII, MicrowaveGenerator,
        ADwinGold, NIDAQ, PXI6733, NI6281, PCI6229, PCI6601,
        MCLNanoDrive, PulseBlaster, AWG520Device
    )
    
    # Register microwave generators
    device_role_manager.register_device_for_role('microwave_generator', 'sg384', SG384Generator)
    device_role_manager.register_device_for_role('microwave_generator', 'windfreak_synth_usbii', WindfreakSynthUSBII)
    device_role_manager.register_device_for_role('microwave_generator', 'microwave_generator', MicrowaveGenerator)
    
    # Register data acquisition devices
    device_role_manager.register_device_for_role('data_acquisition', 'adwin', ADwinGold)
    device_role_manager.register_device_for_role('data_acquisition', 'nidaq', NIDAQ)
    device_role_manager.register_device_for_role('data_acquisition', 'pxi6733', PXI6733)
    device_role_manager.register_device_for_role('data_acquisition', 'ni6281', NI6281)
    device_role_manager.register_device_for_role('data_acquisition', 'pci6229', PCI6229)
    device_role_manager.register_device_for_role('data_acquisition', 'pci6601', PCI6601)
    
    # Register scanners
    device_role_manager.register_device_for_role('scanner', 'nanodrive', MCLNanoDrive)
    
    # Register pulse generators
    device_role_manager.register_device_for_role('pulse_generator', 'pulseblaster', PulseBlaster)
    device_role_manager.register_device_for_role('pulse_generator', 'awg520', AWG520Device)


def get_device_for_role(role: str, device_type: str, **kwargs) -> Device:
    """Convenience function to get a device for a specific role."""
    return device_role_manager.create_device_for_role(role, device_type, **kwargs)


def get_available_devices_for_role(role: str) -> List[str]:
    """Get list of available device types for a given role."""
    devices = device_role_manager.get_devices_for_role(role)
    return list(devices.keys())


# Initialize device role registrations
register_device_roles() 