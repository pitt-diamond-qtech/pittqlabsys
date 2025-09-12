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
# utils.py
from __future__ import annotations
import numpy as np
import random

def integrate_cumulative(x: np.ndarray, dx: float) -> np.ndarray:
    return np.cumsum(x) * dx

def interp1d_cubic(x, y, kind='cubic'):
    from scipy.interpolate import interp1d
    return interp1d(x, y, kind=kind)

PauliGates = ['(identity)', '(+pi_x)', '(+pi_y)', '(+pi_z)',
              '(-pi_x)', '(-pi_y)', '(-pi_z)']

CompGates  = ['(+pi/2_x)', '(-pi/2_x)', '(+pi/2_y)', '(-pi/2_y)']

# Build your rotation matrices once
I = np.eye(2)
X = np.array([[0, 1], [1, 0]])
Y = np.array([[0, -1j], [1j, 0]])
Z = np.array([[1, 0], [0, -1]])

def rotation(axis: np.ndarray, angle: float) -> np.ndarray:
    """Return the unitary for a rotation about `axis` by `angle` radians."""
    return np.cos(angle/2)*I - 1j*np.sin(angle/2)*axis

# Gate → matrix lookup
# GateMatrix = {
#     '(identity)':     I,
#     '(+pi_x)':        rotation(X, np.pi),
#     '(-pi_x)':        rotation(-X, np.pi),
#     '(+pi_y)':        rotation(Y, np.pi),
#     '(-pi_y)':        rotation(-Y, np.pi),
#     '(+pi_z)':        rotation(Z, np.pi),
#     '(-pi_z)':        rotation(-Z, np.pi),
#     **{g: rotation(X, np.pi/2) for g in ['(+pi/2_x)']},  # etc…
#     # Fill out all CompGates similarly…
# }


gate_specs = [
    ('(+pi/2_x)', X,  np.pi/2),
    ('(-pi/2_x)', X, -np.pi/2),
    ('(+pi/2_y)', Y,  np.pi/2),
    ('(-pi/2_y)', Y, -np.pi/2),
    ('(+pi/2_z)', Z,  np.pi/2),
    ('(-pi/2_z)', Z, -np.pi/2),
    # … add full-pi gates too if you like …
    ('(+pi_x)', X,  np.pi),
    ('(-pi_x)', X, -np.pi),
    ('(+pi_y)', Y,  np.pi),
    ('(-pi_y)', Y, -np.pi),
    ('(+pi_z)', Z,  np.pi),
    ('(-pi_z)', Z, -np.pi),
    ('(identity)', I, 0.0)
]

GateMatrix = { name: rotation(axis, angle) for name, axis, angle in gate_specs }


def generate_comp_sequences(num_seqs: int, length: int, cache_file: str=None) -> List[List[str]]:
    """
    Return `num_seqs` lists of `length` random computational gates.
    Optionally caches/loads from `cache_file` to stay reproducible.
    """
    if cache_file and os.path.exists(cache_file):
        raw = np.genfromtxt(cache_file, dtype=str, delimiter='\n')
        return raw.reshape(num_seqs, length).tolist()

    seqs = []
    for _ in range(num_seqs):
        seqs.append([random.choice(CompGates) for __ in range(length)])
    if cache_file:
        # flatten and write
        with open(cache_file, 'w') as f:
            for row in seqs:
                for gate in row:
                    f.write(gate + "\n")
    return seqs

def random_pauli_list(length: int) -> List[str]:
    """Return a random list of Pauli gates of size `length+2` (for head/tail)."""
    return [random.choice(PauliGates) for _ in range(length+2)]

def find_R_and_final_state(comp_seq: List[str]) -> Tuple[str, str]:
    """
    Given a computational gate list, compute which 'R' gate
    makes the overall map end up in |0> or |1>, return (R, final_state).
    """
    # Multiply the matrices
    M = I
    for g in comp_seq:
        M = GateMatrix[g] @ M

    # Try all R gates
    Rcands = {g: mat for g, mat in GateMatrix.items() if g in CompGates}
    z0 = np.array([1, 0])
    z1 = np.array([0, 1])
    def state_after(R):
        M2 = GateMatrix[R] @ M
        # check overlap with z-basis
        if np.isclose(abs(z0.conj() @ (M2 @ z0)), 1):
            return 'z0'
        if np.isclose(abs(z1.conj() @ (M2 @ z0)), 1):
            return 'z1'
        return None

    valid = [(R, state_after(R)) for R in Rcands if state_after(R)]
    if not valid:
        raise RuntimeError("No valid R found")
    return random.choice(valid)
