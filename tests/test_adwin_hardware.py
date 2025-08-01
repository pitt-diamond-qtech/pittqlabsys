"""
ADwin Hardware Integration Tests

This module provides tests for ADwin hardware integration that can run with either:
1. Mock ADwin (default) - for testing without hardware
2. Real ADwin hardware - when hardware is available

Usage:
    # Run with mock (default)
    pytest tests/test_adwin_hardware.py
    
    # Run with real hardware
    pytest tests/test_adwin_hardware.py -m hardware
    
    # Skip hardware tests
    pytest tests/test_adwin_hardware.py -m "not hardware"
"""

from src.Controller.adwin import ADwinGold
from src.core.adwin_helpers import get_adwin_binary_path, get_adwin_process_config
import pytest
import os
from unittest.mock import Mock, patch
from time import sleep

# Environment variable to control hardware testing
USE_REAL_HARDWARE = os.getenv('ADWIN_USE_REAL_HARDWARE', 'false').lower() == 'true'


@pytest.fixture
def adwin_instance():
    """
    ADwin fixture that provides either mock or real hardware based on configuration.
    """
    if USE_REAL_HARDWARE:
        # Use real hardware
        try:
            adwin = ADwinGold()
            if not adwin.is_connected:
                pytest.skip("ADwin hardware not connected")
            yield adwin
            adwin.close()
        except Exception as e:
            pytest.skip(f"ADwin hardware not available: {e}")
    else:
        # Use mock hardware
        with patch('src.Controller.adwin.ADwin') as mock_adwin_class:
            mock_adw = Mock()
            mock_adwin_class.return_value = mock_adw
            
            # Set up mock properties and methods
            mock_adw.ADwindir = '/mock/adwin/dir/'
            mock_adw.Boot = Mock()
            mock_adw.Test_Version = Mock(return_value="Mock ADwin v1.0")
            
            # Mock process control methods
            mock_adw.Load_Process = Mock()
            mock_adw.Clear_Process = Mock()
            mock_adw.Start_Process = Mock()
            mock_adw.Stop_Process = Mock()
            mock_adw.Set_Processdelay = Mock()
            mock_adw.Get_Processdelay = Mock(return_value=3000)
            mock_adw.Process_Status = Mock(return_value=0)
            
            # Mock variable setting/getting methods
            mock_adw.Set_Par = Mock()
            mock_adw.Set_FPar = Mock()
            mock_adw.Get_Par = Mock(return_value=0)
            mock_adw.Get_FPar = Mock(return_value=0.0)
            mock_adw.Get_FPar_Double = Mock(return_value=0.0)
            
            # Mock array methods
            mock_adw.Data_Length = Mock(return_value=5)
            mock_adw.GetData_Long = Mock(return_value=[1, 2, 3, 4, 5])
            mock_adw.GetData_Float = Mock(return_value=[1.0, 2.0, 3.0, 4.0, 5.0])
            mock_adw.GetData_Double = Mock(return_value=[1.0, 2.0, 3.0, 4.0, 5.0])
            mock_adw.GetData_String = Mock(return_value=b'Hello')
            mock_adw.String_Length = Mock(return_value=5)
            
            # Mock FIFO methods
            mock_adw.GetFifo_Long = Mock(return_value=[1, 2, 3])
            mock_adw.GetFifo_Float = Mock(return_value=[1.0, 2.0, 3.0])
            mock_adw.GetFifo_Double = Mock(return_value=[1.0, 2.0, 3.0])
            mock_adw.Fifo_Empty = Mock(return_value=True)
            mock_adw.Fifo_Full = Mock(return_value=0)
            
            # Mock other methods
            mock_adw.Get_Par_All = Mock(return_value=[0] * 80)
            mock_adw.Get_FPar_All = Mock(return_value=[0.0] * 80)
            mock_adw.Get_FPar_All_Double = Mock(return_value=[0.0] * 80)
            mock_adw.Get_Error_Text = Mock(return_value="No error")
            mock_adw.Get_Last_Error = Mock(return_value=0)
            mock_adw.Workload = Mock(return_value=25.5)
            
            adwin = ADwinGold(boot=False)
            yield adwin
            
            # Clean up
            try:
                adwin.close()
            except:
                pass


@pytest.mark.hardware
def test_adwin_connection(adwin_instance):
    """
    Test ADwin connection and basic functionality.
    """
    assert adwin_instance.is_connected
    
    if USE_REAL_HARDWARE:
        print("Testing with real ADwin hardware")
    else:
        print("Testing with mock ADwin")


@pytest.mark.hardware
def test_adwin_process_loading(adwin_instance):
    """
    Test loading processes with ADwin.
    """
    # Set up mock responses if using mock
    if not USE_REAL_HARDWARE:
        adwin_instance.adw.Get_Processdelay.return_value = 3000
        adwin_instance.adw.Process_Status.return_value = 0
    
    # Test loading a binary file
    binary_path = get_adwin_binary_path('Test_Adbasic.TB4')
    adwin_instance.update({'process_1': {'load': str(binary_path), 'delay': 3000}})
    
    # Verify the process was loaded
    delay = adwin_instance.read_probes('process_delay', id=1)
    assert delay == 3000
    
    # Clean up
    adwin_instance.update({'process_1': {'load': ''}})


