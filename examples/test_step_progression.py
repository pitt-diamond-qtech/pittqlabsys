#!/usr/bin/env python3
"""
Test Step Progression

Simple test to verify step progression with the new triangle sweep script.
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
    """Test step progression with new triangle sweep script."""
    print("🎯 Step Progression Test - New Triangle Sweep")
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
    
    # Load new triangle sweep script
    print("\n📁 Loading new triangle sweep script...")
    try:
        script_path = get_adwin_binary_path('ODMR_Sweep_Counter_Debug.TB1')
        print(f"📁 Script path: {script_path}")
        adwin.update({'process_1': {'load': str(script_path)}})
        print("✅ Script loaded successfully")
    except Exception as e:
        print(f"❌ Failed to load script: {e}")
        return False
    
    # Set up parameters for new script
    print("\n⚙️  Setting up test parameters...")
    try:
        # New parameter mapping:
        # FPar_1 = Vmin (-1.0V for SG384)
        # FPar_2 = Vmax (+1.0V for SG384)
        # Par_1 = N_STEPS (10 steps)
        # Par_2 = SETTLE_US (1000 microseconds = 1ms)
        # Par_3 = DWELL_US (5000 microseconds = 5ms)
        # Par_4 = DAC_CH (1)
        # Par_10 = START (0=stop initially)
        
        adwin.set_float_var(1, -1.0)  # FPar_1: Vmin (-1.0V)
        adwin.set_float_var(2, 1.0)   # FPar_2: Vmax (+1.0V)
        adwin.set_int_var(1, 10)      # Par_1: N_STEPS (10 steps)
        adwin.set_int_var(2, 1000)    # Par_2: SETTLE_US (1ms)
        adwin.set_int_var(3, 5000)    # Par_3: DWELL_US (5ms)
        adwin.set_int_var(4, 1)       # Par_4: DAC_CH (1)
        adwin.set_int_var(10, 0)      # Par_10: START (0=stop)
        print("✅ Parameters set successfully")
    except Exception as e:
        print(f"❌ Failed to set parameters: {e}")
        return False
    
    # Start the process
    print("\n🚀 Starting triangle sweep...")
    try:
        adwin.set_int_var(10, 1)  # Par_10: START (1=run)
        print("✅ Sweep started")
    except Exception as e:
        print(f"❌ Failed to start sweep: {e}")
        return False
    
    # Monitor sweep progression
    print("\n⏳ Monitoring sweep progression...")
    print("Time | Par_20 (Ready) | Par_21 (Points) | Par_22 (Step) | Par_23 (Pos) | Par_24 (Volt) | Par_25 (Event)")
    print("--------------------------------------------------------------------------------------------------------")
    
    start_time = time.time()
    max_wait_time = 15.0  # 15 second timeout
    last_step = -1
    step_count = 0
    
    while time.time() - start_time < max_wait_time:
        try:
            par_20 = adwin.get_int_var(20)  # Sweep ready flag
            par_21 = adwin.get_int_var(21)  # Number of points
            par_22 = adwin.get_int_var(22)  # Current step index
            par_23 = adwin.get_int_var(23)  # Current position in triangle
            par_24 = adwin.get_float_var(24)  # Current voltage
            par_25 = adwin.get_int_var(25)  # Event cycle counter
            
            elapsed = time.time() - start_time
            
            # Only print when step changes
            if par_22 != last_step:
                print(f"{elapsed:5.1f}s | {par_20:13d} | {par_21:12d} | {par_22:10d} | {par_23:9d} | {par_24:9.2f} | {par_25:9d}")
                last_step = par_22
                step_count += 1
            
            if par_20 == 1:  # Sweep ready
                print(f"{elapsed:5.1f}s | {par_20:13d} | {par_21:12d} | {par_22:10d} | {par_23:9d} | {par_24:9.2f} | {par_25:9d}")
                print("✅ Sweep completed!")
                break
                
            time.sleep(0.05)  # Check every 50ms
        except Exception as e:
            print(f"❌ Error monitoring: {e}")
            break
    else:
        print("⚠️  Timeout waiting for sweep completion")
    
    print(f"\n📊 Total steps observed: {step_count}")
    print(f"📊 Expected: 18 steps (10 forward + 8 reverse, no repeated endpoints)")
    
    # Stop the process
    print("\n🛑 Stopping process...")
    try:
        adwin.set_int_var(10, 0)  # Par_10: START (0=stop)
        adwin.stop_process(1)
        print("✅ Process stopped")
    except Exception as e:
        print(f"⚠️  Error stopping process: {e}")
    
    print("\n✅ Test completed!")
    return True

if __name__ == "__main__":
    main()