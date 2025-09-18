#!/usr/bin/env python3
"""
Debug ODMR Arrays Script

This script waits for a complete ODMR sweep and then reads all the data arrays
from the Adwin to verify step progression and data capture with the new triangle sweep.

Usage:
    python debug_odmr_arrays.py --real-hardware
"""

import argparse
import sys
import time
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent / '..'))

from src.core.device_config import load_devices_from_config


def debug_odmr_arrays(use_real_hardware=False, config_path=None):
    """
    Debug the ODMR arrays by waiting for complete sweep and reading all data.
    
    Args:
        use_real_hardware (bool): Whether to use real hardware
        config_path (str): Path to config.json file
    """
    print("\n" + "="*60)
    print("ODMR ARRAYS DEBUG SESSION - NEW TRIANGLE SWEEP")
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
                for device_name, error in failed_devices.items():
                    print(f"  - {device_name}: {error}")
            
            if not loaded_devices:
                print("❌ No devices loaded, falling back to mock hardware")
                return debug_mock_arrays()
            
            adwin = loaded_devices['adwin']
            print(f"✅ Adwin loaded: {type(adwin)}")
            print(f"✅ Connected: {adwin.is_connected}")
            
        except Exception as e:
            print(f"❌ Failed to load real hardware: {e}")
            return debug_mock_arrays()
    else:
        print("🔧 Using mock hardware...")
        return debug_mock_arrays()
    
    print("\n🔍 Starting array diagnostics...")
    
    # Use the new triangle sweep debug script
    from src.core.adwin_helpers import get_adwin_binary_path
    
    try:
        # Stop any running process
        adwin.stop_process(1)
        time.sleep(0.1)
        adwin.clear_process(1)
        
        # Load the new triangle sweep debug script
        script_path = get_adwin_binary_path('ODMR_Sweep_Counter_Debug.TB1')
        print(f"📁 Loading new triangle sweep debug script: {script_path}")
        adwin.update({'process_1': {'load': str(script_path)}})
        
        # Set up parameters for new script
        print("⚙️  Setting up test parameters...")
        adwin.set_float_var(1, -1.0)  # FPar_1: Vmin (-1.0V)
        adwin.set_float_var(2, 1.0)   # FPar_2: Vmax (+1.0V)
        adwin.set_int_var(1, 10)      # Par_1: N_STEPS (10 steps)
        adwin.set_int_var(2, 1000)    # Par_2: SETTLE_US (1ms)
        adwin.set_int_var(3, 5000)    # Par_3: DWELL_US (5ms)
        adwin.set_int_var(4, 1)       # Par_4: DAC_CH (1)
        adwin.set_int_var(10, 0)      # Par_10: START (0=stop initially)
        
        print("🚀 Starting triangle sweep...")
        adwin.set_int_var(10, 1)  # Par_10: START (1=run)
        
        # Wait for sweep to complete (monitor Par_20 = sweep ready flag)
        print("\n⏳ Waiting for sweep to complete...")
        print("Monitoring Par_20 (sweep ready flag)...")
        
        start_time = time.time()
        timeout = 10  # 10 second timeout
        
        while time.time() - start_time < timeout:
            try:
                par_20 = adwin.get_int_var(20)    # Sweep ready flag
                par_21 = adwin.get_int_var(21)    # Number of points
                par_22 = adwin.get_int_var(22)    # Current step index
                par_25 = adwin.get_int_var(25)    # Event cycle counter
                
                elapsed = time.time() - start_time
                print(f"  {elapsed:5.1f}s | Par_20={par_20} | Par_21={par_21} | Par_22={par_22} | Par_25={par_25}")
                
                if par_20 == 1:  # Sweep ready
                    print("✅ Sweep completed!")
                    break
                    
                time.sleep(0.1)  # Check every 100ms
                
            except Exception as e:
                print(f"❌ Error reading parameters: {e}")
                break
        else:
            print("⏰ Timeout waiting for sweep completion")
            return False
        
        # Read all the data arrays
        print("\n📊 Reading data arrays...")
        
        # Get the number of points from the script
        n_points = adwin.get_int_var(21)
        print(f"📊 Number of points in sweep: {n_points}")
        
        # Read the main data arrays using the correct method
        try:
            # Read arrays using read_probes with correct array types
            counts = adwin.read_probes('int_array', 1, n_points)  # Data_1: counts per step
            dac_digits = adwin.read_probes('int_array', 2, n_points)  # Data_2: DAC digits per step
            
        except Exception as e:
            print(f"⚠️  Error reading arrays with read_probes: {e}")
            print("   Trying alternative method...")
            
            # Fallback: try reading individual elements
            counts = []
            dac_digits = []
            
            # Read first n_points elements of each array
            for i in range(n_points):
                try:
                    counts.append(adwin.get_int_var(1 + i))
                    dac_digits.append(adwin.get_int_var(1001 + i))
                except:
                    break
        
        print(f"📊 Counts array length: {len(counts)}")
        print(f"📊 DAC digits array length: {len(dac_digits)}")
        
        # Analyze the captured data
        print("\n📋 Analysis of Captured Data:")
        print("=" * 50)
        
        if len(counts) > 0:
            print(f"✅ Successfully captured {len(counts)} data points")
            
            # Show first 20 captured points
            print("\nFirst 20 captured points:")
            print("Index | Counts | DAC Digits | Voltage (V)")
            print("-" * 45)
            for i in range(min(20, len(counts))):
                count = counts[i] if i < len(counts) else 0
                dac = dac_digits[i] if i < len(dac_digits) else 0
                # Convert DAC digits to voltage: (dac * 20.0 / 65535.0) - 10.0
                voltage = (dac * 20.0 / 65535.0) - 10.0
                print(f"{i:5d} | {count:6d} | {dac:10d} | {voltage:10.3f}")
            
            # Check for expected pattern
            print("\nPattern Analysis:")
            if len(counts) >= 18:  # Should have 18 points (10 forward + 8 reverse)
                print("✅ Captured enough points for complete triangle sweep")
                
                # Check forward sweep (first 10 points)
                forward_counts = counts[:10]
                forward_voltages = [(dac_digits[i] * 20.0 / 65535.0) - 10.0 for i in range(10)]
                print(f"Forward sweep counts: {forward_counts}")
                print(f"Forward sweep voltages: {[f'{v:.2f}' for v in forward_voltages]}")
                
                # Check reverse sweep (next 8 points)
                if len(counts) >= 18:
                    reverse_counts = counts[10:18]
                    reverse_voltages = [(dac_digits[i] * 20.0 / 65535.0) - 10.0 for i in range(10, 18)]
                    print(f"Reverse sweep counts: {reverse_counts}")
                    print(f"Reverse sweep voltages: {[f'{v:.2f}' for v in reverse_voltages]}")
                
                # Verify voltage progression
                expected_forward_voltages = [-1.0 + i * 2.0 / 9.0 for i in range(10)]  # -1.0 to +1.0
                expected_reverse_voltages = [1.0 - i * 2.0 / 9.0 for i in range(1, 9)]  # +0.78 to -0.78 (no repeated endpoints)
                
                print(f"\nExpected forward voltages: {[f'{v:.2f}' for v in expected_forward_voltages]}")
                print(f"Expected reverse voltages: {[f'{v:.2f}' for v in expected_reverse_voltages]}")
                
                # Check if voltages are close to expected (within 0.1V tolerance)
                forward_ok = all(abs(actual - expected) < 0.1 for actual, expected in zip(forward_voltages, expected_forward_voltages))
                reverse_ok = all(abs(actual - expected) < 0.1 for actual, expected in zip(reverse_voltages, expected_reverse_voltages))
                
                if forward_ok:
                    print("✅ Forward sweep voltage progression correct")
                else:
                    print("❌ Forward sweep voltage progression incorrect")
                
                if reverse_ok:
                    print("✅ Reverse sweep voltage progression correct")
                else:
                    print("❌ Reverse sweep voltage progression incorrect")
                
            else:
                print(f"⚠️  Only captured {len(counts)} points, expected 18 (10 forward + 8 reverse)")
        else:
            print("❌ No data points captured!")
        
        # Check data arrays
        print("\nData Array Analysis:")
        print(f"Counts: {counts[:10]}...")
        print(f"DAC digits: {dac_digits[:10]}...")
        
        print("\n🛑 Stopping process...")
        adwin.set_int_var(10, 0)  # Par_10: START (0=stop)
        adwin.stop_process(1)
        time.sleep(0.1)
        adwin.clear_process(1)
        
        return True
        
    except Exception as e:
        print(f"❌ Error during debug session: {e}")
        import traceback
        traceback.print_exc()
        return False


def debug_mock_arrays():
    """Debug with mock hardware."""
    print("🔧 Mock hardware debug not implemented yet")
    print("   (This would simulate the array behavior)")
    return True


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Debug ODMR Arrays - New Triangle Sweep')
    parser.add_argument('--real-hardware', action='store_true',
                       help='Use real hardware instead of mock hardware')
    parser.add_argument('--config', type=str, default=None,
                       help='Path to config.json file (default: src/config.json)')
    
    args = parser.parse_args()
    
    print("🎯 ODMR Arrays Debug Tool - New Triangle Sweep")
    print(f"🔧 Hardware mode: {'Real' if args.real_hardware else 'Mock'}")
    
    success = debug_odmr_arrays(args.real_hardware, args.config)
    
    if success:
        print("\n✅ Debug session completed!")
    else:
        print("\n❌ Debug session failed!")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())