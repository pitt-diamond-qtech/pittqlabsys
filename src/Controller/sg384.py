# Created by gurudevdutt at 7/30/25
# controllers/sg384.py

from .mw_generator_base import MicrowaveGeneratorBase, Parameter
import logging

logger = logging.getLogger("sg384")

class SG384Generator(MicrowaveGeneratorBase):
    """
    Stanford Research Systems SG384 concrete implementation.
    Adds any SG384‐specific settings and maps them to SCPI.
    """
    
    # Parameter mappings for SG384
    PARAM_MAPPINGS = {
        'enable_output': 'ENBR',
        'enable_rf_output': 'ENBL', 
        'frequency': 'FREQ',
        'amplitude': 'AMPR',
        'amplitude_rf': 'AMPL',
        'phase': 'PHAS',
        'enable_modulation': 'MODL',
        'modulation_type': 'TYPE',
        'modulation_function': 'MFNC',
        'pulse_modulation_function': 'PFNC',
        'dev_width': 'FDEV',
        'mod_rate': 'RATE'
    }
    
    # Modulation type mappings
    MOD_TYPE_MAPPINGS = {
        'AM': 0,
        'FM': 1, 
        'PhaseM': 2,
        'Freq sweep': 3,
        'Pulse': 4,
        'Blank': 5,
        'IQ': 6
    }
    
    # Reverse mapping for internal to string conversion
    INTERNAL_TO_MOD_TYPE = {v: k for k, v in MOD_TYPE_MAPPINGS.items()}
    
    # Modulation function mappings
    MOD_FUNC_MAPPINGS = {
        'Sine': 0,
        'Ramp': 1,
        'Triangle': 2,
        'Square': 3,
        'Noise': 4,
        'External': 5
    }
    
    INTERNAL_TO_MOD_FUNC = {v: k for k, v in MOD_FUNC_MAPPINGS.items()}
    
    # Pulse modulation function mappings
    PULSE_MOD_FUNC_MAPPINGS = {
        'Square': 3,
        'Noise(PRBS)': 4,
        'External': 5
    }
    
    INTERNAL_TO_PULSE_MOD_FUNC = {v: k for k, v in PULSE_MOD_FUNC_MAPPINGS.items()}
    
    # Update dispatch mapping
    UPDATE_MAPPING = {
        'frequency': 'set_frequency',
        'power': 'set_power',
        'amplitude': 'set_power',  # Alias for power
        'phase': 'set_phase',
        'enable_output': '_set_output_enable',
        'enable_modulation': '_set_modulation_enable',
        'modulation_type': '_set_modulation_type',
        'modulation_function': '_set_modulation_function',
        'pulse_modulation_function': '_set_pulse_modulation_function',
        'dev_width': '_set_dev_width',
        'mod_rate': '_set_mod_rate'
    }

    _DEFAULT_SETTINGS = Parameter([
        # Base settings from MicrowaveGeneratorBase
        Parameter('connection_type', 'LAN', ['LAN','GPIB','RS232'], 'Transport type'),
        Parameter('ip_address', '',     str, 'IP for LAN'),
        Parameter('port',       5025,   int, 'Port for LAN'),
        Parameter('visa_resource', '',  str, 'PyVISA resource string, e.g. GPIB0::20::INSTR or ASRL9::INSTR'),
        Parameter('baud_rate',   115200,int, 'Baud for RS232'),
        # Common parameters
        Parameter('frequency', 1e9, float, 'Frequency in Hz'),
        Parameter('power', -10, float, 'Power in dBm'),
        Parameter('phase', 0, float, 'Phase in degrees'),
        Parameter('amplitude', -10, float, 'Amplitude in dBm'),
        # SG384-specific settings
        Parameter('enable_output', False, bool, 'Enable output'),
        Parameter('enable_modulation', True, bool, 'Enable modulation'),
        Parameter('modulation_type', 'FM', ['AM','FM','PM','Sweep'], 'Modulation type'),
        Parameter('modulation_function', 'Sine', ['Sine','Ramp','Triangle','Square','Noise','External'], 'Modulation function'),
        Parameter('pulse_modulation_function', 'Square', ['Square','Noise(PRBS)','External'], 'Pulse modulation function'),
        Parameter('modulation_depth', 1e6, float, 'Deviation in Hz'),
        Parameter('dev_width', 1e6, float, 'Deviation width in Hz'),
        Parameter('mod_rate', 1e7, float, 'Modulation rate in Hz'),
        # add more SG384‐only knobs here…
    ])

    def __init__(self, name=None, settings=None):
        super().__init__(name, settings)
        # verify comms
        idn = self._query("*IDN?")
        logger.info(f"SG384 IDN: {idn}")

    def set_frequency(self, hz: float):
        """SCPI: FREQ <value>HZ"""
        self.settings['frequency'] = hz
        self._send(f"FREQ {hz}HZ")

    def set_power(self, dbm: float):
        """SCPI: POWR <value>DBM"""
        self.settings['amplitude'] = dbm
        self._send(f"POWR {dbm}DBM")

    def set_phase(self, deg: float):
        """SCPI: PHAS <value>DEG"""
        self.settings['phase'] = deg
        self._send(f"PHAS {deg}DEG")

    def enable_modulation(self):
        self._send("MODL:STAT ON")

    def disable_modulation(self):
        self._send("MODL:STAT OFF")

    def set_modulation_type(self, mtype: str):
        self.settings['modulation_type'] = mtype
        self._send(f"MODL:TYPE {mtype}")

    def set_modulation_depth(self, depth_hz: float):
        self.settings['modulation_depth'] = depth_hz
        self._send(f"FDEV {depth_hz}")

    # Helper methods using mapping dictionaries
    def _param_to_internal(self, param: str) -> str:
        """Convert parameter name to internal command using mapping dictionary."""
        if param not in self.PARAM_MAPPINGS:
            raise KeyError(f"Unknown parameter: {param}")
        return self.PARAM_MAPPINGS[param]
    
    def _mod_type_to_internal(self, value: str) -> int:
        """Convert modulation type string to internal value using mapping dictionary."""
        if value not in self.MOD_TYPE_MAPPINGS:
            raise KeyError(f"Unknown modulation type: {value}")
        return self.MOD_TYPE_MAPPINGS[value]
    
    def _internal_to_mod_type(self, value: int) -> str:
        """Convert internal modulation type value to string using mapping dictionary."""
        if value not in self.INTERNAL_TO_MOD_TYPE:
            raise KeyError(f"Unknown internal modulation type: {value}")
        return self.INTERNAL_TO_MOD_TYPE[value]
    
    def _mod_func_to_internal(self, value: str) -> int:
        """Convert modulation function string to internal value using mapping dictionary."""
        if value not in self.MOD_FUNC_MAPPINGS:
            raise KeyError(f"Unknown modulation function: {value}")
        return self.MOD_FUNC_MAPPINGS[value]
    
    def _internal_to_mod_func(self, value: int) -> str:
        """Convert internal modulation function value to string using mapping dictionary."""
        if value not in self.INTERNAL_TO_MOD_FUNC:
            raise KeyError(f"Unknown internal modulation function: {value}")
        return self.INTERNAL_TO_MOD_FUNC[value]
    
    def _pulse_mod_func_to_internal(self, value: str) -> int:
        """Convert pulse modulation function string to internal value using mapping dictionary."""
        if value not in self.PULSE_MOD_FUNC_MAPPINGS:
            raise KeyError(f"Unknown pulse modulation function: {value}")
        return self.PULSE_MOD_FUNC_MAPPINGS[value]
    
    def _internal_to_pulse_mod_func(self, value: int) -> str:
        """Convert internal pulse modulation function value to string using mapping dictionary."""
        if value not in self.INTERNAL_TO_PULSE_MOD_FUNC:
            raise KeyError(f"Unknown internal pulse modulation function: {value}")
        return self.INTERNAL_TO_PULSE_MOD_FUNC[value]
    
    def _dispatch_update(self, settings: dict):
        """
        Dispatch update operations using mapping dictionary.
        This replaces long if-elif chains in update methods.
        """
        for key, value in settings.items():
            if key in self.UPDATE_MAPPING:
                method_name = self.UPDATE_MAPPING[key]
                method = getattr(self, method_name)
                
                # Convert values as needed
                if isinstance(value, bool):
                    value = int(value)
                elif key == 'modulation_type':
                    value = self._mod_type_to_internal(value)
                elif key == 'modulation_function':
                    value = self._mod_func_to_internal(value)
                elif key == 'pulse_modulation_function':
                    value = self._pulse_mod_func_to_internal(value)
                
                # Call the appropriate method
                method(value)
            else:
                logger.warning(f"Unknown parameter for update: {key}")
    
    # Setter methods for update dispatch
    def _set_output_enable(self, enable: int):
        """Set output enable/disable."""
        self._send(f"ENBR {enable}")
    
    def _set_modulation_enable(self, enable: int):
        """Set modulation enable/disable."""
        self._send(f"MODL {enable}")
    
    def _set_modulation_type(self, mod_type: int):
        """Set modulation type."""
        self._send(f"TYPE {mod_type}")
    
    def _set_modulation_function(self, mod_func: int):
        """Set modulation function."""
        self._send(f"MFNC {mod_func}")
    
    def _set_pulse_modulation_function(self, pulse_mod_func: int):
        """Set pulse modulation function."""
        self._send(f"PFNC {pulse_mod_func}")
    
    def _set_dev_width(self, dev_width: float):
        """Set deviation width."""
        self._send(f"FDEV {dev_width}")
    
    def _set_mod_rate(self, mod_rate: float):
        """Set modulation rate."""
        self._send(f"RATE {mod_rate}")

    def update(self, settings: dict):
        """
        Updates the internal settings and physical parameters using mapping dictionaries.
        This replaces the long if-elif chain from the original microwave_generator.py.
        """
        super().update(settings)
        
        # Only send commands if _inst is available (i.e., not during initialization)
        if hasattr(self, '_inst') and self._inst is not None:
            self._dispatch_update(settings)
    
    @property
    def _PROBES(self):
        return {
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
        """Read probe values using mapping dictionaries."""
        assert self._settings_initialized
        assert key in list(self._PROBES.keys())
        
        # Define probe reading mappings with their conversion functions
        probe_mapping = {
            # Boolean probes (return True/False)
            'enable_output': self._read_boolean_probe,
            'enable_rf_output': self._read_boolean_probe,
            'enable_modulation': self._read_boolean_probe,
            
            # Modulation probes (return string values)
            'modulation_type': self._read_modulation_type_probe,
            'modulation_function': self._read_modulation_function_probe,
            'pulse_modulation_function': self._read_pulse_modulation_function_probe,
            
            # Float probes (return numeric values)
            'frequency': self._read_float_probe,
            'amplitude': self._read_float_probe,
            'amplitude_rf': self._read_float_probe,
            'phase': self._read_float_probe,
            'dev_width': self._read_float_probe,
            'mod_rate': self._read_float_probe
        }
        
        if key in probe_mapping:
            return probe_mapping[key](key)
        else:
            raise KeyError(f"No such probe: {key}")
    
    def _read_boolean_probe(self, key):
        """Read boolean probe values (enable_output, enable_modulation, etc.)."""
        key_internal = self._param_to_internal(key)
        value = int(self._query(key_internal + '?'))
        return bool(value)
    
    def _read_modulation_type_probe(self, key):
        """Read modulation type probe values."""
        key_internal = self._param_to_internal(key)
        value = int(self._query(key_internal + '?'))
        return self._internal_to_mod_type(value)
    
    def _read_modulation_function_probe(self, key):
        """Read modulation function probe values."""
        key_internal = self._param_to_internal(key)
        value = int(self._query(key_internal + '?'))
        return self._internal_to_mod_func(value)
    
    def _read_pulse_modulation_function_probe(self, key):
        """Read pulse modulation function probe values."""
        key_internal = self._param_to_internal(key)
        value = int(self._query(key_internal + '?'))
        return self._internal_to_pulse_mod_func(value)
    
    def _read_float_probe(self, key):
        """Read float probe values (frequency, amplitude, phase, etc.)."""
        key_internal = self._param_to_internal(key)
        return float(self._query(key_internal + '?'))
    
    @property
    def is_connected(self):
        """Check if the device is connected."""
        try:
            self._query('*IDN?')  # arbitrary call to check connection
            return True
        except Exception:
            return False
    
    def close(self):
        """Close the connection to the device."""
        if hasattr(self, '_inst') and self._inst is not None:
            try:
                self._inst.close()
                return True
            except Exception:
                return False
        return True  # Already closed or no connection
