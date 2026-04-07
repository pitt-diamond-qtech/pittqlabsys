"""
MUX Control Device for mux trigger.

This device wraps around a multiplexer chip to switch between
three different trigger sources: confocal, CW-ESR, and Pulsed ESR.
"""

import logging
import pyvisa as visa
from typing import Optional, Literal

from src.core.device import Device
from src.core.parameter import Parameter

# Default connection settings
#_DEFAULT_PORT = 'COM3'
_DEFAULT_PORT = 502
_DEFAULT_TIMEOUT = 5000
_IP_ADDRESS = '192.168.2.85'

# Valid trigger selectors
TRIGGER_SELECTORS = Literal['confocal', 'odmr', 'pulsed']

from pymodbus.client import ModbusTcpClient

class MUXControlDevice(Device):
    """
    Device wrapper for MUX controller.
    
    The MUX controller uses a multiplexer to switch between
    3 different trigger sources:
    1. Confocal trigger - from MCL nanodrive
    2. CW-ESR trigger - from PTS Arduino  (old setup)
    3. Pulsed ESR trigger - from AWG
    - Commands: "1"=confocal, "2"=cw-esr, "3"=pulsed
    """
    
    _DEFAULT_SETTINGS = Parameter(Device._get_base_settings() +[
        Parameter('ip_address', _IP_ADDRESS, str, 'IP address of device'),
        Parameter('port', _DEFAULT_PORT, int, 'Port'),
        Parameter('timeout', _DEFAULT_TIMEOUT, int, 'Serial timeout in milliseconds'),
        Parameter('auto_connect', True, bool, 'Automatically connect on initialization'),
    ])
    
    _PROBES = {
        'get_data': 'choose whether you need to get data from this device or not',
        'status': 'Current MUX selection status',
        'port': 'Current port',
        'connected': 'Connection status to Mux',
    }
    
    def __init__(self, name=None, settings=None):
        super().__init__(name=name, settings=settings)
        self.logger = logging.getLogger(__name__)
        self.mux = None
        self._current_selection = None
        
        if self.settings.get('auto_connect', True):
            self.connect()

    @property
    def is_connected(self) -> bool:
        """Check if the MUX controller is connected and accessible."""
        return bool(getattr(self, "_is_connected", False) and self.mux is not None)

    def connect(self) -> bool:
        """
        Connect to the MUX controller.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        cfg = self.settings
        self.mux = ModbusTcpClient(cfg['ip_address'], port = self.settings['port'], timeout=self.settings.get('timeout', _DEFAULT_TIMEOUT) / 1000)
        try:
            if self.mux.connect():
                self.logger.info(f"Connected to MUX controller")
                self._is_connected = True
                return True
            else:
                self.logger.info(f"Failed to connect to MUX controller")
                self._is_connected = False
                return False
        except Exception as e:
            self.logger.error(f"Unexpected error connecting to MUX controller: {e}")
            self._is_connected = False
            return False
    
    def disconnect(self):
        """Disconnect from the MUX controller."""
        if self.mux is not None:
            try:
                self.mux.close()
                self.mux = None
                self._is_connected = False
                self._current_selection = None
                self.logger.info("MUX controller disconnected successfully")
            except Exception as e:
                self.logger.error(f"Error disconnecting from MUX controller: {e}")

    def select_trigger(self, selector: TRIGGER_SELECTORS) -> bool:
        if not self.is_connected:
            self.logger.error("Cannot select trigger: not connected to MUX controller")
            return False
        command_map = {
            'confocal': 0,
            'odmr': 1,
            'pulsed': 2
        }
        if selector not in command_map:
            self.logger.error(f"Invalid trigger selector: {selector}")
            return False

        try:
            # Turn OFF all coils
            for coil in command_map.values():
                print(f"coil {coil}")
                self.mux.write_coil(coil, False, device_id = 1)
            # Turn ON selected coil
            selected_coil = command_map[selector]
            self.mux.write_coil(selected_coil, True, device_id = 1)
            responses = {}
            returned = False
            # Read back all coils
            for coil in command_map.values():
                responses[coil] = self.mux.read_coils(coil, count = 1, device_id = 1)
                print(f"coil {coil} response: {responses[coil].bits[0]}")
                if coil == selected_coil:
                    returned = returned or not(responses[coil].bits[0])
                else:
                    returned = returned or responses[coil].bits[0]
            response = responses[selected_coil]
            if response.isError():
                self.logger.error(f"Failed to read coil states: {response}")
                return False
            states = response.bits[0]
            print(states)
            # Verify hardware state
            if not returned:
                self._current_selection = selector
                self.logger.info(
                    f"Selected {selector} trigger (coil {selected_coil}, states={states})"
                )
                return True
            else:
                self.logger.error(
                    f"Trigger selection mismatch for {selector}: states={states}"
                )
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
            'multiplexer': 'Modbus POE ETH Relay',
            'channel_mapping': {
                'confocal': {
                    'command': '1'
                },
                        'odmr': {
            'command': '2'
        },
                'pulsed': {
                    'command': '3'
                }
            },
            'port': self.settings.get('port', 502)
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
        elif key == 'get_data':
            return self.settings['get_data']
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

if __name__ == "__main__":
    mux = MUXControlDevice()
    mux.connect()
    if mux.is_connected:
        mux.select_trigger('confocal')