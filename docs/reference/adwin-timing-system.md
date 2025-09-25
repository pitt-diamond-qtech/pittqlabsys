# ADwin Timing System Documentation

## Overview

The ADwin timing system uses a hybrid approach to optimize `Processdelay` for different dwell times, ensuring responsive communication while maintaining accurate timing.

## Timing Fundamentals

### ADwin Gold II Clock
- **Clock frequency**: ~303 MHz
- **Tick period**: 3.3 ns per tick
- **Processdelay units**: ticks (not microseconds)

### Conversion Formulas
```adbasic
Processdelay_ticks = microseconds * 1000 / 3.3
Processdelay_ticks = microseconds * 303  ' (approximate)

' Convert Processdelay (ticks) to tick_us (microseconds)
tick_us = Processdelay * 3.3 / 1000   ' Convert ticks to µs
```

## Hybrid Processdelay Control

### Parameter: `Par_8` (PROCESSDELAY_US)

**Usage:**
- `Par_8 = 0`: **Auto-calculate** (recommended for most cases)
- `Par_8 > 0`: **Manual override** (for special timing requirements)

### Auto-Calculate Mode (`Par_8 = 0`)

The system automatically calculates optimal `Processdelay` based on dwell time using the `SetProcessdelay()` subroutine:

```adbasic
Sub SetProcessdelay()
  Dim pd_us, pd_ticks As Long
  
  IF (Par_8 > 0) THEN
    pd_us = Par_8   ' Python specified (µs)
  ELSE
    pd_us = Par_3 / 10   ' Auto-calculate: dwell_us / 10
  ENDIF
  
  pd_ticks = pd_us * 300   ' Convert µs to ticks (approximate)
  
  ' Clamp to reasonable bounds
  IF (pd_ticks < 1000) THEN pd_ticks = 1000 ENDIF     ' min 3.3µs
  IF (pd_ticks > 5000000) THEN pd_ticks = 5000000 ENDIF ' max 16.7ms
  
  Processdelay = pd_ticks
EndSub
```

**Benefits:**
- **Short dwells** (100µs-1ms): Fine timing resolution
- **Long dwells** (5ms+): Efficient chunking without excessive Event calls
- **Always responsive**: PC communication every 330µs to 3.3ms

### Manual Override Mode (`Par_8 > 0`)

When `Par_8` is set to a positive value, it specifies the `Processdelay` in microseconds:

```adbasic
Processdelay = Par_8 * 100   ' Convert µs to ticks
```

**Use cases:**
- **Debugging**: Test specific timing scenarios
- **Special requirements**: Very precise timing control
- **Legacy compatibility**: Maintain existing timing behavior

## Timing Examples

### Example 1: Short Dwell (500µs)
```
Dwell time: 500µs
Auto-calculated pd_us: 500µs / 10 = 50µs → clamped to 3.3µs (min)
Processdelay ticks: 3.3µs × 300 = ~1000 ticks
tick_us: 1000 × 3.3 / 1000 = 3.3µs
Chunks: 500µs ÷ 3.3µs = ~150 chunks
Result: Very fine timing resolution
```

### Example 2: Medium Dwell (5ms)
```
Dwell time: 5000µs
Auto-calculated pd_us: 5000µs / 10 = 500µs
Processdelay ticks: 500µs × 300 = ~150000 ticks
tick_us: 150000 × 3.3 / 1000 = 495µs
Chunks: 5000µs ÷ 495µs = ~10 chunks
Result: Optimal balance
```

### Example 3: Long Dwell (50ms)
```
Dwell time: 50000µs
Auto-calculated pd_us: 50000µs / 10 = 5000µs → clamped to 16.7ms (max)
Processdelay ticks: 16.7ms × 300 = ~5000000 ticks
tick_us: 5000000 × 3.3 / 1000 = 16500µs = 16.5ms
Chunks: 50000µs ÷ 16500µs = ~3 chunks
Result: Efficient chunking
```

## Python Usage

### Recommended (Auto Mode)
```python
# Let ADbasic automatically optimize timing
adwin.set_int_var(8, 0)  # Auto-calculate Processdelay
adwin.set_int_var(3, 5000)  # Set 5ms dwell time
```

### Manual Override
```python
# Force specific timing (for debugging or special cases)
adwin.set_int_var(8, 200)  # Force 200µs Processdelay
adwin.set_int_var(3, 5000)  # Set 5ms dwell time
```

### Legacy Compatibility
```python
# Maintain old behavior (fixed 300µs Processdelay)
adwin.set_int_var(8, 300)  # Fixed 300µs Processdelay
```

## State Machine Chunking

The timing system works with the state machine to break long operations into small chunks:

### Dwell State (Case 50)
```adbasic
Case 50     ' DWELL (counting window)
  IF (dwell_rem_us > 0) THEN
    IF (dwell_rem_us > tick_us) THEN
      dwell_rem_us = dwell_rem_us - tick_us
    ELSE
      dwell_rem_us = 0
    ENDIF
  ELSE
    state = 60  ' Move to next state
  ENDIF
```

### Settle State (Case 30)
```adbasic
Case 30     ' SETTLE (excluded from counting)
  IF (settle_rem_us > 0) THEN
    IF (settle_rem_us > tick_us) THEN
      settle_rem_us = settle_rem_us - tick_us
    ELSE
      settle_rem_us = 0
    ENDIF
  ELSE
    state = 40  ' Move to next state
  ENDIF
```

## Performance Characteristics

### Communication Responsiveness
- **Minimum**: 330µs between Event calls
- **Maximum**: 3.3ms between Event calls
- **Typical**: 500µs-1ms for most dwell times

### Timing Accuracy
- **Short dwells**: ±330µs accuracy
- **Medium dwells**: ±500µs accuracy  
- **Long dwells**: ±3.3ms accuracy

### CPU Efficiency
- **Event calls**: 10-15 per dwell (optimal)
- **No blocking**: Event loop always returns quickly
- **Scalable**: Works for any dwell time

## Troubleshooting

### Issue: Poor timing resolution
**Solution**: Use auto-calculate mode (`Par_8 = 0`) or reduce manual `Par_8`

### Issue: Too many Event calls
**Solution**: Increase manual `Par_8` or use auto-calculate mode

### Issue: Communication timeouts
**Solution**: Ensure `Processdelay` is reasonable (330µs - 3.3ms)

## Migration Guide

### From Fixed Timing
```python
# Old approach
adwin.set_int_var(8, 300)  # Fixed 300µs

# New approach (recommended)
adwin.set_int_var(8, 0)     # Auto-calculate
```

### From Manual Timing
```python
# Old approach
adwin.set_int_var(8, 200)  # Manual 200µs

# New approach (if you want same behavior)
adwin.set_int_var(8, 200)  # Still works!
```

The hybrid approach is backward compatible - existing code continues to work unchanged.
