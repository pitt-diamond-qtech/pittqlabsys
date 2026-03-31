import serial
import time
import logging
from src.core.device import Device, Parameter

class HC3500(Device):

    # Command parameters
    read_func_code = 0x52 # 82 in decimal (Read Function)
    write_func_code = 0x43
    param_code = 0x00 # 0x00 targets the Setpoint


    def __init__(self, name=None, port="COM1", settings=None):
        self.name = name
        self.port = settings.get("port", port)
        self.address = settings.get("address", 1)
        self.addr_byte = self.address + 0x80

        self.logger = logging.getLogger(f"HC3500-{self.port}")

        self._ser = serial.Serial()
        self._ser.port = self.port
        self._ser.baudrate = settings.get("baudrate", 9600)
        self._ser.timeout = settings.get("timeout", 5000) / 1000.0

        self._settings = settings

    def connect(self):
        if not self._ser.is_open:
            try:
                self._ser.open()
                self.logger.info(f"Connected to HC3500 on {self.port}")
            except serial.SerialException as e:
                self.logger.error(f"Failed to connect to {self.port}: {e}")
                raise
    def disconnect(self):
        if self._ser.is_open:
            self._ser.close()
            self.logger.info(f"disconnected from HC3500 on {self.port}")

    def _calculate_checksum(self, func_code, param_code, target_val=0):
        checksum = (param_code * 256) + func_code + self.address + target_val
        chk_low = checksum & 0xFF
        chk_high = (checksum >> 8) & 0xFF
        return chk_low, chk_high
    def _send_command(self, func_code, param_code, target_val=0):

        data_low = target_val & 0xFF
        data_high = (target_val >> 8) & 0xFF

        chk_low, chk_high = self._calculate_checksum(func_code, param_code, target_val)

        command = bytes([
            self.addr_byte, self.addr_byte,
            func_code, param_code,
            data_low, data_high,
            chk_low, chk_high
        ])
        self.connect()
        self._ser.write(command)
        response = self._ser.read(10)
        if len(response) != 10:
            self.logger.warning("Invalid reponse length from HC3500 or timeout")
            return None
        return response

    @property
    def temperature(self):
        ##Reads the current temperature 
        ##Ex temp = hc3500.temperature

        response = self._send_command(self.read_func_code, self.param_code)
        if response:
            raw_pv = int.from_bytes(response[0:2], byteorder='little', signed=True)
            return raw_pv / 10.0

        return None


    @temperature.setter
    def temperature(self, target_temp_c):
        ##Sets the temperature setpoint
        ##Ex hc3500.temperature = 40.0

        target_val = int(target_temp_c * 10) & 0xFFFF

        response = self._send_command(self.write_read_code, self.param_code, target_val)
        if response:
            self.logger.info(f"Setpoint updated to {target_temp_c}")
        else:
            self.logger.error("failed to write new setpoint")
    @property
    def settings(self):
        return {
            'port': self.port,
            'baudrate': self.baudrate,
            'timeout': self.timeout,
            'auto_connect': self.auto_connect
        }


  
            