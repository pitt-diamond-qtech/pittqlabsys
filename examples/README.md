# Scan Examples

This directory contains example Python scripts for running different types of scans with the PittQLabSys system. These examples can work with either real hardware or mock hardware, making them perfect for testing, development, and learning.

## Overview

The examples demonstrate three main types of scans commonly used in quantum sensing and microscopy:

1. **Galvo Scan** (`galvo_scan_example.py`) - 2D scanning using galvo mirrors
2. **Confocal Scan** (`confocal_scan_example.py`) - Confocal microscopy using nanodrive stage
3. **ODMR Scan** (`odmr_scan_example.py`) - Optically Detected Magnetic Resonance

## Features

- **Hardware Flexibility**: Run with real hardware or mock hardware
- **Command Line Interface**: Easy-to-use command line arguments
- **Data Saving**: Automatic data saving with timestamps
- **Plotting**: Built-in visualization of results
- **Error Handling**: Robust error handling and fallback options
- **Mock Devices**: Realistic simulation of hardware behavior
- **Cross-Platform**: Works on Windows (real hardware) and other platforms (mock hardware)

## Prerequisites

1. **Python Environment**: Make sure you have the virtual environment activated:
   ```bash
   source venv/bin/activate
   ```

2. **Dependencies**: The examples require the following packages:
   - `numpy` - For numerical operations
   - `matplotlib` - For plotting (optional)
   - `pint` - For unit handling
   - `pyqtgraph` - For real-time plotting (optional)

3. **Project Structure**: Make sure you're running from the project root directory.

## Usage

### Basic Usage

All examples follow the same pattern:

```bash
# Run with mock hardware (default)
python examples/galvo_scan_example.py

# Run with real hardware
python examples/galvo_scan_example.py --real-hardware

# Get help
python examples/galvo_scan_example.py --help
```

### Common Options

All examples support these common options:

- `--real-hardware`: Use real hardware instead of mock hardware
- `--no-save`: Don't save scan data to files
- `--no-plot`: Don't show plots (useful for headless operation)

### Galvo Scan Example

```bash
# Basic galvo scan with mock hardware (works on all platforms)
python examples/galvo_scan_example.py

# Galvo scan with real hardware (Windows only)
python examples/galvo_scan_example.py --real-hardware

# Galvo scan without saving data
python examples/galvo_scan_example.py --no-save
```

**What it does:**
- Creates a 2D image by sweeping galvo voltages
- Counts photons at each position
- Uses mock devices on non-Windows platforms
- Saves data as `galvo_scan_YYYYMMDD_HHMMSS.npz`
- **Status**: ✅ Working with mock hardware

### Confocal Scan Example

```bash
# Fast confocal scan (default)
python examples/confocal_scan_example.py

# Slow confocal scan
python examples/confocal_scan_example.py --scan-type slow

# Confocal scan with real hardware
python examples/confocal_scan_example.py --real-hardware
```

**What it does:**
- Uses nanodrive to move the sample stage
- Uses ADwin device to acquire count data
- Supports both fast and slow scanning modes
- Saves data as `confocal_scan_fast_YYYYMMDD_HHMMSS.npz` or `confocal_scan_slow_YYYYMMDD_HHMMSS.npz`

### ODMR Scan Example

```bash
# Single ODMR sweep
python examples/odmr_scan_example.py

# Continuous ODMR monitoring
python examples/odmr_scan_example.py --scan-mode continuous

# 2D ODMR scan
python examples/odmr_scan_example.py --scan-mode 2d_scan

# ODMR with real hardware
python examples/odmr_scan_example.py --real-hardware
```

**What it does:**
- Sweeps microwave frequency while monitoring fluorescence
- Identifies NV center transitions (ms=0 ↔ ms=±1)
- Supports single, continuous, averaged, and 2D scan modes
- Generates realistic mock data with NV resonances at 2.87, 2.82, and 2.92 GHz
- Saves data as `odmr_scan_single_YYYYMMDD_HHMMSS.npz` (or other modes)

## Mock Hardware

When using mock hardware, the examples simulate realistic device behavior:

### Mock DAQ (Galvo Scan)
- Simulates analog outputs and inputs
- Generates photon counts based on position
- Creates a bright spot at (0.5, 0.5) to simulate an NV center

### Mock NanoDrive (Confocal/ODMR)
- Tracks position in 3D space
- Simulates movement and waveform execution
- Provides realistic position feedback

### Mock ADwin (Confocal/ODMR)
- Simulates data acquisition arrays
- Generates realistic count data
- Supports process loading and execution

### Mock Microwave Generator (ODMR)
- Simulates frequency and power control
- Generates realistic ODMR spectra with NV resonances
- Supports modulation and output control

## Output Files

All examples create a `scan_data/` directory with:

1. **Data Files** (`.npz` format):
   - Compressed NumPy arrays containing scan data
   - Include settings, timing, and hardware information
   - Timestamped filenames for easy organization

2. **Plot Files** (`.png` format):
   - High-resolution plots of scan results
   - Include colorbars and proper labels
   - Useful for presentations and documentation

## Data Structure

The saved `.npz` files contain:

```python
# Load saved data
data = np.load('scan_data/galvo_scan_20241201_143022.npz')

# Access data
scan_data = data['data']           # Raw scan data
settings = data['settings']        # Scan parameters
scan_time = data['scan_time']      # Duration
hardware_type = data['hardware_type']  # 'real' or 'mock'
```

## Error Handling

The examples include robust error handling:

- **Hardware Failures**: Automatically fall back to mock hardware if real hardware fails
- **Import Errors**: Graceful handling of missing dependencies
- **User Interruption**: Clean shutdown on Ctrl+C
- **Data Saving**: Continues even if plotting fails

## Development

### Adding New Examples

To create a new scan example:

1. Copy an existing example as a template
2. Modify the mock devices to match your hardware requirements
3. Update the scan parameters and settings
4. Add appropriate plotting functions
5. Test with both mock and real hardware

### Customizing Mock Devices

You can modify the mock devices to simulate different scenarios:

```python
class MockDAQ:
    def read_counter(self, channel):
        # Customize the photon count simulation
        x, y = self.analog_outputs['ao0'], self.analog_outputs['ao1']
        
        # Add multiple NV centers
        nv_positions = [(0.5, 0.5), (0.2, 0.8), (0.8, 0.2)]
        total_counts = 0
        
        for nv_x, nv_y in nv_positions:
            distance = np.sqrt((x - nv_x)**2 + (y - nv_y)**2)
            if distance < 0.1:
                total_counts += np.random.poisson(1000)
            else:
                total_counts += np.random.poisson(50)
                
        return total_counts
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Make sure you're in the project root and the virtual environment is activated
2. **Hardware Not Found**: The examples will automatically fall back to mock hardware
3. **Plotting Issues**: Use `--no-plot` if matplotlib is not available
4. **Permission Errors**: Check write permissions for the `scan_data/` directory

### Debug Mode

For debugging, you can add print statements to the mock devices or modify the scan parameters:

```python
# In the example files, modify the scan_settings dictionary
scan_settings = {
    'num_points': {
        'x': 16,  # Reduce for faster testing
        'y': 16
    },
    'time_per_pt': 0.001,  # Reduce for faster testing
}
```

## Contributing

When adding new examples or modifying existing ones:

1. Follow the existing code structure and style
2. Include comprehensive docstrings
3. Add appropriate error handling
4. Test with both mock and real hardware
5. Update this README with new features

## License

These examples are part of the PittQLabSys project and are subject to the same license terms. 