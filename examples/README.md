# Examples Directory

This directory contains example scripts and demonstrations of the PittQLabSys framework.

## Contents

### `simple_experiment_demo.py`
A comprehensive demonstration script that shows how to:
- Create and run experiments using the role-based system
- Use mock devices for testing without real hardware
- Manage experiment configurations
- Handle data output and logging
- Work with different lab configurations

### `results/`
Directory containing all outputs from running the example scripts:
- Configuration files (JSON)
- Experiment logs
- Example data files (.npy)
- Metadata files

## Running the Examples

### Prerequisites
Make sure you have the required dependencies installed:
```bash
pip install numpy scipy pandas pyqt5 pyqtgraph
```

### Running the Experiment Demo
```bash
cd examples
python simple_experiment_demo.py
```

This will:
1. Set up mock devices (microwave generator, DAQ, scanner)
2. Create an experiment configuration
3. Run a demonstration ODMR experiment
4. Save all outputs to `results/` directory

## What You'll Learn

### 1. Role-Based Experiment System
- How experiments specify required device roles instead of concrete hardware
- How different labs can use the same experiment with different hardware
- How device selection is handled through configuration

### 2. Configuration Management
- Creating experiment-specific configurations
- Lab-specific hardware configurations
- Loading and saving configuration files
- Merging configurations from different sources

### 3. Mock Device System
- How to create mock devices for testing
- How mock devices simulate real hardware behavior
- How to register mock devices with the role system

### 4. Data Handling
- Expected data formats for different experiment types
- How to save and load experiment data
- Metadata management for experiments

## Example Outputs

After running `experiment_demo.py`, you'll find these files in `results/`:

### Configuration Files
- `experiment_config.json` - The experiment configuration used
- `pitt_lab_config.json` - Pitt Lab hardware configuration
- `mit_lab_config.json` - MIT Lab hardware configuration

### Log Files
- `experiment_logs.json` - Detailed logs from device operations

### Data Files
- `odmr_spectrum.npy` - Example ODMR spectrum data
- `scan_image.npy` - Example scan image data
- `time_trace.npy` - Example time trace data
- `experiment_metadata.json` - Metadata about the experiment

## Using These Examples

1. **Study the code**: Look at how the mock devices are implemented
2. **Examine configurations**: Use the JSON files as templates for your own experiments
3. **Modify and test**: Change parameters and see how they affect the experiment
4. **Adapt to your hardware**: Replace mock devices with real hardware implementations

## Next Steps

After understanding these examples:
1. Create your own experiment configurations
2. Implement real device drivers
3. Build custom experiments using the role-based system
4. Set up lab-specific configurations for your research group

## Troubleshooting

If you encounter issues:
1. Make sure all dependencies are installed
2. Check that the `src/` directory is in your Python path
3. Verify that the mock devices are properly registered
4. Look at the error messages in the console output

For more help, see the main documentation in the `docs/` directory. 