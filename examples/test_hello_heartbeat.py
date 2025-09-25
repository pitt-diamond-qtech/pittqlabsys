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
    
    # Get the TB1 path using relative path
    script_path = Path(__file__).parent / '..' / 'src' / 'Controller' / 'binary_files' / 'ADbasic' / 'hello_heartbeat.TB1'
    if not script_path.exists():
        print(f"❌ TB1 not found: {script_path}")
        print("   Please compile hello_heartbeat.bas on the lab PC first!")
        return False
    
    # Check file size
    file_size = script_path.stat().st_size
    print(f"📁 TB1 path: {script_path}")
    print(f"📊 TB1 file size: {file_size} bytes")
    if file_size == 0:
        print("❌ TB1 file is empty! Compilation may have failed.")
        return False
    
    # Test basic parameter read/write functionality first
    print("\n🔍 Testing basic parameter read/write...")
    try:
        print("   Testing Par_77 read/write...")
        adwin.set_int_var(77, 123456)
        val = adwin.get_int_var(77)
        print(f"   Set Par_77 = 123456, Read Par_77 = {val}")
        if val == 123456:
            print("   ✅ Basic parameter read/write working!")
        else:
            print(f"   ❌ Parameter read/write failed! Expected 123456, got {val}")
            return False
    except Exception as e:
        print(f"   ❌ Error with parameter read/write: {e}")
        print(f"   Error type: {type(e).__name__}")
        return False
    
    # Clean start - stop/clear everything
    print("\n🧹 Clean start...")
    adwin.stop_process(1)
    adwin.clear_process(1)
    time.sleep(0.1)
    
    # Load and start
    print("📁 Loading hello_heartbeat.TB1...")
    try:
        adwin.load_process(str(script_path))
        print("   ✅ TB1 loaded successfully")
    except Exception as e:
        print(f"   ❌ Failed to load TB1: {e}")
        return False
    
    print("▶️  Starting process...")
    try:
        adwin.start_process(1)
        print("   ✅ Process start command sent")
    except Exception as e:
        print(f"   ❌ Failed to start process: {e}")
        return False
    
    # Check signature and process delay using wrapper functions
    print("\n🔍 Verifying script loaded...")
    try:
        sig = adwin.get_int_var(80)
        pd = adwin.get_int_var(71)
        print(f"   Signature Par_80 = {sig} (expect 4242)")
        print(f"   ProcessDelay Par_71 = {pd} (expect 300000)")
        if sig == 4242:
            print("   ✅ Correct script loaded!")
        else:
            print(f"   ❌ Wrong signature! Expected 4242, got {sig}")
            return False
    except Exception as e:
        print(f"   ❌ Error reading signature: {e}")
        print(f"   Error type: {type(e).__name__}")
        return False
    
    # Watch for 5 seconds with detailed monitoring
    print("\n⏱️  Monitoring for 5 seconds...")
    t0 = time.time()
    last_status = "Not running"
    last_hb = 0
    start_hb = adwin.get_int_var(25)
    
    while time.time() - t0 < 5.0:
        try:
            st  = adwin.get_process_status(1)
            hb  = adwin.get_int_var(25)
            tog  = adwin.get_int_var(78)
            c2  = adwin.get_int_var(72)
            elapsed = time.time() - t0
            print(f"{elapsed:5.2f}s | status={st} | heartbeat (Par_25)={hb} | toggle (Par_78)={tog} | trace (Par_72)={c2}")
            
            if st == "Not running" and last_status != "Not running":
                # process just stopped — grab last error text
                try:
                    last_error = adwin.read_probes('last_error', 1)
                    print("LastError:", last_error)
                except Exception:
                    pass
                print("❌ Process stopped unexpectedly!")
                return False
            
            # Check if heartbeat is advancing
            if last_hb > 0 and hb <= last_hb:
                print("⚠️  Heartbeat not advancing!")
            
            last_status = st
            last_hb = hb
            time.sleep(0.05)
        except Exception as e:
            print(f"❌ Error during monitoring: {e}")
            return False
    
    # Calculate event rate after monitoring is complete
    end_hb = adwin.get_int_var(25)
    total_elapsed = time.time() - t0
    rate = (end_hb - start_hb) / total_elapsed
    print(f"\n📊 Event rate: {rate:.1f} Hz (over {total_elapsed:.1f}s)")
    
    print("\n✅ Hello Heartbeat test completed successfully!")
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
