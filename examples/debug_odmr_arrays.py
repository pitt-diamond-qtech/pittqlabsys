#!/usr/bin/env python3
"""
Debug ODMR Arrays Script (for non-blocking DEBUG ADbasic)

- Waits for Par_20 == 1 (sweep ready)
- Reads step-resolved arrays:
    Data_1  (counts, int)
    Data_2  (DAC digits, int)
    FData_1 (volts, float)  [if not present, compute from digits]
    Data_3  (triangle position, int)
- Reads end-of-sweep summaries:
    Par_30 (sum), Par_31 (max), Par_32 (idx of max), FPar_33 (avg)
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


def v_to_d(v: float) -> int:
    """Volts -> 16-bit DAC digits for ±10 V range."""
    return int(round((v + 10.0) * 65535.0 / 20.0))


def d_to_v(d: int) -> float:
    """16-bit DAC digits -> Volts for ±10 V range."""
    return (d * 20.0 / 65535.0) - 10.0


def read_int_array(adwin, idx: int, n: int):
    """Read INT Data_idx using your class' read_probes."""
    return adwin.read_probes('int_array', idx, n)


def read_float_array_or_compute(adwin, idx: int, n: int, digits=None):
    """
    Try reading FLOAT FData_idx via read_probes('float_array', idx, n).
    If that fails (or not provided in the DSP), compute volts from digits.
    """
    try:
        return adwin.read_probes('float_array', idx, n)
    except Exception:
        if digits is None:
            raise
        return [d_to_v(int(d)) for d in digits]


def bring_up_process(adwin, tb1_filename: str):
    """Stop, clear, load TB1; no hidden fallbacks."""
    try:
        adwin.stop_process(1)
        time.sleep(0.1)
    except Exception:
        pass
    try:
        adwin.clear_process(1)
    except Exception:
        pass
    script_path = get_adwin_binary_path(tb1_filename)
    print(f"📁 Loading TB1: {script_path}")
    adwin.update({'process_1': {'load': str(script_path)}})


