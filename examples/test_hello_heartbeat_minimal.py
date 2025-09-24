#!/usr/bin/env python3
"""
Minimal Hello Heartbeat Test
"""

import sys
import time
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).parent / '..'))

from src.Controller.adwin_gold import AdwinGoldDevice

def main():
    print("🎯 Minimal Hello Heartbeat Test")
    print("=" * 40)
    
    # Connect to ADwin
    print("🔧 Connecting to ADwin...")
    try:
        adwin = AdwinGoldDevice()
        if not adwin.is_connected:
            print("❌ Failed to connect to ADwin")
            return 1
        print(f"✅ ADwin connected: {adwin.is_connected}")
    except Exception as e:
        print(f"❌ Hardware connection failed: {e}")
        return 1
    
    # Test basic parameter read/write first
    print("🔍 Testing parameter read/write...")
    adwin.set_int_var(77, 123456)
    val = adwin.get_int_var(77)
    print(f"Set Par_77 = 123456, Read Par_77 = {val}")
    if val != 123456:
        print("❌ Parameter read/write failed!")
        return 1
    print("✅ Parameter read/write working!")
    
    # Your minimal test code
    tb1 = Path(r"D:\PyCharmProjects\pittqlabsys\src\Controller\binary_files\ADbasic\hello_heartbeat.TB1")
    
    adwin.stop_process(1); time.sleep(0.05); adwin.clear_process(1)
    adwin.update({'process_1': {'load': str(tb1)}})
    
    print("Status before start:", adwin.adw.Process_Status(1))  # expect 0
    adwin.start_process(1)
    print("Status after start :", adwin.adw.Process_Status(1))  # expect >0
    
    # Give it a tick
    time.sleep(0.05)
    
    # Confirm we loaded the right file and Event is ticking
    print("sig =", adwin.get_int_var(80))  # expect 4242
    hb1 = adwin.get_int_var(25); time.sleep(0.05); hb2 = adwin.get_int_var(25)
    print("HB:", hb1, "→", hb2)            # expect hb2 > hb1
    
    print("\n✅ Test completed!")
    return 0

if __name__ == '__main__':
    sys.exit(main())
