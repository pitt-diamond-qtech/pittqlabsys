# Created by Gurudev Dutt <gdutt@pitt.edu> on 2023-08-03
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

import time
from collections import deque
import numpy as np
#from scipy.ndimage.filters import uniform_filter1d
#import matplotlib.pyplot as plt
from src.Controller import NIDAQ,PXI6733
from src.View.plotting.plots_1d import plot_counts,  update_counts_vs_pos
from src.core import Parameter, Experiment
#from src.Model.experiments import FindNV


class Pxi6733ReadCounter(Experiment):
    """
This experiment reads the Counter input from the DAQ and plots it.

WARNING: Only implemented either for the PCI DAQ (NI6281) or PXIe6733 !!!!

If you want to use it make sure that the right device is defined in _DEVICES = {'daq': PXI6733} in the python code.

    """
    _DEFAULT_SETTINGS = [
        Parameter('integration_time', .1, float, 'Time per data point (s)'),
        Parameter('counter_channel', 'ctr0', ['ctr0', 'ctr2'], 'Daq channel used for counter'),
        Parameter('total_int_time', 5.0, float, 'Total time to integrate (s) (if -1 then it will go indefinitely)'),
        Parameter('plot_style',"main",['main', 'aux', '2D', 'two'])
    ]

    #_DEVICES = {'daq': PXI6733}
    #####_DEVICES = {'daq':PXI6733()}
    _EXPERIMENTS = {}

    def __init__(self, devices, experiments=None, name=None, settings=None, log_function=None, data_path=None):
        """
        Example of a experiment that emits a QT signal for the gui
        Args:
            name (optional): name of experiment, if empty same as class name
            settings (optional): settings for this experiment, if empty same as default settings
        """
        super().__init__(name, settings=settings, sub_experiments=experiments,devices=devices,
                        log_function=log_function, data_path=data_path)

        self.data = {'counts': deque(),  'normalized_counts': deque()}


    def _function(self):
        """
        This is the actual function that will be executed. It uses only information that is provided in the settings property
        will be overwritten in the __init__
        """



        sample_rate = 1.0 / self.settings['integration_time']
        normalization = self.settings['integration_time']/.001
        #print("the devices dict is", self.devices)
        # added this line on 08/31/2023 to make GUI work
        # modified test function as well to pass the right dictionary
        dev_instance = self.devices['daq']['instance']
        #print("Device instance is ",dev_instance)
        dig_input = dev_instance.settings['digital_input']
        #print("Digital input is ",dig_input)
        counter_chan = dig_input[self.settings['counter_channel']]
        #print("counter chan is", counter_chan)
        counter_chan['sample_rate'] = sample_rate
        self.data = {'counts': deque(), 'laser_power': deque(), 'normalized_counts': deque(), 'laser_power2': deque()}
        self.last_value = 0
        sample_num = 2

        task = dev_instance.setup_counter(self.settings['counter_channel'], sample_num, continuous_acquisition=True,use_external_clock=False)


        # maximum number of samples if total_int_time > 0
        if self.settings['total_int_time'] > 0:
            max_samples = np.floor(self.settings['total_int_time']/self.settings['integration_time'])



        dev_instance.run(task)

        # GD 20230803 wait for at least one clock tick to go by to start with a full clock tick of acquisition time for the first bin
        time.sleep(self.settings['integration_time'])

        sample_index = 0 # keep track of samples made to know when to stop if finite integration time

        while True:
            if self._abort:
                break



            raw_data, num_read = dev_instance.read(task)

            #skip first read, which gives an anomolous value
            if num_read == 1:
                self.last_value = raw_data[0] #update running value to last measured value to prevent count spikes
                time.sleep(2.0 / sample_rate)
                continue

            tmp_count = 0
            for value in raw_data:
                new_val = ((float(value) - self.last_value) / normalization)
                self.data['counts'].append(new_val)
                self.last_value = value


                tmp_count = tmp_count + 1

            if self.settings['total_int_time'] > 0:
                self.progress = sample_index/max_samples
            else:
                self.progress = 50.
            self.updateProgress.emit(int(self.progress))

            time.sleep(2.0 / sample_rate)
            sample_index = sample_index + 1
            if self.settings['total_int_time'] > 0. and sample_index >= max_samples: # if the maximum integration time is hit
                self._abort = True # tell the experiment to abort

        # clean up APD tasks
        dev_instance.stop(task)


        self.data['counts'] = list(self.data['counts'])



    def plot(self, figure_list):
        super(Pxi6733ReadCounter, self).plot([figure_list[0]])

    def _plot(self, axes_list, data = None):
        # COMMENT_ME

        if data is None:
            data = self.data

        if len(data['counts']) > 0:
            array_to_plot = np.delete(data['counts'], 0)

            plot_counts(axes_list[0], array_to_plot)

    def _update_plot(self, axes_list, data = None):
        if data is None:
            data = self.data

        if data:
            array_to_plot = np.delete(data['counts'], 0)

            update_counts_vs_pos(axes_list[0], array_to_plot, np.linspace(0, len(array_to_plot), len(array_to_plot)))





if __name__ == '__main__':
    experiment = {}
    instr = {'daq': PXI6733()}
    #experiment, failed, instr = Experiment.load_and_append({'Daq_Read_Counter': 'Daq_Read_Counter'}, experiment, instr)
    expt = Pxi6733ReadCounter(instr, name='daq_read_ctr')
    print(expt.data)
    expt.run()
    print(expt.data)

    # print(experiment)
    # print(failed)
    # print(instr)