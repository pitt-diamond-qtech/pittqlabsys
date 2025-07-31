# Simple Experiment Demo Results

This directory contains the outputs from running the simple experiment demonstration script.

## Files Generated

### Configuration Files
- `experiment_config.json` - The experiment configuration used
- `pitt_lab_config.json` - Pitt Lab hardware configuration
- `mit_lab_config.json` - MIT Lab hardware configuration

### Log Files
- `experiment_logs.json` - Detailed logs from device operations

### Data Files
- `experiment_data.npy` - Raw experiment data (NumPy array)
- `experiment_data.csv` - Experiment data in CSV format
- `odmr_spectrum.npy` - Example ODMR spectrum data (20x100 array)
- `scan_image.npy` - Example scan image data (50x50 array)
- `time_trace.npy` - Example time trace data (1000 points)
- `experiment_metadata.json` - Metadata about the experiment and data files

## How to Use These Examples

1. **Configuration**: Use the JSON config files as templates for your own experiments
2. **Data Format**: The .npy and .csv files show the expected data format
3. **Logging**: The logs demonstrate how device operations are tracked
4. **Metadata**: Use the metadata structure to document your experiments

## Running Your Own Experiments

```python
from examples.simple_experiment_demo import SimpleRoleBasedExperiment

# Create experiment with custom configuration
device_config = {
    'microwave': 'your_microwave_device',
    'daq': 'your_daq_device',
    'scanner': 'your_scanner_device'
}

experiment = SimpleRoleBasedExperiment(
    name="my_experiment",
    device_config=device_config
)

# Run experiment
experiment.setup()
data = experiment.run()
experiment.cleanup()
```

## Key Features Demonstrated

1. **Role-Based Device System**: Experiments specify device roles, not concrete hardware
2. **Configuration Management**: JSON-based configuration files
3. **Mock Devices**: Testing without real hardware
4. **Data Handling**: Saving and loading experiment data
5. **Logging**: Comprehensive logging of device operations

Generated on: 2025-07-31T12:51:26.854803
