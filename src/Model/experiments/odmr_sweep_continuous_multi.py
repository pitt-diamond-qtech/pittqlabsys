"""
ODMR Phase Continuous Sweep Experiment - Multi-Waveform

This experiment extends the basic ODMR sweep with support for multiple waveform types
using the ODMR_Sweep_Counter_Multi.bas ADbasic script.

Supported waveforms:
- Triangle (bidirectional, original behavior)
- Ramp/Saw (up only, sharp return)
- Sine (one period)
- Square (constant setpoint)
- Noise (random step-to-step)
- Custom table (user-defined)

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


class ODMRSweepContinuousMultiExperiment(Experiment):
    """
    ODMR Experiment with Multi-Waveform Phase Continuous Sweep.
    
    This experiment extends the basic ODMR sweep with support for multiple waveform types:
    1. Configuring SG384 for phase continuous frequency sweep
    2. Using Adwin ODMR_Sweep_Counter_Multi for synchronized counting with waveform selection
    3. Collecting data during the sweep for high-speed acquisition
    
    Waveform Types:
    - Triangle (0): Bidirectional sweep (original behavior)
    - Ramp (1): Up only, sharp return
    - Sine (2): One complete sine period
    - Square (3): Constant setpoint
    - Noise (4): Random step-to-step
    - Custom (100): User-defined table
    
    Parameters:
        frequency_range: [start, stop] frequency range in Hz
        power: Microwave power in dBm
        step_freq: Frequency step size in Hz
        waveform: Waveform type (0-4, 100)
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
            Parameter('waveform', 0, [0, 1, 2, 3, 4, 100], 'Waveform type: 0=Triangle, 1=Ramp, 2=Sine, 3=Square, 4=Noise, 100=Custom'),
            Parameter('square_setpoint', 0.0, float, 'Square wave setpoint in V (for waveform=3)', units='V'),
            Parameter('noise_seed', 12345, int, 'Random seed for noise waveform (for waveform=4)')
        ]),
        Parameter('acquisition', [
            Parameter('integration_time', 0.001, float, 'Integration time per point in seconds', units='s'),
            Parameter('averages', 10, int, 'Number of sweep averages'),
            Parameter('settle_time', 0.01, float, 'Settle time between sweeps', units='s'),
            Parameter('bidirectional', True, bool, 'Enable bidirectional sweeps (only for Triangle waveform)')
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
        'adwin': 'adwin'
        # 'nanodrive': 'nanodrive'  # Optional - not needed for ODMR sweeps
    }
    
    _EXPERIMENTS = {}
    
    def __init__(self, devices, experiments=None, name=None, settings=None, 
                 log_function=None, data_path=None):
        """
        Initialize ODMR Multi-Waveform Phase Continuous Sweep Experiment.
        
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
        self.microwave = self.devices.get('microwave', {}).get('instance')
        self.adwin = self.devices.get('adwin', {}).get('instance')
        self.nanodrive = self.devices.get('nanodrive', {}).get('instance')
        
        if not self.microwave:
            raise ValueError("SG384 microwave generator is required")
        if not self.adwin:
            raise ValueError("Adwin device is required")
    
    def setup(self):
        """Setup the experiment and devices."""
        # Calculate sweep parameters first (needed by other setup methods)
        self._calculate_sweep_parameters()
        
        # Setup microwave generator for sweep
        self._setup_microwave_sweep()
        
        # Setup Adwin for sweep counting
        self._setup_adwin_sweep()
        
        # Setup nanodrive if available
        if self.nanodrive:
            self._setup_nanodrive()
        
        # Initialize data arrays
        self._initialize_data_arrays()
        
        self.log("ODMR Multi-Waveform Phase Continuous Sweep Experiment setup complete")
    
    def _setup_microwave_sweep(self):
        """Setup the SG384 for external DAC-controlled frequency sweep."""
        if not self.microwave.is_connected:
            self.microwave.connect()
        
        # Set power
        self.microwave.set_power(self.settings['microwave']['power'])
        
        # Configure sweep parameters using calculated values
        start_freq = self.settings['frequency_range']['start']
        stop_freq = self.settings['frequency_range']['stop']
        center_freq = (start_freq + stop_freq) / 2
        deviation = abs(stop_freq - start_freq) / 2
        
        # Validate sweep parameters using SG384 validation
        try:
            self.microwave.validate_sweep_parameters(center_freq, deviation)
            self.log(f"✅ Sweep parameters validated: {center_freq/1e9:.3f} GHz ± {deviation/1e6:.1f} MHz")
        except ValueError as e:
            self.log(f"❌ Sweep parameter validation failed: {e}")
            raise ValueError(f"Invalid sweep parameters: {e}")
        
        # Set center frequency
        self.microwave.set_frequency(center_freq)
        
        # Set sweep deviation (for FM input scaling)
        self.microwave.set_sweep_deviation(deviation)
        
        # CRITICAL: Disable internal sweep - let ADwin DAC control frequency via FM input
        self.microwave.set_modulation_type('Freq sweep')  # Use FM input, not internal sweep
        self.microwave.set_modulation_function("External")  # Don't enable internal modulation

        try:
            modfunc = self.microwave.read_probes('modulation_function')
            modtype = self.microwave.read_probes("modulation_type")
            if modtype == "Freq sweep":
                print(f"SG384 setup for phase continuous sweep")
                self.log(f"SG384 setup for phase continuous sweep")
            else:
                raise IOError(f"Unknown or Incorrect modulation type: {modtype}")
            if modfunc == "External":
                print(f"SG384 setup for external DAC control:{center_freq/1e9:.3f} GHz ± {deviation/1e6:.1f} MHz")
                self.log(f"Microwave setup for external DAC control: {center_freq / 1e9:.3f} GHz ± {deviation / 1e6:.1f} MHz")
                self.log(f"✅ SG384 internal sweep DISABLED - ADwin DAC will control frequency via FM input")
            else:
                raise IOError(f"Unknown or Incorrect modulation function : {modfunc}")
        except Exception as e:
            print("Issue with modulation function or type:",e)

        # Enable modulation
        self.microwave.enable_modulation()
        # Enable output
        self.microwave.enable_output()
    
    def _setup_adwin_sweep(self):
        """Setup Adwin parameters for multi-waveform sweep."""
        if not self.adwin.is_connected:
            self.adwin.connect()
        
        # Proper cleanup like debug script (bring_up_process function)
        self.log("🧹 Cleaning up any existing ADwin process...")
        try:
            self.adwin.stop_process(1)
            time.sleep(0.1)
        except Exception:
            pass
        try:
            self.adwin.clear_process(1)
        except Exception:
            pass
        
        # Store parameters for later use
        # Convert directly from seconds to microseconds (no intermediate ms step)
        self.integration_time_us = int(self.settings['acquisition']['integration_time'] * 1e6)
        self.settle_time_us = int(self.settings['acquisition']['settle_time'] * 1e6)
        self.bidirectional = self.settings['acquisition'].get('bidirectional', True)
        
        # Get waveform parameters
        waveform_type = self.settings['microwave']['waveform']
        square_setpoint = self.settings['microwave']['square_setpoint']
        noise_seed = self.settings['microwave']['noise_seed']
        
        # Debug: Print conversion details
        self.log(f"🔍 DEBUG - Parameter conversions:")
        self.log(f"   integration_time: {self.settings['acquisition']['integration_time']} s → {self.integration_time_us} µs")
        self.log(f"   settle_time: {self.settings['acquisition']['settle_time']} s → {self.settle_time_us} µs")
        self.log(f"   num_steps: {self.num_steps}")
        self.log(f"   waveform_type: {waveform_type}")
        self.log(f"   bidirectional: {self.bidirectional}")
        
        # Set parameters BEFORE loading/starting process
        self.log("⚙️  Setting ADwin parameters...")
        try:
            # Par_1: Number of steps in sweep
            self.log(f"🔍 Setting Par_1 (N_STEPS) = {self.num_steps}")
            self.adwin.set_int_var(1, self.num_steps)
            
            # Par_2: Settle time in microseconds
            self.log(f"🔍 Setting Par_2 (SETTLE_US) = {self.settle_time_us}")
            self.adwin.set_int_var(2, self.settle_time_us)
            
            # Par_3: Dwell/integration time in microseconds
            self.log(f"🔍 Setting Par_3 (DWELL_US) = {self.integration_time_us}")
            self.adwin.set_int_var(3, self.integration_time_us)
            
            # Par_4: Edge mode (0=rising, 1=falling) - use rising like debug script
            edge_mode = 0  # Rising edges
            self.log(f"🔍 Setting Par_4 (EDGE_MODE) = {edge_mode} (rising edges)")
            self.adwin.set_int_var(4, edge_mode)
            
            # Par_5: DAC channel (1 or 2)
            dac_channel = 1  # Use DAC channel 1
            self.log(f"🔍 Setting Par_5 (DAC_CH) = {dac_channel}")
            self.adwin.set_int_var(5, dac_channel)
            
            # Par_6: Direction sense (0=DIR Low=up, 1=DIR High=up) - use DIR High=up like debug script
            dir_sense = 1  # DIR High=up
            self.log(f"🔍 Setting Par_6 (DIR_SENSE) = {dir_sense} (DIR High=up)")
            self.adwin.set_int_var(6, dir_sense)
            
            # Par_7: Waveform type (0-4, 100)
            self.log(f"🔍 Setting Par_7 (WAVEFORM) = {waveform_type}")
            self.adwin.set_int_var(7, waveform_type)
            
            # Par_8: Processdelay_us (0 = auto-calculate, >0 = manual override)
            processdelay_us = 0  # Auto-calculate like debug script
            self.log(f"🔍 Setting Par_8 (PROCESSDELAY_US) = {processdelay_us} (auto-calculate)")
            self.adwin.set_int_var(8, processdelay_us)
            
            # Par_9: Overhead factor (scaled by 10: 12 = 1.2x)
            overhead_factor_scaled = 12  # 1.2x overhead factor like debug script
            self.log(f"🔍 Setting Par_9 (OVERHEAD_FACTOR) = {overhead_factor_scaled} (1.2× scaled by 10)")
            self.adwin.set_int_var(9, overhead_factor_scaled)
            
            # Par_10: START (will be set to 1 when ready to run)
            self.log(f"🔍 Setting Par_10 (START) = 0 (idle)")
            self.adwin.set_int_var(10, 0)
            
            # Par_11: RNG seed for noise waveform
            self.log(f"🔍 Setting Par_11 (RNG_SEED) = {noise_seed}")
            self.adwin.set_int_var(11, noise_seed)
            
            # FPar_1: VMIN (voltage range minimum)
            vmin = -1.0  # -1.0V like debug script
            self.log(f"🔍 Setting FPar_1 (VMIN) = {vmin} V")
            self.adwin.set_float_var(1, vmin)
            
            # FPar_2: VMAX (voltage range maximum)
            vmax = 1.0  # +1.0V like debug script
            self.log(f"🔍 Setting FPar_2 (VMAX) = {vmax} V")
            self.adwin.set_float_var(2, vmax)
            
            # FPar_5: Square setpoint (for waveform=3)
            self.log(f"🔍 Setting FPar_5 (SQUARE_SETPOINT) = {square_setpoint} V")
            self.adwin.set_float_var(5, square_setpoint)
            
            # For custom waveform (waveform=100), populate Data_3
            if waveform_type == 100:
                self._setup_custom_waveform()
            
            self.log("✅ All parameters set successfully!")
            
        except Exception as e:
            self.log(f"❌ Error setting ADwin parameters: {e}")
            raise RuntimeError(f"Failed to set ADwin parameters: {e}")
        
        # Load ODMR Sweep Counter Multi script
        from src.core.adwin_helpers import get_adwin_binary_path
        sweep_binary_path = get_adwin_binary_path('ODMR_Sweep_Counter_Multi.TB1')
        self.log(f"📁 Loading TB1: {sweep_binary_path}")
        self.adwin.update({
            'process_1': {
                'load': str(sweep_binary_path),
                'delay': 1000000,  # 1ms base delay
                'running': False
            }
        })
        
        # Start the process once (like debug script)
        self.log("▶️  Starting ADwin process...")
        self.adwin.start_process(1)
        time.sleep(0.1)  # Give process time to start
        
        # Verify process started
        process_status = self.adwin.get_process_status(1)
        if process_status != "Running":
            self.log(f"❌ Process failed to start! Status: {process_status}")
            raise RuntimeError("ADwin process failed to start")
        
        # Check signature
        signature = self.adwin.get_int_var(80)
        if signature != 7777:
            self.log(f"❌ Wrong signature! Expected 7777, got {signature}")
            raise RuntimeError("Wrong ADwin script loaded")
        
        # Check waveform type used
        waveform_used = self.adwin.get_int_var(81)
        n_points = self.adwin.get_int_var(82)
        
        self.log(f"✅ ADwin process started correctly (signature: {signature})")
        self.log(f"✅ Waveform type: {waveform_used}, n_points: {n_points}")
        
        self.log(f"Adwin sweep setup: {self.num_steps} steps, {self.settings['acquisition']['integration_time']*1e3:.1f} ms per step")
        if self.bidirectional and waveform_type == 0:
            self.log(f"✅ Bidirectional sweeps enabled - will collect data during both forward and reverse sweeps")
            self.log(f"   This doubles acquisition efficiency compared to unidirectional sweeps")
        else:
            self.log(f"ℹ️  Unidirectional sweeps enabled - will collect data during forward sweep only")
    
    def _setup_custom_waveform(self):
        """Setup custom waveform table for waveform=100."""
        self.log("📊 Setting up custom waveform table...")
        
        # Create a custom waveform (example: sawtooth with sine variation)
        n_steps = self.num_steps
        custom_volts = []
        
        for i in range(min(n_steps, 1000)):  # Safety limit
            # Create sawtooth with sine variation
            t = i / (n_steps - 1)  # 0 to 1
            val = -1.0 + 2.0 * t  # Sawtooth from -1 to +1
            val += 0.1 * np.sin(4 * np.pi * t)  # Add sine variation
            val = np.clip(val, -1.0, 1.0)  # Clamp to ±1V
            custom_volts.append(val)
        
        # Convert to DAC digits
        custom_digits = []
        for v in custom_volts:
            digit = int((v + 10.0) * 65535.0 / 20.0)
            custom_digits.append(digit)
        
        # Pad to 1000 elements
        while len(custom_digits) < 1000:
            custom_digits.append(custom_digits[-1] if custom_digits else 0)
        
        # Set Data_3 array
        self.adwin.set_data_long(3, custom_digits)
        self.log(f"✅ Custom waveform table set with {len(custom_volts)} points")
    
    def _setup_nanodrive(self):
        """Setup MCL nanodrive if available."""
        if not self.nanodrive.is_connected:
            self.nanodrive.connect()
        
        # Set to current position (no movement)
        # Get position for all axes (x, y, z) - lowercase required
        try:
            current_pos = self.nanodrive.get_position('x')
            self.log(f"Nanodrive X position: {current_pos}")
        except Exception as e:
            self.log(f"Could not get nanodrive X position: {e}")
        
        try:
            current_pos = self.nanodrive.get_position('y')
            self.log(f"Nanodrive Y position: {current_pos}")
        except Exception as e:
            self.log(f"Could not get nanodrive Y position: {e}")
        
        try:
            current_pos = self.nanodrive.get_position('z')
            self.log(f"Nanodrive Z position: {current_pos}")
        except Exception as e:
            self.log(f"Could not get nanodrive Z position: {e}")
    
    def _calculate_sweep_parameters(self):
        """Calculate sweep timing and frequency parameters."""
        start_freq = self.settings['frequency_range']['start']
        stop_freq = self.settings['frequency_range']['stop']
        step_freq = self.settings['microwave']['step_freq']
        integration_time = self.settings['acquisition']['integration_time']
        settle_time = self.settings['acquisition']['settle_time']
        waveform_type = self.settings['microwave']['waveform']
        
        # Calculate number of steps based on frequency range and step size
        self.num_steps = int(abs(stop_freq - start_freq) / step_freq)
        
        # Calculate n_points based on waveform type
        if waveform_type == 0:  # Triangle (bidirectional)
            self.n_points = 2 * self.num_steps - 2
        else:  # All other waveforms (unidirectional)
            self.n_points = self.num_steps
        
        # Calculate sweep time based on integration time and settle time per step
        time_per_step = integration_time + settle_time
        self.sweep_time = self.n_points * time_per_step
        
        # Generate frequency array for data collection
        self.frequencies = np.linspace(start_freq, stop_freq, self.n_points)
        
        # Log calculation results
        waveform_names = {0: "Triangle", 1: "Ramp", 2: "Sine", 3: "Square", 4: "Noise", 100: "Custom"}
        waveform_name = waveform_names.get(waveform_type, "Unknown")
        
        self.log(f"Step frequency: {step_freq/1e6:.2f} MHz")
        self.log(f"Number of steps: {self.num_steps}")
        self.log(f"Number of points: {self.n_points}")
        self.log(f"Waveform type: {waveform_type} ({waveform_name})")
        self.log(f"Time per step: {time_per_step*1e3:.1f} ms")
        self.log(f"Sweep time: {self.sweep_time:.3f} s")
        self.log(f"Frequency range: {start_freq/1e9:.3f} - {stop_freq/1e9:.3f} GHz")
        self.log(f"Frequency deviation: {abs(stop_freq - start_freq)/1e6:.1f} MHz")
    
    def _initialize_data_arrays(self):
        """Initialize data storage arrays."""
        averages = self.settings['acquisition']['averages']
        
        # Main data arrays - size depends on waveform type
        self.counts_forward = np.zeros(self.n_points)
        self.counts_reverse = np.zeros(self.n_points)
        self.counts_averaged = np.zeros(self.n_points)
        self.voltages = np.zeros(self.n_points)
        
        # For bidirectional waveforms, we'll split the data
        if self.settings['microwave']['waveform'] == 0 and self.bidirectional:
            # Triangle waveform with bidirectional - split into forward/reverse
            half = self.n_points // 2
            self.counts_forward = np.zeros(half)
            self.counts_reverse = np.zeros(half)
            self.counts_averaged = np.zeros(half)
            self.voltages = np.zeros(half)
        
        # Analysis arrays
        self.fit_parameters = None
        self.resonance_frequencies = None
        self.fit_quality = None
    
    def cleanup(self):
        """Cleanup experiment resources."""
        # Stop Adwin process
        if self.adwin and self.adwin.is_connected:
            self.adwin.stop_process(1)
            self.adwin.clear_process(1)
        
        # Disable microwave sweep and output
        if self.microwave and self.microwave.is_connected:
            self.microwave.disable_modulation()
            self.microwave.disable_output()
        
        self.log("ODMR Multi-Waveform Phase Continuous Sweep Experiment cleanup complete")
    
    def _function(self):
        """Main experiment function."""
        try:
            self.log("Starting ODMR Multi-Waveform Phase Continuous Sweep Experiment")
            
            # Setup experiment and devices first
            self.setup()
            
            # Calculate sweep parameters first
            self._calculate_sweep_parameters()
            
            # Run multiple sweep averages
            self._run_sweep_averages()
            
            # Analyze the data
            self._analyze_data()
            
            # Store results
            self._store_results_in_data()
            
            self.log("ODMR Multi-Waveform Phase Continuous Sweep Experiment completed successfully")
            
        except Exception as e:
            self.log(f"Error in ODMR multi-waveform sweep experiment: {e}")
            raise
    
    def _run_sweep_averages(self):
        """Run multiple sweep averages."""
        averages = self.settings['acquisition']['averages']
        settle_time = self.settings['acquisition']['settle_time']
        waveform_type = self.settings['microwave']['waveform']
        
        self.log(f"Starting sweep averages: {averages} sweeps")
        
        # Preallocate arrays for data
        all_counts = np.empty((averages, self.n_points), dtype=np.int32)
        all_volts = np.empty((averages, self.n_points), dtype=np.float32)
        
        for avg in range(averages):
            self.log(f"Running sweep {avg + 1}/{averages}")
            
            # Run single sweep - get raw data
            counts, volts = self._run_single_sweep()
            
            # Store data
            all_counts[avg, :] = counts
            all_volts[avg, :] = volts
            
            # Settle time between sweeps
            if avg < averages - 1:
                time.sleep(settle_time)
        
        # Average the data
        self.counts_averaged = np.mean(all_counts, axis=0)
        self.voltages = np.mean(all_volts, axis=0)
        
        # For bidirectional Triangle waveform, split into forward/reverse
        if waveform_type == 0 and self.bidirectional and self.n_points > 1:
            half = self.n_points // 2
            self.counts_forward = self.counts_averaged[:half]
            self.counts_reverse = self.counts_averaged[half:]
            self.counts_averaged = (self.counts_forward + self.counts_reverse) / 2
        else:
            # For unidirectional waveforms, forward and reverse are the same
            self.counts_forward = self.counts_averaged.copy()
            self.counts_reverse = self.counts_averaged.copy()
        
        self.log("Sweep averages completed")
    
    def _run_single_sweep(self):
        """Run a single frequency sweep."""
        # Process should already be running from _setup_adwin_sweep
        self.log("✅ Using already-running ADwin process")
        
        # Arm the sweep
        self.log("🚀 Arming sweep...")
        self.adwin.set_int_var(10, 1)  # Par_10 = START
        
        # Wait for heartbeat to start advancing
        self.log("⏳ Waiting for ADwin heartbeat to start...")
        initial_hb = self.adwin.get_int_var(25)
        start_time = time.time()
        
        while time.time() - start_time < 1.0:  # Wait up to 1 second
            try:
                current_hb = self.adwin.get_int_var(25)
                if current_hb > initial_hb:
                    self.log(f"✅ ADwin heartbeat advancing: {initial_hb} → {current_hb}")
                    break
                time.sleep(0.01)  # 10ms polling
            except Exception as e:
                self.log(f"⚠️  Transient Get_Par error (tolerated): {e}")
                time.sleep(0.01)
        else:
            self.log("❌ ADwin heartbeat not advancing after 1s - process not running!")
            return np.zeros(self.n_points), np.zeros(self.n_points)
        
        # Clear any stale ready flags first
        self.log("🧹 Clearing any stale ready flags...")
        try:
            self.adwin.set_int_var(20, 0)  # Clear Par_20 (ready flag)
        except Exception as e:
            self.log(f"Warning: Could not clear ready flag: {e}")
        
        # Wait for sweep to complete
        integration_time = self.settings['acquisition']['integration_time']  # Already in seconds
        settle_time = self.settings['acquisition']['settle_time']  # Already in seconds
        per_point_s = settle_time + integration_time  # Both already in seconds
        timeout = max(5.0, self.n_points * per_point_s * 10)  # Very generous margin
        
        self.log(f"⏳ Waiting for Par_20 == 1 (sweep ready)…")
        self.log(f"   Expected {self.n_points} points, timeout: {timeout:.1f}s")
        
        t0 = time.time()
        last_hb = self.adwin.get_int_var(25)
        
        while True:
            try:
                ready = self.adwin.get_int_var(20)  # ready flag
                hb = self.adwin.get_int_var(25)     # heartbeat
                state = self.adwin.get_int_var(26)  # current state
                elapsed = time.time() - t0
                
                if ready == 1:
                    self.log(f"✅ Sweep ready after {elapsed:.2f}s!")
                    break
                    
                # Check if heartbeat is still advancing (after 100ms grace period)
                if hb <= last_hb and elapsed > 0.1:
                    self.log(f"⚠️  Heartbeat stalled at {hb}!")
                    
                last_hb = hb
                time.sleep(0.05)
            except Exception as e:
                self.log(f"⚠️  Transient Get_Par error (tolerated): {e}")
                time.sleep(0.05)  # Continue polling despite error

            if elapsed > timeout:
                self.log(f"❌ Timeout after {elapsed:.1f}s (expected ~{self.n_points * per_point_s:.1f}s)")
                return np.zeros(self.n_points), np.zeros(self.n_points)
        
        # Read arrays
        n_points = self.adwin.get_int_var(21)
        if n_points <= 0:
            self.log("❌ n_points <= 0 — nothing to read.")
            return np.zeros(self.n_points), np.zeros(self.n_points)
        
        self.log(f"📊 Sweep reports n_points = {n_points}")
        
        # Read the data arrays
        try:
            counts = self.adwin.read_probes('int_array', 1, n_points)  # Data_1
            dac_digits = self.adwin.read_probes('int_array', 2, n_points)  # Data_2
            
            # Compute volts from DAC digits
            volts = []
            for d in dac_digits:
                d_int = int(d)
                if 0 <= d_int <= 65535:
                    volt = (d_int * 20.0 / 65535.0) - 10.0
                    volts.append(volt)
                else:
                    volts.append(0.0)  # Invalid digit
            
            self.log(f"✅ Read {len(counts)} counts, {len(volts)} volts")
            
        except Exception as e:
            self.log(f"❌ Error reading arrays: {e}")
            return np.zeros(self.n_points), np.zeros(self.n_points)
        
        # Sanity check: ensure n_points matches expected value
        if n_points != self.n_points:
            self.log(f"❌ CRITICAL: n_points mismatch!")
            self.log(f"   Expected: {self.n_points} points")
            self.log(f"   Received: {n_points} points")
            self.log(f"   This indicates ADwin sweep did not complete properly")
            return np.zeros(self.n_points), np.zeros(self.n_points)
        
        # Convert to numpy arrays
        counts = np.array(counts)
        volts = np.array(volts)
        
        # Clear ready flag for next sweep
        self.adwin.set_int_var(20, 0)
        
        return counts, volts
    
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
        self.data['n_points'] = self.n_points
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
            
            waveform_type = self.settings['microwave']['waveform']
            waveform_names = {0: "Triangle", 1: "Ramp", 2: "Sine", 3: "Square", 4: "Noise", 100: "Custom"}
            waveform_name = waveform_names.get(waveform_type, "Unknown")
            
            # Plot forward and reverse sweeps (if different)
            if not np.array_equal(self.counts_forward, self.counts_reverse):
                ax.plot(self.frequencies / 1e9, self.counts_forward, 'b-', linewidth=1, 
                       label='Forward Sweep', alpha=0.7)
                ax.plot(self.frequencies / 1e9, self.counts_reverse, 'g-', linewidth=1, 
                       label='Reverse Sweep', alpha=0.7)
            
            # Plot averaged data
            ax.plot(self.frequencies / 1e9, self.counts_averaged, 'r-', linewidth=2, 
                   label=f'{waveform_name} Spectrum')
            
            # Plot resonance frequencies if available
            if self.resonance_frequencies:
                for i, freq in enumerate(self.resonance_frequencies):
                    ax.axvline(x=freq/1e9, color='orange', linestyle='--', 
                              label=f'Resonance {i+1}: {freq/1e9:.3f} GHz')
            
            ax.set_xlabel('Frequency (GHz)')
            ax.set_ylabel('Photon Counts')
            ax.set_title(f'ODMR Multi-Waveform Spectrum ({waveform_name})')
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
        waveform_type = self.settings['microwave']['waveform']
        waveform_names = {0: "Triangle", 1: "Ramp", 2: "Sine", 3: "Square", 4: "Noise", 100: "Custom"}
        waveform_name = waveform_names.get(waveform_type, "Unknown")
        
        return {
            'name': 'ODMR Multi-Waveform Phase Continuous Sweep Experiment',
            'description': f'ODMR with {waveform_name} waveform using SG384 and synchronized Adwin counting',
            'devices': list(self._DEVICES.keys()),
            'frequency_range': f"{self.settings['frequency_range']['start']/1e9:.3f} - {self.settings['frequency_range']['stop']/1e9:.3f} GHz",
            'step_frequency': f"{self.settings['microwave']['step_freq']/1e6:.2f} MHz",
            'waveform': f"{waveform_type} ({waveform_name})",
            'sweep_time': f"{self.sweep_time:.3f} s",
            'num_steps': self.num_steps,
            'n_points': self.n_points,
            'averages': self.settings['acquisition']['averages'],
            'integration_time': f"{self.settings['acquisition']['integration_time']*1e3:.1f} ms"
        }

