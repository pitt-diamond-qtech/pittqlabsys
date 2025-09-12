# Experiment Development Guide

This guide explains how to create new experiments for AQuISS.

> **📚 Documentation Index**: For a complete overview of all documentation, see [README.md](README.md)

## Related Guides

- **[Development Guide](DEVELOPMENT_GUIDE.md)** - General development practices and standards
- **[Device Development Guide](DEVICE_DEVELOPMENT.md)** - Creating hardware device drivers
- **[Recent Updates](RECENT_UPDATES.md)** - Latest bug fixes and new features

## Overview

Experiments in AQuISS are modular classes that define scientific procedures. They inherit from the base `Experiment` class and provide a standardized interface for data acquisition, processing, and visualization.

**Recent Updates**: The base `Experiment` class has been enhanced with robust path management capabilities. See [Recent Updates](RECENT_UPDATES.md) for details on the latest improvements.

## Experiment Class Structure

### Required Components

1. **Class Definition**: Inherit from `Experiment`
2. **Default Settings**: Define `_DEFAULT_SETTINGS`
3. **Device Requirements**: Define `_DEVICES`
4. **Sub-experiments**: Define `_EXPERIMENTS` (if needed)
5. **Core Methods**: Implement `_function()`, `_plot()`, `_update()`

### Example Template

