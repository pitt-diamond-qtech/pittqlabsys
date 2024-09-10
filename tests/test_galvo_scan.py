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
from src.Controller.ni_daq import PXI6733,NI6281,PCI6229,PCI6601
from src.core import Experiment
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

@pytest.fixture
def get_pci6229() -> PCI6229:
    # create a fixture for the PCI6229
    return PCI6229()

@pytest.fixture
def get_pci6601() -> PCI6601:
    # create a fixture for the PCI6601
    return PCI6601()

def test_galvo_scan(capsys,get_pxi6733,get_ni6281):
    """Test passed success to generate a confocal image
    --- GD 20230817
    ----- UPDATE GD 08/31/2023
    To get Experiment load and append to work, I had to modify galvo scan class
    which has now broken this test. If I modify it again, I will break the Experiment
    load and append test function given below.
    -------- FINAL APPROACH-----------
    If testing the Galvo scan class separately, you must give it the instruments in the
    form {'dev_1": {'instance':instance_of_dev_1},'dev_2": {'instance':instance_of_dev_2}} etc.
    --- TEST PASSED for both this function and Load and append test function below
    --- GD 08/31/2023
    """
    daq = get_pxi6733
    daq2 = get_ni6281
    instr = {"daq": {'instance':daq},"daq2":{'instance':daq2}}
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


def test_load_append_galvo_scan(capsys,get_pxi6733,get_ni6281):
    """Wrote this test to verify if Experiment load and append works
    with Galvo scan. Test PASSED !
    --- GD 08/30/2023
    -- UPDATE GD 08/31/2023
    Because we have made the GalvoScan class work with Load and Append,
    we now seem to have an issue with the actual execution of the setup_scan
    function.
    """
    daq = get_pxi6733
    daq2 = get_ni6281
    instr = {"daq": daq, "daq2": daq2}
    ew, failed, instr = Experiment.load_and_append({'Galvo': 'GalvoScan'})
    assert failed == {}
    with capsys.disabled():
        print(failed)
        print(ew)


def test_galvo_scan_NI6281(capsys,get_pxi6733,get_ni6281):
    """Test passed success to generate a confocal image with
    NI6281 as the primary board, and connections

    --- GD 08/31/2023
    """
    daq = get_ni6281
    daq2 = get_pxi6733
    instr = {"daq": {'instance':daq},"daq2":{'instance':daq2}}
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


def test_galvo_scan_PCI6229(capsys, get_pci6229, get_pci6601):
    """Test generates a successful confocal image using an internal
    hardware timed clock and external hardware timed clock
    Test passed for PCI6229 8/27/2204, Abby Bakkenist
    Test passed with PCI6601 9/9/2024, Abby Bakkenist
    """   
    daq = get_pci6229
    daq2 = get_pci6601
    instr = {"daq": {'instance':daq}, "daq2":{'instance':daq2}}
    fig, ax = plt.subplots(2, 1)

    with capsys.disabled():
        expt = GalvoScan( name='galvo_scan',devices=instr)
        expt.settings['plot_style'] = "main"
        expt.run()
        # print(expt.data)
        dat = expt.data['image_data']
        print("The average counting rate is {} kcts/sec".format(np.mean(dat)))
        expt.plot(figure_list=[fig])
        plt.show()
