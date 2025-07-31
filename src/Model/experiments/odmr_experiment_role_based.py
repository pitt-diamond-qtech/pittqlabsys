"""
Role-Based ODMR Experiment

This experiment demonstrates how to use role-based device selection to make
experiments hardware-agnostic and portable across different lab setups.

Author: Gurudev Dutt <gdutt@pitt.edu>
Created: 2024
License: GPL v2
"""

import numpy as np
import pyqtgraph as pg
from typing import List, Dict, Any, Optional, Tuple
import time

from src.core.role_based_experiment import RoleBasedExperiment
from src.core import Parameter


class RoleBasedODMRExperiment(RoleBasedExperiment):
    """
    Role-Based ODMR Experiment - Hardware Agnostic Version
    
    This experiment performs ODMR measurements on nitrogen-vacancy centers in diamond.
    Instead of hardcoding specific device classes, it defines required device roles
    and lets configuration specify which device implements each role.
    
    Required Device Roles:
    - microwave: Microwave generator for frequency sweeps
    - daq: Data acquisition for photon counting
    - scanner: Scanner for 2D position scanning (optional)
    
    This makes the experiment portable across different lab setups with different hardware.
    """
    
    # Define required device roles (hardware-agnostic)
    _REQUIRED_DEVICE_ROLES = {
        'microwave': 'microwave_generator',
        'daq': 'data_acquisition',
        'scanner': 'scanner'  # Optional for 2D scans
    }
    
    # Default device types (can be overridden by configuration)
    _DEFAULT_DEVICE_TYPES = {
        'microwave': 'sg384',
        'daq': 'adwin',
        'scanner': 'nanodrive'
    }
    
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
    
    _EXPERIMENTS = {}
    
    def __init__(self, name=None, settings=None, devices=None, sub_experiments=None,
                 log_function=None, data_path=None, device_config=None):
        """
        Initialize the role-based ODMR experiment.
        
        Args:
            device_config: Optional device configuration to override defaults
                          Example: {'microwave': 'windfreak_synth_usbii', 'daq': 'nidaq'}
        """
        super().__init__(name, settings, devices, sub_experiments, log_function, data_path, device_config)
        
        # Store device references (now accessed by role name)
        self.microwave = self.devices['microwave']['instance']
        self.daq = self.devices['daq']['instance']
        self.scanner = self.devices.get('scanner', {}).get('instance')  # Optional
        
        # Initialize experiment data
        self.frequencies = None
        self.fluorescence_data = None
        self.fit_parameters = None
        self.resonance_frequencies = None
        self.background_level = None
        
        # NV center parameters (typical values)
        self.nv_zero_field_splitting = 2.87e9  # Hz
        self.nv_gyromagnetic_ratio = 2.8e6  # Hz/Gauss
        
        self.log(f"Initialized ODMR experiment with devices:")
        for role, device_info in self.devices.items():
            self.log(f"  {role}: {device_info['type']} (role: {device_info['role']})")
    
    def setup(self):
        """Setup experiment before execution."""
        self.log("Setting up role-based ODMR experiment...")
        
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
        
        # Configure microwave generator (hardware-agnostic interface)
        self.microwave.set_frequency(self.frequencies[0])
        self.microwave.set_power(self.settings['microwave']['power'])
        self.microwave.output_off()
        
        # Configure modulation if enabled
        if self.settings['microwave']['modulation']:
            self.microwave.enable_modulation()
            self.microwave.set_modulation_type('FM')
            self.microwave.set_modulation_depth(self.settings['microwave']['mod_depth'])
        
        # Configure DAQ for photon counting
        self._setup_daq()
        
        # Move to scan position if 2D scan and scanner available
        if self.settings['scan_mode'] == '2d_scan' and self.scanner:
            self._setup_2d_scan()
        
        self.log("Role-based ODMR experiment setup complete")
    
    def _setup_daq(self):
        """Configure DAQ for photon counting (hardware-agnostic)."""
        self.log("Configuring DAQ for photon counting...")
        
        # Use role-based interface - works with any DAQ device
        self.daq.update({
            'integration_time': self.settings['acquisition']['integration_time'],
            'trigger_mode': 'internal'
        })
    
    def _setup_2d_scan(self):
        """Setup 2D scan parameters (if scanner available)."""
        if not self.scanner:
            self.log("Warning: 2D scan requested but no scanner available")
            return
            
        x_start = self.settings['2d_scan_settings']['x_range'][0]
        y_start = self.settings['2d_scan_settings']['y_range'][0]
        
        # Move to starting position using role-based interface
        self.scanner.update({
            'x_pos': x_start,
            'y_pos': y_start,
            'z_pos': 0.0
        })
    
    def cleanup(self):
        """Cleanup after experiment."""
        self.log("Cleaning up role-based ODMR experiment...")
        
        # Turn off microwave output
        self.microwave.output_off()
        
        # Stop DAQ processes
        self.daq.stop_process()
        
        self.log("Role-based ODMR experiment cleanup complete")
    
    def _function(self):
        """Main experiment function - hardware-agnostic implementation."""
        self.log("Starting role-based ODMR experiment...")
        
        # Run experiment based on scan mode
        if self.settings['scan_mode'] == 'single':
            self._run_single_sweep()
        elif self.settings['scan_mode'] == 'continuous':
            self._run_continuous_sweeps()
        elif self.settings['scan_mode'] == 'averaged':
            self._run_averaged_sweeps()
        elif self.settings['scan_mode'] == '2d_scan':
            self._run_2d_scan()
        else:
            raise ValueError(f"Unknown scan mode: {self.settings['scan_mode']}")
        
        # Analyze data
        self._analyze_data()
        
        self.log("Role-based ODMR experiment completed")
    
    def _run_single_sweep(self):
        """Run single ODMR sweep."""
        self.log("Running single ODMR sweep...")
        
        # Enable microwave output
        self.microwave.output_on()
        
        # Sweep through frequencies
        for i, freq in enumerate(self.frequencies):
            if self.is_stopped():
                break
                
            # Set frequency
            self.microwave.set_frequency(freq)
            
            # Settle time
            time.sleep(self.settings['acquisition']['settle_time'])
            
            # Acquire counts
            counts = self._acquire_counts()
            
            # Store data
            if self.settings['scan_mode'] == '2d_scan':
                self.fluorescence_data[0, 0, i] = counts
            else:
                self.fluorescence_data[i] = counts
            
            # Update progress
            progress = int((i + 1) / len(self.frequencies) * 100)
            self.updateProgress.emit(progress)
            
            # Update plots
            self._update_plots()
        
        # Disable microwave
        self.microwave.output_off()
    
    def _run_continuous_sweeps(self):
        """Run continuous ODMR sweeps."""
        self.log("Running continuous ODMR sweeps...")
        
        while not self.is_stopped():
            self._run_single_sweep()
            if self.is_stopped():
                break
    
    def _run_averaged_sweeps(self):
        """Run averaged ODMR sweeps."""
        self.log("Running averaged ODMR sweeps...")
        
        averages = self.settings['acquisition']['averages']
        temp_data = np.zeros((averages, len(self.frequencies)))
        
        for avg in range(averages):
            if self.is_stopped():
                break
                
            self.log(f"Running sweep {avg + 1}/{averages}")
            self._run_single_sweep()
            
            # Store this sweep
            temp_data[avg, :] = self.fluorescence_data
        
        # Average the data
        self.fluorescence_data = np.mean(temp_data, axis=0)
    
    def _run_2d_scan(self):
        """Run 2D ODMR scan."""
        if not self.scanner:
            self.log("Error: 2D scan requested but no scanner available")
            return
            
        self.log("Running 2D ODMR scan...")
        
        x_steps = self.settings['2d_scan_settings']['x_steps']
        y_steps = self.settings['2d_scan_settings']['y_steps']
        x_range = self.settings['2d_scan_settings']['x_range']
        y_range = self.settings['2d_scan_settings']['y_range']
        
        x_positions = np.linspace(x_range[0], x_range[1], x_steps)
        y_positions = np.linspace(y_range[0], y_range[1], y_steps)
        
        total_points = x_steps * y_steps
        point_count = 0
        
        for y_idx, y_pos in enumerate(y_positions):
            for x_idx, x_pos in enumerate(x_positions):
                if self.is_stopped():
                    break
                
                # Move to position
                self.scanner.update({
                    'x_pos': x_pos,
                    'y_pos': y_pos,
                    'z_pos': 0.0
                })
                
                # Run single sweep at this position
                self._run_single_sweep()
                
                # Store 2D data
                self.fluorescence_data[y_idx, x_idx, :] = self.fluorescence_data[:]
                
                # Update progress
                point_count += 1
                progress = int(point_count / total_points * 100)
                self.updateProgress.emit(progress)
    
    def _acquire_counts(self) -> float:
        """Acquire photon counts (hardware-agnostic)."""
        # Start DAQ process
        self.daq.start_process()
        
        # Wait for integration time
        time.sleep(self.settings['acquisition']['integration_time'])
        
        # Stop and read data
        self.daq.stop_process()
        
        # This is a simplified example - actual implementation would read specific channels
        # The key point is that this works with any DAQ device that implements the role interface
        return np.random.poisson(1000)  # Simulated counts
    
    def _analyze_data(self):
        """Analyze ODMR data."""
        self.log("Analyzing ODMR data...")
        
        if self.settings['analysis']['smoothing']:
            self._smooth_data()
        
        if self.settings['analysis']['background_subtraction']:
            self._subtract_background()
        
        if self.settings['analysis']['auto_fit']:
            self._fit_resonances()
    
    def _smooth_data(self):
        """Apply smoothing to data."""
        window = self.settings['analysis']['smooth_window']
        if window > 1:
            from scipy.ndimage import uniform_filter1d
            if self.fluorescence_data.ndim == 1:
                self.fluorescence_data = uniform_filter1d(self.fluorescence_data, window)
            else:
                for i in range(self.fluorescence_data.shape[0]):
                    for j in range(self.fluorescence_data.shape[1]):
                        self.fluorescence_data[i, j, :] = uniform_filter1d(
                            self.fluorescence_data[i, j, :], window)
    
    def _subtract_background(self):
        """Subtract background from data."""
        if self.fluorescence_data.ndim == 1:
            self.background_level = np.min(self.fluorescence_data)
            self.fluorescence_data -= self.background_level
        else:
            # For 2D data, subtract minimum from each spectrum
            for i in range(self.fluorescence_data.shape[0]):
                for j in range(self.fluorescence_data.shape[1]):
                    min_val = np.min(self.fluorescence_data[i, j, :])
                    self.fluorescence_data[i, j, :] -= min_val
    
    def _fit_resonances(self):
        """Fit resonance peaks."""
        if self.fluorescence_data.ndim == 1:
            self.fit_parameters = self._fit_single_spectrum(self.fluorescence_data)
        else:
            # For 2D data, fit each spectrum
            self.fit_parameters = np.zeros((self.fluorescence_data.shape[0], 
                                          self.fluorescence_data.shape[1], 4))
            for i in range(self.fluorescence_data.shape[0]):
                for j in range(self.fluorescence_data.shape[1]):
                    self.fit_parameters[i, j, :] = self._fit_single_spectrum(
                        self.fluorescence_data[i, j, :])
    
    def _fit_single_spectrum(self, spectrum: np.ndarray) -> np.ndarray:
        """Fit a single ODMR spectrum."""
        # Simple Lorentzian fit (in practice, use scipy.optimize)
        def lorentzian(x, amplitude, center, width, offset):
            return amplitude * width**2 / ((x - center)**2 + width**2) + offset
        
        # This is a simplified fit - actual implementation would use proper fitting
        return np.array([1000, 2.87e9, 1e6, 100])  # [amplitude, center, width, offset]
    
    def _plot(self, axes_list: List[pg.PlotItem]):
        """Plot ODMR data."""
        if self.fluorescence_data.ndim == 1:
            self._plot_1d_data(axes_list)
        else:
            self._plot_2d_data(axes_list)
    
    def _plot_1d_data(self, axes_list: List[pg.PlotItem]):
        """Plot 1D ODMR data."""
        if len(axes_list) < 1:
            return
        
        ax = axes_list[0]
        ax.clear()
        
        if self.frequencies is not None and self.fluorescence_data is not None:
            ax.plot(self.frequencies / 1e9, self.fluorescence_data, 'b-', linewidth=2)
            
            # Plot fit if available
            if self.fit_parameters is not None:
                fit_curve = self._lorentzian_fit(self.frequencies, self.fit_parameters)
                ax.plot(self.frequencies / 1e9, fit_curve, 'r--', linewidth=1)
        
        ax.set_xlabel('Frequency (GHz)')
        ax.set_ylabel('Fluorescence (counts)')
        ax.set_title('ODMR Spectrum')
        ax.grid(True)
    
    def _plot_2d_data(self, axes_list: List[pg.PlotItem]):
        """Plot 2D ODMR data."""
        if len(axes_list) < 2:
            return
        
        # Plot integrated fluorescence
        ax1 = axes_list[0]
        ax1.clear()
        
        if self.fluorescence_data is not None:
            integrated_data = np.sum(self.fluorescence_data, axis=2)
            img = pg.ImageItem(integrated_data)
            ax1.addItem(img)
            ax1.setTitle('Integrated Fluorescence')
        
        # Plot spectrum at center
        ax2 = axes_list[1]
        ax2.clear()
        
        if self.frequencies is not None and self.fluorescence_data is not None:
            center_idx = self.fluorescence_data.shape[0] // 2, self.fluorescence_data.shape[1] // 2
            spectrum = self.fluorescence_data[center_idx[0], center_idx[1], :]
            ax2.plot(self.frequencies / 1e9, spectrum, 'b-', linewidth=2)
            ax2.set_xlabel('Frequency (GHz)')
            ax2.set_ylabel('Fluorescence (counts)')
            ax2.set_title('Center Spectrum')
            ax2.grid(True)
    
    def _update_plots(self):
        """Update plots during experiment."""
        # This would be called during experiment execution
        pass
    
    def _lorentzian_fit(self, x: np.ndarray, params: np.ndarray) -> np.ndarray:
        """Calculate Lorentzian fit."""
        amplitude, center, width, offset = params
        return amplitude * width**2 / ((x - center)**2 + width**2) + offset
    
    def get_axes_layout(self, figure_list: List[str]) -> List[List[str]]:
        """Get axes layout for plotting."""
        if self.settings['scan_mode'] == '2d_scan':
            return [['2d_fluorescence', 'center_spectrum']]
        else:
            return [['odmr_spectrum']]
    
    def get_experiment_info(self) -> Dict[str, Any]:
        """Get experiment information."""
        info = super().get_experiment_info()
        
        # Add role-based device information
        info['device_roles'] = self.get_device_role_info()
        info['device_config'] = self.get_device_config_template()
        
        return info


# Example usage:
def create_odmr_with_different_hardware():
    """
    Example showing how the same experiment can work with different hardware.
    """
    
    # Example 1: Use default hardware (SG384 + ADwin + NanoDrive)
    experiment1 = RoleBasedODMRExperiment(
        name="ODMR_Default",
        device_config=None  # Uses defaults
    )
    
    # Example 2: Use different microwave generator
    experiment2 = RoleBasedODMRExperiment(
        name="ODMR_Windfreak",
        device_config={
            'microwave': 'windfreak_synth_usbii',  # Different microwave generator
            'daq': 'adwin',
            'scanner': 'nanodrive'
        }
    )
    
    # Example 3: Use different DAQ
    experiment3 = RoleBasedODMRExperiment(
        name="ODMR_NIDAQ",
        device_config={
            'microwave': 'sg384',
            'daq': 'nidaq',  # Different DAQ
            'scanner': 'nanodrive'
        }
    )
    
    # All three experiments use the same code but work with different hardware!
    # The experiment logic is completely hardware-agnostic.
    
    return experiment1, experiment2, experiment3 