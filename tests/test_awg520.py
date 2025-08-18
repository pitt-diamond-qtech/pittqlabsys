"""
Comprehensive test suite for Tektronix AWG520 driver.

These tests cover:
- Basic SCPI communication
- Clock configuration
- Sequence control
- File operations via FTP
- Marker control for laser applications
- Device wrapper functionality

Tests are designed to work with both real hardware and mocked connections.
"""

import pytest
import sys
import os
import time
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.Controller.awg520 import AWG520Driver, AWG520Device, FileTransferWorker


class TestAWG520Driver:
    """Test suite for AWG520Driver class."""
    
    @pytest.fixture
    def mock_awg_driver(self):
        """Create a mocked AWG520Driver instance."""
        with patch('src.Controller.awg520.FTP') as mock_ftp:
            # Mock FTP connection
            mock_ftp_instance = Mock()
            mock_ftp.return_value = mock_ftp_instance
            mock_ftp_instance.connect.return_value = None
            mock_ftp_instance.login.return_value = None
            
            # Create driver instance
            driver = AWG520Driver(
                ip_address='192.168.1.100',
                scpi_port=4000,
                ftp_port=21
            )
            
            # Mock the send_command method
            driver.send_command = Mock()
            
            return driver
    
    def test_initialization(self, mock_awg_driver):
        """Test AWG520Driver initialization."""
        assert mock_awg_driver.addr == ('192.168.1.100', 4000)
        assert mock_awg_driver.ftp_port == 21
        assert mock_awg_driver.ftp_user == 'usr'
        assert mock_awg_driver.ftp_pass == 'pw'
        assert mock_awg_driver.logger is not None
    
    def test_ftp_connection_success(self):
        """Test successful FTP connection."""
        with patch('src.Controller.awg520.FTP') as mock_ftp:
            mock_ftp_instance = Mock()
            mock_ftp.return_value = mock_ftp_instance
            mock_ftp_instance.connect.return_value = None
            mock_ftp_instance.login.return_value = None
            
            driver = AWG520Driver('192.168.1.100')
            assert driver.ftp is not None
    
    def test_ftp_connection_failure(self):
        """Test FTP connection failure."""
        with patch('src.Controller.awg520.FTP') as mock_ftp:
            mock_ftp_instance = Mock()
            mock_ftp.return_value = mock_ftp_instance
            mock_ftp_instance.connect.side_effect = Exception("Connection failed")
            
            with pytest.raises(Exception):
                AWG520Driver('192.168.1.100')
    
    @patch('socket.socket')
    def test_send_command_success(self, mock_socket, mock_awg_driver):
        """Test successful SCPI command sending."""
        # Mock socket
        mock_socket_instance = Mock()
        mock_socket.return_value.__enter__.return_value = mock_socket_instance
        mock_socket_instance.recv.return_value = b'OK\n'
        
        # Mock the send_command method to avoid actual socket calls
        original_send_command = mock_awg_driver.send_command
        mock_awg_driver.send_command = Mock()
        
        # Test command without query
        mock_awg_driver.send_command.return_value = None
        result = mock_awg_driver.send_command('AWGC:RUN')
        assert result is None  # No query, so no response expected
        
        # Test command with query
        mock_awg_driver.send_command.return_value = '2.5GHz'
        result = mock_awg_driver.send_command('FREQ?', query=True)
        assert result == '2.5GHz'
        
        # Restore original method
        mock_awg_driver.send_command = original_send_command
    
    @patch('socket.socket')
    def test_send_command_failure(self, mock_socket, mock_awg_driver):
        """Test SCPI command failure."""
        # Mock the send_command method to avoid actual socket calls
        original_send_command = mock_awg_driver.send_command
        mock_awg_driver.send_command = Mock()
        mock_awg_driver.send_command.return_value = None
        
        result = mock_awg_driver.send_command('AWGC:RUN')
        assert result is None
        
        # Restore original method
        mock_awg_driver.send_command = original_send_command
    
    def test_clock_configuration(self, mock_awg_driver):
        """Test clock configuration methods."""
        # Test external clock
        mock_awg_driver.send_command.return_value = None
        result = mock_awg_driver.set_clock_external()
        mock_awg_driver.send_command.assert_called_with('AWGC:CLOC:SOUR EXT')
        assert result is None
        
        # Test internal clock
        result = mock_awg_driver.set_clock_internal()
        mock_awg_driver.send_command.assert_called_with('AWGC:CLOC:SOUR INT')
        assert result is None
    
    def test_ref_clock_configuration(self, mock_awg_driver):
        """Test reference clock configuration methods."""
        # Test external reference clock
        mock_awg_driver.send_command.return_value = None
        result = mock_awg_driver.set_ref_clock_external()
        assert mock_awg_driver.send_command.call_count >= 2
        assert result is None
        
        # Test internal reference clock
        result = mock_awg_driver.set_ref_clock_internal()
        assert mock_awg_driver.send_command.call_count >= 4
        assert result is None
    
    def test_enhanced_run_mode(self, mock_awg_driver):
        """Test enhanced run mode setting."""
        mock_awg_driver.send_command.return_value = None
        result = mock_awg_driver.set_enhanced_run_mode()
        mock_awg_driver.send_command.assert_called_with('AWGC:RMOD ENH')
        assert result is None
    
    def test_sequence_setup(self, mock_awg_driver):
        """Test sequence setup method."""
        mock_awg_driver.send_command.return_value = None
        
        result = mock_awg_driver.setup_sequence('test.seq', enable_iq=True)
        
        # Verify that all expected commands were sent
        expected_calls = [
            'SOUR1:ROSC:SOUR EXT',
            'SOUR2:ROSC:SOUR EXT',
            'AWGC:RMOD ENH',
            'SOUR1:FUNC:USER "test.seq","MAIN"',
            'SOUR2:FUNC:USER "test.seq","MAIN"',
            'SOUR1:VOLT:AMPL 1000mV',
            'SOUR1:VOLT:OFFS 0mV',
            'SOUR1:MARK1:VOLT:LOW 0',
            'SOUR1:MARK1:VOLT:HIGH 2.0',
            'SOUR1:MARK2:VOLT:LOW 0',
            'SOUR1:MARK2:VOLT:HIGH 2.0',
            'SOUR2:VOLT:AMPL 1000mV',
            'SOUR2:VOLT:OFFS 0mV',
            'SOUR2:MARK1:VOLT:LOW 0',
            'SOUR2:MARK1:VOLT:HIGH 2.0',
            'SOUR2:MARK2:VOLT:LOW 0',
            'SOUR2:MARK2:VOLT:HIGH 2.0',
            'OUTP1:STAT ON',
            'OUTP2:STAT ON'
        ]
        
        for call in expected_calls:
            mock_awg_driver.send_command.assert_any_call(call)
        
        assert result is None
    
    def test_sequence_control(self, mock_awg_driver):
        """Test sequence control methods."""
        mock_awg_driver.send_command.return_value = None
        
        # Test run
        result = mock_awg_driver.run()
        mock_awg_driver.send_command.assert_called_with('AWGC:RUN')
        assert result is None
        
        # Test stop
        result = mock_awg_driver.stop()
        mock_awg_driver.send_command.assert_called_with('AWGC:STOP')
        assert result is None
        
        # Test trigger
        result = mock_awg_driver.trigger()
        mock_awg_driver.send_command.assert_called_with('*TRG')
        assert result is None
        
        # Test event
        result = mock_awg_driver.event()
        mock_awg_driver.send_command.assert_called_with('AWGC:EVEN')
        assert result is None
    
    def test_jump_function(self, mock_awg_driver):
        """Test jump to line function."""
        mock_awg_driver.send_command.return_value = None
        
        result = mock_awg_driver.jump(5)
        mock_awg_driver.send_command.assert_called_with('AWGC:EVEN:SOFT 5')
        assert result is None
    
    def test_file_operations(self, mock_awg_driver):
        """Test file operation methods."""
        # Mock FTP methods
        mock_awg_driver.ftp.nlst.return_value = ['file1.wfm', 'file2.seq', 'file3.txt']
        mock_awg_driver.ftp.delete.return_value = None
        
        # Test list files
        files = mock_awg_driver.list_files()
        assert files == ['file1.wfm', 'file2.seq', 'file3.txt']
        
        # Test delete file
        result = mock_awg_driver.delete_file('file1.wfm')
        mock_awg_driver.ftp.delete.assert_called_with('file1.wfm')
        assert result is True
        
        # Test delete protected file
        result = mock_awg_driver.delete_file('parameter.dat')
        assert result is False
    
    def test_upload_download_files(self, mock_awg_driver):
        """Test file upload and download."""
        # Mock file operations
        mock_awg_driver.ftp.storbinary.return_value = None
        mock_awg_driver.ftp.retrbinary.return_value = None
        
        # Test upload
        with patch('builtins.open', create=True) as mock_open:
            mock_file = Mock()
            mock_open.return_value.__enter__.return_value = mock_file
            
            result = mock_awg_driver.upload_file('local.txt', 'remote.txt')
            assert result is True
            mock_awg_driver.ftp.storbinary.assert_called_once()
        
        # Test download
        result = mock_awg_driver.download_file('remote.txt', 'local.txt')
        assert result is True
        mock_awg_driver.ftp.retrbinary.assert_called_once()
    
    def test_cleanup(self, mock_awg_driver):
        """Test cleanup method."""
        mock_awg_driver.stop = Mock()
        mock_awg_driver.ftp.quit = Mock()
        
        mock_awg_driver.cleanup()
        
        mock_awg_driver.stop.assert_called_once()
        mock_awg_driver.ftp.quit.assert_called_once()


