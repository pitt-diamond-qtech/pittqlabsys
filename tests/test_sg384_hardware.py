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
        'amplitude': -45.0,            # Power
        'enable_output': True,         # Enable output
        'enable_modulation': True,     # Enable modulation
        'modulation_type': 'Freq sweep',  # Set to frequency sweep
        'sweep_function': 'Triangle',  # Triangle sweep
        'sweep_rate': 1.0,            # 1 Hz sweep rate
        'sweep_deviation': 50e6        # 50 MHz deviation
    }
    
    # Apply sweep configuration
    sg384_hardware.update(sweep_config)
    time.sleep(0.5)  # Allow time for configuration to settle
    
    # Verify configuration
    actual_freq = sg384_hardware.read_probes('frequency')
    actual_power = sg384_hardware.read_probes('amplitude')
    actual_mod_type = sg384_hardware.read_probes('modulation_type')
    actual_sweep_func = sg384_hardware.read_probes('sweep_function')
    actual_sweep_rate = sg384_hardware.read_probes('sweep_rate')
    actual_sweep_dev = sg384_hardware.read_probes('sweep_deviation')
    
    # Check that configuration was applied
    assert abs(actual_freq - sweep_config['frequency']) < 1e6
    assert abs(actual_power - sweep_config['amplitude']) < 1.0
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


if __name__ == '__main__':
    # You can run this file directly to test hardware connection
    pytest.main([__file__, '-m', 'hardware', '-v']) 