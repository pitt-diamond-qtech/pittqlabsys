#!/usr/bin/env python3
"""
Debug ODMR Counter Script

This script helps diagnose counting issues with the new triangle sweep counter.
It loads the debug version of the ADbasic script and monitors all parameters.

Usage:
    python debug_odmr_counter.py --real-hardware
"""

import argparse
import sys
import time
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent / '..'))

from src.core.device_config import load_devices_from_config


def debug_odmr_counter(use_real_hardware=False, config_path=None):
    """
    Debug the ODMR counter by monitoring all parameters with new triangle sweep.
    
    Args:
        use_real_hardware (bool): Whether to use real hardware
        config_path (str): Path to config.json file
    """
    print("\n" + "="*60)
    print("ODMR COUNTER DEBUG SESSION - NEW TRIANGLE SWEEP")
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
                return debug_mock_counter()
            
            adwin = loaded_devices['adwin']
            print(f"✅ Adwin loaded: {type(adwin)}")
            print(f"✅ Connected: {adwin.is_connected}")
            
        except Exception as e:
            print(f"❌ Failed to load real hardware: {e}")
            return debug_mock_counter()
    else:
        print("🔧 Using mock hardware...")
        return debug_mock_counter()
    
    print("\n🔍 Starting counter diagnostics...")
    
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
        
        # Monitor parameters for 2 seconds
        print("\n📊 Monitoring parameters (2 seconds)...")
        print("Time | Par_20 | Par_21 | Par_22 | Par_23 | Par_24 | Par_25")
        print("-" * 60)
        
        start_time = time.time()
        while time.time() - start_time < 2:
            try:
                # Read all diagnostic parameters from new script
                par_20 = adwin.get_int_var(20)  # Sweep ready flag
                par_21 = adwin.get_int_var(21)  # Number of points
                par_22 = adwin.get_int_var(22)  # Current step index
                par_23 = adwin.get_int_var(23)  # Current position in triangle
                par_24 = adwin.get_float_var(24)  # Current voltage
                par_25 = adwin.get_int_var(25)  # Event cycle counter
                
                elapsed = time.time() - start_time
                print(f"{elapsed:5.1f} | {par_20:6d} | {par_21:6d} | {par_22:6d} | {par_23:6d} | {par_24:6.2f} | {par_25:6d}")
                
                time.sleep(0.1)  # Monitor every 100ms
                
            except Exception as e:
                print(f"❌ Error reading parameters: {e}")
                break
        
        print("\n🛑 Stopping process...")
        adwin.set_int_var(10, 0)  # Par_10: START (0=stop)
        adwin.stop_process(1)
        time.sleep(0.1)
        adwin.clear_process(1)
        
        print("\n📋 Final Analysis:")
        print("=" * 50)
        print("Key Debug Parameters to Check:")
        print("1. Par_20 (Sweep Ready): 0=in progress, 1=ready for Python to read")
        print("2. Par_21 (Number of Points): Should be 18 (10 forward + 8 reverse, no repeated endpoints)")
        print("3. Par_22 (Current Step): Should increment from 0 to 17 during sweep")
        print("4. Par_23 (Position): Should go 0,1,2,3,4,5,6,7,8,9,8,7,6,5,4,3,2,1 (triangle)")
        print("5. Par_24 (Voltage): Should sweep from -1.0V to +1.0V and back")
        print("6. Par_25 (Event Cycles): Should increment continuously (shows process is running)")
        print("\nExpected Pattern:")
        print("- Forward sweep: Par_23 goes 0,1,2,3,4,5,6,7,8,9")
        print("- Reverse sweep: Par_23 goes 8,7,6,5,4,3,2,1 (no repeated endpoints)")
        print("- Total points: 18 (not 20 like old script)")
        print("- Voltage: -1.0V to +1.0V and back to -1.0V")
        print("\nIf Par_25 is not incrementing:")
        print("- Process is not running or crashed")
        print("- Check ADbasic script compilation")
        print("\nIf Par_20 stays 0:")
        print("- Sweep is still in progress")
        print("- Wait longer or check if process is stuck")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during debug session: {e}")
        import traceback
        traceback.print_exc()
        return False


def debug_mock_counter():
    """Debug with mock hardware."""
    print("🔧 Mock hardware debug not implemented yet")
    print("   (This would simulate the counter behavior)")
    return True


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Debug ODMR Counter - New Triangle Sweep')
    parser.add_argument('--real-hardware', action='store_true',
                       help='Use real hardware instead of mock hardware')
    parser.add_argument('--config', type=str, default=None,
                       help='Path to config.json file (default: src/config.json)')
    
    args = parser.parse_args()
    
    print("🎯 ODMR Counter Debug Tool - New Triangle Sweep")
    print(f"🔧 Hardware mode: {'Real' if args.real_hardware else 'Mock'}")
    
    success = debug_odmr_counter(args.real_hardware, args.config)
    
    if success:
        print("\n✅ Debug session completed!")
    else:
        print("\n❌ Debug session failed!")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())