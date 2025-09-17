#!/usr/bin/env python3
"""
Debug ODMR Counter Script

This script helps diagnose counting issues with the ODMR sweep counter.
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
    Debug the ODMR counter by monitoring all parameters.
    
    Args:
        use_real_hardware (bool): Whether to use real hardware
        config_path (str): Path to config.json file
    """
    print("\n" + "="*60)
    print("ODMR COUNTER DEBUG SESSION")
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
    
    # Use the compiled debug version for detailed diagnostics
    from src.core.adwin_helpers import get_adwin_binary_path
    
    try:
        # Stop any running process
        adwin.stop_process(1)
        time.sleep(0.1)
        adwin.clear_process(1)
        
        # Load the debug ODMR script (with detailed diagnostics)
        script_path = get_adwin_binary_path('ODMR_Sweep_Counter_Debug.TB1')
        print(f"📁 Loading debug ODMR script: {script_path}")
        adwin.update({'process_1': {'load': str(script_path)}})
        
        # Set up parameters matching real ODMR experiment (5ms integration time)
        print("⚙️  Setting up test parameters...")
        adwin.set_int_var(2, 5)      # Par_2: Integration time (5 cycles = ~5ms) - CRITICAL for speed
        adwin.set_int_var(3, 10)     # Par_3: Number of steps (10 steps)
        adwin.set_int_var(11, 1)     # Par_11: Settle time (1 cycle = ~1ms)
        
        print("🚀 Starting counter process...")
        adwin.update({'process_1': {'running': True}})
        
        # Monitor parameters for 2 seconds (should see all 10 steps with 5ms integration)
        print("\n📊 Monitoring parameters (2 seconds)...")
        print("Time | Par_1 | Par_4 | Par_8 | Par_12 | Par_13 | Par_14 | Par_15")
        print("-" * 70)
        
        start_time = time.time()
        while time.time() - start_time < 2:
            try:
                # Read all diagnostic parameters from debug script
                par_1 = adwin.get_int_var(1)    # Raw counter
                par_4 = adwin.get_int_var(4)    # Step index
                par_8 = adwin.get_int_var(8)    # Total counts
                par_12 = adwin.get_int_var(12)  # Event cycles
                par_13 = adwin.get_int_var(13)  # Integration cycles
                par_14 = adwin.get_int_var(14)  # Raw counter before clear
                par_15 = adwin.get_int_var(15)  # Counter mode
                
                elapsed = time.time() - start_time
                print(f"{elapsed:5.1f} | {par_1:5d} | {par_4:5d} | {par_8:5d} | {par_12:6d} | {par_13:6d} | {par_14:6d} | {par_15:5d}")
                
                time.sleep(0.05)  # Monitor every 50ms to catch 6ms steps
                
            except Exception as e:
                print(f"❌ Error reading parameters: {e}")
                break
        
        print("\n🛑 Stopping process...")
        adwin.update({'process_1': {'running': False}})
        adwin.stop_process(1)
        time.sleep(0.1)
        adwin.clear_process(1)
        
        print("\n📋 Final Analysis:")
        print("=" * 50)
        print("Key Debug Parameters to Check:")
        print("1. Par_1 (Raw Counter): Should show counts if detector is working")
        print("2. Par_4 (Step Index): Should increment from 0 to 9 (10 steps total)")
        print("3. Par_8 (Total Counts): Should accumulate counts over integration time")
        print("4. Par_12 (Event Cycles): Should increment continuously (shows process is running)")
        print("5. Par_13 (Integration Cycles): Should increment during integration time")
        print("6. Par_14 (Raw Counter Before Clear): Should show accumulated counts before clearing")
        print("7. Par_15 (Counter Mode): Should be 8 (falling edge) - same as other working scripts")
        print("\nIf Par_1 is always 0:")
        print("- Check detector connection to Adwin input")
        print("- Verify detector is powered on and working")
        print("- Check if detector output is connected to correct input")
        print("- If Par_12 is incrementing but Par_1 is 0, detector signal issue")
        print("- If Par_13 is incrementing but Par_8 is 0, counter clearing issue")
        print("\nIf Par_1 shows counts but Par_8 is 0:")
        print("- Counter clearing logic issue (should be fixed now)")
        print("- Check if integration time is too short")
        
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
    parser = argparse.ArgumentParser(description='Debug ODMR Counter')
    parser.add_argument('--real-hardware', action='store_true',
                       help='Use real hardware instead of mock hardware')
    parser.add_argument('--config', type=str, default=None,
                       help='Path to config.json file (default: src/config.json)')
    
    args = parser.parse_args()
    
    print("🎯 ODMR Counter Debug Tool")
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
