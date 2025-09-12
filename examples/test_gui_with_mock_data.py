#!/usr/bin/env python3
"""
Test script for GUI with mock data generation.

This script creates mock experiments with realistic data so you can test
the GUI functionality without needing real hardware.

Usage:
    python test_gui_with_mock_data.py
"""

import sys
import os
import numpy as np
from datetime import datetime

# Add project root to path
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.tools.generate_mock_data import add_mock_data_to_experiment, create_mock_experiment_with_data
from src.Model.experiments.odmr_sweep_continuous import ODMRSweepContinuousExperiment
from src.Model.experiments.odmr_stepped import ODMRSteppedExperiment
from src.Model.experiments.confocal import ConfocalScan_Fast
from src.core.parameter import Parameter

# Mock devices for testing
class MockDevice:
    def __init__(self, name="MockDevice"):
        self.name = name
        self.is_connected = True
        self._is_connected = True
    
    def connect(self): 
        self.is_connected = True
        self._is_connected = True
        print(f"{self.name}: Connected")
    
    def disconnect(self): 
        self.is_connected = False
        self._is_connected = False
        print(f"{self.name}: Disconnected")
    
    def set_frequency(self, freq): print(f"{self.name}: Set frequency to {freq/1e9:.3f} GHz")
    def set_power(self, power): print(f"{self.name}: Set power to {power} dBm")
    def enable_output(self): print(f"{self.name}: Output enabled")
    def disable_output(self): print(f"{self.name}: Output disabled")
    def set_sweep_deviation(self, dev): print(f"{self.name}: Set sweep deviation to {dev/1e6:.1f} MHz")
    def set_sweep_function(self, func): print(f"{self.name}: Set sweep function to {func}")
    def set_sweep_rate(self, rate): print(f"{self.name}: Set sweep rate to {rate/1e6:.2f} MHz/s")
    def set_modulation_type(self, mod_type): print(f"{self.name}: Set modulation type to {mod_type}")
    def enable_modulation(self): print(f"{self.name}: Modulation enabled")
    def disable_modulation(self): print(f"{self.name}: Modulation disabled")
    def get_position(self): return [0.0, 0.0, 0.0]
    def start_process(self, process): print(f"{self.name}: Started process {process}")
    def stop_process(self, process): print(f"{self.name}: Stopped process {process}")
    def clear_process(self, process): print(f"{self.name}: Cleared process {process}")


def create_mock_experiments():
    """Create a set of mock experiments with realistic data."""
    
    # Mock devices (in the format expected by experiments)
    devices = {
        'microwave': {'instance': MockDevice("SG384")},
        'adwin': {'instance': MockDevice("Adwin")},
        'nanodrive': {'instance': MockDevice("Nanodrive")}
    }
    
    experiments = {}
    
    # 1. ODMR Sweep Continuous Experiment
    print("Creating ODMR Sweep Continuous Experiment...")
    odmr_sweep_settings = {
        'frequency_range': {
            'start': 2.7e9,  # 2.7 GHz
            'stop': 3.0e9    # 3.0 GHz
        },
        'microwave': {
            'step_freq': 1e6,  # 1 MHz steps
            'power': -10.0
        },
        'acquisition': {
            'integration_time': 0.001,  # 1 ms
            'settle_time': 0.01,        # 10 ms
            'averages': 5
        }
    }
    
    odmr_sweep_exp = create_mock_experiment_with_data(
        ODMRSweepContinuousExperiment,
        devices=devices,
        settings=odmr_sweep_settings,
        data_type='odmr_sweep'
    )
    experiments['ODMR_Sweep_Continuous'] = odmr_sweep_exp
    
    # 2. ODMR Stepped Experiment
    print("Creating ODMR Stepped Experiment...")
    odmr_stepped_settings = {
        'frequency_range': {
            'start': 2.8e9,  # 2.8 GHz
            'stop': 2.9e9,   # 2.9 GHz
            'steps': 50
        },
        'microwave': {
            'power': -15.0
        },
        'acquisition': {
            'integration_time': 0.1,  # 100 ms
            'averages': 10
        }
    }
    
    odmr_stepped_exp = create_mock_experiment_with_data(
        ODMRSteppedExperiment,
        devices=devices,
        settings=odmr_stepped_settings,
        data_type='odmr'
    )
    experiments['ODMR_Stepped'] = odmr_stepped_exp
    
    # 3. Confocal Scan Experiment
    print("Creating Confocal Scan Experiment...")
    confocal_settings = {
        'point_a': {'x': -5.0, 'y': -5.0},  # Start point
        'point_b': {'x': 5.0, 'y': 5.0},    # End point
        'resolution': 0.5,  # Step size in microns (valid value)
        'time_per_pt': 2.0  # Time per point in ms
    }
    
    confocal_exp = create_mock_experiment_with_data(
        ConfocalScan_Fast,
        devices=devices,
        settings=confocal_settings,
        data_type='confocal'
    )
    experiments['Confocal_Scan'] = confocal_exp
    
    print(f"Created {len(experiments)} mock experiments with data")
    return experiments


