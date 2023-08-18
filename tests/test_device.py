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

from src.Controller.example_device import Plant,PIController,ExampleDevice
from src.core import Device
import pytest
import numpy as np
import time

@pytest.fixture
def get_example_device() -> ExampleDevice:
    return ExampleDevice()

@pytest.fixture
def get_plant() -> Plant:
    return Plant()

@pytest.fixture
def get_pi_controller() -> PIController:
    return PIController()

def test_example_device(capsys,get_example_device):
    """ This test has passed successfully
        -- GD 20230818
    """
    dev = get_example_device
    with capsys.disabled():
        print("Example device has settings ",dev.settings)

def test_plant(capsys,get_plant):
    """ This test has passed successfully
    -- GD 20230818
    """
    dev = get_plant
    with capsys.disabled():
        print((dev.settings))
        for i in range(15):
            time.sleep(0.1)
            print((dev.read_probes('output')))
        dev.save_aqs("C:\\Users\\l00055843\\Experiments\\AQuISS_default_save_location\\aqs_tmp\\plant.aqs")
        print('done')
        dev.run()


def test_device_load_and_append(capsys):
    """
    This test has passed successfully. Note that device load_and_ppend requires a dictionary of form
    {'dev_name': dev_class_name} and NOT {'dev_name':dev_class_instance}.

    This is similar to the Experiment.load_and_append which also requires
    {'expt_name':expt_class_name}.
    -- GD 20230818
    """
    dev,failed = Device.load_and_append({"PID":PIController})
    with capsys.disabled():
        print(failed)
        print(dev)
    assert failed == {}