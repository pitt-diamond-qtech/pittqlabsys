# Created by Jannet Trabelsi on 2025-09-22
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
"""Please Note: This device has a BaudRate of 921600, and it is not even written in their manual.
Command Format:
Commands are two-letter ASCII commands with optional address prefix (nn).
Format: nn AA xx where
nn is the controller address (optional or required depending on context)
AA is the command
xx is an optional parameter or ? to query
Command Terminator:
CR + LF (\r\n) is the required command terminator (carriage return + line feed, ASCII 13 + 10).
Controller executes command only after it receives this full terminator.
All commands must be terminated with CRLF.
Commands with address:
You can prefix the command with the controller address (e.g., 14SA?) if needed.
The controller echoes back the full command before the response.
State machine:
The controller must be initialized and homed (OR command) before moves.
Some commands only valid in certain states.
The controller boots into NOT REFERENCED state, must be homed to get to READY.
Command execution time:
Query commands (like TP? or SA?) respond fast (~10 ms).
Move commands may take seconds, but controller can handle other commands during motion.
Error handling:
The controller stores errors, accessible with TE command."""

import pyvisa
from src.core import Device, Parameter
import re
import time

_min_acceleration = pow(10, -6)
_max_acceleration = pow(10, 12)
_min_backlash = 0
_max_backlash = pow(10, 12)
_min_hysteresis = 0
_max_hysteresis = pow(10, 12)
_min_voltage = 12
_max_voltage = 48
_min_cutoff_frequency = pow(10,-6)
_max_cutoff_frequency = 2000
_min_error_limit = pow(10,-6)
_max_error_limit = pow(10,12)
_min_friction_compensation = 0
_min_model_number = 1
_max_model_number = 31
_min_jerk_time = 0.001
_max_jerk_time = pow(10,12)
_min_derivative_gain= 0
_max_derivative_gain = pow(10,12)
_min_integral_gain = 0
_max_integral_gain = pow(10,12)
_min_proportional_gain = 0
_max_proportional_gain = pow(10,12)
_min_velocity_feed_forward = 0
_max_velocity_feed_forward = pow(10,12)
_min_home_high_velocity = pow(10,-6)
_max_home_high_velocity = pow(10,12)
_min_home_timeout = 1
_max_home_timeout = 1000
_min_displacement = pow(10,-6)
_max_displacement = pow(10,12)
_min_peak_current_limit = 0.05
_max_peak_current_limit = 0.30
_min_rms_current_limit = 0.05
_max_rms_current_limit = 0.15
_min_rms_current_averaging_time = 0.01
_max_rms_current_averaging_time = 100
_min_negative_software_limit = -pow(10,-12)
_max_negative_software_limit = 0
_min_positive_software_limit = 0
_max_positive_software_limit = pow(10,12)
_min_increment_value = pow(10,-6)
_max_increment_value = pow(10,12)
_min_velocity = pow(10,-6)
_max_velocity = pow(10,12)
_server_port = 5004