class TestAWG520LaserControl:
    """Test suite for laser control functionality via CH1 Marker 2."""
    
    @pytest.fixture
    def mock_awg_driver(self):
        """Create a mocked AWG520Driver instance for laser control tests."""
        with patch('Controller.awg520.FTP') as mock_ftp:
            mock_ftp_instance = Mock()
            mock_ftp.return_value = mock_ftp_instance
            mock_ftp_instance.connect.return_value = None
            mock_ftp_instance.login.return_value = None
            
            driver = AWG520Driver('192.168.1.100')
            driver.send_command = Mock()
            
            return driver
    
    def test_laser_on(self, mock_awg_driver):
        """Test turning on the laser via CH1 Marker 2."""
        mock_awg_driver.send_command.return_value = True
        
        result = mock_awg_driver.set_ch1_marker2_laser_on()
        
        # Verify both voltage commands were sent
        expected_calls = [
            'SOUR1:MARK2:VOLT:LOW 2.0',
            'SOUR1:MARK2:VOLT:HIGH 2.0'
        ]
        
        for call in expected_calls:
            mock_awg_driver.send_command.assert_any_call(call)
        
        assert result is True
        assert mock_awg_driver.send_command.call_count == 2
    
    def test_laser_off(self, mock_awg_driver):
        """Test turning off the laser via CH1 Marker 2."""
        mock_awg_driver.send_command.return_value = True
        
        result = mock_awg_driver.set_ch1_marker2_laser_off()
        
        # Verify both voltage commands were sent
        expected_calls = [
            'SOUR1:MARK2:VOLT:LOW 0.0',
            'SOUR1:MARK2:VOLT:HIGH 0.0'
        ]
        
        for call in expected_calls:
            mock_awg_driver.send_command.assert_any_call(call)
        
        assert result is True
        assert mock_awg_driver.send_command.call_count == 2
    
    def test_set_custom_laser_voltage(self, mock_awg_driver):
        """Test setting custom laser voltage levels."""
        mock_awg_driver.send_command.return_value = True
        
        result = mock_awg_driver.set_ch1_marker2_voltage(3.3, 3.3)
        
        expected_calls = [
            'SOUR1:MARK2:VOLT:LOW 3.3',
            'SOUR1:MARK2:VOLT:HIGH 3.3'
        ]
        
        for call in expected_calls:
            mock_awg_driver.send_command.assert_any_call(call)
        
        assert result is True
    
    def test_set_custom_laser_voltage_different_levels(self, mock_awg_driver):
        """Test setting different low and high voltage levels."""
        mock_awg_driver.send_command.return_value = True
        
        result = mock_awg_driver.set_ch1_marker2_voltage(2.5, 5.0)
        
        expected_calls = [
            'SOUR1:MARK2:VOLT:LOW 2.5',
            'SOUR1:MARK2:VOLT:HIGH 5.0'
        ]
        
        for call in expected_calls:
            mock_awg_driver.send_command.assert_any_call(call)
        
        assert result is True
    
    def test_get_laser_voltage_success(self, mock_awg_driver):
        """Test getting laser voltage levels successfully."""
        mock_awg_driver.send_command.side_effect = ['2.5', '5.0']
        
        low_v, high_v = mock_awg_driver.get_ch1_marker2_voltage()
        
        assert low_v == 2.5
        assert high_v == 5.0
        
        # Verify query commands were sent
        expected_calls = [
            'SOUR1:MARK2:VOLT:LOW?',
            'SOUR1:MARK2:VOLT:HIGH?'
        ]
        
        for call in expected_calls:
            mock_awg_driver.send_command.assert_any_call(call, query=True)
    
    def test_get_laser_voltage_failure(self, mock_awg_driver):
        """Test getting laser voltage levels when commands fail."""
        mock_awg_driver.send_command.return_value = None
        
        low_v, high_v = mock_awg_driver.get_ch1_marker2_voltage()
        
        assert low_v is None
        assert high_v is None
    
    def test_is_laser_on_voltage_above_threshold(self, mock_awg_driver):
        """Test laser status detection when voltage is above threshold."""
        mock_awg_driver.get_ch1_marker2_voltage = Mock(return_value=(3.0, 3.0))
        
        result = mock_awg_driver.is_ch1_marker2_laser_on()
        
        assert result is True
    
    def test_is_laser_on_voltage_below_threshold(self, mock_awg_driver):
        """Test laser status detection when voltage is below threshold."""
        mock_awg_driver.get_ch1_marker2_voltage = Mock(return_value=(1.0, 1.0))
        
        result = mock_awg_driver.is_ch1_marker2_laser_on()
        
        assert result is False
    
    def test_is_laser_on_voltage_mixed(self, mock_awg_driver):
        """Test laser status detection with mixed voltage levels."""
        mock_awg_driver.get_ch1_marker2_voltage = Mock(return_value=(1.0, 3.0))
        
        result = mock_awg_driver.is_ch1_marker2_laser_on()
        
        assert result is True  # High voltage is above threshold
    
    def test_is_laser_on_voltage_none(self, mock_awg_driver):
        """Test laser status detection when voltage reading fails."""
        mock_awg_driver.get_ch1_marker2_voltage = Mock(return_value=(None, None))
        
        result = mock_awg_driver.is_ch1_marker2_laser_on()
        
        assert result is False

    def test_additional_marker_functions(self, mock_awg_driver):
        """Test additional marker control functions."""
        mock_awg_driver.send_command.return_value = True
        
        # Test CH1 Marker 1
        result = mock_awg_driver.set_ch1_marker1_voltage(2.0)
        assert result is True
        mock_awg_driver.send_command.assert_any_call('SOUR1:MARK1:VOLT:LOW 2.0')
        mock_awg_driver.send_command.assert_any_call('SOUR1:MARK1:VOLT:HIGH 2.0')
        
        # Test CH2 Marker 1
        result = mock_awg_driver.set_ch2_marker1_voltage(3.0)
        assert result is True
        mock_awg_driver.send_command.assert_any_call('SOUR2:MARK1:VOLT:LOW 3.0')
        mock_awg_driver.send_command.assert_any_call('SOUR2:MARK1:VOLT:HIGH 3.0')
        
        # Test CH2 Marker 2
        result = mock_awg_driver.set_ch2_marker2_voltage(4.0)
        assert result is True
        mock_awg_driver.send_command.assert_any_call('SOUR2:MARK2:VOLT:LOW 4.0')
        mock_awg_driver.send_command.assert_any_call('SOUR2:MARK2:VOLT:HIGH 4.0')
    
    def test_legacy_functions(self, mock_awg_driver):
        """Test legacy CH2 Marker 2 functions for backward compatibility."""
        mock_awg_driver.send_command.return_value = True
        
        # Test legacy laser on (should call CH2 Marker 2 voltage)
        result = mock_awg_driver.set_ch2_marker2_laser_on()
        assert result is True
        mock_awg_driver.send_command.assert_any_call('SOUR2:MARK2:VOLT:LOW 2.0')
        mock_awg_driver.send_command.assert_any_call('SOUR2:MARK2:VOLT:HIGH 2.0')
        
        # Test legacy laser off
        result = mock_awg_driver.set_ch2_marker2_laser_off()
        assert result is True
        mock_awg_driver.send_command.assert_any_call('SOUR2:MARK2:VOLT:LOW 0.0')
        mock_awg_driver.send_command.assert_any_call('SOUR2:MARK2:VOLT:HIGH 0.0')


