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
    
    # Clean start - stop/clear everything
    print("\n🧹 Clean start...")
    adwin.stop_process(1)
    adwin.clear_process(1)
    time.sleep(0.1)
    
    # Load and start
    script_path = Path(__file__).parent / '..' / 'src' / 'Controller' / 'binary_files' / 'ADbasic' / 'hello_heartbeat_v2.TB1'
    print(f"📁 Loading: {script_path}")
    adwin.load_process(str(script_path))
    adwin.start_process(1)
    print("Status after start:", adwin.get_process_status(1))
    
    # Check signature and process delay using wrapper functions
    print("sig:", adwin.get_int_var(80))        # expect 4242
    print("PD :", adwin.get_int_var(71))        # expect 300000
    
    # Watch for 2 seconds
    print("\n⏱️  Monitoring for 2 seconds...")
    t0 = time.time()
    last_status = "Not running"
    while time.time() - t0 < 2.0:
        st  = adwin.get_process_status(1)
        hb  = adwin.get_int_var(25)
        tr  = adwin.get_int_var(60)
        c2  = adwin.get_int_var(72)
        print(f"status={st} | heartbeat (Par_25)={hb} | trace1 (Par_60)={tr} | trace2 (Par_72)={c2}")
        if st == "Not running" and last_status != "Not running":
            # process just stopped — grab last error text
            try:
                last_error = adwin.read_probes('last_error', 1)
                print("LastError:", last_error)
            except Exception:
                pass
            break
        last_status = st
        time.sleep(0.05)
    
    print("\n✅ Test completed!")
    return 0

if __name__ == '__main__':
    sys.exit(main())
