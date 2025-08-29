"""
Tests for the device configuration system.

This module tests the DeviceConfigManager and related functionality
for loading devices from config.json files.
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.core.device_config import DeviceConfigManager, load_devices_from_config
from src.core.device import Device


class MockDevice(Device):
    """Mock device for testing."""
    
    _DEFAULT_SETTINGS = {
        'test_param': 'default_value',
        'ip_address': 'localhost',
        'port': 1234
    }
    
    def __init__(self, name=None, settings=None):
        super().__init__(name, settings)
    
    def update(self, settings):
        self._settings.update(settings)
    
    _PROBES = {'test_probe': 'Test probe value'}
    
    @property
    def is_connected(self):
        return True


class TestDeviceConfigManager:
    """Test the DeviceConfigManager class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "test_config.json"
        
        # Create a basic test config
        self.test_config = {
            "environment": {
                "is_development": False,
                "is_mock": False
            },
            "devices": {
                "test_device": {
                    "class": "MockDevice",
                    "filepath": "src/Controller/mock_device.py",
                    "settings": {
                        "test_param": "test_value",
                        "ip_address": "192.168.1.100"
                    }
                },
                "test_device2": {
                    "class": "MockDevice",
                    "filepath": "src/Controller/mock_device.py",
                    "settings": {
                        "port": 5678
                    }
                }
            }
        }
        
        # Write test config to file
        with open(self.config_path, 'w') as f:
            json.dump(self.test_config, f)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_init_with_config_path(self):
        """Test initialization with explicit config path."""
        manager = DeviceConfigManager(self.config_path)
        assert manager.config_path == self.config_path
        assert manager.config == self.test_config
    
    def test_init_without_config_path(self):
        """Test initialization without config path (should look in project root)."""
        with patch('src.core.device_config.Path') as mock_path:
            mock_path.return_value.parent.parent.parent = Path("/fake/project/root")
            mock_path.return_value.exists.return_value = False
            
            manager = DeviceConfigManager()
            assert "config.json" in str(manager.config_path)
    
    def test_load_config_success(self):
        """Test successful config loading."""
        manager = DeviceConfigManager(self.config_path)
        assert manager.config == self.test_config
    
    def test_load_config_file_not_found(self):
        """Test config loading when file doesn't exist."""
        non_existent_path = Path("/non/existent/config.json")
        manager = DeviceConfigManager(non_existent_path)
        assert manager.config == {}
    
    def test_load_config_invalid_json(self):
        """Test config loading with invalid JSON."""
        invalid_config_path = Path(self.temp_dir) / "invalid_config.json"
        with open(invalid_config_path, 'w') as f:
            f.write("invalid json content")
        
        manager = DeviceConfigManager(invalid_config_path)
        assert manager.config == {}
    
    def test_get_device_configs(self):
        """Test getting device configurations."""
        manager = DeviceConfigManager(self.config_path)
        device_configs = manager.get_device_configs()
        
        assert "test_device" in device_configs
        assert "test_device2" in device_configs
        assert device_configs["test_device"]["class"] == "MockDevice"
    
    def test_get_device_configs_empty(self):
        """Test getting device configs when none exist."""
        empty_config = {"environment": {"is_development": False}}
        empty_config_path = Path(self.temp_dir) / "empty_config.json"
        
        with open(empty_config_path, 'w') as f:
            json.dump(empty_config, f)
        
        manager = DeviceConfigManager(empty_config_path)
        device_configs = manager.get_device_configs()
        assert device_configs == {}
    
    def test_get_device_config_specific(self):
        """Test getting configuration for a specific device."""
        manager = DeviceConfigManager(self.config_path)
        device_config = manager.get_device_config("test_device")
        
        assert device_config is not None
        assert device_config["class"] == "MockDevice"
        assert device_config["settings"]["test_param"] == "test_value"
    
    def test_get_device_config_not_found(self):
        """Test getting configuration for non-existent device."""
        manager = DeviceConfigManager(self.config_path)
        device_config = manager.get_device_config("non_existent")
        assert device_config is None
    
    def test_update_device_config(self):
        """Test updating device configuration."""
        manager = DeviceConfigManager(self.config_path)
        
        new_config = {
            "class": "UpdatedMockDevice",
            "filepath": "src/Controller/updated_mock_device.py",
            "settings": {"new_param": "new_value"}
        }
        
        success = manager.update_device_config("new_device", new_config)
        assert success is True
        
        # Check if config was updated
        updated_config = manager.get_device_config("new_device")
        assert updated_config == new_config
        
        # Check if file was written
        with open(self.config_path, 'r') as f:
            saved_config = json.load(f)
        assert "new_device" in saved_config["devices"]
    
    def test_update_device_config_failure(self):
        """Test device config update failure."""
        manager = DeviceConfigManager(self.config_path)
        
        # Make the file read-only to cause write failure
        os.chmod(self.config_path, 0o444)
        
        new_config = {"class": "TestDevice", "filepath": "test.py"}
        success = manager.update_device_config("test_device", new_config)
        assert success is False
        
        # Restore permissions
        os.chmod(self.config_path, 0o666)
    
    def test_reload_config(self):
        """Test reloading configuration."""
        manager = DeviceConfigManager(self.config_path)
        
        # Modify the config file
        updated_config = self.test_config.copy()
        updated_config["devices"]["new_device"] = {
            "class": "NewDevice",
            "filepath": "src/Controller/new_device.py"
        }
        
        with open(self.config_path, 'w') as f:
            json.dump(updated_config, f)
        
        # Reload config
        manager.reload_config()
        
        # Check if new device is loaded
        assert "new_device" in manager.get_device_configs()


