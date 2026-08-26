# Created by Gurudev Dutt <gdutt@pitt.edu>
# Stepped voltage sweep experiment for HP8350B external-sweep ODMR.
#
# Sweeps an NI-DAQ analog output voltage while counting photons at each step.
# Voltages are converted to microwave frequencies using HP8350B calibration.

import time

import numpy as np

from src.core import Experiment, Parameter


class HP8350BVoltageSweep(Experiment):
    """
    Stepped voltage sweep with photon counting for HP8350B external-sweep ODMR.

    The PCI6229 (or compatible NI-DAQ) outputs a voltage ramp on an analog output
    channel. That voltage controls the HP8350B frequency in external sweep mode.
    Photon counts are acquired either from a counter input (APD / photon counter)
    or from an analog input (bright photodiode signal).

    Hardware wiring (typical lab setup):
      - PCI6229 AO0 -> HP8350B external frequency input
      - PCI6229 ctr0 PFI -> APD pulse input  (count_mode='counter')
      - PCI6229 ai0      -> photodiode       (count_mode='analog')
      - Optional PCI6601 provides external sample clock when both AO and counter
        are used on PCI6229 (same pattern as GalvoScan).
    """

    _DEFAULT_SETTINGS = [
        Parameter('sweep', [
            Parameter('start_frequency', 2.80e9, float, 'Sweep start frequency (Hz)', units='Hz'),
            Parameter('stop_frequency', 2.95e9, float, 'Sweep stop frequency (Hz)', units='Hz'),
            Parameter('num_points', 50, int, 'Number of voltage/frequency steps'),
            Parameter('voltage_min', 0.0, float, 'AO voltage at start_frequency (V)', units='V'),
            Parameter('voltage_max', 10.0, float, 'AO voltage at stop_frequency (V)', units='V'),
        ]),
        Parameter('microwave', [
            Parameter('power', -10.0, float, 'HP8350B output power (dBm)', units='dBm'),
            Parameter('turn_off_after', True, bool, 'Disable HP8350B output after sweep'),
        ]),
        Parameter('timing', [
            Parameter('time_per_pt', 0.010, float, 'Integration time per point (s)', units='s'),
            Parameter('settle_time', 0.002, float, 'Settle time after voltage step (s)', units='s'),
        ]),
        Parameter('count_mode', 'counter', ['counter', 'analog'],
                  "counter: gated photon counter on ctr channel; "
                  "analog: average AI voltage (photodiode for bright signals)"),
        Parameter('DAQ_channels', [
            Parameter('ao_channel', 'ao0', ['ao0', 'ao1', 'ao2', 'ao3'],
                      'Analog output channel driving HP8350B frequency input'),
            Parameter('counter_channel', 'ctr0', ['ctr0', 'ctr1'],
                      'Counter channel for APD pulses (count_mode=counter)'),
            Parameter('analog_input_channel', 'ai0', ['ai0', 'ai1', 'ai2', 'ai3'],
                      'Analog input for photodiode (count_mode=analog)'),
        ]),
        Parameter('use_external_counter_clock', True, bool,
                  'Use external clock for counter (recommended with PCI6229 AO + PCI6601)'),
        Parameter('counter_daq', 'same', ['same', 'secondary'],
                  "Which DAQ provides the counter: 'same' uses daq, "
                  "'secondary' uses daq2 (e.g. PCI6601)"),
        Parameter('plot_style', 'main', ['main', 'aux', '2D', 'two']),
    ]

    _DEVICES = {
        'hp8350b': 'hp8350b',
        'daq': 'pci6229',
        'daq2': 'pci6601',
    }

    _EXPERIMENTS = {}

    def __init__(self, devices=None, name=None, settings=None, log_function=None, data_path=None):
        super().__init__(name=name, settings=settings, devices=devices,
                         log_function=log_function, data_path=data_path)
        self.hp = self.devices['hp8350b']['instance']
        self.ao_daq = self.devices['daq']['instance']
        self.counter_daq = self._get_counter_daq()
        self.setup_sweep()

    def _get_counter_daq(self):
        if self.settings['counter_daq'] == 'secondary':
            if 'daq2' not in self.devices:
                raise ValueError("counter_daq='secondary' requires daq2 in devices dict")
            return self.devices['daq2']['instance']
        return self.ao_daq

    def setup_sweep(self):
        sweep = self.settings['sweep']
        self.hp.update({
            'start_frequency': sweep['start_frequency'],
            'stop_frequency': sweep['stop_frequency'],
            'power': self.settings['microwave']['power'],
            'voltage_min': sweep['voltage_min'],
            'voltage_max': sweep['voltage_max'],
        })

        self.clock_adjust = int(
            (self.settings['timing']['time_per_pt'] + self.settings['timing']['settle_time'])
            / self.settings['timing']['settle_time']
        )
        if self.clock_adjust < 1:
            self.clock_adjust = 1

        v_min = sweep['voltage_min']
        v_max = sweep['voltage_max']
        base_voltages = np.linspace(v_min, v_max, sweep['num_points'], endpoint=True)
        self.voltage_array = np.repeat(base_voltages, self.clock_adjust)
        self.frequency_array = self.hp.voltages_to_frequencies(base_voltages)

        sample_rate = 1.0 / self.settings['timing']['settle_time']
        ao_ch = self.settings['DAQ_channels']['ao_channel']
        self.ao_daq.settings['analog_output'][ao_ch]['sample_rate'] = sample_rate

        if self.settings['count_mode'] == 'counter':
            ctr_ch = self.settings['DAQ_channels']['counter_channel']
            self.counter_daq.settings['digital_input'][ctr_ch]['sample_rate'] = sample_rate
        else:
            ai_ch = self.settings['DAQ_channels']['analog_input_channel']
            self.ao_daq.settings['analog_input'][ai_ch]['sample_rate'] = sample_rate

    def _setup_microwave(self):
        self.log("Configuring HP8350B for external sweep...")
        self.hp.configure_external_sweep(
            start_freq=self.settings['sweep']['start_frequency'],
            stop_freq=self.settings['sweep']['stop_frequency'],
            power=self.settings['microwave']['power'],
            enable_output=True,
        )

    def _cleanup_microwave(self):
        if self.settings['microwave']['turn_off_after']:
            self.hp.output_off()

    def _read_sweep_counter(self):
        """Synchronized AO voltage ramp + counter read (GalvoScan-style)."""
        ao_ch = self.settings['DAQ_channels']['ao_channel']
        ctr_ch = self.settings['DAQ_channels']['counter_channel']
        use_ext_clk = self.settings['use_external_counter_clock']

        ctr_task = self.counter_daq.setup_counter(
            ctr_ch, len(self.voltage_array) + 1, use_external_clock=use_ext_clk
        )

        init_pt = np.array([self.voltage_array[0]], dtype=float)
        ao_task = self.ao_daq.setup_AO([ao_ch], init_pt, "")
        self.ao_daq.run(ao_task)
        self.ao_daq.stop(ao_task)

        ao_task = self.ao_daq.setup_AO([ao_ch], self.voltage_array, clk_source=ctr_task)
        self.ao_daq.run(ao_task)
        self.counter_daq.run(ctr_task)

        self.ao_daq.stop(ao_task)
        raw_data, _ = self.counter_daq.read(ctr_task)
        self.counter_daq.stop(ctr_task)

        diff_data = np.diff(raw_data)
        n_bins = int(len(self.voltage_array) / self.clock_adjust)
        summed = np.zeros(n_bins)
        for i in range(n_bins):
            start = i * self.clock_adjust + 1
            end = i * self.clock_adjust + self.clock_adjust - 1
            summed[i] = np.sum(diff_data[start:end])

        normalization = 0.001 / self.settings['timing']['time_per_pt']
        return summed * normalization

    def _read_sweep_analog(self):
        """Stepped sweep using analog input averaging (photodiode mode)."""
        ao_ch = self.settings['DAQ_channels']['ao_channel']
        ai_ch = self.settings['DAQ_channels']['analog_input_channel']
        time_per_pt = self.settings['timing']['time_per_pt']
        settle = self.settings['timing']['settle_time']
        sample_rate = 1.0 / self.settings['timing']['settle_time']
        n_samples = max(int(time_per_pt * sample_rate), 2)

        counts = []
        base_voltages = np.linspace(
            self.settings['sweep']['voltage_min'],
            self.settings['sweep']['voltage_max'],
            self.settings['sweep']['num_points'],
            endpoint=True,
        )
        for voltage in base_voltages:
            if self._abort:
                break
            pt = np.array([voltage], dtype=float)
            ao_task = self.ao_daq.setup_AO([ao_ch], pt)
            self.ao_daq.run(ao_task)
            self.ao_daq.AO_waitToFinish()
            self.ao_daq.stop(ao_task)
            time.sleep(settle)

            ai_task = self.ao_daq.setup_AI(ai_ch, n_samples)
            self.ao_daq.run(ai_task)
            self.ao_daq.AO_waitToFinish()
            data, _ = self.ao_daq.read(ai_task)
            self.ao_daq.stop(ai_task)
            counts.append(float(np.mean(np.asarray(data).flatten())))

        return np.asarray(counts)

    def _function(self):
        self.log("Starting HP8350B voltage sweep...")
        self._setup_microwave()

        try:
            if self.settings['count_mode'] == 'counter':
                count_data = self._read_sweep_counter()
            else:
                count_data = self._read_sweep_analog()

            voltages = np.linspace(
                self.settings['sweep']['voltage_min'],
                self.settings['sweep']['voltage_max'],
                self.settings['sweep']['num_points'],
                endpoint=True,
            )
            frequencies = self.hp.voltages_to_frequencies(voltages)

            self.data = {
                'voltages': voltages,
                'frequencies': frequencies,
                'counts': count_data,
                'count_mode': self.settings['count_mode'],
                'frequency_ghz': frequencies / 1e9,
            }
            self.log(
                f"Sweep complete: {len(voltages)} points, "
                f"avg rate {np.mean(count_data):.2f} kcps"
            )
        finally:
            self._cleanup_microwave()

    def plot(self, figure_list):
        super().plot([figure_list[0]])

    def _plot(self, axes_list, data=None):
        if data is None:
            data = self.data
        if data is None or len(data.get('counts', [])) == 0:
            return
        ax = axes_list[0]
        ax.clear()
        ax.plot(data['frequency_ghz'], data['counts'], 'b.-')
        ax.set_xlabel('Frequency (GHz)')
        ax.set_ylabel('Counts (kcps)' if self.settings['count_mode'] == 'counter' else 'AI voltage (V)')
        ax.set_title('HP8350B voltage sweep')
        ax.grid(True, alpha=0.3)

    def _update_plot(self, axes_list, data=None):
        if data is None:
            data = self.data
        if data and len(data.get('counts', [])) > 0:
            axes_list[0].plot(data['frequency_ghz'], data['counts'], 'b.-')


if __name__ == '__main__':
    experiment, failed, devices = Experiment.load_and_append(
        experiment_dict={'HP8350BVoltageSweep': HP8350BVoltageSweep},
        raise_errors=True,
    )
    print(experiment)
    print(failed)