class TestAWG520Device:
    """Test suite for AWG520Device wrapper class."""
    
    @pytest.fixture
    def mock_awg_device(self):
        """Create a mocked AWG520Device instance."""
        with patch('src.Controller.awg520.AWG520Driver') as mock_driver_class:
            mock_driver = Mock()
            mock_driver_class.return_value = mock_driver
            
            # Mock the send_command method for connection testing
            mock_driver.send_command.return_value = "SONY/TEK,AWG520,0,SCPI:95.0 OS:3.0"
            
            # Create device first
            device = AWG520Device(settings={
                'ip_address': '192.168.1.100',
                'scpi_port': 4000,
                'ftp_port': 21,
                'ftp_user': 'usr',
                'ftp_pass': 'pw',
                'seq_file': 'test.seq',
                'enable_iq': False
            })
            
            # Replace the driver with our mock after creation
            # Use object.__setattr__ to bypass the custom __setattr__ method
            object.__setattr__(device, 'driver', mock_driver)
            object.__setattr__(device, '_ftp_thread', Mock())
            
            return device, mock_driver

    def test_device_initialization(self, mock_awg_device):
        """Test AWG520Device initialization."""
        device, mock_driver = mock_awg_device
        
        assert device.settings['ip_address'] == '192.168.1.100'
        assert device.settings['scpi_port'] == 4000
        assert device.settings['ftp_port'] == 21
        assert device.settings['seq_file'] == 'test.seq'
        assert device.settings['enable_iq'] is False
        assert device.driver is mock_driver

    def test_device_connection_testing(self, mock_awg_device):
        """Test AWG520Device connection testing functionality."""
        device, mock_driver = mock_awg_device
        
        # Test successful connection
        mock_driver.send_command.return_value = "SONY/TEK,AWG520,0,SCPI:95.0 OS:3.0"
        device._test_connection()
        assert device.is_connected is True
        
        # Test failed connection
        mock_driver.send_command.side_effect = Exception("Connection failed")
        device._test_connection()
        assert device.is_connected is False
        
        # Test unrecognized device
        mock_driver.send_command.side_effect = None
        mock_driver.send_command.return_value = "UNKNOWN_DEVICE"
        device._test_connection()
        assert device.is_connected is False

    def test_device_identification_variants(self, mock_awg_device):
        """Test AWG520Device identification with different valid response formats."""
        device, mock_driver = mock_awg_device
        
        # Test with SONY/TEK identifier
        mock_driver.send_command.return_value = "SONY/TEK,AWG520,0,SCPI:95.0 OS:3.0"
        device._test_connection()
        assert device.is_connected is True
        
        # Test with just AWG520 identifier
        mock_driver.send_command.return_value = "AWG520,SomeOtherInfo,Version"
        device._test_connection()
        assert device.is_connected is True
        
        # Test with empty response
        mock_driver.send_command.return_value = ""
        device._test_connection()
        assert device.is_connected is False
        
        # Test with None response
        mock_driver.send_command.return_value = None
        device._test_connection()
        assert device.is_connected is False

    def test_device_connection_status(self, mock_awg_device):
        """Test AWG520Device connection status property."""
        device, mock_driver = mock_awg_device
        
        # Mock the connection test to simulate successful connection
        mock_driver.send_command.return_value = "SONY/TEK,AWG520,0,SCPI:95.0 OS:3.0"
        
        # Test connection status
        assert device.is_connected is True
        
        # Test connection loss
        mock_driver.send_command.side_effect = Exception("Connection lost")
        assert device.is_connected is False

    def test_device_connection_loss_detection(self, mock_awg_device):
        """Test AWG520Device connection loss detection in is_connected property."""
        device, mock_driver = mock_awg_device
        
        # Start with successful connection
        mock_driver.send_command.return_value = "SONY/TEK,AWG520,0,SCPI:95.0 OS:3.0"
        device._test_connection()
        assert device.is_connected is True
        
        # Simulate connection loss during status check
        mock_driver.send_command.side_effect = Exception("Connection lost")
        
        # The is_connected property should detect this and update internal state
        assert device.is_connected is False
        assert device._is_connected is False

    def test_device_setup_with_connection(self, mock_awg_device):
        """Test AWG520Device setup when connected."""
        device, mock_driver = mock_awg_device
        
        # Mock successful connection
        mock_driver.send_command.return_value = "SONY/TEK,AWG520,0,SCPI:95.0 OS:3.0"
        
        # Setup should succeed when connected
        result = device.setup()
        assert result is True
        
        # Verify setup commands were called
        mock_driver.set_ref_clock.assert_any_call(1, 'EXT')
        mock_driver.set_ref_clock.assert_any_call(2, 'EXT')
        mock_driver.send_command.assert_any_call('AWGC:RMOD ENH')

    def test_device_setup_without_connection(self, mock_awg_device):
        """Test AWG520Device setup when not connected."""
        device, mock_driver = mock_awg_device
        
        # Mock failed connection
        mock_driver.send_command.side_effect = Exception("Connection failed")
        
        # Setup should fail when not connected
        result = device.setup()
        assert result is False

    def test_device_setup_connection_required(self, mock_awg_device):
        """Test AWG520Device setup requires active connection."""
        device, mock_driver = mock_awg_device
        
        # Ensure device is not connected
        device._is_connected = False
        
        # Setup should fail and return False
        result = device.setup()
        assert result is False
        
        # No setup commands should be called
        mock_driver.set_ref_clock.assert_not_called()
        mock_driver.send_command.assert_not_called()

    def test_device_reconnect(self, mock_awg_device):
        """Test AWG520Device reconnection functionality."""
        device, mock_driver = mock_awg_device
        
        # Mock successful reconnection
        mock_driver.send_command.return_value = "SONY/TEK,AWG520,0,SCPI:95.0 OS:3.0"
        
        # Test reconnection
        result = device.reconnect()
        assert result is True
        assert device.is_connected is True

    def test_device_cleanup(self, mock_awg_device):
        """Test AWG520Device cleanup functionality."""
        device, mock_driver = mock_awg_device
        
        # Mock successful connection first
        mock_driver.send_command.return_value = "SONY/TEK,AWG520,0,SCPI:95.0 OS:3.0"
        assert device.is_connected is True
        
        # Test cleanup
        device.cleanup()
        assert device.is_connected is False
        
        # Verify driver cleanup was called
        mock_driver.cleanup.assert_called_once()

    def test_laser_control_methods(self, mock_awg_device):
        """Test laser control methods in device wrapper."""
        device, mock_driver = mock_awg_device
        
        # Test laser on
        mock_driver.set_ch1_marker2_laser_on.return_value = True
        result = device.laser_on()
        mock_driver.set_ch1_marker2_laser_on.assert_called_once()
        assert result is True
        
        # Test laser off
        mock_driver.set_ch1_marker2_laser_off.return_value = True
        result = device.laser_off()
        mock_driver.set_ch1_marker2_laser_off.assert_called_once()
        assert result is True
        
        # Test set laser voltage
        mock_driver.set_ch1_marker2_voltage.return_value = True
        result = device.set_laser_voltage(3.3)
        mock_driver.set_ch1_marker2_voltage.assert_called_with(3.3)
        assert result is True
        
        # Test get laser voltage
        mock_driver.get_ch1_marker2_voltage.return_value = (2.5, 5.0)
        result = device.get_laser_voltage()
        mock_driver.get_ch1_marker2_voltage.assert_called_once()
        assert result == (2.5, 5.0)
        
        # Test is laser on
        mock_driver.is_ch1_marker2_laser_on.return_value = True
        result = device.is_laser_on()
        mock_driver.is_ch1_marker2_laser_on.assert_called_once()
        assert result is True
    
    def test_function_generator_methods(self, mock_awg_device):
        """Test function generator methods in device wrapper."""
        device, mock_driver = mock_awg_device
        
        # Test MW on/off
        mock_driver.mw_on_sb10MHz.return_value = True
        result = device.mw_on_sb10MHz(enable_iq=True)
        mock_driver.mw_on_sb10MHz.assert_called_with(True)
        assert result is True
        
        mock_driver.mw_off_sb10MHz.return_value = True
        result = device.mw_off_sb10MHz(enable_iq=True)
        mock_driver.mw_off_sb10MHz.assert_called_with(True)
        assert result is True
        
        # Test function generator configuration
        mock_driver.set_function_generator.return_value = True
        result = device.set_function_generator(1, 'SIN', '5MHz', 3.0, 45.0, True)
        mock_driver.set_function_generator.assert_called_with(1, 'SIN', '5MHz', 3.0, 45.0, True)
        assert result is True
        
        # Test function generator status
        mock_driver.get_function_generator_status.return_value = {'function': 'SIN', 'frequency': '10MHz', 'voltage': 2.0, 'phase': 0.0}
        result = device.get_function_generator_status(1)
        mock_driver.get_function_generator_status.assert_called_with(1)
        assert result == {'function': 'SIN', 'frequency': '10MHz', 'voltage': 2.0, 'phase': 0.0}
        
        # Test IQ modulation
        mock_driver.enable_iq_modulation.return_value = True
        result = device.enable_iq_modulation('5MHz', 3.0)
        mock_driver.enable_iq_modulation.assert_called_with('5MHz', 3.0)
        assert result is True
        
        mock_driver.disable_iq_modulation.return_value = True
        result = device.disable_iq_modulation()
        mock_driver.disable_iq_modulation.assert_called_once()
        assert result is True
    
    def test_sequence_control(self, mock_awg_device):
        """Test sequence control methods."""
        device, mock_driver = mock_awg_device
        
        # Test run sequence
        device.run_sequence()
        mock_driver.run.assert_called_once()
        
        # Test stop sequence
        device.stop_sequence()
        mock_driver.stop.assert_called_once()
        
        # Test trigger
        device.trigger()
        mock_driver.trigger.assert_called_once()
    
    def test_read_probes(self, mock_awg_device):
        """Test probe reading functionality."""
        device, mock_driver = mock_awg_device
        
        # Test status probe
        mock_driver.send_command.return_value = '0'
        result = device.read_probes('status')
        mock_driver.send_command.assert_called_with('*STB?', query=True)
        assert result == '0'
        
        # Test unknown probe
        with pytest.raises(KeyError):
            device.read_probes('unknown')
    
    def test_cleanup(self, mock_awg_device):
        """Test cleanup method."""
        device, mock_driver = mock_awg_device
        
        # Mock QThread
        device._ftp_thread = Mock()
        device._ftp_thread.isRunning.return_value = False
        
        device.cleanup()
        
        mock_driver.cleanup.assert_called_once()


