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

from src.Controller.ni_daq import NIDAQ,PXI6733
import pytest
import matplotlib.pyplot as plt
import time
import numpy as np

#@pytest.mark.run_this
def test_nidaq(capsys):
    daq = NIDAQ()
    dev_list = daq.get_connected_devices()
    for d in dev_list:
        with capsys.disabled():
            print(d)

def test_pxi6733_connection():
    daq = PXI6733()
    assert daq.is_connected

@pytest.mark.run_this
def test_pxi6733_ctrout():
    daq = PXI6733()
    clk_task = daq.setup_clock('ctr0', 1000)
    print('clktask: ', clk_task)
    time.sleep(0.1)
    daq.run(clk_task)
    daq.wait_to_finish(clk_task)
    daq.stop(clk_task)

@pytest.mark.parametrize("ext_clock",[True,False])
def test_pxi6733_ctr_read(capsys,ext_clock):
    daq = PXI6733()
    ctr_task = daq.setup_counter('ctr0', 50, use_external_clock=ext_clock)
    samp_rate = daq.tasklist[ctr_task]['sample_rate']
    avg_counts_per_bin = np.diff(data).mean()
    time.sleep(0.1)
    daq.run(ctr_task)
    time.sleep(0.1)
    # daq.wait_to_finish(ctr_task)
    data, nums = daq.read(ctr_task)
    daq.stop(ctr_task)


    with capsys.disabled():
        print('ctrtask: ', ctr_task)
        print(data)
        print('the sampling rate was {}'.format(samp_rate))
        print("The avg counts per bin was {}".format(avg_counts_per_bin))
        print("The counting rate is {} cts/sec".format(avg_counts_per_bin * samp_rate))



