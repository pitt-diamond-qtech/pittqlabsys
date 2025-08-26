# Created by Gurudev Dutt <gdutt@pitt.edu> on 7/28/25
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
import matplotlib
matplotlib.use("Agg")  # non-interactive, no window pops up
import pytest
import os
import sys
from unittest.mock import Mock
import signal
from functools import wraps
import time
import threading

# Pytest configuration for hardware tests
def pytest_configure(config):
    """Configure pytest to handle hardware tests."""
    config.addinivalue_line(
        "markers", "hardware: marks tests as requiring hardware (deselect with '-m \"not hardware\"')"
    )

# ============================================================================
# Timeout Utilities for Hardware Tests
# ============================================================================

def timeout_handler(signum, frame):
    """Signal handler for timeout."""
    raise TimeoutError("Operation timed out")

def timeout(seconds=10):
    """
    Decorator to add timeout to functions.
    
    Args:
        seconds (int): Timeout in seconds (default: 10)
    
    Returns:
        function: Decorated function with timeout
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Set up signal handler for timeout
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(seconds)
            
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                # Restore original signal handler and cancel alarm
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)
        return wrapper
    return decorator

def safe_hardware_connection(device_class, settings=None, timeout_seconds=10):
    """
    Safely attempt to connect to hardware with timeout.
    
    Args:
        device_class: The device class to instantiate
        settings (dict, optional): Device settings
        timeout_seconds (int): Connection timeout in seconds
    
    Returns:
        tuple: (device_instance, success_message) or (None, error_message)
    """
    start_time = time.time()
    
    try:
        # Create device with custom timeout settings if it's a microwave generator
        if settings is None:
            settings = {}
        
        # Add timeout settings for microwave generators
        if hasattr(device_class, '_DEFAULT_SETTINGS'):
            # Check if this is a microwave generator by looking for connection_type parameter
            has_connection_type = any('connection_type' in str(param) for param in device_class._DEFAULT_SETTINGS)
            if has_connection_type:
                settings.update({
                    'connection_timeout': timeout_seconds,
                    'socket_timeout': min(timeout_seconds / 2, 5.0)  # Socket timeout half of connection timeout
                })
        
        device = device_class(settings=settings)
        
        # Test connection if the device has a test_connection method
        if hasattr(device, 'test_connection'):
            if not device.test_connection():
                return None, "Device connection test failed"
        
        # Check if device is actually connected
        if hasattr(device, 'is_connected'):
            if not device.is_connected:
                return None, "Device instantiated but not connected"
        
        # Test basic communication
        if hasattr(device, '_query'):
            try:
                idn = device._query('*IDN?')
                success_msg = f"Connected to {device_class.__name__}: {idn}"
            except Exception as e:
                return None, f"Device connected but communication failed: {e}"
        else:
            success_msg = f"Connected to {device_class.__name__}"
        
        return device, success_msg
        
    except Exception as e:
        elapsed = time.time() - start_time
        return None, f"Connection failed after {elapsed:.1f}s: {e}"

# ============================================================================
# Hardware Test Configuration
# ============================================================================

def pytest_collection_modifyitems(config, items):
    """Automatically skip hardware tests if no hardware is available."""
    # You can set this environment variable to force hardware tests
    if not os.getenv('RUN_HARDWARE_TESTS'):
        skip_hardware = pytest.mark.skip(reason="Hardware tests disabled by default. Set RUN_HARDWARE_TESTS=1 to enable.")
        for item in items:
            if "hardware" in item.keywords:
                item.add_marker(skip_hardware)

# ============================================================================
# Mock Device Fixtures
# ============================================================================

@pytest.fixture
def mock_devices():
    """Create mock devices for testing confocal and other experiments.
    
    Returns:
        dict: Dictionary with mock device instances for common devices
    """
    mock_nanodrive = Mock()
    mock_adwin = Mock()
    
    # Mock nanodrive methods
    mock_nanodrive.read_probes.return_value = 50.0
    mock_nanodrive.clock_functions.return_value = None
    mock_nanodrive.setup.return_value = None
    mock_nanodrive.waveform_acquisition.return_value = [1.0, 2.0, 3.0]
    mock_nanodrive.empty_waveform = []
    mock_nanodrive.update.return_value = None
    
    # Mock adwin methods
    mock_adwin.stop_process.return_value = None
    mock_adwin.clear_process.return_value = None
    mock_adwin.update.return_value = None
    mock_adwin.read_probes.return_value = [100, 200, 300]
    mock_adwin.reboot_adwin.return_value = None
    mock_adwin.set_int_var.return_value = None
    
    return {
        'nanodrive': {'instance': mock_nanodrive},
        'adwin': {'instance': mock_adwin}
    }

@pytest.fixture
def mock_awg_device():
    """Create a mocked AWG520Device instance.
    
    Returns:
        tuple: (device, mock_driver) where device is AWG520Device and mock_driver is the mocked driver
    """
    from src.Controller.awg520 import AWG520Device
    
    with pytest.MonkeyPatch.context() as m:
        # Mock the AWG520Driver class
        mock_driver = Mock()
        m.setattr('src.Controller.awg520.AWG520Driver', Mock(return_value=mock_driver))
        
        # Create device
        device = AWG520Device(settings={
            'ip_address': '192.168.1.100',
            'scpi_port': 4000,
            'ftp_port': 21,
            'ftp_user': 'usr',
            'ftp_pass': 'pw',
            'seq_file': 'test.seq',
            'enable_iq': False
        })
        
        # Set the driver and ftp_thread attributes
        object.__setattr__(device, 'driver', mock_driver)
        object.__setattr__(device, '_ftp_thread', Mock())
        
        return device, mock_driver

@pytest.fixture
def mock_mux_device():
    """Create a mocked MUXControlDevice instance.
    
    Returns:
        Mock: Mocked MUXControlDevice instance
    """
    from src.Controller import MockMUXControlDevice
    
    mock_device = MockMUXControlDevice(name='test_mux')
    return mock_device

@pytest.fixture
def mock_sg384_device():
    """Create a mocked SG384Generator instance.
    
    Returns:
        Mock: Mocked SG384Generator instance
    """
    mock_device = Mock()
    
    # Mock SG384 methods
    mock_device.set_frequency.return_value = None
    mock_device.set_power.return_value = None
    mock_device.set_modulation_type.return_value = None
    mock_device.set_sweep_deviation.return_value = None
    mock_device.set_sweep_rate.return_value = None
    mock_device.set_modulation_depth.return_value = None
    mock_device.set_modulation_rate.return_value = None
    mock_device.set_modulation_function.return_value = None
    mock_device.update.return_value = None
    
    return mock_device