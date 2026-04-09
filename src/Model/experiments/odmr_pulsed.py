#!/usr/bin/env python3
"""
ODMR Pulsed Experiment

This experiment implements pulsed ODMR measurements using the Proteus for
sequence generation and ADwin for photon counting. Users can specify
sequences using a text-based language and preview scan results.
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional, Tuple, Union
from pathlib import Path
import json
import os
import logging
import time
import matplotlib.pyplot as plt
from fontTools.misc.plistlib import end_data
from matplotlib.animation import FuncAnimation
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import datetime

from src.core.experiment import Experiment
from src.core import Parameter
from src.Model.sequence_parser import SequenceTextParser
from src.Model.sequence_builder import SequenceBuilder
from src.Model.proteus_hardware_calibrator import ProteusHardwareCalibrator
from src.Model.sequence import Sequence
from src.core.struct_hdf5 import MyStruct, save_data, StructArray
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
        Parameter('sequence',[
            Parameter('file_path', "D:\Data\jannet_trabelsi\March2026\odmr_sequence.txt", str, 'Path to sequence definition file'),
            Parameter('load_from_file', False, bool, 'load the sequence from a file'),
            Parameter('text',"sequence: name=odmr_pulsed, type=odmr, duration=1002500ns, sample_rate=1GHz, repeat_count=50000\nvariable pulse_duration, start=50ns, stop=500ns, steps=20\nmarker, laser_int_1 on channel 1 at 0ns, 500ns\npi/2 pulse on channel 1 at 500ns, gaussian, pulse_duration, 1.0\npi/2 pulse on channel 2 at 500ns, gaussian, pulse_duration, 1.0 \nwait pulse on channel 1 at pulse_duration+0.000000500, square, 2*pulse_duration, 0.0\nwait pulse on channel 2 at pulse_duration+0.000000500, square, 2*pulse_duration, 0.0\npi/2 pulse on channel 1 at 3*pulse_duration+0.000000500, gaussian, pulse_duration, 1.0\npi/2 pulse on channel 2 at 3*pulse_duration+0.000000500, gaussian, pulse_duration, 1.0\nmarker, laser_readout_1 on channel 1 at 2500ns, 1ms\nmarker, readout_counts_1 on channel 2 at 2500ns, 300ns\nmarker, reference_counts_1 on channel 2 at 1002200ns, 300ns"
        )]),
        Parameter('microwave', [
            Parameter('frequency range', [2.87e9], list, 'Microwave frequency in Hz', units='Hz'),
            Parameter('power', -10.0, float, 'Microwave power in dBm', units='dBm')
        ]),
        Parameter('green_laser', [
            Parameter('power', 1.0, float, 'Green Laser power in mW', units='mW'),
            Parameter('wavelength', 532.0, float, 'Green Laser wavelength in nm', units='nm')
        ]),
        Parameter('delays', [
            Parameter('green_laser_delay', 50.0, float, 'green_laser_delay in ns', units='ns'),
            Parameter('mw_delay', 25.0, float, 'Microwave delay in ns', units='ns'),
            Parameter('iq_delay', 30.0, float, 'iq delay in ns', units='ns'),
            Parameter('counter_delay', 15.0, float, 'AOM delay in ns', units='ns'),
            Parameter('trigger_delay', 0.0, float, 'Counter delay in ns', units='ns')
        ]),
        Parameter('adwin', [
            Parameter('count_time', 300, float, 'Photon counting time in ns', units='ns'),
            Parameter('reset_time', 150, float, 'Reset time between counts in ns', units='ns')        ]),
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
    
    def __init__(self, devices=None, experiments=None, name=None, settings=None, log_function=None, data_path=None, config_path: Optional[Path] = None):
        """Initialize the ODMR Pulsed experiment."""
        super().__init__(name=name, settings=settings, devices=devices, sub_experiments=experiments, log_function=log_function, data_path=data_path)
        # Setup logging
        self.logger = logging.getLogger(__name__)
        self.repeat_count = None
        self.number_of_iterations = 0
        self.config_path = config_path or self.get_config_path("D:\\Duttlab\\Experiments\\AQuISS_default_save_location\\experiments_auto_generated\\ODMRPulsedExperiment.json")
        # Configuration
        self.config = self._load_config()
        self.sequence_text = None

        # Sequence components
        self.sequence_parser = SequenceTextParser()
        self.sequence_builder = SequenceBuilder()

        # Initialize hardware calibrator with experiment-specific connection file
        connection_file = Path(__file__).parent / "odmr_pulsed_connection.json"
        self.hardware_calibrator = ProteusHardwareCalibrator(connection_file=str(connection_file))
        self.adwin = self.devices['adwin']['instance']
        self.proteus = self.devices['proteus']['instance']
        self.sg384 = self.devices['sg384']['instance']
        self.mux = self.devices['mux_control']['instance']
        self.mux.select_trigger('pulsed')
        # Sequence data
        self.sequence_description = None
        self.scan_sequences = []
        self.current_scan_point = 0

        # ADwin parameters
        self.count_time = self.settings["adwin"]["count_time"]  # ns
        self.reset_time = self.settings["adwin"]["reset_time"]  # ns
        self.sequence_duration = 1700  # just a placeholder
        self.proteus_response_delay = self.settings["proteus"]["proteus_response_delay"]  # ns we tested this by running test_adwin_delays : 21 digout - 16 digout = 57.5 ns and 21 - proteus = 364 ns (when digout 16 is used to trigger proteus) and since we pad the zeros at the end, proteus delay should be relatively constant

        #self.adwin = AdwinGoldDevice()
        #self.proteus = ProteusDevice()
        #self.proteus = None
        # self.mux = self.devices['mux']['instance']
        #self.mux = MUXControlDevice()
    
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
    
    def load_sequence_from_text(self) -> bool:
        """
        Load sequence definition from text using the sequence language.
        
        Args:
            sequence_text: Sequence definition in the sequence language format
            
        Returns:
            True if sequence loaded successfully
        """
        try:
            # Parse sequence text using the sequence language parser
            self.sequence_description = self.sequence_parser.parse_text(self.sequence_text)
            self.repeat_count = self.sequence_description.repeat_count
            print("self.sequence_description.total_duration")
            print(self.sequence_description.total_duration)
            if self.sequence_description:
                self.logger.info(f"Sequence loaded: {self.sequence_description.name}")
                self.logger.info(f"Variables: {len(self.sequence_description.variables)}")
                self.logger.info(f"Pulses: {len(self.sequence_description.pulses)}")
                self.logger.info(f"Markers: {len(self.sequence_description.markers)}")
                return True
            else:
                self.logger.error("Failed to parse sequence text")
                print("Failed to parse sequence text")
                return False
                
        except Exception as e:
            self.logger.error(f"Error loading sequence: {e}")
            print(f"Error loading sequence: {e}")
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
            print("load_sequence_from_file")
            if not sequence_file.exists():
                self.logger.error(f"Sequence file not found: {sequence_file}")
                print("Sequence file not found")
                return False
            
            # Read sequence text
            with open(sequence_file, 'r') as f:
                print("reading from file")
                self.sequence_text = f.read()
            print("parsing sequence text")
            # Parse sequence
            self.sequence_description = self.sequence_parser.parse_text(self.sequence_text)
            self.repeat_count = self.sequence_description.repeat_count
            
            if self.sequence_description:
                self.logger.info(f"Sequence loaded: {self.sequence_description.name}")
                self.logger.info(f"Variables: {len(self.sequence_description.variables)}")
                self.logger.info(f"Pulses: {len(self.sequence_description.pulses)}")
                self.logger.info(f"Markers: {len(self.sequence_description.markers)}")
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
            self.sampling_rate = self.sequence_builder.sample_rate
            if self.sequence_description.variables:
                for seq in self.scan_sequences:
                    self.number_of_iterations += 1
            else:
                self.number_of_iterations = 1

            # Apply hardware calibration
            for i, sequence in enumerate(self.scan_sequences):
                calibrated_sequence = self.hardware_calibrator.calibrate_sequence(
                    sequence,
                    self.sequence_description.sample_rate
                )
                self.scan_sequences[i] = calibrated_sequence
            self.sequence_duration = calibrated_sequence.length
            print(f"calibrated_sequence duration {self.sequence_duration}")
            self.logger.info(f"Built {len(self.scan_sequences)} scan sequences")
            return True
            
        except Exception as e:
            self.logger.error(f"Error building scan sequences: {e}")
            return False

    def generate_awg_task_sequences_adwin_triggering_awg_case(self) -> bool:
        """
        Generate Proteus AWG waveforms with maximum timing resolution.
        One continuous waveform per channel.
        one segment and one task entry per iteration per channel.
        64-sample alignment is applied at the end of each waveform.
        The advantage of this option is that adwin does the counts then it tells proteus
        to move to the next sequence. This ensures that counts are measured as expected.
        """

        def prepare_markers_for_tabor(markers_array: np.ndarray) -> np.ndarray:
            """
            Correct Proteus marker packing for 16-bit DAC mode.
            markers_array: 1 marker value per waveform sample (0 or 255)
            """

            # Convert to binary 0/1
            m = (markers_array > 0).astype(np.uint8)

            # Ensure multiple of 4 samples
            # pad at the end:
            if len(m) % 4 != 0:
                m = np.pad(m, (0, 4 - len(m) % 4))

            # One marker byte per 4 waveform samples
            marker_bytes = np.zeros(len(m) // 4, dtype=np.uint8)

            for i in range(len(marker_bytes)):
                block = m[i * 4:(i + 1) * 4]

                if np.any(block):
                    # Marker 1 ON for all 4 samples → 0b00010001
                    marker_bytes[i] = 0x11
                else:
                    marker_bytes[i] = 0x00

            return marker_bytes

        try:
            if not self.scan_sequences:
                self.logger.error("No scan sequences available")
                return False
            # ------------------------------------------------------------
            # DAC configuration
            # ------------------------------------------------------------
            max_dac = 65535
            half_dac = max_dac // 2
            ALIGNMENT = 64  # Proteus requirement (segment length)

            # ------------------------------------------------------------
            # Determine all channels, initialize buffers
            # ------------------------------------------------------------
            all_channels = set()
            channels = set()
            marker_indices = set()
            marker_channels = set()
            for sequence in self.scan_sequences:
                for _, pulse_ in enumerate(sequence.pulses):
                    pulse = pulse_[1]
                    ch = int(pulse.name.split("_")[-1])
                    channels.add(ch)
                    all_channels.add(ch)

                for marker in sequence.markers:
                    mkr_index = int(marker.name.split('_')[-2])
                    marker_indices.add(mkr_index)
                    mk_ch = int(marker.name.split("_")[-1])
                    marker_channels.add(mk_ch)
                    all_channels.add(mk_ch)

            segment_for_channel = {ch: set() for ch in all_channels}
            padded_zeros = {
                ch: 0 for ch in all_channels
            }
            max_delay = {
                it: 0 for it in range(self.number_of_iterations)
            }

            # ------------------------------------------------------------
            # Build continuous waveform per channel (sample-accurate)
            # ------------------------------------------------------------
            SEGNUM = 1
            for sequence in self.scan_sequences:
                seq_waveforms = sequence.to_waveform()
                for ch, data in seq_waveforms.items():
                    self.proteus.driver.set_channel(ch)
                    #self.proteus.driver.delete_all_segment()
                    analog_voltage = "MAX"
                    self.proteus.driver.set_voltage(analog_voltage)

                    self.proteus.driver.apply_sampling_configuration(self.sampling_rate)
                    # so far envelope is a sum of pulses in a single iteration
                    # but we need to add another for loop inside items to get pulses and their timing
                    envelope = data["envelope"]
                    markers = data["markers"]
                    """import matplotlib.pyplot as plt
                    import numpy as np

                    samples = np.arange(len(envelope))

                    fig, ax = plt.subplots(2, 1, sharex=True, figsize=(10, 4))

                    # Envelope plot
                    ax[0].plot(samples, envelope, color="blue")
                    ax[0].set_ylabel("Envelope")
                    ax[0].set_title("Envelope vs Samples")
                    ax[0].grid(True)

                    # Markers plot
                    ax[1].step(samples, markers, where="post", color="red")
                    ax[1].set_ylabel("Markers")
                    ax[1].set_xlabel("Sample index")
                    ax[1].set_title("Markers vs Samples")
                    ax[1].grid(True)

                    plt.tight_layout()
                    plt.show()"""

                    segment_num = SEGNUM
                    segment_for_channel[ch].add(segment_num)
                    rem = len(envelope) % ALIGNMENT
                    padded_zeros[ch] = rem
                    if rem:
                        # pad at the end
                        envelope = np.pad(envelope, (0, ALIGNMENT - rem))
                        markers = np.pad(markers, (0, ALIGNMENT - rem))
                        padded_zeros[ch] = ALIGNMENT - rem
                    # Scale to DAC
                    dac_wave = np.clip(envelope, -1.0, 1.0)
                    dac_wave = ((dac_wave+1.0) * half_dac).astype(np.uint16)
                    self.proteus.driver.define_trace(segment_num, len(dac_wave))
                    self.proteus.driver.select_segment(segment_num)

                    # Upload waveform
                    self.proteus.driver.write_trace_data(dac_wave)
                    resp = self.proteus.driver.query_error()
                    print(f"loading trace data {resp}")
                    self.proteus.driver.inst.send_scpi_cmd(":VOLT:OFFS 0.012")
                    print(f"offset: {self.proteus.driver.inst.send_scpi_query(":VOLT:OFFS?")}")

                    # Convert to uint8
                    markers = markers.astype(np.uint8)

                    # Now prepare for Tabor
                    tabor_markers = prepare_markers_for_tabor(markers)

                    self.proteus.driver.write_marker_data(tabor_markers)
                    resp = self.proteus.driver.query_error()
                    print(f'Marker upload result: {resp}')
                    # proteus P1284M only has 1 marker per channel, for other awgs, please implement code that handles that
                    # I have already coded the marker index here: mkr_index = int(marker.name.split('_')[-2]) so, for example, if the user
                    # gives the following command: "marker, laser_int_1 on channel 4 at 0ns, 500ns" then you know whatever is after "laser_init_" is the marker index
                    marker_index = 1
                    self.proteus.driver.set_marker(marker_index)
                    self.proteus.driver.set_marker_ptop_voltage(1.2) # 1.2
                    self.proteus.driver.set_marker_voltage_offset(0) # 0.5
                    # Check for errors
                    resp = self.proteus.driver.query_error()
                    print(f'Marker setup result: {resp}')
                    SEGNUM += 1
            i = 0
            for sequence in self.scan_sequences:
                seq_waveforms = sequence.to_waveform()
                for ch1, data1 in seq_waveforms.items():
                    for ch2, data2 in seq_waveforms.items():
                        if padded_zeros[ch1] > padded_zeros[ch2] and padded_zeros[ch1]>max_delay[i]:
                            max_delay[i]=padded_zeros[ch1]
                        elif padded_zeros[ch2] > padded_zeros[ch1] and padded_zeros[ch2]>max_delay[i]:
                            max_delay[i]=padded_zeros[ch2]

                i += 1

            for ch in sorted(all_channels):
                self.proteus.driver.set_channel(ch)
                if ch in marker_channels:
                    self.proteus.driver.set_marker(1)
                    self.proteus.driver.set_marker_state('ON')
                if ch in channels:
                    self.proteus.driver.set_output("ON")
                #--self.proteus.driver.set_continuous_run(0)
            self.proteus.driver.set_trigger_level(2)
            self.proteus.driver.activate_instrument(1)
            for ch in sorted(all_channels):
                self.proteus.driver.set_channel(ch)
                self.proteus.driver.set_trigger_source('TRG1')
                self.proteus.driver.set_trigger("TRG1") # :TRIG:SEL
                self.proteus.driver.set_trigger_state("ON") # :TRIG:STAT

            for ch in sorted(all_channels):
                task_num = 1
                self.proteus.driver.set_channel(ch)
                self.proteus.driver.set_task_table_length(self.number_of_iterations)
                print(f"channel {ch}: {ch}")
                print(f"number of iterations: {self.number_of_iterations}")
                for segment_number in segment_for_channel[ch]:
                    print(f"channel: {ch} Segment: {segment_number}")
                    self.proteus.driver.set_task_number(task_num)
                    if task_num == 1:
                        self.proteus.driver.set_task_type("STAR") #--
                    elif task_num == self.number_of_iterations:
                        self.proteus.driver.set_task_type("END") #--
                    else:
                        self.proteus.driver.set_task_type("SEQ") #--
                    self.proteus.driver.set_task_segment_number(segment_number)
                    self.proteus.driver.set_trigger_IDLE_state("DC")
                    self.proteus.driver.set_trigger_IDLE_level(0)
                    if task_num == 1:
                        self.proteus.driver.set_enabling_task_signal("TRG1")
                    else:
                        self.proteus.driver.set_enabling_task_signal("TRG1")

                    if task_num == self.number_of_iterations:
                        self.proteus.driver.set_next1_task(1)
                    else:
                        self.proteus.driver.set_next1_task(task_num+1)

                    task_num+=1
                    #self.proteus.driver.set_task_delay(max_delay[task_num-2] - padded_zeros[ch])
                    print(f"max_delay[task_num-2] {max_delay[task_num - 2] }")
                    print(f"padded_zeros[ch] {padded_zeros[ch]}")

                    self.proteus.driver.write_composer_array_to_task_table()
                    self.proteus.driver.set_waveform_type('TASK')
                ###self.proteus.driver.set_task_loop(self.repeat_count)
            self.proteus.driver.set_task_sync()
            resp = self.proteus.driver.set_trigger_coupling('ON')
            print(resp)
            # for trigger source INT send:
            self.proteus.driver.set_channel(1)
            # trigger command:
            self.proteus.driver.trigger()
            #time.sleep(1)
            #self.proteus.driver._close()
            return True
        except Exception as e:
            self.logger.exception("Error generating AWG sequences")
            return False

    def _function(self):
        print("selected start")
        # new work to be tested:
        def build_calibration_overrides():
            return {
                "green_laser_delay": self.settings['delays']['green_laser_delay'],
                "mw_delay": self.settings['delays']['mw_delay'],
                "iq_delay": self.settings['delays']['iq_delay'],
                "counter_delay": self.settings['delays']['counter_delay'],
                "trigger_delay": self.settings['delays']['trigger_delay'],
                "units": "ns"
            }
        # this part is for when we adjust the settings in the gui, the calibration changes accordingly: so no need to change the json
        overrides = build_calibration_overrides()
        self.hardware_calibrator.update_calibration_delays(overrides)
        # Experiment parameters: the next section updates the settings every start click
        self.microwave_power = self.settings['microwave']['power']
        self.mw_delay = self.settings['delays']['mw_delay']
        self.green_laser_delay = self.settings['delays']['green_laser_delay']
        self.counter_delay = self.settings['delays']['counter_delay']
        self.iq_delay = self.settings['delays']['iq_delay']
        self.trigger_delay = self.settings['delays']['trigger_delay']

        self.green_laser_power = self.settings['green_laser']['power']
        self.green_laser_wavelength = self.settings['green_laser']['wavelength']

        # Output paths
        self.output_dir = self.get_output_dir("odmr_pulsed_output")
        self.logger.info("ODMR Pulsed Experiment initialized")

        # Create and load sequence
        source = None
        sequence_loaded = False

        if self.settings['sequence']['load_from_file']:
            print("loading from file")
            file_path = self.settings['sequence']['file_path']
            file_path = Path(file_path)

            if file_path and os.path.exists(file_path):
                sequence_loaded = self.load_sequence_from_file(file_path)
                print(f"file path: {file_path}")
                source = "file"
            else:
                self.logger.info("File path is invalid or does not exist")
        else:
            print("loading from text")
            self.sequence_text = self.settings['sequence']['text']
            print("ODMR Sequence:")
            print(self.sequence_text)
            print("\n" + "=" * 50 + "\n")
            sequence_loaded = self.load_sequence_from_text()
            source = "text"

        if sequence_loaded:
            self.logger.info(f"Sequence loaded successfully from {source}")
        else:
            self.logger.info(f"Failed to load sequence from {source}")
            return
        # Run experiment
        print("running exp")
        self.logger.info("Running experiment...")
        start_time = datetime.datetime.now()
        self.s_t = start_time.strftime("%m_%d_%Y_%H:%M:%S")
        results = self.run_experiment(self.settings['microwave']['frequency range'])
        end_time = datetime.datetime.now()
        self.e_t = end_time.strftime("%m_%d_%Y_%H:%M:%S")
        self.data = results
        self.save_hdf5()
        if results['success']:
            self.logger.info("Experiment completed successfully!")
            self.logger.info(f"Frequencies scanned: {[f / 1e9 for f in results['frequencies']]} GHz")
            self.logger.info(
                f"Signal counts shape: {len(results['signal_counts'])} frequencies x {len(results['signal_counts'][0])} points")
        else:
            self.logger.info(f"Experiment failed: {results['error']}")
        self.show_sequence_preview(10)
        self.logger.info("\nODMR Pulsed Experiment ready!")
        print("experiment ready")

    def save_hdf5(self):
        """this function defines its custom data and metadata to be saved and then calls the
        save_hdf_data function that is in the parent Experiment class, which adds the external
        devices in case you ever check the Get Basic Data checkbox in the GUI"""
        structure_to_save = MyStruct()
        signal_counts = self.data["signal_counts"]
        reference_counts = self.data["reference_counts"]
        total_counts = self.data["total_counts"]
        structure_to_save.data = MyStruct(
            signal_counts=signal_counts,
            reference_counts = reference_counts,
            total_counts = total_counts
        )
        structure_to_save.meta = MyStruct(
            count_time = self.count_time,
            counter_delay = self.counter_delay,
            end_time = self.e_t,
            frequency_range = self.data['frequencies'],
            green_laser_delay = self.green_laser_delay,
            green_laser_power = self.green_laser_power,
            green_laser_wavelength = self.green_laser_wavelength,
            iq_delay = self.iq_delay,
            microwave_power = self.microwave_power,
            mw_delay = self.mw_delay,
            number_of_iterations = self.number_of_iterations,
            proteus_response_delay = self.proteus_response_delay,
            repeat_count = self.repeat_count,
            reset_time = self.reset_time,
            sampling_rate = self.sampling_rate,
            sequence_text=self.sequence_text,
            sequence_duration = self.sequence_duration,
            start_time = self.s_t,
            success = self.data["success"],
            trigger_delay = self.trigger_delay
            )
        structure_to_save.devices = self.devices
        self.save_hdf_data(structure_to_save)

    def generate_awg_sequences_awg_triggering_adwin_case(self) -> bool:
        """
        Generate Proteus AWG waveforms with maximum timing resolution.
        One continuous waveform per channel.
        one segment and one task entry per channel.
        64-sample alignment is applied at the end of each waveform.
        The disadvantage of this option is that proteus does not know if the adwin is ready to count and whether it finished counting
        """

        def prepare_markers_for_tabor(markers_array: np.ndarray) -> np.ndarray:
            """
            Correct Proteus marker packing for 16-bit DAC mode.
            markers_array: 1 marker value per waveform sample (0 or 255)
            """

            # Convert to binary 0/1
            m = (markers_array > 0).astype(np.uint8)

            # Ensure multiple of 4 samples
            if len(m) % 4 != 0:
                m = np.pad(m, (0, 4 - len(m) % 4))

            # One marker byte per 4 waveform samples
            marker_bytes = np.zeros(len(m) // 4, dtype=np.uint8)

            for i in range(len(marker_bytes)):
                block = m[i * 4:(i + 1) * 4]

                if np.any(block):
                    # Marker 1 ON for all 4 samples → 0b00010001
                    marker_bytes[i] = 0x11
                else:
                    marker_bytes[i] = 0x00

            return marker_bytes

        try:
            self.proteus.driver.set_channel(3)
            self.proteus.driver.set_voltage('MAX')
            if not self.scan_sequences:
                self.logger.error("No scan sequences available")
                return False
            # ------------------------------------------------------------
            # DAC configuration
            # ------------------------------------------------------------
            max_dac = 65535
            half_dac = max_dac // 2
            ALIGNMENT = 64  # Proteus requirement (segment length)

            # ------------------------------------------------------------
            # Determine all channels, initialize buffers
            # ------------------------------------------------------------
            all_channels = set()
            channels = set()
            marker_indices = set()
            marker_channels = set()
            for sequence in self.scan_sequences:
                # ++++++++++++++++++++++
                print(f"to waveform output: {sequence.to_waveform()}")
                # ++++++++++++++++++++++
                for _, pulse_ in enumerate(sequence.pulses):
                    pulse = pulse_[1]
                    ch = int(pulse.name.split("_")[-1])
                    channels.add(ch)
                    all_channels.add(ch)

                for marker in sequence.markers:
                    mkr_index = int(marker.name.split('_')[-2])
                    marker_indices.add(mkr_index)
                    mk_ch = int(marker.name.split("_")[-1])
                    marker_channels.add(mk_ch)
                    all_channels.add(mk_ch)


            channel_waveforms = {
                ch: [] for ch in all_channels
            }
            channel_markers = {
                ch: [] for ch in all_channels
            }
            for ch in all_channels:
                self.proteus.driver.set_channel(ch)
                self.proteus.driver.delete_all_segment()
                self.proteus.driver.set_voltage("MAX")
                self.proteus.driver.apply_sampling_configuration(self.sampling_rate)

            # ------------------------------------------------------------
            # Build continuous waveform per channel (sample-accurate)
            # ------------------------------------------------------------
            for sequence in self.scan_sequences:
                seq_waveforms = sequence.to_waveform()
                for ch, data in seq_waveforms.items():
                    envelope = data["envelope"]
                    markers = data["markers"]
                    if not np.all(markers == 0):
                        print(f"channel {ch}: Found non-zero markers")
                        print(f"unique values {np.unique(markers)}")

                    channel_waveforms[ch].append(envelope)
                    channel_markers[ch].append(markers)
            # ------------------------------------------------------------
            # Upload one segment per channel
            # ------------------------------------------------------------
            segment_index = 1
            segment_for_channel = {}

            for ch in sorted(all_channels):
                self.proteus.driver.set_channel(ch)

                waveform = np.concatenate(channel_waveforms[ch])
                print(f"waveform: {waveform}")

                # Apply required alignment
                rem = len(waveform) % ALIGNMENT
                print(f"rem: {rem}")
                if rem:
                    waveform = np.pad(waveform, (0, ALIGNMENT - rem))
                    print(f"waveform: {waveform}")

                # Scale to DAC
                dac_wave = np.clip(waveform, -1.0, 1.0)
                dac_wave = ((dac_wave + 1.0) * half_dac).astype(np.uint16)

                # Define and select segment
                self.proteus.driver.define_trace(segment_index, len(dac_wave))
                self.proteus.driver.select_segment(segment_index)

                # Upload waveform
                self.proteus.driver.write_trace_data(dac_wave)  # write, and wait while *OPC completes
                resp = self.proteus.driver.query_error()
                print('analog upload result: "{0}" after writing trace binary values'.format(resp))

                segment_for_channel[ch] = segment_index
                # Handle markers for this channel
                if ch in channel_markers:
                    markers = np.concatenate(channel_markers[ch])
                    print(f"\n=== MARKER VALUE ANALYSIS ===")
                    print(f"Markers dtype: {markers.dtype}")
                    print(f"Min value: {np.min(markers)}")
                    print(f"Max value: {np.max(markers)}")
                    print(f"Unique values: {np.unique(markers)}")

                    rem = len(waveform) % ALIGNMENT
                    if rem:
                        waveform_padded_len = len(waveform) + (ALIGNMENT - rem)
                    else:
                        waveform_padded_len = len(waveform)

                    print(f"Waveform after padding: {waveform_padded_len} samples")
                    print(f"Markers before padding: {len(markers)} samples")

                    # Now pad/truncate markers to match waveform length
                    if len(markers) < waveform_padded_len:
                        # Pad markers with zeros
                        markers = np.pad(markers, (0, waveform_padded_len - len(markers)), mode='constant')
                        print(f"Markers padded to match waveform: {len(markers)} samples")
                    elif len(markers) > waveform_padded_len:
                        # Truncate markers
                        markers = markers[:waveform_padded_len]
                        print(f"Markers truncated to match waveform: {len(markers)} samples")
                    else:
                        print(f"Markers already match waveform length")

                    if not np.all(markers == 0):

                        # Convert to uint8
                        markers = markers.astype(np.uint8)

                        # Now prepare for Tabor
                        tabor_markers = prepare_markers_for_tabor(markers)

                        # For 16-bit mode, marker bytes should be waveform_bytes / 4
                        expected_marker_bytes = len(dac_wave) // 4
                        actual_marker_bytes = len(tabor_markers)

                        if actual_marker_bytes != expected_marker_bytes:
                            if actual_marker_bytes < expected_marker_bytes:
                                tabor_markers = np.pad(tabor_markers, (0, expected_marker_bytes - actual_marker_bytes),
                                                       mode='constant')
                            else:
                                tabor_markers = tabor_markers[:expected_marker_bytes]

                        self.proteus.driver.write_marker_data(tabor_markers)
                        resp = self.proteus.driver.query_error()
                        print(f'Marker upload result: {resp}')
                        # proteus P1284M only has 1 marker per channel, for other awgs, please implement code that handels that
                        # I have already coded the marker index here: mkr_index = int(marker.name.split('_')[-2]) so if the user
                        # gives marker, laser_int_1 on channel 4 at 0ns, 500ns then you know whatever is after laser_init_ is the index
                        marker_index = 1

                        self.proteus.driver.set_marker(marker_index)
                        # Verify Proteus marker settings
                        resp = self.proteus.driver.get_marker()
                        print(f"Selected marker: {resp}")
                        resp = self.proteus.driver.get_marker_state()
                        print(f"Marker state: {resp}")
                        resp = self.proteus.driver.query_error()
                        print(f"System error: {resp}")

                        resp = self.proteus.driver.get_marker_ptop_voltage()
                        print(f"Marker voltage PTOP setting: {resp}")

                        resp = self.proteus.driver.get_marker_voltage()
                        print(f"Marker voltage LEV setting: {resp}")
                        self.proteus.driver.set_marker_ptop_voltage(1)
                        resp = self.proteus.driver.get_marker_ptop_voltage()
                        print(f"Marker voltage PTOP setting: {resp}")
                        resp = self.proteus.driver.get_marker_voltage_offset()
                        print(f"Marker voltage offset setting: {resp}")
                        self.proteus.driver.set_marker_voltage_offset(0.5)
                        resp = self.proteus.driver.get_marker_voltage_offset()
                        print(f"Marker voltage offset setting: {resp}")

                        # Check for errors
                        resp = self.proteus.driver.query_error()
                        print(f'Marker upload result: {resp}')
                    else:
                        print(f"Channel {ch}: Markers are all zeros, skipping marker upload")

                segment_index += 1

            # ------------------------------------------------------------
            # Build ONE task entry per channel
            # ------------------------------------------------------------

            # Task must be set per channel
            for ch in sorted(all_channels):
                self.proteus.driver.set_channel(ch)
                self.proteus.driver.set_continuous_run(0)
                task_table_length = 1
                self.proteus.driver.set_task_table_length(task_table_length)
                self.proteus.driver.set_task_number(1)
                self.proteus.driver.set_task_type("SING")
                #self.proteus.driver.set_next1_task(0)
                self.proteus.driver.set_task_segment_number(segment_for_channel[ch])
                self.proteus.driver.set_task_loop(self.repeat_count)
                self.proteus.driver.write_composer_array_to_task_table()

                # ------------------------------------------------------------
                # Enable TASK mode and output
                # ------------------------------------------------------------
            self.proteus.driver.set_task_sync()
            self.proteus.start_sequence()
            time.sleep(1)
            self.proteus.driver._close()
            return True
        except Exception as e:
            self.logger.exception("Error generating AWG files")
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
        this is just for testing: we need to only use json or gui for this
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
    
    def set_green_laser_parameters(self, power: float, wavelength: float) -> None:
        """
        this is just for testing: we need to only use json or gui for this
        Set laser parameters.
        
        Args:
            power: Power in mW
            wavelength: Wavelength in nm
        """
        self.green_laser_power = power
        self.green_laser_wavelength = wavelength
        self.logger.info(f"Laser: {power} mW, {wavelength} nm")
    
    def set_delay_parameters(self, mw_delay: float, green_laser_delay: float, counter_delay: float) -> None:
        """
        this is just for testing: we need to only use json or gui for this
        Set delay parameters.
        
        Args:
            mw_delay: Microwave delay in ns
            green_laser_delay: green_laser_delay delay in ns
            counter_delay: Counter delay in ns
        """
        self.mw_delay = mw_delay
        self.green_laser_delay = green_laser_delay
        self.counter_delay = counter_delay
        self.logger.info(f"Delays: MW={mw_delay}ns, AOM={green_laser_delay}ns, Counter={counter_delay}ns")
    
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
            print("Starting ODMR Pulsed Experiment")
            # Step 1: Load sequence
            if not self.sequence_description:
                self.logger.error("No sequence loaded")
                print("No sequence loaded")
                return {'success': False, 'error': 'No sequence loaded'}

            # Step 2: Build scan sequences
            if not self.build_scan_sequences():
                return {'success': False, 'error': 'Failed to build scan sequences'}

            # Step 3: Generate AWG sequences
            if not self.generate_awg_task_sequences_adwin_triggering_awg_case():
                return {'success': False, 'error': 'Failed to generate AWG sequences'}
            
            # Step 4: Setup ADwin for photon counting
            if not self._setup_adwin_counting():
                return {'success': False, 'error': 'Failed to setup ADwin counting'}

            
            # Step 6: Run experiment for each frequency
            #'success': True,
            #'frequencies': frequency_range,
            results = {
                'signal_counts': [],
                'reference_counts': [],
                'total_counts': []
            }
            # delete later:
            #frequency_range = [2.87e9]
            for freq in frequency_range:
                print(f"Running experiment at {freq/1e9:.3f} GHz")
                self.logger.info(f"Running experiment at {freq/1e9:.3f} GHz")
                
                # Set SG384 frequency
                if 'sg384' in self.devices:
                    self.sg384.set_frequency(freq)
                    self.sg384.set_power(self.microwave_power)
                    self.microwave_frequency = freq
                    self.logger.info(f"Set SG384 to {freq/1e9:.3f} GHz, {self.microwave_power} dBm")
                    print(f"Set SG384 to {freq / 1e9:.3f} GHz, {self.microwave_power} dBm")
                
                # Run sequence and collect data
                freq_results = self._run_sequence_and_collect_data()
                if not freq_results['success']:
                    return {'success': False, 'error': f'Failed at frequency {freq/1e9:.3f} GHz'}
                
                results['signal_counts'].append(freq_results['signal_counts'])
                results['reference_counts'].append(freq_results['reference_counts'])
                results['total_counts'].append(freq_results['total_counts'])
            results['signal_counts']=np.array(results['signal_counts'], dtype = np.int64)
            results['reference_counts']=np.array(results['reference_counts'], dtype = np.int64)
            results['total_counts']=np.array(results['total_counts'], dtype = np.int64)
            results['success'] = True
            results['frequencies'] = frequency_range
            
            self.logger.info("ODMR Pulsed Experiment completed successfully")
            print("ODMR Pulsed Experiment completed successfully")
            return results
            
        except Exception as e:
            self.logger.error(f"Experiment failed: {e}")
            return {'success': False, 'error': str(e)}
    
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
            #process_file = "odmr_pulsed_counter.__2"
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
            # the following were tests for option 3
            """# test 1
            odmr_pulsed_counter_path = get_adwin_binary_path('odmr_pulsed_counter.TB2')
            # test 2
            odmr_pulsed_counter_path = get_adwin_binary_path('adbasic_long_waveform_v1.TB2')
            # test 3
            odmr_pulsed_counter_path = get_adwin_binary_path('adbasic_long_waveform_v2.TB2')
            #tested digout
            odmr_pulsed_counter_path = get_adwin_binary_path('test_adwin_digout.TB1')
            # tested proteus delay and digout delay
            odmr_pulsed_counter_path = get_adwin_binary_path('test_adwin_delays.TB1')"""
            # option 3 file: SEQUENTIAL MODEL
            odmr_pulsed_counter_path = get_adwin_binary_path('adwin_triggering_proteus.TB1')
            # option 3 file: BEHAVIORAL MODEL
            #odmr_pulsed_counter_path = get_adwin_binary_path('adwin_odmr_pulsed_ticks.TB1')
            self.adwin.update({'process_1': {'load': str(odmr_pulsed_counter_path)}})
            # Set ADwin parameters for counting
            # Par_3: count_time (with calibration offset)
            # Par_4: reset_time (with calibration offset) 
            # Par_5: repeat_count
            # Par_6: number of iterations
            self.adwin.set_int_var(3, self.count_time )
            self.adwin.set_int_var(4, self.reset_time )
            self.adwin.set_int_var(5, self.repeat_count)
            self.adwin.set_int_var(6, self.number_of_iterations)
            self.adwin.set_int_var(9, self.sequence_duration)
            self.adwin.set_int_var(10, self.proteus_response_delay)
            self.adwin.set_int_var(11, 1)
            # Start the counting process
            self.adwin.start_process(process_number)
            time.sleep(0.1)  # Give process time to start
            # Verify process started
            """process_status = self.adwin.get_process_status(1)
            print(f"process_status: {process_status}")
            if process_status != "Running":
                self.log(f"Process failed to start! Status: {process_status}")
                raise RuntimeError("ADwin process failed to start")"""
            
            self.logger.info(f"ADwin counting setup: count_time={self.count_time}ns, reset_time={self.reset_time}ns, reps={self.repeat_count}")
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
            # Wait for sequence to complete and collect data
            # The ADwin adwin_triggering_proteus.bas process accumulates counts
            # and stores them in arrays Data_1[iteration] (signal) and Data_2[iteration] (reference)

            # Collect data
            # this method has python collecting data and telling aadwin to stop:
            # Collect data
            wait_time = (self.sequence_duration + self.proteus_response_delay)
            wait_time = wait_time * self.repeat_count * self.number_of_iterations  # remember: wait_time is in ns
            wait_time = wait_time * (10 ** (-9)) * 10  * 10 * 10
            print(f"wait time: {wait_time}")
            # wait for length of the entire experiment, then get the data
            time.sleep(wait_time)
            # this method has adwin collecting data and telling python that it has finished (which is the correct way to do it):
            """while self.adwin.get_int_var(7) == 0:
                time.sleep(60)"""
            print(f"self.adwin.get_int_var(8): {self.adwin.get_int_var(8)}")
            signal_counts = np.array(self.adwin.get_int_data(1, self.number_of_iterations), dtype=np.int64)
            ref_counts = np.array(self.adwin.get_int_data(2, self.number_of_iterations), dtype=np.int64)
            total_counts=signal_counts.astype(np.int64)+ref_counts.astype(np.int64)
            for signal_counts_val in signal_counts:
                self.logger.info(f"signal_counts_val {signal_counts_val}")
                print(f"signal_counts_val {signal_counts_val}")
            for reference_counts_val in ref_counts:
                self.logger.info(f"reference_counts_val {reference_counts_val}")
                print(f"reference_counts_val {reference_counts_val}")
            for total_counts_val in total_counts:
                self.logger.info(f"total_counts_val {total_counts_val}")
                print(f"total_counts_val {total_counts_val}")
            # Stop Proteus
            #self.proteus.stop_sequence()
            self.proteus.driver._close()
            print(f"end of _run_sequence_and_collect_data()")

            return {
                'success': True,
                'signal_counts': signal_counts,
                'reference_counts': ref_counts,
                'total_counts': total_counts
            }
            
        except Exception as e:
            self.logger.error(f"Failed to run sequence and collect data: {e}")
            return {'success': False, 'error': str(e)}
    
    """

