#!/usr/bin/env python3
"""
Mock Data Experiment for GUI Testing

This experiment generates realistic mock data for testing GUI functionality
without requiring real hardware. It can be loaded as a regular experiment
in the main GUI.

Usage:
1. Load this experiment in the main GUI
2. Run it to generate mock data
3. Test the "send to dataset" functionality
"""

import sys
import os
import numpy as np
from datetime import datetime

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.core.experiment import Experiment
from src.core.parameter import Parameter
from src.tools.generate_mock_data import MockDataGenerator


class MockDataExperiment(Experiment):
    """
    Mock Data Experiment for GUI Testing
    
    This experiment generates realistic mock data for testing GUI functionality
    without requiring real hardware. It creates ODMR sweep data, confocal scan data,
    and other experimental data types.
    """
    
    _DEFAULT_SETTINGS = [
        Parameter('data_type', 'odmr_sweep', ['odmr_sweep', 'odmr_stepped', 'confocal'], 
                 'Type of mock data to generate'),
        Parameter('num_points', 200, int, 'Number of data points to generate'),
        Parameter('noise_level', 0.1, float, 'Noise level (0-1)'),
        Parameter('generate_plot', True, bool, 'Generate plot data'),
        Parameter('save_data', True, bool, 'Save generated data to file'),
    ]
    
    _DEVICES = {}  # No devices required for mock data generation
    _EXPERIMENTS = {}  # No sub-experiments for this simple experiment
    
    def __init__(self, name=None, settings=None, devices=None, log_function=None, data_path=None):
        """
        Initialize the Mock Data Experiment.
        
        Args:
            name: Name of the experiment
            settings: Experiment settings
            devices: Device dictionary (not used for mock data)
            log_function: Logging function
            data_path: Path to save data
        """
        super().__init__(name, settings, devices, log_function, data_path)
        
        # Set default name if not provided
        if self.name is None:
            self.name = "MockDataExperiment"
        
        self.log(f"Mock Data Experiment initialized: {self.name}")
        self.log(f"Data type: {self.settings['data_type']}")
        self.log(f"Number of points: {self.settings['num_points']}")
    
    def _function(self):
        """
        Main experiment function - generates mock data.
        """
        self.log("Starting mock data generation...")
        
        try:
            # Generate mock data based on selected type
            data_type = self.settings['data_type']
            num_points = self.settings['num_points']
            noise_level = self.settings['noise_level']
            
            if data_type == 'odmr_sweep':
                self.log("Generating ODMR sweep data...")
                frequencies = np.linspace(2.7e9, 3.0e9, num_points)
                mock_data = MockDataGenerator.generate_odmr_sweep_data(frequencies)
                
            elif data_type == 'odmr_stepped':
                self.log("Generating ODMR stepped data...")
                frequencies = np.linspace(2.7e9, 3.0e9, num_points)
                mock_data = MockDataGenerator.generate_odmr_data(frequencies)
                
            elif data_type == 'confocal':
                self.log("Generating confocal scan data...")
                mock_data = MockDataGenerator.generate_confocal_data(
                    point_a=(-5, -5), point_b=(5, 5), resolution=0.5
                )
                
            else:
                raise ValueError(f"Unknown data type: {data_type}")
            
            # Add noise if specified
            if noise_level > 0:
                self.log(f"Adding noise level: {noise_level}")
                for key, value in mock_data.items():
                    if isinstance(value, np.ndarray) and value.dtype in [np.float64, np.float32]:
                        noise = np.random.normal(0, noise_level * np.std(value), value.shape)
                        mock_data[key] = value + noise
            
            # Store the generated data
            self.data = mock_data
            
            # Generate plot data if requested
            if self.settings['generate_plot']:
                self.log("Generating plot data...")
                self._generate_plot_data()
            
            # Save data if requested
            if self.settings['save_data']:
                self._save_generated_data()
            
            self.log(f"Mock data generation completed successfully!")
            self.log(f"Generated data keys: {list(self.data.keys())}")
            
        except Exception as e:
            self.log(f"Error generating mock data: {e}")
            raise
    
    def _generate_plot_data(self):
        """Generate additional data for plotting."""
        if 'frequencies' in self.data and 'counts_averaged' in self.data:
            # ODMR data - add fit parameters
            self.data['fit_parameters'] = {
                'resonance_freq': 2.87e9,
                'linewidth': 1e6,
                'amplitude': 0.5,
                'baseline': 1.0
            }
            self.data['resonance_frequencies'] = [2.87e9]
            
        elif 'x_pos' in self.data and 'y_pos' in self.data:
            # Confocal data - add summary statistics
            self.data['max_intensity'] = np.max(self.data['count_img'])
            self.data['min_intensity'] = np.min(self.data['count_img'])
            self.data['mean_intensity'] = np.mean(self.data['count_img'])
    
    def _save_generated_data(self):
        """Save generated data to file."""
        try:
            if self.data_path:
                import pickle
                data_file = os.path.join(self.data_path, f"{self.name}_mock_data.pkl")
                with open(data_file, 'wb') as f:
                    pickle.dump(self.data, f)
                self.log(f"Data saved to: {data_file}")
        except Exception as e:
            self.log(f"Error saving data: {e}")
    
    def get_experiment_info(self):
        """Return information about the experiment."""
        info = {
            'name': self.name,
            'data_type': self.settings['data_type'],
            'num_points': self.settings['num_points'],
            'noise_level': self.settings['noise_level'],
            'data_keys': list(self.data.keys()) if hasattr(self, 'data') and self.data else [],
            'start_time': self.start_time,
            'end_time': self.end_time,
            'progress': self.progress
        }
        return info


def create_mock_data_experiment():
    """Create a mock data experiment instance."""
    return MockDataExperiment(
        name="MockDataExperiment",
        settings={
            'data_type': 'odmr_sweep',
            'num_points': 200,
            'noise_level': 0.1,
            'generate_plot': True,
            'save_data': True
        }
    )


if __name__ == "__main__":
    # Test the experiment
    print("Testing Mock Data Experiment...")
    
    experiment = create_mock_data_experiment()
    print(f"Created experiment: {experiment.name}")
    print(f"Settings: {experiment.settings}")
    
    # Run the experiment
    experiment.start_time = datetime.now()
    experiment._function()
    experiment.end_time = datetime.now()
    experiment.progress = 100.0
    
    # Print results
    info = experiment.get_experiment_info()
    print(f"\nExperiment completed!")
    print(f"Data keys: {info['data_keys']}")
    print(f"Duration: {experiment.end_time - experiment.start_time}")
    
    print("\nMock Data Experiment test completed!")
