#!/usr/bin/env python3
"""
Pytest tests for FeedbackArduino experiment classes.

Tests cover:
- FeedbackArduinoAcquireBlock experiment
- FeedbackArduinoLivePlot experiment
- Experiment parameter validation
- Data acquisition workflow
- Plotting functionality

Usage:
    pytest tests/test_feedback_arduino_experiments.py -v
    RUN_HARDWARE_TESTS=1 pytest tests/test_feedback_arduino_experiments.py -m hardware -v
"""

import pytest
import numpy as np
from unittest.mock import Mock, MagicMock, patch
from src.Model.experiments.feedback_arduino_acquire_block import FeedbackArduinoAcquireBlock
from src.Model.experiments.feedback_arduino_live_plot import FeedbackArduinoLivePlot
from src.Controller.feedback_arduino import FeedbackArduino


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_arduino_device():
    """Mock FeedbackArduino device for testing."""
    device = Mock(spec=FeedbackArduino)
    device.name = 'mock_arduino'
    device.is_connected = True
    device._is_acquiring = False

    # Mock methods
    device.configure_scope_mode = Mock(return_value='OK')
    device.configure_filter_mode = Mock(return_value='OK')
    device.start_acquisition = Mock(return_value='OK')
    device.stop_acquisition = Mock(return_value='OK')

    # Mock data acquisition
    mock_data = np.array([
        [100, 200, 300, 400],
        [150, 250, 350, 450],
        [110, 210, 310, 410],
        [120, 220, 320, 420],
    ], dtype=np.int16)

    device.get_data_block = Mock(return_value={
        'kind': 'binary',
        'samples_by_channel': mock_data,
        'n_channels': 4,
        'n_samples_per_channel': 4,
    })

    device.poll_data_block = Mock(return_value={
        'kind': 'binary',
        'samples_by_channel': mock_data,
        'n_channels': 4,
        'n_samples_per_channel': 4,
    })

    device.read_probes = Mock(return_value={
        'adc_n_channels': 4,
        'adc_sample_rate_hz': 140000.0,
        'adc_clock_hz': 14000000.0,
    })

    return device


@pytest.fixture
def acquire_block_experiment(mock_arduino_device):
    """Create FeedbackArduinoAcquireBlock experiment with mock device."""
    devices = {'arduino': {'instance': mock_arduino_device}}

    experiment = FeedbackArduinoAcquireBlock(
        name='test_acquire_block',
        settings={'decimator': 100, 'usb_data_n': 256},
        devices=devices
    )

    return experiment


@pytest.fixture
def live_plot_experiment(mock_arduino_device):
    """Create FeedbackArduinoLivePlot experiment with mock device."""
    devices = {'arduino': {'instance': mock_arduino_device}}

    experiment = FeedbackArduinoLivePlot(
        name='test_live_plot',
        settings={'decimator': 100, 'usb_data_n': 256, 'max_runtime': 0.5},
        devices=devices
    )

    return experiment


# ============================================================================
# Test: FeedbackArduinoAcquireBlock Initialization
# ============================================================================

def test_acquire_block_initialization(acquire_block_experiment):
    """Test that acquire block experiment initializes correctly."""
    assert acquire_block_experiment.name == 'test_acquire_block'
    assert acquire_block_experiment.settings['decimator'] == 100
    assert acquire_block_experiment.settings['usb_data_n'] == 256
    assert acquire_block_experiment.settings['trig_channel'] == 0
    assert acquire_block_experiment.settings['max_wait_s'] == 5.0


def test_acquire_block_default_settings():
    """Test default settings for acquire block experiment."""
    experiment = FeedbackArduinoAcquireBlock(name='test')

    assert experiment.settings['decimator'] == 100
    assert experiment.settings['usb_data_n'] == 256
    assert experiment.settings['trig_level'] == 0
    assert experiment.settings['trig_hyst'] == 1
    assert experiment.settings['poll_dt'] == 0.02


def test_acquire_block_devices_required(acquire_block_experiment):
    """Test that acquire block requires arduino device."""
    assert 'arduino' in acquire_block_experiment._DEVICES


# ============================================================================
# Test: FeedbackArduinoAcquireBlock Execution
# ============================================================================

def test_acquire_block_run_success(acquire_block_experiment, mock_arduino_device):
    """Test successful acquisition block run."""
    # Run the experiment
    acquire_block_experiment.run()

    # Verify device methods were called
    mock_arduino_device.configure_scope_mode.assert_called_once()
    mock_arduino_device.start_acquisition.assert_called_once()
    mock_arduino_device.stop_acquisition.assert_called_once()
    mock_arduino_device.get_data_block.assert_called_once()

    # Verify data was stored
    assert acquire_block_experiment.data is not None
    assert 'samples_by_channel' in acquire_block_experiment.data
    assert 'chA' in acquire_block_experiment.data
    assert 'chB' in acquire_block_experiment.data
    assert 'chC' in acquire_block_experiment.data
    assert 'chD' in acquire_block_experiment.data
    assert acquire_block_experiment.data['n_channels'] == 4


