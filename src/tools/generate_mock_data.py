"""
Mock Data Generator for AQuISS Experiments

This module generates realistic mock data for experiments to enable GUI testing
without requiring actual hardware or long experiment execution times.

Author: Assistant
Created: 2025
License: GPL v2
"""

import numpy as np
import time
from datetime import datetime
from typing import Dict, Any, Optional
import logging

from src.core.experiment import Experiment
from src.core.parameter import Parameter

logger = logging.getLogger(__name__)


class MockDataGenerator:
    """Generates realistic mock data for various experiment types."""
    
    @staticmethod
    def generate_odmr_data(frequencies: np.ndarray, num_resonances: int = 2) -> Dict[str, Any]:
        """
        Generate realistic ODMR data with Lorentzian dips.
        
        Args:
            frequencies: Frequency array in Hz
            num_resonances: Number of resonance dips to generate
            
        Returns:
            Dictionary containing ODMR data
        """
        # Base fluorescence level
        base_level = 1000
        
        # Generate multiple Lorentzian dips
        data = np.ones_like(frequencies) * base_level
        
        for i in range(num_resonances):
            # Random resonance parameters
            center_freq = np.random.uniform(frequencies.min(), frequencies.max())
            width = np.random.uniform(5e6, 20e6)  # 5-20 MHz width
            depth = np.random.uniform(0.1, 0.4)  # 10-40% dip depth
            
            # Lorentzian dip
            lorentzian = 1 - depth * (width/2)**2 / ((frequencies - center_freq)**2 + (width/2)**2)
            data *= lorentzian
        
        # Add noise
        noise_level = 0.02  # 2% noise
        data += np.random.normal(0, noise_level * base_level, len(frequencies))
        
        return {
            'frequencies': frequencies,
            'counts': data,
            'counts_raw': np.tile(data, (5, 1)).T,  # 5 averages
            'powers': np.ones_like(frequencies) * -10.0,  # -10 dBm
            'fit_parameters': [
                {'center': 2.87e9, 'width': 10e6, 'amplitude': 0.2},
                {'center': 2.92e9, 'width': 15e6, 'amplitude': 0.15}
            ],
            'resonance_frequencies': [2.87e9, 2.92e9],
            'settings': {
                'frequency_range': {'start': frequencies.min(), 'stop': frequencies.max()},
                'microwave': {'power': -10.0},
                'acquisition': {'averages': 5}
            }
        }
    
    @staticmethod
    def generate_confocal_data(point_a: tuple, point_b: tuple, resolution: float) -> Dict[str, Any]:
        """
        Generate realistic confocal scan data.
        
        Args:
            point_a: (x_min, y_min) in microns
            point_b: (x_max, y_max) in microns  
            resolution: Step size in microns
            
        Returns:
            Dictionary containing confocal data
        """
        x_min, y_min = point_a
        x_max, y_max = point_b
        
        # Generate position arrays based on step size
        x_pos = np.arange(x_min, x_max + resolution, resolution)
        y_pos = np.arange(y_min, y_max + resolution, resolution)
        
        x_points, y_points = len(x_pos), len(y_pos)
        
        # Create a 2D grid
        X, Y = np.meshgrid(x_pos, y_pos)
        
        # Generate realistic confocal image with some features
        # Base level with some structure
        img = np.ones((y_points, x_points)) * 1000
        
        # Add some bright spots (NV centers)
        for _ in range(np.random.randint(2, 6)):
            center_x = np.random.uniform(x_min, x_max)
            center_y = np.random.uniform(y_min, y_max)
            sigma = np.random.uniform(0.5, 2.0)
            amplitude = np.random.uniform(2000, 5000)
            
            # 2D Gaussian
            gaussian = amplitude * np.exp(-((X - center_x)**2 + (Y - center_y)**2) / (2 * sigma**2))
            img += gaussian
        
        # Add noise
        noise = np.random.normal(0, 50, img.shape)
        img += noise
        
        # Ensure positive values
        img = np.maximum(img, 0)
        
        return {
            'x_pos': x_pos,
            'y_pos': y_pos,
            'count_img': img,
            'raw_img': img + np.random.normal(0, 20, img.shape),
            'count_rate': img,
            'raw_counts': img * 0.001,  # Convert to counts
            'settings': {
                'point_a': point_a,
                'point_b': point_b,
                'resolution': resolution,
                'time_per_pt': 0.001
            }
        }
    
    @staticmethod
    def generate_odmr_sweep_data(frequencies: np.ndarray) -> Dict[str, Any]:
        """
        Generate ODMR sweep data (forward/reverse).
        
        Args:
            frequencies: Frequency array in Hz
            
        Returns:
            Dictionary containing sweep data
        """
        # Generate forward sweep data
        forward_data = MockDataGenerator.generate_odmr_data(frequencies, num_resonances=2)
        
        # Generate reverse sweep data (slightly different due to hysteresis)
        reverse_data = MockDataGenerator.generate_odmr_data(frequencies, num_resonances=2)
        
        # Add some systematic difference between forward and reverse
        reverse_data['counts'] *= np.random.uniform(0.95, 1.05, len(frequencies))
        
        return {
            'frequencies': frequencies,
            'counts_forward': forward_data['counts'],
            'counts_reverse': reverse_data['counts'],
            'counts_averaged': (forward_data['counts'] + reverse_data['counts']) / 2,
            'voltages': np.linspace(-1, 1, len(frequencies)),
            'sweep_time': 1.0,
            'num_steps': len(frequencies),
            'fit_parameters': forward_data['fit_parameters'],
            'resonance_frequencies': forward_data['resonance_frequencies'],
            'settings': forward_data['settings']
        }


