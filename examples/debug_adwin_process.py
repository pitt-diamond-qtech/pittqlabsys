#!/usr/bin/env python3
"""
Debug Adwin Process Loading

This script provides detailed debugging for Adwin process loading issues.
"""

import sys
import time
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent / '..'))

from src.core.adwin_helpers import get_adwin_binary_path, setup_adwin_for_sweep_odmr, read_adwin_sweep_odmr_data
from src.core.device_config import load_devices_from_config


def debug_adwin_process_loading():
    """Debug Adwin process loading step by step."""
    print("🔍 Debug Adwin Process Loading")
    print("=" * 50)
    
    # 1. Check binary file exists
    print("\n1. Checking binary file...")
    binary_path = get_adwin_binary_path('ODMR_Sweep_Counter.TB1')
    print(f"   Binary path: {binary_path}")
    print(f"   File exists: {binary_path.exists()}")
    
    if not binary_path.exists():
        print("❌ Binary file not found!")
        return False
    
    # 2. Load Adwin device
    print("\n2. Loading Adwin device...")
    try:
        from pathlib import Path
        config_path = Path("src/config.json")
        loaded_devices, failed_devices = load_devices_from_config(config_path)
        adwin = loaded_devices['adwin']
        print(f"   ✅ Adwin loaded: {type(adwin)}")
        print(f"   ✅ Connected: {adwin.is_connected}")
    except Exception as e:
        print(f"   ❌ Failed to load Adwin: {e}")
        return False
    
    # 3. Check current process status
    print("\n3. Checking current process status...")
    try:
        for i in range(1, 4):
            try:
                status = adwin.get_process_status(i)
                print(f"   Process {i}: {status}")
            except Exception as e:
                print(f"   Process {i}: Error - {e}")
    except Exception as e:
        print(f"   Error checking process status: {e}")
    
    # 4. Try to load the process manually
    print("\n4. Loading process manually...")
    try:
        # Stop process 1 first
        adwin.stop_process(1)
        print("   ✅ Stopped process 1")
        
        # Clear process 1
        adwin.clear_process(1)
        print("   ✅ Cleared process 1")
        
        # Load the binary
        adwin.load_process(str(binary_path))
        print(f"   ✅ Loaded binary: {binary_path}")
        
        # Check process status after loading
        status = adwin.get_process_status(1)
        print(f"   Process 1 status after loading: {status}")
        
    except Exception as e:
        print(f"   ❌ Failed to load process: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 5. Set parameters
    print("\n5. Setting parameters...")
    try:
        adwin.set_int_var(2, 5000)  # Integration time in microseconds
        adwin.set_int_var(3, 100)   # Number of steps
        adwin.set_int_var(5, 1)     # Bidirectional
        adwin.set_int_var(11, 1000) # Settle time in microseconds
        print("   ✅ Parameters set successfully")
        
        # Read back parameters
        print("   Reading back parameters:")
        print(f"     Par_2 (integration): {adwin.get_int_var(2)}")
        print(f"     Par_3 (steps): {adwin.get_int_var(3)}")
        print(f"     Par_5 (bidirectional): {adwin.get_int_var(5)}")
        print(f"     Par_11 (settle): {adwin.get_int_var(11)}")
        
    except Exception as e:
        print(f"   ❌ Failed to set parameters: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 6. Start the process
    print("\n6. Starting process...")
    try:
        adwin.start_process(1)
        print("   ✅ Process started")
        
        # Check status after starting
        status = adwin.get_process_status(1)
        print(f"   Process 1 status after starting: {status}")
        
    except Exception as e:
        print(f"   ❌ Failed to start process: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 7. Wait and check data
    print("\n7. Waiting and checking data...")
    try:
        print("   Waiting 2 seconds...")
        time.sleep(2)
        
        # Check data
        data = read_adwin_sweep_odmr_data(adwin)
        print(f"   Data: {data}")
        
        # Check process status
        status = adwin.get_process_status(1)
        print(f"   Process 1 status: {status}")
        
    except Exception as e:
        print(f"   ❌ Error checking data: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 8. Stop process
    print("\n8. Stopping process...")
    try:
        adwin.stop_process(1)
        print("   ✅ Process stopped")
        
        status = adwin.get_process_status(1)
        print(f"   Process 1 status after stopping: {status}")
        
    except Exception as e:
        print(f"   ❌ Failed to stop process: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n✅ Debug completed successfully!")
    return True


if __name__ == "__main__":
    success = debug_adwin_process_loading()
    if success:
        print("\n🎉 All steps completed successfully!")
        sys.exit(0)
    else:
        print("\n💥 Debug failed!")
        sys.exit(1)
