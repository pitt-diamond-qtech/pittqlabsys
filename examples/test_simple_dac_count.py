#!/usr/bin/env python3
"""
Simple DAC + Count Test

Tests basic DAC output and counting functionality with settle/dwell timing.
Follows the pattern from hello_heartbeat test files.
"""

import sys
import time
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).parent / '..'))

from src.Controller.adwin_gold import AdwinGoldDevice
from src.core.adwin_helpers import get_adwin_binary_path

def test_simple_dac_count(adwin, output_volts=0.0, settle_us=1000, dwell_us=5000, dac_ch=1, edge_rising=False):
    """
    Test simple DAC output and counting.
    
    Args:
        adwin: ADwin device instance
        output_volts: Voltage to output (-10.0 to +10.0)
        settle_us: Settle time in microseconds (excluded from counting)
        dwell_us: Dwell time in microseconds (counting window)
        dac_ch: DAC channel (1 or 2)
        edge_rising: True for rising edges, False for falling edges
    """
    print(f"🧪 Simple DAC + Count Test")
    print(f"   Output: {output_volts}V on DAC{dac_ch}")
    print(f"   Settle: {settle_us}µs, Dwell: {dwell_us}µs")
    print(f"   Edge: {'rising' if edge_rising else 'falling'}")
    print()
    
    # Clean start
    print("🧹 Clean start...")
    adwin.stop_process(1)
    adwin.clear_process(1)
    time.sleep(0.1)
    
    # Load the test script using adwin_helpers
    script_path = get_adwin_binary_path('simple_dac_count.TB1')
    print(f"📁 Loading: {script_path}")
    adwin.load_process(str(script_path))
    
    # Set parameters while STOPPED
    print("⚙️  Setting parameters...")
    adwin.set_int_var(1, dwell_us)       # Par_1 = dwell_us
    adwin.set_int_var(2, settle_us)      # Par_2 = settle_us
    adwin.set_int_var(4, 0 if edge_rising else 1)  # Par_4 = edge mode (0=rising, 1=falling)
    adwin.set_int_var(5, dac_ch)         # Par_5 = dac_ch
    adwin.set_float_var(1, output_volts) # FPar_1 = output_volts
    
    
    # Start process
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
    
    # Check signature
    sig = adwin.get_int_var(80)
    if sig != 4242:
        print(f"❌ Wrong signature! Expected 4242, got {sig}")
        return False
    print("✅ Correct script loaded!")
    
    # Run measurement
    print("\n⏳ Running measurement...")
    adwin.set_int_var(20, 0)   # clear ready
    adwin.set_int_var(10, 1)   # START
    # generous timeout: settle + dwell + margin
    timeout_s = (settle_us + dwell_us)/1e6 + 1.0
    t0 = time.time()
    print(f"⏳ Waiting for result (Par_20=1) for {timeout_s:.1f}s...")
    while True:
        try:
            ready = adwin.get_int_var(20)
            counts = adwin.get_int_var(21)  # Par_21 = counts
            hb = adwin.get_int_var(25)
            
            elapsed = time.time() - t0
            print(f"  {elapsed:5.2f}s | ready={ready} counts={counts} hb={hb}", end='\r')
            
            if ready == 1:
                print()
                break
                
            if elapsed > timeout_s:
                print(f"\n❌ Adwin Result Timeout after {elapsed:.1f}s")
                return False
                
            time.sleep(0.02)
            
        except Exception as e:
            print(f"\n❌ Polling error: {e}")
            return False
    
    # Get final results
    final_counts = adwin.get_int_var(21)  # Par_21 = counts
    process_delay = adwin.get_int_var(71)  # Par_71 = Processdelay
    
    print(f"\n✅ Test completed!")
    print(f"   Final counts: {final_counts}")
    print(f"   Process delay: {process_delay} ticks")
    print(f"   Expected counts: ~{dwell_us * 50 / 1000} (assuming 50kHz signal) over {dwell_us}µs")
    
    # Read the Data_1 array that the ADbasic script populated
    try:
        array_length_1 = adwin.get_data_length(1)
        print(f"   Data_1 length = {array_length_1}")
        
        # Read the actual data from Data_1 array
        data_1_array = adwin.get_int_data(1, length=8)  # Read first 8 elements
        print(f"   Data_1 array: {data_1_array}")
        
        # Show first few elements for analysis
        if len(data_1_array) > 0:
            print(f"   First element (Data_1[1]): {data_1_array[0]}")
            if len(data_1_array) > 1:
                print(f"   Second element (Data_1[2]): {data_1_array[1]}")
        
    except Exception as e:
        print(f"   Error reading Data_1 array: {e}")
    
    return True

def main():
    print("🎯 Simple DAC + Count Test")
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
    
    try:
        # Run the test
        success = test_simple_dac_count(
            adwin,
            output_volts=0.0,    # 0V output
            settle_us=1000,      # 1ms settle
            dwell_us=5000,       # 5ms dwell
            dac_ch=1,            # DAC channel 1
            edge_rising=False    # falling edges
        )
        
        if success:
            print("\n🎉 Test completed successfully!")
            return 0
        else:
            print("\n❌ Test failed!")
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
        # Clean up - clear ready flag and stop/clear process
        try:
            adwin.set_int_var(20, 0)   # clear ready flag
            adwin.stop_process(1)
            adwin.clear_process(1)
            print("✅ Cleanup completed")
        except:
            pass

if __name__ == '__main__':
    sys.exit(main())
