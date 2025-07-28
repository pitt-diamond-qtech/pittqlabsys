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
### services/spincore_driver.py
from pulseblaster import PulseBlaster  # existing low-level library
import logging

class SpinCoreDriver:
    """
    Low-level interface to SpinCore PulseBlaster device.
    Wraps the existing PulseBlaster class to fit our service pattern.
    """
    def __init__(self, board_num=0):
        self.logger = logging.getLogger(__name__)
        self.pb = PulseBlaster(board_num)
        self.logger.info(f"Initialized PulseBlaster board {board_num}")

    def reset(self):
        """Halt and reset the pulse sequencer."""
        self.pb.reset()
        self.logger.debug("SpinCore reset")

    def load_instructions(self, instructions: list):
        """
        Load a list of low-level instructions into the device.
        `instructions` should be a list of tuples matching PulseBlaster API.
        """
        self.reset()
        for inst in instructions:
            self.pb.insert_instruction(*inst)
        self.logger.info(f"Loaded {len(instructions)} instructions")

    def start(self):
        """Begin pulse sequence playback."""
        self.pb.start()
        self.logger.debug("SpinCore sequence started")

    def stop(self):
        """Stop playback; leaves device in halted state."""
        self.pb.stop()
        self.logger.debug("SpinCore sequence stopped")

    def close(self):
        """Cleanup and close access to the device."""
        self.pb.close()
        self.logger.info("PulseBlaster connection closed")

### controllers/spincore_device.py
import logging
from src.core.device import Device
from src.Model.sequence import Sequence
from src.Model.pulses import Pulse


class SpinCoreDevice(Device):
    """
    Device wrapper for a SpinCore PulseBlaster.
    Uses Sequence and Pulse models to generate low-level instructions,
    then drives the SpinCore via SpinCoreDriver.
    """
    _DEFAULT_SETTINGS = {
        'board_num': 0,
    }

    _PROBES = {
        'status': 'Sequence running state',
    }

    def __init__(self, name=None, settings=None):
        super().__init__(name=name, settings=settings)
        self.logger = logging.getLogger(__name__)
        cfg = self.settings
        # Initialize low-level driver
        self.driver = SpinCoreDriver(board_num=cfg['board_num'])

    def load_sequence(self, seq: Sequence):
        """
        Convert a Sequence model into device instructions and load them.
        """
        # Flatten Sequence into events: (time, channel_mask, flags)
        events = seq.to_events()
        # Translate events into PulseBlaster instructions
        instructions = []
        for evt in events:
            # evt: dict with keys time, channels, marker
            inst = (evt['channels'], evt['duration'], evt['flags'])
            instructions.append(inst)
        self.driver.load_instructions(instructions)
        self.logger.info(f"Sequence {seq.name} loaded to SpinCore")

    def start_sequence(self):
        """Begin playback of the loaded sequence."""
        self.driver.start()

    def stop_sequence(self):
        """Stop playback."""
        self.driver.stop()

    def read_probes(self, key):
        """Read device-specific state."""
        if key == 'status':
            # Example: return True if running, False otherwise
            return self.driver.pb.is_running()
        raise KeyError(f"Unknown probe '{key}'")

    def cleanup(self):
        """Clean up driver resources."""
        self.driver.close()

### controllers/spincore_controller.py
from src.Model.sequence import Sequence

class SpinCoreController:
    """
    Synchronous controller for SpinCore PulseBlaster.
    Useful for scripting without threading.
    """
    def __init__(self, driver: SpinCoreDriver):
        self.driver = driver

    def run_sequence(self, seq: Sequence):
        """
        Load and start a Sequence in one call.
        """
        # Flatten and load
        events = seq.to_events()
        instructions = [(evt['channels'], evt['duration'], evt.get('flags', 0)) for evt in events]
        self.driver.load_instructions(instructions)
        # Start
        self.driver.start()

    def stop(self):
        """Stop sequence playback."""
        self.driver.stop()

    def reset(self):
        """Reset the device sequencer."""
        self.driver.reset()
