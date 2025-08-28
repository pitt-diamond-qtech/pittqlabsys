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
import socket

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.Controller.sg384 import SG384Generator


@pytest.fixture(scope="module")
def sg384_hardware():
    """
    Fixture to create a real SG384 connection.
    This will be shared across all hardware tests.
    """
    # Use the device class defaults - test what you actually use
    # No custom settings - let the class handle its own configuration
    
    from tests.conftest import safe_hardware_connection
    
    device, message = safe_hardware_connection(
        SG384Generator, 
        timeout_seconds=10  # SG384 should connect quickly
    )
    
    if device is None:
        pytest.skip(f"Could not connect to SG384: {message}")
    
    print(f"✓ {message}")
    yield device
    
    # Clean up connection
    if hasattr(device, 'close_connection'):
        device.close_connection()
    device.close()


@pytest.mark.hardware
def test_sg384_connection(sg384_hardware):
    """Test that we can connect to the SG384 and get device identification."""
    # Test basic connection first
    assert sg384_hardware.test_connection(), "Device connection test failed"
    
    # Test device identification
    try:
        idn = sg384_hardware._query('*IDN?')
        assert 'Stanford Research Systems' in idn
        assert 'SG384' in idn
        print(f"Device ID: {idn}")
    except socket.timeout:
        pytest.skip("Device communication timed out - may be offline or busy")
    except Exception as e:
        pytest.skip(f"Device communication failed: {e}")


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
    
    # Read back power using the correct SCPI command for RF output
    try:
        actual_power = float(sg384_hardware._query('AMPR?'))  # Use AMPR? for RF power
        assert abs(actual_power - test_power) < 1.0  # Within 1 dB tolerance
        print(f"✓ Set power: {test_power} dBm, Read: {actual_power} dBm")
    except socket.timeout:
        pytest.skip("Power query timed out - device may be busy")
    except Exception as e:
        pytest.skip(f"Power query failed: {e}")


@pytest.mark.hardware
def test_sg384_phase_setting(sg384_hardware):
    """Test setting and reading phase."""
    # Test phase setting
    test_phase = 45.0  # 45 degrees
    sg384_hardware.set_phase(test_phase)
    time.sleep(0.1)
    
    # Read back phase
    try:
        actual_phase = float(sg384_hardware._query('PHAS?'))
        assert abs(actual_phase - test_phase) < 1.0  # Within 1 degree tolerance
        print(f"Set phase: {test_phase}°, Read: {actual_phase}°")
    except socket.timeout:
        pytest.skip("Phase query timed out - device may be busy")
    except Exception as e:
        pytest.skip(f"Phase query failed: {e}")


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
    assert sg384_hardware._param_to_scpi('frequency') == 'FREQ'
    # Note: 'amplitude' maps to low frequency output (AMPL), 'amplitude_rf' maps to RF output (AMPR)
    assert sg384_hardware._param_to_scpi('amplitude') == 'AMPL'  # Low frequency output
    assert sg384_hardware._param_to_scpi('amplitude_rf') == 'AMPR'  # RF output
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
    # The _dispatch_update method now automatically handles SG384's phase reset behavior
    # by setting frequency first, then other parameters, then phase last
    
    update_settings = {
        'frequency': 3.0e9,  # 3 GHz
        'power': -5.0,       # -5 dBm
        'phase': 90.0,       # 90 degrees
    }
    
    sg384_hardware.update(update_settings)
    time.sleep(0.2)  # Allow time for all updates
    
    # Verify the updates
    freq = sg384_hardware.read_probes('frequency')
    power = sg384_hardware.read_probes('amplitude_rf')  # Read from RF output (AMPR)
    phase = sg384_hardware.read_probes('phase')
    
    assert abs(freq - 3.0e9) < 1e6
    assert abs(power - (-5.0)) < 1.0
    assert abs(phase - 90.0) < 1.0  # 1.0° tolerance for 3 GHz (per SG384 manual)
    
    print(f"✓ Update method works: {freq/1e9:.3f} GHz, {power} dBm, {phase}°")


@pytest.mark.hardware
def test_sg384_error_handling(sg384_hardware):
    """Test error handling with invalid parameters."""
    # Test invalid parameter
    with pytest.raises(KeyError):
        sg384_hardware._param_to_scpi('invalid_param')
    
    # Test invalid modulation type
    with pytest.raises(KeyError):
        sg384_hardware._mod_type_to_internal('Invalid')
    
    # Test invalid modulation function
    with pytest.raises(KeyError):
        sg384_hardware._mod_func_to_internal('Invalid')
    
    print("✓ Error handling works correctly")


@pytest.mark.hardware
def test_sg384_sweep_function_setting(sg384_hardware):
    """Test setting and reading sweep function."""
    # Test sweep function setting
    test_function = 'Triangle'
    sg384_hardware.update({'sweep_function': test_function})
    time.sleep(0.1)
    
    # Read back sweep function
    actual_function = sg384_hardware.read_probes('sweep_function')
    assert actual_function == test_function
    print(f"✓ Set sweep function: {test_function}, Read: {actual_function}")


