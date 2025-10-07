#!/usr/bin/env python3
"""
Multi-Waveform ODMR Test Script

This script demonstrates how to use the new ODMR_Sweep_Counter_Multi.bas
ADbasic script with different waveform types.

Waveform Types:
- Par_7 = 0: Triangle (bidirectional, n_points = 2*N_STEPS-2)
- Par_7 = 1: Ramp/Saw (up only, n_points = N_STEPS)
- Par_7 = 2: Sine (one period, n_points = N_STEPS)
- Par_7 = 3: Square (constant, n_points = N_STEPS)
- Par_7 = 4: Noise (random, n_points = N_STEPS)
- Par_7 = 100: Custom table (n_points = N_STEPS)

Usage:
    python test_multi_waveform_odmr.py --waveform 0 --real-hardware
    python test_multi_waveform_odmr.py --waveform 2 --mock-hardware
    python test_multi_waveform_odmr.py --list-waveforms
"""

import argparse
import sys
import time
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent / '..'))

from src.Controller.adwin_gold import AdwinGoldDevice
from src.core.helper_functions import get_adwin_binary_path


def create_devices(use_real_hardware=False):
    """Create device instances."""
    if use_real_hardware:
        print("Using real hardware...")
        try:
            from src.core.device_config import load_devices_from_config
            from pathlib import Path
            
            config_path = Path(__file__).parent.parent / "src" / "config.json"
            loaded_devices, failed_devices = load_devices_from_config(config_path)
            
            if 'adwin' not in loaded_devices:
                print("❌ ADwin device not found in config")
                return None
                
            return loaded_devices['adwin']
            
        except Exception as e:
            print(f"❌ Failed to load real hardware: {e}")
            return None
    else:
        print("Using mock hardware...")
        try:
            from src.Controller import MockAdwinGoldDevice
            return MockAdwinGoldDevice()
        except Exception as e:
            print(f"❌ Failed to create mock hardware: {e}")
            return None


