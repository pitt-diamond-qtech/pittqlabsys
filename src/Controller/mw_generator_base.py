# Created by gurudevdutt at 7/30/25
# controllers/mw_generator_base.py

import socket
import pyvisa
from abc import ABC, abstractmethod
from pathlib import Path
from src.core.device import Device, Parameter  # <-- your existing base
import logging

logger = logging.getLogger("mw_generator_base")

class MicrowaveGeneratorBase(Device, ABC):

    _DEFAULT_SETTINGS = Parameter([
        Parameter('connection_type', 'LAN', ['LAN','GPIB','RS232'], 'Transport type'),
        # for LAN:
        Parameter('ip_address', '',     str, 'IP for LAN'),
        Parameter('port',       5025,   int, 'Port for LAN'),
        # for VISA (GPIB or RS232):
        Parameter('visa_resource', '',  str, 'PyVISA resource string, e.g. GPIB0::20::INSTR or ASRL9::INSTR'),
        # optional RS232 baud:
        Parameter('baud_rate',   115200,int, 'Baud for RS232'),
        # Common parameters that might be used by subclasses
        Parameter('frequency', 1e9, float, 'Frequency in Hz'),
        Parameter('power', -10, float, 'Power in dBm'),
        Parameter('phase', 0, float, 'Phase in degrees'),
        Parameter('amplitude', -10, float, 'Amplitude in dBm'),
    ])

    def __init__(self, name=None, settings=None):
        # Initialize _inst to None first to avoid AttributeError
        self._inst = None
        super().__init__(name, settings)
        self._init_transport()

    def _init_transport(self):
        t = self.settings['connection_type']
        if t == 'LAN':
            self._addr = (self.settings['ip_address'], self.settings['port'])
            # For testing purposes, create a dummy _inst for LAN connections
            self._inst = None
        elif t in ('GPIB','RS232'):
            rm = pyvisa.ResourceManager()
            res = self.settings['visa_resource']
            self._inst = rm.open_resource(res)
            if t == 'RS232':
                try:
                    # RS-232 on USB-VISA often uses serial settings
                    self._inst.baud_rate = self.settings['baud_rate']
                except AttributeError:
                    # some backends may not expose baud_rate property
                    logger.debug("Could not set baud_rate on VISA inst")
        else:
            raise ValueError(f"Unknown transport: {t}")
        
        # Ensure _inst is always available for testing
        if not hasattr(self, '_inst'):
            self._inst = None

    def _send(self, cmd: str):
        if self.settings['connection_type']=='LAN':
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(self._addr)
            sock.sendall((cmd + "\n").encode())
            # Store socket for testing purposes
            self._sock = sock
            # Don't close immediately for testing
            # sock.close()
        else:  # GPIB or RS232
            if self._inst is not None:
                self._inst.write(cmd)
            else:
                raise RuntimeError(f"No VISA instrument available for {self.settings['connection_type']} connection")

    def _query(self, cmd: str) -> str:
        if self.settings['connection_type']=='LAN':
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(self._addr)
            if not cmd.endswith('?'):
                cmd = cmd.strip() + '?'
            sock.sendall((cmd + "\n").encode())
            data = b''
            while not data.endswith(b'\n'):
                data += sock.recv(1024)
            sock.close()
            return data.decode().strip()
        else:
            # GPIB or RS232
            return self._inst.query(cmd)

    @abstractmethod
    def set_frequency(self, freq_hz: float):    pass

    @abstractmethod
    def set_power(self, power_dbm: float):      pass

    @abstractmethod
    def set_phase(self, phase_deg: float):      pass

    def output_on(self):
        self._send("OUTP ON")

    def output_off(self):
        self._send("OUTP OFF")

    def close(self):
        if self.settings['connection_type'] in ('GPIB','RS232'):
            self._inst.close()

    @property
    def sock(self):
        """Return the socket for testing purposes."""
        return getattr(self, '_sock', None)
