# Created by gurudevdutt at 7/30/25
# controllers/sg384.py

from .mw_generator_base import MicrowaveGeneratorBase, Parameter
import logging
import time

logger = logging.getLogger("sg384")

class SG384Generator(MicrowaveGeneratorBase):
    """
    Stanford Research Systems SG384 concrete implementation.
    Adds any SG384‐specific settings and maps them to SCPI.
    """
    
    # SCPI command mappings for SG384
    SCPI_MAPPINGS = {
        'enable_output': 'ENBL',
        'enable_rf_output': 'ENBR', 
        'frequency': 'FREQ',
        'amplitude': 'AMPL',
        'amplitude_rf': 'AMPR',
        'power': 'AMPR',  # Add power mapping for RF output
        'phase': 'PHAS',
        'enable_modulation': 'MODL',
        'modulation_type': 'TYPE',
        'modulation_function': 'MFNC',
        'pulse_modulation_function': 'PFNC',
        'dev_width': 'FDEV',
        'mod_rate': 'RATE',
        'sweep_function': 'SFNC',
        'sweep_rate': 'SRAT',
        'sweep_deviation': 'SDEV',
        'modulation_depth': 'FDEV'  # Add modulation depth mapping
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
    
    # Sweep function mappings
    SWEEP_FUNC_MAPPINGS = {
        'Sine': 0,
        'Ramp': 1,
        'Triangle': 2,
        'Square': 3,
        'Noise': 4,
        'External': 5
    }
    
    INTERNAL_TO_SWEEP_FUNC = {v: k for k, v in SWEEP_FUNC_MAPPINGS.items()}
    
    # Update dispatch mapping
    UPDATE_MAPPING = {
        'frequency': 'set_frequency',
        'power': 'set_power_rf',  # Use new RF power method
        'amplitude': 'set_amplitude_lo',  # Use new low freq amplitude method
        'amplitude_rf': 'set_amplitude_rf',  # Add RF amplitude mapping
        'phase': 'set_phase',
        'enable_output': '_set_output_enable',
        'enable_modulation': '_set_modulation_enable',
        'modulation_type': '_set_modulation_type',
        'modulation_function': '_set_modulation_function',
        'pulse_modulation_function': '_set_pulse_modulation_function',
        'dev_width': '_set_dev_width',
        'mod_rate': '_set_mod_rate',
        'sweep_function': '_set_sweep_function',
        'sweep_rate': '_set_sweep_rate',
        'sweep_deviation': '_set_sweep_deviation'
    }

    _DEFAULT_SETTINGS = Parameter([
        # Base settings from MicrowaveGeneratorBase
        Parameter('connection_type', 'LAN', ['LAN','GPIB','RS232'], 'Transport type'),
        Parameter('ip_address', '192.168.2.217', str, 'IP for LAN'),
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
        Parameter('modulation_type', 'FM', ['AM','FM','PM','Sweep','Freq sweep'], 'Modulation type'),
        Parameter('modulation_function', 'Sine', ['Sine','Ramp','Triangle','Square','Noise','External'], 'Modulation function'),
        Parameter('pulse_modulation_function', 'Square', ['Square','Noise(PRBS)','External'], 'Pulse modulation function'),
        Parameter('modulation_depth', 1e6, float, 'Deviation in Hz'),
        Parameter('dev_width', 1e6, float, 'Deviation width in Hz'),
        Parameter('mod_rate', 1e7, float, 'Modulation rate in Hz'),
        # Sweep parameters
        Parameter('sweep_function', 'Triangle', ['Sine','Ramp','Triangle','Square','Noise','External'], 'Sweep function'),
        Parameter('sweep_rate', 1.0, float, 'Sweep rate in Hz (must be < 120 Hz)'),
        Parameter('sweep_deviation', 1e6, float, 'Sweep deviation in Hz'),
        Parameter('sweep_center_frequency', 2.87e9, float, 'Sweep center frequency in Hz'),
        Parameter('sweep_max_frequency', 4.1e9, float, 'Sweep maximum frequency in Hz'),
        Parameter('sweep_min_frequency', 1.9e9, float, 'Sweep minimum frequency in Hz'),
        # add more SG384‐only knobs here…
    ])

    def __init__(self, name=None, settings=None):
        super().__init__(name, settings)
        # verify comms
        idn = self._query("*IDN?")
        logger.info(f"SG384 IDN: {idn}")

    def set_frequency(self, hz: float):
        """Set frequency using SCPI_MAPPINGS."""
        self.settings['frequency'] = hz
        param = self._param_to_scpi('frequency')
        self._send(f"{param} {hz}HZ")

    def set_power(self, dbm: float):
        """Set power using SCPI_MAPPINGS."""
        self.settings['amplitude'] = dbm
        param = self._param_to_scpi('power')
        self._send(f"{param} {dbm}DBM")

    def set_amplitude_rf(self, value: float, unit: str = "DBM"):
        """Set RF amplitude with flexible units.
        
        Args:
            value: Amplitude value
            unit: Unit type - "DBM" (default) or "V"/"RMS"/"VRMS"
        """
        self.settings['amplitude_rf'] = value
        param = self._param_to_scpi('amplitude_rf')
        
        if unit.upper() == "DBM":
            # Don't send DBM suffix - let SG384 use default
            self._send(f"{param} {value}")
        elif unit.upper() in ["V", "VRMS", "RMS"]:
            # Explicit unit needed for voltage
            self._send(f"{param} {value}RMS")
        else:
            raise ValueError(f"Unsupported unit: {unit}. Use 'DBM', 'V', 'RMS', or 'VRMS'")

    def set_amplitude_lo(self, value: float, unit: str = "DBM"):
        """Set low frequency amplitude with flexible units.
        
        Args:
            value: Amplitude value
            unit: Unit type - "DBM" (default) or "V"/"RMS"/"VRMS"
        """
        self.settings['amplitude'] = value
        param = self._param_to_scpi('amplitude')
        
        if unit.upper() == "DBM":
            # Don't send DBM suffix - let SG384 use default
            self._send(f"{param} {value}")
        elif unit.upper() in ["V", "VRMS", "RMS"]:
            # Explicit unit needed for voltage
            self._send(f"{param} {value}RMS")
        else:
            raise ValueError(f"Unsupported unit: {unit}. Use 'DBM', 'V', 'RMS', or 'VRMS'")

    def set_power_rf(self, dbm: float):
        """Set RF power in dBm (alias for set_amplitude_rf with dBm)."""
        self.set_amplitude_rf(dbm, "DBM")

    def set_power_lo(self, dbm: float):
        """Set low frequency power in dBm (alias for set_amplitude_lo with dBm)."""
        self.set_amplitude_lo(dbm, "DBM")

    def set_voltage_rf(self, voltage: float, unit: str = "RMS"):
        """Set RF voltage.
        
        Args:
            voltage: Voltage value
            unit: Unit type - "RMS" (default) or "V"/"VRMS"
        """
        self.set_amplitude_rf(voltage, unit)

    def set_voltage_lo(self, voltage: float, unit: str = "RMS"):
        """Set low frequency voltage.
        
        Args:
            voltage: Voltage value
            unit: Unit type - "RMS" (default) or "V"/"VRMS"
        """
        self.set_amplitude_lo(voltage, unit)

    def set_phase(self, deg: float):
        """Set phase using SCPI_MAPPINGS with step validation and stepping."""
        current_phase = float(self._query(self._param_to_scpi('phase') + '?'))  # Get current phase
        print(f"🔍 Current phase: {current_phase}°")
        
        # Calculate phase step (handle wraparound)
        phase_diff = abs(deg - current_phase)
        if phase_diff > 360:
            # Need to step in smaller increments
            print(f"⚠️  Phase step {phase_diff:.1f}° exceeds 360° limit. Current: {current_phase:.1f}°, Target: {deg:.1f}°")
            print(f"   Stepping phase in 360° increments...")
            logger.warning(f"Phase step {phase_diff:.1f}° exceeds 360° limit. Stepping from {current_phase:.1f}° to {deg:.1f}°")
            
            # Implement stepping logic
            if deg > current_phase:
                # Step up
                step_phase = current_phase + 360
                while step_phase < deg:
                    param = self._param_to_scpi('phase')
                    self._send(f"{param} {step_phase:.1f}DEG")
                    step_phase += 360
            else:
                # Step down
                step_phase = current_phase - 360
                while step_phase > deg:
                    param = self._param_to_scpi('phase')
                    self._send(f"{param} {step_phase:.1f}DEG")
                    step_phase -= 360
            
            print(f"   Final phase step: {deg:.1f}°")
            logger.info(f"Completed phase stepping to {deg:.1f}°")
        else:
            print(f"✅ Phase step {phase_diff:.1f}° within 360° limit. Setting directly to {deg:.1f}°")
            logger.info(f"Setting phase directly to {deg:.1f}° (step: {phase_diff:.1f}°)")
        
        self.settings['phase'] = deg
        param = self._param_to_scpi('phase')
        scpi_cmd = f"{param} {deg}DEG"
        print(f"📤 Sending SCPI command: {scpi_cmd}")
        self._send(scpi_cmd)
        
        # Verify the phase was set
        time.sleep(0.1)  # Give hardware time to process
        new_phase = float(self._query(self._param_to_scpi('phase') + '?'))
        print(f"🔍 Phase after setting: {new_phase}° (target: {deg}°)")
        
        if abs(new_phase - deg) > 0.1:
            print(f"⚠️  WARNING: Phase setting may have failed! Expected: {deg}°, Got: {new_phase}°")
            logger.warning(f"Phase setting may have failed! Expected: {deg}°, Got: {new_phase}°")

    def enable_modulation(self):
        param = self._param_to_scpi('enable_modulation')
        self._send(f"{param}:STAT ON")

    def disable_modulation(self):
        param = self._param_to_scpi('enable_modulation')
        self._send(f"{param}:STAT OFF")

    def set_modulation_type(self, mtype: str):
        self.settings['modulation_type'] = mtype
        param = self._param_to_scpi('modulation_type')
        self._send(f"{param} {mtype}")

    def set_modulation_depth(self, depth_hz: float):
        self.settings['modulation_depth'] = depth_hz
        param = self._param_to_scpi('modulation_depth')
        self._send(f"{param} {depth_hz}")
    
    def validate_sweep_parameters(self, center_freq: float, deviation: float, sweep_rate: float = None) -> bool:
        """
        Validate sweep parameters to ensure they're within SG384 limits.
        
        Args:
            center_freq: Center frequency in Hz
            deviation: Frequency deviation in Hz
            sweep_rate: Sweep rate in Hz (optional, for rate validation)
            
        Returns:
            True if parameters are valid
            
        Raises:
            ValueError: If parameters are outside valid range
        """
        min_freq = self.settings['sweep_min_frequency']
        max_freq = self.settings['sweep_max_frequency']
        
        sweep_min = center_freq - deviation
        sweep_max = center_freq + deviation
        
        if sweep_min < min_freq:
            raise ValueError(f"Sweep minimum frequency {sweep_min/1e9:.3f} GHz is below minimum {min_freq/1e9:.3f} GHz")
        
        if sweep_max > max_freq:
            raise ValueError(f"Sweep maximum frequency {sweep_max/1e9:.3f} GHz is above maximum {max_freq/1e9:.3f} GHz")
        
        # Validate sweep rate if provided
        if sweep_rate is not None and sweep_rate >= 120.0:
            raise ValueError(f"Sweep rate {sweep_rate} Hz must be less than 120 Hz")
        
        return True

    # Helper methods using mapping dictionaries
    def _param_to_scpi(self, param: str) -> str:
        """Convert parameter name to SCPI command using mapping dictionary."""
        if param not in self.SCPI_MAPPINGS:
            raise KeyError(f"Unknown parameter: {param}")
        return self.SCPI_MAPPINGS[param]
    
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
    
    def _sweep_func_to_internal(self, value: str) -> int:
        """Convert sweep function string to internal value using mapping dictionary."""
        if value not in self.SWEEP_FUNC_MAPPINGS:
            raise KeyError(f"Unknown sweep function: {value}")
        return self.SWEEP_FUNC_MAPPINGS[value]
    
    def _internal_to_sweep_func(self, value: int) -> str:
        """Convert internal sweep function value to string using mapping dictionary."""
        if value not in self.INTERNAL_TO_SWEEP_FUNC:
            raise KeyError(f"Unknown internal sweep function value: {value}")
        return self.INTERNAL_TO_SWEEP_FUNC[value]
    
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
                elif key == 'sweep_function':
                    value = self._sweep_func_to_internal(value)
                
                # Call the appropriate method
                method(value)
            else:
                logger.warning(f"Unknown parameter for update: {key}")
    
    # Setter methods for update dispatch
    def _set_output_enable(self, enable: int):
        """Set output enable/disable."""
        param = self._param_to_scpi('enable_rf_output')
        self._send(f"{param} {enable}")
    
    def _set_modulation_enable(self, enable: int):
        """Set modulation enable/disable."""
        param = self._param_to_scpi('enable_modulation')
        self._send(f"{param} {enable}")
    
    def _set_modulation_type(self, mod_type: int):
        """Set modulation type."""
        param = self._param_to_scpi('modulation_type')
        self._send(f"{param} {mod_type}")
    
    def _set_modulation_function(self, mod_func: int):
        """Set modulation function."""
        param = self._param_to_scpi('modulation_function')
        self._send(f"{param} {mod_func}")
    
    def _set_pulse_modulation_function(self, pulse_mod_func: int):
        """Set pulse modulation function."""
        param = self._param_to_scpi('pulse_modulation_function')
        self._send(f"{param} {pulse_mod_func}")
    
    def _set_dev_width(self, dev_width: float):
        """Set deviation width."""
        param = self._param_to_scpi('dev_width')
        self._send(f"{param} {dev_width}")
    
    def _set_mod_rate(self, mod_rate: float):
        """Set modulation rate."""
        param = self._param_to_scpi('mod_rate')
        self._send(f"{param} {mod_rate}")
    
    def _set_sweep_function(self, sweep_func: int):
        """Set sweep function."""
        param = self._param_to_scpi('sweep_function')
        self._send(f"{param} {sweep_func}")
    
    def _set_sweep_rate(self, sweep_rate: float):
        """Set sweep rate (must be < 120 Hz)."""
        if sweep_rate >= 120.0:
            raise ValueError(f"Sweep rate {sweep_rate} Hz must be less than 120 Hz")
        param = self._param_to_scpi('sweep_rate')
        self._send(f"{param} {sweep_rate}")
    
    def _set_sweep_deviation(self, sweep_deviation: float):
        """Set sweep deviation."""
        param = self._param_to_scpi('sweep_deviation')
        self._send(f"{param} {sweep_deviation}")

    def update(self, settings: dict):
        """
        Updates the internal settings and physical parameters using mapping dictionaries.
        This replaces the long if-elif chain from the original microwave_generator.py.
        """
        super().update(settings)
        
        # Send commands if device is connected
        if self.is_connected:
            self._dispatch_update(settings)
    
    @property
    def _PROBES(self):
        return {
            'enable_output': 'if type-N output is enabled',
            'frequency': 'frequency of output in Hz',
            # Low frequency output (BNC)
            'amplitude': 'low frequency amplitude in dBm',      # AMPL
            'amplitude_lo': 'low frequency amplitude in dBm',   # AMPL (alias)
            'power_lo': 'low frequency power in dBm',           # AMPL (alias)
            # RF output (Type-N)
            'amplitude_rf': 'RF amplitude in dBm',              # AMPR
            'power_rf': 'RF power in dBm',                      # AMPR (alias)
            'phase': 'phase',
            'enable_modulation': 'is modulation enabled',
            'modulation_type': 'Modulation Type: 0= AM, 1=FM, 2= PhaseM, 3= Freq sweep, 4= Pulse, 5 = Blank, 6=IQ',
            'modulation_function': 'Modulation Function: 0=Sine, 1=Ramp, 2=Triangle, 3=Square, 4=Noise, 5=External',
            'pulse_modulation_function': 'Pulse Modulation Function: 3=Square, 4=Noise(PRBS), 5=External',
            'dev_width': 'Width of deviation from center frequency in FM',
            'mod_rate': 'Rate of modulation in Hz',
            'sweep_function': 'Sweep Function: 0=Sine, 1=Ramp, 2=Triangle, 3=Square, 4=Noise, 5=External',
            'sweep_rate': 'Sweep rate in Hz',
            'sweep_deviation': 'Sweep deviation in Hz'
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
            'sweep_function': self._read_sweep_function_probe,
            
            # Float probes (return numeric values)
            'frequency': self._read_float_probe,
            'dev_width': self._read_float_probe,
            'mod_rate': self._read_float_probe,
            'sweep_rate': self._read_float_probe,
            'sweep_deviation': self._read_float_probe,
            
            # Output-specific amplitude probes
            'amplitude': self._read_amplitude_lo_probe,      # Low freq (AMPL)
            'amplitude_lo': self._read_amplitude_lo_probe,   # Low freq (AMPL)
            'power_lo': self._read_amplitude_lo_probe,       # Low freq (AMPL)
            'amplitude_rf': self._read_amplitude_rf_probe,   # RF (AMPR)
            'power_rf': self._read_amplitude_rf_probe,       # RF (AMPR)
            
            # Phase probe (dedicated method)
            'phase': self._read_phase_probe,
        }
        
        if key in probe_mapping:
            return probe_mapping[key](key)
        else:
            raise KeyError(f"No such probe: {key}")
    
    def _read_boolean_probe(self, key):
        """Read boolean probe values (enable_output, enable_modulation, etc.)."""
        key_internal = self._param_to_scpi(key)
        value = int(self._query(key_internal + '?'))
        return bool(value)
    
    def _read_modulation_type_probe(self, key):
        """Read modulation type probe values."""
        key_internal = self._param_to_scpi(key)
        value = int(self._query(key_internal + '?'))
        return self._internal_to_mod_type(value)
    
    def _read_modulation_function_probe(self, key):
        """Read modulation function probe values."""
        key_internal = self._param_to_scpi(key)
        value = int(self._query(key_internal + '?'))
        return self._internal_to_mod_func(value)
    
    def _read_pulse_modulation_function_probe(self, key):
        """Read pulse modulation function probe values."""
        key_internal = self._param_to_scpi(key)
        value = int(self._query(key_internal + '?'))
        return self._internal_to_pulse_mod_func(value)
    
    def _read_sweep_function_probe(self, key):
        """Read sweep function probe values."""
        key_internal = self._param_to_scpi(key)
        value = int(self._query(key_internal + '?'))
        return self._internal_to_sweep_func(value)
    
    def _read_float_probe(self, key):
        """Read float probe values (frequency, amplitude, phase, etc.)."""
        key_internal = self._param_to_scpi(key)
        return float(self._query(key_internal + '?'))

    def _read_amplitude_lo_probe(self, key):
        """Read low frequency amplitude from AMPL? command."""
        return float(self._query('AMPL?'))

    def _read_amplitude_rf_probe(self, key):
        """Read RF amplitude from AMPR? command."""
        return float(self._query('AMPR?'))
    
    def _read_phase_probe(self, key):
        """Read phase from PHAS? command."""
        raw_response = self._query('PHAS?')
        print(f"🔍 Raw phase response: '{raw_response}'")
        phase_value = float(raw_response)
        print(f"🔍 Parsed phase value: {phase_value}°")
        return phase_value
    
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
