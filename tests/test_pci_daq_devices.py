# Unit tests for PCI6229 and PCI6601 device classes (no hardware required).

import pytest

from src.Controller import MockNI6229, MockPCI6601, PCI6229, PCI6601


class TestPCI6229Mock:
    """Tests using MockNI6229 (runs on all platforms)."""

    @pytest.fixture
    def daq(self):
        return MockNI6229()

    def test_connection(self, daq):
        assert daq.is_connected

    def test_setup_ao(self, daq):
        import numpy as np
        waveform = np.linspace(0, 10, 20)
        task = daq.setup_AO(['ao0'], waveform)
        assert task in daq._tasks
        assert daq._tasks[task]['type'] == 'AO'

    def test_setup_counter(self, daq):
        task = daq.setup_counter('ctr0', 50)
        assert task in daq._tasks
        assert daq._tasks[task]['length'] == 50

    def test_counter_read_returns_data(self, daq):
        task = daq.setup_counter('ctr0', 100)
        daq.run(task)
        data, _ = daq.read(task)
        daq.stop(task)
        assert len(data) == 1000  # mock returns fixed length

    def test_digital_input_settings(self, daq):
        assert 'ctr0' in daq.settings['digital_input']
        assert 'sample_rate' in daq.settings['digital_input']['ctr0']


class TestPCI6601Mock:
    """Tests using MockPCI6601 (runs on all platforms)."""

    @pytest.fixture
    def daq(self):
        return MockPCI6601()

    def test_connection(self, daq):
        assert daq.is_connected

    def test_setup_counter(self, daq):
        task = daq.setup_counter('ctr0', 30, use_external_clock=True)
        assert task in daq._tasks
        assert daq._tasks[task]['use_external_clock'] is True

    def test_read_counter(self, daq):
        task = daq.setup_counter('ctr1', 50)
        daq.run(task)
        data, _ = daq.read(task)
        daq.stop(task)
        assert len(data) > 0


@pytest.mark.hardware
class TestPCI6229Hardware:
    """Hardware tests for PCI6229 (Windows + NI-DAQ only)."""

    @pytest.fixture
    def daq(self):
        return PCI6229()

    def test_connection(self, daq):
        assert daq.is_connected

    def test_settings_have_ao_and_counter(self, daq):
        assert 'ao0' in daq.settings['analog_output']
        assert 'ctr0' in daq.settings['digital_input']


@pytest.mark.hardware
class TestPCI6601Hardware:
    """Hardware tests for PCI6601 (Windows + NI-DAQ only)."""

    @pytest.fixture
    def daq(self):
        return PCI6601()

    def test_connection(self, daq):
        assert daq.is_connected

    def test_counter_channels_configured(self, daq):
        assert 'ctr0' in daq.settings['digital_input']
        assert 'ctr1' in daq.settings['digital_input']
