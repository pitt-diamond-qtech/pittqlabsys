"""
Enhanced Optically Detected Magnetic Resonance (ODMR) Experiment

DEPRECATED: This legacy experiment is superseded by:
- `ODMRSteppedExperiment` (precise stepped control)
- `ODMRSweepContinuousExperiment` (phase-continuous sweep)
- `ODMRFMModulationExperiment` (fine, fast FM sweeps)

These newer experiments directly control the SG384 and integrate with ADwin helpers.
See docs/ODMR_EXPERIMENTS_OVERVIEW.md.

This module implemented an enhanced ODMR experiment with advanced features such as FM, laser
power tracking, and ADwin integration.

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
import warnings

from src.core.experiment import Experiment
from src.core.parameter import Parameter
from src.Controller.sg384 import SG384Generator
from src.Controller.adwin_gold import AdwinGoldDevice
from src.core.adwin_helpers import setup_adwin_for_odmr, read_adwin_odmr_data

# Emit a deprecation warning when this module is imported
warnings.warn(
    "src.Model.experiments.odmr_enhanced is deprecated. Use ODMRSteppedExperiment, "
    "ODMRSweepContinuousExperiment, or ODMRFMModulationExperiment (see docs/ODMR_EXPERIMENTS_OVERVIEW.md).",
    FutureWarning,
    stacklevel=2,
)


class EnhancedODMRExperiment(Experiment):
    """
    Enhanced ODMR Experiment with Frequency Modulation and Advanced Features.
    
    This experiment performs ODMR measurements with advanced capabilities:
    - Frequency modulation (FM) using microwave generator
    - Laser power tracking and normalization using ADwin
    - Advanced frequency range handling
    - ADwin-based data acquisition
    - Real-time data processing
    
    Based on the old EsrDaqFm class but modernized with the new architecture.
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
            Parameter('modulation_type', 'FM', ['FM', 'AM', 'None'], 'Modulation type'),
            Parameter('dev_width', 3.2e7, float, 'Frequency deviation width in Hz', units='Hz'),
            Parameter('enable_modulation', True, bool, 'Enable frequency modulation'),
            Parameter('enable_output', True, bool, 'Enable microwave output'),
            Parameter('fm_source', 'ADwin', ['ADwin', 'Internal'], 'Source of FM modulation signal'),
            Parameter('fm_frequency', 1000.0, float, 'FM modulation frequency in Hz', units='Hz'),
            Parameter('fm_amplitude', 1.0, float, 'FM modulation amplitude in volts', units='V')
        ]),
        Parameter('acquisition', [
            Parameter('integration_time', 10.0, float, 'Integration time per point in milliseconds', units='ms'),
            Parameter('settle_time', 0.2, float, 'Settle time after frequency change', units='s'),
            Parameter('mw_switching_time', 0.01, float, 'Time to wait after switching center frequencies', units='s'),
            Parameter('averages', 50, int, 'Number of sweeps to average'),
            Parameter('save_full_data', True, bool, 'Save all individual sweep data'),
            Parameter('adwin_samples_per_point', 1, int, 'Number of ADwin samples to average per frequency point')
        ]),
        Parameter('laser_tracking', [
            Parameter('enabled', False, bool, 'Enable laser power tracking'),
            Parameter('normalize_data', True, bool, 'Normalize data by laser power')
        ]),
        Parameter('analysis', [
            Parameter('auto_fit', True, bool, 'Automatically fit resonances'),
            Parameter('minimum_counts', 0.5, float, 'Minimum counts for valid resonance'),
            Parameter('contrast_factor', 1.5, float, 'Minimum contrast for valid resonance'),
            Parameter('smoothing', True, bool, 'Apply smoothing to data'),
            Parameter('smooth_window', 5, int, 'Smoothing window size')
        ]),
        Parameter('experiment_control', [
            Parameter('turn_off_after', False, bool, 'Turn off microwave output after experiment'),
            Parameter('take_reference', True, bool, 'Normalize each sweep by average counts'),
            Parameter('reboot_adwin', False, bool, 'Reboot ADwin before experiment (useful if data looks corrupted)')
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
        """Initialize the enhanced ODMR experiment."""
        super().__init__(name, settings, devices, experiments, log_function, data_path)
        
        # Initialize data structures
        self.frequencies = None
        self.esr_data = None
        self.laser_data = None
        self.normalized_data = None
        self.average_counts = None
        
        # Get device instances
        self.microwave = self.devices['microwave']['instance']
        self.adwin = self.devices['adwin']['instance']
    
    def setup(self):
        """Setup the experiment hardware and parameters."""
        self.log("Setting up enhanced ODMR experiment...")
        
        # Reboot ADwin if requested
        if self.settings['experiment_control']['reboot_adwin']:
            self.log("Rebooting ADwin...")
            self.adwin.reboot_adwin()
        
        # Calculate frequencies based on range type
        self._calculate_frequencies()
        
        # Setup microwave generator
        self._setup_microwave()
        
        # Setup ADwin for ODMR
        self._setup_adwin()
        
        # Initialize data arrays
        self._initialize_data_arrays()
        
        self.log("Enhanced ODMR experiment setup complete")
    
    def _calculate_frequencies(self):
        """Calculate frequency array based on range type."""
        range_type = self.settings['frequency_range']['range_type']
        start = self.settings['frequency_range']['start']
        stop = self.settings['frequency_range']['stop']
        points = self.settings['frequency_range']['points']
        
        if range_type == 'start_stop':
            if start > stop:
                raise ValueError("End frequency must be larger than start frequency for start_stop mode")
            if start < 0 or stop > 4.05e9:
                raise ValueError("Frequency out of bounds (0-4.05 GHz)")
            
            self.frequencies = np.linspace(start, stop, points)
            self.freq_range = max(self.frequencies) - min(self.frequencies)
            
        elif range_type == 'center_range':
            if start < 2 * stop:
                raise ValueError("End freq(range) must be smaller than 2x start freq(center) for center_range mode")
            
            self.frequencies = np.linspace(start - stop/2, start + stop/2, points)
            self.freq_range = max(self.frequencies) - min(self.frequencies)
            
            if stop > 1e9:
                self.log("Warning: freq_stop (range) is quite large - did you mean 'start_stop'?", flag='warning')
        else:
            raise ValueError(f"Unknown range type: {range_type}")
    
    def _setup_microwave(self):
        """Setup microwave generator parameters."""
        # Set basic parameters
        self.microwave.update({
            'amplitude': self.settings['microwave']['power'],
            'modulation_type': self.settings['microwave']['modulation_type'],
            'dev_width': self.settings['microwave']['dev_width'],
            'enable_modulation': self.settings['microwave']['enable_modulation'],
            'enable_output': self.settings['microwave']['enable_output']
        })
        
        # If using ADwin for FM, disable internal modulation
        if (self.settings['microwave']['enable_modulation'] and 
            self.settings['microwave']['modulation_type'] == 'FM' and
            self.settings['microwave']['fm_source'] == 'ADwin'):
            # The ADwin will provide the FM signal via AO1
            # The microwave generator should be set to external modulation
            self.log("Using ADwin AO1 for FM modulation signal")
            # Note: The actual external modulation setup depends on the microwave generator implementation
    
    def _setup_adwin(self):
        """Setup ADwin for ODMR experiments."""
        integration_time_ms = self.settings['acquisition']['integration_time']
        num_averages = self.settings['acquisition']['adwin_samples_per_point']
        enable_laser_tracking = self.settings['laser_tracking']['enabled']
        
        # Check if FM modulation should be enabled
        enable_fm_modulation = (
            self.settings['microwave']['enable_modulation'] and 
            self.settings['microwave']['modulation_type'] == 'FM' and
            self.settings['microwave']['fm_source'] == 'ADwin'
        )
        
        fm_frequency = self.settings['microwave']['fm_frequency']
        fm_amplitude = self.settings['microwave']['fm_amplitude']
        
        setup_adwin_for_odmr(
            self.adwin,
            integration_time_ms=integration_time_ms,
            num_averages=num_averages,
            enable_laser_tracking=enable_laser_tracking,
            enable_fm_modulation=enable_fm_modulation,
            fm_frequency=fm_frequency,
            fm_amplitude=fm_amplitude
        )
    
    def _initialize_data_arrays(self):
        """Initialize data arrays for the experiment."""
        averages = self.settings['acquisition']['averages']
        num_freq = len(self.frequencies)
        
        self.esr_data = np.zeros((averages, num_freq))
        self.laser_data = np.zeros((averages, num_freq))
        self.normalized_data = np.zeros((averages, num_freq))
        self.average_counts = np.zeros(averages)
    
    def _function(self):
        """Main experiment execution with advanced features."""
        self.log("Starting enhanced ODMR experiment...")
        
        try:
            # Start ADwin process
            self.adwin.start_process(2)
            time.sleep(0.1)  # Allow process to start
            
            # Run the experiment
            for scan_num in range(self.settings['acquisition']['averages']):
                if self.is_stopped():
                    break
                
                self.log(f"Running sweep {scan_num + 1}/{self.settings['acquisition']['averages']}")
                
                # Process each frequency point
                for freq_idx, frequency in enumerate(self.frequencies):
                    if self.is_stopped():
                        break
                    
                    # Set microwave frequency
                    self.microwave.update({'frequency': float(frequency)})
                    time.sleep(self.settings['acquisition']['settle_time'])
                    
                    # Read data from ADwin
                    adwin_data = read_adwin_odmr_data(self.adwin)
                    
                    # Store data
                    self.esr_data[scan_num, freq_idx] = adwin_data['counts']
                    
                    if self.settings['laser_tracking']['enabled']:
                        self.laser_data[scan_num, freq_idx] = adwin_data['laser_power']
                
                # Calculate average counts for this sweep
                self.average_counts[scan_num] = np.mean(self.esr_data[scan_num])
                
                # Normalize if requested
                if self.settings['experiment_control']['take_reference']:
                    self.esr_data[scan_num] /= self.average_counts[scan_num]
                
                # Update progress
                progress = int(100 * (scan_num + 1) / self.settings['acquisition']['averages'])
                self.updateProgress.emit(progress)
            
            # Calculate normalized data if laser tracking is enabled
            if self.settings['laser_tracking']['enabled']:
                self._calculate_normalized_data()
            
            # Analyze data
            self._analyze_data()
            
            # Cleanup
            self.cleanup()
            
            self.log("Enhanced ODMR experiment completed successfully")
            
        except Exception as e:
            self.log(f"Enhanced ODMR experiment failed: {e}")
            self.cleanup()
            raise
    
    def _calculate_normalized_data(self):
        """Calculate laser-normalized data."""
        for scan_num in range(self.settings['acquisition']['averages']):
            for freq_idx in range(len(self.frequencies)):
                if self.laser_data[scan_num, freq_idx] > 0:
                    # Normalize by laser power
                    self.normalized_data[scan_num, freq_idx] = (
                        self.esr_data[scan_num, freq_idx] / self.laser_data[scan_num, freq_idx]
                    )
                else:
                    self.normalized_data[scan_num, freq_idx] = self.esr_data[scan_num, freq_idx]
    
    def _analyze_data(self):
        """Analyze the collected data."""
        self.log("Analyzing enhanced ODMR data...")
        
        # Calculate averaged data
        self.data = {
            'frequency': self.frequencies,
            'esr_avg': np.mean(self.esr_data, axis=0),
            'esr_std': np.std(self.esr_data, axis=0),
            'average_counts': self.average_counts,
            'fit_params': None
        }
        
        # Add laser tracking data if enabled
        if self.settings['laser_tracking']['enabled']:
            self.data.update({
                'laser_avg': np.mean(self.laser_data, axis=0),
                'normalized_avg': np.mean(self.normalized_data, axis=0)
            })
        
        # Add full data if requested
        if self.settings['acquisition']['save_full_data']:
            self.data.update({
                'esr_data': self.esr_data,
                'laser_data': self.laser_data if self.settings['laser_tracking']['enabled'] else None,
                'normalized_data': self.normalized_data if self.settings['laser_tracking']['enabled'] else None
            })
        
        # Fit resonances if enabled
        if self.settings['analysis']['auto_fit']:
            self._fit_resonances()
        
        self.log("Data analysis complete")
    
    def _fit_resonances(self):
        """Fit resonance peaks in the data."""
        try:
            # Use normalized data if available, otherwise use raw data
            if self.settings['laser_tracking']['enabled']:
                fit_data = self.data['normalized_avg']
            else:
                fit_data = self.data['esr_avg']
            
            # Apply smoothing if enabled
            if self.settings['analysis']['smoothing']:
                fit_data = savgol_filter(fit_data, self.settings['analysis']['smooth_window'], 3)
            
            # Fit resonances
            fit_params = self._fit_esr_peaks(self.frequencies, fit_data)
            self.data['fit_params'] = fit_params
            
        except Exception as e:
            self.log(f"Resonance fitting failed: {e}")
            self.data['fit_params'] = None
    
    def _fit_esr_peaks(self, frequencies: np.ndarray, data: np.ndarray) -> List[Dict[str, float]]:
        """
        Fit ESR peaks using Lorentzian functions.
        
        Args:
            frequencies: Frequency array
            data: Intensity data
            
        Returns:
            List of fit parameters for each peak
        """
        # Simple peak finding and fitting
        # This is a basic implementation - could be enhanced with more sophisticated peak finding
        
        peaks = []
        min_counts = self.settings['analysis']['minimum_counts']
        contrast_factor = self.settings['analysis']['contrast_factor']
        
        # Find peaks above threshold
        mean_data = np.mean(data)
        threshold = mean_data * contrast_factor
        
        # Simple peak detection (could be improved)
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
        self.log("Cleaning up enhanced ODMR experiment...")
        
        # Stop ADwin process
        self.adwin.stop_process(2)
        
        # Turn off microwave if requested
        if self.settings['experiment_control']['turn_off_after']:
            self.microwave.update({'enable_output': False})
        
        self.log("Enhanced ODMR experiment cleanup complete")
    
    def _plot(self, axes_list: List[pg.PlotItem]):
        """Plot the enhanced ODMR data."""
        if not axes_list:
            return
        
        ax = axes_list[0]
        ax.clear()
        
        # Plot main ESR data
        if self.settings['laser_tracking']['enabled']:
            # Plot normalized data
            ax.plot(self.frequencies / 1e9, self.data['normalized_avg'], 
                   pen='b', name='Laser-Normalized ESR')
            
            # Plot raw data for comparison
            ax.plot(self.frequencies / 1e9, self.data['esr_avg'], 
                   pen='r', name='Raw ESR')
        else:
            # Plot raw data
            ax.plot(self.frequencies / 1e9, self.data['esr_avg'], 
                   pen='b', name='ESR')
        
        # Plot fit results if available
        if self.data['fit_params']:
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
        
        ax.setLabel('left', 'Fluorescence (counts)')
        ax.setLabel('bottom', 'Frequency (GHz)')
        ax.setTitle('Enhanced ODMR Spectrum (ADwin)')
        ax.showGrid(x=True, y=True)
        
        # Add legend
        ax.addLegend()
    
    def get_axes_layout(self, figure_list: List[str]) -> List[List[str]]:
        """Get the axes layout for plotting."""
        return [[figure_list[0]]]  # Single plot
    
    def get_experiment_info(self) -> Dict[str, Any]:
        """Get experiment information and metadata."""
        return {
            'experiment_type': 'Enhanced ODMR (ADwin)',
            'frequency_range': {
                'start': self.settings['frequency_range']['start'],
                'stop': self.settings['frequency_range']['stop'],
                'points': self.settings['frequency_range']['points'],
                'range_type': self.settings['frequency_range']['range_type']
            },
            'microwave_settings': {
                'power': self.settings['microwave']['power'],
                'modulation_type': self.settings['microwave']['modulation_type'],
                'dev_width': self.settings['microwave']['dev_width'],
                'fm_source': self.settings['microwave']['fm_source'],
                'fm_frequency': self.settings['microwave']['fm_frequency'],
                'fm_amplitude': self.settings['microwave']['fm_amplitude']
            },
            'acquisition_settings': {
                'integration_time': self.settings['acquisition']['integration_time'],
                'settle_time': self.settings['acquisition']['settle_time'],
                'averages': self.settings['acquisition']['averages'],
                'adwin_samples_per_point': self.settings['acquisition']['adwin_samples_per_point']
            },
            'laser_tracking': {
                'enabled': self.settings['laser_tracking']['enabled'],
                'normalize_data': self.settings['laser_tracking']['normalize_data']
            },
            'fit_results': {
                'num_peaks': len(self.data['fit_params']) if self.data['fit_params'] else 0,
                'peaks': self.data['fit_params'] if self.data['fit_params'] else []
            }
        } 