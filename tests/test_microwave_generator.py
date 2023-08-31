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


from src.Controller.microwave_generator import MicrowaveGenerator,RFGenerator
import pytest


@pytest.fixture
def get_mw_gen() -> MicrowaveGenerator:
    return MicrowaveGenerator()

def test_mw_gen(capsys,get_mw_gen):
    """
    This test is passing, it reads the frequency of the SRS signal generator,
    but it returns a weird Windows fatal exception error from pyvisa

    Windows fatal exception: access violation

    Current thread 0x00000ed4 (most recent call first): .....rest of Traceback omitted....

    The weird part is that when I instantiate the microwave generator class directly from its
    definition file, everything works with no error. i.e. running the definition file works perfectly.
    the error only occurs here during the creation of the fixture. I have tried also creating the instance inside
    the test function instead of using the fixture, and the same error results
    -- GD 08/28/2023
    """
    mwgen = get_mw_gen
    assert mwgen.is_connected
    with capsys.disabled():
        print("Frequency is {} Hz".format(mwgen.read_probes('frequency')))