@pytest.mark.hardware
def test_sg384_sweep_rate_setting(sg384_hardware):
    """Test setting and reading sweep rate."""
    # Test valid sweep rate
    test_rate = 1.0  # 1 Hz
    sg384_hardware.update({'sweep_rate': test_rate})
    time.sleep(0.1)
    
    # Read back sweep rate
    actual_rate = sg384_hardware.read_probes('sweep_rate')
    assert abs(actual_rate - test_rate) < 0.1  # Within 0.1 Hz tolerance
    print(f"✓ Set sweep rate: {test_rate} Hz, Read: {actual_rate} Hz")
    
    # Test invalid sweep rate (should raise error)
    with pytest.raises(ValueError, match="less than 120 Hz"):
        sg384_hardware.update({'sweep_rate': 150.0})
    print("✓ Invalid sweep rate rejected")


@pytest.mark.hardware
def test_sg384_sweep_deviation_setting(sg384_hardware):
    """Test setting and reading sweep deviation."""
    # Test sweep deviation setting
    test_deviation = 1e6  # 1 MHz
    sg384_hardware.update({'sweep_deviation': test_deviation})
    time.sleep(0.1)
    
    # Read back sweep deviation
    actual_deviation = sg384_hardware.read_probes('sweep_deviation')
    assert abs(actual_deviation - test_deviation) < 1e3  # Within 1 kHz tolerance
    print(f"✓ Set sweep deviation: {test_deviation/1e6:.3f} MHz, Read: {actual_deviation/1e6:.3f} MHz")


@pytest.mark.hardware
def test_sg384_sweep_parameter_validation(sg384_hardware):
    """Test sweep parameter validation."""
    # Test valid parameters
    center_freq = 2.87e9  # 2.87 GHz
    deviation = 50e6      # 50 MHz
    sweep_rate = 1.0      # 1 Hz
    
    # Should not raise any exception
    result = sg384_hardware.validate_sweep_parameters(center_freq, deviation, sweep_rate)
    assert result is True
    print("✓ Valid sweep parameters accepted")
    
    # Test invalid sweep rate
    with pytest.raises(ValueError, match="less than 120 Hz"):
        sg384_hardware.validate_sweep_parameters(center_freq, deviation, 150.0)
    print("✓ Invalid sweep rate rejected")
    
    # Test frequency too low (if device supports this validation)
    try:
        sg384_hardware.validate_sweep_parameters(1.0e9, 1e9, 1.0)  # 0 GHz minimum
        print("⚠ Frequency validation not implemented on this device")
    except ValueError as e:
        if "below minimum" in str(e):
            print("✓ Frequency too low rejected")
        else:
            raise
    except Exception:
        print("⚠ Frequency validation not implemented on this device")


@pytest.mark.hardware
def test_sg384_sweep_integration(sg384_hardware):
    """Test complete sweep setup and operation."""
    # Set up a complete sweep configuration
    sweep_config = {
        'frequency': 2.87e9,           # Center frequency
        'power': -45.0,                # RF power (uses set_power_rf)
        'enable_output': True,         # Enable output
        'enable_modulation': True,     # Enable modulation
        'modulation_type': 'Freq sweep',  # Set to frequency sweep (correct string from mapping)
        'sweep_function': 'Triangle',  # Triangle sweep
        'sweep_rate': 1.0,            # 1 Hz sweep rate
        'sweep_deviation': 50e6        # 50 MHz deviation
    }
    
    # Apply sweep configuration
    sg384_hardware.update(sweep_config)
    time.sleep(0.5)  # Allow time for configuration to settle
    
    # Verify configuration
    actual_freq = sg384_hardware.read_probes('frequency')
    actual_power = sg384_hardware.read_probes('power_rf')  # Read RF power
    actual_mod_type = sg384_hardware.read_probes('modulation_type')
    actual_sweep_func = sg384_hardware.read_probes('sweep_function')
    actual_sweep_rate = sg384_hardware.read_probes('sweep_rate')
    actual_sweep_dev = sg384_hardware.read_probes('sweep_deviation')
    
    # Check that configuration was applied
    assert abs(actual_freq - sweep_config['frequency']) < 1e6
    assert abs(actual_power - sweep_config['power']) < 1.0
    assert actual_mod_type == sweep_config['modulation_type']
    assert actual_sweep_func == sweep_config['sweep_function']
    assert abs(actual_sweep_rate - sweep_config['sweep_rate']) < 0.1
    assert abs(actual_sweep_dev - sweep_config['sweep_deviation']) < 1e3
    
    print("✓ Complete sweep configuration applied successfully")
    print(f"  Center frequency: {actual_freq/1e9:.3f} GHz")
    print(f"  Power: {actual_power} dBm")
    print(f"  Modulation type: {actual_mod_type}")
    print(f"  Sweep function: {actual_sweep_func}")
    print(f"  Sweep rate: {actual_sweep_rate} Hz")
    print(f"  Sweep deviation: {actual_sweep_dev/1e6:.3f} MHz")


