# Created by Gurudev Dutt <gdutt@pitt.edu> on 2025-07-28
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

import socket
import time
import numpy as np
import logging
from pathlib import Path
from ftplib import FTP
from src.core import Parameter, Device
from PyQt5.QtCore import QThread, pyqtSignal, QObject

_DAC_BITS = 10
_IP_ADDRESS = '172.17.39.2' # comment out for testing
#_IP_ADDRESS = '127.0.0.1'# use loopback for testing
_PORT = 4000 # comment out for testing
#_PORT = 65432 #switch ports for loopback
_FTP_PORT = 21 # 63217 use this for teting
#_FTP_PORT = 63217
_MW_S1 = 'S1' #disconnected for now
_MW_S2 = 'S2'#channel 1, marker 1
_GREEN_AOM = 'Green' # ch1, marker 2
_ADWIN_TRIG = 'Measure' # ch2, marker 2
_WAVE = 'Wave' #channel 1 and 2, analog I/Q data
_DAC_UPPER = 1024.0 # DAC has only 1024 levels
_DAC_MID = 512
_WFM_MEMORY_LIMIT = 1048512 # at most this many points can be in a waveform
_SEQ_MEMORY_LIMIT = 8000
_IQTYPE = np.dtype('<f4') # AWG520 stores analog values as 4 bytes in little-endian format
_MARKTYPE = np.dtype('<i1') # AWG520 stores marker values as 1 byte
# unit conversion factors
_GHz = 1.0e9  # Gigahertz
_MHz = 1.0e6  # Megahertz
_us = 1.0e-6  # Microseconds
_ns = 1.0e-9  # Nanoseconds


