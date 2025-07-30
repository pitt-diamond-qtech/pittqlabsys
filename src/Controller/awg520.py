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
import numpy as np
import logging
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

    def setup(self):
        cfg = self.settings
        seq = cfg['seq_file']
        self.driver.set_ref_clock(1, 'EXT')
        self.driver.set_ref_clock(2, 'EXT')
        time.sleep(0.1)
        self.driver.send_command('AWGC:RMOD ENH')
        time.sleep(0.1)
        self._start_file_transfer(seq)

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

    def read_probes(self, key):
        if key == 'status':
            return self.driver.send_command('*STB?', query=True)
        raise KeyError(f"Unknown probe '{key}'")

    def cleanup(self):
        if self._ftp_thread and self._ftp_thread.isRunning():
            self._ftp_thread.quit()
            self._ftp_thread.wait()
        self.driver.cleanup()
