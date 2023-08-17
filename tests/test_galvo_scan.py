# Created by Gurudev Dutt <gdutt@pitt.edu> on 2023-08-17
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
from src.Controller.ni_daq import PXI6733,NI6281
from src.Model.experiments.galvo_scan import GalvoScan
import pytest
import matplotlib.pyplot as plt
import numpy as np


@pytest.fixture
def get_pxi6733() -> PXI6733:
    # create a fixture for the PXI6733
    return PXI6733()

@pytest.fixture
def get_ni6281() -> NI6281:
    # create a fixture for the PXI6733
    return NI6281()

def test_galvo_scan(capsys,get_pxi6733,get_ni6281):
    """Test passed success to generate a confocal image
    --- GD 20230817"""
    daq = get_pxi6733
    daq2 = get_ni6281
    instr = {"daq": daq,"daq2":daq2}
    fig, ax = plt.subplots(2, 1)

    with capsys.disabled():
        expt = GalvoScan( name='galvo_scan',devices=instr)
        expt.settings['plot_style'] = "main"
        expt.run()
        #print(expt.data)
        dat = expt.data['image_data']
        print("The average counting rate is {} kcts/sec".format(np.mean(dat)))
        expt.plot(figure_list=[fig])
        plt.show()
