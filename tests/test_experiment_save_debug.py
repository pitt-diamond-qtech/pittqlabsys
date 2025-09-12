"""
Debug test for experiment save functionality.
This test focuses on the save process to identify the 'settings' error.
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


def test_experiment_save_debug():
    """Debug test to identify the 'settings' error in save functionality."""
    
    # Create a test experiment
    experiment = TestExperiment(
        name="TestExperiment",
        settings=None,
        devices={},
        sub_experiments={},
        log_function=None,
        data_path=None
    )
    
    print(f"✅ Experiment created successfully")
    print(f"   - Name: {experiment.name}")
    print(f"   - Settings type: {type(experiment.settings)}")
    print(f"   - Settings content: {experiment.settings}")
    print(f"   - _settings type: {type(experiment._settings)}")
    print(f"   - _settings content: {experiment._settings}")
    
    # Test the to_dict method
    try:
        experiment_dict = experiment.to_dict()
        print(f"✅ to_dict() succeeded")
        print(f"   - Dict keys: {list(experiment_dict.keys())}")
        if 'TestExperiment' in experiment_dict:
            exp_data = experiment_dict['TestExperiment']
            print(f"   - Experiment data keys: {list(exp_data.keys())}")
            if 'settings' in exp_data:
                print(f"   - Settings in dict: {exp_data['settings']}")
            else:
                print(f"   ❌ 'settings' key missing from experiment dict")
    except Exception as e:
        print(f"❌ to_dict() failed: {e}")
        raise
    
    # Test save_aqs method
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_file = os.path.join(temp_dir, "test_experiment.json")
        
        try:
            experiment.save_aqs(temp_file)
            print(f"✅ save_aqs() succeeded")
            print(f"   - File created: {os.path.exists(temp_file)}")
            
            # Check if file has content
            if os.path.exists(temp_file):
                with open(temp_file, 'r') as f:
                    content = f.read()
                    print(f"   - File size: {len(content)} characters")
                    if 'settings' in content:
                        print(f"   - 'settings' found in saved file")
                    else:
                        print(f"   ❌ 'settings' not found in saved file")
                        
        except Exception as e:
            print(f"❌ save_aqs() failed: {e}")
            print(f"   - Error type: {type(e)}")
            import traceback
            print(f"   - Traceback: {traceback.format_exc()}")
            raise


if __name__ == "__main__":
    test_experiment_save_debug()
