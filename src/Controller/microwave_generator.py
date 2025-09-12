# Created by Gurudev Dutt <gdutt@pitt.edu> on 2023-08-02
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

import pyvisa as visa
import pyvisa.errors
import socket

from src.core import Parameter, Device

# RANGE_MIN = 2025000000 #2.025 GHz
RANGE_MIN = 1012500000
RANGE_MAX = 4050000000 #4.050 GHZ

class MicrowaveGenerator(Device):
    """
    This class implements the Stanford Research Systems SG384 microwave generator. The class commuicates with the
    device over GPIB using pyvisa or LAN using socket.
    """
        # SHOULD BE 4
    ## GD: watch out for the ports this might be different on each computer and might cause issues when running export default
    _DEFAULT_SETTINGS = Parameter([
        Parameter('connection_type', 'LAN', ['GPIB', 'RS232', 'LAN'], 'type of connection to open to controller'),
        Parameter('port', 5025, int, 'GPIB, COM, or LAN port on which to connect'),
        Parameter('GPIB_num', 0, int, 'GPIB device on which to connect'),
        Parameter('ip_address', '169.254.146.198', str, 'ip address of signal generator'),
        Parameter('enable_output', False, bool, 'Type-N output enabled'),
        Parameter('frequency', 3e9, float, 'frequency in Hz, or with label in other units ex 300 MHz'),
        Parameter('amplitude', -60, float, 'Type-N amplitude in dBm'),
        Parameter('phase', 0, float, 'output phase'),
        Parameter('enable_modulation', True, bool, 'enable modulation'),
        Parameter('modulation_type', 'FM', ['AM', 'FM', 'PhaseM', 'Freq sweep', 'Pulse', 'Blank', 'IQ'],
                  'Modulation Type: 0= AM, 1=FM, 2= PhaseM, 3= Freq sweep, 4= Pulse, 5 = Blank, 6=IQ'),
        Parameter('modulation_function', 'External', ['Sine', 'Ramp', 'Triangle', 'Square', 'Noise', 'External'],
                  'Modulation Function: 0=Sine, 1=Ramp, 2=Triangle, 3=Square, 4=Noise, 5=External'),
        Parameter('pulse_modulation_function', 'External', ['Square', 'Noise(PRBS)', 'External'], 'Pulse Modulation Function: 3=Square, 4=Noise(PRBS), 5=External'),
        Parameter('dev_width', 32e6, float, 'Width of deviation from center frequency in FM Hz'),
        Parameter('mod_rate', 1e7, float, 'Rate of modulation [Hz]')
    ])

    def __init__(self, name=None, settings=None):

        super(MicrowaveGenerator, self).__init__(name, settings)
        #super().__init__(name,settings)

        # XXXXX MW ISSUE = START
        #===========================================
        # Issue where visa.ResourceManager() takes 4 minutes no longer happens after using pdb to debug (??? not sure why???)
        if self.settings['connection_type'] == 'LAN':
            self.addr = (self.settings['ip_address'], self.settings['port'])
            try:
                self._lan_command('*IDN?')
            except socket.error:
                print('No Microwave Controller Detected!. Check that you are using the correct communication type')
                raise
            except Exception as e:
                raise (e)
        else: #elif self.settings['connection_type'] == 'GPIB' or self.settings['connection_type'] == 'RS232':
            try:
                self._connect()
            except pyvisa.errors.VisaIOError:
                print('No Microwave Controller Detected!. Check that you are using the correct communication type')
                raise
            except Exception as e:
                raise (e)
        #XXXXX MW ISSUE = END
        #===========================================

    def _connect(self):     #for GPIB and RS232 Connections
        if self.settings['connection_type'] == 'LAN':
            return None
        else:
            rm = visa.ResourceManager()
            if self.settings['connection_type'] == 'GPIB':
                self.srs = rm.open_resource(
                    'GPIB' + str(self.settings['GPIB_num']) + '::' + str(self.settings['port']) + '::INSTR')
            else: #elif self.settings['connection_type'] == 'RS232':
                self.srs = rm.open_resource('COM' + str(self.settings['port']))
                self.srs.baud_rate = 115200
            self.srs.query('*IDN?')

    def _lan_command(self, command):    #method for sending socket command through ethernet
        query = '?' in command  # if the command has a ?, query signifies that there will be a response
        if not command.endswith('\n'):
            command += '\n'
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as mysocket:
            mysocket.connect(self.addr)
            mysocket.sendall(command.encode())
            if query:
                reply = b''
                while not reply.endswith(b'\n'):  # recives bytes until the characters \n
                    reply += mysocket.recv(1024)  # recives up to size 1024
                return reply.decode()
            else:
                return None

    #Doesn't appear to be necessary, can't manually make two sessions conflict, rms may share well
    def __del__(self):
        if self.settings['connection_type'] == 'LAN':
            pass    #LAN closes soket connection after each command is sent
        else: #elif self.settings['connection_type'] == 'GPIB' or self.settings['connection_type'] == 'RS232':
            self.srs.close()

    def update(self, settings):
        """
        Updates the internal settings of the SG384, and then also updates physical parameters such as
        frequency, amplitude, modulation type, etc in the hardware
        Args:
            settings: a dictionary in the standard settings format
        """
        super(MicrowaveGenerator, self).update(settings)
        #super().update(settings)
        # print(self.settings)
        # XXXXX MW ISSUE = START
        # ===========================================
        for key, value in settings.items():
            if key == 'connection_type':
                self._connect()
            elif key == 'ip_address' or key == 'port':
                self.addr = (self.settings['ip_address'], self.settings['port'])    #updates socket address
            elif not (key == 'port' or key == 'GPIB_num'):
                if self.settings.valid_values[key] == bool:  # converts booleans, which are more natural to store for on/off, to
                    value = int(value)  # the integers used internally in the SRS
                elif key == 'modulation_type':
                    value = self._mod_type_to_internal(value)
                elif key == 'modulation_function':
                    value = self._mod_func_to_internal(value)
                elif key == 'pulse_modulation_function':
                    value = self._pulse_mod_func_to_internal(value)
                # elif key == 'frequency':
                #     if value > RANGE_MAX or value < RANGE_MIN:
                #         raise ValueError("Invalid frequency. All frequencies must be between 2.025 GHz and 4.050 GHz.")
                key = self._param_to_internal(key)

                # only send update to Device if connection to Device has been established
                if self._settings_initialized:
                    if self.settings['connection_type'] == 'LAN':
                        self._lan_command(key + ' ' + str(value))
                    else: #elif self.settings['connection_type'] == 'GPIB' or self.settings['connection_type'] == 'RS232':
                        self.srs.write(key + ' ' + str(value))  # frequency change operation timed using timeit.timeit and
                        # completion confirmed by query('*OPC?'), found delay of <10ms
                    # ER 20180904
                # if key == 'FREQ':
                #     print('frequency set to: ', float(self.srs.query('FREQ?')))
                # print(self.srs.query('*OPC?'))

        # XXXXX MW ISSUE = END
        # ===========================================

    @property
    def _PROBES(self):
        return{
            'enable_output': 'if type-N output is enabled',
            'frequency': 'frequency of output in Hz',
            'amplitude': 'type-N amplitude in dBm',
            'phase': 'phase',
            'enable_modulation': 'is modulation enabled',
            'modulation_type': 'Modulation Type: 0= AM, 1=FM, 2= PhaseM, 3= Freq sweep, 4= Pulse, 5 = Blank, 6=IQ',
            'modulation_function': 'Modulation Function: 0=Sine, 1=Ramp, 2=Triangle, 3=Square, 4=Noise, 5=External',
            'pulse_modulation_function': 'Pulse Modulation Function: 3=Square, 4=Noise(PRBS), 5=External',
            'dev_width': 'Width of deviation from center frequency in FM',
            'mod_rate': 'Rate of modulation in Hz'
        }

    def read_probes(self, key):
        # assert hasattr(self, 'srs') #will cause read_probes to fail if connection not yet established, such as when called in init
        assert (self._settings_initialized)  # will cause read_probes to fail if settings (and thus also connection) not yet initialized
        assert key in list(self._PROBES.keys())

        # query always returns string, need to cast to proper return type
        if key in ['enable_output', 'enable_rf_output', 'enable_modulation']:
            key_internal = self._param_to_internal(key)
            if self.settings['connection_type'] == 'LAN':
                value = int(self._lan_command(key_internal + '?'))
            else: #elif self.settings['connection_type'] == 'GPIB' or self.settings['connection_type'] == 'RS232':
                value = int(self.srs.query(key_internal + '?'))
            if value == 1:
                value = True
            elif value == 0:
                value = False
        elif key in ['modulation_type', 'modulation_function', 'pulse_modulation_function']:
            key_internal = self._param_to_internal(key)
            if self.settings['connection_type'] == 'LAN':
                value = int(self._lan_command(key_internal + '?'))
            else: #elif self.settings['connection_type'] == 'GPIB' or self.settings['connection_type'] == 'RS232':
                value = int(self.srs.query(key_internal + '?'))
            if key == 'modulation_type':
                value = self._internal_to_mod_type(value)
            elif key == 'modulation_function':
                value = self._internal_to_mod_func(value)
            elif key == 'pulse_modulation_function':
                value = self._internal_to_pulse_mod_func(value)
        else:
            key_internal = self._param_to_internal(key)
            if self.settings['connection_type'] == 'LAN':
                value = float(self._lan_command(key_internal + '?'))
            else: #elif self.settings['connection_type'] == 'GPIB' or self.settings['connection_type'] == 'RS232':
                value = float(self.srs.query(key_internal + '?'))

        return value

    @property
    def is_connected(self):
        if self.settings['connection_type'] == 'LAN':
            try:
                self._lan_command('*IDN?')  # arbitrary call to check connection, throws exception on failure to get response
                return True
            except socket.error:
                return False
        else: #elif self.settings['connection_type'] == 'GPIB' or self.settings['connection_type'] == 'RS232':
            try:
                self.srs.query('*IDN?')  # arbitrary call to check connection, throws exception on failure to get response
                return True
            except pyvisa.errors.VisaIOError:
                return False

    def close(self):  # dont need close for ethernet connection
        if self.settings['connection_type'] == 'LAN':
            pass
        else: #elif self.settings['connection_type'] == 'GPIB' or self.settings['connection_type'] == 'RS232':
            try:
                self.srs.close()
                return True
            except pyvisa.errors.VisaIOError:
                return False

    def _param_to_internal(self, param):
        """
        Converts settings parameters to the corresponding key used for GPIB commands in the SRS.
        Args:
            param: settings parameter, ex. enable_output

        Returns: GPIB command, ex. ENBR

        """
        if param == 'enable_output':
            return 'ENBR'
        if param == 'enable_rf_output':
            return 'ENBL'
        elif param == 'frequency':
            return 'FREQ'
        elif param == 'amplitude':
            return 'AMPR'
        elif param == 'amplitude_rf':
            return 'AMPL'
        elif param == 'phase':
            return 'PHAS'
        elif param == 'enable_modulation':
            return 'MODL'
        elif param == 'modulation_type':
            return 'TYPE'
        elif param == 'modulation_function':
            return 'MFNC'
        elif param == 'pulse_modulation_function':
            return 'PFNC'
        elif param == 'dev_width':
            return 'FDEV'
        elif param == 'mod_rate':
            return 'RATE'
        else:
            raise KeyError

    def _mod_type_to_internal(self, value):
        #COMMENT_ME
        if value == 'AM':
            return 0
        elif value == 'FM':
            return 1
        elif value == 'PhaseM':
            return 2
        elif value == 'Freq sweep':
            return 3
        elif value == 'Pulse':
            return 4
        elif value == 'Blank':
            return 5
        elif value == 'IQ':
            return 6
        else:
            raise KeyError

    def _internal_to_mod_type(self, value):
        #COMMENT_ME
        if value == 0:
            return 'AM'
        elif value == 1:
            return 'FM'
        elif value == 2:
            return 'PhaseM'
        elif value == 3:
            return 'Freq sweep'
        elif value == 4:
            return 'Pulse'
        elif value == 5:
            return 'Blank'
        elif value == 6:
            return 'IQ'
        else:
            raise KeyError

    def _mod_func_to_internal(self, value):
        #COMMENT_ME
        if value == 'Sine':
            return 0
        elif value == 'Ramp':
            return 1
        elif value == 'Triangle':
            return 2
        elif value == 'Square':
            return 3
        elif value == 'Noise':
            return 4
        elif value == 'External':
            return 5
        else:
            raise KeyError

    def _internal_to_mod_func(self, value):
        #COMMENT_ME
        mapping = {
            0: 'Sine',
            1: 'Ramp',
            2: 'Triangle',
            3: 'Square',
            4: 'Noise',
            5: 'External'
        }
        if value not in mapping:
            raise KeyError
        return mapping[value]

    def _pulse_mod_func_to_internal(self, value):
        #COMMENT_ME
        mapping = {
            'Square': 3,
            'Noise(PRBS)': 4,
            'External': 5
        }
        if value not in mapping:
            raise KeyError
        return mapping[value]

    def _internal_to_pulse_mod_func(self, value):
        #COMMENT_ME
        mapping = {
            3: 'Square',
            4: 'Noise(PRBS)',
            5: 'External'
        }
        if value not in mapping:
            raise KeyError
        return mapping[value]




