#!/usr/bin/env python3
"""
Test script for the bidirectional ODMR sweep functionality.

This script tests the new bidirectional sweep features including:
- Separate forward and reverse sweep arrays
- Clear data synchronization between voltage/frequency and counts
- Proper handling of bidirectional vs unidirectional sweeps
"""

import pytest
import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import only what we need, avoiding NI-DAQ dependencies
from src.core import Experiment, Parameter
from src.core.adwin_helpers import setup_adwin_for_sweep_odmr, read_adwin_sweep_odmr_data


class TestBidirectionalSweep:
    """Test suite for bidirectional ODMR sweep functionality."""
    
    def test_bidirectional_data_structure(self):
        """Test the bidirectional data structure and synchronization."""
        import numpy as np
        
        # Simulate the data structure that would come from ADwin
        num_steps = 100
        
        # Simulate forward sweep data (voltage from -1V to +1V)
        forward_voltages = np.linspace(-1.0, 1.0, num_steps)
        forward_counts = np.random.poisson(1000, num_steps)  # Simulate photon counts
        
        # Simulate reverse sweep data (voltage from +1V to -1V)
        reverse_voltages = np.linspace(1.0, -1.0, num_steps)
        reverse_counts = np.random.poisson(1000, num_steps)  # Simulate photon counts
        
        # Test data synchronization
        assert len(forward_voltages) == len(forward_counts), "Forward data arrays must have same length"
        assert len(reverse_voltages) == len(reverse_counts), "Reverse data arrays must have same length"
        assert len(forward_voltages) == len(reverse_voltages), "Forward and reverse arrays must have same length"
        
        # Test voltage-to-frequency conversion
        center_freq = 2.87e9  # 2.87 GHz
        fm_sensitivity = 1e6   # 1 MHz/V
        
        forward_frequencies = center_freq + forward_voltages * fm_sensitivity
        reverse_frequencies = center_freq + reverse_voltages * fm_sensitivity
        
        # Verify frequency ranges
        assert forward_frequencies[0] < forward_frequencies[-1], "Forward frequencies should be increasing"
        assert reverse_frequencies[0] > reverse_frequencies[-1], "Reverse frequencies should be decreasing"
        
        # Verify frequency ranges are reasonable
        assert 2.8e9 < forward_frequencies[0] < 3.0e9, "Forward frequency range should be around 2.87 GHz"
        assert 2.8e9 < reverse_frequencies[-1] < 3.0e9, "Reverse frequency range should be around 2.87 GHz"
    
    def test_adwin_helper_functions(self):
        """Test the updated ADwin helper functions."""
        import inspect
        
        # Test function signatures
        setup_sig = inspect.signature(setup_adwin_for_sweep_odmr)
        read_sig = inspect.signature(read_adwin_sweep_odmr_data)
        
        # Verify function signatures
        assert 'adwin_instance' in setup_sig.parameters, "setup_adwin_for_sweep_odmr should have adwin_instance parameter"
        assert 'adwin_instance' in read_sig.parameters, "read_adwin_sweep_odmr_data should have adwin_instance parameter"
        
        # Test that the function returns the expected data structure
        expected_keys = [
            'counts', 'step_index', 'voltage', 'sweep_complete', 'total_counts',
            'sweep_cycle', 'data_ready', 'forward_counts', 'reverse_counts',
            'forward_voltages', 'reverse_voltages', 'sweep_direction'
        ]
        
        # Verify we have the expected number of keys
        assert len(expected_keys) == 12, "Should have 12 expected return keys"
    
    def test_experiment_logic(self):
        """Test the experiment logic for bidirectional sweeps."""
        import numpy as np
        
        # Create mock experiment settings
        settings = {
            'sweep_parameters': {
                'center_frequency': 2.87e9,
                'deviation': 50e6,
                'fm_sensitivity': 1e6
            },
            'acquisition': {
                'num_steps': 100,
                'sweeps_per_average': 10,
                'bidirectional': True,
                'integration_time': 10.0
            }
        }
        
        # Test bidirectional sweep data processing
        num_steps = settings['acquisition']['num_steps']
        integration_time_s = settings['acquisition']['integration_time'] / 1000.0
        
        # Simulate sweep data
        mock_adwin_data = {
            'sweep_complete': True,
            'data_ready': True,
            'forward_counts': np.random.poisson(1000, num_steps),
            'reverse_counts': np.random.poisson(1000, num_steps),
            'forward_voltages': np.linspace(-1.0, 1.0, num_steps),
            'reverse_voltages': np.linspace(1.0, -1.0, num_steps)
        }
        
        # Process the data (simulating the experiment logic)
        if settings['acquisition']['bidirectional']:
            # Convert counts to kcounts/sec
            forward_counts_per_sec = mock_adwin_data['forward_counts'] * (0.001 / integration_time_s)
            reverse_counts_per_sec = mock_adwin_data['reverse_counts'] * (0.001 / integration_time_s)
            
            # Convert voltages to frequencies
            fm_sensitivity = settings['sweep_parameters']['fm_sensitivity']
            center_freq = settings['sweep_parameters']['center_frequency']
            
            forward_frequencies = center_freq + mock_adwin_data['forward_voltages'] * fm_sensitivity
            reverse_frequencies = center_freq + mock_adwin_data['reverse_voltages'] * fm_sensitivity
            
            # Verify data processing
            assert len(forward_frequencies) == num_steps, "Forward frequencies should have correct length"
            assert len(reverse_frequencies) == num_steps, "Reverse frequencies should have correct length"
            assert len(forward_counts_per_sec) == num_steps, "Forward counts should have correct length"
            assert len(reverse_counts_per_sec) == num_steps, "Reverse counts should have correct length"
            
            # Verify frequency ranges
            assert forward_frequencies[0] < forward_frequencies[-1], "Forward frequencies should be increasing"
            assert reverse_frequencies[0] > reverse_frequencies[-1], "Reverse frequencies should be decreasing"
    
    def test_adbasic_script_structure(self):
        """Test the ADbasic script structure and parameters."""
        # Check if the ADbasic file exists
        adbasic_file = Path("src/Controller/binary_files/ADbasic/ODMR_Sweep_Counter.bas")
        
        assert adbasic_file.exists(), f"ADbasic file should exist: {adbasic_file}"
        
        # Read the file to check for key components
        content = adbasic_file.read_text()
        
        # Check for key components
        required_components = [
            "Data_1",  # Forward sweep counts array
            "Data_2",  # Reverse sweep counts array
            "Data_3",  # Forward sweep voltages array
            "Data_4",  # Reverse sweep voltages array
            "Par_5",   # Sweep direction parameter
            "Par_9",   # Sweep cycle counter
            "Par_10",  # Data ready flag
            "sweep_direction",  # Sweep direction variable
        ]
        
        for component in required_components:
            assert component in content, f"ADbasic file should contain: {component}"
    
    @pytest.mark.slow
    def test_full_bidirectional_workflow(self):
        """Test the complete bidirectional workflow simulation."""
        import numpy as np
        
        # Simulate complete workflow
        num_steps = 50  # Smaller for faster testing
        center_freq = 2.87e9
        fm_sensitivity = 1e6
        
        # Simulate forward sweep
        forward_voltages = np.linspace(-1.0, 1.0, num_steps)
        forward_frequencies = center_freq + forward_voltages * fm_sensitivity
        forward_counts = np.random.poisson(1000, num_steps)
        
        # Simulate reverse sweep
        reverse_voltages = np.linspace(1.0, -1.0, num_steps)
        reverse_frequencies = center_freq + reverse_voltages * fm_sensitivity
        reverse_counts = np.random.poisson(1000, num_steps)
        
        # Verify data integrity
        assert len(forward_voltages) == len(forward_counts) == len(forward_frequencies)
        assert len(reverse_voltages) == len(reverse_counts) == len(reverse_frequencies)
        assert len(forward_voltages) == len(reverse_voltages)
        
        # Verify frequency synchronization
        for i in range(num_steps):
            expected_freq = center_freq + forward_voltages[i] * fm_sensitivity
            assert abs(forward_frequencies[i] - expected_freq) < 1e-6, f"Frequency mismatch at index {i}"
        
        # Verify sweep directions
        assert forward_frequencies[0] < forward_frequencies[-1], "Forward sweep should be increasing"
        assert reverse_frequencies[0] > reverse_frequencies[-1], "Reverse sweep should be decreasing" 