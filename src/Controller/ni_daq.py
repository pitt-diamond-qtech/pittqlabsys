# Created by Gurudev Dutt <gdutt@pitt.edu> on 2020-07-31
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
from src.core.read_write_functions import get_config_value
from PyQt5.QtCore import QThread
import nidaqmx as ni
from nidaqmx.constants import AcquisitionType, UnitsPreScaled, Edge, LineGrouping
from nidaqmx.stream_writers import DigitalMultiChannelWriter, AnalogMultiChannelWriter,AnalogSingleChannelWriter
from nidaqmx.stream_readers import CounterReader, AnalogMultiChannelReader,AnalogSingleChannelReader
import numpy as np
import time

#########################################################################################
# NI DAQmx Analog constants
DAQmx_Val_Cfg_Default = int(-1)
DAQmx_Val_Volts = UnitsPreScaled.VOLTS.value
DAQmx_Val_Rising = Edge.RISING.value
DAQmx_Val_Falling = Edge.FALLING.value
DAQmx_Val_FiniteSamps = AcquisitionType.FINITE.value
DAQmx_Val_ContSamps = AcquisitionType.CONTINUOUS.value
DAQmx_Val_GroupByChannel = ni.constants.FillMode.GROUP_BY_CHANNEL.value

# DI constants
DAQmx_Val_CountUp = ni.constants.CountDirection.COUNT_UP.value
DAQmx_Val_Hz = ni.constants.UnitsPreScaled.HERTZ.value  # Hz
DAQmx_Val_Low = ni.constants.Level.LOW.value  # Low
DAQmx_Val_Seconds = ni.constants.UnitsPreScaled.SECONDS.value
DAQmx_Val_Ticks = ni.constants.UnitsPreScaled.TICKS.value  # specifies units as timebase ticks

DAQmx_Val_ChanPerLine = ni.constants.LineGrouping.CHAN_PER_LINE.value  # One Channel For Each Line
DAQmx_Val_ChanForAllLines = ni.constants.LineGrouping.CHAN_FOR_ALL_LINES.value  # One Channel For All Lines


