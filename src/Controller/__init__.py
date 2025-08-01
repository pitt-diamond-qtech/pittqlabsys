# Created by Gurudev Dutt <gdutt@pitt.edu> on 2023-08-03
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

from .example_device import ExampleDevice,Plant,PIController
#from .ni_daq import PXI6733,NIDAQ,NI6281
from .ni_daq import PXI6733,NIDAQ,NI6281,PCI6229,PCI6601
# from .microwave_generator import MicrowaveGenerator  # Deprecated - use SG384Generator instead
from .nanodrive import MCLNanoDrive
from .adwin import ADwinGold
from .pulse_blaster import PulseBlaster
from .awg520 import AWG520Device
from .sg384 import SG384Generator
from .windfreak_synth_usbii import WindfreakSynthUSBII
# registry maps your config "type" strings → classes
_DEVICE_REGISTRY = {
    "awg520": AWG520Device, 
    "sg384": SG384Generator,
    "windfreak_synth_usbii": WindfreakSynthUSBII,
    "nanodrive": MCLNanoDrive,
    "adwin": ADwinGold,
    "pulseblaster": PulseBlaster,
    "example_device": ExampleDevice,
    "plant": Plant,
    "pi_controller": PIController,
    "ni_daq": NIDAQ,
    "pxi6733": PXI6733,
    "ni6281": NI6281,
    "pci6229": PCI6229,
    "pci6601": PCI6601,
}

def create_device(kind: str, **kwargs):
    cls = _DEVICE_REGISTRY.get(kind.lower())
    if cls is None:
        raise ValueError(f"Unknown device type: {kind}")
    return cls(**kwargs)