```python
from src.core import Experiment, Parameter
from typing import List, Dict, Any, Optional
import numpy as np
import pyqtgraph as pg

class MyExperiment(Experiment):
    """
    Description of what this experiment does.
    
    This experiment performs [specific scientific procedure] using [devices]
    to measure [quantities] for [purpose].
    """
    
    _DEFAULT_SETTINGS = [
        Parameter('duration', 10.0, float, 'Experiment duration in seconds'),
        Parameter('samples', 1000, int, 'Number of data points'),
        Parameter('frequency', 1e6, float, 'Sampling frequency in Hz'),
        Parameter('advanced_settings', [
            Parameter('averaging', 1, int, 'Number of averages'),
            Parameter('trigger_mode', 'internal', ['internal', 'external'], 'Trigger source')
        ])
    ]
    
    _DEVICES = {
        'daq': 'ni_daq',      # Device name string (maps to config.json)
        'microwave': 'sg384',  # Device name string (maps to config.json)
        'positioner': 'nanodrive'  # Device name string (maps to config.json)
    }
    
    _EXPERIMENTS = {}  # Sub-experiments if needed
    
    def __init__(self, devices: Dict[str, Any], experiments: Optional[Dict[str, Any]] = None,
                 name: Optional[str] = None, settings: Optional[Dict[str, Any]] = None,
                 log_function=None, data_path: Optional[str] = None):
        """
        Initialize the experiment.
        
        Args:
            devices: Dictionary of device instances
            experiments: Dictionary of sub-experiment instances
            name: Optional experiment name
            settings: Optional initial settings
            log_function: Optional logging function
            data_path: Optional data storage path
        """
        super().__init__(name, settings, devices, experiments, log_function, data_path)
        
        # Store device references for convenience
        self.daq = self.devices['daq']['instance']
        self.microwave = self.devices['microwave']['instance']
        self.positioner = self.devices['positioner']['instance']
        
        # Initialize experiment-specific variables
        self.data = None
        self.timestamps = None
        
    def setup(self):
        """
        Setup experiment before execution.
        
        Called before _function() to prepare devices and parameters.
        """
        self.log("Setting up experiment...")
        
        # Configure devices
        self.daq.update({
            'sample_rate': self.settings['frequency'],
            'samples': self.settings['samples']
        })
        
        self.microwave.update({
            'frequency': 2.87e9,  # NV center frequency
            'power': -10.0
        })
        
        # Initialize data structures
        self.data = np.zeros(self.settings['samples'])
        self.timestamps = np.linspace(0, self.settings['duration'], 
                                    self.settings['samples'])
        
    def cleanup(self):
        """
        Cleanup after experiment execution.
        
        Called after _function() to reset devices and free resources.
        """
        self.log("Cleaning up experiment...")
        
        # Reset devices to safe state
        self.microwave.update({'output_enabled': False})
        self.daq.stop_acquisition()
        
    def _function(self):
        """
        Main experiment execution logic.
        
        This method contains the core experimental procedure.
        """
        self.log("Starting experiment execution...")
        
        try:
            # Setup phase
            self.setup()
            
            # Get output directories using enhanced path management
            output_dir = self.get_output_dir()
            raw_data_dir = self.get_output_dir("raw_data")
            config_path = self.get_config_path()
            
            self.log(f"Output directory: {output_dir}")
            self.log(f"Raw data directory: {raw_data_dir}")
            
            # Main experiment loop
            for i in range(self.settings['advanced_settings']['averaging']):
                self.log(f"Running iteration {i+1}/{self.settings['advanced_settings']['averaging']}")
                
                # Start data acquisition
                self.daq.start_acquisition()
                
                # Trigger microwave
                self.microwave.update({'output_enabled': True})
                
                # Wait for acquisition to complete
                while not self.daq.acquisition_complete():
                    self.updateProgress.emit(int(50 * (i + 0.5) / self.settings['advanced_settings']['averaging']))
                    self.msleep(10)  # Small delay to prevent GUI freezing
                
                # Read data
                raw_data = self.daq.read_data()
                
                # Save raw data to configured directory
                raw_data_file = raw_data_dir / f"iteration_{i+1}.npy"
                np.save(raw_data_file, raw_data)
                
                # Process data
                if i == 0:
                    self.data = raw_data
                else:
                    self.data += raw_data
                
                # Stop microwave
                self.microwave.update({'output_enabled': False})
                
                # Check for stop signal
                if self.is_stopped():
                    self.log("Experiment stopped by user")
                    break
            
            # Finalize data
            if self.settings['advanced_settings']['averaging'] > 1:
                self.data /= self.settings['advanced_settings']['averaging']
            
            # Save final results to configured output directory
            results_file = output_dir / "final_results.npy"
            np.save(results_file, self.data)
            
            # Cleanup
            self.cleanup()
            
            self.log("Experiment completed successfully")
            
        except Exception as e:
            self.log(f"Experiment failed: {e}")
            self.cleanup()
            raise
    
    def _plot(self, axes_list: List[pg.PlotItem]):
        """
        Create initial plots.
        
        Args:
            axes_list: List of PyQtGraph plot items
        """
        if self.data is None:
            return
        
        # Clear existing plots
        for ax in axes_list:
            ax.clear()
        
        # Create plots
        if len(axes_list) >= 1:
            # Time series plot
            ax1 = axes_list[0]
            ax1.plot(self.timestamps, self.data, pen='b', symbol='o')
            ax1.setLabel('left', 'Signal', units='V')
            ax1.setLabel('bottom', 'Time', units='s')
            ax1.setTitle('Time Series Data')
            ax1.showGrid(x=True, y=True)
        
        if len(axes_list) >= 2:
            # FFT plot
            ax2 = axes_list[1]
            fft_data = np.fft.fft(self.data)
            freqs = np.fft.fftfreq(len(self.data), 1/self.settings['frequency'])
            ax2.plot(freqs[:len(freqs)//2], np.abs(fft_data[:len(fft_data)//2]), pen='r')
            ax2.setLabel('left', 'Magnitude')
            ax2.setLabel('bottom', 'Frequency', units='Hz')
            ax2.setTitle('Frequency Spectrum')
            ax2.showGrid(x=True, y=True)
    
    def _update(self, axes_list: List[pg.PlotItem]):
        """
        Update existing plots with new data.
        
        Args:
            axes_list: List of PyQtGraph plot items
        """
        # Update plots with new data
        self._plot(axes_list)
    
    def get_axes_layout(self, figure_list: List[str]) -> List[List[str]]:
        """
        Define the layout of plots for this experiment.
        
        Args:
            figure_list: List of figure names
            
        Returns:
            List of lists defining plot layout
        """
        return [
            ['Time Series'],  # Single plot in first figure
            ['Frequency Spectrum']  # Single plot in second figure
        ]
```

## Parameter Types for Experiments

### Basic Parameters

```python
Parameter('name', default_value, type, description)
```

### Parameters with Units

```python
Parameter('frequency', 1e9, float, 'Frequency', units='Hz')
```

### Parameters with Choices

```python
Parameter('mode', 'continuous', ['continuous', 'pulsed'], 'Operation mode')
```

### Nested Parameters

```python
Parameter('scan_settings', [
    Parameter('start', 0.0, float, 'Start position'),
    Parameter('stop', 100.0, float, 'Stop position'),
    Parameter('steps', 100, int, 'Number of steps')
])
```

## Device Integration

### Device Requirements

Define required devices in `_DEVICES` using device name strings:

```python
_DEVICES = {
    'daq': 'ni_daq',      # Device name string (maps to config.json)
    'microwave': 'sg384',  # Device name string (maps to config.json)
    'positioner': 'nanodrive'  # Device name string (maps to config.json)
}
```