class NIDAQ(Device):
    """
    Class containing all functions used to interact with the NI DAQ, mostly
    acting as a wrapper around python functions provided by NI. Tested on an
    NI PXI 6733 and PCI 6281, but should be compatable with most daqmx devices. Supports
    analog output (ao), analog input (ai), and digital input (di) channels.
    Also supports gated digital input, using one PFI channel as a counter
    and a second as a clock.

    In general, the order of calls to use one of these channels is:
    setup
    run
    (read or write if required)
    stop

    In general, 'setup' sets up the buffer, either filling it with the values to
    output or telling it to ready for input, and locks the task so the correct clock.
    'Run' starts the input to or output from the buffer.
    'Read' sends data from the buffer to the computer (if applicable).
    'Stop' ends the task and cleans up.
    """

    tasklist = {}
    tasknum = 0

    # currently includes four analog outputs, five analog inputs, and one digital counter input. Add
    # more as needed and your device allows
    # TODO: write a function that loads all the parameters from a .cfg or .ini file for that instrument
    _DEFAULT_SETTINGS = Parameter([
        Parameter('device', 'Dev1', ['Dev1', "PXI1Slot3", "PXI1Slot8"], 'Name of NI-DAQ device'),
        Parameter('override_buffer_size', -1, int, 'Buffer size for manual override (unused if -1)'),
        Parameter('ao_read_offset', .005, float, 'Empirically determined offset for reading ao voltages internally',
                  units='V'),
        Parameter('analog_output', [
            Parameter('ao0', [
                Parameter('channel', 0, [0, 1, 2, 3], 'output channel'),
                Parameter('sample_rate', 1000.0, float, 'output sample rate (Hz)', units="Hz"),
                Parameter('min_voltage', -10.0, float, 'minimum output voltage (V)', units="V"),
                Parameter('max_voltage', 10.0, float, 'maximum output voltage (V)', units="V")
            ]),
            Parameter('ao1', [
                Parameter('channel', 1, [0, 1, 2, 3], 'output channel'),
                Parameter('sample_rate', 1000.0, float, 'output sample rate (Hz)', units="Hz"),
                Parameter('min_voltage', -10.0, float, 'minimum output voltage (V)', units="V"),
                Parameter('max_voltage', 10.0, float, 'maximum output voltage (V)', units="V")
            ]),
            Parameter('ao2', [
                Parameter('channel', 2, [0, 1, 2, 3], 'output channel'),
                Parameter('sample_rate', 1000.0, float, 'output sample rate (Hz)', units="Hz"),
                Parameter('min_voltage', -10.0, float, 'minimum output voltage (V)', units="V"),
                Parameter('max_voltage', 10.0, float, 'maximum output voltage (V)', units="V")
            ]),
            Parameter('ao3', [
                Parameter('channel', 3, [0, 1, 2, 3], 'output channel'),
                Parameter('sample_rate', 1000.0, float, 'output sample rate (Hz)', units="Hz"),
                Parameter('min_voltage', -10.0, float, 'minimum output voltage (V)', units="V"),
                Parameter('max_voltage', 10.0, float, 'maximum output voltage (V)', units="V")
            ])
        ]),
        Parameter('analog_input', [
            Parameter('ai0',
                      [
                          Parameter('channel', 0, list(range(0, 32)), 'input channel'),
                          Parameter('sample_rate', 1000.0, float, 'input sample rate (Hz)', units="Hz"),
                          Parameter('min_voltage', -10.0, float, 'minimum input voltage'),
                          Parameter('max_voltage', 10.0, float, 'maximum input voltage')
                      ]
                      ),
            Parameter('ai1', [
                Parameter('channel', 1, list(range(0, 32)), 'input channel'),
                Parameter('sample_rate', 1000.0, float, 'input sample rate', units="Hz"),
                Parameter('min_voltage', -10.0, float, 'minimum input voltage'),
                Parameter('max_voltage', 10.0, float, 'maximum input voltage')
            ]),
            Parameter('ai2',
                      [
                          Parameter('channel', 2, list(range(0, 32)), 'input channel'),
                          Parameter('sample_rate', 1000.0, float, 'input sample rate', units="Hz"),
                          Parameter('min_voltage', -10.0, float, 'minimum input voltage'),
                          Parameter('max_voltage', 10.0, float, 'maximum input voltage')
                      ]
                      ),
            Parameter('ai3',
                      [
                          Parameter('channel', 3, list(range(0, 32)), 'input channel'),
                          Parameter('sample_rate', 1000.0, float, 'input sample rate', units="Hz"),
                          Parameter('min_voltage', -10.0, float, 'minimum input voltage'),
                          Parameter('max_voltage', 10.0, float, 'maximum input voltage')
                      ]
                      ),
            Parameter('ai4',
                      [
                          Parameter('channel', 4, list(range(0, 32)), 'input channel'),
                          Parameter('sample_rate', 1000.0, float, 'input sample rate', units="Hz"),
                          Parameter('min_voltage', -10.0, float, 'minimum input voltage'),
                          Parameter('max_voltage', 10.0, float, 'maximum input voltage (V)')
                      ]
                      )
        ]),
        Parameter('digital_input', [
            Parameter('ctr0', [
                Parameter('input_channel', 0, list(range(0, 32)), 'channel for counter signal input'),
                Parameter('counter_PFI_channel', 8, list(range(0, 32)), 'PFI for counter channel input'),
                Parameter('gate_PFI_channel', 9, list(range(0, 32)), 'PFI for counter channel input'),
                Parameter('clock_PFI_channel', 13, list(range(0, 32)), 'PFI for clock channel output'),
                Parameter('clock_counter_channel', 1, [0, 1], 'channel for clock output'),
                Parameter('sample_rate', 1000.0, float, 'input sample rate (Hz)', units="Hz")
            ]),
            Parameter('ctr1', [
                Parameter('input_channel', 1, list(range(0, 32)),
                          'channel for counter signal input'),
                Parameter('counter_PFI_channel', 3, list(range(0, 32)),
                          'PFI for counter channel input'),
                Parameter('gate_PFI_channel', 4, list(range(0, 32)),
                          'PFI for counter channel input'),
                Parameter('clock_PFI_channel', 12, list(range(0, 32)), 'PFI for clock channel output'),
                Parameter('clock_counter_channel', 0, [0, 1], 'channel for clock output'),
                Parameter('sample_rate', 1000.0, float, 'input sample rate (Hz)', units="Hz")
            ])
        ]),
        Parameter('digital_output', [
            Parameter('do0', [
                Parameter('channel', 0, list(range(0, 16)), 'channel')
            ]),
            Parameter('do8',
                      [
                          Parameter('channel', 8, list(range(0, 16)), 'channel')
                      ]
                      )
        ])
    ])

    def __init__(self, name=None, settings=None):
        try:
            local_system = ni.system.System.local()
            driver_version = local_system.driver_version

            print(
                "DAQmx {0}.{1}.{2}".format(
                    driver_version.major_version,
                    driver_version.minor_version,
                    driver_version.update_version,
                )
            )
            self.local_system = local_system
            # print("NI-DAQ System Version: %s", system.driver_version)
            super(NIDAQ, self).__init__(name, settings)
        except:
            raise EnvironmentError('Cannot load device, no DAQ system detected')

    def update(self, settings):
        """
        Updates daq settings for each channel in the software instrument.
        Unlike most instruments, all of the settings are sent to the DAQ on instantiation of
        a task, such as an input or output. Thus, changing the settings only updates the internal
        daq construct in the program and makes no hardware changes.
        Args:
            settings: a settings dictionary in the standard form
        """
        super(NIDAQ, self).update(settings)
        for key, value in settings.items():
            if key == 'device':
                if not (self.is_connected):
                    raise EnvironmentError('Device invalid, cannot connect to DAQ')

    def _add_to_tasklist(self, name, task):
        matching = [x for x in self.tasklist if name in x]
        if not matching:
            task_name = name + '000'
        else:
            last_task = sorted(matching)[-1]
            task_name = name + '{0:03d}'.format(int(last_task[-3:]) + 1)
        self.tasklist.update({task_name: task})
        return task_name

    @property
    def _PROBES(self):
        return None

    def read_probes(self, key):
        pass

    @property
    def is_connected(self):
        """
        Makes a non-state-changing call (a get id call) to check connection to a daq
        Returns: True if daq is connected, false if it is not
        """
        buf_size = 10
        # data = ctypes.create_string_buffer(('\000' * buf_size).encode('ascii'))
        try:
            # Calls arbitrary function to check connection
            # self._check_error(
            #     self.nidaq.DAQmxGetDevProductType(self.settings['device'].encode('ascii'), ctypes.byref(data),
            #                                       buf_size))
            dev = ni.system.device.Device(self.settings['device'])
            serial_num = dev.serial_num
            return True
        except RuntimeError:
            return False

    def setup_counter(self, channel, sample_num, continuous_acquisition=False):
        """
        Initializes a hardware-timed digital counter, bound to a hardware clock
        Args:
            channel: digital channel to initialize for read in
            sample_num: number of samples to read in for finite operation, or number of samples between
                       reads for continuous operation (to set buffer size)
            continuous_acquisition: run in continuous acquisition mode (ex for a continuous counter) or
                                    finite acquisition mode (ex for a scan, where the number of samples needed
                                    is known a priori)

        Returns: source of clock that this method sets up, which can be given to another function to synch that
        input or output to the same clock

        """

        # Note that for this counter, we have two tasks. The normal 'task_handle' corresponds to the clock, and this
        # is the task which is started when run is called. The second 'task_handle_ctr' corresponds to the counter,
        # and this waits for the clock and will be started simultaneously.
        task = {
            'task_handle': None,
            'task_handle_ctr': None,
            'counter_out_PFI_str': None,
            'sample_num': None,
            'sample_rate': None,
            'num_samples_per_channel': None,
            'timeout': None
        }

        task_name = self._add_to_tasklist('ctr', task)

        if 'digital_input' not in list(self.settings.keys()):
            raise ValueError('This DAQ does not support digital input')
        if not channel in list(self.settings['digital_input'].keys()):
            raise KeyError('This is not a valid digital input channel')
        channel_settings = self.settings['digital_input'][channel]
        self.running = True
        task['sample_num'] = sample_num
        task['sample_rate'] = float(channel_settings['sample_rate'])
        if not continuous_acquisition:
            task['num_samples_per_channel'] = task['sample_num']
        else:
            task['num_samples_per_channel'] = -1
        task['timeout'] = float(5 * (1 / task['sample_rate']) * task['sample_num'])
        input_channel_str = ('/' +self.settings['device'] + '/' + channel).encode('ascii')
        task['counter_out_PFI_str'] = ('/' + self.settings['device'] + '/PFI' + str(
            channel_settings['clock_PFI_channel'])).encode(
            'ascii')  # initial / required only here, see NIDAQ documentation
        counter_out_str = ('/' +self.settings['device'] + '/ctr' + str(channel_settings['clock_counter_channel'])).encode(
            'ascii')
        # with ni.Task() as clock_task, ni.Task() as counter_task:
        clock_task = ni.Task()
        counter_task = ni.Task()
        task['task_handle'] = clock_task
        task['task_handle_ctr'] = counter_task
        clock_task.co_channels.add_co_pulse_chan_freq(counter_out_str, freq=float(task['sample_rate']),
                                                      duty_cycle=0.5)
        counter_task.ci_channels.add_ci_count_edges_chan(input_channel_str)
        # set up clock
        clock_task.timing.cfg_implicit_timing(samps_per_chan=int(task['sample_num']))

        # set up counter using clock as reference
        # PFI13 is standard output channel for ctr1 channel used for clock and
        # is internally looped back to ctr1 input to be read
        if not continuous_acquisition:

            counter_task.timing.cfg_samp_clk_timing(float(task['sample_rate']), source=task['counter_out_PFI_str'],
                                                    samps_per_chan=task['sample_num'])
        else:

            counter_task.timing.cfg_samp_clk_timing(float(task['sample_rate']), source=task['counter_out_PFI_str'],
                                                    sample_mode=AcquisitionType.CONTINUOUS)

        # self._check_error(self.nidaq.DAQmxStartTask(task['task_handle_ctr']))
        counter_task.start()
        # clock_task.start()

        return task_name

    def _dig_pulse_train_cont(self, task, duty_cycle, counter_out_str):
        """
        Initializes a digital pulse train to act as a reference clock, really here for backward compatibility
        as most of these functions are re-implemented by the counter/timer functions themselves.
        Args:
            Freq: frequency of reference clock
            DutyCycle: percentage of cycle that clock should be high voltage (usually .5)
            Samps: number of samples to generate

        Returns:

        """
        pulse_train_task = task['task_handle']
        co_channel = pulse_train_task.co_channels.add_co_pulse_chan_freq(counter_out_str,
                                                                         freq=float(pulse_train_task['sample_rate']),
                                                                         duty_cycle=duty_cycle)
        pulse_train_task.timing.cfg_implicit_timing(samps_per_chan=int(pulse_train_task['sample_num']))

    def setup_clock(self, channel, sample_num):
        task = {
            'task_handle': None,
            'counter_out_PFI_str': None,
            'sample_num': None,
            'sample_rate': None,
            'num_samples_per_channel': None,
            'timeout': None
        }
        task_name = self._add_to_tasklist('clk', task)

        channel_settings = self.settings['digital_input'][channel]
        counter_out_str = (self.settings['device'] + '/ctr' + str(channel_settings['clock_counter_channel'])).encode(
            'ascii')
        task['sample_num'] = sample_num
        task['sample_rate'] = float(channel_settings['sample_rate'])
        task['counter_out_PFI_str'] = ('/' + self.settings['device'] + '/PFI' + str(
            channel_settings['clock_PFI_channel'])).encode('ascii')
        # self._dig_pulse_train_cont(task, .5, counter_out_str)
        # with ni.Task() as clk_task:
        #     task['task_handle'] = clk_task
        #     clk_task.co_channels.add_co_pulse_chan_freq(counter_out_str, freq=float(task['sample_rate']), )
        #     clk_task.timing.cfg_implicit_timing(samps_per_chan=int(task['sample_num']))
        clk_task = ni.Task()
        task['task_handle'] = clk_task
        clk_task.co_channels.add_co_pulse_chan_freq(counter_out_str, freq=float(task['sample_rate']))
        clk_task.timing.cfg_implicit_timing(samps_per_chan=int(task['sample_num']))
        return task_name

    def setup_gated_counter(self, channel, num_samples):
        """
        Initializes a gated digital input task. The gate acts as a clock for the counter, so if one has a fast ttl source
        this allows one to read the counter for a shorter time than would be allowed by the daq's internal clock.
        Args:
            channel: channel to use for counter input
            num_samples: number of samples to read on counter
        """
        if 'digital_input' not in list(self.settings.keys()):
            raise ValueError('This DAQ does not support digital input')
        if not channel in list(self.settings['digital_input'].keys()):
            raise KeyError('This is not a valid digital input channel')
        channel_settings = self.settings['digital_input'][channel]

        task = {
            'task_handle': None,
            'sample_num': None,
            'sample_rate': None,
            'num_samples_per_channel': None,
            'timeout': None
        }

        task_name = self._add_to_tasklist('gatedctr', task)

        input_channel_str_gated = (self.settings['device'] + '/' + channel).encode('ascii')
        counter_out_PFI_str_gated = ('/' + self.settings['device'] + '/PFI' + str(
            channel_settings['counter_PFI_channel'])).encode(
            'ascii')  # initial / required only here, see NIDAQ documentation
        gate_PFI_str = ('/' + self.settings['device'] + '/PFI' + str(
            channel_settings['gate_PFI_channel'])).encode(
            'ascii')  # initial / required only here, see NIDAQ documentation

        # set both to same value, no option for continuous counting (num_samples_per_channel == -1) with gated counter
        task['sample_num'] = num_samples
        task['num_samples_per_channel'] = num_samples
        # with ni.Task() as task_ctr:
        task_ctr = ni.Task()
        task['task_handle'] = task_ctr
        MIN_TICKS = 0
        MAX_TICKS = 100000

        # setup counter to measure pulse widths
        task_ctr.ci_channels.add_ci_pulse_width_chan(input_channel_str_gated, min_val=MIN_TICKS, max_val=MAX_TICKS)
        # specify number of samples to acquire
        task_ctr.timing.cfg_implicit_timing(sample_mode=AcquisitionType.FINITE,
                                            samps_per_chan=int(task['sample_num']))
        # set the terminal for the counter timebase source to the APD source
        # in B103, this is the ctr0 source PFI8, but this will vary from daq to daq
        task_ctr.ci_channels[0].ci_ctr_timebase_src = counter_out_PFI_str_gated
        # set the terminal for the gate to the pulseblaster source
        # in B103, due to crosstalk issues when we use the default PFI9 which is adjacent to the ctr0 source, we set this
        # to the non-default value PFI5
        task_ctr.ci_channels[0].ci_pulse_width_term = gate_PFI_str
        # turn on duplicate count prevention (allows 0 counts to be a valid count for clock ticks during a gate, even
        # though the timebase never went high and thus nothing would normally progress, by also referencing to the internal
        # clock at max frequency, see http://zone.ni.com/reference/en-XX/help/370466AC-01/mxdevconsid/dupcountprevention/
        # for more details)
        task_ctr.ci_channels[0].ci_dup_count_prevention = True

        return task_name

    # read sample_num previously generated values from a buffer, and return the
    # corresponding 1D array of ctypes.c_double values
    def read_counter(self, task_name):
        """
        read sample_num previously generated values from a buffer, and return the
        corresponding 1D numpy array of float values
        Returns: 1d numpy array of float values with the requested counts. Counts as given by the daq are a running
            total, that is if you get 5 counts/s, the returned array will be [5,10,15,20...]

        """
        task = self.tasklist[task_name]

        # difference between gated and non gated counter: the non-gated has a separate clock, while the gated one doesn't
        # For the gated case the task it self is also the clock
        # so if there is not extra handle for the clock we use the task_handle
        if 'task_handle_ctr' in task:
            task_handle_ctr = task['task_handle_ctr']
        else:
            task_handle_ctr = task['task_handle']

        # initialize array and integer to pass as pointers
        # data = (float * task['sample_num'])()
        # samplesPerChanRead = int32()
        # initialize a numpy array and subtract 10 so we know if the value returned was 0 or never updated.
        #data = np.zeros(task['num_samples_per_channel']) - 10
        data = np.zeros(task['sample_num']) -10

        reader = CounterReader(task_handle_ctr.in_stream)

        samples_read = reader.read_many_sample_double(data,
                                                      number_of_samples_per_channel=task['sample_num'])

        return data, samples_read

    def setup_AO(self, channels, waveform, clk_source=""):
        """
        Initializes a arbitrary number of analog output channels to output an arbitrary waveform
        Args:
            channels: List of channels to output on
            waveform: 2d array of voltages to output, with each column giving the output values at a given time
                (the timing given by the sample rate of the channel) with the channels going from top to bottom in
                the column in the order given in channels
            clk_source: the PFI channel of the hardware clock to lock the output to, or "" to use the default
                internal clock
        """
        if 'analog_output' not in list(self.settings.keys()):
            raise ValueError('This DAQ does not support analog output')
        for c in channels:
            if not c in list(self.settings['analog_output'].keys()):
                raise KeyError('This is not a valid analog output channel')

        task = {
            'task_handle': None,
            'sample_num': None,
            'sample_rate': None,
            'num_samples_per_channel': None,
            'timeout': None
        }

        task_name = self._add_to_tasklist('ao', task)

        task['sample_rate'] = float(
            self.settings['analog_output'][channels[0]]['sample_rate'])  # float prevents truncation in division

        for c in channels:
            if not self.settings['analog_output'][c]['sample_rate'] == task['sample_rate']:
                raise ValueError('All sample rates must be the same')
        channel_list = ''.encode('ascii')
        for c in channels:
            channel_list += (self.settings['device'] + '/' + c + ',').encode('ascii')
        # this line below has been modified to fix a bug where channel_list ended up as a string
        # channel_list = channel_list[:-1]
        channel_list = channel_list[:-1].split(b",")
        self.running = True
        # special case 1D waveform since length(waveform[0]) is undefined
        if (len(np.shape(waveform)) == 2):
            num_channels = len(waveform)
            task['sample_num'] = len(waveform[0])
        else:
            task['sample_num'] = len(waveform)
            num_channels = 1

        # special case 1D waveform since length(waveform[0]) is undefined
        # converts python array to numpy array
        if len(np.shape(waveform)) == 2:
            data = np.zeros((num_channels, task['sample_num']), dtype=np.float64)
            for i in range(num_channels):
                for j in range(task['sample_num']):
                    data[i, j] = waveform[i, j]
        else:
            data = np.zeros((task['sample_num']), dtype=np.float64)
            for i in range(task['sample_num']):
                data[i] = waveform[i]

        if not (clk_source == ""):
            clk_source = self.tasklist[clk_source]['counter_out_PFI_str']

        # with ni.Task() as task_ao:
        task_ao = ni.Task()
        task['task_handle'] = task_ao
        for chan in channel_list:
            task_ao.ao_channels.add_ao_voltage_chan(chan, min_val=-10.0, max_val=10.0)
        task_ao.timing.cfg_samp_clk_timing(task['sample_rate'], source=clk_source,
                                           samps_per_chan=task['sample_num'])
        if len(np.shape(waveform)) == 2:
            writer = AnalogMultiChannelWriter(task_ao.in_stream)
        else:
            writer = AnalogSingleChannelWriter(task_ao.in_stream)
        samples_to_write = task['sample_num']
        samples_written = writer.write_many_sample(data)
        assert samples_written == samples_to_write

        return task_name

    def setup_AI(self, channels, num_samples_to_acquire, continuous=False, clk_source=""):
        """
        Initializes a single or multiple analog input channels to read on
        Args:
            channels: List of Channels to read input, eg ['ai0','ai1'] or a string 'ai0'
            num_samples_to_acquire: number of samples to acquire on that channel
        """

        task = {
            'task_handle': None,
            'sample_num': None,
            'sample_rate': None,
            'num_samples_per_channel': None,
            'num_channels': None,
            'timeout': None
        }

        task_name = self._add_to_tasklist('ai', task)
        num_channels = 0
        channel_list = ''
        if type(channels) == str:
            channels = [channels]
        elif type(channels) == list:
            pass
        else:
            RuntimeError("AI channel must be of type list of strings or string")

        for chan in channels:
            assert type(chan) == str
            channel_list += ('/' + self.settings['device'] + '/' + chan + ',')
            num_channels += 1
        channel_list = channel_list.encode('ascii')
        print(channel_list)
        if 'analog_input' not in list(self.settings.keys()):
            raise ValueError('This DAQ does not support analog input')

        task['sample_num'] = num_samples_to_acquire
        task['num_channels'] = num_channels
        #data = np.zeros((num_channels,task['sample_num']))
        # now, on with the program

        if not (clk_source == ""):
            clk_source = self.tasklist[clk_source]['counter_out_PFI_str']
        # with ni.Task() as task_ai:
        task_ai = ni.Task()
        task['task_handle'] = task_ai
        task_ai.ai_channels.add_ai_voltage_chan(channel_list,min_val=-10.0, max_val=10.0)
        # # this line below has been modified to fix a bug where channel_list ended up as a string
        # # channel_list = channel_list[:-1]
        # channel_list = channel_list[:-1].split(b",")
        # for chan in channel_list:
        #     # TODO: I think it would be fine to just pass the channel list as a string
        #     # in fact my scratch_19 file shows that this works fine.
        #     task_ai.ai_channels.add_ai_voltage_chan(chan, min_val=-10.0, max_val=10.0)
        sample_rate = self.settings['analog_input'][channels[0]]['sample_rate']
        if not continuous:
            task_ai.timing.cfg_samp_clk_timing(sample_rate, source=clk_source, samps_per_chan=task['sample_num'])

        else:
            task_ai.timing.cfg_samp_clk_timing(sample_rate, source=clk_source, sample_mode=AcquisitionType.CONTINUOUS,
                                               samps_per_chan=task['sample_num'])

        return task_name

    def setup_DO(self, channels):
        """
        Initializes a arbitrary number of digital output channels to output an arbitrary waveform
        Args:
            channels: List of channels to output, check in self.settings['digital_output'] for available channels
            waveform: 2d array of boolean values to output, with each column giving the output values at a given time
                (the timing given by the sample rate of the channel) with the channels going from top to bottom in
                the column in the order given in channels
            clk_source: the PFI channel of the hardware clock to lock the output to, or "" to use the default
                internal clock

        sets up creates self.DO_taskHandle
        """

        task = {
            'task_handle': None,
            'sample_num': None,
            'sample_rate': None,
            'num_samples_per_channel': None,
            'timeout': None
        }

        task_name = self._add_to_tasklist('DO', task)

        if 'digital_output' not in list(self.settings.keys()):
            raise ValueError('This DAQ does not support digital output')
        for c in channels:
            if not c in list(self.settings['digital_output'].keys()):
                raise KeyError('This is not a valid digital output channel')
        task['sample_rate'] = float(
            self.settings['digital_output'][channels[0]]['sample_rate'])  # float prevents truncation in division
        for c in channels:
            if not self.settings['digital_output'][c]['sample_rate'] == task['sample_rate']:
                raise ValueError('All sample rates must be the same')

        lines_list = ''
        for c in channels:
            lines_list += self.settings['device'] + '/port0/line' + str(
                self.settings['digital_output'][c]['channel']) + ','
        lines_list = lines_list[:-1]  # remove the last comma

        self.running = True

        # with ni.Task() as task:
        task['task_handle'] = ni.Task()
        task['task_handle'].do_channels.add_do_chan(lines_list, line_grouping=LineGrouping.CHAN_PER_LINE)

        return task_name

    def DO_write(self, task_name, output_values):
        task = self.tasklist[task_name]
        sample_num = np.array(output_values).shape[-1]

        writer = DigitalMultiChannelWriter(task['task_handle'].out_stream, auto_start=True)
        samples_written = writer.write_many_sample_port_byte(output_values)
        assert samples_written == sample_num

    def read_AI(self, task_name):
        """
        Reads the AI voltage values from the buffer
        Returns: array of ctypes.c_long with the voltage data
        """
        task = self.tasklist[task_name]
        # data = (float64 * task['sample_num'])()

        sample_num = task['sample_num']
        num_channels = task['num_channels']
        data = np.zeros((num_channels,task['sample_num']))
        # samples_per_channel_read = int32()
        #reader = AnalogSingleChannelReader(task['task_handle'].in_stream)
        reader = AnalogMultiChannelReader(task['task_handle'].in_stream)
        reader.verify_array_shape = True
        samples_read = reader.read_many_sample(data, number_of_samples_per_channel=sample_num)
        assert samples_read == sample_num
        # self._check_error(self.nidaq.DAQmxReadAnalogF64(task['task_handle'], task['sample_num'], float64(10.0),
        #                                                 DAQmx_Val_GroupByChannel, ctypes.byref(data),
        #                                                 # data.ctypes.data, ER 20180626
        #                                                 task['sample_num'], ctypes.byref(samples_per_channel_read),
        #                                                 None))

        return data, samples_read


    # run the task specified by task_name
    # todo: GD - should this be threaded?  is this actually blocking? Is the threading actually doing anything? see nidaq cookbook
    def run(self, task_name):
        """
        Runs the task or list of tasks specified in taskname. What 'running' does depends on the type of task that was
        set up, but generally either begins output from a buffer or input to a buffer.

        Args:
            task_name: string identifying task

        """
        # run list of tasks
        if type(task_name) == list:
            for name in task_name:
                task = self.tasklist[name]
                # self._check_error(self.nidaq.DAQmxStartTask(task['task_handle']))
                task['task_handle'].start()
        # run single task
        else:
            task = self.tasklist[task_name]
            # self._check_error(self.nidaq.DAQmxStartTask(task['task_handle']))
            task['task_handle'].start()

    def wait_to_finish(self, task_name):
        """
        Blocks until the task specified by task_name is completed

        Args:
            task_name: string identifying task

        """
        task = self.tasklist[task_name]
        task["timeout"] = float(task['sample_num']/task['sample_rate']*10 + 1)
        t1 = time.perf_counter()
        try:
            while not task['task_handle'].is_task_done():
                time.sleep(0.1)
                t2 = time.perf_counter()
                if (t2 - t1) > task["timeout"]:
                    raise TimeoutError("Task {} has exceeded max. timeout {}".format(task_name,task["timeout"]))

        except TimeoutError as e:
            print("Timeout Error {0}".format(e))
            self.stop(task_name)
            raise
        # self._check_error(self.nidaq.DAQmxWaitUntilTaskDone(task['task_handle'],
        #                                                     float64(task['sample_num'] / task['sample_rate'] * 4 + 1)))

    def read(self, task_name):
        if 'ctr' in task_name:
            return (self.read_counter(task_name))
        elif 'ai' in task_name:
            return (self.read_AI(task_name))
        else:
            raise ValueError('This task does not allow reads.')

    def write(self, task_name, output_values):
        if 'DO' in task_name:
            self.DO_write(task_name, output_values)
        else:
            raise ValueError('This task does not allow writes.')

    def stop(self, task_name):
        # remove task to be cleared from tasklist
        task = self.tasklist.pop(task_name)

        # special case counters, which create two tasks that need to be cleared
        if 'task_handle_ctr' in list(task.keys()):
            task_ctr = task['task_handle_ctr']
            task_ctr.stop()
            task_clk = task['task_handle']
            task_clk.stop()
            task_clk.close()
            task_ctr.close()
            # self.nidaq.DAQmxStopTask(task['task_handle_ctr'])
            # self.nidaq.DAQmxClearTask(task['task_handle_ctr'])
        else:
            task_h = task['task_handle']
            task_h.stop()
            task_h.close()
        # self.nidaq.DAQmxStopTask(task['task_handle'])
        # self.nidaq.DAQmxClearTask(task['task_handle'])

    def get_analog_voltages(self, channel_list):
        """
        Args:
            channel_list: list (length N) of channels from which to read the voltage, channels are given as strings, e.g. ['ao1', 'ai3']

        Returns:
            list of voltages (length N)

        """
        daq_channels_str = ''
        for channel in channel_list:
            if channel in self.settings['analog_output']:
                daq_channels_str += self.settings['device'] + '/_' + channel + '_vs_aognd, '
            elif (channel in self.settings['analog_input']):
                daq_channels_str += self.settings['device'] + '/' + channel + ', '
        daq_channels_str = daq_channels_str[:-2].encode('ascii')  # strip final comma period
        # data = (float64 * len(channel_list))()
        num_channels = len(channel_list)
        samples_to_read = 1
        data = np.full((num_channels, samples_to_read), np.inf)
        # get_voltage_taskHandle = TaskHandle(0)
        with ni.Task() as task_ai:
            task_ai.ai_channels.add_ai_voltage_chan(daq_channels_str, min_val=-10.0, max_val=10.0)
            # self._check_error(self.nidaq.DAQmxCreateTask("", ctypes.byref(get_voltage_taskHandle)))
            reader = AnalogMultiChannelReader(task_ai.in_stream)
            samples_read = reader.read_many_sample(data, samples_to_read)
            task_ai.start()
            assert samples_read == samples_to_read
            task_ai.stop()
        # self._check_error(self.nidaq.DAQmxCreateAIVoltageChan(get_voltage_taskHandle, daq_channels_str, "",
        #                                                       DAQmx_Val_Cfg_Default,
        #                                                       float64(-10.0), float64(10.0),
        #                                                       DAQmx_Val_Volts, None))
        # self._check_error(self.nidaq.DAQmxReadAnalogF64(get_voltage_taskHandle, int32(sample_num), float64(10.0),
        #                                                 DAQmx_Val_GroupByChannel, ctypes.byref(data),
        #                                                 int32(sample_num * len(channel_list)), None, None))
        # self._check_error(self.nidaq.DAQmxClearTask(get_voltage_taskHandle))

        for i, channel in enumerate(channel_list):
            # if channel in self.settings['analog_output']:
            data[i] += self.settings['ao_read_offset']

        return [1. * d for d in data]  # return and convert from ctype to python float

    def set_analog_voltages(self, output_dict):
        """

        Args:
            output_dict: dictionary with names of channels as key and voltage as value, e.g. {'ao0': 0.1} or {'0':0.1} for setting channel 0 to 0.1

        Returns: nothing

        """
        # daq API only accepts either one point and one channel or multiple points and multiple channels

        #
        # # make sure the key has the right format, e.g. ao0
        # channels = ['ao'+k.replace('ao','') for k in output_dict.keys()]

        channels = []
        voltages = []
        for k, v in output_dict.items():
            channels.append('ao' + k.replace('ao', ''))  # make sure the key has the right format, e.g. ao0
            voltages.append(v)

        voltages = np.array([voltages]).T
        voltages = (np.repeat(voltages, 2, axis=1))
        # pt = np.transpose(np.column_stack((pt[0],pt[1])))
        # pt = (np.repeat(pt, 2, axis=1))

        task_name = self.setup_AO(channels, voltages)
        self.run(task_name)
        self.wait_to_finish(task_name)
        self.stop(task_name)

    def set_digital_output(self, output_dict):
        """

        Args:
            output_dict: dictionary with names of channels as key and voltage as value, e.g. {'do0': True} or {'0':True} for setting channel 0 to True

        Returns: nothing

        """

        channels = []
        values = []
        for k, v in output_dict.items():
            channels.append('DO' + k.replace('DO', ''))  # make sure the key has the right format, e.g. ao0
            values.append(v)

        print(('channels', channels))
        print(('voltages', values))

        task_name = self.setup_DO(channels)

        self.run(task_name)

        self.DO_write(task_name, values)

        self.stop(task_name)

    def _check_error(self, err):
        """
        Error Checking Routine for DAQmx functions. Pass in the returned values form DAQmx functions (the errors) to get
        an error description. Raises a runtime error
        Args:
            err: 32-it integer error from an NI-DAQmx function

        Returns: a verbose description of the error taken from the nidaq dll

        """
        pass
        # if err < 0:
        #     buffer_size = 1000
        #     buffer = ctypes.create_string_buffer(('\000' * buffer_size).encode('ascii'))
        #     self.nidaq.DAQmxGetExtendedErrorInfo(ctypes.byref(buffer), buffer_size)
        #     # raise RuntimeError('nidaq call failed with error %d: %s' % (err, repr(buffer.value)))
        #     raise RuntimeError('nidaq call failed with error %d: %s' % (err, buffer.value))
        # if err > 0:
        #     buffer_size = 1000
        #     buffer = ctypes.create_string_buffer(('\000' * buffer_size).encode('ascii'))
        #     self.nidaq.DAQmxGetErrorString(err, ctypes.byref(buffer), buffer_size)
        #     # raise RuntimeError('nidaq generated warning %d: %s' % (err, repr(buffer.value)))
        #     print('nidaq generated warning %d: %s' % (err, repr(buffer.value)))

    @classmethod
    def get_connected_devices(cls):
        """
        Checks which devices are present in the system
        Returns: A list of device names, that are currently connected

        """

        device_list = []
        local_system = ni.system.System.local()
        for device in local_system.devices:
            device_list.append("Device Name : {0}, Product Category: {1}, Product Type: {2}".format(device.name,
                                                                                                    device.product_category,
                                                                                                    device.product_type))
        return device_list