class Newport_CONEX_CC_xy_stage(Device):
    _DEFAULT_SETTINGS = Parameter(Device._get_base_settings() +[
        Parameter('connection_type', "SERIAL", ["SERIAL"], 'type of connection to open to controller'),
        Parameter('xport', 14, list(range(0, 31)), 'COM port on which to connect'),
        Parameter('x-address', 1, int, 'address prefix (nn)'),
        Parameter('yport', 15, list(range(0, 31)), 'COM port on which to connect'),
        Parameter('y-address', 1, int, 'address prefix (nn)'),
        Parameter('x-position', 0, float,'position of x axis in microns'),
        Parameter('y-position', 0,float,'position of y axis in microns'),
        Parameter('server_port', _server_port, int, 'server_port'),
    ])

    def __init__(self, name=None, settings=None):
        super(Newport_CONEX_CC_xy_stage, self).__init__(name, settings)
        try:
            self._connect()
        except pyvisa.errors.VisaIOError:
            print('No stage Detected!. Check that you are using the correct communication type')
            raise
        except Exception as e:
            raise e

    def _connect(self):
        rm = pyvisa.ResourceManager()
        if self.settings['connection_type'] == "SERIAL":
            self.newport_conex_cc_x_stage = rm.open_resource('ASRL' + str(self.settings['xport']) + '::INSTR')
            self.newport_conex_cc_y_stage = rm.open_resource('ASRL' + str(self.settings['yport']) + '::INSTR')
            print("newport_conex_cc_x_stage Connected.")
            print("newport_conex_cc_y_stage Connected.")
            self.newport_conex_cc_x_stage.baud_rate = 921600
            self.newport_conex_cc_x_stage.data_bits = 8
            self.newport_conex_cc_x_stage.parity = pyvisa.constants.Parity.none
            self.newport_conex_cc_x_stage.stop_bits = pyvisa.constants.StopBits.one
            self.newport_conex_cc_x_stage.timeout = 2 * 1000
            self.newport_conex_cc_y_stage.baud_rate = 921600
            self.newport_conex_cc_y_stage.data_bits = 8
            self.newport_conex_cc_y_stage.parity = pyvisa.constants.Parity.none
            self.newport_conex_cc_y_stage.stop_bits = pyvisa.constants.StopBits.one
            self.newport_conex_cc_y_stage.timeout = 2 * 1000
        return 0

    def close(self):
        return

    def update(self, settings):
        super(Newport_CONEX_CC_xy_stage, self).update(settings)
        for key, value in settings.items():
            if key == 'connection_type':
                self._connect()
            elif not (key == 'xport' or key == 'yport'or key == 'server_port'):
                if self.settings.valid_values[key] == bool:  # converts booleans, which are more natural to store for on/off, to
                    value = int(value)  # the integers used internally in the stage
                axis = key[0]
                print(f"setting {key}")
                key = self._param_to_internal(key)
                # only send update to Device if connection to Device has been established
                if self._settings_initialized:
                    if axis == 'x':
                        # This sends the command to the microstage
                        self.newport_conex_cc_x_stage.write(str(self.settings['x-address']) + key + str(value))
                        # This overwrites the value variable in the GUI
                        time.sleep(100) # find exact sleep time later
                        #value = self.read_probes(key)

                    else:
                        # This sends the command to the microstage
                        self.newport_conex_cc_y_stage.write(str(self.settings['y-address']) + key + str(value))
                        # This overwrites the value variable in the GUI
                        time.sleep(100) # find exact sleep time later
                        #value = self.read_probes(key)
    @property
    def _PROBES(self):
        return {
            'get_data': 'choose whether you need to get data from this device or not',
            "x acceleration": 'acceleration',
            "x backlash compensation": 'backlash compensation',
            "x hysteresis compensation": 'hysteresis compensation',
            "x driver voltage": 'driver voltage',
            "x low pass filter for Kd":'low pass filter for Kd',
            "x following error limit": 'following error limit',
            "x friction compensation": 'friction compensation',
            "x HOME search type": 'home search type',
            "x stage identifier": 'stage identifier',
            "x jerk time": 'jerk time',
            "x derivative gain": 'derivative gain',
            "x integral gain": 'integral gain',
            "x proportional gain": 'proportional gain',
            "x velocity feed forward": 'velocity feed forward',
            "x disable state": 'disable state',
            "x home search velocity": 'home search velocity',
            "x home search time-out": 'home search time-out',
            "x absolute target position": 'target position',
            "x relative target position": 'target position',
            "x motion time for a relative move": 'motion time for a relative move',
            "x configuration state": 'configuration state',
            "x motor's peak current limit": 'motor peak current limits',
            "x motor's rms current limit": 'motor rms current limits',
            "x motor's rms current averaging time": 'motor rms current averaging time',
            "x-address": 'controller address',
            "x control loop state": 'control loop state',
            "x simultaneous started move target position": 'simultaneous started move target position',
            "x negative software limit": 'negative software limit',
            "x positive software limit": 'positive software limit',
            "x encoder increment value": 'encoder increment value',
            "x command error string": 'command error string',
            "x last command error": 'last command error',
            "x set-point position": 'set point position',
            "x position": 'current position',
            "x positioner error and controller state": 'positioner error and controller state',
            "x velocity": 'velocity',
            "x controller revision information": 'controller revision information',
            "x all axis parameters": 'all axis parameters',
            "y acceleration": 'acceleration',
            "y backlash compensation": 'backlash compensation',
            "y hysteresis compensation": 'hysteresis compensation',
            "y driver voltage": 'driver voltage',
            "y low pass filter for Kd": 'low pass filter for Kd',
            "y following error limit": 'following error limit',
            "y friction compensation": 'friction compensation',
            "y HOME search type": 'home search type',
            "y stage identifier": 'stage identifier',
            "y jerk time": 'jerk time',
            "y derivative gain": 'derivative gain',
            "y integral gain": 'integral gain',
            "y proportional gain": 'proportional gain',
            "y velocity feed forward": 'velocity feed forward',
            "y disable state": 'disable state',
            "y home search velocity": 'home search velocity',
            "y home search time-out": 'home search time-out',
            "y absolute target position": 'target position',
            "y relative target position": 'target position',
            "y motion time for a relative move": 'motion time for a relative move',
            "y configuration state": 'configuration state',
            "y motor's peak current limit": 'motor peak current limits',
            "y motor's rms current limit": 'motor rms current limits',
            "y motor's rms current averaging time": 'motor rms current averaging time',
            "y-address": 'controller address',
            "y control loop state": 'control loop state',
            "y simultaneous started move target position" : 'simultaneous started move target position',
            "y negative software limit": 'negative software limit',
            "y positive software limit": 'positive software limit',
            "y encoder increment value": 'encoder increment value',
            "y command error string": 'command error string',
            "y last command error": 'last command error',
            "y set-point position": 'set point position',
            "y position": 'current position',
            "y positioner error and controller state": 'positioner error and controller state',
            "y velocity": 'velocity',
            "y controller revision information": 'controller revision information',
            "y all axis parameters": 'all axis parameters',
            "x-position": 'x position set',
            "y-position": 'y position set'
        }

    def read_probes(self, key):
        assert (
            self._settings_initialized)  # will cause read_probes to fail if settings (and thus also connection) not yet initialized
        # Strip digits from the end
        newkey = re.sub(r'\d+$', '', key).strip()
        testkey = key[0:21]
        if newkey == "x motion time for a relative move" or newkey == "y motion time for a relative move":
            displacement =key[33:]
            key = newkey
        if testkey == "x command error string" or testkey == "y command error string":
            error = key[21:]
            key = testkey
        assert key in list(self._PROBES.keys())
        key_internal = self._param_to_internal(key)
        if key_internal[0] == "x":
            if key == "x motion time for a relative move":
                return self.newport_conex_cc_x_stage.query(key_internal[1:]+displacement)
            if key == "x command error string":
                return self.newport_conex_cc_x_stage.query(key_internal[1:] + error)
            if key == "x-position":
                return self.newport_conex_cc_x_stage.query(key_internal + "?")
            return self.newport_conex_cc_x_stage.query(key_internal[1:])
        elif key_internal[0] == "y":
            if key == "y motion time for a relative move":
                return self.newport_conex_cc_y_stage.query(key_internal[1:]+displacement)
            if key == "y command error string":
                return self.newport_conex_cc_y_stage.query(key_internal[1:] + error)
            if key == "y-position":
                return self.newport_conex_cc_y_stage.query(key_internal + "?")
            return self.newport_conex_cc_y_stage.query(key_internal[1:])
        elif key == 'get_data':
            return self.settings['get_data']
        else:
            raise KeyError

    @property
    def is_connected(self):
        try:
            self.newport_conex_cc_x_stage.query(str(self.settings['x-address'])+"SA?")  # arbitrary call to check connection, throws exception on failure to get response
            self.newport_conex_cc_y_stage.query(str(self.settings['y-address'])+"SA?")
            return True
        except pyvisa.errors.VisaIOError:
            return False

    def _param_to_internal(self, param):
        """
        Converts settings parameters to the corresponding key used for ASCII commands in the stage.
        Args:
            param: settings parameter, ex. enable_output
        Returns: ASCII command, ex. ENBR
        """
        if param == "x-address":
            return "x"+str(self.settings['x-address'])+"SA?"
        if param == "y-address":
            return "y"+str(self.settings['y-address'])+"SA?"
        elif param == "x acceleration":
            return "x"+str(self.settings['x-address'])+"AC?"
        elif param == "y acceleration":
            return "y"+str(self.settings['y-address'])+"AC?"
        elif param == "x backlash compensation":
            return "x"+str(self.settings['x-address'])+"BA?"
        elif param == "y backlash compensation":
            return "y"+str(self.settings['y-address'])+"BA?"
        elif param == "x hysteresis compensation":
            return "x"+str(self.settings['x-address'])+"BH?"
        elif param == "y hysteresis compensation":
            return "y"+str(self.settings['y-address'])+"BH?"
        elif param == "x driver voltage":
            return "x"+str(self.settings['x-address'])+"DV?"
        elif param == "y driver voltage":
            return "y"+str(self.settings['y-address'])+"DV?"
        elif param == "x low pass filter for Kd":
            return "x"+str(self.settings['x-address'])+"FD?"
        elif param == "y low pass filter for Kd":
            return "y"+str(self.settings['y-address'])+"FD?"
        elif param == "x following error limit":
            return "x"+str(self.settings['x-address'])+"FE?"
        elif param == "y following error limit":
            return "y"+str(self.settings['y-address'])+"FE?"
        elif param == "x friction compensation":
            return "x"+str(self.settings['x-address'])+"FF?"
        elif param == "y friction compensation":
            return "y"+str(self.settings['y-address'])+"FF?"
        elif param == "x HOME search type":
            return "x"+str(self.settings['x-address'])+"HT?"
        elif param == "y HOME search type":
            return "y"+str(self.settings['y-address'])+"HT?"
        elif param == "x stage identifier":
            return "x"+str(self.settings['x-address'])+"ID?"
        elif param == "y stage identifier":
            return "y"+str(self.settings['y-address'])+"ID?"
        elif param == "x jerk time":
            return "x"+str(self.settings['x-address'])+"JR?"
        elif param == "y jerk time":
            return "y"+str(self.settings['y-address'])+"JR?"
        elif param == "x derivative gain":
            return "x"+str(self.settings['x-address'])+"KD?"
        elif param == "y derivative gain":
            return "y"+str(self.settings['y-address'])+"KD?"
        elif param == "x integral gain":
            return "x"+str(self.settings['x-address'])+"KI?"
        elif param == "y integral gain":
            return "y"+str(self.settings['y-address'])+"KI?"
        elif param == "x proportional gain":
            return "x"+str(self.settings['x-address'])+"KP?"
        elif param == "y proportional gain":
            return "y"+str(self.settings['y-address'])+"KP?"
        elif param == "x velocity feed forward":
            return "x"+str(self.settings['x-address'])+"KV?"
        elif param == "y velocity feed forward":
            return "y"+str(self.settings['y-address'])+"KV?"
        elif param == "x disable state":
            return "x"+str(self.settings['x-address'])+"MM?"
        elif param == "y disable state":
            return "y"+str(self.settings['y-address'])+"MM?"
        elif param == "x home search velocity":
            return "x"+str(self.settings['x-address'])+"OH?"
        elif param == "y home search velocity":
            return "y"+str(self.settings['y-address'])+"OH?"
        elif param == "x home search time-out":
            return "x"+str(self.settings['x-address'])+"OT?"
        elif param == "y home search time-out":
            return "y"+str(self.settings['y-address'])+"OT?"
        elif param == "x absolute target position":
            return "x"+str(self.settings['x-address'])+"PA?"
        elif param == "y absolute target position":
            return "y"+str(self.settings['y-address'])+"PA?"
        elif param == "x relative target position":
            return "x"+str(self.settings['x-address'])+"PR?"
        elif param == "y relative target position":
            return "y"+str(self.settings['y-address'])+"PR?"
        elif param == "x motion time for a relative move":
            return "x"+str(self.settings['x-address'])+"PT"
        elif param == "y motion time for a relative move":
            return "y"+str(self.settings['y-address'])+"PT"
        elif param == "x configuration state":
            return "x"+str(self.settings['x-address'])+"PW?"
        elif param == "y configuration state":
            return "y"+str(self.settings['y-address'])+"PW?"
        elif param == "x motor's peak current limit":
            return "x"+str(self.settings['x-address'])+"QIL?"
        elif param == "y motor's peak current limit":
            return "y"+str(self.settings['y-address'])+"QIL?"
        elif param == "x motor's rms current limit":
            return "x"+str(self.settings['x-address'])+"QIR?"
        elif param == "y motor's rms current limit":
            return "y"+str(self.settings['y-address'])+"QIR?"
        elif param == "x motor's rms current averaging time":
            return "x"+str(self.settings['x-address'])+"QIT?"
        elif param == "y motor's rms current averaging time":
            return "y"+str(self.settings['y-address'])+"QIT?"
        elif param == "x control loop state":
            return "x"+str(self.settings['x-address'])+"SC?"
        elif param == "y control loop state":
            return "y"+str(self.settings['y-address'])+"SC?"
        elif param == "x simultaneous started move target position":
            return "x"+str(self.settings['x-address'])+"SE?"
        elif param == "y simultaneous started move target position":
            return "y"+str(self.settings['y-address'])+"SE?"
        elif param == "x negative software limit":
            return "x"+str(self.settings['x-address'])+"SL?"
        elif param == "x-position":
            return "x"+str(self.settings['x-address'])+"PA"
        elif param == "y negative software limit":
            return "y"+str(self.settings['y-address'])+"SL?"
        elif param == "x positive software limit":
            return "x"+str(self.settings['x-address'])+"SR?"
        elif param == "y positive software limit":
            return "y"+str(self.settings['y-address'])+"SR?"
        elif param == "x encoder increment value":
            return "x"+str(self.settings['x-address'])+"SU?"
        elif param == "y encoder increment value":
            return "y"+str(self.settings['y-address'])+"SU?"
        elif param == "x command error string":
            return "x"+str(self.settings['x-address'])+"TB"
        elif param == "y command error string":
            return "y"+str(self.settings['y-address'])+"TB"
        elif param == "x last command error":
            return "x"+str(self.settings['x-address'])+"TE"
        elif param == "y last command error":
            return "y"+str(self.settings['y-address'])+"TE"
        elif param == "x set-point position":
            return "x"+str(self.settings['x-address'])+"TH"
        elif param == "y set-point position":
            return "y"+str(self.settings['y-address'])+"TH"
        elif param == "x position":
            return "x"+str(self.settings['x-address'])+"TP"
        elif param == "y position":
            return "y"+str(self.settings['y-address'])+"TP"
        elif param == ("x positioner error and controller state"):
            return "x"+str(self.settings['x-address'])+"TS"
        elif param == ("y positioner error and controller state"):
            return "y"+str(self.settings['y-address'])+"TS"
        elif param == "x velocity":
            return "x"+str(self.settings['x-address'])+"VA?"
        elif param == "y velocity":
            return "y"+str(self.settings['y-address'])+"VA?"
        elif param == "x controller revision information":
            return "x"+str(self.settings['x-address'])+"VE"
        elif param == "y controller revision information":
            return "y"+str(self.settings['y-address'])+"VE"
        elif param == "x all axis parameters":
            return "x"+str(self.settings['x-address'])+"ZT"
        elif param == "y all axis parameters":
            return "y"+str(self.settings['y-address'])+"ZT"
        elif param == "y-position":
            return "y"+str(self.settings['y-address'])+"PA"
        else:
            raise KeyError

    def get_address(self, axis):
        if axis == "x":
            return self.read_probes("x-address")[3:]
        if axis == "y":
            return self.read_probes("y-address")[3:]
        raise KeyError

    def get_position(self, axis):
        if axis == "x":
            return self.read_probes("x position")[3:]
        if axis == "y":
            return self.read_probes("y position")[3:]
        raise KeyError

    def get_setpoint_position(self, axis):
        if axis == "x":
            return self.read_probes("x set-point position")[3:]
        if axis == "y":
            return self.read_probes("y set-point position")[3:]
        raise KeyError

    def get_acceleration(self, axis):
        if axis == "x":
            return self.read_probes("x acceleration")[3:]
        if axis == "y":
            return self.read_probes("y acceleration")[3:]
        raise KeyError

    def get_backlash_compensation(self, axis):
        if axis == "x":
            return self.read_probes("x backlash compensation")[3:]
        if axis == "y":
            return self.read_probes("y backlash compensation")[3:]
        raise KeyError

    def get_hysteresis_compensation(self, axis):
        if axis == "x":
            return self.read_probes("x hysteresis compensation")[3:]
        if axis == "y":
            return self.read_probes("y hysteresis compensation")[3:]
        raise KeyError

    def get_driver_voltage(self, axis):
        if axis == "x":
            return self.read_probes("x driver voltage")[3:]
        if axis == "y":
            return self.read_probes("y driver voltage")[3:]
        raise KeyError

    def get_low_pass_filter_for_kd(self, axis):
        if axis == "x":
            return self.read_probes("x low pass filter for Kd")[3:]
        if axis == "y":
            return self.read_probes("y low pass filter for Kd")[3:]
        raise KeyError

    def get_following_error_limit(self, axis):
        if axis == "x":
            return self.read_probes("x following error limit")[3:]
        if axis == "y":
            return self.read_probes("y following error limit")[3:]
        raise KeyError

    def get_friction_compensation(self, axis):
        if axis == "x":
            return self.read_probes("x friction compensation")[3:]
        if axis == "y":
            return self.read_probes("y friction compensation")[3:]
        raise KeyError

    def get_home_search_type(self, axis):
        if axis == "x":
            return self.read_probes("x HOME search type")[3:]
        if axis == "y":
            return self.read_probes("y HOME search type")[3:]
        raise KeyError

    def get_stage_identifier(self, axis):
        if axis == "x":
            return self.read_probes("x stage identifier")[3:]
        if axis == "y":
            return self.read_probes("y stage identifier")[3:]
        raise KeyError

    def get_jerk_time(self, axis):
        if axis == "x":
            return self.read_probes("x jerk time")[3:]
        if axis == "y":
            return self.read_probes("y jerk time")[3:]
        raise KeyError

    def get_derivative_gain(self, axis):
        if axis == "x":
            return self.read_probes("x derivative gain")[3:]
        if axis == "y":
            return self.read_probes("y derivative gain")[3:]
        raise KeyError

    def get_integral_gain(self, axis):
        if axis == "x":
            return self.read_probes("x integral gain")[3:]
        if axis == "y":
            return self.read_probes("y integral gain")[3:]
        raise KeyError

    def get_proportional_gain(self, axis):
        if axis == "x":
            return self.read_probes("x proportional gain")[3:]
        if axis == "y":
            return self.read_probes("y proportional gain")[3:]
        raise KeyError

    def get_velocity_feed_forward(self, axis):
        if axis == "x":
            return self.read_probes("x velocity feed forward")[3:]
        if axis == "y":
            return self.read_probes("y velocity feed forward")[3:]
        raise KeyError

    def get_state(self, axis):
        """When the MM command is sent without preceding controller number or the controller
        number is 0, the MM command gets executed on all controllers.
        MM0 changes the controller’s state from READY to DISABLE. In DISABLE state the
        control loop is open and the motor is not energized . The encoder, though, is still read
        and the current position gets updated.
        MM1 changes the controller’s state from DISABLE to READY. The controller’s set
        point position is set equal to its current position and the control loop gets closed
        (depending on the closed-loop state). The residual following error gets cleared from the
        buffer and the motor gets energized.
        Returns If the sign “?” takes place of nn, this command returns the current state. Refer to the TS"""
        if axis == "x":
            return self.read_probes("x disable state")[3:]
        if axis == "y":
            return self.read_probes("y disable state")[3:]
        raise KeyError

    def get_home_search_velocity(self, axis):
        if axis == "x":
            return self.read_probes("x home search velocity")[3:]
        if axis == "y":
            return self.read_probes("y home search velocity")[3:]
        raise KeyError

    def get_home_search_timeout(self, axis):
        if axis == "x":
            return self.read_probes("x home search time-out")[3:]
        if axis == "y":
            return self.read_probes("y home search time-out")[3:]
        raise KeyError

    def get_absolute_target_position(self, axis):
        if axis == "x":
            return self.read_probes("x absolute target position")[3:]
        if axis == "y":
            return self.read_probes("y absolute target position")[3:]
        raise KeyError

    def get_relative_target_position(self, axis):
        if axis == "x":
            return self.read_probes("x relative position")
        if axis == "y":
            return self.read_probes("y relative position")
        raise KeyError

    def get_motion_time_for_a_relative_move(self, axis, displacement):
        if not (_min_displacement < displacement < _max_displacement):
            raise KeyError
        if axis == "x":
            return self.read_probes("x motion time for a relative move"+str(displacement))
        if axis == "y":
            return self.read_probes("y motion time for a relative move"+str(displacement))
        raise KeyError

    def get_configuration_state(self, axis):
        if axis == "x":
            return self.read_probes("x configuration state")[3:]
        if axis == "y":
            return self.read_probes("y configuration state")[3:]
        raise KeyError

    def get_motor_peak_current_limit(self, axis):
        if axis == "x":
            return self.read_probes("x motor's peak current limit")[3:]
        if axis == "y":
            return self.read_probes("y motor's peak current limit")[3:]
        raise KeyError

    def get_motor_rms_current_limit(self, axis):
        if axis == "x":
            return self.read_probes("x motor's rms current limit")[3:]
        if axis == "y":
            return self.read_probes("y motor's rms current limit")[3:]
        raise KeyError

    def get_motor_rms_current_averating_time(self, axis):
        if axis == "x":
            return self.read_probes("x motor's rms current averaging time")[3:]
        if axis == "y":
            return self.read_probes("y motor's rms current averaging time")[3:]
        raise KeyError

    def get_control_loop_state(self, axis):
        if axis == "x":
            return self.read_probes("x control loop state")[3:]
        if axis == "y":
            return self.read_probes("y control loop state")[3:]
        raise KeyError

    def get_simultaneous_started_move_target_position(self, axis):
        """this command returns the target position value set by
        the SE command, which is not necessarily the same as the target position set by the PA
        command."""
        if axis == "x":
            return self.read_probes("x simultaneous started move target position")[3:]
        if axis == "y":
            return self.read_probes("y simultaneous started move target position")[3:]
        raise KeyError

    def get_negative_software_limit(self, axis):
        if axis == "x":
            return float(self.read_probes("x negative software limit")[3:])
        if axis == "y":
            return float(self.read_probes("y negative software limit")[3:])
        raise KeyError

    def get_positive_software_limit(self, axis):
        if axis == "x":
            return float(self.read_probes("x positive software limit")[3:])
        if axis == "y":
            return float(self.read_probes("y positive software limit")[3:])
        raise KeyError

    def get_encoder_increment_value(self, axis):
        """The SU command sets the value for one encoder count. It defines also the system of
        units for all other parameters like travel limits, velocities, accelerations, etc. Therefore,
        it is the first parameter to be defined for any positioner.
        Example: For a positioner with an encoder resolution of 1 µm, the command
        xxSU0.001 sets 1 encoder count = 1 µm = 0.001 unit or 1 unit = 1 mm."""
        if axis == "x":
            return self.read_probes("x encoder increment value")[3:]
        if axis == "y":
            return self.read_probes("y encoder increment value")[3:]
        raise KeyError

    def get_command_error_string(self, axis):
        error=self.get_last_command_error(axis)
        if axis == "x":
            return self.read_probes("x command error string"+str(error))
        if axis == "y":
            return self.read_probes("y command error string"+str(error))
        raise KeyError

    def get_last_command_error(self, axis):
        if axis == "x":
            return self.read_probes("x last command error")[3:]
        if axis == "y":
            return self.read_probes("y last command error")[3:]
        raise KeyError

    def get_positioner_error_and_controller_state(self, axis):
        if axis == "x":
            return self.read_probes("x positioner error and controller state")[3:]
        if axis == "y":
            return self.read_probes("y positioner error and controller state")[3:]
        raise KeyError
    def get_velocity(self, axis):
        if axis == "x":
            return self.read_probes("x velocity")[3:]
        if axis == "y":
            return self.read_probes("y velocity")[3:]
        raise KeyError

    def get_controller_revision_information(self, axis):
        if axis == "x":
            return self.read_probes("x controller revision information")[4:]
        if axis == "y":
            return self.read_probes("y controller revision information")[4:]
        raise KeyError

    def get_all_axis_parameters(self, axis):
        if axis == "x":
            return self.read_probes("x all axis parameters")[3:]
        if axis == "y":
            return self.read_probes("y all axis parameters")[3:]
        raise KeyError

    def set_acceleration(self, axis, acceleration):
        if not (_min_acceleration < acceleration < _max_acceleration):
            raise KeyError
        if axis == "x":
            self.newport_conex_cc_x_stage.write(str(self.settings['x-address'])+"AC"+str(acceleration))
        elif axis == "y":
            self.newport_conex_cc_y_stage.write(str(self.settings['y-address'])+"AC"+str(acceleration))
        else:
            raise KeyError

    def set_backlash_compensation(self, axis, backlash):
        """The BA command sets the backlash compensation value. This is the value that the
        controller moves the motor in addition to the commanded distance with any move that
        reverses the direction of motion without changing the current position value (TP
        command).
        The BA command helps compensate for repeatable mechanical defects that appear
        when reversing the direction of motion, for instance mechanical play. The value 0
        disables this function. This feature can be only used when the hysteresis compensation
        (BH) is disabled."""
        if not (_min_backlash <= backlash < _max_backlash):
            raise KeyError
        if axis == "x":
            self.newport_conex_cc_x_stage.write(str(self.settings['x-address'])+"BA"+str(backlash))
        elif axis == "y":
            self.newport_conex_cc_y_stage.write(str(self.settings['y-address'])+"BA"+str(backlash))
        else:
            raise KeyError

    def set_hysteresis_compensation(self, axis, hysteresis):
        """The BH command sets the hysteresis compensation value. When set to a value different
        from zero, the controller will issue for each move in the positive direction a move of the
        commanded distance plus the hysteresis compensation value, and then a second move of
        the hysteresis compensation value in the negative direction. This motion ensures that a
        final position gets always approached from the same direction and distance and helps
        compensate for non–repeatable mechanical defects like hysteresis or mechanical
        stiffness variations.
        The value 0 disables this function. The BH command can not be used when the
        backlash compensation is enabled (BA command)."""
        if not (_min_hysteresis <= hysteresis < _max_hysteresis):
            raise KeyError
        if axis == "x":
            self.newport_conex_cc_x_stage.write(str(self.settings['x-address'])+"BH"+str(hysteresis))
        elif axis == "y":
            self.newport_conex_cc_y_stage.write(str(self.settings['y-address'])+"BH"+str(hysteresis))
        else:
            raise KeyError

    def set_driver_voltage(self, axis, voltage):
        """This command sets the max. output voltage of the driver to the motor"""
        if not (_min_voltage <= voltage <= _max_voltage):
            raise KeyError
        if axis == "x":
            self.newport_conex_cc_x_stage.write(str(self.settings['x-address'])+"DV"+str(voltage))
        elif axis == "y":
            self.newport_conex_cc_y_stage.write(str(self.settings['y-address'])+"DV"+str(voltage))
        else:
            raise KeyError

    def set_low_pass_filter_for_Kd(self, axis, cutoff_frequency):
        """In CONFIGURATION state, this command sets the value for the low pass filter cut-off
        frequency which can then be saved in the controller’s nonvolatile memory using the PW
        command. It is also the default value that will be used unless a different value is set in
        DISABLE state.
        In DISABLE state, this command allows setting a new working parameter for the low
        pass filter cut-off frequency. This value is not saved in the controller’s memory and will
        be lost after reboot"""
        if not (_min_cutoff_frequency < cutoff_frequency < _max_cutoff_frequency):
            raise KeyError
        if axis == "x":
            self.newport_conex_cc_x_stage.write(str(self.settings['x-address'])+"FD"+str(cutoff_frequency))
        elif axis == "y":
            self.newport_conex_cc_y_stage.write(str(self.settings['y-address'])+"FD"+str(cutoff_frequency))
        else:
            raise KeyError

    def set_following_error_limit(self, axis, error_limit):
        """In CONFIGURATION state, this command sets the value for the maximum allowed
        following error which can then be saved in the controller’s nonvolatile memory using
        the PW command. It is also the default value that will be used for the closed-loop
        control unless a different value is set in DISABLE state.
        The following error is the most important parameter to control motion. It is the
        difference between the set point (or theoretical) position and the current (or encoder)
        position. When the current following error exceeds the maximum allowed value, a
        following error is issued and the controller is set to DISABLE state.
        In DISABLE state, this command allows setting a new working parameter for the
        maximum allowed following error. This value is not saved in the controller’s memory
        and will be lost after reboot."""
        if not (_min_error_limit < error_limit < _max_error_limit):
            raise KeyError
        if axis == "x":
            self.newport_conex_cc_x_stage.write(str(self.settings['x-address'])+"FE"+str(error_limit))
        elif axis == "y":
            self.newport_conex_cc_y_stage.write(str(self.settings['y-address'])+"FE"+str(error_limit))
        else:
            raise KeyError

    def set_friction_compensation(self, axis, compensation):
        """In CONFIGURATION state, this command sets the value for the friction compensation
        which can then be saved in the controller’s nonvolatile memory using the PW
        command. It is also the default value that will be used for any move unless a different
        value is set in DISABLE state.
        The FF command helps minimize the following error with systems that have
        significant friction. The value for the friction compensation is the voltage that gets
        added to the output voltage whenever the set point (or theoretical) velocity is different
        from zero. The sign of this voltage is the same as the sign of the set point velocity.
        In DISABLE state, this command allows setting a new working parameter for the
        friction compensation. This value is not saved in the controller’s memory and will be
        lost after reboot."""
        DV = self.get_driver_voltage(axis)
        if not (_min_friction_compensation <= compensation < DV):
            raise KeyError
        if axis == "x":
            self.newport_conex_cc_x_stage.write(str(self.settings['x-address'])+"FF"+str(compensation))
        elif axis == "y":
            self.newport_conex_cc_y_stage.write(str(self.settings['y-address'])+"FF"+str(compensation))
        else:
            raise KeyError

    def set_home_search_type(self, axis, home_search_type):
        """This command sets the type of HOME search used with the OR command
        0 use MZ switch and encoder Index.
        1 use current position as HOME.
        2 use MZ switch only.
        3 use EoR- switch and encoder Index.
        4 use EoR- switch only."""
        if home_search_type not in [0, 1, 2, 3, 4]:
            raise KeyError
        if axis == "x":
            self.newport_conex_cc_x_stage.write(str(self.settings['x-address'])+"HT"+str(home_search_type))
        elif axis == "y":
            self.newport_conex_cc_y_stage.write(str(self.settings['y-address'])+"HT"+str(home_search_type))
        else:
            raise KeyError

    def set_stage_identifier(self, axis, model_number):
        """The ID? command return the stage identifier. When used with Newport ESP compatible
    stages (see blue label on the product), this is the identical to the Newport product name."""
        if not(_min_model_number <= model_number <= _max_model_number):
            raise KeyError
        if axis == "x":
            self.newport_conex_cc_x_stage.write(str(self.settings['x-address'])+"ID"+str(model_number))
        elif axis == "y":
            self.newport_conex_cc_y_stage.write(str(self.settings['y-address'])+"ID"+str(model_number))
        else:
            raise KeyError

    def set_jerk_time(self, axis, jerk_time):
        """In CONFIGURATION state, this command sets the value for the maximum jerk time
        which can then be saved in the controller’s nonvolatile memory using the PW
        command. It is also the default value that will be used unless a different value is set in
        DISABLE or READY state.
        Jerk is the derivative of acceleration. The jerk time defines the time to reach the needed
        acceleration. A longer jerk time reduces stress to the mechanics and smoothes motion.
        In DISABLE or READY state, this command allows setting a new working parameter
        for the maximum jerk time. This value is not saved in the controller’s memory and will
        be lost after reboot."""
        if not (_min_jerk_time < jerk_time < _max_jerk_time):
            raise KeyError
        if axis == "x":
            self.newport_conex_cc_x_stage.write(str(self.settings['x-address'])+"JR"+str(jerk_time))
        elif axis == "y":
            self.newport_conex_cc_y_stage.write(str(self.settings['y-address'])+"JR"+str(jerk_time))
        else:
            raise KeyError

    def set_derivative_gain(self, axis, kd):
        """In CONFIGURATION state, this command sets the derivative gain of the PID control
        loop which can then be saved in the controller’s nonvolatile memory using the PW
        command. It is also the default value that will be used unless a different value is set in
        DISABLE state.
        In DISABLE state, this command allows setting a new working parameter for the
        derivative gain. This value is not saved in the controller’s memory and will be lost after
        reboot."""
        if not (_min_derivative_gain <= kd < _max_derivative_gain):
            raise KeyError
        if axis == "x":
            self.newport_conex_cc_x_stage.write(str(self.settings['x-address'])+"KD"+str(kd))
        elif axis == "y":
            self.newport_conex_cc_y_stage.write(str(self.settings['y-address'])+"KD"+str(kd))
        else:
            raise KeyError

    def set_integral_gain(self, axis, ki):
        """In CONFIGURATION state, this command sets the integral gain of the PID control
        loop which can then be saved in the controller’s nonvolatile memory using the PW
        command. It is also the default value that will be used unless a different value is set in
        DISABLE state.
        In DISABLE state, this command allows setting a new working parameter for the
        derivative gain. This value is not saved in the controller’s memory and will be lost after
        reboot."""
        if not (_min_integral_gain <= ki < _max_integral_gain):
            raise KeyError
        if axis == "x":
            self.newport_conex_cc_x_stage.write(str(self.settings['x-address'])+"KI"+str(ki))
        elif axis == "y":
            self.newport_conex_cc_y_stage.write(str(self.settings['y-address'])+"KI"+str(ki))
        else:
            raise KeyError

    def set_proportional_gain(self, axis, kp):
        """In CONFIGURATION state, this command sets the proportional gain of the PID control
        loop which can then be saved in the controller’s nonvolatile memory using the PW
        command. It is also the default value that will be used unless a different value is set in
        DISABLE state.
        In DISABLE state, this command allows setting a new working parameter for the
        derivative gain. This value is not saved in the controller’s memory and will be lost after
        reboot."""
        if not (_min_proportional_gain <= kp < _max_proportional_gain):
            raise KeyError
        if axis == "x":
            self.newport_conex_cc_x_stage.write(str(self.settings['x-address'])+"KP"+str(kp))
        elif axis == "y":
            self.newport_conex_cc_y_stage.write(str(self.settings['y-address'])+"KP"+str(kp))
        else:
            raise KeyError

    def set_velocity_feed_forward(self, axis, velocity_feed_forward):
        """In CONFIGURATION state, this command sets the velocity feed forward of the PID
        control loop which can then be saved in the controller’s nonvolatile memory using the
        PW command. It is also the default value that will be used unless a different value is set
        in DISABLE state.
        In DISABLE state, this command allows setting a new working parameter for the
        derivative gain. This value is not saved in the controller’s memory and will be lost after
        reboot."""
        if not (_min_velocity_feed_forward <velocity_feed_forward < _max_velocity_feed_forward):
            raise KeyError
        if axis == "x":
            self.newport_conex_cc_x_stage.write(str(self.settings['x-address'])+"KV"+str(velocity_feed_forward))
        elif axis == "y":
            self.newport_conex_cc_y_stage.write(str(self.settings['y-address'])+"KV"+str(velocity_feed_forward))
        else:
            raise KeyError

    def set_disable_state(self, axis, enable):
        """When the MM command is sent without preceding controller number or the controller
        number is 0, the MM command gets executed on all controllers.
        MM0 changes the controller’s state from READY to DISABLE. In DISABLE state the
        control loop is open and the motor is not energized . The encoder, though, is still read
        and the current position gets updated.
        MM1 changes the controller’s state from DISABLE to READY. The controller’s set
        point position is set equal to its current position and the control loop gets closed
        (depending on the closed-loop state). The residual following error gets cleared from the
        buffer and the motor gets energized."""
        if enable not in [0,1]:
            raise KeyError
        if axis == "x":
            self.newport_conex_cc_x_stage.write(str(self.settings['x-address'])+"MM"+str(enable))
        elif axis == "y":
            self.newport_conex_cc_y_stage.write(str(self.settings['y-address'])+"MM"+str(enable))
        else:
            raise KeyError

    def set_home_search_velocity(self, axis, home_high_velocity):
        """This command sets the maximum velocity used by the controller for the HOME search"""
        if not (_min_home_high_velocity < home_high_velocity < _max_home_high_velocity):
            raise KeyError
        if axis == "x":
            self.newport_conex_cc_x_stage.write(str(self.settings['x-address'])+"OH"+str(home_high_velocity))
        elif axis == "y":
            self.newport_conex_cc_y_stage.write(str(self.settings['y-address'])+"OH"+str(home_high_velocity))
        else:
            raise KeyError

    def execute_home_search(self, axis):
        """This command starts the execution of the HOME search as defined by the H command.
        When in NOT REFERENCED state, for instance after system start, any positioner must
        first get homed with the OR command before further motion commands can get
        executed.
        The OR command gets accepted only in NOT REFERENCED state and only with no
        present hardware errors, except for end-of-run. Refer to the TS command to get
        more information on the possible hardware errors."""
        if axis == "x":
            self.newport_conex_cc_x_stage.write(str(self.settings['x-address']) + "OR")
        elif axis == "y":
            self.newport_conex_cc_y_stage.write(str(self.settings['y-address']) + "OR")
        else:
            raise KeyError

    def set_home_search_timeout(self, axis, home_timeout):
        """This command sets the time-out value for the HOME search. When the HOME search
        does not finish successfully before this time elapses, the HOME search will be aborted
        and an error gets recorded"""
        if not (_min_home_timeout < home_timeout < _max_home_timeout):
            raise KeyError
        if axis == "x":
            self.newport_conex_cc_x_stage.write(str(self.settings['x-address'])+"OT"+str(home_timeout))
        elif axis == "y":
            self.newport_conex_cc_y_stage.write(str(self.settings['y-address'])+"OT"+str(home_timeout))
        else:
            raise KeyError

    def set_position(self, axis, position):
        """The PA command initiates an absolute move. When received, the positioner will move,
        with the predefined acceleration and velocity, to the new target position specified by nn.
        The PA command gets only accepted in READY, READY T or TRACKING states,
        AND when the new target position is higher or equal to the negative software limit
        (SL), AND lower or equal to the positive software limit (SR).
        To avoid any mismatch, the controller always rounds the new target position to the
        closest encoder position."""
        negative_software_limit = self.get_negative_software_limit(axis)
        positive_software_limit = self.get_positive_software_limit(axis)
        if not (negative_software_limit < position < positive_software_limit):
            raise KeyError
        if axis == "x":
            self.newport_conex_cc_x_stage.write(str(self.settings['x-address'])+"PA"+str(position))
        elif axis == "y":
            self.newport_conex_cc_y_stage.write(str(self.settings['y-address'])+"PA"+str(position))
        else:
            raise KeyError

    def move_relative(self, axis, position):
        """The PR command initiates a relative move. When received, the positioner will move,
        with the predefined acceleration and velocity, to a new target position nn units away
        from the current target position.
        The PR command gets only accepted in READY, READY T or TRACKING states,
        AND when the distance of the positioner to the end of runs is larger than the
        commanded displacement.
        To avoid any mismatch, the controller always rounds the new target position to the
        closest encoder position."""
        negative_software_limit = self.get_negative_software_limit(axis)
        positive_software_limit = self.get_positive_software_limit(axis)
        if not (negative_software_limit < position < positive_software_limit):
            raise KeyError
        if axis == "x":
            self.newport_conex_cc_x_stage.write(str(self.settings['x-address'])+"PR"+str(position))
        elif axis == "y":
            self.newport_conex_cc_y_stage.write(str(self.settings['y-address'])+"PR"+str(position))
        else:
            raise KeyError

    def set_configuration_state(self, axis, enable):
        """PW1 changes the controller’s state from NOT REFERENCED to CONFIGURATION.
        In Configuration state all parameter settings are saved in the controller’s memory and
        remain available after switching off the controller. In addition, some settings are only
        possible in CONFIGURATION state (e.g. set drive voltage, set Backlash compensation,
        etc.).
        PW0 checks all stage parameters, and if they are acceptable, saves them in the flash
        memory of the controller. After that, it changes the controller’s state from
        CONFIGURATION to NOT REFERENCED.
        The execution of a PW0 command may take up to 10 seconds. During that time the
        controller will not respond to any other command"""
        if enable not in [0,1]:
            raise KeyError
        if axis == "x":
            self.newport_conex_cc_x_stage.write(str(self.settings['x-address'])+"PW"+str(enable))
        elif axis == "y":
            self.newport_conex_cc_y_stage.write(str(self.settings['y-address'])+"PW"+str(enable))
        else:
            raise KeyError

    def set_peak_current_limit(self, axis, peak_current_limit):
        """Sets the controller’s maximum or peak output current limit to the motor. When the
        controller detects a higher current than the peak current limit, it will generate a
        hardware error and a fault will be recorded."""
        if not (_min_peak_current_limit <= peak_current_limit <= _max_peak_current_limit):
            raise KeyError
        if axis == "x":
            self.newport_conex_cc_x_stage.write(str(self.settings['x-address'])+"QIL"+str(peak_current_limit))
        elif axis == "y":
            self.newport_conex_cc_y_stage.write(str(self.settings['y-address'])+"QIL"+str(peak_current_limit))
        else:
            raise KeyError

    def set_rms_current_limit(self, axis, rms_current_limit):
        """Sets the controller’s rms output current limit to the motor. The rms current limit
        must be lower than the peak current limit. When the controller’s output current exceeds
        the rms current limit, it will generate a hardware error and a fault will be recorded."""
        peak_current_limit = self.get_peak_current_limit(axis)
        if not (_min_rms_current_limit <= rms_current_limit <= _max_rms_current_limit and rms_current_limit <= peak_current_limit):
            raise KeyError
        if axis == "x":
            self.newport_conex_cc_x_stage.write(str(self.settings['x-address'])+"QIR"+str(rms_current_limit))
        elif axis == "y":
            self.newport_conex_cc_y_stage.write(str(self.settings['y-address'])+"QIR"+str(rms_current_limit))
        else:
            raise KeyError

    def set_rms_current_averaging_time(self, axis, rms_current_averaging_time):
        """Sets the controller’s averaging period for rms current calculation. In general, the
        QIT command defines for how long time the actual motor current is allowed to exceed
        the rms output current limit."""
        if not (_min_rms_current_averaging_time < rms_current_averaging_time <= _max_rms_current_averaging_time):
            raise KeyError
        if axis == "x":
            self.newport_conex_cc_x_stage.write(str(self.settings['x-address'])+"QIT"+str(rms_current_averaging_time))
        elif axis == "y":
            self.newport_conex_cc_y_stage.write(str(self.settings['y-address'])+"QIT"+str(rms_current_averaging_time))
        else:
            raise KeyError

    def reset_controller(self, axis):
        """The RS command issues a hardware reset of the controller, equivalent to a power-up.
        To go from DISABLE or READY state to CONFIGURATION state, it is also needed to
        first reset the controller with the RS command, and then to change the controller’s state
        with the PW1 command from NOT REFERENCED to CONFIGURATION."""
        if axis == "x":
            self.newport_conex_cc_x_stage.write(str(self.settings['x-address'])+"RS")
        elif axis == "y":
            self.newport_conex_cc_y_stage.write(str(self.settings['y-address'])+"RS")
        else:
            raise KeyError

    def reset_controller_address(self, axis):
        """The RS## command resets the controller’s address to 1. This address needs to be
        different for each CONEX-CC when connected on an RS-485 communication network."""
        if axis == "x":
            self.newport_conex_cc_x_stage.write(str(self.settings['x-address'])+"RS##")
        elif axis == "y":
            self.newport_conex_cc_y_stage.write(str(self.settings['y-address'])+"RS##")
        else:
            raise KeyError

    def set_controller_address(self, axis, address):
        """The SA command sets the controller’s RS-485 address. This address is ONLY used
        when the controller is configured for RS-485 communication.
        The SA command can only be sent to a controller configured for RS-232-C
        communication. In this configuration, the controller’s address is 1. Only one controller
        can be configured for RS-232-C communication.
        Newport recommends using the supplied utility software for all controller
        configurations. The SA command is of practical use only when not using this software."""
        if not (_min_model_number < address <=_max_model_number):
            raise KeyError
        if axis == "x":
            self.newport_conex_cc_x_stage.write(str(self.settings['x-address'])+"SA"+str(address))
        elif axis == "y":
            self.newport_conex_cc_y_stage.write(str(self.settings['y-address'])+"SA"+str(address))
        else:
            raise KeyError

    def set_control_loop_state(self, axis, state):
        """SC1 sets the controller to CLOSED loop control. This is the default.
        SC0 sets the controller to OPEN loop control. Open loop control might be useful for
        defining stage parameters like friction compensation or velocity feed forward.
        SC is not applicable in Tracking mode."""
        if state not in [0,1]:
            raise KeyError
        if axis == "x":
            self.newport_conex_cc_x_stage.write(str(self.settings['x-address'])+"SC"+str(state))
        elif axis == "y":
            self.newport_conex_cc_y_stage.write(str(self.settings['y-address'])+"SC"+str(state))
        else:
            raise KeyError

    def configure_simultaneous_started_move(self, axis, target_position):
        """The SE command allows starting a move on different controllers at the same time.
        The command xxSEnn sets a new target position for the controller nn. But different
        from the PA command, the move does not get executed immediately, but only after
        receipt of an SE command without preceding controller number and without following
        position value. When receiving the SE command, all controllers start a move to their
        new target position.
        The xxSEnn command gets only accepted in READY state, AND when the new target
        position is higher or equal to the negative software limit (SL), AND lower or equal to
        the positive software limit (SR). To avoid any mismatch, the controller always rounds
        the new target position to the closest encoder position.
        The SE command should not be confused with a synchronized move. With a
        synchronized move, all positioners start their motion simultaneously and have
        velocities, accelerations and jerk times which are limited to a rate which make all
        positioners start and complete their moves at the same time. The emphasis here is that
        they all start AND stop at the same time. The SE command starts a move on all
        controllers at the same time, but each positioner moves with its individually defined
        velocity and acceleration. So naturally, the different positioners don’t complete their
        motion at the same time."""
        negative_software_limit = self.get_negative_software_limit(axis)
        positive_software_limit = self.get_positive_software_limit(axis)
        if not (negative_software_limit < target_position < positive_software_limit):
            raise KeyError
        if axis == "x":
            self.newport_conex_cc_x_stage.write(str(self.settings['x-address']) + "SE" + str(target_position))
        elif axis == "y":
            self.newport_conex_cc_y_stage.write(str(self.settings['y-address']) + "SE" + str(target_position))
        else:
            raise KeyError

    def execute_simultaneous_started_move(self):
        """The SE command allows starting a move on different controllers at the same time. Please use after configure_simultaneous_started_move method"""
        self.newport_conex_cc_x_stage.write("SE")
        self.newport_conex_cc_y_stage.write("SE")

    def set_negative_software_limit(self, axis, negative_software_limit):
        """In CONFIGURATION state, this command sets the negative software limit which can
        then be saved in the controller’s nonvolatile memory using the PW command. It is also
        the default value that will be used unless a different value is set in DISABLE or
        READY state.
        In DISABLE or READY state, this command allows setting a new working parameter
        for the negative software limit. It must be lower or equal to the set-point position. This
        value is not saved in the controller’s memory and will be lost after reboot.
        The software limits are useful to limit the travel range of a positioner. There is no
        possibility to disable software limits. For an almost infinite motion, for instance with a
        rotation stage, set the lowest possible value, which is: -2147000000 * "encoder
        increment value" (see SU command). For instance if the encoder increment value is
        0,0005, this limit is -1073500."""
        if not (_min_negative_software_limit < negative_software_limit <= _max_negative_software_limit):
            raise KeyError
        if axis == "x":
            self.newport_conex_cc_x_stage.write(str(self.settings['x-address']) + "SL" + str(negative_software_limit))
        elif axis == "y":
            self.newport_conex_cc_y_stage.write(str(self.settings['y-address']) + "SL" + str(negative_software_limit))
        else:
            raise KeyError

    def set_positive_software_limit(self, axis, positive_software_limit):
        """In CONFIGURATION state, this command sets the positive software limit which can
        then be saved in the controller’s nonvolatile memory using the PW command. It is also
        the default value that will be used unless a different value is set in DISABLE or
        READY state.
        In DISABLE or READY state, this command allows setting a new working parameter
        for the positive software limit. It must be larger or equal to the set-point position. This
        value is not saved in the controller’s memory and will be lost after reboot.
        The software limits are useful to limit the travel range of a positioner. There is no
        possibility to disable software limits. For an almost infinite motion, for instance with a
        rotation stage, set the largest possible value, which is: 2147000000 * "encoder
        increment value" (see SU command). For instance if the encoder increment value is
        0,0005, this limit is 1073500."""
        if not (_min_positive_software_limit <= positive_software_limit < _max_positive_software_limit):
            raise KeyError
        if axis == "x":
            self.newport_conex_cc_x_stage.write(str(self.settings['x-address']) + "SR" + str(positive_software_limit))
        elif axis == "y":
            self.newport_conex_cc_y_stage.write(str(self.settings['y-address']) + "SR" + str(positive_software_limit))
        else:
            raise KeyError

    def stop_motion(self, axis):
        """The ST command is a safety feature. It stops a move in progress by decelerating the
        positioner immediately with the acceleration defined by the AC command until it stops.
        The xxST command with preceding controller address stops a move in progress on
        controller xx. The ST command without preceding controller address stops the moves
        on ALL controllers."""
        if axis == "x":
            self.newport_conex_cc_x_stage.write(str(self.settings['x-address']) + "ST")
        elif axis == "y":
            self.newport_conex_cc_y_stage.write(str(self.settings['y-address']) + "ST")
        else:
            raise KeyError

    def set_controller_increment_value(self, axis, increment_value = 0.001):
        """The SU command sets the value for one encoder count. It defines also the system of
        units for all other parameters like travel limits, velocities, accelerations, etc. Therefore,
        it is the first parameter to be defined for any positioner.
        Example: For a positioner with an encoder resolution of 1 µm, the command
        xxSU0.001 sets 1 encoder count = 1 µm = 0.001 unit or 1 unit = 1 mm"""
        if not (_min_increment_value < increment_value < _max_increment_value):
            raise KeyError
        if axis == "x":
            self.newport_conex_cc_x_stage.write(str(self.settings['x-address']) + "SU"+ str(increment_value))
        elif axis == "y":
            self.newport_conex_cc_y_stage.write(str(self.settings['y-address']) + "SU"+ str(increment_value))
        else:
            raise KeyError

    def enable_tracking_mode(self, axis, enable):
        """The TK command enables to enter or leave Tracking Mode"""
        if enable not in [0,1]:
            raise KeyError
        if axis == "x":
            self.newport_conex_cc_x_stage.write(str(self.settings['x-address']) + "TK"+ str(enable))
        elif axis == "y":
            self.newport_conex_cc_y_stage.write(str(self.settings['y-address']) + "TK"+ str(enable))
        else:
            raise KeyError

    def set_velocity(self, axis, velocity):
        """In CONFIGURATION state, this command sets the maximum velocity value which can
        then be saved in the controller’s nonvolatile memory using the PW command. This is
        the maximum velocity that can be applied to the mechanical system. It is also the
        default velocity that will be used for all moves unless a lower value is set in DISABLE
        or READY state.
        In DISABLE or READY state, this command sets the velocity used for the following
        moves. Its value can be up to the programmed value in CONFIGURATION state. This
        value is not saved in the controller’s memory and will be lost after reboot."""
        if not (_min_velocity < velocity < _max_velocity):
            raise KeyError
        if axis == "x":
            self.newport_conex_cc_x_stage.write(str(self.settings['x-address']) + "VA"+ str(velocity))
        elif axis == "y":
            self.newport_conex_cc_y_stage.write(str(self.settings['y-address']) + "VA"+ str(velocity))
        else:
            raise KeyError

