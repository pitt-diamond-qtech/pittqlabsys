#!/usr/bin/env python3
"""
ODMR Pulsed Experiment

This experiment implements pulsed ODMR measurements using the AWG520 for
sequence generation and ADwin for photon counting. Users can specify
sequences using our text-based language and preview scan results.
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional, Tuple, Union
from pathlib import Path
import json
import logging
import time
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from src.core.experiment import Experiment
from src.core import Parameter
from src.Model.sequence_parser import SequenceTextParser
from src.Model.sequence_builder import SequenceBuilder
from src.Model.hardware_calibrator import HardwareCalibrator
from src.Model.awg520_optimizer import AWG520SequenceOptimizer
from src.Model.awg_file import AWGFile
from src.Model.sequence import Sequence
from src.Model.pulses import Pulse
from src.Controller.awg520 import AWG520Device
from src.Controller.adwin_gold import AdwinGoldDevice


class ODMRPulsedExperiment(Experiment):
    """
    Pulsed ODMR experiment using AWG520 for sequence generation and ADwin for counting.
    
    Features:
    - Text-based sequence definition using our sequence language
    - Sequence preview with first 10 scan points
    - Microwave frequency, power, and delay parameters
    - Laser power and wavelength configuration
    - AWG520 triggers ADwin for photon counting
    - Memory optimization for long sequences
    """
    
    _DEFAULT_SETTINGS = [
        Parameter('sequence', [
            Parameter('file_path', '', str, 'Path to sequence definition file'),
            Parameter('name', 'odmr_pulsed', str, 'Sequence name'),
            Parameter('sample_rate', 1e9, float, 'Sample rate in Hz', units='Hz'),
            Parameter('repeat_count', 50000, int, 'Number of repetitions per scan point')
        ]),
        Parameter('microwave', [
            Parameter('frequency', 2.87e9, float, 'Microwave frequency in Hz', units='Hz'),
            Parameter('power', -10.0, float, 'Microwave power in dBm', units='dBm'),
            Parameter('delay', 25.0, float, 'Microwave delay in ns', units='ns')
        ]),
        Parameter('laser', [
            Parameter('power', 1.0, float, 'Laser power in mW', units='mW'),
            Parameter('wavelength', 532.0, float, 'Laser wavelength in nm', units='nm')
        ]),
        Parameter('delays', [
            Parameter('mw_delay', 25.0, float, 'Microwave delay in ns', units='ns'),
            Parameter('aom_delay', 50.0, float, 'AOM delay in ns', units='ns'),
            Parameter('counter_delay', 15.0, float, 'Counter delay in ns', units='ns')
        ]),
        Parameter('adwin', [
            Parameter('count_time', 300, float, 'Photon counting time in ns', units='ns'),
            Parameter('reset_time', 2000, float, 'Reset time between counts in ns', units='ns'),
            Parameter('repetitions_per_point', 50000, int, 'Number of repetitions per scan point')
        ]),
        Parameter('scan', [
            Parameter('preview_points', 10, int, 'Number of scan points to preview'),
            Parameter('auto_generate_files', True, bool, 'Automatically generate AWG files'),
            Parameter('output_directory', 'odmr_pulsed_output', str, 'Output directory for AWG files')
        ]),
        Parameter('optimization', [
            Parameter('enable_compression', True, bool, 'Enable memory compression'),
            Parameter('dead_time_threshold', 100000, int, 'Dead time threshold for compression (samples)'),
            Parameter('high_resolution_threshold', 1000, int, 'High resolution threshold (samples)')
        ])
    ]
    
    _DEVICES = {
        'awg520': 'awg520',
        'adwin': 'adwin',
        'sg384': 'sg384'  # String reference to device loaded from config
    }
    
    _EXPERIMENTS = {}
    
    def __init__(self, devices=None, experiments=None, name=None, settings=None, log_function=None, data_path=None, config_path: Optional[Path] = None):
        """Initialize the ODMR Pulsed experiment."""
        super().__init__(name=name, settings=settings, devices=devices, sub_experiments=experiments, log_function=log_function, data_path=data_path)
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.config_path = config_path or self.get_config_path("config.json")
        self.config = self._load_config()
        
        # Sequence components
        self.sequence_parser = SequenceTextParser()
        self.sequence_builder = SequenceBuilder()
        
        # Initialize hardware calibrator with experiment-specific connection file
        connection_file = Path(__file__).parent / "odmr_pulsed_connection.json"
        self.hardware_calibrator = HardwareCalibrator(
            connection_file=str(connection_file),
            config_file=str(self.config_path)
        )
        
        self.awg_optimizer = AWG520SequenceOptimizer()
        
        # Experiment parameters (will be set from _DEFAULT_SETTINGS)
        self.microwave_frequency = 2.87e9  # 2.87 GHz (NV center)
        self.microwave_power = -10.0       # dBm
        self.mw_delay = 25.0              # ns
        self.aom_delay = 50.0             # ns
        self.counter_delay = 15.0         # ns
        
        self.laser_power = 1.0            # mW
        self.laser_wavelength = 532       # nm
        
        # Sequence data
        self.sequence_description = None
        self.scan_sequences = []
        self.current_scan_point = 0
        
        # ADwin parameters (from your code)
        self.count_time = 300             # ns
        self.reset_time = 2000            # ns
        self.repetitions_per_point = 50000  # 50K reps for statistics
        
        # Output paths
        self.output_dir = self.get_output_dir("odmr_pulsed_output")
        
        self.logger.info("ODMR Pulsed Experiment initialized")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                self.logger.info(f"Configuration loaded from {self.config_path}")
                return config
            else:
                self.logger.warning(f"Configuration file not found: {self.config_path}")
                return {}
        except Exception as e:
            self.logger.error(f"Error loading configuration: {e}")
            return {}
    
    def load_sequence_from_text(self, sequence_text: str) -> bool:
        """
        Load sequence definition from text using the sequence language.
        
        Args:
            sequence_text: Sequence definition in the sequence language format
            
        Returns:
            True if sequence loaded successfully
        """
        try:
            # Parse sequence text using the sequence language parser
            self.sequence_description = self.sequence_parser.parse_text(sequence_text)
            
            if self.sequence_description:
                self.logger.info(f"Sequence loaded: {self.sequence_description.name}")
                self.logger.info(f"Variables: {len(self.sequence_description.variables)}")
                self.logger.info(f"Pulses: {len(self.sequence_description.pulses)}")
                return True
            else:
                self.logger.error("Failed to parse sequence text")
                return False
                
        except Exception as e:
            self.logger.error(f"Error loading sequence: {e}")
            return False
    
    def load_sequence_from_file(self, sequence_file: Path) -> bool:
        """
        Load sequence definition from text file.
        
        Args:
            sequence_file: Path to sequence text file
            
        Returns:
            True if sequence loaded successfully
        """
        try:
            if not sequence_file.exists():
                self.logger.error(f"Sequence file not found: {sequence_file}")
                return False
            
            # Read sequence text
            with open(sequence_file, 'r') as f:
                sequence_text = f.read()
            
            # Parse sequence
            self.sequence_description = self.sequence_parser.parse_text(sequence_text)
            
            if self.sequence_description:
                self.logger.info(f"Sequence loaded: {self.sequence_description.name}")
                self.logger.info(f"Variables: {len(self.sequence_description.variables)}")
                self.logger.info(f"Pulses: {len(self.sequence_description.pulses)}")
                return True
            else:
                self.logger.error("Failed to parse sequence text")
                return False
                
        except Exception as e:
            self.logger.error(f"Error loading sequence: {e}")
            return False
    
    def build_scan_sequences(self) -> bool:
        """
        Build scan sequences from the loaded sequence description.
        
        Returns:
            True if sequences built successfully
        """
        try:
            if not self.sequence_description:
                self.logger.error("No sequence description loaded")
                return False
            
            # Build scan sequences
            self.scan_sequences = self.sequence_builder.build_scan_sequences(
                self.sequence_description
            )
            
            # Apply hardware calibration
            for i, sequence in enumerate(self.scan_sequences):
                calibrated_sequence = self.hardware_calibrator.calibrate_sequence(
                    sequence, 
                    self.sequence_description.sample_rate
                )
                self.scan_sequences[i] = calibrated_sequence
            
            self.logger.info(f"Built {len(self.scan_sequences)} scan sequences")
            return True
            
        except Exception as e:
            self.logger.error(f"Error building scan sequences: {e}")
            return False
    
    def generate_awg_files(self) -> bool:
        """
        Generate AWG520 waveform and sequence files using the proper pipeline.
        
        Returns:
            True if files generated successfully
        """
        try:
            if not self.scan_sequences:
                self.logger.error("No scan sequences available")
                return False
            
            # Create AWG file handler
            awg_file = AWGFile(out_dir=self.output_dir)
            
            # Generate waveforms for each sequence using the proper pipeline
            waveform_files = []
            for i, sequence in enumerate(self.scan_sequences):
                # Use AWG520SequenceOptimizer to properly optimize the sequence
                optimized_sequence = self.awg_optimizer.optimize_sequence_for_awg520(sequence)
                
                # Get waveform data from the optimized sequence
                waveform_data = optimized_sequence.get_waveform_data()
                
                # Generate waveform files for each channel
                for channel in [1, 2]:  # AWG520 has 2 channels
                    # Get the appropriate waveform data for this channel
                    if f"channel_{channel}" in waveform_data:
                        iq_data = waveform_data[f"channel_{channel}"]
                    else:
                        # Fallback: use the first available waveform
                        iq_data = list(waveform_data.values())[0] if waveform_data else np.zeros(1000)
                    
                    # Generate marker data (this would come from the sequence markers)
                    marker_data = np.zeros(len(iq_data), dtype=int)
                    
                    # Generate waveform file
                    wfm_path = awg_file.write_waveform(
                        iq_data, 
                        marker_data,
                        f"scan_point_{i:03d}",
                        channel=channel
                    )
                    waveform_files.append(wfm_path)
                    self.logger.info(f"Generated waveform: {wfm_path}")
            
            # Generate sequence file using the optimized sequence entries
            if self.scan_sequences:
                # Use the first sequence to get the optimized sequence entries
                first_sequence = self.scan_sequences[0]
                optimized_sequence = self.awg_optimizer.optimize_sequence_for_awg520(first_sequence)
                sequence_entries = optimized_sequence.get_sequence_entries()
                
                # Convert to the format expected by AWGFile.write_sequence
                seq_entries = []
                for i, entry in enumerate(sequence_entries):
                    # Format: ch1_wfm, ch2_wfm, repeat, wait, goto, logic
                    seq_entry = (
                        f"scan_point_{i:03d}_1.wfm",  # ch1_wfm
                        f"scan_point_{i:03d}_2.wfm",  # ch2_wfm
                        self.repetitions_per_point,    # repeat count
                        0,                             # wait (no wait)
                        (i + 1) % len(sequence_entries) + 1,  # goto next
                        0                              # logic (no logic)
                    )
                    seq_entries.append(seq_entry)
                
                # Create sequence file
                seq_path = awg_file.write_sequence(
                    seq_entries,
                    "odmr_pulsed_scan"
                )
                
                self.logger.info(f"Generated sequence file: {seq_path}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error generating AWG files: {e}")
            return False
    
    def show_sequence_preview(self, num_points: int = 10) -> None:
        """
        Show sequence preview window with first N scan points.
        
        Args:
            num_points: Number of scan points to preview
        """
        if not self.scan_sequences:
            messagebox.showerror("Error", "No scan sequences available. Build sequences first.")
            return
        
        # Limit to available sequences
        preview_sequences = self.scan_sequences[:min(num_points, len(self.scan_sequences))]
        
        # Create preview window
        preview_window = SequencePreviewWindow(preview_sequences, self.sequence_description)
        preview_window.show()
    
    def set_microwave_parameters(self, frequency: float, power: float, delay: float) -> None:
        """
        Set microwave parameters.
        
        Args:
            frequency: Frequency in Hz
            power: Power in dBm
            delay: Delay in ns
        """
        self.microwave_frequency = frequency
        self.microwave_power = power
        self.mw_delay = delay
        self.logger.info(f"Microwave: {frequency/1e9:.3f} GHz, {power} dBm, {delay} ns delay")
    
    def set_laser_parameters(self, power: float, wavelength: float) -> None:
        """
        Set laser parameters.
        
        Args:
            power: Power in mW
            wavelength: Wavelength in nm
        """
        self.laser_power = power
        self.laser_wavelength = wavelength
        self.logger.info(f"Laser: {power} mW, {wavelength} nm")
    
    def set_delay_parameters(self, mw_delay: float, aom_delay: float, counter_delay: float) -> None:
        """
        Set delay parameters.
        
        Args:
            mw_delay: Microwave delay in ns
            aom_delay: AOM delay in ns
            counter_delay: Counter delay in ns
        """
        self.mw_delay = mw_delay
        self.aom_delay = aom_delay
        self.counter_delay = counter_delay
        self.logger.info(f"Delays: MW={mw_delay}ns, AOM={aom_delay}ns, Counter={counter_delay}ns")
    
    def get_adwin_parameters(self) -> Dict[str, Any]:
        """
        Get ADwin parameters for the experiment.
        
        Returns:
            Dictionary of ADwin parameters
        """
        return {
            'count_time': self.count_time,
            'reset_time': self.reset_time,
            'repetitions_per_point': self.repetitions_per_point,
            'microwave_frequency': self.microwave_frequency,
            'microwave_power': self.microwave_power,
            'laser_power': self.laser_power,
            'laser_wavelength': self.laser_wavelength
        }
    
    def run_experiment(self, frequency_range: Optional[List[float]] = None) -> Dict[str, Any]:
        """
        Run the complete ODMR pulsed experiment.
        
        Args:
            frequency_range: List of frequencies in Hz to scan. If None, uses single frequency.
            
        Returns:
            Dictionary containing:
            - 'success': bool - Whether experiment completed successfully
            - 'frequencies': List[float] - Frequencies scanned
            - 'signal_counts': List[List[float]] - Signal counts for each frequency and sequence point
            - 'reference_counts': List[List[float]] - Reference counts for each frequency and sequence point
            - 'total_counts': List[List[float]] - Total counts for each frequency and sequence point
        """
        try:
            self.logger.info("Starting ODMR Pulsed Experiment")
            
            # Step 1: Load sequence
            if not self.sequence_description:
                self.logger.error("No sequence loaded")
                return {'success': False, 'error': 'No sequence loaded'}
            
            # Step 2: Build scan sequences
            if not self.build_scan_sequences():
                return {'success': False, 'error': 'Failed to build scan sequences'}
            
            # Step 3: Generate AWG files
            if not self.generate_awg_files():
                return {'success': False, 'error': 'Failed to generate AWG files'}
            
            # Step 4: Setup ADwin for photon counting
            if not self._setup_adwin_counting():
                return {'success': False, 'error': 'Failed to setup ADwin counting'}
            
            # Step 5: Determine frequency range
            if frequency_range is None:
                frequency_range = [self.microwave_frequency]
            
            # Step 6: Run experiment for each frequency
            results = {
                'success': True,
                'frequencies': frequency_range,
                'signal_counts': [],
                'reference_counts': [],
                'total_counts': []
            }
            
            for freq in frequency_range:
                self.logger.info(f"Running experiment at {freq/1e9:.3f} GHz")
                
                # Set SG384 frequency
                if 'sg384' in self.devices:
                    self.devices['sg384'].set_frequency(freq)
                    self.devices['sg384'].set_power(self.microwave_power)
                    self.logger.info(f"Set SG384 to {freq/1e9:.3f} GHz, {self.microwave_power} dBm")
                
                # Run sequence and collect data
                freq_results = self._run_sequence_and_collect_data()
                if not freq_results['success']:
                    return {'success': False, 'error': f'Failed at frequency {freq/1e9:.3f} GHz: {freq_results["error"]}'}
                
                results['signal_counts'].append(freq_results['signal_counts'])
                results['reference_counts'].append(freq_results['reference_counts'])
                results['total_counts'].append(freq_results['total_counts'])
            
            self.logger.info("ODMR Pulsed Experiment completed successfully")
            return results
            
        except Exception as e:
            self.logger.error(f"Experiment failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def _setup_adwin_counting(self) -> bool:
        """
        Setup ADwin for photon counting using the measure_protocol.bas process.
        
        Returns:
            True if setup successful
        """
        try:
            if 'adwin' not in self.devices:
                self.logger.error("ADwin device not available")
                return False
            
            adwin = self.devices['adwin']
            
            # Load the measure_protocol.bas process (Process 2)
            # This process handles dual-gate counting triggered by AWG520
            process_file = "measure_protocol.__2"
            adwin.load_process(process_file)
            
            # Set ADwin parameters for counting
            # Par_3: count_time (with calibration offset)
            # Par_4: reset_time (with calibration offset) 
            # Par_5: repetitions_per_point
            count_time_calibrated = self.count_time + 10  # Add calibration offset
            reset_time_calibrated = self.reset_time + 30  # Add calibration offset
            
            adwin.set_parameter(3, count_time_calibrated)
            adwin.set_parameter(4, reset_time_calibrated)
            adwin.set_parameter(5, self.repetitions_per_point)
            
            # Start the counting process
            adwin.start_process(process_file)
            
            self.logger.info(f"ADwin counting setup: count_time={self.count_time}ns, reset_time={self.reset_time}ns, reps={self.repetitions_per_point}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to setup ADwin counting: {e}")
            return False
    
    def _run_sequence_and_collect_data(self) -> Dict[str, Any]:
        """
        Run a single sequence and collect photon counting data from ADwin.
        
        Returns:
            Dictionary with signal_counts, reference_counts, total_counts
        """
        try:
            if 'awg520' not in self.devices:
                return {'success': False, 'error': 'AWG520 device not available'}
            
            if 'adwin' not in self.devices:
                return {'success': False, 'error': 'ADwin device not available'}
            
            awg = self.devices['awg520']
            adwin = self.devices['adwin']
            
            # Start AWG520 sequence (this will trigger ADwin via markers)
            # The AWG520 should be configured to use external triggering
            # and the sequence should include proper marker outputs for ADwin triggering
            awg.start_sequence()
            
            # Wait for sequence to complete and collect data
            # The ADwin measure_protocol.bas process accumulates counts
            # and stores them in Par_1 (signal) and Par_2 (reference) after each scan point
            
            signal_counts = []
            reference_counts = []
            total_counts = []
            
            # Collect data for each sequence point
            for i in range(len(self.scan_sequences)):
                # Wait for ADwin to complete counting for this sequence point
                # The measure_protocol.bas process will increment Par_10 when done
                max_wait_time = 10.0  # seconds
                wait_time = 0.0
                while wait_time < max_wait_time:
                    scan_point = adwin.get_parameter(10)  # Current scan point
                    if scan_point > i:
                        break
                    time.sleep(0.1)
                    wait_time += 0.1
                
                if wait_time >= max_wait_time:
                    self.logger.warning(f"Timeout waiting for scan point {i}")
                
                # Read accumulated counts from ADwin
                signal_count = adwin.get_parameter(1)  # Par_1: signal counts
                reference_count = adwin.get_parameter(2)  # Par_2: reference counts
                total_count = signal_count + reference_count
                
                signal_counts.append(signal_count)
                reference_counts.append(reference_count)
                total_counts.append(total_count)
                
                self.logger.info(f"Scan point {i}: signal={signal_count}, reference={reference_count}, total={total_count}")
            
            # Stop AWG520
            awg.stop_sequence()
            
            return {
                'success': True,
                'signal_counts': signal_counts,
                'reference_counts': reference_counts,
                'total_counts': total_counts
            }
            
        except Exception as e:
            self.logger.error(f"Failed to run sequence and collect data: {e}")
            return {'success': False, 'error': str(e)}
    
    def create_example_odmr_sequence(self) -> str:
        """
        Create an example ODMR sequence using the sequence language.
        
        Returns:
            Sequence text in the sequence language format
        """
        sequence_text = """
