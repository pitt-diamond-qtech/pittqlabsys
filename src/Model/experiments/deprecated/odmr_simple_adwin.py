"""
Simple Optically Detected Magnetic Resonance (ODMR) Experiment with ADwin

DEPRECATED: This legacy simple ODMR experiment is superseded by the new
`ODMRSteppedExperiment`, which performs real stepped frequency control of the SG384
and integrates with ADwin helpers. See docs/ODMR_EXPERIMENTS_OVERVIEW.md.

This module implemented a simple ODMR experiment using ADwin for data acquisition.

Author: Gurudev Dutt <gdutt@pitt.edu>
Created: 2024
License: GPL v2
"""

import numpy as np
import pyqtgraph as pg
from scipy.optimize import curve_fit
from scipy.signal import savgol_filter
from typing import List, Dict, Any, Optional, Tuple
import time
import random
import warnings

from src.core.experiment import Experiment
from src.core.parameter import Parameter
from src.Controller.sg384 import SG384Generator
from src.Controller.adwin_gold import AdwinGoldDevice
from src.core.adwin_helpers import setup_adwin_for_simple_odmr, read_adwin_simple_odmr_data

# Emit a deprecation warning when this module is imported
warnings.warn(
    "src.Model.experiments.odmr_simple_adwin is deprecated. Use ODMRSteppedExperiment "
    "(see docs/ODMR_EXPERIMENTS_OVERVIEW.md).",
    FutureWarning,
    stacklevel=2,
)


