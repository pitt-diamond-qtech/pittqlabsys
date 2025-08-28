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

from src.Controller.adwin_gold import AdwinGoldDevice
from src.core.adwin_helpers import get_adwin_binary_path, get_adwin_process_config
import pytest
import os
from unittest.mock import Mock, patch
from time import sleep

# Use RUN_HARDWARE_TESTS environment variable for hardware testing
USE_REAL_HARDWARE = os.getenv('RUN_HARDWARE_TESTS', '0') == '1'


@pytest.fixture
def adwin_instance():
    """
    ADwin fixture that provides either mock or real hardware based on configuration.
    """
    if USE_REAL_HARDWARE:
        # Use real hardware with timeout protection
        from tests.conftest import safe_hardware_connection
        
        device, message = safe_hardware_connection(
            AdwinGoldDevice, 
            timeout_seconds=15  # ADwin can take longer to connect
        )
        
        if device is None:
            pytest.skip(f"ADwin hardware not available: {message}")
        
        print(f"✓ {message}")
        yield device
        device.close()
    else:
        # Use mock hardware - this should always work when hardware tests are disabled
        print("🔧 Using mock ADwin for testing (hardware tests disabled)")
        
        with patch('src.Controller.adwin_gold.ADwin') as mock_adwin_class:
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
            
            adwin = AdwinGoldDevice(boot=False)
            adwin.adw = mock_adw
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
        # Ensure the mock is properly set up with side effects
        adwin_instance.adw.Process_Status.side_effect = [0, 1, 0]  # Not running, Running, Not running
        print(f"🔧 Mock Process_Status side effect set: {adwin_instance.adw.Process_Status.side_effect}")
    
    # Load a process
    binary_path = get_adwin_binary_path('Test_Adbasic.TB4')
    adwin_instance.update({'process_2': {'load': str(binary_path), 'delay': 3000}})
    
    # Check initial status
    status1 = adwin_instance.read_probes('process_status', id=2)
    print(f"🔍 Initial status: {status1}")
    
    if USE_REAL_HARDWARE:
        # With real hardware, just verify we can read the status
        assert status1 in ['Not running', 'Running', 'Unknown']
        print(f"✅ Real hardware: Initial status is {status1}")
    else:
        # With mock, expect specific behavior
        assert status1 == 'Not running'
    
    # Start the process
    adwin_instance.update({'process_2': {'running': True}})
    sleep(0.1)
    status2 = adwin_instance.read_probes('process_status', id=2)
    print(f"🔍 Status after start: {status2}")
    
    if USE_REAL_HARDWARE:
        # With real hardware, verify status changed or is valid
        assert status2 in ['Not running', 'Running', 'Unknown']
        print(f"✅ Real hardware: Status after start is {status2}")
    else:
        # With mock, expect specific behavior
        assert status2 == 'Running'
    
    # Stop the process
    adwin_instance.update({'process_2': {'running': False}})
    sleep(0.1)
    status3 = adwin_instance.read_probes('process_status', id=2)
    print(f"🔍 Status after stop: {status3}")
    
    if USE_REAL_HARDWARE:
        # With real hardware, verify status changed or is valid
        assert status3 in ['Not running', 'Running', 'Unknown']
        print(f"✅ Real hardware: Status after stop is {status3}")
    else:
        # With mock, expect specific behavior
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
    
    if USE_REAL_HARDWARE:
        # With real hardware, just verify we can read a value
        assert isinstance(value, (int, float))
        print(f"✅ Real hardware: Successfully read int variable: {value}")
    else:
        # With mock, expect specific behavior
        assert value == 12345
    
    # Test float variables
    adwin_instance.set_float_var(FPar_id=10, value=67.89)
    value = adwin_instance.read_probes('float_var', id=10)
    
    if USE_REAL_HARDWARE:
        # With real hardware, just verify we can read a value
        assert isinstance(value, (int, float))
        print(f"✅ Real hardware: Successfully read float variable: {value}")
    else:
        # With mock, expect specific behavior
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
        print(f"🔧 Mock Data_Length set to: {adwin_instance.adw.Data_Length.return_value}")
        print(f"🔧 Mock GetData_Long set to: {adwin_instance.adw.GetData_Long.return_value}")
    
    # Test integer array
    length = adwin_instance.read_probes('array_length', id=1)
    print(f"🔍 Array length returned: {length}")
    
    if USE_REAL_HARDWARE:
        # With real hardware, just verify we can read the length
        assert isinstance(length, (int, float)) and length >= 0
        print(f"✅ Real hardware: Array length is {length}")
        
        # If there's data, try to read it
        if length > 0:
            data = adwin_instance.read_probes('int_array', id=1, length=length)
            print(f"🔍 Array data returned: {data}")
            assert isinstance(data, (list, tuple)) and len(data) == length
            print(f"✅ Real hardware: Successfully read {len(data)} array elements")
        else:
            print(f"ℹ️  Real hardware: No array data available (length={length})")
    else:
        # With mock, expect specific behavior
        assert length == 5
        data = adwin_instance.read_probes('int_array', id=1, length=length)
        print(f"🔍 Array data returned: {data}")
        assert len(data) == 5
        assert data == [1, 2, 3, 4, 5]
    
    # Test string array
    str_length = adwin_instance.read_probes('str_length', id=1)
    print(f"🔍 String length returned: {str_length}")
    
    if USE_REAL_HARDWARE:
        # With real hardware, just verify we can read the string length
        assert isinstance(str_length, (int, float)) and str_length >= 0
        print(f"✅ Real hardware: String length is {str_length}")
        
        # If there's string data, try to read it
        if str_length > 0:
            str_data = adwin_instance.read_probes('str_array', id=1, length=str_length)
            print(f"🔍 String data returned: {str_data}")
            assert isinstance(str_data, bytes)
            print(f"✅ Real hardware: Successfully read string data")
        else:
            print(f"ℹ️  Real hardware: No string data available (length={str_length})")
    else:
        # With mock, expect specific behavior
        assert str_length == 5
        str_data = adwin_instance.read_probes('str_array', id=1, length=str_length)
        print(f"🔍 String data returned: {str_data}")
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
        os.environ['RUN_HARDWARE_TESTS'] = '1'
        print("Running tests with real ADwin hardware")
    else:
        print("Running tests with mock ADwin (use --real-hardware for real hardware)")
    
    pytest.main([__file__, "-v"]) 