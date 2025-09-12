"""
Tests for ODMR Scan Example

This module contains tests for the ODMR scan example script.
Tests cover both mock and real hardware scenarios.
"""

import pytest
import numpy as np
import unittest.mock as mock
from unittest.mock import MagicMock, patch
import sys
import os
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from examples.odmr_scan_example import run_odmr_scan, create_devices, create_mock_devices


class TestODMRScanExample:
    """Test cases for ODMR scan example."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create mock devices following the pattern from existing tests
        self.mock_microwave = MagicMock()
        self.mock_adwin = MagicMock()
        self.mock_nanodrive = MagicMock()
        
        # Configure mock devices with settings
        self.mock_microwave.settings = {
            'frequency': 2.87e9,
            'power': -10.0,
            'phase': 0.0,
            'amplitude': -10.0,
            'enable_output': False,
            'enable_modulation': False
        }
        
        self.mock_adwin.settings = {
            'process_1': {'running': False},
            'process_2': {'running': False},
            'array_size': 1000
        }
        
        self.mock_nanodrive.settings = {
            'serial': 2849,
            'step_size': 1.0,
            'max_velocity': 1000.0
        }
        
        # Mock device methods
        self.mock_microwave.update = MagicMock()
        self.mock_adwin.update = MagicMock()
        self.mock_nanodrive.update = MagicMock()
        
        self.mock_microwave.read_probes = MagicMock(return_value=2.87e9)
        self.mock_adwin.read_probes = MagicMock(return_value=np.random.poisson(100, 100))
        self.mock_nanodrive.read_probes = MagicMock(return_value=0.0)
    
    def test_create_mock_devices(self):
        """Test mock device creation."""
        # Patch the imports from src.Controller where they're actually imported
        with patch('src.Controller.SG384Generator', return_value=self.mock_microwave), \
             patch('src.Controller.AdwinGoldDevice', return_value=self.mock_adwin), \
             patch('src.Controller.MCLNanoDrive', return_value=self.mock_nanodrive):
            
            devices = create_mock_devices()
            
            assert 'microwave' in devices
            assert 'adwin' in devices
            assert 'nanodrive' in devices
            assert devices['microwave']['instance'] == self.mock_microwave
            assert devices['adwin']['instance'] == self.mock_adwin
            assert devices['nanodrive']['instance'] == self.mock_nanodrive
    
    def test_create_devices_mock_mode(self):
        """Test device creation in mock mode."""
        with patch('examples.odmr_scan_example.create_mock_devices') as mock_create:
            mock_create.return_value = {
                'microwave': {'instance': self.mock_microwave},
                'adwin': {'instance': self.mock_adwin},
                'nanodrive': {'instance': self.mock_nanodrive}
            }
            
            devices = create_devices(use_real_hardware=False)
            
            mock_create.assert_called_once()
            assert devices == mock_create.return_value
    
    def test_create_devices_real_hardware_success(self):
        """Test device creation with real hardware when available."""
        # Patch the imports from src.Controller where they're actually imported
        with patch('src.Controller.SG384Generator', return_value=self.mock_microwave), \
             patch('src.Controller.AdwinGoldDevice', return_value=self.mock_adwin), \
             patch('src.Controller.MCLNanoDrive', return_value=self.mock_nanodrive):
            
            devices = create_devices(use_real_hardware=True)
            
            assert 'microwave' in devices
            assert 'adwin' in devices
            assert 'nanodrive' in devices
    
    def test_create_devices_real_hardware_failure(self):
        """Test device creation with real hardware when not available."""
        # Patch the imports from src.Controller where they're actually imported
        with patch('src.Controller.SG384Generator', side_effect=ImportError("No hardware")), \
             patch('examples.odmr_scan_example.create_mock_devices') as mock_create:
            
            mock_create.return_value = {
                'microwave': {'instance': self.mock_microwave},
                'adwin': {'instance': self.mock_adwin},
                'nanodrive': {'instance': self.mock_nanodrive}
            }
            
            devices = create_devices(use_real_hardware=True)
            
            mock_create.assert_called_once()
            assert devices == mock_create.return_value
    
    def test_run_odmr_scan_mock_success(self):
        """Test successful ODMR scan with mock devices."""
        # Mock the experiment class
        mock_experiment = MagicMock()
        mock_experiment.data = {
            'odmr_spectrum': np.random.random(20),
            'frequencies': np.linspace(2.85e9, 2.89e9, 20)
        }
        mock_experiment.settings = {
            'frequency_range': {'start': 2.85e9, 'stop': 2.89e9, 'steps': 20}
        }
        
        with patch('examples.odmr_scan_example.ODMRExperiment', return_value=mock_experiment), \
             patch('examples.odmr_scan_example.create_devices') as mock_create_devices:
            
            mock_create_devices.return_value = {
                'microwave': {'instance': self.mock_microwave},
                'adwin': {'instance': self.mock_adwin},
                'nanodrive': {'instance': self.mock_nanodrive}
            }
            
            results = run_odmr_scan(use_real_hardware=False, save_data=False)
            
            assert results is not None
            assert results['hardware_type'] == 'mock'
            assert results['scan_mode'] == 'single'
            assert 'data' in results
            assert 'settings' in results
            assert 'scan_time' in results
    
    def test_run_odmr_scan_import_failure(self):
        """Test ODMR scan when experiment class cannot be imported."""
        # Mock the experiment import to fail at the module level
        with patch('src.Model.experiments.odmr_experiment.ODMRExperiment', side_effect=ImportError("No module")), \
             patch('examples.odmr_scan_example.create_devices') as mock_create_devices:
            
            mock_create_devices.return_value = {
                'microwave': {'instance': self.mock_microwave},
                'adwin': {'instance': self.mock_adwin},
                'nanodrive': {'instance': self.mock_nanodrive}
            }
            
            results = run_odmr_scan(use_real_hardware=False, save_data=False)
            
            # The function should return None when import fails
            assert results is None
    
    def test_run_odmr_scan_experiment_failure(self):
        """Test ODMR scan when experiment setup fails."""
        # Mock the experiment class to raise an exception during setup
        mock_experiment = MagicMock()
        mock_experiment.setup.side_effect = ValueError("Setup failed")
        
        with patch('src.Model.experiments.odmr_experiment.ODMRExperiment', return_value=mock_experiment), \
             patch('examples.odmr_scan_example.create_devices') as mock_create_devices:
            
            mock_create_devices.return_value = {
                'microwave': {'instance': self.mock_microwave},
                'adwin': {'instance': self.mock_adwin},
                'nanodrive': {'instance': self.mock_nanodrive}
            }
            
            results = run_odmr_scan(use_real_hardware=False, save_data=False)
            
            # The function should return None when experiment fails
            assert results is None
    
    def test_run_odmr_scan_different_modes(self):
        """Test ODMR scan with different scan modes."""
        mock_experiment = MagicMock()
        mock_experiment.data = {
            'odmr_spectrum': np.random.random(20),
            'frequencies': np.linspace(2.85e9, 2.89e9, 20)
        }
        mock_experiment.settings = {
            'frequency_range': {'start': 2.85e9, 'stop': 2.89e9, 'steps': 20}
        }
        
        with patch('src.Model.experiments.odmr_experiment.ODMRExperiment', return_value=mock_experiment), \
             patch('examples.odmr_scan_example.create_devices') as mock_create_devices:
            
            mock_create_devices.return_value = {
                'microwave': {'instance': self.mock_microwave},
                'adwin': {'instance': self.mock_adwin},
                'nanodrive': {'instance': self.mock_nanodrive}
            }
            
            # Test different scan modes
            for mode in ['single', 'continuous', 'averaged', '2d_scan']:
                results = run_odmr_scan(use_real_hardware=False, save_data=False, scan_mode=mode)
                assert results is not None
                assert results['scan_mode'] == mode
    
    def test_save_scan_data(self):
        """Test scan data saving functionality."""
        mock_experiment = MagicMock()
        mock_experiment.data = {
            'odmr_spectrum': np.random.random(20),
            'frequencies': np.linspace(2.85e9, 2.89e9, 20)
        }
        mock_experiment.settings = {
            'frequency_range': {'start': 2.85e9, 'stop': 2.89e9, 'steps': 20}
        }
        
        with patch('src.Model.experiments.odmr_experiment.ODMRExperiment', return_value=mock_experiment), \
             patch('examples.odmr_scan_example.create_devices') as mock_create_devices, \
             patch('examples.odmr_scan_example.np.savez_compressed') as mock_save:
            
            mock_create_devices.return_value = {
                'microwave': {'instance': self.mock_microwave},
                'adwin': {'instance': self.mock_adwin},
                'nanodrive': {'instance': self.mock_nanodrive}
            }
            
            results = run_odmr_scan(use_real_hardware=False, save_data=True)
            
            assert results is not None
            mock_save.assert_called_once()


class TestODMRScanExampleIntegration:
    """Integration tests for ODMR scan example."""
    
    def setup_method(self):
        """Set up integration test fixtures."""
        # Create mock devices
        self.mock_microwave = MagicMock()
        self.mock_adwin = MagicMock()
        self.mock_nanodrive = MagicMock()
        
        # Configure mock devices
        self.mock_microwave.settings = {
            'frequency': 2.87e9,
            'power': -10.0,
            'phase': 0.0,
            'amplitude': -10.0,
            'enable_output': False,
            'enable_modulation': False
        }
        
        self.mock_adwin.settings = {
            'process_1': {'running': False},
            'process_2': {'running': False},
            'array_size': 1000
        }
        
        self.mock_nanodrive.settings = {
            'serial': 2849,
            'step_size': 1.0,
            'max_velocity': 1000.0
        }
    
    def test_full_example_workflow(self):
        """Test the complete ODMR scan example workflow."""
        # Mock the experiment class
        mock_experiment = MagicMock()
        mock_experiment.data = {
            'odmr_spectrum': np.random.random(20),
            'frequencies': np.linspace(2.85e9, 2.89e9, 20),
            'resonance_frequencies': [2.87e9]
        }
        mock_experiment.settings = {
            'frequency_range': {'start': 2.85e9, 'stop': 2.89e9, 'steps': 20}
        }
        
        with patch('src.Model.experiments.odmr_experiment.ODMRExperiment', return_value=mock_experiment), \
             patch('examples.odmr_scan_example.create_devices') as mock_create_devices, \
             patch('examples.odmr_scan_example.plot_results') as mock_plot:
            
            mock_create_devices.return_value = {
                'microwave': {'instance': self.mock_microwave},
                'adwin': {'instance': self.mock_adwin},
                'nanodrive': {'instance': self.mock_nanodrive}
            }
            
            # Test the full workflow
            results = run_odmr_scan(use_real_hardware=False, save_data=True, scan_mode='single')
            
            # Verify results
            assert results is not None
            assert results['hardware_type'] == 'mock'
            assert results['scan_mode'] == 'single'
            assert 'data' in results
            assert 'settings' in results
            assert 'scan_time' in results
            
            # Verify experiment was called correctly
            mock_experiment.setup.assert_called_once()
            mock_experiment._function.assert_called_once()
    
    def test_example_with_real_hardware_simulation(self):
        """Test the example with simulated real hardware."""
        # Mock the experiment class
        mock_experiment = MagicMock()
        mock_experiment.data = {
            'odmr_spectrum': np.random.random(20),
            'frequencies': np.linspace(2.85e9, 2.89e9, 20)
        }
        mock_experiment.settings = {
            'frequency_range': {'start': 2.85e9, 'stop': 2.89e9, 'steps': 20}
        }
        
        with patch('src.Model.experiments.odmr_experiment.ODMRExperiment', return_value=mock_experiment), \
             patch('examples.odmr_scan_example.create_devices') as mock_create_devices:
            
            mock_create_devices.return_value = {
                'microwave': {'instance': self.mock_microwave},
                'adwin': {'instance': self.mock_adwin},
                'nanodrive': {'instance': self.mock_nanodrive}
            }
            
            # Test with real hardware flag
            results = run_odmr_scan(use_real_hardware=True, save_data=False)
            
            assert results is not None
            assert results['hardware_type'] == 'real'  # Should be 'real' even with mock devices
            assert 'data' in results
            assert 'settings' in results
            assert 'scan_time' in results 