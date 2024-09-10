from src.Controller.ni_daq import NIDAQ, PCI6601
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
def get_pci6601() -> PCI6601:
    # create a fixture for the PCI6601
   return PCI6601()

def test_pci6601_connection(get_pci6601):
    """This test checks if pci6601 is connected, Assertion Error if not
    passed 7/16/2024, Abby Bakkenist
    """
    assert get_pci6601.is_connected

def test_pci6601_ctrout(get_pci6601):
    """This test successfully outputs a waveform on the specified counter output channel
    passed 7/22/2024, Abby Bakkenist
    """
    daq = get_pci6601
    clk_task = daq.setup_clock('ctr1', 100)
    print('clktask: ', clk_task)
    time.sleep(0.1)
    daq.run(clk_task)
    daq.wait_to_finish(clk_task)
    daq.stop(clk_task)

def test_pci6601_ctr_read(capsys, get_pci6601):
    """This test successfully reads finite samples from the specified counter channel using external hardware timed clock
    passed 7/22/2024, Abby Bakkenist
    """
    daq = get_pci6601
    ctr_task = daq.setup_counter('ctr1', 50, use_external_clock=True)
    samp_rate = daq.tasklist[ctr_task]['sample_rate']
    time.sleep(0.1)
    daq.run(ctr_task)
    time.sleep(0.1)
    data, nums = daq.read(ctr_task)
    avg_counts_per_bin = np.diff(data).mean()
    daq.stop(ctr_task)
    with capsys.disabled():
        print('ctrtask: ', ctr_task)
        print(data)
        print('The sampling rate was {}'.format(samp_rate))
        print("The avg counts per bin was {}".format(avg_counts_per_bin))
        print("The counting rate is {} cts/sec".format(avg_counts_per_bin * samp_rate))
