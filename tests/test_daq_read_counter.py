# Created by Gurudev Dutt <gdutt@pitt.edu> on 2023-08-16
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

from src.Model.experiments.daq_read_counter import Pxi6733readcounter
from src.Controller.ni_daq import PXI6733
import pytest
import matplotlib.pyplot as plt


@pytest.fixture
def get_pxi6733() -> PXI6733:
    # create a fixture for the PXI6733
    return PXI6733()


def test_read_counter(capsys, get_pxi6733):
    daq = get_pxi6733
    instr = {"daq":daq}
    expt = Pxi6733readcounter(instr, name='daq_read_ctr')
    fig, ax = plt.subplots(2, 1)
    expt.settings['plot_style'] = "2D"
    with capsys.disabled():
        expt.run()
        expt.plot(figure_list=[fig])
        plt.show()

