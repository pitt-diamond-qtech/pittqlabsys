# Created by Jannet Trabelsi <jat332@pitt.edu> on 2025-11-12
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
# Please note: this code does not include the digitizer commands (please refer to programming manual chapters 10 and 11 for these commands
import os
import sys
import struct
srcpath = os.path.realpath(r'C:\Users\Duttlab\Downloads\PythonExamples\Examples\SourceFiles')
sys.path.append(srcpath)
from teproteus import TEProteusAdmin as TepAdmin
from tevisainst import TEVisaInst
import matplotlib.pyplot as plt
import numpy as np
import socket
import time
import numpy as np
import logging
from pathlib import Path
from ftplib import FTP
from src.core import Parameter, Device
from PyQt5.QtCore import QThread, pyqtSignal, QObject

_DAC_BITS = 10
_IP_ADDRESS = '192.168.2.4'
_PORT = 5025
_MW_S1 = 'S1'  # disconnected for now
_MW_S2 = 'S2'  # channel 1, marker 1
_GREEN_AOM = 'Green'  # ch1, marker 2
_ORANGE_AOM = 'orange'  # ch2, marker 1
_ADWIN_TRIG = 'Measure'  # ch2, marker 2
_WAVE = 'Wave'  # channel 1 and 2, analog I/Q data
_DAC_UPPER = 1024.0  # DAC has only 1024 levels
_DAC_MID = 512
_WFM_MEMORY_LIMIT = 1048512  # at most this many points can be in a waveform
_SEQ_MEMORY_LIMIT = 8000
# unit conversion factors
_GHz = 1.0e9  # Gigahertz
_MHz = 1.0e6  # Megahertz
_us = 1.0e-6  # Microseconds
_ns = 1.0e-9  # Nanoseconds
_SID = 6