def test_waveform(adwin, waveform_type, n_steps=10, settle_us=500, dwell_us=2000, 
                 vmin=-1.0, vmax=1.0, square_setpoint=0.0, noise_seed=12345):
    """
    Test a specific waveform type.
    
    Args:
        adwin: ADwin device instance
        waveform_type (int): Waveform type (0-4, 100)
        n_steps (int): Number of steps
        settle_us (int): Settle time in microseconds
        dwell_us (int): Dwell time in microseconds
        vmin (float): Minimum voltage
        vmax (float): Maximum voltage
        square_setpoint (float): Square wave setpoint (for waveform 3)
        noise_seed (int): Random seed (for waveform 4)
    """
    
    waveform_names = {
        0: "Triangle (bidirectional)",
        1: "Ramp/Saw (up only)",
        2: "Sine (one period)",
        3: "Square (constant)",
        4: "Noise (random)",
        100: "Custom table"
    }
    
    print(f"\n🎯 Testing {waveform_names.get(waveform_type, 'Unknown')} waveform")
    print(f"   Steps: {n_steps}, Settle: {settle_us}µs, Dwell: {dwell_us}µs")
    print(f"   Voltage range: {vmin}V to {vmax}V")
    
    try:
        # Load the multi-waveform ADbasic script
        script_path = get_adwin_binary_path('ODMR_Sweep_Counter_Multi.TB1')
        print(f"📁 Loading script: {script_path}")
        
        # Stop any existing process
        adwin.stop_process(1)
        time.sleep(0.1)
        adwin.clear_process(1)
        time.sleep(0.1)
        
        # Load the binary
        adwin.load_process(1, script_path)
        time.sleep(0.1)
        
        # Set parameters
        print("⚙️ Setting parameters...")
        adwin.set_float_var(1, vmin)      # FPar_1: Vmin
        adwin.set_float_var(2, vmax)      # FPar_2: Vmax
        adwin.set_float_var(5, square_setpoint)  # FPar_5: Square setpoint
        
        adwin.set_int_var(1, n_steps)     # Par_1: N_STEPS
        adwin.set_int_var(2, settle_us)   # Par_2: SETTLE_US
        adwin.set_int_var(3, dwell_us)    # Par_3: DWELL_US
        adwin.set_int_var(4, 0)           # Par_4: EDGE_MODE (rising)
        adwin.set_int_var(5, 1)           # Par_5: DAC_CH (channel 1)
        adwin.set_int_var(6, 1)           # Par_6: DIR_SENSE (DIR high = up)
        adwin.set_int_var(7, waveform_type)  # Par_7: WAVEFORM
        adwin.set_int_var(8, 0)           # Par_8: PROCESSDELAY_US (auto)
        adwin.set_int_var(9, 12)          # Par_9: OVERHEAD_FACTOR (1.2x)
        adwin.set_int_var(10, 0)          # Par_10: START (idle)
        adwin.set_int_var(11, noise_seed) # Par_11: RNG_SEED
        
        # For custom table (waveform 100), populate Data_3
        if waveform_type == 100:
            print("📊 Populating custom table...")
            custom_table = []
            for i in range(min(n_steps, 1000)):  # Safety limit
                # Create a custom pattern (e.g., sawtooth with some variation)
                val = (i / (n_steps - 1)) * (vmax - vmin) + vmin
                val += 0.1 * np.sin(4 * np.pi * i / n_steps)  # Add some sine variation
                val = np.clip(val, -1.0, 1.0)  # Clamp to ±1V
                custom_table.append(int((val + 10.0) * 65535.0 / 20.0))  # Convert to DAC digits
            
            # Pad to 1000 elements
            while len(custom_table) < 1000:
                custom_table.append(custom_table[-1] if custom_table else 0)
            
            adwin.set_data_long(3, custom_table)
        
        # Start the process
        print("▶️ Starting process...")
        adwin.start_process(1)
        time.sleep(0.1)
        
        # Wait for process to be ready
        print("⏳ Waiting for process to start...")
        for i in range(50):  # 5 second timeout
            if adwin.get_process_status(1) == 1:
                break
            time.sleep(0.1)
        else:
            print("❌ Process failed to start")
            return None
        
        # Check signature
        signature = adwin.get_int_var(80)
        if signature != 7777:
            print(f"❌ Wrong signature: {signature}, expected 7777")
            return None
        
        print(f"✅ Process started, signature: {signature}")
        
        # Start the sweep
        print("🚀 Starting sweep...")
        adwin.set_int_var(10, 1)  # START
        time.sleep(0.1)
        adwin.set_int_var(20, 0)  # Clear ready flag
        
        # Wait for completion
        print("⏳ Waiting for sweep completion...")
        start_time = time.time()
        timeout = 30.0  # 30 second timeout
        
        while time.time() - start_time < timeout:
            ready = adwin.get_int_var(20)
            state = adwin.get_int_var(26)
            heartbeat = adwin.get_int_var(25)
            
            if ready == 1:
                break
            time.sleep(0.1)
        else:
            print("❌ Sweep timed out")
            return None
        
        # Read results
        print("📊 Reading results...")
        n_points = adwin.get_int_var(21)
        waveform_used = adwin.get_int_var(81)
        actual_points = adwin.get_int_var(82)
        
        print(f"✅ Sweep completed!")
        print(f"   Expected points: {n_points}")
        print(f"   Actual points: {actual_points}")
        print(f"   Waveform used: {waveform_used}")
        print(f"   Duration: {time.time() - start_time:.2f}s")
        
        # Read data arrays
        counts = adwin.read_probes('int_array', 'Data_1', 0, n_points)
        dac_digits = adwin.read_probes('int_array', 'Data_2', 0, n_points)
        
        # Convert DAC digits to voltages
        volts = [(d * 20.0 / 65535.0) - 10.0 for d in dac_digits]
        
        print(f"📈 Data summary:")
        print(f"   Counts: min={min(counts)}, max={max(counts)}, avg={np.mean(counts):.1f}")
        print(f"   Volts: min={min(volts):.3f}V, max={max(volts):.3f}V")
        
        return {
            'waveform_type': waveform_type,
            'waveform_name': waveform_names.get(waveform_type, 'Unknown'),
            'n_points': n_points,
            'counts': counts,
            'volts': volts,
            'dac_digits': dac_digits,
            'duration': time.time() - start_time
        }
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    finally:
        # Cleanup
        try:
            adwin.set_int_var(10, 0)  # Stop
            adwin.stop_process(1)
            adwin.clear_process(1)
        except:
            pass