if __name__ == '__main__':
    newport_stage = Newport_CONEX_CC_xy_stage()
    #print(newport_stage.get_positive_software_limit('x'))
    #print(newport_stage.get_positive_software_limit('y'))
    #print(newport_stage.get_position('x'))
    #print(newport_stage.get_position('y'))
    #newport_stage.set_position('y', 12)
    #newport_stage.set_position('y', 10)
    #print(newport_stage.get_position('x'))
    #print(newport_stage.get_position('y'))
    """
    print(newport_stage.get_setpoint_position('x'))
    print(newport_stage.get_setpoint_position('y'))
    print(newport_stage.get_acceleration('x'))
    print(newport_stage.get_acceleration('y'))
    print(newport_stage.get_backlash_compensation('x'))
    print(newport_stage.get_backlash_compensation('y'))
    print(newport_stage.get_hysteresis_compensation('x'))
    print(newport_stage.get_hysteresis_compensation('y'))
    print(newport_stage.get_driver_voltage('x'))
    print(newport_stage.get_driver_voltage('y'))
    print(newport_stage.get_low_pass_filter_for_kd('x'))
    print(newport_stage.get_low_pass_filter_for_kd('y'))
    print(newport_stage.get_following_error_limit('x'))
    print(newport_stage.get_following_error_limit('y'))
    print(newport_stage.get_friction_compensation('x'))
    print(newport_stage.get_friction_compensation('y'))

    print(newport_stage.get_home_search_type('x'))
    print(newport_stage.get_home_search_type('y'))
    print(newport_stage.get_stage_identifier('x'))
    print(newport_stage.get_stage_identifier('y'))
    print(newport_stage.get_jerk_time('x'))
    print(newport_stage.get_jerk_time('y'))
    print(newport_stage.get_derivative_gain('x'))
    print(newport_stage.get_derivative_gain('y'))
    print(newport_stage.get_integral_gain('x'))
    print(newport_stage.get_integral_gain('y'))
    print(newport_stage.get_proportional_gain('x'))
    print(newport_stage.get_proportional_gain('y'))
    print(newport_stage.get_velocity_feed_forward('x'))
    print(newport_stage.get_velocity_feed_forward('y'))
    print(newport_stage.get_state('x'))
    print(newport_stage.get_state('y'))


    print(newport_stage.get_home_search_velocity('x'))
    print(newport_stage.get_home_search_velocity('y'))
    print(newport_stage.get_home_search_timeout('x'))
    print(newport_stage.get_home_search_timeout('y'))
    print(newport_stage.get_absolute_target_position('x'))
    print(newport_stage.get_absolute_target_position('y'))
    #print(newport_stage.get_relative_target_position('x'))
    #print(newport_stage.get_relative_target_position('y'))


    #print(newport_stage.get_motion_time_for_a_relative_move('x'))
    #print(newport_stage.get_motion_time_for_a_relative_move('y'))

    print(newport_stage.get_configuration_state('x'))
    print(newport_stage.get_configuration_state('y'))

    print(newport_stage.get_motor_peak_current_limit('x'))
    print(newport_stage.get_motor_peak_current_limit('y'))

    print(newport_stage.get_motor_rms_current_limit('x'))
    print(newport_stage.get_motor_rms_current_limit('y'))

    print(newport_stage.get_motor_rms_current_averating_time('x'))
    print(newport_stage.get_motor_rms_current_averating_time('y'))
    print(newport_stage.get_control_loop_state('x'))
    print(newport_stage.get_control_loop_state('y'))

    print(newport_stage.get_simultaneous_started_move_target_position('x'))
    print(newport_stage.get_simultaneous_started_move_target_position('y'))

    print(newport_stage.get_negative_software_limit('x'))
    print(newport_stage.get_negative_software_limit('y'))
    print(newport_stage.get_positive_software_limit('x'))
    print(newport_stage.get_positive_software_limit('y'))
    print(newport_stage.get_encoder_increment_value('x'))
    print(newport_stage.get_encoder_increment_value('y'))
    #print(newport_stage.get_command_error_string('x'))
    #print(newport_stage.get_command_error_string('y'))
    print(newport_stage.get_last_command_error('x'))
    print(newport_stage.get_last_command_error('y'))
    print(newport_stage.get_positioner_error_and_controller_state('x'))
    print(newport_stage.get_positioner_error_and_controller_state('y'))

    print(newport_stage.get_velocity('x'))
    print(newport_stage.get_velocity('y'))

    print(newport_stage.get_controller_revision_information('x'))
    print(newport_stage.get_controller_revision_information('y'))
    print(newport_stage.get_all_axis_parameters('x'))
    print(newport_stage.get_all_axis_parameters('y'))"""

    """newport_stage.set_controller_increment_value('x')
    newport_stage.set_controller_increment_value('y')
    print(newport_stage.get_encoder_i                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  ncrement_value('x'))
    print(newport_stage.get_encoder_increment_value('y'))
    print(newport_stage.get_position('x'))
    print(newport_stage.get_position('y'))"""