def int_to_voltage(integer):
    """
    convert integer value to voltage
    Args:
        integer:

    Returns:

    """
    return (10 * integer) / 32767.


class PXI6733(NIDAQ):
    """This class implements the PXIe6733 DAQ, which includes 8 analog outputs, 8 DIO channels, 2 counters, 1 frequency scaler
    and inherits basic input/output functionality from NIDAQ. A subset of these channels are accessible here, but more
    can added up to the above limits
    """
    _DEFAULT_SETTINGS = Parameter([
        Parameter('device', "PXI1Slot8", ["PXI1Slot8"], "Name of DAQ device"),
        Parameter('override_buffer_size', -1, int, 'Buffer size for manual override (unused if -1)'),
        Parameter('ao_read_offset', .005, float, 'Empirically determined offset for reading ao voltages internally'),
        Parameter('external_daq', "Dev1", ["Dev1", "Dev2"], "Name of external DAQ device for clock"),
        Parameter('analog_output',
                  [
                      Parameter('ao0',
                                [
                                    Parameter('channel', 0, [0, 1, 2, 3], 'output channel'),
                                    Parameter('sample_rate', 1000.0, float, 'output sample rate (Hz)'),
                                    Parameter('min_voltage', -10.0, float, 'minimum output voltage (V)'),
                                    Parameter('max_voltage', 10.0, float, 'maximum output voltage (V)')
                                ]
                                ),
                      Parameter('ao1',
                                [
                                    Parameter('channel', 1, [0, 1, 2, 3], 'output channel'),
                                    Parameter('sample_rate', 1000.0, float, 'output sample rate (Hz)'),
                                    Parameter('min_voltage', -10.0, float, 'minimum output voltage (V)'),
                                    Parameter('max_voltage', 10.0, float, 'maximum output voltage (V)')
                                ]
                                ),
                      Parameter('ao2',
                                [
                                    Parameter('channel', 2, [0, 1, 2, 3], 'output channel'),
                                    Parameter('sample_rate', 1000.0, float, 'output sample rate (Hz)'),
                                    Parameter('min_voltage', -10.0, float, 'minimum output voltage (V)'),
                                    Parameter('max_voltage', 10.0, float, 'maximum output voltage (V)')
                                ]
                                ),
                      Parameter('ao3',
                                [
                                    Parameter('channel', 3, [0, 1, 2, 3], 'output channel'),
                                    Parameter('sample_rate', 1000.0, float, 'output sample rate (Hz)'),
                                    Parameter('min_voltage', -10.0, float, 'minimum output voltage (V)'),
                                    Parameter('max_voltage', 10.0, float, 'maximum output voltage (V)')
                                ]
                                )
                  ]
                  ),
        Parameter('digital_input',
                  [
                      Parameter('ctr0',
                                [
                                    Parameter('input_channel', 0, list(range(0, 32)),
                                              'channel for counter signal input'),
                                    Parameter('counter_PFI_channel', 8, list(range(0, 32)),
                                              'PFI for counter channel input'),
                                    Parameter('gate_PFI_channel', 9, list(range(0, 32)),
                                              'PFI for counter channel input'),
                                    # changed the PFI for clock channel out to PFI5, which should be ok according to NIMAX routing diagram
                                    # testing the clock out with my scratch_2 file and the NIMAX, I see a waveform
                                    Parameter('clock_PFI_channel', 5, list(range(0, 32)),
                                              'PFI for clock channel output'),
                                    Parameter('clock_counter_channel', 1, [0, 1], 'channel for clock output'),
                                    Parameter('sample_rate', 1000.0, float, 'input sample rate (Hz)')
                                ]
                                ),
                      Parameter('ctr1',
                                [
                                    Parameter('input_channel', 1, list(range(0, 32)),
                                              'channel for counter signal input'),
                                    Parameter('counter_PFI_channel', 3, list(range(0, 32)),
                                              'PFI for counter channel input'),
                                    Parameter('gate_PFI_channel', 4, list(range(0, 32)),
                                              'PFI for counter channel input'),
                                    # changed the PFI for clock channel out to PFI6, which should be ok according to NIMAX routing diagram
                                    Parameter('clock_PFI_channel', 12, list(range(0, 32)),
                                              'PFI for clock channel output'),
                                    Parameter('clock_counter_channel', 0, [0, 1], 'channel for clock output'),
                                    Parameter('sample_rate', 1000.0, float, 'input sample rate (Hz)')
                                ]
                                )
                  ]
                  ),
        Parameter('external_daq_clock',
                  [
                      Parameter('ctr0',
                                [
                                    Parameter('channel', 0, list(range(0, 8)), 'channel'),
                                    Parameter('sample_rate', 1000.0, float, 'output sample rate (Hz)'),
                                    Parameter('clock_PFI_channel', 0, list(range(0, 2)), "PFI for external clock input")
                                ]
                                )

                  ]
                  ),
        Parameter('digital_output',
                  [
                      Parameter('do0',
                                [
                                    Parameter('channel', 0, list(range(0, 8)), 'channel'),
                                    # Parameter('value', False, bool, 'value')
                                    Parameter('sample_rate', 1000.0, float, 'output sample rate (Hz)')
                                    # Parameter('min_voltage', -10.0, float, 'minimum output voltage (V)'),
                                    # Parameter('max_voltage', 10.0, float, 'maximum output voltage (V)')
                                ]
                                ),
                      Parameter('do7',
                                [
                                    Parameter('channel', 7, list(range(0, 8)), 'channel'),
                                    # Parameter('value', False, bool, 'value')
                                    Parameter('sample_rate', 1000.0, float, 'output sample rate (Hz)')
                                    # Parameter('min_voltage', -10.0, float, 'minimum output voltage (V)'),
                                    # Parameter('max_voltage', 10.0, float, 'maximum output voltage (V)')
                                ]
                                )
                  ]
                  )

    ])

    def setup_counter(self, channel, sample_num, continuous_acquisition=False, use_external_clock=True):
        """
        We must reimplement the setup_counter function due to board limitations. Initializes a hardware-timed digital counter, bound to a hardware clock.
        we add a parameter to allow us to supply an external clock channel from another device, and require that
        the other board must be connected to PFI0 on this board.
        Args:
            channel: digital channel to initialize for read in
            sample_num: number of samples to read in for finite operation, or number of samples between
                       reads for continuous operation (to set buffer size)
            continuous_acquisition: run in continuous acquisition mode (ex for a continuous counter) or
                                    finite acquisition mode (ex for a scan, where the number of samples needed
                            is known a priori)
            use_external_clock: decide if an external clock may be supplied

        Returns: source of clock that this method sets up, which can be given to another function to synch that
        input or output to the same clock

        """

        # Note that for this counter, we have two tasks. The normal 'task_handle' corresponds to the clock, and this
        # is the task which is started when run is called. The second 'task_handle_ctr' corresponds to the counter,
        # and this waits for the clock and will be started simultaneously.
        task = {
            'task_handle': None,
            'task_handle_ctr': None,
            'counter_out_PFI_str': None,
            'sample_num': None,
            'sample_rate': None,
            'num_samples_per_channel': None,
            'timeout': None
        }

        task_name = self._add_to_tasklist('ctr', task)

        if 'digital_input' not in list(self.settings.keys()):
            raise ValueError('This DAQ does not support digital input')
        if not channel in list(self.settings['digital_input'].keys()):
            raise KeyError('This is not a valid digital input channel')

        channel_settings = self.settings['digital_input'][channel]
        ext_clock_channel_settings = self.settings['external_daq_clock']['ctr0']
        ext_clock_channel = ext_clock_channel_settings['channel']
        ext_clock_pfi_channel = ext_clock_channel_settings['clock_PFI_channel']
        # external_daq_channel_settings = self.settings['external_daq'][channel]
        self.running = True
        task['sample_num'] = sample_num
        task['sample_rate'] = float(channel_settings['sample_rate'])
        if not continuous_acquisition:
            task['num_samples_per_channel'] = task['sample_num']
        else:
            task['num_samples_per_channel'] = -1
        # set the timeout to be 5 times the amount of time required
        task['timeout'] = float(5 * (1 / task['sample_rate']) * task['sample_num'])
        input_channel_str = (self.settings['device'] + '/' + channel).encode('ascii')

        """
        Due to the board limitations, when finite pulse train generation
        are requested, both ctr0 and ctr1 get occupied as one is used to gate the other.
        So, we used the internal output of the clock counter as timing source for the input counter, but must use CONTINUOUS 
        generation mode. The other option is to use the external clock using PFI0
        """

        if use_external_clock:
            # we read in the external daq board clock
            counter_out_str = (self.settings['external_daq'] + "/ctr" + str(ext_clock_channel)).encode('ascii')
            task['counter_out_PFI_str'] = ("/" + self.settings['device'] + "/PFI" + str(ext_clock_pfi_channel)).encode(
                'ascii')
        else:
            # we use the internal output of the other counter
            counter_out_str = (
                        self.settings['device'] + '/ctr' + str(channel_settings['clock_counter_channel'])).encode(
                'ascii')
            task['counter_out_PFI_str'] = ("/" +
                                           self.settings['device'] + '/Ctr' + str(
                        channel_settings['clock_counter_channel']) + "InternalOutput").encode(
                'ascii')
            RuntimeWarning("You are requesting a hardware generated clock in finite sampling mode.")
            RuntimeWarning(
                "This board uses up both counters in finite sampling mode, so you need to supply external clock")
            RuntimeWarning(
                "Switching the internal clock to continuous mode, samples beyond those requested will be ignored...")

        # with ni.Task() as clock_task, ni.Task() as counter_task:
        clock_task = ni.Task()
        counter_task = ni.Task()
        task['task_handle'] = clock_task
        task['task_handle_ctr'] = counter_task
        clock_task.co_channels.add_co_pulse_chan_freq(counter_out_str, freq=float(task['sample_rate']),
                                                      duty_cycle=0.5)

        counter_task.ci_channels.add_ci_count_edges_chan(input_channel_str)

        # set up clock
        if use_external_clock:
            clock_task.timing.cfg_implicit_timing(samps_per_chan=int(task['sample_num']))
        else:
            # if we want to use the 2nd counter, we must choose continuous freq generation
            clock_task.timing.cfg_implicit_timing(sample_mode=AcquisitionType.CONTINUOUS)
        # set up counter using clock as reference
        if not continuous_acquisition:

            counter_task.timing.cfg_samp_clk_timing(float(task['sample_rate']), source=task['counter_out_PFI_str'],
                                                    samps_per_chan=task['sample_num'])
        else:

            counter_task.timing.cfg_samp_clk_timing(float(task['sample_rate']), source=task['counter_out_PFI_str'],
                                                    sample_mode=AcquisitionType.CONTINUOUS)

        # self._check_error(self.nidaq.DAQmxStartTask(task['task_handle_ctr']))
        counter_task.start()
        # clock_task.start()

        return task_name

    def setup_AO(self, channels, waveform, clk_source=""):
        """
        Re-implement setup_AO due to board limitations for the clock.
        Initializes a arbitrary number of analog output channels to output an arbitrary waveform
        Args:
            channels: List of channels to output on
            waveform: 2d array of voltages to output, with each column giving the output values at a given time
                (the timing given by the sample rate of the channel) with the channels going from top to bottom in
                the column in the order given in channels
            clk_source: the task name of the clock, if none it will use the default on-board clock.
            for 1d or 2d AO scans with counter read, this will be the name of the counter task , e.g. ctr000.

        """
        if 'analog_output' not in list(self.settings.keys()):
            raise ValueError('This DAQ does not support analog output')
        for c in channels:
            if not c in list(self.settings['analog_output'].keys()):
                raise KeyError('This is not a valid analog output channel')

        task = {
            'task_handle': None,
            'sample_num': None,
            'sample_rate': None,
            'num_samples_per_channel': None,
            'timeout': None
        }

        task_name = self._add_to_tasklist('ao', task)

        task['sample_rate'] = float(
            self.settings['analog_output'][channels[0]]['sample_rate'])  # float prevents truncation in division

        for c in channels:
            if not self.settings['analog_output'][c]['sample_rate'] == task['sample_rate']:
                raise ValueError('All sample rates must be the same')
        channel_list = ''.encode('ascii')
        for c in channels:
            channel_list += (self.settings['device'] + '/' + c + ',').encode('ascii')
        # this line below has been modified to fix a bug where channel_list ended up as a string
        # channel_list = channel_list[:-1]
        channel_list = channel_list[:-1].split(b",")
        self.running = True
        # special case 1D waveform since length(waveform[0]) is undefined
        if (len(np.shape(waveform)) == 2):
            num_channels = len(waveform)
            # for the PXI6733 the AO buffer has to be an even number
            if len(waveform[0]) % 2 == 0:
                task['sample_num'] = len(waveform[0])
            else:
                task['sample_num'] = len(waveform[0]) - 1
                RuntimeWarning("The waveform must have an even number of points, dropping the last point")
        else:
            task['sample_num'] = len(waveform)
            num_channels = 1
            # for the PXI6733 the AO buffer has to be an even number
            if len(waveform) % 2 == 0:
                task['sample_num'] = len(waveform)
            else:
                task['sample_num'] = len(waveform) - 1
                RuntimeWarning("The waveform must have an even number of points, dropping the last point")

        # special case 1D waveform since length(waveform[0]) is undefined
        # converts python array to numpy array
        if len(np.shape(waveform)) == 2:
            data = np.zeros((num_channels, task['sample_num']), dtype=np.float64)
            for i in range(num_channels):
                for j in range(task['sample_num']):
                    data[i, j] = waveform[i, j]
        else:
            data = np.zeros((task['sample_num']), dtype=np.float64)
            for i in range(task['sample_num']):
                data[i] = waveform[i]



        if not (clk_source == ""):
            clk_source = self.tasklist[clk_source]['counter_out_PFI_str']

        # with ni.Task() as task_ao:
        task_ao = ni.Task()
        task['task_handle'] = task_ao
        for chan in channel_list:
            task_ao.ao_channels.add_ao_voltage_chan(chan, min_val=-10.0, max_val=10.0)
            # set up clock

        task_ao.timing.cfg_samp_clk_timing(float(task['sample_rate']), source=clk_source,
                                                    samps_per_chan=task['sample_num'])

        # task_ao.timing.cfg_samp_clk_timing(task['sample_rate'], source=clk_source,
        #                                    samps_per_chan=task['sample_num'])
        if len(np.shape(waveform)) == 2:
            writer = AnalogMultiChannelWriter(task_ao.in_stream)
        else:
            writer = AnalogSingleChannelWriter(task_ao.in_stream)
        samples_to_write = task['sample_num']
        samples_written = writer.write_many_sample(data)
        assert samples_written == samples_to_write

        return task_name


