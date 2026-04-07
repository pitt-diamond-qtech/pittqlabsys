# Created by Jannet Trabelsi on 2025-08-18
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

import pyvisa
import pyvisa.errors
from src.core import Device, Parameter

RANGE_MAX = 1
RANGE_MIN = 225000000
class Agilent53132(Device):

    _DEFAULT_SETTINGS = Parameter(Device._get_base_settings() +[
        Parameter('connection_type', 'GPIB', ['GPIB'], 'type of connection to open to controller'),
        Parameter('port', 3, list(range(0, 31)), 'GPIB port on which to connect'),
        Parameter('GPIB_num', 0, int, 'GPIB device on which to connect')
    ])

    def __init__(self, name=None, settings=None):
        super(Agilent53132, self).__init__(name, settings)
        try:
            self._connect()
        except pyvisa.errors.VisaIOError:
            print('No Universal Counter Detected!. Check that you are using the correct communication type')
            raise
        except Exception as e:
            raise e

    def _connect(self):
        rm = pyvisa.ResourceManager()
        if self.settings['connection_type'] == 'GPIB':
            self.agilent_counter = rm.open_resource(
                'GPIB' + str(self.settings['GPIB_num']) + '::' + str(self.settings['port']) + '::INSTR')
            self.agilent_counter.write("*RST")
            self.agilent_counter.write("*CLS")
            self.agilent_counter.write("*SRE 0")
            self.agilent_counter.write("*ESE 0")
            self.agilent_counter.write("STAT:PRES")
        return self.agilent_counter.query('*IDN?')

    def update(self, settings):
        super(Agilent53132, self).update(settings)
        for key, value in settings.items():
            if key == 'connection_type':
                self._connect()
            elif not (key == 'port' or key == 'GPIB_num'):
                if self.settings.valid_values[key] == bool: #converts booleans, which are more natural to store for on/off, to
                    value = int(value)                #the integers used internally in the counter
                key = self._param_to_internal(key)
                # only send update to Device if connection to Device has been established
                if self._settings_initialized:
                    self.agilent_counter.write(key + ' ' + str(value))


    @property
    def _PROBES(self):
        return{
            'get_data': 'choose whether you need to get data from this device or not',
            'frequency': 'frequency in Hz',
            'period': 'period in s',
            'phase': 'phase of input in degrees',
            'attenuation': 'attenuation',
            'coupling': 'AC or DC coupling',
            'lowpass': 'Lowpass Filter',
            'impedance': 'Impedance in OHMS',
            'calibration': 'Device calibration',
            'lpassfreq': 'Low Pass Frequency',
            'max voltage': 'max voltage',
            'min voltage': 'min voltage',
            'peak to peak': 'peak to peak'
        }

    def read_probes(self, key):
        assert(self._settings_initialized) #will cause read_probes to fail if settings (and thus also connection) not yet initialized
        assert key in list(self._PROBES.keys())
        if key == 'get_data':
            return self.settings['get_data']
        else:
            key_internal = self._param_to_internal(key)
            value = float(self.agilent_counter.query(key_internal + '?'))
            return value

    # :INPUT# read probes
    def read_probes_channel(self, key, channel_number):
        assert(self._settings_initialized) #will cause read_probes to fail if settings (and thus also connection) not yet initialized
        assert key in list(self._PROBES.keys())
        channel = self.channel_selection(channel_number)
        key_internal = self._param_to_internal(key)
        if key in ['frequency', 'period']:
            self.agilent_counter.write('CONF:FREQ (@' + str(channel_number)+')')
            self.agilent_counter.write("INIT")
            value = self.agilent_counter.query(key_internal + '?')
        elif key in ['max voltage', 'min voltage', 'peak to peak']:
            value = self.agilent_counter.query(key_internal + '? (@' + str(channel_number)+')')
        else:
            value = self.agilent_counter.query(channel + key_internal + '?')
        return value

    @property
    def is_connected(self):
        try:
            self.agilent_counter.query('*IDN?') # arbitrary call to check connection, throws exception on failure to get response
            return True
        except pyvisa.errors.VisaIOError:
            return False


    def _param_to_internal(self, param):
        """
        Converts settings parameters to the corresponding key used for GPIB commands in the counter.
        Args:
            param: settings parameter, ex. enable_output

        Returns: GPIB command, ex. ENBR
        """
        if param == 'frequency':
            return 'FETCH:FREQUENCY'
        elif param == 'period':
            return 'FETCH:PERIOD'
        elif param == 'phase':
            return 'MEASure:phase'
        # need to call it this way: print(ag.read_probes_channel('attenuation', 1)) #1 is channel number you can do any channel number
        elif param == 'attenuation':
            return ':ATTENUATION'
        # need to call it this way: print(ag.read_probes_channel('coupling', 1)) #1 is channel number you can do any channel number
        elif param == 'coupling':
            return ':COUPLING'
        # need to call it this way: print(ag.read_probes_channel('lowpass', 1)) #1 is channel number you can do any channel number
        elif param == 'lowpass':
            return ':FILTER:LPASS:STATE'
        # need to call it this way: print(ag.read_probes_channel('impedance', 1)) #1 is channel number you can do any channel number
        elif param == 'impedance':
            return ':IMPEDANCE'
        elif param == 'calibration':
            return ':CALIBRATION:ALL'
        #need to call it this way: print(ag.read_probes_channel('lpassfreq', 1)) #1 is channel number you can do any channel number
        elif param == 'lpassfreq':
            return ':FILTER:LPASS:FREQUENCY'
        elif param == 'max voltage':
            return ':MEASURE:SCALAR:VOLTAGE:MAX'
        elif param == 'min voltage':
            return ':MEASURE:SCALAR:VOLTAGE:MIN'
        elif param == 'peak to peak':
            return ':MEASURE:SCALAR:VOLTAGE:PTP'
        else:
            raise KeyError

    def measure_time_interval(self):
        print("\nTime Interval from 1 to 2 measured using MEAS:TINT? (@1),(@2)")
        result = self.agilent_counter.query("MEAS:TINT? (@1),(@2)")
        print("Time Interval 1 to 2 = " + result)

    #returns channel number command as :INPUT#
    def channel_selection(self, channel_number):
        if channel_number == 1 or channel_number == 2 or channel_number == 3:
            result =':INPUT'+str(channel_number)
        else:
            raise KeyError
        return result

    #abort measurement as quickly as possible
    def abort(self):
        self.agilent_counter.write(':ABORT')

    # set methods:

    #setting attenuation
    def set_attenuation(self, channel_number, value):
        channel = self.channel_selection(channel_number)
        if value == 1:
            self.agilent_counter.write(channel+':ATTENUATION 1')
        elif value == 10:
            self.agilent_counter.write(channel + ':ATTENUATION 10')
        else:
            raise KeyError

    #coupling: PLEASE NOTE THAT YOU CAN ONLY SET CHANNEL 1 OR 2, BUT FOR CHANNEL 3 YOU CAN ONLY QUERY
    def set_coupling(self, channel_number, Current):
        channel = self.channel_selection(channel_number)
        if Current == 'AC':
            self.agilent_counter.write(channel+':COUPLING AC')
        elif Current == 'DC':
            self.agilent_counter.write(channel+':COUPLING DC')
        else:
            raise KeyError

    def set_lowpass(self, channel_number, ENABLE):
        channel = self.channel_selection(channel_number)
        if ENABLE == True:
            self.agilent_counter.write(channel+':FILTER:LPASS:STATE 1')
        else:
            self.agilent_counter.write(channel + ':FILTER:LPASS:STATE 0')

    #: PLEASE NOTE THAT YOU CAN ONLY SET CHANNEL 1 OR 2, BUT FOR CHANNEL 3 YOU CAN ONLY QUERY
    def set_impedance(self, channel_number, value):
        channel = self.channel_selection(channel_number)
        if value == 50 or value == 1000000:
            self.agilent_counter.write(channel + ':IMPEDANCE ' + str(value))
        else:
            raise KeyError

    #enable/disable display on counter screen
    def display(self, EN):
        if EN == 1:
            self.agilent_counter.write(':DISP:ENABLE 1') #ENABLE
        elif EN == 0:
            self.agilent_counter.write(':DISP:ENABLE 0') #DISABLE
        else:
            raise KeyError

    #get methods:
    def get_frequency(self, channel_number):
        return self.read_probes_channel('frequency', channel_number)
    def get_period(self, channel_number):
        return self.read_probes_channel('period', channel_number)
    def get_phase(self):
        return self.read_probes('phase')
    def get_attenuation(self, channel_number):
        return self.read_probes_channel('attenuation', channel_number)
    def get_coupling(self, channel_number):
        return self.read_probes_channel('coupling', channel_number)
    def get_lowpass(self, channel_number):
        return self.read_probes_channel('lowpass', channel_number)
    def get_impedance(self, channel_number):
        return self.read_probes_channel('impedance', channel_number)
    def get_calibration(self, channel_number):
        return self.read_probes_channel('calibration', channel_number)
    def get_lowpass_frequency(self, channel_number):
        return self.read_probes_channel('lpassfreq', channel_number)
    def get_max_voltage(self, channel_number):
        return self.read_probes_channel('max voltage', channel_number)
    def get_min_voltage(self, channel_number):
        return self.read_probes_channel('min voltage', channel_number)
    def get_peak_to_peak(self, channel_number):
        return self.read_probes_channel('peak to peak', channel_number)
