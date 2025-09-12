"""
ODMR Frequency Modulation Experiment

This experiment performs ODMR measurements using the SG384 frequency modulation
for fine frequency sweeps and high-speed acquisition with the ODMR_Sweep_Counter.

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
from src.Controller import SG384Generator, AdwinGoldDevice, MCLNanoDrive
from src.core.adwin_helpers import setup_adwin_for_odmr, read_adwin_odmr_data


class ODMRFMModulationExperiment(Experiment):
    """
    ODMR Experiment with Frequency Modulation.
    
    This experiment performs ODMR measurements by:
    1. Setting SG384 to a center frequency
    2. Enabling frequency modulation with specified depth and rate
    3. Using Adwin ODMR_Sweep_Counter for synchronized counting
    4. Collecting data during the modulation cycle
    
    This approach provides:
    - High-speed fine frequency sweeps
    - Precise frequency control around a center frequency
    - Fast data acquisition for dynamic measurements
    - Ideal for small frequency ranges and high temporal resolution
    
    Parameters:
        center_frequency: Center frequency in Hz
        modulation_depth: Frequency modulation depth in Hz
        modulation_rate: Modulation rate in Hz
        power: Microwave power in dBm
        integration_time: Integration time per modulation cycle
        averages: Number of modulation cycle averages
        
    Returns:
        odmr_spectrum: Fluorescence vs frequency data
        fit_parameters: Fitted parameters for NV center transitions
        resonance_frequencies: Identified resonance frequencies
    """
    
    _DEFAULT_SETTINGS = [
        Parameter('frequency', [
            Parameter('center', 2.87e9, float, 'Center frequency in Hz', units='Hz'),
            Parameter('modulation_depth', 10e6, float, 'Frequency modulation depth in Hz', units='Hz'),
            Parameter('modulation_rate', 1e3, float, 'Modulation rate in Hz', units='Hz')
        ]),
        Parameter('microwave', [
            Parameter('power', -10.0, float, 'Microwave power in dBm', units='dBm'),
            Parameter('modulation_function', 'Sine', ['Sine', 'Ramp', 'Triangle', 'Square', 'Noise'], 'Modulation waveform')
        ]),
        Parameter('acquisition', [
            Parameter('integration_time', 0.001, float, 'Integration time per cycle in seconds', units='s'),
            Parameter('averages', 100, int, 'Number of modulation cycle averages'),
            Parameter('cycles_per_average', 10, int, 'Number of cycles per average in Adwin'),
            Parameter('settle_time', 0.001, float, 'Settle time between averages', units='s')
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
            Parameter('background_subtraction', True, bool, 'Subtract background'),
            Parameter('lock_in_detection', True, bool, 'Use lock-in detection for improved SNR')
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
        Initialize ODMR Frequency Modulation Experiment.
        
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
        self.modulation_phase = None
        self.powers = None
        
        # Initialize analysis results
        self.fit_parameters = None
        self.resonance_frequencies = None
        self.fit_quality = None
        self.lock_in_signal = None
        
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
        
        # Setup microwave generator for frequency modulation
        self._setup_microwave_fm()
        
        # Setup Adwin for modulation counting
        self._setup_adwin_fm()
        
        # Setup nanodrive if available
        if self.nanodrive:
            self._setup_nanodrive()
        
        # Calculate modulation parameters
        self._calculate_modulation_parameters()
        
        # Initialize data arrays
        self._initialize_data_arrays()
        
        self.logger.info("ODMR Frequency Modulation Experiment setup complete")
    
    def _setup_microwave_fm(self):
        """Setup the SG384 for frequency modulation."""
        if not self.microwave.is_connected:
            self.microwave.connect()
        
        # Set center frequency
        center_freq = self.settings['frequency']['center']
        self.microwave.set_frequency(center_freq)
        
        # Set power
        self.microwave.set_power(self.settings['microwave']['power'])
        
        # Configure frequency modulation
        mod_depth = self.settings['frequency']['modulation_depth']
        mod_rate = self.settings['frequency']['modulation_rate']
        mod_func = self.settings['microwave']['modulation_function']
        
        # Set modulation depth (frequency deviation)
        self.microwave.set_modulation_depth(mod_depth)
        
        # Set modulation rate
        self.microwave.set_modulation_rate(mod_rate)
        
        # Set modulation function
        self.microwave.set_modulation_function(mod_func)
        
        # Enable frequency modulation
        self.microwave.set_modulation_type('FM')
        self.microwave.enable_modulation()
        
        # Enable output
        self.microwave.enable_output()
        
        self.logger.info(f"Microwave FM setup: {center_freq/1e9:.3f} GHz ± {mod_depth/1e6:.1f} MHz")
        self.logger.info(f"Modulation: {mod_func} at {mod_rate/1e3:.1f} kHz")
    
    def _setup_adwin_fm(self):
        """Setup Adwin for frequency modulation counting."""
        if not self.adwin.is_connected:
            self.adwin.connect()
        
        # Use new helper function specifically for FM ODMR
        from src.core.adwin_helpers import setup_adwin_for_fm_odmr
        
        # Calculate parameters for FM counting
        mod_rate = self.settings['frequency']['modulation_rate']
        integration_time = self.settings['acquisition']['integration_time']
        cycles_per_avg = self.settings['acquisition']['cycles_per_average']
        
        # Setup using FM-specific helper function
        integration_time_ms = integration_time * 1000
        
        setup_adwin_for_fm_odmr(
            self.adwin, 
            integration_time_ms, 
            cycles_per_avg, 
            mod_rate
        )
        
        # Start the process
        self.adwin.start_process("Process_1")
        
        self.logger.info(f"Adwin FM setup: {total_points} points, {points_per_cycle} per cycle")
        self.logger.info(f"Integration: {integration_time*1e3:.1f} ms, Cycles: {cycles_per_avg}")
    
    def _setup_nanodrive(self):
        """Setup MCL nanodrive if available."""
        if not self.nanodrive.is_connected:
            self.nanodrive.connect()
        
        # Set to current position (no movement)
        current_pos = self.nanodrive.get_position()
        self.logger.info(f"Nanodrive position: {current_pos}")
    
    def _calculate_modulation_parameters(self):
        """Calculate modulation timing and frequency parameters."""
        center_freq = self.settings['frequency']['center']
        mod_depth = self.settings['frequency']['modulation_depth']
        mod_rate = self.settings['frequency']['modulation_rate']
        integration_time = self.settings['acquisition']['integration_time']
        cycles_per_avg = self.settings['acquisition']['cycles_per_average']
        
        # Calculate frequency range
        start_freq = center_freq - mod_depth
        stop_freq = center_freq + mod_depth
        
        # Calculate timing
        cycle_time = 1.0 / mod_rate
        points_per_cycle = int(cycle_time / integration_time)
        total_points = points_per_cycle * cycles_per_avg
        
        # Generate frequency array for one modulation cycle
        self.frequencies = np.linspace(start_freq, stop_freq, points_per_cycle)
        self.modulation_phase = np.linspace(0, 2*np.pi, points_per_cycle)
        
        # Store parameters
        self.cycle_time = cycle_time
        self.points_per_cycle = points_per_cycle
        self.total_points = total_points
        
        self.logger.info(f"FM parameters: {start_freq/1e9:.3f} - {stop_freq/1e9:.3f} GHz")
        self.logger.info(f"Cycle time: {cycle_time*1e3:.1f} ms, Points per cycle: {points_per_cycle}")
    
    def _initialize_data_arrays(self):
        """Initialize data storage arrays."""
        points_per_cycle = self.points_per_cycle
        averages = self.settings['acquisition']['averages']
        
        # Main data arrays
        self.counts = np.zeros(points_per_cycle)
        self.counts_raw = np.zeros((points_per_cycle, averages))
        self.powers = np.zeros(points_per_cycle)
        
        # Analysis arrays
        self.fit_parameters = None
        self.resonance_frequencies = None
        self.fit_quality = None
        self.lock_in_signal = None
    
    def cleanup(self):
        """Cleanup experiment resources."""
        # Stop Adwin process
        if self.adwin and self.adwin.is_connected:
            self.adwin.stop_process("Process_1")
            self.adwin.clear_process("Process_1")
        
        # Disable microwave modulation and output
        if self.microwave and self.microwave.is_connected:
            self.microwave.disable_modulation()
            self.microwave.disable_output()
        
        super().cleanup()
        self.logger.info("ODMR Frequency Modulation Experiment cleanup complete")
    
    def _function(self):
        """Main experiment function."""
        try:
            self.logger.info("Starting ODMR Frequency Modulation Experiment")
            
            # Run multiple modulation cycle averages
            self._run_modulation_averages()
            
            # Analyze the data
            self._analyze_data()
            
            # Store results
            self._store_results_in_data()
            
            self.logger.info("ODMR Frequency Modulation Experiment completed successfully")
            
        except Exception as e:
            self.logger.error(f"Error in ODMR FM experiment: {e}")
            raise
    
    def _run_modulation_averages(self):
        """Run multiple modulation cycle averages."""
        averages = self.settings['acquisition']['averages']
        settle_time = self.settings['acquisition']['settle_time']
        
        self.logger.info(f"Starting modulation averages: {averages} averages")
        
        # Arrays to store individual cycle data
        all_counts = np.zeros((averages, self.points_per_cycle))
        all_powers = np.zeros((averages, self.points_per_cycle))
        
        for avg in range(averages):
            self.logger.info(f"Running average {avg + 1}/{averages}")
            
            # Run single modulation cycle
            counts, powers = self._run_single_modulation_cycle()
            
            # Store data
            all_counts[avg, :] = counts
            all_powers[avg, :] = powers
            
            # Settle time between averages
            if avg < averages - 1:
                time.sleep(settle_time)
        
        # Average the data
        self.counts = np.mean(all_counts, axis=0)
        self.counts_raw = all_counts
        self.powers = np.mean(all_powers, axis=0)
        
        self.logger.info("Modulation averages completed")
    
    def _run_single_modulation_cycle(self):
        """Run a single frequency modulation cycle."""
        # Reset Adwin counting
        self.adwin.clear_process("Process_1")
        self.adwin.start_process("Process_1")
        
        # Wait for one complete modulation cycle
        cycle_time = self.cycle_time
        time.sleep(cycle_time + 0.01)  # Add small buffer
        
        # Stop the counting
        self.adwin.stop_process("Process_1")
        
        # Read cycle data from Adwin using FM-specific helper function
        from src.core.adwin_helpers import read_adwin_fm_odmr_data
        fm_data = read_adwin_fm_odmr_data(self.adwin)
        
        # Extract FM cycle data
        counts = fm_data['modulation_cycles']
        voltages = fm_data['cycle_voltages']
        
        # Convert voltages to frequencies
        center_freq = self.settings['frequency']['center']
        mod_depth = self.settings['frequency']['modulation_depth']
        frequencies = center_freq + voltages * mod_depth
        
        # Read power at each point
        powers = np.zeros(self.points_per_cycle)
        for i in range(self.points_per_cycle):
            powers[i] = self.microwave.read_probes('power')
        
        return counts, powers
    
    def _analyze_data(self):
        """Analyze the ODMR frequency modulation data."""
        self.logger.info("Analyzing ODMR FM data...")
        
        # Apply smoothing if enabled
        if self.settings['analysis']['smoothing']:
            self.counts = self._smooth_data(self.counts)
        
        # Subtract background if enabled
        if self.settings['analysis']['background_subtraction']:
            self.counts = self._subtract_background(self.counts)
        
        # Apply lock-in detection if enabled
        if self.settings['analysis']['lock_in_detection']:
            self._apply_lock_in_detection()
        
        # Fit resonances if enabled
        if self.settings['analysis']['auto_fit']:
            self._fit_resonances()
        
        self.logger.info("Data analysis completed")
    
    def _apply_lock_in_detection(self):
        """Apply lock-in detection to improve SNR."""
        try:
            # Use the modulation phase for lock-in detection
            phase = self.modulation_phase
            
            # Calculate in-phase and quadrature components
            in_phase = np.mean(self.counts * np.cos(phase))
            quadrature = np.mean(self.counts * np.sin(phase))
            
            # Calculate lock-in signal magnitude
            self.lock_in_signal = np.sqrt(in_phase**2 + quadrature**2)
            
            # Apply phase-sensitive detection
            # This is a simplified approach - can be enhanced with proper lock-in algorithms
            self.counts = self.counts - np.mean(self.counts)  # Remove DC component
            
            self.logger.info(f"Lock-in detection applied: signal magnitude = {self.lock_in_signal:.2f}")
            
        except Exception as e:
            self.logger.warning(f"Lock-in detection failed: {e}")
    
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
                fit_range = 5  # points on each side (smaller for FM)
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
        """Find peaks in the ODMR FM spectrum."""
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
        self.data['modulation_phase'] = self.modulation_phase
        self.data['counts'] = self.counts
        self.data['counts_raw'] = self.counts_raw
        self.data['powers'] = self.powers
        self.data['cycle_time'] = self.cycle_time
        self.data['points_per_cycle'] = self.points_per_cycle
        self.data['fit_parameters'] = self.fit_parameters
        self.data['resonance_frequencies'] = self.resonance_frequencies
        self.data['lock_in_signal'] = self.lock_in_signal
        self.data['settings'] = self.settings
    
    def _plot(self, axes_list: List[pg.PlotItem]):
        """Plot the ODMR frequency modulation data."""
        if len(axes_list) < 1:
            return
        
        # Clear previous plots
        for ax in axes_list:
            ax.clear()
        
        # Plot main ODMR FM spectrum
        if self.frequencies is not None and self.counts is not None:
            ax = axes_list[0]
            
            # Plot frequency vs counts
            ax.plot(self.frequencies / 1e9, self.counts, 'b-', linewidth=2, 
                   label='ODMR FM Spectrum')
            
            # Plot resonance frequencies if available
            if self.resonance_frequencies:
                for i, freq in enumerate(self.resonance_frequencies):
                    ax.axvline(x=freq/1e9, color='r', linestyle='--', 
                              label=f'Resonance {i+1}: {freq/1e9:.3f} GHz')
            
            ax.set_xlabel('Frequency (GHz)')
            ax.set_ylabel('Photon Counts')
            ax.set_title('ODMR Frequency Modulation Spectrum')
            ax.legend()
            ax.grid(True)
    
    def _update(self, axes_list: List[pg.PlotItem]):
        """Update the plots with new data."""
        self._plot(axes_list)
    
    def get_axes_layout(self, figure_list: List[str]) -> List[List[str]]:
        """Get the layout of plot axes."""
        return [['odmr_fm_spectrum']]
    
    def get_experiment_info(self) -> Dict[str, Any]:
        """Get information about the experiment."""
        center_freq = self.settings['frequency']['center']
        mod_depth = self.settings['frequency']['modulation_depth']
        mod_rate = self.settings['frequency']['modulation_rate']
        
        return {
            'name': 'ODMR Frequency Modulation Experiment',
            'description': 'ODMR with frequency modulation using SG384 for fine sweeps and high-speed acquisition',
            'devices': list(self._DEVICES.keys()),
            'frequency_range': f"{center_freq/1e9:.3f} ± {mod_depth/1e6:.1f} MHz",
            'modulation_rate': f"{mod_rate/1e3:.1f} kHz",
            'cycle_time': f"{self.cycle_time*1e3:.1f} ms",
            'points_per_cycle': self.points_per_cycle,
            'averages': self.settings['acquisition']['averages'],
            'integration_time': f"{self.settings['acquisition']['integration_time']*1e3:.1f} ms"
        } 