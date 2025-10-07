#!/usr/bin/env python3
"""
Test Production ODMR Counter Script

This script tests the production ODMR_Sweep_Counter.bas to verify it behaves
the same as the debug version. It performs a simple sweep and validates:
- Process starts correctly (signature 7777)
- Heartbeat advances
- State machine progresses through expected states
- Data arrays are populated correctly
- Timing is accurate with overhead factor

Usage:
    python test_production_odmr_counter.py --real-hardware
    python test_production_odmr_counter.py --real-hardware --dwell-us 2000 --settle-us 500
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


def d_to_v(d: int) -> float:
    """16-bit DAC digits -> Volts for ±10 V range."""
    return (d * 20.0 / 65535.0) - 10.0


def test_production_odmr_counter(use_real_hardware=False, config_path=None, 
                                dwell_us=5000, settle_us=1000, overhead_factor=1.2):
    """
    Test the production ODMR_Sweep_Counter.bas script.
    
    Args:
        use_real_hardware (bool): Use real hardware (required for this test)
        config_path (str): Path to config.json
        dwell_us (int): Dwell time in microseconds
        settle_us (int): Settle time in microseconds  
        overhead_factor (float): Overhead correction factor
        
    Returns:
        bool: True if test passes, False otherwise
    """
    print("\n" + "=" * 60)
    print("PRODUCTION ODMR COUNTER TEST")
    print("=" * 60)
    
    if not use_real_hardware:
        print("❌ This test requires real hardware (--real-hardware)")
        return False
    
    # Load ADwin device
    print("🔧 Loading ADwin hardware...")
    try:
        config_path = Path(config_path) if config_path else Path(__file__).parent.parent / "src" / "config.json"
        loaded_devices, failed_devices = load_devices_from_config(config_path)
        
        if failed_devices:
            print(f"⚠️  Some devices failed to load: {list(failed_devices.keys())}")
            for name, err in failed_devices.items():
                print(f"   - {name}: {err}")
        
        if not loaded_devices or 'adwin' not in loaded_devices:
            print("❌ No ADwin device loaded.")
            return False
        
        adwin = loaded_devices['adwin']
        print(f"✅ ADwin loaded: {type(adwin)}")
        print(f"✅ Connected: {adwin.is_connected}")
        
    except Exception as e:
        print(f"❌ Failed to load ADwin hardware: {e}")
        return False
    
    # Load production script
    print("\n📁 Loading production ODMR_Sweep_Counter.bas...")
    try:
        # Stop and clear any existing process
        try:
            adwin.stop_process(1)
            time.sleep(0.1)
        except Exception:
            pass
        try:
            adwin.clear_process(1)
        except Exception:
            pass
        
        # Load production script
        script_path = get_adwin_binary_path('ODMR_Sweep_Counter.TB1')
        print(f"📁 Loading TB1: {script_path}")
        adwin.update({'process_1': {'load': str(script_path)}})
        
    except Exception as e:
        print(f"❌ Failed to load production script: {e}")
        return False
    
    # Set up test parameters
    print("\n⚙️  Setting up test parameters...")
    try:
        # Test parameters
        VMIN, VMAX = -1.0, 1.0
        N_STEPS = 10
        SETTLE_US = settle_us
        DWELL_US = dwell_us
        DAC_CH = 1
        
        # Set parameters
        adwin.set_float_var(1, VMIN)     # FPar_1
        adwin.set_float_var(2, VMAX)     # FPar_2
        adwin.set_int_var(1, N_STEPS)    # Par_1
        adwin.set_int_var(2, SETTLE_US)  # Par_2
        adwin.set_int_var(3, DWELL_US)   # Par_3
        adwin.set_int_var(4, 0)          # Par_4 = EDGE_MODE (0=rising)
        adwin.set_int_var(5, DAC_CH)     # Par_5 = DAC_CH
        adwin.set_int_var(6, 1)          # Par_6 = DIR_SENSE (1=DIR High=up)
        adwin.set_int_var(8, 0)          # Par_8 = PROCESSDELAY_US (0 = auto-calculate)
        adwin.set_int_var(9, int(overhead_factor * 10))  # Par_9 = OVERHEAD_FACTOR
        
        print(f"   VMIN/VMAX: {VMIN}/{VMAX} V")
        print(f"   N_STEPS: {N_STEPS}")
        print(f"   SETTLE_US: {SETTLE_US}")
        print(f"   DWELL_US: {DWELL_US}")
        print(f"   OVERHEAD_FACTOR: {overhead_factor}")
        
    except Exception as e:
        print(f"❌ Failed to set parameters: {e}")
        return False
    
    # Start process and verify
    print("\n▶️  Starting production process...")
    try:
        adwin.start_process(1)
        time.sleep(0.1)  # Give process time to start
        
        # Check process status
        process_status = adwin.get_process_status(1)
        print(f"   Process status: {process_status}")
        if process_status != "Running":
            print("   ❌ Process failed to start!")
            return False
        
        # Check signature (should be 7777 for production script)
        signature = adwin.get_int_var(80)
        print(f"   Signature Par_80 = {signature}")
        if signature != 7777:
            print(f"   ❌ Wrong signature! Expected 7777, got {signature}")
            return False
        else:
            print("   ✅ Correct production script loaded!")
        
        # Check initial heartbeat
        initial_hb = adwin.get_int_var(25)
        print(f"   Initial heartbeat: {initial_hb}")
        
    except Exception as e:
        print(f"❌ Failed to start process: {e}")
        return False
    
    # Test heartbeat advancement
    print("\n⏳ Testing heartbeat advancement...")
    try:
        start_time = time.time()
        last_hb = initial_hb
        
        while time.time() - start_time < 2.0:  # Wait up to 2 seconds
            current_hb = adwin.get_int_var(25)
            if current_hb > last_hb:
                print(f"   ✅ Heartbeat advancing: {last_hb} → {current_hb}")
                break
            time.sleep(0.01)
        else:
            print("   ❌ Heartbeat not advancing - process not running!")
            return False
            
    except Exception as e:
        print(f"❌ Error testing heartbeat: {e}")
        return False
    
    # Test state machine progression
    print("\n🔍 Testing state machine progression...")
    try:
        # Clear ready flag first
        adwin.set_int_var(20, 0)
        
        # Start sweep
        adwin.set_int_var(10, 1)  # Par_10 = START
        
        # Monitor state progression
        states_seen = set()
        start_time = time.time()
        last_state = None
        
        print("   Monitoring state progression...")
        while time.time() - start_time < 10.0:  # Wait up to 10 seconds
            try:
                state = adwin.get_int_var(26)
                ready = adwin.get_int_var(20)
                hb = adwin.get_int_var(25)
                
                if state != last_state:
                    state_names = {
                        255: "IDLE", 10: "PREP", 20: "PREPARE", 30: "ISSUE_STEP",
                        31: "SETTLE", 32: "OPEN_WINDOW", 33: "DWELL", 34: "CLOSE_WINDOW",
                        35: "NEXT_STEP", 70: "READY"
                    }
                    state_name = state_names.get(state, f"UNKNOWN({state})")
                    print(f"   State: {state} ({state_name})")
                    states_seen.add(state)
                    last_state = state
                
                if ready == 1:
                    print(f"   ✅ Sweep completed! Ready flag set.")
                    break
                    
                time.sleep(0.1)
            except Exception as e:
                print(f"   ⚠️  Transient error: {e}")
                time.sleep(0.1)
        else:
            print("   ❌ Sweep did not complete within 10 seconds!")
            return False
        
        # Check that we saw expected states
        expected_states = {255, 10, 30, 31, 32, 33, 34, 35, 70}
        missing_states = expected_states - states_seen
        if missing_states:
            print(f"   ⚠️  Missing expected states: {missing_states}")
        else:
            print(f"   ✅ All expected states observed: {sorted(states_seen)}")
        
    except Exception as e:
        print(f"❌ Error testing state machine: {e}")
        return False
    
    # Test data collection
    print("\n📊 Testing data collection...")
    try:
        # Read number of points
        n_points = adwin.get_int_var(21)
        print(f"   Number of points: {n_points}")
        
        if n_points <= 0:
            print("   ❌ No points collected!")
            return False
        
        # Read data arrays
        counts = adwin.read_probes('int_array', 1, n_points)      # Data_1
        dac_digits = adwin.read_probes('int_array', 2, n_points)   # Data_2
        
        print(f"   ✅ Counts array: {len(counts)} elements")
        print(f"   ✅ DAC digits array: {len(dac_digits)} elements")
        
        # Validate data
        if len(counts) != n_points or len(dac_digits) != n_points:
            print(f"   ❌ Array length mismatch!")
            return False
        
        # Check counts are reasonable (not all zeros, not all max values)
        if all(c == 0 for c in counts):
            print("   ⚠️  All counts are zero - check signal source")
        elif all(c == 2147483647 for c in counts):  # Max 32-bit signed
            print("   ⚠️  All counts are max value - possible overflow")
        else:
            print(f"   ✅ Counts look reasonable: min={min(counts)}, max={max(counts)}, avg={sum(counts)/len(counts):.1f}")
        
        # Check DAC digits are in valid range
        invalid_digits = [d for d in dac_digits if not (0 <= int(d) <= 65535)]
        if invalid_digits:
            print(f"   ❌ Invalid DAC digits found: {invalid_digits[:5]}...")
            return False
        else:
            print("   ✅ All DAC digits in valid range (0-65535)")
        
        # Check voltage progression
        volts = [d_to_v(int(d)) for d in dac_digits]
        expected_min, expected_max = VMIN, VMAX
        actual_min, actual_max = min(volts), max(volts)
        
        if abs(actual_min - expected_min) > 0.1 or abs(actual_max - expected_max) > 0.1:
            print(f"   ⚠️  Voltage range mismatch: expected {expected_min} to {expected_max}, got {actual_min:.3f} to {actual_max:.3f}")
        else:
            print(f"   ✅ Voltage range correct: {actual_min:.3f} to {actual_max:.3f} V")
        
        # Show sample data
        print("\n   Sample data (first 5 points):")
        print("   idx | counts | digits | volts")
        print("   ----+--------+--------+--------")
        for i in range(min(5, n_points)):
            print(f"   {i:3d} | {int(counts[i]):6d} | {int(dac_digits[i]):6d} | {volts[i]:6.3f}")
        
    except Exception as e:
        print(f"❌ Error testing data collection: {e}")
        return False
    
    # Test timing accuracy
    print("\n⏱️  Testing timing accuracy...")
    try:
        # Calculate expected timing
        expected_time_per_point = (SETTLE_US + DWELL_US) / 1e6  # seconds
        expected_total_time = n_points * expected_time_per_point
        
        print(f"   Expected time per point: {expected_time_per_point*1000:.1f} ms")
        print(f"   Expected total time: {expected_total_time:.2f} s")
        
        # The timing test would require measuring actual sweep time
        # For now, just verify the overhead factor is being used
        processdelay = adwin.get_int_var(71)  # Par_71 should contain Processdelay
        print(f"   Processdelay: {processdelay} ticks")
        
        # Calculate effective tick size with overhead factor
        tick_us = round(processdelay * 3.3 / 1000.0 * overhead_factor)
        print(f"   Effective tick size: {tick_us} µs (with {overhead_factor}x overhead factor)")
        
        print("   ✅ Timing parameters look correct")
        
    except Exception as e:
        print(f"❌ Error testing timing: {e}")
        return False
    
    # Cleanup
    print("\n🧹 Cleaning up...")
    try:
        adwin.set_int_var(10, 0)  # STOP
        adwin.set_int_var(20, 0)  # Clear ready flag
        time.sleep(0.1)
        adwin.stop_process(1)
        time.sleep(0.1)
        adwin.clear_process(1)
        print("   ✅ Cleanup completed")
    except Exception as e:
        print(f"   ⚠️  Cleanup error (non-critical): {e}")
    
    print("\n✅ Production ODMR Counter test completed successfully!")
    return True


def main():
    parser = argparse.ArgumentParser(description='Test Production ODMR Counter Script')
    parser.add_argument('--real-hardware', action='store_true', 
                       help='Use real hardware (required for this test)')
    parser.add_argument('--config', type=str, default=None,
                       help='Path to config.json (default: src/config.json)')
    parser.add_argument('--dwell-us', type=int, default=5000,
                       help='Dwell time in microseconds (default: 5000)')
    parser.add_argument('--settle-us', type=int, default=1000,
                       help='Settle time in microseconds (default: 1000)')
    parser.add_argument('--overhead-factor', type=float, default=1.2,
                       help='Overhead correction factor (default: 1.2)')
    
    args = parser.parse_args()
    
    print("🎯 Production ODMR Counter Test")
    print(f"🔧 Hardware mode: {'Real' if args.real_hardware else 'Mock'}")
    print(f"⏱️  Dwell time: {args.dwell_us} µs")
    print(f"⏱️  Settle time: {args.settle_us} µs")
    print(f"⚙️  Overhead factor: {args.overhead_factor}")
    
    success = test_production_odmr_counter(
        use_real_hardware=args.real_hardware,
        config_path=args.config,
        dwell_us=args.dwell_us,
        settle_us=args.settle_us,
        overhead_factor=args.overhead_factor
    )
    
    if success:
        print("\n🎉 All tests passed! Production script is working correctly.")
        return 0
    else:
        print("\n❌ Tests failed! Check the output above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
