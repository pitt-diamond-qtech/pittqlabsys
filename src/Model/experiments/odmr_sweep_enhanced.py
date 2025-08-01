"""
Enhanced Optically Detected Magnetic Resonance (ODMR) Experiment with SG384 Sweep

This module implements an enhanced ODMR experiment that uses the SG384's built-in
sweep function for much faster frequency sweeps compared to step-by-step frequency
setting. The sweep is handled internally by the microwave generator, making it
much more efficient for ODMR measurements.

Key Features:
- Uses SG384's built-in frequency sweep function
- Fast frequency sweeps (limited by sweep rate < 120 Hz)
- Automatic validation of sweep parameters
- Real-time data acquisition synchronized with sweep
- Support for different sweep functions (Triangle, Ramp, etc.)

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

from src.core import Experiment, Parameter
from src.Controller import SG384Generator, ADwinGold
from src.core.adwin_helpers import setup_adwin_for_sweep_odmr, read_adwin_sweep_odmr_data


class EnhancedODMRSweepExperiment(Experiment):
    """
    Enhanced ODMR Experiment using SG384's built-in sweep function.
    
    This experiment performs ODMR measurements using the SG384's internal sweep
    capability, which is much faster than step-by-step frequency setting. The
    sweep is synchronized with data acquisition for efficient measurements.
    
    The sweep parameters are automatically validated to ensure they're within
    the SG384's frequency range (1.9 GHz - 4.1 GHz).
    """
    
    _DEFAULT_SETTINGS = [
        Parameter('sweep_parameters', [
            Parameter('center_frequency', 2.87e9, float, 'Center frequency in Hz', units='Hz'),
            Parameter('deviation', 50e6, float, 'Frequency deviation (half sweep width) in Hz', units='Hz'),
            Parameter('sweep_rate', 1.0, float, 'Sweep rate in Hz (must be < 120 Hz)', units='Hz'),
            Parameter('sweep_function', 'Triangle', ['Triangle', 'Ramp', 'Sine', 'Square', 'Noise', 'External'], 
                     'Sweep function type')
        ]),
        Parameter('microwave', [
            Parameter('power', -45.0, float, 'Microwave power in dBm', units='dBm'),
            Parameter('enable_output', True, bool, 'Enable microwave output'),
            Parameter('turn_off_after', False, bool, 'Turn off microwave output after experiment')
        ]),
        Parameter('acquisition', [
            Parameter('integration_time', 10.0, float, 'Integration time per data point in milliseconds', units='ms'),
            Parameter('num_steps', 100, int, 'Number of steps in the sweep'),
            Parameter('sweeps_per_average', 10, int, 'Number of sweeps to average'),
            Parameter('bidirectional', False, bool, 'Do bidirectional sweeps (forward/reverse)'),
            Parameter('save_full_data', True, bool, 'Save all individual sweep data'),
            Parameter('trigger_mode', 'internal', ['internal', 'external'], 'Sweep trigger mode')
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
        'microwave': SG384Generator,
        'adwin': ADwinGold
    }
    
    _EXPERIMENTS = {}
    
    def __init__(self, devices: Dict[str, Any], experiments: Optional[Dict[str, Any]] = None,
                 name: Optional[str] = None, settings: Optional[Dict[str, Any]] = None,
                 log_function=None, data_path: Optional[str] = None):
        """Initialize the enhanced ODMR sweep experiment."""
        super().__init__(devices, experiments, name, settings, log_function, data_path)
        
        # Initialize data structures
        self.frequencies = None
        self.sweep_data = None
        self.average_data = None
        
        # Get device instances
        self.microwave = self.devices['microwave']['instance']
        self.adwin = self.devices['adwin']['instance']
    
    def setup(self):
        """Setup the experiment hardware and parameters."""
        self.log("Setting up enhanced ODMR sweep experiment...")
        
        # Validate sweep parameters
        self._validate_sweep_parameters()
        
        # Calculate frequency array for plotting
        self._calculate_frequency_array()
        
        # Setup microwave generator with sweep
        self._setup_microwave_sweep()
        
        # Setup ADwin for data acquisition
        self._setup_adwin()
        
        # Initialize data arrays
        self._initialize_data_arrays()
        
        self.log("Enhanced ODMR sweep experiment setup complete")
    
    def _validate_sweep_parameters(self):
        """Validate sweep parameters to ensure they're within SG384 limits."""
        center_freq = self.settings['sweep_parameters']['center_frequency']
        deviation = self.settings['sweep_parameters']['deviation']
        sweep_rate = self.settings['sweep_parameters']['sweep_rate']
        
        # Validate all sweep parameters including rate
        try:
            self.microwave.validate_sweep_parameters(center_freq, deviation, sweep_rate)
        except ValueError as e:
            self.log(f"Sweep parameter validation failed: {e}", flag='error')
            raise
        
        # Log sweep parameters
        sweep_min = center_freq - deviation
        sweep_max = center_freq + deviation
        self.log(f"Sweep range: {sweep_min/1e9:.3f} - {sweep_max/1e9:.3f} GHz")
        self.log(f"Sweep rate: {sweep_rate} Hz")
        self.log(f"Sweep function: {self.settings['sweep_parameters']['sweep_function']}")
    
    def _calculate_frequency_array(self):
        """Calculate frequency array for plotting based on sweep parameters."""
        center_freq = self.settings['sweep_parameters']['center_frequency']
        deviation = self.settings['sweep_parameters']['deviation']
        
        # Create frequency array for plotting
        # We'll use 1000 points for smooth plotting
        num_points = 1000
        self.frequencies = np.linspace(center_freq - deviation, center_freq + deviation, num_points)
    
    def _setup_microwave_sweep(self):
        """Setup microwave generator for sweep operation."""
        self.log("Setting up microwave sweep...")
        
        # Set basic parameters
        self.microwave.update({
            'frequency': self.settings['sweep_parameters']['center_frequency'],
            'amplitude': self.settings['microwave']['power'],
            'enable_output': self.settings['microwave']['enable_output'],
            'enable_modulation': True,
            'modulation_type': 'Freq sweep'
        })
        
        # Set sweep parameters
        self.microwave.update({
            'sweep_function': self.settings['sweep_parameters']['sweep_function'],
            'sweep_rate': self.settings['sweep_parameters']['sweep_rate'],
            'sweep_deviation': self.settings['sweep_parameters']['deviation']
        })
        
        self.log("Microwave sweep setup complete")
    
    def _setup_adwin(self):
        """Setup ADwin for synchronized sweep data acquisition."""
        integration_time_ms = self.settings['acquisition']['integration_time']
        num_steps = self.settings['acquisition']['num_steps']
        bidirectional = self.settings['acquisition']['bidirectional']
        
        setup_adwin_for_sweep_odmr(
            self.adwin,
            integration_time_ms=integration_time_ms,
            num_steps=num_steps,
            bidirectional=bidirectional
        )
    
    def _initialize_data_arrays(self):
        """Initialize data arrays for the experiment."""
        sweeps_per_avg = self.settings['acquisition']['sweeps_per_average']
        num_freq = len(self.frequencies)
        
        self.sweep_data = np.zeros((sweeps_per_avg, num_freq))
        self.average_data = np.zeros(num_freq)
    
    def _function(self):
        """Main experiment execution."""
        self.log("Starting enhanced ODMR sweep experiment...")
        
        try:
            # Start ADwin process
            self.adwin.start_process(1)
            time.sleep(0.1)  # Allow process to start
            
            start_time = time.time()
            
            # Run sweeps
            for sweep_num in range(self.settings['acquisition']['sweeps_per_average']):
                if self.is_stopped():
                    break
                
                self.log(f"Starting sweep {sweep_num + 1}/{self.settings['acquisition']['sweeps_per_average']}, "
                        f"time elapsed: {np.round(time.time() - start_time, 1)}s")
                
                # Run single sweep
                sweep_data = self._run_single_sweep()
                
                if self.is_stopped():
                    break
                
                # Store data
                self.sweep_data[sweep_num] = sweep_data
                
                # Calculate current average
                self.average_data = np.mean(self.sweep_data[0:(sweep_num + 1)], axis=0)
                
                # Fit to the data
                fit_params = self._fit_esr_peaks(self.frequencies, self.average_data)
                
                # Update data dictionary
                self.data.update({
                    'frequency': self.frequencies,
                    'data': self.average_data,
                    'fit_params': fit_params
                })
                
                # Update progress
                progress = int(100 * (sweep_num + 1) / self.settings['acquisition']['sweeps_per_average'])
                self.updateProgress.emit(progress)
            
            # Save full data if requested
            if self.settings['acquisition']['save_full_data']:
                self.data.update({'sweep_data': self.sweep_data})
            
            # Analyze final data
            self._analyze_data()
            
            # Cleanup
            self.cleanup()
            
            self.log("Enhanced ODMR sweep experiment completed successfully")
            
        except Exception as e:
            self.log(f"Enhanced ODMR sweep experiment failed: {e}")
            self.cleanup()
            raise
    
    def _run_single_sweep(self) -> np.ndarray:
        """
        Run a single frequency sweep.
        
        Returns:
            Array of fluorescence data for each frequency point
        """
        num_steps = self.settings['acquisition']['num_steps']
        integration_time_s = self.settings['acquisition']['integration_time'] / 1000.0
        
        # Initialize data array
        sweep_data = np.zeros(num_steps)
        
        # Wait for sweep to start and collect data
        sweep_complete = False
        step_index = 0
        
        while not sweep_complete and step_index < num_steps:
            # Read data from ADwin
            adwin_data = read_adwin_sweep_odmr_data(self.adwin)
            
            # Check if sweep is complete
            if adwin_data['sweep_complete']:
                sweep_complete = True
                break
            
            # Store data for current step
            current_step = adwin_data['step_index']
            if current_step < num_steps:
                # Convert counts to kcounts/sec
                counts_per_sec = adwin_data['total_counts'] * (0.001 / integration_time_s)
                sweep_data[current_step] = counts_per_sec
            
            # Update step index
            step_index = current_step
            
            # Small delay to avoid overwhelming the ADwin
            time.sleep(0.001)
        
        # Resample to match our frequency array if needed
        if len(sweep_data) != len(self.frequencies):
            from scipy.interpolate import interp1d
            x_old = np.linspace(0, 1, len(sweep_data))
            x_new = np.linspace(0, 1, len(self.frequencies))
            f = interp1d(x_old, sweep_data, kind='linear', bounds_error=False, fill_value=0)
            sweep_data = f(x_new)
        
        return sweep_data
    
    def _analyze_data(self):
        """Analyze the collected data."""
        self.log("Analyzing enhanced ODMR sweep data...")
        
        # Apply smoothing if enabled
        if self.settings['analysis']['smoothing']:
            self.data['data'] = savgol_filter(
                self.data['data'], 
                self.settings['analysis']['smooth_window'], 
                3
            )
        
        # Fit resonances if enabled
        if self.settings['analysis']['auto_fit']:
            fit_params = self._fit_esr_peaks(self.frequencies, self.data['data'])
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
        self.log("Cleaning up enhanced ODMR sweep experiment...")
        
        # Stop ADwin process
        self.adwin.stop_process(1)
        
        # Turn off microwave if requested
        if self.settings['microwave']['turn_off_after']:
            self.microwave.update({'enable_output': False})
        
        self.log("Enhanced ODMR sweep experiment cleanup complete")
    
    def _plot(self, axes_list: List[pg.PlotItem]):
        """Plot the enhanced ODMR sweep data."""
        if not axes_list:
            return
        
        ax = axes_list[0]
        ax.clear()
        
        # Plot main ESR data
        ax.plot(self.frequencies / 1e9, self.data['data'], 
               pen='b', name='ESR Sweep')
        
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
        ax.setTitle('Enhanced ODMR Sweep Spectrum (SG384)')
        ax.showGrid(x=True, y=True)
        
        # Add legend
        ax.addLegend()
    
    def get_axes_layout(self, figure_list: List[str]) -> List[List[str]]:
        """Get the axes layout for plotting."""
        return [[figure_list[0]]]  # Single plot
    
    def get_experiment_info(self) -> Dict[str, Any]:
        """Get experiment information and metadata."""
        center_freq = self.settings['sweep_parameters']['center_frequency']
        deviation = self.settings['sweep_parameters']['deviation']
        
        return {
            'experiment_type': 'Enhanced ODMR Sweep (SG384)',
            'sweep_parameters': {
                'center_frequency': center_freq,
                'deviation': deviation,
                'sweep_range': f"{(center_freq - deviation)/1e9:.3f} - {(center_freq + deviation)/1e9:.3f} GHz",
                'sweep_rate': self.settings['sweep_parameters']['sweep_rate'],
                'sweep_function': self.settings['sweep_parameters']['sweep_function']
            },
            'microwave_settings': {
                'power': self.settings['microwave']['power'],
                'enable_output': self.settings['microwave']['enable_output']
            },
            'acquisition_settings': {
                'integration_time': self.settings['acquisition']['integration_time'],
                'sweeps_per_average': self.settings['acquisition']['sweeps_per_average']
            },
            'fit_results': {
                'num_peaks': len(self.data['fit_params']) if 'fit_params' in self.data and self.data['fit_params'] else 0,
                'peaks': self.data['fit_params'] if 'fit_params' in self.data and self.data['fit_params'] else []
            }
        } 