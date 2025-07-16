# Created by Gurudev Dutt <gdutt@pitt.edu> on 2023-08-17
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

import numpy as np
import time
from src.core import Parameter, Experiment
from src.Controller import PXI6733, NI6281, MicrowaveGenerator, NIDAQ
from src.Model.experiments.galvo_scan_generic import GalvoScanGeneric


class GalvoScan(GalvoScanGeneric):
    """
    GalvoScan uses the apd, daq, and galvo to sweep across voltages while counting photons at each voltage,
    resulting in an image in the current field of view of the objective.
    """

    _DEFAULT_SETTINGS = [
        Parameter('point_a',
                  [Parameter('x', 0, float, 'x-coordinate'),
                   Parameter('y', 0, float, 'y-coordinate')
                   ]),
        Parameter('point_b',
                  [Parameter('x', 1.0, float, 'x-coordinate'),
                   Parameter('y', 1.0, float, 'y-coordinate')
                   ]),
        Parameter('RoI_mode', 'center', ['corner', 'center'], 'mode to calculate region of interest.\n \
                                                               corner: pta and ptb are diagonal corners of rectangle.\n \
                                                               center: pta is center and pta is extend or rectangle'),
        Parameter('num_points',
                  [Parameter('x', 64, int, 'number of x points to scan'),
                   Parameter('y', 64, int, 'number of y points to scan')
                   ]),
        Parameter('time_per_pt', .002, [.0005, .001, .002, .005, .01, .015, .02, .05, .1],
                  'time in s to measure at each point'),
        Parameter('settle_time', .0002, [.0002, .0005], 'wait time between points to allow galvo to settle'),
        Parameter('max_counts_plot', -1, int, 'Rescales colorbar with this as the maximum counts on replotting'),
        Parameter('DAQ_channels',
                  [Parameter('x_ao_channel', 'ao0', ['ao0', 'ao1', 'ao2', 'ao3'],
                             'Daq channel used for x voltage analog output'),
                   Parameter('y_ao_channel', 'ao1', ['ao0', 'ao1', 'ao2', 'ao3'],
                             'Daq channel used for y voltage analog output'),
                   Parameter('x_ai_channel',"ai0",['ai0','ai1','ai2','ai3'],
                             'Daq channel used for x voltage analog input'),
                   Parameter('y_ai_channel', "ai1", ['ai0', 'ai1', 'ai2', 'ai3'],
                             'Daq channel used for x voltage analog input'),
                   Parameter('counter_channel', 'ctr0', ['ctr0', 'ctr1'],
                             'Daq channel used for counter')
                   ]),
        Parameter('ending_behavior', 'return_to_start', ['return_to_start', 'return_to_origin', 'leave_at_corner'],
                  'return to the corn'),
        Parameter('daq_type', 'PXI', ['PCI', 'PXI'], 'Type of daq to use for scan'),
        Parameter('plot_style', "main", ['main', 'aux', '2D', 'two'])
    ]

    #####_DEVICES = {'daq': PXI6733(),'daq2': NI6281()}

    def __init__(self, devices=None, name=None, settings=None, log_function=None, data_path=None):
        '''
        Initializes GalvoScan experiment for use in gui

        Args:
            devices: list of device objects
            name: name to give to instantiated experiment object
            settings: dictionary of new settings to pass in to override defaults
            log_function: log function passed from the gui to direct log calls to the gui log
            data_path: path to save data

        '''
        self._DEFAULT_SETTINGS = self._DEFAULT_SETTINGS + GalvoScanGeneric._DEFAULT_SETTINGS
        super().__init__(name=name, devices=devices, settings=settings, log_function=log_function,
                         data_path=data_path)
        # GD 20230817: tried to ensure that we use at least one NI device ...not working will debug later
        # device_list = NIDAQ.get_connected_devices()
        # if not (self.devices['daq'].settings['device'] in device_list):
        #     self.settings['daq_type'] = 'PCI'
        #     self.devices = {'daq': NI6281()}
        # I should probably add the instances to a dictionary and keep track of them, but would have to re-implement
        # that in the Experiment class first. doing it by hand for now
        self.dev_instance = self.devices['daq']['instance']
        self.dev_instance2 = self.devices['daq2']['instance']
        self.setup_scan()

    def setup_scan(self):

        # clock_adjust is needed to account for the finite settle time of the Galvo
        # since we have to give the DAQ a clock time we define the settle time as one time bin unit and then the
        # measurement time must be a multiple of that unit. t_meas = N x t_settle
        # Hence, instead of measuring once at each position we measure N+1 times and set the galvo N+1 times to the same position
        # Later we throw out the first measurement since that is when the galvo still settles.
        self.clock_adjust = int(
            (self.settings['time_per_pt'] + self.settings['settle_time']) / self.settings['settle_time'])

        [x_vmin, x_vmax, y_vmax, y_vmin] = self.pts_to_extent(self.settings['point_a'], self.settings['point_b'],
                                                              self.settings['RoI_mode'])

        self.x_array = np.repeat(np.linspace(x_vmin, x_vmax, self.settings['num_points']['x'], endpoint=True),
                                 self.clock_adjust)
        self.y_array = np.linspace(y_vmin, y_vmax, self.settings['num_points']['y'], endpoint=True)
        sample_rate = float(1) / self.settings['settle_time']

        self.dev_instance.settings['analog_output'][
            self.settings['DAQ_channels']['x_ao_channel']]['sample_rate'] = sample_rate
        self.dev_instance.settings['analog_output'][
            self.settings['DAQ_channels']['y_ao_channel']]['sample_rate'] = sample_rate
        self.dev_instance.settings['digital_input'][
            self.settings['DAQ_channels']['counter_channel']]['sample_rate'] = sample_rate

    def get_galvo_location(self):
        """
        returns the current position of the galvo
        Returns: list with two floats, which give the x and y position of the galvo mirror
        """
        # GD 20230817: I need to think about this, if I try to read in the voltage using NI6281, I will need to sync the AI input
        # using the ctr0 which means I would also have to select use external clock for the counter task. all of this will
        # need re-tested with the nidaq_test module which I don't have time to do right now . IN fact, it almost looks
        # like the NI6281 module would have been better to use from that perspective and I should change the code and the wiring to do that eventually.
        # galvo_position = self.dev_instance2.get_analog_voltages([
        #     self.settings['DAQ_channels']['x_ai_channel'],
        #     self.settings['DAQ_channels']['y_ai_channel']]
        # )
        return [self.x_array[-1],self.y_array[-1]]

    def set_galvo_location(self, galvo_position):
        """
        sets the current position of the galvo
        galvo_position: list with two floats, which give the x and y position of the galvo mirror
        """
        if galvo_position[0] > 1 or galvo_position[0] < -1 or galvo_position[1] > 1 or galvo_position[1] < -1:
            raise ValueError(
                'The experiment attempted to set the galvo position to an illegal position outside of +- 1 V')

        pt = galvo_position
        # daq = self.devices['daq']['instance']
        # daq API only accepts either one point and one channel or multiple points and multiple channels
        pt = np.transpose(np.column_stack((pt[0], pt[1])))
        pt = (np.repeat(pt, 2, axis=1))

        ao_task = self.dev_instance.setup_AO(
            [self.settings['DAQ_channels']['x_ao_channel'], self.settings['DAQ_channels']['y_ao_channel']], pt)
        self.dev_instance.run(ao_task)
        # self.dev_instance.AO_waitToFinish()
        self.dev_instance.stop(ao_task)

    def read_line(self, y_pos):
        """
        reads a line of data from the DAQ
        Args:
            y_pos: y position of the scan

        Returns:

        """
        # initialize APD thread
        # ctr_task = self.dev_instance.setup_counter(self.settings['DAQ_channels']['counter_channel'],
        #                                            len(self.x_array) + 1,use_external_clock=False)
        ctr_task = self.dev_instance.setup_counter(self.settings['DAQ_channels']['counter_channel'],
                                                   len(self.x_array) + 1)
        self.init_pt = np.transpose(np.column_stack((self.x_array[0], y_pos)))
        self.init_pt = (np.repeat(self.init_pt, 2, axis=1))

        # move galvo to first point in line
        ao_task = self.dev_instance.setup_AO(
            [self.settings['DAQ_channels']['x_ao_channel'], self.settings['DAQ_channels']['y_ao_channel']],
            self.init_pt, "")
        self.dev_instance.run(ao_task)
        # self.devices['daq']['instance'].AO_waitToFinish()
        self.dev_instance.stop(ao_task)

        # now set up the 1d line scan
        ao_task = self.dev_instance.setup_AO([self.settings['DAQ_channels']['x_ao_channel']], self.x_array,
                                             clk_source=ctr_task)
        # start counter and scanning sequence
        self.dev_instance.run(ao_task)
        self.dev_instance.run(ctr_task)

        self.dev_instance.stop(ao_task)
        x_line_data, _ = self.dev_instance.read(ctr_task)
        self.dev_instance.stop(ctr_task)
        diff_data = np.diff(x_line_data)

        summed_data = np.zeros(int(len(self.x_array) / self.clock_adjust))
        for i in range(0, int((len(self.x_array) / self.clock_adjust))):
            summed_data[i] = np.sum(
                diff_data[(i * self.clock_adjust + 1):(i * self.clock_adjust + self.clock_adjust - 1)])
        # also normalizing to kcounts/sec
        return summed_data * (.001 / self.settings['time_per_pt'])


if __name__ == '__main__':
    experiment, failed, devices = Experiment.load_and_append(experiment_dict={'GalvoScan': GalvoScan},
                                                             raise_errors=True)
    #
    print(experiment)
    print(failed)
# # print(devices)
