# Sequence Language and Pipeline Documentation

## Overview

The PittQLabSys includes a sophisticated system for defining and executing arbitrary pulse sequences on the Tektronix AWG520 arbitrary waveform generator. This system provides multiple layers of abstraction, from a simple human-readable text language to optimized hardware-specific output files.

## Architecture Overview

The system follows a multi-layer architecture:

```
User Text Language → Sequence Parser → Sequence Description → Sequence Builder → AWG520 Optimizer → AWG Files
```

1. **User Text Language**: Human-readable sequence definitions
2. **Sequence Parser**: Converts text to structured data
3. **Sequence Description**: Intermediate representation with variables and metadata
4. **Sequence Builder**: Hardware-agnostic sequence optimization
5. **AWG520 Optimizer**: Hardware-specific optimization and file generation
6. **AWG Files**: Final `.wfm` and `.seq` files for the AWG520

## Sequence Language Syntax

### Basic Structure

Sequences are defined using a simple text format with the following components:

```
sequence: name=experiment_name, type=experiment_type, duration=total_duration, sample_rate=sample_rate, repeat=repeat_count

# Variable definitions
variable variable_name, start=start_value, stop=stop_value, steps=number_of_steps

# Pulse definitions
pulse_type pulse on channel channel_number at time, shape, duration, amplitude

# Control structures
loop variable_name:
    # nested pulses
end loop

if condition:
    # conditional pulses
end if
```

### Sequence Header

The `sequence:` line defines global parameters:

- **name**: Identifier for the sequence
- **type**: Type of experiment (e.g., "odmr", "rabi", "custom")
- **duration**: Total sequence duration with units (e.g., "1ms", "100μs")
- **sample_rate**: Sampling rate with units (e.g., "1GHz", "100MHz")
- **repeat**: Number of repetitions for statistics (e.g., 50000)

**Example:**
```
sequence: name=rabi_experiment, type=rabi, duration=1μs, sample_rate=1GHz, repeat=50000
```

### Variable Definitions

Variables define scan parameters with range-based syntax:

```
variable pulse_duration, start=100ns, stop=1000ns, steps=50
variable laser_power, start=0.5V, stop=2.0V, steps=10
variable frequency, start=1MHz, stop=10MHz, steps=20
```

**Supported Units:**
- **Time**: ns, μs, us, ms, s
- **Voltage**: V
- **Frequency**: Hz, kHz, MHz, GHz
- **Unitless**: Numbers without units

### Pulse Definitions

Pulse syntax: `pulse_type pulse on channel channel_number at time, shape, duration, amplitude`

**Pulse Types:**
- `pi/2`, `pi`, `3pi/2` (standard qubit pulses)
- `laser`, `microwave`, `readout` (functional descriptions)
- Custom names (e.g., `excitation`, `detection`)

**Shapes:**
- `square` - Rectangular pulse
- `gaussian` - Gaussian pulse
- `sech` - Hyperbolic secant pulse
- `lorentzian` - Lorentzian pulse
- `sine` - Sine wave
- `loadfile` - Load from external file

**Example:**
```
pi/2 pulse on channel 1 at 0ns, gaussian, 100ns, 1.0
laser pulse on channel 2 at 200ns, square, 500ns, 0.8
```

### Control Structures

#### Loops

```
loop pulse_duration:
    pi/2 pulse on channel 1 at 0ns, gaussian, pulse_duration, 1.0
    wait 100ns
    pi pulse on channel 1 at 100ns, gaussian, pulse_duration, 1.0
end loop
```

#### Conditionals

```
if laser_power > 1.0:
    laser pulse on channel 2 at 0ns, square, 1μs, laser_power
else:
    laser pulse on channel 2 at 0ns, square, 1μs, 0.5
end if
```

### Preset Experiments

The system includes predefined experiment templates:

```
# Load ODMR experiment
load preset: odmr

# Load Rabi experiment
load preset: rabi

# Load Spin Echo experiment
load preset: spin_echo
```

## Complete Example

```
sequence: name=rabi_scan, type=rabi, duration=2μs, sample_rate=1GHz, repeat=50000

# Define scan variables
variable pulse_duration, start=50ns, stop=500ns, steps=20
variable laser_power, start=0.5V, stop=2.0V, steps=5

# Define the pulse sequence
pi/2 pulse on channel 1 at 0ns, gaussian, pulse_duration, 1.0
wait 100ns
pi pulse on channel 1 at 100ns, gaussian, pulse_duration, 1.0
wait 200ns
laser pulse on channel 2 at 300ns, square, 1μs, laser_power
```

## Pipeline Components

### 1. SequenceTextParser

**File**: `src/Model/sequence_parser.py`

