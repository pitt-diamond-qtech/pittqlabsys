"""
Experiment Configuration System

This module provides configuration management for role-based experiments,
allowing device selection and experiment settings to be specified in
configuration files rather than hardcoded in the experiment classes.

Author: Gurudev Dutt <gdutt@pitt.edu>
Created: 2024
License: GPL v2
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from src.config_store import load_config, save_config
from src.core.helper_functions import get_project_root


class ExperimentConfigManager:
    """
    Manages experiment configurations including device selection and settings.
    """
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize the configuration manager.
        
        Args:
            config_dir: Directory for configuration files (defaults to project config dir)
        """
        if config_dir is None:
            config_dir = get_project_root() / 'config' / 'experiments'
        
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def get_experiment_config_path(self, experiment_name: str) -> Path:
        """Get the configuration file path for an experiment."""
        return self.config_dir / f"{experiment_name}_config.json"
    
    def load_experiment_config(self, experiment_name: str) -> Dict[str, Any]:
        """
        Load configuration for a specific experiment.
        
        Args:
            experiment_name: Name of the experiment
            
        Returns:
            Configuration dictionary
        """
        config_path = self.get_experiment_config_path(experiment_name)
        
        if not config_path.exists():
            # Return default configuration
            return self.get_default_config(experiment_name)
        
        try:
            config = load_config(config_path)
            return config
        except Exception as e:
            print(f"Warning: Failed to load config for {experiment_name}: {e}")
            return self.get_default_config(experiment_name)
    
    def save_experiment_config(self, experiment_name: str, config: Dict[str, Any]):
        """
        Save configuration for a specific experiment.
        
        Args:
            experiment_name: Name of the experiment
            config: Configuration dictionary to save
        """
        config_path = self.get_experiment_config_path(experiment_name)
        save_config(config_path, config)
    
    def get_default_config(self, experiment_name: str) -> Dict[str, Any]:
        """
        Get default configuration for an experiment.
        
        Args:
            experiment_name: Name of the experiment
            
        Returns:
            Default configuration dictionary
        """
        # Default configurations for different experiment types
        default_configs = {
            'odmr': {
                'device_config': {
                    'microwave': 'sg384',
                    'daq': 'adwin',
                    'scanner': 'nanodrive'
                },
                'settings': {
                    'frequency_range': {
                        'start': 2.7e9,
                        'stop': 3.0e9,
                        'steps': 100
                    },
                    'microwave': {
                        'power': -10.0,
                        'modulation': False,
                        'mod_depth': 1e6,
                        'mod_freq': 1e3
                    },
                    'acquisition': {
                        'integration_time': 0.1,
                        'averages': 1,
                        'settle_time': 0.01
                    }
                }
            },
            'confocal': {
                'device_config': {
                    'daq': 'adwin',
                    'scanner': 'nanodrive'
                },
                'settings': {
                    'scan_range': {
                        'x_start': 0.0,
                        'x_stop': 10.0,
                        'y_start': 0.0,
                        'y_stop': 10.0,
                        'steps': 100
                    },
                    'laser': {
                        'power': 1.0,
                        'wavelength': 532.0
                    }
                }
            },
            'rabi': {
                'device_config': {
                    'microwave': 'sg384',
                    'daq': 'adwin',
                    'pulse_generator': 'pulseblaster'
                },
                'settings': {
                    'rabi_settings': {
                        'frequency': 2.87e9,
                        'power': -10.0,
                        'pulse_duration_range': [0.0, 1e-6],
                        'pulse_steps': 50
                    }
                }
            }
        }
        
        # Extract experiment type from name (e.g., 'odmr_experiment' -> 'odmr')
        experiment_type = experiment_name.lower().split('_')[0]
        
        return default_configs.get(experiment_type, {
            'device_config': {},
            'settings': {}
        })
    
    def create_experiment_config_template(self, experiment_name: str, 
                                        required_roles: Dict[str, str]) -> Dict[str, Any]:
        """
        Create a configuration template for an experiment.
        
        Args:
            experiment_name: Name of the experiment
            required_roles: Dictionary of required device roles
            
        Returns:
            Configuration template
        """
        from src.core.device_roles import get_available_devices_for_role
        
        device_config = {}
        for role_name, role_type in required_roles.items():
            available_devices = get_available_devices_for_role(role_type)
            device_config[role_name] = available_devices[0] if available_devices else 'unknown'
        
        return {
            'experiment_name': experiment_name,
            'description': f'Configuration for {experiment_name}',
            'device_config': device_config,
            'settings': {},
            'metadata': {
                'created': '2024-01-01',
                'version': '1.0',
                'author': 'Generated by ExperimentConfigManager'
            }
        }
    
    def validate_experiment_config(self, experiment_name: str, config: Dict[str, Any]) -> bool:
        """
        Validate an experiment configuration.
        
        Args:
            experiment_name: Name of the experiment
            config: Configuration to validate
            
        Returns:
            True if configuration is valid
        """
        try:
            # Check required fields
            required_fields = ['device_config', 'settings']
            for field in required_fields:
                if field not in config:
                    return False
            
            # Validate device configuration
            device_config = config.get('device_config', {})
            if not isinstance(device_config, dict):
                return False
            
            # Additional validation could be added here
            return True
        except Exception:
            return False
    
    def list_experiment_configs(self) -> List[str]:
        """
        List all available experiment configurations.
        
        Returns:
            List of experiment names with configurations
        """
        configs = []
        for config_file in self.config_dir.glob("*_config.json"):
            experiment_name = config_file.stem.replace("_config", "")
            configs.append(experiment_name)
        return configs
    
    def get_lab_config(self, lab_name: str) -> Dict[str, Any]:
        """
        Get lab-specific configuration that can override experiment defaults.
        
        Args:
            lab_name: Name of the lab
            
        Returns:
            Lab configuration
        """
        lab_config_path = self.config_dir / f"{lab_name}_lab_config.json"
        
        if lab_config_path.exists():
            return load_config(lab_config_path)
        else:
            return {}
    
    def save_lab_config(self, lab_name: str, config: Dict[str, Any]):
        """
        Save lab-specific configuration.
        
        Args:
            lab_name: Name of the lab
            config: Lab configuration
        """
        lab_config_path = self.config_dir / f"{lab_name}_lab_config.json"
        save_config(lab_config_path, config)


