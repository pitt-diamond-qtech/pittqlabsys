"""
Debug test for the specific experiments that are failing on the lab PC.
This test focuses on the experiments mentioned in the lab PC error logs.
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch

# Import the specific experiments that are failing on lab PC
from src.Model.experiments.confocal import ConfocalScan_Fast, ConfocalScan_Slow, Confocal_Point
from src.Model.experiments.nanodrive_adwin_confocal_scan_slow import NanodriveAdwinConfocalScanSlow
from src.Model.experiments.nanodrive_adwin_confocal_scan_fast import NanodriveAdwinConfocalScanFast
from src.Model.experiments.nanodrive_adwin_confocal_point import NanodriveAdwinConfocalPoint
from src.Model.experiments.odmr_simple_adwin import SimpleODMRExperiment


def test_confocal_experiments_save():
    """Test save functionality for confocal experiments."""
    
    # Create mock devices
    mock_nanodrive = Mock()
    mock_nanodrive.__class__.__name__ = "MCLNanoDrive"
    mock_nanodrive.settings = {'test_setting': 'test_value'}
    
    mock_adwin = Mock()
    mock_adwin.__class__.__name__ = "AdwinGoldDevice"
    mock_adwin.settings = {'test_setting': 'test_value'}
    
    devices = {
        'nanodrive': {'instance': mock_nanodrive, 'settings': mock_nanodrive.settings},
        'adwin': {'instance': mock_adwin, 'settings': mock_adwin.settings}
    }
    
    # Test each confocal experiment
    experiments = [
        ConfocalScan_Fast,
        ConfocalScan_Slow, 
        Confocal_Point
    ]
    
    for exp_class in experiments:
        print(f"\n🔧 Testing {exp_class.__name__}")
        
        try:
            # Create experiment (mimicking export tool)
            experiment = exp_class(
                devices=devices,
                experiments={},
                name=exp_class.__name__,
                settings=None,
                log_function=None,
                data_path=None
            )
            
            print(f"   ✅ {exp_class.__name__} created successfully")
            
            # Test save
            with tempfile.TemporaryDirectory() as temp_dir:
                filename = os.path.join(temp_dir, f'{exp_class.__name__}.json')
                
                try:
                    experiment.save_aqs(filename)
                    print(f"   ✅ {exp_class.__name__} save_aqs() succeeded")
                    
                except Exception as e:
                    print(f"   ❌ {exp_class.__name__} save_aqs() failed: {e}")
                    print(f"      - Error type: {type(e)}")
                    import traceback
                    print(f"      - Traceback: {traceback.format_exc()}")
                    raise
                    
        except Exception as e:
            print(f"   ❌ {exp_class.__name__} creation failed: {e}")
            print(f"      - Error type: {type(e)}")
            import traceback
            print(f"      - Traceback: {traceback.format_exc()}")
            raise


def test_nanodrive_adwin_experiments_save():
    """Test save functionality for nanodrive-adwin experiments."""
    
    # Create mock devices
    mock_nanodrive = Mock()
    mock_nanodrive.__class__.__name__ = "MCLNanoDrive"
    mock_nanodrive.settings = {'test_setting': 'test_value'}
    
    mock_adwin = Mock()
    mock_adwin.__class__.__name__ = "AdwinGoldDevice"
    mock_adwin.settings = {'test_setting': 'test_value'}
    
    devices = {
        'nanodrive': {'instance': mock_nanodrive, 'settings': mock_nanodrive.settings},
        'adwin': {'instance': mock_adwin, 'settings': mock_adwin.settings}
    }
    
    # Test each nanodrive-adwin experiment
    experiments = [
        NanodriveAdwinConfocalScanSlow,
        NanodriveAdwinConfocalScanFast,
        NanodriveAdwinConfocalPoint
    ]
    
    for exp_class in experiments:
        print(f"\n🔧 Testing {exp_class.__name__}")
        
        try:
            # Create experiment (mimicking export tool)
            experiment = exp_class(
                devices=devices,
                experiments={},
                name=exp_class.__name__,
                settings=None,
                log_function=None,
                data_path=None
            )
            
            print(f"   ✅ {exp_class.__name__} created successfully")
            
            # Test save
            with tempfile.TemporaryDirectory() as temp_dir:
                filename = os.path.join(temp_dir, f'{exp_class.__name__}.json')
                
                try:
                    experiment.save_aqs(filename)
                    print(f"   ✅ {exp_class.__name__} save_aqs() succeeded")
                    
                except Exception as e:
                    print(f"   ❌ {exp_class.__name__} save_aqs() failed: {e}")
                    print(f"      - Error type: {type(e)}")
                    import traceback
                    print(f"      - Traceback: {traceback.format_exc()}")
                    raise
                    
        except Exception as e:
            print(f"   ❌ {exp_class.__name__} creation failed: {e}")
            print(f"      - Error type: {type(e)}")
            import traceback
            print(f"      - Traceback: {traceback.format_exc()}")
            raise


def test_simple_odmr_experiment_save():
    """Test save functionality for SimpleODMRExperiment."""
    
    # Create mock devices
    mock_sg384 = Mock()
    mock_sg384.__class__.__name__ = "SG384Generator"
    mock_sg384.settings = {'test_setting': 'test_value'}
    
    mock_adwin = Mock()
    mock_adwin.__class__.__name__ = "AdwinGoldDevice"
    mock_adwin.settings = {'test_setting': 'test_value'}
    
    devices = {
        'microwave': {'instance': mock_sg384, 'settings': mock_sg384.settings},
        'adwin': {'instance': mock_adwin, 'settings': mock_adwin.settings}
    }
    
    print(f"\n🔧 Testing SimpleODMRExperiment")
    
    try:
        # Create experiment (mimicking export tool)
        experiment = SimpleODMRExperiment(
            devices=devices,
            experiments={},
            name="SimpleODMRExperiment",
            settings=None,
            log_function=None,
            data_path=None
        )
        
        print(f"   ✅ SimpleODMRExperiment created successfully")
        
        # Test save
        with tempfile.TemporaryDirectory() as temp_dir:
            filename = os.path.join(temp_dir, 'SimpleODMRExperiment.json')
            
            try:
                experiment.save_aqs(filename)
                print(f"   ✅ SimpleODMRExperiment save_aqs() succeeded")
                
            except Exception as e:
                print(f"   ❌ SimpleODMRExperiment save_aqs() failed: {e}")
                print(f"      - Error type: {type(e)}")
                import traceback
                print(f"      - Traceback: {traceback.format_exc()}")
                raise
                
    except Exception as e:
        print(f"   ❌ SimpleODMRExperiment creation failed: {e}")
        print(f"      - Error type: {type(e)}")
        import traceback
        print(f"      - Traceback: {traceback.format_exc()}")
        raise


if __name__ == "__main__":
    test_confocal_experiments_save()
    test_nanodrive_adwin_experiments_save()
    test_simple_odmr_experiment_save()
