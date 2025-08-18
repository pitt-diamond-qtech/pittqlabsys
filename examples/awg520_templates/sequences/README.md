# AWG520 Sequence Templates

This directory contains template sequence files (`.seq`) for common experiment types.

## Available Templates

### 1. **odmr_scan.seq** - ODMR Experiment Sequence
- **Purpose**: Microwave generation and laser control for ODMR experiments
- **Channels**: Uses both CH1 and CH2 for microwave and control signals
- **Markers**: M1 for timing, M2 for laser control
- **Waveforms**: Sine waves for microwave, ramps for scanning

### 2. **confocal_scan.seq** - Confocal Microscopy Sequence
- **Purpose**: Galvanometer scanning and laser control for confocal imaging
- **Channels**: CH1 for X-scan, CH2 for Y-scan and sync
- **Markers**: M1 for scan control, M2 for laser and acquisition timing
- **Waveforms**: Ramps for scanning, square waves for timing

## Sequence File Format

Each line in a sequence file follows this format:
```
[Waveform Name] [Duration] [Channel] [Marker Settings] [Comments]
```

### Fields:
- **Waveform Name**: Reference to a `.wfm` file (without extension)
- **Duration**: Time in microseconds or samples
- **Channel**: Output channel (1 or 2)
- **Marker Settings**: M1 and M2 states (ON/OFF)
- **Comments**: Optional description (after #)

### Example:
```
sine_10MHz.wfm    1000    1    M1:ON M2:OFF    # Microwave output
ramp_100kHz.wfm   2000    2    M1:OFF M2:ON   # Scanning signal
```

## Usage

### 1. **Copy Template for Your Experiment**
```python
import shutil
import os

# Copy template to your experiment directory
template_path = 'examples/awg520_templates/sequences/odmr_scan.seq'
experiment_path = 'my_experiment/scan.seq'

# Ensure target directory exists
os.makedirs(os.path.dirname(experiment_path), exist_ok=True)
shutil.copy(template_path, experiment_path)
```

### 2. **Modify for Your Specific Needs**
- Adjust durations based on your experiment timing
- Modify marker settings for your hardware configuration
- Add or remove waveform references as needed
- Update comments for clarity

### 3. **Load in AWG520 Device**
```python
from src.Controller.awg520 import AWG520Device

device = AWG520Device(settings={
    'seq_file': 'my_experiment/scan.seq',
    # ... other settings
})

# The device will automatically load this sequence file
device.setup()
```

## Creating Custom Sequences

### 1. **Start with a Template**
- Copy the closest template to your needs
- Modify parameters for your experiment
- Test with small changes first

### 2. **Sequence Design Principles**
- **Keep it simple**: Start with basic patterns
- **Test incrementally**: Add complexity step by step
- **Document timing**: Note critical timing requirements
- **Consider markers**: Use markers for synchronization

### 3. **Common Patterns**
- **Microwave generation**: Sine waves with specific frequencies
- **Scanning**: Ramps for linear motion, sine for oscillatory
- **Timing**: Square waves for precise timing control
- **Laser control**: Marker-based power and timing control

## Troubleshooting

### Common Issues:
- **Sequence not loading**: Check file format and syntax
- **Timing problems**: Verify duration values and clock settings
- **Marker issues**: Ensure marker syntax is correct
- **Waveform references**: Verify all referenced `.wfm` files exist

### Validation:
- Check sequence file syntax
- Verify waveform file existence
- Test with simple sequences first
- Use AWG520 device's connection status

## Best Practices

1. **Always backup** your working sequences
2. **Use descriptive names** for custom sequences
3. **Document changes** and their purpose
4. **Test thoroughly** before using in experiments
5. **Keep templates updated** with improvements
