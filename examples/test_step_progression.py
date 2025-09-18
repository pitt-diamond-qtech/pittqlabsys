#!/usr/bin/env python3
"""
Test Step Progression

Simple test to verify step progression with the original ODMR script.
"""

import sys
import time
from pathlib import Path

# Add the project root to the path (same as other working examples)
sys.path.insert(0, str(Path(__file__).parent / '..'))

# Now import the modules we need
from src.core.device_config import load_devices_from_config
from src.core.adwin_helpers import get_adwin_binary_path

def main():
    """Test step progression with debug script."""
    print("🎯 Step Progression Test")
    print("🔧 Hardware mode: Real")
    print()
    
    # Load real hardware
    print("🔧 Loading real hardware...")
    try:
        
        # Load devices
        config_path = Path("src/config.json")
        loaded_devices, failed_devices = load_devices_from_config(config_path)
        adwin = loaded_devices['adwin']
        print(f"✅ Adwin loaded: {type(adwin)}")
        print(f"✅ Connected: {adwin.is_connected}")
        
    except Exception as e:
        print(f"❌ Failed to load hardware: {e}")
        return False
    
    # Load debug ODMR script (with our fixes)
    print("\n📁 Loading debug ODMR script...")
    try:
        script_path = get_adwin_binary_path('ODMR_Sweep_Counter_Debug.TB1')
        print(f"📁 Script path: {script_path}")
        adwin.update({'process_1': {'load': str(script_path)}})
        print("✅ Script loaded successfully")
    except Exception as e:
        print(f"❌ Failed to load script: {e}")
        return False
    
    # Set up parameters
    print("\n⚙️  Setting up test parameters...")
    try:
        adwin.set_int_var(2, 5)   # Par_2: Integration time (5 cycles)
        adwin.set_int_var(3, 10)  # Par_3: Number of steps (10)
        adwin.set_int_var(11, 1)  # Par_11: Settle time (1 cycle)
        print("✅ Parameters set successfully")
    except Exception as e:
        print(f"❌ Failed to set parameters: {e}")
        return False
    
    # Start the process
    print("\n🚀 Starting counter process...")
    try:
        adwin.update({'process_1': {'running': True}})
        print("✅ Process started")
    except Exception as e:
        print(f"❌ Failed to start process: {e}")
        return False
    
    # Monitor step progression
    print("\n⏳ Monitoring step progression...")
    print("Time | Par_4 (Step) | Par_5 (Dir) | Par_7 (Complete) | Par_9 (Cycle) | Par_13 (Int) | Par_16 (Total)")
    print("--------------------------------------------------------------------------------------------------")
    
    start_time = time.time()
    max_wait_time = 15.0  # 15 second timeout
    last_step = -1
    step_count = 0
    
    while time.time() - start_time < max_wait_time:
        try:
            par_4 = adwin.get_int_var(4)    # Step index
            par_5 = adwin.get_int_var(5)    # Sweep direction
            par_7 = adwin.get_int_var(7)    # Sweep complete flag
            par_9 = adwin.get_int_var(9)    # Sweep cycle
            par_13 = adwin.get_int_var(13)  # Integration cycles
            par_16 = adwin.get_int_var(16)  # Total captured steps
            
            elapsed = time.time() - start_time
            
            # Only print when step changes
            if par_4 != last_step:
                print(f"{elapsed:5.1f}s | {par_4:11d} | {par_5:10d} | {par_7:14d} | {par_9:11d} | {par_13:10d} | {par_16:11d}")
                last_step = par_4
                step_count += 1
            
            if par_7 == 1:  # Sweep complete
                print(f"{elapsed:5.1f}s | {par_4:11d} | {par_5:10d} | {par_7:14d} | {par_9:11d} | {par_13:10d} | {par_16:11d}")
                print("✅ Sweep completed!")
                break
                
            time.sleep(0.05)  # Check every 50ms
        except Exception as e:
            print(f"❌ Error monitoring: {e}")
            break
    else:
        print("⚠️  Timeout waiting for sweep completion")
    
    print(f"\n📊 Total steps observed: {step_count}")
    print(f"📊 Expected: 20 steps (10 forward + 10 reverse)")
    
    # Stop the process
    print("\n🛑 Stopping process...")
    try:
        adwin.update({'process_1': {'running': False}})
        adwin.stop_process(1)
        print("✅ Process stopped")
    except Exception as e:
        print(f"⚠️  Error stopping process: {e}")
    
    print("\n✅ Test completed!")
    return True

if __name__ == "__main__":
    main()
