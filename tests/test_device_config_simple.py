"""
Simple test for the device configuration system.

This is a quick test to verify the basic functionality works
before running the full test suite.
"""

import pytest
import json
import tempfile
from pathlib import Path
import sys

# Add src to path for imports
import os
os.chdir(str(Path(__file__).parent.parent))  # Change to project root
sys.path.insert(0, '.')

from src.core.device_config import DeviceConfigManager


def test_basic_device_config_loading():
    """Basic test to verify device config loading works."""
    
    # Create a temporary test config
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        test_config = {
            "devices": {
                "test_device": {
                    "class": "MockDevice",
                    "filepath": "src/Controller/mock_device.py",
                    "settings": {
                        "test_param": "test_value"
                    }
                }
            }
        }
        json.dump(test_config, f)
        config_path = Path(f.name)
    
    try:
        # Test basic functionality
        manager = DeviceConfigManager(config_path)
        
        # Check if config was loaded
        assert manager.config is not None
        assert "devices" in manager.config
        
        # Check if device configs can be retrieved
        device_configs = manager.get_device_configs()
        assert "test_device" in device_configs
        
        # Check specific device config
        device_config = manager.get_device_config("test_device")
        assert device_config["class"] == "MockDevice"
        assert device_config["settings"]["test_param"] == "test_value"
        
        print("✅ Basic device config loading test passed!")
        
    finally:
        # Clean up
        config_path.unlink()


if __name__ == "__main__":
    test_basic_device_config_loading()
    print("🎉 All basic tests passed!")
