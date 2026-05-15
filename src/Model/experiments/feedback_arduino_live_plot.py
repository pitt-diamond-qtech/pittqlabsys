# Created by gurudevdutt on 2026-05-13
# Converted from MATLAB script: feedback_arduinos_live_plot.m
# Model/experiments/feedback_arduino_live_plot.py

import logging
import time

import numpy as np

from src.core import Experiment, Parameter

logger = logging.getLogger(__name__)

_CHANNEL_PENS = ['r', 'g', 'b', 'y']
_CHANNEL_KEYS = ['histA', 'histB', 'histC', 'histD']
_CHANNEL_TITLES = ['Channel A', 'Channel B', 'Channel C', 'Channel D']


class FeedbackArduinoLivePlot(Experiment):
    """Continuously acquire and plot 4-channel data from Arduino feedback controller.

    This experiment runs a live data acquisition loop:
    1. Configure Arduino in continuous filter mode (mode 0)
    2. Start acquisition
    3. Continuously poll for data blocks
    4. Update rolling history buffers for each channel
    5. Update live plots in real-time

    Unlike triggered scope mode, filter mode provides continuous streaming
    data without waiting for trigger events. This is ideal for monitoring
    signals in real-time.

    The experiment runs until:
    - max_runtime is reached (if > 0)
    - User stops it via GUI
    - self._abort flag is set

    Typical use case: Real-time monitoring of QPD (quad photodiode) or
    other multi-channel analog signals during alignment or feedback tuning.

    Attributes:
        _DEFAULT_SETTINGS: Experiment parameters for live acquisition.
        _DEVICES: Requires FeedbackArduino device.
        _EXPERIMENTS: No sub-experiments.
    """

    _DEFAULT_SETTINGS = [
        Parameter('bandwidth', 1, int, 'Filter bandwidth parameter (mode 0)'),
        Parameter('decimator', 100, int, 'ADC decimation factor'),
        Parameter('usb_data_n', 256, int, 'Number of int16 values per USB block'),
        Parameter('pause_dt', 0.01, float, 'Pause between poll attempts in s'),
        Parameter('history_blocks', 200, int, 'Number of data blocks to display in rolling buffer'),
        Parameter('max_runtime', 60.0, float, 'Maximum runtime in s (0 = run indefinitely)'),
        Parameter('save', False, bool, 'Save data to disk after acquisition'),
        Parameter('tag', 'arduino_live', str, 'Tag for saved data files'),
    ]

    _DEVICES = {
        'arduino': 'feedback_arduino'
    }

    _EXPERIMENTS = {}

    def _function(self):
        """Core experiment logic: continuous acquisition and plotting.

        This method runs the main acquisition loop, continuously polling
        the Arduino for data blocks and updating the rolling history buffers.

        The loop continues until:
        - max_runtime is reached (if > 0)
        - self._abort is True (user stopped experiment)

        Data is stored in self.data as rolling history arrays:
            - histA, histB, histC, histD: Rolling buffers for each channel
            - block_count: Number of blocks successfully acquired
            - none_count: Number of 'none' responses (data not ready)
            - blocks_per_second: Average block acquisition rate
            - n_samples_per_block: Samples per channel per block
        """
        arduino = self.devices['arduino']['instance']

        bandwidth = self.settings['bandwidth']
        decimator = self.settings['decimator']
        usb_data_n = self.settings['usb_data_n']
        pause_dt = self.settings['pause_dt']
        history_blocks = self.settings['history_blocks']
        max_runtime = self.settings['max_runtime']

        self.log(f"Configuring Arduino in filter mode: bandwidth={bandwidth}, "
                f"decimator={decimator}, data_n={usb_data_n}")

        arduino.configure_filter_mode(
            bandwidth=bandwidth,
            decimator=decimator,
            usb_data_n=usb_data_n
        )

        try:
            info = arduino.read_probes('info')
            nch = info['adc_n_channels']
            adc_sample_rate_hz = info['adc_sample_rate_hz']
        except Exception as e:
            self.log(f"ERROR: Could not query device info: {e}")
            self.data = {'error': str(e)}
            return

        if nch != 4:
            self.log(f"ERROR: Expected 4 ADC channels, but device reports {nch}")
            self.data = {'error': f'Expected 4 channels, got {nch}'}
            return

        n_samples_per_block = usb_data_n // nch

        self.log(f"Device configured: {nch} channels, {n_samples_per_block} samples/channel/block")

        max_hist_samples = history_blocks * n_samples_per_block

        histA = np.full(max_hist_samples, np.nan, dtype=float)
        histB = np.full(max_hist_samples, np.nan, dtype=float)
        histC = np.full(max_hist_samples, np.nan, dtype=float)
        histD = np.full(max_hist_samples, np.nan, dtype=float)

        self.log("Starting live data acquisition")
        arduino.start_acquisition()

        t_start = time.time()
        t_rate_start = time.time()
        blocks_ok = 0
        blocks_none = 0

        self.log(f"Entering acquisition loop (max_runtime={max_runtime}s)")

        while not self._abort:
            if max_runtime > 0 and (time.time() - t_start) > max_runtime:
                self.log(f"Maximum runtime {max_runtime}s reached")
                break

            try:
                result = arduino.poll_data_block()
            except Exception as e:
                logger.warning(f"Data poll failed: {e}")
                time.sleep(pause_dt)
                continue

            if result['kind'] != 'binary':
                if result['kind'] == 'none':
                    blocks_none += 1
                time.sleep(pause_dt)
                continue

            data_array = result['samples_by_channel']
            if data_array is None or data_array.shape[1] != 4:
                logger.warning(
                    "Expected 4-channel data, got shape %s",
                    data_array.shape if data_array is not None else 'None',
                )
                time.sleep(pause_dt)
                continue

            chA = data_array[:, 0].astype(float)
            chB = data_array[:, 1].astype(float)
            chC = data_array[:, 2].astype(float)
            chD = data_array[:, 3].astype(float)

            n_new = len(chA)

            histA = np.roll(histA, -n_new)
            histA[-n_new:] = chA

            histB = np.roll(histB, -n_new)
            histB[-n_new:] = chB

            histC = np.roll(histC, -n_new)
            histC[-n_new:] = chC

            histD = np.roll(histD, -n_new)
            histD[-n_new:] = chD

            blocks_ok += 1

            elapsed = time.time() - t_rate_start
            block_rate = blocks_ok / elapsed if elapsed > 0 else np.nan

            self.data = {
                'histA': histA.copy(),
                'histB': histB.copy(),
                'histC': histC.copy(),
                'histD': histD.copy(),
                'block_count': blocks_ok,
                'none_count': blocks_none,
                'blocks_per_second': block_rate,
                'n_samples_per_block': n_samples_per_block,
                'max_hist_samples': max_hist_samples,
                'adc_sample_rate_hz': adc_sample_rate_hz,
            }

            if max_runtime > 0:
                self.progress = int(100 * (time.time() - t_start) / max_runtime)
                self.progress = min(self.progress, 99)
                self.updateProgress.emit(self.progress)

            time.sleep(pause_dt)

        self.log("Stopping live data acquisition")
        arduino.stop_acquisition()

        elapsed_total = time.time() - t_start
        self.log(f"Acquisition complete: {blocks_ok} blocks in {elapsed_total:.1f}s "
                f"({blocks_ok/elapsed_total:.2f} blocks/s)")
        self.log(f"'None' responses: {blocks_none}")

        self.progress = 100
        self.updateProgress.emit(self.progress)

    def get_axes_layout(self, figure_list):
        """Return four PlotItem axes in a 2x2 grid on the first figure.

        Args:
            figure_list: List of pyqtgraph GraphicsLayoutWidget objects.

        Returns:
            axes_list: [Ch A, Ch B, Ch C, Ch D] PlotItem objects.
        """
        axes_list = []
        if self._plot_refresh is True:
            for graph in figure_list:
                graph.clear()
            graph = figure_list[0]
            for row, col in ((0, 0), (0, 1), (1, 0), (1, 1)):
                axes_list.append(graph.addPlot(row=row, col=col))
        else:
            graph = figure_list[0]
            for row, col in ((0, 0), (0, 1), (1, 0), (1, 1)):
                axes_list.append(graph.getItem(row=row, col=col))

        return axes_list

    def _plot(self, axes_list, data=None):
        """Plot rolling 4-channel history in a 2x2 grid.

        Args:
            axes_list: Four PlotItem objects from get_axes_layout.
            data: Optional data dict; defaults to self.data.
        """
        if data is None:
            data = self.data

        if not data or 'histA' not in data or 'error' in data:
            return

        if len(axes_list) < 4:
            return

        max_hist = data['max_hist_samples']
        x = np.arange(max_hist)

        for ax, key, pen, title in zip(
            axes_list, _CHANNEL_KEYS, _CHANNEL_PENS, _CHANNEL_TITLES
        ):
            ax.clear()
            ax.plot(x, data[key], pen=pen)
            ax.setLabel('left', 'ADC Counts')
            ax.setLabel('bottom', 'Sample Index')
            ax.setTitle(title)
            ax.showGrid(x=True, y=True, alpha=0.3)
