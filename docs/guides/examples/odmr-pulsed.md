# ODMR Pulsed Experiment

## Overview

The ODMR Pulsed Experiment implements pulsed ODMR (Optically Detected Magnetic Resonance) measurements using the AWG520 for sequence generation and ADwin for photon counting. This experiment provides a user-friendly interface for defining complex pulse sequences using our text-based sequence language.

## Features

### 🎯 Core Capabilities
- **Text-based sequence definition** using our sequence language
- **Sequence preview window** showing first 10 scan points
- **Microwave parameter control** (frequency, power, delays)
- **Laser parameter configuration** (power, wavelength)
- **Hardware delay calibration** (MW, AOM, counter delays)
- **AWG520 integration** for waveform and sequence generation
- **Memory optimization** for long sequences

### 🔧 Technical Features
- **Variable scanning** with automatic timing adjustment
- **Hardware calibration** for delay compensation
- **Waveform compression** using repeat field optimization
- **Sequence validation** and error checking
- **Comprehensive logging** and debugging

## Quick Start

### 1. Create Experiment
```python
from src.Model.experiments.odmr_pulsed import ODMRPulsedExperiment

# Create experiment
experiment = ODMRPulsedExperiment()

# Set parameters
experiment.set_microwave_parameters(2.87e9, -10.0, 25.0)  # 2.87 GHz, -10 dBm, 25ns delay
experiment.set_laser_parameters(1.0, 532)                  # 1 mW, 532 nm
experiment.set_delay_parameters(25.0, 50.0, 15.0)         # MW, AOM, Counter delays
```

### 2. Load Sequence
```python
# Load sequence from text file
sequence_file = Path("my_sequence.txt")
experiment.load_sequence_from_file(sequence_file)

# Build scan sequences
experiment.build_scan_sequences()

# Show preview
experiment.show_sequence_preview(num_points=10)
```

### 3. Generate AWG Files
```python
# Generate .wfm and .seq files
experiment.generate_awg_files()

# Files saved to odmr_pulsed_output/ directory
```

## Sequence Language

### Basic Syntax
```
sequence_name: "experiment_name"
sample_rate: 1GHz
repeat_count: 50000

# Define scan variables
variable: pulse_width, start=10ns, stop=1000ns, steps=50
variable: wait_time, start=100ns, stop=10000ns, steps=20

# Define pulses
laser_init on channel 1 at 0ns, square, 1000ns, 1.0
pi_pulse on channel 2 at 1200ns, gaussian, pulse_width, 1.0
wait on channel 1 at 1200ns + pulse_width, square, wait_time, 0.0
```

### Supported Pulse Types
- **square**: Square pulse with specified duration
- **gaussian**: Gaussian pulse with variable width
- **sech**: Sech pulse for adiabatic processes
- **lorentzian**: Lorentzian pulse shape
- **data**: Load pulse shape from CSV file

### Channel Mapping
- **Channel 1**: Laser control (AOM)
- **Channel 2**: Microwave control (IQ modulator)
- **Markers**: Available for additional control signals

## Example Sequences

### Rabi Oscillation
```
sequence_name: "rabi_oscillation"
sample_rate: 1GHz
repeat_count: 50000

variable: pulse_duration, start=10ns, stop=1000ns, steps=50

# Laser initialization
laser_init on channel 1 at 0ns, square, 1000ns, 1.0

# Variable pi pulse
pi_pulse on channel 2 at 1200ns, gaussian, pulse_duration, 1.0

# Laser readout
laser_readout on channel 1 at 1200ns + pulse_duration, square, 3000ns, 1.0

# Counter trigger
counter_trigger on channel 2 at 1200ns + pulse_duration, square, 3000ns, 1.0
```

### Ramsey Interferometry
```
sequence_name: "ramsey_interferometry"
sample_rate: 1GHz
repeat_count: 50000

variable: wait_time, start=100ns, stop=10000ns, steps=100

# Pi/2 pulse 1
pi2_pulse_1 on channel 2 at 1200ns, gaussian, 200ns, 0.7

# Variable wait time
wait on channel 1 at 1400ns, square, wait_time, 0.0

# Pi/2 pulse 2
pi2_pulse_2 on channel 2 at 1400ns + wait_time, gaussian, 200ns, 0.7

# Laser readout
laser_readout on channel 1 at 1600ns + wait_time, square, 3000ns, 1.0
```

