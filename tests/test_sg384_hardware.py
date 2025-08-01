"""
Hardware integration tests for SG384 microwave generator.
These tests require an actual SG384 device to be connected.

To run these tests:
    pytest tests/test_sg384_hardware.py -m hardware -v

To skip these tests:
    pytest tests/test_sg384_hardware.py -m "not hardware" -v

To run all tests except hardware:
    pytest -m "not hardware"
"""

import pytest
import sys
import os
import time

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from Controller.sg384 import SG384Generator


@pytest.fixture(scope="module")
def sg384_hardware():
    """
    Fixture to create a real SG384 connection.
    This will be shared across all hardware tests.
    """
    # Hardware connection settings - modify these for your setup
    settings = {
        'connection_type': 'LAN',  # or 'GPIB' or 'RS232'
        'ip_address': '169.254.146.198',  # Modify for your SG384 IP
        'port': 5025,  # Modify for your SG384 port
        # For GPIB: 'visa_resource': 'GPIB0::20::INSTR'
        # For RS232: 'visa_resource': 'ASRL9::INSTR'
    }
    
    try:
        sg384 = SG384Generator(settings=settings)
        print(f"✓ Connected to SG384: {sg384._query('*IDN?')}")
        yield sg384
    except Exception as e:
        pytest.skip(f"Could not connect to SG384: {e}")
    finally:
        # Clean up connection
        if 'sg384' in locals():
            sg384.close()


@pytest.mark.hardware
def test_sg384_connection(sg384_hardware):
    """Test that we can connect to the SG384 and get device identification."""
    idn = sg384_hardware._query('*IDN?')
    assert 'Stanford Research Systems' in idn
    assert 'SG384' in idn
    print(f"Device ID: {idn}")


@pytest.mark.hardware
def test_sg384_frequency_setting(sg384_hardware):
    """Test setting and reading frequency."""
    # Test frequency setting
    test_freq = 2.5e9  # 2.5 GHz
    sg384_hardware.set_frequency(test_freq)
    time.sleep(0.1)  # Small delay for device to settle
    
    # Read back frequency
    actual_freq = float(sg384_hardware._query('FREQ?'))
    assert abs(actual_freq - test_freq) < 1e6  # Within 1 MHz tolerance
    print(f"Set frequency: {test_freq/1e9:.3f} GHz, Read: {actual_freq/1e9:.3f} GHz")


@pytest.mark.hardware
def test_sg384_power_setting(sg384_hardware):
    """Test setting and reading power."""
    # Test power setting
    test_power = -10.0  # -10 dBm
    sg384_hardware.set_power(test_power)
    time.sleep(0.1)
    
    # Read back power
    actual_power = float(sg384_hardware._query('POWR?'))
    assert abs(actual_power - test_power) < 1.0  # Within 1 dB tolerance
    print(f"Set power: {test_power} dBm, Read: {actual_power} dBm")


@pytest.mark.hardware
def test_sg384_phase_setting(sg384_hardware):
    """Test setting and reading phase."""
    # Test phase setting
    test_phase = 45.0  # 45 degrees
    sg384_hardware.set_phase(test_phase)
    time.sleep(0.1)
    
    # Read back phase
    actual_phase = float(sg384_hardware._query('PHAS?'))
    assert abs(actual_phase - test_phase) < 1.0  # Within 1 degree tolerance
    print(f"Set phase: {test_phase}°, Read: {actual_phase}°")


@pytest.mark.hardware
def test_sg384_output_control(sg384_hardware):
    """Test enabling and disabling the output."""
    # Enable output
    sg384_hardware._send('ENBR 1')
    time.sleep(0.1)
    output_enabled = int(sg384_hardware._query('ENBR?'))
    assert output_enabled == 1
    print("✓ Output enabled")
    
    # Disable output
    sg384_hardware._send('ENBR 0')
    time.sleep(0.1)
    output_enabled = int(sg384_hardware._query('ENBR?'))
    assert output_enabled == 0
    print("✓ Output disabled")


