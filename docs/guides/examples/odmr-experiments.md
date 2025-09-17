# ODMR Experiments Overview

## Introduction

This document provides an overview of the three focused ODMR (Optically Detected Magnetic Resonance) experiments that properly integrate the SG384 microwave generator with Adwin photon counting for NV center characterization.

## Background

The previous ODMR experiments (`odmr_enhanced`, `odmr_experiment`, `odmr_simple_adwin`, `odmr_sweep_enhanced`) were not actually controlling the SG384 frequency or using the Adwin counters effectively. These new experiments address this by providing three distinct approaches to ODMR measurements, each optimized for different experimental requirements.

## Experiment 1: ODMR Stepped Frequency (`odmr_stepped.py`)

### Purpose
High-precision frequency stepping for detailed resonance characterization.

### How It Works
1. **SG384 Control**: Sets frequency to each point in the scan range using `set_frequency()`
2. **Adwin Integration**: Uses `Averagable_Trial_Counter.TB1` for photon counting
3. **Data Collection**: Collects counts at each frequency point with configurable averaging
4. **Analysis**: Applies smoothing, background subtraction, and Lorentzian fitting

### Key Features
- **Precise Frequency Control**: Each frequency point is set individually
- **Flexible Averaging**: Configurable integration time and number of averages
- **High Resolution**: Suitable for detailed resonance studies
- **Settle Time Control**: Configurable delay after frequency changes

### Use Cases
- **Resonance Characterization**: Detailed study of NV center transitions
- **Power Dependence Studies**: Measure resonance properties at different microwave powers
- **High-Resolution Scans**: Fine frequency resolution around known resonances
- **Research Applications**: When precise frequency control is required

### Settings
```python
frequency_range: [start, stop] frequency range in Hz
microwave: power and settle time
acquisition: integration_time, averages, cycles_per_average
analysis: auto_fit, smoothing, background_subtraction
```

## Experiment 2: ODMR Phase Continuous Sweep (`odmr_sweep_continuous.py`)

### Purpose
Fast frequency sweeps with phase continuity for high-speed data acquisition.

### How It Works
1. **SG384 Sweep Mode**: Configures SG384 for phase continuous frequency sweep
2. **Adwin Synchronization**: Uses `ODMR_Sweep_Counter.TB1` for synchronized counting
3. **Sweep Control**: Triangle, sine, or other sweep waveforms with configurable rate
4. **Bidirectional Data**: Collects forward and reverse sweep data

### Key Features
- **Phase Continuity**: Maintains phase relationship during sweeps
- **High Speed**: Much faster than stepped approach
- **Synchronized Counting**: Adwin counting synchronized with frequency sweep
- **Multiple Waveforms**: Triangle, sine, ramp, square, or noise sweep functions

### Use Cases
- **Fast Surveys**: Quick frequency range exploration
- **Dynamic Measurements**: Time-resolved ODMR studies
- **Large Frequency Ranges**: Efficient coverage of wide frequency bands
- **Production Applications**: When speed is more important than precision

### Settings
```python
frequency_range: [start, stop] frequency range in Hz
microwave: power, sweep_rate, sweep_function
acquisition: integration_time, averages, settle_time
analysis: auto_fit, smoothing, background_subtraction
```

## Experiment 3: ODMR Frequency Modulation (`odmr_fm_modulation.py`)

### Purpose
High-speed fine frequency sweeps around a center frequency using FM modulation.

### How It Works
1. **SG384 FM Mode**: Sets center frequency and enables frequency modulation
2. **Modulation Control**: Configurable modulation depth and rate
3. **Adwin Integration**: Uses `ODMR_Sweep_Counter.TB1` adapted for FM
4. **Lock-in Detection**: Optional phase-sensitive detection for improved SNR

### Key Features
- **Fine Frequency Control**: Small frequency ranges around center frequency
- **High Modulation Rates**: kHz to MHz modulation frequencies
- **Lock-in Detection**: Phase-sensitive detection for noise reduction
- **Fast Acquisition**: Sub-millisecond integration times possible

### Use Cases
- **Fine Resonance Studies**: Detailed study of narrow resonances
- **High-Speed Measurements**: Dynamic processes requiring fast acquisition
- **Noise Reduction**: Lock-in detection for improved signal quality
- **Modulation Spectroscopy**: When frequency modulation is required

### Settings
```python
frequency: center, modulation_depth, modulation_rate
microwave: power, modulation_function
acquisition: integration_time, averages, cycles_per_average
analysis: auto_fit, smoothing, background_subtraction, lock_in_detection
```

## Device Integration

### SG384 Microwave Generator
- **Frequency Control**: `set_frequency()`, `set_power()`, `enable_output()`
- **Sweep Mode**: `set_modulation_type('Freq sweep')`, `set_sweep_deviation()`, `set_sweep_rate()`
- **FM Mode**: `set_modulation_type('FM')`, `set_modulation_depth()`, `set_modulation_rate()`
- **Modulation Functions**: Sine, ramp, triangle, square, noise waveforms

### Adwin Gold Device
- **Averagable_Trial_Counter.TB1**: For stepped frequency experiments
- **ODMR_Sweep_Counter.TB1**: For sweep and FM experiments
- **Parameter Control**: Integration time, number of steps, cycles per average
- **Data Arrays**: Forward/reverse sweep data, voltage ramps, counts

### MCL Nanodrive (Optional)
- **Position Monitoring**: Current position logging
- **No Movement**: Experiments run at fixed positions

### Adwin Helper Functions Integration
The experiments leverage existing helper functions from `src/core/adwin_helpers.py`:

