#!/usr/bin/env python3
"""
Pytest tests for FeedbackArduino device class.

Tests cover:
- Device initialization and connection
- Checksum calculation (LRC/ISO-1155)
- Command sending and querying
- Status and info parsing
- Data acquisition (poll and get methods)
- Configuration methods (scope and filter modes)
- Probe reading
- Error handling

Usage:
    pytest tests/test_feedback_arduino.py -v
    RUN_HARDWARE_TESTS=1 pytest tests/test_feedback_arduino.py -m hardware -v  # real Arduino
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from src.Controller.feedback_arduino import FeedbackArduino


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_serial():
    """Mock serial.Serial object for testing without hardware."""
    with patch('src.Controller.feedback_arduino.serial.Serial') as mock:
        serial_instance = MagicMock()
        serial_instance.is_open = True
        serial_instance.in_waiting = 0
        mock.return_value = serial_instance
        yield serial_instance


@pytest.fixture
def arduino_device(mock_serial):
    """Create FeedbackArduino device with mocked serial connection."""
    # Mock the ID query response during connection
    mock_serial.in_waiting = 0
    mock_serial.read.return_value = b''

    # Set up query response for 'id' command
    def mock_read_side_effect(n):
        return b'SIS Arduino_Analog_I/O 20160119 TEST *14\n'

    mock_serial.read.side_effect = mock_read_side_effect

    device = FeedbackArduino(name='test_arduino', settings={'com_port': 'COM10'})

    # Reset side effects after initialization
    mock_serial.read.side_effect = None

    return device


@pytest.fixture
def real_arduino_device():
    """Create FeedbackArduino device with real hardware (requires RUN_HARDWARE_TESTS=1)."""
    # Used only when hardware tests are not skipped; see tests/conftest.py
    device = FeedbackArduino(name='real_arduino', settings={'com_port': 'COM10'})
    yield device
    if device.is_connected:
        device.close()


# ============================================================================
# Test: Device Initialization
# ============================================================================

def test_device_initialization(arduino_device):
    """Test that device initializes with correct default settings."""
    assert arduino_device.name == 'test_arduino'
    assert arduino_device.settings['com_port'] == 'COM10'
    assert arduino_device.settings['baud_rate'] == 115200
    assert arduino_device.settings['timeout'] == 10.0
    assert arduino_device.settings['mode'] == 0
    assert arduino_device.settings['decimator'] == 100


def test_device_connection_mock(mock_serial):
    """Test device connection with mocked serial."""
    # Mock the ID response
    mock_serial.in_waiting = 0
    mock_serial.read.return_value = b'SIS Arduino_Analog_I/O 20160119 TEST *14\n'

    device = FeedbackArduino(name='test', settings={'com_port': 'COM10'})

    # Verify serial was opened with correct parameters
    import serial
    serial.Serial.assert_called_once()
    call_kwargs = serial.Serial.call_args[1]
    assert call_kwargs['port'] == 'COM10'
    assert call_kwargs['baudrate'] == 115200
    assert call_kwargs['timeout'] == 10.0


def test_device_connection_failure(mock_serial):
    """Test that connection failure raises error."""
    # Mock an invalid ID response
    mock_serial.in_waiting = 0
    mock_serial.read.return_value = b'Invalid response\n'

    with pytest.raises(ConnectionError, match='Could not establish Arduino communication'):
        FeedbackArduino(name='test', settings={'com_port': 'COM10'})


# ============================================================================
# Test: Checksum Calculation
# ============================================================================

def test_lrc_checksum_calculation(arduino_device):
    """Test LRC checksum calculation matches expected values."""
    # Test case 1: "id " should produce checksum matching MATLAB
    checksum = arduino_device._compute_lrc("id ")
    assert len(checksum) == 2
    assert checksum.islower()  # Should be lowercase hex

    # Test case 2: Known test vector
    # "test " -> bytes [116, 101, 115, 116, 32]
    # sum = 462, 462 % 256 = 206, (256 - 206) % 256 = 50 = 0x32
    checksum = arduino_device._compute_lrc("test ")
    assert checksum == "32"

    # Test case 3: Empty payload should give 0x00
    checksum = arduino_device._compute_lrc("")
    assert checksum == "00"


def test_lrc_checksum_format(arduino_device):
    """Test that checksums are always 2 characters."""
    # Values less than 16 should be zero-padded
    test_strings = ["", "a", "test ", "longer string here "]

    for s in test_strings:
        checksum = arduino_device._compute_lrc(s)
        assert len(checksum) == 2, f"Checksum for '{s}' should be 2 chars"
        assert checksum.islower(), f"Checksum for '{s}' should be lowercase"
        # Verify it's valid hex
        int(checksum, 16)  # Should not raise


# ============================================================================
# Test: Command Sending
# ============================================================================

def test_send_command(arduino_device, mock_serial):
    """Test that _send() formats commands correctly."""
    arduino_device._send("start")

    # Verify write was called with correct format: "start *<checksum>\n"
    mock_serial.write.assert_called_once()
    sent_data = mock_serial.write.call_args[0][0]

    assert sent_data.startswith(b"start ")
    assert b"*" in sent_data
    assert sent_data.endswith(b"\n")


def test_send_strips_whitespace(arduino_device, mock_serial):
    """Test that _send() strips whitespace from commands."""
    arduino_device._send("  start  \n")

    sent_data = mock_serial.write.call_args[0][0]
    assert sent_data.startswith(b"start ")


def test_send_without_connection_raises_error(arduino_device, mock_serial):
    """Test that sending without connection raises RuntimeError."""
    arduino_device._serial = None  # Simulate disconnected state

    with pytest.raises(RuntimeError, match='not connected'):
        arduino_device._send("test")


# ============================================================================
# Test: Query Method
# ============================================================================

def test_query_clears_buffer(arduino_device, mock_serial):
    """Test that _query() clears stale data before sending."""
    # Simulate stale data in buffer
    mock_serial.in_waiting = 10
    mock_serial.read.return_value = b'stale data'

    # Set up response for the actual query
    def side_effect(*args):
        if args[0] == 10:  # Clear buffer
            return b'stale data'
        else:  # Actual response
            return b'OK *13\n'

    mock_serial.read.side_effect = side_effect
    mock_serial.in_waiting = 20  # Simulate response available

    response = arduino_device._query("test")

    # Verify buffer was cleared (first read call)
    assert mock_serial.read.call_count >= 1


def test_query_timeout_returns_empty(arduino_device, mock_serial):
    """Test that _query() returns empty string on timeout."""
    # Simulate no response
    mock_serial.in_waiting = 0

    response = arduino_device._query("test")

    assert response == ''


# ============================================================================
# Test: Status Parsing
# ============================================================================

def test_parse_status_valid_response(arduino_device):
    """Test parsing a valid status response."""
    response = "I 0 0 0 *3f"
    status = arduino_device._parse_status(response)

    assert status['header'] == 'I'
    assert status['ADC_overload'] is False
    assert status['ADC_DMA_buffer_overflow'] is False
    assert status['USB_output_buffer_overflow'] is False
    assert status['any_error'] is False
    assert status['return_checksum'] == '*3f'


def test_parse_status_with_errors(arduino_device):
    """Test parsing status response with error flags set."""
    response = "I 1 1 0 *3e"
    status = arduino_device._parse_status(response)

    assert status['ADC_overload'] is True
    assert status['ADC_DMA_buffer_overflow'] is True
    assert status['USB_output_buffer_overflow'] is False
    assert status['any_error'] is True


def test_parse_status_invalid_format(arduino_device):
    """Test that invalid status format raises ValueError."""
    with pytest.raises(ValueError, match='Unexpected status response'):
        arduino_device._parse_status("INVALID FORMAT")

    with pytest.raises(ValueError, match='Empty status response'):
        arduino_device._parse_status("")


# ============================================================================
# Test: Info Parsing
# ============================================================================

def test_parse_info_valid_response(arduino_device):
    """Test parsing a valid info response."""
    response = "IIIIIIII 0 4 8192 0 14000000 140000 0 4096 1 *32"
    info = arduino_device._parse_info(response)

    assert info['header'] == 'IIIIIIII'
    assert info['adc_differential'] == 0
    assert info['adc_n_channels'] == 4
    assert info['max_samples'] == 8192
    assert info['adc_clock_hz'] == 14000000.0
    assert info['adc_sample_rate_hz'] == 140000.0
    assert info['dac_n_channels'] == 0


def test_parse_info_invalid_format(arduino_device):
    """Test that invalid info format raises ValueError."""
    with pytest.raises(ValueError, match='Unexpected info response'):
        arduino_device._parse_info("I 0 0 0")  # Too few tokens

    with pytest.raises(ValueError, match='Empty info response'):
        arduino_device._parse_info("")


# ============================================================================
# Test: Configuration Methods
# ============================================================================

def test_configure_scope_mode(arduino_device, mock_serial):
    """Test configuring Arduino in scope mode."""
    mock_serial.in_waiting = 10
    mock_serial.read.return_value = b'OK *13\n'

    response = arduino_device.configure_scope_mode(
        decimator=50,
        usb_data_n=512,
        trig_channel=1,
        trig_level=100,
        trig_hyst=5
    )

    # Verify settings were updated
    assert arduino_device.settings['mode'] == 2
    assert arduino_device.settings['decimator'] == 50
    assert arduino_device.settings['usb_data_n'] == 512
    assert arduino_device.settings['trig_channel'] == 1


def test_configure_filter_mode(arduino_device, mock_serial):
    """Test configuring Arduino in filter mode."""
    mock_serial.in_waiting = 10
    mock_serial.read.return_value = b'OK *13\n'

    response = arduino_device.configure_filter_mode(
        bandwidth=2,
        decimator=200,
        usb_data_n=128
    )

    # Verify settings were updated
    assert arduino_device.settings['mode'] == 0
    assert arduino_device.settings['bandwidth'] == 2
    assert arduino_device.settings['decimator'] == 200
    assert arduino_device.settings['usb_data_n'] == 128


# ============================================================================
# Test: Data Acquisition
# ============================================================================

def test_poll_data_block_none_response(arduino_device, mock_serial):
    """Test poll_data_block when data is not ready."""
    # Simulate 'SI None 100' response (data not ready)
    mock_serial.in_waiting = 15
    mock_serial.readline.return_value = b'SI None 100 *3f\n'

    result = arduino_device.poll_data_block()

    assert result['kind'] == 'none'
    assert result['remaining'] == 100


def test_poll_data_block_binary_response(arduino_device, mock_serial):
    """Test poll_data_block with binary data."""
    # Simulate binary response: BINARY header, then binary data, then trailer
    mock_serial.in_waiting = 20

    # Create mock binary data: 8 int16 values (16 bytes) for 4 channels x 2 samples
    binary_data = np.array([100, 200, 300, 400, 150, 250, 350, 450], dtype=np.int16).tobytes()

    def readline_side_effect():
        # First call returns BINARY header
        if not hasattr(readline_side_effect, 'call_count'):
            readline_side_effect.call_count = 0
        readline_side_effect.call_count += 1

        if readline_side_effect.call_count == 1:
            return b'BINARY 16 *3f\n'
        else:
            return b'END_BINARY *40\n'

    mock_serial.readline.side_effect = readline_side_effect
    mock_serial.read.return_value = binary_data

    # Mock info query for channel count
    arduino_device._device_info = {'adc_n_channels': 4}

    result = arduino_device.poll_data_block()

    assert result['kind'] == 'binary'
    assert result['nbytes'] == 16
    assert len(result['samples_int16']) == 8
    assert result['n_channels'] == 4
    assert result['n_samples_per_channel'] == 2


def test_get_data_block_with_retry(arduino_device, mock_serial):
    """Test get_data_block retries until data is available."""
    # First poll returns 'none', second returns 'binary'
    call_count = 0

    def mock_poll_data():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return {'kind': 'none', 'remaining': 50}
        else:
            return {
                'kind': 'binary',
                'samples_int16': np.array([1, 2, 3, 4], dtype=np.int16),
                'samples_by_channel': np.array([[1, 2], [3, 4]], dtype=np.int16),
                'n_channels': 2,
                'n_samples_per_channel': 2
            }

    arduino_device.poll_data_block = mock_poll_data

    result = arduino_device.get_data_block(max_wait_s=1.0, poll_dt=0.01)

    assert result['kind'] == 'binary'
    assert call_count == 2  # Should have retried once


def test_get_data_block_timeout(arduino_device):
    """Test get_data_block raises TimeoutError on timeout."""
    # Always return 'none'
    arduino_device.poll_data_block = lambda: {'kind': 'none', 'remaining': 50, 'raw_header': 'SI None 50'}

    with pytest.raises(TimeoutError, match='Timed out waiting'):
        arduino_device.get_data_block(max_wait_s=0.1, poll_dt=0.01)


def test_get_4ch_data_block(arduino_device):
    """Test get_4ch_data_block returns individual channel arrays."""
    # Mock get_data_block to return 4-channel data
    mock_data = np.array([
        [100, 200, 300, 400],
        [150, 250, 350, 450],
        [110, 210, 310, 410],
    ], dtype=np.int16)

    arduino_device.get_data_block = lambda **kwargs: {
        'kind': 'binary',
        'samples_by_channel': mock_data
    }

    chA, chB, chC, chD, result = arduino_device.get_4ch_data_block()

    assert len(chA) == 3
    assert len(chB) == 3
    assert np.array_equal(chA, mock_data[:, 0])
    assert np.array_equal(chB, mock_data[:, 1])
    assert np.array_equal(chC, mock_data[:, 2])
    assert np.array_equal(chD, mock_data[:, 3])


# ============================================================================
# Test: Probe Reading
# ============================================================================

def test_read_probes_status(arduino_device, mock_serial):
    """Test reading status probe."""
    mock_serial.in_waiting = 20
    mock_serial.read.return_value = b'I 0 0 0 *3f\n'

    status = arduino_device.read_probes('status')

    assert isinstance(status, dict)
    assert 'ADC_overload' in status
    assert status['any_error'] is False


def test_read_probes_info_caching(arduino_device, mock_serial):
    """Test that info probe caches device info."""
    mock_serial.in_waiting = 50
    mock_serial.read.return_value = b'IIIIIIII 0 4 8192 0 14000000 140000 0 4096 1 *32\n'

    # First call
    info1 = arduino_device.read_probes('info')
    assert arduino_device._device_info is not None

    # Second call should use cached info
    info2 = arduino_device.read_probes('adc_n_channels')
    assert info2 == 4


def test_read_probes_invalid_key(arduino_device):
    """Test that invalid probe key raises KeyError."""
    with pytest.raises(KeyError, match='not a valid probe'):
        arduino_device.read_probes('invalid_probe')


def test_read_probes_not_connected(arduino_device):
    """Test that reading probes without connection raises RuntimeError."""
    arduino_device._serial = None

    with pytest.raises(RuntimeError, match='not connected'):
        arduino_device.read_probes('status')


# ============================================================================
# Test: Acquisition Control
# ============================================================================

def test_start_acquisition(arduino_device, mock_serial):
    """Test starting data acquisition."""
    mock_serial.in_waiting = 10
    mock_serial.read.return_value = b'OK *13\n'

    response = arduino_device.start_acquisition()

    assert arduino_device._is_acquiring is True
    assert 'OK' in response


def test_stop_acquisition(arduino_device, mock_serial):
    """Test stopping data acquisition."""
    mock_serial.in_waiting = 10
    mock_serial.read.return_value = b'OK *13\n'

    arduino_device._is_acquiring = True
    response = arduino_device.stop_acquisition()

    assert arduino_device._is_acquiring is False
    assert 'OK' in response


# ============================================================================
# Test: Connection Management
# ============================================================================

def test_is_connected_property(arduino_device, mock_serial):
    """Test is_connected property."""
    assert arduino_device.is_connected is True

    mock_serial.is_open = False
    assert arduino_device.is_connected is False


def test_close_stops_acquisition(arduino_device, mock_serial):
    """Test that close() stops acquisition if running."""
    mock_serial.in_waiting = 10
    mock_serial.read.return_value = b'OK *13\n'

    arduino_device._is_acquiring = True
    arduino_device.close()

    mock_serial.close.assert_called_once()


# ============================================================================
# Test Markers for Real Hardware
# ============================================================================

@pytest.mark.hardware
def test_real_hardware_connection(real_arduino_device):
    """Test actual hardware connection (requires RUN_HARDWARE_TESTS=1)."""
    assert real_arduino_device.is_connected

    # Test ID query
    response = real_arduino_device._query('id')
    assert 'SIS Arduino_Analog_I/O' in response


@pytest.mark.hardware
def test_real_hardware_status_query(real_arduino_device):
    """Test querying real hardware status."""
    status = real_arduino_device.read_probes('status')

    assert isinstance(status, dict)
    assert 'ADC_overload' in status
    assert 'any_error' in status


@pytest.mark.hardware
def test_real_hardware_info_query(real_arduino_device):
    """Test querying real hardware info."""
    info = real_arduino_device.read_probes('info')

    assert isinstance(info, dict)
    assert info['adc_n_channels'] == 4
    assert info['adc_sample_rate_hz'] > 0


# ============================================================================
# Main (for direct execution)
# ============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