class ProteusDriver:
    """
    Low-level service for Proteus. Handles SCPI commands over TCP
    """

    def __init__(self, ip_address: str, port: int = _PORT, sid = _SID):
        self.addr = (ip_address)
        self.admin = None
        self.sid = sid
        self.port = port
        self.model_name = None
        self.chan_list = None
        self.segm_list = None
        self.sampling_rate = None
        self.options = None
        self.logger = logging.getLogger(__name__)
        self.paranoia_level = 2  # 0, 1 or 2
        self.num_of_channels = 0
        self._connect()

    def _connect(self):
        try:
            self.admin = TepAdmin()  # required to control PXI module
            self.inst = self.admin.open_instrument(slot_id=self.sid)
            resp = self.inst.send_scpi_query("*IDN?")  # Get the instrument's *IDN
            print('connected to: ' + resp)  # Print *IDN
            # if using LAN (slower)
            """inst_addr = 'TCPIP::'+self.addr+'::'+str(self.port)+'::'+'SOCKET'
            self.inst = TEVisaInst(inst_addr)"""
            resp = self.inst.send_scpi_query("*IDN?")
            print('Connected to: ' + resp)  # print insturmrnt ID
            self.logger.info('Proteus connection successful')
            self.inst.send_scpi_cmd('*CLS; *RST')
            self.options = self.get_options()
            self.model_name = self.identify_model()
            self.sampling_rate = self.get_sampling_rate()
            self.interpol = 1
            self.dac_mode = 16
            if (self.sampling_rate / self.interpol) > 2.5E9:
                self.dac_mode = 8
                self.interpol = 1
            if (self.sampling_rate / self.interpol) < 250E6:
                self.interpol = 1
            self.granul = self.get_granularity(self.dac_mode)
            self.chan_list, self.segm_list = self.get_channels(self.model_name, self.sampling_rate/self.interpol)
            self.num_of_channels = len(self.chan_list)
            print(f'Number of channels: {self.num_of_channels} interpol {self.interpol} dac mode {self.dac_mode} granul {self.granul}')
            #self.calculate_wfms()
        except Exception as e:
            self.logger.error(f'Proteus connection failed: {e}')
            raise

    def calculate_wfms(self):
        minCycles = 1
        period = 1E-7
        if self.interpol > 1:
            self.inst.send_scpi_cmd(':FREQ:RAST 1.25E9')
            self.inst.send_scpi_cmd(f':INT X {self.interpol}')
        self.inst.send_scpi_cmd(f':FREQ:RAST {self.sampling_rate}')
        wfmVolt = 0.5
        wfmOff = 0.0
        mkrVolt = 1.0
        mkrOff = 0.5
        for channel in range(1, self.num_of_channels + 1):
            if channel % 4 == 1:
                myWfm = self.get_square_wfm(
                    self.sampling_rate / self.interpol,
                    minCycles,
                    period,
                    self.granul
                )
            mkrDiv = 2
            if self.dac_mode == 8:
                mkrDiv = 8
            import numpy as np
            myMkr1 = np.zeros(int(len(myWfm) / mkrDiv), dtype=np.uint8)
            myMkr1[0:channel] = np.uint8(1)
            myMkr2 = np.random.rand(len(myMkr1))
            myMkr2 = (myMkr2 > 0.5).astype(np.uint8)
            myMkr = self.format_mkr2(self.dac_mode, myMkr1, myMkr2)
            self.inst.send_scpi_cmd(f':INST:CHAN {self.chan_list[channel-1]}')
            self.inst.send_scpi_cmd(':SOUR:MODE DIRECT')
            if self.segm_list[channel-1] == 1:
                self.inst.send_scpi_cmd(':TRAC:DEL:ALL')
            print(f'DOWNLOADING WAVEFORM FOR CH{self.chan_list[channel-1]}')

            self.send_wfm_to_proteus(
                self.sampling_rate,
                self.chan_list[channel-1],
                self.segm_list[channel-1],
                myWfm,
                self.dac_mode,
                False
            )
            result = self.send_mkr_to_proteus(myMkr)
            print('WAVEFORM DOWNLOADED!')
            print('SETTING AWG OUTPUT')
            self.inst.send_scpi_cmd(f':SOUR:FUNC:MODE:SEGM {self.segm_list[channel-1]}')
            self.inst.send_scpi_cmd(f':SOUR:VOLT {wfmVolt}')
            self.inst.send_scpi_cmd(f':SOUR:VOLT:OFFS {wfmOff}')
            self.inst.send_scpi_cmd(':OUTP ON')
            # Marker 1
            self.inst.send_scpi_cmd(':MARK:SEL 1')
            self.inst.send_scpi_cmd(f':MARK:VOLT:PTOP {mkrVolt}')
            self.inst.send_scpi_cmd(f':MARK:VOLT:OFFS {mkrOff}')
            self.inst.send_scpi_cmd(':MARK ON')
            # Marker 2
            self.inst.send_scpi_cmd(':MARK:SEL 2')
            self.inst.send_scpi_cmd(f':MARK:VOLT:PTOP {mkrVolt}')
            self.inst.send_scpi_cmd(f':MARK:VOLT:OFFS {mkrOff}')
            self.inst.send_scpi_cmd(':MARK ON')
            if channel % 4 < 3:
                myWfm = np.cumsum(myWfm)
                myWfm = myWfm - np.mean(myWfm)
                myWfm = myWfm / np.max(np.abs(myWfm))

    def reset(self):
        self.send_command('*RST')
        self.send_command('*CLS')

    def get_voltage_range(self):
        """The RANGe? query will return the legal range of the accepted values of the numeric parameter
        used in the command. The response format is min value, max value, default value."""
        return self.send_command('VOLT RANG?', query = True)

    def get_minimum_voltage(self):
        """The MIN? query will return the legal minimum accepted value of the numeric parameter used in
        the command. The response format is min value."""
        return self.send_command('VOLT MIN?', query = True)

    def get_maximum_voltage(self):
        """The MAX? query will return the legal maximum accepted value of the numeric parameter used in
        the command. The response format is max value."""
        return self.send_command('VOLT MAX?', query = True)

    def get_default_voltage(self):
        """The DEF? query will return the default value of the numeric parameter used in the command. The
        response format is default value."""
        return self.send_command('VOLT DEF?', query = True)

    def configure_sampling_mode(self, target_sampling_rate):
        """
        Auto-configure DAC mode and interpolation based on target sampling rate.
        Returns: (dac_mode, interpol, actual_sampling_rate, baseband_rate)
        """
        # Initial assumptions
        interpol = 1
        dac_mode = 16

        # Calculate baseband rate (before interpolation)
        baseband_rate = target_sampling_rate / interpol
        if target_sampling_rate <= 2500000000:
            interpol = 1
            baseband_rate = target_sampling_rate
        # KEY DECISION: Determine DAC mode and interpolation
        if baseband_rate > 2.5e9:
            # For high rates: 8-bit mode, no interpolation
            dac_mode = 8
            interpol = 1
            baseband_rate = target_sampling_rate
        elif baseband_rate <= 250e6:
            # For low rates: no interpolation needed
            interpol = 1
            baseband_rate = target_sampling_rate

        # Get model-specific granularity
        granul = self.get_granularity(dac_mode)

        # Get active channels for this configuration
        self.logger.info(f"Sampling Configuration:")
        self.logger.info(f"  Target Rate: {target_sampling_rate / 1e9:.1f} GS/s")
        self.logger.info(f"  DAC Mode: {dac_mode}-bit")
        self.logger.info(f"  Interpolation: x{interpol}")
        self.logger.info(f"  Baseband Rate: {baseband_rate / 1e9:.1f} GS/s")
        self.logger.info(f"  Granularity: {granul} samples")
        self.logger.info(f"  Active Channels: {self.chan_list}")

        return dac_mode, interpol, baseband_rate, granul, self.chan_list, self.segm_list

    def apply_sampling_configuration(self, sampling_rate):
        """
        Apply the sampling configuration to the instrument
        """
        self.send_command(f':FREQ:RAST {sampling_rate}')
        """# Set DAC resolution first
        if dac_mode == 16:
            self.send_command(':TRAC:FORM U16')
        else:
            self.send_command(':TRAC:FORM U8')

        # Configure interpolation and sampling rate
        if interpol > 1:
            # Set base rate and enable interpolation
            self.send_command(':FREQ:RAST 2.5E9')
            self.send_command(f':INT X{interpol}')
        else:
            # Disable interpolation and set final rate directly
            #self.send_command(':INT OFF')
            self.send_command(f':FREQ:RAST {sampling_rate}')"""

    def get_options(self):
        """
        Get instrument options
        """
        try:
            opt_str = self.send_command('*OPT?', query=True).strip()
            return opt_str.split(',')
        except RuntimeError as e:
            if "illegal/unknown scpi" in str(e) or "209" in str(e):
                # *OPT? not supported - return empty options
                self.logger.warning("*OPT? command not supported by this instrument, returning empty options")
                return []
            else:
                # Re-raise other errors
                raise

    def get_num_of_channels(self):
        model = self.model_name
        if '9082' in model or '9482' in model or '1282' in model or '2582' in model:
            return 2
        elif '9086' in model or '9486' in model or '1286' in model or '2586' in model:
            return 6
        elif '9488' in model or '1288' in model or '2588' in model:
            return 8
        elif '94812' in model or '12812' in model or '25812' in model:
            return 12
        return 4

    def set_device_timeout(self, timeout):
        self.inst.timeout = timeout

    def identify_model(self):
        idn = self.inst.send_scpi_query('*IDN?') # another option :SYST:INF:MOD?
        idn = self._net_str_to_str(idn).strip()
        parts = idn.split(',')
        if len(parts) > 1:
            self.model = parts[1]
        else:
            self.model = ''
        return self.model

    def send_command(self, cmd: str, query: bool = False, timeout: float = 5.0):
        """
        Unified SCPI command/query interface for Proteus.
        """

        # --- Send & get result ---
        if query:
            resp = self.inst.send_scpi_query(cmd)
            resp = self._net_str_to_str(resp).strip()
        else:
            self.inst.send_scpi_cmd(cmd)
            resp = None

        # --- Paranoia Controls (debug only) ---
        if self.paranoia_level == 1:
            # Force sync
            self.inst.send_scpi_query('*OPC?')

        elif self.paranoia_level == 2:
            # Query SCPI error queue
            err = self.inst.send_scpi_query('SYST:ERR?')
            err = self._net_str_to_str(err).strip()
            if not err.startswith('0'):
                raise RuntimeError(f"Instrument SCPI Error: {err}")
        return resp
        
    def get_channels(self, model, sampleRate):
        """Mirror GetChannels MATLAB function. Returns (chanList, segmList) as Python lists."""
        chanList = []
        segmList = []
        if ('P9484' in model) or ('P2584' in model) or ('P1284' in model):
            if sampleRate <= 2.5e9:
                chanList = [1,2,3,4]
                segmList = [1,2,1,2]
            else:
                chanList = [1,3]
                segmList = [1,1]
        elif ('P9482' in model) or ('P2582' in model) or ('P1282' in model):
            if sampleRate <= 2.5e9:
                chanList = [1,2]
                segmList = [1,2]
            else:
                chanList = [1]
                segmList = [1]
        elif ('P9488' in model) or ('P2588' in model) or ('P1288' in model):
            if sampleRate <= 2.5e9:
                chanList = [1,2,3,4,5,6,7,8]
                segmList = [1,2,1,2,1,2,1,2]
            else:
                chanList = [1,3,5,7]
                segmList = [1,1,1,1]
        elif ('P94812' in model) or ('P25812' in model) or ('P12812' in model):
            if sampleRate <= 2.5e9:
                chanList = [1,2,3,4,5,6,7,8,9,10,11,12]
                segmList = [1,2,1,2,1,2,1,2,1,2,1,2]
            else:
                chanList = [1,3,5,7,9,11]
                segmList = [1,1,1,1,1,1]
        elif 'P9082' in model:
            chanList = [1,2]
            segmList = [1,1]
        elif 'P9084' in model:
            chanList = [1,2,3,4]
            segmList = [1,1,1,1]
        elif 'P9086' in model:
            chanList = [1,2,3,4,5,6]
            segmList = [1,1,1,1,1,1]
        return chanList, segmList

    def write_binary_data(self, prefix, data_bytes):
        """Wrap inst.WriteBinaryData(prefix, data) call expecting the same return structure"""
        # In MATLAB: res = inst.WriteBinaryData(prefix, myWfm); assert(res.ErrCode == 0)
        res = self.inst.WriteBinaryData(prefix, data_bytes)
        """if hasattr(res, 'ErrCode'):
            if res.ErrCode != 0:
                raise RuntimeError(f"WriteBinaryData failed ErrCode={res.ErrCode}")"""
        if res != 0:
            raise RuntimeError(f"WriteBinaryData failed with errorCode={res}")
        return res

    def get_min_sampling_rate(self):
        return float(self.send_command(':FREQ:RAST MIN?').strip())

    def get_max_sampling_rate(self):
        return float(self.send_command(':FREQ:RAST MAX?').strip())

    def get_granularity(self, dac_mode=16):
        flag_low = False
        for opt in self.options:
            if 'G1' in opt or 'G2' in opt:
                flag_low = True
        granul = 32
        model = self.model_name
        if 'P258' in model:
            granul = 32
            if flag_low:
                granul = 16
        elif '128' in model:
            granul = 32
            if flag_low:
                granul = 16
        elif 'P948' in model:
            if dac_mode ==16:
                granul = 32
                if flag_low:
                    granul = 16
            else:
                granul = 64
                if flag_low:
                    granul = 32
        elif 'P908' in model:
            granul = 64
            if flag_low:
                granul = 32
        else:
            raise ValueError
        return granul

    def get_dac_resolution(self):
        res = self.send_command(':TRAC:FORM?').strip()
        if 'U8' in res:
            return 8
        return 16
    
    def my_quantization(self, arr, dacRes, minLevel=0):
        maxLevel = (2 ** dacRes) - 1
        numOfLevels = maxLevel - minLevel + 1
        # MATLAB: retval = round((numOfLevels .* (myArray + 1) - 1) ./ 2);
        retval = np.round((numOfLevels * (arr + 1.0) - 1.0) / 2.0).astype(np.int64)
        retval = retval + minLevel
        retval[retval > maxLevel] = maxLevel
        retval[retval < minLevel] = minLevel
        return retval
    
    def get_square_wfm(self, samplingRate, numCycles, period, granularity):
        # MATLAB:
        # wfmLength = round(numCycles * period * samplingRate);
        # wfmLength = round(wfmLength / granularity) * granularity;
        wfmLength = int(round(numCycles * period * samplingRate))
        wfmLength = int(round(wfmLength / granularity) * granularity)
        if wfmLength <= 0:
            wfmLength = granularity
        period_samples = wfmLength / numCycles
        idx = np.arange(0, wfmLength)
        # square(sqrWfm * 2 * pi / period) in MATLAB -> use sign(sin(.))
        sqrWfm = np.sign(np.sin(2.0 * np.pi * idx / period_samples))
        # MATLAB's square returns -1..1; ensure same dtype
        return sqrWfm

    def format_mkr2(self, dac_Mode, mkr1, mkr2):
        # mkr1 and mkr2 are arrays of 0/1 ints
        # MATLAB: mkrData = mkr1 + 2 * mkr2;
        mkr1 = np.asarray(mkr1, dtype=np.uint8)
        mkr2 = np.asarray(mkr2, dtype=np.uint8)
        mkrData = mkr1 + 2 * mkr2
        if dac_Mode == 16:
            # MATLAB: pack pairs: mkrData(1:2:end) + 16 * mkrData(2:2:end)
            a = mkrData[0::2]
            b = mkrData[1::2]
            # if odd length, MATLAB would drop final unmatched element in the indexing behavior
            minlen = min(len(a), len(b))
            packed = (a[:minlen].astype(np.uint8) + (16 * b[:minlen].astype(np.uint8)))
            return packed
        else:
            return mkrData.astype(np.uint8)

    def format_mkr4(self, dac_Mode, m1, m2, m3, m4):
        m1 = np.asarray(m1, dtype=np.uint8)
        m2 = np.asarray(m2, dtype=np.uint8)
        m3 = np.asarray(m3, dtype=np.uint8)
        m4 = np.asarray(m4, dtype=np.uint8)
        mkrData = m1 + 2*m2 + 4*m3 + 8*m4
        if dac_Mode == 16:
            a = mkrData[0::2]
            b = mkrData[1::2]
            minlen = min(len(a), len(b))
            packed = (a[:minlen].astype(np.uint8) + (16 * b[:minlen].astype(np.uint8)))
            return packed
        else:
            return mkrData.astype(np.uint8)

    def send_wfm_to_proteus(self, samplingRate, channel, segment, myWfm, dacRes, initialize=False):
        try:
            print(f"=== Waveform Download Debug ===")
            print(f"Channel: {channel}, Segment: {segment}, DAC Mode: {dacRes}")
            print(f"Input waveform length: {len(myWfm)}, dtype: {myWfm.dtype}")
            """if dacRes == 16:
                self.inst.send_scpi_cmd(':TRAC:FORM U16')
            else:
                self.inst.send_scpi_cmd(':TRAC:FORM U8')"""
            # Channel selection
            """if initialize:
                self.send_command(':TRAC:DEL:ALL')
                self.send_command(':FREQ:RAST {0}'.format(samplingRate))"""
            print("setting channel")
            cmd = ':INST:CHAN {0}'.format(channel)
            self.inst.send_scpi_cmd(cmd)
            cmd = ':FREQ:RAST {0}'.format(samplingRate)
            self.inst.send_scpi_cmd(cmd)
            cmd = ':TRAC:DEL:ALL'  # Clear CH Memory
            self.inst.send_scpi_cmd(cmd)
            cmd = ':INIT:CONT ON'  # play waveform continuously
            self.inst.send_scpi_cmd(cmd)
            segnum = segment
            cmd = ':TRAC:DEF {0}, {1}'.format(segnum, len(myWfm))  # memory location and length
            self.inst.send_scpi_cmd(cmd)
            # Select the segment
            cmd = ':TRAC:SEL {0}'.format(segnum)
            self.inst.send_scpi_cmd(cmd)
            # Sometimes waveforms can be very large so its good practice to increase the instrument timeout length, before downloading the date.

            self.inst.timeout = 30000  # increase
            self.inst.write_binary_data('*OPC?; :TRAC:DATA', myWfm)  # write, and wait while *OPC completes
            self.inst.timeout = 10000  # return to normal

            # The instrument now has a waveform stored in its internal segment memory location number 1. The next step is to play it out. This is simply done by selecting segment and switching the instruments output on.

            cmd = ':FUNC:MODE:SEGM {0}'.format(segnum)
            self.inst.send_scpi_cmd(cmd)
            cmd = ':OUTP ON'
            rc = self.inst.send_scpi_cmd(cmd)
            """myWfm = self.my_quantization(myWfm, dacRes, 0)"""
            print(f"Waveform download successful")
            result = len(myWfm)
            return result
        except Exception as e:
            print(f"Error in waveform download: {e}")
            # Try to get instrument error
            try:
                error = self.send_command(':SYST:ERR?', query=True)
                print(f"Instrument error: {error}")
            except:
                pass
            return 0

    def send_mkr_to_proteus(self, myMkr):
        """Fixed marker download using write_binary_data"""
        try:
            prefix = ':MARK:DATA 0,'
            # Ensure myMkr is bytes
            if isinstance(myMkr, np.ndarray):
                data_bytes = myMkr.tobytes()
            elif isinstance(myMkr, (bytes, bytearray)):
                data_bytes = bytes(myMkr)
            else:
                data_bytes = bytes(myMkr)
            # Use the actual write_binary_data method
            self.inst.write_binary_data(prefix, data_bytes)
            return len(data_bytes)
        except Exception as e:
            print(f"Error sending marker to Proteus: {e}")
            return 0

    def debug_tevisa_methods(self):
        """Check available methods on TEVisaInst object"""
        print("Available methods on TEVisaInst:")
        for method_name in dir(self.inst):
            if not method_name.startswith('_'):  # Skip private methods
                print(f"  {method_name}")
        # Check specifically for write methods
        write_methods = [method for method in dir(self.inst) if 'write' in method.lower() or 'send' in method.lower()]
        print(f"\nWrite/Send methods: {write_methods}")

    # --- Clock configuration ---
    def set_clock_external(self):
        """Use this command to select or query the source of the sample clock generator for all channels in
        a Proteus unit. This command affects all of the waveforms, as the internal clock is removed, and
        external clock is applied. Make sure that a valid clock is applied to the external clock input before
        you change the option to external, because the generator cannot generate waveforms without a
        valid source of sample clock generator. Note that the internal sample clock generator is unique
        for each 4-channel group however, when an external clock source is selected, the same source is
        applied to all channels."""
        for ch in (1,2):
            self.send_command(f':INST: CHAN {ch}')
            self.send_command('[:SOUR]:FREQ:SOUR EXT')

    def get_clock_state(self):
        """The Proteus will return INT, or EXT depending on the current sample clock source setting."""
        return self.send_command(f':FREQ:SOUR?', query=True)

    def set_clock_internal(self):
        for ch in (1,2):
            self.send_command(f':INST: CHAN {ch}')
            self.send_command('[:SOUR]:FREQ:SOUR INT')

    def set_sample_clock_output_state(self, state):
        if state not in [0, 1, "ON", "OFF"]:
            raise ValueError(f"Invalid sample clock output state: {state}")
        self.send_command(f':FREQ:OUTP {state}')

    def get_sample_clock_output_state(self):
        return self.send_command(f':FREQ:OUTP?', query=True)

    def set_waveform_type(self, type):
        """Use this command to set or query the type of waveform that will be available at the output
        connector."""
        if type not in ["TASK", "ARB"]:
            raise ValueError(f"Invalid waveform type: {type}")
        self.send_command(f':FUNC:MODE {type}')

    def get_waveform_type(self):
        return self.send_command(f':FUNC:MODE?', query=True)

    def set_segment(self, segment_number):
        """Use this command in case of Arbitrary mode to set or query the active segment to be played back
        for the user generation mode for the channel selected with the :INST:ACT and :INST:CHAN
        commands. The first 128 segment are "Fast-Segments"."""
        if not isinstance(segment_number, int):
            raise ValueError(f"Invalid segment number: {segment_number}")
        if not (1 <= segment_number <= 64000):
            raise ValueError(f"Invalid segment number: {segment_number}")
        self.send_command(f':FUNC:MODE:SEGM {segment_number}')

    def get_segment(self):
        return self.send_command(f':FUNC:MODE:SEGM?', query=True)

    def set_task_number_in_function_mode(self, task_number):
        """Use this command in case of Task-Mode to set or query the initial task to be played back for the
        task generation mode for the channel selected with the :INST:ACT and :INST:CHAN commands."""
        if not isinstance(task_number, int):
            raise ValueError(f"Invalid task number: {task_number}")
        if not (1 <= task_number <= 64000):
            raise ValueError(f"Invalid task number: {task_number}")
        self.send_command(f':FUNC:MODE:TASK {task_number}')

    def get_task_number_in_function_mode(self):
        return self.send_command(f':FUNC:MODE:TASK?', query=True)

    def set_ref_clock_external(self):
        for ch in (1,2):
            self.send_command(f':INST: CHAN {ch}')
            self.send_command('[:SOURce]:ROSC:SOUR EXT')

    def set_ref_clock_internal(self):
        for ch in (1,2):
            self.send_command(f':INST: CHAN {ch}')
            self.send_command('[:SOURce]:ROSC:SOUR INT')

    def get_ref_clock_state(self):
        """The Proteus will return INT, or EXT depending on the present 10 MHz clock reference source
        setting."""
        return self.send_command(f':ROSC:SOUR?', query=True)

    def set_ref_clock_frequency(self, frequency):
        """Use this command to set or query the frequency range that will be applied to the reference
        oscillator input. The frequency value must be close to the value of the external frequency because
        it sets up the PLLs for the reference oscillator to accept and lock on the correct external frequency
        value."""
        if frequency not in ["10M", "100M"]:
            raise ValueError(f"Invalid frequency value: {frequency}")
        self.send_command(f':ROSC:FREQ {frequency}')

    def get_ref_clock_frequency(self):
        return self.send_command(f':ROSC:FREQ?', query=True)

    def set_ref_clock_bypass_state(self, state):
        """Select if the TCXO and the analog output source are synchronized. When the BYPass is set to ON
        the internal DDS is adjusted so that the output frequency accuracy is 1ppm. When it is set to OFF
        there is no adjustment and the accuracy is 2.5ppm.
        OFF: There is no adjustment and the accuracy is 2.5ppm.
        ON: Internal DDS is adjusted so that the output frequency
        accuracy is 1ppm."""
        if state not in ["ON", "OFF"]:
            raise ValueError(f"Invalid ref_clock_bypass_state: {state}")
        self.send_command(f':ROSC:BYP {state}')

    def get_ref_clock_bypass_state(self):
        return self.send_command(f':ROSC:BYP?', query=True)

    def set_voltage(self, voltage):
        """Use this command to set or query the voltage amplitude of the waveform for the currently
        selected channel. The Proteus displays a calibrated value when on load impedance of 50 Ω offset
        and amplitude settings are independent providing that the “offset + amplitude/2” value does not
        exceed the specified voltage window. This command does not apply to the AC output module."""
        if not(isinstance(voltage, (float, int)) or (voltage == 'MAX')):
            raise ValueError(f"Invalid voltage: {voltage}")
        if isinstance(voltage, (float, int)) and not (0.001 <= voltage <= 1.2):
            raise ValueError(f"Invalid voltage: {voltage}")
        self.send_command(f':VOLT {voltage}')

    def get_voltage(self):
        return self.send_command(f':VOLT?', query=True)

    def set_voltage_offset(self, offset):
        """Use this command to set or query the DC offset of the output waveform for the currently selected
        channel. The Proteus unit displays a calibrated value with a load impedance of 50 Ω. Offset and
        amplitude settings are independent providing that the |offset + amplitude| value does not exceed
        the specified amplitude window. This command does not apply to the DIRECT output option as it
        is AC-coupled."""
        if not isinstance(offset, (float, int)):
            raise ValueError(f"Invalid voltage: {offset}")
        if not (-0.5 <= offset <= 0.5):
            raise ValueError(f"Invalid voltage: {offset}")
        self.send_command(f':VOLT:OFFS {offset}')

    def get_voltage_offset(self):
        return self.send_command(f':VOLT:OFFS?', query=True)

    def _close(self):
        self.inst.close_instrument()
        self.admin.close_inst_admin()

    def query_error(self):
        return self.inst.send_scpi_query('SYST:ERR?').rstrip()

    def write_trace_data(self, trace_data):
        self.set_device_timeout(30000)
        self.inst.write_binary_data('*OPC?; :TRAC:DATA', trace_data)
        self.set_device_timeout(10000)

    def write_marker_data(self, marker_data):
        self.set_device_timeout(30000)
        self.inst.write_binary_data('*OPC?; :MARK:DATA', marker_data)
        self.set_device_timeout(10000)

    """def setup_sequence(self, seqfilename: str, enable_iq: bool = False):
        # High-level setup: clocks, enhanced mode, load sequence, set voltages.

        self.set_ref_clock_external()
        time.sleep(0.1)
        # load sequence on both channels
        for ch in (1, 2):
            self.send_command(f'SOUR{ch}:FUNC:USER "{seqfilename}","MAIN"')
            time.sleep(0.1)
        # set default voltages and markers
        for ch in (1, 2):
            self.send_command(f':INST: CHAN {ch}')
            self.send_command(f':SOUR:VOLT 1')
            time.sleep(0.1)
            self.send_command(f':VOLT:OFFS 0')
            time.sleep(0.1)
            for m in (1, 2):
                self.send_command(f':MARK:SEL {m}')
                self.send_command(f':MARK:VOLT:PTOP 2.0')
                self.send_command(f':MARK:VOLT:OFFS 0')
                self.send_command(f':MARK ON')
                time.sleep(0.05)
        # output state
        if enable_iq:
            for ch in (1, 2):
                self.send_command(f':INST: CHAN {ch}')
                self.send_command(':OUTP ON')
                time.sleep(0.1)
        else:
            ch = 1
            self.send_command(f':INST: CHAN {ch}')
            self.send_command(':OUTP ON')
            time.sleep(0.1)"""
            
    def _net_str_to_str(self, net_str):
        """ convert .NET string-like object to python string (mirrors netStrToStr) """
        try:
            return str(net_str)
        except Exception:
            return ''

    def stop(self):
        for ch in self.chan_list:
            self.send_command(f':INST: CHAN {ch}')
            self.inst.send_scpi_cmd(':INIT:CONT OFF')
            self.set_output("OFF")

    def trigger(self):
        self.inst.send_scpi_cmd('*TRG')

    # --- Marker control for laser applications ---
    def set_ch1_marker2_laser_on(self):
        """
        Turn on CH1 Marker 2 for laser control.
        In Proteus, markers use PTOP (amplitude) and OFFS (offset),
        so setting PTOP=0 and OFFS=2.0 produces a constant 2 V output.
        """
        self.logger.info("Turning on CH1 Marker 2 (laser control)")
        self.send_command(':INST:CHAN 1')  # select channel 1
        self.send_command(f':MARK:SEL {2}')
        self.send_command(f':MARK:VOLT:PTOP 0')
        self.send_command(f':MARK:VOLT:OFFS 2.0')
        self.send_command(f':MARK ON')
        time.sleep(0.05)

    def set_ch1_marker2_laser_off(self):
        """
        Turn off CH1 Marker 2 for laser control by setting low level to 0V.
        This effectively disables the laser by setting the marker to a low voltage level.
        """
        self.logger.info("Turning off CH1 Marker 2 (laser control)")
        # Set low level to 0V to turn off the laser
        self.send_command(":INST:CHAN 1")
        self.send_command(f":MARK:SEL {2}")
        self.send_command(":MARK:VOLT:PTOP 0")
        self.send_command(":MARK:VOLT:OFFS 0")

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
        ptop = high_voltage - low_voltage
        offset = (high_voltage + low_voltage)/2
        self.send_command(':INST:CHAN 1')  # select channel 1
        self.send_command(f':MARK:SEL {2}')
        self.send_command(f':MARK:VOLT:PTOP {ptop}')
        self.send_command(f':MARK:VOLT:OFFS {offset}')
        self.send_command(f':MARK ON')

    def get_ch1_marker2_voltage(self):
        """
        Get current CH1 Marker 2 voltage levels.

        Returns:
            tuple: (low_voltage, high_voltage) in volts
        """
        try:
            self.send_command(':INST:CHAN 1')  # select channel 1
            self.send_command(f':MARK:SEL {2}')
            ptop = self.send_command(f':MARK: VOLT:PTOP?', query=True)
            offset = self.send_command(f':MARK: VOLT:OFFS?', query=True)
            low_v = offset - 0.5 * ptop
            high_v = offset + 0.5 * ptop

            if low_v is not None and high_v is not None:
                return (float(low_v), float(high_v))
            else:
                return (None, None)
        except Exception as e:
            self.logger.error(f"Failed to get CH1 Marker 2 voltage: {e}")
            return (None, None)

    def is_ch1_marker2_laser_on(self):
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
        ptop = high_voltage - low_voltage
        offset = (high_voltage + low_voltage) / 2
        self.send_command(':INST:CHAN 1')  # select channel 1
        self.send_command(f':MARK:SEL {1}')
        self.send_command(f':MARK:VOLT:PTOP {ptop}')
        self.send_command(f':MARK:VOLT:OFFS {offset}')
        self.send_command(f':MARK ON')

    def get_ch1_marker1_voltage(self):
        """
        Get current CH1 Marker 1 voltage levels.

        Returns:
            tuple: (low_voltage, high_voltage) in volts
        """
        try:
            self.send_command(':INST:CHAN 1')  # select channel 1
            self.send_command(f':MARK:SEL {1}')
            ptop = self.send_command(f':MARK: VOLT:PTOP?', query=True)
            offset = self.send_command(f':MARK: VOLT:OFFS?', query=True)
            low_v = offset - 0.5 * ptop
            high_v = offset + 0.5 * ptop

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
        ptop = high_voltage - low_voltage
        offset = (high_voltage + low_voltage) / 2
        self.send_command(':INST:CHAN 2')  # select channel 1
        self.send_command(f':MARK:SEL {1}')
        self.send_command(f':MARK:VOLT:PTOP {ptop}')
        self.send_command(f':MARK:VOLT:OFFS {offset}')
        self.send_command(f':MARK ON')

    def get_ch2_marker1_voltage(self):
        """
        Get current CH2 Marker 1 voltage levels.

        Returns:
            tuple: (low_voltage, high_voltage) in volts
        """
        try:
            self.send_command(':INST:CHAN 2')  # select channel 1
            self.send_command(f':MARK:SEL {1}')
            ptop = self.send_command(f':MARK: VOLT:PTOP?', query=True)
            offset = self.send_command(f':MARK: VOLT:OFFS?', query=True)
            low_v = offset - 0.5 * ptop
            high_v = offset + 0.5 * ptop

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
        ptop = high_voltage - low_voltage
        offset = (high_voltage + low_voltage) / 2
        self.send_command(':INST:CHAN 2')  # select channel 1
        self.send_command(f':MARK:SEL {2}')
        self.send_command(f':MARK:VOLT:PTOP {ptop}')
        self.send_command(f':MARK:VOLT:OFFS {offset}')
        self.send_command(f':MARK ON')

    def get_ch2_marker2_voltage(self):
        """
        Get current CH2 Marker 2 voltage levels.

        Returns:
            tuple: (low_voltage, high_voltage) in volts
        """
        try:
            self.send_command(f':INST:CHAN {2}')  # select channel 1
            self.send_command(f':MARK:SEL {2}')
            ptop = self.send_command(f':MARK: VOLT:PTOP?', query=True)
            offset = self.send_command(f':MARK: VOLT:OFFS?', query=True)
            low_v = float(offset) - 0.5 * float(ptop)
            high_v = float(offset) + 0.5 * float(ptop)

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
        self.logger.warning(
            "set_ch2_marker2_laser_off is deprecated. Use set_ch1_marker2_laser_off() for laser control.")
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
        self.set_ch1_marker1_voltage(2.0, 3.0) # originally: low 2.0 (no setting for high)
        time.sleep(0.05)

        if enable_iq:
            # Configure both channels for IQ modulation
            # CH1: Sine wave at 10MHz
            self.set_function_generator(1, 'SIN', 10e6, 2.0) # to be tested
            time.sleep(0.05)

            # CH2: Cosine wave at 10MHz (90° phase shift)
            self.set_function_generator(2, 'SIN', 10e6, 2.0, 90.0) # to be tested
            time.sleep(0.05)

            return 0
        else:
            # Configure only CH1 for single channel output
            self.set_function_generator(1, 'SIN', 10e6, 2.0)  # to be tested
            time.sleep(0.05)

            return 0

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
        self.set_ch1_marker1_voltage(0, 0)
        time.sleep(0.05)

        if enable_iq:
            # Turn off both channels
            self.off()
            time.sleep(0.05)

            return 0
        else:
            # Turn off only CH1
            self.off()
            time.sleep(0.05)
            return 0

    def enable_iq_modulation(self, frequency=10e6, voltage=2.0):
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
        self.set_function_generator(1, 'SIN', frequency, voltage, 0.0, True)

        # Configure CH2 for Q (sine wave, 90° phase)
        self.set_function_generator(2, 'SIN', frequency, voltage, 90.0, True)

        return 0 and 0

    def disable_iq_modulation(self):
        """
        Disable I/Q modulation by setting both channels to 0V.

        Returns:
            bool: True if I/Q modulation was disabled successfully
        """
        self.logger.info("Disabling I/Q modulation")
        # Turn off both channels
        self.off()
        time.sleep(0.05)
        return 0 and 0

    def cleanup(self):
        """Clean up resources and mark device as disconnected."""
        try:
            self.off()
        except:
            pass
        try:
            self.stop()
        except:
            pass

    def get_sampling_rate(self):
        model = self.model_name
        if '1284' in model:
            return 1250000000
        elif '2582' in model:
            return 2500000000
        elif '9082' or '9484' in model:
            return 9000000000
        else:
            raise ValueError(f'no sampling rate provided for model number {model}')

    def set_function_generator(self, channel, function='SIN', frequency=10e6,
                               voltage=1, phase=0.0, enable=True):
        if channel not in self.chan_list:
            self.logger.error(f"Invalid channel: {channel}")
            return False
        self.logger.info(f"Configuring channel {channel}: {function}, {frequency} Hz, {voltage}V, phase={phase}°")
        # AUTO-CONFIGURE sampling mode
        target_sampling_rate = self.get_sampling_rate()  # Model's max rate
        dac_mode, interpol, baseband_rate, granul, chan_list, segm_list = self.configure_sampling_mode(
            target_sampling_rate)
        print(f'dacmode: {dac_mode}')
        print(f'interpol: {interpol}')
        print(f'baseband_rate: {baseband_rate}')
        print(f'granul: {granul}')
        print(f'chan_list: {chan_list}')
        print(f'segm_list: {segm_list}')
        # Check if requested channel is available in this mode
        if channel not in chan_list:
            self.logger.error(f"Channel {channel} not available at {target_sampling_rate / 1e9:.1f} GS/s")
            return False
        segLen = 1024
        # Compute cycles in this segment
        cycles = int(round(frequency * segLen / baseband_rate))  # Use baseband_rate
        time = np.linspace(0, segLen - 1, segLen)
        w = 2 * np.pi * cycles
        phase_rad = np.deg2rad(phase)
        # Waveform generation
        function = function.upper()
        if function == 'SIN':
            dacWave = voltage * np.sin(w * time / segLen + phase_rad)
        elif function == 'SQU':
            dacWave = voltage * np.sign(np.sin(w * time / segLen + phase_rad))
        elif function == 'TRI':
            phase_samp = (phase / 360.0) * segLen
            x = ((time + phase_samp) / segLen) % 1
            dacWave = voltage * 4 * np.abs(x - 0.5) - 1
        elif function == 'RAMP':
            phase_samp = (phase / 360.0) * segLen
            x = ((time + phase_samp) / segLen) % 1
            dacWave = voltage * 2 * x - 1
        elif function == 'NOIS':
            dacWave = voltage * np.random.uniform(-1.0, 1.0, segLen)
        elif function == 'DC':
            dacWave = voltage * np.ones(segLen)
        else:
            self.logger.error(f"Unsupported waveform function: {function}")
            return False
        print('Frequency {0} Hz'.format(baseband_rate * cycles / segLen))
        max_dac = 65535  # Max Dac
        half_dac = max_dac / 2  # DC Level
        data_type = np.uint16  # DAC data type
        dacWave = ((dacWave) + 1.0) * half_dac
        dacWave = dacWave.astype(data_type)
        # Upload to instrument
        try:
            # Use auto-detected DAC mode and target sampling rate
            self.send_wfm_to_proteus(samplingRate=baseband_rate, channel=channel, segment=channel, myWfm=dacWave,
                                     dacRes=dac_mode, initialize=True if enable else False)
            #self.send_command(f":SOUR:VOLT {voltage}")
            print('Done')
            return True

        except Exception as e:
            self.logger.error(f"Failed to set function generator: {e}")
            return False

    def get_function_generator_status(self, channel):
      
        #Get current function generator status for a specific channel.
    
        samplingRate = self.get_sampling_rate()
        chanlist, segmList = self.get_channels(self.model_name, samplingRate)
        if channel not in chanlist:
            self.logger.error(f"Invalid channel: {channel}")
            return None

        try:
            # Query all parameters
            time.sleep(0.05)
            samplingRate = self.get_sampling_rate()
            time.sleep(0.05)
            self.send_command(f':INST:CHAN {channel}')
            voltage = self.get_voltage()
            time.sleep(0.05)
            time.sleep(0.05)

            if all([samplingRate, voltage]):
                return {
                    'sampling Rate': samplingRate,
                    'voltage': float(voltage),
                }
            else:
                return None

        except Exception as e:
            self.logger.error(f"Failed to get FG{channel} status: {e}")
            return None

    def activate_instrument(self, instrument_number):
        """This command will set the active Proteus Module for future programming command sequences.
        Subsequent commands affect the selected Proteus Module only. 0 is the chassis"""
        if instrument_number not in [0,1,2]:
            raise ValueError(f"Invalid instrument number: {instrument_number}")
        self.send_command(f':INST:ACT {instrument_number}')

    def get_active_instrument(self):
        return self.send_command(':INST:ACT?', query=True)

    def set_channel(self, channel_number):
        """This command will set the active channel (for a given module) or device (for standalone devices)
        for future programming command sequences. Subsequent commands affect the selected channel
        only."""
        if channel_number not in self.chan_list:
            raise ValueError(f"Invalid channel number: {channel_number}")
        self.send_command(f':INST: CHAN {channel_number}')

    def get_channel(self):
        return self.send_command(':INST:CHAN?', query=True)

    def set_continuous_run(self, state):
        """This command defines the continuous run mode of the instrument. This command does not
        activate the trigger sources, which must be set up and activated using additional commands.
        The figure below depicts a standard trigger with a minimum instrument delay (additional user
        defined delay can be added). """
        if state not in [0,1]:
            raise ValueError(f"Invalid state: {state}")
        self.send_command(f':INIT:CONT {state}')

    def get_continuous_run_state(self):
        return self.send_command(':INIT:CONT?', query=True)

    def set_trigger_coupling(self, state):
        """This command defines the trigger coupling between synchronized modules. When set to ON all
        synchronized modules will receive the trigger from the master module trigger 1. Use this when
        you would like all units to receive the trigger from a common trigger input. For example, in a
        Desktop or Benchtop multi-channel unit when the trigger couple is set to ON all channels will
        receive the trigger from TRIG1."""
        if state not in [0, 1, "OFF", "ON"]:
            raise ValueError(f"Invalid state: {state}")
        self.send_command(f':TRIG:COUP {state}')

    def set_trigger_source(self, trigger):
        """Use this command to set or query the source of the trigger enable signal. The trigger inputs in the
        front panel are associated to a specific output channel depending on the Proteus model. Refer to
        the table “Effected Channels” below.
        Parameters
        Name    Type        Default     Description
        <NONE> Discrete     NONE        No source of the enable signal.
        <TRG1> Discrete                 Trigger input 1
        <TRG2> Discrete                 Trigger input 2
        <TRG3> Discrete                 Trigger input 3
        <TRG4> Discrete                 Trigger input 4
        <TRG5> Discrete                 Trigger input 5
        <TRG6> Discrete                 Trigger input 6
        <INTernal> Discrete             Internal trigger
        <CPU>   Discrete                Bus
        <FBTgR> Discrete                Feedback trigger. Relevant for AWT digitizer option.
        <HWControl> Discrete            Dynamic jump connector."""
        if trigger not in ["NONE", "TRG1", "TRG2", "TRG3", "TRG4", "TRG5", "TRG6", "INT", "CPU", "FBT", "HWC"]:
            raise ValueError(f"Invalid signal: {trigger}")
        if (trigger == "TRG3" or trigger == "TRG4") and (not "P1288D" in self.model or not "P12812D" in self.model or not "P2588D" in self.model or not "P25812D" in self.model or not "P1288B" in self.model or not "P12812B" in self.model or not "P2588B" in self.model or not "P25812B" in self.model or not "P9084D" in self.model or not "P9086D" in self.model or not "P9084B" in self.model or not "P9086B" in self.model):
            raise ValueError(f"Invalid signal: {trigger} for model {self.model}")
        if (trigger == "TRG5" or trigger == "TRG6") and (not "P12812D" in self.model or not "P25812D" in self.model or not "P12812B" in self.model or not "P25812B" in self.model or not "P9086D" in self.model or not "P9086B" in self.model):
            raise ValueError(f"Invalid signal: {trigger} for model {self.model}")
        self.send_command(f':TRIG:SOUR:ENAB {trigger}')

    def get_trigger_source(self):
        return self.send_command(f':TRIG:SOUR:ENAB?', query=True)

    def set_abort_source_signal(self, signal):
        """Use this command to set or query the source of the trigger disable (abort) signal."""
        if signal not in ["NONE", "TRIG1", "TRIG2", "TRIG3", "TRIG4", "TRIG5", "TRIG6", "INT", "CPU", "FBTR", "HWC"]:
            raise ValueError(f"Invalid signal: {signal}")
        if (signal == "TRIG3" or signal == "TRIG4") and (not "P1288D" in self.model or not "P12812D" in self.model or not "P2588D" in self.model or not "P25812D" in self.model or not "P1288B" in self.model or not "P12812B" in self.model or not "P2588B" in self.model or not "P25812B" in self.model or not "P9084D" in self.model or not "P9086D" in self.model or not "P9084B" in self.model or not "P9086B" in self.model):
            raise ValueError(f"Invalid signal: {signal} for model {self.model}")
        if (signal == "TRIG5" or signal == "TRIG6") and (not "P12812D" in self.model or not "P25812D" in self.model or not "P12812B" in self.model or not "P25812B" in self.model or not "P9086D" in self.model or not "P9086B" in self.model):
            raise ValueError(f"Invalid signal: {signal} for model {self.model}")
        self.send_command(f':TRIG:SOUR:DIS {signal}')

    def get_abort_source_signal(self):
        return self.send_command(f':TRIG:SOUR:DIS?', query=True)

    def select_next_trigger_source(self, signal):
        """Select the trigger source as the target for the next related SCPI commands setup."""
        if signal not in ["TRIG1", "TRIG2", "TRIG3", "TRIG4", "TRIG5", "TRIG6", "INT"]:
            raise ValueError(f"Invalid signal: {signal}")
        if (signal == "TRIG3" or signal == "TRIG4") and (not "P1288D" in self.model or not "P12812D" in self.model or not "P2588D" in self.model or not "P25812D" in self.model or not "P1288B" in self.model or not "P12812B" in self.model or not "P2588B" in self.model or not "P25812B" in self.model or not "P9084D" in self.model or not "P9086D" in self.model or not "P9084B" in self.model or not "P9086B" in self.model):
            raise ValueError(f"Invalid signal: {signal} for model {self.model}")
        if (signal == "TRIG5" or signal == "TRIG6") and (not "P12812D" in self.model or not "P25812D" in self.model or not "P12812B" in self.model or not "P25812B" in self.model or not "P9086D" in self.model or not "P9086B" in self.model):
            raise ValueError(f"Invalid signal: {signal} for model {self.model}")
        self.send_command(f':TRIG:ACTIVE:SEL {signal}')

    def get_next_trigger_source(self):
        return self.send_command(f':TRIG:ACTIVE:SEL?', query=True)

    def set_trigger_state(self, state):
        """Enable / disable the selected external trigger (as designated by the :TRG:SEL command)). Enabling
        the trigger source is mandatory as just selecting a given trigger source will not activate the
        selected source."""
        if state not in [0, 1, "OFF", "ON"]:
            raise ValueError(f"Invalid state: {state}")
        self.send_command(f':TRIG:STAT {state}')

    def get_trigger_state(self):
        return self.send_command(f':TRIG:STAT?', query=True)

    def set_cpu_trigger_mode(self, mode):
        """When using the CPU trigger the user can select between LOCAL mode where only the active
        channel receives the CPU trigger or GLOBAL where all channels receive the same CPU trigger
        simultaneously."""
        if mode not in ["LOCAL", "GLOBAL"]:
            raise ValueError(f"Invalid mode: {mode}")
        self.send_command(f':TRIG:CPU:MODE {mode}')

    def get_cpu_trigger_mode(self):
        return self.send_command(f':TRIG:CPU:MODE?', query=True)

    def set_trigger_gate_state(self, state):
        """Enable or disable Gated-Mode of the selected external trigger (channel dependent). (Internal
        trigger has no gate mode, so its gate mode is only OFF.)
        The figure below depicts that the gating signal will for “Jump Eventually” initiate the playing of
        the whole segment, while for “Jump Immediate” only play the segment that fits in the Gating
        Signal time length.
        0 – Disable the gated run mode.
        1 – Enable the gated run mode. The gated run mode
        should only be selected if continuous run mode is off
        otherwise it has no effect on the current run mode.
        The gating signal is applied to the trigger input only
        and output waveforms will be generated only when
        the gate signal is valid and true. The slope and level of
        the gating entry are programmable."""
        if state not in [0, 1, "OFF", "ON"]:
            raise ValueError(f"Invalid state: {state}")
        self.send_command(f':TRIG:GATE {state}')

    def get_trigger_gate_state(self):
        return self.send_command(f':TRIG:GATE?', query=True)

    def set_trigger_level(self, level):
        """Use this command to set or query the trigger level setting for a given trigger input selected
        through the :TRIG:SEL command and for the channel defined by the :INST command. This
        command is effective only when the Proteus unit is programmed to operate in triggered run mode
        (:INIT:CONT 0). The external Trigger Source must be activated using the :TRIG:STAT ON command
        to actually produce a trigger event for the associated channel/s."""
        if not isinstance(level, (int, float)):
            raise ValueError("error: level must be a number")
        if not (-5 <= level <= 5):
            raise ValueError("error: level out of range")
        self.send_command(f':TRIG:LEV {level}')

    def get_trigger_level(self):
        return self.send_command(f':TRIG:LEV?', query=True)

    def set_trigger_count(self, cycles):
        """Use this command to set or query the cycles counter setting for a given trigger input selected
        through the :TRIG:SEL command and for the channel defined by the :INST command. This
        command is effective only when the Proteus unit is programmed to operate in triggered run mode
        (INIT:CONT 0). The command defines the number of times the current segment will be played for
        a given trigger signal.
        Programs the burst count. Following a
        valid trigger signal, the Proteus generates
        a pre-programmed number of waveform
        cycles and then resumes an idle state. The
        counted burst can be initiated using one
        of the following:
        • Front panel Man Trigger push button
        • Remote command such as *TRG
        • A transition at any of the trigger input
        connectors."""
        if not isinstance(cycles, int):
            raise ValueError("error: cycles must be a number")
        if not (0 <= cycles <= 1000000):
            raise ValueError("error: cycles out of range")
        self.send_command(f':TRIG:COUN {cycles}')

    def get_trigger_count(self):
        return self.send_command(f':TRIG:COUN?', query=True)

    def set_trigger_width(self, width):
        """Use this command to set or query the trigger width value for a given trigger input selected
        through the :TRIG:SEL command and a given channel selected by the :INST command. Trigger
        signal having a pulse width below the programmed settings will not trigger the unit. Width is
        measured according to the threshold level set up by the :TRIG:LEV command and it refers to the
        pulse duration over the threshold level."""
        if not isinstance(width, (int, float)):
            raise ValueError("error: delay must be a number")
        if not (0.000000001 <= width <= 2):
            raise ValueError(f"Invalid width: {width}")
        self.send_command(f':TRIG:WIDT {width}')

    def get_trigger_width(self):
        return self.send_command(f':TRIG:WIDT?', query=True)

    def set_trigger_slope(self, slope):
        """Use this command to define or query the valid slope for the Proteus trigger input selected through
        the :TRIG:SEL command and a given channel selected by the :INST command. You can choose
        between positive (up) and negative (down) independently for each trigger input."""
        if slope not in ["POS", "NEG"]:
            raise ValueError(f"Invalid slope: {slope}")
        self.send_command(f':TRIG:SLOP {slope}')

    def get_trigger_slope(self):
        return self.send_command(f':TRIG:SLOP?', query=True)

    def set_trigger_timer(self, time):
        """Use this command to set or query the period of the internal timed trigger generator. This value is
        associated with the internal trigger run mode only and has no effect on other trigger modes. The
        internal trigger generator is a free-running oscillator, asynchronous with the frequency of the
        output waveform. The timer intervals are measured from waveform start to waveform start."""
        if not isinstance(time, (int, float)):
            raise ValueError(f"Invalid time: {time}")
        if not (2 <= time <= 200000000000):
            raise ValueError(f"Invalid time: {time}")
        self.send_command(f':TRIG:TIM {time}')

    def get_trigger_timer(self):
        return self.send_command(f':TRIG:TIM?', query=True)

    def set_double_trigger_delay(self, delay):
        """This is a double trigger command. When executed, the command sends two triggers with a time
        delay between them equal to the value sent by the user. Minimum is 1 μs and maximum is
        65536 μs in units of μs."""
        if not isinstance(delay, (int, float)):
            raise ValueError(f"Invalid delay: {delay}")
        if not (0 <= delay <= 65536):
            raise ValueError(f"Invalid delay: {delay}")
        self.send_command(f':TRIG:DOUB {delay}')

    def get_double_trigger_delay(self):
        return self.send_command(f':TRIG:DOUB?', query=True)

    def set_abort_trigger_mode(self, mode):
        """Use this command to define or query the DISABLE (ABORT) trigger mode. In the EVENtually mode,
        the trigger aborts the generation of the selected segment as soon as the current loop is
        completed. In the IMMediate mode, the generation of the selected segment is aborted as soon
        as possible without waiting for the end of the current loop."""
        if mode not in ["EVEN", "IMM"]:
            raise ValueError(f"Invalid mode: {mode}")
        self.send_command(f':TRIG:MODE {mode}')

    def get_trigger_mode(self):
        return self.send_command(f':TRIG:MODE?', query=True)

    def set_trigger_LJT_state(self, state):
        """Use this command to set or query the status of the low-jitter trigger functionality for a given
        trigger input selected through the :TRIG:SEL command and a given channel selected by the :INST
        command."""
        if state not in [0, 1, "ON", "OFF"]:
            raise ValueError(f"Invalid state: {state}")
        self.send_command(f':TRIG:LTJ {state}')

    def get_trigger_LJT_state(self):
        return self.send_command(f':TRIG:LTJ?', query=True)

    def set_trigger_IDLE_state(self, state):
        """Use this command to define or query the trigger mode. In normal mode, the first trigger activates
        the output and consecutive triggers are ignored for the duration of the output waveform. In
        override mode, the first trigger activates the output and consecutive triggers restart the output
        waveform, regardless of if the current waveform has been completed or not."""
        if state not in ["DC", "FIRS", "CURR"]:
            raise ValueError(f"Invalid state: {state}")
        self.send_command(f':TRIG:IDLE {state}')

    def get_trigger_IDLE_state(self):
        return self.send_command(f':TRIG:IDLE?', query=True)

    def set_trigger_IDLE_level(self, level):
        """Use this command to set or query the DC level for the idle state when the mode has been set to
        DC with the :TRIG:IDLE DC command."""
        if not isinstance(level, (int, float)):
            raise ValueError(f"Invalid level: {level}")
        if not (0 <= level <= 65536):
            raise ValueError(f"Invalid level: {level}")
        self.send_command(f':TRIG:IDLE:LEV {level}')

    def get_trigger_IDLE_level(self):
        return self.send_command(f':TRIG:IDLE:LEV?', query=True)

    def set_trigger_pulse_state(self, state):
        """Use this command to set or query the status of the pulse trigger for a given trigger input selected
        through the :TRIGger:ACTive:SELect command and a given channel selected by the :INST:CHAN
        command."""
        if state not in [0, 1, "ON", "OFF"]:
            raise ValueError(f"Invalid state: {state}")
        self.send_command(f':TRIG:PULS {state}')

    def get_trigger_pulse_state(self):
        return self.send_command(f':TRIG:PULS?', query=True)

    def set_trigger_pulse_count(self, count):
        """Use this command to query the number of pulses for pulse trigger mode when it has been set
        activated with the :TRIGger:PULSe[:STATe] on command."""
        if not isinstance(count, int):
            raise ValueError(f"Invalid count: {count}")
        if not (1 <= count <= 4284967295):
            raise ValueError(f"Invalid count: {count}")
        self.send_command(f':TRIG:PULS:COUN {count}')

    def get_trigger_pulse_count(self):
        return self.send_command(f':TRIG:PULS:COUN?', query=True)

    def reset_pulse_count(self):
        """Use this command to re-start the pulse counter associated to the pulse trigger when the trigger
        mode when it has been set activated with the :TRIG:PULS on command."""
        self.send_command(f':TRIG:PULS:COUN:RES')

    def set_trigger_delay(self, delay):
        """Use this command to set or query the period of time between a valid trigger event and the action
        triggered by it.
        Name        Range               Type        Default     Description
        <delay>     external-trigger:   Numeric     0           Programs the internal delay timer to
                    0 to at least                               delay the action triggered by a valid
                    6.55μs.                                     external trigger event.
                    Resolution:
                    DAC mode M0:
                    8SCLKs
                    DAC mode M1:
                    32SCLKs
                    internal-trigger:
                    only 0"""
        if not isinstance(delay, (int, float)):
            raise ValueError("error: delay must be a number")
        if not (0 <= delay <= 6.55):
            raise ValueError("error: delay out of range")
        self.send_command(f':TRIG:DEL {delay}')

    def get_trigger_delay(self):
        return self.send_command(f':TRIG:DEL?', query=True)

    def set_trigger_holdoff(self, holdoff):
        """Set the holdoff time for the selected external-trigger of the selected channel. Incoming trigger will
        be ignored during the holdoff period.
        The figure below depicts that “Ext. Trigger #3” will be ignored and the segment will not be played
        when “Output Trigger Holdoff > 0” because the time distance to “Ext. Trigger #2” is shorter than
        the “Holdoff Time”.
        < holdoff >     external-trigger:       Numeric     100ns       Set the holdoff of the selected external
                        from 0 to TBD.                      external    trigger of the selected channel.
                        Internal-trigger:                   trigger
                        only 0 (no
                        holdoff"""
        if not isinstance(holdoff, (int, float)):
            raise ValueError("error: holdoff must be a number")
        if not (0 <= holdoff <= 0.000000100):
            raise ValueError("error: holdoff out of range")
        self.send_command(f':TRIG:HOLD {holdoff}')

    def get_trigger_holdoff(self):
        return self.send_command(f':TRIG:HOLD?', query=True)

    def set_output(self, enable):
        """This command will set or query the output state of the channel specified by the previous
        :INSTrument:CHANnel:SELect command. Note that for safety, the outputs always default to off,
        even if the last instrument setting before power down was on. Also note that the offsetting leaves
        the output connector connected to the amplifier path but no signal is being generated while in
        the off state."""
        if enable not in [0,1, "ON", "OFF"]:
            raise ValueError(f"Invalid enable: {enable}")
        self.send_command(f':OUTP {enable}')

    def get_output_state(self):
        return self.send_command(':OUTP:?', query=True)

    def set_channel_arbitrary_generation_mode(self, mode):
        """This command will set or query the arbitrary generation mode of the channel specified by the
        previous :INSTrument:CHANnel:SELect command. There are three modes: Direct, NCO, and DUC.
        The direct mode uses one sample per sampling period and samples are applied directly to the
        Proteus Programming Manual Rev. 1.7
        Confidential | 88
        DAC. The NCO mode internally generated a sine wave with the frequency and phase set by the
        :SOUR:CFR and :SOUR:CPH respectively. The IQ mode uses two samples (I, or in-Phase, and Q, or
        quadrature) per sampling period in order to feed the associated quadrature modulator in the DUC
        (Digital Up-Converter) for each channel. The quadrature modulator uses two NCOs (Numerically
        Controlled Oscillator) whose operating frequency may be set using the :SOUR:CFR command."""
        if mode not in ["DIR", "NCO", "DUC"]:
            raise ValueError(f"Invalid mode: {mode}")
        self.send_command(f':MODE {mode}')

    def get_channel_arbitrary_generation_mode(self):
        return self.send_command(':MODE?', query=True)

    def set_numerically_controlled_oscillator_mode(self, mode):
        """Set the NCO mode. In dual mode, the user can control two NCOs (1 or 2) per channel"""
        if mode not in ["SING", "DUAL"]:
            raise ValueError(f"Invalid mode: {mode}")
        self.send_command(f':NCO:MODE {mode}')

    def get_numerically_controlled_oscillator_mode(self):
        return self.send_command(':NCO:MODE?', query=True)

    def set_numerically_controlled_oscillator_carrier_frequency(self, NCO_NUMBER, frequency):
        """Use this command to set the carrier frequency in Hz for the selected NCO <1|2> of the selected
        channel. It will be effective when the waveform generation mode is set to DIR, NCO, or DUC, refer
        to 5.2 [:SOURce]:MODE{ DIRect |NCO | DUC }(?), page 87."""
        sclk = self.send_command(':FREQ?', query=True)
        if NCO_NUMBER not in [1, 2] or frequency > sclk or frequency < 0:
            raise ValueError(f"Invalid NCO_NUMBER: {NCO_NUMBER} or frequency: {frequency}")
        self.send_command(f':NCO:CFR{int(NCO_NUMBER)} {float(frequency)}')

    def get_numerically_controlled_oscillator_carrier_frequency(self, NCO_NUMBER):
        if NCO_NUMBER not in [1, 2]:
            raise ValueError(f"Invalid NCO_NUMBER: {NCO_NUMBER}")
        return self.send_command(f':NCO:CFR{int(NCO_NUMBER)}?', query=True)

    def set_numerically_controlled_oscillator_phase(self, NCO_NUMBER, phase):
        """Use this command to set the phase (in degrees) for the selected NCO <1|2> of the
        selected channel."""
        if NCO_NUMBER not in [1, 2]:
            raise ValueError(f"Invalid NCO_NUMBER: {NCO_NUMBER}")
        if phase > 360 or phase <0:
            raise ValueError(f"Invalid phase: {phase}")
        self.send_command(f':NCO:PHAS{int(NCO_NUMBER)} {int(phase)}')

    def get_numerically_controlled_oscillator_phase(self, NCO_NUMBER):
        if NCO_NUMBER not in [1, 2]:
            raise ValueError(f"Invalid NCO_NUMBER: {NCO_NUMBER}")
        return self.send_command(f':NCO:PHAS{int(NCO_NUMBER)}?', query=True)

    def set_six_db_gain_state(self, NCO_NUMBER, state):
        """This command will set or query the 6dB gain for the selected NCO<1|2>."""
        if NCO_NUMBER not in [1, 2]:
            raise ValueError(f"Invalid NCO_NUMBER: {NCO_NUMBER}")
        if state not in [0, 1, "ON", "OFF"]:
            raise ValueError(f"Invalid state: {state}")
        self.send_command(f':NCO:SIXD{int(NCO_NUMBER)} {state}', query=True)

    def get_six_db_gain_state(self, NCO_NUMBER):
        if NCO_NUMBER not in [1, 2]:
            raise ValueError(f"Invalid NCO_NUMBER: {NCO_NUMBER}")
        return self.send_command(f':NCO:SIXD{int(NCO_NUMBER)}?', query=True)

    def set_iq_modulation_type(self, iq_modulation_type):
        """Set the IQ modulation type. It is shared by all channels in the module and by all modules in a
        synchronized master-slaves chain. The IQ modulation type are classified by the number of IQ pairs
        per channel.
        IQ modulation requires one or more complex waveform, s(n) = I(n) + j x Q(n), to work. The
        different modes express the complex waveforms in a different way according to the internal
        processing performed over them."""
        if iq_modulation_type not in ["NONE", "HALF", "ONE", "TWO"]:
            raise ValueError(f"Invalid iq_modulation_type: {iq_modulation_type}")
        self.send_command(f':IQM {iq_modulation_type}')

    def get_iq_modulation_type(self):
        return self.send_command(f':IQM?', query=True)

    def set_sample_clock_frequency(self, sample_clock):
        """Use this command to set or query the sample clock frequency for the DAC in units of samples per
        second (Sa/s). The actual waveform sample rate will be determined by the combination of the
        DAC’s sample rate and the corresponding repetition factor (set by the [:SOURce]:PTRepeat
        command) or the interpolation factor (set by the [:SOURce]:INTerpolation command)."""
        if sample_clock < 0:
            raise ValueError(f"Invalid sample_clock_frequency: {sample_clock}")
        if "P128" in self.model:
            if sample_clock > 1000000000:
                raise ValueError(f"Invalid sample_clock_frequency: {sample_clock}")
        if "P258" in self.model:
            if sample_clock > 2500000000:
                raise ValueError(f"Invalid sample_clock_frequency: {sample_clock}")
        if "P908" in self.model or "P948" in self.model:
            if sample_clock > 9000000000:
                raise ValueError(f"Invalid sample_clock_frequency: {sample_clock}")

        self.send_command(f':FREQ {int(sample_clock)}')

    def get_sample_clock_frequency(self):
        return self.send_command(f':FREQ?', query=True)

    # marker commands:
    def set_marker(self, marker):
        """This command will select a given marker of the currently selected channel for programming.
        Markers (numbered 1 to 4 in the Proteus unit front panel) are associated to specific arbitrary
        waveform generation channels. Depending on the Proteus version and the total number of
        channels and marker outputs, there may be a total of up to two (2) or four (4) markers per channel."""
        if marker not in [1, 2, 3, 4]:
            raise ValueError(f"Invalid marker: {marker}")
        self.send_command(f":MARK:SEL {marker}")

    def get_marker(self):
        return self.send_command(f':MARK:SEL?', query=True)

    def set_marker_state(self, state):
        """This command will set or query the state of the marker outputs for the current active marker.
        Markers (numbered 1 to 4 on the Proteus unit front panel) are associated to specific arbitrary
        waveform generation channel. Depending on the Proteus version and the total number of
        channels and marker outputs, there may be a total of up to two (2) or four (4) markers per channel.
        Note that for safety, the outputs always default to off, even if the last instrument setting before
        power down was on. The on/off setting affects both markers simultaneously on each channel."""
        if state not in [0, 1, "ON", "OFF"]:
            raise ValueError(f"Invalid state: {state}")
        self.send_command(f':MARK {state}')

    def get_marker_state(self):
        return self.send_command(f':MARK?', query=True)

    def set_marker_coarse_delay(self, delay):
        """Use this command to set or query the coarse delay of the marker output. The delay is measured
        from the sync output in units of samples. The marker has an initial delay of 0 sample clock periods,
        not including initial skew."""
        if not isinstance (delay, (int, float)):
            raise ValueError(f"Invalid delay: {delay}")
        if self.get_dac_resolution() == 16:
            if delay > 256 or delay < -255:
                raise ValueError(f"Invalid delay: {delay}")
        else:
            if delay >1016 or delay < -1024:
                raise ValueError(f"Invalid delay: {delay}")
        self.send_command(f':MARK:DEL:COAR {int(delay)}')

    def get_marker_coarse_delay(self):
        return self.send_command(f':MARK:DEL:COAR?', query=True)

    def set_marker_fine_delay(self, delay):
        """Use this command to set or query the delay of the marker output. The delay is measured from
        the sync output in units of seconds. The marker has an initial delay of 0 seconds (after factory
        calibration)."""
        if not isinstance(delay, (int, float)):
            raise ValueError(f"Invalid delay: {delay}")
        if delay < -0.6e-9 or delay > 0.6e-9:
            raise ValueError(f"Invalid delay: {delay}")
        self.send_command(f':MARK:DEL:FINE {delay}')

    def get_marker_fine_delay(self):
        return self.send_command(f':MARK:DEL:FINE?', query=True)

    def set_marker_voltage(self, voltage):
        """Use this command to set or query the marker gain. The level is defined in dB."""
        if not isinstance (voltage, (int, float)):
            raise ValueError(f"Invalid voltage: {voltage}")
        if voltage >0 or voltage<32:
            raise ValueError(f"Invalid voltage: {voltage}")
        self.send_command(f':MARK:VOLT:LEV {voltage}')

    def get_marker_voltage(self):
        return self.send_command(f':MARK:VOLT:LEV?', query=True)

    def set_marker_ptop_voltage(self, voltage):
        """Use this command to set or query the peak-to-peak level of the marker output. The level is defined
        in unit of volt."""
        if not isinstance (voltage, (int, float)):
            raise ValueError(f"Invalid voltage: {voltage}")
        if voltage < 0.05 or voltage > 1.2:
            raise ValueError(f"Invalid voltage: {voltage}")
        self.send_command(f':MARK:VOLT:PTOP {voltage}')

    def get_marker_ptop_voltage(self):
        return self.send_command(f':MARK:VOLT:PTOP?', query=True)

    def set_marker_voltage_offset(self, offset):
        """Use this command to set or query the offset level of the marker output. The offset level is defined
        in units of volts."""
        if not isinstance (offset, (int, float)):
            raise ValueError(f"Invalid offset: {offset}")
        if offset >0.5 or offset <-0.5:
            raise ValueError(f"Invalid offset: {offset}")
        self.send_command(f':MARK:VOLT:OFFS {offset}')

    def get_marker_voltage_offset(self):
        self.send_command(f':MARK:VOLT:OFFS?', query=True)

    def set_marker_data(self, offset, binary_block):
        """This command will download marker data to the Proteus unit sequence memory for the active
        segment and channel. Marker data is loaded to the Proteus unit using high-speed binary data
        transfer. High-speed binary data transfer allows any number of 8-bit bytes to be transmitted in a
        message. Refer to the Proteus user manual chapter Markers for a detailed description.
        The following command will download to the generator a block of marker data of 1,024 entries:
        :MARK:DATA #41024<binary_block>
        This command causes the transfer of 1,024 bytes of data (1,024 marker states) into the active
        memory segment. The <header> is interpreted this way:
        • The ASCII "#" ($23) designates the start of the binary data block.
        • "4" designates the number of digits that follow representing the binary data block size in bytes.
        • "1,024" is the number of bytes to follow.
        • <binary_block> Represents task-related data."""
        if not isinstance(offset, int):
            raise ValueError("Invalid offset: {offset}")
        if offset < 0 or offset > 64000: # TO BE TESTED WHEN PROTEUS IS SHIPPED BACK: MAXIMUM IS NOT CLEAR IN THE MANUAL
            raise ValueError("Invalid arguments")
        header = self.make_binary_header (binary_block)
        self.write_binary_data(f':MARK:DATA {offset}{header}', binary_block)

    def set_marker_memory(self, offset, binary_block):
        """please use set_marker_data if that is enough: this function is advanced and it bypasses segment definition
        Direct download to the arbitrary memory without any segment attributes. This command (or
        query) is the same as :MARK[:DATA] [<offset-in-bytes-of-wave-data>] #<binary-header><binarydata>
        except that the offset, in case of :MARKer:MEMory, is from the beginning of the memoryspace
        rather than the beginning of memory of the selected segment."""
        if not isinstance(offset, int):
            raise ValueError("Invalid offset: {offset}")
        if offset < 0 or offset > 64000: # TO BE TESTED WHEN PROTEUS IS SHIPPED BACK: MAXIMUM IS NOT CLEAR IN THE MANUAL
            raise ValueError("Invalid arguments")
        header = self.make_binary_header (binary_block)
        self.write_binary_data(f':MARK:MEM {offset}{header}', binary_block)

    def from_spreadsheet_to_marker_binary_data(self, filepath):
        import pandas as pd
        import struct

        # Read Excel data
        df = pd.read_excel(filepath)

        # Prepare a list to store binary task data
        all_markers_binary = b""

        for index, row in df.iterrows():
            # Convert each row into task binary format
            task_binary = self.create_task(
            segment_number=row['Segment'],
            next1=row['Next Task (Trigger 1)'],
            next2=row['Next Task (Trigger 2)'],
            task_loop=row['Task Loop Count'],
            seq_loop=row['Sequence Loop Count'],
            delay=row['Delay'],
            idle_dac=row['DC waveform idle task DAC Value'],
            idle_behavior=row['Idle Behavior'],
            enable_signal=row['Enable Signal'],
            abort_signal=row['Abort Signal'],
            jump_type=row['Jump Type'],
            abort_jump_type=row['Abort Jump Type'],
            task_state=row['Task State'],
            task_loop_trigger_enable=row['Task Loop Trigger Enable'],
            adc_trigger=row['Generate ADC Trigger'],
            adc_feedback_trigger=row['ADC Feedback Trigger'],
            adc_trigger_source=row['ADC Trigger Source Type'],
            scale_enable=row['Scale Enable'],
            phase_enable=row['Phase Enable']
        )
            all_markers_binary += task_binary

        # Write the binary data to a file
        with open("task_table.bin", "wb") as file:
            file.write(all_markers_binary)

        # Load the task data from the binary file
        self.set_task_file("task_table.bin")
        self.load_tasks_from_file(offset=0, number_of_task_table_rows=len(df))

    def set_marker_file(self, filepath: str):
        """This command will set-up the marker information as the :MAR:DATA command does but reading
        the contents from a file stored in the target standalone Proteus. The file name is defined as an
        IEEE-488.2 binary block with the name codified in 8-bit unsigned integers (bytes) with the ASCII
        codes containing the full path to the source file."""
        if not isinstance(filepath, str) or len(filepath) == 0:
            raise ValueError("Invalid filepath")
        # Encode as unsigned short array (UTF-16LE without BOM)
        binary_block = filepath.encode('utf-16le')
        # Build the SCPI binary header
        header = self.make_binary_header(binary_block)
        # Send the command with binary data
        # Format: :TASK:FILE #<header><binary_block>
        self.write_binary_data(f":MARK:FILE {header}", binary_block)

    def set_marker_file_offset(self, offset):
        """This command will set the start offset in the file in bytes for the load or store command."""
        if not isinstance(offset, int):
            raise ValueError("Invalid arguments")
        if offset < 0 or offset>64000:
            raise ValueError("Invalid arguments")
        self.send_command(f":MARK:FILE:OFFS {offset}")

    def get_marker_file_offset(self):
        """The Proteus will return the start offset in bytes."""
        return self.send_command(f":MARK:FILE:OFFS?", query=True)

    def set_marker_file_destination(self, destination):
        """This command specifies the destination to load/store the file data."""
        if destination not in ["SEGM", "MEM"]:
            raise ValueError("Invalid arguments")
        self.send_command(f":MARK:FILE:DEST {destination}")

    def get_marker_file_destination(self):
        return self.send_command(f":MARK:FILE:DEST?", query=True)

    def load_marker_data_from_file(self, offset = None, binary_block_size_in_bytes=None):
        """Load block of markers-data from the binary-file specified in :MARKer:FILE:NAME to the
        hardware-memory specified in :MARKer:FILE:DESTination. The starting offset in the file is
        specified in :MARKer:FILE:OFFSet, while the block-size and the write-offset in the destination
        hardware memory are specified by the (optional) arguments of the command. If the <offset>
        argument is missing then zero <offset> is assumed. If both the <offset> argument and the <size>
        argument are missing, then all data from the start-offset in the file to the end of the file is
        written."""
        # Validate arguments
        if offset is not None and not isinstance(offset, int):
            raise ValueError("offset must be an integer")
        if binary_block_size_in_bytes is not None and not isinstance(binary_block_size_in_bytes, int):
            raise ValueError("size must be an integer")
        if offset is not None and offset < 0:
            raise ValueError("offset must be >= 0")
        if binary_block_size_in_bytes is not None and binary_block_size_in_bytes <= 0:
            raise ValueError("size must be > 0")
        # Build SCPI command
        if offset is None and binary_block_size_in_bytes is None:
            # No arguments → load entire file
            cmd = ":MARK:FILE:LOAD"
        elif offset is None and binary_block_size_in_bytes is not None:
            # Only size → offset defaults to file start-offset
            cmd = f":MARK:FILE:LOAD {binary_block_size_in_bytes}"
        else:
            # offset and size provided
            cmd = f":MARK:FILE:LOAD {offset},{binary_block_size_in_bytes}"
        # Send the command
        self.send_command(cmd)

    def store_marker_data_into_task_file(self, offset  = None, binary_block_size_in_bytes = None):
        """Store block of markers-data from the hardware memory specified in :MARKer:FILE:DESTination to
        the binary-file specified in :MARKer:FILE:NAME. The block-size and the write-offset in the
        hardware memory are specified by the (optional) arguments of the command. If the <offset>
        argument is missing then zero <offset> is assumed. If both the <offset> argument and the <size>
        argument are missing, then all data from the start-offset in the segment to the end of the segment
        is written."""
        # Validate types
        if offset is not None and not isinstance(offset, int):
            raise ValueError("offset must be an integer")
        if binary_block_size_in_bytes is not None and not isinstance(binary_block_size_in_bytes, int):
            raise ValueError("size must be an integer")
        # Validate ranges
        if offset is not None and offset < 0:
            raise ValueError("offset must be >= 0")
        if binary_block_size_in_bytes is not None and binary_block_size_in_bytes <= 0:
            raise ValueError("size must be > 0")
        # SCPI only allows offset if size is also provided
        if offset is not None and binary_block_size_in_bytes is None:
            raise ValueError("Cannot provide offset without size")
        # Build command
        if offset is None and binary_block_size_in_bytes is None:
            cmd = ":MARK:FILE:STOR"
        elif offset is None and binary_block_size_in_bytes is not None:
            cmd = f":MARK:FILE:STOR {binary_block_size_in_bytes}"
        else:
            cmd = f":MARK:FILE:STOR {offset},{binary_block_size_in_bytes}"
        self.send_command(cmd)

    # Task commands:
    def set_task_table_length(self, length):
        if length > 64000 or length < 0:
            raise ValueError(f"Invalid length: {length}")
        self.send_command(f':TASK:COMP:LENG {int(length)}')

    def get_task_table_length(self):
        return self.send_command(f':TASK:COMP:LENG?', query=True)

    def set_task_number(self, task_number):
        if task_number > 64000 or task_number < 1:
            raise ValueError(f"Invalid length: {task_number}")
        self.send_command(f':TASK:COMP:SEL {int(task_number)}')

    def get_task_number(self):
        return self.send_command(f':TASK:COMP:SEL?', query=True)

    def set_task_type(self, type):
        """Use this command to define the task type the current entry in the task table. It is possible to define
        different sequences within the task table. A sequence is composed of a start task, optional intermediate tasks, and an end task.
        Once a number of tasks are defined as a sequence it is possible to program the number of times the sequence will be repeated.
        The task # must be selected before using this command or query through the :TASK:SEL command."""
        if type not in ["SING", "STAR", "END", "SEQ"]:
            raise ValueError(f"Invalid length: {type}")
        self.send_command(f':TASK:COMP:TYPE {type}')

    def get_task_type(self):
        return self.send_command(f':TASK:COMP:TYPE?', query=True)

    def set_task_loop(self, repetition_number):
        """Use this command to define the number of loops for the current entry in the task table. The task
        # must be selected before using this command or query through the :TASK:SEL command.
        A task table is made up of several tasks (lines in the task table). There can be up to 64K tasks, or
        lines in the task table. Each task defines which segment is generated. The task loops parameter
        defines how many times the current task is repeated. The KEEP parameter (refer to
        :TASK:COMPoser[:DEFine]:KEEP{OFF|ON|0|1}(?) ) is with respect to the trigger. So if the number
        of Task loops is N, and the enabling signal is TRIG1. There are 2 options of how this task plays out
        when a trigger is initiated to TRIG1:
        1. KEEP=0 - A single trigger is received, and the task is played N times.
        2. KEEP=1 – A trigger is received, and the task is played once. After N triggers the task is
        completed and it proceeds to the next task (line) in the task table."""
        if not isinstance(repetition_number, int):
            raise ValueError(f"Invalid repetition_number: {repetition_number}")
        if repetition_number < 0 or repetition_number > 1000000:
            raise ValueError(f"Invalid repetition_number: {repetition_number}")
        self.send_command(f':TASK:COMP:LOOP {repetition_number}')

    def get_task_loop(self):
        return self.send_command(f':TASK:COMP:LOOP?', query=True)

    def set_sequence_loop(self, repetition_number):
        """Use this command to define the number of loops for the current sequence. The task # for the
        START task must be selected before using this command or query through the :TASK:SEL
        command."""
        if not isinstance(repetition_number, int):
            raise ValueError(f"Invalid repetition_number: {repetition_number}")
        if repetition_number < 0 or repetition_number > 1000000:
            raise ValueError(f"Invalid repetition_number: {repetition_number}")
        self.send_command(f':TASK:COMP:SEQ {repetition_number}')

    def get_sequence_loop(self):
        return self.send_command(f':TASK:COMP:SEQ?', query=True)

    def set_task_segment_number(self, segment):
        """Use this command to define the segment attached to the current entry in the task table. The task
        # must be selected before using this command or query through the :TASK:SEL command. The
        same segment may be used by any number of tasks."""
        if not isinstance(segment, int):
            raise ValueError(f"Invalid segment: {segment}")
        if segment < 1 or segment > 64000:
            raise ValueError(f"Invalid segment: {segment}")
        self.send_command(f':TASK:COMP:SEGM {segment}')

    def get_task_segment_number(self):
        return self.send_command(f':TASK:COMP:SEGM?', query=True)

    def set_task_IDLE(self, type):
        """Use this command to define the behavior of the current task while in the idle state. The task must
        be selected before using this command or query through the :TASK:SEL command. DC: DC level, FIRST:
        First level in the segment associated to the task. CURRENT: Continuous loop of the current segment."""
        if type not in ["DC", "FIRST", "CURRENT"]:
            raise ValueError(f"Invalid type: {type}")
        self.send_command(f':TASK:COMP:IDLE {type}')

    def get_task_IDLE(self):
        return self.send_command(f':TASK:COMP:IDLE?', query=True)

    def set_task_IDLE_DC_level(self, level):
        """Use this command to define the DC level while in the idle state for the current task when the idle
        type has been set to DC. The task must be selected before using this command or query through
        the :TASK:SEL command."""
        type = self.get_task_IDLE()
        dac = self.get_dac_resolution()
        if dac == 8:
            limit = 255
        else:
            limit = 65535
        if type != "DC" or level < 0 or level > limit:
            raise ValueError(f"Invalid level: {level}")
        self.send_command(f':TASK:COMP:IDLE:LEV {level}')

    def get_task_IDLE_DC_level(self):
        return self.send_command(f':TASK:COMP:IDLE:LEV?', query=True)

    def set_enabling_task_signal(self, signal):
        """Use this command to define enabling signal for the current entry in the task table. The task # must
        be selected before using this command or query through the :TASK:SEL.
        NONE: No enabling signal required, TRIG#: Trigger number, INT: Enabling signal generated internally, CPU:
        Enabling signal through SCPI command, FBTRg: Enabling signal generated by the digitizer block, ANY: any of the above"""
        if signal not in ["NONE", "TRG1", "TRG2", "TRG3", "TRG4", "TRG5", "TRG6", "INT", "CPU", "FBTR", "ANY"]:
            raise ValueError(f"Invalid signal: {signal}")
        if (signal == "TRG3" or signal == "TRG4") and (not "P1288D" in self.model or not "P12812D" in self.model or not "P2588D" in self.model or not "P25812D" in self.model or not "P1288B" in self.model or not "P12812B" in self.model or not "P2588B" in self.model or not "P25812B" in self.model or not "P9084D" in self.model or not "P9086D" in self.model or not "P9084B" in self.model or not "P9086B" in self.model):
            raise ValueError(f"Invalid signal: {signal} for model {self.model}")
        if (signal == "TRG5" or signal == "TRG6") and (not "P12812D" in self.model or not "P25812D" in self.model or not "P12812B" in self.model or not "P25812B" in self.model or not "P9086D" in self.model or not "P9086B" in self.model):
            raise ValueError(f"Invalid signal: {signal} for model {self.model}")
        self.send_command(f':TASK:COMP:ENAB {signal}')

    def get_enabling_task_signal(self):
        return self.send_command(f':TASK:COMP:ENAB?', query=True)

    def set_immediate_trigger(self):
        self.send_command(f':TRIG:IMM')

    def set_abort_task_signal(self, signal):
        """Use this command to define the abort signal for the current entry in the task table. The task #
        must be selected before using this command or query through the :TASK:SEL command."""
        if signal not in ["NONE", "TRG1", "TRG2", "TRG3", "TRG4", "TRG5", "TRG6", "INT", "CPU", "FBTR", "ANY"]:
            raise ValueError(f"Invalid signal: {signal}")
        if (signal == "TRG3" or signal == "TRG4") and (not "P1288D" in self.model or not "P12812D" in self.model or not "P2588D" in self.model or not "P25812D" in self.model or not "P1288B" in self.model or not "P12812B" in self.model or not "P2588B" in self.model or not "P25812B" in self.model or not "P9084D" in self.model or not "P9086D" in self.model or not "P9084B" in self.model or not "P9086B" in self.model):
            raise ValueError(f"Invalid signal: {signal} for model {self.model}")
        if (signal == "TRG5" or signal == "TRG6") and (not "P12812D" in self.model or not "P25812D" in self.model or not "P12812B" in self.model or not "P25812B" in self.model or not "P9086D" in self.model or not "P9086B" in self.model):
            raise ValueError(f"Invalid signal: {signal} for model {self.model}")
        self.send_command(f':TASK:COMP:ABOR {signal}')

    def get_abort_task_signal(self):
        return self.send_command(f':TASK:COMP:ABOR?', query=True)

    def set_abort_task_jump(self, argument):
        """Use this command to define the way to jump to a different task for the currently selected task
        when a valid ABORT event occurs. The task # must be selected before using this command or
        query through the :TASK:SEL command. EVEN: Sets the effective jump to happen at the end of the
        current loop."""
        if argument not in ["EVEN", "IMM"]:
            raise ValueError(f"Invalid argument: {argument}")
        self.send_command(f':TASK:COMP:JUMP {argument}')

    def get_abort_task_jump(self):
        return self.send_command(f':TASK:COMP:JUMP?', query=True)

    def set_next_task_destination(self, argument):
        """Use this command to define the next task to be generated after the currently selected task. The
        task # must be selected before using this command or query through the :TASK:SEL command.
        <NEXT> Discrete NEXT Points to the next task to be generated according to the :NEXT1 command setting
        <FBTR> Discrete Points to the next task to be generated according to the digitizer setting.
        <TRG> Discrete A conditional jump. Points to the next task to be generated according to the trigger inputs. Valid signal
                at trigger 1 points to the next task as set in :NEXT1 setting while a valid signal at trigger 2 points to next task as set in :NEXT2 setting.
        <NTS> Discrete The next task in the table
        <SCEN> Discrete The beginning of next scenario
        <DSP> Discrete Destination is NEXT1 current segment to be generated is according to decision block condition in DSP.
        <DSIG> Discrete NEXT1 if digitizer-signal = 1, NEXT2 if digitizer-signal = 0."""
        if argument not in ["NEXT", "FBTR", "TRG", "NTS", "SCEN", "DSP", "DSIG"]:
            raise ValueError(f"Invalid argument: {argument}")
        self.send_command(f':TASK:COMP:DEST {argument}')

    def get_next_task_destination(self):
        return self.send_command(f':TASK:COMP:DEST?', query=True)

    def set_next1_task(self, argument):
        """When setting a conditional jump use this command to define the next task to be generated after
        the currently selected task when the Trigger 1 input or digitizer-signal=0 are the source for
        jumping. The task # must be selected before using this command or query through the :TASK:SEL
        command."""
        if not isinstance(argument, int):
            raise ValueError(f"Invalid argument: {argument}")
        if argument < 0 or argument > 64000:
            raise ValueError(f"Invalid argument: {argument}")
        self.send_command(f":TASK:COMP:NEXT1 {argument}")

    def get_next1_task(self):
        """The Proteus unit will return the next task to be generated after the current task is executed."""
        return self.send_command(f':TASK:COMP:NEXT1?', query=True)

    def set_next2_task(self, argument):
        """When setting a conditional jump use this command to define the next task to be generated after
        the currently selected task when the Trigger 2 input or digitizer-signal=0 are the source for
        jumping. The task # must be selected before using this command or query through the :TASK:SEL
        command."""
        if not isinstance(argument, int):
            raise ValueError(f"Invalid argument: {argument}")
        if argument <= 0 or argument > 64000:
            raise ValueError(f"Invalid argument: {argument}")
        self.send_command(f":TASK:COMP:NEXT2 {argument}")

    def get_next2_task(self):
        """The Proteus unit will return the next task number mode for the current task when trigger 2 or
        digitizer-signal=0 are the source for jumping."""
        return self.send_command(f':TASK:COMP:NEXT2?', query=True)

    def set_task_delay(self, argument):
        """Use this command to define the delay in clocks before executing the next task. The task # must
        be selected before using this command or query through the :TASK:SEL command."""
        if not isinstance(argument, int):
            raise ValueError(f"Invalid argument: {argument}")
        if argument < 0 or argument > 65536:
            raise ValueError(f"Invalid argument: {argument}")
        self.send_command(f":TASK: COMP:DEL {argument}")

    def get_task_delay(self):
        return self.send_command(f':TASK:COMP:DEL?', query=True)

    def set_task_keep(self, argument):
        """Use this command to define the behavior of loops for this task with respect to the trigger. The
        task # must be selected before using this command or query through the :TASK:SEL command.
        1. KEEP=0 - A single trigger is received, and the task is played N times.
        2. KEEP=1 – A trigger is received, and the task is played once. After N triggers the task is
        completed and it proceeds to the next task (line) in the task table."""
        if argument not in [0, 1, "ON", "OFF"]:
            raise ValueError(f"Invalid argument: {argument}")
        self.send_command(f':TASK:COMP:KEEP {argument}')

    def get_task_keep(self):
        return self.send_command(f':TASK:COMP:KEEP?', query=True)

    def set_task_pid(self, argument):
        """This command sets which parameter of the PID is used in the current task.
        OFF: PID is not used in the current task.
        SCALE: The current task uses the PID scale value.
        PHASE: The current task uses the PID phase value.
        BOTH: The current task uses both PID scale and phase value."""
        if argument not in ["OFF", "SCALE", "PHASE", "BOTH"]:
            raise ValueError(f"Invalid argument: {argument}")
        self.send_command(f':TASK:COMP:PID {argument}')

    def get_task_pid(self):
        return self.send_command(f':TASK:COMP:PID?', query=True)

    def write_composer_array_to_task_table(self):
        """Write the composer's array to the task-table of the selected channel at the specified offset (no
        query). Issue this command once all the Task table parameters have been defined."""
        """if not isinstance(offset, int):
            raise ValueError(f"Invalid offset: {offset}")
        if offset < 1 or offset > 64000:
            raise ValueError(f"Invalid offset: {offset}")"""
        self.send_command(":TASK:COMP:WRIT")

    def read_composer_array_from_task_table(self, offset):
        """Read the composer's array from the task-table of the selected channel at the specified offset (no
        query). See :TASK:DATA command for data format definitions"""
        if not isinstance(offset, int):
            raise ValueError(f"Invalid argument: {offset}")
        if offset < 0 or offset > 64000:
            raise ValueError(f"Invalid argument: {offset}")
        return self.send_command(f':TASK:COMP:READ {offset}')

    def get_current_task(self):
        """Query only. Returns the current task number."""
        return self.send_command(f':TASK:CURR?', query=True)

    def set_task_sync(self):
        """No query. Issue this command to synchronize the task tables of all channels. This command needs
        to be issued every time before generation is started."""
        self.send_command(':TASK:SYNC')

    def set_task_data(self, offset, binary_block):
        """Write data to the specified offset in the task-table of the selected channel. Binary transfers are a
        much faster way to define tasks lists, especially when they are long. Binary data is defined as an
        array of structs (see format below) of fixed length, with one element representing each individual
        task in the list. This format is also used when reading data from the task list using the
        :TASK:COMP:READ command and when transferring task lists from/to files using the
        :TASK:FILE:LOAD and :TASK:FILE:STOR commands.
        As an example, the :TASK:DATA #41024<binary_block> command will cause the transfer of 1,024
        bytes of data into the active memory segment. The <header> is interpreted this way:
        • The ASCII "#" ($23) designates the start of the binary data block.
        • "4" designates the number of digits that follow representing the binary data block size in bytes.
        • "1,024" is the number of bytes to follow.
        • <binary_block> Represents task-related data.
        Name        Range       Type            Default     Description
        < offset >  0 64k       Numeric(int)    0           Write the data to specified offset in the task table.
        < header >              Numeric(int)                Contains information on the size of the binary block that follows.
        < binary_block >        Binary                      Block of binary data that contains task related data, as explained above.
                                Type            Bytes
                                UINT32          0 - 3       The segment number.
                                UINT32          4 - 7       The next task for trigger 1 (zero for end)
                                UINT32          8 - 11      The next task for trigger 2 (zero for end).
                                UINT32          12 - 15     The task loop count.
                                UINT32          16 - 19     The sequence loop count.
                                UINT16          20 - 21     The delay in clocks before executing the next task.
                                UINT16          22 - 23     The DAC value of the idle task DC waveform.
                                UINT8           24          The behavior during idle-time.
                                                            0 – DC
                                                            1 – First point
                                                            2 – Current segment
                                UINT8           25          The enabling signal.
                                                            0 – None
                                                            1 – ExternTrig1
                                                            2 – ExternTrig2
                                                            3 – InternTrig
                                                            4 – CPU
                                                            5 – FeedbackTrig
                                                            6 – HW-Ctrl
                                UINT8           26          The aborting signal.
                                                            0 – None
                                                            1 – ExterTrig1
                                                            2 – ExternTrig2
                                                            3 – InternTrig
                                                            4 – CPU
                                                            5 – FeedbackTrig
                                                            6 – Any
                                UINT8           27          How to decide where to jump.
                                                            0 – Next1
                                                            1 – By FBTrig-value
                                                            2 – ExtTrig[1/2]->Next[1/2]
                                                            3 – NextTaskSel
                                                            4 – Next scenario
                                UINT8           28          Task abort jump type.
                                                            0 – Eventually
                                                            1 – Immediate
                                UINT8           29          The task state.
                                                            0 – Single
                                                            1 – First of sequence
                                                            2 – Last of sequence
                                                            3 – Inside sequence
                                UINT8           30          Task loop trigger enable, waiting for trigger
                                                            on looping.
                                                            1 – Enable
                                                            0 – Disable
                                UINT8           31          Generate an ADC trigger at the beginning of
                                                            the current task.
                                                            1 – Enable
                                                            0 – Disable
                                UINT8           32          ADC feedback trigger.
                                                            1 – Wave
                                                            0 – Idle
                                UINT8           33          ADC trigger source type.
                                                            3 – PID Phase
                                                            2 – PID Scale
                                                            1 – Grabber
                                                            0 – Wave
                                UINT8           34          Scale enable.
                                                            1 – Enable
                                                            0 – Disable
                                UINT8           35          Phase enable.
                                                            1 – Enable
                                                            0 – Disable"""
        if not isinstance(offset, int):
            raise ValueError("Invalid arguments")
        if offset < 0 or offset > 64000:
            raise ValueError("Invalid arguments")
        header = self.make_binary_header (binary_block)
        self.write_binary_data(f':TASK:DATA {offset}{header}', binary_block)

    def from_spreadsheet_to_task_binary_data(self, filepath):
        import pandas as pd
        import struct

        # Read Excel data
        df = pd.read_excel(filepath)

        # Prepare a list to store binary task data
        all_tasks_binary = b""

        for index, row in df.iterrows():
            # Convert each row into task binary format
            task_binary = self.create_task(
                segment_number=row['Segment'],
                next1=row['Next Task (Trigger 1)'],
                next2=row['Next Task (Trigger 2)'],
                task_loop=row['Task Loop Count'],
                seq_loop=row['Sequence Loop Count'],
                delay=row['Delay'],
                idle_dac=row['DC waveform idle task DAC Value'],
                idle_behavior=row['Idle Behavior'],
                enable_signal=row['Enable Signal'],
                abort_signal=row['Abort Signal'],
                jump_type=row['Jump Type'],
                abort_jump_type=row['Abort Jump Type'],
                task_state=row['Task State'],
                task_loop_trigger_enable=row['Task Loop Trigger Enable'],
                adc_trigger=row['Generate ADC Trigger'],
                adc_feedback_trigger=row['ADC Feedback Trigger'],
                adc_trigger_source=row['ADC Trigger Source Type'],
                scale_enable=row['Scale Enable'],
                phase_enable=row['Phase Enable']
            )
            all_tasks_binary += task_binary

        # Write the binary data to a file
        with open("task_table.bin", "wb") as file:
            file.write(all_tasks_binary)

        # Load the task data from the binary file
        self.set_task_file("task_table.bin")
        self.load_tasks_from_file(offset=0, number_of_task_table_rows=len(df))

    def create_task(self,
            segment_number,
            next1=0,
            next2=0,
            task_loop=1,
            seq_loop=1,
            delay=0,
            idle_dac=0,
            idle_behavior=0,
            enable_signal=0,
            abort_signal=0,
            jump_type=0,
            abort_jump_type=0,
            task_state=0,
            task_loop_trigger_enable=1,
            adc_trigger=0,
            adc_feedback_trigger=0,
            adc_trigger_source=0,
            scale_enable=0,
            phase_enable=0
    ):
        """Pack a single task into a 36-byte binary block."""
        return struct.pack(
            '<IIIIIHHBBBBBBBBBBBB',
            segment_number,
            next1,
            next2,
            task_loop,
            seq_loop,
            delay,
            idle_dac,
            idle_behavior,
            enable_signal,
            abort_signal,
            jump_type,
            abort_jump_type,
            task_state,
            task_loop_trigger_enable,
            adc_trigger,
            adc_feedback_trigger,
            adc_trigger_source,
            scale_enable,
            phase_enable
        )

    def set_trigger(self, trigger):
        if trigger not in ["TRG1", "TRG2"]:
            raise ValueError(f"Invalid number: {trigger}")
        self.send_command(f':TRIG:SEL {trigger}')

    def make_binary_header(self, binary_block: bytes) -> str:
        """
        Create a binary header string of form '#<d><size>',
        where <d> is the digit count of <size>.
        """
        size = len(binary_block)
        digit_count = len(str(size))
        return f"#{digit_count}{size}"

    def set_task_file(self, filepath: str):
        """This command will identify the file path storing the task table information for further transfers
        to/from the task table. The file path is passed as a binary-block."""
        if not isinstance(filepath, str) or len(filepath) == 0:
            raise ValueError("Invalid filepath")

        # Encode as unsigned short array (UTF-16LE without BOM)
        binary_block = filepath.encode('utf-16le')

        # Build the SCPI binary header
        header = self.make_binary_header(binary_block)

        # Send the command with binary data
        # Format: :TASK:FILE #<header><binary_block>
        self.write_binary_data(f":TASK:FILE {header}", binary_block)

    def set_task_file_offset(self, offset):
        """This command will set the start offset inside the file in bytes."""
        if not isinstance(offset, int):
            raise ValueError("Invalid arguments")
        if offset < 0 or offset>64000:
            raise ValueError("Invalid arguments")
        self.send_command(f":TASK:FILE:OFFS {offset}")

    def load_tasks_from_file(self, offset, number_of_task_table_rows):
        """This command will load task data from the file defined by the :TASK:FILE:NAME command to the
        Proteus desktop unit task table memory. If the offset and number of tasks are not specified, then
        the whole task-table is written. If the file is too small then the rest of the task-table rows are
        zeroed. See :TASK:DATA command for data format definitions."""
        if not isinstance(offset, int):
            raise ValueError("Invalid arguments")
        if offset < 0 or offset>64000:
            raise ValueError("Invalid arguments")
        if not isinstance(number_of_task_table_rows, int):
            raise ValueError("Invalid arguments")
        if number_of_task_table_rows < 1 or number_of_task_table_rows > 64000:
            raise ValueError("Invalid arguments")
        self.send_command(f":TASK:FILE:LOAD {offset}, {number_of_task_table_rows}")

    def store_data_into_task_file(self, offset, number_of_task_table_rows):
        """This command will save task data from the Proteus unit to the file defined by the :TASK:FILE:NAME
        command. The command, when no parameters are specified, saves all the entries in the task table
        in the file (no query). See :TASK:DATA command for data format definitions."""
        if not isinstance(offset, int):
            raise ValueError("Invalid arguments")
        if offset < 0 or offset > 64000:
            raise ValueError("Invalid arguments")
        if not isinstance(number_of_task_table_rows, int):
            raise ValueError("Invalid arguments")
        if number_of_task_table_rows < 1 or number_of_task_table_rows > 64000:
            raise ValueError("Invalid arguments")
        self.send_command(f":TASK:FILE:STOR {offset}, {number_of_task_table_rows}")

    def set_zero_tasks(self, start_row, number_of_task_table_rows):
        """This command will set the designated entries in the task to an “all zeros” content. Issue this
        command e.g., when you have a task table of 8 tasks and want to write a task table of 4 tasks."""
        #Clear rows starting at <offset>, for <num_of_tasks> rows
        if not isinstance(start_row, int):
            raise ValueError("Invalid arguments")
        if start_row < 1 or start_row > 64000:
            raise ValueError("Invalid arguments")
        if not isinstance(number_of_task_table_rows, int):
            raise ValueError("Invalid arguments")
        if number_of_task_table_rows < 1 or number_of_task_table_rows > 64000:
            raise ValueError("Invalid arguments")
        self.send_command(f":TASK:ZERO {start_row},{number_of_task_table_rows}")

    def zero_all_tasks(self):
        """This command will set the all the entries in the task to an “all zeros” content."""
        self.send_command(f":TASK:ZERO:ALL")

    def define_scenario(self, scenario_number, task_number, loops):
        """Use this command to define the specified entry in the scenario-table of the selected channel.
        In principle it is a table consisting of Task numbers. So, if a task is a “playlist of songs” then a
        scenario is a “playlist of playlists”."""
        if not isinstance(scenario_number, int):
            raise ValueError("Invalid arguments")
        if scenario_number < 1 or scenario_number > 1000:
            raise ValueError("Invalid arguments")
        if not isinstance(task_number, int):
            raise ValueError("Invalid arguments")
        if task_number < 1 or task_number > 64000:
            raise ValueError("Invalid arguments")
        if not isinstance(loops, int):
            raise ValueError("Invalid arguments")
        if loops < 1 or loops > 1000000:
            raise ValueError("Invalid arguments")
        self.send_command(f":SCEN:DEF {scenario_number}, {task_number}, {loops}")

    def get_current_scenario(self):
        return self.send_command(":SCEN:DEF?")

    def set_scenario_data(self, offset, binary_block):
        """This command will download scenario data to the Proteus unit sequence memory. Scenario data
        is loaded to the Proteus unit using high-speed binary data transfer. High-speed binary data
        transfer allows any number of 8-bit bytes to be transmitted in a message. This command is
        particularly useful for sending large quantities of data. As an example, the next command will
        download to the generator a block of scenario related data of 512 entries:
        :SCEN:DATA #3512<binary_block>
        This command causes the transfer of 512 bytes of data (256 waveform points) into the active
        scenario. The <header> is interpreted this way:
        The ASCII "#" (0x23) designates the start of the binary data block.
        • "4" designates the number of digits that follow representing the binary data block size in
        bytes.
        • "512" is the number of bytes to follow.
        • <binary_block> Represents task-related data.
        Offset: Offset in scenario table rows"""
        if not isinstance(offset, int):
            raise ValueError("Invalid arguments")
        if offset < 0 or offset > 1000:
            raise ValueError("Invalid arguments")
        header = self.make_binary_header (binary_block)
        self.write_binary_data(f':SCEN:DATA {offset},{header}', binary_block)

    def set_scenario_file(self, filepath: str):
        """This command will identify the file path storing the scenario table information for further transfers
        to/from the scenario table. The file path is passed as a binary block.
        < header > Discrete The first digit in ASCII is the number of digits to follow.
        The following digits specify the length of the target file full
        path name in ASCII.
        < binary_block > Binary Full path name for the file in ASCII coded as an unsigned
        short integer array."""
        if not isinstance(filepath, str):
            raise ValueError("Invalid filepath")
        if len(filepath) == 0:
            raise ValueError("Invalid filepath")
        # Encode as unsigned short array (UTF-16LE without BOM)
        binary_block = filepath.encode('utf-16le')
        # Build the SCPI binary header
        header = self.make_binary_header(binary_block)
        # Send the command with binary data
        # Format: :SCENario:FILE[:NAME]{ #<header><binary_block>}
        self.write_binary_data(f":SCEN:FILE:NAME {header}", binary_block)

    def set_scenario_file_offset(self, offset):
        """This command will set the start offset inside the file in bytes."""
        if not isinstance(offset, int):
            raise ValueError("Invalid arguments")
        if offset < 0 or offset > 65536:
            raise ValueError("Invalid arguments")
        self.send_command(f":SCEN:FILE:OFFS {offset}")

    def load_scenarios_from_file(self, offset, number_of_scenario_table_rows):
        """This command will load the task data from the file defined by the :SCEN:FILE:NAME command to
        the Proteus unit task table memory. If the offset and number of tasks are not specified, then the
        whole task-table is written. If the file is too small then the rest of the task-table rows are zeroed.
        <offset> Integer Offset in scenario table rows
        <number_of_scenario_table_rows> Integer Number of scenario table rows"""
        if not isinstance(offset, int):
            raise ValueError("Invalid arguments")
        if offset < 0 or offset > 999:
            raise ValueError("Invalid arguments")
        if not isinstance(number_of_scenario_table_rows, int):
            raise ValueError("Invalid arguments")
        if number_of_scenario_table_rows < 1 or number_of_scenario_table_rows > 1000:
            raise ValueError("Invalid arguments")
        self.send_command(f":SCEN:FILE:LOAD {offset}, {number_of_scenario_table_rows}")

    def store_data_into_scenario_file(self, offset, number_of_scenario_table_rows):
        """This command will save scenario data from the Proteus unit to the file defined by the
        :SCEN:FILE:NAME command. The command, when no parameters are specified, saves all the
        entries in the task table in the file (no query)."""
        if not isinstance(offset, int):
            raise ValueError("Invalid arguments")
        if offset < 0 or offset > 999:
            raise ValueError("Invalid arguments")
        if not isinstance(number_of_scenario_table_rows, int):
            raise ValueError("Invalid arguments")
        if number_of_scenario_table_rows < 1 or number_of_scenario_table_rows > 1000:
            raise ValueError("Invalid arguments")
        self.send_command(f":SCEN:FILE:STOR {offset}, {number_of_scenario_table_rows}")

    def set_zero_scenarios(self, scenario_number):
        """Reset the data of a single row in the scenario table of the selected channel (no query)."""
        if not isinstance(scenario_number, int):
            raise ValueError("Invalid arguments")
        if scenario_number < 1 or scenario_number > 1000:
            raise ValueError("Invalid arguments")
        self.send_command(f":SCEN:ZERO {scenario_number}")

    def zero_all_scenario(self):
        """This command will set the all the entries in the scenario table to an “all zeros” content."""
        self.send_command(f":SCEN:ZERO:ALL")

    # arbitrary waveform commands:
    def set_trace_data(self, offset, binary_block):
        """This command will download waveform data starting from the specified offset to the Proteus
        waveform memory. Waveform data is loaded to the Proteus using high-speed binary data
        transfer. High-speed binary data transfer allows any number of 8-bit bytes to be transmitted in a
        message. This command is particularly useful for sending large quantities of data. As an example,
        the next command will download to the generator an arbitrary block of data of 1,024 points
        TRACe #42048<binary_block>"""
        if not isinstance(offset, int):
            raise ValueError(f"Invalid offset: {offset}")
        if offset < 0 or offset > 64000: # TO BE TESTED WHEN PROTEUS IS SHIPPED BACK: MAXIMUM IS NOT CLEAR IN THE MANUAL
            raise ValueError("Invalid arguments")
        header = self.make_binary_header (binary_block)
        self.write_binary_data(f':TRAC {offset}{header}', binary_block)

    def set_trace_format(self, trace_format):
        """Set the resolution of the user waveform data that is to be transferred to the Proteus to unsigned
        16/8-bit. This command does not modify the internal sample size (see :TRACe:DATA command),
        just the size of the downloaded data."""
        if trace_format not in ["U16", "U8"]:
            raise ValueError("Invalid format")
        self.send_command(f":TRAC:FORM {trace_format}")

    def get_trace_format(self):
        return self.send_command(f":TRAC:FORM?", query=True)

    def set_trace_memory(self, offset, binary_block):
        """Write waveform data to the arbitrary-memory space starting from the specified offset.
        The query format is:
        :TRAC:MEM? [<offset in wave-points>,]<size in wave-points>.
        This command (or query) is the same as
        :TRACe[:DATA] [<offset-in-bytes-of-wave-data>] #<binary-header><binarydata>
        except that the offset, in case of :TRACe:MEMory, is from the beginning of the memory-space
        rather than the beginning of memory of the selected segment. This command ca be used to write
        or read multiple segments at once."""
        if not isinstance(offset, int):
            raise ValueError(f"Invalid offset: {offset}")
        if offset < 0 or offset > 64000: # TO BE TESTED WHEN PROTEUS IS SHIPPED BACK: MAXIMUM IS NOT CLEAR IN THE MANUAL
            raise ValueError("Invalid arguments")
        header = self.make_binary_header (binary_block)
        self.write_binary_data(f':TRAC:MEM {offset}{header}', binary_block)

    def set_trace_segment_data(self, first_segment_number, binary_block):
        """Delete the previous definition, if any, of all the designated N segments of the selected channel
        (no sample information is actually deleted) and define N consecutive new segments (no query).
        The N segment-lengths, expressed in bytes of wave-data, are specified by the binary-block which
        consists of N uint64 values (8N bytes). The new segments are allocated, one after the other, from
        the beginning of the arbitrary-memory space."""
        if not isinstance(first_segment_number, int):
            raise ValueError(f"Invalid offset: {first_segment_number}")
        if first_segment_number < 0 or first_segment_number > 64000:
            raise ValueError("Invalid arguments")
        header = self.make_binary_header (binary_block)
        self.write_binary_data(f':TRAC:SEGM {first_segment_number}{header}', binary_block)

    def set_trace_segment_file(self, filepath):
        """This command will identify the file path storing the waveform data information for further
        transfers to/from the unit’s memory. The file path is passed as a binary-block."""
        if not isinstance(filepath, str) or len(filepath) == 0:
            raise ValueError("Invalid filepath")
        # Encode as unsigned short array (UTF-16LE without BOM)
        binary_block = filepath.encode('utf-16le')
        # Build the SCPI binary header
        header = self.make_binary_header(binary_block)
        # Send the command with binary data
        self.write_binary_data(f":TRAC:SEGM:FILE {header}", binary_block)

    def set_trace_segment_file_offset(self, offset):
        """This command will set the start offset inside the file in bytes."""
        if not isinstance(offset, int):
            raise ValueError("Invalid arguments")
        if offset < 0 or offset>64000:
            raise ValueError("Invalid arguments")
        self.send_command(f":TRAC:SEGM:FILE:OFFS {offset}")

    def get_trace_segment_file_offset(self):
        return self.send_command(f":TRAC:SEGM:FILE:OFFS?", query=True)

    def load_trace_segment_data_from_file(self, first_segment, number_of_segments):
        """This command will load the segment table data from the file defined by the
        :TRACe:SEGM:FILE:NAME command to the Proteus unit memory. If the first segment is not
        specified, then the default segment is 1."""
        if not isinstance(first_segment, int):
            raise ValueError("Invalid arguments")
        if first_segment < 0 or first_segment>64000:
            raise ValueError("Invalid arguments")
        if not isinstance(number_of_segments, int):
            raise ValueError("Invalid arguments")
        if number_of_segments < 1 or number_of_segments > 64000:
            raise ValueError("Invalid arguments")
        self.send_command(f":TRAC:SEGM:FILE:LOAD {first_segment}, {number_of_segments}")

    def set_trace_file(self, filepath):
        """This command will identify the file path storing the waveform data information for further
        transfers to/from the unit’s memory. The file path is passed as a binary-block"""
        if not isinstance(filepath, str) or len(filepath) == 0:
            raise ValueError("Invalid filepath")
        # Encode as unsigned short array (UTF-16LE without BOM)
        binary_block = filepath.encode('utf-16le')
        # Build the SCPI binary header
        header = self.make_binary_header(binary_block)
        # Send the command with binary data
        self.write_binary_data(f":TRAC:FILE {header}", binary_block)

    def set_trace_file_offset(self, offset):
        """Set the start offset inside the file in bytes."""
        if not isinstance(offset, int):
            raise ValueError("Invalid arguments")
        if offset < 0 or offset>64000:
            raise ValueError("Invalid arguments")
        self.send_command(f":TRAC:FILE:OFFS {offset}")

    def get_trace_file_offset(self):
        return self.send_command(f":TRAC:FILE:OFFS?", query=True)

    def set_trace_file_destination(self, destination):
        """Use this command to set the destination to load/store the file data."""
        if destination not in ["SEGM", "MEM"]:
            raise ValueError("Invalid arguments")
        self.send_command(f":TRAC:FILE:DEST {destination}")

    def get_trace_file_destination(self):
        return self.send_command(f":TRAC:FILE:DEST?", query=True)

    def load_trace_data_from_file(self, offset=None, size_in_wavepoints=None):
        """This command will load the waveform data from the file defined by the :TRACe:FILE:NAME
        command to the Proteus unit memory. If the offset and the number of wave-points are not
        specified, then the whole segment is written. No query."""
        cmd = ":TRAC:FILE:LOAD"
        if offset is not None and size_in_wavepoints is not None:
            cmd += f" {offset}, {size_in_wavepoints}"
        elif size_in_wavepoints is not None:
            cmd += f" {size_in_wavepoints}"
        # offset defaults to 0 if size only; SCPI allows this
        self.send_command(cmd)

    def store_trace_data_into_file(self, offset = None, size_in_wavepoints = None):
        """This command will save waveform data from the Proteus unit to the file defined by the
        :TRAC:FILE:NAME command. If the offset and the number of wave-points are not specified,
        then the whole segment is read. No query."""
        cmd = ":TRAC:FILE:STOR"
        if offset is not None and size_in_wavepoints is not None:
            cmd += f" {offset}, {size_in_wavepoints}"
        elif size_in_wavepoints is not None:
            cmd += f" {size_in_wavepoints}"
        self.send_command(cmd)

    def set_trace_streaming_mode(self, mode):
        """This command will set or query the target type of streaming mode."""
        if mode not in ["FILE", "DYN"]:
            raise ValueError("Invalid arguments")
        self.send_command(f":TRAC:STR:MODE {mode}")

    def get_trace_streaming_mode(self):
        return self.send_command(f":TRAC:STR:MODE?", query=True)

    def set_trace_streaming_state(self, state):
        """This command will set or query the state of the streaming functionality. Only for units with
        installed streaming option (STM)."""
        if state not in [0, 1, "ON", "OFF"]:
            raise ValueError("Invalid arguments")
        self.send_command(f":TRAC:STR:STAT {state}")

    def get_trace_streaming_state(self):
        return self.send_command(f":TRAC:STR:STAT?", query=True)

    def define_trace(self, segment_number, segment_length):
        if not isinstance (segment_number, int):
            raise ValueError("Invalid arguments")
        if not isinstance (segment_length, int):
            raise ValueError("Invalid arguments")
        if segment_number<1 or segment_number>64000:
            raise ValueError("Invalid arguments")
        self.send_command(f":TRAC:DEF {segment_number}, {segment_length}")

    def get_trace_definition(self):
        segment_number, size = self.send_command(":TRAC:DEF?")
        return segment_number, size

    def get_segment_length(self):
        return self.send_command(":TRAC:DEF:LENG?")

    def set_zero_segments(self, segment_number):
        """Zero the markers and waveform data of specified single segment (no query). The segment-number
        is optional. If it is not given then the current segment is zeroed."""
        if not isinstance(segment_number, int):
            raise ValueError("Invalid arguments")
        if segment_number < 1 or segment_number > 64000:
            raise ValueError("Invalid arguments")
        self.send_command(f":TRAC:ZERO {segment_number}")

    def zero_all_segments(self):
        """This command will zero all the arbitrary-memory space of the selected channel's DDR (no query)."""
        self.send_command(f":TRAC:ZERO:ALL")

    def delete_trace_segment(self, segment):
        """This command will delete the predefined segment from the working memory."""
        if not isinstance(segment, int):
            raise ValueError("Invalid arguments")
        if segment <1 or segment>64000:
            raise ValueError("Invalid arguments")
        self.send_command(f":TRAC:DEL {segment}")

    def delete_all_segment(self):
        """Delete all segments of the programmable channel's DDR."""
        self.send_command(":TRAC:DEL:ALL")

    def select_segment(self, segment):
        """Use this command to specify the segment to be selected. Do not confuse it with the selectedsegment
        for playback (:FUNCtion:MODE:SEGMent)."""
        if not isinstance(segment, int):
            raise ValueError("Invalid arguments")
        if segment<1 or segment>64000:
            raise ValueError("Invalid arguments")
        self.send_command(f":TRAC:SEL {segment}")

    def get_selected_segment(self):
        return self.send_command(f":TRAC:SEL?", query = True)

    def trace_select_source(self, source):
        """Use this command to set or query the source of the segment select command. This defines from
        where the select command is expected to be received, causing a waveform segment change. Using
        the BUS option, waveforms can be selected using remote commands only. The EXT option
        transfers the control to a connector in the front panel that allows dynamic selection of the active
        waveform segment. Using the external waveform control, one can dynamically select a waveform
        from a preprogrammed list of waveforms. Using the ADC option, waveforms can be selected by
        the digitizer trigger. The transition characteristics from waveform segment to another is
        programmed using the TRAC:SEL:TIM command.
        BUS: Defines that waveform segments will be switched only
             when a remote command has been received.
        EXTernal: Defines that the segment control is transferred to
                sequence control connector. The connector has 8 bits
                of parallel control lines that can switch between up to
                256 segments.
        ADC: Source for segment selection (for playback) is by the
            ADC trigger (if this option is supported).
        DCT: Source for segment selection (for playback) is by the
            daisy-chain-trigger"""
        if source not in ["EXT", "ADC", "BUS", "DCT"]:
            raise ValueError("Invalid arguments")
        self.send_command(f":TRAC:SEL:SOUR {source}")

    def get_trace_select_source(self):
        return self.send_command(f":TRAC:SEL:SOUR?", query = True)

    def set_trace_select_timing(self, timing):
        """Use this command to set or query the timing characteristics of the trace select command. This
        defines how the generator transitions from waveform to waveform. Use the eventually option to
        let the waveform complete before it jumps to the next waveform. Applications that require an
        unconditional jump can use the immediate option, where the generation of the current waveform
        is aborted and the new waveform is started immediately thereafter. This command affects the
        segment transition timing, regardless of if the segment control is from remote or from the rear
        panel connector."""
        if timing not in ["EVEN", "IMM"]:
            raise ValueError("Invalid arguments")
        self.send_command(f":TRAC:SEL:TIM {timing}")

    def get_trace_select_timing(self):
        return self.send_command(f":TRAC:SEL:TIM?", query = True)

    def get_available_waveform_memory(self):
        """Query only. Query the available waveform memory in the DDR including biggest fragment. Ask
        for the current behavior of this command as it should give the biggest section of contiguous data
        so users can define a new segment of equal or shorter length than that. Additionally, it could
        return a second number with the total free memory."""
        return self.send_command(":TRAC:FREE?", query = True)

    def get_selected_channel_memory_space_fragmentation_level(self):
        """Query only. Query the fragmentation level of the of the selected channel's memory-space.
        Fragmentation can occur after some existing segments are deleted. Waveform and marker data
        for a give segment is always stored in contiguous sections of the memory. This means that
        unused sections of the memory can only be reused by a new segment if its length is equal or
        shorter than the largest unused section."""
        return self.send_command(f":TRAC:FRAG?", query = True)

    def defragment_arbitrary_memory_space(self):
        """This command will defragment the arbitrary-memory space of the selected channel DDR."""
        self.send_command(":TRAC:DEFR")

    # system commands:
    def set_system_log_verbosity(self, level: int):
        if level not in [0, 1, 2, 3, 4, 5, 6]:
            raise ValueError("Invalid arguments")
        return self.send_command(f":SYST:LOG {level}")

    def get_system_log_verbosity(self):
        return self.send_command(":SYST:LOG?", query=True)

    def get_system_error(self):
        resp = self.send_command(":SYST:ERR?", query=True)
        if resp == "":
            return "good"  # No error
        else:
            return f"error {resp}"

    def get_system_calibration_date(self):
        return self.send_command(":SYST:INF:CAL?", query=True)

    def get_system_model(self):
        return self.send_command(":SYST:INF:MOD?", query=True)

    def get_system_serial_number(self):
        return self.send_command(":SYST:INF:SER?", query=True)

    def get_system_hardware_revision(self):
        return self.send_command(":SYST:INF:HARD?", query=True)

    def get_system_fpga_version(self):
        return self.send_command(":SYST:INF:FPGA:VER?", query=True)

    def get_system_fpga_build_date(self):
        return self.send_command(":SYST:INF:FPGA:DATE?", query=True)

    def get_system_firmware_version(self):
        return self.send_command(":SYST:INF:FIRM:VERS?", query=True)

    def get_system_firmware_date(self):
        return self.send_command(":SYST:INF:FIRM:DATE?", query=True)

    def get_system_dac_mode(self):
        return self.send_command(":SYST:INF:DAC?", query=True)

    def get_system_slot_number(self):
        return self.send_command(":SYST:INF:SLOT?", query=True)

    def get_system_scpi_version(self):
        return self.send_command(":SYST:INF:SCPI?", query=True)

    def get_system_temperature(self):
        return self.send_command(":SYST:TEMP?", query=True)

    def get_system_highest_temperature(self):
        return self.send_command(":SYST:HTP?", query=True)

    def get_system_lowest_temperature(self):
        return self.send_command(":SYST:LTP?", query=True)

    def get_system_internal_voltage(self):
        return self.send_command(":SYST:VINT?", query=True)

    def get_system_aux_voltage(self):
        return self.send_command(":SYST:VAUX?", query=True)

    def get_system_file_catalog(self):
        return self.send_command(":SYST:FILE:CAT?", query=True)

    def set_system_file(self, filepath):
        # header_and_block includes: #<header><binary>
        binary_block = filepath.encode('utf-16le')
        # Build the SCPI binary header
        header = self.make_binary_header(binary_block)
        # Send the command with binary data
        self.write_binary_data(f":SYST:FILE {header}", binary_block)

    def get_system_file_size(self):
        return self.send_command(":SYST:FILE:SIZE?", query=True)

    def set_system_file_data(self, offset, binary_block):
        # data_command contains [<offset>], #<header><binary>
        header = self.make_binary_header(binary_block)
        return self.write_binary_data(f":SYSTEM:FILE:DATA {offset}, {header}", binary_block)

    def get_system_file_data(self):
        return self.send_command(":SYSTEM:FILE:DATA?", query=True)

    def delete_system_file(self):
        """This command will delete the Proteus system file."""
        return self.send_command(":SYSTEM:FILE:DEL")

    def off(self):
        for i in range (1,5):
            ch = i
            cmd = ':INST:CHAN {0}'.format(ch)
            self.inst.send_scpi_cmd(cmd)
            cmd = ':INIT:CONT OFF'  # play waveform continuously
            self.inst.send_scpi_cmd(cmd)

            cmd = ':OUTP OFF'
            self.inst.send_scpi_cmd(cmd)