def test_acquire_block_data_structure(acquire_block_experiment):
    """Test that acquired data has correct structure."""
    acquire_block_experiment.run()

    data = acquire_block_experiment.data

    # Check data arrays
    assert isinstance(data['samples_by_channel'], np.ndarray)
    assert data['samples_by_channel'].shape[1] == 4  # 4 channels
    assert len(data['chA']) == data['n_samples']
    assert len(data['chB']) == data['n_samples']
    assert len(data['chC']) == data['n_samples']
    assert len(data['chD']) == data['n_samples']


def test_acquire_block_timeout_handling(acquire_block_experiment, mock_arduino_device):
    """Test handling of acquisition timeout."""
    # Make get_data_block raise TimeoutError
    mock_arduino_device.get_data_block.side_effect = TimeoutError("Timeout")

    acquire_block_experiment.run()

    # Verify error was stored in data
    assert 'error' in acquire_block_experiment.data
    assert 'Timeout' in acquire_block_experiment.data['error']

    # Verify stop was still called
    mock_arduino_device.stop_acquisition.assert_called_once()


def test_acquire_block_exception_handling(acquire_block_experiment, mock_arduino_device):
    """Test handling of general exceptions during acquisition."""
    # Make get_data_block raise generic exception
    mock_arduino_device.get_data_block.side_effect = RuntimeError("Device error")

    acquire_block_experiment.run()

    # Verify error was stored
    assert 'error' in acquire_block_experiment.data
    assert 'Device error' in acquire_block_experiment.data['error']


def test_acquire_block_abort(acquire_block_experiment, mock_arduino_device):
    """Test aborting acquisition."""
    # Set abort flag before run
    acquire_block_experiment._abort = True

    acquire_block_experiment.run()

    # Should still clean up (stop acquisition)
    # Note: _function checks _abort but in this test setup it won't be checked
    # during the mock calls, so we just verify the experiment completes


# ============================================================================
# Test: FeedbackArduinoAcquireBlock Plotting
# ============================================================================

def test_acquire_block_plot_with_data(acquire_block_experiment):
    """Test plotting with valid data."""
    # Run experiment to populate data
    acquire_block_experiment.run()

    # Create mock axes
    mock_ax = Mock()
    mock_ax.clear = Mock()
    mock_ax.plot = Mock()
    mock_ax.setLabel = Mock()
    mock_ax.setTitle = Mock()
    mock_ax.addLegend = Mock()

    # Call plot
    acquire_block_experiment._plot([mock_ax])

    # Verify plotting methods were called
    mock_ax.clear.assert_called_once()
    assert mock_ax.plot.call_count == 4  # 4 channels


def test_acquire_block_plot_no_data(acquire_block_experiment):
    """Test plotting with no data (should not crash)."""
    acquire_block_experiment.data = None

    mock_ax = Mock()
    acquire_block_experiment._plot([mock_ax])

    # Should not call any plot methods
    mock_ax.plot.assert_not_called()


def test_acquire_block_plot_with_error(acquire_block_experiment):
    """Test plotting when acquisition had error."""
    acquire_block_experiment.data = {'error': 'Test error'}

    mock_ax = Mock()
    acquire_block_experiment._plot([mock_ax])

    # Should not crash, but not plot either
    mock_ax.plot.assert_not_called()


# ============================================================================
# Test: FeedbackArduinoLivePlot Initialization
# ============================================================================

def test_live_plot_initialization(live_plot_experiment):
    """Test that live plot experiment initializes correctly."""
    assert live_plot_experiment.name == 'test_live_plot'
    assert live_plot_experiment.settings['decimator'] == 100
    assert live_plot_experiment.settings['bandwidth'] == 1
    assert live_plot_experiment.settings['history_blocks'] == 200
    assert live_plot_experiment.settings['max_runtime'] == 0.5


def test_live_plot_default_settings():
    """Test default settings for live plot experiment."""
    experiment = FeedbackArduinoLivePlot(name='test')

    assert experiment.settings['bandwidth'] == 1
    assert experiment.settings['decimator'] == 100
    assert experiment.settings['pause_dt'] == 0.01
    assert experiment.settings['history_blocks'] == 200
    assert experiment.settings['max_runtime'] == 60.0


