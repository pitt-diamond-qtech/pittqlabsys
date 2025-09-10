"""
ODMR Phase Continuous Sweep Experiment

This experiment performs ODMR measurements using the SG384 phase continuous sweep
functions and the Adwin ODMR_Sweep_Counter for synchronized data collection.

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


class ODMRSweepContinuousExperiment(Experiment):
    """
    ODMR Experiment with Phase Continuous Sweep.
    
    This experiment performs ODMR measurements by:
    1. Configuring SG384 for phase continuous frequency sweep
    2. Using Adwin ODMR_Sweep_Counter for synchronized counting
    3. Collecting data during the sweep for high-speed acquisitionhey 
    
    This approach provides:
    - Fast frequency sweeps with phase continuity
    - Synchronized data collection
    - High temporal resolution
    - Efficient for large frequency ranges
    
    Parameters:
        frequency_range: [start, stop] frequency range in Hz
        power: Microwave power in dBm
        sweep_rate: Sweep rate in Hz/s
        integration_time: Integration time per frequency point
        averages: Number of sweep averages
        
    Returns:
        odmr_spectrum: Fluorescence vs frequency data
        fit_parameters: Fitted parameters for NV center transitions
        resonance_frequencies: Identified resonance frequencies
    """
    
    _DEFAULT_SETTINGS = [
        Parameter('frequency_range', [
            Parameter('start', 2.7e9, float, 'Start frequency in Hz', units='Hz'),
            Parameter('stop', 3.0e9, float, 'Stop frequency in Hz', units='Hz')
        ]),
        Parameter('microwave', [
            Parameter('power', -10.0, float, 'Microwave power in dBm', units='dBm'),
            Parameter('step_freq', 1e6, float, 'Frequency step size in Hz', units='Hz'),
            Parameter('sweep_function', 'Triangle', ['Sine', 'Ramp', 'Triangle', 'Square', 'Noise'], 'Sweep waveform')
        ]),
        Parameter('acquisition', [
            Parameter('integration_time', 0.001, float, 'Integration time per point in seconds', units='s'),
            Parameter('averages', 10, int, 'Number of sweep averages'),
            Parameter('settle_time', 0.01, float, 'Settle time between sweeps', units='s')
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
        Initialize ODMR Phase Continuous Sweep Experiment.
        
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
        self.counts_forward = None
        self.counts_reverse = None
        self.counts_averaged = None
        self.voltages = None
        self.sweep_time = None
        
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
        
        # Setup microwave generator for sweep
        self._setup_microwave_sweep()
        
        # Setup Adwin for sweep counting
        self._setup_adwin_sweep()
        
        # Setup nanodrive if available
        if self.nanodrive:
            self._setup_nanodrive()
        
        # Calculate sweep parameters
        self._calculate_sweep_parameters()
        
        # Initialize data arrays
        self._initialize_data_arrays()
        
        self.log("ODMR Phase Continuous Sweep Experiment setup complete")
    
    def _setup_microwave_sweep(self):
        """Setup the SG384 for frequency sweep."""
        if not self.microwave.is_connected:
            self.microwave.connect()
        
        # Set power
        self.microwave.set_power(self.settings['microwave']['power'])
        
        # Configure sweep parameters using calculated values
        start_freq = self.settings['frequency_range']['start']
        stop_freq = self.settings['frequency_range']['stop']
        center_freq = (start_freq + stop_freq) / 2
        deviation = abs(stop_freq - start_freq) / 2
        
        # Set center frequency
        self.microwave.set_frequency(center_freq)
        
        # Set sweep deviation
        self.microwave.set_sweep_deviation(deviation)
        
        # Set sweep function
        sweep_func = self.settings['microwave']['sweep_function']
        self.microwave.set_sweep_function(sweep_func)
        
        # Set sweep rate using calculated value
        self.microwave.set_sweep_rate(self.sweep_rate)
        
        # Enable sweep mode
        self.microwave.set_modulation_type('Freq sweep')
        self.microwave.enable_modulation()
        
        # Enable output
        self.microwave.enable_output()
        
        self.log(f"Microwave sweep setup: {center_freq/1e9:.3f} GHz ± {deviation/1e6:.1f} MHz")
        self.log(f"Sweep function: {sweep_func}, Rate: {self.sweep_rate/1e6:.2f} MHz/s")
    
    def _setup_adwin_sweep(self):
        """Setup Adwin for sweep-synchronized counting."""
        if not self.adwin.is_connected:
            self.adwin.connect()
        
        # Use existing helper function for sweep ODMR setup
        from src.core.adwin_helpers import setup_adwin_for_sweep_odmr
        
        # Use calculated parameters
        integration_time = self.settings['acquisition']['integration_time']
        settle_time = self.settings['acquisition']['settle_time']
        
        # Setup using helper function
        integration_time_ms = integration_time * 1000
        settle_time_ms = settle_time * 1000
        bidirectional = True  # Enable bidirectional sweeps
        
        setup_adwin_for_sweep_odmr(
            self.adwin, 
            integration_time_ms, 
            settle_time_ms, 
            self.num_steps, 
            bidirectional
        )
        
        # Start the process
        self.adwin.start_process("Process_1")
        
        self.log(f"Adwin sweep setup: {self.num_steps} steps, {integration_time*1e3:.1f} ms per step")
    
    def _setup_nanodrive(self):
        """Setup MCL nanodrive if available."""
        if not self.nanodrive.is_connected:
            self.nanodrive.connect()
        
        # Set to current position (no movement)
        current_pos = self.nanodrive.get_position()
        self.log(f"Nanodrive position: {current_pos}")
    
    def _calculate_sweep_parameters(self):
        """Calculate sweep timing and frequency parameters."""
        start_freq = self.settings['frequency_range']['start']
        stop_freq = self.settings['frequency_range']['stop']
        step_freq = self.settings['microwave']['step_freq']
        integration_time = self.settings['acquisition']['integration_time']
        settle_time = self.settings['acquisition']['settle_time']
        
        # Calculate number of steps based on frequency range and step size
        self.num_steps = int(abs(stop_freq - start_freq) / step_freq)
        
        # Calculate sweep time based on integration time and settle time per step
        time_per_step = integration_time + settle_time
        self.sweep_time = self.num_steps * time_per_step
        
        # Calculate actual sweep rate (Hz/s)
        self.sweep_rate = abs(stop_freq - start_freq) / self.sweep_time
        
        # Generate frequency array
        self.frequencies = np.linspace(start_freq, stop_freq, self.num_steps)
        
        # Log calculation results
        self.log(f"Step frequency: {step_freq/1e6:.2f} MHz")
        self.log(f"Number of steps: {self.num_steps}")
        self.log(f"Time per step: {time_per_step*1e3:.1f} ms")
        self.log(f"Sweep time: {self.sweep_time:.3f} s")
        self.log(f"Calculated sweep rate: {self.sweep_rate/1e6:.2f} MHz/s")
        self.log(f"Frequency range: {start_freq/1e9:.3f} - {stop_freq/1e9:.3f} GHz")
    
    def _initialize_data_arrays(self):
        """Initialize data storage arrays."""
        averages = self.settings['acquisition']['averages']
        
        # Main data arrays
        self.counts_forward = np.zeros(self.num_steps)
        self.counts_reverse = np.zeros(self.num_steps)
        self.counts_averaged = np.zeros(self.num_steps)
        self.voltages = np.zeros(self.num_steps)
        
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
        
        # Disable microwave sweep and output
        if self.microwave and self.microwave.is_connected:
            self.microwave.disable_modulation()
            self.microwave.disable_output()
        
        super().cleanup()
        self.log("ODMR Phase Continuous Sweep Experiment cleanup complete")
    
    def _function(self):
        """Main experiment function."""
        try:
            self.log("Starting ODMR Phase Continuous Sweep Experiment")
            
            # Run multiple sweep averages
            self._run_sweep_averages()
            
            # Analyze the data
            self._analyze_data()
            
            # Store results
            self._store_results_in_data()
            
            self.log("ODMR Phase Continuous Sweep Experiment completed successfully")
            
        except Exception as e:
            self.log(f"Error in ODMR sweep experiment: {e}")
            raise
    
    def _run_sweep_averages(self):
        """Run multiple sweep averages."""
        averages = self.settings['acquisition']['averages']
        settle_time = self.settings['acquisition']['settle_time']
        
        self.log(f"Starting sweep averages: {averages} sweeps")
        
        # Arrays to store individual sweep data
        all_forward = np.zeros((averages, self.num_steps))
        all_reverse = np.zeros((averages, self.num_steps))
        all_voltages = np.zeros((averages, self.num_steps))
        
        for avg in range(averages):
            self.log(f"Running sweep {avg + 1}/{averages}")
            
            # Run single sweep
            forward, reverse, voltages = self._run_single_sweep()
            
            # Store data
            all_forward[avg, :] = forward
            all_reverse[avg, :] = reverse
            all_voltages[avg, :] = voltages
            
            # Settle time between sweeps
            if avg < averages - 1:
                time.sleep(settle_time)
        
        # Average the data
        self.counts_forward = np.mean(all_forward, axis=0)
        self.counts_reverse = np.mean(all_reverse, axis=0)
        self.counts_averaged = (self.counts_forward + self.counts_reverse) / 2
        self.voltages = np.mean(all_voltages, axis=0)
        
        self.log("Sweep averages completed")
    
    def _run_single_sweep(self):
        """Run a single frequency sweep."""
        # Reset Adwin sweep
        self.adwin.clear_process("Process_1")
        self.adwin.start_process("Process_1")
        
        # Start microwave sweep
        # The SG384 will automatically sweep when modulation is enabled
        
        # Wait for sweep to complete using calculated sweep time
        time.sleep(self.sweep_time + 0.1)  # Add small buffer
        
        # Stop the sweep
        self.adwin.stop_process("Process_1")
        
        # Read sweep data from Adwin using helper function
        from src.core.adwin_helpers import read_adwin_sweep_odmr_data
        sweep_data = read_adwin_sweep_odmr_data(self.adwin)
        
        forward_counts = sweep_data['forward_counts']
        reverse_counts = sweep_data['reverse_counts']
        forward_voltages = sweep_data['forward_voltages']
        reverse_voltages = sweep_data['reverse_voltages']
        
        # Convert voltages to frequencies
        # Voltage range is -1V to +1V, corresponding to frequency deviation
        center_freq = (self.settings['frequency_range']['start'] + self.settings['frequency_range']['stop']) / 2
        deviation = abs(self.settings['frequency_range']['stop'] - self.settings['frequency_range']['start']) / 2
        
        forward_freqs = center_freq + forward_voltages * deviation
        reverse_freqs = center_freq + reverse_voltages * deviation
        
        return forward_counts, reverse_counts, forward_freqs
    
    def _analyze_data(self):
        """Analyze the ODMR sweep data."""
        self.log("Analyzing ODMR sweep data...")
        
        # Use averaged data for analysis
        data = self.counts_averaged
        
        # Apply smoothing if enabled
        if self.settings['analysis']['smoothing']:
            data = self._smooth_data(data)
        
        # Subtract background if enabled
        if self.settings['analysis']['background_subtraction']:
            data = self._subtract_background(data)
        
        # Fit resonances if enabled
        if self.settings['analysis']['auto_fit']:
            self._fit_resonances()
        
        self.log("Data analysis completed")
    
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
                self.log("No peaks found for fitting")
                return
            
            # Fit each peak with Lorentzian
            fit_params = []
            for peak_idx in peaks:
                # Define fitting range around peak
                fit_range = 10  # points on each side
                start_idx = max(0, peak_idx - fit_range)
                end_idx = min(len(self.frequencies), peak_idx + fit_range)
                
                x_fit = self.frequencies[start_idx:end_idx]
                y_fit = self.counts_averaged[start_idx:end_idx]
                
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
                    self.log(f"Failed to fit peak at {center/1e9:.3f} GHz: {e}")
            
            self.fit_parameters = fit_params
            self.log(f"Fitted {len(fit_params)} resonances")
            
        except Exception as e:
            self.log(f"Error in resonance fitting: {e}")
    
    def _find_peaks(self) -> List[int]:
        """Find peaks in the ODMR spectrum."""
        # Simple peak finding using local maxima
        peaks = []
        data = self.counts_averaged
        
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
        self.data['counts_forward'] = self.counts_forward
        self.data['counts_reverse'] = self.counts_reverse
        self.data['counts_averaged'] = self.counts_averaged
        self.data['voltages'] = self.voltages
        self.data['sweep_time'] = self.sweep_time
        self.data['num_steps'] = self.num_steps
        self.data['fit_parameters'] = self.fit_parameters
        self.data['resonance_frequencies'] = self.resonance_frequencies
        self.data['settings'] = self.settings
    
    def _plot(self, axes_list: List[pg.PlotItem]):
        """Plot the ODMR sweep data."""
        if len(axes_list) < 1:
            return
        
        # Clear previous plots
        for ax in axes_list:
            ax.clear()
        
        # Plot main ODMR spectrum
        if self.frequencies is not None and self.counts_averaged is not None:
            ax = axes_list[0]
            
            # Plot forward and reverse sweeps
            ax.plot(self.frequencies / 1e9, self.counts_forward, 'b-', linewidth=1, 
                   label='Forward Sweep', alpha=0.7)
            ax.plot(self.frequencies / 1e9, self.counts_reverse, 'g-', linewidth=1, 
                   label='Reverse Sweep', alpha=0.7)
            
            # Plot averaged data
            ax.plot(self.frequencies / 1e9, self.counts_averaged, 'r-', linewidth=2, 
                   label='Averaged Spectrum')
            
            # Plot resonance frequencies if available
            if self.resonance_frequencies:
                for i, freq in enumerate(self.resonance_frequencies):
                    ax.axvline(x=freq/1e9, color='orange', linestyle='--', 
                              label=f'Resonance {i+1}: {freq/1e9:.3f} GHz')
            
            ax.set_xlabel('Frequency (GHz)')
            ax.set_ylabel('Photon Counts')
            ax.set_title('ODMR Phase Continuous Sweep Spectrum')
            ax.legend()
            ax.grid(True)
    
    def _update(self, axes_list: List[pg.PlotItem]):
        """Update the plots with new data."""
        self._plot(axes_list)
    
    def get_axes_layout(self, figure_list: List[str]) -> List[List[str]]:
        """Get the layout of plot axes."""
        return [['odmr_sweep_spectrum']]
    
    def get_experiment_info(self) -> Dict[str, Any]:
        """Get information about the experiment."""
        return {
            'name': 'ODMR Phase Continuous Sweep Experiment',
            'description': 'ODMR with phase continuous frequency sweep using SG384 and synchronized Adwin counting',
            'devices': list(self._DEVICES.keys()),
            'frequency_range': f"{self.settings['frequency_range']['start']/1e9:.3f} - {self.settings['frequency_range']['stop']/1e9:.3f} GHz",
            'step_frequency': f"{self.settings['microwave']['step_freq']/1e6:.2f} MHz",
            'calculated_sweep_rate': f"{self.sweep_rate/1e6:.2f} MHz/s",
            'sweep_time': f"{self.sweep_time:.3f} s",
            'num_steps': self.num_steps,
            'averages': self.settings['acquisition']['averages'],
            'integration_time': f"{self.settings['acquisition']['integration_time']*1e3:.1f} ms"
        } 