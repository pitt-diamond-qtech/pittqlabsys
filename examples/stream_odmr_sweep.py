#!/usr/bin/env python3
"""
Stream ODMR Sweep Results

Real-time streaming of ODMR sweep data with live plotting.
Continuously runs sweeps and displays results as they come in.

Usage:
    python stream_odmr_sweep.py --real-hardware
"""

import argparse
import sys
import time
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from collections import deque

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent / '..'))

from src.core.device_config import load_devices_from_config


def v_to_d(v):
    """Convert voltage to DAC digits."""
    return int(round((v + 10.0) * 65535.0 / 20.0))


def d_to_v(d):
    """Convert DAC digits to voltage."""
    return (d * 20.0 / 65535.0) - 10.0


class ODMRStreamer:
    """Real-time ODMR sweep data streamer with live plotting."""
    
    def __init__(self, adwin, n_steps=10, vmin=-1.0, vmax=1.0, 
                 settle_us=1000, dwell_us=5000, dac_ch=1):
        self.adwin = adwin
        self.n_steps = n_steps
        self.vmin = vmin
        self.vmax = vmax
        self.settle_us = settle_us
        self.dwell_us = dwell_us
        self.dac_ch = dac_ch
        self.expected_points = 2 * n_steps - 2
        
        # Data storage
        self.sweep_count = 0
        self.all_voltages = []
        self.all_counts = []
        self.sweep_times = []
        
        # Setup plotting
        self.setup_plot()
        
    def setup_plot(self):
        """Setup the live plotting window."""
        plt.ion()  # Interactive mode
        self.fig, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(12, 8))
        
        # Top plot: Voltage vs Counts (scatter)
        self.ax1.set_xlabel('Voltage (V)')
        self.ax1.set_ylabel('Counts')
        self.ax1.set_title('ODMR Sweep - Live Data')
        self.ax1.grid(True, alpha=0.3)
        
        # Bottom plot: Counts vs Time (line plot)
        self.ax2.set_xlabel('Time (s)')
        self.ax2.set_ylabel('Counts')
        self.ax2.set_title('Counts vs Time')
        self.ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.show(block=False)
        
    def setup_sweep(self):
        """Setup the sweep parameters."""
        print("⚙️  Setting up sweep parameters...")
        self.adwin.set_float_var(1, self.vmin)  # FPar_1: Vmin
        self.adwin.set_float_var(2, self.vmax)  # FPar_2: Vmax
        self.adwin.set_int_var(1, self.n_steps)  # Par_1: N_STEPS
        self.adwin.set_int_var(2, self.settle_us)  # Par_2: SETTLE_US
        self.adwin.set_int_var(3, self.dwell_us)  # Par_3: DWELL_US
        self.adwin.set_int_var(4, self.dac_ch)  # Par_4: DAC_CH
        self.adwin.set_int_var(10, 0)  # Par_10: START (0=stop initially)
        
    def wait_for_sweep(self, timeout=5.0):
        """Wait for a sweep to complete."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                par_20 = self.adwin.get_int_var(20)  # Sweep ready flag
                par_21 = self.adwin.get_int_var(21)  # Number of points
                par_22 = self.adwin.get_int_var(22)  # Current step
                
                if par_20 == 1:  # Sweep ready
                    return True
                    
                time.sleep(0.01)  # Check every 10ms
                
            except Exception as e:
                print(f"❌ Error reading parameters: {e}")
                return False
                
        return False
        
    def read_sweep_data(self):
        """Read the completed sweep data."""
        try:
            # Get number of points
            n_points = self.adwin.get_int_var(21)
            if n_points != self.expected_points:
                print(f"⚠️  Unexpected n_points: {n_points}, expected {self.expected_points}")
                return None, None
                
            # Read arrays
            try:
                counts = self.adwin.read_probes('int_array', 1, n_points)
                dac_digits = self.adwin.read_probes('int_array', 2, n_points)
            except Exception:
                # Fallback
                try:
                    counts = self.adwin.get_data(1, n_points)
                    dac_digits = self.adwin.get_data(2, n_points)
                except Exception:
                    print("❌ Failed to read arrays")
                    return None, None
                    
            # Convert to voltages
            voltages = [d_to_v(d) for d in dac_digits]
            
            return counts, voltages
            
        except Exception as e:
            print(f"❌ Error reading sweep data: {e}")
            return None, None
            
    def update_plot(self, counts, voltages):
        """Update the live plot with new data."""
        # Add to data storage
        self.all_voltages.extend(voltages)
        self.all_counts.extend(counts)
        self.sweep_times.extend([time.time()] * len(counts))
        
        # Clear and replot
        self.ax1.clear()
        self.ax2.clear()
        
        # Top plot: Voltage vs Counts
        self.ax1.scatter(self.all_voltages, self.all_counts, alpha=0.6, s=20)
        self.ax1.set_xlabel('Voltage (V)')
        self.ax1.set_ylabel('Counts')
        self.ax1.set_title(f'ODMR Sweep - Live Data (Sweep #{self.sweep_count})')
        self.ax1.grid(True, alpha=0.3)
        
        # Bottom plot: Counts vs Time
        if len(self.all_counts) > 0:
            times = np.array(self.sweep_times) - self.sweep_times[0]
            self.ax2.plot(times, self.all_counts, 'b-', alpha=0.7)
            self.ax2.set_xlabel('Time (s)')
            self.ax2.set_ylabel('Counts')
            self.ax2.set_title('Counts vs Time')
            self.ax2.grid(True, alpha=0.3)
        
        # Refresh display
        plt.draw()
        plt.pause(0.01)
        
    def run_continuous(self, max_sweeps=50):
        """Run continuous sweeps with live plotting."""
        print(f"🚀 Starting continuous ODMR sweeps (max {max_sweeps})")
        print("🛑 Stop methods:")
        print("   - Press Ctrl+C to stop immediately")
        print("   - Close the plot window to stop")
        print("   - Wait for max sweeps to complete")
        print()
        
        try:
            while max_sweeps == 0 or self.sweep_count < max_sweeps:
                # Clear ready flag to enable next sweep
                self.adwin.set_int_var(20, 0)
                
                # Start sweep
                self.adwin.set_int_var(10, 1)
                
                # Wait for completion
                if not self.wait_for_sweep():
                    print("⏰ Timeout waiting for sweep")
                    break
                    
                # Read data
                counts, voltages = self.read_sweep_data()
                if counts is None:
                    print("❌ Failed to read sweep data")
                    break
                    
                # Update plot
                self.update_plot(counts, voltages)
                
                self.sweep_count += 1
                print(f"✅ Sweep #{self.sweep_count} completed ({len(counts)} points)")
                
                # Check if plot window is still open
                if not plt.get_fignums():
                    print("🛑 Plot window closed - stopping sweeps")
                    break
                
                # Small delay between sweeps
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            print("\n🛑 Stopping continuous sweeps...")
            
        finally:
            # Cleanup
            self.cleanup()
            
    def cleanup(self):
        """Clean up resources."""
        try:
            self.adwin.set_int_var(10, 0)  # Stop sweep
            self.adwin.set_int_var(20, 0)  # Clear ready flag
        except Exception:
            pass
            
        print(f"📊 Total sweeps completed: {self.sweep_count}")
        print(f"📊 Total data points: {len(self.all_counts)}")


def stream_odmr_sweep(use_real_hardware=False, config_path=None, 
                     n_steps=10, vmin=-1.0, vmax=1.0, 
                     settle_us=1000, dwell_us=5000, max_sweeps=50):
    """Main streaming function."""
    print("\n" + "="*60)
    print("ODMR SWEEP STREAMING - LIVE PLOTTING")
    print("="*60)
    
    if use_real_hardware:
        print("🔧 Loading real hardware...")
        try:
            if config_path is None:
                config_path = Path(__file__).parent.parent / "src" / "config.json"
            else:
                config_path = Path(config_path)
            
            loaded_devices, failed_devices = load_devices_from_config(config_path)
            
            if failed_devices:
                print(f"⚠️  Some devices failed to load: {list(failed_devices.keys())}")
                
            if not loaded_devices:
                print("❌ No devices loaded")
                return False
                
            adwin = loaded_devices['adwin']
            print(f"✅ Adwin loaded: {type(adwin)}")
            print(f"✅ Connected: {adwin.is_connected}")
            
        except Exception as e:
            print(f"❌ Failed to load real hardware: {e}")
            return False
    else:
        print("❌ Mock hardware not implemented for streaming")
        return False
    
    # Load the triangle sweep script
    from src.core.adwin_helpers import get_adwin_binary_path
    
    try:
        # Stop any running process
        adwin.stop_process(1)
        time.sleep(0.1)
        adwin.clear_process(1)
        
        # Load script
        script_path = get_adwin_binary_path('ODMR_Sweep_Counter_Debug.TB1')
        print(f"📁 Loading script: {script_path}")
        adwin.update({'process_1': {'load': str(script_path)}})
        adwin.start_process(1)
        
        # Create streamer and run
        streamer = ODMRStreamer(adwin, n_steps, vmin, vmax, settle_us, dwell_us)
        streamer.setup_sweep()
        streamer.run_continuous(max_sweeps)
        
        return True
        
    except Exception as e:
        print(f"❌ Error during streaming: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Cleanup
        try:
            adwin.set_int_var(10, 0)
            adwin.stop_process(1)
            time.sleep(0.1)
            adwin.clear_process(1)
        except Exception:
            pass


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Stream ODMR Sweep Results')
    parser.add_argument('--real-hardware', action='store_true',
                       help='Use real hardware instead of mock hardware')
    parser.add_argument('--config', type=str, default=None,
                       help='Path to config.json file')
    parser.add_argument('--n-steps', type=int, default=10,
                       help='Number of steps per sweep (default: 10)')
    parser.add_argument('--vmin', type=float, default=-1.0,
                       help='Minimum voltage (default: -1.0V)')
    parser.add_argument('--vmax', type=float, default=1.0,
                       help='Maximum voltage (default: 1.0V)')
    parser.add_argument('--settle-us', type=int, default=1000,
                       help='Settle time in microseconds (default: 1000)')
    parser.add_argument('--dwell-us', type=int, default=5000,
                       help='Dwell time in microseconds (default: 5000)')
    parser.add_argument('--max-sweeps', type=int, default=10,
                       help='Maximum number of sweeps (default: 10, use 0 for unlimited)')
    
    args = parser.parse_args()
    
    print("🎯 ODMR Sweep Streaming Tool")
    print(f"🔧 Hardware mode: {'Real' if args.real_hardware else 'Mock'}")
    print(f"📊 Sweep parameters: {args.n_steps} steps, {args.vmin}V to {args.vmax}V")
    print(f"⏱️  Timing: {args.settle_us}μs settle, {args.dwell_us}μs dwell")
    
    success = stream_odmr_sweep(
        args.real_hardware, args.config, 
        args.n_steps, args.vmin, args.vmax,
        args.settle_us, args.dwell_us, args.max_sweeps
    )
    
    if success:
        print("\n✅ Streaming completed!")
    else:
        print("\n❌ Streaming failed!")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