def test_live_plot_devices_required(live_plot_experiment):
    """Test that live plot requires arduino device."""
    assert 'arduino' in live_plot_experiment._DEVICES


# ============================================================================
# Test: FeedbackArduinoLivePlot Execution
# ============================================================================

def test_live_plot_run_success(live_plot_experiment, mock_arduino_device):
    """Test successful live plot run."""
    # Make poll return binary data a few times, then set abort
    call_count = 0

    def poll_side_effect():
        nonlocal call_count
        call_count += 1
        if call_count > 3:
            live_plot_experiment._abort = True

        return {
            'kind': 'binary',
            'samples_by_channel': np.random.randint(-1000, 1000, (4, 4), dtype=np.int16).T,
            'n_channels': 4,
            'n_samples_per_channel': 4,
        }

    mock_arduino_device.poll_data_block.side_effect = poll_side_effect

    # Run experiment
    live_plot_experiment.run()

    # Verify device methods were called
    mock_arduino_device.configure_filter_mode.assert_called_once()
    mock_arduino_device.start_acquisition.assert_called_once()
    mock_arduino_device.stop_acquisition.assert_called_once()

    # Verify data was stored
    assert live_plot_experiment.data is not None
    assert 'histA' in live_plot_experiment.data
    assert 'histB' in live_plot_experiment.data
    assert 'block_count' in live_plot_experiment.data
    assert live_plot_experiment.data['block_count'] >= 1


def test_live_plot_rolling_buffer(live_plot_experiment, mock_arduino_device):
    """Test that rolling history buffer works correctly."""
    # Create consistent mock data
    mock_data = np.array([[100, 200, 300, 400]] * 4, dtype=np.int16)

    call_count = 0

    def poll_side_effect():
        nonlocal call_count
        call_count += 1
        if call_count > 5:
            live_plot_experiment._abort = True

        return {
            'kind': 'binary',
            'samples_by_channel': mock_data,
            'n_channels': 4,
            'n_samples_per_channel': 4,
        }

    mock_arduino_device.poll_data_block.side_effect = poll_side_effect

    live_plot_experiment.run()

    # Check history buffers
    assert len(live_plot_experiment.data['histA']) == live_plot_experiment.data['max_hist_samples']
    assert len(live_plot_experiment.data['histB']) == live_plot_experiment.data['max_hist_samples']


def test_live_plot_none_response_handling(live_plot_experiment, mock_arduino_device):
    """Test handling of 'none' responses during polling."""
    call_count = 0

    def poll_side_effect():
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            return {'kind': 'none', 'remaining': 50}
        elif call_count <= 4:
            return {
                'kind': 'binary',
                'samples_by_channel': np.array([[100, 200, 300, 400]] * 4, dtype=np.int16),
                'n_channels': 4,
                'n_samples_per_channel': 4,
            }
        else:
            live_plot_experiment._abort = True
            return {'kind': 'none', 'remaining': 0}

    mock_arduino_device.poll_data_block.side_effect = poll_side_effect

    live_plot_experiment.run()

    # Should have recorded 'none' responses
    assert live_plot_experiment.data['none_count'] >= 2


def test_live_plot_max_runtime(live_plot_experiment, mock_arduino_device):
    """Test that experiment stops after max_runtime."""
    # Set very short runtime
    live_plot_experiment.settings['max_runtime'] = 0.1

    # Make poll always return data
    mock_arduino_device.poll_data_block.return_value = {
        'kind': 'binary',
        'samples_by_channel': np.array([[100, 200, 300, 400]] * 4, dtype=np.int16),
        'n_channels': 4,
        'n_samples_per_channel': 4,
    }

    import time
    start = time.time()
    live_plot_experiment.run()
    elapsed = time.time() - start

    # Should stop near max_runtime (with some tolerance for loop overhead)
    assert elapsed < 1.0  # Should be much less than default 60s


def test_live_plot_invalid_channel_count(live_plot_experiment, mock_arduino_device):
    """Test handling of invalid channel count from device."""
    # Mock info to return wrong channel count
    mock_arduino_device.read_probes.return_value = {
        'adc_n_channels': 2,  # Wrong! Should be 4
        'adc_sample_rate_hz': 140000.0,
    }

    live_plot_experiment.run()

    # Should have error in data
    assert 'error' in live_plot_experiment.data
    assert '4 channels' in live_plot_experiment.data['error']


# ============================================================================
# Test: FeedbackArduinoLivePlot Plotting
# ============================================================================