class AWG520Driver:
    """
    Low-level service for Tektronix AWG520. Handles SCPI commands over TCP and file transfers over FTP.
    """
    def __init__(self, ip_address: str, scpi_port: int = _PORT,
                 ftp_port: int = _FTP_PORT, ftp_user: str = 'usr', ftp_pass: str = 'pw'):
        self.addr = (ip_address, scpi_port)
        self.ftp_port = ftp_port
        self.ftp_user = ftp_user
        self.ftp_pass = ftp_pass
        self.logger = logging.getLogger(__name__)
        self._connect_ftp()

    def _connect_ftp(self):
        try:
            self.ftp = FTP()
            self.ftp.connect(self.addr[0], self.ftp_port)
            self.ftp.login(self.ftp_user, self.ftp_pass)
            self.logger.info('AWG520 FTP login successful')
        except Exception as e:
            self.logger.error(f'FTP connection failed: {e}')
            raise

    def send_command(self, cmd: str, query: bool = False, timeout: float = 5.0):
        """
        Send a SCPI command over TCP. If query=True, return the response string.
        """
        if not cmd.endswith('\n'):
            cmd += '\n'
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(timeout)
                s.connect(self.addr)
                self.logger.debug(f"SCPI >>> {cmd.strip()}")
                s.sendall(cmd.encode())
                if query:
                    reply = b''
                    while not reply.endswith(b'\n'):
                        reply += s.recv(1024)
                    text = reply.decode().strip()
                    self.logger.debug(f"SCPI <<< {text}")
                    return text
        except Exception as e:
            self.logger.error(f"SCPI command failed: {e}")
            return None

    # --- Clock configuration ---
    def set_clock_external(self):
        return self.send_command('AWGC:CLOC:SOUR EXT')

    def set_clock_internal(self):
        return self.send_command('AWGC:CLOC:SOUR INT')

    def set_ref_clock_external(self):
        self.send_command('SOUR1:ROSC:SOUR EXT')
        return self.send_command('SOUR2:ROSC:SOUR EXT')

    def set_ref_clock_internal(self):
        self.send_command('SOUR1:ROSC:SOUR INT')
        return self.send_command('SOUR2:ROSC:SOUR INT')

    # --- Sequence control ---
    def set_enhanced_run_mode(self):
        return self.send_command('AWGC:RMOD ENH')

    def setup_sequence(self, seqfilename: str, enable_iq: bool = False):
        """
        High-level setup: clocks, enhanced mode, load sequence, set voltages.
        """
        self.set_ref_clock_external()
        time.sleep(0.1)
        self.set_enhanced_run_mode()
        time.sleep(0.1)
        # load sequence on both channels
        for ch in (1, 2):
            self.send_command(f'SOUR{ch}:FUNC:USER "{seqfilename}","MAIN"')
            time.sleep(0.1)
        # set default voltages and markers
        for ch in (1, 2):
            self.send_command(f'SOUR{ch}:VOLT:AMPL 1000mV')
            time.sleep(0.1)
            self.send_command(f'SOUR{ch}:VOLT:OFFS 0mV')
            time.sleep(0.1)
            for m in (1, 2):
                self.send_command(f'SOUR{ch}:MARK{m}:VOLT:LOW 0')
                time.sleep(0.05)
                self.send_command(f'SOUR{ch}:MARK{m}:VOLT:HIGH 2.0')
                time.sleep(0.05)
        # output state
        if enable_iq:
            self.send_command('OUTP1:STAT ON')
            time.sleep(0.1)
            self.send_command('OUTP2:STAT ON')
            time.sleep(0.1)
        else:
            self.send_command('OUTP1:STAT ON')
            time.sleep(0.1)

    def run(self):
        return self.send_command('AWGC:RUN')

    def stop(self):
        return self.send_command('AWGC:STOP')

    def trigger(self):
        return self.send_command('*TRG')

    def event(self):
        return self.send_command('AWGC:EVEN')

    def jump(self, line: int):
        return self.send_command(f'AWGC:EVEN:SOFT {line}')

    # --- Marker control for laser applications ---
    def set_ch1_marker2_laser_on(self):
        """
        Turn on CH1 Marker 2 for laser control by setting low level to 5V.
        This effectively enables the laser by setting the marker to a high voltage level.
        """
        self.logger.info("Turning on CH1 Marker 2 (laser control)")
        # Set low level to 2V to turn on the laser
        result1 = self.send_command('SOUR1:MARK2:VOLT:LOW 2.0')
        time.sleep(0.05)
        # Set high level to 2V as well to ensure consistent output
        result2 = self.send_command('SOUR1:MARK2:VOLT:HIGH 2.0')
        time.sleep(0.05)
        return result1 and result2

    def set_ch1_marker2_laser_off(self):
        """
        Turn off CH1 Marker 2 for laser control by setting low level to 0V.
        This effectively disables the laser by setting the marker to a low voltage level.
        """
        self.logger.info("Turning off CH1 Marker 2 (laser control)")
        # Set low level to 0V to turn off the laser
        result1 = self.send_command('SOUR1:MARK2:VOLT:LOW 0.0')
        time.sleep(0.05)
        # Set high level to 0V as well to ensure consistent output
        result2 = self.send_command('SOUR1:MARK2:VOLT:HIGH 0.0')
        time.sleep(0.05)
        return result1 and result2

    def set_ch1_marker2_voltage(self, low_voltage: float, high_voltage: float = None):
        """
        Set CH1 Marker 2 voltage levels for custom laser control.
        
        Args:
            low_voltage: Low voltage level in volts
            high_voltage: High voltage level in volts (defaults to low_voltage if None)
        """
        if high_voltage is None:
            high_voltage = low_voltage
        
        self.logger.info(f"Setting CH1 Marker 2 voltage: LOW={low_voltage}V, HIGH={high_voltage}V")
        
        # Set low level
        result1 = self.send_command(f'SOUR1:MARK2:VOLT:LOW {low_voltage}')
        time.sleep(0.05)
        # Set high level
        result2 = self.send_command(f'SOUR1:MARK2:VOLT:HIGH {high_voltage}')
        time.sleep(0.05)
        
        return result1 and result2

    def get_ch1_marker2_voltage(self):
        """
        Get current CH1 Marker 2 voltage levels.
        
        Returns:
            tuple: (low_voltage, high_voltage) in volts
        """
        try:
            low_v = self.send_command('SOUR1:MARK2:VOLT:LOW?', query=True)
            time.sleep(0.05)
            high_v = self.send_command('SOUR1:MARK2:VOLT:HIGH?', query=True)
            time.sleep(0.05)
            
            if low_v is not None and high_v is not None:
                return (float(low_v), float(high_v))
            else:
                return (None, None)
        except Exception as e:
            self.logger.error(f"Failed to get CH1 Marker 2 voltage: {e}")
            return (None, None)

    def is_ch1_marker2_laser_on(self):
        """
        Check if CH1 Marker 2 laser control is currently on.
        
        Returns:
            bool: True if laser is on (voltage > 2.0V), False otherwise
        """
        try:
            low_v, high_v = self.get_ch1_marker2_voltage()
            if low_v is not None and high_v is not None:
                # Consider laser "on" if voltage is above 2.0V (typical threshold)
                return low_v > 2.0 or high_v > 2.0
            return False
        except Exception as e:
            self.logger.error(f"Failed to check CH1 Marker 2 laser status: {e}")
            return False

    # --- Additional marker control functions for flexibility ---
    def set_ch1_marker1_voltage(self, low_voltage: float, high_voltage: float = None):
        """
        Set CH1 Marker 1 voltage levels.
        
        Args:
            low_voltage: Low voltage level in volts
            high_voltage: High voltage level in volts (defaults to low_voltage if None)
        """
        if high_voltage is None:
            high_voltage = low_voltage
        
        self.logger.info(f"Setting CH1 Marker 1 voltage: LOW={low_voltage}V, HIGH={high_voltage}V")
        
        result1 = self.send_command(f'SOUR1:MARK1:VOLT:LOW {low_voltage}')
        time.sleep(0.05)
        result2 = self.send_command(f'SOUR1:MARK1:VOLT:HIGH {high_voltage}')
        time.sleep(0.05)
        
        return result1 and result2

    def get_ch1_marker1_voltage(self):
        """
        Get current CH1 Marker 1 voltage levels.
        
        Returns:
            tuple: (low_voltage, high_voltage) in volts
        """
        try:
            low_v = self.send_command('SOUR1:MARK1:VOLT:LOW?', query=True)
            time.sleep(0.05)
            high_v = self.send_command('SOUR1:MARK1:VOLT:HIGH?', query=True)
            time.sleep(0.05)
            
            if low_v is not None and high_v is not None:
                return (float(low_v), float(high_v))
            else:
                return (None, None)
        except Exception as e:
            self.logger.error(f"Failed to get CH1 Marker 1 voltage: {e}")
            return (None, None)

    def set_ch2_marker1_voltage(self, low_voltage: float, high_voltage: float = None):
        """
        Set CH2 Marker 1 voltage levels.
        
        Args:
            low_voltage: Low voltage level in volts
            high_voltage: High voltage level in volts (defaults to low_voltage if None)
        """
        if high_voltage is None:
            high_voltage = low_voltage
        
        self.logger.info(f"Setting CH2 Marker 1 voltage: LOW={low_voltage}V, HIGH={high_voltage}V")
        
        result1 = self.send_command(f'SOUR2:MARK1:VOLT:LOW {low_voltage}')
        time.sleep(0.05)
        result2 = self.send_command(f'SOUR2:MARK1:VOLT:HIGH {high_voltage}')
        time.sleep(0.05)
        
        return result1 and result2

    def get_ch2_marker1_voltage(self):
        """
        Get current CH2 Marker 1 voltage levels.
        
        Returns:
            tuple: (low_voltage, high_voltage) in volts
        """
        try:
            low_v = self.send_command('SOUR2:MARK1:VOLT:LOW?', query=True)
            time.sleep(0.05)
            high_v = self.send_command('SOUR2:MARK1:VOLT:HIGH?', query=True)
            time.sleep(0.05)
            
            if low_v is not None and high_v is not None:
                return (float(low_v), float(high_v))
            else:
                return (None, None)
        except Exception as e:
            self.logger.error(f"Failed to get CH2 Marker 1 voltage: {e}")
            return (None, None)

    def set_ch2_marker2_voltage(self, low_voltage: float, high_voltage: float = None):
        """
        Set CH2 Marker 2 voltage levels.
        
        Args:
            low_voltage: Low voltage level in volts
            high_voltage: High voltage level in volts (defaults to low_voltage if None)
        """
        if high_voltage is None:
            high_voltage = low_voltage
        
        self.logger.info(f"Setting CH2 Marker 2 voltage: LOW={low_voltage}V, HIGH={high_voltage}V")
        
        result1 = self.send_command(f'SOUR2:MARK2:VOLT:LOW {low_voltage}')
        time.sleep(0.05)
        result2 = self.send_command(f'SOUR2:MARK2:VOLT:HIGH {high_voltage}')
        time.sleep(0.05)
        
        return result1 and result2

    def get_ch2_marker2_voltage(self):
        """
        Get current CH2 Marker 2 voltage levels.
        
        Returns:
            tuple: (low_voltage, high_voltage) in volts
        """
        try:
            low_v = self.send_command('SOUR2:MARK2:VOLT:LOW?', query=True)
            time.sleep(0.05)
            high_v = self.send_command('SOUR2:MARK2:VOLT:HIGH?', query=True)
            time.sleep(0.05)
            
            if low_v is not None and high_v is not None:
                return (float(low_v), float(high_v))
            else:
                return (None, None)
        except Exception as e:
            self.logger.error(f"Failed to get CH2 Marker 2 voltage: {e}")
            return (None, None)

    # --- Legacy functions for backward compatibility ---
    def set_ch2_marker2_laser_on(self):
        """
        Legacy function: Turn on CH2 Marker 2 for laser control.
        Note: This function is deprecated. Use set_ch1_marker2_laser_on() for laser control.
        """
        self.logger.warning("set_ch2_marker2_laser_on is deprecated. Use set_ch1_marker2_laser_on() for laser control.")
        return self.set_ch2_marker2_voltage(2.0)

    def set_ch2_marker2_laser_off(self):
        """
        Legacy function: Turn off CH2 Marker 2 for laser control.
        Note: This function is deprecated. Use set_ch1_marker2_laser_off() for laser control.
        """
        self.logger.warning("set_ch2_marker2_laser_off is deprecated. Use set_ch1_marker2_laser_off() for laser control.")
        return self.set_ch2_marker2_voltage(0.0)

    def is_ch2_marker2_laser_on(self):
        """
        Legacy function: Check if CH2 Marker 2 laser control is currently on.
        Note: This function is deprecated. Use is_ch1_marker2_laser_on() for laser control.
        """
        self.logger.warning("is_ch2_marker2_laser_on is deprecated. Use is_ch1_marker2_laser_on() for laser control.")
        try:
            low_v, high_v = self.get_ch2_marker2_voltage()
            if low_v is not None and high_v is not None:
                return low_v > 2.0 or high_v > 2.0
            return False
        except Exception as e:
            self.logger.error(f"Failed to check CH2 Marker 2 laser status: {e}")
            return False

    # --- Function Generator (FG) for IQ Modulation ---
    def mw_on_sb10MHz(self, enable_iq=False):
        """
        Turn on microwave output with 10MHz sine wave(s) for IQ modulation.
        
        Args:
            enable_iq (bool): If True, enables both channels for I/Q modulation.
                            If False, only CH1 outputs a sine wave.
        
        This function:
        - Sets external reference clock (Rubidium lab clock)
        - Configures CH1 Marker 1 for MW control
        - Generates 10MHz sine waves on CH1 and optionally CH2
        - For IQ mode: CH1 = sine, CH2 = cosine (90° phase shift)
        """
        self.logger.info(f"Turning on MW with 10MHz {'IQ modulation' if enable_iq else 'single channel'}")
        
        # Setup external reference clock (Rubidium lab clock)
        self.set_ref_clock_external()
        time.sleep(0.1)
        
        # Configure CH1 Marker 1 for MW control
        result1 = self.send_command('SOUR1:MARK1:VOLT:LOW 2.0')
        time.sleep(0.05)
        
        if enable_iq:
            # Configure both channels for IQ modulation
            # CH1: Sine wave at 10MHz
            result2 = self.send_command('AWGC:FG1:FUNC SIN')
            time.sleep(0.05)
            result3 = self.send_command('AWGC:FG1:FREQ 10MHz')
            time.sleep(0.05)
            result4 = self.send_command('AWGC:FG1:VOLT 2.0')
            time.sleep(0.05)
            
            # CH2: Cosine wave at 10MHz (90° phase shift)
            result5 = self.send_command('AWGC:FG2:FUNC SIN')
            time.sleep(0.05)
            result6 = self.send_command('AWGC:FG2:FREQ 10MHz')
            time.sleep(0.05)
            result7 = self.send_command('AWGC:FG2:PHAS 90DEG')
            time.sleep(0.05)
            result8 = self.send_command('AWGC:FG2:VOLT 2.0')
            time.sleep(0.05)
            
            return all([result1, result2, result3, result4, result5, result6, result7, result8])
        else:
            # Configure only CH1 for single channel output
            result2 = self.send_command('AWGC:FG1:FUNC SIN')
            time.sleep(0.05)
            result3 = self.send_command('AWGC:FG1:FREQ 10MHz')
            time.sleep(0.05)
            result4 = self.send_command('AWGC:FG1:VOLT 2.0')
            time.sleep(0.05)
            
            return all([result1, result2, result3, result4])

    def mw_off_sb10MHz(self, enable_iq=False):
        """
        Turn off microwave output by setting function generator voltages to 0.
        
        Args:
            enable_iq (bool): If True, turns off both channels.
                            If False, turns off only CH1.
        
        Note: This function assumes mw_on_sb10MHz was called previously.
        """
        self.logger.info(f"Turning off MW {'IQ modulation' if enable_iq else 'single channel'}")
        
        # Turn off CH1 Marker 1 MW control
        result1 = self.send_command('SOUR1:MARK1:VOLT:HIGH 0.0')
        time.sleep(0.05)
        
        if enable_iq:
            # Turn off both channels
            result2 = self.send_command('AWGC:FG1:VOLT 0.0')
            time.sleep(0.05)
            result3 = self.send_command('AWGC:FG2:VOLT 0.0')
            time.sleep(0.05)
            
            return all([result1, result2, result3])
        else:
            # Turn off only CH1
            result2 = self.send_command('AWGC:FG1:VOLT 0.0')
            time.sleep(0.05)
            
            return all([result1, result2])

    def set_function_generator(self, channel, function='SIN', frequency='10MHz', 
                             voltage=2.0, phase=0.0, enable=True):
        """
        Configure function generator parameters for a specific channel.
        
        Args:
            channel (int): Channel number (1 or 2)
            function (str): Waveform function ('SIN', 'SQU', 'TRI', 'RAMP', 'NOIS', 'DC')
            frequency (str): Frequency in Hz, kHz, MHz, or GHz (e.g., '10MHz', '1kHz')
            voltage (float): Output voltage in volts
            phase (float): Phase offset in degrees
            enable (bool): If True, sets voltage to specified value, if False sets to 0V
        
        Returns:
            bool: True if all commands succeeded, False otherwise
        """
        if channel not in [1, 2]:
            self.logger.error(f"Invalid channel: {channel}. Must be 1 or 2.")
            return False
        
        self.logger.info(f"Setting FG{channel}: {function} at {frequency}, {voltage}V, {phase}°")
        
        # Set function type
        result1 = self.send_command(f'AWGC:FG{channel}:FUNC {function}')
        time.sleep(0.05)
        
        # Set frequency
        result2 = self.send_command(f'AWGC:FG{channel}:FREQ {frequency}')
        time.sleep(0.05)
        
        # Set phase
        if phase != 0.0:
            result3 = self.send_command(f'AWGC:FG{channel}:PHAS {phase}DEG')
            time.sleep(0.05)
        else:
            result3 = True
        
        # Set voltage
        voltage_set = voltage if enable else 0.0
        result4 = self.send_command(f'AWGC:FG{channel}:VOLT {voltage_set}')
        time.sleep(0.05)
        
        return all([result1, result2, result3, result4])

    def get_function_generator_status(self, channel):
        """
        Get current function generator status for a specific channel.
        
        Args:
            channel (int): Channel number (1 or 2)
        
        Returns:
            dict: Dictionary containing function, frequency, voltage, and phase
        """
        if channel not in [1, 2]:
            self.logger.error(f"Invalid channel: {channel}. Must be 1 or 2.")
            return None
        
        try:
            # Query all parameters
            function = self.send_command(f'AWGC:FG{channel}:FUNC?', query=True)
            time.sleep(0.05)
            frequency = self.send_command(f'AWGC:FG{channel}:FREQ?', query=True)
            time.sleep(0.05)
            voltage = self.send_command(f'AWGC:FG{channel}:VOLT?', query=True)
            time.sleep(0.05)
            phase = self.send_command(f'AWGC:FG{channel}:PHAS?', query=True)
            time.sleep(0.05)
            
            if all([function, frequency, voltage, phase]):
                return {
                    'function': function,
                    'frequency': frequency,
                    'voltage': float(voltage),
                    'phase': float(phase)
                }
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to get FG{channel} status: {e}")
            return None

    def enable_iq_modulation(self, frequency='10MHz', voltage=2.0):
        """
        Enable I/Q modulation with sine and cosine waves.
        
        Args:
            frequency (str): Frequency for both channels (e.g., '10MHz')
            voltage (float): Voltage amplitude for both channels
        
        Returns:
            bool: True if I/Q modulation was enabled successfully
        """
        self.logger.info(f"Enabling I/Q modulation at {frequency}, {voltage}V")
        
        # Configure CH1 for I (sine wave, 0° phase)
        result1 = self.set_function_generator(1, 'SIN', frequency, voltage, 0.0, True)
        
        # Configure CH2 for Q (sine wave, 90° phase)
        result2 = self.set_function_generator(2, 'SIN', frequency, voltage, 90.0, True)
        
        return result1 and result2

    def disable_iq_modulation(self):
        """
        Disable I/Q modulation by setting both channels to 0V.
        
        Returns:
            bool: True if I/Q modulation was disabled successfully
        """
        self.logger.info("Disabling I/Q modulation")
        
        # Turn off both channels
        result1 = self.send_command('AWGC:FG1:VOLT 0.0')
        time.sleep(0.05)
        result2 = self.send_command('AWGC:FG2:VOLT 0.0')
        time.sleep(0.05)
        
        return result1 and result2

    # --- File operations via FTP ---
    def list_files(self):
        try:
            return self.ftp.nlst()
        except Exception as e:
            self.logger.error(f'List files failed: {e}')
            return []

    def upload_file(self, local_path: str, remote_name: str) -> bool:
        try:
            with open(local_path, 'rb') as f:
                self.ftp.storbinary(f'STOR {remote_name}', f)
            self.logger.info(f"FTP upload: {local_path} -> {remote_name}")
            return True
        except Exception as e:
            self.logger.error(f"FTP upload failed: {e}")
            return False

    def download_file(self, filename: str, local_path: str) -> bool:
        try:
            with open(local_path, 'wb') as f:
                self.ftp.retrbinary(f'RETR {filename}', f.write)
            self.logger.info(f"FTP download: {filename} -> {local_path}")
            return True
        except Exception as e:
            self.logger.error(f"FTP download failed: {e}")
            return False

    def get_select_files(self, pattern: str) -> list:
        matched = []
        try:
            for fn in self.ftp.nlst():
                if pattern in fn:
                    self.download_file(fn, fn)
                    matched.append(fn)
            return matched
        except Exception as e:
            self.logger.error(f"FTP pattern download failed: {e}")
            return matched

    def delete_file(self, filename: str) -> bool:
        try:
            if filename == 'parameter.dat':
                raise ValueError('Cannot delete protected file')
            self.ftp.delete(filename)
            self.logger.info(f"FTP delete: {filename}")
            return True
        except Exception as e:
            self.logger.error(f"FTP delete failed: {e}")
            return False

    def remove_selected_files(self, pattern: str) -> list:
        removed = []
        try:
            for fn in self.ftp.nlst():
                if pattern in fn:
                    if self.delete_file(fn):
                        removed.append(fn)
            return removed
        except Exception as e:
            self.logger.error(f"FTP remove selected failed: {e}")
            return removed

    def cleanup(self):
        """Clean up resources and mark device as disconnected."""
        try:
            self.stop()
        except:
            pass
        try:
            self.ftp.quit()
        except:
            pass