class TestDeviceLoading:
    """Test device loading functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "test_config.json"
        
        # Create a test config with mock device
        self.test_config = {
            "devices": {
                "mock_device": {
                    "class": "MockDevice",
                    "filepath": "src/Controller/mock_device.py",
                    "settings": {
                        "test_param": "test_value"
                    }
                }
            }
        }
        
        with open(self.config_path, 'w') as f:
            json.dump(self.test_config, f)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    @patch('src.core.device_config.import_module')
    @patch('src.core.device_config.module_name_from_path')
    def test_create_device_instance_success(self, mock_module_name, mock_import):
        """Test successful device instance creation."""
        # Mock the module import
        mock_module = Mock()
        mock_module.MockDevice = MockDevice
        mock_import.return_value = mock_module  # Return the mock module, not a tuple
        mock_module_name.return_value = ("mock_module", None)
        
        manager = DeviceConfigManager(self.config_path)
        device_config = manager.get_device_config("mock_device")
        
        device_instance = manager._create_device_instance("mock_device", device_config)
        
        assert device_instance is not None
        assert isinstance(device_instance, MockDevice)
        assert device_instance.name == "mock_device"
        assert device_instance.settings["test_param"] == "test_value"
    
    @patch('src.core.device_config.import_module')
    @patch('src.core.device_config.module_name_from_path')
    def test_create_device_instance_missing_class(self, mock_module_name, mock_import):
        """Test device creation with missing class."""
        # Mock the module import
        mock_module = Mock()
        mock_module.MockDevice = MockDevice
        mock_import.return_value = ("mock_module", None)
        mock_module_name.return_value = ("mock_module", None)
        
        manager = DeviceConfigManager(self.config_path)
        
        # Test with missing class
        device_config = {"filepath": "test.py", "settings": {}}
        device_instance = manager._create_device_instance("test_device", device_config)
        assert device_instance is None
    
    @patch('src.core.device_config.import_module')
    @patch('src.core.device_config.module_name_from_path')
    def test_create_device_instance_missing_filepath(self, mock_module_name, mock_import):
        """Test device creation with missing filepath."""
        manager = DeviceConfigManager(self.config_path)
        
        # Test with missing filepath
        device_config = {"class": "MockDevice", "settings": {}}
        device_instance = manager._create_device_instance("test_device", device_config)
        assert device_instance is None
    
    @patch('src.core.device_config.import_module')
    @patch('src.core.device_config.module_name_from_path')
    def test_create_device_instance_not_device_subclass(self, mock_module_name, mock_import):
        """Test device creation with class that's not a Device subclass."""
        # Mock the module import with a non-Device class
        mock_module = Mock()
        mock_module.NotADevice = str  # str is not a Device subclass
        mock_import.return_value = ("mock_module", None)
        mock_module_name.return_value = ("mock_module", None)
        
        manager = DeviceConfigManager(self.config_path)
        
        device_config = {
            "class": "NotADevice",
            "filepath": "test.py",
            "settings": {}
        }
        device_instance = manager._create_device_instance("test_device", device_config)
        assert device_instance is None
    
    @patch('src.core.device_config.import_module')
    @patch('src.core.device_config.module_name_from_path')
    def test_load_devices_from_config_success(self, mock_module_name, mock_import):
        """Test successful loading of devices from config."""
        # Mock the module import
        mock_module = Mock()
        mock_module.MockDevice = MockDevice
        mock_import.return_value = mock_module  # Return the mock module, not a tuple
        mock_module_name.return_value = ("mock_module", None)
        
        manager = DeviceConfigManager(self.config_path)
        loaded_devices, failed_devices = manager.load_devices_from_config()
        
        assert len(loaded_devices) == 1
        assert "mock_device" in loaded_devices
        assert len(failed_devices) == 0
        
        device = loaded_devices["mock_device"]
        assert isinstance(device, MockDevice)
        assert device.settings["test_param"] == "test_value"
    
    @patch('src.core.device_config.import_module')
    @patch('src.core.device_config.module_name_from_path')
    def test_load_devices_from_config_with_failures(self, mock_module_name, mock_import):
        """Test device loading with some failures."""
        # Mock the module import to fail for one device
        mock_module = Mock()
        mock_module.MockDevice = MockDevice
        mock_import.return_value = mock_module  # Return the mock module, not a tuple
        mock_module_name.return_value = ("mock_module", None)
        
        # Create config with one valid and one invalid device
        config_with_failures = {
            "devices": {
                "valid_device": {
                    "class": "MockDevice",
                    "filepath": "src/Controller/mock_device.py",
                    "settings": {"test_param": "valid"}
                },
                "invalid_device": {
                    "class": "NonExistentClass",
                    "filepath": "src/Controller/non_existent.py",
                    "settings": {}
                }
            }
        }
        
        config_path = Path(self.temp_dir) / "failure_config.json"
        with open(config_path, 'w') as f:
            json.dump(config_with_failures, f)
        
        manager = DeviceConfigManager(config_path)
        loaded_devices, failed_devices = manager.load_devices_from_config()
        
        assert len(loaded_devices) == 1
        assert "valid_device" in loaded_devices
        assert len(failed_devices) == 1
        assert "invalid_device" in failed_devices
    
    def test_load_devices_from_config_empty(self):
        """Test loading devices from empty config."""
        empty_config = {"environment": {"is_development": False}}
        empty_config_path = Path(self.temp_dir) / "empty_config.json"
        
        with open(empty_config_path, 'w') as f:
            json.dump(empty_config, f)
        
        manager = DeviceConfigManager(empty_config_path)
        loaded_devices, failed_devices = manager.load_devices_from_config()
        
        assert len(loaded_devices) == 0
        assert len(failed_devices) == 0


