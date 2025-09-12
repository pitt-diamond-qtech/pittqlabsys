# pulse.py
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
from typing import List, Dict
import numpy as np
from abc import ABC, abstractmethod

class Pulse(ABC):
    """
    Abstract base class for hardware-agnostic waveform pulses.
    Subclasses implement `generate_samples()` to return a float array of envelope values.
    """
    def __init__(self, name: str, length: int, fixed_timing: bool = False):
        """
        :param name: Identifier for this pulse
        :param length: Number of samples in the pulse envelope
        :param fixed_timing: If True, this pulse's timing should not be adjusted during scans
        """
        self.name = name
        self.length = length
        self.fixed_timing = fixed_timing

    @abstractmethod
    def generate_samples(self) -> np.ndarray:
        """
        Generate the normalized envelope of the pulse as a 1D float array of length `self.length`.
        """
        pass


class GaussianPulse(Pulse):
    """
    Gaussian-shaped pulse envelope.
    """
    def __init__(self, name: str, length: int, sigma: float, amplitude: float = 1.0, fixed_timing: bool = False):
        super().__init__(name, length, fixed_timing)
        self.sigma = sigma
        self.amplitude = amplitude
        # Center the Gaussian at the midpoint
        self.center = (length - 1) / 2.0

    def generate_samples(self) -> np.ndarray:
        t = np.arange(self.length)
        envelope = self.amplitude * np.exp(-((t - self.center)**2) / (2 * self.sigma**2))
        return envelope.astype(float)


class SechPulse(Pulse):
    """
    Hyperbolic secant-shaped pulse envelope.
    """
    def __init__(self, name: str, length: int, width: float, amplitude: float = 1.0, fixed_timing: bool = False):
        super().__init__(name, length, fixed_timing)
        self.width = width
        self.amplitude = amplitude
        self.center = (length - 1) / 2.0

    def generate_samples(self) -> np.ndarray:
        t = np.arange(self.length) - self.center
        envelope = self.amplitude * (1.0 / np.cosh(t / self.width))
        return envelope.astype(float)


class LorentzianPulse(Pulse):
    """
    Lorentzian-shaped pulse envelope.
    """
    def __init__(self, name: str, length: int, gamma: float, amplitude: float = 1.0, fixed_timing: bool = False):
        super().__init__(name, length, fixed_timing)
        self.gamma = gamma
        self.amplitude = amplitude
        self.center = (length - 1) / 2.0

    def generate_samples(self) -> np.ndarray:
        t = np.arange(self.length)
        envelope = self.amplitude * (self.gamma**2) / ((t - self.center)**2 + self.gamma**2)
        return envelope.astype(float)


class SquarePulse(Pulse):
    """
    Constant-amplitude (square) pulse envelope.
    """
    def __init__(self, name: str, length: int, amplitude: float = 1.0, fixed_timing: bool = False):
        super().__init__(name, length, fixed_timing)
        self.amplitude = amplitude

    def generate_samples(self) -> np.ndarray:
        return np.full(self.length, self.amplitude, dtype=float)


class DataPulse(Pulse):
    """
    Pulse defined by external data file (e.g. CSV of time vs amplitude).
    Automatically resamples to `length`.
    """
    def __init__(self, name: str, length: int, filename: str):
        super().__init__(name, length)
        self.filename = filename

    def generate_samples(self) -> np.ndarray:
        # Load data, skipping the first row (header) and using comma delimiter
        data = np.loadtxt(self.filename, delimiter=',', skiprows=1)
        # assume data[:,0] = time, data[:,1] = amplitude
        times = data[:,0]
        amps = data[:,1]
        # resample uniformly across times
        resampled_times = np.linspace(times[0], times[-1], num=self.length)
        envelope = np.interp(resampled_times, times, amps)
        return envelope.astype(float)


class MarkerEvent:
    """
    Represents a digital marker for a given pulse window.
    """
    def __init__(self, name: str, length: int, on_index: int, off_index: int):
        self.name = name
        self.length = length
        self.on_index = on_index
        self.off_index = off_index

    def generate_markers(self) -> np.ndarray:
        """
        Returns a binary (0/1) array of length `self.length` marking the event window.
        """
        markers = np.zeros(self.length, dtype=int)
        markers[self.on_index:self.off_index] = 1
        return markers


