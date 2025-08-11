"""
Test suite for SG384 example script.

These tests verify that the SG384 example script works correctly
without requiring actual hardware.
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Import the example script
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'examples'))
from sg384_example import SG384Example


class TestSG384Example:
    """Test suite for SG384Example class."""
    
    @pytest.fixture
    def mock_sg384(self):
        """Create a mocked SG384 instance."""
        mock_sg = Mock()
        
        # Mock the _query method to return expected responses
        mock_sg._query.side_effect = lambda cmd: {
            '*IDN?': 'Stanford Research Systems,SG384,12345,1.0.0',
            'FREQ?': '2.5e9',
            'POWR?': '-10.0',
            'PHAS?': '0.0',
            'ENBL?': '0',
            'SSWP?': '0'
        }.get(cmd, '0')
        
        # Mock the _send method
        mock_sg._send = Mock()
        
        # Mock the close method
        mock_sg.close = Mock()
        
        return mock_sg
    
    @pytest.fixture
    def example_instance(self):
        """Create an SG384Example instance with test settings."""
        settings = {
            'connection_type': 'LAN',
            'ip_address': '192.168.1.100',
            'port': 5025
        }
        return SG384Example(settings)
    
    def test_initialization(self, example_instance):
        """Test SG384Example initialization."""
        assert example_instance.settings['connection_type'] == 'LAN'
        assert example_instance.settings['ip_address'] == '192.168.1.100'
        assert example_instance.settings['port'] == 5025
        assert example_instance.sg384 is None
        assert len(example_instance.data_log) == 0
        
        # Check that output directory was created
        assert example_instance.output_dir.exists()
        assert example_instance.output_dir.name == 'sg384_data'
    
    @patch('sg384_example.SG384Generator')
    def test_connect_success(self, mock_generator_class, example_instance):
        """Test successful connection to SG384."""
        # Mock the SG384Generator constructor
        mock_sg384 = Mock()
        mock_generator_class.return_value = mock_sg384
        
        # Mock the _query method
        mock_sg384._query.return_value = 'Stanford Research Systems,SG384,12345,1.0.0'
        
        # Test connection
        result = example_instance.connect()
        
        assert result is True
        assert example_instance.sg384 is not None
        mock_generator_class.assert_called_once_with(settings=example_instance.settings)
    
    @patch('sg384_example.SG384Generator')
    def test_connect_failure(self, mock_generator_class, example_instance):
        """Test failed connection to SG384."""
        # Mock the SG384Generator constructor to raise an exception
        mock_generator_class.side_effect = Exception("Connection failed")
        
        # Test connection
        result = example_instance.connect()
        
        assert result is False
        assert example_instance.sg384 is None
    
    def test_disconnect(self, example_instance, mock_sg384):
        """Test disconnection from SG384."""
        example_instance.sg384 = mock_sg384
        
        example_instance.disconnect()
        
        mock_sg384.close.assert_called_once()
    
    def test_print_device_status(self, example_instance, mock_sg384):
        """Test device status printing."""
        example_instance.sg384 = mock_sg384
        
        # Mock the _query method for device status
        mock_sg384._query.side_effect = lambda cmd: {
            'FREQ?': '2.5e9',
            'POWR?': '-10.0',
            'PHAS?': '0.0',
            'ENBL?': '0',
            'SSWP?': '0'
        }.get(cmd, '0')
        
        # This should not raise an exception
        example_instance._print_device_status()
    
    def test_log_data(self, example_instance):
        """Test data logging functionality."""
        from datetime import datetime
        
        # Log some test data
        example_instance._log_data('test_operation', value=42, status='success')
        
        assert len(example_instance.data_log) == 1
        log_entry = example_instance.data_log[0]
        
        assert log_entry['operation'] == 'test_operation'
        assert log_entry['value'] == 42
        assert log_entry['status'] == 'success'
        assert isinstance(log_entry['timestamp'], datetime)
    
    @patch('sg384_example.SG384Generator')
    def test_basic_operation_demo(self, mock_generator_class, example_instance):
        """Test basic operation demonstration."""
        # Mock the SG384Generator
        mock_sg384 = Mock()
        mock_generator_class.return_value = mock_sg384
        example_instance.sg384 = mock_sg384
        
        # Mock the _query method for frequency, power, and phase
        mock_sg384._query.side_effect = lambda cmd: {
            'FREQ?': '2.5e9',
            'POWR?': '-10.0',
            'PHAS?': '0.0'
        }.get(cmd, '0')
        
        # Mock the setter methods
        mock_sg384.set_frequency = Mock()
        mock_sg384.set_power = Mock()
        mock_sg384.set_phase = Mock()
        
        # This should not raise an exception
        example_instance.basic_operation_demo()
        
        # Verify that setters were called
        assert mock_sg384.set_frequency.call_count == 5  # 5 test frequencies
        assert mock_sg384.set_power.call_count == 7      # 7 test powers
        assert mock_sg384.set_phase.call_count == 9      # 9 test phases
    
    @patch('sg384_example.SG384Generator')
    def test_sweep_generation_demo(self, mock_generator_class, example_instance):
        """Test sweep generation demonstration."""
        # Mock the SG384Generator
        mock_sg384 = Mock()
        mock_generator_class.return_value = mock_sg384
        example_instance.sg384 = mock_sg384
        
        # Mock the _query method for sweep
        mock_sg384._query.side_effect = lambda cmd: {
            'SSWP?': '1'  # Sweep is running
        }.get(cmd, '0')
        
        # Mock the _send method
        mock_sg384._send = Mock()
        
        # Mock the setter methods
        mock_sg384.set_frequency = Mock()
        
        # This should not raise an exception
        example_instance.sweep_generation_demo()
        
        # Verify that sweep commands were sent
        assert mock_sg384._send.call_count >= 4  # At least SFNC, SDEV, SRAT, SSWP
    
    @patch('sg384_example.SG384Generator')
    def test_power_ramping_demo(self, mock_generator_class, example_instance):
        """Test power ramping demonstration."""
        # Mock the SG384Generator
        mock_sg384 = Mock()
        mock_generator_class.return_value = mock_sg384
        example_instance.sg384 = mock_sg384
        
        # Mock the _query method for power
        mock_sg384._query.return_value = '-10.0'
        
        # Mock the setter methods
        mock_sg384.set_frequency = Mock()
        mock_sg384.set_power = Mock()
        
        # This should not raise an exception
        example_instance.power_ramping_demo()
        
        # Verify that power was set multiple times
        assert mock_sg384.set_power.call_count > 0
    
    @patch('sg384_example.SG384Generator')
    def test_frequency_hopping_demo(self, mock_generator_class, example_instance):
        """Test frequency hopping demonstration."""
        # Mock the SG384Generator
        mock_sg384 = Mock()
        mock_generator_class.return_value = mock_sg384
        example_instance.sg384 = mock_sg384
        
        # Mock the _query method for frequency
        mock_sg384._query.return_value = '2.5e9'
        
        # Mock the setter methods
        mock_sg384.set_power = Mock()
        mock_sg384.set_frequency = Mock()
        
        # This should not raise an exception
        example_instance.frequency_hopping_demo()
        
        # Verify that frequency was set multiple times
        assert mock_sg384.set_frequency.call_count == 8  # 8 test frequencies
    
    @patch('sg384_example.SG384Generator')
    def test_cleanup(self, mock_generator_class, example_instance):
        """Test cleanup and safety measures."""
        # Mock the SG384Generator
        mock_sg384 = Mock()
        mock_generator_class.return_value = mock_sg384
        example_instance.sg384 = mock_sg384
        
        # Mock the _query method for cleanup verification
        mock_sg384._query.side_effect = lambda cmd: {
            'ENBL?': '0',
            'SSWP?': '0'
        }.get(cmd, '0')
        
        # Mock the _send method
        mock_sg384._send = Mock()
        
        # Mock the setter methods
        mock_sg384.set_frequency = Mock()
        mock_sg384.set_power = Mock()
        mock_sg384.set_phase = Mock()
        
        # This should not raise an exception
        example_instance.cleanup()
        
        # Verify that cleanup commands were sent
        assert mock_sg384._send.call_count >= 2  # At least SSWP 0 and ENBL 0
    
    def test_data_saving_methods(self, example_instance):
        """Test data saving methods."""
        import numpy as np
        
        # Test data
        timestamps = np.array([0, 1, 2, 3, 4])
        frequencies = np.array([2.0e9, 2.1e9, 2.2e9, 2.3e9, 2.4e9])
        powers = np.array([-10, -9, -8, -7, -6])
        
        # Test sweep data saving
        example_instance._save_sweep_data(timestamps, frequencies, powers, 2.2e9, 100e6, 1e6)
        
        # Test power ramp data saving
        set_powers = np.array([-20, -18, -16, -14, -12])
        actual_powers = np.array([-19.5, -17.8, -15.9, -13.7, -11.8])
        example_instance._save_power_ramp_data(set_powers, actual_powers)
        
        # Test frequency hop data saving
        measurements = [
            {'hop': 1, 'set_freq': 2.0e9, 'actual_freq': 2.0e9, 'error': 0, 'hop_time': 0.001},
            {'hop': 2, 'set_freq': 2.5e9, 'actual_freq': 2.5e9, 'error': 0, 'hop_time': 0.001}
        ]
        example_instance._save_frequency_hop_data(measurements)
        
        # Check that files were created
        output_files = list(example_instance.output_dir.glob('*.csv'))
        assert len(output_files) >= 3  # At least 3 CSV files should be created
    
    def test_plot_generation(self, example_instance):
        """Test plot generation functionality."""
        import numpy as np
        
        # Test data
        timestamps = np.array([0, 1, 2, 3, 4])
        frequencies = np.array([2.0e9, 2.1e9, 2.2e9, 2.3e9, 2.4e9])
        powers = np.array([-10, -9, -8, -7, -6])
        
        # This should not raise an exception
        example_instance._plot_sweep_results(timestamps, frequencies, powers)
        
        # Check that plot file was created
        plot_files = list(example_instance.output_dir.glob('*.png'))
        assert len(plot_files) >= 1  # At least 1 PNG file should be created


class TestSG384ExampleIntegration:
    """Integration tests for SG384Example."""
    
    @patch('sg384_example.SG384Generator')
    def test_full_demo_run(self, mock_generator_class):
        """Test running the full demonstration."""
        # Mock the SG384Generator
        mock_sg384 = Mock()
        mock_generator_class.return_value = mock_sg384
        
        # Mock all necessary methods
        mock_sg384._query.side_effect = lambda cmd: {
            '*IDN?': 'Stanford Research Systems,SG384,12345,1.0.0',
            'FREQ?': '2.5e9',
            'POWR?': '-10.0',
            'PHAS?': '0.0',
            'ENBL?': '0',
            'SSWP?': '0'
        }.get(cmd, '0')
        
        mock_sg384._send = Mock()
        mock_sg384.set_frequency = Mock()
        mock_sg384.set_power = Mock()
        mock_sg384.set_phase = Mock()
        mock_sg384.close = Mock()
        
        # Create example instance
        settings = {
            'connection_type': 'LAN',
            'ip_address': '192.168.1.100',
            'port': 5025
        }
        example = SG384Example(settings)
        
        # Run the demo
        result = example.run_demo()
        
        # Should complete successfully
        assert result is True
        
        # Verify cleanup was called
        mock_sg384.close.assert_called_once()


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"]) 