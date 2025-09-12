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
# tests/test_sequence.py

import numpy as np
import pytest

# Adjust these imports to match your project structure:
from src.Model.sequence import Sequence
from src.Model.pulses import DataPulse, GaussianPulse, MarkerEvent

@pytest.fixture
def simple_sequence():
    """A Sequence with one Gaussian pulse and one marker."""
    seq_len = 500
    seq = Sequence(length=seq_len)
    gauss = GaussianPulse(name="g1", length=50, sigma=10, amplitude=1.0)
    seq.add_pulse(start=100, pulse=gauss)

    mk = MarkerEvent(name="m1", length=seq_len, on_index=100, off_index=150)
    seq.add_marker(mk)
    return seq

def test_to_waveform_length_and_types(simple_sequence):
    """Envelope and marker arrays have correct shapes and dtypes."""
    wave = simple_sequence.to_waveform()
    env = wave["envelope"]
    mks = wave["markers"]

    assert env.shape == (simple_sequence.length,)
    assert mks.shape == (simple_sequence.length,)

    assert env.dtype.kind == 'f'
    assert mks.dtype.kind == 'i'

    # Envelope zeros outside pulse window
    assert np.all(env[:100] == 0.0)
    assert np.all(env[150:] == 0.0)

    # Markers only 0 or 1, and high during [100:150)
    assert set(np.unique(mks)) <= {0, 1}
    assert np.all(mks[:100] == 0)
    assert np.all(mks[100:150] == 1)
    assert np.all(mks[150:] == 0)

def test_clear_resets_sequence(simple_sequence):
    """clear() removes pulses and markers and produces all-zero output."""
    seq = simple_sequence
    assert seq.pulses and seq.markers

    seq.clear()
    assert not seq.pulses
    assert not seq.markers

    wave = seq.to_waveform()
    assert np.all(wave["envelope"] == 0.0)
    assert np.all(wave["markers"] == 0)

def test_data_pulse_resampling(tmp_path):
    """DataPulse loads a CSV and resamples to its declared length."""
    # Create a small CSV: time vs amplitude
    data = np.array([[0.0, 0.0],
                     [0.5, 1.0],
                     [1.0, 0.0]])
    csv = tmp_path / "data.csv"
    np.savetxt(csv, data, delimiter=",")

    dp = DataPulse(name="d1", length=10, filename=str(csv))
    samples = dp.generate_samples()

    assert isinstance(samples, np.ndarray)
    assert samples.shape == (10,)
    # Peak should be near the center
    peak_idx = np.argmax(samples)
    assert peak_idx in (4, 5)
    
def test_sequence_plot_returns_fig_ax(simple_seq, matplotlib):
    # matplotlib fixture silences interactive window
    fig, ax = simple_seq.plot()
    # It should be a matplotlib Figure
    from matplotlib.figure import Figure
    assert isinstance(fig, Figure)
    # And the Axes should contain exactly two artists: one Line2D and one Step (also Line2D)
    lines = ax.get_lines()
    # Envelope + markers → 2 lines
    assert len(lines) == 2

    # Check labels
    assert ax.get_xlabel() == "Sample Index"
    assert ax.get_ylabel() == "Amplitude"
    # Title contains the repr of the sequence
    assert "Sequence" in ax.get_title()

@pytest.mark.skipif(
    not hasattr(Sequence, "create_sequence") or not hasattr(SequenceList, "create_sequence_list"),
    reason="SequenceList not implemented"
)
def test_sequence_list_generation(tmp_path):
    """
    If you’ve ported SequenceList, this test checks you get a non-empty list.
    """
    seq_str = "RandBench,1e-6,1.125e-6,Gauss,width++"
    params = {
        'amplitude': 500.0,
        'pulsewidth': 10e-9,
        'SB freq': 0,
        'IQ scale factor': 1.0,
        'phase': 0.0,
        'skew phase': 0.0,
        'num pulses': 1
    }
    scan = {'type': 'random scan', 'start': 1, 'stepsize': 50, 'steps': 2}

    sl = SequenceList(seq_str,
                      pulseparams=params,
                      timeres=1,
                      scanparams=scan,
                      compseqnum=1,
                      paulirandnum=2)

    # should not fail
    sl.create_sequence_list()
    # should produce at least one sequence
    assert isinstance(sl.sequencelist, list)
    assert len(sl.sequencelist) >= 1

    # each entry should itself be a Sequence
    for s in sl.sequencelist:
        assert hasattr(s, "to_waveform")
        wf = s.to_waveform()
        assert "envelope" in wf and "markers" in wf
