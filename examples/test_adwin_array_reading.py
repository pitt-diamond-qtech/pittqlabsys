#!/usr/bin/env python3
"""
Simple test script to diagnose ADwin array reading issues.
This script tests the basic array reading functionality without requiring
the full ODMR setup or signal generator.
"""

import argparse
import sys
import time
from pathlib import Path
import numpy as np

# Add project root
sys.path.insert(0, str(Path(__file__).parent / '..'))

from src.core.device_config import load_devices_from_config
from src.core.adwin_helpers import get_adwin_binary_path


def test_array_reading(adwin):
    """Test basic array reading functionality."""
    print("\n" + "=" * 60)
    print("ADWIN ARRAY READING DIAGNOSTIC TEST")
    print("=" * 60)
    
    try:
        # Test 1: Check if we can read array lengths
        print("\n🔍 Test 1: Array Length Reading")
        for i in range(1, 6):  # Test Data_1 through Data_5
            try:
                length = adwin.read_probes('array_length', i)
                print(f"   Data_{i} length: {length}")
            except Exception as e:
                print(f"   Data_{i} length: ERROR - {e}")
        
        # Test 2: Try reading small arrays
        print("\n🔍 Test 2: Small Array Reading")
        for i in range(1, 4):  # Test Data_1, Data_2, Data_3
            try:
                # Try reading just 1 element
                single = adwin.read_probes('int_array', i, 1)
                print(f"   Data_{i}[0]: {single}")
                
                # Try reading 5 elements
                small_array = adwin.read_probes('int_array', i, 5)
                print(f"   Data_{i}[0:5]: {small_array}")
                
            except Exception as e:
                print(f"   Data_{i}: ERROR - {e}")
        
        # Test 3: Check float arrays
        print("\n🔍 Test 3: Float Array Reading")
        for i in range(1, 4):  # Test FData_1, FData_2, FData_3
            try:
                single_float = adwin.read_probes('float_array', i, 1)
                print(f"   FData_{i}[0]: {single_float}")
                
                small_float_array = adwin.read_probes('float_array', i, 5)
                print(f"   FData_{i}[0:5]: {small_float_array}")
                
            except Exception as e:
                print(f"   FData_{i}: ERROR - {e}")
        
        # Test 4: Check process status and parameters
        print("\n🔍 Test 4: Process Status")
        try:
            status = adwin.read_probes('process_status', 1)
            print(f"   Process 1 status: {status}")
        except Exception as e:
            print(f"   Process status: ERROR - {e}")
        
        # Test 5: Check some parameters
        print("\n🔍 Test 5: Parameter Reading")
        for par_id in [20, 21, 25, 30, 31, 32]:
            try:
                value = adwin.get_int_var(par_id)
                print(f"   Par_{par_id}: {value}")
            except Exception as e:
                print(f"   Par_{par_id}: ERROR - {e}")
        
        # Test 6: Check float parameters
        print("\n🔍 Test 6: Float Parameter Reading")
        for fpar_id in [1, 2, 33]:
            try:
                value = adwin.get_float_var(fpar_id)
                print(f"   FPar_{fpar_id}: {value}")
            except Exception as e:
                print(f"   FPar_{fpar_id}: ERROR - {e}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error during array reading test: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_with_simple_script(adwin):
    """Test with a simple ADwin script that writes known values to arrays."""
    print("\n" + "=" * 60)
    print("TESTING WITH SIMPLE ADWIN SCRIPT")
    print("=" * 60)
    
    try:
        # Load a simple test script (if available)
        # For now, let's just test with the existing ODMR script but with minimal parameters
        print("📁 Loading ODMR_Sweep_Counter_Debug.TB1...")
        script_path = get_adwin_binary_path('ODMR_Sweep_Counter_Debug.TB1')
        adwin.update({'process_1': {'load': str(script_path)}})
        
        # Set minimal parameters
        print("⚙️  Setting minimal parameters...")
        adwin.set_float_var(1, -0.5)    # FPar_1 = Vmin
        adwin.set_float_var(2, 0.5)     # FPar_2 = Vmax  
        adwin.set_int_var(1, 3)         # Par_1 = N_STEPS (small)
        adwin.set_int_var(2, 100)       # Par_2 = SETTLE_US (short)
        adwin.set_int_var(3, 1000)      # Par_3 = DWELL_US (short)
        adwin.set_int_var(4, 1)         # Par_4 = DAC_CH
        
        # Start the process
        print("▶️  Starting process...")
        adwin.set_int_var(10, 1)        # Par_10 = START
        adwin.start_process(1)
        
        # Wait a bit for it to complete
        print("⏳ Waiting for completion...")
        time.sleep(2.0)
        
        # Now test array reading
        print("📥 Testing array reading after script execution...")
        success = test_array_reading(adwin)
        
        # Clean up
        print("🧹 Cleaning up...")
        adwin.set_int_var(10, 0)        # STOP
        adwin.stop_process(1)
        time.sleep(0.1)
        adwin.clear_process(1)
        
        return success
        
    except Exception as e:
        print(f"\n❌ Error during simple script test: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    p = argparse.ArgumentParser(description='Test ADwin Array Reading')
    p.add_argument('--config', type=str, default=None, help='Path to config.json')
    p.add_argument('--with-script', action='store_true', help='Test with a simple ADwin script')
    args = p.parse_args()
    
    print("🎯 ADwin Array Reading Diagnostic Tool")
    
    # Load hardware
    print("🔧 Loading hardware...")
    try:
        config_path = Path(args.config) if args.config else Path(__file__).parent.parent / "src" / "config.json"
        loaded_devices, failed_devices = load_devices_from_config(config_path)
        
        if failed_devices:
            print(f"⚠️  Some devices failed to load: {list(failed_devices.keys())}")
            for name, err in failed_devices.items():
                print(f"   - {name}: {err}")
        
        if not loaded_devices or 'adwin' not in loaded_devices:
            print("❌ No ADwin device loaded.")
            return 1
        
        adwin = loaded_devices['adwin']
        print(f"✅ Adwin loaded: {type(adwin)}")
        print(f"✅ Connected: {adwin.is_connected}")
        
    except Exception as e:
        print(f"❌ Failed to load hardware: {e}")
        return 1
    
    # Run tests
    if args.with_script:
        success = test_with_simple_script(adwin)
    else:
        success = test_array_reading(adwin)
    
    print("\n✅ Test completed!" if success else "\n❌ Test failed!")
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
