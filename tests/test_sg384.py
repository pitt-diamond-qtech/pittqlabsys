import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add the src directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from Controller.sg384 import SG384Generator
from src.core import Parameter


class TestSG384Generator:
    """Test suite for SG384Generator with mocked microwave generator."""
    
    @pytest.fixture
    def mock_sg384(self):
        """Create a mocked SG384Generator instance."""
        with patch('Controller.mw_generator_base.pyvisa') as mock_pyvisa:
            # Mock the ResourceManager and resource
            mock_rm = Mock()
            mock_resource = Mock()
            mock_pyvisa.ResourceManager.return_value = mock_rm
            mock_rm.open_resource.return_value = mock_resource
            
            # Create SG384 instance with test settings
            settings = {
                'connection_type': 'GPIB',
                'visa_resource': 'GPIB0::20::INSTR',
                'frequency': 2.5e9,
                'power': -10.0,
                'phase': 0.0,
                'enable_output': True,
                'enable_modulation': True,
                'modulation_type': 'FM',
                'modulation_function': 'Sine',
                'pulse_modulation_function': 'Square',
                'dev_width': 1e6,
                'mod_rate': 1e7
            }
            
            sg384 = SG384Generator(settings=settings)
            
            # Mock the _query method to return expected responses
            sg384._query = Mock()
            sg384._send = Mock()
            
            return sg384
    
    def test_parameter_mappings(self, mock_sg384):
        """Test that parameter mappings work correctly."""
        # Test parameter to internal conversion
        assert mock_sg384._param_to_internal('frequency') == 'FREQ'
        assert mock_sg384._param_to_internal('amplitude') == 'AMPR'
        assert mock_sg384._param_to_internal('enable_output') == 'ENBR'
        assert mock_sg384._param_to_internal('modulation_type') == 'TYPE'
        
        # Test invalid parameter
        with pytest.raises(KeyError):
            mock_sg384._param_to_internal('invalid_param')
    
    def test_modulation_type_mappings(self, mock_sg384):
        """Test modulation type conversion mappings."""
        # Test string to internal conversion
        assert mock_sg384._mod_type_to_internal('AM') == 0
        assert mock_sg384._mod_type_to_internal('FM') == 1
        assert mock_sg384._mod_type_to_internal('PhaseM') == 2
        assert mock_sg384._mod_type_to_internal('Freq sweep') == 3
        assert mock_sg384._mod_type_to_internal('Pulse') == 4
        assert mock_sg384._mod_type_to_internal('Blank') == 5
        assert mock_sg384._mod_type_to_internal('IQ') == 6
        
        # Test internal to string conversion
        assert mock_sg384._internal_to_mod_type(0) == 'AM'
        assert mock_sg384._internal_to_mod_type(1) == 'FM'
        assert mock_sg384._internal_to_mod_type(2) == 'PhaseM'
        assert mock_sg384._internal_to_mod_type(3) == 'Freq sweep'
        assert mock_sg384._internal_to_mod_type(4) == 'Pulse'
        assert mock_sg384._internal_to_mod_type(5) == 'Blank'
        assert mock_sg384._internal_to_mod_type(6) == 'IQ'
        
        # Test invalid values
        with pytest.raises(KeyError):
            mock_sg384._mod_type_to_internal('Invalid')
        with pytest.raises(KeyError):
            mock_sg384._internal_to_mod_type(99)
    
    def test_modulation_function_mappings(self, mock_sg384):
        """Test modulation function conversion mappings."""
        # Test string to internal conversion
        assert mock_sg384._mod_func_to_internal('Sine') == 0
        assert mock_sg384._mod_func_to_internal('Ramp') == 1
        assert mock_sg384._mod_func_to_internal('Triangle') == 2
        assert mock_sg384._mod_func_to_internal('Square') == 3
        assert mock_sg384._mod_func_to_internal('Noise') == 4
        assert mock_sg384._mod_func_to_internal('External') == 5
        
        # Test internal to string conversion
        assert mock_sg384._internal_to_mod_func(0) == 'Sine'
        assert mock_sg384._internal_to_mod_func(1) == 'Ramp'
        assert mock_sg384._internal_to_mod_func(2) == 'Triangle'
        assert mock_sg384._internal_to_mod_func(3) == 'Square'
        assert mock_sg384._internal_to_mod_func(4) == 'Noise'
        assert mock_sg384._internal_to_mod_func(5) == 'External'
        
        # Test invalid values
        with pytest.raises(KeyError):
            mock_sg384._mod_func_to_internal('Invalid')
        with pytest.raises(KeyError):
            mock_sg384._internal_to_mod_func(99)
    
    def test_sweep_function_mappings(self, mock_sg384):
        """Test sweep function conversion mappings."""
        # Test string to internal conversion
        assert mock_sg384._sweep_func_to_internal('Sine') == 0
        assert mock_sg384._sweep_func_to_internal('Ramp') == 1
        assert mock_sg384._sweep_func_to_internal('Triangle') == 2
        assert mock_sg384._sweep_func_to_internal('Square') == 3
        assert mock_sg384._sweep_func_to_internal('Noise') == 4
        assert mock_sg384._sweep_func_to_internal('External') == 5
        
        # Test internal to string conversion
        assert mock_sg384._internal_to_sweep_func(0) == 'Sine'
        assert mock_sg384._internal_to_sweep_func(1) == 'Ramp'
        assert mock_sg384._internal_to_sweep_func(2) == 'Triangle'
        assert mock_sg384._internal_to_sweep_func(3) == 'Square'
        assert mock_sg384._internal_to_sweep_func(4) == 'Noise'
        assert mock_sg384._internal_to_sweep_func(5) == 'External'
        
        # Test invalid values
        with pytest.raises(KeyError):
            mock_sg384._sweep_func_to_internal('Invalid')
        with pytest.raises(KeyError):
            mock_sg384._internal_to_sweep_func(99)
    
    def test_pulse_modulation_function_mappings(self, mock_sg384):
        """Test pulse modulation function conversion mappings."""
        # Test string to internal conversion
        assert mock_sg384._pulse_mod_func_to_internal('Square') == 3
        assert mock_sg384._pulse_mod_func_to_internal('Noise(PRBS)') == 4
        assert mock_sg384._pulse_mod_func_to_internal('External') == 5
        
        # Test internal to string conversion
        assert mock_sg384._internal_to_pulse_mod_func(3) == 'Square'
        assert mock_sg384._internal_to_pulse_mod_func(4) == 'Noise(PRBS)'
        assert mock_sg384._internal_to_pulse_mod_func(5) == 'External'
    
    def test_dispatch_update(self, mock_sg384):
        """Test the dispatch update method with mapping dictionary."""
        # Mock the setter methods
        mock_sg384.set_frequency = Mock()
        mock_sg384.set_power = Mock()
        mock_sg384.set_phase = Mock()
        mock_sg384._set_output_enable = Mock()
        mock_sg384._set_modulation_enable = Mock()
        mock_sg384._set_modulation_type = Mock()
        mock_sg384._set_modulation_function = Mock()
        mock_sg384._set_pulse_modulation_function = Mock()
        mock_sg384._set_dev_width = Mock()
        mock_sg384._set_mod_rate = Mock()
        
        # Test update with various parameters
        test_settings = {
            'frequency': 3.0e9,
            'power': -5.0,
            'phase': 45.0,
            'enable_output': True,
            'enable_modulation': False,
            'modulation_type': 'AM',
            'modulation_function': 'Square',
            'pulse_modulation_function': 'External',
            'dev_width': 2e6,
            'mod_rate': 5e6
        }
        
        mock_sg384._dispatch_update(test_settings)
        
        # Verify that the correct methods were called with correct values
        mock_sg384.set_frequency.assert_called_once_with(3.0e9)
        mock_sg384.set_power.assert_called_once_with(-5.0)
        mock_sg384.set_phase.assert_called_once_with(45.0)
        mock_sg384._set_output_enable.assert_called_once_with(1)  # True -> 1
        mock_sg384._set_modulation_enable.assert_called_once_with(0)  # False -> 0
        mock_sg384._set_modulation_type.assert_called_once_with(0)  # 'AM' -> 0
        mock_sg384._set_modulation_function.assert_called_once_with(3)  # 'Square' -> 3
        mock_sg384._set_pulse_modulation_function.assert_called_once_with(5)  # 'External' -> 5
        mock_sg384._set_dev_width.assert_called_once_with(2e6)
        mock_sg384._set_mod_rate.assert_called_once_with(5e6)
    
    def test_read_probes_boolean(self, mock_sg384):
        """Test reading boolean probe values."""
        # Mock _query to return '1' for enabled, '0' for disabled
        mock_sg384._query.side_effect = lambda cmd: '1' if 'ENBR' in cmd else '0'
        
        # Test boolean probes
        assert mock_sg384.read_probes('enable_output') is True
        assert mock_sg384.read_probes('enable_modulation') is False
        
        # Verify the correct queries were made
        mock_sg384._query.assert_any_call('ENBR?')
        mock_sg384._query.assert_any_call('MODL?')
    
    def test_read_probes_modulation(self, mock_sg384):
        """Test reading modulation probe values."""
        # Mock _query to return different values for different probes
        def mock_query(cmd):
            if 'TYPE' in cmd:
                return '1'  # FM
            elif 'MFNC' in cmd:
                return '3'  # Square
            elif 'PFNC' in cmd:
                return '4'  # Noise(PRBS)
            else:
                return '0'
        
        mock_sg384._query.side_effect = mock_query
        
        # Test modulation probes
        assert mock_sg384.read_probes('modulation_type') == 'FM'
        assert mock_sg384.read_probes('modulation_function') == 'Square'
        assert mock_sg384.read_probes('pulse_modulation_function') == 'Noise(PRBS)'
    
    def test_read_probes_float(self, mock_sg384):
        """Test reading float probe values."""
        # Mock _query to return float values
        def mock_query(cmd):
            if 'FREQ' in cmd:
                return '2.5e9'
            elif 'AMPR' in cmd:
                return '-10.0'
            elif 'PHAS' in cmd:
                return '45.0'
            elif 'FDEV' in cmd:
                return '1e6'
            elif 'RATE' in cmd:
                return '1e7'
            else:
                return '0.0'
        
        mock_sg384._query.side_effect = mock_query
        
        # Test float probes
        assert mock_sg384.read_probes('frequency') == 2.5e9
        assert mock_sg384.read_probes('amplitude') == -10.0
        assert mock_sg384.read_probes('phase') == 45.0
        assert mock_sg384.read_probes('dev_width') == 1e6
        assert mock_sg384.read_probes('mod_rate') == 1e7
    
    def test_read_probes_invalid_key(self, mock_sg384):
        """Test that read_probes raises AssertionError for invalid keys."""
        with pytest.raises(AssertionError):
            mock_sg384.read_probes('invalid_probe')
    
    def test_is_connected(self, mock_sg384):
        """Test the is_connected property."""
        # Test when connected (query succeeds)
        mock_sg384._query.return_value = "Stanford Research Systems,SG384,12345,1.0"
        assert mock_sg384.is_connected is True
        
        # Test when not connected (query raises exception)
        mock_sg384._query.side_effect = Exception("Connection failed")
        assert mock_sg384.is_connected is False
    
    def test_close(self, mock_sg384):
        """Test the close method."""
        # Mock the _inst attribute
        mock_sg384._inst = Mock()
        
        # Test successful close
        result = mock_sg384.close()
        assert result is True
        mock_sg384._inst.close.assert_called_once()
        
        # Test close with exception
        mock_sg384._inst.close.side_effect = Exception("Close failed")
        result = mock_sg384.close()
        assert result is False
    
    def test_setter_methods(self, mock_sg384):
        """Test the individual setter methods."""
        # Test output enable setter
        mock_sg384._set_output_enable(1)
        mock_sg384._send.assert_called_with("ENBR 1")
        
        # Test modulation enable setter
        mock_sg384._set_modulation_enable(0)
        mock_sg384._send.assert_called_with("MODL 0")
        
        # Test modulation type setter
        mock_sg384._set_modulation_type(2)
        mock_sg384._send.assert_called_with("TYPE 2")
        
        # Test modulation function setter
        mock_sg384._set_modulation_function(4)
        mock_sg384._send.assert_called_with("MFNC 4")
        
        # Test pulse modulation function setter
        mock_sg384._set_pulse_modulation_function(3)
        mock_sg384._send.assert_called_with("PFNC 3")
        
        # Test deviation width setter
        mock_sg384._set_dev_width(5e6)
        mock_sg384._send.assert_called_with("FDEV 5000000.0")
        
        # Test modulation rate setter
        mock_sg384._set_mod_rate(2e7)
        mock_sg384._send.assert_called_with("RATE 20000000.0")
        
        # Test sweep function setter
        mock_sg384._set_sweep_function(2)
        mock_sg384._send.assert_called_with("SFNC 2")
        
        # Test sweep rate setter
        mock_sg384._set_sweep_rate(10.0)
        mock_sg384._send.assert_called_with("SRAT 10.0")
        
        # Test sweep rate validation (should raise error for rate >= 120 Hz)
        with pytest.raises(ValueError, match="less than 120 Hz"):
            mock_sg384._set_sweep_rate(150.0)
        
        # Test sweep deviation setter
        mock_sg384._set_sweep_deviation(1e6)
        mock_sg384._send.assert_called_with("SDEV 1000000.0")
    
    def test_update_method(self, mock_sg384):
        """Test the update method integration."""
        # Mock the dispatch_update method
        mock_sg384._dispatch_update = Mock()
        mock_sg384._inst = Mock()  # Simulate connected state
        
        test_settings = {'frequency': 3.0e9, 'power': -5.0}
        mock_sg384.update(test_settings)
        
        # Verify that dispatch_update was called
        mock_sg384._dispatch_update.assert_called_once_with(test_settings)
    
    def test_probes_property(self, mock_sg384):
        """Test the _PROBES property."""
        probes = mock_sg384._PROBES
        
        # Check that all expected probes are present
        expected_probes = [
            'enable_output', 'frequency', 'amplitude', 'phase',
            'enable_modulation', 'modulation_type', 'modulation_function',
            'pulse_modulation_function', 'dev_width', 'mod_rate',
            'sweep_function', 'sweep_rate', 'sweep_deviation'
        ]
        
        for probe in expected_probes:
            assert probe in probes
            assert isinstance(probes[probe], str)  # All descriptions should be strings
    
    def test_validate_sweep_parameters_valid(self, mock_sg384):
        """Test sweep parameter validation with valid parameters."""
        # Test valid parameters
        center_freq = 2.87e9  # 2.87 GHz
        deviation = 50e6      # 50 MHz
        sweep_rate = 1.0      # 1 Hz
        
        # Should not raise any exception
        result = mock_sg384.validate_sweep_parameters(center_freq, deviation, sweep_rate)
        assert result is True
    
    def test_validate_sweep_parameters_frequency_too_low(self, mock_sg384):
        """Test sweep parameter validation with frequency too low."""
        center_freq = 1.0e9   # 1 GHz
        deviation = 1e9       # 1 GHz deviation
        sweep_rate = 1.0      # 1 Hz
        
        # This should fail: center_freq - deviation = 0 GHz < 1.9 GHz
        with pytest.raises(ValueError, match="below minimum"):
            mock_sg384.validate_sweep_parameters(center_freq, deviation, sweep_rate)
    
    def test_validate_sweep_parameters_frequency_too_high(self, mock_sg384):
        """Test sweep parameter validation with frequency too high."""
        center_freq = 5.0e9   # 5 GHz
        deviation = 1e9       # 1 GHz deviation
        sweep_rate = 1.0      # 1 Hz
        
        # This should fail: center_freq + deviation = 6 GHz > 4.1 GHz
        with pytest.raises(ValueError, match="above maximum"):
            mock_sg384.validate_sweep_parameters(center_freq, deviation, sweep_rate)
    
    def test_validate_sweep_parameters_rate_too_high(self, mock_sg384):
        """Test sweep parameter validation with sweep rate too high."""
        center_freq = 2.87e9  # 2.87 GHz
        deviation = 50e6      # 50 MHz
        sweep_rate = 150.0    # 150 Hz (too high)
        
        # This should fail: sweep_rate >= 120 Hz
        with pytest.raises(ValueError, match="less than 120 Hz"):
            mock_sg384.validate_sweep_parameters(center_freq, deviation, sweep_rate)
    
    def test_validate_sweep_parameters_no_rate(self, mock_sg384):
        """Test sweep parameter validation without sweep rate."""
        center_freq = 2.87e9  # 2.87 GHz
        deviation = 50e6      # 50 MHz
        
        # Should not raise any exception (sweep_rate is None)
        result = mock_sg384.validate_sweep_parameters(center_freq, deviation)
        assert result is True


if __name__ == '__main__':
    pytest.main([__file__, '-v']) 