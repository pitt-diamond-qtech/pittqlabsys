"""
MUX Control Device for Arduino-based trigger multiplexing.

This device wraps around an Arduino that controls a multiplexer chip to switch between
three different trigger sources: confocal, CW-ESR, and Pulsed ESR.
"""

import logging
import pyvisa as visa
from typing import Optional, Literal

from src.core.device import Device
from src.core.parameter import Parameter

# Default connection settings
_DEFAULT_PORT = 'COM3'
_DEFAULT_BAUDRATE = 9600
_DEFAULT_TIMEOUT = 5000

# Valid trigger selectors
TRIGGER_SELECTORS = Literal['confocal', 'odmr', 'pulsed']


class MUXControlDevice(Device):
    """
    Device wrapper for Arduino-based MUX controller.
    
    The MUX controller uses a 74HC4051 8-channel multiplexer to switch between
    3 different trigger sources:
    1. Confocal trigger (Y0) - from MCL nanodrive
    2. CW-ESR trigger (Y1) - from PTS Arduino  
    3. Pulsed ESR trigger (Y2) - from AWG
    
    Hardware Setup:
    - Arduino pins 2,3,4 control multiplexer select lines S0, S1, S2
    - Pin 5 (Z) is the common I/O line
    - Commands: "1"=confocal, "2"=cw-esr, "3"=pulsed
    """
    
    _DEFAULT_SETTINGS = Parameter([
        Parameter('port', _DEFAULT_PORT, str, 'Serial port for Arduino connection'),
        Parameter('baudrate', _DEFAULT_BAUDRATE, int, 'Serial baudrate'),
        Parameter('timeout', _DEFAULT_TIMEOUT, int, 'Serial timeout in milliseconds'),
        Parameter('auto_connect', True, bool, 'Automatically connect on initialization'),
    ])
    
    _PROBES = {
        'status': 'Current MUX selection status',
        'port': 'Current serial port',
        'connected': 'Connection status to Arduino',
    }
    
    def __init__(self, name=None, settings=None):
        super().__init__(name=name, settings=settings)
        self.logger = logging.getLogger(__name__)
        self.arduino = None
        self._current_selection = None
        
        if self.settings.get('auto_connect', True):
            self.connect()
    
    @property
    def is_connected(self) -> bool:
        """Check if the MUX controller is connected and accessible."""
        if not self._is_connected or self.arduino is None:
            return False
        try:
            # Test actual connection by sending valid command and checking response
            response = self.arduino.query('1')
            # Arduino should respond with "Input is in range" for valid input
            return 'Input is in range' in response
        except Exception:
            self._is_connected = False
            return False
    
    def connect(self) -> bool:
        """
        Connect to the Arduino MUX controller.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            rm = visa.ResourceManager()
            port = self.settings['port']
            baudrate = self.settings['baudrate']
            timeout = self.settings['timeout']
            
            # Construct VISA resource string for serial connection
            resource_string = f"ASRL{port}::INSTR"
            
            self.arduino = rm.open_resource(resource_string)
            self.arduino.baud_rate = baudrate
            self.arduino.timeout = timeout
            self.arduino.write_termination = '\n'
            self.arduino.read_termination = '\n'
            
            # Test communication by reading initial message
            try:
                initial_message = self.arduino.read()
                self.logger.info(f"Connected to MUX controller on {port}: {initial_message}")
                self._is_connected = True
                return True
            except visa.VisaIOError as e:
                self.logger.warning(f"Connected but no initial message: {e}")
                self._is_connected = True
                return True
                
        except visa.VisaIOError as e:
            self.logger.error(f"Failed to connect to MUX controller on {self.settings['port']}: {e}")
            self._is_connected = False
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error connecting to MUX controller: {e}")
            self._is_connected = False
            return False
    
    def disconnect(self):
        """Disconnect from the Arduino MUX controller."""
        if self.arduino is not None:
            try:
                self.arduino.close()
                self.arduino = None
                self._is_connected = False
                self._current_selection = None
                self.logger.info("MUX controller disconnected successfully")
            except Exception as e:
                self.logger.error(f"Error disconnecting from MUX controller: {e}")
    
    def select_trigger(self, selector: TRIGGER_SELECTORS) -> bool:
        """
        Select the trigger source.
        
        Args:
            selector: Trigger source to select ('confocal', 'odmr', or 'pulsed')
            
        Returns:
            bool: True if selection successful, False otherwise
        """
        if not self.is_connected:
            self.logger.error("Cannot select trigger: not connected to MUX controller")
            return False
        
        if selector not in ['confocal', 'odmr', 'pulsed']:
            self.logger.error(f"Invalid trigger selector: {selector}. Must be 'confocal', 'odmr', or 'pulsed'")
            return False
        
        try:
            # Map selector to command (matches Arduino code)
            command_map = {
                'confocal': '1',  # Maps to Y0 (S0=0, S1=0, S2=0)
                'odmr': '2',     # Maps to Y1 (S0=1, S1=0, S2=0)
                'pulsed': '3'     # Maps to Y2 (S0=0, S1=1, S2=0)
            }
            
            command = command_map[selector]
            response = self.arduino.query(command)
            
            # Check Arduino response for success/failure
            if response and "Input is in range" in response:
                self._current_selection = selector
                self.logger.info(f"Successfully selected {selector} trigger source (Y{command_map[selector]})")
                return True
            elif response and "Input out of range" in response:
                self.logger.error(f"Arduino rejected trigger selection: {response}")
                return False
            else:
                # If response doesn't contain expected text, assume success
                self._current_selection = selector
                self.logger.info(f"Selected {selector} trigger source (response: {response})")
                return True
            
        except visa.VisaIOError as e:
            self.logger.error(f"Error selecting {selector} trigger: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error selecting {selector} trigger: {e}")
            return False
    
    def get_current_selection(self) -> Optional[str]:
        """
        Get the currently selected trigger source.
        
        Returns:
            str: Current selection ('confocal', 'odmr', 'pulsed') or None if unknown
        """
        return self._current_selection
    
    def get_hardware_mapping(self) -> dict:
        """
        Get the hardware pin mapping information.
        
        Returns:
            dict: Dictionary containing hardware pin mappings and multiplexer details
        """
        return {
            'multiplexer': '74HC4051 8-Channel',
            'arduino_pins': {
                'S0': 2,  # Select line 0
                'S1': 3,  # Select line 1  
                'S2': 4,  # Select line 2
                'Z': 5    # Common I/O line
            },
            'channel_mapping': {
                'confocal': {
                    'command': '1',
                    'channel': 'Y0',
                    'pins': {'S0': 0, 'S1': 0, 'S2': 0}
                },
                        'odmr': {
            'command': '2',
            'channel': 'Y1',
            'pins': {'S0': 1, 'S1': 0, 'S2': 0}
        },
                'pulsed': {
                    'command': '3',
                    'channel': 'Y2', 
                    'pins': {'S0': 0, 'S1': 1, 'S2': 0}
                }
            },
            'baudrate': self.settings.get('baudrate', 9600),
            'port': self.settings.get('port', 'COM3')
        }
    
    def test_connection(self) -> dict:
        """
        Test the connection to the Arduino and get initialization message.
        
        Returns:
            dict: Connection test results including Arduino response
        """
        if not self.is_connected:
            return {
                'connected': False,
                'error': 'Device not connected',
                'arduino_message': None
            }
        
        try:
            # Try to read the Arduino's initialization message
            # The Arduino sends "Initialized...Enter 1 for Confocal, 2 for CW, or 3 for Pulsed."
            # when it starts up, and we can read this to verify communication
            arduino_message = self.arduino.read()
            
            return {
                'connected': True,
                'arduino_message': arduino_message,
                'port': self.settings.get('port'),
                'baudrate': self.settings.get('baudrate'),
                'current_selection': self._current_selection
            }
            
        except visa.VisaIOError as e:
            return {
                'connected': False,
                'error': f'VISA communication error: {e}',
                'arduino_message': None
            }
        except Exception as e:
            return {
                'connected': False,
                'error': f'Unexpected error: {e}',
                'arduino_message': None
            }
    
    def get_arduino_info(self) -> dict:
        """
        Get Arduino firmware and hardware information.
        
        Returns:
            dict: Arduino information including firmware details
        """
        return {
            'firmware': {
                'name': 'MUX_control',
                'author': 'Vincent Musso, Duttlab',
                'date': 'March 25, 2019',
                'modified': 'December 12, 2019 by Gurudev',
                'description': '74HC4051 8-Channel Multiplexer Controller'
            },
            'hardware': {
                'multiplexer': '74HC4051 8-Channel',
                'arduino_pins': {
                    'S0': 2,  # Select line 0
                    'S1': 3,  # Select line 1
                    'S2': 4,  # Select line 2
                    'Z': 5    # Common I/O line
                },
                'jumpers': {
                    'JP1': 'VEE to GND (closed)'
                }
            },
            'commands': {
                '1': 'Select confocal trigger (Y0)',
                '2': 'Select CW-ESR trigger (Y1)',
                '3': 'Select pulsed ESR trigger (Y2)'
            },
            'responses': {
                'success': 'Input is in range',
                'failure': 'Input out of range',
                'initialization': 'Initialized...Enter 1 for Confocal, 2 for CW, or 3 for Pulsed.'
            }
        }
    
    def read_probes(self, key=None):
        """
        Read device probes.
        
        Args:
            key: Specific probe to read, or None for all probes
            
        Returns:
            Value of requested probe or dict of all probes
        """
        if key is None:
            return {
                'status': self.get_current_selection(),
                'port': self.settings.get('port', 'Not set'),
                'connected': self.is_connected
            }
        elif key == 'status':
            return self.get_current_selection()
        elif key == 'port':
            return self.settings.get('port', 'Not set')
        elif key == 'connected':
            return self.is_connected
        else:
            raise KeyError(f"Unknown probe: {key}")
    
    def update(self, settings):
        """
        Update device settings and reconnect if port changes.
        
        Args:
            settings: Dictionary of settings to update
        """
        old_port = self.settings.get('port')
        
        # Update settings
        super().update(settings)
        
        # Reconnect if port changed
        new_port = self.settings.get('port')
        if old_port != new_port and self.is_connected:
            self.logger.info(f"Port changed from {old_port} to {new_port}, reconnecting...")
            self.disconnect()
            if self.settings.get('auto_connect', True):
                self.connect()
    
    def cleanup(self):
        """Clean up device resources."""
        self.disconnect()
    
    def __del__(self):
        """Destructor to ensure cleanup."""
        self.cleanup()


# Legacy compatibility - keep the old class name for backward compatibility
class MUXControl(MUXControlDevice):
    """
    Legacy MUXControl class for backward compatibility.
    
    This class maintains the same interface as the original MUXControl class
    but now inherits from Device for better integration.
    """
    
    def __init__(self, port='COM3'):
        # Convert old-style initialization to new format
        settings = {'port': port, 'auto_connect': True}
        super().__init__(settings=settings)
    
    def run(self, selector):
        """
        Legacy method for backward compatibility.
        
        Args:
            selector: Trigger source to select
            
        Returns:
            0 on success, -1 on failure
        """
        if self.select_trigger(selector):
            return 0
        else:
            return -1
    
    def close(self):
        """Legacy method for backward compatibility."""
        self.disconnect() 