class TestFileTransferWorker:
    """Test suite for FileTransferWorker class."""
    
    def test_file_transfer_worker(self):
        """Test FileTransferWorker functionality."""
        mock_driver = Mock()
        mock_driver.upload_file.return_value = True
        
        worker = FileTransferWorker(mock_driver, 'local.txt', 'remote.txt')
        
        # Test run method
        worker.run()
        
        mock_driver.upload_file.assert_called_with('local.txt', 'remote.txt')
        # Note: Signal emission testing would require QApplication context


class TestAWG520FunctionGenerator:
    """Test suite for function generator and IQ modulation functionality."""
    
    @pytest.fixture
    def mock_awg_driver(self):
        """Create a mocked AWG520Driver instance for function generator tests."""
        with patch('Controller.awg520.FTP') as mock_ftp:
            mock_ftp_instance = Mock()
            mock_ftp.return_value = mock_ftp_instance
            mock_ftp_instance.connect.return_value = None
            mock_ftp_instance.login.return_value = None
            
            driver = AWG520Driver('192.168.1.100')
            driver.send_command = Mock()
            driver.set_ref_clock_external = Mock(return_value=None)
            
            return driver
    
    def test_mw_on_sb10MHz_single_channel(self, mock_awg_driver):
        """Test turning on MW with single channel 10MHz sine wave."""
        mock_awg_driver.send_command.return_value = True
        
        result = mock_awg_driver.mw_on_sb10MHz(enable_iq=False)
        
        # Verify external clock setup
        mock_awg_driver.set_ref_clock_external.assert_called_once()
        
        # Verify CH1 Marker 1 configuration
        mock_awg_driver.send_command.assert_any_call('SOUR1:MARK1:VOLT:LOW 2.0')
        
        # Verify function generator configuration for CH1 only
        expected_calls = [
            'AWGC:FG1:FUNC SIN',
            'AWGC:FG1:FREQ 10MHz',
            'AWGC:FG1:VOLT 2.0'
        ]
        
        for call in expected_calls:
            mock_awg_driver.send_command.assert_any_call(call)
        
        # Should not configure CH2
        ch2_calls = [call for call in mock_awg_driver.send_command.call_args_list 
                     if 'FG2' in str(call)]
        assert len(ch2_calls) == 0
        
        assert result is True
    
    def test_mw_on_sb10MHz_iq_modulation(self, mock_awg_driver):
        """Test turning on MW with IQ modulation (both channels)."""
        mock_awg_driver.send_command.return_value = True
        
        result = mock_awg_driver.mw_on_sb10MHz(enable_iq=True)
        
        # Verify external clock setup
        mock_awg_driver.set_ref_clock_external.assert_called_once()
        
        # Verify CH1 Marker 1 configuration
        mock_awg_driver.send_command.assert_any_call('SOUR1:MARK1:VOLT:LOW 2.0')
        
        # Verify function generator configuration for both channels
        expected_calls = [
            'AWGC:FG1:FUNC SIN',
            'AWGC:FG1:FREQ 10MHz',
            'AWGC:FG1:VOLT 2.0',
            'AWGC:FG2:FUNC SIN',
            'AWGC:FG2:FREQ 10MHz',
            'AWGC:FG2:PHAS 90DEG',
            'AWGC:FG2:VOLT 2.0'
        ]
        
        for call in expected_calls:
            mock_awg_driver.send_command.assert_any_call(call)
        
        assert result is True
    
    def test_mw_off_sb10MHz_single_channel(self, mock_awg_driver):
        """Test turning off MW with single channel."""
        mock_awg_driver.send_command.return_value = True
        
        result = mock_awg_driver.mw_off_sb10MHz(enable_iq=False)
        
        # Verify CH1 Marker 1 turn off
        mock_awg_driver.send_command.assert_any_call('SOUR1:MARK1:VOLT:HIGH 0.0')
        
        # Verify function generator turn off for CH1 only
        mock_awg_driver.send_command.assert_any_call('AWGC:FG1:VOLT 0.0')
        
        # Should not turn off CH2
        ch2_calls = [call for call in mock_awg_driver.send_command.call_args_list 
                     if 'FG2' in str(call)]
        assert len(ch2_calls) == 0
        
        assert result is True
    
    def test_mw_off_sb10MHz_iq_modulation(self, mock_awg_driver):
        """Test turning off MW with IQ modulation (both channels)."""
        mock_awg_driver.send_command.return_value = True
        
        result = mock_awg_driver.mw_off_sb10MHz(enable_iq=True)
        
        # Verify CH1 Marker 1 turn off
        mock_awg_driver.send_command.assert_any_call('SOUR1:MARK1:VOLT:HIGH 0.0')
        
        # Verify function generator turn off for both channels
        expected_calls = [
            'AWGC:FG1:VOLT 0.0',
            'AWGC:FG2:VOLT 0.0'
        ]
        
        for call in expected_calls:
            mock_awg_driver.send_command.assert_any_call(call)
        
        assert result is True
    
    def test_set_function_generator_valid_channel(self, mock_awg_driver):
        """Test setting function generator parameters for valid channels."""
        mock_awg_driver.send_command.return_value = True
        
        # Test CH1
        result = mock_awg_driver.set_function_generator(1, 'SIN', '5MHz', 3.0, 45.0, True)
        
        expected_calls = [
            'AWGC:FG1:FUNC SIN',
            'AWGC:FG1:FREQ 5MHz',
            'AWGC:FG1:PHAS 45.0DEG',
            'AWGC:FG1:VOLT 3.0'
        ]
        
        for call in expected_calls:
            mock_awg_driver.send_command.assert_any_call(call)
        
        assert result is True
        
        # Test CH2
        result = mock_awg_driver.set_function_generator(2, 'SQU', '1kHz', 1.5, 0.0, False)
        
        expected_calls = [
            'AWGC:FG2:FUNC SQU',
            'AWGC:FG2:FREQ 1kHz',
            'AWGC:FG2:VOLT 0.0'  # Should be 0.0 when enable=False
        ]
        
        for call in expected_calls:
            mock_awg_driver.send_command.assert_any_call(call)
        
        assert result is True
    
    def test_set_function_generator_invalid_channel(self, mock_awg_driver):
        """Test setting function generator parameters for invalid channels."""
        result = mock_awg_driver.set_function_generator(3, 'SIN', '10MHz', 2.0)
        assert result is False
        
        result = mock_awg_driver.set_function_generator(0, 'SIN', '10MHz', 2.0)
        assert result is False
    
    def test_get_function_generator_status_success(self, mock_awg_driver):
        """Test getting function generator status successfully."""
        mock_awg_driver.send_command.side_effect = ['SIN', '10MHz', '2.0', '0.0']
        
        status = mock_awg_driver.get_function_generator_status(1)
        
        assert status is not None
        assert status['function'] == 'SIN'
        assert status['frequency'] == '10MHz'
        assert status['voltage'] == 2.0
        assert status['phase'] == 0.0
        
        # Verify query commands were sent
        expected_calls = [
            'AWGC:FG1:FUNC?',
            'AWGC:FG1:FREQ?',
            'AWGC:FG1:VOLT?',
            'AWGC:FG1:PHAS?'
        ]
        
        for call in expected_calls:
            mock_awg_driver.send_command.assert_any_call(call, query=True)
    
    def test_get_function_generator_status_failure(self, mock_awg_driver):
        """Test getting function generator status when commands fail."""
        mock_awg_driver.send_command.return_value = None
        
        status = mock_awg_driver.get_function_generator_status(1)
        assert status is None
    
    def test_enable_iq_modulation(self, mock_awg_driver):
        """Test enabling I/Q modulation."""
        mock_awg_driver.set_function_generator = Mock(return_value=True)
        
        result = mock_awg_driver.enable_iq_modulation('5MHz', 3.0)
        
        # Verify both channels were configured
        mock_awg_driver.set_function_generator.assert_any_call(1, 'SIN', '5MHz', 3.0, 0.0, True)
        mock_awg_driver.set_function_generator.assert_any_call(2, 'SIN', '5MHz', 3.0, 90.0, True)
        
        assert result is True
    
    def test_disable_iq_modulation(self, mock_awg_driver):
        """Test disabling I/Q modulation."""
        mock_awg_driver.send_command.return_value = True
        
        result = mock_awg_driver.disable_iq_modulation()
        
        # Verify both channels were turned off
        mock_awg_driver.send_command.assert_any_call('AWGC:FG1:VOLT 0.0')
        mock_awg_driver.send_command.assert_any_call('AWGC:FG2:VOLT 0.0')
        
        assert result is True