def plot_results(results_list, save_plot=True):
    """Plot results from multiple waveform tests."""
    if not results_list:
        print("❌ No results to plot")
        return
    
    n_waveforms = len(results_list)
    fig, axes = plt.subplots(2, n_waveforms, figsize=(4*n_waveforms, 8))
    
    if n_waveforms == 1:
        axes = axes.reshape(2, 1)
    
    for i, result in enumerate(results_list):
        if result is None:
            continue
            
        # Plot counts
        axes[0, i].plot(result['counts'], 'b-', linewidth=2)
        axes[0, i].set_title(f"{result['waveform_name']}\nCounts")
        axes[0, i].set_xlabel('Step')
        axes[0, i].set_ylabel('Counts')
        axes[0, i].grid(True, alpha=0.3)
        
        # Plot voltage
        axes[1, i].plot(result['volts'], 'r-', linewidth=2)
        axes[1, i].set_title(f"Voltage Ramp")
        axes[1, i].set_xlabel('Step')
        axes[1, i].set_ylabel('Voltage (V)')
        axes[1, i].grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if save_plot:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        plot_file = f"multi_waveform_test_{timestamp}.png"
        plt.savefig(plot_file, dpi=300, bbox_inches='tight')
        print(f"📊 Plot saved: {plot_file}")
    
    plt.show()


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Test Multi-Waveform ODMR Script')
    parser.add_argument('--waveform', type=int, default=0,
                       help='Waveform type: 0=Triangle, 1=Ramp, 2=Sine, 3=Square, 4=Noise, 100=Custom')
    parser.add_argument('--real-hardware', action='store_true',
                       help='Use real hardware instead of mock')
    parser.add_argument('--mock-hardware', action='store_true',
                       help='Use mock hardware (default)')
    parser.add_argument('--test-all', action='store_true',
                       help='Test all waveform types')
    parser.add_argument('--list-waveforms', action='store_true',
                       help='List available waveform types')
    parser.add_argument('--n-steps', type=int, default=10,
                       help='Number of steps (default: 10)')
    parser.add_argument('--dwell-us', type=int, default=2000,
                       help='Dwell time in microseconds (default: 2000)')
    parser.add_argument('--vmin', type=float, default=-1.0,
                       help='Minimum voltage (default: -1.0)')
    parser.add_argument('--vmax', type=float, default=1.0,
                       help='Maximum voltage (default: 1.0)')
    parser.add_argument('--square-setpoint', type=float, default=0.0,
                       help='Square wave setpoint (default: 0.0)')
    
    args = parser.parse_args()
    
    if args.list_waveforms:
        print("Available waveform types:")
        print("  0: Triangle (bidirectional sweep)")
        print("  1: Ramp/Saw (up only, sharp return)")
        print("  2: Sine (one period)")
        print("  3: Square (constant setpoint)")
        print("  4: Noise (random step to step)")
        print("  100: Custom table (use Data_3 array)")
        return 0
    
    # Create devices
    adwin = create_devices(use_real_hardware=args.real_hardware)
    if adwin is None:
        print("❌ Failed to create ADwin device")
        return 1
    
    print(f"✅ ADwin device created: {type(adwin).__name__}")
    
    if args.test_all:
        # Test all waveform types
        waveform_types = [0, 1, 2, 3, 4, 100]
        results = []
        
        for waveform_type in waveform_types:
            result = test_waveform(
                adwin, waveform_type, 
                n_steps=args.n_steps,
                dwell_us=args.dwell_us,
                vmin=args.vmin,
                vmax=args.vmax,
                square_setpoint=args.square_setpoint
            )
            results.append(result)
        
        # Plot all results
        plot_results(results)
        
    else:
        # Test single waveform
        result = test_waveform(
            adwin, args.waveform,
            n_steps=args.n_steps,
            dwell_us=args.dwell_us,
            vmin=args.vmin,
            vmax=args.vmax,
            square_setpoint=args.square_setpoint
        )
        
        if result:
            plot_results([result])
        else:
            print("❌ Test failed")
            return 1
    
    print("✅ Test completed successfully!")
    return 0


if __name__ == "__main__":
    exit(main())