**Important**: Use device name strings (not device classes) for maximum flexibility and cross-lab compatibility.

### How Device Mapping Works

The system automatically maps experiment device names to actual device instances:

1. **Experiment specifies**: `'microwave': 'sg384'`
2. **Export tool maps**: `'sg384'` → actual SG384Generator instance
3. **Device available**: Experiment gets the real device instance
4. **Device missing**: Clear error message about what's needed

This approach allows:
- **Cross-lab compatibility**: Same experiment works with different hardware
- **Easy maintenance**: Change device types in config, not experiment code
- **Clear dependencies**: Experiments clearly state what devices they need

For more details on device development, see [Device Development Guide](DEVICE_DEVELOPMENT.md).

### Device Access

Access devices in the constructor:

```python
def __init__(self, devices, ...):
    super().__init__(...)
    
    # Store device references
    self.daq = self.devices['daq']['instance']
    self.microwave = self.devices['microwave']['instance']
```

### Device Configuration

Configure devices in setup:

```python
def setup(self):
    # Configure DAQ
    self.daq.update({
        'sample_rate': self.settings['frequency'],
        'samples': self.settings['samples'],
        'trigger_source': self.settings['advanced_settings']['trigger_mode']
    })
    
    # Configure microwave
    self.microwave.update({
        'frequency': 2.87e9,
        'power': -10.0,
        'output_enabled': False
    })
```

## Path Management

The base `Experiment` class provides robust path management with sensible defaults:

### Automatic Path Management

```python
def _function(self):
    """Main experiment logic with automatic path management."""
    
    # Get configured output directory for this experiment
    output_dir = self.get_output_dir()  # Uses configured data folder + experiment name
    
    # Get output directory with subfolder
    data_dir = self.get_output_dir("raw_data")  # data_folder/experiment_name/raw_data
    
    # Get config file path (tries experiment dir first, then project root)
    config_path = self.get_config_path("my_config.json")
    
    # Use paths in your experiment
    self.save_data_to_file(output_dir / "results.csv")
```

### Key Features

- **Automatic**: All experiments get configurable paths by default
- **Safe**: Handles special characters, empty names, and filesystem issues
- **Consistent**: Same path structure across all experiments
- **Flexible**: Can still customize per experiment if needed
- **Future-proof**: New experiments automatically get proper path handling

### Path Normalization

