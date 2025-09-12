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
#from src.Controller.ni_daq import PXI6733, NI6281, PCI6229, PCI6601
from src.View.plotting.plots_2d import plot_fluorescence, update_fluorescence
from src.core import Experiment, Parameter


class GalvoScanGeneric(Experiment):
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
                                                           center: pta is center and ptb is extend of rectangle'),
        Parameter('num_points',
                  [Parameter('x', 25, int, 'number of x points to scan'),
                   Parameter('y', 25, int, 'number of y points to scan')
                   ]),
        Parameter('time_per_pt', .002, [.0001, .001, .002, .005, .01, .015, .02], 'time in s to measure at each point'),
        Parameter('settle_time', .0002, [.0002], 'wait time between points to allow galvo to settle in seconds'),
        Parameter('max_counts_plot', -1, int, 'Rescales colorbar with this as the maximum counts on replotting'),
        Parameter('ending_behavior', 'return_to_start', ['return_to_start', 'return_to_origin', 'leave_at_corner'],
                  'return to the corn')
    ]

    _DEVICES = {}
    _EXPERIMENTS = {}
    _ACQ_TYPE = 'line'  # this defines if the galvo acquisition is line by line or point by point, the default is line

    # Only for line scans. If true, scans each line twice, but with different conditions (e.g. second scan
    # has laser off or MW off)

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
        from src.Controller.ni_daq import PXI6733, NI6281, PCI6229, PCI6601
        super().__init__(name, settings=settings, devices=devices, log_function=log_function,
                         data_path=data_path)

    def setup_scan(self):
        """
        prepares the scan
        Returns:

        """
        pass

    def check_bounds(self):
        """
        Checks that the scan positions are legal
        Returns:

        """
        pass

    def scale(self):
        """
        Custom scaling for voltages
        For galvo scans, this should be left as 1
        For Pizeo scans, this should be 7.5/10/15, depending on the voltage limit of the piezo controller
        Returns:
        1 as default
        """
        return 1

    def before_scan(self):
        """
        Runs something before starting the scan.
        This can be something like moving the laser to a certain position, running findNV, or turning on MW
        Returns:

        """
        pass

    def after_scan(self):
        """
        Runs something after finishing the scan.
        This can be something like moving the laser to a certain position, running findNV, or turning off MW
        Returns:

        """
        pass

    def _function(self):
        """
        Executes threaded galvo scan
        """
        self.before_scan()

        self.data = {'image_data': np.zeros((self.settings['num_points']['y'], self.settings['num_points']['x']))}
        self.data['extent'] = self.pts_to_extent(self.settings['point_a'], self.settings['point_b'],
                                                 self.settings['RoI_mode'])

        [x_vmin, x_vmax, y_vmax, y_vmin] = self.data['extent']
        self.x_array = np.linspace(x_vmin, x_vmax, self.settings['num_points']['x'], endpoint=True) / self.scale()
        self.y_array = np.linspace(y_vmin, y_vmax, self.settings['num_points']['y'], endpoint=True) / self.scale()
        try:
            self.check_bounds()
        except AttributeError:
            return

        if self._ACQ_TYPE == 'point':
            # stores the complete data acquired at each point, image_data holds only a scalar at each point
            self.data['point_data'] = []

        # error is raised in setup_scan if requested daq is not connected. This then ends the experiment.
        try:
            self.setup_scan()
        except AttributeError:
            return

        initial_position = self.get_galvo_location()
        if len(initial_position) == 0:
            print('WARNING!! GALVO POSITION COULD NOT BE DETERMINED. SET ENDING ending_behavior TO leave_at_corner')
            self.settings['ending_behavior'] = 'leave_at_corner'

        nx, ny = self.settings['num_points']['x'], self.settings['num_points']['y']

        for y_num in range(0, ny):

            if self._ACQ_TYPE == 'line':
                if self._abort:
                    break

                line_data = self.read_line_wrapper(self.y_array[y_num])
                # line_data = self.read_line(self.y_array[y_num])

                self.data['image_data'][y_num] = line_data

                self.progress = float(y_num + 1) / ny * 100
                self.updateProgress.emit(int(self.progress))

            elif self._ACQ_TYPE == 'point':
                for x_num in range(0, nx):
                    if self._abort:
                        break

                    point_data = self.read_point(self.x_array[x_num], self.y_array[y_num])
                    self.data['image_data'][y_num, x_num] = np.mean(point_data)

                    self.data['point_data'].append(point_data)
                    self.progress = float(y_num * nx + 1 + x_num) / (nx * ny) * 100

                    # GD: tmp print info about progress
                    print(('current acquisition {:02d}/{:02d} ({:0.2f}%)'.format(y_num * nx + x_num, nx * ny,
                                                                                 self.progress)))

                    self.updateProgress.emit(int(self.progress))

                # fill the rest of the array with the mean of the data up to now
                # (otherwise it's zero and the data is not visible in the plot)
                if y_num < ny:
                    self.data['image_data'][y_num + 1:, :] = np.mean(self.data['image_data'][0:y_num, :].flatten())

        self.after_scan()

        # set point after scan based on ending_behavior setting
        if self.settings['ending_behavior'] == 'leave_at_corner':
            return
        elif self.settings['ending_behavior'] == 'return_to_start':
            self.set_galvo_location(initial_position)
        elif self.settings['ending_behavior'] == 'return_to_origin':
            self.set_galvo_location([0, 0])

    def get_galvo_location(self):
        """
        returns the current position of the galvo
        Returns: list with two floats, which give the x and y position of the galvo mirror
        """
        raise NotImplementedError

    def set_galvo_location(self, galvo_position):
        """
        sets the current position of the galvo
        galvo_position: list with two floats, which give the x and y position of the galvo mirror
        """
        raise NotImplementedError

    def read_line_wrapper(self, y_pos):
        """
                In the simplest scenario this just runs read_line
                However, you can rewrite this to call read_line twice with different conditions, e.g. read_line with MW
                on and off and extract the difference
                Args:
                    y_pos: y position of the scan

                Returns:

                """
        return self.read_line(y_pos)

    def read_line(self, y_pos):
        """
        reads a line of data from the DAQ, this function is used if _ACQ_TYPE = 'line'
        Args:
            y_pos: y position of the scan

        Returns:

        """
        raise NotImplementedError

    def read_point(self, x_pos, y_pos):
        """
        reads a line of data from the DAQ, this function is used if _ACQ_TYPE = 'point'
        Args:
            x_pos: x position of the scan
            y_pos: y position of the scan
        Returns:

        """
        raise NotImplementedError

    @staticmethod
    def pts_to_extent(pta, ptb, roi_mode):
        """

        Args:
            pta: point a
            ptb: point b
            roi_mode:   mode how to calculate region of interest
                        corner: pta and ptb are diagonal corners of rectangle.
                        center: pta is center and ptb is extend or rectangle

        Returns: extend of region of interest [x_vmin, x_vmax, y_vmax, y_vmin]

        """
        x_vmin, x_vmax, y_vmin, y_vmax = ((0.0,) * 4)

        if roi_mode == 'corner':
            x_vmin = min(pta['x'], ptb['x'])
            x_vmax = max(pta['x'], ptb['x'])
            y_vmin = min(pta['y'], ptb['y'])
            y_vmax = max(pta['y'], ptb['y'])
        elif roi_mode == 'center':
            x_vmin = pta['x'] - float(ptb['x']) / 2.
            x_vmax = pta['x'] + float(ptb['x']) / 2.
            y_vmin = pta['y'] - float(ptb['y']) / 2.
            y_vmax = pta['y'] + float(ptb['y']) / 2.
        return [x_vmin, x_vmax, y_vmax, y_vmin]

    def _plot(self, axes_list, data=None):
        """
        Plots the galvo scan image
        Args:
            axes_list: list of axes objects on which to plot the galvo scan on the first axes object
            data: data (dictionary that contains keys image_data, extent) if not provided use self.data
        """

        if data is None:
            data = self.data

        plot_fluorescence(data['image_data'], data['extent'], axes_list[0],
                          max_counts=self.settings['max_counts_plot'])

    def _update_plot(self, axes_list):
        """
        updates the galvo scan image
        Args:
            axes_list: list of axes objects on which to plot plots the esr on the first axes object
        """
        update_fluorescence(self.data['image_data'], axes_list[0], self.settings['max_counts_plot'])

    def get_axes_layout(self, figure_list):
        """
        returns the axes objects the experiment needs to plot its data
        the default creates a single axes object on each figure
        This can/should be overwritten in a child experiment if more axes objects are needed
        Args:
            figure_list: a list of figure objects
        Returns:
            axes_list: a list of axes objects

        """

        # only pick the first figure from the figure list, this avoids that get_axes_layout clears all the figures
        return super(GalvoScanGeneric, self).get_axes_layout([figure_list[0]])
