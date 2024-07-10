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
    """
    assert get_pci6229.is_connected

@pytest.mark.parametrize("channel", ["ao0", "ao1", "ao2", "ao3"])
def test_pci6229_analog_out(get_pci6229, channel):
    """This test outputs AO voltages on a single channel
    """
    daq = get_pci6229
    samp_rate = 20000.0

    period = 1e-3
    t_end = period

    num_samples = math.ceil(t_end * samp_rate)
    t_array = np.linspace(0, t_end, num_samples)
    waveform = np.sin(2 * np.pi * t_array / period)
    waveform2 = signal.sawtooth(2 * np.pi * t_array / period, 0.5) + 1
    ao_task = daq.setup_AO([channel],waveform2)
    daq.run(ao_task)
    daq.wait_to_finish(ao_task)
    daq.stop(ao_task)
    
@pytest.mark.parametrize("channel", ["ai0", "ai1"])
def test_pci6229_analog_in(get_pci6229, channel):
    daq = get_pci6229
    samp_rate = 1000.0
    samp_num = 100
    ai_task = daq.setup_AI(channel, samp_rate, samp_num)
    daq.run(ai_task)
    time.sleep(0.1) 
    data, nums = daq.read(ai_task)
    daq.stop(ai_task)
    assert len(data) == samp_num

def test_pci6229_ctrout(get_pci6229):
    """This test outputs a waveform on the specified counter output channel
    """
    daq = get_pci6229
    clk_task = daq.setup_clock('ctr1', 100)
    print('clktask: ', clk_task)
    time.sleep(0.1)
    daq.run(clk_task)
    daq.wait_to_finish(clk_task)
    daq.stop(clk_task)

def test_pci6229_ctr_read(capsys, get_pci6229):
    """This test reads finite samples from the specified counter channel using internal hardware timed clock
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

def test_pci6601_dio_read(capsys, get_pci6229):
    """This test reads digital inputs from the specified channel
    """
    daq = get_pci6229
    dio_task = daq.setup_dio_read('ctr0')
    time.sleep(0.1)
    daq.run(dio_task)
    data = daq.read(dio_task)
    daq.stop(dio_task)
    with capsys.disabled():
        print('diotask', dio_task)
        print(data)

@pytest.mark.parametrize("channel", ["do0", "do47"])
@pytest.mark.parametrize("voltage", [0, 1])
def test_pci6601_digital_output(capsys, get_pci6229, channel, voltage):
    """This test outputs a digital signal on the specified channel
    """
    daq = get_pci6229
    with capsys.disabled():
        print(f"PCI6229 DIO channel = {channel}, voltage = {voltage}")
        time.sleep(1.0)
    daq.set_digital_output(channel, voltage)
    daq.run()
    daq.stop() 
