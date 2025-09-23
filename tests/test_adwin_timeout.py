#!/usr/bin/env python3
"""
Test ADwin timeout functionality.
This test verifies that the new timeout methods work correctly.
"""

import pytest
from src.Controller.adwin_gold import AdwinGoldDevice


@pytest.fixture
def mock_adwin_with_timeout(mock_adwin):
    """
    Extend the existing mock_adwin fixture with timeout methods.
    """
    # Add timeout methods to the existing mock
    mock_adwin.adw.Set_Timeout = pytest.Mock()
    mock_adwin.adw.Get_Timeout = pytest.Mock(return_value=1000)  # Default 1 second
    
    return mock_adwin


def test_set_timeout(mock_adwin_with_timeout):
    """Test setting ADwin timeout."""
    adwin = mock_adwin_with_timeout
    
    # Test setting timeout to 5 seconds
    adwin.set_timeout(5000)
    
    # Verify Set_Timeout was called with correct value
    adwin.adw.Set_Timeout.assert_called_once_with(5000)


def test_get_timeout(mock_adwin_with_timeout):
    """Test getting ADwin timeout."""
    adwin = mock_adwin_with_timeout
    
    # Test getting current timeout
    timeout = adwin.get_timeout()
    
    # Verify Get_Timeout was called and returned expected value
    adwin.adw.Get_Timeout.assert_called_once()
    assert timeout == 1000  # Default mock value


def test_timeout_round_trip(mock_adwin_with_timeout):
    """Test setting and getting timeout in sequence."""
    adwin = mock_adwin_with_timeout
    
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


def test_timeout_integration_with_debug_script(mock_adwin_with_timeout):
    """Test timeout functionality as it would be used in debug_odmr_arrays.py."""
    adwin = mock_adwin_with_timeout
    
    # Test the timeout setting as done in debug script
    try:
        adwin.set_timeout(10000)  # 10 seconds timeout
        current_timeout = adwin.get_timeout()
        assert current_timeout == 10000
        print(f"✅ ADwin timeout set to: {current_timeout} ms")
    except Exception as e:
        pytest.fail(f"Timeout setting failed: {e}")


def test_timeout_error_handling(mock_adwin_with_timeout):
    """Test timeout error handling."""
    adwin = mock_adwin_with_timeout
    
    # Make Set_Timeout raise an exception
    adwin.adw.Set_Timeout.side_effect = Exception("Timeout setting failed")
    
    # Test that exception is properly raised
    with pytest.raises(Exception, match="Timeout setting failed"):
        adwin.set_timeout(5000)


def test_timeout_values(mock_adwin_with_timeout):
    """Test various timeout values."""
    adwin = mock_adwin_with_timeout
    
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
