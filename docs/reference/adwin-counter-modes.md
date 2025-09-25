# ADwin Counter Modes and Directions

This document explains how ADwin counters work, the different counting modes available, and how to configure them for various applications.

## Overview

ADwin counters can operate in two main modes:
1. **Clock/Direction** - Simple pulse counting with direction control
2. **A/B Quadrature** - Two-phase signal decoding for encoders

## 1. Clock/Direction Mode

### How It Works

You provide the counter with:
- **CLK**: A pulse for each event to count
- **DIR**: A level that determines counting direction

### Visual Example

```
DIR:  ──────────────── High (count UP) ────────────────
CLK:   _   _   _   _   _   _   _   _   _   _           (pulses)
        |   |   |   |   |   |   |   |   |   |
Count:  0→1→2→3→4→5→6→7→8→9  ...  (rising edges add 1 when DIR=High)
```

If DIR = Low, the same edges subtract (count down).

### Configuration Bits

- **bit 0**: Mode selection
  - `0` = Clock/Direction (use CLK + DIR)
  - `1` = A/B Quadrature (use A + B)

- **bit 2**: Invert A/CLK
  - Clock/Dir: flips which CLK edge counts (rising vs falling)
  - A/B: inverts A channel

- **bit 3**: Invert B/DIR
  - Clock/Dir: flips the DIR sense (High=down instead of up)
  - A/B: inverts B channel

- **bit 4-5**: External pin function + enable
  - Select whether external pin acts as CLR (clear) or LATCH
  - Enable/disable external pin functionality

### When to Use

Perfect for:
- TTL pulse sources (APD pulses, function generator)
- Simple event counting
- ODMR photon counting

### Example Configuration

```adbasic
' Clock/Dir, count up on rising edges (DIR tied high)
Cnt_Enable(0)          ' disable while configuring
Cnt_Clear(0001b)       ' clear counter 1
Cnt_Mode(1, 00000000b) ' mode=Clock/Dir, no inversions, ext CLR/LATCH disabled
Cnt_SE_Diff(0000b)     ' single-ended TTL inputs
Cnt_Enable(0001b)      ' enable counter 1
```

**For falling-edge counting**: `Cnt_Mode(1, 00000100b)` (set bit 2)

## 2. A/B Quadrature Mode

### How It Works

You provide two square waves (A and B) shifted by 90°. Direction is encoded in which signal leads the other.

### Visual Example

```
A:  ┌─┐   ┌─┐   ┌─┐
    │ │   │ │   │ │
    └─┴───┘ └───┘ └───
B:    ┌─┐   ┌─┐   ┌─┐
      │ │   │ │   │ │
      └─┴───┘ └───┘ └───

Forward (A leads B): count UP
Reverse (B leads A): count DOWN
```

The counter watches edge order to decide direction automatically.

### Decoding Options

Some counters support X1/X2/X4 decoding:
- **X1**: Count one edge per cycle
- **X2**: Count two edges per cycle  
- **X4**: Count all four edges per cycle (highest resolution)

### When to Use

Perfect for:
- Rotary encoders
- Linear encoders
- Motor position feedback
- Any application requiring both position and direction

## Counter Mode Bit Patterns

### Clock/Direction Examples

| Bit Pattern | Description |
|-------------|-------------|
| `00000000b` | Clock/Dir, rising edges, count up, no external pin |
| `00000100b` | Clock/Dir, falling edges, count up, no external pin |
| `00001000b` | Clock/Dir, rising edges, count down, no external pin |
| `00001100b` | Clock/Dir, falling edges, count down, no external pin |

### A/B Quadrature Examples

| Bit Pattern | Description |
|-------------|-------------|
| `00000001b` | A/B Quadrature, X1 decoding, no inversions |
| `00000101b` | A/B Quadrature, X1 decoding, invert A |
| `00001001b` | A/B Quadrature, X1 decoding, invert B |
| `00001101b` | A/B Quadrature, X1 decoding, invert both A and B |

## LATCH vs GATE

### LATCH (Software Method)

A **latch** is a snapshot mechanism:
- Short pulse copies live count into latch register
- Counting continues uninterrupted
- Get per-window counts by subtracting consecutive latched values

```adbasic
' Example: Count during dwell window
Cnt_Latch(0001b)           ' snapshot current count
old_cnt = Cnt_Read_Latch(1) ' read latched value
' ... dwell time ...
Cnt_Latch(0001b)           ' snapshot again
new_cnt = Cnt_Read_Latch(1) ' read new latched value
counts = new_cnt - old_cnt   ' difference = counts during dwell
```

### GATE (Hardware Method)

A **gate** stops counting outside the measurement window:
- External logic gates the CLK signal
- Counter only sees pulses during active periods
- More complex hardware setup required

For most applications, the software latch method is preferred as it's simpler and more flexible.

## Troubleshooting Common Issues

### Issue: Counter Counting Down Instead of Up

**Symptoms**: Negative delta values, overflow in calculations

**Solutions**:
1. **Check DIR signal**: Ensure DIR is tied High for count up
2. **Invert DIR sense**: Use `Cnt_Mode(1, 00001000b)` to invert DIR
3. **Force count up**: Use `Cnt_Mode(1, 00000110b)` to force up counting

### Issue: Wrong Edge Detection

**Symptoms**: Counts don't match expected signal frequency

**Solutions**:
1. **Rising edges**: Use `Cnt_Mode(1, 00000000b)`
2. **Falling edges**: Use `Cnt_Mode(1, 00000100b)`
3. **Check signal polarity**: Verify CLK signal levels

### Issue: Overflow in Calculations

**Symptoms**: Results showing `2147483647` (2^31-1)

**Solutions**:
1. **Use proper delta calculation**:
   ```adbasic
   fd = Float(cur_cnt) - Float(last_cnt)
   IF (fd < 0.0) THEN
     fd = fd + 4294967296.0  ' handle wrap
   ENDIF
   ```
2. **Clamp results**:
   ```adbasic
   IF (fd > 2147483647.0) THEN
     fd = 2147483647.0
   ENDIF
   ```

## Best Practices

1. **Always disable counter** before reconfiguring
2. **Clear counter** before starting measurements
3. **Use software latch** for time-windowed counting
4. **Handle counter wrap** in delta calculations
5. **Validate counter direction** with known test signals
6. **Use appropriate mode** for your signal type (Clock/Dir vs A/B)

## References

- ADwin Gold II Manual - Counter Functions
- ADbasic Language Reference - Counter Commands
- Hardware-specific counter pin assignments