# Global configuration manager instance
experiment_config_manager = ExperimentConfigManager()


def load_experiment_config(experiment_name: str) -> Dict[str, Any]:
    """
    Convenience function to load experiment configuration.
    
    Args:
        experiment_name: Name of the experiment
        
    Returns:
        Configuration dictionary
    """
    return experiment_config_manager.load_experiment_config(experiment_name)


def save_experiment_config(experiment_name: str, config: Dict[str, Any]):
    """
    Convenience function to save experiment configuration.
    
    Args:
        experiment_name: Name of the experiment
        config: Configuration to save
    """
    experiment_config_manager.save_experiment_config(experiment_name, config)


def create_experiment_from_config(experiment_class, experiment_name: str, 
                                lab_name: Optional[str] = None) -> Any:
    """
    Create an experiment instance from configuration.
    
    Args:
        experiment_class: The experiment class to instantiate
        experiment_name: Name of the experiment
        lab_name: Optional lab name for lab-specific overrides
        
    Returns:
        Experiment instance
    """
    # Load experiment configuration
    config = load_experiment_config(experiment_name)
    
    # Apply lab-specific overrides if specified
    if lab_name:
        lab_config = experiment_config_manager.get_lab_config(lab_name)
        if lab_config:
            # Override device configuration with lab-specific devices
            if 'device_config' in lab_config:
                config['device_config'].update(lab_config['device_config'])
    
    # Extract device configuration and settings
    device_config = config.get('device_config', {})
    settings = config.get('settings', {})
    
    # Create experiment instance
    experiment = experiment_class(
        name=experiment_name,
        settings=settings,
        device_config=device_config
    )
    
    return experiment


# Example usage and documentation
def example_configuration_usage():
    """
    Example showing how to use the configuration system.
    """
    
    # 1. Create a configuration template for an ODMR experiment
    from src.Model.experiments.odmr_experiment_role_based import RoleBasedODMRExperiment
    
    template = experiment_config_manager.create_experiment_config_template(
        'odmr_experiment',
        RoleBasedODMRExperiment._REQUIRED_DEVICE_ROLES
    )
    
    # 2. Save the template
    save_experiment_config('odmr_experiment', template)
    
    # 3. Modify the configuration for a specific lab
    lab_config = {
        'device_config': {
            'microwave': 'windfreak_synth_usbii',  # Different microwave generator
            'daq': 'nidaq'  # Different DAQ
        }
    }
    experiment_config_manager.save_lab_config('pitt_lab', lab_config)
    
    # 4. Create experiments with different configurations
    
    # Default configuration
    experiment1 = create_experiment_from_config(
        RoleBasedODMRExperiment, 
        'odmr_experiment'
    )
    
    # Lab-specific configuration
    experiment2 = create_experiment_from_config(
        RoleBasedODMRExperiment, 
        'odmr_experiment',
        lab_name='pitt_lab'
    )
    
    # The same experiment code works with different hardware configurations!
    
    return experiment1, experiment2


def create_lab_configuration_files():
    """
    Create example lab configuration files.
    """
    
    # Pitt Lab configuration
    pitt_config = {
        'description': 'University of Pittsburgh Quantum Lab Configuration',
        'device_config': {
            'microwave': 'sg384',
            'daq': 'adwin',
            'scanner': 'nanodrive',
            'pulse_generator': 'pulseblaster'
        },
        'settings': {
            'default_integration_time': 0.1,
            'default_laser_power': 1.0
        },
        'metadata': {
            'lab_manager': 'Gurudev Dutt',
            'contact': 'gdutt@pitt.edu',
            'location': 'Pittsburgh, PA'
        }
    }
    
    # MIT Lab configuration (example)
    mit_config = {
        'description': 'MIT Quantum Lab Configuration',
        'device_config': {
            'microwave': 'windfreak_synth_usbii',
            'daq': 'nidaq',
            'scanner': 'galvo_scanner',
            'pulse_generator': 'awg520'
        },
        'settings': {
            'default_integration_time': 0.05,
            'default_laser_power': 0.5
        },
        'metadata': {
            'lab_manager': 'MIT Researcher',
            'contact': 'researcher@mit.edu',
            'location': 'Cambridge, MA'
        }
    }
    
    # Save configurations
    experiment_config_manager.save_lab_config('pitt_lab', pitt_config)
    experiment_config_manager.save_lab_config('mit_lab', mit_config)
    
    print("Created lab configuration files:")
    print("- pitt_lab_config.json")
    print("- mit_lab_config.json") 