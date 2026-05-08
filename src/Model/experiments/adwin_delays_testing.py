#!/usr/bin/env python3
"""
This runs adwin file to measure T1 time without the need of an awg (connect adwin DIGOUT 28 to AOM directly)
"""

from __future__ import annotations
from typing import Dict, Any, Optional
from pathlib import Path
import json
import logging
import time
from src.Controller import SG384Generator
from src.core.experiment import Experiment
from src.core import Parameter
from src.Model.sequence_parser import SequenceTextParser
from src.Model.sequence_builder import SequenceBuilder
from src.Model.proteus_hardware_calibrator import ProteusHardwareCalibrator
from src.core.struct_hdf5 import MyStruct
from src.Controller.Proteus_device import ProteusDevice
from src.Controller.adwin_gold import AdwinGoldDevice
from src.Controller.mux_control import MUXControlDevice
import numpy as np
from src.core.adwin_helpers import get_adwin_binary_path


class ODMRPulsedExperiment(Experiment):
    """
    Pulsed ODMR experiment using Proteus for sequence generation and ADwin for counting.

    Features:
    - Text-based sequence definition using the sequence language
    - Sequence preview with first 10 scan points
    - Microwave frequency and power
    - Laser power and wavelength configuration
    - Proteus triggers ADwin for photon counting
    """
    _DEFAULT_SETTINGS = [
        Parameter('sequence', [
            Parameter('file_path', "D:\Data\jannet_trabelsi\March2026\odmr_sequence.txt", str,
                      'Path to sequence definition file'),
            Parameter('load_from_file', False, bool, 'load the sequence from a file'),
            Parameter('text',
                      "sequence: name=odmr_pulsed, type=odmr, duration=1002500ns, sample_rate=1GHz, repeat_count=50000\nvariable pulse_duration, start=50ns, stop=500ns, steps=20\nmarker, laser_int_1 on channel 1 at 0ns, 500ns\npi/2 pulse on channel 1 at 500ns, gaussian, pulse_duration, 1.0\npi/2 pulse on channel 2 at 500ns, gaussian, pulse_duration, 1.0 \nwait pulse on channel 1 at pulse_duration+0.000000500, square, 2*pulse_duration, 0.0\nwait pulse on channel 2 at pulse_duration+0.000000500, square, 2*pulse_duration, 0.0\npi/2 pulse on channel 1 at 3*pulse_duration+0.000000500, gaussian, pulse_duration, 1.0\npi/2 pulse on channel 2 at 3*pulse_duration+0.000000500, gaussian, pulse_duration, 1.0\nmarker, laser_readout_1 on channel 1 at 2500ns, 1ms\nmarker, readout_counts_1 on channel 2 at 2500ns, 300ns\nmarker, reference_counts_1 on channel 2 at 1002200ns, 300ns",
                      str, 'sequence_text')
        ]),
        Parameter('microwave', [
            Parameter('frequency range', [2.87e9], list, 'Microwave frequency in Hz', units='Hz'),
            Parameter('power', -10.0, float, 'Microwave power in dBm', units='dBm')
        ]),
        Parameter('green_laser', [
            Parameter('power', 1.0, float, 'Green Laser power in mW', units='mW'),
            Parameter('wavelength', 532.0, float, 'Green Laser wavelength in nm', units='nm')
        ]),
        Parameter('delays', [
            Parameter('green_laser_delay', 6265.0, float, 'green_laser_delay in ns', units='ns'),
            Parameter('mw_delay', 25.0, float, 'Microwave delay in ns', units='ns'),
            Parameter('iq_delay', 30.0, float, 'iq delay in ns', units='ns'),
            Parameter('counter_delay', 15.0, float, 'AOM delay in ns', units='ns'),
            Parameter('trigger_delay', 0.0, float, 'Counter delay in ns', units='ns')
        ]),
        Parameter('adwin', [
            Parameter('count_time', 300, float, 'Photon counting time in ns', units='ns'),
            Parameter('reset_time', 0, float, 'Reset time between counts in ns', units='ns')]),
        Parameter('proteus', [
            Parameter('proteus_response_delay', 306.5, float, 'proteus response delay to triggers in ns', units='ns')]),
        Parameter('scan', [
            Parameter('preview_points', 10, int, 'Number of scan points to preview'),
            Parameter('auto_generate_files', True, bool, 'Automatically generate AWG files'),
            Parameter('output_directory', 'odmr_pulsed_output', str, 'Output directory for AWG files')
        ]),
        Parameter('path', "D:\Data"),
        Parameter('filename', "odmr_pulsed_output"),
        Parameter('tag', "odmrpulsedexperiment"),
        Parameter('save', False)
    ]

    _DEVICES = {
        'proteus': 'proteus',
        'adwin': 'adwin',
        'sg384': 'sg384',
        'mux_control': 'mux_control'
    }

    _EXPERIMENTS = {}

    def __init__(self, devices=None, experiments=None, name=None, settings=None, log_function=None, data_path=None,
                 config_path: Optional[Path] = None):
        """Initialize the ODMR Pulsed experiment."""
        super().__init__(name=name, settings=settings, devices=devices, sub_experiments=experiments,
                         log_function=log_function, data_path=data_path)
        # Setup logging
        self.logger = logging.getLogger(__name__)
        self.repeat_count = None
        self.number_of_iterations = 0
        self.config_path = config_path or self.get_config_path(
            "D:\\Duttlab\\Experiments\\AQuISS_default_save_location\\experiments_auto_generated\\ODMRPulsedExperiment.json")
        # Configuration
        self.config = self._load_config()
        self.sequence_text = None

        # Sequence components
        self.sequence_parser = SequenceTextParser()
        self.sequence_builder = SequenceBuilder()

        # Initialize hardware calibrator with experiment-specific connection file
        connection_file = Path(__file__).parent / "odmr_pulsed_connection.json"
        self.hardware_calibrator = ProteusHardwareCalibrator(connection_file=str(connection_file))
        """self.adwin = self.devices['adwin']['instance']
        self.proteus = self.devices['proteus']['instance']
        self.sg384 = self.devices['sg384']['instance']
        self.mux = self.devices['mux_control']['instance']"""
        self.proteus = ProteusDevice()
        self.adwin = AdwinGoldDevice()
        self.mux = MUXControlDevice()
        self.sg384 = SG384Generator()
        self.mux.select_trigger('pulsed')
        # Sequence data
        self.sequence_description = None
        self.scan_sequences = []
        self.current_scan_point = 0

        # ADwin parameters
        self.count_time = self.settings["adwin"]["count_time"]  # ns
        self.reset_time = self.settings["adwin"]["reset_time"]  # ns
        self.sequence_duration = 1700  # just a placeholder
        self.proteus_response_delay = self.settings["proteus"][
            "proteus_response_delay"]  # ns we tested this by running test_adwin_delays : 21 digout - 16 digout = 57.5 ns and 21 - proteus = 364 ns (when digout 16 is used to trigger proteus) and since we pad the zeros at the end, proteus delay should be relatively constant

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

    def save_hdf5(self):
        """this function defines its custom data and metadata to be saved and then calls the
        save_hdf_data function that is in the parent Experiment class, which adds the external
        devices in case you ever check the Get Basic Data checkbox in the GUI"""
        structure_to_save = MyStruct()
        structure_to_save.data = MyStruct(
            signal_counts=self.signal_counts,
            reference_counts=self.reference_counts,
            total_counts=self.total_counts
        )
        structure_to_save.meta = MyStruct(
            count_time=self.count_time,
            number_of_iterations=self.number_of_iterations,
            repeat_count=self.repeat_count,
            sequence_duration=self.sequence_duration,
            laser_init = self.laser_init
        )
        self.save_hdf_data(structure_to_save)

    def _setup_adwin_counting(self) -> bool:
        """
        Setup ADwin for photon counting using the odmr_pulsed_counter.bas process.

        Returns:
            True if setup successful
        """
        try:
            print("Setting ADwin counting")
            # Load the odmr_pulsed_counter.bas process (Process 2)
            # This process handles dual-gate counting triggered by Proteus
            # process_file = "odmr_pulsed_counter.__2"
            process_number = 1

            if not self.adwin.is_connected:
                self.adwin.connect()
                print("adwin connected")

            # Proper cleanup like debug script
            self.log("Cleaning up any existing ADwin process...")
            try:
                self.adwin.stop_process(process_number)
                time.sleep(0.1)
            except Exception:
                pass
            try:
                self.adwin.clear_process(process_number)
            except Exception:
                pass
            odmr_pulsed_counter_path = get_adwin_binary_path('ADWIN_T1_DIGITAL.TB1')
            #odmr_pulsed_counter_path = get_adwin_binary_path('test_adwin_delays.TB1')
            self.adwin.update({'process_1': {'load': str(odmr_pulsed_counter_path)}})
            # Set ADwin parameters for counting
            self.repeat_count = 50000
            self.number_of_iterations = 20
            #self.sequence_duration = 450002600
            self.sequence_duration = 502600
            self.count_time = 300
            self.laser_init = 2000
            self.adwin.set_int_var(3, self.count_time)
            self.adwin.set_int_var(4, self.laser_init)
            self.adwin.set_int_var(5, self.repeat_count)
            self.adwin.set_int_var(6, self.number_of_iterations)
            self.adwin.set_int_var(9, self.sequence_duration)
            self.adwin.set_int_var(11, 1)
            # Start the counting process
            self.adwin.start_process(process_number)
            time.sleep(0.1)  # Give process time to start
            self.logger.info(
                f"ADwin counting setup: count_time={self.count_time}ns, reset_time={self.reset_time}ns, reps={self.repeat_count}")
            # Wait for sequence to complete and collect data
            # The ADwin adwin_triggering_proteus.bas process accumulates counts
            # and stores them in arrays Data_1[iteration] (signal) and Data_2[iteration] (reference)

            # Collect data
            # this method has python collecting data and telling aadwin to stop:
            # Collect data
            wait_time = self.sequence_duration + 936.65
            wait_time = wait_time * self.repeat_count * self.number_of_iterations  # remember: wait_time is in ns
            wait_time = wait_time * (10 ** (-9))
            print(f"wait time: {wait_time}")
            # wait for length of the entire experiment, then get the data
            time.sleep(wait_time)
            # After time.sleep(wait_time)
            input(
                f"\n=== Wait time finished ({wait_time:.2f} seconds) ===\nPress Enter to collect data or Ctrl+C to cancel...")
            print(f"self.adwin.get_int_var(8): {self.adwin.get_int_var(8)}")
            self.signal_counts = np.array(self.adwin.get_int_data(1, self.number_of_iterations), dtype=np.int64)
            self.total_counts = np.array(self.adwin.get_int_data(2, self.number_of_iterations), dtype=np.int64)
            self.ref_counts = self.total_counts.astype(np.int64) - self.signal_counts.astype(np.int64)
            for signal_counts_val in self.signal_counts:
                self.logger.info(f"signal_counts_val {signal_counts_val}")
                print(f"signal_counts_val {signal_counts_val}")
            for reference_counts_val in self.ref_counts:
                self.logger.info(f"reference_counts_val {reference_counts_val}")
                print(f"reference_counts_val {reference_counts_val}")
            for total_counts_val in self.total_counts:
                self.logger.info(f"total_counts_val {total_counts_val}")
                print(f"total_counts_val {total_counts_val}")
            print(f"end of _run_sequence_and_collect_data()")
            self.save_hdf5()

        except Exception as e:
            self.logger.error(f"Failed to setup ADwin counting: {e}")
            return False

    def _update(self):
        pass


# Example usage and testing
if __name__ == "__main__":
    # Create experiment for testing
    experiment = ODMRPulsedExperiment(name="test_odmr")

    # Set parameters
    experiment._setup_adwin_counting()