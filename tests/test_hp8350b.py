# Tests for HP8350B sweep oscillator device class.

import pytest
from unittest.mock import MagicMock, patch

from src.Controller.hp8350b import HP8350B


@pytest.fixture
def mock_visa_instrument():
    mock_inst = MagicMock()
    mock_inst.written = []
    mock_inst.write = MagicMock(side_effect=lambda cmd: mock_inst.written.append(cmd))
    mock_inst.query = MagicMock(return_value="HEWLETT-PACKARD,8350B,0,1.0\n")
    mock_inst.close = MagicMock()
    mock_inst.timeout = 10000
    return mock_inst


@pytest.fixture
def mock_resource_manager(mock_visa_instrument):
    mock_rm = MagicMock()
    mock_rm.open_resource = MagicMock(return_value=mock_visa_instrument)
    return mock_rm


@pytest.fixture
def hp8350b(mock_resource_manager):
    with patch("src.Controller.hp8350b.pyvisa.ResourceManager", return_value=mock_resource_manager):
        device = HP8350B(settings={
            'visa_resource': 'GPIB0::19::INSTR',
            'start_frequency': 2.80e9,
            'stop_frequency': 2.90e9,
            'voltage_min': 0.0,
            'voltage_max': 10.0,
            'power': -10.0,
        })
    return device


def test_hp8350b_connection(hp8350b):
    assert hp8350b.is_connected


def test_voltage_frequency_calibration(hp8350b):
    assert hp8350b.sweep_sensitivity == pytest.approx(10e6)  # 100 MHz / 10 V
    assert hp8350b.voltage_to_frequency(0.0) == pytest.approx(2.80e9)
    assert hp8350b.voltage_to_frequency(10.0) == pytest.approx(2.90e9)
    assert hp8350b.frequency_to_voltage(2.85e9) == pytest.approx(5.0)

    import numpy as np
    voltages = np.array([0.0, 5.0, 10.0])
    freqs = hp8350b.voltages_to_frequencies(voltages)
    assert freqs[1] == pytest.approx(2.85e9)


def test_configure_external_sweep(hp8350b, mock_visa_instrument):
    hp8350b.configure_external_sweep(
        start_freq=2.82e9,
        stop_freq=2.92e9,
        power=-5.0,
        enable_output=True,
    )
    written = mock_visa_instrument.written
    assert any("FA" in cmd for cmd in written)
    assert any("FB" in cmd for cmd in written)
    assert any("PL" in cmd for cmd in written)
    assert "SX" in written
    assert "T3" in written
    assert "RF1" in written
    assert hp8350b.settings['output_enabled'] is True


def test_output_off(hp8350b, mock_visa_instrument):
    hp8350b.output_off()
    assert "RF0" in mock_visa_instrument.written
    assert hp8350b.settings['output_enabled'] is False


def test_set_cw_frequency(hp8350b, mock_visa_instrument):
    hp8350b.set_cw_frequency(2.87e9)
    assert any("CW" in cmd and "2870000000" in cmd for cmd in mock_visa_instrument.written)
    assert hp8350b.settings['sweep_mode'] == 'cw'


def test_read_probes(hp8350b):
    assert hp8350b.read_probes('start_frequency') == 2.80e9
    assert hp8350b.read_probes('power') == -10.0