"""
    def wait_for_out_of_limit_period(self, lower_limit, upper_limit, channel=1, timeout=10):

        # Set up period measurement on desired channel
        self.agilent_counter.write(f":FUNC 'PER {channel}'")
        self.agilent_counter.write(":FREQ:ARM:STAR:SOUR IMM")
        self.agilent_counter.write(":FREQ:ARM:STOP:SOUR IMM")

        # Set up limit checking
        self.agilent_counter.write(":CALC2:LIM:STAT ON")
        self.agilent_counter.write(":CALC2:LIM:DISP GRAP")
        self.agilent_counter.write(f":CALC2:LIM:LOWER {lower_limit}")
        self.agilent_counter.write(f":CALC2:LIM:UPPER {upper_limit}")
        self.agilent_counter.write(":INIT:AUTO ON")

        # Enable SRQ on questionable status
        self.agilent_counter.write(":STAT:QUES:ENAB 1024")
        self.agilent_counter.write("*SRE 8")
        self.agilent_counter.write("INIT:CONT ON")

        print("Monitoring for out-of-limit period value...")

        start_time = time.time()
        while True:
            status_byte = self.agilent_counter.read_stb()
            if status_byte & 0x08:
                break
            if time.time() - start_time > timeout:
                raise TimeoutError("Timeout waiting for out-of-limit condition.")
            time.sleep(0.1)

        period = float(self.agilent_counter.query("FETCH:PERIOD?"))
        print(f"Out-of-limit period detected: {period:.3e} s")
        return period
"""
if __name__ == '__main__':

    ag = Agilent53132()
    print(ag._connect())

    #TESTS RAN SUCCESSULLY (YOU NEED A FUNCTINO GENERATOR TO TEST:
    #print(ag.read_probes('calibration'))  # return 0 if successful
    print(ag.read_probes_channel('frequency', 1))
    print(ag.read_probes_channel('period', 1))
    #print(ag.read_probes_channel('frequency', 2))
    #print(ag.read_probes_channel('period', 2))
    #print(ag.read_probes('phase'))
    #ag.measure_time_interval()
    #print(ag.read_probes_channel('lpassfreq', 1))
    #print(ag.read_probes_channel('attenuation', 1))
    #ag.set_attenuation(1, 10)
    #print(ag.read_probes_channel('attenuation', 1))
    #print(ag.read_probes_channel('coupling', 1))
    #ag.set_coupling(1, 'DC')
    #print(ag.read_probes_channel('coupling', 1))
    #ag.set_coupling(1, 'AC')
    #print(ag.read_probes_channel('lowpass', 1))
    #ag.set_lowpass(1, 1)
    #print(ag.read_probes_channel('lowpass', 1))
    #ag.set_lowpass(1, 0)
    #print(ag.read_probes_channel('lowpass', 1))
    #print(ag.read_probes_channel('impedance', 1))
    #ag.set_impedance(1,50)
    #print(ag.read_probes_channel('impedance', 1))
    #ag.set_impedance(1, 1.00000E+006)
    #print(ag.read_probes_channel('impedance', 1))
    #ag.display(0)
    #ag.display(1)
    #print(ag.read_probes_channel('max voltage', 2))
    #print(ag.read_probes_channel('min voltage', 2))
    #print(ag.read_probes_channel('peak to peak', 2))
    #print(ag.read_probes_channel('peak to peak', 2))
    """
    try:
        ag.wait_for_out_of_limit_period(
            lower_limit=5e-7,
            upper_limit=1e-6,
            channel=1,
            timeout=15
        )
    except TimeoutError as e:
        print("No out-of-limit condition detected:", e)
    """
    print('done')