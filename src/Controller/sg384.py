# Created by gurudevdutt at 7/30/25
# controllers/sg384.py

from .mw_generator_base import MicrowaveGeneratorBase, Parameter
import logging

logger = logging.getLogger("sg384")

class SG384Generator(MicrowaveGeneratorBase):
    """
    Stanford Research Systems SG384 concrete implementation.
    Adds any SG384‐specific settings and maps them to SCPI.
    """
    _DEFAULT_SETTINGS = MicrowaveGeneratorBase._DEFAULT_SETTINGS + Parameter([
        Parameter('modulation_type',   'FM',  ['AM','FM','PM','Sweep'],    'Modulation type'),
        Parameter('modulation_depth',  1e6,   float,   'Deviation in Hz'),
        # add more SG384‐only knobs here…
    ])

    def __init__(self, name=None, settings=None):
        super().__init__(name, settings)
        # verify comms
        idn = self._query("*IDN?")
        logger.info(f"SG384 IDN: {idn}")

    def set_frequency(self, hz: float):
        """SCPI: FREQ <value>HZ"""
        self.settings['frequency'] = hz
        self._send(f"FREQ {hz}HZ")

    def set_power(self, dbm: float):
        """SCPI: POWR <value>DBM"""
        self.settings['amplitude'] = dbm
        self._send(f"POWR {dbm}DBM")

    def set_phase(self, deg: float):
        """SCPI: PHAS <value>DEG"""
        self.settings['phase'] = deg
        self._send(f"PHAS {deg}DEG")

    def enable_modulation(self):
        self._send("MODL:STAT ON")

    def disable_modulation(self):
        self._send("MODL:STAT OFF")

    def set_modulation_type(self, mtype: str):
        self.settings['modulation_type'] = mtype
        self._send(f"MODL:TYPE {mtype}")

    def set_modulation_depth(self, depth_hz: float):
        self.settings['modulation_depth'] = depth_hz
        self._send(f"FDEV {depth_hz}")
