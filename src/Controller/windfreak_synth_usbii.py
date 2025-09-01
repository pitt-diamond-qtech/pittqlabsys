# Created by gurudevdutt at 7/30/25
# controllers/usb_rf_generator.py

from .mw_generator_base import MicrowaveGeneratorBase, Parameter
import logging
import time

logger = logging.getLogger("usb_rf_generator")

class WindfreakSynthUSBII(MicrowaveGeneratorBase):
    """
    Windfreak SynthUSBII driver.
    Communicates over VISA (USB/RS232) using pyvisa.
    """

    _DEFAULT_SETTINGS = Parameter([
        # Base settings from MicrowaveGeneratorBase
        Parameter('connection_type', 'LAN', ['LAN','GPIB','RS232'], 'Transport type'),
        Parameter('ip_address', '',     str, 'IP for LAN'),
        Parameter('port',       5025,   int, 'Port for LAN'),
        Parameter('visa_resource', '',  str, 'PyVISA resource string, e.g. GPIB0::20::INSTR or ASRL9::INSTR'),
        Parameter('baud_rate',   115200,int, 'Baud for RS232'),
        # Windfreak-specific settings
        Parameter('frequency', 1000.0, float, 'frequency in MHz (0 to stop)'),
        Parameter('power',    -4,   [-4, -1, 2, 5], 'output power in dBm'),
        Parameter('reference','internal',['internal','external'], 'reference: internal/external'),
        Parameter('phase_lock','lock',['lock','unlock'],    'phase-lock: lock/unlock'),
        Parameter('sweep', {
            'freq_lower':        1000.0,
            'freq_upper':        2000.0,
            'freq_step':         100.0,
            'time_step':         0.3,
            'continuous_sweep':  False,
            'run_sweep':         False,
        }, dict, 'sweep parameters')
    ])

    def __init__(self, name=None, settings=None):
        super().__init__(name, settings)
        # on init, turn on output and apply defaults
        # Note: Don't call _send methods here as _inst may not be ready yet
        # These will be called when the device is actually used

    # --- basic SCPI wrappers -----------------------------------
    def set_frequency(self, mhz: float):
        """SCPI: f<mhz> sets frequency in MHz."""
        if mhz != 0.0:
            assert 35.0 <= mhz <= 4400.0, "Frequency out of range"
        self.settings['frequency'] = mhz
        self._send(f"f{mhz}")

    def set_power(self, dbm: float):
        """SCPI: a<code> sets power; map dBm->0-3."""
        code = { -4:0, -1:1, 2:2, 5:3 }[dbm]
        self.settings['power'] = dbm
        self._send(f"a{code}")

    def set_phase(self, deg: float):
        """SCPI: phase setting (not implemented for Windfreak)."""
        # Windfreak doesn't support phase setting, so we just store it
        self.settings['phase'] = deg
        # Could implement if the device supports it

    def set_reference(self, mode: str):
        """SCPI: x<0|1> sets internal(1)/external(0)."""
        val = {'external':0, 'internal':1}[mode]
        self.settings['reference'] = mode
        self._send(f"x{val}")

    def set_phase_lock(self, mode: str):
        """SCPI: p<0|1> lock/unlock."""
        val = {'unlock':0, 'lock':1}[mode]
        self.settings['phase_lock'] = mode
        self._send(f"p{val}")

    def set_continuous(self, on: bool):
        """SCPI: c<0|1> sets continuous sweep."""
        val = 1 if on else 0
        self.settings['sweep']['continuous_sweep'] = on
        self._send(f"c{val}")

    def run_sweep(self):
        """SCPI: g1 triggers a sweep run once."""
        self._send("g1")
        # auto-reset flag in settings
        self.settings['sweep']['run_sweep'] = False

    def set_sweep_params(self,
        lower: float, upper: float,
        step: float, tstep: float
    ):
        """SCPI: l<u>, u<upper>, s<step>, t<time-step>."""
        self.settings['sweep'].update({
            'freq_lower': lower,
            'freq_upper': upper,
            'freq_step': step,
            'time_step': tstep,
        })
        for cmd, val in (("l",lower), ("u",upper), ("s",step), ("t",tstep)):
            self._send(f"{cmd}{val}")

    # --- override update to dispatch to methods ----------------
    def update(self, new_settings: dict):
        super().update(new_settings)
        # Only send commands if _inst is available (i.e., not during initialization)
        if hasattr(self, '_inst') and self._inst is not None:
            for key, val in new_settings.items():
                if key == 'frequency':
                    self.set_frequency(val)
                elif key == 'power':
                    self.set_power(val)
                elif key == 'reference':
                    self.set_reference(val)
                elif key == 'phase_lock':
                    self.set_phase_lock(val)
                elif key == 'sweep':
                    sp = val
                    # set sub-parameters
                    self.set_sweep_params(
                        sp['freq_lower'], sp['freq_upper'],
                        sp['freq_step'],  sp['time_step']
                    )
                    if sp.get('continuous_sweep', False):
                        self.set_continuous(True)
                    if sp.get('run_sweep', False):
                        self.run_sweep()

    # --- probes ------------------------------------------------
    @property
    def _PROBES(self):
        return {
            'frequency': 'MHz',
            'power':     'dBm',
            'reference': 'internal/external',
            'phase_lock':'lock/unlock',
            'freq_lower':'MHz',
            'freq_upper':'MHz',
            'freq_step': 'MHz',
            'time_step': 'ms',
            'continuous_sweep': 'bool'
        }

    def read_probes(self, key):
        assert self._settings_initialized
        if key == 'frequency':
            return float(self._query('f?'))
        elif key == 'power':
            code = self._query('a?')
            return { '0':-4, '1':-1, '2':2, '3':5 }[code]
        elif key == 'reference':
            return { '0':'external', '1':'internal' }[self._query('x?')]
        elif key == 'phase_lock':
            return { '0':'unlock', '1':'lock' }[self._query('p?')]
        elif key == 'continuous_sweep':
            return self._query('c?') == '1'
        elif key in ('freq_lower','freq_upper','freq_step','time_step'):
            cmd = {'freq_lower':'l?','freq_upper':'u?',
                   'freq_step':'s?','time_step':'t?'}[key]
            return float(self._query(cmd))
        else:
            raise KeyError(f"No such probe: {key}")

