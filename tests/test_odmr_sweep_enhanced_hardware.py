"""
Hardware Tests for Enhanced ODMR Sweep Experiment

This module contains hardware integration tests for the EnhancedODMRSweepExperiment class.
These tests require actual SG384 and ADwin hardware to be connected.

Use pytest markers to control test execution:
- Run without hardware: pytest -m "not hardware"
- Run with hardware: pytest -m hardware
"""

import pytest
import numpy as np
import time
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.Model.experiments.odmr_sweep_enhanced import EnhancedODMRSweepExperiment
from src.Controller import SG384Generator, AdwinGoldDevice


class TestEnhancedODMRSweepHardware:
    """Hardware tests for EnhancedODMRSweepExperiment."""
    
    def setup_method(self):
        """Set up hardware test fixtures."""
        # Check if hardware is available
        self.hardware_available = self._check_hardware_availability()
        
        if self.hardware_available:
            # Initialize hardware devices
            self.microwave = SG384Generator()
            self.adwin = AdwinGoldDevice()
            
            # Configure devices
            self.devices = {
                'microwave': {'instance': self.microwave},
                'adwin': {'instance': self.adwin}
            }
            
            # Create experiment instance
            self.experiment = EnhancedODMRSweepExperiment(self.devices)
    
    def _check_hardware_availability(self):
        """Check if required hardware is available."""
        try:
            # Try to initialize SG384
            microwave = SG384Generator()
            microwave.update({'enable_output': False})  # Ensure output is off
            
            # Try to initialize ADwin
            adwin = AdwinGoldDevice()
            
            return True
        except Exception as e:
            print(f"Hardware not available: {e}")
            return False
    
    @pytest.mark.hardware
    def test_hardware_initialization(self):
        """Test hardware device initialization."""
        if not self.hardware_available:
            pytest.skip("Hardware not available")
        
        # Test SG384 initialization
        assert self.microwave is not None
        assert hasattr(self.microwave, 'update')
        assert hasattr(self.microwave, 'read_probes')
        
        # Test ADwin initialization
        assert self.adwin is not None
        assert hasattr(self.adwin, 'start_process')
        assert hasattr(self.adwin, 'stop_process')
        assert hasattr(self.adwin, 'set_int_var')
    
    @pytest.mark.hardware
    def test_experiment_initialization_with_hardware(self):
        """Test experiment initialization with real hardware."""
        if not self.hardware_available:
            pytest.skip("Hardware not available")
        
        # Test experiment creation
        assert self.experiment is not None
        assert self.experiment.name == "EnhancedODMRSweepExperiment"
        
        # Check that devices are properly connected
        assert self.experiment.microwave is self.microwave
        assert self.experiment.adwin is self.adwin
    
    @pytest.mark.hardware
    def test_sweep_parameter_validation_with_hardware(self):
        """Test sweep parameter validation with hardware constraints."""
        if not self.hardware_available:
            pytest.skip("Hardware not available")
        
        # Test valid parameters
        self.experiment.settings['sweep_parameters']['start_frequency'] = 2.8e9
        self.experiment.settings['sweep_parameters']['stop_frequency'] = 2.9e9
        
        # Should not raise exception
        self.experiment._validate_sweep_parameters()
        
        # Test invalid parameters (should raise exception)
        self.experiment.settings['sweep_parameters']['start_frequency'] = 1.5e9  # Below limit
        
        with pytest.raises(ValueError):
            self.experiment._validate_sweep_parameters()
    
    @pytest.mark.hardware
    def test_microwave_setup_with_hardware(self):
        """Test microwave setup with real hardware."""
        if not self.hardware_available:
            pytest.skip("Hardware not available")
        
        # Configure test parameters
        self.experiment.settings['sweep_parameters']['start_frequency'] = 2.8e9
        self.experiment.settings['sweep_parameters']['stop_frequency'] = 2.9e9
        self.experiment.settings['microwave']['power'] = -50.0  # Low power for safety
        self.experiment.settings['microwave']['enable_output'] = False  # Keep output off
        
        # Setup microwave
        self.experiment._setup_microwave()
        
        # Check that sweep sensitivity was calculated
        assert self.experiment.settings['sweep_parameters']['sweep_sensitivity'] is not None
        expected_sensitivity = (2.9e9 - 2.8e9) / 2.0  # 50 MHz/V
        assert abs(self.experiment.settings['sweep_parameters']['sweep_sensitivity'] - expected_sensitivity) < 1e6
        
        # Verify microwave settings
        microwave_probes = self.microwave.read_probes(['frequency', 'power', 'enable_output'])
        assert microwave_probes['frequency'] == 2.85e9  # Center frequency
        assert microwave_probes['power'] == -50.0
        assert microwave_probes['enable_output'] == False  # Should remain off
    
    @pytest.mark.hardware
    def test_adwin_setup_with_hardware(self):
        """Test ADwin setup with real hardware."""
        if not self.hardware_available:
            pytest.skip("Hardware not available")
        
        # Configure test parameters
        self.experiment.settings['acquisition']['integration_time'] = 10.0
        self.experiment.settings['acquisition']['settle_time'] = 0.1
        self.experiment.settings['acquisition']['num_steps'] = 10  # Small number for testing
        self.experiment.settings['acquisition']['bidirectional'] = False
        
        # Setup ADwin
        self.experiment._setup_adwin()
        
        # Check that ADwin parameters were set
        # Note: We can't directly read back the parameters, but we can check that no exceptions were raised
        assert True  # If we get here, setup was successful
    
    @pytest.mark.hardware
    def test_frequency_calculation_with_hardware(self):
        """Test frequency array calculation with hardware constraints."""
        if not self.hardware_available:
            pytest.skip("Hardware not available")
        
        # Test frequency calculation
        self.experiment.settings['sweep_parameters']['start_frequency'] = 2.8e9
        self.experiment.settings['sweep_parameters']['stop_frequency'] = 2.9e9
        self.experiment.settings['acquisition']['num_steps'] = 10
        
        self.experiment._calculate_frequency_array()
        
        assert len(self.experiment.frequencies) == 10
        assert self.experiment.frequencies[0] == 2.8e9
        assert self.experiment.frequencies[-1] == 2.9e9
        
        # Check that all frequencies are within SG384 range
        for freq in self.experiment.frequencies:
            assert 1.9e9 <= freq <= 4.1e9
    
    @pytest.mark.hardware
    def test_sweep_rate_validation_with_hardware(self):
        """Test sweep rate validation with hardware limits."""
        if not self.hardware_available:
            pytest.skip("Hardware not available")
        
        # Test valid sweep rate
        self.experiment.settings['acquisition']['integration_time'] = 10.0
        self.experiment.settings['acquisition']['settle_time'] = 0.1
        self.experiment.settings['acquisition']['num_steps'] = 100
        self.experiment.settings['acquisition']['bidirectional'] = False
        
        # Should not raise exception
        self.experiment._validate_sweep_parameters()
        
        # Test too fast sweep rate
        self.experiment.settings['acquisition']['integration_time'] = 0.1
        self.experiment.settings['acquisition']['settle_time'] = 0.1
        self.experiment.settings['acquisition']['num_steps'] = 1000
        
        with pytest.raises(ValueError, match="Sweep time.*is too fast"):
            self.experiment._validate_sweep_parameters()
    
    @pytest.mark.hardware
    def test_bidirectional_sweep_rate_validation(self):
        """Test sweep rate validation for bidirectional sweeps."""
        if not self.hardware_available:
            pytest.skip("Hardware not available")
        
        # Test valid bidirectional sweep rate
        self.experiment.settings['acquisition']['integration_time'] = 10.0
        self.experiment.settings['acquisition']['settle_time'] = 0.1
        self.experiment.settings['acquisition']['num_steps'] = 100
        self.experiment.settings['acquisition']['bidirectional'] = True
        
        # Should not raise exception
        self.experiment._validate_sweep_parameters()
        
        # Test too fast bidirectional sweep rate
        self.experiment.settings['acquisition']['integration_time'] = 0.1
        self.experiment.settings['acquisition']['settle_time'] = 0.1
        self.experiment.settings['acquisition']['num_steps'] = 1000
        self.experiment.settings['acquisition']['bidirectional'] = True
        
        with pytest.raises(ValueError, match="Bidirectional sweep time.*is too fast"):
            self.experiment._validate_sweep_parameters()
    
    @pytest.mark.hardware
    def test_experiment_setup_with_hardware(self):
        """Test complete experiment setup with hardware."""
        if not self.hardware_available:
            pytest.skip("Hardware not available")
        
        # Configure safe test parameters
        self.experiment.settings['sweep_parameters']['start_frequency'] = 2.8e9
        self.experiment.settings['sweep_parameters']['stop_frequency'] = 2.9e9
        self.experiment.settings['microwave']['power'] = -50.0
        self.experiment.settings['microwave']['enable_output'] = False
        self.experiment.settings['acquisition']['integration_time'] = 10.0
        self.experiment.settings['acquisition']['settle_time'] = 0.1
        self.experiment.settings['acquisition']['num_steps'] = 10
        self.experiment.settings['acquisition']['bidirectional'] = False
        self.experiment.settings['acquisition']['sweeps_per_average'] = 1
        
        # Setup experiment
        self.experiment.setup()
        
        # Check that all components were set up
        assert self.experiment.frequencies is not None
        assert len(self.experiment.frequencies) == 10
        assert self.experiment.sweep_data is not None
        assert self.experiment.average_data is not None
        assert self.experiment.settings['sweep_parameters']['sweep_sensitivity'] is not None
    
    @pytest.mark.hardware
    def test_experiment_cleanup_with_hardware(self):
        """Test experiment cleanup with hardware."""
        if not self.hardware_available:
            pytest.skip("Hardware not available")
        
        # Configure test parameters
        self.experiment.settings['microwave']['turn_off_after'] = True
        
        # Run cleanup
        self.experiment.cleanup()
        
        # Verify that microwave output is off
        microwave_probes = self.microwave.read_probes(['enable_output'])
        assert microwave_probes['enable_output'] == False
    
    @pytest.mark.hardware
    def test_experiment_info_with_hardware(self):
        """Test experiment info retrieval with hardware."""
        if not self.hardware_available:
            pytest.skip("Hardware not available")
        
        # Configure test parameters
        self.experiment.settings['sweep_parameters']['start_frequency'] = 2.8e9
        self.experiment.settings['sweep_parameters']['stop_frequency'] = 2.9e9
        
        # Get experiment info
        info = self.experiment.get_experiment_info()
        
        # Verify info
        assert info['name'] == 'Enhanced ODMR Sweep'
        assert info['start_frequency'] == 2.8
        assert info['stop_frequency'] == 2.9
        assert info['center_frequency'] == 2.85
        assert info['deviation'] == 50.0
        assert info['max_sweep_rate'] == 110.0
        assert info['integration_time'] == 10.0
        assert info['settle_time'] == 0.1
    
    @pytest.mark.hardware
    def test_custom_sweep_rate_parameter(self):
        """Test custom sweep rate parameter with hardware."""
        if not self.hardware_available:
            pytest.skip("Hardware not available")
        
        # Test with custom sweep rate
        self.experiment.settings['sweep_parameters']['max_sweep_rate'] = 50.0  # More conservative
        
        # Configure parameters that would be too fast with default 110 Hz limit
        self.experiment.settings['acquisition']['integration_time'] = 5.0
        self.experiment.settings['acquisition']['settle_time'] = 0.1
        self.experiment.settings['acquisition']['num_steps'] = 100
        self.experiment.settings['acquisition']['bidirectional'] = False
        
        # Should raise exception with custom 50 Hz limit
        with pytest.raises(ValueError, match="max rate: 50.0 Hz"):
            self.experiment._validate_sweep_parameters()
        
        # Reset to default
        self.experiment.settings['sweep_parameters']['max_sweep_rate'] = 110.0
    
    def teardown_method(self):
        """Clean up after each test."""
        if self.hardware_available:
            # Ensure microwave output is off
            try:
                self.microwave.update({'enable_output': False})
            except:
                pass
            
            # Stop any running ADwin processes
            try:
                self.adwin.stop_process(1)
            except:
                pass


