"""
Enhanced Optically Detected Magnetic Resonance (ODMR) Experiment with External FM Modulation

This module implements an enhanced ODMR experiment that uses external FM modulation
of the SG384 microwave generator. The ADwin generates a voltage ramp on AO1 that
is connected to the SG384's FM input, providing synchronized frequency sweeping
and data acquisition.

Key Features:
- Uses external FM modulation for frequency sweeping
- Synchronized data acquisition with voltage ramp
- Automatic validation of sweep parameters
- Real-time data acquisition synchronized with sweep
- Support for different sweep functions and bidirectional sweeps

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
    Enhanced ODMR Experiment using external FM modulation.
    
    This experiment performs ODMR measurements using external FM modulation of the
    SG384 microwave generator. The ADwin generates a voltage ramp on AO1 that is
    connected to the SG384's FM input, providing synchronized frequency sweeping
    and data acquisition.
    
    The sweep parameters are automatically validated to ensure they're within
    the SG384's frequency range (1.9 GHz - 4.1 GHz).
    """
    
    _DEFAULT_SETTINGS = [
        Parameter('sweep_parameters', [
            Parameter('center_frequency', 2.87e9, float, 'Center frequency in Hz', units='Hz'),
            Parameter('deviation', 50e6, float, 'Frequency deviation (half sweep width) in Hz', units='Hz'),
            Parameter('fm_sensitivity', 1e6, float, 'FM sensitivity in Hz/V', units='Hz/V'),
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
        
        # Calculate frequency array
        self._calculate_frequency_array()
        
        # Setup microwave generator
        self._setup_microwave()
        
        # Setup ADwin for synchronized data acquisition
        self._setup_adwin()
        
        # Initialize data arrays
        self._initialize_data_arrays()
        
        self.log("Enhanced ODMR sweep experiment setup complete")
    
    def _validate_sweep_parameters(self):
        """Validate sweep parameters are within SG384 limits."""
        center_freq = self.settings['sweep_parameters']['center_frequency']
        deviation = self.settings['sweep_parameters']['deviation']
        
        # Check frequency range
        min_freq = center_freq - deviation
        max_freq = center_freq + deviation
        
        if min_freq < 1.9e9:
            raise ValueError(f"Minimum frequency {min_freq/1e9:.2f} GHz is below SG384 limit of 1.9 GHz")
        
        if max_freq > 4.1e9:
            raise ValueError(f"Maximum frequency {max_freq/1e9:.2f} GHz is above SG384 limit of 4.1 GHz")
        
        self.log(f"Frequency range: {min_freq/1e9:.3f} - {max_freq/1e9:.3f} GHz")
    
    def _calculate_frequency_array(self):
        """Calculate the frequency array for the sweep."""
        center_freq = self.settings['sweep_parameters']['center_frequency']
        deviation = self.settings['sweep_parameters']['deviation']
        num_steps = self.settings['acquisition']['num_steps']
        
        # Create frequency array from -deviation to +deviation
        self.frequencies = np.linspace(
            center_freq - deviation,
            center_freq + deviation,
            num_steps
        )
        
        self.log(f"Frequency array: {num_steps} points from {self.frequencies[0]/1e9:.3f} to {self.frequencies[-1]/1e9:.3f} GHz")
    
    def _setup_microwave(self):
        """Setup microwave generator for external FM modulation."""
        self.log("Setting up microwave generator for external FM modulation...")
        
        # Set center frequency and power
        self.microwave.update({
            'frequency': self.settings['sweep_parameters']['center_frequency'],
            'power': self.settings['microwave']['power'],
            'enable_output': self.settings['microwave']['enable_output']
        })
        
        # Enable external FM modulation
        # The ADwin will generate the modulation signal on AO1
        self.microwave.update({
            'enable_modulation': True,
            'modulation_function': 'External',  # Use external modulation input
            'modulation_frequency': 0,  # Not used for external modulation
            'modulation_amplitude': 1.0  # Full modulation depth
        })
        
        self.log("Microwave generator setup complete")
    
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
            bidirectional = self.settings['acquisition']['bidirectional']
            
            # Initialize data structures for bidirectional sweeps
            if bidirectional:
                self.forward_sweep_data = np.zeros((self.settings['acquisition']['sweeps_per_average'], 
                                                   self.settings['acquisition']['num_steps']))
                self.reverse_sweep_data = np.zeros((self.settings['acquisition']['sweeps_per_average'], 
                                                   self.settings['acquisition']['num_steps']))
                self.forward_average_data = np.zeros(self.settings['acquisition']['num_steps'])
                self.reverse_average_data = np.zeros(self.settings['acquisition']['num_steps'])
            else:
                self.sweep_data = np.zeros((self.settings['acquisition']['sweeps_per_average'], 
                                          self.settings['acquisition']['num_steps']))
                self.average_data = np.zeros(self.settings['acquisition']['num_steps'])
            
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
                
                # Store data based on sweep type
                if bidirectional:
                    # Store bidirectional sweep data
                    self.forward_sweep_data[sweep_num] = sweep_data['forward_data']
                    self.reverse_sweep_data[sweep_num] = sweep_data['reverse_data']
                    
                    # Calculate current averages
                    self.forward_average_data = np.mean(self.forward_sweep_data[0:(sweep_num + 1)], axis=0)
                    self.reverse_average_data = np.mean(self.reverse_sweep_data[0:(sweep_num + 1)], axis=0)
                    
                    # Store frequency arrays (same for all sweeps)
                    self.forward_frequencies = sweep_data['forward_frequencies']
                    self.reverse_frequencies = sweep_data['reverse_frequencies']
                    
                    # Fit to the data (use forward sweep for fitting)
                    fit_params = self._fit_esr_peaks(self.forward_frequencies, self.forward_average_data)
                    
                    # Update data dictionary
                    self.data.update({
                        'forward_frequency': self.forward_frequencies,
                        'reverse_frequency': self.reverse_frequencies,
                        'forward_data': self.forward_average_data,
                        'reverse_data': self.reverse_average_data,
                        'fit_params': fit_params
                    })
                    
                else:
                    # Store unidirectional sweep data
                    self.sweep_data[sweep_num] = sweep_data['forward_data']
                    
                    # Calculate current average
                    self.average_data = np.mean(self.sweep_data[0:(sweep_num + 1)], axis=0)
                    
                    # Store frequency array
                    self.frequencies = sweep_data['forward_frequencies']
                    
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
                if bidirectional:
                    self.data.update({
                        'forward_sweep_data': self.forward_sweep_data,
                        'reverse_sweep_data': self.reverse_sweep_data
                    })
                else:
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
    
    def _run_single_sweep(self) -> Dict[str, np.ndarray]:
        """
        Run a single bidirectional frequency sweep.
        
        Returns:
            Dictionary containing:
            - 'forward_data': Array of forward sweep data
            - 'reverse_data': Array of reverse sweep data
            - 'forward_frequencies': Array of forward sweep frequencies
            - 'reverse_frequencies': Array of reverse sweep frequencies
        """
        num_steps = self.settings['acquisition']['num_steps']
        integration_time_s = self.settings['acquisition']['integration_time'] / 1000.0
        bidirectional = self.settings['acquisition']['bidirectional']
        
        # Wait for sweep to complete
        sweep_complete = False
        data_ready = False
        
        while not sweep_complete:
            # Read data from ADwin
            adwin_data = read_adwin_sweep_odmr_data(self.adwin)
            
            # Check if sweep is complete
            if adwin_data['sweep_complete'] and adwin_data['data_ready']:
                sweep_complete = True
                data_ready = True
                break
            
            # Small delay to avoid overwhelming the ADwin
            time.sleep(0.001)
        
        if not data_ready:
            raise RuntimeError("Sweep did not complete properly")
        
        # Process the completed sweep data
        if bidirectional and adwin_data['forward_counts'] is not None and adwin_data['reverse_counts'] is not None:
            # Bidirectional sweep - process both directions
            
            # Convert counts to kcounts/sec
            forward_counts_per_sec = np.array(adwin_data['forward_counts']) * (0.001 / integration_time_s)
            reverse_counts_per_sec = np.array(adwin_data['reverse_counts']) * (0.001 / integration_time_s)
            
            # Convert voltages to frequencies using FM sensitivity
            fm_sensitivity = self.settings['sweep_parameters']['fm_sensitivity']
            center_freq = self.settings['sweep_parameters']['center_frequency']
            
            forward_voltages = np.array(adwin_data['forward_voltages'])
            reverse_voltages = np.array(adwin_data['reverse_voltages'])
            
            # Calculate frequencies: f = f_center + V * fm_sensitivity
            forward_frequencies = center_freq + forward_voltages * fm_sensitivity
            reverse_frequencies = center_freq + reverse_voltages * fm_sensitivity
            
            return {
                'forward_data': forward_counts_per_sec,
                'reverse_data': reverse_counts_per_sec,
                'forward_frequencies': forward_frequencies,
                'reverse_frequencies': reverse_frequencies,
                'forward_voltages': forward_voltages,
                'reverse_voltages': reverse_voltages
            }
            
        else:
            # Unidirectional sweep - use only forward data
            if adwin_data['forward_counts'] is not None:
                forward_counts_per_sec = np.array(adwin_data['forward_counts']) * (0.001 / integration_time_s)
                forward_voltages = np.array(adwin_data['forward_voltages'])
                
                # Convert voltages to frequencies
                fm_sensitivity = self.settings['sweep_parameters']['fm_sensitivity']
                center_freq = self.settings['sweep_parameters']['center_frequency']
                forward_frequencies = center_freq + forward_voltages * fm_sensitivity
                
                return {
                    'forward_data': forward_counts_per_sec,
                    'reverse_data': None,
                    'forward_frequencies': forward_frequencies,
                    'reverse_frequencies': None,
                    'forward_voltages': forward_voltages,
                    'reverse_voltages': None
                }
            else:
                raise RuntimeError("No sweep data available")
    
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
                        'center_ghz': popt[1] / 1e9,
                        'width_mhz': popt[2] / 1e6
                    })
                    
                except Exception as e:
                    self.log(f"Failed to fit peak at index {i}: {e}")
                    continue
        
        self.log(f"Found {len(peaks)} ESR peaks")
        return peaks
    
    def cleanup(self):
        """Cleanup after experiment."""
        self.log("Cleaning up enhanced ODMR sweep experiment...")
        
        # Stop ADwin process
        try:
            self.adwin.stop_process(1)
        except:
            pass
        
        # Turn off microwave if requested
        if self.settings['microwave']['turn_off_after']:
            self.microwave.update({'enable_output': False})
        
        self.log("Cleanup complete")
    
    def _plot(self, axes_list: List[pg.PlotItem]):
        """Plot the experiment data."""
        if not axes_list:
            return
        
        # Plot frequency vs intensity
        axes = axes_list[0]
        axes.clear()
        
        # Check if we have bidirectional data
        if 'forward_frequency' in self.data and 'reverse_frequency' in self.data:
            # Bidirectional sweep - plot both directions
            forward_frequencies = self.data['forward_frequency'] / 1e9  # Convert to GHz
            reverse_frequencies = self.data['reverse_frequency'] / 1e9  # Convert to GHz
            forward_data = self.data['forward_data']
            reverse_data = self.data['reverse_data']
            
            # Plot forward sweep
            axes.plot(forward_frequencies, forward_data, pen='b', name='Forward Sweep')
            
            # Plot reverse sweep
            axes.plot(reverse_frequencies, reverse_data, pen='r', name='Reverse Sweep')
            
            # Plot fit if available (use forward sweep for fitting)
            if 'fit_params' in self.data and self.data['fit_params']:
                for peak in self.data['fit_params']:
                    # Define Lorentzian function
                    def lorentzian(x, amplitude, center, width, offset):
                        return amplitude * (width**2 / ((x - center)**2 + width**2)) + offset
                    
                    # Generate fit curve
                    x_fit = np.linspace(forward_frequencies[0], forward_frequencies[-1], 1000)
                    y_fit = lorentzian(x_fit * 1e9, peak['amplitude'], peak['center'], peak['width'], peak['offset'])
                    
                    axes.plot(x_fit, y_fit, pen='g', name=f'Peak at {peak["center_ghz"]:.3f} GHz')
            
            axes.setLabel('left', 'Intensity', units='kcounts/s')
            axes.setLabel('bottom', 'Frequency', units='GHz')
            axes.setTitle('Enhanced ODMR Sweep (Bidirectional)')
            axes.showGrid(x=True, y=True)
            axes.addLegend()
            
        elif 'frequency' in self.data and 'data' in self.data:
            # Unidirectional sweep
            frequencies = self.data['frequency'] / 1e9  # Convert to GHz
            data = self.data['data']
            
            # Plot data
            axes.plot(frequencies, data, pen='b', name='ODMR Data')
            
            # Plot fit if available
            if 'fit_params' in self.data and self.data['fit_params']:
                for peak in self.data['fit_params']:
                    # Define Lorentzian function
                    def lorentzian(x, amplitude, center, width, offset):
                        return amplitude * (width**2 / ((x - center)**2 + width**2)) + offset
                    
                    # Generate fit curve
                    x_fit = np.linspace(frequencies[0], frequencies[-1], 1000)
                    y_fit = lorentzian(x_fit * 1e9, peak['amplitude'], peak['center'], peak['width'], peak['offset'])
                    
                    axes.plot(x_fit, y_fit, pen='r', name=f'Peak at {peak["center_ghz"]:.3f} GHz')
            
            axes.setLabel('left', 'Intensity', units='kcounts/s')
            axes.setLabel('bottom', 'Frequency', units='GHz')
            axes.setTitle('Enhanced ODMR Sweep')
            axes.showGrid(x=True, y=True)
            axes.addLegend()
    
    def get_axes_layout(self, figure_list: List[str]) -> List[List[str]]:
        """Get the axes layout for plotting."""
        return [['ODMR Sweep']]
    
    def get_experiment_info(self) -> Dict[str, Any]:
        """Get information about the experiment."""
        return {
            'name': 'Enhanced ODMR Sweep',
            'description': 'ODMR experiment using external FM modulation',
            'center_frequency': self.settings['sweep_parameters']['center_frequency'] / 1e9,
            'deviation': self.settings['sweep_parameters']['deviation'] / 1e6,
            'num_steps': self.settings['acquisition']['num_steps'],
            'sweeps_per_average': self.settings['acquisition']['sweeps_per_average']
        } 