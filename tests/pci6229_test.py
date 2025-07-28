from src.Controller.ni_daq import NIDAQ, PCI6229
import pytest
import matplotlib.pyplot as plt
import time
import numpy as np
from scipy import signal
import math

@pytest.fixture
def get_nidaq() -> NIDAQ:
    # create a fixture for the NIDAQ
    return NIDAQ()

@pytest.fixture
def get_pci6229() -> PCI6229:
    # create a fixture for the PCI6229
    return PCI6229()

def test_pci6229_connection(get_pci6229):
    """This test checks if the pci6229 is connected
    returns true if connected, AssertionError if not
    passed 07/11/2024, Abby Bakkenist
    """
    assert get_pci6229.is_connected

@pytest.mark.parametrize("channel", ["ao0", "ao1", "ao2", "ao3"])
def test_pci6229_analog_out(get_pci6229, channel):
    """This successfully test outputs AO voltages on a single channel
    passed 7/12/2024, Abby Bakkenist
    """
    daq = get_pci6229
    samp_rate = 20000.0

    period = 1e-3
    t_end = period

    num_samples = math.ceil(t_end * samp_rate)
    t_array = np.linspace(0, t_end, num_samples)
    waveform = signal.sawtooth(2 * np.pi * t_array / period, 0.5) + 1
    ao_task = daq.setup_AO([channel],waveform)
    daq.run(ao_task)
    daq.wait_to_finish(ao_task)
    daq.stop(ao_task)

def test_pci6229_ai_read(capsys, get_pci6229):
    """This test successfully reads finite samples from AI0, using an
    internal hardware-timed clock
    passed 7/18/2024, Abby Bakkenist
    """
    daq = get_pci6229
    ai_task = daq.setup_AI('ai0', num_samples_to_acquire=50)
    time.sleep(0.1)
    daq.run(ai_task)
    time.sleep(1.0)
    data, num_samples = daq.read(ai_task)
    daq.stop(ai_task)

    X = np.arange(0, num_samples)
    avg_volts_per_bin = np.mean(data)

    with capsys.disabled():
        print('AItask: ', ai_task)
        print(num_samples)
        print(data)
        print("The avg volts read was {}".format(avg_volts_per_bin))
        plt.plot(X, data[0], color='r', label='AI0')
        plt.show()

def test_pci6229_ctrout(get_pci6229):
    """This test successfully outputs a waveform on the specified counter output 
    channel for both ctr0 and ctr1
    passed 7/12/2024, Abby Bakkenist
    """
    daq = get_pci6229
    clk_task = daq.setup_clock('ctr1', 100)
    print('clktask: ', clk_task)
    time.sleep(0.1)
    daq.run(clk_task)
    daq.wait_to_finish(clk_task)
    daq.stop(clk_task)

def test_pci6229_ctr_read(capsys, get_pci6229):
    """This test successfully reads finite samples from the specified counter channel 
    using internal hardware timed clock
    passed 7/18/2024, Abby Bakkenist
    """
    daq = get_pci6229
    ctr_task = daq.setup_counter('ctr0', 50)
    samp_rate = daq.tasklist[ctr_task]['sample_rate']
    time.sleep(0.1)
    daq.run(ctr_task)
    time.sleep(0.1)
    data, nums = daq.read(ctr_task)
    avg_counts_per_bin = np.diff(data).mean()
    daq.stop(ctr_task)
    with capsys.disabled():
        print('ctrtask', ctr_task)
        print(data)
        print('The sampling rate was {}'.format(samp_rate))
        print("The avg counts per bin was {}".format(avg_counts_per_bin))
        print("The counting rate is {} cts/sec".format(avg_counts_per_bin * samp_rate))