def test_live_plot_plotting_2x2_grid(live_plot_experiment, mock_arduino_device):
    """Test that live plot creates 2x2 subplot grid."""
    # Run experiment briefly to populate data
    call_count = 0

    def poll_side_effect():
        nonlocal call_count
        call_count += 1
        if call_count > 2:
            live_plot_experiment._abort = True
        return {
            'kind': 'binary',
            'samples_by_channel': np.array([[100, 200, 300, 400]] * 4, dtype=np.int16),
            'n_channels': 4,
            'n_samples_per_channel': 4,
        }

    mock_arduino_device.poll_data_block.side_effect = poll_side_effect

    live_plot_experiment.run()

    # Create mock GraphicsLayoutWidget
    mock_layout = Mock()
    mock_layout.clear = Mock()
    mock_layout.addPlot = Mock(return_value=Mock())

    # Call plot
    live_plot_experiment._plot([mock_layout])

    # Verify 2x2 grid was created
    assert mock_layout.addPlot.call_count == 4  # 4 subplots

    # Check that correct positions were used
    calls = mock_layout.addPlot.call_args_list
    positions = [(call[1]['row'], call[1]['col']) for call in calls]
    assert (0, 0) in positions  # Channel A
    assert (0, 1) in positions  # Channel B
    assert (1, 0) in positions  # Channel C
    assert (1, 1) in positions  # Channel D


def test_live_plot_no_data_no_crash(live_plot_experiment):
    """Test that plotting with no data doesn't crash."""
    live_plot_experiment.data = None

    mock_layout = Mock()
    live_plot_experiment._plot([mock_layout])

    # Should not crash
    mock_layout.clear.assert_not_called()


def test_live_plot_get_axes_layout(live_plot_experiment):
    """Test get_axes_layout returns GraphicsLayoutWidget."""
    mock_graph = Mock()
    mock_graph.clear = Mock()

    # First call (plot_refresh=True)
    live_plot_experiment._plot_refresh = True
    axes = live_plot_experiment.get_axes_layout([mock_graph])

    assert len(axes) == 1
    assert axes[0] == mock_graph
    mock_graph.clear.assert_called_once()


# ============================================================================
# Test: Experiment Parameter Validation
# ============================================================================

def test_acquire_block_parameter_update(acquire_block_experiment):
    """Test updating experiment parameters."""
    acquire_block_experiment.update({
        'decimator': 200,
        'trig_level': 500,
    })

    assert acquire_block_experiment.settings['decimator'] == 200
    assert acquire_block_experiment.settings['trig_level'] == 500


def test_live_plot_parameter_update(live_plot_experiment):
    """Test updating live plot parameters."""
    live_plot_experiment.update({
        'bandwidth': 2,
        'history_blocks': 100,
    })

    assert live_plot_experiment.settings['bandwidth'] == 2
    assert live_plot_experiment.settings['history_blocks'] == 100


# ============================================================================
# Hardware Tests (require RUN_HARDWARE_TESTS=1; see tests/conftest.py)
# ============================================================================

@pytest.mark.hardware
def test_acquire_block_real_hardware():
    """Test acquire block with real hardware."""
    from src.core.device_config import load_devices_from_config
    from pathlib import Path

    # Load real device
    config_path = Path(__file__).parent.parent / 'src' / 'config.json'
    devices, failed = load_devices_from_config(config_path)

    if 'feedback_arduino' not in devices:
        pytest.skip("FeedbackArduino not configured in config.json")

    arduino = devices['feedback_arduino']

    # Create experiment
    experiment = FeedbackArduinoAcquireBlock(
        name='hardware_test',
        devices={'arduino': {'instance': arduino}},
        settings={'usb_data_n': 256, 'max_wait_s': 10.0}
    )

    # Run experiment
    experiment.run()

    # Verify data was acquired
    assert experiment.data is not None
    assert 'samples_by_channel' in experiment.data
    assert experiment.data['n_channels'] == 4
    assert experiment.data['n_samples'] > 0


@pytest.mark.hardware
def test_live_plot_real_hardware():
    """Test live plot with real hardware (brief run)."""
    from src.core.device_config import load_devices_from_config
    from pathlib import Path

    # Load real device
    config_path = Path(__file__).parent.parent / 'src' / 'config.json'
    devices, failed = load_devices_from_config(config_path)

    if 'feedback_arduino' not in devices:
        pytest.skip("FeedbackArduino not configured in config.json")

    arduino = devices['feedback_arduino']

    # Create experiment with short runtime
    experiment = FeedbackArduinoLivePlot(
        name='hardware_test',
        devices={'arduino': {'instance': arduino}},
        settings={'max_runtime': 2.0, 'history_blocks': 50}
    )

    # Run experiment
    experiment.run()

    # Verify data was acquired
    assert experiment.data is not None
    assert 'histA' in experiment.data
    assert experiment.data['block_count'] > 0


# ============================================================================
# Main (for direct execution)
# ============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
