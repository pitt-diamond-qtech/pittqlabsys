"""
Optically Detected Magnetic Resonance (ODMR) Experiment

This module implements ODMR experiments for nitrogen-vacancy (NV) center characterization.
ODMR is a key technique for NV center quantum sensing and quantum information applications.

DEPRECATED: This legacy experiment does not directly control the SG384 for sweeping and is
superseded by the following experiments which integrate SG384 + ADwin properly:
- `ODMRSteppedExperiment` (precise stepped control)
- `ODMRSweepContinuousExperiment` (phase-continuous sweep)
- `ODMRFMModulationExperiment` (fine, fast FM sweeps)

Please migrate to one of the experiments above. See docs/ODMR_EXPERIMENTS_OVERVIEW.md.

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

from src.core import Experiment, Parameter
from src.Controller import SG384Generator, AdwinGoldDevice, MCLNanoDrive
from src.core.adwin_helpers import setup_adwin_for_odmr, read_adwin_odmr_data, setup_adwin_for_simple_odmr, read_adwin_simple_odmr_data

# Emit a deprecation warning when this module is imported
warnings.warn(
    "src.Model.experiments.odmr_experiment is deprecated. Use ODMRSteppedExperiment, "
    "ODMRSweepContinuousExperiment, or ODMRFMModulationExperiment (see docs/ODMR_EXPERIMENTS_OVERVIEW.md).",
    FutureWarning,
    stacklevel=2,
)


class ODMRExperiment(Experiment):
    """
    Optically Detected Magnetic Resonance (ODMR) Experiment for NV Center Characterization.
    
    This experiment performs ODMR measurements on nitrogen-vacancy centers in diamond.
    It sweeps microwave frequency while monitoring fluorescence intensity to identify
    the NV center's ground state transitions (ms=0 ↔ ms=±1).
    
    The experiment can operate in several modes:
    - Single sweep: One frequency sweep
    - Continuous: Repeated sweeps for monitoring
    - Averaged: Multiple sweeps with averaging
    - 2D scan: ODMR at multiple positions
    
    Parameters:
        frequency_range: [start, stop] frequency range in Hz
        power: Microwave power in dBm
        integration_time: Integration time per frequency point
        laser_power: Laser power for excitation
        magnetic_field: Applied magnetic field (optional)
        
    Returns:
        odmr_spectrum: Fluorescence vs frequency data
        fit_parameters: Fitted parameters for NV center transitions
        resonance_frequencies: Identified resonance frequencies
    """
    
    _DEFAULT_SETTINGS = [
        Parameter('frequency_range', [
            Parameter('start', 2.7e9, float, 'Start frequency in Hz', units='Hz'),
            Parameter('stop', 3.0e9, float, 'Stop frequency in Hz', units='Hz'),
            Parameter('steps', 100, int, 'Number of frequency points')
        ]),
        Parameter('microwave', [
            Parameter('power', -10.0, float, 'Microwave power in dBm', units='dBm'),
            Parameter('modulation', False, bool, 'Enable frequency modulation'),
            Parameter('mod_depth', 1e6, float, 'Modulation depth in Hz', units='Hz'),
            Parameter('mod_freq', 1e3, float, 'Modulation frequency in Hz', units='Hz')
        ]),
        Parameter('acquisition', [
            Parameter('integration_time', 0.1, float, 'Integration time per point in seconds', units='s'),
            Parameter('averages', 1, int, 'Number of sweeps to average'),
            Parameter('settle_time', 0.01, float, 'Settle time after frequency change', units='s')
        ]),
        Parameter('laser', [
            Parameter('power', 1.0, float, 'Laser power in mW', units='mW'),
            Parameter('wavelength', 532.0, float, 'Laser wavelength in nm', units='nm')
        ]),
        Parameter('magnetic_field', [
            Parameter('enabled', False, bool, 'Enable magnetic field'),
            Parameter('strength', 0.0, float, 'Magnetic field strength in Gauss', units='G'),
            Parameter('direction', [0.0, 0.0, 1.0], list, 'Magnetic field direction [x, y, z]')
        ]),
        Parameter('scan_mode', 'single', ['single', 'continuous', 'averaged', '2d_scan'], 
                 'ODMR scan mode'),
        Parameter('2d_scan_settings', [
            Parameter('x_range', [0.0, 10.0], list, 'X scan range in microns', units='μm'),
            Parameter('y_range', [0.0, 10.0], list, 'Y scan range in microns', units='μm'),
            Parameter('x_steps', 10, int, 'Number of X positions'),
            Parameter('y_steps', 10, int, 'Number of Y positions')
        ]),
        Parameter('analysis', [
            Parameter('auto_fit', True, bool, 'Automatically fit resonances'),
            Parameter('smoothing', True, bool, 'Apply smoothing to data'),
            Parameter('smooth_window', 5, int, 'Smoothing window size'),
            Parameter('background_subtraction', True, bool, 'Subtract background')
        ])
    ]
    
    _DEVICES = {
        'microwave': 'sg384',
        'adwin': 'adwin',
        'nanodrive': 'nanodrive'
    }
    
    _EXPERIMENTS = {}
    
    def __init__(self, devices: Dict[str, Any], experiments: Optional[Dict[str, Any]] = None,
                 name: Optional[str] = None, settings: Optional[Dict[str, Any]] = None,
                 log_function=None, data_path: Optional[str] = None):
        """
        Initialize the ODMR experiment.
        
        Args:
            devices: Dictionary of device instances
            experiments: Dictionary of sub-experiment instances
            name: Optional experiment name
            settings: Optional initial settings
            log_function: Optional logging function
            data_path: Optional data storage path
        """
        super().__init__(name, settings, devices, experiments, log_function, data_path)
        
        # Store device references
        self.microwave = self.devices['microwave']['instance']
        self.adwin = self.devices['adwin']['instance']
        self.nanodrive = self.devices['nanodrive']['instance']
        
        # Initialize experiment data
        self.frequencies = None
        self.fluorescence_data = None
        self.fit_parameters = None
        self.resonance_frequencies = None
        self.background_level = None
        
        # NV center parameters (typical values)
        self.nv_zero_field_splitting = 2.87e9  # Hz
        self.nv_gyromagnetic_ratio = 2.8e6  # Hz/Gauss
        
    def setup(self):
        """Setup experiment before execution."""
        self.log("Setting up ODMR experiment...")
        
        # Generate frequency array
        start_freq = self.settings['frequency_range']['start']
        stop_freq = self.settings['frequency_range']['stop']
        steps = self.settings['frequency_range']['steps']
        self.frequencies = np.linspace(start_freq, stop_freq, steps)
        
        # Initialize data arrays
        if self.settings['scan_mode'] == '2d_scan':
            x_steps = self.settings['2d_scan_settings']['x_steps']
            y_steps = self.settings['2d_scan_settings']['y_steps']
            self.fluorescence_data = np.zeros((y_steps, x_steps, steps))
        else:
            self.fluorescence_data = np.zeros(steps)
        
        # Configure microwave generator
        self.microwave.update({
            'frequency': self.frequencies[0],
            'amplitude': self.settings['microwave']['power'],
            'enable_output': False
        })
        
        # Configure modulation if enabled
        if self.settings['microwave']['modulation']:
            self.microwave.update({
                'enable_modulation': True,
                'modulation_type': 'FM',
                'dev_width': self.settings['microwave']['mod_depth'],
                'mod_rate': self.settings['microwave']['mod_freq']
            })
        
        # Configure ADwin for photon counting
        self._setup_adwin()
        
        # Start ADwin process
        self.adwin.start_process(2)
        time.sleep(0.1)  # Allow process to start
        
        # Move to scan position if 2D scan
        if self.settings['scan_mode'] == '2d_scan':
            self._setup_2d_scan()
        
        self.log("ODMR experiment setup complete")
        
    def _setup_adwin(self):
        """Configure ADwin for photon counting."""
        self.log("Configuring ADwin for photon counting...")
        
        # Convert integration time from seconds to milliseconds
        integration_time_ms = self.settings['acquisition']['integration_time'] * 1000.0
        
        # Setup ADwin for simple ODMR using Trial_Counter.TB1 (which exists)
        # instead of ODMR_FM_Laser_Tracker.TB2 (which doesn't exist)
        setup_adwin_for_simple_odmr(
            self.adwin,
            integration_time_ms=integration_time_ms
        )
        
    def _setup_2d_scan(self):
        """Setup 2D scan parameters."""
        x_start = self.settings['2d_scan_settings']['x_range'][0]
        y_start = self.settings['2d_scan_settings']['y_range'][0]
        
        # Move to starting position
        self.nanodrive.update({
            'x_pos': x_start,
            'y_pos': y_start
        })
        
    def cleanup(self):
        """Cleanup after experiment execution."""
        self.log("Cleaning up ODMR experiment...")
        
        # Turn off microwave
        self.microwave.update({'enable_output': False})
        
        # Stop ADwin acquisition
        self.adwin.stop_process(2)
        
        # Move to safe position if 2D scan
        if self.settings['scan_mode'] == '2d_scan':
            self.nanodrive.update({
                'x_pos': 0.0,
                'y_pos': 0.0
            })
        
    def _function(self):
        """Main ODMR experiment execution."""
        self.log("Starting ODMR experiment...")
        
        try:
            self.setup()
            
            if self.settings['scan_mode'] == 'single':
                self._run_single_sweep()
            elif self.settings['scan_mode'] == 'continuous':
                self._run_continuous_sweeps()
            elif self.settings['scan_mode'] == 'averaged':
                self._run_averaged_sweeps()
            elif self.settings['scan_mode'] == '2d_scan':
                self._run_2d_scan()
            
            # Analyze data
            self._analyze_data()
            
            self.cleanup()
            self.log("ODMR experiment completed successfully")
            
        except Exception as e:
            self.log(f"ODMR experiment failed: {e}")
            self.cleanup()
            raise
    
    def _run_single_sweep(self):
        """Run a single ODMR frequency sweep."""
        self.log("Running single ODMR sweep...")
        
        # Enable microwave output
        self.microwave.update({'enable_output': True})
        
        # Sweep through frequencies
        for i, freq in enumerate(self.frequencies):
            if self._abort:
                break
                
            # Set frequency
            self.microwave.update({'frequency': freq})
            
            # Settle time
            time.sleep(self.settings['acquisition']['settle_time'])
            
            # Acquire data
            counts = self._acquire_counts()
            self.fluorescence_data[i] = counts
            
            # Update progress
            progress = int(100 * i / len(self.frequencies))
            self.updateProgress.emit(progress)
            
            # Real-time plotting
            if i % 10 == 0:
                self._update_plots()
        
        # Disable microwave
        self.microwave.update({'enable_output': False})
    
    def _run_continuous_sweeps(self):
        """Run continuous ODMR sweeps."""
        self.log("Running continuous ODMR sweeps...")
        
        sweep_count = 0
        while not self._abort:
            self.log(f"Starting sweep {sweep_count + 1}")
            
            # Run single sweep
            self._run_single_sweep()
            
            if self._abort:
                break
                
            sweep_count += 1
            
            # Brief pause between sweeps
            time.sleep(1.0)
    
    def _run_averaged_sweeps(self):
        """Run averaged ODMR sweeps."""
        self.log("Running averaged ODMR sweeps...")
        
        averages = self.settings['acquisition']['averages']
        accumulated_data = np.zeros(len(self.frequencies))
        
        for avg in range(averages):
            if self._abort:
                break
                
            self.log(f"Running average {avg + 1}/{averages}")
            
            # Run single sweep
            self._run_single_sweep()
            
            # Accumulate data
            accumulated_data += self.fluorescence_data
            
            # Update progress
            progress = int(100 * (avg + 1) / averages)
            self.updateProgress.emit(progress)
        
        # Calculate average
        if averages > 0:
            self.fluorescence_data = accumulated_data / averages
    
    def _run_2d_scan(self):
        """Run 2D ODMR scan."""
        self.log("Running 2D ODMR scan...")
        
        x_start, x_stop = self.settings['2d_scan_settings']['x_range']
        y_start, y_stop = self.settings['2d_scan_settings']['y_range']
        x_steps = self.settings['2d_scan_settings']['x_steps']
        y_steps = self.settings['2d_scan_settings']['y_steps']
        
        x_positions = np.linspace(x_start, x_stop, x_steps)
        y_positions = np.linspace(y_start, y_stop, y_steps)
        
        total_positions = x_steps * y_steps
        position_count = 0
        
        for i, y_pos in enumerate(y_positions):
            self.nanodrive.update({'y_pos': y_pos})
            
            for j, x_pos in enumerate(x_positions):
                if self._abort:
                    break
                    
                self.nanodrive.update({'x_pos': x_pos})
                
                # Run ODMR sweep at this position
                self._run_single_sweep()
                
                # Store data
                self.fluorescence_data[i, j, :] = self.fluorescence_data.copy()
                
                position_count += 1
                progress = int(100 * position_count / total_positions)
                self.updateProgress.emit(progress)
    
    def _acquire_counts(self) -> float:
        """Acquire photon counts from ADwin."""
        # Read data from ADwin using simple helper function
        counts = read_adwin_simple_odmr_data(self.adwin)
        
        # Return the counts
        return counts
    
    def _update_plots(self):
        """Update plots during experiment execution."""
        # This is a simple wrapper for the base class _update_plot method
        # For now, we'll just pass an empty list since we're not using GUI plots
        pass
    
    def _analyze_data(self):
        """Analyze ODMR data and fit resonances."""
        self.log("Analyzing ODMR data...")
        
        if self.settings['analysis']['smoothing']:
            self._smooth_data()
        
        if self.settings['analysis']['background_subtraction']:
            self._subtract_background()
        
        if self.settings['analysis']['auto_fit']:
            self._fit_resonances()
        
        # Store results in standard data dictionary for compatibility
        self._store_results_in_data()
    
    def _store_results_in_data(self):
        """Store experiment results in the standard data dictionary."""
        if hasattr(self, 'fluorescence_data') and self.fluorescence_data is not None:
            # Store the main ODMR spectrum
            self.data['odmr_spectrum'] = self.fluorescence_data
            
            # Store frequency array
            if hasattr(self, 'frequencies'):
                self.data['frequencies'] = self.frequencies
            
            # Store fit parameters if available
            if hasattr(self, 'fit_parameters') and self.fit_parameters is not None:
                self.data['fit_parameters'] = self.fit_parameters
            
            # Store 2D scan data if available
            if self.settings['scan_mode'] == '2d_scan' and hasattr(self, 'fluorescence_data'):
                if len(self.fluorescence_data.shape) == 3:  # 2D scan with frequency dimension
                    self.data['2d_scan_data'] = self.fluorescence_data
    
    def _smooth_data(self):
        """Apply smoothing to the data."""
        window = self.settings['analysis']['smooth_window']
        if window > 1:
            if self.settings['scan_mode'] == '2d_scan':
                for i in range(self.fluorescence_data.shape[0]):
                    for j in range(self.fluorescence_data.shape[1]):
                        self.fluorescence_data[i, j, :] = savgol_filter(
                            self.fluorescence_data[i, j, :], window, 2)
            else:
                self.fluorescence_data = savgol_filter(self.fluorescence_data, window, 2)
    
    def _subtract_background(self):
        """Subtract background from data."""
        if self.settings['scan_mode'] == '2d_scan':
            # For 2D scan, subtract background from each spectrum
            for i in range(self.fluorescence_data.shape[0]):
                for j in range(self.fluorescence_data.shape[1]):
                    spectrum = self.fluorescence_data[i, j, :]
                    background = np.percentile(spectrum, 90)  # Use 90th percentile as background
                    self.fluorescence_data[i, j, :] = spectrum - background
        else:
            # For 1D scan
            background = np.percentile(self.fluorescence_data, 90)
            self.background_level = background
            self.fluorescence_data = self.fluorescence_data - background
    
    def _fit_resonances(self):
        """Fit resonance peaks in the ODMR spectrum."""
        if self.settings['scan_mode'] == '2d_scan':
            # For 2D scan, fit each spectrum
            self.fit_parameters = np.zeros((self.fluorescence_data.shape[0], 
                                          self.fluorescence_data.shape[1], 6))
            for i in range(self.fluorescence_data.shape[0]):
                for j in range(self.fluorescence_data.shape[1]):
                    params = self._fit_single_spectrum(self.fluorescence_data[i, j, :])
                    self.fit_parameters[i, j, :] = params
        else:
            # For 1D scan
            self.fit_parameters = self._fit_single_spectrum(self.fluorescence_data)
    
    def _fit_single_spectrum(self, spectrum: np.ndarray) -> np.ndarray:
        """Fit a single ODMR spectrum."""
        # Define Lorentzian function for fitting
        def lorentzian(x, amplitude, center, width, offset):
            return amplitude * width**2 / ((x - center)**2 + width**2) + offset
        
        # Initial guess for parameters
        min_idx = np.argmin(spectrum)
        center_guess = self.frequencies[min_idx]
        amplitude_guess = np.max(spectrum) - np.min(spectrum)
        width_guess = 1e6  # 1 MHz
        offset_guess = np.min(spectrum)
        
        try:
            # Fit the spectrum
            popt, _ = curve_fit(lorentzian, self.frequencies, spectrum,
                              p0=[amplitude_guess, center_guess, width_guess, offset_guess],
                              bounds=([0, 2.5e9, 1e5, 0], 
                                    [np.inf, 3.5e9, 1e8, np.inf]))
            return popt
        except:
            # Return default parameters if fitting fails
            return np.array([amplitude_guess, center_guess, width_guess, offset_guess])
    
    def _plot(self, axes_list: List[pg.PlotItem]):
        """Create initial ODMR plots."""
        if self.fluorescence_data is None:
            return
        
        # Clear existing plots
        for ax in axes_list:
            ax.clear()
        
        if self.settings['scan_mode'] == '2d_scan':
            self._plot_2d_data(axes_list)
        else:
            self._plot_1d_data(axes_list)
    
    def _plot_1d_data(self, axes_list: List[pg.PlotItem]):
        """Plot 1D ODMR data."""
        if len(axes_list) >= 1:
            # Main ODMR spectrum
            ax1 = axes_list[0]
            ax1.plot(self.frequencies / 1e9, self.fluorescence_data, 
                    pen='b', symbol='o', symbolSize=5)
            ax1.setLabel('left', 'Fluorescence', units='counts')
            ax1.setLabel('bottom', 'Frequency', units='GHz')
            ax1.setTitle('ODMR Spectrum')
            ax1.showGrid(x=True, y=True)
            
            # Add fit if available
            if self.fit_parameters is not None:
                fit_freq = np.linspace(self.frequencies[0], self.frequencies[-1], 1000)
                fit_data = self._lorentzian_fit(fit_freq, self.fit_parameters)
                ax1.plot(fit_freq / 1e9, fit_data, pen='r', width=2)
        
        if len(axes_list) >= 2 and self.fit_parameters is not None:
            # Resonance parameters
            ax2 = axes_list[1]
            if len(self.fit_parameters.shape) == 1:
                # Single spectrum
                center = self.fit_parameters[1] / 1e9
                width = self.fit_parameters[2] / 1e6
                ax2.plot([center], [width], 'ro', symbolSize=10)
            ax2.setLabel('left', 'Linewidth', units='MHz')
            ax2.setLabel('bottom', 'Resonance Frequency', units='GHz')
            ax2.setTitle('Resonance Parameters')
            ax2.showGrid(x=True, y=True)
    
    def _plot_2d_data(self, axes_list: List[pg.PlotItem]):
        """Plot 2D ODMR data."""
        if len(axes_list) >= 1:
            # 2D fluorescence map at resonance frequency
            ax1 = axes_list[0]
            
            # Find resonance frequency
            if self.fit_parameters is not None:
                # Use fitted resonance frequency
                res_freq_idx = np.argmin(np.abs(self.frequencies - self.nv_zero_field_splitting))
            else:
                # Use zero-field splitting
                res_freq_idx = np.argmin(np.abs(self.frequencies - self.nv_zero_field_splitting))
            
            fluorescence_map = self.fluorescence_data[:, :, res_freq_idx]
            
            # Create image
            img = pg.ImageItem(fluorescence_map)
            ax1.addItem(img)
            ax1.setLabel('left', 'Y Position', units='μm')
            ax1.setLabel('bottom', 'X Position', units='μm')
            ax1.setTitle('Fluorescence Map at Resonance')
            
            # Add colorbar
            bar = pg.ColorBarItem(values=(0, np.max(fluorescence_map)), 
                                colorMap='viridis')
            bar.setImageItem(img)
    
    def _update(self, axes_list: List[pg.PlotItem]):
        """Update existing plots with new data."""
        self._plot(axes_list)
    
    def _lorentzian_fit(self, x: np.ndarray, params: np.ndarray) -> np.ndarray:
        """Calculate Lorentzian fit."""
        amplitude, center, width, offset = params
        return amplitude * width**2 / ((x - center)**2 + width**2) + offset
    
    def get_axes_layout(self, figure_list: List[str]) -> List[List[str]]:
        """Define the layout of plots for this experiment."""
        if self.settings['scan_mode'] == '2d_scan':
            return [
                ['2D Fluorescence Map'],  # Single plot in first figure
                ['Resonance Parameters']  # Single plot in second figure
            ]
        else:
            return [
                ['ODMR Spectrum'],  # Single plot in first figure
                ['Resonance Parameters']  # Single plot in second figure
            ]
    
    def get_experiment_info(self) -> Dict[str, Any]:
        """Get experiment information for documentation."""
        info = {
            'experiment_type': 'ODMR',
            'scan_mode': self.settings['scan_mode'],
            'frequency_range': f"{self.settings['frequency_range']['start']/1e9:.2f}-{self.settings['frequency_range']['stop']/1e9:.2f} GHz",
            'microwave_power': f"{self.settings['microwave']['power']} dBm",
            'integration_time': f"{self.settings['acquisition']['integration_time']} s",
            'averages': self.settings['acquisition']['averages']
        }
        
        if self.settings['magnetic_field']['enabled']:
            info['magnetic_field'] = f"{self.settings['magnetic_field']['strength']} G"
        
        return info


class ODMRRabiExperiment(Experiment):
    """
    ODMR Rabi Oscillation Experiment.
    
    This experiment measures Rabi oscillations at the NV center resonance
    to determine the microwave driving strength and coherence time.
    """
    
    _DEFAULT_SETTINGS = [
        Parameter('rabi_settings', [
            Parameter('frequency', 2.87e9, float, 'Microwave frequency in Hz', units='Hz'),
            Parameter('power', -10.0, float, 'Microwave power in dBm', units='dBm'),
            Parameter('pulse_duration_range', [0.0, 1e-6], list, 'Pulse duration range in seconds', units='s'),
            Parameter('pulse_steps', 50, int, 'Number of pulse duration points')
        ]),
        Parameter('sequence', [
            Parameter('laser_duration', 1e-6, float, 'Laser pulse duration', units='s'),
            Parameter('readout_duration', 1e-6, float, 'Readout duration', units='s'),
            Parameter('repetition_rate', 1e3, float, 'Sequence repetition rate', units='Hz')
        ]),
        Parameter('acquisition', [
            Parameter('averages', 1000, int, 'Number of averages per point'),
            Parameter('integration_time', 1e-3, float, 'Integration time per point', units='s')
        ])
    ]
    
    _DEVICES = {
        'microwave': 'sg384',
        'adwin': 'adwin',
        'pulse_blaster': 'pulse_blaster'
    }
    
    _EXPERIMENTS = {}
    
    def __init__(self, devices, experiments=None, name=None, settings=None, 
                 log_function=None, data_path=None):
        super().__init__(name, settings, devices, experiments, log_function, data_path)
        
        # Store device references
        self.microwave = self.devices['microwave']['instance']
        self.adwin = self.devices['adwin']['instance']
        
        # Initialize data
        self.pulse_durations = None
        self.rabi_data = None
        self.rabi_frequency = None
        self.pi_pulse_duration = None
    
    def _function(self):
        """Execute Rabi oscillation experiment."""
        self.log("Starting Rabi oscillation experiment...")
        
        # Generate pulse duration array
        start_dur = self.settings['rabi_settings']['pulse_duration_range'][0]
        stop_dur = self.settings['rabi_settings']['pulse_duration_range'][1]
        steps = self.settings['rabi_settings']['pulse_steps']
        self.pulse_durations = np.linspace(start_dur, stop_dur, steps)
        
        # Initialize data array
        self.rabi_data = np.zeros(steps)
        
        # Configure microwave
        self.microwave.update({
            'frequency': self.settings['rabi_settings']['frequency'],
            'amplitude': self.settings['rabi_settings']['power'],
            'enable_output': False
        })
        
        # Run Rabi measurement
        for i, pulse_duration in enumerate(self.pulse_durations):
            if self._abort:
                break
                
            # Set pulse duration
            # This would interface with your pulse blaster
            # self.pulse_blaster.set_pulse_duration(pulse_duration)
            
            # Run sequence and acquire data
            counts = self._run_rabi_sequence(pulse_duration)
            self.rabi_data[i] = counts
            
            # Update progress
            progress = int(100 * i / steps)
            self.updateProgress.emit(progress)
        
        # Analyze data
        self._fit_rabi_oscillations()
        
        self.log("Rabi oscillation experiment completed")
    
    def _run_rabi_sequence(self, pulse_duration: float) -> float:
        """Run a single Rabi sequence."""
        # This would implement the actual pulse sequence
        # For now, return simulated data
        
        # Simulate Rabi oscillations
        rabi_freq = 1e6  # 1 MHz Rabi frequency
        contrast = 0.3
        offset = 1000
        
        oscillation = contrast * np.cos(2 * np.pi * rabi_freq * pulse_duration)
        counts = offset * (1 + oscillation) + np.random.normal(0, 50)
        
        return counts
    
    def _fit_rabi_oscillations(self):
        """Fit Rabi oscillations to extract parameters."""
        def rabi_function(t, amplitude, frequency, phase, offset):
            return amplitude * np.cos(2 * np.pi * frequency * t + phase) + offset
        
        try:
            popt, _ = curve_fit(rabi_function, self.pulse_durations, self.rabi_data,
                              p0=[np.max(self.rabi_data) - np.min(self.rabi_data), 
                                  1e6, 0, np.mean(self.rabi_data)])
            
            self.rabi_frequency = popt[1]
            self.pi_pulse_duration = 1 / (2 * self.rabi_frequency)
            
        except:
            self.log("Rabi fitting failed")
    
    def _plot(self, axes_list: List[pg.PlotItem]):
        """Plot Rabi oscillation data."""
        if self.rabi_data is None:
            return
        
        if len(axes_list) >= 1:
            ax = axes_list[0]
            ax.clear()
            
            # Plot data
            ax.plot(self.pulse_durations * 1e6, self.rabi_data, 
                   pen='b', symbol='o', symbolSize=5)
            ax.setLabel('left', 'Fluorescence', units='counts')
            ax.setLabel('bottom', 'Pulse Duration', units='μs')
            ax.setTitle('Rabi Oscillations')
            ax.showGrid(x=True, y=True)
            
            # Add fit if available
            if self.rabi_frequency is not None:
                fit_t = np.linspace(self.pulse_durations[0], self.pulse_durations[-1], 1000)
                fit_data = self._rabi_fit(fit_t)
                ax.plot(fit_t * 1e6, fit_data, pen='r', width=2)
    
    def _rabi_fit(self, t: np.ndarray) -> np.ndarray:
        """Calculate Rabi fit."""
        amplitude = np.max(self.rabi_data) - np.min(self.rabi_data)
        offset = np.mean(self.rabi_data)
        return amplitude * np.cos(2 * np.pi * self.rabi_frequency * t) + offset
    
    def get_axes_layout(self, figure_list: List[str]) -> List[List[str]]:
        """Define plot layout."""
        return [['Rabi Oscillations']] 