# Created by gurudevdutt on 2026-05-13
# Converted from MATLAB scripts in matlab-feedback-arduinos/
# Controllers/feedback_arduino.py

from src.core import Device, Parameter
import logging
import time
import numpy as np
from typing import Optional, Dict, Tuple, Any

logger = logging.getLogger(__name__)


class FeedbackArduino(Device):
    """Arduino-based feedback controller for analog I/O and data acquisition.

    This device communicates with an Arduino Due running the SIS Arduino_Analog_I/O
    firmware over a serial (USB virtual COM) port. The Arduino provides:
    - Multi-channel ADC acquisition (typically 4 channels)
    - DAC output for feedback control
    - Triggered scope mode and continuous filter mode
    - Checksummed command protocol (LRC/ISO-1155)

    Hardware interface:
        - Serial USB (virtual COM port)
        - Baud rate: 115200 (default for Due native USB)
        - Terminator: LF (\n)
        - Command format: "<command> *<checksum>\n"

    Attributes:
        _DEFAULT_SETTINGS: Class-level list of Parameter objects.
        _PROBES: Dict mapping probe key → human-readable description.
    """

    _DEFAULT_SETTINGS = [
        # Serial connection parameters
        Parameter('com_port', 'COM10', str, 'Serial port (COM10 on Windows, /dev/ttyUSB0 on Linux, /dev/cu.usbmodem* on macOS)'),
        Parameter('baud_rate', 115200, int, 'Serial baud rate in Hz'),
        Parameter('timeout', 10.0, float, 'Serial timeout in s'),
        Parameter('input_buffer_size', 100000, int, 'Serial input buffer size in bytes'),
        Parameter('output_buffer_size', 100000, int, 'Serial output buffer size in bytes'),

        # Acquisition mode parameters
        Parameter('mode', 0, int, 'Acquisition mode (0=filter, 2=scope)'),

        # Common acquisition parameters
        Parameter('decimator', 100, int, 'ADC decimation factor'),
        Parameter('usb_data_n', 256, int, 'Number of int16 values per USB block'),

        # Mode 2 (triggered scope) parameters
        Parameter('trig_channel', 0, int, 'Trigger channel index (mode 2 only)'),
        Parameter('trig_level', 0, int, 'Trigger threshold (mode 2 only)'),
        Parameter('trig_hyst', 10, int, 'Trigger hysteresis (mode 2 only)'),

        # Mode 0 (filter) parameters
        Parameter('bandwidth', 1, int, 'Filter bandwidth (mode 0 only)'),
    ]

    _PROBES = {
        'status': 'ADC overload and buffer overflow flags (dict)',
        'info': 'ADC/DAC configuration and sample rates - WARNING: resets error flags (dict)',
        'adc_n_channels': 'Number of ADC channels (int)',
        'adc_sample_rate_hz': 'ADC sample rate in Hz (float)',
        'adc_clock_hz': 'ADC clock frequency in Hz (float)',
        'dac_n_channels': 'Number of DAC channels (int)',
        'is_acquiring': 'Whether data acquisition is currently running (bool)',
    }

    def __init__(self, name='FeedbackArduino', settings=None):
        """Initialize FeedbackArduino device with optional settings override.

        Args:
            name: Human-readable identifier for this device instance.
            settings: Dict of settings to override defaults.
        """
        super().__init__(name, settings)
        self._serial = None  # serial.Serial object, set in _connect()
        self._is_acquiring = False  # track acquisition state
        self._device_info = None  # cached info struct

    def _connect(self):
        """Open the serial connection to the Arduino.

        The first connection initializes the serial port, waits for the Arduino
        to enumerate, clears any startup text, and verifies communication by
        sending an 'id' query.

        Raises:
            ImportError: If pyserial is not installed.
            ConnectionError: If Arduino does not respond correctly to 'id' query.
        """
        # Lazy import of pyserial - allows repo to be imported on machines without hardware drivers
        try:
            import serial
        except ImportError:
            raise ImportError(
                "pyserial is required for FeedbackArduino. "
                "Install with: pip install pyserial"
            )

        logger.info(f"Connecting to Arduino on {self.settings['com_port']}...")
        logger.info("This may take a moment - please be patient.")

        # Create serial connection
        # Note: For native USB virtual COM on Arduino Due, the host baud rate
        # often doesn't matter much, but we use 115200 to match the Arduino source.
        self._serial = serial.Serial(
            port=self.settings['com_port'],
            baudrate=self.settings['baud_rate'],
            timeout=self.settings['timeout'],
            # Note: pyserial doesn't have input/output_buffer_size parameters
            # These are set at OS level, but we include them in settings for documentation
        )

        # Give the board time to boot/enumerate after opening the port
        time.sleep(2)

        # Clear any startup text already sitting in the input buffer
        if self._serial.in_waiting > 0:
            startup_text = self._serial.read(self._serial.in_waiting).decode('utf-8', errors='ignore')
            logger.info(f"Startup text from Arduino:\n{startup_text.strip()}")

        # Verify communication with 'id' query
        response = self._query('id')

        # Check if communication was successful
        # Expected response contains: 'SIS Arduino_Analog_I/O 20160119 TEST *14'
        if response and 'SIS Arduino_Analog_I/O' in response:
            logger.info(f"Arduino ID: {response}")
            logger.info("Communication with Arduino successful")
        else:
            logger.warning(
                f"Unexpected ID response: {response}\n"
                "If communication fails, try power cycling the Arduino and restarting Python"
            )
            raise ConnectionError(
                f"Could not establish Arduino communication. Got: {response}"
            )

    def _compute_lrc(self, payload: str) -> str:
        """Compute ISO-1155 style LRC (Longitudinal Redundancy Check) checksum.

        The Arduino SerialUSBCommandEC library uses this checksum format:
        1. Sum all payload bytes modulo 256
        2. Take two's complement: 256 - (sum mod 256)
        3. Modulo 256 again to handle edge case
        4. Convert to two-character lowercase hex

        Args:
            payload: Command string (without checksum)

        Returns:
            Two-character lowercase hex string (e.g., '3f', '0a')
        """
        # Convert payload to bytes and sum
        payload_bytes = payload.encode('utf-8')
        checksum = (256 - (sum(payload_bytes) % 256)) % 256

        # Format as two-character lowercase hex (force two digits even for values < 16)
        return format(checksum, '02x')

    def _send(self, msg: str) -> None:
        """Send one checksummed command to the Arduino.

        This method adds the LRC checksum and terminator, then sends the complete
        message. It does not wait for or parse any response.

        Command format: "<msg> *<checksum>\n"
        Example: "id *13\n"

        Args:
            msg: Command string (will be stripped of whitespace)

        Raises:
            RuntimeError: If serial connection is not open.
        """
        if not self.is_connected:
            raise RuntimeError(f"{self.name} is not connected")

        # Strip whitespace from message
        msg = msg.strip()

        # The Arduino library tokenizes on spaces and expects a trailing space
        # before the checksum, e.g. "id *13" not "id*13"
        payload = msg + ' '

        # Compute checksum
        checksum_hex = self._compute_lrc(payload)

        # Build final message with checksum and LF terminator
        full_msg = f"{payload}*{checksum_hex}\n"

        # Send as bytes
        self._serial.write(full_msg.encode('utf-8'))
        self._serial.flush()

        logger.debug(f"Sent: {full_msg.strip()}")

    def _query(self, msg: str) -> str:
        """Send command and read ASCII response.

        This is the main communication method for simple commands that return
        text responses (NOT for the 'data' command which returns binary).

        The method:
        1. Clears any stale data in the input buffer
        2. Sends the command using _send()
        3. Waits up to 2 seconds for a response
        4. Returns the stripped response string

        Args:
            msg: Command string to send

        Returns:
            Response string (stripped of whitespace), or empty string if no response

        Raises:
            RuntimeError: If serial connection is not open.
        """
        if not self.is_connected:
            raise RuntimeError(f"{self.name} is not connected")

        # Clear any stale data in the input buffer
        if self._serial.in_waiting > 0:
            self._serial.read(self._serial.in_waiting)

        # Send the command
        self._send(msg)

        # Give the device a moment to reply
        time.sleep(0.2)

        # Wait for response with timeout
        t0 = time.time()
        while self._serial.in_waiting == 0 and (time.time() - t0) < 2.0:
            time.sleep(0.02)

        # Read response if available
        if self._serial.in_waiting > 0:
            response = self._serial.read(self._serial.in_waiting).decode('utf-8', errors='ignore')
            response = response.strip()
            logger.debug(f"Received: {response}")
            return response
        else:
            logger.warning(f"No response to command: {msg}")
            return ''

    def _parse_status(self, response: str) -> Dict[str, Any]:
        """Parse the response from 'status' query.

        Expected format: 'I 0 0 0 *xx'
        Fields:
            - Header: 'I'
            - ADC overload flag (0/1)
            - ADC DMA buffer overflow flag (0/1)
            - USB output buffer overflow flag (0/1)
            - Checksum: '*xx'

        Args:
            response: Raw status response string

        Returns:
            Dict with keys:
                - raw: original response
                - header: 'I'
                - ADC_overload: bool
                - ADC_DMA_buffer_overflow: bool
                - USB_output_buffer_overflow: bool
                - any_error: bool (True if any of the above are set)
                - return_checksum: checksum string

        Raises:
            ValueError: If response format is unexpected.
        """
        if not response:
            raise ValueError("Empty status response received")

        tokens = response.split()

        if len(tokens) < 5:
            raise ValueError(f"Unexpected status response format: {response}")

        if tokens[0] != 'I':
            raise ValueError(f"Response does not look like a status packet: {response}")

        status = {
            'raw': response,
            'header': tokens[0],
            'ADC_overload': bool(int(tokens[1])),
            'ADC_DMA_buffer_overflow': bool(int(tokens[2])),
            'USB_output_buffer_overflow': bool(int(tokens[3])),
            'return_checksum': tokens[4] if len(tokens) >= 5 else '',
        }

        status['any_error'] = (
            status['ADC_overload'] or
            status['ADC_DMA_buffer_overflow'] or
            status['USB_output_buffer_overflow']
        )

        return status

    def _parse_info(self, response: str) -> Dict[str, Any]:
        """Parse the response from 'info' query.

        WARNING: The 'info' command resets/clears error flags on the Arduino.
        Do not call this unless you are ready to handle errors, as it may mask
        errors from other parts of your code.

        Expected format: 'IIIIIIII 0 4 8192 0 14000000 140000 0 4096 1 *32'
        Fields:
            - Header: 'IIIIIIII'
            - adc_differential (0/1)
            - adc_n_channels (typically 4)
            - max_samples (buffer size)
            - single_shot (0/1)
            - adc_clock_hz (Hz)
            - adc_sample_rate_hz (Hz)
            - dac_n_channels
            - dac_table_length
            - dac_sample_rate_hz (Hz)
            - Checksum: '*xx'

        Args:
            response: Raw info response string

        Returns:
            Dict with all info fields as keys

        Raises:
            ValueError: If response format is unexpected.
        """
        if not response:
            raise ValueError("Empty info response received")

        tokens = response.split()

        if len(tokens) < 11:
            raise ValueError(f"Unexpected info response format: {response}")

        if tokens[0] != 'IIIIIIII':
            raise ValueError(f"Response does not look like an info packet: {response}")

        info = {
            'raw': response,
            'header': tokens[0],
            'adc_differential': int(tokens[1]),
            'adc_n_channels': int(tokens[2]),
            'max_samples': int(tokens[3]),
            'single_shot': int(tokens[4]),
            'adc_clock_hz': float(tokens[5]),
            'adc_sample_rate_hz': float(tokens[6]),
            'dac_n_channels': int(tokens[7]),
            'dac_table_length': int(tokens[8]),
            'dac_sample_rate_hz': float(tokens[9]),
            'return_checksum': tokens[10],
        }

        return info

    def start_acquisition(self) -> str:
        """Begin the data acquisition process.

        Sends the 'start' command to the Arduino, which begins filling internal
        buffers with ADC samples. After starting, use get_data_block() or
        poll_data_block() to retrieve data.

        Returns:
            Response string from Arduino (typically 'OK' or similar)
        """
        response = self._query('start')
        self._is_acquiring = True
        logger.info("Data acquisition started")
        return response

    def stop_acquisition(self) -> str:
        """End the data acquisition process.

        Sends the 'stop' command to the Arduino, which halts ADC sampling.

        Returns:
            Response string from Arduino
        """
        response = self._query('stop')
        self._is_acquiring = False
        logger.info("Data acquisition stopped")
        return response

    def configure_scope_mode(
        self,
        decimator: int = 100,
        usb_data_n: int = 1024,
        trig_channel: int = 0,
        trig_level: int = 0,
        trig_hyst: int = 10
    ) -> str:
        """Configure Arduino in ADC oscilloscope mode (mode 2).

        In scope mode, the Arduino waits for a trigger event on the specified
        channel, then captures a block of samples.

        Args:
            decimator: ADC decimation factor (reduces sample rate)
            usb_data_n: Number of int16 values to download over USB per block
            trig_channel: Trigger channel index (0-based)
            trig_level: Trigger threshold (ADC counts)
            trig_hyst: Trigger hysteresis (ADC counts) to avoid false triggers

        Returns:
            Response string from Arduino
        """
        cmd = f"config 2 {decimator} {usb_data_n} {trig_channel} {trig_level} {trig_hyst}"
        response = self._query(cmd)

        # Update internal settings to match
        self.settings['mode'] = 2
        self.settings['decimator'] = decimator
        self.settings['usb_data_n'] = usb_data_n
        self.settings['trig_channel'] = trig_channel
        self.settings['trig_level'] = trig_level
        self.settings['trig_hyst'] = trig_hyst

        logger.info(f"Configured scope mode: decimator={decimator}, data_n={usb_data_n}, "
                   f"trig_ch={trig_channel}, level={trig_level}, hyst={trig_hyst}")
        return response

    def configure_filter_mode(
        self,
        bandwidth: int = 1,
        decimator: int = 100,
        usb_data_n: int = 256
    ) -> str:
        """Configure Arduino in mode 0: ADC filter with no downconversion.

        In filter mode, the Arduino continuously acquires data without waiting
        for triggers. This is better for continuous/live data streaming.

        Command format from firmware: config 0 <bandwidth> <decimator> <ADC_USB_data_N>

        Args:
            bandwidth: Filter bandwidth parameter
            decimator: ADC decimation factor
            usb_data_n: Number of int16 values to download over USB per block

        Returns:
            Response string from Arduino
        """
        cmd = f"config 0 {bandwidth} {decimator} {usb_data_n}"
        response = self._query(cmd)

        # Update internal settings to match
        self.settings['mode'] = 0
        self.settings['bandwidth'] = bandwidth
        self.settings['decimator'] = decimator
        self.settings['usb_data_n'] = usb_data_n

        logger.info(f"Configured filter mode: bandwidth={bandwidth}, decimator={decimator}, data_n={usb_data_n}")
        return response

    def poll_data_block(self) -> Dict[str, Any]:
        """Poll the Arduino once for a data block (single attempt, no retry).

        This sends a 'data' command and immediately tries to read the response.
        If no data is ready, returns a result with kind='none' or kind='timeout'.

        Returns:
            Dict with keys:
                - kind: 'binary', 'none', or 'timeout'
                - raw_header: Header line from Arduino
                - remaining: Samples remaining until next block (if kind='none')
                - nbytes: Number of binary bytes (if kind='binary')
                - raw_bytes: Raw uint8 bytes (if kind='binary')
                - samples_int16: Converted int16 array (if kind='binary')
                - samples_by_channel: [N_samples x N_channels] array (if kind='binary')
                - n_channels: Number of channels
                - n_samples_per_channel: Samples per channel
                - trailer: END_BINARY trailer line (if kind='binary')
        """
        if not self.is_connected:
            raise RuntimeError(f"{self.name} is not connected")

        result = {
            'kind': 'timeout',
            'raw_header': '',
            'remaining': None,
            'nbytes': 0,
            'raw_bytes': np.array([], dtype=np.uint8),
            'samples_int16': np.array([], dtype=np.int16),
            'samples_by_channel': None,
            'trailer': '',
            'n_channels': None,
            'n_samples_per_channel': None,
        }

        # Send 'data' command
        self._send('data')

        # Wait briefly for first ASCII header line
        t0 = time.time()
        while self._serial.in_waiting == 0 and (time.time() - t0) < 1.0:
            time.sleep(0.005)

        if self._serial.in_waiting == 0:
            return result  # timeout

        # Read header line
        header = self._serial.readline().decode('utf-8', errors='ignore').strip()
        result['raw_header'] = header
        tokens = header.split()

        if not tokens:
            return result

        # Handle 'SI None' response (data not ready yet)
        if tokens[0] == 'SI':
            result['kind'] = 'none'
            if len(tokens) >= 3 and tokens[1] == 'None':
                result['remaining'] = int(tokens[2])
            return result

        # Handle 'BINARY' response (data is ready)
        if tokens[0] != 'BINARY':
            raise ValueError(f"Unexpected data header: {header}")

        if len(tokens) < 2:
            raise ValueError(f"Malformed BINARY header: {header}")

        nbytes = int(tokens[1])
        if nbytes <= 0:
            raise ValueError(f"Invalid byte count in BINARY header: {header}")

        result['kind'] = 'binary'
        result['nbytes'] = nbytes

        # Read exact binary payload
        raw_bytes = self._serial.read(nbytes)
        if len(raw_bytes) != nbytes:
            raise ValueError(f"Expected {nbytes} binary bytes, got {len(raw_bytes)}")

        result['raw_bytes'] = np.frombuffer(raw_bytes, dtype=np.uint8)

        # Convert little-endian bytes to int16 array
        result['samples_int16'] = np.frombuffer(raw_bytes, dtype=np.int16)

        # Read END_BINARY trailer
        t1 = time.time()
        while self._serial.in_waiting == 0 and (time.time() - t1) < 1.0:
            time.sleep(0.005)

        if self._serial.in_waiting == 0:
            raise ValueError("Missing END_BINARY trailer")

        result['trailer'] = self._serial.readline().decode('utf-8', errors='ignore').strip()

        # Try to reshape into [Nsamp x Nch] array using board's reported channel count
        try:
            # Get channel count from cached info or query device
            if self._device_info is None:
                info = self.read_probes('info')
                self._device_info = info

            nch = self._device_info['adc_n_channels']

            if len(result['samples_int16']) % nch != 0:
                raise ValueError(
                    f"Sample count {len(result['samples_int16'])} is not divisible "
                    f"by channel count {nch}"
                )

            nsamp = len(result['samples_int16']) // nch

            # Arduino sends interleaved samples: ch0(0), ch1(0), ..., chN(0), ch0(1), ch1(1), ...
            # Reshape to [Nch x Nsamp] then transpose to [Nsamp x Nch]
            result['samples_by_channel'] = result['samples_int16'].reshape(nch, nsamp).T
            result['n_channels'] = nch
            result['n_samples_per_channel'] = nsamp

        except Exception as e:
            logger.warning(f"Could not reshape data by channel: {e}")
            result['samples_by_channel'] = None
            result['n_channels'] = None
            result['n_samples_per_channel'] = None

        return result

    def get_data_block(self, max_wait_s: float = 2.0, poll_dt: float = 0.02) -> Dict[str, Any]:
        """Poll Arduino 'data' command until a binary block is ready or timeout occurs.

        This repeatedly calls poll_data_block() until either:
        - A binary block is received (kind='binary')
        - The timeout expires

        Args:
            max_wait_s: Maximum total wait time in seconds
            poll_dt: Pause duration between retry attempts in seconds

        Returns:
            Same dict structure as poll_data_block()

        Raises:
            TimeoutError: If no data is received within max_wait_s
        """
        t0 = time.time()

        while (time.time() - t0) < max_wait_s:
            result = self.poll_data_block()

            if result['kind'] == 'binary':
                return result

            # If 'none', just wait and retry
            time.sleep(poll_dt)

        raise TimeoutError(
            f"Timed out waiting for binary data block after {max_wait_s}s. "
            f"Last header: {result['raw_header']}"
        )

    def get_4ch_data_block(self, max_wait_s: float = 5.0, poll_dt: float = 0.02) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, Dict]:
        """Convenience method to get 4-channel data as separate arrays.

        This wraps get_data_block() and extracts the four channels as individual
        column arrays.

        Args:
            max_wait_s: Maximum wait time in seconds
            poll_dt: Polling interval in seconds

        Returns:
            Tuple of (chA, chB, chC, chD, full_result_dict)
            Each channel is a 1D numpy array of int16 values.

        Raises:
            TimeoutError: If no data received within max_wait_s
            ValueError: If data does not have exactly 4 channels
        """
        result = self.get_data_block(max_wait_s, poll_dt)

        if result['kind'] != 'binary':
            raise ValueError(
                f"Did not receive binary data block. Last header: {result['raw_header']}"
            )

        if result['samples_by_channel'] is None or result['samples_by_channel'].shape[1] != 4:
            raise ValueError("Expected 4-channel data")

        data = result['samples_by_channel']
        chA = data[:, 0]
        chB = data[:, 1]
        chC = data[:, 2]
        chD = data[:, 3]

        return chA, chB, chC, chD, result

    def update(self, settings: Dict[str, Any]) -> None:
        """Apply new settings to the device.

        This base implementation just updates the internal settings dict.
        If the device needs to push settings to hardware (e.g., reconfigure mode),
        that should be done explicitly via configure_scope_mode() or configure_filter_mode().

        Args:
            settings: Dict mapping parameter name → new value
        """
        super().update(settings)

        # If we're already connected and certain settings change, we might need to
        # reconfigure the device. For now, we require explicit reconfiguration via
        # the configure_*_mode() methods.
        logger.info(f"Settings updated: {settings}")

    def read_probes(self, key: str) -> Any:
        """Query a live value from the hardware.

        Args:
            key: One of the keys defined in _PROBES

        Returns:
            The queried value

        Raises:
            KeyError: If key is not in _PROBES
            RuntimeError: If device is not connected
        """
        if key not in self._PROBES:
            raise KeyError(f"{key} is not a valid probe for {self.name}")

        if not self.is_connected:
            raise RuntimeError(f"{self.name} is not connected")

        if key == 'status':
            response = self._query('status')
            return self._parse_status(response)

        elif key == 'info':
            # WARNING: This resets error flags on the Arduino
            response = self._query('info')
            info = self._parse_info(response)
            self._device_info = info  # cache for use in data parsing
            return info

        elif key == 'adc_n_channels':
            if self._device_info is None:
                self._device_info = self.read_probes('info')
            return self._device_info['adc_n_channels']

        elif key == 'adc_sample_rate_hz':
            if self._device_info is None:
                self._device_info = self.read_probes('info')
            return self._device_info['adc_sample_rate_hz']

        elif key == 'adc_clock_hz':
            if self._device_info is None:
                self._device_info = self.read_probes('info')
            return self._device_info['adc_clock_hz']

        elif key == 'dac_n_channels':
            if self._device_info is None:
                self._device_info = self.read_probes('info')
            return self._device_info['dac_n_channels']

        elif key == 'is_acquiring':
            return self._is_acquiring

        else:
            raise KeyError(f"{key} is not a valid probe for {self.name}")

    @property
    def is_connected(self) -> bool:
        """Return True if the serial connection is active."""
        return self._serial is not None and self._serial.is_open

    def close(self) -> None:
        """Close the serial connection.

        This is called automatically by the base class context manager.
        """
        if self._serial is not None and self._serial.is_open:
            # Stop acquisition if running
            if self._is_acquiring:
                try:
                    self.stop_acquisition()
                except Exception as e:
                    logger.warning(f"Could not stop acquisition during close: {e}")

            self._serial.close()
            logger.info(f"{self.name} closed")
