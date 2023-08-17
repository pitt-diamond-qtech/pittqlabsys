# Created by Gurudev Dutt <gdutt@pitt.edu> on 2023-08-03
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

from src.Controller.ni_daq import NIDAQ, PXI6733,NI6281
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
def get_pxi6733() -> PXI6733:
    # create a fixture for the PXI6733
    return PXI6733()

@pytest.fixture
def get_ni6281() -> NI6281:
    # create a fixture for the PXI6733
    return NI6281()
def test_nidaq(capsys,get_nidaq):
    """simple test will return all the devices in the system
    -- GD 08/03/2023
    """
    daq = get_nidaq
    dev_list = daq.get_connected_devices()
    for d in dev_list:
        with capsys.disabled():
            print(d)




def test_pxi6733_connection(get_pxi6733):
    """This test checks if pxi6733 is connected"""
    assert get_pxi6733.is_connected

@pytest.mark.run_this
def test_pxi6733_ctrout(get_pxi6733):
    """This test has passed successfully. It outputs a waveform on the ctr0 output
    - GD 08/15/2023"""
    daq = get_pxi6733
    clk_task = daq.setup_clock('ctr0', 1000)
    print('clktask: ', clk_task)
    time.sleep(0.1)
    daq.run(clk_task)
    daq.wait_to_finish(clk_task)
    daq.stop(clk_task)

@pytest.mark.parametrize("ext_clock", [True, False])
def test_pxi6733_ctr_read(capsys, get_pxi6733,ext_clock):
    """This test has passed successfully . It reads finite samples from ctr0 using either internal hardware timed clock
    or external hardware timed clock
    - GD 08/15/2023"""
    daq = get_pxi6733
    ctr_task = daq.setup_counter('ctr0', 50, use_external_clock=ext_clock)
    samp_rate = daq.tasklist[ctr_task]['sample_rate']
    time.sleep(0.1)
    daq.run(ctr_task)
    time.sleep(0.1)
    data, nums = daq.read(ctr_task)
    daq.stop(ctr_task)
    avg_counts_per_bin = np.diff(data).mean()
    # daq.wait_to_finish(ctr_task)


    with capsys.disabled():
        print('ctrtask: ', ctr_task)
        print(data)
        print('the sampling rate was {}'.format(samp_rate))
        print("The avg counts per bin was {}".format(avg_counts_per_bin))
        print("The counting rate is {} cts/sec".format(avg_counts_per_bin * samp_rate))

@pytest.mark.parametrize("channel",["ao0","ao1"])
def test_pxi6733_analog_out(get_pxi6733,channel):
    """This test has passed successfully for both AO0 and Ao1. it outputs AO voltages on a single channel
    - GD 08/15/2023"""
    daq = get_pxi6733
    samp_rate = 20000.0

    period = 1e-3
    t_end = period

    num_samples = math.ceil(t_end * samp_rate / 2.) * 2  # for AO, it appears only even sample numbers allowed
    t_array = np.linspace(0, t_end, num_samples)
    waveform = np.sin(2 * np.pi * t_array / period)
    waveform2 = signal.sawtooth(2 * np.pi * t_array / period, 0.5) + 1
    ao_task = daq.setup_AO([channel],waveform2)
    daq.run(ao_task)
    daq.wait_to_finish(ao_task)
    daq.stop(ao_task)

@pytest.mark.parametrize("channel",["ao0","ao1"])
def test_pxi6733_analog_out_single_val(get_pxi6733,channel):
    """This test has passed successfully for both AO0 and Ao1. it outputs AO voltages on a single channel
    - GD 08/15/2023"""
    daq = get_pxi6733
    samp_rate = 20000.0

    period = 1e-3
    t_end = period

    num_samples = 2  # for AO, it appears only even sample numbers allowed
    waveform = [-0.5,-0.5]
    ao_task = daq.setup_AO([channel],waveform)
    daq.run(ao_task)
    daq.wait_to_finish(ao_task)
    daq.stop(ao_task)
def test_pxi6733_multi_analog_out(get_pxi6733):
    """This test has passed successfully. it successively outputs the same waveform on ao0 and ao1
    I would like to rewrite it also to pass with a 2-D waveform, but that will be done later.
    - GD 08/15/2023
        """
    daq = get_pxi6733
    samp_rate = 20000.0

    period = 1e-3
    t_end = period

    num_samples = math.ceil(t_end * samp_rate / 2.) * 2  # for AO, it appears only even sample numbers allowed
    t_array = np.linspace(0, t_end, num_samples)
    waveform = np.sin(2 * np.pi * t_array / period)
    waveform2 = signal.sawtooth(2 * np.pi * t_array / period, 0.5) + 1
    ao_task = daq.setup_AO(["ao0","ao1"],waveform2)
    daq.run(ao_task)
    daq.wait_to_finish(ao_task)
    daq.stop(ao_task)

