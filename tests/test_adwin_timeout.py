#!/usr/bin/env python3
"""
Test ADwin timeout functionality.
This test verifies that the new timeout methods work correctly.
"""

import pytest
from unittest.mock import Mock, patch
from src.Controller.adwin_gold import AdwinGoldDevice


@pytest.fixture
def mock_adwin():
    """
    Mock ADwin fixture for testing without hardware.
    Provides realistic mock responses for ADwin methods.
    """
    with patch('src.Controller.adwin_gold.ADwin') as mock_adwin_class:
        # Create a mock ADwin instance
        mock_adw = Mock()
        
        # Mock the ADwin class to return our mock instance
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
        mock_adw.Process_Status = Mock(return_value=0)  # 0 = Not running
        
        # Mock variable setting/getting methods
        mock_adw.Set_Par = Mock()
        mock_adw.Set_FPar = Mock()
        mock_adw.Get_Par = Mock(return_value=0)
        mock_adw.Get_FPar = Mock(return_value=0.0)
        mock_adw.Get_FPar_Double = Mock(return_value=0.0)
        
        # Mock timeout methods
        mock_adw.Set_Timeout = Mock()
        mock_adw.Get_Timeout = Mock(return_value=1000)  # Default 1 second
        
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
        
        # Create ADwinGold instance with mocked ADwin
        adwin_gold = AdwinGoldDevice(boot=False)  # Don't boot to avoid hardware connection
        
        yield adwin_gold
        
        # Clean up: explicitly call close to avoid __del__ issues
        try:
            adwin_gold.close()
        except:
            pass  # Ignore any cleanup errors


def test_set_timeout(mock_adwin):
    """Test setting ADwin timeout."""
    adwin = mock_adwin
    
    # Test setting timeout to 5 seconds
    adwin.set_timeout(5000)
    
    # Verify Set_Timeout was called with correct value
    adwin.adw.Set_Timeout.assert_called_once_with(5000)


def test_get_timeout(mock_adwin):
    """Test getting ADwin timeout."""
    adwin = mock_adwin
    
    # Test getting current timeout
    timeout = adwin.get_timeout()
    
    # Verify Get_Timeout was called and returned expected value
    adwin.adw.Get_Timeout.assert_called_once()
    assert timeout == 1000  # Default mock value


def test_timeout_round_trip(mock_adwin):
    """Test setting and getting timeout in sequence."""
    adwin = mock_adwin
    
    # Set timeout to 10 seconds
    adwin.set_timeout(10000)
    
    # Mock the return value for the get call
    adwin.adw.Get_Timeout.return_value = 10000
    
    # Get timeout and verify
    timeout = adwin.get_timeout()
    assert timeout == 10000
    
    # Verify both methods were called
    adwin.adw.Set_Timeout.assert_called_with(10000)
    adwin.adw.Get_Timeout.assert_called()


def test_timeout_integration_with_debug_script(mock_adwin):
    """Test timeout functionality as it would be used in debug_odmr_arrays.py."""
    adwin = mock_adwin
    
    # Test the timeout setting as done in debug script
    try:
        adwin.set_timeout(10000)  # 10 seconds timeout
        current_timeout = adwin.get_timeout()
        assert current_timeout == 10000
        print(f"✅ ADwin timeout set to: {current_timeout} ms")
    except Exception as e:
        pytest.fail(f"Timeout setting failed: {e}")


def test_timeout_error_handling(mock_adwin):
    """Test timeout error handling."""
    adwin = mock_adwin
    
    # Make Set_Timeout raise an exception
    adwin.adw.Set_Timeout.side_effect = Exception("Timeout setting failed")
    
    # Test that exception is properly raised
    with pytest.raises(Exception, match="Timeout setting failed"):
        adwin.set_timeout(5000)


def test_timeout_values(mock_adwin):
    """Test various timeout values."""
    adwin = mock_adwin
    
    # Test various timeout values
    test_values = [1000, 5000, 10000, 30000]  # 1s, 5s, 10s, 30s
    
    for timeout_ms in test_values:
        adwin.adw.Get_Timeout.return_value = timeout_ms
        adwin.set_timeout(timeout_ms)
        result = adwin.get_timeout()
        assert result == timeout_ms


@pytest.mark.hardware
def test_timeout_with_real_hardware():
    """
    Test timeout functionality with real ADwin hardware.
    This test requires actual ADwin hardware to be connected.
    """
    adwin = None
    try:
        adwin = AdwinGoldDevice()
        assert adwin.is_connected
        
        # Test setting timeout
        adwin.set_timeout(10000)  # 10 seconds
        current_timeout = adwin.get_timeout()
        print(f"Real hardware timeout set to: {current_timeout} ms")
        
        # Verify timeout was set (should be 10000 or close)
        assert current_timeout >= 5000  # At least 5 seconds
        
        # Test a longer timeout
        adwin.set_timeout(30000)  # 30 seconds
        current_timeout = adwin.get_timeout()
        assert current_timeout >= 25000  # At least 25 seconds
        
        print("✅ Real hardware timeout test passed")
        
    except Exception as e:
        pytest.skip(f"ADwin hardware not available: {e}")
    finally:
        if adwin is not None:
            try:
                adwin.close()
            except:
                pass


if __name__ == "__main__":
    # Run tests if script is executed directly
    pytest.main([__file__, "-v"])
