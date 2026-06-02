# sequence.py
from __future__ import annotations
from typing import List, Dict
import numpy as np

"""
Sequence scheduler for waveform generation.

A Sequence holds:
  - A list of (start_index, Pulse) entries
  - A list of MarkerEvent entries

When you call `to_waveform()`, it:
  1. Allocates two arrays of length `self.length`:
       • `envelope` (float)
       • `markers`  (int, 0/1)
  2. Iterates over each scheduled pulse, asks it for its samples,
     and adds them into the envelope at the correct offset.
  3. Iterates over each marker event and ORs its bits into the marker array.
"""

from .pulses import Pulse, MarkerEvent

class Sequence:
    """
    Represents a timed sequence of analog pulses and digital markers.

    Attributes:
        length   (int): Total number of samples in the output waveform.
        pulses   (List[tuple[int, Pulse]]):
                   Each item is (start_index, Pulse instance).
        markers  (List[MarkerEvent]):
                   Digital marker events (0/1) over the same timeline.
    """

    def __init__(self, length: int):
        """
        Initialize an empty Sequence.

        Args:
            length: Number of samples in the final waveform.
        """
        self.length = length
        self.pulses: List[tuple[int, Pulse]] = []
        self.markers: List[MarkerEvent]   = []

    def add_pulse(self, start: int, pulse: Pulse) -> None:
        """
        Schedule a pulse to begin at a given sample index.

        Args:
            start: Sample index at which to begin the pulse (0-based).
            pulse: A Pulse subclass instance with its own `length`.
        """
        if start < 0 or start >= self.length:
            raise ValueError(f"start index {start} out of range [0, {self.length})")
        self.pulses.append((start, pulse))

    def add_marker(self, marker: MarkerEvent) -> None:
        """
        Add a digital marker event covering a window in the sequence.

        Args:
            marker: A MarkerEvent instance, which knows its own on/off indices.
        """
        if marker.length != self.length:
            raise ValueError("MarkerEvent length must match Sequence length")
        self.markers.append(marker)

    def to_waveform(self) -> Dict[int, Dict[str, np.ndarray]]:
        """
        Render waveforms and markers **per channel**.


        Returns:
            Dict mapping channel -> {'envelope': np.ndarray, 'markers': np.ndarray}
        """
        # 1) Determine all channels used in pulses or markers
        channels = set()
        for start, pulse in self.pulses:
            ch = int(pulse.name.split("_")[-1])
            channels.add(ch)
        for mk in self.markers:
            channels.add(int(mk.name.split("_")[-1]))

        # 2) Prepare per-channel outputs
        output: Dict[int, Dict[str, np.ndarray]] = {}

        for ch in channels:
            # Allocate arrays of length equal to the sequence's total length
            envelope = np.zeros(self.length, dtype=float)
            markers = np.zeros(self.length, dtype=np.uint64)

            # Place pulses for this channel
            for start, pulse in self.pulses:
                if int(pulse.name.split("_")[-1]) != ch:
                    continue
                end = min(start + pulse.length, self.length)
                num = end - start
                envelope[start:end] += pulse.generate_samples()[:num]

            # Place markers for this channel
            for mk in self.markers:
                if (int(mk.name.split("_")[-1])) != ch:
                    continue

                mk_markers = mk.generate_markers()

                # Check first pulse
                on_indices = np.where(mk_markers != 0)[0]
                if len(on_indices) > 0:
                    # Check duration
                    first_pulse_end = on_indices[0]
                    while first_pulse_end < len(mk_markers) and mk_markers[first_pulse_end] != 0:
                        first_pulse_end += 1

                markers |= mk_markers

            # Store per-channel waveform
            output[ch] = {"envelope": envelope, "markers": markers}

        return output

    def clear(self) -> None:
        """
        Remove all scheduled pulses and markers, resetting the Sequence.
        """
        self.pulses.clear()
        self.markers.clear()

    def plot(self, *, show_markers: bool = True, ax=None):
        """
        Quick‐and‐dirty plot of the sequence:
          - Red line: analog envelope
          - Green step: digital markers (if requested)
        Returns the (fig, ax) tuple so we can customize or save it.
        """
        wave = self.to_waveform()
        env = wave['envelope']
        mks = wave['markers']

        if ax is None:
            fig, ax = plt.subplots(figsize=(6, 3))
        else:
            fig = ax.get_figure()

        x = range(self.length)
        ax.plot(x, env, label='Envelope')
        if show_markers:
            # scale marker to 10% of max envelope
            scale = max(env) * 0.1 if env.any() else 1.0
            ax.step(x, mks * scale, where='post', label='Markers', linestyle='--')
        ax.set_xlabel('Sample Index')
        ax.set_ylabel('Amplitude')
        ax.legend(loc='best')
        ax.set_title(repr(self))

        return fig, ax
    def __repr__(self) -> str:
        return (f"<Sequence length={self.length}  "
                f"pulses={len(self.pulses)}  markers={len(self.markers)}>")

# Example usage (would go in an examples/ file, not here):
# seq = Sequence(length=500)
# seq.add_pulse(100, GaussianPulse("g1", 50, sigma=10))
# seq.add_marker(MarkerEvent("m1", 500, 100, 150))
# wave = seq.to_waveform()