class NI6281(NIDAQ):  # yet to be implemented
    """This class implements the PCI6281 DAQ, which includes 16 analog inputs (8 differential), 24 DIO channels, 2 analog outs, 2 counter/timers
        and inherits basic input/output functionality from NIDAQ. A subset of these channels are accessible here, but more can added up to the above limits
        """
    _DEFAULT_SETTINGS = Parameter([
        Parameter('device', "Dev1", ["Dev1", "PXI1Slot8"], "Name of DAQ device"),
        Parameter('override_buffer_size', -1, int, 'Buffer size for manual override (unused if -1)'),
        Parameter('ao_read_offset', .005, float, 'Empirically determined offset for reading ao voltages internally'),
        Parameter('analog_input',
                  [
                      Parameter('ai0',
                                [
                                    Parameter('channel', 0, [0, 1, 2, 3], 'output channel'),
                                    Parameter('sample_rate', 1000.0, float, 'output sample rate (Hz)'),
                                    Parameter('min_voltage', -10.0, float, 'minimum output voltage (V)'),
                                    Parameter('max_voltage', 10.0, float, 'maximum output voltage (V)')
                                ]
                                ),
                      Parameter('ai1',
                                [
                                    Parameter('channel', 1, [0, 1, 2, 3], 'output channel'),
                                    Parameter('sample_rate', 1000.0, float, 'output sample rate (Hz)'),
                                    Parameter('min_voltage', -10.0, float, 'minimum output voltage (V)'),
                                    Parameter('max_voltage', 10.0, float, 'maximum output voltage (V)')
                                ]
                                )
                  ]
                  ),
        Parameter('analog_output',
                  [
                      Parameter('ao0',
                                [
                                    Parameter('channel', 0, [0, 1, 2, 3], 'output channel'),
                                    Parameter('sample_rate', 1000.0, float, 'output sample rate (Hz)'),
                                    Parameter('min_voltage', -10.0, float, 'minimum output voltage (V)'),
                                    Parameter('max_voltage', 10.0, float, 'maximum output voltage (V)')
                                ]
                                ),
                      Parameter('ao1',
                                [
                                    Parameter('channel', 1, [0, 1, 2, 3], 'output channel'),
                                    Parameter('sample_rate', 1000.0, float, 'output sample rate (Hz)'),
                                    Parameter('min_voltage', -10.0, float, 'minimum output voltage (V)'),
                                    Parameter('max_voltage', 10.0, float, 'maximum output voltage (V)')
                                ]
                                )
                  ]
                  ),
        Parameter('digital_input',
                  [
                      Parameter('ctr0',
                                [
                                    Parameter('input_channel', 0, list(range(0, 32)),
                                              'channel for counter signal input'),
                                    Parameter('counter_PFI_channel', 8, list(range(0, 32)),
                                              'PFI for counter channel input'),
                                    Parameter('gate_PFI_channel', 9, list(range(0, 32)),
                                              'PFI for counter channel input'),
                                    # changed the PFI for clock channel out to PFI5, which should be ok according to NIMAX routing diagram
                                    # testing the clock out with my scratch_2 file and the NIMAX, I see a waveform
                                    Parameter('clock_PFI_channel', 13, list(range(0, 32)),
                                              'PFI for clock channel output'),
                                    Parameter('clock_counter_channel', 1, [0, 1], 'channel for clock output'),
                                    Parameter('sample_rate', 1000.0, float, 'input sample rate (Hz)')
                                ]
                                ),
                      Parameter('ctr1',
                                [
                                    Parameter('input_channel', 1, list(range(0, 32)),
                                              'channel for counter signal input'),
                                    Parameter('counter_PFI_channel', 3, list(range(0, 32)),
                                              'PFI for counter channel input'),
                                    Parameter('gate_PFI_channel', 4, list(range(0, 32)),
                                              'PFI for counter channel input'),
                                    # changed the PFI for clock channel out to PFI6, which should be ok according to NIMAX routing diagram
                                    Parameter('clock_PFI_channel', 12, list(range(0, 32)),
                                              'PFI for clock channel output'),
                                    Parameter('clock_counter_channel', 0, [0, 1], 'channel for clock output'),
                                    Parameter('sample_rate', 1000.0, float, 'input sample rate (Hz)')
                                ]
                                )
                  ]
                  ),


    ])
    def setup_counter(self, channel, sample_num, continuous_acquisition=False):
        """
        We must reimplement the setup_counter function due to board limitations. Initializes a hardware-timed digital
        counter, bound to a hardware clock. The clock must be run in CONTINUOUS mode.

        Args:
            channel: digital channel to initialize for read in
            sample_num: number of samples to read in for finite operation, or number of samples between
                       reads for continuous operation (to set buffer size)
            continuous_acquisition: run in continuous acquisition mode (ex for a continuous counter) or
                                    finite acquisition mode (ex for a scan, where the number of samples needed
                            is known a priori)


        Returns: source of clock that this method sets up, which can be given to another function to synch that
        input or output to the same clock

        """

        # Note that for this counter, we have two tasks. The normal 'task_handle' corresponds to the clock, and this
        # is the task which is started when run is called. The second 'task_handle_ctr' corresponds to the counter,
        # and this waits for the clock and will be started simultaneously.
        task = {
            'task_handle': None,
            'task_handle_ctr': None,
            'counter_out_PFI_str': None,
            'sample_num': None,
            'sample_rate': None,
            'num_samples_per_channel': None,
            'timeout': None
        }

        task_name = self._add_to_tasklist('ctr', task)

        if 'digital_input' not in list(self.settings.keys()):
            raise ValueError('This DAQ does not support digital input')
        if not channel in list(self.settings['digital_input'].keys()):
            raise KeyError('This is not a valid digital input channel')

        channel_settings = self.settings['digital_input'][channel]

        self.running = True
        task['sample_num'] = sample_num
        task['sample_rate'] = float(channel_settings['sample_rate'])
        if not continuous_acquisition:
            task['num_samples_per_channel'] = task['sample_num']
        else:
            task['num_samples_per_channel'] = -1
        # set the timeout to be 5 times the amount of time required
        task['timeout'] = float(5 * (1 / task['sample_rate']) * task['sample_num'])
        input_channel_str = ('/' + self.settings['device'] + '/' + channel).encode('ascii')
        task['counter_out_PFI_str'] = ('/' + self.settings['device'] + '/PFI' + str(
            channel_settings['clock_PFI_channel'])).encode(
            'ascii')  # initial / required only here, see NIDAQ documentation
        counter_out_str = (
                    '/' + self.settings['device'] + '/ctr' + str(channel_settings['clock_counter_channel'])).encode(
            'ascii')


        # with ni.Task() as clock_task, ni.Task() as counter_task:
        clock_task = ni.Task()
        counter_task = ni.Task()
        task['task_handle'] = clock_task
        task['task_handle_ctr'] = counter_task
        clock_task.co_channels.add_co_pulse_chan_freq(counter_out_str, freq=float(task['sample_rate']),
                                                      duty_cycle=0.5)

        counter_task.ci_channels.add_ci_count_edges_chan(input_channel_str)

        # set up clock
        """
        Due to the board limitations, the clock must always be run in CONTINUOUS mode
        """
        clock_task.timing.cfg_implicit_timing(sample_mode=AcquisitionType.CONTINUOUS)
        # set up counter using clock as reference
        if not continuous_acquisition:

            counter_task.timing.cfg_samp_clk_timing(float(task['sample_rate']), source=task['counter_out_PFI_str'],
                                                    samps_per_chan=task['sample_num'])
        else:

            counter_task.timing.cfg_samp_clk_timing(float(task['sample_rate']), source=task['counter_out_PFI_str'],
                                                    sample_mode=AcquisitionType.CONTINUOUS)

        # self._check_error(self.nidaq.DAQmxStartTask(task['task_handle_ctr']))
        counter_task.start()
        # clock_task.start()

        return task_name
    