class ProteusDevice(Device):
    """Device wrapper for Proteus awg using Device framework."""
    file_transfer_completed = pyqtSignal(bool, str)

    _DEFAULT_SETTINGS = Parameter(Device._get_base_settings() +[
        Parameter('ip_address', _IP_ADDRESS, str, 'ip address'),
        Parameter('slot_id', _SID, int, 'slot id on the chassis')
    ])

    _PROBES = {
        'ip_address': 'ip_address',
        'slot_id': 'slot_id',
        'get_data': 'choose whether you need to get data from this device or not',
        'status': 'AWG device status',
    }

    def __init__(self, name=None, settings=None):
        super().__init__(name=name, settings=settings)
        self.logger = logging.getLogger(__name__)
        cfg = self.settings
        self.driver = ProteusDriver(ip_address = cfg['ip_address'], sid = cfg['slot_id'])
        # Test connection and set connection status
        self._test_connection()
        """# stop TaborInstrumentation service
        import subprocess
        service_name = "TaborInstrumentation"
        result = subprocess.run(["sc", "stop", service_name], capture_output=True, text=True, shell=True)
        print(result.stdout)
        print(result.stderr)"""

    def _test_connection(self):
        """Test if the device is reachable and set connection status."""
        try:
            # Test SCPI connection with *IDN? query
            idn = self.driver.send_command('*IDN?', query=True)
            if idn:
                self._is_connected = True
                self.logger.info(f"Connected to Proteus: {idn}")
                print(f"Connected to Proteus: {idn}")
            else:
                self._is_connected = False
                self.logger.warning("Proteus responded but ID not recognized")
        except Exception as e:
            self._is_connected = False
            self.logger.error(f"Failed to connect to Proteus: {e}")

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
                self.driver.get_system_model()
                return True
            except Exception:
                self._is_connected = False
                self.logger.warning("Proteus connection lost")
        return self._is_connected

    def setup(self):
        # Setup the Proteus device with sequence file.
        if not self.is_connected:
            self.logger.error("Cannot setup Proteus: device not connected")
            return False

        cfg = self.settings
        #seq = cfg['seq_file']

        # Set the reference clocks if needed for the Proteus device
        self.driver.set_ref_clock_external()
        time.sleep(0.1)

        # Assuming Proteus doesn't need this exact AWG520 command, so we skip it
        # self.driver.send_command('AWGC:RMOD ENH')
        # time.sleep(0.1)

        # Start the file transfer
        #self._start_file_transfer(seq)
        return True

    def _start_file_transfer(self, local_path: str):

        # Proteus: Set the file to be uploaded
        self.driver.set_task_file(local_path)
        self.driver.load_tasks_from_file(offset=0, number_of_task_table_rows=64000)
        self.logger.info(f"Started task file upload from {local_path}")

    def _on_file_transfer_finished(self, success: bool, remote_name: str):
        if success:
            self.logger.info(f"Upload succeeded: {remote_name}")

            # In Proteus, after file upload, we can configure the sequence or tasks
            # This depends on how we intend to start and manage the sequence
            self.driver.set_task_sync()  # Synchronize all tasks

            for ch in (1, 2):  # Assuming we're working with two channels
                self.driver.set_amplitude(ch)  # Configure each channel
                self.driver.set_offset(ch)
                self.driver.set_marker(ch, 1)  # Marker 1
                self.driver.set_marker(ch, 2)  # Marker 2

            self.logger.info('Proteus setup complete after file transfer')
        else:
            self.logger.error(f"Upload failed for {remote_name}")

        self.file_transfer_completed.emit(success, remote_name)

    """
    def run_sequence(self):
        self.driver.run()"""
    def start_sequence(self):
        for ch in sorted(self.driver.chan_list):
            self.driver.set_channel(ch)
            self.driver.set_marker(1)
            self.driver.set_marker_state('ON')
            self.driver.set_output("ON")
            self.driver.set_waveform_type("TASK")

    def stop_sequence(self):
        self.driver.stop()
        self.driver._close()

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
        #Turn on microwave output with 10MHz sine wave(s) for IQ modulation.
        self.driver.mw_on_sb10MHz(enable_iq)
        return 0

    def mw_off_sb10MHz(self, enable_iq=False):
        #Turn off microwave output.
        self.driver.mw_off_sb10MHz(enable_iq)
        return 0

    def set_function_generator(self, channel, function='SIN', frequency=10e6,
                               voltage=2.0, phase=0.0, enable=True):
        """Configure function generator parameters for a specific channel."""
        return self.driver.set_function_generator(channel, function, frequency, voltage, phase, enable)

    def get_function_generator_status(self, channel):
        #Get current function generator status for a specific channel.
        return self.driver.get_function_generator_status(channel)

    def enable_iq_modulation(self, frequency=10e6, voltage=2.0):
        #Enable I/Q modulation with sine and cosine waves.
        return self.driver.enable_iq_modulation(frequency, voltage)

    def disable_iq_modulation(self):
        #Disable I/Q modulation by setting both channels to 0V.
        return self.driver.disable_iq_modulation()

    def read_probes(self, key):
        if key == 'status':
            resp = self.driver.get_system_error()
            return resp
        elif key == 'get_data':
            return self.settings['get_data']
        elif key == 'ip_address':
            return self.settings['ip_address']
        elif key == 'slot_id':
            return self.settings['slot_id']
        raise KeyError(f"Unknown probe '{key}'")

    def cleanup(self):
        # Clean up resources and mark device as disconnected
        if hasattr(self, 'driver'):
            self.driver.cleanup()
        self._is_connected = False
        self.logger.info("Proteus device disconnected")

    def reconnect(self):
        """Attempt to reconnect to the Proteus device."""
        try:
            self.logger.info("Attempting to reconnect to Proteus...")
            # Recreate driver instance
            cfg = self.settings
            self.driver = ProteusDriver(
                ip_address=cfg['ip_address']
            )
            # Test connection
            self._test_connection()
            if self.is_connected:
                self.logger.info("Successfully reconnected to Proteus")
                return True
            else:
                self.logger.error("Failed to reconnect to Proteus")
                return False
        except Exception as e:
            self.logger.error(f"Reconnection failed: {e}")
            self._is_connected = False
            return False

if __name__ == "__main__":
    dev = ProteusDriver('192.168.2.4')
    dev.set_function_generator(1, 'SQU', 1000000)
    #dev.set_function_generator(4, 'SIN')
    dev.set_function_generator(3, 'SQU', 1000000)
    #dev.set_function_generator(2, 'SIN')
    #dev.set_ch1_marker1_voltage(-0.5, 0.5)
    #time.sleep(10)
    dev._close()