Parses the human-readable text format into structured data:
- Extracts sequence header parameters
- Parses variable definitions with units
- Converts pulse definitions to PulseDescription objects
- Handles control structures (loops, conditionals)
- Loads preset experiments

**Key Methods:**
- `parse_text(text)`: Main parsing method
- `parse_file(filepath)`: Parse from file
- `parse_preset(preset_name)`: Load preset experiment

### 2. SequenceDescription

**File**: `src/Model/sequence_description.py`

Intermediate data structure containing:
- Sequence metadata (name, type, duration, sample_rate, repeat_count)
- Variable definitions with scan ranges
- Pulse descriptions with timing and parameters
- Loop and conditional structures

**Key Classes:**
- `SequenceDescription`: Main container
- `PulseDescription`: Individual pulse definition
- `VariableDescription`: Scan variable with range and steps
- `LoopDescription`: Loop structure
- `ConditionalDescription`: Conditional structure

### 3. SequenceBuilder

**File**: `src/Model/sequence_builder.py`

Hardware-agnostic sequence optimization:
- Converts SequenceDescription to Sequence objects
- Handles memory optimization strategies
- Splits sequences at optimal boundaries
- Creates optimized sequence chunks

**Key Methods:**
- `build_sequence(description)`: Build from description
- `optimize_for_memory_constraints(sequence, max_samples)`: Memory optimization
- `_split_sequence_at_boundaries(sequence, max_samples)`: Sequence splitting

### 4. AWG520SequenceOptimizer

**File**: `src/Model/awg520_optimizer.py`

Hardware-specific optimization for AWG520:
- Converts optimized sequences to AWG520 format
- Handles 4M-word memory constraints
- Generates waveform files (`.wfm`)
- Creates sequence table files (`.seq`)
- Implements arming sequence (laser on for full duration)

**Key Methods:**
- `optimize_sequence_for_awg520(sequence)`: Main optimization
- `create_waveforms(sequence)`: Generate .wfm files
- `create_sequence_file(sequence)`: Generate .seq file

### 5. AWGFile

**File**: `src/Model/awg_file.py`

Low-level file I/O for AWG520:
- Writes binary waveform files (`.wfm`)
- Writes sequence table files (`.seq`)
- Handles AWG520-specific file formats

## Memory Optimization Strategy

The system handles the AWG520's 4M-word memory constraint through:

1. **Waveform-Level Optimization**: Compresses or chunks long waveforms
2. **Sequence Splitting**: Breaks sequences at optimal boundaries
3. **Pattern Repetition**: Uses sequence file looping for repeated patterns
4. **Dead Time Handling**: Optimizes long periods of no output

**Important Note**: The `repeat` field in sequence headers is used for **experiment statistics** (e.g., 50,000 repetitions for qubit measurements), not for memory optimization. Memory optimization is handled separately at the waveform level.

## File Generation

### Waveform Files (.wfm)

- Binary files containing actual waveform data
- Generated for each unique pulse shape
- Optimized for memory constraints
- Not tracked in version control (too large)

### Sequence Files (.seq)

- Text files defining the sequence table
- Maps waveforms to sequence positions
- Includes repetition counts and timing
- Tracked in version control as templates

## Usage Examples

### Basic Usage

```python
from src.Model.sequence_parser import SequenceTextParser
from src.Model.sequence_builder import SequenceBuilder
from src.Model.awg520_optimizer import AWG520SequenceOptimizer

# Parse text sequence
parser = SequenceTextParser()
desc = parser.parse_text(user_text)

# Build optimized sequence
builder = SequenceBuilder()
sequence = builder.build_sequence(desc)

# Optimize for AWG520
optimizer = AWG520SequenceOptimizer()
awg_seq = optimizer.optimize_sequence_for_awg520(sequence)

# Generate files
optimizer.create_waveforms(awg_seq)
optimizer.create_sequence_file(awg_seq)
```

### Running the Example

```bash
cd examples/awg520_templates
python generate_example_sequence.py
```

This generates:
- Waveform files in `waveforms_out/`
- Sequence file `rabi_experiment.seq`
- Demonstrates the full pipeline

## Testing

The system includes comprehensive test coverage:

```bash
# Run all tests
python -m pytest

# Run specific test files
python -m pytest tests/test_sequence_parser.py
python -m pytest tests/test_sequence_builder.py
python -m pytest tests/test_awg520_optimizer.py

# Run with coverage
python -m pytest --cov=src
```

## Future Enhancements

1. **Additional Pulse Shapes**: More mathematical functions
2. **Advanced Control**: Nested loops and complex conditionals
3. **Real-time Optimization**: Dynamic memory management
4. **Hardware Abstraction**: Support for other AWG models
5. **Visual Editor**: GUI for sequence design

## Upcoming Optimization Plan

### AWG520 Memory Optimization Strategy (Next Phase)