@pytest.mark.parametrize("ext_clock",[True, False])
@pytest.mark.parametrize("channel",["ao0","ao1"])
def test_pxi6733_ao_ctr_read(capsys, get_pxi6733,ext_clock,channel):
    """This test has passed successfully. equivalent to a 1d AO scan with counter reading
    However, note the bug below that prevents the wait to finish function from executing correctly
    TODO: fix the error that prevents us from waiting to finish either ctr or ao task here.
    - GD 08/15/2023
    """
    daq = get_pxi6733

    samp_rate = 20000
    # we need to set the sample rate correctly otherwise it uses the default sample rate for the clock
    # this will result in an error in the number of counts/sec reported.
    daq.settings["digital_input"]["ctr0"]["sample_rate"] = samp_rate
    daq.settings["digital_input"]["ctr1"]["sample_rate"] = samp_rate
    period = 1e-3
    t_end = period

    num_samples = math.ceil(t_end * samp_rate / 2.) * 2  # for AO, it appears only even sample numbers allowed
    t_array = np.linspace(0, t_end, num_samples)
    waveform = np.sin(2 * np.pi * t_array / period)
    waveform2 = signal.sawtooth(2 * np.pi * t_array / period, 0.5) + 1
    ctr_task = daq.setup_counter('ctr0', num_samples, use_external_clock=ext_clock)
    daq.tasklist[ctr_task]['sample_rate'] =samp_rate
    ao_task = daq.setup_AO([channel],waveform2,clk_source=ctr_task)

    time.sleep(0.1)
    daq.run(ao_task)
    daq.run(ctr_task)
    time.sleep(0.1)
    # I am a little puzzled why the test hangs if we wait to finish, it reports the timeout was exceeded
    # skipping this litte bug for now.
    # TODO: fix the bug that prevents us from waiting to finish the task in this code alone.
    #daq.wait_to_finish(ao_task)
    #daq.wait_to_finish(ctr_task)
    data, nums = daq.read(ctr_task)
    daq.stop(ao_task)
    daq.stop(ctr_task)
    avg_counts_per_bin = np.diff(data).mean()
    # daq.wait_to_finish(ctr_task)


    with capsys.disabled():
        print('ctrtask: ', ctr_task)
        print(data)
        print('the sampling rate was {}'.format(samp_rate))
        print("The avg counts per bin was {}".format(avg_counts_per_bin))
        print("The counting rate is {} cts/sec".format(avg_counts_per_bin * samp_rate))

@pytest.mark.parametrize("ext_clock", [True, False])
def test_pxi6733_multi_ao_ctr_read(capsys, get_pxi6733,ext_clock):
    """This test fails because I have only prepared 1d data in the waveform2, need to rewrite for 2d data
    DO NOT RUN THIS AS IT WILL CRASH THE PXI CHASSIS AND YOU WILL HAVE TO RESTART !
    - GD 08/15/2023
    """
    daq = get_pxi6733

    samp_rate = 20000
    # we need to set the sample rate correctly otherwise it uses the default sample rate for the clock
    # this will result in an error in the number of counts/sec reported.
    daq.settings["digital_input"]["ctr0"]["sample_rate"] = samp_rate
    daq.settings["digital_input"]["ctr1"]["sample_rate"] = samp_rate

    period = 1e-3
    t_end = period

    num_samples = math.ceil(t_end * samp_rate / 2.) * 2  # for AO, it appears only even sample numbers allowed
    t_array = np.linspace(0, t_end, num_samples)
    waveform = np.sin(2 * np.pi * t_array / period)
    waveform2 = signal.sawtooth(2 * np.pi * t_array / period, 0.5) + 1
    ctr_task = daq.setup_counter('ctr0', num_samples, use_external_clock=ext_clock)
    ao_task = daq.setup_AO(["ao0","ao1"],waveform2,clk_source=ctr_task)

    time.sleep(0.1)
    daq.run(ao_task)
    daq.run(ctr_task)
    time.sleep(0.1)
    daq.wait_to_finish(ao_task)
    data, nums = daq.read(ctr_task)
    daq.stop(ao_task)
    daq.stop(ctr_task)
    avg_counts_per_bin = np.diff(data).mean()
    # daq.wait_to_finish(ctr_task)


    with capsys.disabled():
        print('ctrtask: ', ctr_task)
        print(data)
        print('the sampling rate was {}'.format(samp_rate))
        print("The avg counts per bin was {}".format(avg_counts_per_bin))
        print("The counting rate is {} cts/sec".format(avg_counts_per_bin * samp_rate))


@pytest.mark.parametrize("channel",["ao0","ao1"])
def test_pxi6733_ni6281_analog_out_read_analog_in(capsys,get_pxi6733,get_ni6281,channel):
    """This test outputs Ao0 voltage, and reads in on Ai0 voltage. sync is carried out through the ctr0 of NI6281.
    Test does not work yet, DO NOT RUN !
    - GD 08/15/2023
    """
    daq = get_pxi6733
    daq2 = get_ni6281
    samp_rate = 20000.0

    period = 1e-3
    t_end = period

    num_samples = math.ceil(t_end * samp_rate / 2.) * 2  # for AO, it appears only even sample numbers allowed
    t_array = np.linspace(0, t_end, num_samples)
    waveform = np.sin(2 * np.pi * t_array / period)
    waveform2 = signal.sawtooth(2 * np.pi * t_array / period, 0.5) + 1

    ctr_task = daq2.setup_counter('ctr0', num_samples)

    ao_task = daq.setup_AO([channel],waveform2)
    daq.run(ao_task)
    daq.wait_to_finish(ao_task)
    daq.stop(ao_task)