sequence: name=odmr_pulsed, type=odmr, duration=2μs, sample_rate=1GHz, repeat=50000

# Define scan variables (single variable for simplicity)
variable pulse_duration, start=50ns, stop=500ns, steps=20

# Define the ODMR pulse sequence
# pi/2 pulse for initialization (duration will be varied by the scanner)
# Channel 1: IQ modulator I input (microwave pulses)
pi/2 pulse on channel 1 at 0ns, gaussian, 100ns, 1.0

# pi pulse for refocusing (duration will be varied by the scanner)
pi pulse on channel 1 at 200ns, gaussian, 100ns, 1.0

# Channel 2: IQ modulator Q input (for complex microwave pulses)
# For simple ODMR, we can use channel 2 for additional microwave control
# or leave it empty if not needed

# Laser control via AWG520 markers:
# ch1_marker2: laser_switch (triggers laser on/off)
# ch2_marker2: counter_trigger (triggers ADwin counting)
# Note: Marker control is handled automatically by the AWG520SequenceOptimizer
# based on the connection template and pulse types
"""
        return sequence_text.strip()
    
    def create_example_rabi_sequence(self) -> str:
        """
        Create an example Rabi sequence using the sequence language.
        
        Returns:
            Sequence text in the sequence language format
        """
        sequence_text = """
