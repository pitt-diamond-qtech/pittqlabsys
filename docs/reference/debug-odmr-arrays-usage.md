# Debug ODMR Arrays Script Usage

## Overview

The `debug_odmr_arrays.py` script is a diagnostic tool for testing and debugging ADwin-based ODMR sweep counting functionality. It provides comprehensive testing of the ADbasic state machine, counter timing, and data collection.

## Purpose

- **Test ADbasic Scripts**: Verify that ADbasic scripts load, compile, and run correctly
- **Debug Counting Issues**: Diagnose problems with photon counting and timing
- **Validate Parameters**: Test different dwell times, settle times, and sweep parameters
- **Monitor State Machine**: Track the ADbasic state progression in real-time
- **Calibrate Timing**: Test and calibrate event loop overhead factors

## Usage

### Basic Usage

```bash
# Use debug script with real hardware (default)
python examples/debug_odmr_arrays.py --real-hardware

# Use production script with real hardware
python examples/debug_odmr_arrays.py --real-hardware --script production

# Use test script with real hardware
python examples/debug_odmr_arrays.py --real-hardware --script test
```

### Command Line Options

```bash
python examples/debug_odmr_arrays.py [OPTIONS]
```

**Hardware Options:**
- `--real-hardware`: Use real ADwin hardware (required for actual testing)
- `--config PATH`: Path to config.json file (default: src/config.json)

**Script Selection:**
- `--script {debug,production,test}`: Convenience option to select script
  - `debug`: Uses `ODMR_Sweep_Counter_Debug.TB1` (default)
  - `production`: Uses `ODMR_Sweep_Counter.TB1`
  - `test`: Uses `ODMR_Sweep_Counter_Test.TB1`
- `--tb1 FILENAME`: Direct TB1 filename specification

**Timing Parameters:**
- `--dwell-us MICROSECONDS`: Dwell time in microseconds (default: 5000)
- `--settle-us MICROSECONDS`: Settle time in microseconds (default: 1000)
- `--overhead-factor FACTOR`: Event loop overhead correction factor (default: 1.2)

## Expected Output

### Successful Run
```
🎯 ODMR Arrays Debug Tool — Array Diagnostics
🔧 Hardware mode: Real
📄 Script: ODMR_Sweep_Counter_Debug.TB1

============================================================
ODMR ARRAYS DEBUG SESSION – new DEBUG ADbasic (non-blocking)
============================================================

🔧 Loading real hardware...
✅ Adwin loaded: <class 'src.Controller.adwin_gold.AdwinGoldDevice'>
✅ Connected: True

📁 Loading TB1: /path/to/ODMR_Sweep_Counter_Debug.TB1
⚙️ Applying parameters…
▶️ Starting process 1…
🔍 Checking signature...
   ✅ Correct debug script loaded!

🚀 Arming sweep...
⏳ Waiting for heartbeat to start...
   ✅ Heartbeat advancing: 1234 → 5678

🧹 Clearing any stale ready flags...
⏳ Waiting for Par_20 == 1 (sweep ready)…
  0.15s | ready=1 n_points=18 hb=4692

📊 Sweep reports n_points = 18 (expected ≈ 18)
📥 Reading arrays…
✅ Data_1 read successfully: 18 elements
✅ Data_2 read successfully: 18 elements
✅ Volts computed from 18 valid DAC digits: 18 elements
✅ Data_3 read successfully: 18 elements

📈 End-of-sweep summaries:
   total counts: 5403
   max per step: 301 (at index 4)
   average: 300.167

First 20 points:
 idx | counts | digits |   volts  | pos
-----+--------+--------+----------+-----
   0 |    300 |  29491 | -0.9999 |   0
   1 |    300 |  30219 | -0.7778 |   1
   2 |    300 |  30947 | -0.5556 |   2
   ...
```

### Key Metrics to Check

1. **Points Collected**: Should match expected (18 for 10 steps)
2. **Count Values**: Should be consistent (~100-300 counts per point)
3. **State Progression**: Should show proper state machine operation
4. **Voltage Range**: Should span from -1V to +1V
5. **Triangle Pattern**: Position array should show triangle sweep pattern

## Troubleshooting

### Common Issues

**Timeout Errors:**
```
❌ Timeout after 10.0s (expected ~0.5s)
```
- **Cause**: ADbasic script not responding or stuck in state
- **Solution**: Check signal generator connection, reduce dwell time, or restart ADwin

**Wrong Count Values:**
```
Point 1: 2147483647  # 32-bit overflow
```
- **Cause**: Counter direction mismatch or timing issues
- **Solution**: Check `EDGE_MODE` and `DIR_SENSE` parameters

**Only 2 Points Collected:**
```
📊 Points collected: 2 (expected ≈ 18)
```
- **Cause**: Sweep not starting properly or parameters not set
- **Solution**: Check parameter sequence, verify START command

**Process Not Starting:**
```
❌ Process failed to start!
```
- **Cause**: ADbasic compilation error or memory issues
- **Solution**: Check script syntax, reduce array sizes

### Parameter Tuning

**Dwell Time Calibration:**
```bash
# Test different dwell times
python examples/debug_odmr_arrays.py --real-hardware --dwell-us 1000
python examples/debug_odmr_arrays.py --real-hardware --dwell-us 5000
python examples/debug_odmr_arrays.py --real-hardware --dwell-us 10000
```

**Overhead Factor Calibration:**
```bash
# Test different overhead factors
python examples/debug_odmr_arrays.py --real-hardware --overhead-factor 1.0
python examples/debug_odmr_arrays.py --real-hardware --overhead-factor 1.2
python examples/debug_odmr_arrays.py --real-hardware --overhead-factor 1.5
```

## Integration with Production Code

The debug script validates the same ADbasic functionality used by:
- `ODMRSweepContinuousExperiment` in `src/Model/experiments/odmr_sweep_continuous.py`
- Production ADbasic scripts in `src/Controller/binary_files/ADbasic/`

Use this script to verify ADwin functionality before running full experiments.

## Related Documentation

- [ADwin Timing Calibration](adwin-timing-calibration.md)
- [ODMR Continuous Sweep Experiment](../experiments/odmr-sweep-continuous.md)
- [ADbasic Best Practices](adbasic-best-practices.md)
