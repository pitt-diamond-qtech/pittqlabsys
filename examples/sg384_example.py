#!/usr/bin/env python3
"""
SG384 Microwave Generator Example Script

This script demonstrates the operation of the Stanford Research Systems SG384
microwave generator, including:
- Basic frequency, power, and phase control
- Internal phase continuous sweep generation
- Power ramping and frequency hopping
- Real-time monitoring and data logging

Usage:
    python examples/sg384_example.py [--connection-type LAN|GPIB|RS232] [--ip-address IP] [--port PORT] [--visa-resource RESOURCE]

Examples:
    # LAN connection (default)
    python examples/sg384_example.py --ip-address 169.254.146.198 --port 5025
    
    # GPIB connection
    python examples/sg384_example.py --connection-type GPIB --visa-resource "GPIB0::20::INSTR"
    
    # RS232 connection
    python examples/sg384_example.py --connection-type RS232 --visa-resource "ASRL9::INSTR"
"""

import sys
import time
import argparse
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / '..'))

from src.Controller.sg384 import SG384Generator


class SG384Example:
    """Example class for SG384 microwave generator operation."""
    
    def __init__(self, connection_settings):
        """Initialize SG384 with connection settings."""
        self.settings = connection_settings
        self.sg384 = None
        self.data_log = []
        
        # Create output directory for data
        self.output_dir = Path(__file__).parent / "sg384_data"
        self.output_dir.mkdir(exist_ok=True)
        
        print("=" * 60)
        print("SG384 MICROWAVE GENERATOR EXAMPLE")
        print("=" * 60)
        print(f"Connection type: {connection_settings['connection_type']}")
        if connection_settings['connection_type'] == 'LAN':
            print(f"IP Address: {connection_settings['ip_address']}")
            print(f"Port: {connection_settings['port']}")
        else:
            print(f"VISA Resource: {connection_settings['visa_resource']}")
        print("=" * 60)
    
    def connect(self):
        """Connect to the SG384 device."""
        try:
            print("Connecting to SG384...")
            self.sg384 = SG384Generator(settings=self.settings)
            
            # Test connection
            idn = self.sg384._query('*IDN?')
            print(f"✓ Connected to: {idn}")
            
            # Get device status
            self._print_device_status()
            
            return True
            
        except Exception as e:
            print(f"✗ Connection failed: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from the SG384 device."""
        if self.sg384:
            print("Disconnecting from SG384...")
            self.sg384.close()
            print("✓ Disconnected")
    
    def _print_device_status(self):
        """Print current device status."""
        print("\n--- Device Status ---")
        try:
            freq = float(self.sg384._query('FREQ?'))
            power = float(self.sg384._query('POWR?'))
            phase = float(self.sg384._query('PHAS?'))
            output = self.sg384._query('ENBL?')
            sweep = self.sg384._query('SSWP?')
            
            print(f"Frequency: {freq/1e9:.6f} GHz")
            print(f"Power: {power:.1f} dBm")
            print(f"Phase: {phase:.1f}°")
            print(f"Output: {'ON' if output.strip() == '1' else 'OFF'}")
            print(f"Sweep: {'RUNNING' if sweep.strip() == '1' else 'STOPPED'}")
            
        except Exception as e:
            print(f"Could not read device status: {e}")
    
    def _log_data(self, operation, **kwargs):
        """Log operation data with timestamp."""
        timestamp = datetime.now()
        log_entry = {
            'timestamp': timestamp,
            'operation': operation,
            **kwargs
        }
        self.data_log.append(log_entry)
    
    def basic_operation_demo(self):
        """Demonstrate basic frequency, power, and phase control."""
        print("\n" + "=" * 40)
        print("BASIC OPERATION DEMONSTRATION")
        print("=" * 40)
        
        # Test frequency setting
        print("\n1. Frequency Control Test")
        test_frequencies = [1e9, 2e9, 2.5e9, 3e9, 3.5e9]  # 1-3.5 GHz
        
        for freq in test_frequencies:
            print(f"   Setting frequency to {freq/1e9:.3f} GHz...")
            self.sg384.set_frequency(freq)
            time.sleep(0.2)  # Allow device to settle
            
            # Read back frequency
            actual_freq = float(self.sg384._query('FREQ?'))
            error = abs(actual_freq - freq)
            print(f"   ✓ Set: {freq/1e9:.3f} GHz, Read: {actual_freq/1e9:.3f} GHz, Error: {error/1e6:.1f} MHz")
            
            self._log_data('frequency_set', set_freq=freq, actual_freq=actual_freq, error=error)
        
        # Test power control
        print("\n2. Power Control Test")
        test_powers = [-20, -15, -10, -5, 0, 5, 10]
        
        for power in test_powers:
            print(f"   Setting power to {power} dBm...")
            self.sg384.set_power(power)
            time.sleep(0.2)
            
            # Read back power
            actual_power = float(self.sg384._query('POWR?'))
            error = abs(actual_power - power)
            print(f"   ✓ Set: {power} dBm, Read: {actual_power:.1f} dBm, Error: {error:.1f} dB")
            
            self._log_data('power_set', set_power=power, actual_power=actual_power, error=error)
        
        # Test phase control
        print("\n3. Phase Control Test")
        test_phases = [0, 45, 90, 135, 180, 225, 270, 315, 360]
        
        for phase in test_phases:
            print(f"   Setting phase to {phase}°...")
            self.sg384.set_phase(phase)
            time.sleep(0.1)
            
            # Read back phase
            actual_phase = float(self.sg384._query('PHAS?'))
            error = abs(actual_phase - phase)
            print(f"   ✓ Set: {phase}°, Read: {actual_phase:.1f}°, Error: {error:.1f}°")
            
            self._log_data('phase_set', set_phase=phase, actual_phase=actual_phase, error=error)
        
        print("\n✓ Basic operation demonstration completed")
    
    def sweep_generation_demo(self):
        """Demonstrate internal phase continuous sweep generation."""
        print("\n" + "=" * 40)
        print("SWEEP GENERATION DEMONSTRATION")
        print("=" * 40)
        
        # Configure sweep parameters
        center_freq = 2.5e9  # 2.5 GHz center
        deviation = 100e6     # 100 MHz deviation
        sweep_rate = 1e6      # 1 MHz/s sweep rate
        
        print(f"Center frequency: {center_freq/1e9:.3f} GHz")
        print(f"Deviation: ±{deviation/1e6:.1f} MHz")
        print(f"Sweep rate: {sweep_rate/1e6:.1f} MHz/s")
        
        # Set center frequency
        print(f"\nSetting center frequency to {center_freq/1e9:.3f} GHz...")
        self.sg384.set_frequency(center_freq)
        time.sleep(0.2)
        
        # Configure sweep
        print("Configuring sweep parameters...")
        self.sg384._send('SFNC 0')  # Sine wave sweep
        self.sg384._send(f'SDEV {deviation}')
        self.sg384._send(f'SRAT {sweep_rate}')
        
        # Calculate sweep cycle time
        sweep_time = (2 * deviation) / sweep_rate
        print(f"Sweep cycle time: {sweep_time:.3f} seconds")
        
        # Start sweep
        print("Starting sweep...")
        self.sg384._send('SSWP 1')
        time.sleep(0.2)
        
        # Verify sweep is running
        sweep_status = self.sg384._query('SSWP?')
        if sweep_status.strip() != '1':
            print("✗ Failed to start sweep")
            return
        
        print("✓ Sweep started successfully")
        
        # Monitor frequency during sweep
        print("\nMonitoring frequency during sweep...")
        frequencies = []
        powers = []
        timestamps = []
        
        start_time = time.time()
        duration = min(sweep_time * 3, 15)  # Monitor for 3 cycles or max 15 seconds
        
        print(f"Monitoring for {duration:.1f} seconds...")
        
        while time.time() - start_time < duration:
            current_time = time.time() - start_time
            
            try:
                freq = float(self.sg384._query('FREQ?'))
                power = float(self.sg384._query('POWR?'))
                
                frequencies.append(freq)
                powers.append(power)
                timestamps.append(current_time)
                
                # Log data every 0.5 seconds
                if len(timestamps) % 5 == 0:
                    self._log_data('sweep_monitor', time=current_time, frequency=freq, power=power)
                
                time.sleep(0.1)
                
            except Exception as e:
                print(f"Error reading during sweep: {e}")
                break
        
        # Stop sweep
        print("Stopping sweep...")
        self.sg384._send('SSWP 0')
        time.sleep(0.2)
        
        # Analyze sweep results
        if frequencies:
            frequencies = np.array(frequencies)
            powers = np.array(powers)
            timestamps = np.array(timestamps)
            
            freq_range = np.max(frequencies) - np.min(frequencies)
            expected_range = 2 * deviation
            
            print(f"\n--- Sweep Results ---")
            print(f"Frequency range: {freq_range/1e6:.1f} MHz")
            print(f"Expected range: {expected_range/1e6:.1f} MHz")
            print(f"Power variation: {np.max(powers) - np.min(powers):.2f} dB")
            print(f"Data points collected: {len(frequencies)}")
            
            # Save sweep data
            self._save_sweep_data(timestamps, frequencies, powers, center_freq, deviation, sweep_rate)
            
            # Plot sweep results
            self._plot_sweep_results(timestamps, frequencies, powers)
            
            print("✓ Sweep demonstration completed")
        else:
            print("✗ No sweep data collected")
    
    def power_ramping_demo(self):
        """Demonstrate power ramping functionality."""
        print("\n" + "=" * 40)
        print("POWER RAMPING DEMONSTRATION")
        print("=" * 40)
        
        # Set frequency
        freq = 2.5e9
        print(f"Setting frequency to {freq/1e9:.3f} GHz...")
        self.sg384.set_frequency(freq)
        time.sleep(0.2)
        
        # Power ramping parameters
        start_power = -20.0
        end_power = 0.0
        step_size = 2.0  # 2 dB steps
        step_delay = 0.2  # 200ms between steps
        
        print(f"Power ramping from {start_power} dBm to {end_power} dBm")
        print(f"Step size: {step_size} dB, Step delay: {step_delay*1000:.0f} ms")
        
        powers = np.arange(start_power, end_power + step_size, step_size)
        measurements = []
        
        print("\nRamping power...")
        for i, power in enumerate(powers):
            print(f"   Step {i+1}/{len(powers)}: {power} dBm")
            self.sg384.set_power(power)
            time.sleep(step_delay)
            
            # Read back power
            actual_power = float(self.sg384._query('POWR?'))
            measurements.append((power, actual_power))
            
            self._log_data('power_ramp', step=i+1, set_power=power, actual_power=actual_power)
        
        # Analyze results
        errors = [abs(actual - set_power) for set_power, actual in measurements]
        max_error = max(errors)
        avg_error = np.mean(errors)
        
        print(f"\n--- Power Ramping Results ---")
        print(f"Maximum error: {max_error:.2f} dB")
        print(f"Average error: {avg_error:.2f} dB")
        print(f"Steps completed: {len(powers)}")
        
        # Save power ramping data
        self._save_power_ramp_data(powers, [m[1] for m in measurements])
        
        print("✓ Power ramping demonstration completed")
    
    def frequency_hopping_demo(self):
        """Demonstrate rapid frequency hopping."""
        print("\n" + "=" * 40)
        print("FREQUENCY HOPPING DEMONSTRATION")
        print("=" * 40)
        
        # Set power
        power = -10.0
        print(f"Setting power to {power} dBm...")
        self.sg384.set_power(power)
        time.sleep(0.2)
        
        # Frequency hopping pattern
        frequencies = [2.0e9, 2.5e9, 3.0e9, 2.5e9, 2.0e9, 2.3e9, 2.7e9, 2.1e9]
        hop_delay = 0.05  # 50ms between hops
        
        print(f"Frequency hopping pattern: {len(frequencies)} frequencies")
        print(f"Hop delay: {hop_delay*1000:.0f} ms")
        
        measurements = []
        start_time = time.time()
        
        print("\nStarting frequency hopping...")
        for i, freq in enumerate(frequencies):
            print(f"   Hop {i+1}/{len(frequencies)}: {freq/1e9:.3f} GHz")
            
            hop_start = time.time()
            self.sg384.set_frequency(freq)
            hop_time = time.time() - hop_start
            
            time.sleep(hop_delay)
            
            # Verify frequency
            actual_freq = float(self.sg384._query('FREQ?'))
            error = abs(actual_freq - freq)
            
            measurements.append({
                'hop': i+1,
                'set_freq': freq,
                'actual_freq': actual_freq,
                'error': error,
                'hop_time': hop_time
            })
            
            self._log_data('frequency_hop', **measurements[-1])
        
        total_time = time.time() - start_time
        
        # Analyze results
        errors = [m['error'] for m in measurements]
        hop_times = [m['hop_time'] for m in measurements]
        
        print(f"\n--- Frequency Hopping Results ---")
        print(f"Total time: {total_time:.3f} seconds")
        print(f"Average hop time: {np.mean(hop_times)*1000:.1f} ms")
        print(f"Maximum frequency error: {max(errors)/1e6:.1f} MHz")
        print(f"Average frequency error: {np.mean(errors)/1e6:.1f} MHz")
        
        # Save frequency hopping data
        self._save_frequency_hop_data(measurements)
        
        print("✓ Frequency hopping demonstration completed")
    
    def _save_sweep_data(self, timestamps, frequencies, powers, center_freq, deviation, sweep_rate):
        """Save sweep data to files."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save as NPZ
        npz_file = self.output_dir / f"sg384_sweep_{timestamp}.npz"
        np.savez(npz_file,
                 timestamps=timestamps,
                 frequencies=frequencies,
                 powers=powers,
                 center_freq=center_freq,
                 deviation=deviation,
                 sweep_rate=sweep_rate)
        
        # Save as CSV
        csv_file = self.output_dir / f"sg384_sweep_{timestamp}.csv"
        import pandas as pd
        df = pd.DataFrame({
            'timestamp_s': timestamps,
            'frequency_hz': frequencies,
            'frequency_ghz': frequencies / 1e9,
            'power_dbm': powers
        })
        df.to_csv(csv_file, index=False)
        
        # Save summary
        summary_file = self.output_dir / f"sg384_sweep_{timestamp}_summary.csv"
        summary_data = {
            'parameter': ['center_freq_hz', 'center_freq_ghz', 'deviation_hz', 'deviation_mhz', 
                         'sweep_rate_hz_per_s', 'sweep_rate_mhz_per_s', 'sweep_time_s', 'data_points'],
            'value': [center_freq, center_freq/1e9, deviation, deviation/1e6, 
                     sweep_rate, sweep_rate/1e6, (2*deviation)/sweep_rate, len(frequencies)]
        }
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_csv(summary_file, index=False)
        
        print(f"   Data saved to: {npz_file}")
        print(f"   CSV saved to: {csv_file}")
        print(f"   Summary saved to: {summary_file}")
    
    def _save_power_ramp_data(self, set_powers, actual_powers):
        """Save power ramping data to files."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save as CSV
        csv_file = self.output_dir / f"sg384_power_ramp_{timestamp}.csv"
        import pandas as pd
        df = pd.DataFrame({
            'step': range(1, len(set_powers) + 1),
            'set_power_dbm': set_powers,
            'actual_power_dbm': actual_powers,
            'error_db': [abs(actual - set_p) for set_p, actual in zip(set_powers, actual_powers)]
        })
        df.to_csv(csv_file, index=False)
        
        print(f"   Power ramping data saved to: {csv_file}")
    
    def _save_frequency_hop_data(self, measurements):
        """Save frequency hopping data to files."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save as CSV
        csv_file = self.output_dir / f"sg384_frequency_hop_{timestamp}.csv"
        import pandas as pd
        df = pd.DataFrame(measurements)
        df.to_csv(csv_file, index=False)
        
        print(f"   Frequency hopping data saved to: {csv_file}")
    
    def _plot_sweep_results(self, timestamps, frequencies, powers):
        """Plot sweep results and save as PNG."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
        
        # Frequency plot
        ax1.plot(timestamps, frequencies / 1e9, 'b-', linewidth=2)
        ax1.set_ylabel('Frequency (GHz)')
        ax1.set_title('SG384 Frequency Sweep')
        ax1.grid(True, alpha=0.3)
        
        # Power plot
        ax2.plot(timestamps, powers, 'r-', linewidth=2)
        ax2.set_xlabel('Time (s)')
        ax2.set_ylabel('Power (dBm)')
        ax2.set_title('Power During Sweep')
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Save plot
        plot_file = self.output_dir / f"sg384_sweep_plot_{timestamp}.png"
        plt.savefig(plot_file, dpi=150, bbox_inches='tight')
        print(f"   Plot saved to: {plot_file}")
        
        plt.close()
    
    def run_demo(self):
        """Run the complete SG384 demonstration."""
        if not self.connect():
            return False
        
        try:
            # Run demonstrations
            self.basic_operation_demo()
            self.sweep_generation_demo()
            self.power_ramping_demo()
            self.frequency_hopping_demo()
            
            print("\n" + "=" * 60)
            print("ALL DEMONSTRATIONS COMPLETED SUCCESSFULLY!")
            print("=" * 60)
            
            # Final device status
            self._print_device_status()
            
            return True
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Demo interrupted by user")
            return False
        except Exception as e:
            print(f"\n\n✗ Demo failed with error: {e}")
            return False
        finally:
            # Always cleanup
            self.cleanup()
    
    def cleanup(self):
        """Clean up and set device to safe state."""
        if not self.sg384:
            return
        
        print("\n--- Cleanup and Safety ---")
        
        try:
            # Stop any ongoing sweeps
            self.sg384._send('SSWP 0')
            time.sleep(0.1)
            
            # Set safe parameters
            self.sg384.set_frequency(2.5e9)  # 2.5 GHz
            self.sg384.set_power(-20.0)      # Low power
            self.sg384.set_phase(0.0)        # 0 degrees
            
            # Disable output for safety
            self.sg384._send('ENBL 0')
            time.sleep(0.1)
            
            # Verify safe state
            output_enabled = self.sg384._query('ENBL?')
            sweep_running = self.sg384._query('SSWP?')
            
            if output_enabled.strip() == '0' and sweep_running.strip() == '0':
                print("✓ Device set to safe state")
            else:
                print("⚠️  Could not verify safe state")
                
        except Exception as e:
            print(f"⚠️  Cleanup error: {e}")
        
        # Disconnect
        self.disconnect()


def main():
    """Main function to run the SG384 example."""
    parser = argparse.ArgumentParser(description='SG384 Microwave Generator Example')
    parser.add_argument('--connection-type', choices=['LAN', 'GPIB', 'RS232'], 
                       default='LAN', help='Connection type (default: LAN)')
    parser.add_argument('--ip-address', default='169.254.146.198', 
                       help='IP address for LAN connection (default: 169.254.146.198)')
    parser.add_argument('--port', type=int, default=5025, 
                       help='Port for LAN connection (default: 5025)')
    parser.add_argument('--visa-resource', default='', 
                       help='VISA resource string for GPIB/RS232 connection')
    
    args = parser.parse_args()
    
    # Build connection settings
    if args.connection_type == 'LAN':
        settings = {
            'connection_type': 'LAN',
            'ip_address': args.ip_address,
            'port': args.port
        }
    else:
        if not args.visa_resource:
            print(f"Error: --visa-resource is required for {args.connection_type} connection")
            sys.exit(1)
        
        settings = {
            'connection_type': args.connection_type,
            'visa_resource': args.visa_resource
        }
        
        if args.connection_type == 'RS232':
            settings['baud_rate'] = 115200
    
    # Create and run example
    example = SG384Example(settings)
    success = example.run_demo()
    
    if success:
        print("\n🎉 SG384 example completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ SG384 example failed!")
        sys.exit(1)


if __name__ == "__main__":
    main() 