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
    
    # Load the debug version of the ADbasic script
    debug_script_path = Path(__file__).parent.parent / "src" / "Controller" / "binary_files" / "ADbasic" / "ODMR_Sweep_Counter_Debug.bas"
    
    if not debug_script_path.exists():
        print(f"❌ Debug script not found: {debug_script_path}")
        return False
    
    try:
        # Stop any running process
        adwin.stop_process(1)
        time.sleep(0.1)
        adwin.clear_process(1)
        
        # Load the debug script
        print(f"📁 Loading debug script: {debug_script_path}")
        adwin.update({'process_1': {'load': str(debug_script_path)}})
        
        # Set up parameters for a short test
        print("⚙️  Setting up test parameters...")
        adwin.set_int_var(2, 1000)   # Par_2: Integration time (1000 cycles)
        adwin.set_int_var(3, 5)      # Par_3: Number of steps (5 steps)
        adwin.set_int_var(11, 100)   # Par_11: Settle time (100 cycles)
        
        print("🚀 Starting counter process...")
        adwin.update({'process_1': {'running': True}})
        
        # Monitor parameters for 10 seconds
        print("\n📊 Monitoring parameters (10 seconds)...")
        print("Time | Par_1 | Par_4 | Par_8 | Par_12 | Par_13 | Par_14 | Par_15")
        print("-" * 70)
        
        start_time = time.time()
        while time.time() - start_time < 10:
            try:
                # Read all diagnostic parameters
                par_1 = adwin.get_int_var(1)    # Raw counter
                par_4 = adwin.get_int_var(4)    # Step index
                par_8 = adwin.get_int_var(8)    # Total counts
                par_12 = adwin.get_int_var(12)  # Event cycles
                par_13 = adwin.get_int_var(13)  # Integration cycles
                par_14 = adwin.get_int_var(14)  # Raw counter before clear
                par_15 = adwin.get_int_var(15)  # Counter mode
                
                elapsed = time.time() - start_time
                print(f"{elapsed:5.1f} | {par_1:5d} | {par_4:5d} | {par_8:5d} | {par_12:6d} | {par_13:6d} | {par_14:6d} | {par_15:5d}")
                
                time.sleep(0.5)
                
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
        print("Key Issues to Check:")
        print("1. Par_1 (Raw Counter): Should show counts if detector is working")
        print("2. Par_12 (Event Cycles): Should increment continuously")
        print("3. Par_13 (Integration Cycles): Should increment during integration")
        print("4. Par_14 (Raw Counter Before Clear): Should show accumulated counts")
        print("5. Par_15 (Counter Mode): 0=rising edge, 8=falling edge")
        print("\nIf Par_1 is always 0:")
        print("- Check detector connection")
        print("- Try changing counter mode (rising vs falling edge)")
        print("- Verify detector is powered on")
        print("- Check if detector output is inverted")
        
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