def test_dataset_functionality():
    """Test the dataset storage and retrieval functionality."""
    print("\n" + "="*60)
    print("TESTING DATASET FUNCTIONALITY")
    print("="*60)
    
    # Create results directory if it doesn't exist
    results_dir = os.path.join(os.path.dirname(__file__), 'results')
    os.makedirs(results_dir, exist_ok=True)
    print(f"Results will be saved to: {results_dir}")
    
    # Create mock experiments
    experiments = create_mock_experiments()
    
    # Simulate the dataset storage process
    data_sets = {}
    
    for name, experiment in experiments.items():
        print(f"\nTesting dataset storage for: {name}")
        
        # Simulate the store_experiment_data function
        try:
            # Create time tag
            time_tag = experiment.start_time.strftime('%y%m%d-%H_%M_%S')
            print(f"  Time tag: {time_tag}")
            
            # Duplicate experiment (simulate the duplicate() call)
            experiment_copy = experiment  # In real code, this would be experiment.duplicate()
            
            # Store in datasets
            data_sets[time_tag] = experiment_copy
            print(f"  Stored in datasets. Total datasets: {len(data_sets)}")
            
            # Save experiment data to results directory
            if hasattr(experiment, 'data') and experiment.data:
                import pickle
                data_file = os.path.join(results_dir, f"{name}_{time_tag}_data.pkl")
                with open(data_file, 'wb') as f:
                    pickle.dump(experiment.data, f)
                print(f"  Data saved to: {os.path.basename(data_file)}")
            
            # Check data content
            print(f"  Data keys: {list(experiment.data.keys())}")
            print(f"  Experiment name: {experiment.name}")
            print(f"  Settings tag: {experiment.settings.get('tag', 'No tag')}")
            
        except Exception as e:
            print(f"  ERROR: {e}")
    
    print(f"\nFinal dataset count: {len(data_sets)}")
    print(f"Results saved to: {results_dir}")
    print("Dataset functionality test completed!")
    
    return data_sets


def print_experiment_info(experiment):
    """Print information about an experiment."""
    print(f"\nExperiment: {experiment.name}")
    print(f"  Start time: {experiment.start_time}")
    print(f"  End time: {experiment.end_time}")
    print(f"  Progress: {experiment.progress}%")
    print(f"  Data keys: {list(experiment.data.keys())}")
    print(f"  Settings tag: {experiment.settings.get('tag', 'No tag')}")


if __name__ == '__main__':
    print("AQuISS GUI Mock Data Test")
    print("=" * 40)
    
    # Test dataset functionality
    data_sets = test_dataset_functionality()
    
    # Print summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Created {len(data_sets)} datasets")
    
    for time_tag, experiment in data_sets.items():
        print_experiment_info(experiment)
    
    print("\nMock data generation test completed!")
    print("\nYou can now use these experiments in the GUI to test the 'send to dataset' functionality.")