sequence: name=odmr_pulsed, type=odmr, duration=1002500ns, sample_rate=1GHz, repeat_count=50000
variable pulse_duration, start=50ns, stop=500ns, steps=20
marker, laser_int_1 on channel 1 at 0ns, 500ns
pi/2 pulse on channel 1 at 500ns, gaussian, pulse_duration, 1.0
pi/2 pulse on channel 2 at 500ns, gaussian, pulse_duration, 1.0
wait pulse on channel 1 at pulse_duration+0.000000500, square, 2*pulse_duration, 0.0
wait pulse on channel 2 at pulse_duration+0.000000500, square, 2*pulse_duration, 0.0
pi/2 pulse on channel 1 at 3*pulse_duration+0.000000500, gaussian, pulse_duration, 1.0
pi/2 pulse on channel 2 at 3*pulse_duration+0.000000500, gaussian, pulse_duration, 1.0
marker, laser_readout_1 on channel 1 at 2500ns, 1ms
marker, readout_counts_1 on channel 2 at 2500ns, 300ns
marker, reference_counts_1 on channel 2 at 1002200ns, 300ns
sequence: name=SCC, type=SCC, duration=1400ns, sample_rate=1GHz, repeat=50000
shelving pulse on channel 3 at 0ns, square, 300ns, 0.6
ionization pulse on channel 3 at 300ns, square, 500ns, 1.0
readout pulse on channel 3 at 800ns, square, 600ns, 0.3
    sequence: name=SCC, type=SCC, duration=1400ns, sample_rate=1GHz, repeat=50000
    shelving pulse on channel 1 at 0ns, square, 300ns, 0.6
    ionization pulse on channel 1 at 300ns, square, 500ns, 1.0
    readout pulse on channel 1 at 800ns, square, 600ns, 0.3"""

    def create_example_odmr_sequence(self) -> str:
        """
        This is just for testing, please use a file or GUI setting updates
        Create an example ODMR sequence using the sequence language.

        Returns:
            Sequence text in the sequence language format
        """
        sequence_text = """    
