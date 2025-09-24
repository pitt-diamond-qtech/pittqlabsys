#!/usr/bin/env python3
"""
Simple Voltage Count Test - Minimal ADwin Test Script

Tests basic voltage output and counting functionality without complex state machines.
This helps isolate timing issues and understand ADwin fundamentals.
"""

import sys
import os
import time
import argparse
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).parent / '..'))

from src.Controller.adwin_gold import AdwinGoldDevice

def test_simple_voltage_count(adwin, output_volts=0.0, settle_us=1000, dwell_us=5000, dac_ch=1, edge_rising=False, tick_us=200):
    """
    Test simple voltage output and counting using minimal approach.
    
    Args:
        adwin: ADwin device instance
        output_volts: Voltage to output (-1.0 to +1.0)
        settle_us: Settle time in microseconds (excluded from counting)
        dwell_us: Dwell time in microseconds (counting window)
        dac_ch: DAC channel (1 or 2)
        edge_rising: True for rising edges, False for falling edges
        tick_us: Tick size in microseconds (affects Processdelay)
    """
    print(f"🧪 Simple Voltage Count Test")
    print(f"   Output: {output_volts}V on DAC{dac_ch}")
    print(f"   Settle: {settle_us}µs, Dwell: {dwell_us}µs")
    print(f"   Edge: {'rising' if edge_rising else 'falling'}, Tick: {tick_us}µs")
    print()
    
    # Clean start
    print("🧹 Clean start...")
    adwin.stop_process(1)
    time.sleep(0.1)
    adwin.clear_process(1)
    
    # Load the simple test script using the same pattern as debug_odmr_arrays.py
    script_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'Controller', 'binary_files', 'ADbasic', 'Simple_Voltage_Count_Test.TB1')
    print(f"📁 Loading: {script_path}")
    adwin.update({'process_1': {'load': str(script_path)}})
    
    # Set parameters while STOPPED
    print("⚙️  Setting parameters...")
    adwin.set_int_var(8, tick_us)    # tick size (Processdelay = tick_us*100)
    adwin.set_int_var(2, settle_us)  # SETTLE_US
    adwin.set_int_var(3, dwell_us)   # DWELL_US
    adwin.set_int_var(4, dac_ch)     # DAC_CH
    adwin.set_int_var(5, 0 if edge_rising else 1)  # edge select (0=rising, 1=falling)
    adwin.set_float_var(1, output_volts)  # Vout
    
    # Set START=1 first (so Event sees START=1 on its first tick)
    adwin.set_int_var(10, 1)         # Par_10 = START
    print("▶️  Starting process...")
    adwin.start_process(1)
    time.sleep(0.05)
    
    # Quick heartbeat sanity check
    print("💓 Checking heartbeat...")
    hb1 = adwin.get_int_var(25)
    time.sleep(0.05)
    hb2 = adwin.get_int_var(25)
    if hb2 == hb1:
        print("❌ DSP heartbeat not advancing!")
        return False
    print(f"   Heartbeat advancing: {hb1} -> {hb2}")
    
    # Run one window
    print("\n⏳ Running measurement window...")
    adwin.set_int_var(20, 0)   # clear ready
    # START is already set to 1, state machine will re-arm
    
    t0 = time.time()
    while True:
        try:
            ready = adwin.get_int_var(20)
            state = adwin.get_int_var(26)
            counts = adwin.get_int_var(30)
            hb = adwin.get_int_var(25)
            
            elapsed = time.time() - t0
            print(f"  {elapsed:5.2f}s | ready={ready} counts={counts} hb={hb} state={state}", end='\r')
            
            if ready == 1:
                print()
                break
                
            if elapsed > 3.0:
                print(f"\n❌ Timeout after {elapsed:.1f}s")
                return False
                
            time.sleep(0.02)
            
        except Exception as e:
            print(f"\n❌ Communication error: {e}")
            return False
    
    # Get final results
    final_counts = adwin.get_int_var(30)
    final_state = adwin.get_int_var(26)
    dwell_echo = adwin.get_int_var(21)
    settle_echo = adwin.get_int_var(22)
    
    print(f"\n✅ Test completed!")
    print(f"   Final counts: {final_counts}")
    print(f"   Final state: {final_state}")
    print(f"   Settle: {settle_echo}µs, Dwell: {dwell_echo}µs")
    print(f"   Expected counts: ~{dwell_us * 50 / 1000} (assuming 50kHz signal)")
    
    return True

