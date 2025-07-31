#!/usr/bin/env python3
"""
Simple Experiment Creation Demo

This script demonstrates how to create and run experiments using the
role-based experiment system without importing hardware-dependent modules.
All outputs are stored in examples/results/.

Author: Gurudev Dutt <gdutt@pitt.edu>
Created: 2024
License: GPL v2
"""

import sys
import os
import json
import time
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.helper_functions import get_project_root
from src.core.device_roles import device_role_manager, register_device_roles


class MockMicrowaveGenerator:
    """Mock microwave generator for demonstration."""
    
    def __init__(self, name="mock_microwave"):
        self.name = name
        self.frequency = 2.8e9
        self.power = -10.0
        self.output_enabled = False
        self.log = []
    
    def set_frequency(self, frequency):
        self.frequency = frequency
        self.log.append(f"Set frequency to {frequency} Hz")
    
    def set_power(self, power):
        self.power = power
        self.log.append(f"Set power to {power} dBm")
    
    def output_on(self):
        self.output_enabled = True
        self.log.append("Microwave output enabled")
    
    def output_off(self):
        self.output_enabled = False
        self.log.append("Microwave output disabled")
    
    def close(self):
        self.log.append("Microwave generator closed")


class MockDataAcquisition:
    """Mock data acquisition system for demonstration."""
    
    def __init__(self, name="mock_daq"):
        self.name = name
        self.sample_rate = 1000
        self.channels = ['ai0', 'ai1']
        self.log = []
    
    def configure_analog_input(self, channel, voltage_range, sample_rate):
        self.log.append(f"Configured {channel} with range {voltage_range}V, rate {sample_rate}Hz")
    
    def read_analog_input(self, channel, samples):
        # Simulate reading data
        data = np.random.normal(0, 0.1, samples)
        self.log.append(f"Read {samples} samples from {channel}")
        return data
    
    def start_acquisition(self):
        self.log.append("Started data acquisition")
    
    def stop_acquisition(self):
        self.log.append("Stopped data acquisition")
    
    def close(self):
        self.log.append("Data acquisition closed")


class MockScanner:
    """Mock scanner for demonstration."""
    
    def __init__(self, name="mock_scanner"):
        self.name = name
        self.x_position = 0.0
        self.y_position = 0.0
        self.z_position = 0.0
        self.log = []
    
    def move_to(self, x, y, z=None):
        self.x_position = x
        self.y_position = y
        if z is not None:
            self.z_position = z
        self.log.append(f"Moved to position ({x}, {y}, {z})")
    
    def get_position(self):
        return (self.x_position, self.y_position, self.z_position)
    
    def scan_line(self, start, stop, steps):
        positions = []
        for i in range(steps):
            x = start[0] + (stop[0] - start[0]) * i / (steps - 1)
            y = start[1] + (stop[1] - start[1]) * i / (steps - 1)
            positions.append((x, y))
        self.log.append(f"Scanned line from {start} to {stop} with {steps} steps")
        return positions
    
    def close(self):
        self.log.append("Scanner closed")


class SimpleRoleBasedExperiment:
    """Simple role-based experiment for demonstration."""
    
    def __init__(self, name="demo_experiment", device_config=None):
        self.name = name
        self.devices = {}
        self.log = []
        
        # Default device configuration
        if device_config is None:
            device_config = {
                'microwave': 'mock_microwave',
                'daq': 'mock_daq',
                'scanner': 'mock_scanner'
            }
        
        # Create device instances
        self._create_devices(device_config)
    
    def _create_devices(self, device_config):
        """Create device instances based on configuration."""
        device_creators = {
            'mock_microwave': MockMicrowaveGenerator,
            'mock_daq': MockDataAcquisition,
            'mock_scanner': MockScanner
        }
        
        for role, device_type in device_config.items():
            if device_type in device_creators:
                device = device_creators[device_type]()
                self.devices[role] = {
                    'type': device_type,
                    'instance': device
                }
                self.log.append(f"Created {device_type} for role {role}")
    
    def setup(self):
        """Setup the experiment."""
        self.log.append("Setting up experiment...")
        
        # Setup microwave
        if 'microwave' in self.devices:
            microwave = self.devices['microwave']['instance']
            microwave.set_frequency(2.8e9)
            microwave.set_power(-10.0)
            microwave.output_on()
        
        # Setup DAQ
        if 'daq' in self.devices:
            daq = self.devices['daq']['instance']
            daq.configure_analog_input('ai0', 10.0, 1000)
            daq.start_acquisition()
        
        # Setup scanner
        if 'scanner' in self.devices:
            scanner = self.devices['scanner']['instance']
            scanner.move_to(5.0, 5.0, 0.0)
        
        self.log.append("Experiment setup complete")
    
    def run(self):
        """Run the experiment."""
        self.log.append("Running experiment...")
        
        # Simulate experiment execution
        frequencies = np.linspace(2.7e9, 2.9e9, 20)
        data = []
        
        for freq in frequencies:
            # Set microwave frequency
            if 'microwave' in self.devices:
                microwave = self.devices['microwave']['instance']
                microwave.set_frequency(freq)
            
            # Acquire data
            if 'daq' in self.devices:
                daq = self.devices['daq']['instance']
                sample_data = daq.read_analog_input('ai0', 100)
                data.append(np.mean(sample_data))
            
            # Small delay to simulate real experiment
            time.sleep(0.01)
        
        self.log.append(f"Experiment completed, acquired {len(data)} data points")
        return np.array(data)
    
    def cleanup(self):
        """Cleanup the experiment."""
        self.log.append("Cleaning up experiment...")
        
        # Turn off microwave
        if 'microwave' in self.devices:
            microwave = self.devices['microwave']['instance']
            microwave.output_off()
            microwave.close()
        
        # Stop DAQ
        if 'daq' in self.devices:
            daq = self.devices['daq']['instance']
            daq.stop_acquisition()
            daq.close()
        
        # Close scanner
        if 'scanner' in self.devices:
            scanner = self.devices['scanner']['instance']
            scanner.close()
        
        self.log.append("Cleanup complete")