class PCI6229(NIDAQ):
    """This class implements the PCI6229 DAQ, which includes 32 analog input (16 differential) channels, 4 analog outputs, 
    48 DIO channels, 2 counters, 1 frequency generator, and inherits basic input/output functionality from 
    NIDAQ. A subset of these channels are accessible here, but more can be added up to the above limits.
    """
    _DEFAULT_SETTINGS = Parameter([
        Parameter('device', "Dev1", ["Dev1"], "Name of DAQ device"),
        Parameter('override_buffer_size', -1, int, 'Buffer size for manual override (unused if -1)'),
        Parameter('ao_read_offset', 0.005, float, 'Empirically determined offset for reading ao voltages internally'),
        Parameter('external_daq', "Dev2", ["Dev2"], "Name of external daq device for clock"),
        Parameter('analog_input', 
                  [
                      Parameter('ai0', 
                                [
                                    Parameter('channel', 0, list(range(0, 32)), 'input channel'),
                                    Parameter('sample_rate', 1000.0, float, 'input sample rate(Hz)'),
                                    Parameter('min_voltage', -10.0, float, 'minimum output voltage (V)'),
                                    Parameter('max_voltage', 10.0, float, 'maximum output voltage(V)')
                                ]
                                ),
                      Parameter('ai1', 
                                [
                                    Parameter('channel', 1, list(range(0, 32)), 'input channel'),
                                    Parameter('sample_rate', 1000.0, float, 'input sample rate(Hz)'),
                                    Parameter('min_voltage', -10.0, float, 'minimum output voltage (V)'),
                                    Parameter('max_voltage', 10.0, float, 'maximum output voltage(V)')
                                ]
                                )

                  ]
                  ),
        Parameter('analog_output', 
                  [
                      Parameter('ao0', 
                                [
                                    Parameter('channel', 0, [0, 1, 2, 3], 'output channel'),
                                    Parameter('sample_rate', 1000.0, float, 'output sample rate (Hz)'),
                                    Parameter('min_voltage', -10.0, float, 'minimum output voltage(V)'),
                                    Parameter('max_voltage', 10.0, float, 'maximum output voltage (V)')
                                ]
                                ), 
                      Parameter('ao1', 
                                [
                                    Parameter('channel', 1, [0, 1, 2, 3], 'output channel'),
                                    Parameter('sample_rate', 1000.0, float, 'output sample rate (Hz)'),
                                    Parameter('min_voltage', -10.0, float, 'minimum output voltage(V)'),
                                    Parameter('max_voltage', 10.0, float, 'maximum output voltage (V)')
                                ]
                                ),
                      Parameter('ao2', 
                                [
                                    Parameter('channel', 2, [0, 1, 2, 3], 'output channel'),
                                    Parameter('sample_rate', 1000.0, float, 'output sample rate (Hz)'),
                                    Parameter('min_voltage', -10.0, float, 'minimum output voltage(V)'),
                                    Parameter('max_voltage', 10.0, float, 'maximum output voltage (V)')
                                ]
                                ),

                      Parameter('ao3', 
                                [
                                    Parameter('channel', 3, [0, 1, 2, 3], 'output channel'),
                                    Parameter('sample_rate', 1000.0, float, 'output sample rate (Hz)'),
                                    Parameter('min_voltage', -10.0, float, 'minimum output voltage(V)'),
                                    Parameter('max_voltage', 10.0, float, 'maximum output voltage (V)')
                                ]
                                )
                  ]
                  ),
        Parameter('external_daq_clock',
                  [
                      Parameter('ctr0',
                                [
                                    Parameter('channel', 0, list(range(0, 8)), 'channel'),
                                    Parameter('sample_rate', 1000.0, float, 'output sample rate (Hz)'),
                                    Parameter('clock_PFI_channel', 0, list(range(0, 2)), "PFI for external clock input")
                                ]
                                )

                  ]
                  ),
        Parameter('digital_input', 
                  [
                      Parameter('ctr0', 
                                [
                                    Parameter('input_channel', 0, list(range(0, 32)), 
                                            'channel for counter signal input'),
                                    Parameter('counter_PFI_channel', 1, list(range(0, 32)), 
                                            'PFI for counter channel input'),
                                    Parameter('gate_PFI_channel', 2, list(range(0, 8)),
                                            'PFI for counter channel input'),
                                    Parameter('clock_PFI_channel', 3, list(range(0, 8)),
                                            'PFI for clock channel output'),
                                    Parameter('clock_counter_channel', 1, [0, 1], 'channel for clock output'),
                                    Parameter('sample_rate', 1000.0, float, 'input sample rate (Hz)')
                                ]
                                ),
                      Parameter('ctr1', 
                                [
                                    Parameter('input_channel', 1, list(range(0, 32)), 
                                            'channel for counter signal input'),
                                    Parameter('counter_PFI_channel', 4, list(range(0, 32)), 
                                            'PFI for counter channel input'),
                                    Parameter('gate_PFI_channel', 5, list(range(0, 8)),
                                            'PFI for counter channel input'),
                                    Parameter('clock_PFI_channel', 6, list(range(0, 8)),
                                            'PFI for clock channel output'),
                                    Parameter('clock_counter_channel', 0, [0, 1], 'channel for clock output'),
                                    Parameter('sample_rate', 1000.0, float, 'input sample rate (Hz)')
                                ]
                                )
                      ]
                      ),
        Parameter('digital_output', 
                  [
                      Parameter('do0', 
                                [
                                    Parameter('channel', 0, list(range(0, 48)), 'channel'),
                                    Parameter('sample_rate', 1000.0, float, 'output sample rate(Hz)')
                                ]
                                ), 
                      Parameter('do47', 
                                [
                                    Parameter('channel', 47, list(range(0, 48)), 'channel'),
                                    Parameter('sample_rate', 1000.0, float, 'output sample rate(Hz)')
                                ]
                                )
                  ]
                  )
    ]
    )


    def setup_counter(self, channel, sample_num, continuous_acquisition=False, use_external_clock=True):
        """
        Args:
            channel: digital channel to initialize for read in
            sample_num: number of samples to read in for finite operation, or number of samples between
                       reads for continuous operation (to set buffer size)
            continuous_acquisition: run in continuous acquisition mode (ex for a continuous counter) or
                                    finite acquisition mode (ex for a scan, where the number of samples needed
                            is known a priori)
            use_external_clock: decide if an external clock may be supplied

        Returns: source of clock that this method sets up, which can be given to another function to synch that
        input or output to the same clock
        """

        task = {
            'task_handle': None,
            'task_handle_ctr': None,
            'counter_out_PFI_str': None,
            'sample_num': None,
            'sample_rate': None,
            'num_samples_per_channel': None,
            'timeout': None
        }

        task_name = self._add_to_tasklist('ctr', task)

        if 'digital_input' not in list(self.settings.keys()):
            raise ValueError('This DAQ does not support digital input')
        if not channel in list(self.settings['digital_input'].keys()):
            raise KeyError('This is not a valid digital input channel')
        
        channel_settings = self.settings['digital_input'][channel]
        # takes external clock signal
        ext_clock_channel_settings = self.settings['external_daq_clock']['ctr0']
        ext_clock_channel = ext_clock_channel_settings['channel']
        ext_clock_pfi_channel = ext_clock_channel_settings['clock_PFI_channel']

        self.running = True
        task['sample_num'] = sample_num
        task['sample_rate'] = float(channel_settings['sample_rate'])
        if not continuous_acquisition:
            task['num_samples_per_channel'] = task['sample_num']
        else:
            task['num_samples_per_channel'] = -1
        # set timeout to be 5 times the amount of time required
        task['timeout'] = float(5 * (1/task['sample_rate']) * task['sample_num'])
        input_channel_str = (self.settings['device'] + '/' + channel).encode('ascii')

        if use_external_clock:
            counter_out_str = (self.settings['external_daq'] + "/ctr" + str(ext_clock_channel)).encode('ascii')
            task['counter_out_PFI_str'] = ("/" + self.settings['device'] + "/PFI" + str(ext_clock_pfi_channel)).encode(
                'ascii')
        else:
            counter_out_str = (
                               self.settings['device'] + '/ctr' + str(channel_settings['clock_counter_channel'])).encode(
                'ascii')
            task['counter_out_PFI_str'] = ('/' +
                                           self.settings['device'] + '/Ctr' + str(
                        channel_settings['clock_counter_channel']) + "InternalOutput").encode(
                'ascii')
                                
            RuntimeWarning("You are requesting a hardware generated clock in finite sampling mode.")
            RuntimeWarning(
                "This board uses up both counters in finite sampling mode, so you need to supply external clock")
            RuntimeWarning(
                "Switching the internal clock to continuous mode, samples beyond those requested will be ignored...")
            
        # with ni.Task() as clock_task, ni.Task() as counter_task:
        clock_task = ni.Task()
        counter_task = ni.Task()
        task['task_handle'] = clock_task
        task['task_handle_ctr'] = counter_task
        clock_task.co_channels.add_co_pulse_chan_freq(counter_out_str, freq=float(task['sample_rate']),
                                                      duty_cycle=0.5)
        
        counter_task.ci_channels.add_ci_count_edges_chan(input_channel_str)

        return task_name


