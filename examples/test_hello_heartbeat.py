#!/usr/bin/env python3
"""
Hello Heartbeat Test - Ultra-minimal ADwin Test

Tests basic ADwin communication with the simplest possible ADbasic script.
This isolates fundamental communication issues from complex timing logic.
"""

import sys
import os
import time
from pathlib import Path, PureWindowsPath

# Add project root
sys.path.insert(0, str(Path(__file__).parent / '..'))

from src.Controller.adwin_gold import AdwinGoldDevice

def test_hello_heartbeat(adwin):
    """
    Test ultra-minimal ADwin communication.
    """
    print("🧪 Hello Heartbeat Test - Ultra-minimal ADwin test")
    print("=" * 60)
    
    # Get the TB1 path using absolute Windows path
    tb1 = Path(r"D:\PyCharmProjects\pittqlabsys\src\Controller\binary_files\ADbasic\hello_heartbeat.TB1")
    if not tb1.exists():
        print(f"❌ TB1 not found: {tb1}")
        print("   Please compile hello_heartbeat.bas on the lab PC first!")
        return False
    
    # Check file size
    file_size = tb1.stat().st_size
    tbi_path = str(tb1)
    print(f"📁 TB1 path: {tbi_path}")
    print(f"📊 TB1 file size: {file_size} bytes")
    if file_size == 0:
        print("❌ TB1 file is empty! Compilation may have failed.")
        return False
    
    # Clean start
    print("\n🧹 Clean start...")
    adwin.stop_process(1)
    time.sleep(0.05)
    adwin.clear_process(1)
    
    # Load the minimal script
    print("📁 Loading hello_heartbeat.TB1...")
    try:
        adwin.update({'process_1': {'load': str(tbi_path)}})
        print("   ✅ TB1 loaded successfully")
    except Exception as e:
        print(f"   ❌ Failed to load TB1: {e}")
        return False
    
    # Start process
    print("▶️  Starting process...")
    try:
        adwin.start_process(1)
        print("   ✅ Process start command sent")
    except Exception as e:
        print(f"   ❌ Failed to start process: {e}")
        return False
    time.sleep(0.1)
    
    # Try reading some basic parameters first
    print("\n🔍 Testing basic parameter access...")
    try:
        print("   Testing Par_25 (heartbeat)...")
        hb_test = adwin.get_int_var(25)
        print(f"   Par_25 = {hb_test}")
        print("   ✅ Basic parameter access working!")
    except Exception as e:
        print(f"   ❌ Error reading Par_25: {e}")
        print(f"   Error type: {type(e).__name__}")
        return False
    
    # Check if process is running first
    print("\n📊 Checking process status...")
    try:
        st = adwin.read_probes('process_status', 1)
        print(f"   Process_Status(1) = {st}")
        if st != 'Running':
            print(f"   ❌ Process not running! Status: {st}")
            print("   This explains why Par_80 is not accessible")
            return False
        else:
            print("   ✅ Process is running!")
    except Exception as e:
        print(f"   ⚠️  Could not check process status: {e}")
    
    # Try reading Par_80 now that we know the process is running
    print("\n🔍 Verifying script loaded...")
    
    # First, let's test what parameters are accessible
    print("   Testing parameter accessibility...")
    accessible_params = []
    for par_num in [25, 80, 1, 2, 3, 10, 20]:
        try:
            val = adwin.get_int_var(par_num)
            accessible_params.append(f"Par_{par_num}={val}")
        except:
            accessible_params.append(f"Par_{par_num}=ERROR")
    print(f"   Accessible parameters: {', '.join(accessible_params)}")
    
    try:
        print("   Attempting to read Par_80...")
        sig = adwin.get_int_var(80)
        print(f"   Signature Par_80 = {sig}")
        if sig == 4242:
            print("   ✅ Correct script loaded!")
        else:
            print(f"   ❌ Wrong signature! Expected 4242, got {sig}")
            return False
    except Exception as e:
        print(f"   ❌ Error reading signature: {e}")
        print(f"   Error type: {type(e).__name__}")
        print("   This suggests the script didn't load properly or Par_80 is not accessible")
        return False
    
    # Heartbeat check
    print("\n💓 Checking heartbeat...")
    try:
        hb1 = adwin.get_int_var(25)
        time.sleep(0.05)
        hb2 = adwin.get_int_var(25)
        print(f"   Heartbeat: {hb1} → {hb2}")
        if hb2 > hb1:
            print("   ✅ Heartbeat advancing!")
        else:
            print("   ❌ Heartbeat not advancing!")
            return False
    except Exception as e:
        print(f"   ❌ Error checking heartbeat: {e}")
        return False
    
    # Process status check
    print("\n📊 Process status...")
    try:
        st = adwin.adw.Process_Status(1)
        print(f"   Process_Status(1) = {st}")
        if st == 1:
            print("   ✅ Process running!")
        else:
            print(f"   ⚠️  Process status: {st} (expected 1)")
    except Exception as e:
        print(f"   ⚠️  Could not check process status: {e}")
    
    # Monitor heartbeat for a few seconds
    print("\n⏱️  Monitoring heartbeat for 3 seconds...")
    start_time = time.time()
    last_hb = hb2
    while time.time() - start_time < 3.0:
        try:
            current_hb = adwin.get_int_var(25)
            elapsed = time.time() - start_time
            print(f"   {elapsed:5.2f}s | HB: {current_hb} (Δ: {current_hb - last_hb})", end='\r')
            last_hb = current_hb
            time.sleep(0.1)
        except Exception as e:
            print(f"\n   ❌ Error during monitoring: {e}")
            return False
    
    print("\n\n✅ Hello Heartbeat test completed successfully!")
    return True

def main():
    print("🎯 Hello Heartbeat Test - Ultra-minimal ADwin Test")
    print("=" * 60)
    
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
    
    try:
        # Run the test
        success = test_hello_heartbeat(adwin)
        
        if success:
            print("\n🎉 All tests passed! ADwin communication is working.")
            return 0
        else:
            print("\n❌ Test failed! There are fundamental ADwin communication issues.")
            return 1
    
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        # Clean up
        try:
            adwin.stop_process(1)
            adwin.clear_process(1)
        except:
            pass

if __name__ == '__main__':
    sys.exit(main())
