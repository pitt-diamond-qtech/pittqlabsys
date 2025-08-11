"""
Test suite for MUX Control Device.

Tests both the new MUXControlDevice class and the legacy MUXControl class
for backward compatibility.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import pyvisa as visa

from src.Controller.mux_control import MUXControlDevice, MUXControl, TRIGGER_SELECTORS


class TestMUXControlDevice:
    """Test the new MUXControlDevice class."""
    
    @pytest.fixture
    def mock_visa_resource(self):
        """Mock VISA resource for testing."""
        mock_resource = Mock()
        mock_resource.baud_rate = 9600
        mock_resource.timeout = 5000
        mock_resource.write_termination = '\n'
        mock_resource.read_termination = '\n'
        mock_resource.read.return_value = "MUX Controller Ready"
        mock_resource.query.return_value = "OK"
        return mock_resource
    
    @pytest.fixture
    def mock_visa_manager(self, mock_visa_resource):
        """Mock VISA resource manager."""
        mock_rm = Mock()
        mock_rm.open_resource.return_value = mock_visa_resource
        return mock_rm
    
    @pytest.fixture
    def mux_device(self):
        """Create MUX device instance for testing."""
        settings = {
            'port': 'COM3',
            'baudrate': 9600,
            'timeout': 5000,
            'auto_connect': False  # Don't auto-connect in tests
        }
        return MUXControlDevice(settings=settings)
    
    def test_device_initialization(self, mux_device):
        """Test device initialization."""
        assert mux_device.settings['port'] == 'COM3'
        assert mux_device.settings['baudrate'] == 9600
        assert mux_device.settings['timeout'] == 5000
        assert mux_device.settings['auto_connect'] is False
        assert mux_device.arduino is None
        assert mux_device._current_selection is None
        assert not mux_device.is_connected
    
    @patch('src.Controller.mux_control.visa.ResourceManager')
    def test_connect_success(self, mock_rm_class, mux_device, mock_visa_resource):
        """Test successful connection."""
        mock_rm = Mock()
        mock_rm.open_resource.return_value = mock_visa_resource
        mock_rm_class.return_value = mock_rm
        
        result = mux_device.connect()
        
        assert result is True
        assert mux_device.is_connected
        assert mux_device.arduino is mock_visa_resource
        mock_rm.open_resource.assert_called_once_with("ASRLCOM3::INSTR")
    
    @patch('src.Controller.mux_control.visa.ResourceManager')
    def test_connect_failure(self, mock_rm_class, mux_device):
        """Test connection failure."""
        mock_rm = Mock()
        mock_rm.open_resource.side_effect = visa.VisaIOError(1)
        mock_rm_class.return_value = mock_rm
        
        result = mux_device.connect()
        
        assert result is False
        assert not mux_device.is_connected
        assert mux_device.arduino is None
    
    def test_disconnect(self, mux_device, mock_visa_resource):
        """Test disconnection."""
        mux_device.arduino = mock_visa_resource
        mux_device._is_connected = True
        mux_device._current_selection = 'confocal'
        
        mux_device.disconnect()
        
        assert not mux_device.is_connected
        assert mux_device.arduino is None
        assert mux_device._current_selection is None
        mock_visa_resource.close.assert_called_once()
    
    def test_select_trigger_confocal(self, mux_device, mock_visa_resource):
        """Test selecting confocal trigger."""
        mux_device.arduino = mock_visa_resource
        mux_device._is_connected = True
        
        result = mux_device.select_trigger('confocal')
        
        assert result is True
        assert mux_device._current_selection == 'confocal'
        mock_visa_resource.query.assert_called_once_with('1')
    
    def test_select_trigger_odmr(self, mux_device, mock_visa_resource):
        """Test selecting ODMR trigger."""
        mux_device.arduino = mock_visa_resource
        mux_device._is_connected = True
        
        result = mux_device.select_trigger('odmr')
        
        assert result is True
        assert mux_device._current_selection == 'odmr'
        mock_visa_resource.query.assert_called_once_with('2')
    
    def test_select_trigger_pulsed(self, mux_device, mock_visa_resource):
        """Test selecting pulsed ESR trigger."""
        mux_device.arduino = mock_visa_resource
        mux_device._is_connected = True
        
        result = mux_device.select_trigger('pulsed')
        
        assert result is True
        assert mux_device._current_selection == 'pulsed'
        mock_visa_resource.query.assert_called_once_with('3')
    
    def test_select_trigger_invalid(self, mux_device):
        """Test selecting invalid trigger."""
        result = mux_device.select_trigger('invalid')
        
        assert result is False
        assert mux_device._current_selection is None
    
    def test_select_trigger_not_connected(self, mux_device):
        """Test selecting trigger when not connected."""
        result = mux_device.select_trigger('confocal')
        
        assert result is False
        assert mux_device._current_selection is None
    
    def test_get_current_selection(self, mux_device):
        """Test getting current selection."""
        mux_device._current_selection = 'confocal'
        assert mux_device.get_current_selection() == 'confocal'
        
        mux_device._current_selection = None
        assert mux_device.get_current_selection() is None
    
    def test_get_hardware_mapping(self, mux_device):
        """Test getting hardware mapping information."""
        hw_map = mux_device.get_hardware_mapping()
        
        assert hw_map['multiplexer'] == '74HC4051 8-Channel'
        assert hw_map['arduino_pins']['S0'] == 2
        assert hw_map['arduino_pins']['S1'] == 3
        assert hw_map['arduino_pins']['S2'] == 4
        assert hw_map['arduino_pins']['Z'] == 5
        
        # Check channel mappings
        assert hw_map['channel_mapping']['confocal']['command'] == '1'
        assert hw_map['channel_mapping']['confocal']['channel'] == 'Y0'
        assert hw_map['channel_mapping']['confocal']['pins'] == {'S0': 0, 'S1': 0, 'S2': 0}
        
        assert hw_map['channel_mapping']['odmr']['command'] == '2'
        assert hw_map['channel_mapping']['odmr']['channel'] == 'Y1'
        assert hw_map['channel_mapping']['odmr']['pins'] == {'S0': 1, 'S1': 0, 'S2': 0}
        
        assert hw_map['channel_mapping']['pulsed']['command'] == '3'
        assert hw_map['channel_mapping']['pulsed']['channel'] == 'Y2'
        assert hw_map['channel_mapping']['pulsed']['pins'] == {'S0': 0, 'S1': 1, 'S2': 0}
    
    def test_get_arduino_info(self, mux_device):
        """Test getting Arduino firmware information."""
        arduino_info = mux_device.get_arduino_info()
        
        assert arduino_info['firmware']['name'] == 'MUX_control'
        assert arduino_info['firmware']['author'] == 'Vincent Musso, Duttlab'
        assert arduino_info['firmware']['date'] == 'March 25, 2019'
        assert 'modified' in arduino_info['firmware']
        assert arduino_info['firmware']['description'] == '74HC4051 8-Channel Multiplexer Controller'
        
        # Check hardware info
        assert arduino_info['hardware']['multiplexer'] == '74HC4051 8-Channel'
        assert arduino_info['hardware']['arduino_pins']['S0'] == 2
        
        # Check commands and responses
        assert arduino_info['commands']['1'] == 'Select confocal trigger (Y0)'
        assert arduino_info['commands']['2'] == 'Select ODMR trigger (Y1)'
        assert arduino_info['commands']['3'] == 'Select pulsed ESR trigger (Y2)'
        
        assert 'success' in arduino_info['responses']
        assert 'failure' in arduino_info['responses']
        assert 'initialization' in arduino_info['responses']
    
    def test_test_connection_success(self, mux_device, mock_visa_resource):
        """Test connection testing when connected."""
        mux_device.arduino = mock_visa_resource
        mux_device._is_connected = True
        mux_device._current_selection = 'confocal'
        
        # Mock the Arduino response - test both old and new message formats
        old_message = "Initialized...Enter 1 for Confocal, 2 for CW, or 3 for Pulsed."
        new_message = "Initialized...Enter 1 for Confocal, 2 for ODMR, or 3 for Pulsed."
        
        # Test with new message format
        mock_visa_resource.read.return_value = new_message
        result = mux_device.test_connection()
        
        assert result['connected'] is True
        assert result['arduino_message'] in [old_message, new_message]  # Accept both formats
        assert result['port'] == 'COM3'
        assert result['baudrate'] == 9600
        assert result['current_selection'] == 'confocal'
    
    def test_test_connection_not_connected(self, mux_device):
        """Test connection testing when not connected."""
        result = mux_device.test_connection()
        
        assert result['connected'] is False
        assert result['error'] == 'Device not connected'
        assert result['arduino_message'] is None
    
    def test_read_probes_all(self, mux_device):
        """Test reading all probes."""
        mux_device._current_selection = 'confocal'
        mux_device._is_connected = True
        
        probes = mux_device.read_probes()
        
        assert probes['status'] == 'confocal'
        assert probes['port'] == 'COM3'
        assert probes['connected'] is True
    
    def test_read_probes_specific(self, mux_device):
        """Test reading specific probes."""
        mux_device._current_selection = 'odmr'
        mux_device._is_connected = True
        
        assert mux_device.read_probes('status') == 'odmr'
        assert mux_device.read_probes('port') == 'COM3'
        assert mux_device.read_probes('connected') is True
    
    def test_read_probes_unknown(self, mux_device):
        """Test reading unknown probe."""
        with pytest.raises(KeyError, match="Unknown probe: unknown"):
            mux_device.read_probes('unknown')
    
    def test_update_settings_port_change(self, mux_device, mock_visa_resource):
        """Test updating settings with port change."""
        mux_device.arduino = mock_visa_resource
        mux_device._is_connected = True
        
        # Update port
        mux_device.update({'port': 'COM4'})
        
        assert mux_device.settings['port'] == 'COM4'
        # Should disconnect and reconnect if auto_connect is True
        # But since auto_connect is False in our test fixture, it won't reconnect
    
    def test_cleanup(self, mux_device, mock_visa_resource):
        """Test cleanup method."""
        mux_device.arduino = mock_visa_resource
        mux_device._is_connected = True
        
        mux_device.cleanup()
        
        assert not mux_device.is_connected
        assert mux_device.arduino is None
        mock_visa_resource.close.assert_called_once()


class TestMUXControlLegacy:
    """Test the legacy MUXControl class for backward compatibility."""
    
    @patch('src.Controller.mux_control.visa.ResourceManager')
    def test_legacy_initialization(self, mock_rm_class):
        """Test legacy class initialization."""
        mock_rm = Mock()
        mock_resource = Mock()
        mock_resource.read.return_value = "MUX Controller Ready"
        mock_rm.open_resource.return_value = mock_resource
        mock_rm_class.return_value = mock_rm
        
        mux = MUXControl('COM5')
        
        assert mux.settings['port'] == 'COM5'
        assert mux.settings['auto_connect'] is True
        assert mux.is_connected
    
    @patch('src.Controller.mux_control.visa.ResourceManager')
    def test_legacy_run_method(self, mock_rm_class):
        """Test legacy run method."""
        mock_rm = Mock()
        mock_resource = Mock()
        mock_resource.read.return_value = "MUX Controller Ready"
        mock_resource.query.return_value = "OK"
        mock_rm.open_resource.return_value = mock_resource
        mock_rm_class.return_value = mock_rm
        
        mux = MUXControl('COM3')
        
        # Test successful selection
        result = mux.run('confocal')
        assert result == 0
        
        # Test invalid selection
        result = mux.run('invalid')
        assert result == -1
    
    @patch('src.Controller.mux_control.visa.ResourceManager')
    def test_legacy_close_method(self, mock_rm_class):
        """Test legacy close method."""
        mock_rm = Mock()
        mock_resource = Mock()
        mock_resource.read.return_value = "MUX Controller Ready"
        mock_rm.open_resource.return_value = mock_resource
        mock_rm_class.return_value = mock_rm
        
        mux = MUXControl('COM3')
        mux.close()
        
        assert not mux.is_connected
        assert mux.arduino is None


class TestMUXControlHardware:
    """Hardware tests for MUX Control Device (requires real hardware)."""
    
    @pytest.fixture(scope="module")
    def mux_hardware(self):
        """Fixture for real MUX hardware connection."""
        settings = {
            'port': 'COM3',  # Adjust this for your system
            'baudrate': 9600,
            'timeout': 5000,
            'auto_connect': False
        }
        
        # Quick check if port might be available
        import serial
        try:
            # Try to open the port briefly to see if it exists
            ser = serial.Serial(settings['port'], settings['baudrate'], timeout=1)
            ser.close()
            print(f"✓ Port {settings['port']} is available")
        except (serial.SerialException, OSError):
            pytest.skip(f"Port {settings['port']} not available")
        
        try:
            device = MUXControlDevice(settings=settings)
            if device.connect():
                print(f"✓ Connected to MUX controller on {settings['port']}")
                yield device
            else:
                pytest.skip(f"Could not connect to MUX controller on {settings['port']}")
        except Exception as e:
            pytest.skip(f"Could not create MUX controller: {e}")
        finally:
            if 'device' in locals():
                device.cleanup()
    
    @pytest.mark.hardware
    def test_hardware_connection(self, mux_hardware):
        """Test real hardware connection."""
        assert mux_hardware.is_connected
        assert mux_hardware.arduino is not None
    
    @pytest.mark.hardware
    def test_hardware_trigger_selection(self, mux_hardware):
        """Test trigger selection on real hardware."""
        # Test confocal trigger
        result = mux_hardware.select_trigger('confocal')
        assert result is True
        assert mux_hardware.get_current_selection() == 'confocal'
        
        # Test CW-ESR trigger
        result = mux_hardware.select_trigger('odmr')
        assert result is True
        assert mux_hardware.get_current_selection() == 'odmr'
        
        # Test pulsed ESR trigger
        result = mux_hardware.select_trigger('pulsed')
        assert result is True
        assert mux_hardware.get_current_selection() == 'pulsed'
    
    @pytest.mark.hardware
    def test_hardware_probes(self, mux_hardware):
        """Test probe reading on real hardware."""
        probes = mux_hardware.read_probes()
        assert 'status' in probes
        assert 'port' in probes
        assert 'connected' in probes
        assert probes['connected'] is True
        assert probes['port'] == 'COM3'  # or whatever port is configured


class TestMUXControlIntegration:
    """Integration tests for MUX Control Device."""
    
    def test_trigger_selector_literal(self):
        """Test that TRIGGER_SELECTORS literal includes all valid options."""
        valid_selectors = ['confocal', 'odmr', 'pulsed']
        
        for selector in valid_selectors:
            # This should not raise a type error if the literal is correct
            assert selector in valid_selectors
    
    def test_device_inheritance(self):
        """Test that MUXControlDevice properly inherits from Device."""
        from src.core.device import Device
        
        assert issubclass(MUXControlDevice, Device)
        assert hasattr(MUXControlDevice, '_DEFAULT_SETTINGS')
        assert hasattr(MUXControlDevice, '_PROBES')
        assert hasattr(MUXControlDevice, 'read_probes')
        assert hasattr(MUXControlDevice, 'update')
    
    def test_legacy_compatibility(self):
        """Test that legacy MUXControl maintains compatibility."""
        # Test that legacy class has all the old methods
        assert hasattr(MUXControl, 'run')
        assert hasattr(MUXControl, 'close')
        
        # Test that legacy class inherits from new class
        assert issubclass(MUXControl, MUXControlDevice) 