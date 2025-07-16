# Created by Gurudev Dutt on 2023-07-31
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

from src.core import Device, Parameter
from PyQt5.QtCore import QThread
import random, time
import numpy as np

class ExampleDevice(Device):
    '''
    Dummy device
    a implementation of a dummy device
    '''

    _DEFAULT_SETTINGS = Parameter([
        Parameter('test1', 0, int, 'some int parameter'),
        Parameter('output probe2', 0, int, 'return value of probe 2 (int)'),
        Parameter('test2', [Parameter('test2_1', 'string', str, 'test parameter (str)'),
                            Parameter('test2_2', 0.0, float, 'test parameter (float)')
                            ])
    ])

    _PROBES = {'value1': 'this is some value from the device',
               'value2': 'this is another',
               'internal': 'gives the internal state variable',
               'deep_internal': 'gives another internal state variable'
               }

    def __init__(self, name =  None, settings = None):
        self._test_variable = 1
        super(ExampleDevice, self).__init__(name, settings)
        self._internal_state = None
        self._internal_state_deep = None


    def update(self, settings):
        '''
        updates the internal dictionary and sends changed values to device
        Args:
            settings: parameters to be set
        # mabe in the future:
        # Returns: boolean that is true if update successful

        '''
        Device.update(self, settings)

        for key, value in settings.items():
            if key == 'test1':
                self._internal_state = value



    def read_probes(self, key):
        """
        requestes value from the device and returns it
        Args:
            key: name of requested value

        Returns: reads values from device

        """
        assert key in list(self._PROBES.keys())

        import random
        if key == 'value1':
            value = random.random()
        elif key == 'value2':
            value = self.settings['output probe2']
        elif key == 'internal':
            value = self._internal_state
        elif key == 'deep_internal':
            value = self._internal_state_deep

        return value

    @property
    def is_connected(self):
        '''
        check if device is active and connected and return True in that case
        :return: bool
        '''
        return self._is_connected


class Plant(Device, QThread):

    _DEFAULT_SETTINGS = Parameter([
        Parameter('update frequency', 20, float, 'update frequency of signal in Hz',units="Hz"),
        Parameter('noise_strength', 1.0, float, 'strength of noise'),
        Parameter('noise_bandwidth', 1.0, float, 'bandwidth of noise (Hz)'),
        Parameter('control', 0.0, float, 'set the output varariable to a given value (in the absence of noise)')
    ])

    _PROBES = {'output': 'this is some random output signal (float)'
               }

    def __init__(self, name =  None, settings = None):

        QThread.__init__(self)
        Device.__init__(self, name, settings)
        self._is_connected = True
        self._output = 0
        self.start()

    def start(self, *args, **kwargs):
        """
        start the device thread
        """
        self._stop = False

        super(Plant, self).start(*args, **kwargs)


    def quit(self, *args, **kwargs):  # real signature unknown
        """
        quit the  device thread
        """
        self.stop()
        self._stop = True
        self.msleep(2* int(1e3 / self.settings['update frequency']))
        super(Plant, self).quit(*args, **kwargs)

    def run(self):
        """
        this is the actual execution of the device thread: continuously read values from the probes
        """

        eta = self.settings['noise_strength']
        gamma = 2 * np.pi * self.settings['noise_bandwidth']
        dt = 1. / self.settings['update frequency']
        control = self.settings['control']

        self._state = self._output
        while self._stop is False:

            A = -gamma * dt

            noise = np.sqrt(2*gamma*eta)*np.random.randn()
            self._state *= (1. + A)
            self._state += noise + control
            self._output =  self._state

            self.msleep(int(1e3 / self.settings['update frequency']))



    def read_probes(self, key):
        """
        requestes value from the device and returns it
        Args:
            key: name of requested value

        Returns: reads values from device

        """
        assert key in list(self._PROBES.keys())

        if key == 'output':
            value = self._output

        return value

    @property
    def is_connected(self):
        '''
        check if device is active and connected and return True in that case
        :return: bool
        '''
        return self._is_connected


class PIController(Device):
    """
    Discrete PI control
    """
    _DEFAULT_SETTINGS = Parameter([
        Parameter('set_point', 0.0, float, 'setpoint to which to stabilize'),
        Parameter('gains', [
            Parameter('proportional', 0.0, float, 'proportional gain'),
            Parameter('integral', 0.0, float, 'integral gain')
        ]),
        Parameter('time_step', 1.0, float, 'time_step of loop'),
        Parameter('output_range', [
            Parameter('min', -10000, float, 'min allowed value for PI-loop output'),
            Parameter('max', 10000, float, 'max allowed value for PI-loop output')
        ])
    ])
    _PROBES = {}
    def __init__(self, name = None, settings = None):
        super(PIController, self).__init__(name, settings)
        self.reset()
    def update(self, settings):
        super(PIController, self).update(settings)

    def read_probes(self, key = None):

        if key is None:
            super(PIController, self).read_probes()
        else:
            assert key in list(self._PROBES.keys()), "key assertion failed %s" % str(key)

        return None

    def reset(self):
        #COMMENT_ME
        self.u_P = 0
        self.u_I = 0
        self.error = 0

    def controller_output(self, current_value):
        """
        Calculate PI output value for given reference input and feedback
        """

        set_point = self.settings['set_point']
        Kp = self.settings['gains']['proportional']
        Ki = self.settings['gains']['integral']
        output_range = self.settings['output_range']
        time_step = self.settings['time_step']

        error_new = set_point - current_value
        print(('PD- error:\t', error_new, Ki, Kp, time_step))
        #proportional action
        self.u_P = Kp * error_new * time_step
        print(('PD- self.u_P:\t', self.u_P, self.u_I))

        #integral action
        self.u_I += Kp * Ki * (error_new + self.error) / 2.0 * time_step

        self.error = error_new

        print(('PD- self.u_P:\t', self.u_P, self.u_I))

        # anti-windup
        if self.u_P + self.u_I > output_range['max']:
            self.u_I = output_range['max']-self.u_P
        if self.u_P + self.u_I < output_range['min']:
            self.u_I = output_range['min']-self.u_P


        output = self.u_P + self.u_I
        print(('PD- output:\t', output))
        return output

if __name__ == '__main__':

    d = Plant()
    print((d.settings))
    for i in range(15):
        time.sleep(0.1)
        print((d.read_probes('output')))
    d.save_aqs("C:\\Users\\l00055843\\PycharmProjects\\AQuISS\\aqsfiles\\example_device.aqs")
    print('done')