@pytest.mark.hardware
def test_adwin_process_control(adwin_instance):
    """
    Test starting and stopping processes.
    """
    # Set up mock responses if using mock
    if not USE_REAL_HARDWARE:
        adwin_instance.adw.Process_Status.side_effect = [0, 1, 0]  # Not running, Running, Not running
    
    # Load a process
    binary_path = get_adwin_binary_path('Test_Adbasic.TB4')
    adwin_instance.update({'process_2': {'load': str(binary_path), 'delay': 3000}})
    
    # Check initial status
    status1 = adwin_instance.read_probes('process_status', id=2)
    assert status1 == 'Not running'
    
    # Start the process
    adwin_instance.update({'process_2': {'running': True}})
    sleep(0.1)
    status2 = adwin_instance.read_probes('process_status', id=2)
    assert status2 == 'Running'
    
    # Stop the process
    adwin_instance.update({'process_2': {'running': False}})
    sleep(0.1)
    status3 = adwin_instance.read_probes('process_status', id=2)
    assert status3 == 'Not running'
    
    # Clean up
    adwin_instance.update({'process_2': {'load': ''}})


@pytest.mark.hardware
def test_adwin_variable_operations(adwin_instance):
    """
    Test setting and reading variables.
    """
    # Set up mock responses if using mock
    if not USE_REAL_HARDWARE:
        adwin_instance.adw.Get_Par.return_value = 12345
        adwin_instance.adw.Get_FPar.return_value = 67.89
    
    # Test integer variables
    adwin_instance.set_int_var(Par_id=10, value=12345)
    value = adwin_instance.read_probes('int_var', id=10)
    assert value == 12345
    
    # Test float variables
    adwin_instance.set_float_var(FPar_id=10, value=67.89)
    value = adwin_instance.read_probes('float_var', id=10)
    assert abs(value - 67.89) < 0.01


@pytest.mark.hardware
def test_adwin_array_operations(adwin_instance):
    """
    Test reading arrays from ADwin.
    """
    # Set up mock responses if using mock
    if not USE_REAL_HARDWARE:
        adwin_instance.adw.Data_Length.return_value = 5
        adwin_instance.adw.GetData_Long.return_value = [1, 2, 3, 4, 5]
        adwin_instance.adw.GetData_String.return_value = b'Hello'
        adwin_instance.adw.String_Length.return_value = 5
    
    # Test integer array
    length = adwin_instance.read_probes('array_length', id=1)
    assert length == 5
    
    data = adwin_instance.read_probes('int_array', id=1, length=length)
    assert len(data) == 5
    assert data == [1, 2, 3, 4, 5]
    
    # Test string array
    str_length = adwin_instance.read_probes('str_length', id=1)
    str_data = adwin_instance.read_probes('str_array', id=1, length=str_length)
    assert str_data.decode('utf-8') == 'Hello'


@pytest.mark.hardware
def test_adwin_helpers_integration(adwin_instance):
    """
    Test integration with adwin_helpers module.
    """
    # Set up mock responses if using mock
    if not USE_REAL_HARDWARE:
        adwin_instance.adw.Get_Processdelay.return_value = 5000
        adwin_instance.adw.Process_Status.return_value = 0
    
    # Test using get_adwin_process_config helper
    process_config = get_adwin_process_config(
        process_number=3,
        binary_file='Test_Adbasic.TB4',
        delay=5000,
        auto_start=False
    )
    
    # Apply the configuration
    adwin_instance.update(process_config)
    
    # Verify the process was loaded correctly
    delay = adwin_instance.read_probes('process_delay', id=3)
    assert delay == 5000
    
    status = adwin_instance.read_probes('process_status', id=3)
    assert status == 'Not running'
    
    # Clean up
    adwin_instance.update({'process_3': {'load': ''}})


@pytest.mark.hardware
def test_adwin_error_handling(adwin_instance):
    """
    Test error handling in ADwin operations.
    """
    # Test invalid parameter ID
    with pytest.raises(KeyError):
        adwin_instance.set_int_var(Par_id=100, value=123)  # Invalid ID
    
    with pytest.raises(KeyError):
        adwin_instance.set_float_var(FPar_id=100, value=123.45)  # Invalid ID
    
    # Test invalid probe key
    with pytest.raises(AssertionError):
        adwin_instance.read_probes('invalid_probe', id=1)


@pytest.mark.hardware
def test_adwin_cleanup(adwin_instance):
    """
    Test proper cleanup of ADwin resources.
    """
    # Set up mock responses if using mock
    if not USE_REAL_HARDWARE:
        adwin_instance.adw.Get_Processdelay.return_value = 3000
    
    # Load multiple processes
    binary_path = get_adwin_binary_path('Test_Adbasic.TB4')
    adwin_instance.update({
        'process_1': {'load': str(binary_path), 'delay': 3000},
        'process_2': {'load': str(binary_path), 'delay': 3000}
    })
    
    # Verify processes are loaded
    delay1 = adwin_instance.read_probes('process_delay', id=1)
    delay2 = adwin_instance.read_probes('process_delay', id=2)
    assert delay1 == 3000
    assert delay2 == 3000
    
    # Clean up should work without errors
    adwin_instance.close()
    
    print("ADwin cleanup completed successfully")


if __name__ == "__main__":
    # Allow running tests directly with hardware flag
    import sys
    
    if "--real-hardware" in sys.argv:
        os.environ['ADWIN_USE_REAL_HARDWARE'] = 'true'
        print("Running tests with real ADwin hardware")
    else:
        print("Running tests with mock ADwin (use --real-hardware for real hardware)")
    
    pytest.main([__file__, "-v"]) 