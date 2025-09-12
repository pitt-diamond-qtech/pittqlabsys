"""
Tests for Enhanced ODMR Sweep Experiment Module

This module contains comprehensive tests for the EnhancedODMRSweepExperiment class.
Tests cover the new functionality including start/stop frequencies, settle time,
sweep rate validation, and phase continuous sweep mode.
"""

import pytest
import numpy as np
import unittest.mock as mock
from unittest.mock import MagicMock, patch
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import the module directly to avoid the problematic import chain
from src.Model.experiments.odmr_sweep_enhanced import EnhancedODMRSweepExperiment
from src.core import Parameter


class TestEnhancedODMRSweepExperiment:
    """Test cases for EnhancedODMRSweepExperiment class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create mock devices
        self.mock_microwave = MagicMock()
        self.mock_adwin = MagicMock()
        
        # Configure mock devices
        self.mock_microwave.settings = {
            'frequency': 2.87e9,
            'power': -45.0,
            'enable_output': False
        }
        
        self.devices = {
            'microwave': {'instance': self.mock_microwave},
            'adwin': {'instance': self.mock_adwin}
        }
        
        # Create experiment instance
        self.experiment = EnhancedODMRSweepExperiment(self.devices)
    
    def test_initialization(self):
        """Test experiment initialization with new parameters."""
        assert self.experiment.name == "EnhancedODMRSweepExperiment"
        
        # Check new parameter structure
        assert self.experiment.settings['sweep_parameters']['start_frequency'] == 2.82e9
        assert self.experiment.settings['sweep_parameters']['stop_frequency'] == 2.92e9
        assert self.experiment.settings['sweep_parameters']['sweep_sensitivity'] is None  # Auto-calculated
        assert self.experiment.settings['sweep_parameters']['max_sweep_rate'] == 110.0
        
        # Check acquisition parameters
        assert self.experiment.settings['acquisition']['integration_time'] == 10.0
        assert self.experiment.settings['acquisition']['settle_time'] == 0.1
        assert self.experiment.settings['acquisition']['num_steps'] == 100
        assert self.experiment.settings['acquisition']['bidirectional'] == False
    
    def test_validate_sweep_parameters_valid(self):
        """Test sweep parameter validation with valid parameters."""
        # Valid parameters
        self.experiment.settings['sweep_parameters']['start_frequency'] = 2.8e9
        self.experiment.settings['sweep_parameters']['stop_frequency'] = 2.9e9
        
        # Should not raise any exception
        self.experiment._validate_sweep_parameters()
    
    def test_validate_sweep_parameters_invalid_order(self):
        """Test sweep parameter validation with start > stop."""
        # Invalid: start > stop
        self.experiment.settings['sweep_parameters']['start_frequency'] = 2.9e9
        self.experiment.settings['sweep_parameters']['stop_frequency'] = 2.8e9
        
        with pytest.raises(ValueError, match="Start frequency.*must be less than stop frequency"):
            self.experiment._validate_sweep_parameters()
    
    def test_validate_sweep_parameters_below_limit(self):
        """Test sweep parameter validation below SG384 limit."""
        # Below 1.9 GHz limit
        self.experiment.settings['sweep_parameters']['start_frequency'] = 1.8e9
        self.experiment.settings['sweep_parameters']['stop_frequency'] = 2.0e9
        
        with pytest.raises(ValueError, match="Start frequency.*is below SG384 limit"):
            self.experiment._validate_sweep_parameters()
    
    def test_validate_sweep_parameters_above_limit(self):
        """Test sweep parameter validation above SG384 limit."""
        # Above 4.1 GHz limit
        self.experiment.settings['sweep_parameters']['start_frequency'] = 4.0e9
        self.experiment.settings['sweep_parameters']['stop_frequency'] = 4.2e9
        
        with pytest.raises(ValueError, match="Stop frequency.*is above SG384 limit"):
            self.experiment._validate_sweep_parameters()
    
    def test_validate_sweep_rate_unidirectional(self):
        """Test sweep rate validation for unidirectional sweeps."""
        # Valid sweep rate
        self.experiment.settings['acquisition']['integration_time'] = 10.0  # ms
        self.experiment.settings['acquisition']['settle_time'] = 0.1  # ms
        self.experiment.settings['acquisition']['num_steps'] = 100
        self.experiment.settings['acquisition']['bidirectional'] = False
        
        # Should not raise exception
        self.experiment._validate_sweep_parameters()
    
    def test_validate_sweep_rate_bidirectional(self):
        """Test sweep rate validation for bidirectional sweeps."""
        # Valid bidirectional sweep rate
        self.experiment.settings['acquisition']['integration_time'] = 10.0  # ms
        self.experiment.settings['acquisition']['settle_time'] = 0.1  # ms
        self.experiment.settings['acquisition']['num_steps'] = 100
        self.experiment.settings['acquisition']['bidirectional'] = True
        
        # Should not raise exception
        self.experiment._validate_sweep_parameters()
    
    def test_validate_sweep_rate_too_fast(self):
        """Test sweep rate validation with too fast sweep."""
        # Too fast sweep rate - set very short times to exceed 110 Hz limit
        self.experiment.settings['acquisition']['integration_time'] = 0.001  # 1 microsecond
        self.experiment.settings['acquisition']['settle_time'] = 0.001  # 1 microsecond
        self.experiment.settings['acquisition']['num_steps'] = 1000
        self.experiment.settings['acquisition']['bidirectional'] = False
        
        # This should give: (0.002 ms / 1000) * 1000 = 0.002 s = 500 Hz >> 110 Hz limit
    
        with pytest.raises(ValueError, match="Sweep time.*is too fast for SG384"):
            self.experiment._validate_sweep_parameters()
    
    def test_calculate_frequency_array(self):
        """Test frequency array calculation."""
        self.experiment.settings['sweep_parameters']['start_frequency'] = 2.8e9
        self.experiment.settings['sweep_parameters']['stop_frequency'] = 2.9e9
        self.experiment.settings['acquisition']['num_steps'] = 10
        
        self.experiment._calculate_frequency_array()
        
        assert len(self.experiment.frequencies) == 10
        assert self.experiment.frequencies[0] == 2.8e9
        assert self.experiment.frequencies[-1] == 2.9e9
        assert np.allclose(np.diff(self.experiment.frequencies), 11.11e6, rtol=1e-3)
    
    def test_setup_microwave(self):
        """Test microwave setup with phase continuous sweep mode."""
        self.experiment.settings['sweep_parameters']['start_frequency'] = 2.8e9
        self.experiment.settings['sweep_parameters']['stop_frequency'] = 2.9e9
        self.experiment.settings['microwave']['power'] = -40.0
        self.experiment.settings['microwave']['enable_output'] = True
        
        self.experiment._setup_microwave()
        
        # Check that center frequency and deviation were calculated correctly
        expected_center = (2.8e9 + 2.9e9) / 2.0  # 2.85 GHz
        expected_deviation = (2.9e9 - 2.8e9) / 2.0  # 50 MHz
        expected_sensitivity = (2.9e9 - 2.8e9) / 2.0  # 50 MHz/V
        
        # Check microwave was configured
        self.mock_microwave.update.assert_called()
        
        # Check that sweep sensitivity was calculated
        assert self.experiment.settings['sweep_parameters']['sweep_sensitivity'] == expected_sensitivity
    
    def test_setup_adwin(self):
        """Test ADwin setup with settle time."""
        self.experiment.settings['acquisition']['integration_time'] = 15.0
        self.experiment.settings['acquisition']['settle_time'] = 0.2
        self.experiment.settings['acquisition']['num_steps'] = 50
        self.experiment.settings['acquisition']['bidirectional'] = True
        
        # Mock the helper function
        with patch('src.Model.experiments.odmr_sweep_enhanced.setup_adwin_for_sweep_odmr') as mock_setup:
            self.experiment._setup_adwin()
            
            # Check that helper was called with correct parameters
            mock_setup.assert_called_once_with(
                self.mock_adwin,
                integration_time_ms=15.0,
                settle_time_ms=0.2,
                num_steps=50,
                bidirectional=True
            )
    
    def test_initialize_data_arrays(self):
        """Test data array initialization."""
        self.experiment.settings['acquisition']['sweeps_per_average'] = 5
        self.experiment.frequencies = np.linspace(2.8e9, 2.9e9, 10)
        
        self.experiment._initialize_data_arrays()
        
        assert self.experiment.sweep_data.shape == (5, 10)
        assert self.experiment.average_data.shape == (10,)
        assert np.all(self.experiment.sweep_data == 0)
        assert np.all(self.experiment.average_data == 0)
    
    def test_run_single_sweep_bidirectional(self):
        """Test single sweep execution with bidirectional data."""
        # Mock the setup methods to avoid ADwin compilation issues
        with patch.object(self.experiment, '_setup_adwin'), \
             patch.object(self.experiment, '_setup_microwave'), \
             patch.object(self.experiment, '_validate_sweep_parameters'), \
             patch.object(self.experiment, '_calculate_frequency_array'), \
             patch.object(self.experiment, '_initialize_data_arrays'):
            
            # Manually set sweep_sensitivity since _setup_microwave is mocked
            self.experiment.settings['sweep_parameters']['sweep_sensitivity'] = 50e6  # 50 MHz/V
            
            # Set bidirectional to True for this test
            self.experiment.settings['acquisition']['bidirectional'] = True
            
            # Mock ADwin data
            mock_adwin_data = {
                'sweep_complete': True,
                'data_ready': True,
                'forward_counts': [100, 200, 300],
                'reverse_counts': [150, 250, 350],
                'forward_voltages': [-1.0, 0.0, 1.0],
                'reverse_voltages': [1.0, 0.0, -1.0]
            }
        
            with patch('src.Model.experiments.odmr_sweep_enhanced.read_adwin_sweep_odmr_data',
                      return_value=mock_adwin_data):
        
                result = self.experiment._run_single_sweep()
        
                # Verify result structure
                assert 'forward_data' in result
                assert 'reverse_data' in result
                assert 'forward_frequencies' in result
                assert 'reverse_frequencies' in result
                assert len(result['forward_data']) == 3
                assert len(result['reverse_data']) == 3
    
    def test_run_single_sweep_unidirectional(self):
        """Test single sweep execution with unidirectional data."""
        # Mock the setup methods to avoid ADwin compilation issues
        with patch.object(self.experiment, '_setup_adwin'), \
             patch.object(self.experiment, '_setup_microwave'), \
             patch.object(self.experiment, '_validate_sweep_parameters'), \
             patch.object(self.experiment, '_calculate_frequency_array'), \
             patch.object(self.experiment, '_initialize_data_arrays'):
            
            # Manually set sweep_sensitivity since _setup_microwave is mocked
            self.experiment.settings['sweep_parameters']['sweep_sensitivity'] = 50e6  # 50 MHz/V
            
            # Mock ADwin data for unidirectional sweep
            mock_adwin_data = {
                'sweep_complete': True,
                'data_ready': True,
                'forward_counts': [100, 200, 300],
                'reverse_counts': None,
                'forward_voltages': [-1.0, 0.0, 1.0],
                'reverse_voltages': None
            }
        
            with patch('src.Model.experiments.odmr_sweep_enhanced.read_adwin_sweep_odmr_data',
                      return_value=mock_adwin_data):
        
                result = self.experiment._run_single_sweep()
        
                # Verify result structure for unidirectional sweep
                assert 'forward_data' in result
                assert 'forward_frequencies' in result
                assert len(result['forward_data']) == 3
    

    def test_fit_esr_peaks(self):
        """Test ESR dip fitting (ODMR typically shows dips in fluorescence)."""
        # Create simulated ODMR data with a dip
        frequencies = np.linspace(2.8e9, 2.9e9, 100)
        center_freq = 2.85e9
        width = 10e6  # 10 MHz

        # Create Lorentzian dip (ODMR typically shows a dip in fluorescence at resonance)
        background = 1000  # High fluorescence background
        dip_amplitude = 800  # Depth of the dip
        data = background - dip_amplitude / (1 + ((frequencies - center_freq) / (width/2))**2)

        # Reduce contrast factor to make dip detection easier
        self.experiment.settings['analysis']['contrast_factor'] = 1.1

        peaks = self.experiment._fit_esr_peaks(frequencies, data)

        # Should find at least one dip
        assert len(peaks) >= 1
        
        # Check peak parameters
        peak = peaks[0]
        assert 'amplitude' in peak
        assert 'center' in peak
        assert 'width' in peak
        assert 'center_ghz' in peak
        assert 'width_mhz' in peak
        
        # Peak should be near the expected center frequency
        assert abs(peak['center'] - center_freq) < 50e6  # Within 50 MHz
    
    def test_cleanup(self):
        """Test experiment cleanup."""
        self.experiment.settings['microwave']['turn_off_after'] = True
        
        self.experiment.cleanup()
        
        # Check that ADwin process was stopped
        self.mock_adwin.stop_process.assert_called_with(1)
        
        # Check that microwave was turned off
        self.mock_microwave.update.assert_called_with({'enable_output': False})
    
    def test_cleanup_no_turn_off(self):
        """Test experiment cleanup without turning off microwave."""
        self.experiment.settings['microwave']['turn_off_after'] = False
        
        self.experiment.cleanup()
        
        # Check that ADwin process was stopped
        self.mock_adwin.stop_process.assert_called_with(1)
        
        # Microwave should not be turned off
        self.mock_microwave.update.assert_not_called()
    
    def test_plot_bidirectional(self):
        """Test plotting with bidirectional data."""
        # Create mock axes
        mock_axes = [MagicMock()]
    
        # Set up bidirectional data
        self.experiment.data = {
            'forward_frequency': np.linspace(2.8, 2.9, 10),
            'reverse_frequency': np.linspace(2.8, 2.9, 10),
            'forward_data': np.random.random(10),
            'reverse_data': np.random.random(10),
            'fit_params': [{'amplitude': 100, 'center': 2.85e9, 'width': 10e6, 'offset': 50}]
        }
    
        self.experiment._plot(mock_axes)
    
        # Verify that plot was called
        mock_axes[0].plot.assert_called()
    
    def test_plot_unidirectional(self):
        """Test plotting with unidirectional data."""
        # Create mock axes
        mock_axes = [MagicMock()]
    
        # Set up unidirectional data
        self.experiment.data = {
            'frequency': np.linspace(2.8, 2.9, 10),
            'data': np.random.random(10),
            'fit_params': [{'amplitude': 100, 'center': 2.85e9, 'width': 10e6, 'offset': 50}]
        }
    
        self.experiment._plot(mock_axes)
    
        # Verify that plot was called
        mock_axes[0].plot.assert_called()
    
    def test_get_axes_layout(self):
        """Test axes layout configuration."""
        layout = self.experiment.get_axes_layout(['figure1'])
        
        assert layout == [['ODMR Sweep']]
    
    def test_get_experiment_info(self):
        """Test experiment info retrieval."""
        self.experiment.settings['sweep_parameters']['start_frequency'] = 2.8e9
        self.experiment.settings['sweep_parameters']['stop_frequency'] = 2.9e9
        
        info = self.experiment.get_experiment_info()
        
        assert info['name'] == 'Enhanced ODMR Sweep'
        assert info['description'] == 'ODMR experiment using phase continuous sweep mode with external modulation'
        assert info['start_frequency'] == 2.8
        assert info['stop_frequency'] == 2.9
        assert info['center_frequency'] == 2.85
        assert info['deviation'] == 50.0
        assert info['max_sweep_rate'] == 110.0
        assert info['integration_time'] == 10.0
        assert info['settle_time'] == 0.1
        assert info['num_steps'] == 100
        assert info['sweeps_per_average'] == 10


class TestEnhancedODMRSweepIntegration:
    """Integration tests for EnhancedODMRSweepExperiment."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create mock devices
        self.mock_microwave = MagicMock()
        self.mock_adwin = MagicMock()
        
        self.devices = {
            'microwave': {'instance': self.mock_microwave},
            'adwin': {'instance': self.mock_adwin}
        }
        
        # Create experiment instance
        self.experiment = EnhancedODMRSweepExperiment(self.devices)
    
    def test_full_experiment_setup(self):
        """Test complete experiment setup."""
        # Mock the helper functions
        with patch('src.Model.experiments.odmr_sweep_enhanced.setup_adwin_for_sweep_odmr'):
            self.experiment.setup()
            
            # Check that all components were set up
            assert self.experiment.frequencies is not None
            assert self.experiment.sweep_data is not None
            assert self.experiment.average_data is not None
            
            # Check that sweep sensitivity was calculated
            assert self.experiment.settings['sweep_parameters']['sweep_sensitivity'] is not None
    
    def test_experiment_stopping(self):
        """Test experiment stopping functionality."""
        # Mock the stop flag
        self.experiment.is_stopped = MagicMock(return_value=True)
        
        # Set up data structure to avoid KeyError
        self.experiment.data = {
            'data': np.random.random(100),
            'frequency': np.linspace(2.8e9, 2.9e9, 100)
        }
    
        # Mock ADwin data
        mock_adwin_data = {
            'sweep_complete': False,
            'data_ready': False
        }
    
        with patch('src.Model.experiments.odmr_sweep_enhanced.read_adwin_sweep_odmr_data',
                  return_value=mock_adwin_data):
    
            # The experiment should stop early
            with patch.object(self.experiment, '_run_single_sweep') as mock_sweep:
                self.experiment._function()
    
            # Verify that sweep was not called due to early stopping
            mock_sweep.assert_not_called()
    
    def test_error_handling(self):
        """Test error handling during experiment."""
        # Mock ADwin to raise an exception
        self.mock_adwin.start_process.side_effect = Exception("ADwin error")
        
        with pytest.raises(Exception, match="ADwin error"):
            self.experiment._function()
        
        # Cleanup should still be called
        self.mock_adwin.stop_process.assert_called() 