# Mock Data Generation for GUI Testing

This directory contains scripts for generating mock experimental data to test the GUI functionality without requiring real hardware.

## Files

- `test_gui_with_mock_data.py` - Command-line script to test mock data generation and dataset storage
- `test_dataset_gui.py` - Simple GUI window to test the "send to dataset" functionality
- `results/` - Directory where generated data files are saved

## Usage

### 1. Command Line Test

```bash
cd examples
source ../venv/bin/activate
python test_gui_with_mock_data.py
```

This will:
- Create mock experiments with realistic data
- Test the dataset storage functionality
- Save data files to `results/` directory
- Print detailed information about the generated data

### 2. GUI Test Window

```bash
cd examples
source ../venv/bin/activate
python test_dataset_gui.py
```

This will open a simple GUI window where you can:
- Select experiments from the left panel
- Click "Send to Datasets" button
- See experiments appear in the right panel
- Test the dataset functionality interactively

## Generated Data

The scripts generate realistic mock data for:

- **ODMR Sweep Continuous**: Phase continuous microwave sweep with Lorentzian dips
- **ODMR Stepped**: Stepped frequency control with multiple resonances
- **Confocal Scan**: 2D confocal images with bright spots (NV centers)

## Data Files

Generated data is saved as pickle files in the `results/` directory:
- `ODMR_Sweep_Continuous_YYYYMMDD-HH_MM_SS_data.pkl`
- `ODMR_Stepped_YYYYMMDD-HH_MM_SS_data.pkl`
- `Confocal_Scan_YYYYMMDD-HH_MM_SS_data.pkl`

## Integration with Main GUI

You can use these mock experiments in the main GUI by:
1. Loading experiments normally through the GUI
2. Running them (they'll generate mock data instantly)
3. Testing the "send to dataset" button functionality

## Requirements

- Virtual environment must be activated (`source ../venv/bin/activate`)
- All project dependencies must be installed
- PyQt5 for GUI testing

## Troubleshooting

- If you get import errors, make sure you're in the `examples` directory
- If the GUI doesn't open, check that PyQt5 is installed
- If data isn't saved, check that the `results/` directory exists and is writable
