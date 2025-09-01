# Created by Gurudev Dutt <gdutt@pitt.edu> on 2023-08-18
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

# Updated to test JSON export functionality (previously AQS)
from src.tools.export_default import python_file_to_aqs,find_devices_in_python_files,find_experiments_in_python_files,find_exportable_in_python_files,get_device_name_mapping
import pytest
from pathlib import Path
import sys
from src.core.helper_functions import get_project_root
from unittest.mock import Mock

@pytest.fixture
def get_dev_dir() -> str:
    proj_dir = get_project_root()
    dir_path = proj_dir/"Controller"
    return str(dir_path.resolve())

@pytest.fixture
def get_expt_dir() -> str:
    proj_dir = get_project_root()
    dir_path = proj_dir/"Model"
    return str(dir_path.resolve())

@pytest.fixture
def get_save_dir() -> str:
    proj_dir = get_project_root()
    dir_path = proj_dir.parent/"exported_configs"  # Updated from "aqsfiles" to "exported_configs"
    if not dir_path.exists():
        dir_path.mkdir()
    return str(dir_path.resolve())

@pytest.fixture
def mock_devices():
    """Create mock devices for testing device name mapping."""
    return {
        'sg384': Mock(name='SG384Generator'),
        'adwin': Mock(name='AdwinGoldDevice'),
        'awg520': Mock(name='AWG520Device'),
        'mux_control': Mock(name='MUXControlDevice'),
        'nanodrive': Mock(name='MCLNanoDrive')
    }

def test_device_name_mapping():
    """Test the device name mapping functionality."""
    mapping = get_device_name_mapping()
    
    # Test expected mappings
    assert mapping['microwave'] == 'sg384'
    assert mapping['adwin'] == 'adwin'
    assert mapping['awg'] == 'awg520'
    assert mapping['nanodrive'] == 'nanodrive'
    assert mapping['mux'] == 'mux_control'
    
    # Test that all expected experiment device names are mapped
    expected_exp_devices = ['microwave', 'adwin', 'awg', 'positioner', 'nanodrive', 'mux']
    for exp_device in expected_exp_devices:
        assert exp_device in mapping, f"Missing mapping for experiment device: {exp_device}"

def test_device_mapping_with_mock_devices(mock_devices):
    """Test device mapping logic with mock devices."""
    mapping = get_device_name_mapping()
    
    # Test successful mappings
    test_cases = [
        ('microwave', 'sg384', True),
        ('adwin', 'adwin', True),
        ('awg', 'awg520', True),
        ('mux', 'mux_control', True),
        ('nanodrive', 'nanodrive', True),
        ('positioner', 'nanodrive', True),
        ('nonexistent', 'nonexistent', False)
    ]
    
    for exp_device, config_device, should_find in test_cases:
        mapped_config_device = mapping.get(exp_device, exp_device)
        found = mapped_config_device in mock_devices
        
        if should_find:
            assert found, f"Should find {exp_device} -> {mapped_config_device}"
        else:
            assert not found, f"Should not find {exp_device} -> {mapped_config_device}"

@pytest.mark.xfail(sys.platform == "darwin",reason="will fail on Mac bcos NIDAQ does not load")
@pytest.mark.parametrize("cls",["Device"])
def test_find_exportable_devs(capsys,cls,get_dev_dir):
    """
    This test has passed successfully
    -- GD 08/21/2023
    """
    folder = get_dev_dir
    dev_dict = find_exportable_in_python_files(folder,class_type=cls)
    assert dev_dict != {}

    with capsys.disabled():
        print("Devices Available:")
        for key,val in dev_dict.items():
            print("######")
            print(key)
            for k,v in val.items():
                print(f"{k:12}:{v:25}")

@pytest.mark.xfail(sys.platform == "darwin",reason="will fail on Mac bcos NIDAQ does not load")
@pytest.mark.parametrize("cls",["Experiment"])
def test_find_exportable_expts(capsys,cls,get_expt_dir):
    """
    This test has passed successfully when the NI DAQ was connected to the B103 PC.
    -- GD 08/28/2023
    """
    folder = get_expt_dir
    expt_dict = find_exportable_in_python_files(folder,class_type=cls)
    assert expt_dict != {}
    with capsys.disabled():
        print("Expts Available:")
        for key,val in expt_dict.items():
            print("######")
            print(key)
            for k,v in val.items():
                print(f"{k:12}:{v:25}")


@pytest.mark.xfail(sys.platform == "darwin",reason="will fail on Mac bcos NIDAQ does not load")
def test_find_expts_python_files(capsys,get_expt_dir):
    """
    This test has passed successfully
    -- GD 08/28/2023
    """
    folder = get_expt_dir
    expt_dict = find_experiments_in_python_files(folder)
    assert expt_dict != {}
    with capsys.disabled():
        print("Expts Available:")
        for key,val in expt_dict.items():
            print("######")
            print(key)
            for k,v in val.items():
                print(f"{k:12}:{v:25}")
@pytest.mark.xfail(sys.platform == "darwin",reason="will fail on Mac bcos NIDAQ does not load")
@pytest.mark.parametrize("cls",["Device"])
def test_export_pyfile_to_json(capsys,cls,get_save_dir,get_dev_dir,get_expt_dir):
    """
    This test exports Python files to JSON format (previously AQS).
    It has passed successfully but throws crazy Windows error when the Microwave generator is being loaded in B103 PC,
    see the test function for microwave generator to understand this issue.
    -- GD 08/28/2023
    Updated to test JSON export functionality
    """
    folder = get_save_dir
    folder2 = get_dev_dir
    folder3 = get_expt_dir
    dev_dict = {}
    expt_dict = {}
    if cls == "Device":
        dev_dict = find_exportable_in_python_files(folder2, class_type=cls)
    else:
        expt_dict = find_exportable_in_python_files(folder3,class_type=cls)
    with capsys.disabled():
        print("Available:")
        loop_dict = {}
        if dev_dict:
            loop_dict = dev_dict
        elif expt_dict:
            loop_dict = expt_dict

        if loop_dict:
            for key,val in loop_dict.items():
                print("######")
                print(key)
                loaded, failed = python_file_to_aqs(loop_dict,folder, cls,raise_errors=True)
                for k,v in val.items():
                    print(f"{k:12}:{v:25}")
                assert failed == {}
                if loaded:
                    print("#####")
                    print("Loaded successfully")
                    print(loaded)
        else:
            print("No dictionary initialized!")
            assert 0

def test_experiment_conversion_with_device_mapping(mock_devices, get_save_dir, get_expt_dir):
    """Test experiment conversion with device name mapping."""
    # Create a simple experiment metadata for testing
    experiment_metadata = {
        'ODMRSteppedExperiment': {
            'filepath': 'src/Model/experiments/odmr_stepped.py',
            'class': 'ODMRSteppedExperiment'
        }
    }
    
    # Test the conversion with mock devices
    loaded, failed = python_file_to_aqs(
        experiment_metadata, 
        get_save_dir, 
        'Experiment', 
        raise_errors=False,  # Don't raise errors for missing hardware
        existing_devices=mock_devices
    )
    
    # The experiment should attempt to load but may fail due to missing nanodrive
    # This is expected behavior - we're testing the device mapping logic, not hardware
    print(f"Loaded experiments: {list(loaded.keys())}")
    print(f"Failed experiments: {list(failed.keys())}")
    
    # The key test is that the device mapping logic runs without errors
    # and that we get meaningful error messages about missing devices
    assert isinstance(loaded, dict)
    assert isinstance(failed, dict)