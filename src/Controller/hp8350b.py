# Created by Gurudev Dutt <gdutt@pitt.edu>
# HP 8350B sweep oscillator driver for external-sweep ODMR experiments.
#
# The HP8350B is controlled over GPIB. In external sweep mode (SX + T3) the
# NI-DAQ analog output voltage sets the microwave frequency between FA and FB.

import logging
from typing import Optional

import pyvisa

from src.core import Device, Parameter

logger = logging.getLogger("hp8350b")


class HP8350B(Device):
    """
    Hewlett-Packard 8350B sweep oscillator.

    Supports CW operation and external-voltage frequency sweep mode used with
    an NI-DAQ analog output channel. Frequency limits and voltage calibration
    parameters are stored in settings so students can match lab wiring.
    """

    _DEFAULT_SETTINGS = Parameter([
        Parameter('connection_type', 'GPIB', ['GPIB'], 'Transport type (HP8350B uses GPIB)'),
        Parameter('visa_resource', 'GPIB0::19::INSTR', str,
                  'PyVISA resource string, e.g. GPIB0::19::INSTR'),
        Parameter('connection_timeout_ms', 10000, int, 'VISA connection timeout in milliseconds'),
        Parameter('start_frequency', 2.80e9, float, 'External sweep start frequency FA (Hz)', units='Hz'),
        Parameter('stop_frequency', 2.95e9, float, 'External sweep stop frequency FB (Hz)', units='Hz'),
        Parameter('power', -10.0, float, 'Output power PL (dBm)', units='dBm'),
        Parameter('voltage_min', 0.0, float,
                  'AO voltage mapped to start_frequency (V). Match HP8350B external input wiring.',
                  units='V'),
        Parameter('voltage_max', 10.0, float,
                  'AO voltage mapped to stop_frequency (V). Match HP8350B external input wiring.',
                  units='V'),
        Parameter('output_enabled', False, bool, 'Whether RF output is currently enabled'),
        Parameter('sweep_mode', 'external', ['external', 'cw'], 'Operating mode'),
    ])

    _PROBES = {
        'start_frequency': 'Programmed sweep start frequency FA (Hz)',
        'stop_frequency': 'Programmed sweep stop frequency FB (Hz)',
        'power': 'Programmed output power PL (dBm)',
        'output_enabled': 'Whether RF output is enabled',
    }

    def __init__(self, name=None, settings=None):
        self._inst = None
        super().__init__(name, settings)
        self._connect()

    def _connect(self):
        rm = pyvisa.ResourceManager()
        resource = self.settings['visa_resource']
        self._inst = rm.open_resource(resource)
        self._inst.timeout = int(self.settings['connection_timeout_ms'])
        try:
            idn = self._inst.query('*IDN?').strip()
            logger.info("HP8350B connected: %s", idn)
            self._is_connected = True
        except Exception as exc:
            logger.warning("HP8350B *IDN? failed: %s", exc)
            self._is_connected = False

    def _write(self, cmd: str):
        if self._inst is None:
            raise RuntimeError("HP8350B is not connected")
        self._inst.write(cmd)

    def _query(self, cmd: str) -> str:
        if self._inst is None:
            raise RuntimeError("HP8350B is not connected")
        return self._inst.query(cmd).strip()

    @property
    def is_connected(self) -> bool:
        try:
            if self._inst is None:
                return False
            self._inst.query('*IDN?')
            return True
        except Exception:
            return False

    def close(self):
        if self._inst is not None:
            try:
                self._inst.close()
            except Exception:
                pass
            self._inst = None

    # ------------------------------------------------------------------
    # Frequency / voltage calibration helpers
    # ------------------------------------------------------------------

    @property
    def sweep_sensitivity(self) -> float:
        """Frequency change per volt (Hz/V) across the programmed sweep span."""
        v_span = self.settings['voltage_max'] - self.settings['voltage_min']
        if v_span == 0:
            raise ValueError("voltage_max must differ from voltage_min")
        f_span = self.settings['stop_frequency'] - self.settings['start_frequency']
        return f_span / v_span

    def voltage_to_frequency(self, voltage: float) -> float:
        """Convert AO voltage to microwave frequency using linear calibration."""
        v0 = self.settings['voltage_min']
        f0 = self.settings['start_frequency']
        return f0 + (voltage - v0) * self.sweep_sensitivity

    def frequency_to_voltage(self, frequency: float) -> float:
        """Convert microwave frequency to AO voltage using linear calibration."""
        f0 = self.settings['start_frequency']
        v0 = self.settings['voltage_min']
        return v0 + (frequency - f0) / self.sweep_sensitivity

    def voltages_to_frequencies(self, voltages):
        """Vectorized helper for experiment data analysis."""
        import numpy as np
        voltages = np.asarray(voltages, dtype=float)
        return self.settings['start_frequency'] + (
            voltages - self.settings['voltage_min']
        ) * self.sweep_sensitivity

    # ------------------------------------------------------------------
    # Instrument commands (based on legacy HP_Sweep.py)
    # ------------------------------------------------------------------

    def configure_external_sweep(
        self,
        start_freq: Optional[float] = None,
        stop_freq: Optional[float] = None,
        power: Optional[float] = None,
        enable_output: bool = True,
    ):
        """
        Configure external sweep mode.

        FA/FB set frequency endpoints, SX selects external sweep, T3 selects
        external trigger, RF1 enables microwave output.
        """
        start_freq = self.settings['start_frequency'] if start_freq is None else start_freq
        stop_freq = self.settings['stop_frequency'] if stop_freq is None else stop_freq
        power = self.settings['power'] if power is None else power

        self.settings['start_frequency'] = start_freq
        self.settings['stop_frequency'] = stop_freq
        self.settings['power'] = power
        self.settings['sweep_mode'] = 'external'

        self._write(f"FA {start_freq} GZ")
        self._write(f"FB {stop_freq} GZ")
        self._write(f"PL {power} DM")
        self._write("SX")
        self._write("T3")
        if enable_output:
            self.output_on()
        else:
            self.output_off()

    def set_cw_frequency(self, frequency: float):
        """Set CW frequency."""
        self.settings['sweep_mode'] = 'cw'
        self._write(f"CW {frequency} GZ")

    def set_frequency(self, frequency: float):
        """Alias for set_cw_frequency."""
        self.set_cw_frequency(frequency)

    def set_power(self, power: float):
        """Set output power in dBm."""
        self.settings['power'] = power
        self._write(f"PL {power} DM")

    def output_on(self):
        """Enable RF output (RF1)."""
        self._write("RF1")
        self.settings['output_enabled'] = True

    def output_off(self):
        """Disable RF output (RF0)."""
        self._write("RF0")
        self.settings['output_enabled'] = False

    def turn_off(self):
        """Alias for output_off."""
        self.output_off()

    def update(self, settings: dict):
        super().update(settings)
        if not self.is_connected:
            return

        if 'start_frequency' in settings or 'stop_frequency' in settings or 'power' in settings:
            if self.settings.get('sweep_mode', 'external') == 'external':
                self.configure_external_sweep(enable_output=self.settings.get('output_enabled', False))
        if 'power' in settings and self.settings.get('sweep_mode') == 'cw':
            self.set_power(settings['power'])

    def read_probes(self, key):
        assert key in self._PROBES
        if key == 'output_enabled':
            return bool(self.settings['output_enabled'])
        return self.settings[key]