sequence: name=odmr_pulsed, type=odmr, duration=1300ns, sample_rate=1GHz, repeat_count=50000
variable pulse_duration, start=50ns, stop=500ns, steps=20
marker, laser_int_1 on channel 1 at 0ns, 50ns
pi/2 pulse on channel 1 at 50ns, gaussian, pulse_duration, 1.0
pi/2 pulse on channel 2 at 50ns, gaussian, pulse_duration, 1.0 
marker, laser_readout_1 on channel 1 at 550ns, 300ns
marker, ref_readout_1 on channel 1 at 1000ns, 300ns
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

# Laser control via Proteus markers:
# ch1_marker1: laser_switch (triggers laser on/off)
# ch2_marker1: counter_trigger (triggers ADwin counting)
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
            'green_laser_power_mw': self.green_laser_power,
            'green_laser_wavelength_nm': self.green_laser_wavelength,
            'delays_ns': {
                'mw': self.mw_delay,
                'green laser': self.green_laser_delay,
                'counter': self.counter_delay
            },
            'output_directory': str(self.output_dir)
        }

    def _update(self):
        pass

class SequencePreviewWindow:
    """Window for previewing sequence scan points."""

    def __init__(self, sequences: List[Sequence], description):
        """Initialize preview window."""
        self.sequences = sequences
        self.description = description
        self.window = None
        self.sequence_builder = SequenceBuilder()
        self.anim = None

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

            for name, var in self.description.variables.items():
                var_text = f"{var.name}: {var.start_value} to {var.stop_value} ({var.steps} steps)"
                ttk.Label(var_frame, text=var_text).pack(anchor='w')

    def _create_plots_tab(self, parent):
        """Create plots tab."""
        # Create matplotlib figure
        fig, ax = plt.subplots(figsize=(8, 6))

        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        canvas = FigureCanvasTkAgg(fig, parent)
        canvas.get_tk_widget().pack(fill='both', expand=True)

        # IMPORTANT: store animation on self
        self.anim = self.sequence_builder.animate_scan_sequences(
            self.sequences[:min(5, len(self.sequences))],
            fig=fig,
            ax=ax,
            title="Sequence Preview (First 5 Points)"
        )

        canvas.draw()

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
    # Create experiment for testing
    """experiment = ODMRPulsedExperiment(name="test_odmr")
    
    # Set parameters
    experiment.set_microwave_parameters(2.87e9, -10.0, 25.0)
    experiment.set_green_laser_parameters(1.0, 532)
    experiment.set_delay_parameters(25.0, 50.0, 15.0)
    # Create and load example sequence
    sequence_text = experiment.create_example_odmr_sequence()
    print("Example ODMR Sequence:")
    print(sequence_text)
    print("\n" + "="*50 + "\n")
    
    if experiment.load_sequence_from_text(sequence_text):
        print("Sequence loaded successfully")
    else:
        print("Failed to load sequence")

    # Build sequences
    if experiment.build_scan_sequences():
       print("Scan sequences built successfully")
    else:
        print("Failed to build scan sequences")
    # Generate AWG sequences
    if experiment.generate_awg_sequences_awg_triggering_adwin_case():
    #if experiment.generate_awg_task_sequences_adwin_triggering_awg_case():
       print("AWG sequences generated successfully")
    else:
       print("Failed to generate AWG sequences")"""

    # with adwin:
    experiment = ODMRPulsedExperiment(name="test_odmr")

    # Set parameters
    experiment.set_microwave_parameters(2.87e9, -10.0, 25.0)
    experiment.set_green_laser_parameters(1.0, 532)
    experiment.set_delay_parameters(25.0, 50.0, 15.0)
    # Create and load example sequence
    sequence_text = experiment.create_example_odmr_sequence()
    print("Example ODMR Sequence:")
    print(sequence_text)
    print("\n" + "=" * 50 + "\n")

    if experiment.load_sequence_from_text(sequence_text):
        print("Sequence loaded successfully")
    else:
        print("Failed to load sequence")
    # Run experiment
    print("Running experiment...")
    #results = experiment.run_experiment(frequency_range=[2.87e9, 2.88e9, 2.89e9])
    results = experiment.run_experiment(frequency_range=[2.87e9])
    if results['success']:
        print("Experiment completed successfully!")
        print(f"Frequencies scanned: {[f/1e9 for f in results['frequencies']]} GHz")
        print(f"Signal counts shape: {len(results['signal_counts'])} frequencies x {len(results['signal_counts'][0])} points")
    else:
        print(f"Experiment failed: {results['error']}")
    experiment.show_sequence_preview(10)
    print("\nODMR Pulsed Experiment ready!")