class FileTransferWorker(QObject):
    """Worker object to perform FTP transfers in a separate thread."""
    finished = pyqtSignal(bool, str)

    def __init__(self, driver: AWG520Driver, local_path: str, remote_name: str):
        super().__init__()
        self.driver = driver
        self.local_path = local_path
        self.remote_name = remote_name

    def run(self):
        """Uploads the file and emits finished signal when done."""
        success = self.driver.upload_file(self.local_path, self.remote_name)
        self.finished.emit(success, self.remote_name)

class AWG520Device(Device):
    """Device wrapper for Tektronix AWG520 using your Device framework."""
    file_transfer_completed = pyqtSignal(bool, str)

    _DEFAULT_SETTINGS = Parameter([
        Parameter('ip_address', _IP_ADDRESS,str,'IP address of the AWG520'),
        Parameter('scpi_port', _PORT,int,'SCPI port of the AWG520'),
        Parameter('ftp_port', _FTP_PORT,int,'FTP port of the AWG520'),
        Parameter('ftp_user', 'usr',str, 'FTP username for the AWG520'),
        Parameter('ftp_pass','pw',str, 'FTP password for the AWG520'),
        Parameter('seq_file', 'scan.seq', str, 'Sequence file to upload to the AWG520'),
        Parameter('enable_iq', False, bool, 'Enable I/Q output on the AWG520')
    ])


    _PROBES = {
        'status': 'AWG device status',
    }

    def __init__(self, name=None, settings=None):
        super().__init__(name=name, settings=settings)
        self.logger = logging.getLogger(__name__)
        cfg = self.settings
        self.driver = AWG520Driver(
            ip_address=cfg['ip_address'],
            scpi_port=cfg['scpi_port'],
            ftp_port=cfg['ftp_port'],
            ftp_user=cfg['ftp_user'],
            ftp_pass=cfg['ftp_pass']
        )
        self._ftp_thread = None
        self._ftp_worker = None
        # Test connection and set connection status
        self._test_connection()
    
    def get_connection_template_path(self) -> Path:
        """
        Get the path to the default AWG520 connection template.
        
        Returns:
            Path to the connection template file
        """
        return Path(__file__).parent / "awg520_connection.template.json"

    def _test_connection(self):
        """Test if the device is reachable and set connection status."""
        try:
            # Test SCPI connection with *IDN? query
            idn = self.driver.send_command('*IDN?', query=True)
            if idn and ('SONY/TEK' in idn or 'AWG520' in idn):
                self._is_connected = True
                self.logger.info(f"Connected to AWG520: {idn}")
            else:
                self._is_connected = False
                self.logger.warning("AWG520 responded but ID not recognized")
        except Exception as e:
            self._is_connected = False
            self.logger.error(f"Failed to connect to AWG520: {e}")

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
                self.driver.send_command('*STB?', query=True)
                return True
            except Exception:
                self._is_connected = False
                self.logger.warning("AWG520 connection lost")
        return self._is_connected

    def setup(self):
        """Setup the AWG520 device with sequence file."""
        if not self.is_connected:
            self.logger.error("Cannot setup AWG520: device not connected")
            return False
            
        cfg = self.settings
        seq = cfg['seq_file']
        self.driver.set_ref_clock(1, 'EXT')
        self.driver.set_ref_clock(2, 'EXT')
        time.sleep(0.1)
        self.driver.send_command('AWGC:RMOD ENH')
        time.sleep(0.1)
        self._start_file_transfer(seq)
        return True

    def _start_file_transfer(self, local_path: str):
        remote_name = local_path
        self._ftp_thread = QThread()
        self._ftp_worker = FileTransferWorker(self.driver, local_path, remote_name)
        self._ftp_worker.moveToThread(self._ftp_thread)
        self._ftp_thread.started.connect(self._ftp_worker.run)
        self._ftp_worker.finished.connect(self._on_file_transfer_finished)
        self._ftp_worker.finished.connect(self._ftp_thread.quit)
        self._ftp_worker.finished.connect(self._ftp_worker.deleteLater)
        self._ftp_thread.finished.connect(self._ftp_thread.deleteLater)
        self._ftp_thread.start()
        self.logger.info(f"Started async upload of {local_path}")

    def _on_file_transfer_finished(self, success: bool, remote_name: str):
        if success:
            self.logger.info(f"Upload succeeded: {remote_name}")
            self.driver.configure_sequence(remote_name)
            for ch in (1, 2):
                self.driver.set_amplitude(ch)
                self.driver.set_offset(ch)
                self.driver.set_marker(ch, 1)
                self.driver.set_marker(ch, 2)
            self.logger.info('AWG setup complete after file transfer')
        else:
            self.logger.error(f"Upload failed for {remote_name}")
        self.file_transfer_completed.emit(success, remote_name)

    def run_sequence(self):
        self.driver.run()

    def stop_sequence(self):
        self.driver.stop()

    def trigger(self):
        self.driver.trigger()

    # --- Laser control via CH1 Marker 2 ---
    def laser_on(self):
        """Turn on the laser using CH1 Marker 2."""
        return self.driver.set_ch1_marker2_laser_on()

    def laser_off(self):
        """Turn off the laser using CH1 Marker 2."""
        return self.driver.set_ch1_marker2_laser_off()

    def set_laser_voltage(self, voltage: float):
        """Set laser control voltage using CH1 Marker 2."""
        return self.driver.set_ch1_marker2_voltage(voltage)

    def get_laser_voltage(self):
        """Get current laser control voltage from CH1 Marker 2."""
        return self.driver.get_ch1_marker2_voltage()

    def is_laser_on(self):
        """Check if the laser is currently on."""
        return self.driver.is_ch1_marker2_laser_on()

    # --- Additional marker control methods ---
    def set_ch1_marker1_voltage(self, voltage: float):
        """Set CH1 Marker 1 voltage."""
        return self.driver.set_ch1_marker1_voltage(voltage)

    def get_ch1_marker1_voltage(self):
        """Get CH1 Marker 1 voltage."""
        return self.driver.get_ch1_marker1_voltage()

    def set_ch2_marker1_voltage(self, voltage: float):
        """Set CH2 Marker 1 voltage."""
        return self.driver.set_ch2_marker1_voltage(voltage)

    def get_ch2_marker1_voltage(self):
        """Get CH2 Marker 1 voltage."""
        return self.driver.get_ch2_marker1_voltage()

    def set_ch2_marker2_voltage(self, voltage: float):
        """Set CH2 Marker 2 voltage."""
        return self.driver.set_ch2_marker2_voltage(voltage)

    def get_ch2_marker2_voltage(self):
        """Get CH2 Marker 2 voltage."""
        return self.driver.get_ch2_marker2_voltage()

    # --- Function Generator and IQ Modulation ---
    def mw_on_sb10MHz(self, enable_iq=False):
        """Turn on microwave output with 10MHz sine wave(s) for IQ modulation."""
        return self.driver.mw_on_sb10MHz(enable_iq)

    def mw_off_sb10MHz(self, enable_iq=False):
        """Turn off microwave output."""
        return self.driver.mw_off_sb10MHz(enable_iq)

    def set_function_generator(self, channel, function='SIN', frequency='10MHz', 
                             voltage=2.0, phase=0.0, enable=True):
        """Configure function generator parameters for a specific channel."""
        return self.driver.set_function_generator(channel, function, frequency, voltage, phase, enable)

    def get_function_generator_status(self, channel):
        """Get current function generator status for a specific channel."""
        return self.driver.get_function_generator_status(channel)

    def enable_iq_modulation(self, frequency='10MHz', voltage=2.0):
        """Enable I/Q modulation with sine and cosine waves."""
        return self.driver.enable_iq_modulation(frequency, voltage)

    def disable_iq_modulation(self):
        """Disable I/Q modulation by setting both channels to 0V."""
        return self.driver.disable_iq_modulation()

    def read_probes(self, key):
        if key == 'status':
            return self.driver.send_command('*STB?', query=True)
        raise KeyError(f"Unknown probe '{key}'")

    def cleanup(self):
        """Clean up resources and mark device as disconnected."""
        if self._ftp_thread and self._ftp_thread.isRunning():
            self._ftp_thread.quit()
            self._ftp_thread.wait()
        if hasattr(self, 'driver'):
            self.driver.cleanup()
        self._is_connected = False
        self.logger.info("AWG520 device disconnected")

    def reconnect(self):
        """Attempt to reconnect to the AWG520 device."""
        try:
            self.logger.info("Attempting to reconnect to AWG520...")
            # Recreate driver instance
            cfg = self.settings
            self.driver = AWG520Driver(
                ip_address=cfg['ip_address'],
                scpi_port=cfg['scpi_port'],
                ftp_port=cfg['ftp_port'],
                ftp_user=cfg['ftp_user'],
                ftp_pass=cfg['ftp_pass']
            )
            # Test connection
            self._test_connection()
            if self.is_connected:
                self.logger.info("Successfully reconnected to AWG520")
                return True
            else:
                self.logger.error("Failed to reconnect to AWG520")
                return False
        except Exception as e:
            self.logger.error(f"Reconnection failed: {e}")
            self._is_connected = False
            return False
