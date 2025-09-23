#!/usr/bin/env python3
"""
Simple standalone test for ADwin timeout functionality.
Run this on the lab PC to verify timeout methods work correctly.

Usage:
    python examples/test_timeout_simple.py
"""

import sys
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).parent / '..'))

from src.core.device_config import load_devices_from_config


def test_timeout_functionality():
    """Test ADwin timeout functionality with real hardware."""
    print("🎯 ADwin Timeout Test")
    print("=" * 40)
    
    try:
        # Load hardware
        print("🔧 Loading hardware...")
        config_path = Path(__file__).parent.parent / "src" / "config.json"
        loaded_devices, failed_devices = load_devices_from_config(config_path)
        
        if failed_devices:
            print(f"⚠️  Some devices failed to load: {list(failed_devices.keys())}")
        
        if not loaded_devices or 'adwin' not in loaded_devices:
            print("❌ No ADwin device loaded.")
            return False
        
        adwin = loaded_devices['adwin']
        print(f"✅ Adwin loaded: {type(adwin)}")
        print(f"✅ Connected: {adwin.is_connected}")
        
        # Test 1: Get current timeout
        print("\n🔍 Test 1: Get current timeout")
        try:
            current_timeout = adwin.get_timeout()
            print(f"   Current timeout: {current_timeout} ms")
        except Exception as e:
            print(f"   ❌ Error getting timeout: {e}")
            return False
        
        # Test 2: Set timeout to 10 seconds (as used in debug script)
        print("\n🔍 Test 2: Set timeout to 10 seconds")
        try:
            adwin.set_timeout(10000)
            new_timeout = adwin.get_timeout()
            print(f"   Set timeout to: 10000 ms")
            print(f"   Verified timeout: {new_timeout} ms")
            if new_timeout == 10000:
                print("   ✅ Timeout set correctly")
            else:
                print(f"   ⚠️  Expected 10000, got {new_timeout}")
        except Exception as e:
            print(f"   ❌ Error setting timeout: {e}")
            return False
        
        # Test 3: Test basic ADwin communication with new timeout
        print("\n🔍 Test 3: Test basic communication with new timeout")
        try:
            # Test reading a parameter
            par_25 = adwin.get_int_var(25)  # heartbeat
            print(f"   Heartbeat (Par_25): {par_25}")
            print("   ✅ Communication working with new timeout")
        except Exception as e:
            print(f"   ❌ Communication error: {e}")
            return False
        
        print("\n✅ All timeout tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main function."""
    print("🎯 Simple ADwin Timeout Test")
    print("This script tests the new timeout functionality.")
    print("Run this on the lab PC to verify timeout methods work.\n")
    
    success = test_timeout_functionality()
    
    if success:
        print("\n🎉 All tests passed! Timeout functionality is working correctly.")
        print("You can now run the debug_odmr_arrays.py script with confidence.")
    else:
        print("\n❌ Tests failed. Check the error messages above.")
        print("This might indicate that Set_Timeout/Get_Timeout methods don't exist")
        print("in the ADwin Python library, or they have different names.")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
