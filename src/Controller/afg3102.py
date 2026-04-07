# This file establishes communication tectronix AFG3102Device (please finish adding the functions)
# contact jat332@pitt.edu if you need help
import time
import logging
from pathlib import Path
from src.core import Parameter, Device
from PyQt5.QtCore import QThread, pyqtSignal, QObject
import pyvisa
_IP_ADDRESS = '192.168.2.57'

class AFG3102Device(Device):
    file_transfer_completed = pyqtSignal(bool, str)

    _DEFAULT_SETTINGS = Parameter(Device._get_base_settings() +[
        Parameter('ip_address', _IP_ADDRESS, str, 'IP address of the AWG520')
    ])

    _PROBES = {
        'calibrate':'calibrate',
        'test':'test',
        'get_data': 'choose whether you need to get data from this device or not',
    }

    def __init__(self, name=None, settings=None):
        super().__init__(name=name, settings=settings)
        self.logger = logging.getLogger(__name__)
        """cfg = self.settings
        self.driver = AWG520Driver(
            ip_address=cfg['ip_address'],
            scpi_port=cfg['scpi_port'],
            ftp_port=cfg['ftp_port'],
            ftp_user=cfg['ftp_user'],
            ftp_pass=cfg['ftp_pass']
        )"""
        self._ftp_thread = None
        self._ftp_worker = None
        # Test connection and set connection status
        self._test_connection()

    def _param_to_internal(self, param):
        """
        Converts settings parameters to the corresponding key used for GPIB commands in the counter.
        Args:
            param: settings parameter, ex. enable_output
        Returns: GPIB command, ex. ENBR
        """
        if param == "calibrate":
            return "*CAL?"
        elif param == "test":
            return "*TST?"
        elif param == "mass memory status":
            return "*MEM:CAT?"
        elif param == "setup memory availability":
            return "*MEM:STAT:VAL?"
        elif param == "standard event status register":
            return "*ESR?"
        elif param == "Read status byte":
            return "*STB?"
        elif param == "operation condition register":
            return "STATus:OPERation:CONDition?"
        elif param == "Return questionable condition register":
            return "STATus:QUEStionable:CONDition? "
        else:
            raise KeyError

    def update(self, settings):
        super(AFG3102Device, self).update(settings)
        for key, value in settings.items():
            if not (key == 'ip_address'):
                if self.settings.valid_values[
                    key] == bool:  # converts booleans, which are more natural to store for on/off, to
                    value = int(value)  # the integers used internally in the analyzer
                key = self._param_to_internal_write(key)
                # only send update to Device if connection to Device has been established
                if self._settings_initialized:
                    self.afg.write(key + str(value) + "MZ;")

    def _test_connection(self):
        """Test if the device is reachable and set connection status."""
        try:

            # Construct the full SCPI address
            scpi_address = f"TCPIP0::{self.settings['ip_address']}::inst0::INSTR"
            print(f"Trying to connect to: {scpi_address}")
            rm = pyvisa.ResourceManager()
            self.afg = rm.open_resource(scpi_address)
            # Test SCPI connection with *IDN? query
            idn = self.afg.query('*IDN?')
            if 'TEKTRONIX' in idn or 'AFG3102' in idn:
                self._is_connected = True
                self.logger.info(f"Connected to AFG3102: {idn}")
                print("connected to AFG3102")
            else:
                self._is_connected = False
                self.logger.warning("AFG3102 responded but ID not recognized")
        except Exception as e:
            self._is_connected = False
            self.logger.error(f"Failed to connect to AFG3102: {e}")

    @property
    def is_connected(self):
        """
        Check if device is active and connected.
        Returns: bool indicating connection status
        """
        # Re-test connection if we think we're connected but want to verify
        if self._is_connected:
            try:
                # Quick connection test
                self.afg.query('*IDN?')
                return True
            except Exception:
                self._is_connected = False
                self.logger.warning("AFG3102 connection lost")
        return self._is_connected

    def recall(self):
        self.afg.write('*RCL')

    def save(self):
        self.afg.write('*SAV')

    def close(self):
        self.afg.close()
    def read_probes(self, key=None):
        if key == 'get_data':
            return self.settings['get_data']


if __name__ == "__main__":
    dev = AFG3102Device()