def test_multiple_dwell_times(adwin, output_volts=0.0, settle_us=1000, dac_ch=1, edge_rising=False, tick_us=200):
    """
    Test multiple dwell times with the same setup.
    """
    print(f"\n🧪 Multiple Dwell Times Test")
    print(f"   Output: {output_volts}V on DAC{dac_ch}")
    print(f"   Settle: {settle_us}µs, Tick: {tick_us}µs")
    print(f"   Edge: {'rising' if edge_rising else 'falling'}")
    print()
    
    dwell_times = [1000, 2000, 5000, 10000, 20000]  # 1ms to 20ms
    
    for dwell_us in dwell_times:
        print(f"\n--- Testing {dwell_us}µs dwell ---")
        
        # Update dwell time
        adwin.set_int_var(3, dwell_us)  # DWELL_US
        
        # Run measurement
        adwin.set_int_var(20, 0)   # clear ready
        # leave START=1 (ok) or set to 1 again; state machine will re-arm
        
        t0 = time.time()
        while True:
            try:
                ready = adwin.get_int_var(20)
                state = adwin.get_int_var(26)
                counts = adwin.get_int_var(30)
                
                elapsed = time.time() - t0
                print(f"  {elapsed:5.2f}s | ready={ready} counts={counts} state={state}", end='\r')
                
                if ready == 1:
                    print()
                    print(f"   ✅ {dwell_us}µs: {counts} counts")
                    break
                    
                if elapsed > 3.0:
                    print(f"\n   ❌ Timeout at {dwell_us}µs")
                    return False
                    
                time.sleep(0.02)
                
            except Exception as e:
                print(f"\n   ❌ Communication error at {dwell_us}µs: {e}")
                return False
        
        time.sleep(0.1)  # Brief pause between tests
    
    return True

def main():
    parser = argparse.ArgumentParser(description='Simple ADwin voltage count test')
    parser.add_argument('--real-hardware', action='store_true', help='Use real hardware instead of mock')
    parser.add_argument('--volts', type=float, default=0.0, help='Output voltage (-1.0 to +1.0)')
    parser.add_argument('--settle', type=int, default=1000, help='Settle time in microseconds')
    parser.add_argument('--dwell', type=int, default=5000, help='Dwell time in microseconds')
    parser.add_argument('--dac', type=int, default=1, choices=[1, 2], help='DAC channel')
    parser.add_argument('--edge-rising', action='store_true', help='Count on rising edges (default: falling)')
    parser.add_argument('--tick', type=int, default=200, help='Tick size in microseconds')
    parser.add_argument('--test-range', action='store_true', help='Test multiple dwell times')
    
    args = parser.parse_args()
    
    print("🎯 Simple ADwin Voltage Count Test")
    print("=" * 50)
    
    if args.real_hardware:
        print("🔧 Using real hardware...")
        try:
            adwin = AdwinGoldDevice()
            if not adwin.is_connected:
                print("❌ Failed to connect to ADwin")
                return 1
            print(f"✅ ADwin connected: {adwin.is_connected}")
        except Exception as e:
            print(f"❌ Hardware connection failed: {e}")
            return 1
    else:
        print("🔧 Using mock hardware...")
        from src.tests.conftest import mock_adwin
        adwin = mock_adwin()
    
    try:
        if args.test_range:
            # Test multiple dwell times
            success = test_multiple_dwell_times(
                adwin, 
                output_volts=args.volts,
                settle_us=args.settle,
                dac_ch=args.dac,
                edge_rising=args.edge_rising,
                tick_us=args.tick
            )
        else:
            # Single test
            success = test_simple_voltage_count(
                adwin, 
                output_volts=args.volts,
                settle_us=args.settle,
                dwell_us=args.dwell,
                dac_ch=args.dac,
                edge_rising=args.edge_rising,
                tick_us=args.tick
            )
        
        if not success:
            print("❌ Test failed")
            return 1
    
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1
    finally:
        if args.real_hardware:
            try:
                adwin.disconnect()
            except:
                pass
    
    print("\n✅ All tests completed successfully!")
    return 0

if __name__ == '__main__':
    sys.exit(main())