class TestConvenienceFunction:
    """Test the convenience function load_devices_from_config."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "test_config.json"
        
        # Create a simple test config
        self.test_config = {
            "devices": {
                "test_device": {
                    "class": "MockDevice",
                    "filepath": "src/Controller/mock_device.py",
                    "settings": {"test_param": "test_value"}
                }
            }
        }
        
        with open(self.config_path, 'w') as f:
            json.dump(self.test_config, f)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    @patch('src.core.device_config.DeviceConfigManager')
    def test_load_devices_from_config_convenience(self, mock_manager_class):
        """Test the convenience function."""
        # Mock the manager
        mock_manager = Mock()
        mock_manager.load_devices_from_config.return_value = ({"test": "device"}, {})
        mock_manager_class.return_value = mock_manager
        
        # Test the convenience function
        loaded, failed = load_devices_from_config(self.config_path)
        
        # Check that manager was created and called
        mock_manager_class.assert_called_once_with(self.config_path)
        mock_manager.load_devices_from_config.assert_called_once_with(False)  # Positional argument
        
        assert loaded == {"test": "device"}
        assert failed == {}
    
    @patch('src.core.device_config.DeviceConfigManager')
    def test_load_devices_from_config_convenience_with_raise_errors(self, mock_manager_class):
        """Test the convenience function with raise_errors=True."""
        # Mock the manager
        mock_manager = Mock()
        mock_manager.load_devices_from_config.return_value = ({"test": "device"}, {})
        mock_manager_class.return_value = mock_manager
        
        # Test with raise_errors=True
        loaded, failed = load_devices_from_config(self.config_path, raise_errors=True)
        
        # Check that raise_errors was passed correctly
        mock_manager.load_devices_from_config.assert_called_once_with(True)  # Positional argument


class TestIntegration:
    """Integration tests for the device configuration system."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "test_config.json"
        
        # Create a comprehensive test config
        self.test_config = {
            "environment": {
                "is_development": False,
                "is_mock": False
            },
            "devices": {
                "device1": {
                    "class": "MockDevice",
                    "filepath": "src/Controller/mock_device.py",
                    "settings": {
                        "test_param": "value1",
                        "ip_address": "192.168.1.100"
                    }
                },
                "device2": {
                    "class": "MockDevice",
                    "filepath": "src/Controller/mock_device.py",
                    "settings": {
                        "test_param": "value2",
                        "port": 5678
                    }
                }
            }
        }
        
        with open(self.config_path, 'w') as f:
            json.dump(self.test_config, f)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    @patch('src.core.device_config.import_module')
    @patch('src.core.device_config.module_name_from_path')
    def test_full_device_loading_workflow(self, mock_module_name, mock_import):
        """Test the complete device loading workflow."""
        # Mock the module import
        mock_module = Mock()
        mock_module.MockDevice = MockDevice
        mock_import.return_value = mock_module  # Return the mock module, not a tuple
        mock_module_name.return_value = ("mock_module", None)
        
        # Create manager and load devices
        manager = DeviceConfigManager(self.config_path)
        loaded_devices, failed_devices = manager.load_devices_from_config()
        
        # Verify results
        assert len(loaded_devices) == 2
        assert len(failed_devices) == 0
        
        # Check device1
        device1 = loaded_devices["device1"]
        assert isinstance(device1, MockDevice)
        assert device1.name == "device1"
        assert device1.settings["test_param"] == "value1"
        assert device1.settings["ip_address"] == "192.168.1.100"
        
        # Check device2
        device2 = loaded_devices["device2"]
        assert isinstance(device2, MockDevice)
        assert device2.name == "device2"
        assert device2.settings["test_param"] == "value2"
        assert device2.settings["port"] == 5678
        
        # Verify that default settings are preserved where not overridden
        assert device1.settings["port"] == 1234  # Default value
        assert device2.settings["ip_address"] == "localhost"  # Default value


if __name__ == "__main__":
    pytest.main([__file__])