class SimpleODMRExperiment(Experiment):
    """
    Simple ODMR Experiment using ADwin for data acquisition.
    
    This experiment performs basic ODMR measurements on nitrogen-vacancy centers
    by sweeping microwave frequency while monitoring fluorescence intensity.
    It uses ADwin for data acquisition instead of NI-DAQ for better integration
    and simpler setup.
    
    Based on the EsrSimple class but modernized with ADwin integration.
    """
    
    _DEFAULT_SETTINGS = [
        Parameter('frequency_range', [
            Parameter('start', 2.82e9, float, 'Start frequency in Hz', units='Hz'),
            Parameter('stop', 2.92e9, float, 'End frequency in Hz', units='Hz'),
            Parameter('points', 100, int, 'Number of frequency points'),
            Parameter('range_type', 'start_stop', ['start_stop', 'center_range'], 
                     'start_stop: range from start to stop, center_range: centered at start with width stop')
        ]),
        Parameter('microwave', [
            Parameter('power', -45.0, float, 'Microwave power in dBm', units='dBm'),
            Parameter('enable_output', True, bool, 'Enable microwave output'),
            Parameter('turn_off_after', False, bool, 'Turn off microwave output after experiment')
        ]),
        Parameter('acquisition', [
            Parameter('integration_time', 50.0, float, 'Integration time per point in milliseconds', units='ms'),
            Parameter('settle_time', 0.01, float, 'Settle time after frequency change', units='s'),
            Parameter('averages', 50, int, 'Number of sweeps to average'),
            Parameter('save_full_data', True, bool, 'Save all individual sweep data'),
            Parameter('save_timetrace', True, bool, 'Save fluorescence over time (useful when frequencies are randomized)')
        ]),
        Parameter('randomization', [
            Parameter('randomize_frequencies', True, bool, 'Randomize frequency order for each sweep'),
            Parameter('randomize_seed', None, int, 'Random seed for frequency randomization (None for random)')
        ]),
        Parameter('analysis', [
            Parameter('auto_fit', True, bool, 'Automatically fit resonances'),
            Parameter('minimum_counts', 0.5, float, 'Minimum counts for valid resonance'),
            Parameter('contrast_factor', 1.5, float, 'Minimum contrast for valid resonance'),
            Parameter('smoothing', True, bool, 'Apply smoothing to data'),
            Parameter('smooth_window', 5, int, 'Smoothing window size')
        ])
    ]
    
    _DEVICES = {
        'microwave': 'sg384',
        'adwin': 'adwin'
    }
    
    _EXPERIMENTS = {}
    
    def __init__(self, devices: Dict[str, Any], experiments: Optional[Dict[str, Any]] = None,
                 name: Optional[str] = None, settings: Optional[Dict[str, Any]] = None,
                 log_function=None, data_path: Optional[str] = None):
        """Initialize the simple ODMR experiment."""
        super().__init__(name, settings, devices, experiments, log_function, data_path)
        
        # Initialize data structures
        self.frequencies = None
        self.esr_data = None
        self.index_data = None
        self.average_counts = None
        
        # Get device instances
        self.microwave = self.devices['microwave']['instance']
        self.adwin = self.devices['adwin']['instance']
        
        # Set random seed if specified
        if self.settings['randomization']['randomize_seed'] is not None:
            random.seed(self.settings['randomization']['randomize_seed'])
    
    def setup(self):
        """Setup the experiment hardware and parameters."""
        self.log("Setting up simple ODMR experiment...")
        
        # Calculate frequencies based on range type
        self._calculate_frequencies()
        
        # Setup microwave generator
        self._setup_microwave()
        
        # Verify microwave is working
        self._verify_microwave_setup()
        
        # Setup ADwin for ODMR
        self._setup_adwin()
        
        # Initialize data arrays
        self._initialize_data_arrays()
        
        self.log("Simple ODMR experiment setup complete")
    
    def _calculate_frequencies(self):
        """Calculate frequency array based on range type."""
        range_type = self.settings['frequency_range']['range_type']
        start = self.settings['frequency_range']['start']
        stop = self.settings['frequency_range']['stop']
        points = self.settings['frequency_range']['points']
        
        if range_type == 'start_stop':
            if start > stop:
                raise ValueError("End frequency must be larger than start frequency for start_stop mode")
            if start < 950e3 or stop > 4.05e9:
                raise ValueError("Frequency out of bounds (950 kHz - 4.05 GHz)")
            
            self.frequencies = np.linspace(start, stop, points)
            
        elif range_type == 'center_range':
            if start < 2 * stop:
                raise ValueError("End freq(range) must be smaller than 2x start freq(center) for center_range mode")
            
            self.frequencies = np.linspace(start - stop/2, start + stop/2, points)
            
            if stop > 1e9:
                self.log("Warning: freq_stop (range) is quite large - did you mean 'start_stop'?", flag='warning')
        else:
            raise ValueError(f"Unknown range type: {range_type}")
    
    def _setup_microwave(self):
        """Setup microwave generator parameters."""
        self.microwave.update({
            'amplitude': self.settings['microwave']['power'],
            'enable_modulation': False,  # No FM modulation for simple ODMR
            'enable_output': self.settings['microwave']['enable_output']
        })
        
        # Ensure output is enabled if requested
        if self.settings['microwave']['enable_output']:
            self.log("Microwave output enabled")
        else:
            self.log("Microwave output disabled")
    
    def _verify_microwave_setup(self):
        """Verify that the microwave generator is properly configured."""
        self.log("Verifying microwave setup...")
        
        # Set initial frequency and verify
        initial_freq = self.frequencies[0]
        self.microwave.update({
            'frequency': float(initial_freq),
            'enable_output': self.settings['microwave']['enable_output']
        })
        
        # Read back the frequency to verify it was set
        try:
            actual_freq = self.microwave.read_probes('frequency')
            freq_error = abs(actual_freq - initial_freq) / initial_freq
            if freq_error > 1e-6:  # 1 ppm tolerance
                self.log(f"Warning: Frequency set to {initial_freq} Hz but read back as {actual_freq} Hz", flag='warning')
            else:
                self.log(f"Microwave frequency verified: {actual_freq:.3e} Hz")
        except Exception as e:
            self.log(f"Could not verify microwave frequency: {e}", flag='warning')
        
        # Check if output is enabled
        try:
            output_enabled = self.microwave.read_probes('enable_output')
            if output_enabled != self.settings['microwave']['enable_output']:
                self.log(f"Warning: Output enable mismatch. Expected: {self.settings['microwave']['enable_output']}, Actual: {output_enabled}", flag='warning')
            else:
                self.log(f"Microwave output status verified: {'enabled' if output_enabled else 'disabled'}")
        except Exception as e:
            self.log(f"Could not verify microwave output status: {e}", flag='warning')
    
    def _setup_adwin(self):
        """Setup ADwin for simple ODMR experiments."""
        integration_time_ms = self.settings['acquisition']['integration_time']
        
        setup_adwin_for_simple_odmr(
            self.adwin,
            integration_time_ms=integration_time_ms
        )
    
    def _initialize_data_arrays(self):
        """Initialize data arrays for the experiment."""
        averages = self.settings['acquisition']['averages']
        num_freq = len(self.frequencies)
        
        self.esr_data = np.zeros((averages, num_freq))
        self.average_counts = np.zeros(averages)
        
        if self.settings['acquisition']['save_timetrace']:
            self.index_data = np.zeros((averages, num_freq), dtype=int)
    
    def _function(self):
        """Main experiment execution."""
        self.log("Starting simple ODMR experiment...")
        
        try:
            # Start ADwin process
            self.adwin.start_process(1)
            time.sleep(0.1)  # Allow process to start
            
            start_time = time.time()
            
            # Run sweeps
            for scan_num in range(self.settings['acquisition']['averages']):
                if self.is_stopped():
                    break
                
                self.log(f"Starting average {scan_num + 1}/{self.settings['acquisition']['averages']}, "
                        f"time elapsed: {np.round(time.time() - start_time, 1)}s")
                
                # Get frequency indices (randomized if requested)
                freq_indices = list(range(len(self.frequencies)))
                if self.settings['randomization']['randomize_frequencies']:
                    random.shuffle(freq_indices)
                
                # Run single sweep
                single_sweep_data = self._run_single_sweep(freq_indices)
                
                if self.is_stopped():
                    break
                
                # Store data
                self.esr_data[scan_num] = single_sweep_data
                
                if self.settings['acquisition']['save_timetrace']:
                    self.index_data[scan_num] = freq_indices
                
                # Calculate current average
                esr_avg = np.mean(self.esr_data[0:(scan_num + 1)], axis=0)
                
                # Fit to the data
                fit_params = self._fit_esr_peaks(self.frequencies, esr_avg)
                
                # Update data dictionary
                self.data.update({
                    'frequency': self.frequencies,
                    'data': esr_avg,
                    'fit_params': fit_params
                })
                
                # Update progress
                progress = int(100 * (scan_num + 1) / self.settings['acquisition']['averages'])
                self.updateProgress.emit(progress)
            
            # Save full data if requested
            if self.settings['acquisition']['save_full_data']:
                self.data.update({'esr_data': self.esr_data})
            
            if self.settings['acquisition']['save_timetrace']:
                self.data.update({'index_data': self.index_data})
            
            # Analyze final data
            self._analyze_data()
            
            # Cleanup
            self.cleanup()
            
            self.log("Simple ODMR experiment completed successfully")
            
        except Exception as e:
            self.log(f"Simple ODMR experiment failed: {e}")
            self.cleanup()
            raise
    
    def _run_single_sweep(self, freq_indices: List[int]) -> np.ndarray:
        """
        Run a single frequency sweep.
        
        Args:
            freq_indices: List of frequency indices in the order to measure
            
        Returns:
            Array of fluorescence data for each frequency point
        """
        single_sweep_data = np.zeros(len(self.frequencies))
        
        for freq_idx in freq_indices:
            if self.is_stopped():
                break
            
            frequency = self.frequencies[freq_idx]
            
            # Set microwave frequency and ensure output is enabled
            self.microwave.update({
                'frequency': float(frequency),
                'enable_output': self.settings['microwave']['enable_output']
            })
            
            # Log frequency change (but not too frequently to avoid spam)
            if freq_idx % 10 == 0 or freq_idx == len(freq_indices) - 1:
                self.log(f"Set microwave frequency to {frequency/1e9:.3f} GHz")
            
            time.sleep(self.settings['acquisition']['settle_time'])
            
            # Measure signal
            signal = self._measure_signal()
            
            # Store data
            single_sweep_data[freq_idx] = signal
        
        # Convert to kcounts/sec
        integration_time_s = self.settings['acquisition']['integration_time'] / 1000.0
        single_sweep_data = single_sweep_data * (0.001 / integration_time_s)
        
        return single_sweep_data
    
    def _measure_signal(self) -> float:
        """
        Measure the fluorescence signal using ADwin.
        
        Returns:
            Total counts for the integration period
        """
        # Read data from ADwin
        counts = read_adwin_simple_odmr_data(self.adwin)
        
        # Return the counts
        return counts
    
    def _analyze_data(self):
        """Analyze the collected data."""
        self.log("Analyzing simple ODMR data...")
        
        # Calculate averaged data
        self.data.update({
            'esr_avg': np.mean(self.esr_data, axis=0),
            'esr_std': np.std(self.esr_data, axis=0)
        })
        
        # Apply smoothing if enabled
        if self.settings['analysis']['smoothing']:
            self.data['esr_avg'] = savgol_filter(
                self.data['esr_avg'], 
                self.settings['analysis']['smooth_window'], 
                3
            )
        
        # Fit resonances if enabled
        if self.settings['analysis']['auto_fit']:
            fit_params = self._fit_esr_peaks(self.frequencies, self.data['esr_avg'])
            self.data['fit_params'] = fit_params
        
        self.log("Data analysis complete")
    
    def _fit_esr_peaks(self, frequencies: np.ndarray, data: np.ndarray) -> List[Dict[str, float]]:
        """
        Fit ESR peaks using Lorentzian functions.
        
        Args:
            frequencies: Frequency array
            data: Intensity data
            
        Returns:
            List of fit parameters for each peak
        """
        peaks = []
        min_counts = self.settings['analysis']['minimum_counts']
        contrast_factor = self.settings['analysis']['contrast_factor']
        
        # Find peaks above threshold
        mean_data = np.mean(data)
        threshold = mean_data * contrast_factor
        
        # Simple peak detection
        for i in range(1, len(data) - 1):
            if (data[i] > threshold and 
                data[i] > data[i-1] and 
                data[i] > data[i+1] and
                data[i] > min_counts):
                
                # Fit Lorentzian to this peak
                try:
                    # Define Lorentzian function
                    def lorentzian(x, amplitude, center, width, offset):
                        return amplitude * (width**2 / ((x - center)**2 + width**2)) + offset
                    
                    # Initial guess
                    p0 = [data[i] - mean_data, frequencies[i], 1e6, mean_data]
                    
                    # Fit range
                    fit_range = 10  # points on each side
                    start_idx = max(0, i - fit_range)
                    end_idx = min(len(frequencies), i + fit_range + 1)
                    
                    popt, _ = curve_fit(lorentzian, 
                                      frequencies[start_idx:end_idx], 
                                      data[start_idx:end_idx], 
                                      p0=p0)
                    
                    peaks.append({
                        'amplitude': popt[0],
                        'center': popt[1],
                        'width': popt[2],
                        'offset': popt[3],
                        'peak_index': i
                    })
                    
                except Exception as e:
                    self.log(f"Peak fitting failed for peak at index {i}: {e}")
        
        return peaks
    
    def cleanup(self):
        """Cleanup experiment resources."""
        self.log("Cleaning up simple ODMR experiment...")
        
        # Stop ADwin process
        self.adwin.stop_process(1)
        
        # Turn off microwave if requested
        if self.settings['microwave']['turn_off_after']:
            self.microwave.update({'enable_output': False})
        
        self.log("Simple ODMR experiment cleanup complete")
    
    def _plot(self, axes_list: List[pg.PlotItem]):
        """Plot the simple ODMR data."""
        if not axes_list:
            return
        
        ax = axes_list[0]
        ax.clear()
        
        # Plot main ESR data
        ax.plot(self.frequencies / 1e9, self.data['esr_avg'], 
               pen='b', name='ESR')
        
        # Plot fit results if available
        if 'fit_params' in self.data and self.data['fit_params']:
            for i, peak in enumerate(self.data['fit_params']):
                # Generate fit curve
                def lorentzian(x, amplitude, center, width, offset):
                    return amplitude * (width**2 / ((x - center)**2 + width**2)) + offset
                
                x_fit = np.linspace(self.frequencies[0], self.frequencies[-1], 1000)
                y_fit = lorentzian(x_fit, peak['amplitude'], peak['center'], peak['width'], peak['offset'])
                
                ax.plot(x_fit / 1e9, y_fit, pen='g', name=f'Fit {i+1}')
                
                # Mark peak center
                ax.plot([peak['center'] / 1e9], [peak['amplitude'] + peak['offset']], 
                       symbol='o', symbolBrush='g', symbolSize=10)
        
        ax.setLabel('left', 'Fluorescence (kcounts/s)')
        ax.setLabel('bottom', 'Frequency (GHz)')
        ax.setTitle('Simple ODMR Spectrum (ADwin)')
        ax.showGrid(x=True, y=True)
        
        # Add legend
        ax.addLegend()
    
    def get_axes_layout(self, figure_list: List[str]) -> List[List[str]]:
        """Get the axes layout for plotting."""
        return [[figure_list[0]]]  # Single plot
    
    def get_experiment_info(self) -> Dict[str, Any]:
        """Get experiment information and metadata."""
        return {
            'experiment_type': 'Simple ODMR (ADwin)',
            'frequency_range': {
                'start': self.settings['frequency_range']['start'],
                'stop': self.settings['frequency_range']['stop'],
                'points': self.settings['frequency_range']['points'],
                'range_type': self.settings['frequency_range']['range_type']
            },
            'microwave_settings': {
                'power': self.settings['microwave']['power'],
                'enable_output': self.settings['microwave']['enable_output']
            },
            'acquisition_settings': {
                'integration_time': self.settings['acquisition']['integration_time'],
                'settle_time': self.settings['acquisition']['settle_time'],
                'averages': self.settings['acquisition']['averages'],
                'adwin_samples_per_point': self.settings['acquisition']['adwin_samples_per_point']
            },
            'randomization': {
                'randomize_frequencies': self.settings['randomization']['randomize_frequencies'],
                'randomize_seed': self.settings['randomization']['randomize_seed']
            },
            'fit_results': {
                'num_peaks': len(self.data['fit_params']) if 'fit_params' in self.data and self.data['fit_params'] else 0,
                'peaks': self.data['fit_params'] if 'fit_params' in self.data and self.data['fit_params'] else []
            }
        } 