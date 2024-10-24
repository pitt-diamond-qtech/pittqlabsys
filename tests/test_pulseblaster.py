from src.Controller.pulse_blaster import *
import pytest
import numpy as np
from scipy import signal
import math

@pytest.fixture()
def test_pulse_blaster(get_pci6229, channel):
    device = PulseBlaster
    samp_rate = 20000.0

    period = 1e-3
    t_end = period

    num_samples = math.ceil(t_end * samp_rate)
    t_array = np.linspace(0, t_end, num_samples)
    waveform = signal.sawtooth(2 * np.pi * t_array / period, 0.5) + 1
    ao_task = device.setup_AO([channel],waveform)
    device.run(ao_task)
    device.wait_to_finish(ao_task)
    device.stop(ao_task)