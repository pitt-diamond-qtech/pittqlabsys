# Multi-Waveform ODMR Sweep Counter

This document describes the new multi-waveform ODMR sweep counter ADbasic script that extends the original `ODMR_Sweep_Counter.bas` with support for multiple waveform types.

## Overview

The `ODMR_Sweep_Counter_Multi.bas` script provides the same robust state machine and timing control as the original, but adds waveform selection capabilities through `Par_7`. This allows for different sweep patterns while maintaining the same handshake protocol and timing accuracy.

## Waveform Types

| Par_7 | Waveform | Description | n_points | Notes |
|-------|----------|-------------|----------|-------|
| 0 | Triangle | Bidirectional sweep (up then down) | 2×N_STEPS-2 | Original behavior |
| 1 | Ramp/Saw | Up only, sharp return to start | N_STEPS | Single direction |
| 2 | Sine | One complete sine period | N_STEPS | Smooth oscillation |
| 3 | Square | Constant setpoint | N_STEPS | All steps same voltage |
| 4 | Noise | Random step-to-step | N_STEPS | Pseudo-random values |
| 100 | Custom | User-defined table | N_STEPS | Uses Data_3 array |

## Interface Parameters

### From Python (Input)
- **FPar_1**: Vmin [V] (clamped to [-1, +1])
- **FPar_2**: Vmax [V] (clamped to [-1, +1])  
- **FPar_5**: Square setpoint [V] (for Par_7=3, clamped to [-1, +1])
- **Par_1**: N_STEPS (≥2)
- **Par_2**: SETTLE_US (µs)
- **Par_3**: DWELL_US (µs)
- **Par_4**: EDGE_MODE (0=rising, 1=falling)
- **Par_5**: DAC_CH (1..2)
- **Par_6**: DIR_SENSE (0=DIR Low=up, 1=DIR High=up)
- **Par_7**: WAVEFORM (0-4, 100)
- **Par_8**: PROCESSDELAY_US (µs, 0=auto-calculate)
- **Par_9**: OVERHEAD_FACTOR (1.0=no correction, 1.2=20% overhead)
- **Par_10**: START (1=run, 0=idle)
- **Par_11**: RNG_SEED (random number generator seed, default=12345)

### To Python (Output)
- **Data_1[]**: Counts per step (LONG)
- **Data_2[]**: DAC digits per step (LONG)
- **Data_3[]**: Custom waveform table (LONG, for Par_7=100)
- **Par_20**: Ready flag (1=data ready)
- **Par_21**: Number of points (varies by waveform)
- **Par_25**: Heartbeat counter
- **Par_26**: Current state (255=idle, 10=prep, 30=settle, etc.)
- **Par_71**: Processdelay (ticks)
- **Par_80**: Signature (7777)
- **Par_81**: Waveform type used (0-4, 100)
- **Par_82**: Actual n_points for this waveform

## Usage Examples

### Basic Triangle Waveform (Original Behavior)
```python
# Set parameters
adwin.set_int_var(7, 0)  # Triangle waveform
adwin.set_int_var(1, 100)  # 100 steps
adwin.set_float_var(1, -1.0)  # Vmin
adwin.set_float_var(2, 1.0)   # Vmax

# Start sweep
adwin.set_int_var(10, 1)  # START
adwin.set_int_var(20, 0)  # Clear ready flag

# Wait for completion
while adwin.get_int_var(20) != 1:
    time.sleep(0.1)

# Read results
n_points = adwin.get_int_var(21)  # Will be 198 (2×100-2)
counts = adwin.read_probes('int_array', 'Data_1', 0, n_points)
```

### Sine Waveform
```python
# Set parameters for sine wave
adwin.set_int_var(7, 2)  # Sine waveform
adwin.set_int_var(1, 50)  # 50 steps
adwin.set_float_var(1, -1.0)  # Vmin
adwin.set_float_var(2, 1.0)   # Vmax

# Start sweep
adwin.set_int_var(10, 1)
adwin.set_int_var(20, 0)

# Wait and read (n_points will be 50)
```

### Square Waveform
```python
# Set parameters for square wave
adwin.set_int_var(7, 3)  # Square waveform
adwin.set_int_var(1, 20)  # 20 steps
adwin.set_float_var(5, 0.5)  # Square setpoint at 0.5V

# Start sweep
adwin.set_int_var(10, 1)
adwin.set_int_var(20, 0)

# All 20 steps will have the same voltage (0.5V)
```

### Custom Table Waveform
```python
# Create custom waveform table
custom_volts = np.linspace(-1.0, 1.0, 30)  # 30 steps
custom_digits = [(v + 10.0) * 65535.0 / 20.0 for v in custom_volts]

# Set parameters
adwin.set_int_var(7, 100)  # Custom table
adwin.set_int_var(1, 30)   # 30 steps
adwin.set_data_long(3, custom_digits)  # Populate Data_3

# Start sweep
adwin.set_int_var(10, 1)
adwin.set_int_var(20, 0)
```

## Implementation Details

### Waveform Calculation
The waveform calculation happens in Case 30 of the state machine, where the target voltage for each step is computed based on `Par_7`:

- **Triangle**: Bidirectional linear interpolation
- **Ramp**: Unidirectional linear interpolation  
- **Sine**: Uses built-in Sin() function with proper phase shifting
- **Square**: Constant value from FPar_5
- **Noise**: Linear congruential generator (LCG)
- **Custom**: Direct lookup from Data_3 array

### Sine Approximation
The sine function uses the built-in `Sin()` function with proper phase shifting to ensure the waveform starts at the minimum voltage and completes one full period.

### Random Number Generation
The noise waveform uses a linear congruential generator with bit masking for modulo 2³²:
```
temp = a × seed + c
seed = temp AND 0xFFFFFFFF
```
Where a=1664525, c=1013904223, providing a period of 2³².

### Custom Table Safety
The custom table (Data_3) is limited to 1000 elements for memory safety. If the requested number of steps exceeds this limit, the script falls back to the minimum voltage.

## Testing

Use the provided test script to verify functionality:

```bash
# Test all waveforms with mock hardware
python examples/test_multi_waveform_odmr.py --test-all --mock-hardware

# Test specific waveform with real hardware
python examples/test_multi_waveform_odmr.py --waveform 2 --real-hardware

# List available waveforms
python examples/test_multi_waveform_odmr.py --list-waveforms
```

## Integration with Experiments

To integrate with existing ODMR experiments, simply change the binary path:

```python
# In your experiment setup
script_path = get_adwin_binary_path('ODMR_Sweep_Counter_Multi.TB1')

# Set waveform type before starting
adwin.set_int_var(7, waveform_type)  # 0-4, 100
```

## Performance Considerations

- **Triangle**: Same performance as original (bidirectional)
- **Ramp/Sine/Square/Noise**: ~2× faster (single direction)
- **Custom**: Same as single direction, but requires Data_3 setup
- **Memory**: Additional 4KB for Data_3 array (1000 × 4 bytes)

## Backward Compatibility

The script maintains full backward compatibility with the original `ODMR_Sweep_Counter.bas`:
- Same handshake protocol (Par_20, Par_10)
- Same timing control (Par_8, Par_9)
- Same counter configuration (Par_4, Par_6)
- Same data output format (Data_1, Data_2)

The only difference is the additional waveform selection via Par_7 and the corresponding changes to n_points calculation.
