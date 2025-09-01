"""
Device Configuration Manager

This module handles loading and managing device configurations from config.json files.
It provides a centralized way to instantiate devices with their specific settings
for different lab environments.
"""

import json
import traceback
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from .device import Device
from .helper_functions import module_name_from_path
from importlib import import_module


class DeviceConfigManager:
    """
    Manages device configurations and instantiation from config files.
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize the device config manager.
        
        Args:
            config_path: Path to config.json file. If None, will look for config.json
                        in the project root.
        """
        if config_path is None:
            # Look for config.json in src directory
            from .helper_functions import get_project_root
            project_root = get_project_root()
            config_path = project_root / "src" / "config.json"
            print(f"[INFO] No config_path provided, using default: {config_path}")
        else:
            print(f"[INFO] Using provided config_path: {config_path}")
        
        self.config_path = config_path
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """
        Load configuration from the config file.
        
        Returns:
            Configuration dictionary
        """
        try:
            if not self.config_path.exists():
                print(f"[WARNING] Config file not found: {self.config_path}")
                return {}
            
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            
            print(f"[SUCCESS] Loaded config from: {self.config_path}")
            return config
            
        except Exception as e:
            print(f"[ERROR] Failed to load config from {self.config_path}: {e}")
            return {}
    
    def get_device_configs(self) -> Dict[str, Dict[str, Any]]:
        """
        Get device configurations from the loaded config.
        
        Returns:
            Dictionary of device configurations
        """
        return self.config.get('devices', {})
    
    def load_devices_from_config(self, raise_errors: bool = False) -> Tuple[Dict[str, Device], Dict[str, str]]:
        """
        Load all devices specified in the config file.
        
        Args:
            raise_errors: Whether to raise exceptions on device loading failures
            
        Returns:
            Tuple of (loaded_devices, failed_devices)
        """
        device_configs = self.get_device_configs()
        if not device_configs:
            print("[INFO] No device configurations found in config file")
            return {}, {}
        
        print(f"[INFO] Loading {len(device_configs)} devices from config...")
        
        loaded_devices = {}
        failed_devices = {}
        
        for device_name, device_config in device_configs.items():
            try:
                print(f"  [INFO] Loading device: {device_name}")
                device_instance = self._create_device_instance(device_name, device_config)
                
                if device_instance is not None:
                    loaded_devices[device_name] = device_instance
                    print(f"  [SUCCESS] Successfully loaded: {device_name}")
                else:
                    failed_devices[device_name] = "Device creation returned None"
                    print(f"  [ERROR] Failed to load: {device_name}")
                    
            except Exception as e:
                error_msg = f"Device loading failed: {e}"
                failed_devices[device_name] = error_msg
                print(f"  [ERROR] Failed to load {device_name}: {e}")
                
                if raise_errors:
                    raise e
        
        print(f"[SUCCESS] Device loading complete. Loaded: {len(loaded_devices)}, Failed: {len(failed_devices)}")
        return loaded_devices, failed_devices
    
    def _create_device_instance(self, device_name: str, device_config: Dict[str, Any]) -> Optional[Device]:
        """
        Create a device instance from configuration.
        
        Args:
            device_name: Name of the device
            device_config: Device configuration dictionary
            
        Returns:
            Device instance or None if creation failed
        """
        try:
            # Extract device class and filepath
            device_class_name = device_config.get('class')
            device_filepath = device_config.get('filepath')
            device_settings = device_config.get('settings', {})
            
            if not device_class_name:
                raise ValueError("Device class not specified in config")
            
            if not device_filepath:
                raise ValueError("Device filepath not specified in config")
            
            # Import the module
            # Resolve relative filepath to absolute path relative to project root
            if not Path(device_filepath).is_absolute():
                from .helper_functions import get_project_root
                project_root = get_project_root()
                absolute_filepath = project_root / device_filepath
            else:
                absolute_filepath = Path(device_filepath)
            
            module_path, _ = module_name_from_path(str(absolute_filepath), verbose=False)
            module = import_module(module_path)
            
            # Get the device class
            device_class = getattr(module, device_class_name)
            
            if not issubclass(device_class, Device):
                raise ValueError(f"{device_class_name} is not a Device subclass")
            
            # Create device instance with settings
            device_instance = device_class(name=device_name, settings=device_settings)
            
            return device_instance
            
        except Exception as e:
            print(f"  [ERROR] Failed to create {device_name}: {e}")
            traceback.print_exc()
            return None
    
    def reload_config(self) -> None:
        """
        Reload the configuration from the config file.
        """
        self.config = self._load_config()
    
    def get_device_config(self, device_name: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a specific device.
        
        Args:
            device_name: Name of the device
            
        Returns:
            Device configuration or None if not found
        """
        return self.get_device_configs().get(device_name)
    
    def update_device_config(self, device_name: str, config: Dict[str, Any]) -> bool:
        """
        Update configuration for a specific device.
        
        Args:
            device_name: Name of the device
            config: New device configuration
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if 'devices' not in self.config:
                self.config['devices'] = {}
            
            self.config['devices'][device_name] = config
            
            # Save to file
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
            
            print(f"[SUCCESS] Updated device config for: {device_name}")
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to update device config for {device_name}: {e}")
            return False


def load_devices_from_config(config_path: Optional[Path] = None, raise_errors: bool = False) -> Tuple[Dict[str, Device], Dict[str, str]]:
    """
    Convenience function to load devices from config.
    
    Args:
        config_path: Path to config.json file
        raise_errors: Whether to raise exceptions on failures
        
    Returns:
        Tuple of (loaded_devices, failed_devices)
    """
    manager = DeviceConfigManager(config_path)
    return manager.load_devices_from_config(raise_errors)
