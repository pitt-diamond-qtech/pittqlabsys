"""
Debug test for export tool save functionality.
This test mimics what the export tool does to identify the 'settings' error.
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch

from src.core.experiment import Experiment
from src.core.parameter import Parameter


class TestExperiment(Experiment):
    """Simple test experiment for debugging save functionality."""
    
    _DEFAULT_SETTINGS = [
        Parameter('test_param', 'test_value', str, 'Test parameter')
    ]
    
    _DEVICES = {}
    _EXPERIMENTS = {}
    
    def _function(self):
        """Dummy function."""
        pass


def test_export_tool_save_debug():
    """Debug test that mimics the export tool's save process."""
    
    # Create a test experiment (mimicking export tool creation)
    experiment = TestExperiment(
        name="TestExperiment",
        settings=None,  # This is what export tool passes
        devices={},
        sub_experiments={},
        log_function=None,
        data_path=None
    )
    
    print(f"✅ Experiment created successfully")
    print(f"   - Name: {experiment.name}")
    print(f"   - Settings type: {type(experiment.settings)}")
    print(f"   - Settings content: {experiment.settings}")
    
    # Test the exact save process from export tool
    with tempfile.TemporaryDirectory() as temp_dir:
        filename = os.path.join(temp_dir, 'TestExperiment.json')
        
        print(f"🔧 Attempting to save to: {filename}")
        
        try:
            # This is the exact call from export tool: value.save_aqs(filename)
            experiment.save_aqs(filename)
            print(f"✅ save_aqs() succeeded")
            
            # Check if file was created and has content
            if os.path.exists(filename):
                with open(filename, 'r') as f:
                    content = f.read()
                    print(f"   - File size: {len(content)} characters")
                    if 'settings' in content:
                        print(f"   - 'settings' found in saved file")
                    else:
                        print(f"   ❌ 'settings' not found in saved file")
            else:
                print(f"   ❌ File was not created")
                
        except Exception as e:
            print(f"❌ save_aqs() failed: {e}")
            print(f"   - Error type: {type(e)}")
            import traceback
            print(f"   - Traceback: {traceback.format_exc()}")
            raise


def test_export_tool_save_with_devices():
    """Test save functionality with devices (like real experiments)."""
    
    # Create mock devices
    mock_device = Mock()
    mock_device.__class__.__name__ = "MockDevice"
    mock_device.settings = {'test_setting': 'test_value'}
    
    # Create experiment with devices (mimicking real experiments)
    experiment = TestExperiment(
        name="TestExperimentWithDevices",
        settings=None,
        devices={'test_device': {'instance': mock_device, 'settings': mock_device.settings}},
        sub_experiments={},
        log_function=None,
        data_path=None
    )
    
    print(f"✅ Experiment with devices created successfully")
    print(f"   - Name: {experiment.name}")
    print(f"   - Devices: {list(experiment.devices.keys())}")
    
    # Test save process
    with tempfile.TemporaryDirectory() as temp_dir:
        filename = os.path.join(temp_dir, 'TestExperimentWithDevices.json')
        
        try:
            experiment.save_aqs(filename)
            print(f"✅ save_aqs() with devices succeeded")
            
            if os.path.exists(filename):
                with open(filename, 'r') as f:
                    content = f.read()
                    print(f"   - File size: {len(content)} characters")
                    if 'settings' in content:
                        print(f"   - 'settings' found in saved file")
                    if 'devices' in content:
                        print(f"   - 'devices' found in saved file")
                        
        except Exception as e:
            print(f"❌ save_aqs() with devices failed: {e}")
            print(f"   - Error type: {type(e)}")
            import traceback
            print(f"   - Traceback: {traceback.format_exc()}")
            raise


if __name__ == "__main__":
    test_export_tool_save_debug()
    test_export_tool_save_with_devices()
