"""
ODMR Stepped Frequency Experiment

This experiment performs ODMR measurements by stepping the SG384 frequency
at each point and collecting photon counts using the Adwin Averagable_Trial_Counter.

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

from src.core.experiment import Experiment
from src.core.parameter import Parameter
from src.Controller.sg384 import SG384Generator
from src.Controller.adwin_gold import AdwinGoldDevice
from src.Controller.nanodrive import MCLNanoDrive
from src.core.adwin_helpers import setup_adwin_for_odmr, read_adwin_odmr_data


class ODMRSteppedExperiment(Experiment):
    """
    ODMR Experiment with Stepped Frequency Control.
    
    This experiment performs ODMR measurements by:
    1. Setting SG384 to a specific frequency
    2. Collecting photon counts using Adwin Averagable_Trial_Counter
    3. Stepping to the next frequency
    4. Repeating until the full frequency range is covered
    
    This approach provides precise frequency control and is ideal for:
    - High-resolution frequency scans
    - Frequency-dependent power studies
    - Precise resonance characterization
    
    Parameters:
        frequency_range: [start, stop] frequency range in Hz
        power: Microwave power in dBm
        integration_time: Integration time per frequency point
        averages: Number of averages per frequency point
        settle_time: Settle time after frequency change
        
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
            Parameter('settle_time', 0.01, float, 'Settle time after frequency change', units='s')
        ]),
        Parameter('acquisition', [
            Parameter('integration_time', 0.1, float, 'Integration time per point in seconds', units='s'),
            Parameter('averages', 10, int, 'Number of averages per frequency point'),
            Parameter('cycles_per_average', 10, int, 'Number of cycles per average in Adwin')
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
    
    def __init__(self, devices, experiments=None, name=None, settings=None, 
                 log_function=None, data_path=None):
        """
        Initialize ODMR Stepped Frequency Experiment.
        
        Args:
            devices: Dictionary of available devices
            experiments: Dictionary of available experiments
            name: Experiment name
            settings: Experiment settings
            log_function: Logging function
            data_path: Path for data storage
        """
        super().__init__(name, settings, devices, experiments, log_function, data_path)
        
        # Initialize data storage
        self.frequencies = None
        self.counts = None
        self.counts_raw = None
        self.powers = None
        
        # Initialize analysis results
        self.fit_parameters = None
        self.resonance_frequencies = None
        self.fit_quality = None
        
        # Setup devices
        self.microwave = self.devices.get('microwave')
        self.adwin = self.devices.get('adwin')
        self.nanodrive = self.devices.get('nanodrive')
        
        if not self.microwave:
            raise ValueError("SG384 microwave generator is required")
        if not self.adwin:
            raise ValueError("Adwin device is required")
    
    def setup(self):
        """Setup the experiment and devices."""
        super().setup()
        
        # Setup microwave generator
        self._setup_microwave()
        
        # Setup Adwin for counting
        self._setup_adwin()
        
        # Setup nanodrive if available
        if self.nanodrive:
            self._setup_nanodrive()
        
        # Generate frequency array
        self._generate_frequency_array()
        
        # Initialize data arrays
        self._initialize_data_arrays()
        
        self.logger.info("ODMR Stepped Frequency Experiment setup complete")
    
    def _setup_microwave(self):
        """Setup the SG384 microwave generator."""
        if not self.microwave.is_connected:
            self.microwave.connect()
        
        # Set initial power
        self.microwave.set_power(self.settings['microwave']['power'])
        
        # Enable output
        self.microwave.enable_output()
        
        self.logger.info(f"Microwave generator setup: power={self.settings['microwave']['power']} dBm")
    
    def _setup_adwin(self):
        """Setup Adwin for photon counting."""
        if not self.adwin.is_connected:
            self.adwin.connect()
        
        # Use existing helper function for simple ODMR setup
        from src.core.adwin_helpers import setup_adwin_for_simple_odmr
        
        integration_time_ms = self.settings['acquisition']['integration_time'] * 1000
        setup_adwin_for_simple_odmr(self.adwin, integration_time_ms)
        
        # Start the process
        self.adwin.start_process("Process_1")
        
        self.logger.info(f"Adwin setup: {integration_time_ms:.1f} ms integration time")
    
    def _setup_nanodrive(self):
        """Setup MCL nanodrive if available."""
        if not self.nanodrive.is_connected:
            self.nanodrive.connect()
        
        # Set to current position (no movement)
        current_pos = self.nanodrive.get_position()
        self.logger.info(f"Nanodrive position: {current_pos}")
    
    def _generate_frequency_array(self):
        """Generate the frequency array for the scan."""
        start = self.settings['frequency_range']['start']
        stop = self.settings['frequency_range']['stop']
        steps = self.settings['frequency_range']['steps']
        
        self.frequencies = np.linspace(start, stop, steps)
        self.logger.info(f"Frequency range: {start/1e9:.3f} - {stop/1e9:.3f} GHz ({steps} points)")
    
    def _initialize_data_arrays(self):
        """Initialize data storage arrays."""
        steps = self.settings['frequency_range']['steps']
        averages = self.settings['acquisition']['averages']
        
        # Main data arrays
        self.counts = np.zeros(steps)
        self.counts_raw = np.zeros((steps, averages))
        self.powers = np.zeros(steps)
        
        # Analysis arrays
        self.fit_parameters = None
        self.resonance_frequencies = None
        self.fit_quality = None
    
    def cleanup(self):
        """Cleanup experiment resources."""
        # Stop Adwin process
        if self.adwin and self.adwin.is_connected:
            self.adwin.stop_process("Process_1")
            self.adwin.clear_process("Process_1")
        
        # Disable microwave output
        if self.microwave and self.microwave.is_connected:
            self.microwave.disable_output()
        
        super().cleanup()
        self.logger.info("ODMR Stepped Frequency Experiment cleanup complete")
    
    def _function(self):
        """Main experiment function."""
        try:
            self.logger.info("Starting ODMR Stepped Frequency Experiment")
            
            # Run the frequency scan
            self._run_frequency_scan()
            
            # Analyze the data
            self._analyze_data()
            
            # Store results
            self._store_results_in_data()
            
            self.logger.info("ODMR Stepped Frequency Experiment completed successfully")
            
        except Exception as e:
            self.logger.error(f"Error in ODMR experiment: {e}")
            raise
    
    def _run_frequency_scan(self):
        """Run the frequency scan with photon counting."""
        steps = self.settings['frequency_range']['steps']
        averages = self.settings['acquisition']['averages']
        settle_time = self.settings['microwave']['settle_time']
        
        self.logger.info(f"Starting frequency scan: {steps} points, {averages} averages")
        
        for i, freq in enumerate(self.frequencies):
            # Set microwave frequency
            self.microwave.set_frequency(freq)
            
            # Settle time for frequency change
            time.sleep(settle_time)
            
            # Collect counts for this frequency
            counts_at_freq = []
            for avg in range(averages):
                # Clear and start counting
                self.adwin.clear_process("Process_1")
                self.adwin.start_process("Process_1")
                
                # Wait for integration time
                integration_time = self.settings['acquisition']['integration_time']
                time.sleep(integration_time)
                
                # Stop and read counts
                self.adwin.stop_process("Process_1")
                counts = self.adwin.get_int_var(1)  # Par_1 = counts from Trial_Counter
                counts_at_freq.append(counts)
            
            # Store data
            self.counts_raw[i, :] = counts_at_freq
            self.counts[i] = np.mean(counts_at_freq)
            self.powers[i] = self.microwave.read_probes('power')
            
            # Log progress
            if (i + 1) % 10 == 0 or i == steps - 1:
                self.logger.info(f"Progress: {i+1}/{steps} points completed")
        
        self.logger.info("Frequency scan completed")
    
    def _analyze_data(self):
        """Analyze the ODMR data."""
        self.logger.info("Analyzing ODMR data...")
        
        # Apply smoothing if enabled
        if self.settings['analysis']['smoothing']:
            self.counts = self._smooth_data(self.counts)
        
        # Subtract background if enabled
        if self.settings['analysis']['background_subtraction']:
            self.counts = self._subtract_background(self.counts)
        
        # Fit resonances if enabled
        if self.settings['analysis']['auto_fit']:
            self._fit_resonances()
        
        self.logger.info("Data analysis completed")
    
    def _smooth_data(self, data: np.ndarray) -> np.ndarray:
        """Apply Savitzky-Golay smoothing to the data."""
        window = self.settings['analysis']['smooth_window']
        if len(data) > window:
            return savgol_filter(data, window, 3)
        return data
    
    def _subtract_background(self, data: np.ndarray) -> np.ndarray:
        """Subtract background from the data."""
        # Simple background subtraction using minimum value
        background = np.min(data)
        return data - background
    
    def _fit_resonances(self):
        """Fit Lorentzian functions to identify resonances."""
        try:
            # Find peaks (simple approach - can be enhanced)
            peaks = self._find_peaks()
            
            if len(peaks) == 0:
                self.logger.warning("No peaks found for fitting")
                return
            
            # Fit each peak with Lorentzian
            fit_params = []
            for peak_idx in peaks:
                # Define fitting range around peak
                fit_range = 10  # points on each side
                start_idx = max(0, peak_idx - fit_range)
                end_idx = min(len(self.frequencies), peak_idx + fit_range)
                
                x_fit = self.frequencies[start_idx:end_idx]
                y_fit = self.counts[start_idx:end_idx]
                
                # Initial guess for Lorentzian parameters
                amplitude = np.max(y_fit) - np.min(y_fit)
                center = self.frequencies[peak_idx]
                width = 1e6  # 1 MHz initial guess
                offset = np.min(y_fit)
                
                initial_guess = [amplitude, center, width, offset]
                
                try:
                    # Fit Lorentzian
                    popt, pcov = curve_fit(self._lorentzian_function, x_fit, y_fit, 
                                         p0=initial_guess, maxfev=1000)
                    fit_params.append(popt)
                    
                    # Store resonance frequency
                    if self.resonance_frequencies is None:
                        self.resonance_frequencies = []
                    self.resonance_frequencies.append(popt[1])
                    
                except Exception as e:
                    self.logger.warning(f"Failed to fit peak at {center/1e9:.3f} GHz: {e}")
            
            self.fit_parameters = fit_params
            self.logger.info(f"Fitted {len(fit_params)} resonances")
            
        except Exception as e:
            self.logger.error(f"Error in resonance fitting: {e}")
    
    def _find_peaks(self) -> List[int]:
        """Find peaks in the ODMR spectrum."""
        # Simple peak finding using local maxima
        peaks = []
        data = self.counts
        
        for i in range(1, len(data) - 1):
            if data[i] > data[i-1] and data[i] > data[i+1]:
                # Check if it's significantly above background
                threshold = np.mean(data) + 2 * np.std(data)
                if data[i] > threshold:
                    peaks.append(i)
        
        return peaks
    
    def _lorentzian_function(self, x: np.ndarray, amplitude: float, center: float, 
                            width: float, offset: float) -> np.ndarray:
        """Lorentzian function for fitting."""
        return amplitude * (width/2)**2 / ((x - center)**2 + (width/2)**2) + offset
    
    def _store_results_in_data(self):
        """Store experiment results in the data dictionary."""
        self.data['frequencies'] = self.frequencies
        self.data['counts'] = self.counts
        self.data['counts_raw'] = self.counts_raw
        self.data['powers'] = self.powers
        self.data['fit_parameters'] = self.fit_parameters
        self.data['resonance_frequencies'] = self.resonance_frequencies
        self.data['settings'] = self.settings
    
    def _plot(self, axes_list: List[pg.PlotItem]):
        """Plot the ODMR data."""
        if len(axes_list) < 1:
            return
        
        # Clear previous plots
        for ax in axes_list:
            ax.clear()
        
        # Plot main ODMR spectrum
        if self.frequencies is not None and self.counts is not None:
            ax = axes_list[0]
            ax.plot(self.frequencies / 1e9, self.counts, 'b-', linewidth=2, label='ODMR Spectrum')
            
            # Plot resonance frequencies if available
            if self.resonance_frequencies:
                for i, freq in enumerate(self.resonance_frequencies):
                    ax.axvline(x=freq/1e9, color='r', linestyle='--', 
                              label=f'Resonance {i+1}: {freq/1e9:.3f} GHz')
            
            ax.set_xlabel('Frequency (GHz)')
            ax.set_ylabel('Photon Counts')
            ax.set_title('ODMR Stepped Frequency Spectrum')
            ax.legend()
            ax.grid(True)
    
    def _update(self, axes_list: List[pg.PlotItem]):
        """Update the plots with new data."""
        self._plot(axes_list)
    
    def get_axes_layout(self, figure_list: List[str]) -> List[List[str]]:
        """Get the layout of plot axes."""
        return [['odmr_spectrum']]
    
    def get_experiment_info(self) -> Dict[str, Any]:
        """Get information about the experiment."""
        return {
            'name': 'ODMR Stepped Frequency Experiment',
            'description': 'ODMR with precise frequency stepping using SG384 and Adwin counting',
            'devices': list(self._DEVICES.keys()),
            'frequency_range': f"{self.settings['frequency_range']['start']/1e9:.3f} - {self.settings['frequency_range']['stop']/1e9:.3f} GHz",
            'steps': self.settings['frequency_range']['steps'],
            'averages': self.settings['acquisition']['averages'],
            'integration_time': f"{self.settings['acquisition']['integration_time']} s"
        } 