- **`setup_adwin_for_simple_odmr()`**: Used by `ODMRSteppedExperiment` for basic counting
- **`setup_adwin_for_sweep_odmr()`**: Used by `ODMRSweepContinuousExperiment` for sweep counting
- **`setup_adwin_for_fm_odmr()`**: New helper specifically for `ODMRFMModulationExperiment`
- **`read_adwin_sweep_odmr_data()`**: Used by both sweep and FM experiments for data reading
- **`read_adwin_fm_odmr_data()`**: New helper for FM-specific data reading

This integration ensures consistency with existing code and provides a unified interface for Adwin operations.

## Performance Characteristics

| Experiment Type | Speed | Precision | Frequency Range | Best For |
|----------------|-------|-----------|-----------------|----------|
| **Stepped** | Slow | High | Large | Research, detailed studies |
| **Continuous Sweep** | Fast | Medium | Large | Surveys, dynamic measurements |
| **FM Modulation** | Very Fast | High | Small | Fine studies, high-speed |

## Data Output

### Common Data Fields
- `frequencies`: Frequency array for the scan
- `counts`: Photon count data (averaged)
- `counts_raw`: Raw count data for all averages
- `powers`: Microwave power at each point
- `fit_parameters`: Lorentzian fit parameters
- `resonance_frequencies`: Identified resonance frequencies

### Experiment-Specific Data
- **Stepped**: `counts_raw` with shape (frequency_steps, averages)
- **Continuous Sweep**: `counts_forward`, `counts_reverse`, `counts_averaged`, `sweep_time`
- **FM Modulation**: `modulation_phase`, `cycle_time`, `lock_in_signal`

## Analysis Features

### Common Analysis
- **Smoothing**: Savitzky-Golay filtering
- **Background Subtraction**: Minimum value subtraction
- **Peak Finding**: Local maxima detection
- **Lorentzian Fitting**: Resonance parameter extraction

### Advanced Features
- **Lock-in Detection**: Phase-sensitive detection for FM experiments
- **Bidirectional Averaging**: Forward/reverse sweep averaging
- **Multiple Averages**: Statistical improvement through averaging

## Usage Examples

### Basic Stepped ODMR
```python
from src.Model.experiments import ODMRSteppedExperiment

# Create experiment
exp = ODMRSteppedExperiment(devices, settings={
    'frequency_range': {'start': 2.7e9, 'stop': 3.0e9, 'steps': 100},
    'microwave': {'power': -10.0, 'settle_time': 0.01},
    'acquisition': {'integration_time': 0.1, 'averages': 10}
})

# Run experiment
exp.run()
```

### Fast Continuous Sweep
```python
from src.Model.experiments import ODMRSweepContinuousExperiment

# Create experiment
exp = ODMRSweepContinuousExperiment(devices, settings={
    'frequency_range': {'start': 2.7e9, 'stop': 3.0e9},
    'microwave': {'power': -10.0, 'sweep_rate': 1e6, 'sweep_function': 'Triangle'},
    'acquisition': {'integration_time': 0.001, 'averages': 10}
})

# Run experiment
exp.run()
```

### High-Speed FM Modulation
```python
from src.Model.experiments import ODMRFMModulationExperiment

# Create experiment
exp = ODMRFMModulationExperiment(devices, settings={
    'frequency': {'center': 2.87e9, 'modulation_depth': 10e6, 'modulation_rate': 1e3},
    'microwave': {'power': -10.0, 'modulation_function': 'Sine'},
    'acquisition': {'integration_time': 0.001, 'averages': 100}
})

# Run experiment
exp.run()
```

## Migration from Old Experiments

### What to Replace
- **`odmr_enhanced`** → Use `ODMRSteppedExperiment` for detailed studies
- **`odmr_experiment`** → Use `ODMRSweepContinuousExperiment` for fast surveys
- **`odmr_simple_adwin`** → Use `ODMRSteppedExperiment` with simpler settings
- **`odmr_sweep_enhanced`** → Use `ODMRSweepContinuousExperiment` or `ODMRFMModulationExperiment`

### Key Differences
- **Real SG384 Control**: Actually sets frequencies instead of just storing parameters
- **Proper Adwin Integration**: Uses existing helper functions and appropriate counter programs for each experiment type
- **Focused Functionality**: Each experiment optimized for specific use case
- **Better Data Structure**: Consistent data organization and analysis
- **Code Reuse**: Leverages existing `adwin_helpers.py` functions for consistency and maintainability

## Future Enhancements

### Planned Features
- **2D ODMR Scans**: Combine with position scanning
- **Advanced Lock-in**: More sophisticated lock-in detection algorithms
- **Real-time Analysis**: Live data analysis during acquisition
- **Multi-resonance Fitting**: Simultaneous fitting of multiple resonances

### Potential Improvements
- **Adaptive Integration**: Dynamic integration time based on signal strength
- **Smart Averaging**: Intelligent averaging based on noise characteristics
- **Calibration Tools**: Frequency and power calibration procedures
- **Export Formats**: Additional data export formats (CSV, HDF5, etc.)

## Conclusion

These three focused ODMR experiments provide a comprehensive toolkit for NV center characterization, each optimized for different experimental requirements. They properly integrate the SG384 microwave generator with Adwin photon counting, providing real frequency control and efficient data acquisition.

The experiments are designed to be:
- **Easy to Use**: Simple settings and clear documentation
- **Efficient**: Optimized for their specific use cases
- **Extensible**: Easy to modify and enhance
- **Well-Tested**: Comprehensive error handling and validation

Choose the experiment type based on your specific needs:
- **Stepped**: For high-precision, detailed studies
- **Continuous Sweep**: For fast surveys and dynamic measurements  
- **FM Modulation**: For fine studies and high-speed acquisition 