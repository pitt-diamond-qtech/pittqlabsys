# Created by gurudevdutt on 2026-05-13
# Converted from MATLAB script: feedback_arduinos_acquire_block.m
# Model/experiments/feedback_arduino_acquire_block.py

import logging

import numpy as np

from src.core import Experiment, Parameter

logger = logging.getLogger(__name__)


class FeedbackArduinoAcquireBlock(Experiment):
    """Acquire one block of 4-channel data from Arduino feedback controller.

    This experiment performs a complete single-shot acquisition sequence:
    1. Configure the Arduino in triggered scope mode (mode 2)
    2. Start data acquisition
    3. Poll for a complete data block with timeout/retry
    4. Stop acquisition
    5. Store the multi-channel data in self.data

    The Arduino is configured in scope mode, which waits for a trigger event
    on the specified channel before capturing a block of samples.

    Typical use case: Capture a triggered waveform for offline analysis.

    Attributes:
        _DEFAULT_SETTINGS: Experiment parameters for acquisition configuration.
        _DEVICES: Requires FeedbackArduino device.
        _EXPERIMENTS: No sub-experiments.
    """

    _DEFAULT_SETTINGS = [
        Parameter('decimator', 100, int, 'ADC decimation factor'),
        Parameter('usb_data_n', 256, int, 'Number of int16 values per USB block'),
        Parameter('trig_channel', 0, int, 'Trigger channel index (0-3)'),
        Parameter('trig_level', 0, int, 'Trigger threshold in ADC counts'),
        Parameter('trig_hyst', 1, int, 'Trigger hysteresis in ADC counts'),
        Parameter('max_wait_s', 5.0, float, 'Maximum wait time for data block in s'),
        Parameter('poll_dt', 0.02, float, 'Poll interval between retries in s'),
        Parameter('save', True, bool, 'Save data to disk after acquisition'),
        Parameter('tag', 'arduino_block', str, 'Tag for saved data files'),
    ]

    _DEVICES = {
        'arduino': 'feedback_arduino'  # References config.json device key
    }

    _EXPERIMENTS = {}

    def _function(self):
        """Core experiment logic: configure, acquire, and store data block.

        This method is called by the base class run() method. It performs
        the complete acquisition sequence and stores results in self.data.

        The data dict contains:
            - samples_by_channel: [N_samples x 4] numpy array of int16 values
            - chA, chB, chC, chD: Individual channel arrays
            - n_samples: Number of samples per channel
            - n_channels: Number of channels (should be 4)
            - adc_sample_rate_hz: Actual ADC sample rate after decimation
            - decimator: Decimation factor used
        """
        arduino = self.devices['arduino']['instance']

        decimator = self.settings['decimator']
        usb_data_n = self.settings['usb_data_n']
        trig_channel = self.settings['trig_channel']
        trig_level = self.settings['trig_level']
        trig_hyst = self.settings['trig_hyst']
        max_wait_s = self.settings['max_wait_s']
        poll_dt = self.settings['poll_dt']

        self.log(f"Configuring Arduino in scope mode: decimator={decimator}, "
                f"data_n={usb_data_n}, trig_ch={trig_channel}, "
                f"level={trig_level}, hyst={trig_hyst}")

        arduino.configure_scope_mode(
            decimator=decimator,
            usb_data_n=usb_data_n,
            trig_channel=trig_channel,
            trig_level=trig_level,
            trig_hyst=trig_hyst
        )

        self.log("Starting data acquisition")
        arduino.start_acquisition()

        self.progress = 25
        self.updateProgress.emit(self.progress)

        self.log(f"Waiting for data block (max {max_wait_s}s)")
        try:
            result = arduino.get_data_block(max_wait_s=max_wait_s, poll_dt=poll_dt)
        except TimeoutError as e:
            self.log(f"ERROR: {e}")
            arduino.stop_acquisition()
            self.data = {'error': str(e)}
            return
        except Exception as e:
            self.log(f"ERROR during data acquisition: {e}")
            arduino.stop_acquisition()
            self.data = {'error': str(e)}
            return

        self.progress = 75
        self.updateProgress.emit(self.progress)

        self.log("Stopping data acquisition")
        arduino.stop_acquisition()

        if result['samples_by_channel'] is None or result['samples_by_channel'].shape[1] != 4:
            self.log("ERROR: Expected 4-channel data")
            self.data = {'error': 'Expected 4-channel data', 'result': result}
            return

        data_array = result['samples_by_channel']
        n_samples = data_array.shape[0]

        self.log(f"Acquired {n_samples} samples per channel")

        try:
            info = arduino.read_probes('info')
            adc_sample_rate_hz = info['adc_sample_rate_hz']
        except Exception as e:
            logger.warning(f"Could not query ADC sample rate: {e}")
            adc_sample_rate_hz = None

        self.data = {
            'samples_by_channel': data_array,
            'chA': data_array[:, 0],
            'chB': data_array[:, 1],
            'chC': data_array[:, 2],
            'chD': data_array[:, 3],
            'n_samples': n_samples,
            'n_channels': 4,
            'adc_sample_rate_hz': adc_sample_rate_hz,
            'decimator': decimator,
        }

        self.progress = 100
        self.updateProgress.emit(self.progress)

        self.log("Data acquisition complete")

    def _plot(self, axes_list, data=None):
        """Plot the acquired 4-channel data on a single axes.

        Args:
            axes_list: List of pyqtgraph PlotItem objects from get_axes_layout.
            data: Optional data dict; defaults to self.data.
        """
        if data is None:
            data = self.data

        if not data or 'samples_by_channel' not in data or 'error' in data:
            return

        if len(axes_list) < 1:
            return

        ax = axes_list[0]
        ax.clear()

        samples = data['samples_by_channel']
        x = np.arange(samples.shape[0])

        colors = ['r', 'g', 'b', 'y']
        labels = ['Ch A', 'Ch B', 'Ch C', 'Ch D']

        for i in range(4):
            ax.plot(x, samples[:, i], pen=colors[i], name=labels[i])

        ax.setLabel('bottom', 'Sample Index')
        ax.setLabel('left', 'ADC Counts')
        ax.setTitle('Arduino 4-Channel Acquisition')
        ax.addLegend()