class SG384(MicrowaveGenerator):
    """
    Just a clone of MicrowaveGenerator, except that this only allows Type-N output
    """

    _DEFAULT_SETTINGS = Parameter([
        Parameter('connection_type', 'LAN', ['GPIB', 'RS232', 'LAN'], 'type of connection to open to controller'),
        Parameter('port', 5025, int, 'GPIB, COM, or LAN port on which to connect'),
        ## JG: what out for the ports this might be different on each computer and might cause issues when running export default
        Parameter('GPIB_num', 0, int, 'GPIB device on which to connect'),
        Parameter('ip_address', '169.254.146.198', str, 'ip address of signal generator')
    ])

class RFGenerator(MicrowaveGenerator):
    """
    Just a clone of MWGenerator, except that this only allows BNC output
    """

    _DEFAULT_SETTINGS = Parameter([
        Parameter('connection_type', 'LAN', ['GPIB', 'RS232', 'LAN'], 'type of connection to open to controller'),
        Parameter('port', 5025, int, 'GPIB, COM, or LAN port on which to connect'),
        ## JG: what out for the ports this might be different on each computer and might cause issues when running export default
        Parameter('GPIB_num', 0, int, 'GPIB device on which to connect'),
        Parameter('ip_address', '169.254.146.198', str, 'ip address of signal generator'),
        Parameter('enable_rf_output', False, bool, 'BNC output enabled'),
        Parameter('frequency', 3e9, float, 'frequency in Hz, or with label in other units ex 300 MHz'),
        Parameter('amplitude_rf', -60, float, 'BNC amplitude in dBm'),
        Parameter('phase', 0, float, 'output phase'),
        Parameter('enable_modulation', True, bool, 'enable modulation'),
        Parameter('modulation_type', 'FM', ['AM', 'FM', 'PhaseM', 'Freq sweep', 'Pulse', 'Blank', 'IQ'],
                  'Modulation Type: 0= AM, 1=FM, 2= PhaseM, 3= Freq sweep, 4= Pulse, 5 = Blank, 6=IQ'),
        Parameter('modulation_function', 'External', ['Sine', 'Ramp', 'Triangle', 'Square', 'Noise', 'External'],
                  'Modulation Function: 0=Sine, 1=Ramp, 2=Triangle, 3=Square, 4=Noise, 5=External'),
        Parameter('pulse_modulation_function', 'External', ['Square', 'Noise(PRBS)', 'External'],
                  'Pulse Modulation Function: 3=Square, 4=Noise(PRBS), 5=External'),
        Parameter('dev_width', 32e6, float, 'Width of deviation from center frequency in FM')
    ])

    @property
    def _PROBES(self):
        return{
            'enable_rf_output': 'if BNC output is enabled',
            'frequency': 'frequency of output in Hz',
            'amplitude_rf': 'BNC amplitude in dBm',
            'phase': 'phase',
            'enable_modulation': 'is modulation enabled',
            'modulation_type': 'Modulation Type: 0= AM, 1=FM, 2= PhaseM, 3= Freq sweep, 4= Pulse, 5 = Blank, 6=IQ',
            'modulation_function': 'Modulation Function: 0=Sine, 1=Ramp, 2=Triangle, 3=Square, 4=Noise, 5=External',
            'pulse_modulation_function': 'Pulse Modulation Function: 3=Square, 4=Noise(PRBS), 5=External',
            'dev_width': 'Width of deviation from center frequency in FM'
        }

if __name__ == '__main__':
    mw = MicrowaveGenerator(settings={'connection_type':'LAN'})
    print(mw.is_connected)
    mw.update({'frequency':2e9})
    print("Frequency is {} Hz".format(mw.read_probes('frequency')))
    mw.close()

