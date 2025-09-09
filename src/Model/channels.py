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
from __future__ import annotations
from .sequence import Sequence
from .pulses import GaussianPulse, MarkerEvent
from .data_processing.utils import (
    generate_comp_sequences,
    random_pauli_list,
    find_R_and_final_state,
)
from typing import List, Tuple

class Channel:
    """
        Lightweight façade around Sequence that fixes a `channel_id` or
        delay offset if you really want to group pulses per hardware channel.
        """
    def __init__(self, name: str, seq: Sequence, offset: int = 0):
        self.name = name
        self.seq = seq
        self.offset = offset

    def add_pulse(self, start, pulse):
        self.seq.add_pulse(self.offset + start, pulse)

    def plot(self, **kwargs):
        # reuse Sequence.plot but add annotation
        fig, ax = self.seq.plot(**kwargs)
        ax.set_title(f"{self.name}: " + ax.get_title())
        return fig, ax


class RandomGateSequence:
    """
    Build a randomized RB sequence of analog pulses + a final marker.
    """

    def __init__(
        self,
        total_length: int,
        base_width: float,
        separation: float = 0.0,
        num_comp_seqs: int = 4,
        trunc_lengths: List[int] = [2,4,8,16],
        change_width: bool = False,
        change_amp:   bool = False,
    ):
        self.total_length     = total_length
        self.base_width       = base_width
        self.sep              = separation
        self.num_comp_seqs    = num_comp_seqs
        self.trunc_lengths    = trunc_lengths
        self.change_width     = change_width
        self.change_amp       = change_amp

    def _choose_comp_sequence(self, events_in_train: int) -> List[str]:
        all_seqs = generate_comp_sequences(self.num_comp_seqs, max(self.trunc_lengths))
        # pick the user’s comp_seq_num-th (or random)
        raw = all_seqs[0]  # for simplicity, just take index 0
        # truncate to closest length
        length = min(self.trunc_lengths, key=lambda L: abs(L - events_in_train))
        return raw[:length]

    def build(self, events_in_train: int, start_time: float) -> Tuple[Sequence, str]:
        """
        Returns:
          - A Sequence object with all the scheduled Gaussian pulses
          - The final state label ('z0' or 'z1')
        """
        seq = Sequence(length=self.total_length)
        # 1. get Pauli list
        P_list = random_pauli_list(events_in_train)
        # 2. get a comp list, truncated
        G_list = self._choose_comp_sequence(events_in_train)
        # 3. interleave: [P0, G0, P1, G1, ..., Pn-1, Gn-1, Pn, R, Pn+1]
        full = []
        for i in range(len(G_list)):
            full.append(P_list[i])
            full.append(G_list[i])
        full.extend(P_list[-2:])  # tail
        # 4. find R gate
        R, final = find_R_and_final_state(G_list)
        full.insert(len(G_list)*2, R)

        # 5. schedule into Sequence
        t = start_time
        for gate_label in full:
            # Map gate_label → amplitude/width/phase
            amp = 1.0
            width = self.base_width * (2 if self.change_width and 'pi' in gate_label else 1)
            # choose pulse shape (here we use Gaussian for everything)
            pulse = GaussianPulse(
                name=gate_label,
                length=int(width)
            )
            seq.add_pulse(start=int(t), pulse=pulse)
            # optionally add a marker during that pulse
            mk = MarkerEvent(
                name=gate_label+"_m",
                length=self.total_length,
                on_index=int(t),
                off_index=int(t+width)
            )
            seq.add_marker(mk)
            # advance time
            t += width + self.sep

        return seq, final
