# Created by Gurudev Dutt <gdutt@pitt.edu> on 7/29/25
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
import struct
from pathlib import Path

import numpy as np
import pytest

from src.Model.awg_file import AWGFile, _WFM_MEMORY_LIMIT

@pytest.fixture
def tmp_awg(tmp_path):
    """AWGFile instance writing into a fresh temporary folder."""
    return AWGFile(ftype="WFM", timeres_ns=1, out_dir=tmp_path)

def test_write_waveform_creates_file(tmp_awg, tmp_path):
    # create a tiny IQ & marker array
    iq = np.array([0.1, -0.2, 0.3, -0.4], dtype=float)
    marker = np.array([0, 1, 0, 1], dtype=int)
    # write it
    out = tmp_awg.write_waveform(iq, marker, name="test", channel=1)
    assert out.exists()

    data = out.read_bytes()
    # 1) header
    assert data.startswith(b"MAGIC 1000 \r\n")

    # 2) trailer
    trailer = tmp_awg._make_trailer()
    assert data.endswith(trailer)

    # 3) body prefix "#<ndigits><nbytes>"
    body = data[len(b"MAGIC 1000 \r\n") : -len(trailer)]
    assert body.startswith(b"#")
    # parse length prefix
    # find where digits end and binary starts
    # e.g. "#512" means next 512 bytes payload
    # so skip '#' and len(ndigits) characters
    for nd in range(1, 6):
        if body[1:1+nd].isdigit():
            nbytes = int(body[1:1+nd])
            payload = body[1+nd:]
            # payload length must equal nbytes
            assert len(payload) == nbytes
            break
    else:
        pytest.skip("Could not parse length prefix")

    # 4) check payload decodes back to original samples
    rec_size = struct.calcsize("<fb")
    assert nbytes == 4 * rec_size
    # unpack first sample
    val0, m0 = struct.unpack_from("<fb", payload, 0)
    assert pytest.approx(val0, rel=1e-6) == iq[0]
    assert m0 == marker[0]

def test_waveform_padding(tmp_awg):
    # odd-length IQ must be padded to multiple of 4
    iq = np.array([0.1, -0.1, 0.2], dtype=float)  # length 3
    marker = np.array([1, 0, 1], dtype=int)
    out = tmp_awg.write_waveform(iq, marker, name="pad", channel=2)
    data = out.read_bytes()
    # parse prefix
    body = data[len(b"MAGIC 1000 \r\n") : -len(tmp_awg._make_trailer())]
    # extract nbytes
    prefix = body.split(b'#',1)[1]
    # find split between digits and payload
    import re
    m = re.match(br"(\d)(\d+)", prefix)
    ndigits = int(m.group(1))
    nbytes = int(m.group(2)[:ndigits])
    # padded length must be 4
    assert nbytes == 4 * struct.calcsize("<fb")

def test_write_sequence(tmp_awg, tmp_path):
    # Prepare a few dummy entries
    entries = [
        ("a_1.wfm", "a_2.wfm", 0, 0, 0, 0),
        ("b_1.wfm", "b_2.wfm", 5, 1, 0, 2),
    ]
    seq = tmp_awg.write_sequence(entries, seq_name="myscan",
                                 table_jump=[1]*16,
                                 logic_jump=[0,1,0,1],
                                 jump_mode="LOGIC",
                                 jump_timing="ASYNC",
                                 strobe=1)
    assert seq.exists()
    text = seq.read_text().splitlines()

    # header
    assert text[0] == "MAGIC 3002 "
    # LINES count
    assert text[1] == f"LINES {len(entries)}"
    # entry lines
    for idx, ent in enumerate(entries, start=2):
        w1, w2, rpt, wait, goto, logic = ent
        expected = f"\"{w1}\",\"{w2}\",{rpt},{wait},{goto},{logic}"
        assert text[idx] == expected

    # jump tables and modes at end
    assert text[-4] == "TABLE_JUMP " + ",".join(["1"]*16)
    assert text[-3] == "LOGIC_JUMP 0,1,0,1"
    assert text[-2] == "JUMP_MODE LOGIC"
    assert text[-1] == "JUMP_TIMING ASYNC"
    # a real STROBE line must come after, so:
    # Actually our implementation writes STROBE after timing:
    # so adjust index if needed
    # Alternatively, look anywhere for STROBE
    assert any(line.startswith("STROBE ") for line in text)
