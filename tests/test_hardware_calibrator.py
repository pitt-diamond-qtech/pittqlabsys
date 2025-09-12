"""
Tests for the HardwareCalibrator module.

This module tests the hardware-specific timing calibration functionality.
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from src.Model.hardware_calibrator import HardwareCalibrator
from src.Model.sequence import Sequence
from src.Model.pulses import GaussianPulse, SquarePulse


class TestHardwareCalibrator:
    """Test the HardwareCalibrator class."""
    
    def test_initialization_defaults(self):
        """Test that HardwareCalibrator initializes with defaults when no files provided."""
        calibrator = HardwareCalibrator()
        
        assert calibrator.connection_file is None
        assert calibrator.config_file is None
        assert "channels" in calibrator.connection_map
        assert "markers" in calibrator.connection_map
        assert "laser_delay" in calibrator.calibration_delays
    
    def test_default_connection_map(self):
        """Test that default connection map is set correctly."""
        calibrator = HardwareCalibrator()
        
        # Check channels
        assert calibrator.connection_map["channels"]["1"]["connection"] == "IQ_modulator_I_input"
        assert calibrator.connection_map["channels"]["2"]["connection"] == "IQ_modulator_Q_input"
        
        # Check markers
        assert calibrator.connection_map["markers"]["ch1_marker2"]["connection"] == "laser_switch"
        assert calibrator.connection_map["markers"]["ch2_marker2"]["connection"] == "counter_trigger"
    
    def test_default_calibration_delays(self):
        """Test that default calibration delays are set correctly."""
        calibrator = HardwareCalibrator()
        
        assert calibrator.calibration_delays["laser_delay"] == 50.0
        assert calibrator.calibration_delays["iq_delay"] == 30.0
        assert calibrator.calibration_delays["counter_delay"] == 15.0
        assert calibrator.calibration_delays["units"] == "ns"
    
    def test_load_connection_map_from_file(self):
        """Test loading connection map from JSON file."""
        # Create temporary connection file
        connection_data = {
            "awg520_connections": {
                "channels": {
                    "1": {
                        "connection": "custom_I_input",
                        "calibration_delays": ["custom_delay"]
                    }
                },
                "markers": {
                    "ch1_marker1": {
                        "connection": "custom_trigger",
                        "calibration_delays": ["trigger_delay"]
                    }
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(connection_data, f)
            temp_file = f.name
        
        try:
            calibrator = HardwareCalibrator(connection_file=temp_file)
            
            assert calibrator.connection_map["channels"]["1"]["connection"] == "custom_I_input"
            assert calibrator.connection_map["markers"]["ch1_marker1"]["connection"] == "custom_trigger"
        finally:
            Path(temp_file).unlink()
    
    def test_load_calibration_delays_from_config(self):
        """Test loading calibration delays from config file."""
        # Create temporary config file
        config_data = {
            "awg520": {
                "calibration_delays": {
                    "custom_laser_delay": 75.0,
                    "custom_mw_delay": 40.0,
                    "units": "ns"
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_file = f.name
        
        try:
            calibrator = HardwareCalibrator(config_file=temp_file)
            
            assert calibrator.calibration_delays["custom_laser_delay"] == 75.0
            assert calibrator.calibration_delays["custom_mw_delay"] == 40.0
        finally:
            Path(temp_file).unlink()
    
    def test_get_delay_for_connection(self):
        """Test getting delay for specific connections."""
        calibrator = HardwareCalibrator()
        
        # Test channel delay
        delay = calibrator.get_delay_for_connection("channels", "1")
        assert delay == 30.0  # iq_delay
        
        # Test marker delay
        delay = calibrator.get_delay_for_connection("markers", "ch1_marker2")
        assert delay == 50.0  # laser_delay
        
        # Test non-existent connection
        delay = calibrator.get_delay_for_connection("channels", "99")
        assert delay == 0.0
    
    def test_calibrate_sequence(self):
        """Test applying hardware calibration to a sequence."""
        calibrator = HardwareCalibrator()
        
        # Create a test sequence
        seq = Sequence(1000)
        
        # Add pulses at different times
        laser_pulse = SquarePulse("laser_pulse", 100, amplitude=1.0)
        mw_pulse = GaussianPulse("pi_pulse", 80, sigma=20, amplitude=1.0)
        
        seq.add_pulse(200, laser_pulse)  # Should get laser_delay (50ns)
        seq.add_pulse(400, mw_pulse)     # Should get iq_delay (30ns)
        
        # Calibrate the sequence
        calibrated_seq = calibrator.calibrate_sequence(seq, sample_rate=1e9)
        
        # Check that pulses were shifted backward
        # Laser pulse: 200 - (50ns * 1GHz) = 200 - 50 = 150
        # MW pulse: 400 - (30ns * 1GHz) = 400 - 30 = 370
        
        pulse_timings = [(start, pulse.name) for start, pulse in calibrated_seq.pulses]
        assert (150, "laser_pulse") in pulse_timings
        assert (370, "pi_pulse") in pulse_timings
    
    def test_get_pulse_connection(self):
        """Test determining connection type and ID for pulses."""
        calibrator = HardwareCalibrator()
        
        # Test laser pulse
        laser_pulse = SquarePulse("laser_pulse", 100, amplitude=1.0)
        conn_type, conn_id = calibrator._get_pulse_connection(laser_pulse)
        assert conn_type == "markers"
        assert conn_id == "ch1_marker2"
        
        # Test microwave pulse
        mw_pulse = GaussianPulse("pi_pulse", 100, sigma=20, amplitude=1.0)
        conn_type, conn_id = calibrator._get_pulse_connection(mw_pulse)
        assert conn_type == "channels"
        assert conn_id == "1"
        
        # Test counter pulse
        counter_pulse = SquarePulse("counter_pulse", 100, amplitude=1.0)
        conn_type, conn_id = calibrator._get_pulse_connection(counter_pulse)
        assert conn_type == "markers"
        assert conn_id == "ch2_marker2"
    
    def test_get_calibration_summary(self):
        """Test getting calibration summary."""
        calibrator = HardwareCalibrator()
        
        summary = calibrator.get_calibration_summary()
        
        assert "connection_file" in summary
        assert "config_file" in summary
        assert "connection_map" in summary
        assert "calibration_delays" in summary
        assert "total_connections" in summary
        assert summary["total_connections"] == 6  # 2 channels + 4 markers
    
    def test_validate_connections(self):
        """Test connection validation for experiment types."""
        calibrator = HardwareCalibrator()
        
        # Test ODMR experiment validation
        result = calibrator.validate_connections("odmr")
        
        assert "required" in result
        assert "missing" in result
        assert "available" in result
        assert result["experiment_type"] == "odmr"
        
        # Should have required connections: ch1, ch2, ch1_marker2, ch2_marker2
        required = result["required"]
        assert "ch1" in required
        assert "ch2" in required
        assert "ch1_marker2" in required
        assert "ch2_marker2" in required
    
    def test_error_handling_invalid_json(self):
        """Test error handling for invalid JSON files."""
        # Create temporary file with invalid JSON
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json content")
            temp_file = f.name
        
        try:
            # Should not raise exception, should fall back to defaults
            calibrator = HardwareCalibrator(connection_file=temp_file)
            
            # Should have default connection map
            assert "channels" in calibrator.connection_map
            assert "markers" in calibrator.connection_map
        finally:
            Path(temp_file).unlink()
    
    def test_error_handling_missing_file(self):
        """Test error handling for missing files."""
        # Should not raise exception, should fall back to defaults
        calibrator = HardwareCalibrator(connection_file="nonexistent_file.json")
        
        # Should have default connection map
        assert "channels" in calibrator.connection_map
        assert "markers" in calibrator.connection_map


class TestHardwareCalibratorIntegration:
    """Integration tests for HardwareCalibrator."""
    
    def test_full_calibration_pipeline(self):
        """Test the complete calibration pipeline with a realistic sequence."""
        calibrator = HardwareCalibrator()
        
        # Create a realistic qubit sequence
        seq = Sequence(2000)
        
        # Add typical qubit experiment pulses
        pi2_pulse = GaussianPulse("pi_2_pulse", 100, sigma=25, amplitude=1.0)
        laser_pulse = SquarePulse("laser_pulse", 200, amplitude=1.0)
        counter_pulse = SquarePulse("counter_pulse", 150, amplitude=1.0)
        
        seq.add_pulse(0, pi2_pulse)      # Microwave pulse
        seq.add_pulse(300, laser_pulse)   # Laser pulse
        seq.add_pulse(600, counter_pulse) # Counter trigger
        
        # Calibrate the sequence
        calibrated_seq = calibrator.calibrate_sequence(seq, sample_rate=1e9)
        
        # Verify all pulses are present
        assert len(calibrated_seq.pulses) == 3
        
        # Verify timing adjustments were applied
        pulse_timings = {pulse.name: start for start, pulse in calibrated_seq.pulses}
        
        # pi_2_pulse: 0 - 30ns = -30ns, clamped to 0
        assert pulse_timings["pi_2_pulse"] == 0
        
        # laser_pulse: 300 - 50ns = 250
        assert pulse_timings["laser_pulse"] == 250
        
        # counter_pulse: 600 - 15ns = 585
        assert pulse_timings["counter_pulse"] == 585
