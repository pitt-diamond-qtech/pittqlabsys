# Created by Gurudev Dutt <gdutt@pitt.edu> on 7/28/25
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
import pytest
from src.Model.sequence import Sequence
from src.Model.pulses import GaussianPulse, MarkerEvent
from matplotlib.figure import Figure

@pytest.fixture
def simple_seq():
    seq = Sequence(200)
    seq.add_pulse(50, GaussianPulse("g", 20, sigma=5, amplitude=1.0))
    seq.add_marker(MarkerEvent("m", 200, 50, 70))
    return seq

def test_sequence_plot_returns_fig_ax(simple_seq, matplotlib):
    fig, ax = simple_seq.plot()
    assert isinstance(fig, Figure)

    # Two curves: envelope + scaled markers
    lines = ax.get_lines()
    assert len(lines) == 2

    assert ax.get_xlabel() == "Sample Index"
    assert ax.get_ylabel() == "Amplitude"
    assert "Sequence" in ax.get_title()