def debug_odmr_arrays(use_real_hardware=False, config_path=None, tb1_filename='ODMR_Sweep_Counter_Debug.TB1', dwell_us=5000, settle_us=1000, overhead_factor=1.2):
    print("\n" + "=" * 60)
    print("ODMR ARRAYS DEBUG SESSION – new DEBUG ADbasic (non-blocking)")
    print("=" * 60)

    # ---------- hardware bring-up ----------
    if not use_real_hardware:
        print("❌ Mock mode not implemented.")
        return False

    print("🔧 Loading real hardware...")
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
        print(f"✅ Adwin loaded: {type(adwin)}")
        print(f"✅ Connected: {adwin.is_connected}")
        
        # Note: ADwin Python library doesn't support timeout control
        # The timeout is handled at the driver level
        print("ℹ️  ADwin timeout control not available (using driver defaults)")

    except Exception as e:
        print(f"❌ Failed to load real hardware: {e}")
        return False

    # ---------- process & parameters ----------
    try:
        bring_up_process(adwin, tb1_filename)

        # Parameters (adjust as needed)
        VMIN, VMAX = -1.0, 1.0
        N_STEPS    = 10
        SETTLE_US  = settle_us     # Settle time from command line
        DWELL_US   = dwell_us      # Dwell time from command line
        DAC_CH     = 1
        CHUNK_US   = 0        # Use ADbasic auto-calculate (hybrid timing)
        # CHUNK_US = 0: Auto-calculate Processdelay based on dwell time
        # CHUNK_US > 0: Manual Processdelay override (µs)

        print("⚙️  Applying parameters…")
        adwin.set_float_var(1, VMIN)     # FPar_1
        adwin.set_float_var(2, VMAX)     # FPar_2
        adwin.set_int_var(1, N_STEPS)    # Par_1
        adwin.set_int_var(2, SETTLE_US)  # Par_2
        adwin.set_int_var(3, DWELL_US)   # Par_3
        adwin.set_int_var(4, 0)          # Par_4 = EDGE_MODE (0=rising)
        adwin.set_int_var(5, DAC_CH)     # Par_5 = DAC_CH
        adwin.set_int_var(6, 1)          # Par_6 = DIR_SENSE (1=DIR High=up)
        adwin.set_int_var(8, CHUNK_US)   # Par_8 = PROCESSDELAY_US (0 = auto-calculate)
        adwin.set_int_var(9, int(overhead_factor * 10))  # Par_9 = OVERHEAD_FACTOR (scaled by 10 for integer)

        print("▶️  Starting process 1…")
        adwin.start_process(1)
        
        # Wait for process to start and verify it's running
        print("⏳ Waiting for process to start...")
        time.sleep(0.1)  # Give process time to start
        
        process_status = adwin.get_process_status(1)
        print(f"   Process status: {process_status}")
        if process_status != "Running":
            print("   ❌ Process failed to start!")
            return False
        
        # Check signature to confirm correct script loaded
        print("🔍 Checking signature...")
        try:
            signature = adwin.get_int_var(80)
            processdelay = adwin.get_int_var(71)
            pd_us = adwin.get_int_var(72)
            pd_ticks = adwin.get_int_var(73)
            print(f"   Signature Par_80 = {signature} (expect 7777)")
            print(f"   Processdelay Par_71 = {processdelay}")
            print(f"   Calculated pd_us Par_72 = {pd_us}")
            print(f"   Calculated pd_ticks Par_73 = {pd_ticks}")
            if signature == 7777:
                print("   ✅ Correct debug script loaded!")
            else:
                print(f"   ❌ Wrong signature! Expected 7777, got {signature}")
                return False
        except Exception as e:
            print(f"   ❌ Error reading signature: {e}")
            return False

        # Arm the sweep
        print("🚀 Arming sweep...")
        adwin.set_int_var(10, 1)         # Par_10 = START

        # Wait for heartbeat to start advancing (prove Event loop is running)
        print("⏳ Waiting for heartbeat to start...")
        initial_hb = adwin.get_int_var(25)
        start_time = time.time()
        
        while time.time() - start_time < 1.0:  # Wait up to 1 second
            try:
                current_hb = adwin.get_int_var(25)
                if current_hb > initial_hb:
                    print(f"   ✅ Heartbeat advancing: {initial_hb} → {current_hb}")
                    break
                time.sleep(0.01)  # 10ms polling
            except Exception as e:
                print(f"   ⚠️  Transient Get_Par error (tolerated): {e}")
                time.sleep(0.01)
        else:
            print("   ❌ Heartbeat not advancing after 1s - process not running!")
            return False

        # ---------- wait for non-blocking handshake ----------
        expected_points = max(2, 2 * N_STEPS - 2)
        per_point_s = (SETTLE_US + DWELL_US) / 1e6
        timeout = max(5.0, expected_points * per_point_s * 10)  # very generous margin for longer dwell times

        # Clear any stale ready flags first
        print("🧹 Clearing any stale ready flags...")
        try:
            adwin.set_int_var(20, 0)  # Clear Par_20 (ready flag)
        except Exception as e:
            print(f"Warning: Could not clear ready flag: {e}")

        print("\n⏳ Waiting for Par_20 == 1 (sweep ready)…")
        t0 = time.time()
        last_hb = adwin.get_int_var(25)
        
        while True:
            try:
                ready = adwin.get_int_var(20)  # ready flag
                hb    = adwin.get_int_var(25)  # heartbeat
                state = adwin.get_int_var(26)  # current state
                elapsed = time.time() - t0
                print(f"  {elapsed:5.2f}s | ready={ready} hb={hb} state={state}", end='\r')
                
                if ready == 1:
                    print()
                    break
                    
                # Check if heartbeat is still advancing (after 100ms grace period)
                if hb <= last_hb and elapsed > 0.1:
                    print(f"\n⚠️  Heartbeat stalled at {hb}!")
                    
                last_hb = hb
                time.sleep(0.05)
            except Exception as e:
                print(f"\n⚠️  Transient Get_Par error (tolerated): {e}")
                time.sleep(0.05)  # Continue polling despite error

            if elapsed > timeout:
                print(f"\n❌ Timeout after {elapsed:.1f}s (expected ~{expected_points * per_point_s:.1f}s)")
                return False

        # ---------- read arrays ----------
        n_points = adwin.get_int_var(21)
        if n_points <= 0:
            raise RuntimeError("n_points <= 0 — nothing to read.")
        print(f"📊 Sweep reports n_points = {n_points} (expected ≈ {expected_points})")

        print("📥 Reading arrays…")
        
        # Add detailed diagnostics for array reading
        print(f"🔍 Diagnostic info:")
        print(f"   n_points = {n_points}")
        print(f"   Expected array length = {n_points}")
        
        # Test array length first
        try:
            array_length_1 = adwin.read_probes('array_length', 1)
            array_length_2 = adwin.read_probes('array_length', 2)
            array_length_3 = adwin.read_probes('array_length', 3)
            print(f"   Data_1 length = {array_length_1}")
            print(f"   Data_2 length = {array_length_2}")
            print(f"   Data_3 length = {array_length_3}")
        except Exception as e:
            print(f"   Error reading array lengths: {e}")
        
        # Test reading a single element first
        try:
            single_count = adwin.read_probes('int_array', 1, 1)
            single_digit = adwin.read_probes('int_array', 2, 1)
            single_pos = adwin.read_probes('int_array', 3, 1)
            print(f"   Single elements - count: {single_count}, digit: {single_digit}, pos: {single_pos}")
        except Exception as e:
            print(f"   Error reading single elements: {e}")
        
        # Now try reading the full arrays with error handling
        try:
            counts = read_int_array(adwin, 1, n_points)                  # Data_1
            print(f"   ✅ Data_1 read successfully: {len(counts)} elements")
            print(f"   First few counts: {counts[:5] if len(counts) >= 5 else counts}")
        except Exception as e:
            print(f"   ❌ Error reading Data_1: {e}")
            counts = []
        
        try:
            dac_digits = read_int_array(adwin, 2, n_points)              # Data_2
            print(f"   ✅ Data_2 read successfully: {len(dac_digits)} elements")
            print(f"   First few digits: {dac_digits[:5] if len(dac_digits) >= 5 else dac_digits}")
        except Exception as e:
            print(f"   ❌ Error reading Data_2: {e}")
            dac_digits = []
        
        # Always compute volts from DAC digits to avoid garbage data from FData_1
        try:
            if dac_digits:
                # Validate DAC digits are in valid range (0-65535)
                valid_digits = []
                invalid_count = 0
                for d in dac_digits:
                    d_int = int(d)
                    if 0 <= d_int <= 65535:
                        valid_digits.append(d_int)
                    else:
                        invalid_count += 1
                        print(f"   ⚠️  Invalid DAC digit: {d_int} (should be 0-65535)")
                
                if invalid_count > 0:
                    print(f"   ⚠️  Found {invalid_count} invalid DAC digits out of {len(dac_digits)}")
                
                volts = [d_to_v(d) for d in valid_digits]
                print(f"   ✅ Volts computed from {len(valid_digits)} valid DAC digits: {len(volts)} elements")
                print(f"   First few volts: {volts[:5] if len(volts) >= 5 else volts}")
            else:
                volts = []
                print(f"   ❌ No DAC digits available for volt computation")
        except Exception as e:
            print(f"   ❌ Error computing volts from DAC digits: {e}")
            volts = []
        
        try:
            pos = read_int_array(adwin, 3, n_points)                     # Data_3
            print(f"   ✅ Data_3 read successfully: {len(pos)} elements")
            print(f"   First few positions: {pos[:5] if len(pos) >= 5 else pos}")
        except Exception as e:
            print(f"   ⚠️  Data_3 not available (production script): {e}")
            # Generate positions from triangle logic for production script
            pos = []
            for i in range(n_points):
                if i < n_points // 2:
                    pos.append(i)  # Forward sweep
                else:
                    pos.append(n_points - 1 - i)  # Reverse sweep
            print(f"   ✅ Generated positions: {pos[:5] if len(pos) >= 5 else pos}")

        print(f"✅ Got arrays: counts={len(counts)}, digits={len(dac_digits)}, volts={len(volts)}, pos={len(pos)}")

        # ---------- additional diagnostics ----------
        print("\n🔍 Additional diagnostics:")
        try:
            # Check if the process is still running
            process_status = adwin.read_probes('process_status', 1)
            print(f"   Process 1 status: {process_status}")
            
            # Check some key parameters
            par_20 = adwin.get_int_var(20)  # ready flag
            par_21 = adwin.get_int_var(21)  # points
            par_25 = adwin.get_int_var(25)  # heartbeat
            par_26 = adwin.get_int_var(26)  # current state
            print(f"   Par_20 (ready): {par_20}")
            print(f"   Par_21 (points): {par_21}")
            print(f"   Par_25 (heartbeat): {par_25}")
            print(f"   Par_26 (state): {par_26}")
            
            # Check if there are any ADwin errors
            try:
                last_error = adwin.read_probes('last_error')
                print(f"   Last ADwin error: {last_error}")
            except Exception:
                print("   No error information available")
                
        except Exception as e:
            print(f"   Error in additional diagnostics: {e}")

        # ---------- summaries ----------
        try:
            total  = adwin.get_int_var(30)      # Par_30
            cmax   = adwin.get_int_var(31)      # Par_31
            imax   = adwin.get_int_var(32)      # Par_32
            avg    = adwin.get_float_var(33)    # FPar_33
            print("\n📈 End-of-sweep summaries:")
            print(f"   total counts: {total}")
            print(f"   max per step: {cmax} (at index {imax})")
            print(f"   average:      {avg:.3f}")
        except Exception:
            print("\nℹ️  Summaries (Par_30..32 / FPar_33) not available (production script) — computing manually.")
            if counts:
                total = sum(counts)
                cmax = max(counts)
                imax = counts.index(cmax)
                avg = total / len(counts)
                print(f"   total counts: {total}")
                print(f"   max per step: {cmax} (at index {imax})")
                print(f"   average:      {avg:.3f}")

        # ---------- quick sanity checks ----------
        print("\n🔍 Voltage progression checks:")
        v_up   = np.linspace(VMIN, VMAX, N_STEPS)
        v_down = np.linspace(VMAX, VMIN, N_STEPS)[1:-1]  # no repeated endpoints
        expected_digits = [v_to_d(v) for v in np.concatenate([v_up, v_down])]
        ok_digits = len(dac_digits) >= len(expected_digits) and all(
            abs(int(dac_digits[i]) - expected_digits[i]) <= 1 for i in range(len(expected_digits))
        )
        print(f"   digits follow triangle? {ok_digits}")

        up = volts[:N_STEPS]
        down = volts[N_STEPS:]
        up_ok = all(up[i] <= up[i+1] + 1e-9 for i in range(len(up)-1)) if len(up) > 1 else True
        down_ok = all(down[i] >= down[i+1] - 1e-9 for i in range(len(down)-1)) if len(down) > 1 else True
        print(f"   monotonic up? {up_ok} | down? {down_ok}")
        if len(volts):
            print(f"   min/max volts: {min(volts):.3f} / {max(volts):.3f}")

        # ---------- show first rows ----------
        print("\nFirst 20 points:")
        print(" idx | counts | digits |   volts  | pos")
        print("-----+--------+--------+----------+-----")
        for i in range(min(20, n_points)):
            print(f"{i:4d} | {int(counts[i]):6d} | {int(dac_digits[i]):6d} | {float(volts[i]):8.4f} | {int(pos[i]):3d}")

        # ---------- release next sweep ----------
        adwin.set_int_var(20, 0)  # clear ready flag so DSP can start the next sweep

        return True

    except Exception as e:
        print(f"\n❌ Error during debug session: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Always clean up
        try:
            adwin.set_int_var(10, 0)  # STOP
        except Exception:
            pass
        try:
            adwin.stop_process(1)
            time.sleep(0.1)
            adwin.clear_process(1)
        except Exception:
            pass


def main():
    p = argparse.ArgumentParser(description='Debug ODMR Arrays – Triangle Sweep (DEBUG ADbasic)')
    p.add_argument('--real-hardware', action='store_true', help='Use real ADwin hardware')
    p.add_argument('--config', type=str, default=None, help='Path to config.json (default: src/config.json)')
    p.add_argument('--tb1', type=str, default='ODMR_Sweep_Counter_Debug.TB1', 
                   help='TB1 filename to load (default: ODMR_Sweep_Counter_Debug.TB1)')
    p.add_argument('--script', type=str, choices=['debug', 'production', 'test'], 
                   help='Convenience option: debug=ODMR_Sweep_Counter_Debug.TB1, production=ODMR_Sweep_Counter.TB1, test=ODMR_Sweep_Counter_Test.TB1')
    p.add_argument('--dwell-us', type=int, default=5000, help='Dwell time in microseconds (default: 5000)')
    p.add_argument('--settle-us', type=int, default=1000, help='Settle time in microseconds (default: 1000)')
    p.add_argument('--overhead-factor', type=float, default=1.2, help='Event loop overhead correction factor (default: 1.2, calibrated for production)')
    args = p.parse_args()

    # Handle convenience script option
    script_map = {
        'debug': 'ODMR_Sweep_Counter_Debug.TB1',
        'production': 'ODMR_Sweep_Counter.TB1', 
        'test': 'ODMR_Sweep_Counter_Test.TB1'
    }
    
    if args.script:
        tb1_filename = script_map[args.script]
        print(f"🎯 Using convenience script: {args.script} -> {tb1_filename}")
    else:
        tb1_filename = args.tb1

    print("🎯 ODMR Arrays Debug Tool — Array Diagnostics")
    print(f"🔧 Hardware mode: {'Real' if args.real_hardware else 'Mock'}")
    print(f"📄 Script: {tb1_filename}")

    ok = debug_odmr_arrays(args.real_hardware, args.config, tb1_filename, args.dwell_us, args.settle_us, args.overhead_factor)
    print("\n✅ Debug session completed!" if ok else "\n❌ Debug session failed!")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