def create_experiment_configuration(results_dir: Path) -> Dict[str, Any]:
    """Create a custom experiment configuration."""
    print("\nCreating experiment configuration...")
    
    config = {
        "experiment_name": "demo_experiment",
        "description": "Demo experiment for examples",
        "device_config": {
            "microwave": "mock_microwave",
            "daq": "mock_daq",
            "scanner": "mock_scanner"
        },
        "settings": {
            "frequency_range": {
                "start": 2.7e9,
                "stop": 2.9e9,
                "steps": 20
            },
            "microwave": {
                "power": -10.0,
                "modulation": False
            },
            "acquisition": {
                "integration_time": 0.1,
                "averages": 2
            }
        },
        "metadata": {
            "created": datetime.now().isoformat(),
            "author": "Demo Script",
            "purpose": "Demonstration of role-based experiment system",
            "notes": "This is a mock experiment for demonstration purposes"
        }
    }
    
    # Save configuration to results directory
    config_file = results_dir / "experiment_config.json"
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"✅ Configuration saved to {config_file}")
    return config


def run_experiment_demo(results_dir: Path):
    """Run a demonstration experiment."""
    print("\n" + "="*60)
    print("RUNNING EXPERIMENT DEMO")
    print("="*60)
    
    # Create experiment configuration
    config = create_experiment_configuration(results_dir)
    
    # Create experiment instance
    print("\nCreating experiment instance...")
    experiment = SimpleRoleBasedExperiment(
        name="demo_experiment",
        device_config=config['device_config']
    )
    
    print(f"✅ Experiment created: {experiment.name}")
    print(f"   Devices: {list(experiment.devices.keys())}")
    
    # Setup experiment
    print("\nSetting up experiment...")
    experiment.setup()
    print("✅ Experiment setup complete")
    
    # Run experiment
    print("\nRunning experiment...")
    start_time = time.time()
    
    try:
        data = experiment.run()
        execution_time = time.time() - start_time
        print(f"✅ Experiment completed in {execution_time:.2f} seconds")
        print(f"   Acquired {len(data)} data points")
        
    except Exception as e:
        print(f"❌ Experiment failed: {e}")
        return False, None
    
    # Cleanup
    print("\nCleaning up...")
    experiment.cleanup()
    print("✅ Cleanup complete")
    
    return True, experiment


def save_experiment_logs(results_dir: Path, experiment):
    """Save experiment logs and device activity."""
    print("\nSaving experiment logs...")
    
    # Collect logs from all devices
    logs = {
        "experiment_info": {
            "name": experiment.name,
            "timestamp": datetime.now().isoformat(),
            "devices": {}
        },
        "experiment_logs": experiment.log,
        "device_logs": {}
    }
    
    # Get logs from each device
    for role, device_info in experiment.devices.items():
        device = device_info['instance']
        if hasattr(device, 'log'):
            logs["device_logs"][role] = device.log
            logs["experiment_info"]["devices"][role] = {
                "type": device_info['type'],
                "name": getattr(device, 'name', 'unknown')
            }
    
    # Save logs
    log_file = results_dir / "experiment_logs.json"
    with open(log_file, 'w') as f:
        json.dump(logs, f, indent=2)
    
    print(f"✅ Logs saved to {log_file}")


def save_experiment_data(results_dir: Path, data):
    """Save experiment data."""
    print("\nSaving experiment data...")
    
    # Save raw data
    data_file = results_dir / "experiment_data.npy"
    np.save(data_file, data)
    print(f"✅ Data saved to {data_file}")
    
    # Save data as CSV for easy viewing
    csv_file = results_dir / "experiment_data.csv"
    frequencies = np.linspace(2.7e9, 2.9e9, len(data))
    data_array = np.column_stack([frequencies, data])
    np.savetxt(csv_file, data_array, delimiter=',', 
               header='Frequency (Hz),Signal (V)', comments='')
    print(f"✅ CSV data saved to {csv_file}")