@pytest.mark.hardware
def test_sg384_modulation_settings(sg384_hardware):
    """Test modulation type and function settings."""
    # Test modulation type setting
    sg384_hardware._send('TYPE 1')  # FM modulation
    time.sleep(0.1)
    mod_type = int(sg384_hardware._query('TYPE?'))
    assert mod_type == 1
    print("✓ FM modulation type set")
    
    # Test modulation function setting
    sg384_hardware._send('MFNC 3')  # Square wave
    time.sleep(0.1)
    mod_func = int(sg384_hardware._query('MFNC?'))
    assert mod_func == 3
    print("✓ Square wave modulation function set")


@pytest.mark.hardware
def test_sg384_mapping_functions(sg384_hardware):
    """Test that the mapping dictionary functions work with real hardware."""
    # Test parameter mapping
    assert sg384_hardware._param_to_internal('frequency') == 'FREQ'
    assert sg384_hardware._param_to_internal('amplitude') == 'AMPR'
    print("✓ Parameter mapping works with hardware")
    
    # Test modulation type mapping
    assert sg384_hardware._mod_type_to_internal('FM') == 1
    assert sg384_hardware._internal_to_mod_type(1) == 'FM'
    print("✓ Modulation type mapping works with hardware")
    
    # Test modulation function mapping
    assert sg384_hardware._mod_func_to_internal('Square') == 3
    assert sg384_hardware._internal_to_mod_func(3) == 'Square'
    print("✓ Modulation function mapping works with hardware")


@pytest.mark.hardware
def test_sg384_read_probes(sg384_hardware):
    """Test reading probe values from real hardware."""
    # Read frequency probe
    freq = sg384_hardware.read_probes('frequency')
    assert isinstance(freq, float)
    assert freq > 0
    print(f"✓ Frequency probe: {freq/1e9:.3f} GHz")
    
    # Read amplitude probe
    amp = sg384_hardware.read_probes('amplitude')
    assert isinstance(amp, float)
    print(f"✓ Amplitude probe: {amp} dBm")
    
    # Read phase probe
    phase = sg384_hardware.read_probes('phase')
    assert isinstance(phase, float)
    print(f"✓ Phase probe: {phase}°")


@pytest.mark.hardware
def test_sg384_update_method(sg384_hardware):
    """Test the update method with real hardware."""
    # Test updating multiple parameters
    update_settings = {
        'frequency': 3.0e9,  # 3 GHz
        'power': -5.0,       # -5 dBm
        'phase': 90.0,       # 90 degrees
    }
    
    sg384_hardware.update(update_settings)
    time.sleep(0.2)  # Allow time for all updates
    
    # Verify the updates
    freq = sg384_hardware.read_probes('frequency')
    power = sg384_hardware.read_probes('amplitude')  # Note: amplitude is the probe name
    phase = sg384_hardware.read_probes('phase')
    
    assert abs(freq - 3.0e9) < 1e6
    assert abs(power - (-5.0)) < 1.0
    assert abs(phase - 90.0) < 1.0
    
    print(f"✓ Update method works: {freq/1e9:.3f} GHz, {power} dBm, {phase}°")


@pytest.mark.hardware
def test_sg384_error_handling(sg384_hardware):
    """Test error handling with invalid parameters."""
    # Test invalid parameter
    with pytest.raises(KeyError):
        sg384_hardware._param_to_internal('invalid_param')
    
    # Test invalid modulation type
    with pytest.raises(KeyError):
        sg384_hardware._mod_type_to_internal('Invalid')
    
    # Test invalid modulation function
    with pytest.raises(KeyError):
        sg384_hardware._mod_func_to_internal('Invalid')
    
    print("✓ Error handling works correctly")


if __name__ == '__main__':
    # You can run this file directly to test hardware connection
    pytest.main([__file__, '-m', 'hardware', '-v']) 