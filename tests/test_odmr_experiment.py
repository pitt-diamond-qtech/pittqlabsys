"""
Tests for ODMR Experiment Module

This module contains comprehensive tests for the ODMR experiment classes.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch
import pyqtgraph as pg

from src.Model.experiments.odmr_experiment import ODMRExperiment, ODMRRabiExperiment


class TestODMRExperiment:
    """Test cases for ODMRExperiment class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create mock devices
        self.mock_microwave = Mock()
        self.mock_adwin = Mock()
        self.mock_nanodrive = Mock()
        
        # Configure mock devices
        self.mock_microwave.settings = {
            'frequency': 2.87e9,
            'amplitude': -10.0,
            'enable_output': False
        }
        
        self.devices = {
            'microwave': {'instance': self.mock_microwave},
            'adwin': {'instance': self.mock_adwin},
            'nanodrive': {'instance': self.mock_nanodrive}
        }
        
        # Create experiment instance
        self.experiment = ODMRExperiment(self.devices)
    
    def test_initialization(self):
        """Test experiment initialization."""
        assert self.experiment.name == "ODMRExperiment"
        assert self.experiment.settings['frequency_range']['start'] == 2.7e9
        assert self.experiment.settings['frequency_range']['stop'] == 3.0e9
        assert self.experiment.settings['microwave']['power'] == -10.0
    
    def test_setup(self):
        """Test experiment setup."""
        self.experiment.setup()
        
        # Check that frequency array was generated
        assert self.experiment.frequencies is not None
        assert len(self.experiment.frequencies) == 100  # Default steps
        
        # Check that data array was initialized
        assert self.experiment.fluorescence_data is not None
        assert len(self.experiment.fluorescence_data) == 100
        
        # Check that microwave was configured
        self.mock_microwave.update.assert_called()
    
    def test_setup_2d_scan(self):
        """Test setup for 2D scan mode."""
        self.experiment.settings['scan_mode'] = '2d_scan'
        self.experiment.setup()
        
        # Check that 3D data array was initialized
        assert self.experiment.fluorescence_data.shape == (10, 10, 100)  # Default 2D settings
    
    def test_cleanup(self):
        """Test experiment cleanup."""
        self.experiment.cleanup()
        
        # Check that microwave was turned off
        self.mock_microwave.update.assert_called_with({'enable_output': False})
        
        # Check that ADwin was stopped
        self.mock_adwin.stop_process.assert_called_with(2)
    
    def test_single_sweep(self):
        """Test single ODMR sweep."""
        self.experiment.setup()
        
        # Mock the _acquire_counts method to return simulated data
        with patch.object(self.experiment, '_acquire_counts', return_value=100.0):
            self.experiment._run_single_sweep()
        
        # Check that microwave was enabled and disabled
        enable_calls = [call for call in self.mock_microwave.update.call_args_list 
                       if call[0] == {'enable_output': True}]
        disable_calls = [call for call in self.mock_microwave.update.call_args_list 
                        if call[0] == {'enable_output': False}]
        
        assert len(enable_calls) == 1
        assert len(disable_calls) == 1
        
        # Check that data was collected
        assert np.any(self.experiment.fluorescence_data > 0)
    
    def test_acquire_counts(self):
        """Test photon count acquisition."""
        self.experiment.setup()
        
        # Test count acquisition
        counts = self.experiment._acquire_counts()
        
        # Should return a positive number
        assert counts > 0
        assert isinstance(counts, (int, float))
    
    def test_data_analysis(self):
        """Test data analysis methods."""
        self.experiment.setup()
        
        # Generate some test data
        self.experiment.fluorescence_data = np.random.random(100) * 1000
        
        # Test smoothing
        self.experiment._smooth_data()
        assert self.experiment.fluorescence_data is not None
        
        # Test background subtraction
        self.experiment._subtract_background()
        assert self.experiment.background_level is not None
        
        # Test resonance fitting
        self.experiment._fit_resonances()
        assert self.experiment.fit_parameters is not None
    
    def test_fit_single_spectrum(self):
        """Test fitting of single ODMR spectrum."""
        self.experiment.setup()
        
        # Create a simulated ODMR spectrum with a dip
        frequencies = self.experiment.frequencies
        center_freq = 2.87e9
        width = 1e6
        amplitude = 1000
        
        # Create Lorentzian dip
        spectrum = amplitude * (1 - 0.3 * width**2 / ((frequencies - center_freq)**2 + width**2))
        spectrum += np.random.normal(0, 50, len(spectrum))
        
        # Fit the spectrum
        params = self.experiment._fit_single_spectrum(spectrum)
        
        # Check that fitting returned parameters
        assert len(params) == 4  # amplitude, center, width, offset
        assert all(np.isfinite(params))
    
    def test_plotting(self):
        """Test plotting functionality."""
        self.experiment.setup()
        
        # Generate test data
        self.experiment.fluorescence_data = np.random.random(100) * 1000
        
        # Create mock axes
        mock_axes = [Mock(spec=pg.PlotItem) for _ in range(2)]
        
        # Test plotting
        self.experiment._plot(mock_axes)
        
        # Check that plot methods were called
        for ax in mock_axes:
            ax.clear.assert_called()
    
    def test_plot_2d_data(self):
        """Test 2D data plotting."""
        self.experiment.settings['scan_mode'] = '2d_scan'
        self.experiment.setup()
        
        # Generate test 2D data
        self.experiment.fluorescence_data = np.random.random((10, 10, 100)) * 1000
        
        # Create mock axes
        mock_axes = [Mock(spec=pg.PlotItem)]
        
        # Test 2D plotting
        self.experiment._plot_2d_data(mock_axes)
        
        # Check that plot methods were called
        mock_axes[0].clear.assert_called()
    
    def test_get_experiment_info(self):
        """Test experiment information retrieval."""
        info = self.experiment.get_experiment_info()
        
        assert 'experiment_type' in info
        assert info['experiment_type'] == 'ODMR'
        assert 'scan_mode' in info
        assert 'frequency_range' in info
        assert 'microwave_power' in info
    
    def test_magnetic_field_calculation(self):
        """Test magnetic field effects on resonance frequencies."""
        self.experiment.setup()
        
        # Test zero field
        self.experiment.settings['magnetic_field']['enabled'] = False
        counts_zero = self.experiment._acquire_counts()
        
        # Test with magnetic field
        self.experiment.settings['magnetic_field']['enabled'] = True
        self.experiment.settings['magnetic_field']['strength'] = 100.0  # 100 Gauss
        counts_field = self.experiment._acquire_counts()
        
        # Should be different due to magnetic field splitting
        assert counts_zero != counts_field