def create_example_outputs(results_dir: Path):
    """Create example output files to demonstrate data handling."""
    print("\nCreating example output files...")
    
    # Example data files
    data_files = {
        "odmr_spectrum.npy": np.random.normal(0, 1, (20, 100)),  # 20 frequency points, 100 time points
        "scan_image.npy": np.random.poisson(10, (50, 50)),       # 50x50 scan image
        "time_trace.npy": np.random.exponential(1, 1000),        # 1000 point time trace
    }
    
    for filename, data in data_files.items():
        filepath = results_dir / filename
        np.save(filepath, data)
        print(f"   📊 {filename} ({data.shape})")
    
    # Example metadata
    metadata = {
        "experiment_type": "ODMR",
        "date": datetime.now().isoformat(),
        "parameters": {
            "frequency_range": [2.7e9, 2.9e9],
            "integration_time": 0.1,
            "averages": 2
        },
        "data_files": list(data_files.keys()),
        "notes": "Example data files for demonstration"
    }
    
    metadata_file = results_dir / "experiment_metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"   📋 experiment_metadata.json")
    print("✅ Example output files created")


def demonstrate_configuration_management(results_dir: Path):
    """Demonstrate configuration management features."""
    print("\n" + "="*60)
    print("CONFIGURATION MANAGEMENT DEMO")
    print("="*60)
    
    # Create different lab configurations
    labs = {
        "pitt_lab": {
            "description": "University of Pittsburgh Quantum Lab",
            "device_config": {
                "microwave": "sg384",
                "daq": "adwin",
                "scanner": "nanodrive"
            },
            "settings": {
                "default_integration_time": 0.1,
                "default_laser_power": 1.0
            }
        },
        "mit_lab": {
            "description": "MIT Quantum Lab",
            "device_config": {
                "microwave": "windfreak_synth_usbii",
                "daq": "nidaq",
                "scanner": "galvo_scanner"
            },
            "settings": {
                "default_integration_time": 0.05,
                "default_laser_power": 0.5
            }
        }
    }
    
    # Save lab configurations
    for lab_name, config in labs.items():
        config_file = results_dir / f"{lab_name}_config.json"
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"✅ {lab_name} configuration saved")
    
    # Demonstrate configuration loading
    print("\nDemonstrating configuration loading:")
    for lab_name in labs.keys():
        config_file = results_dir / f"{lab_name}_config.json"
        with open(config_file, 'r') as f:
            loaded_config = json.load(f)
        print(f"   📄 {lab_name}: {loaded_config['description']}")


def create_readme(results_dir: Path):
    """Create a README file explaining the example outputs."""
    readme_content = f"""# Simple Experiment Demo Results

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
device_config = {{
    'microwave': 'your_microwave_device',
    'daq': 'your_daq_device',
    'scanner': 'your_scanner_device'
}}

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

Generated on: {datetime.now().isoformat()}
"""
    
    readme_file = results_dir / "README.md"
    with open(readme_file, 'w') as f:
        f.write(readme_content)
    
    print(f"✅ README.md created")


def main():
    """Main demonstration function."""
    print("Simple Experiment Creation and Execution Demo")
    print("=" * 60)
    
    # Setup results directory
    results_dir = Path("results")
    results_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Results will be saved to: {results_dir.absolute()}")
    
    # Run experiment demo
    success, experiment = run_experiment_demo(results_dir)
    
    if success and experiment is not None:
        # Save logs
        save_experiment_logs(results_dir, experiment)
        
        # Save data (we need to run the experiment again to get data)
        print("\nRunning experiment again to capture data...")
        # Extract device types from the experiment devices
        device_config = {role: info['type'] for role, info in experiment.devices.items()}
        experiment2 = SimpleRoleBasedExperiment(
            name="demo_experiment_data",
            device_config=device_config
        )
        experiment2.setup()
        data = experiment2.run()
        experiment2.cleanup()
        
        save_experiment_data(results_dir, data)
        
        # Create example outputs
        create_example_outputs(results_dir)
        
        # Demonstrate configuration management
        demonstrate_configuration_management(results_dir)
        
        # Create README
        create_readme(results_dir)
        
        print("\n" + "="*60)
        print("DEMO COMPLETED SUCCESSFULLY!")
        print("="*60)
        print(f"\nAll outputs saved to: {results_dir.absolute()}")
        print("\nFiles created:")
        for file in results_dir.glob("*"):
            print(f"   📄 {file.name}")
        
        print("\nNext steps:")
        print("1. Examine the configuration files in examples/results/")
        print("2. Look at the experiment logs to see device operations")
        print("3. Use these examples as templates for your own experiments")
        print("4. Modify the configuration files to match your hardware")
    
    else:
        print("\n❌ Demo failed - check the error messages above")


if __name__ == "__main__":
    main() 