class PCI6601(NIDAQ):
    """This class implements the PCI6601 DAQ, which includes 32 DIO channels and 4 counters
    and inherits basic input/output functionality from NIDAQ. A subset of these channels are
    accessible here, but more can be added up to the above limits.
    """
    _DEFAULT_SETTINGS = Parameter([
        Parameter('device', "Dev2", ["Dev2"], "Name of DAQ device"),
        Parameter('override_buffer_size', -1, int, 'Buffer size for manual override (unused if -1)'),
        Parameter('digital_input', 
                  [
                      Parameter('ctr0',
                                [
                                    Parameter('input_channel', 0, list(range(0, 32)),
                                              'channel for counter signal input'),
                                    Parameter('counter_PFI_channel', 39, list(range(8, 40)),
                                              'PFI for counter channel input'),
                                    Parameter('gate_PFI_channel', 38, list(range(8, 40)),
                                              'PFI for counter channel input'),
                                    Parameter('clock_PFI_channel', 31, list(range(8, 40)),
                                              'PFI for clock channel input'),
                                    Parameter('clock_counter_channel', 1, [0, 1], 'channel for clock output'),
                                    Parameter('sample_rate', 1000.0, float, 'sample rate (Hz)')
                                ]
                                ),
                      Parameter('ctr1',
                                [
                                    Parameter('input_channel', 1, list(range(0, 32)),
                                              'channel for counter signal input'),
                                    Parameter('counter_PFI_channel', 35, list(range(8, 40)),
                                              'PFI for counter channel input'),
                                    Parameter('gate_PFI_channel', 34, list(range(8, 40)),
                                              'PFI for counter channel input'),
                                    Parameter('clock_PFI_channel', 27, list(range(8, 40)),
                                              'PFI for clock channel input'),
                                    Parameter('clock_counter_channel', 0, [0, 1], 'channel for clock output'),
                                    Parameter('sample_rate', 1000.0, float, 'input sample rate (Hz)')                                
                                ]
                                )
                  ]
                  ),
        Parameter('digital_output', 
                  [
                      Parameter('do0', 
                                [
                                    Parameter('channel', 0, list(range(0, 32)), 'channel'),
                                    Parameter('sample_rate', 1000.0, float, 'output sample rate(Hz)'),
                                ]
                                ), 
                      Parameter('do31', 
                                [
                                    Parameter('channel', 31, list(range(0, 32)), 'channel'),
                                    Parameter('sample_rate', 1000.0, float, 'output sample rate(Hz)')
                                ]
                                )
                  ]
                  ) 
   
    ])
    
    def setup_counter(self, channel, sample_num, continuous_acquisition = False, use_external_clock=False):
        """
        We must reimplement the setup_counter function due to board limitations. Initializes a hardware-timed digital
        counter, bound to a hardware clock.

        Args:
            channel: digital channel to initialize for read in
            sample_num: number of samples to read in for finite operation, or number of samples between
                       reads for continuous operation (to set buffer size)
            continuous_acquisition: run in continuous acquisition mode (ex for a continuous counter) or
                                    finite acquisition mode (ex for a scan, where the number of samples needed
                            is known a priori)
            use_external_clock: decide if an external clock may be supplied


        Returns: source of clock that this method sets up, which can be given to another function to synch that
        input or output to the same clock

        """
        task = {
            'task_handle': None,
            'task_handle_ctr': None,
            'counter_out_PFI_str': None,
            'sample_num': None,
            'sample_rate': None,
            'num_samples_per_channel': None,
            'timeout': None
        }
        
        task_name = self._add_to_tasklist('ctr', task)
        
        if 'digital_input' not in list(self.settings.keys()):
            raise ValueError('This DAQ does not support digital input')
        if not channel in list(self.settings['digital_input'].keys()):
            raise KeyError('This is not a valid digital input channel')

        channel_settings = self.settings['digital_input'][channel]
        
        self.running = True
        task['sample_num'] = sample_num
        task['sample_rate'] = float(channel_settings['sample_rate'])
        
        if not continuous_acquisition:
            task['num_samples_per_channel'] = task['sample_num']
        else:
            task['num_samples_per_channel'] = -1
            
        # set the timeout to be 5 times the amount of time required
        task['timeout'] = float(5 * (1/task['sample_rate']) * task['sample_num'])
        input_channel_str = ('/' + self.settings['device'] + '/' + channel).encode('ascii')
        task['counter_out_PFI_str'] = ('/' + self.settings['device'] + '/PFI' + str(
            channel_settings['clock_PFI_channel'])).encode(
            'ascii')
        counter_out_str = (
                    '/' + self.settings['device'] + '/ctr' + str(channel_settings['clock_counter_channel'])).encode(
            'ascii')

        # with ni.Task() as clock_task, ni.Task() as counter_task:
        clock_task = ni.Task()
        counter_task = ni.Task()
        task['task_handle'] = clock_task
        task['task_handle_ctr'] = counter_task
        
        clock_task.co_channels.add_co_pulse_chan_freq(counter_out_str, freq=float(task['sample_rate']), 
                                                      duty_cycle=0.5)
        if use_external_clock:
            clock_task.timing.cfg_implicit_timing(samps_per_chan=int(task['sample_num']))
            counter_task.timing.cfg_samp_clk_timing(float(task['sample_rate']), source=task['counter_out_PFI_str'],
                                                samps_per_chan=task['sample_num'])
        else:
            internal_timebase = '100kHz' # can also set to 20 MHz
            clock_task.timing.cfg_implicit_timing()
            counter_task.timing.cfg_samp_clk_timing(float(task['sample_rate']), source=('/' + self.settings['device'] +'/' + internal_timebase),
                                                    sample_mode=AcquisitionType.CONTINUOUS if continuous_acquisition else AcquisitionType.FINITE)
                                                
        counter_task.ci_channels.add_ci_count_edges_chan(input_channel_str)

        counter_task.start()
        clock_task.start()
        
        return task_name


def voltage_to_int(voltage):
    """
    convert voltage to integer value
    Args:
        voltage:

    Returns:

    """
    # TODO: make it work for arrays and lists
    return int((voltage * 32767) / 10)


def time_to_buffersize(time, ticks=56):
    return int(time / (ticks * 0.000000025))


def buffersize_to_time(size, ticks=56):
    return size * (ticks * 0.000000025)


if __name__ == '__main__':
    daq = NIDAQ()
    dev_list = daq.get_connected_devices()
    for d in dev_list:
        print(d)