### Spin Echo
```
sequence_name: "spin_echo"
sample_rate: 1GHz
repeat_count: 50000

variable: echo_time, start=1000ns, stop=100000ns, steps=50

# Pi/2 pulse
pi2_pulse on channel 2 at 1200ns, gaussian, 200ns, 0.7

# First wait
wait1 on channel 1 at 1400ns, square, echo_time/2, 0.0

# Pi pulse
pi_pulse on channel 2 at 1400ns + echo_time/2, gaussian, 400ns, 1.0

# Second wait
wait2 on channel 1 at 1800ns + echo_time/2, square, echo_time/2, 0.0

# Pi/2 pulse
pi2_pulse2 on channel 2 at 2200ns + echo_time, gaussian, 200ns, 0.7

# Laser readout
laser_readout on channel 1 at 2400ns + echo_time, square, 3000ns, 1.0
```

## Parameter Configuration

### Microwave Parameters
```python
experiment.set_microwave_parameters(
    frequency=2.87e9,    # 2.87 GHz (NV center)
    power=-10.0,         # -10 dBm
    delay=25.0           # 25 ns delay
)
```

### Laser Parameters
```python
experiment.set_laser_parameters(
    power=1.0,           # 1 mW
    wavelength=532        # 532 nm
)
```

### Delay Parameters
```python
experiment.set_delay_parameters(
    mw_delay=25.0,       # Microwave delay
    aom_delay=50.0,      # AOM delay
    counter_delay=15.0    # Counter delay
)
```

## ADwin Integration

### ADwin Parameters
The experiment automatically configures ADwin parameters:
- **Count time**: 300 ns (configurable)
- **Reset time**: 2000 ns (configurable)
- **Repetitions per point**: 50,000 (configurable)

### ADwin Code
The experiment works with your existing ADwin code:
```basic
' Process 2, Priority High, External trigger
' Counter 1 for photon counting
' Parameters passed from Python:
'   Par_3: Count time
'   Par_4: Reset time  
'   Par_5: Repetitions per point
```

## Memory Optimization

### Repeat Field Compression
The experiment uses the AWG520 repeat field for memory optimization:
- **Short dead times**: Stored directly
- **Long dead times**: Compressed using repeat field
- **Compression ratios**: 10:1 to 1000:1 for typical sequences

### Example Compression
```
Original: 10ms dead time = 10,000,000 samples = 20MB
Compressed: 1μs × 10,000 reps = 2KB
Compression: 10,000:1
```

## File Structure

### Input Files
- **Sequence files**: Text files with .txt extension
- **Configuration**: config.json for experiment settings

### Output Files
```
odmr_pulsed_output/
├── scan_point_000.wfm    # Waveform for scan point 0
├── scan_point_001.wfm    # Waveform for scan point 1
├── ...
├── scan_point_999.wfm    # Waveform for scan point 999
└── odmr_pulsed_scan.seq  # Sequence file for AWG520
```

## Testing

### Run Test Suite
```bash
cd examples
python test_odmr_pulsed_experiment.py
```

### Test Coverage
- ✅ Basic functionality
- ✅ Sequence loading
- ✅ Sequence building
- ✅ AWG file generation

## Integration

### AWG520 Setup
1. **Transfer files**: Upload .wfm and .seq files to AWG520
2. **Load sequence**: Load odmr_pulsed_scan.seq
3. **Set parameters**: Configure microwave and laser settings
4. **Start sequence**: Begin experiment execution

### ADwin Setup
1. **Load code**: Upload your ADwin counting code
2. **Set parameters**: Configure count time and repetitions
3. **Enable external trigger**: Wait for AWG520 triggers
4. **Start counting**: Begin photon counting

## Troubleshooting

### Common Issues
1. **Sequence parsing errors**: Check syntax in sequence file
2. **Memory overflow**: Reduce scan points or use compression
3. **Timing issues**: Verify delay parameters
4. **File generation errors**: Check output directory permissions

### Debug Steps
1. **Check logs**: Review experiment logging output
2. **Validate sequence**: Use sequence preview window
3. **Test components**: Run individual test functions
4. **Check hardware**: Verify AWG520 and ADwin connections

## Next Steps

### Immediate
1. **Test basic functionality** with example sequences
2. **Configure hardware parameters** for your setup
3. **Create custom sequences** for your experiments
4. **Generate AWG files** and test on hardware

### Future Enhancements
1. **Real-time control** via external triggers
2. **Advanced compression** algorithms
3. **GUI interface** for sequence editing
4. **Data analysis** and visualization tools

## Support

For questions or issues:
1. **Check logs**: Review experiment logging output
2. **Run tests**: Verify functionality with test suite
3. **Review documentation**: Check sequence language syntax
4. **Contact team**: Reach out for technical support

---

**The ODMR Pulsed Experiment is ready for use!** 🚀

This experiment provides a complete solution for pulsed ODMR measurements, combining the power of our sequence language with the efficiency of AWG520 memory optimization and the reliability of ADwin photon counting.