Since the `.seq` file's `repeat` field is now reserved for qubit statistics (e.g., 50,000 repetitions for measurements), we need a new approach for memory optimization.

#### Critical Missing Feature: Variable Scanning with Timing Adjustment

**The Problem**: When scanning variables like `pulse_duration`, the current pipeline doesn't handle timing adjustments for subsequent pulses and dead times.

**Example**: If `pulse_duration` changes from 100ns to 200ns:
- **Pulse 1**: pi/2 at 0ns, duration = 100ns → 200ns
- **Pulse 2**: pi at 100ns → **Should become 200ns** (100ns + new duration)
- **Pulse 3**: laser at 200ns → **Should become 300ns** (200ns + new duration)

**Where to Implement**: This timing adjustment logic belongs in **`SequenceBuilder`** because:
1. It's **pure sequence logic** - mathematical timing calculations, no hardware dependencies
2. It needs to generate multiple sequences (one per scan point) with adjusted timing
3. The `AWG520SequenceOptimizer` should only handle hardware-specific concerns (memory, file formats)

**Implementation Requirements**:
1. **Generate scan sequences**: Create one sequence per variable combination
2. **Adjust timing**: Recalculate all subsequent pulse timings based on variable changes
3. **Return multiple sequences**: Pass all scan sequences to the hardware optimizer
4. **Handle arming sequence**: Add laser-on sequence for full duration as first entry

**Architecture Flow**:
```
SequenceDescription → SequenceBuilder → [Multiple Sequences with Adjusted Timing] → AWG520SequenceOptimizer → Hardware Files
```

The `SequenceBuilder` handles the **logical timing math**, while `AWG520SequenceOptimizer` handles the **hardware-specific optimization**.

#### New Memory Optimization Strategy

1. **Waveform-Level Optimization** (Primary Strategy)
   - **Mathematical Representation**: Store dead times as `(start, end, value)` instead of samples
   - **Pulse Parameter Storage**: Store pulse parameters and regenerate waveforms (e.g., `gaussian, amp=1.0, width=100ns`)
   - **Run-Length Encoding**: Compress long sequences of constant values (perfect for dead times)
   - **Delta Encoding**: Store differences between consecutive samples for smooth transitions

2. **Sequence Splitting** (Secondary Strategy)
   - **Boundary Detection**: Find natural break points (e.g., between pulse groups)
   - **Optimal Chunking**: Create chunks that maximize memory efficiency
   - **Cross-Reference**: Use sequence file to reference multiple waveform chunks

3. **Smart Dead-Time Handling**
   - **Mathematical Dead Times**: Store as `(start_time, end_time, constant_value)` instead of samples
   - **Variable Sampling**: Use lower sampling rates for long dead times
   - **Hybrid Approach**: Combine high-resolution pulses with mathematical dead-time representation

#### Implementation Plan

1. **Remove Dead-Time Repetition Logic**
   - Eliminate the `create_repetition_patterns` method
   - Remove repetition-based memory optimization

2. **Add Waveform Compression**
   - Implement mathematical representation for dead times and pulse shapes
   - Add run-length encoding for constant-value sequences
   - Use delta encoding for smooth transitions
   - Create parameter-based waveform regeneration

3. **Update Sequence Generation**
   - Generate multiple `.seq` entries for scan variables
   - Each entry uses the user-specified `repeat_count`
   - Handle arming sequence (laser on for full duration)

4. **Memory Management**
   - Track actual memory usage of compressed waveforms
   - Split sequences when they exceed 4M words
   - Optimize chunk boundaries for maximum efficiency

#### Key Insight

**Memory optimization and experiment repetition are now completely separate concerns**:
- **Memory optimization** → Waveform compression, chunking, pattern recognition
- **Experiment repetition** → Sequence file entries with user-specified repeat counts

This gives us much more flexibility and better memory efficiency while maintaining the user's ability to specify exactly how many times each sequence should repeat for statistical purposes.

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure virtual environment is activated
2. **Memory Constraints**: Check sequence duration vs. available memory
3. **File Paths**: Use relative paths for portability
4. **Unit Parsing**: Ensure units are correctly specified

### Debug Mode

Enable verbose logging to debug parsing issues:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Contributing

When adding new features:

1. Write tests first (TDD approach)
2. Follow the existing architecture patterns
3. Update this documentation
4. Ensure all tests pass
5. Test the full pipeline

## References

- [AWG520 User Manual](https://www.tek.com/en/products/arbitrary-waveform-generators/awg5000-series)
- [SCPI Command Reference](https://www.tek.com/en/products/arbitrary-waveform-generators/awg5000-series/awg520)
- [Qubit Experiment Design](https://en.wikipedia.org/wiki/Quantum_computing)