@pytest.mark.hardware
class TestAWG520Hardware:
    """Hardware integration tests for AWG520 (requires real device)."""
    
    @pytest.fixture(scope="module")
    def awg520_hardware(self):
        """Fixture to create a real AWG520 connection."""
        # Hardware connection settings - modify these for your setup
        settings = {
            'ip_address': '172.17.39.2',  # Modify for your AWG520 IP
            'scpi_port': 4000,            # Default SCPI port
            'ftp_port': 21,               # Default FTP port
            'ftp_user': 'usr',            # Default username
            'ftp_pass': 'pw'              # Default password
        }
        
        # Quick connection check before creating full driver
        import socket
        try:
            # Test if we can reach the device at all (fast timeout)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1.0)  # 1 second timeout for quick check
            result = sock.connect_ex((settings['ip_address'], settings['scpi_port']))
            sock.close()
            
            if result != 0:
                pytest.skip(f"AWG520 not reachable at {settings['ip_address']}:{settings['scpi_port']}")
            
            # If reachable, try to create the driver
            driver = AWG520Driver(**settings)
            print(f"✓ Connected to AWG520 at {settings['ip_address']}")
            yield driver
        except Exception as e:
            pytest.skip(f"Could not connect to AWG520: {e}")
        finally:
            # Clean up connection
            if 'driver' in locals():
                driver.cleanup()
    
    def test_hardware_connection(self, awg520_hardware):
        """Test basic connection to AWG520."""
        # Test device identification
        idn = awg520_hardware.send_command('*IDN?', query=True)
        assert idn is not None
        assert 'TEKTRONIX' in idn.upper() or 'AWG' in idn.upper()
        print(f"Device ID: {idn}")
    
    def test_hardware_clock_configuration(self, awg520_hardware):
        """Test clock configuration with real hardware."""
        # Test external clock setting
        result = awg520_hardware.set_clock_external()
        assert result is None
        
        # Test internal clock setting
        result = awg520_hardware.set_clock_internal()
        assert result is None
        
        print("✓ Clock configuration test passed")
    
    def test_hardware_laser_control(self, awg520_hardware):
        """Test laser control functionality with real hardware."""
        # Test laser off
        result = awg520_hardware.set_ch1_marker2_laser_off()
        assert result is True
        
        # Verify laser is off
        time.sleep(0.1)
        is_on = awg520_hardware.is_ch1_marker2_laser_on()
        assert is_on is False
        
        # Test laser on
        result = awg520_hardware.set_ch1_marker2_laser_on()
        assert result is True
        
        # Verify laser is on
        time.sleep(0.1)
        is_on = awg520_hardware.is_ch1_marker2_laser_on()
        assert is_on is True
        
        # Test custom voltage
        result = awg520_hardware.set_ch1_marker2_voltage(3.3)
        assert result is True
        
        # Verify voltage was set
        time.sleep(0.1)
        low_v, high_v = awg520_hardware.get_ch1_marker2_voltage()
        assert low_v is not None
        assert high_v is not None
        assert abs(low_v - 3.3) < 0.1
        assert abs(high_v - 3.3) < 0.1
        
        # Turn laser off for safety
        awg520_hardware.set_ch1_marker2_laser_off()
        
        print("✓ Hardware laser control test passed")
    
    def test_hardware_file_operations(self, awg520_hardware):
        """Test file operations with real hardware."""
        # Test listing files
        files = awg520_hardware.list_files()
        assert isinstance(files, list)
        print(f"Available files: {files}")
        
        print("✓ Hardware file operations test passed")


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"]) 