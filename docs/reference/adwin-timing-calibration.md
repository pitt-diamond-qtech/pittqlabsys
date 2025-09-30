# ADwin Timing Calibration Documentation

## Overview

This document describes the calibration process for ADwin timing systems to achieve precise counting measurements. The calibration addresses event loop overhead that causes measured dwell times to be longer than requested dwell times.

## The Problem

When using ADwin for time-windowed counting (e.g., ODMR experiments), the measured counts often exceed expected values due to event loop overhead. This overhead comes from:

1. **Event loop execution time**: Each Event call takes time to execute
2. **State machine processing**: Time spent in state transitions
3. **Hardware communication**: Time for DAC updates and counter operations
4. **Watchdog resets**: Periodic safety checks

### Example Problem

```
Requested dwell time: 5000µs (5ms)
Expected counts at 50kHz: 250 counts
Actual measured counts: 300 counts (20% higher)
Effective dwell time: ~6000µs (6ms)
```

## The Solution: Overhead Factor Calibration

### How It Works

The calibration system uses an **overhead factor** to correct the effective tick duration:

```adbasic
' Calculate base tick_us, then apply overhead correction
tick_us = Round(Processdelay * 3.3 / 1000.0 * overhead_factor)
```

Where:
- `Processdelay` = ADwin event loop period in ticks
- `3.3 / 1000.0` = Conversion from ticks to microseconds
- `overhead_factor` = Calibration multiplier (default: 1.2)

### Parameter: `Par_9` (OVERHEAD_FACTOR)

**Usage:**
- `Par_9 = 10` → `overhead_factor = 1.0` (no correction)
- `Par_9 = 12` → `overhead_factor = 1.2` (20% overhead correction)
- `Par_9 = 15` → `overhead_factor = 1.5` (50% overhead correction)

**Default:** `Par_9 = 12` (1.2× correction) for production use

## Calibration Process

### Step 1: Setup Test Signal

1. **Signal Generator**: 50kHz square wave, 3.5V amplitude, 200ns pulse width
2. **Connection**: Connect to ADwin Counter 1 input
3. **Verify**: Check signal with oscilloscope if available

### Step 2: Run Calibration Tests

Use the debug script with different dwell times:

```bash
# Test 1: Short dwell (500µs)
python examples/debug_odmr_arrays.py --real-hardware --dwell-us 500 --overhead-factor 1.0

# Test 2: Medium dwell (5000µs) 
python examples/debug_odmr_arrays.py --real-hardware --dwell-us 5000 --overhead-factor 1.0

# Test 3: Long dwell (10000µs)
python examples/debug_odmr_arrays.py --real-hardware --dwell-us 10000 --overhead-factor 1.0
```

### Step 3: Calculate Overhead Factor

For each test, calculate the overhead factor:

```
overhead_factor = expected_counts / measured_counts
```

**Example:**
- Expected: 250 counts (5000µs × 50kHz)
- Measured: 300 counts
- Overhead factor: 250/300 = 0.833
- Correction factor: 1/0.833 = 1.2

### Step 4: Verify Calibration

Test with the calculated overhead factor:

```bash
python examples/debug_odmr_arrays.py --real-hardware --dwell-us 5000 --overhead-factor 1.2
```

**Expected result**: Counts should now match expected values within ±2%

## Calibration Results

### Typical Overhead Factors

| System Configuration | Overhead Factor | Notes |
|---------------------|-----------------|-------|
| **Production (Default)** | **1.2** | **Recommended for most systems** |
| Debug/Development | 1.0-1.1 | Lower overhead due to simpler processing |
| High-load systems | 1.3-1.5 | Multiple processes or complex state machines |
| Optimized systems | 1.1-1.2 | Minimal processing overhead |

### Validation Tests

After calibration, verify accuracy across different dwell times:

| Dwell Time | Expected Counts | Measured Counts | Accuracy |
|------------|-----------------|-----------------|----------|
| 500µs | 25 | 25 | 100% |
| 5000µs | 250 | 250 | 100% |
| 10000µs | 500 | 500 | 100% |

## Implementation Details

### ADbasic Code

The calibration is implemented in the `Init` section:

```adbasic
' Use Par_9 as overhead correction factor (scaled by 10: 10=1.0, 12=1.2, 20=2.0)
overhead_factor = Par_9 / 10.0  ' Convert scaled integer back to float
IF (overhead_factor <= 0.0) THEN overhead_factor = 1.2  ' Default to 1.2x for production
' Calculate base tick_us, then apply overhead correction
tick_us = Round(Processdelay * 3.3 / 1000.0 * overhead_factor)   ' Apply overhead correction
```

### Python Integration

The overhead factor is passed from Python to ADbasic:

```python
# Set overhead factor (1.2 = 20% correction)
adwin.set_int_var(9, int(1.2 * 10))  # 12 = 1.2× scaled by 10
```

## Troubleshooting

### Issue: Counts Still Too High

**Symptoms**: Even with overhead factor, counts exceed expected values

**Solutions**:
1. **Increase overhead factor**: Try 1.3 or 1.4
2. **Check signal quality**: Ensure clean 50kHz signal
3. **Verify counter configuration**: Check edge detection settings
4. **System load**: Close unnecessary processes

### Issue: Counts Too Low

**Symptoms**: Counts are lower than expected

**Solutions**:
1. **Decrease overhead factor**: Try 1.1 or 1.0
2. **Check signal amplitude**: Ensure sufficient signal strength
3. **Counter sensitivity**: Verify input threshold settings
4. **Timing issues**: Check for signal jitter

### Issue: Inconsistent Results

**Symptoms**: Counts vary between runs

**Solutions**:
1. **Signal stability**: Use stable signal generator
2. **System temperature**: Allow warm-up time
3. **Power supply**: Check for voltage fluctuations
4. **Cable connections**: Ensure solid connections

## Best Practices

### 1. Regular Calibration

- **Frequency**: Recalibrate monthly or after system changes
- **Documentation**: Record calibration factors and dates
- **Validation**: Test across multiple dwell times

### 2. Environment Control

- **Temperature**: Maintain stable lab temperature
- **Power**: Use clean, stable power supplies
- **Vibrations**: Minimize mechanical vibrations

### 3. Signal Quality

- **Generator**: Use high-quality signal generator
- **Cables**: Use proper impedance-matched cables
- **Connections**: Ensure clean, tight connections

### 4. System Optimization

- **Processes**: Minimize running processes
- **Memory**: Ensure sufficient available memory
- **CPU**: Avoid high CPU usage during measurements

## Integration with Experiments

### ODMR Experiments

The calibrated timing system is automatically used in ODMR experiments:

```python
# The experiment automatically uses the calibrated timing
experiment = ODMRSweepContinuousExperiment(devices)
experiment.setup()  # Uses calibrated overhead factor
```

### Custom Experiments

For custom experiments, set the overhead factor:

```python
# Set calibrated overhead factor
adwin.set_int_var(9, int(1.2 * 10))  # 1.2× correction
adwin.set_int_var(3, 5000)  # 5ms dwell time
```

## References

- [ADwin Timing System Documentation](adwin-timing-system.md)
- [ADwin Counter Modes Documentation](adwin-counter-modes.md)
- ADwin Gold II Manual - Timing and Counter Functions
- ODMR Experiment Implementation Guide

## Version History

- **v1.0** (2024): Initial calibration system implementation
- **v1.1** (2024): Added production default of 1.2×
- **v1.2** (2024): Enhanced troubleshooting and best practices

---

**Note**: This calibration system is essential for accurate ODMR measurements. Always verify calibration before running critical experiments.
