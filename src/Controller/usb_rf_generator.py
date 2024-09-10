import pyvisa.errors

from src.core import Device,Parameter
import pyvisa as visa
from time import sleep

class USB_RFGenerator(Device):
    '''
    This class implements the Windfreak SynthUSBII. The device plugs into a usb port and is communicated with using pyvisa.
    '''
    _DEFAULT_SETTINGS = Parameter([
        Parameter('address','ASRL9::INSTR',str,'serial address of device'),
        Parameter('frequency',1000.0,float,'frequency in MHz'), #input 'frequency':0 to stop output
        Parameter('power',-4,[-4,-1,2,5],'power in dBm; datasheet says ±1 dBm for output'),
        Parameter('reference','internal',['external','internal'],'reference type: 1-internal / 0-external'),
        Parameter('phase_lock', 'lock', ['unlock','lock'], 'phase lock status: lock=1 / unlock=0'),
        Parameter('sweep',[
                  Parameter('freq_lower',1000.0,float,'lower frequency for sweep in MHz'),
                  Parameter('freq_upper',2000.0,float,'upper frequency for sweep in MHz'),
                  Parameter('freq_step',100.0,float,'frequency step for sweep in MHz'),
                  Parameter('time_step',0.3,float,'time step for sweep in milliseconds'),
                  Parameter('continuous_sweep',False, bool, 'If sweep is continuous '),
                  Parameter('run_sweep',False,bool,'Update to run sweep')
                  ])
    ])

    def __init__(self, name=None, settings=None):

        super(USB_RFGenerator, self).__init__(name, settings)
        try:
            self._connect()
        except pyvisa.errors.VisaIOError:
            print('No device deteched')
            raise
        except Exception as e:
            print(e)
            raise(e)

        self._send_command('o', '1')    #turns on
        self._send_command('a', self._power_to_internal(self.settings['power']))   #sets power to low by default
        self._send_command('x', self._reference_to_internal(self.settings['reference']))   #sets reference to external by default
        self._send_command('c',self._continuous_to_internal(self.settings['sweep']['continuous_sweep']))    #sets sweep to not continuous by default

    def _connect(self):
        self.rm = visa.ResourceManager()
        self.srs = self.rm.open_resource(self.settings['address'])

    def __del__(self):
        self.srs.close()

    def update(self, settings):
        """
        Updates the internal settings of the SynthUSBII, and then also updates physical parameters such as
        frequency, power, etc in the hardware
        Args:
            settings: a dictionary in the standard settings format
        """
        super(USB_RFGenerator, self).update(settings)
        for key, value in settings.items():
            if key == 'address':    #connects if address is changed
                self._connect()
            else:                   #otherwise sends corresponding command with value
                if key == 'frequency':
                    value = self._freq_check(value)
                elif key == 'power':
                    value = self._power_to_internal(value)
                elif key == 'reference':
                    value = self._reference_to_internal(value)
                elif key == 'phase_lock':
                    value = self._phase_to_internal(value)
                elif key == 'sweep':
                    for param, param_value in value.items():  #iterates through sub settings of sweep parameter
                        if param == 'freq_lower' or param == 'freq_upper':
                            value = self._freq_check(param_value)
                        elif param == 'freq_step' or param == 'time_step':
                            value = float(param_value)
                        elif param == 'continuous_sweep':
                            value = self._continuous_to_internal(param_value)
                        elif param == 'run_sweep':
                            if param_value == True:
                                value = '1' #Run sweep needs to be a STRING 1 for some reason
                                self.settings['sweep']['run_sweep'] = False     #turns False after running a sweep
                        sweep_key = self._param_to_internal(param)
                        if self._settings_initialized:
                            self._send_command(sweep_key,value)   #sends commands for sweep sub parameters

                if key != 'sweep':  #'sweep' is not a valid command so skips it since correct commands have already been sent
                    key = self._param_to_internal(key)
                    if self._settings_initialized:
                        self._send_command(key,value)

    def sweep(self,lower_freq,upper_freq,step_size,time_step, continuous=False):
        '''
        Basic sweep function if needed. All functionality is also in the update method
        '''
        if continuous:
            self._send_command('c',1)
        elif not continuous:
            self._send_command('c', 0)
        else:
            lower, upper, step, time = float(lower_freq), float(upper_freq), float(step_size), float(time_step)
            self._send_command('l',lower)       #lower freq
            self._send_command('u',upper)       #upper freq
            self._send_command('s',step)        #freq step
            self._send_command('t',time)        #time step in milliseconds
            self._send_command('g','1')   #runs sweep
            print('Running Sweep')

    def _send_command(self,command_letter,value):
        '''
        Sends command to device. Letters are given in _params_to_internal and in manual
        '''
        self.srs.write(f'{command_letter}{value}')
        sleep(0.15)     #sleep time to ensure a second command is not sent before the first one is processed
                        #error occured with sleep of 0.14 seconds

    def _ask_value(self,command_letter):
        self.srs.write(f'{command_letter}?')
        sleep(0.15)
        return self.srs.read().strip()

    @property
    def _PROBES(self):
        return{
            'frequency':'frequency of output in Hz',
            'power':'power of output with -4dBm=minimum, 5dBm=maximmum',
            'reference':'internal or external reference',
            'phase_lock':'phase lock status',
            'freq_lower':'lower frequency for sweep',
            'freq_upper':'upper frequency for sweep',
            'freq_step':'frequency step for sweep',
            'time_step':'time step for sweep',
            'continuous_sweep':'if continuous sweep is enabled'
        }

    def read_probes(self, key):
        assert(self._settings_initialized)
        assert key in list(self._PROBES.keys())

        key_internal = self._param_to_internal(key)
        if key == 'power':
            value = self._internal_to_power(self._ask_value(key_internal))
        elif key == 'reference':
            value = self._internal_to_reference(self._ask_value(key_internal))
        elif key == 'phase_lock':
            value = self._internal_to_phase(self._ask_value(key_internal))
        elif key == 'continuous_sweep':
            value = self._internal_to_continuous(self._ask_value(key_internal))
        else:   #for frequency queries will return in Hz
            value = self._ask_value(key_internal)

        return value

    @property
    def is_connected(self):
        try:
            self._ask_value('f')    #arbitrary call to check connection
            return True
        except pyvisa.errors.VisaIOError:
            return False

    def close(self):
        self._send_command('f',0)   #clears frequency being generated
        self._send_command('o',0)   #turns off
        self.srs.close()

    def _param_to_internal(self, param):
        #converts settings parameter to corresponding key
        if param == 'frequency':
            return 'f'
        elif param == 'power':
            return 'a'
        elif param == 'reference':
            return 'x'
        elif param == 'phase_lock':
            return 'p'
        elif param == 'freq_lower':
            return 'l'
        elif param == 'freq_upper':
            return 'u'
        elif param == 'freq_step':
            return 's'
        elif param == 'time_step':
            return 't'
        elif param == 'continuous_sweep':
            return 'c'
        elif param == 'run_sweep':
            return 'g'
        else:
            raise KeyError

    def _freq_check(self, freq):
        #checks if frequcny is in range
        f_lower_limit = 35.0  # Mhz
        f_upper_limit = 4400.0  # Mhz / 4.4Ghz
        if (freq > f_upper_limit or freq < f_lower_limit) and freq != 0.0:
            print('Frequency out of range')
            raise ValueError
        else:
            return float(freq)

    '''
    Following functions are internal to code and help to make user inputs / read probes more understandable
    '''
    def _power_to_internal(self, power):
        #converts power level (dBm) to device value
        if power == -4:
            return 0
        elif power == -1:
            return 1
        elif power == 2:
            return 2
        elif power == 5:
            return 3
        else:
            raise KeyError

    def _internal_to_power(self, power):
        #converts device value to power level (dBm)
        if power == '0':
            return -4
        elif power == '1':
            return -1
        elif power == '2':
            return 2
        elif power == '3':
            return 5
        else:
            raise KeyError

    def _reference_to_internal(self, value):
        #converts reference type to device value
        if value == 'external':
            return 0
        elif value == 'internal':
            return 1
        else:
            raise KeyError

    def _internal_to_reference(self, value):
        #converts device value to reference type
        if value == '0':
            return 'external'
        elif value == '1':
            return 'internal'
        else:
            raise KeyError

    def _continuous_to_internal(self, value):
        #converts continuous status to device value
        if value == False:
            return 0
        elif value == True:
            return 1
        else:
            raise KeyError

    def _internal_to_continuous(self, value):
        #converts device value to continuous status
        if value == '0':
            return False
        elif value == '1':
            return True
        else:
            raise KeyError

    def _phase_to_internal(self, value):
        #converts lock status to device value
        if value == 'unlock':
            return 0
        elif value == 'lock':
            return 1
        else:
            raise KeyError

    def _internal_to_phase(self, value):
        #converts device value to lock status
        if value == '0':
            return 'unlock'
        elif value == '1':
            return 'lock'
        else:
            raise KeyError

if __name__ == '__main__':
    usb = USB_RFGenerator()
    usb.sweep(1000,2000,100,0.3)
    print(usb.read_probes('freq_step'),usb.read_probes('power'))
    usb.close()