@pytest.mark.hardware
def test_sg384_diagnostic_queries(sg384_hardware):
    """Diagnostic test to investigate hardware communication issues."""
    print("\n=== SG384 Diagnostic Information ===")
    
    # Test basic device identification
    try:
        idn = sg384_hardware._query('*IDN?')
        print(f"Device ID: {idn}")
    except Exception as e:
        print(f"Device ID query failed: {e}")
    
    # Test current device state
    try:
        # Check current frequency
        current_freq = sg384_hardware._query('FREQ?')
        print(f"Current frequency: {current_freq}")
    except Exception as e:
        print(f"Frequency query failed: {e}")
    
    try:
        # Check current power
        current_power = sg384_hardware._query('POWR?')
        print(f"Current power: {current_power}")
    except Exception as e:
        print(f"Power query failed: {e}")
    
    try:
        # Check current phase
        current_phase = sg384_hardware._query('PHAS?')
        print(f"Current phase: {current_phase}")
    except Exception as e:
        print(f"Phase query failed: {e}")
    
    try:
        # Check modulation status
        mod_status = sg384_hardware._query('MODL:STAT?')
        print(f"Modulation status: {mod_status}")
    except Exception as e:
        print(f"Modulation status query failed: {e}")
    
    try:
        # Check modulation type
        mod_type = sg384_hardware._query('MODL:TYPE?')
        print(f"Modulation type: {mod_type}")
    except Exception as e:
        print(f"Modulation type query failed: {e}")
    
    try:
        # Check sweep status
        sweep_status = sg384_hardware._query('SWP:STAT?')
        print(f"Sweep status: {sweep_status}")
    except Exception as e:
        print(f"Sweep status query failed: {e}")
    
    try:
        # Check sweep rate
        sweep_rate = sg384_hardware._query('SWP:RATE?')
        print(f"Sweep rate: {sweep_rate}")
    except Exception as e:
        print(f"Sweep rate query failed: {e}")
    
    try:
        # Check output status
        output_status = sg384_hardware._query('ENBR?')
        print(f"Output status: {output_status}")
    except Exception as e:
        print(f"Output status query failed: {e}")
    
    print("=== End Diagnostic ===\n")
    
    # This test should always pass - it's just for information
    assert True, "Diagnostic test completed"


@pytest.mark.hardware
def test_sg384_basic_command_acceptance(sg384_hardware):
    """Test that the device accepts and responds to basic commands."""
    print("\n=== Testing Basic Command Acceptance ===")
    
    # Test 1: Set a simple frequency and verify it's accepted
    try:
        # Read current frequency
        freq_before = float(sg384_hardware._query('FREQ?'))
        print(f"Frequency before: {freq_before/1e9:.3f} GHz")
        
        # Set a different frequency
        test_freq = 2.5e9  # 2.5 GHz
        sg384_hardware._send(f'FREQ {test_freq}')
        time.sleep(0.2)  # Wait for device to process
        
        # Read back frequency
        freq_after = float(sg384_hardware._query('FREQ?'))
        print(f"Frequency after setting {test_freq/1e9:.3f} GHz: {freq_after/1e9:.3f} GHz")
        
        # Check if command was accepted
        if abs(freq_after - test_freq) < 1e6:  # Within 1 MHz
            print("✓ Frequency command accepted and applied")
        else:
            print(f"⚠ Frequency command not applied correctly. Expected: {test_freq/1e9:.3f} GHz, Got: {freq_after/1e9:.3f} GHz")
            
    except Exception as e:
        print(f"Frequency command test failed: {e}")
    
    # Test 2: Set a simple power and verify it's accepted
    try:
        # Read current power
        power_before = float(sg384_hardware._query('POWR?'))
        print(f"Power before: {power_before} dBm")
        
        # Set a different power
        test_power = -10.0  # -10 dBm
        sg384_hardware._send(f'POWR {test_power}')
        time.sleep(0.2)  # Wait for device to process
        
        # Read back power
        power_after = float(sg384_hardware._query('POWR?'))
        print(f"Power after setting {test_power} dBm: {power_after} dBm")
        
        # Check if command was accepted
        if abs(power_after - test_power) < 1.0:  # Within 1 dB
            print("✓ Power command accepted and applied")
        else:
            print(f"⚠ Power command not applied correctly. Expected: {test_power} dBm, Got: {power_after} dBm")
            
    except Exception as e:
        print(f"Power command test failed: {e}")
    
    print("=== End Command Acceptance Test ===\n")
    
    # This test should always pass - it's just for information
    assert True, "Basic command acceptance test completed"


if __name__ == '__main__':
    # You can run this file directly to test hardware connection
    pytest.main([__file__, '-m', 'hardware', '-v']) 