def add_mock_data_to_experiment(experiment: Experiment, data_type: str = 'auto') -> None:
    """
    Add mock data to an experiment instance.
    
    Args:
        experiment: Experiment instance to add data to
        data_type: Type of data to generate ('auto', 'odmr', 'confocal', 'odmr_sweep')
    """
    logger.info(f"Adding mock data to experiment: {experiment.name}")
    
    # Set start and end times
    experiment.start_time = datetime.now()
    experiment.end_time = datetime.now()
    
    # Auto-detect experiment type if not specified
    if data_type == 'auto':
        if 'odmr' in experiment.name.lower():
            if 'sweep' in experiment.name.lower():
                data_type = 'odmr_sweep'
            else:
                data_type = 'odmr'
        elif 'confocal' in experiment.name.lower():
            data_type = 'confocal'
        else:
            data_type = 'odmr'  # Default fallback
    
    # Generate appropriate data
    if data_type == 'odmr':
        # Generate ODMR stepped data
        frequencies = np.linspace(2.7e9, 3.0e9, 100)
        mock_data = MockDataGenerator.generate_odmr_data(frequencies)
        
    elif data_type == 'odmr_sweep':
        # Generate ODMR sweep data
        frequencies = np.linspace(2.7e9, 3.0e9, 200)
        mock_data = MockDataGenerator.generate_odmr_sweep_data(frequencies)
        
    elif data_type == 'confocal':
        # Generate confocal data
        mock_data = MockDataGenerator.generate_confocal_data(
            point_a=(-5, -5),  # Start point
            point_b=(5, 5),    # End point
            resolution=0.2     # Step size in microns
        )
        
    else:
        logger.warning(f"Unknown data type: {data_type}")
        return
    
    # Add data to experiment
    experiment.data.update(mock_data)
    
    # Set progress to 100%
    experiment.progress = 100.0
    
    logger.info(f"Mock data added successfully. Data keys: {list(mock_data.keys())}")


def create_mock_experiment_with_data(experiment_class, devices: Dict, settings: Dict = None, 
                                   data_type: str = 'auto') -> Experiment:
    """
    Create an experiment instance and populate it with mock data.
    
    Args:
        experiment_class: Experiment class to instantiate
        devices: Dictionary of devices
        settings: Experiment settings
        data_type: Type of data to generate
        
    Returns:
        Experiment instance with mock data
    """
    # Create experiment instance
    experiment = experiment_class(devices=devices, settings=settings)
    
    # Add mock data
    add_mock_data_to_experiment(experiment, data_type)
    
    return experiment


if __name__ == '__main__':
    # Test the mock data generator
    print("Testing Mock Data Generator...")
    
    # Test ODMR data
    frequencies = np.linspace(2.7e9, 3.0e9, 100)
    odmr_data = MockDataGenerator.generate_odmr_data(frequencies)
    print(f"ODMR data generated: {list(odmr_data.keys())}")
    
    # Test confocal data
    confocal_data = MockDataGenerator.generate_confocal_data(
        point_a=(-5, -5), point_b=(5, 5), resolution=0.5
    )
    print(f"Confocal data generated: {list(confocal_data.keys())}")
    
    print("Mock data generator test completed!")