class TestODMRRabiExperiment:
    """Test cases for ODMRRabiExperiment class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create mock devices
        self.mock_microwave = Mock()
        self.mock_adwin = Mock()
        
        self.devices = {
            'microwave': {'instance': self.mock_microwave},
            'adwin': {'instance': self.mock_adwin}
        }
        
        # Create experiment instance
        self.experiment = ODMRRabiExperiment(self.devices)
    
    def test_initialization(self):
        """Test experiment initialization."""
        assert self.experiment.name == "ODMRRabiExperiment"
        assert self.experiment.settings['rabi_settings']['frequency'] == 2.87e9
        assert self.experiment.settings['rabi_settings']['power'] == -10.0
    
    def test_function(self):
        """Test main experiment execution."""
        # Mock the _run_rabi_sequence method
        with patch.object(self.experiment, '_run_rabi_sequence', return_value=100.0):
            self.experiment._function()
        
        # Check that data was collected
        assert self.experiment.rabi_data is not None
        assert len(self.experiment.rabi_data) == 50  # Default pulse steps
        
        # Check that microwave was configured
        self.mock_microwave.update.assert_called()
    
    def test_run_rabi_sequence(self):
        """Test Rabi sequence execution."""
        pulse_duration = 1e-6  # 1 μs
        counts = self.experiment._run_rabi_sequence(pulse_duration)
        
        # Should return a positive number
        assert counts > 0
        assert isinstance(counts, (int, float))
    
    def test_fit_rabi_oscillations(self):
        """Test Rabi oscillation fitting."""
        # Generate test Rabi data
        self.experiment.pulse_durations = np.linspace(0, 1e-6, 50)
        rabi_freq = 1e6  # 1 MHz
        amplitude = 500
        offset = 1000
        
        # Create simulated Rabi oscillations
        self.experiment.rabi_data = amplitude * np.cos(2 * np.pi * rabi_freq * self.experiment.pulse_durations) + offset
        self.experiment.rabi_data += np.random.normal(0, 50, len(self.experiment.rabi_data))
        
        # Fit the oscillations
        self.experiment._fit_rabi_oscillations()
        
        # Check that fitting was successful
        assert self.experiment.rabi_frequency is not None
        assert self.experiment.pi_pulse_duration is not None
        
        # Check that fitted frequency is reasonable
        assert 0.5e6 < self.experiment.rabi_frequency < 2e6  # Should be close to 1 MHz
    
    def test_plotting(self):
        """Test Rabi plotting functionality."""
        # Generate test data
        self.experiment.pulse_durations = np.linspace(0, 1e-6, 50)
        self.experiment.rabi_data = np.random.random(50) * 1000
        
        # Create mock axes
        mock_axes = [Mock(spec=pg.PlotItem)]
        
        # Test plotting
        self.experiment._plot(mock_axes)
        
        # Check that plot methods were called
        mock_axes[0].clear.assert_called()
    
    def test_rabi_fit(self):
        """Test Rabi fit calculation."""
        # Set up test parameters
        self.experiment.rabi_frequency = 1e6
        t = np.linspace(0, 1e-6, 100)
        
        # Calculate fit
        fit_data = self.experiment._rabi_fit(t)
        
        # Check that fit data is reasonable
        assert len(fit_data) == len(t)
        assert all(np.isfinite(fit_data))


class TestODMRIntegration:
    """Integration tests for ODMR experiments."""
    
    def test_full_odmr_experiment(self):
        """Test complete ODMR experiment workflow."""
        # Create mock devices
        mock_microwave = Mock()
        mock_adwin = Mock()
        mock_nanodrive = Mock()
        
        devices = {
            'microwave': {'instance': mock_microwave},
            'adwin': {'instance': mock_adwin},
            'nanodrive': {'instance': mock_nanodrive}
        }
        
        # Create experiment
        experiment = ODMRExperiment(devices)
        
        # Mock data acquisition
        with patch.object(experiment, '_acquire_counts', return_value=100.0):
            # Run experiment
            experiment._function()
        
        # Check that experiment completed successfully
        assert experiment.fluorescence_data is not None
        assert len(experiment.fluorescence_data) > 0
        
        # Check that devices were used correctly
        assert mock_microwave.update.called
        assert mock_adwin.update.called
    
    def test_experiment_stopping(self):
        """Test that experiments can be stopped gracefully."""
        # Create mock devices
        mock_microwave = Mock()
        mock_adwin = Mock()
        mock_nanodrive = Mock()
        
        devices = {
            'microwave': {'instance': mock_microwave},
            'adwin': {'instance': mock_adwin},
            'nanodrive': {'instance': mock_nanodrive}
        }
        
        # Create experiment
        experiment = ODMRExperiment(devices)
        experiment.setup()
        
        # Mock stop signal
        with patch.object(experiment, 'is_stopped', return_value=True):
            experiment._run_single_sweep()
        
        # Check that experiment stopped gracefully
        assert mock_microwave.update.called  # Should have been configured
        # Should not have collected much data due to early stop
        assert np.sum(experiment.fluorescence_data) == 0


if __name__ == "__main__":
    pytest.main([__file__]) 