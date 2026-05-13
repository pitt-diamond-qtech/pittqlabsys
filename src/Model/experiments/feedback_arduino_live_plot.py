# Created by gurudevdutt on 2026-05-13
# Converted from MATLAB script: feedback_arduinos_live_plot.m
# Model/experiments/feedback_arduino_live_plot.py

from src.core import Experiment, Parameter
from src.Controller.feedback_arduino import FeedbackArduino
import numpy as np
import logging
import time

logger = logging.getLogger(__name__)


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
        # Get device instance
        arduino = self.instruments['arduino']['instance']

        # Extract settings
        bandwidth = self.settings['bandwidth']
        decimator = self.settings['decimator']
        usb_data_n = self.settings['usb_data_n']
        pause_dt = self.settings['pause_dt']
        history_blocks = self.settings['history_blocks']
        max_runtime = self.settings['max_runtime']

        self.log(f"Configuring Arduino in filter mode: bandwidth={bandwidth}, "
                f"decimator={decimator}, data_n={usb_data_n}")

        # Configure Arduino in continuous filter mode (mode 0)
        arduino.configure_filter_mode(
            bandwidth=bandwidth,
            decimator=decimator,
            usb_data_n=usb_data_n
        )

        # Query device info to determine channel count and samples per block
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

        # Calculate samples per block per channel
        # usb_data_n is total int16 values across all channels
        n_samples_per_block = usb_data_n // nch

        self.log(f"Device configured: {nch} channels, {n_samples_per_block} samples/channel/block")

        # Initialize rolling history buffers
        max_hist_samples = history_blocks * n_samples_per_block

        histA = np.full(max_hist_samples, np.nan, dtype=float)
        histB = np.full(max_hist_samples, np.nan, dtype=float)
        histC = np.full(max_hist_samples, np.nan, dtype=float)
        histD = np.full(max_hist_samples, np.nan, dtype=float)

        # Start acquisition
        self.log("Starting live data acquisition")
        arduino.start_acquisition()

        # Acquisition loop timing
        t_start = time.time()
        t_rate_start = time.time()
        blocks_ok = 0
        blocks_none = 0

        self.log(f"Entering acquisition loop (max_runtime={max_runtime}s)")

        while not self._abort:
            # Check runtime limit
            if max_runtime > 0 and (time.time() - t_start) > max_runtime:
                self.log(f"Maximum runtime {max_runtime}s reached")
                break

            # Poll for data block (single attempt)
            try:
                result = arduino.poll_data_block()
            except Exception as e:
                logger.warning(f"Data poll failed: {e}")
                time.sleep(pause_dt)
                continue

            # Handle 'none' response (data not ready yet)
            if result['kind'] != 'binary':
                if result['kind'] == 'none':
                    blocks_none += 1
                time.sleep(pause_dt)
                continue

            # Validate 4-channel data
            data_array = result['samples_by_channel']
            if data_array is None or data_array.shape[1] != 4:
                logger.warning(f"Expected 4-channel data, got shape {data_array.shape if data_array is not None else 'None'}")
                time.sleep(pause_dt)
                continue

            # Extract channel data as float (for NaN handling)
            chA = data_array[:, 0].astype(float)
            chB = data_array[:, 1].astype(float)
            chC = data_array[:, 2].astype(float)
            chD = data_array[:, 3].astype(float)

            n_new = len(chA)

            # Roll history buffers (shift left, append new data at end)
            histA = np.roll(histA, -n_new)
            histA[-n_new:] = chA

            histB = np.roll(histB, -n_new)
            histB[-n_new:] = chB

            histC = np.roll(histC, -n_new)
            histC[-n_new:] = chC

            histD = np.roll(histD, -n_new)
            histD[-n_new:] = chD

            blocks_ok += 1

            # Calculate block acquisition rate
            elapsed = time.time() - t_rate_start
            if elapsed > 0:
                block_rate = blocks_ok / elapsed
            else:
                block_rate = np.nan

            # Store current data snapshot in self.data for plotting
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

            # Update progress (percentage of max_runtime if finite)
            if max_runtime > 0:
                self.progress = int(100 * (time.time() - t_start) / max_runtime)
                self.progress = min(self.progress, 99)  # Cap at 99% until loop exits
                self.updateProgress.emit(self.progress)

            # Pause before next poll
            time.sleep(pause_dt)

        # Stop acquisition
        self.log("Stopping live data acquisition")
        arduino.stop_acquisition()

        elapsed_total = time.time() - t_start
        self.log(f"Acquisition complete: {blocks_ok} blocks in {elapsed_total:.1f}s "
                f"({blocks_ok/elapsed_total:.2f} blocks/s)")
        self.log(f"'None' responses: {blocks_none}")

        # Final progress update
        self.progress = 100
        self.updateProgress.emit(self.progress)

    def _plot(self, axes_list):
        """Plot the live 4-channel data in a 2x2 grid.

        Args:
            axes_list: List of pyqtgraph axes provided by the GUI.
                      axes_list[0] contains a GraphicsLayoutWidget.

        The plot shows rolling history for all 4 channels:
            - Top-left: Channel A
            - Top-right: Channel B
            - Bottom-left: Channel C
            - Bottom-right: Channel D
        """
        if self.data is None or 'histA' not in self.data:
            return

        # Check if there was an error
        if 'error' in self.data:
            return

        # Get the graphics layout widget (first element)
        if len(axes_list) == 0:
            return

        layout = axes_list[0]

        # Clear previous plots
        layout.clear()

        # Extract data
        histA = self.data['histA']
        histB = self.data['histB']
        histC = self.data['histC']
        histD = self.data['histD']
        max_hist = self.data['max_hist_samples']

        # Create sample index array
        x = np.arange(max_hist)

        # Create 2x2 subplot grid
        # Row 0, Col 0: Channel A
        ax_A = layout.addPlot(row=0, col=0, title='Channel A')
        ax_A.plot(x, histA, pen='r')
        ax_A.setLabel('left', 'ADC Counts')
        ax_A.setLabel('bottom', 'Sample Index')
        ax_A.showGrid(x=True, y=True, alpha=0.3)

        # Row 0, Col 1: Channel B
        ax_B = layout.addPlot(row=0, col=1, title='Channel B')
        ax_B.plot(x, histB, pen='g')
        ax_B.setLabel('left', 'ADC Counts')
        ax_B.setLabel('bottom', 'Sample Index')
        ax_B.showGrid(x=True, y=True, alpha=0.3)

        # Row 1, Col 0: Channel C
        ax_C = layout.addPlot(row=1, col=0, title='Channel C')
        ax_C.plot(x, histC, pen='b')
        ax_C.setLabel('left', 'ADC Counts')
        ax_C.setLabel('bottom', 'Sample Index')
        ax_C.showGrid(x=True, y=True, alpha=0.3)

        # Row 1, Col 1: Channel D
        ax_D = layout.addPlot(row=1, col=1, title='Channel D')
        ax_D.plot(x, histD, pen='y')
        ax_D.setLabel('left', 'ADC Counts')
        ax_D.setLabel('bottom', 'Sample Index')
        ax_D.showGrid(x=True, y=True, alpha=0.3)

        # Add rate info to window title (handled by base class)
        # Actual title setting would be done by the GUI if we had access to it

    def _update_plot(self, axes_list):
        """Incremental plot update during live run.

        For live plotting, we refresh the entire plot each time since
        we're updating all four subplots with rolling history data.

        Args:
            axes_list: List of axes objects.
        """
        self._plot(axes_list)

    def get_axes_layout(self, figure_list):
        """Override to specify 2x2 subplot layout.

        Args:
            figure_list: List of figure objects

        Returns:
            List containing the GraphicsLayoutWidget for 2x2 plotting
        """
        axes_list = []
        if self._plot_refresh is True:
            for graph in figure_list:
                graph.clear()
                # Return the whole GraphicsLayoutWidget, not individual plots
                # The _plot method will create the 2x2 layout within it
                axes_list.append(graph)
        else:
            for graph in figure_list:
                axes_list.append(graph)

        return axes_list
