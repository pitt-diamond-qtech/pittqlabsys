# Tests for HP8350B voltage sweep experiment (mock hardware).

import importlib.util
from pathlib import Path

import numpy as np
import pytest

from src.Controller import MockHP8350B, MockNI6229, MockPCI6601

# Load experiment module directly to avoid experiments/__init__.py side effects (tkinter).
_spec = importlib.util.spec_from_file_location(
    "hp8350b_voltage_sweep",
    Path(__file__).parent.parent / "src/Model/experiments/hp8350b_voltage_sweep.py",
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
HP8350BVoltageSweep = _mod.HP8350BVoltageSweep


@pytest.fixture
def mock_devices():
    hp = MockHP8350B()
    daq = MockNI6229()
    daq2 = MockPCI6601()
    return {
        'hp8350b': {'instance': hp},
        'daq': {'instance': daq},
        'daq2': {'instance': daq2},
    }


@pytest.fixture
def sweep_settings():
    return {
        'sweep': {
            'start_frequency': 2.80e9,
            'stop_frequency': 2.90e9,
            'num_points': 10,
            'voltage_min': 0.0,
            'voltage_max': 10.0,
        },
        'timing': {
            'time_per_pt': 0.010,
            'settle_time': 0.002,
        },
        'count_mode': 'counter',
        'counter_daq': 'secondary',
        'use_external_counter_clock': True,
        'microwave': {'power': -10.0, 'turn_off_after': True},
    }


def test_experiment_setup(mock_devices, sweep_settings):
    expt = HP8350BVoltageSweep(devices=mock_devices, settings=sweep_settings)
    assert len(expt.frequency_array) == 10
    assert expt.frequency_array[0] == pytest.approx(2.80e9)
    assert expt.frequency_array[-1] == pytest.approx(2.90e9)
    assert len(expt.voltage_array) == 10 * expt.clock_adjust


def test_experiment_run_counter_mode(mock_devices, sweep_settings):
    expt = HP8350BVoltageSweep(devices=mock_devices, settings=sweep_settings)
    expt.run()

    assert 'counts' in expt.data
    assert 'frequencies' in expt.data
    assert 'voltages' in expt.data
    assert len(expt.data['counts']) == sweep_settings['sweep']['num_points']
    assert len(expt.data['frequencies']) == sweep_settings['sweep']['num_points']
    assert mock_devices['hp8350b']['instance'].settings['output_enabled'] is False


def test_experiment_run_analog_mode(mock_devices, sweep_settings):
    sweep_settings['count_mode'] = 'analog'
    sweep_settings['counter_daq'] = 'same'
    expt = HP8350BVoltageSweep(devices=mock_devices, settings=sweep_settings)
    expt.run()

    assert len(expt.data['counts']) == sweep_settings['sweep']['num_points']
    assert expt.data['count_mode'] == 'analog'


def test_voltage_to_frequency_in_data(mock_devices, sweep_settings):
    expt = HP8350BVoltageSweep(devices=mock_devices, settings=sweep_settings)
    expt.run()

    hp = mock_devices['hp8350b']['instance']
    expected = hp.voltages_to_frequencies(expt.data['voltages'])
    np.testing.assert_allclose(expt.data['frequencies'], expected)


def test_same_daq_counter(mock_devices, sweep_settings):
    sweep_settings['counter_daq'] = 'same'
    expt = HP8350BVoltageSweep(devices=mock_devices, settings=sweep_settings)
    assert expt.counter_daq is mock_devices['daq']['instance']