class TestEnhancedODMRSweepHardwareIntegration:
    """Integration tests for EnhancedODMRSweepExperiment with hardware."""
    
    def setup_method(self):
        """Set up hardware integration test fixtures."""
        # Check if hardware is available
        try:
            self.microwave = SG384Generator()
            self.adwin = AdwinGoldDevice()
            self.hardware_available = True
        except Exception as e:
            print(f"Hardware not available: {e}")
            self.hardware_available = False
    
    @pytest.mark.hardware
    def test_full_experiment_cycle_with_hardware(self):
        """Test a complete experiment cycle with hardware (without running actual sweeps)."""
        if not self.hardware_available:
            pytest.skip("Hardware not available")
        
        # Configure devices
        devices = {
            'microwave': {'instance': self.microwave},
            'adwin': {'instance': self.adwin}
        }
        
        # Create experiment
        experiment = EnhancedODMRSweepExperiment(devices)
        
        # Configure safe test parameters
        experiment.settings['sweep_parameters']['start_frequency'] = 2.8e9
        experiment.settings['sweep_parameters']['stop_frequency'] = 2.9e9
        experiment.settings['microwave']['power'] = -50.0
        experiment.settings['microwave']['enable_output'] = False
        experiment.settings['acquisition']['integration_time'] = 10.0
        experiment.settings['acquisition']['settle_time'] = 0.1
        experiment.settings['acquisition']['num_steps'] = 5  # Very small for testing
        experiment.settings['acquisition']['bidirectional'] = False
        experiment.settings['acquisition']['sweeps_per_average'] = 1
        
        # Setup experiment
        experiment.setup()
        
        # Verify setup
        assert experiment.frequencies is not None
        assert len(experiment.frequencies) == 5
        assert experiment.settings['sweep_parameters']['sweep_sensitivity'] is not None
        
        # Cleanup
        experiment.cleanup()
        
        # Verify cleanup
        microwave_probes = self.microwave.read_probes(['enable_output'])
        assert microwave_probes['enable_output'] == False
    
    def teardown_method(self):
        """Clean up after each test."""
        if hasattr(self, 'hardware_available') and self.hardware_available:
            # Ensure microwave output is off
            try:
                self.microwave.update({'enable_output': False})
            except:
                pass
            
            # Stop any running ADwin processes
            try:
                self.adwin.stop_process(1)
            except:
                pass 