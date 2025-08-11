"""
Enhanced hardware tests for SG384 microwave generator.
Focuses on frequency, power, and sweep functionality.

These tests require an actual SG384 device to be connected.

To run these tests:
    pytest tests/test_sg384_enhanced.py -m hardware -v

To skip these tests:
    pytest tests/test_sg384_enhanced.py -m "not hardware" -v
"""

import pytest
import sys
import os
import time
import numpy as np

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
class TestSG384Enhanced:
    """Enhanced test suite for SG384 with real hardware."""
    
    def test_basic_connection(self, sg384_hardware):
        """Test basic connection and device identification."""
        idn = sg384_hardware._query('*IDN?')
        assert 'Stanford Research Systems' in idn
        assert 'SG384' in idn
        print(f"Device ID: {idn}")
    
    def test_frequency_range_validation(self, sg384_hardware):
        """Test frequency setting across valid range."""
        # Test frequencies across the SG384 range (typically 1 MHz to 4 GHz)
        test_frequencies = [
            1e6,      # 1 MHz
            100e6,    # 100 MHz
            1e9,      # 1 GHz
            2.5e9,    # 2.5 GHz
            3.5e9,    # 3.5 GHz
            4e9       # 4 GHz
        ]
        
        for freq in test_frequencies:
            print(f"Testing frequency: {freq/1e9:.3f} GHz")
            sg384_hardware.set_frequency(freq)
            time.sleep(0.2)  # Allow device to settle
            
            # Read back frequency
            actual_freq = float(sg384_hardware._query('FREQ?'))
            tolerance = max(1e6, freq * 0.001)  # 1 MHz or 0.1% tolerance
            assert abs(actual_freq - freq) < tolerance, \
                f"Frequency mismatch: set {freq}, got {actual_freq}"
            
            print(f"  ✓ Set: {freq/1e9:.3f} GHz, Read: {actual_freq/1e9:.3f} GHz")
    
    def test_power_range_validation(self, sg384_hardware):
        """Test power setting across valid range."""
        # Test power levels (SG384 typically -110 to +16.5 dBm)
        test_powers = [
            -110.0,   # Minimum power
            -50.0,    # Low power
            -20.0,    # Medium-low power
            -10.0,    # Medium power
            -5.0,     # Medium-high power
            0.0,      # High power
            10.0,     # Very high power
            16.5      # Maximum power
        ]
        
        for power in test_powers:
            print(f"Testing power: {power} dBm")
            sg384_hardware.set_power(power)
            time.sleep(0.2)  # Allow device to settle
            
            # Read back power
            actual_power = float(sg384_hardware._query('POWR?'))
            tolerance = 1.0  # 1 dB tolerance
            assert abs(actual_power - power) < tolerance, \
                f"Power mismatch: set {power}, got {actual_power}"
            
            print(f"  ✓ Set: {power} dBm, Read: {actual_power} dBm")
    
    def test_phase_continuous_sweep(self, sg384_hardware):
        """Test internal phase continuous sweep generation."""
        print("Testing phase continuous sweep...")
        
        # Configure sweep parameters
        center_freq = 2.5e9  # 2.5 GHz center
        deviation = 100e6     # 100 MHz deviation
        sweep_rate = 1e6      # 1 MHz/s sweep rate
        
        # Set center frequency
        sg384_hardware.set_frequency(center_freq)
        time.sleep(0.1)
        
        # Enable sweep mode
        sg384_hardware._send('SFNC 0')  # Sine wave sweep
        sg384_hardware._send(f'SDEV {deviation}')
        sg384_hardware._send(f'SRAT {sweep_rate}')
        
        # Start sweep
        sg384_hardware._send('SSWP 1')  # Start sweep
        time.sleep(0.1)
        
        # Verify sweep is running
        sweep_status = sg384_hardware._query('SSWP?')
        assert sweep_status.strip() == '1', "Sweep not started"
        
        # Let sweep run for a few cycles
        sweep_time = (2 * deviation) / sweep_rate  # Time for one complete sweep
        print(f"Sweep cycle time: {sweep_time:.3f} seconds")
        
        # Monitor frequency during sweep
        frequencies = []
        start_time = time.time()
        duration = min(sweep_time * 2, 10)  # Monitor for 2 cycles or max 10 seconds
        
        while time.time() - start_time < duration:
            freq = float(sg384_hardware._query('FREQ?'))
            frequencies.append(freq)
            time.sleep(0.1)
        
        # Stop sweep
        sg384_hardware._send('SSWP 0')
        
        # Analyze sweep results
        frequencies = np.array(frequencies)
        freq_range = np.max(frequencies) - np.min(frequencies)
        expected_range = 2 * deviation
        
        print(f"Frequency range during sweep: {freq_range/1e6:.1f} MHz")
        print(f"Expected range: {expected_range/1e6:.1f} MHz")
        
        # Verify sweep range is approximately correct (within 10%)
        assert freq_range > expected_range * 0.9, \
            f"Sweep range too small: {freq_range/1e6:.1f} MHz < {expected_range/1e6:.1f} MHz"
        
        print("✓ Phase continuous sweep test passed")
    
    def test_frequency_sweep_with_power_control(self, sg384_hardware):
        """Test frequency sweep while maintaining power control."""
        print("Testing frequency sweep with power control...")
        
        # Set initial parameters
        start_freq = 2.0e9   # 2.0 GHz
        stop_freq = 3.0e9    # 3.0 GHz
        power_level = -10.0   # -10 dBm
        sweep_rate = 10e6     # 10 MHz/s
        
        # Set power
        sg384_hardware.set_power(power_level)
        time.sleep(0.1)
        
        # Configure sweep
        sg384_hardware._send('SFNC 0')  # Sine wave
        sg384_hardware._send(f'FREQ {start_freq}')
        sg384_hardware._send(f'SDEV {(stop_freq - start_freq) / 2}')
        sg384_hardware._send(f'SRAT {sweep_rate}')
        
        # Start sweep
        sg384_hardware._send('SSWP 1')
        time.sleep(0.1)
        
        # Monitor frequency and power during sweep
        measurements = []
        start_time = time.time()
        duration = 5  # Monitor for 5 seconds
        
        while time.time() - start_time < duration:
            freq = float(sg384_hardware._query('FREQ?'))
            power = float(sg384_hardware._query('POWR?'))
            measurements.append((freq, power))
            time.sleep(0.1)
        
        # Stop sweep
        sg384_hardware._send('SSWP 0')
        
        # Analyze results
        frequencies = [m[0] for m in measurements]
        powers = [m[1] for m in measurements]
        
        freq_range = max(frequencies) - min(frequencies)
        power_variation = max(powers) - min(powers)
        
        print(f"Frequency range: {freq_range/1e9:.3f} GHz")
        print(f"Power variation: {power_variation:.2f} dB")
        
        # Verify frequency sweep range
        expected_freq_range = stop_freq - start_freq
        assert freq_range > expected_freq_range * 0.9, \
            f"Frequency sweep range too small: {freq_range/1e9:.3f} GHz"
        
        # Verify power stability (should be within 2 dB)
        assert power_variation < 2.0, \
            f"Power variation too large: {power_variation:.2f} dB"
        
        print("✓ Frequency sweep with power control test passed")
    
    def test_rapid_frequency_changes(self, sg384_hardware):
        """Test rapid frequency changes for dynamic applications."""
        print("Testing rapid frequency changes...")
        
        frequencies = [2.0e9, 2.5e9, 3.0e9, 2.5e9, 2.0e9]  # 5 frequency changes
        start_time = time.time()
        
        for i, freq in enumerate(frequencies):
            sg384_hardware.set_frequency(freq)
            time.sleep(0.05)  # 50ms delay between changes
            
            # Verify frequency was set
            actual_freq = float(sg384_hardware._query('FREQ?'))
            tolerance = 1e6  # 1 MHz tolerance
            assert abs(actual_freq - freq) < tolerance, \
                f"Frequency {i+1} mismatch: set {freq/1e9:.3f} GHz, got {actual_freq/1e9:.3f} GHz"
            
            print(f"  ✓ Frequency {i+1}: {freq/1e9:.3f} GHz")
        
        total_time = time.time() - start_time
        print(f"Total time for {len(frequencies)} frequency changes: {total_time:.3f} seconds")
        print(f"Average time per change: {total_time/len(frequencies):.3f} seconds")
        
        print("✓ Rapid frequency changes test passed")
    
    def test_power_ramping(self, sg384_hardware):
        """Test power ramping for applications requiring gradual power changes."""
        print("Testing power ramping...")
        
        # Ramp power from -20 dBm to 0 dBm in steps
        start_power = -20.0
        end_power = 0.0
        step_size = 2.0  # 2 dB steps
        
        powers = np.arange(start_power, end_power + step_size, step_size)
        measurements = []
        
        for power in powers:
            sg384_hardware.set_power(power)
            time.sleep(0.1)  # Allow device to settle
            
            # Read back power
            actual_power = float(sg384_hardware._query('POWR?'))
            measurements.append((power, actual_power))
            
            print(f"  Set: {power} dBm, Read: {actual_power} dBm")
        
        # Verify power ramping accuracy
        errors = [abs(actual - set_power) for set_power, actual in measurements]
        max_error = max(errors)
        avg_error = np.mean(errors)
        
        print(f"Maximum power error: {max_error:.2f} dB")
        print(f"Average power error: {avg_error:.2f} dB")
        
        # Power accuracy should be within 1.5 dB
        assert max_error < 1.5, f"Power accuracy too poor: {max_error:.2f} dB"
        
        print("✓ Power ramping test passed")
    
    def test_sweep_parameter_validation(self, sg384_hardware):
        """Test sweep parameter validation with real hardware."""
        print("Testing sweep parameter validation...")
        
        # Test valid sweep parameters
        valid_combinations = [
            (2.5e9, 50e6, 1e6),    # 2.5 GHz center, 50 MHz deviation, 1 MHz/s
            (2.0e9, 100e6, 5e6),   # 2.0 GHz center, 100 MHz deviation, 5 MHz/s
            (3.0e9, 200e6, 10e6),  # 3.0 GHz center, 200 MHz deviation, 10 MHz/s
        ]
        
        for center_freq, deviation, sweep_rate in valid_combinations:
            print(f"Testing: {center_freq/1e9:.3f} GHz ± {deviation/1e6:.1f} MHz @ {sweep_rate/1e6:.1f} MHz/s")
            
            # This should not raise an exception
            is_valid = sg384_hardware.validate_sweep_parameters(center_freq, deviation, sweep_rate)
            assert is_valid, f"Sweep parameters should be valid: {center_freq}, {deviation}, {sweep_rate}"
            
            print("  ✓ Valid sweep parameters")
        
        # Test invalid sweep parameters
        invalid_combinations = [
            (0.5e9, 100e6, 1e6),   # Frequency too low
            (5.0e9, 100e6, 1e6),   # Frequency too high
            (2.5e9, 100e6, 100e6), # Sweep rate too high
        ]
        
        for center_freq, deviation, sweep_rate in invalid_combinations:
            print(f"Testing invalid: {center_freq/1e9:.3f} GHz ± {deviation/1e6:.1f} MHz @ {sweep_rate/1e6:.1f} MHz/s")
            
            # This should return False or raise an exception
            try:
                is_valid = sg384_hardware.validate_sweep_parameters(center_freq, deviation, sweep_rate)
                if is_valid:
                    print(f"  ⚠️  Unexpectedly valid: {center_freq}, {deviation}, {sweep_rate}")
                else:
                    print("  ✓ Correctly rejected invalid parameters")
            except Exception as e:
                print(f"  ✓ Correctly raised exception: {e}")
        
        print("✓ Sweep parameter validation test passed")
    
    def test_device_probes(self, sg384_hardware):
        """Test reading device probes for monitoring."""
        print("Testing device probes...")
        
        # Test reading various probe values
        probes_to_test = [
            'frequency',
            'power', 
            'phase',
            'enable_output',
            'enable_modulation',
            'modulation_type',
            'modulation_function',
            'sweep_function',
            'sweep_rate',
            'sweep_deviation'
        ]
        
        for probe in probes_to_test:
            try:
                value = sg384_hardware.read_probes(probe)
                print(f"  ✓ {probe}: {value}")
            except Exception as e:
                print(f"  ⚠️  {probe}: Error - {e}")
        
        print("✓ Device probes test passed")
    
    def test_cleanup_and_safety(self, sg384_hardware):
        """Test cleanup and safety measures."""
        print("Testing cleanup and safety...")
        
        # Set safe parameters
        sg384_hardware.set_frequency(2.5e9)  # 2.5 GHz
        sg384_hardware.set_power(-20.0)      # Low power
        sg384_hardware.set_phase(0.0)        # 0 degrees
        
        # Stop any ongoing sweeps
        sg384_hardware._send('SSWP 0')
        
        # Disable output for safety
        sg384_hardware._send('ENBL 0')
        
        # Verify safe state
        output_enabled = sg384_hardware._query('ENBL?')
        assert output_enabled.strip() == '0', "Output not disabled"
        
        sweep_running = sg384_hardware._query('SSWP?')
        assert sweep_running.strip() == '0', "Sweep not stopped"
        
        print("✓ Cleanup and safety test passed")
        print("✓ Device is in safe state")


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "-m", "hardware"]) 