- Special characters (`/`, `\`, `*`, `?`, etc.) are replaced with underscores
- Empty experiment names fall back to class name
- All paths are created automatically if they don't exist
- Cross-platform compatible (handles Windows/macOS/Linux differences)

### Customization Examples

```python
class MyCustomExperiment(Experiment):
    def get_output_dir(self, subfolder=None):
        """Override to add custom logic."""
        # Call parent method for basic functionality
        base_dir = super().get_output_dir(subfolder)
        
        # Add custom logic
        if self.settings.get('use_timestamp', False):
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            return base_dir / f"run_{timestamp}"
        
        return base_dir
    
    def get_special_data_path(self):
        """Custom method for experiment-specific needs."""
        # Use base method as foundation
        base_dir = self.get_output_dir()
        
        # Add experiment-specific logic
        return base_dir / "special_data" / f"version_{self.settings.get('version', '1.0')}"
```

## Data Management

### Data Storage

Store data in experiment attributes:

```python
def _function(self):
    # Initialize data structures
    self.data = np.zeros(self.settings['samples'])
    self.timestamps = np.linspace(0, self.settings['duration'], 
                                self.settings['samples'])
    
    # Collect data
    for i in range(self.settings['samples']):
        self.data[i] = self.daq.read_single_sample()
```

### Data Processing

Process data during or after collection:

```python
def process_data(self):
    """Process raw data."""
    # Apply filtering
    from scipy import signal
    self.filtered_data = signal.filtfilt(b, a, self.data)
    
    # Calculate statistics
    self.mean = np.mean(self.data)
    self.std = np.std(self.data)
```

### Data Export

Use built-in save methods:

```python
def save_results(self):
    """Save experiment results."""
    # Save raw data
    self.save_data()
    
    # Save processed data
    processed_data = {
        'filtered_data': self.filtered_data,
        'statistics': {
            'mean': self.mean,
            'std': self.std
        }
    }
    self.save_data(data=processed_data, data_tag='processed')
```

## Plotting with PyQtGraph

### Basic Plotting

```python
def _plot(self, axes_list):
    if len(axes_list) >= 1:
        ax = axes_list[0]
        ax.plot(self.timestamps, self.data, pen='b', symbol='o')
        ax.setLabel('left', 'Signal', units='V')
        ax.setLabel('bottom', 'Time', units='s')
        ax.setTitle('Experiment Data')
```

### Real-time Updates

```python
def _update(self, axes_list):
    # Update existing plots
    if len(axes_list) >= 1:
        ax = axes_list[0]
        ax.clear()
        ax.plot(self.timestamps, self.data, pen='b')
```

### Multiple Plots

```python
def get_axes_layout(self, figure_list):
    return [
        ['Time Series', 'Spectrum'],  # Two plots in first figure
        ['Statistics']  # One plot in second figure
    ]
```

## Progress Reporting

### Progress Updates

```python
def _function(self):
    total_steps = self.settings['samples']
    
    for i in range(total_steps):
        # Update progress
        progress = int(100 * i / total_steps)
        self.updateProgress.emit(progress)
        
        # Check for stop signal
        if self.is_stopped():
            break
```

### Logging

```python
def _function(self):
    self.log("Starting experiment...")
    
    try:
        # Experiment logic
        self.log("Experiment completed successfully")
    except Exception as e:
        self.log(f"Experiment failed: {e}")
        raise
```

## Error Handling

### Exception Handling

```python
def _function(self):
    try:
        # Setup
        self.setup()
        
        # Main experiment
        self.run_experiment()
        
        # Cleanup
        self.cleanup()
        
    except Exception as e:
        self.log(f"Experiment error: {e}")
        self.cleanup()  # Always cleanup
        raise
```

### Device Error Handling

```python
def setup(self):
    # Check device connections
    if not self.daq.is_connected:
        raise RuntimeError("DAQ not connected")
    
    if not self.microwave.is_connected:
        raise RuntimeError("Microwave generator not connected")
```

## Testing Your Experiment

Create a test file in the `tests/` directory:

```python
import pytest
import numpy as np
from unittest.mock import Mock
from src.Model.experiments.my_experiment import MyExperiment

class TestMyExperiment:
    def setup_method(self):
        # Create mock devices
        self.mock_daq = Mock()
        self.mock_microwave = Mock()
        self.mock_positioner = Mock()
        
        self.devices = {
            'daq': {'instance': self.mock_daq},
            'microwave': {'instance': self.mock_microwave},
            'positioner': {'instance': self.mock_positioner}
        }
        
        self.experiment = MyExperiment(self.devices)
    
    def test_initialization(self):
        assert self.experiment.name == "MyExperiment"
        assert self.experiment.settings['duration'] == 10.0
    
    def test_setup(self):
        self.experiment.setup()
        
        # Verify device configuration
        self.mock_daq.update.assert_called()
        self.mock_microwave.update.assert_called()
    
    def test_function(self):
        # Mock data
        self.mock_daq.read_data.return_value = np.random.random(100)
        
        # Run experiment
        self.experiment._function()
        
        # Verify data collection
        assert self.experiment.data is not None
        assert len(self.experiment.data) == 100
```

## Design Philosophy: Foundation + Flexibility

The enhanced base experiment class follows a **foundation + flexibility** approach:

**Base Class Provides:**
- **Sensible defaults** for common use cases
- **Robust path handling** (special characters, empty names, etc.)
- **Configurable paths** that respect the system configuration
- **Consistent behavior** across all experiments

**Individual Experiments Can:**
- **Override** the path methods if they need custom logic
- **Extend** the base functionality for specific needs
- **Use their own** path handling entirely if required
- **Mix and match** - use base methods for some paths, custom for others

**Benefits:**
- **Consistency**: Most experiments get good defaults
- **Flexibility**: Can customize when needed
- **Maintainability**: Common logic centralized
- **Gradual adoption**: No forced changes
- **Future-proof**: Easy to enhance base class

## Migration Strategy

### For New Experiments
- **Get benefits automatically** - just inherit from base class
- **Use path methods** - `get_output_dir()` and `get_config_path()`
- **Customize as needed** - override methods when required

### For Existing Experiments
- **No changes required** - continue working as before
- **Gradual migration** - can adopt base class methods over time
- **Backward compatible** - existing path handling still works

### Migration Example
```python
# Before: Manual path management
class MyExperiment(Experiment):
    def _function(self):
        output_dir = Path("my_experiment_output")
        output_dir.mkdir(exist_ok=True)
        # ... use output_dir

# After: Using enhanced base class
class MyExperiment(Experiment):
    def _function(self):
        output_dir = self.get_output_dir("my_experiment_output")  # Automatic!
        # ... use output_dir
```

## Best Practices

### 1. Modular Design

Break complex experiments into smaller methods:

```python
def _function(self):
    self.setup()
    self.run_acquisition()
    self.process_data()
    self.cleanup()
```

### 2. Resource Management

Always clean up resources:

```python
def cleanup(self):
    # Stop devices
    self.daq.stop_acquisition()
    self.microwave.update({'output_enabled': False})
    
    # Reset to safe state
    self.positioner.move_to_safe_position()
```

### 3. Error Recovery

Implement robust error handling:

```python
def _function(self):
    try:
        self.setup()
        self.run_experiment()
    except DeviceError as e:
        self.log(f"Device error: {e}")
        self.reconnect_devices()
        self._function()  # Retry
    except Exception as e:
        self.log(f"Unexpected error: {e}")
        raise
    finally:
        self.cleanup()
```

### 4. Documentation

Document your experiment thoroughly:

```python
class MyExperiment(Experiment):
    """
    ODMR Experiment for NV Center Characterization.
    
    This experiment performs optically detected magnetic resonance (ODMR)
    measurements on nitrogen-vacancy centers in diamond. It sweeps microwave
    frequency while monitoring fluorescence intensity to identify the NV
    center's ground state transitions.
    
    Parameters:
        frequency_range: [start, stop] frequency range in Hz
        power: Microwave power in dBm
        integration_time: Integration time per frequency point
        
    Returns:
        odmr_spectrum: Fluorescence vs frequency data
        fit_parameters: Fitted parameters for NV center transitions
    """
```

## Common Experiment Patterns

### 1. Sweep Experiments

```python
def run_sweep(self):
    """Run a parameter sweep."""
    start = self.settings['sweep']['start']
    stop = self.settings['sweep']['stop']
    steps = self.settings['sweep']['steps']
    
    self.sweep_data = np.zeros(steps)
    frequencies = np.linspace(start, stop, steps)
    
    for i, freq in enumerate(frequencies):
        self.microwave.update({'frequency': freq})
        self.sweep_data[i] = self.measure_signal()
        
        # Update progress
        self.updateProgress.emit(int(100 * i / steps))
```

### 2. Time Series Experiments

```python
def run_time_series(self):
    """Run a time series measurement."""
    duration = self.settings['duration']
    sample_rate = self.settings['sample_rate']
    samples = int(duration * sample_rate)
    
    self.time_data = np.zeros(samples)
    timestamps = np.linspace(0, duration, samples)
    
    for i in range(samples):
        self.time_data[i] = self.measure_signal()
        
        # Real-time plotting
        if i % 100 == 0:
            self._update(self.axes_list)
```

### 3. Multi-Dimensional Scans

```python
def run_2d_scan(self):
    """Run a 2D parameter scan."""
    x_range = np.linspace(self.settings['x_start'], self.settings['x_stop'], 
                         self.settings['x_steps'])
    y_range = np.linspace(self.settings['y_start'], self.settings['y_stop'], 
                         self.settings['y_steps'])
    
    self.scan_data = np.zeros((len(y_range), len(x_range)))
    
    for i, y in enumerate(y_range):
        self.positioner.update({'y_pos': y})
        
        for j, x in enumerate(x_range):
            self.positioner.update({'x_pos': x})
            self.scan_data[i, j] = self.measure_signal()
            
            # Update progress
            progress = int(100 * (i * len(x_range) + j) / (len(x_range) * len(y_range)))
            self.updateProgress.emit(progress)
```

## Resources

- [Experiment Base Class Documentation](../src/core/experiment.py)
- [Parameter Class Documentation](../src/core/parameter.py)
- [Example Experiment Implementation](../src/Model/experiments/example_experiment.py)
- [PyQtGraph Documentation](https://pyqtgraph.readthedocs.io/)
- [Testing Framework Documentation](../tests/)

## Related Guides

- [Device Development Guide](DEVICE_DEVELOPMENT.md) - How to create new hardware devices
- [Development Guide](DEVELOPMENT_GUIDE.md) - General development practices and standards
- [Configuration Files Guide](CONFIGURATION_FILES.md) - How to configure devices and experiments
- [Recent Updates](RECENT_UPDATES.md) - Latest bug fixes and new features

## Recent Enhancements

The base experiment class has been significantly enhanced with robust path management capabilities. Key improvements include:

- **Automatic path management** with configurable data folders
- **Safe file operations** handling special characters and edge cases
- **Consistent path structure** across all experiments
- **Flexible customization** allowing per-experiment overrides
- **Comprehensive testing** with 26 tests covering all functionality

For detailed information about these enhancements, see [Recent Updates](RECENT_UPDATES.md). 