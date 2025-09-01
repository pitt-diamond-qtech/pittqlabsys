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
        'adwin': 'adwin'
    }
    
    _EXPERIMENTS = {}
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize the ODMR Pulsed experiment."""
        super().__init__()
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.config_path = config_path or Path("config.json")
        self.config = self._load_config()
        
        # Sequence components
        self.sequence_parser = SequenceTextParser()
        self.sequence_builder = SequenceBuilder()
        self.hardware_calibrator = HardwareCalibrator()
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
        self.output_dir = Path("odmr_pulsed_output")
        self.output_dir.mkdir(exist_ok=True)
        
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
        Generate AWG520 waveform and sequence files.
        
        Returns:
            True if files generated successfully
        """
        try:
            if not self.scan_sequences:
                self.logger.error("No scan sequences available")
                return False
            
            # Create AWG file handler
            awg_file = AWGFile(out_dir=self.output_dir)
            
            # Generate waveforms for each sequence
            waveform_files = []
            for i, sequence in enumerate(self.scan_sequences):
                # Optimize sequence for AWG520
                optimized_sequence = self.awg_optimizer.optimize_sequence_for_awg520(sequence)
                
                # Generate waveform file
                wfm_path = awg_file.write_waveform(
                    optimized_sequence, 
                    f"scan_point_{i:03d}"
                )
                waveform_files.append(wfm_path)
                self.logger.info(f"Generated waveform: {wfm_path}")
            
            # Generate sequence file
            sequence_entries = []
            for i, wfm_path in enumerate(waveform_files):
                # Format: ch1_wfm, ch2_wfm, repeat, wait, goto, logic
                entry = (
                    wfm_path.name,           # ch1_wfm
                    wfm_path.name,           # ch2_wfm (same for now)
                    self.repetitions_per_point,  # repeat count
                    0,                       # wait (no wait)
                    (i + 1) % len(waveform_files) + 1,  # goto next
                    0                        # logic (no logic)
                )
                sequence_entries.append(entry)
            
            # Create sequence file
            seq_path = awg_file.write_sequence(
                sequence_entries,
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
    
    def run_experiment(self) -> bool:
        """
        Run the complete ODMR pulsed experiment.
        
        Returns:
            True if experiment completed successfully
        """
        try:
            self.logger.info("Starting ODMR Pulsed Experiment")
            
            # Step 1: Load sequence
            if not self.sequence_description:
                self.logger.error("No sequence loaded")
                return False
            
            # Step 2: Build scan sequences
            if not self.build_scan_sequences():
                return False
            
            # Step 3: Generate AWG files
            if not self.generate_awg_files():
                return False
            
            # Step 4: Show preview (optional)
            # self.show_sequence_preview()
            
            # Step 5: Start AWG520 (this would integrate with AWG520 driver)
            self.logger.info("AWG files generated successfully")
            self.logger.info("Ready to start AWG520 sequence")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Experiment failed: {e}")
            return False
    
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
    # Create experiment
    experiment = ODMRPulsedExperiment()
    
    # Set parameters
    experiment.set_microwave_parameters(2.87e9, -10.0, 25.0)
    experiment.set_laser_parameters(1.0, 532)
    experiment.set_delay_parameters(25.0, 50.0, 15.0)
    
    # Load sequence from file (example)
    sequence_file = Path("example_sequence.txt")
    if sequence_file.exists():
        experiment.load_sequence_from_file(sequence_file)
        
        # Build sequences
        if experiment.build_scan_sequences():
            # Show preview
            experiment.show_sequence_preview()
            
            # Generate AWG files
            experiment.generate_awg_files()
    
    print("ODMR Pulsed Experiment ready!")