sequence: name=rabi_pulsed, type=rabi, duration=1μs, sample_rate=1GHz, repeat=50000

# Define scan variables
variable pulse_duration, start=10ns, stop=200ns, steps=20

# Define the Rabi pulse sequence
# Single microwave pulse with variable duration (will be varied by the scanner)
# Channel 1: IQ modulator I input (microwave pulses)
pi/2 pulse on channel 1 at 0ns, gaussian, 50ns, 1.0

# Channel 2: IQ modulator Q input (for complex microwave pulses)
# For simple Rabi, we can use channel 2 for additional microwave control
# or leave it empty if not needed

# Laser control via AWG520 markers:
# ch1_marker2: laser_switch (triggers laser on/off)
# ch2_marker2: counter_trigger (triggers ADwin counting)
# Note: Marker control is handled automatically by the AWG520SequenceOptimizer
# based on the connection template and pulse types
"""
        return sequence_text.strip()
    
    def get_experiment_summary(self) -> Dict[str, Any]:
        """
        Get summary of experiment configuration.
        
        Returns:
            Dictionary with experiment summary
        """
        return {
            'name': 'ODMR Pulsed Experiment',
            'sequence_name': self.sequence_description.name if self.sequence_description else 'None',
            'scan_points': len(self.scan_sequences),
            'microwave_frequency_ghz': self.microwave_frequency / 1e9,
            'microwave_power_dbm': self.microwave_power,
            'laser_power_mw': self.laser_power,
            'laser_wavelength_nm': self.laser_wavelength,
            'delays_ns': {
                'mw': self.mw_delay,
                'aom': self.aom_delay,
                'counter': self.counter_delay
            },
            'adwin_parameters': self.get_adwin_parameters(),
            'output_directory': str(self.output_dir)
        }


class SequencePreviewWindow:
    """Window for previewing sequence scan points."""
    
    def __init__(self, sequences: List[Sequence], description):
        """Initialize preview window."""
        self.sequences = sequences
        self.description = description
        self.window = None
        
    def show(self):
        """Show the preview window."""
        # Create main window
        self.window = tk.Tk()
        self.window.title("ODMR Pulsed Sequence Preview")
        self.window.geometry("800x600")
        
        # Create notebook for different views
        notebook = ttk.Notebook(self.window)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Tab 1: Sequence overview
        overview_frame = ttk.Frame(notebook)
        notebook.add(overview_frame, text="Overview")
        self._create_overview_tab(overview_frame)
        
        # Tab 2: Sequence plots
        plots_frame = ttk.Frame(notebook)
        notebook.add(plots_frame, text="Plots")
        self._create_plots_tab(plots_frame)
        
        # Tab 3: Parameters
        params_frame = ttk.Frame(notebook)
        notebook.add(params_frame, text="Parameters")
        self._create_parameters_tab(params_frame)
        
        # Show window
        self.window.mainloop()
    
    def _create_overview_tab(self, parent):
        """Create overview tab."""
        # Sequence info
        info_frame = ttk.LabelFrame(parent, text="Sequence Information", padding=10)
        info_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(info_frame, text=f"Name: {self.description.name}").pack(anchor='w')
        ttk.Label(info_frame, text=f"Total scan points: {len(self.sequences)}").pack(anchor='w')
        ttk.Label(info_frame, text=f"Variables: {len(self.description.variables)}").pack(anchor='w')
        ttk.Label(info_frame, text=f"Pulses per sequence: {len(self.description.pulses)}").pack(anchor='w')
        
        # Variables info
        if self.description.variables:
            var_frame = ttk.LabelFrame(parent, text="Scan Variables", padding=10)
            var_frame.pack(fill='x', padx=10, pady=5)
            
            for var in self.description.variables:
                var_text = f"{var.name}: {var.start_value} to {var.stop_value} ({var.steps} steps)"
                ttk.Label(var_frame, text=var_text).pack(anchor='w')
    
    def _create_plots_tab(self, parent):
        """Create plots tab."""
        # Create matplotlib figure
        fig, ax = plt.subplots(figsize=(8, 6))
        fig.canvas.draw()
        
        # Embed in tkinter
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        canvas = FigureCanvasTkAgg(fig, parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)
        
        # Plot first few sequences
        if self.sequences:
            self.sequence_builder.animate_scan_sequences(
                self.sequences[:min(5, len(self.sequences))],
                ax=ax,
                title="Sequence Preview (First 5 Points)"
            )
    
    def _create_parameters_tab(self, parent):
        """Create parameters tab."""
        # Parameters info
        params_frame = ttk.LabelFrame(parent, text="Experiment Parameters", padding=10)
        params_frame.pack(fill='x', padx=10, pady=5)
        
        # This would show the current experiment parameters
        ttk.Label(params_frame, text="Microwave frequency: 2.87 GHz").pack(anchor='w')
        ttk.Label(params_frame, text="Microwave power: -10 dBm").pack(anchor='w')
        ttk.Label(params_frame, text="Laser power: 1.0 mW").pack(anchor='w')
        ttk.Label(params_frame, text="Laser wavelength: 532 nm").pack(anchor='w')
        ttk.Label(params_frame, text="MW delay: 25 ns").pack(anchor='w')
        ttk.Label(params_frame, text="AOM delay: 50 ns").pack(anchor='w')
        ttk.Label(params_frame, text="Counter delay: 15 ns").pack(anchor='w')


# Example usage and testing
if __name__ == "__main__":
    # Create experiment with mock devices for testing
    from unittest.mock import MagicMock
    
    mock_devices = {
        'awg520': MagicMock(),
        'adwin': MagicMock(),
        'sg384': MagicMock()
    }
    
    experiment = ODMRPulsedExperiment(devices=mock_devices, name="test_odmr")
    
    # Set parameters
    experiment.set_microwave_parameters(2.87e9, -10.0, 25.0)
    experiment.set_laser_parameters(1.0, 532)
    experiment.set_delay_parameters(25.0, 50.0, 15.0)
    
    # Create and load example sequence
    sequence_text = experiment.create_example_odmr_sequence()
    print("Example ODMR Sequence:")
    print(sequence_text)
    print("\n" + "="*50 + "\n")
    
    if experiment.load_sequence_from_text(sequence_text):
        print("✅ Sequence loaded successfully")
        
        # Build sequences
        if experiment.build_scan_sequences():
            print("✅ Scan sequences built successfully")
            
            # Generate AWG files
            if experiment.generate_awg_files():
                print("✅ AWG files generated successfully")
                
                # Run experiment (with mock devices)
                print("Running experiment with mock devices...")
                results = experiment.run_experiment(frequency_range=[2.87e9, 2.88e9, 2.89e9])
                
                if results['success']:
                    print("✅ Experiment completed successfully!")
                    print(f"Frequencies scanned: {[f/1e9 for f in results['frequencies']]} GHz")
                    print(f"Signal counts shape: {len(results['signal_counts'])} frequencies x {len(results['signal_counts'][0])} points")
                else:
                    print(f"❌ Experiment failed: {results['error']}")
            else:
                print("❌ Failed to generate AWG files")
        else:
            print("❌ Failed to build scan sequences")
    else:
        print("❌ Failed to load sequence")
    
    print("\nODMR Pulsed Experiment ready!")
