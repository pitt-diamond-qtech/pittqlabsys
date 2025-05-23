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
import pyqtgraph as pg
from scipy.spatial import KDTree
import time
import matplotlib
from matplotlib import patches
import random
from src.core import Experiment, Parameter

class SelectPoints(Experiment):
    """
Experiment to select points on an image. The selected points are saved and can be used in a superexperiment to iterate over.
    """
    _DEFAULT_SETTINGS = [
        Parameter('patch_size', 0.003),
        Parameter('type', 'free', ['free', 'square', 'line', 'ring', 'arc']),
        Parameter('Nx', 5, int, 'number of points along x (type: square) along line (type: line)'),
        Parameter('Ny', 5, int, 'number of points along y (type: square)'),
        Parameter('randomize', False, bool, 'Determines if points should be randomized')
    ]
    _DEVICES = {}
    _EXPERIMENTS = {}
    def __init__(self, devices = None, experiments = None, name = None, settings = None, log_function = None, data_path = None):
        """
        Select points by clicking on an image
        """
        Experiment.__init__(self, name, settings = settings, devices = devices, sub_experiments= experiments, log_function= log_function, data_path = data_path)
        self.text = []
        self.patch_collection = None
        self.plot_settings = {}
    def _function(self):
        """
        Waits until stopped to keep experiment live. Gui must handle calling of Toggle_NV function on mouse click.
        """
        self.data = {'nv_locations': [], 'image_data': None, 'extent': None}
        self.progress = 50
        self.updateProgress.emit(self.progress)
        # keep experiment alive while NVs are selected
        while not self._abort:
            time.sleep(1)

    def plot(self, figure_list):
        '''
        Plots a dot on top of each selected NV, with a corresponding number denoting the order in which the NVs are
        listed.
        Precondition: must have an existing image in figure_list[0] to plot over
        Args:
            figure_list:
        '''
        # if there is not image data get it from the current plot
        if not self.data == {} and self.data['image_data'] is None:
            plot = figure_list[0].getItem(row=0,col=0)
            x_axis = plot.getAxis('bottom')
            y_axis = plot.getAxis('left')


            self.plot_settings['xlabel'] = x_axis.label.text
            self.plot_settings['ylabel'] = y_axis.label.text
            print(self.plot_settings)
            label = plot.getLabel()
            print(label)


            axes = figure_list[0].axes[0]
            if len(axes.images)>0:
                self.data['image_data'] = np.array(axes.images[0].get_array())
                self.data['extent'] = np.array(axes.images[0].get_extent())
                self.plot_settings['cmap'] = axes.images[0].get_cmap().name
                self.plot_settings['xlabel'] = x_axis.label.text
                self.plot_settings['ylabel'] = y_axis.label.text
                self.plot_settings['title'] = axes.get_title()
                self.plot_settings['interpol'] = axes.images[0].get_interpolation()

                print(self.plot_settings)
        Experiment.plot(self, figure_list)

    #must be passed figure with galvo plot on first axis
    def _plot(self, axes_list):
        print('select points _plot executed')
        '''
        Plots a dot on top of each selected NV, with a corresponding number denoting the order in which the NVs are
        listed.
        Precondition: must have an existing image in figure_list[0] to plot over
        Args:
            figure_list:
        '''
        axes = axes_list[0]
        if self.plot_settings:
            axes.imshow(self.data['image_data'], cmap=self.plot_settings['cmap'], interpolation=self.plot_settings['interpol'], extent=self.data['extent'])
            axes.set_xlabel(self.plot_settings['xlabel'])
            axes.set_ylabel(self.plot_settings['ylabel'])
            axes.set_title(self.plot_settings['title'])
        self._update(axes_list)

    def _update(self, axes_list):
        print('select points _update executed')
        #note: may be able to use blit to make things faster
        axes = axes_list[0]
        patch_size = self.settings['patch_size']
        # first clear all old patches (circles and numbers), then redraw all
        if self.patch_collection:
            try:
                self.patch_collection.remove()
                for text in self.text:
                    text.remove()
            except ValueError:
                pass
        patch_list = []
        if(self.data['nv_locations'] is not None):
            for index, pt in enumerate(self.data['nv_locations']):
                circ = patches.Circle((pt[0], pt[1]), patch_size, fc='b')
                patch_list.append(circ)
                #cap number of drawn numbers at 400 since drawing text is extremely slow and they're all so close together
                #as to be unreadable anyways
                if len(self.data['nv_locations']) <= 400:
                    text = axes.text(pt[0], pt[1], '{:d}'.format(index),
                            horizontalalignment='center',
                            verticalalignment='center',
                            color='white'
                            )
                    self.text.append(text)
                else:
                    print("Cannot select more than 400 locations in image!")
                    raise RuntimeError("Cannot select more than 400 locations in image!")
            #patch collection used here instead of adding individual patches for speed
            self.patch_collection = matplotlib.collections.PatchCollection(patch_list)
            axes.add_collection(self.patch_collection)

    def toggle_NV(self, pt):
        print('select points toggle_NV executed')
        '''
        If there is not currently a selected NV within self.settings[patch_size] of pt, adds it to the selected list. If
        there is, removes that point from the selected list.
        Args:
            pt: the point to add or remove from the selected list
        Poststate: updates selected list
        '''
        if not self.data['nv_locations']: #if self.data is empty so this is the first point
            self.data['nv_locations'].append(pt)
            self.data['image_data'] = None # clear image data
        else:
            # use KDTree to find NV closest to mouse click
            tree = KDTree(self.data['nv_locations'])
            #does a search with k=1, that is a search for the nearest neighbor, within distance_upper_bound
            d, i = tree.query(pt,k = 1, distance_upper_bound = self.settings['patch_size'])

            # removes NV if previously selected
            if d is not np.inf:
                self.data['nv_locations'].pop(i)
            # adds NV if not previously selected
            else:
                self.data['nv_locations'].append(pt)

            # randomize
            if self.settings['randomize']:
                self.log('warning! randomize not avalable when manually selecting points')

        # if type is not free we calculate the total points of locations from the first selected points
        if self.settings['type'] == 'square' and len(self.data['nv_locations'])>1:
            # here we create a rectangular grid, where pts a and be define the top left and bottom right corner of the rectangle
            Nx, Ny = self.settings['Nx'], self.settings['Ny']
            pta = self.data['nv_locations'][0]
            ptb = self.data['nv_locations'][1]
            tmp  = np.array([[[pta[0] + 1.0*i*(ptb[0]-pta[0])/(Nx-1), pta[1] + 1.0*j*(ptb[1]-pta[1])/(Ny-1)] for i in range(Nx)] for j in range(Ny)])
            nv_pts = np.reshape(tmp, (Nx * Ny, 2))

            # randomize
            if self.settings['randomize']:
                random.shuffle(nv_pts)  # shuffles in place

            self.data['nv_locations'] = nv_pts

            self.stop()
        elif self.settings['type'] == 'line' and len(self.data['nv_locations'])>1:
            # here we create a straight line between points a and b
            N = self.settings['Nx']
            pta = self.data['nv_locations'][0]
            ptb = self.data['nv_locations'][1]
            nv_pts = [np.array([pta[0] + 1.0*i*(ptb[0]-pta[0])/(N-1), pta[1] + 1.0*i*(ptb[1]-pta[1])/(N-1)]) for i in range(N)]


            # randomize
            if self.settings['randomize']:
                random.shuffle(nv_pts)  # shuffles in place

            self.data['nv_locations'] = nv_pts

            self.stop()
        elif self.settings['type'] == 'ring' and len(self.data['nv_locations'])>1:
            # here we create a circular grid, where pts a and be define the center and the outermost ring
            Nx, Ny = self.settings['Nx'], self.settings['Ny']
            pt_center = self.data['nv_locations'][0] # center
            pt_outer = self.data['nv_locations'][1] # outermost ring
            # radius of outermost ring:
            rmax = np.sqrt((pt_center[0] - pt_outer[0]) ** 2 + (pt_center[1] - pt_outer[1]) ** 2)

            # angles
            angles = np.linspace(0, 2 * np.pi, Nx+1)[0:-1]
            # create points on rings
            nv_pts = []
            for r in np.linspace(rmax, 0, Ny + 1)[0:-1]:
                for theta in angles:
                    nv_pts += [[r * np.sin(theta)+pt_center[0], r * np.cos(theta)+pt_center[1]]]



            # randomize
            if self.settings['randomize']:
                coarray = list(zip(nv_pts, angles))
                random.shuffle(coarray)  # shuffles in place
                nv_pts, angles = zip(*coarray)

            self.data['nv_locations'] = np.array(nv_pts)
            self.data['angles'] = np.array(angles)* 180 / np.pi
            self.data['ring_data'] = [pt_center, pt_outer]
            self.stop()

        elif self.settings['type'] == 'arc' and len(self.data['nv_locations']) > 3:
            # here we create a circular grid, where pts a and be define the center and the outermost ring
            Nx, Ny = self.settings['Nx'], self.settings['Ny']
            pt_center = self.data['nv_locations'][0]  # center
            pt_start = self.data['nv_locations'][1]  # arc point one (radius)
            pt_dir = self.data['nv_locations'][2]  # arc point two (direction)
            pt_end = self.data['nv_locations'][3]  # arc point three (angle)

            # radius of outermost ring:
            rmax = np.sqrt((pt_center[0] - pt_start[0]) ** 2 + (pt_center[1] - pt_start[1]) ** 2)
            angle_start = np.arctan((pt_start[1] - pt_center[1]) / (pt_start[0] - pt_center[0]))
            # arctan always returns between -pi/2 and pi/2, so adjust to allow full range of angles
            if ((pt_start[0] - pt_center[0]) < 0):
                angle_start += np.pi

            angle_end = np.arctan((pt_end[1] - pt_center[1]) / (pt_end[0] - pt_center[0]))
            # arctan always returns between -pi/2 and pi/2, so adjust to allow full range of angles
            if ((pt_end[0] - pt_center[0]) < 0):
                angle_end += np.pi

            if pt_dir[0] < pt_start[0]:
                # counter-clockwise: invert the order of the angles
                angle_start, angle_end = angle_end, angle_start

            if angle_start > angle_end:
                # make sure that start is the smaller
                # (e.g. angle_start= 180 deg and angle_end =10, we want to got from 180 to 370 deg)
                angle_end += 2 * np.pi

            # create points on arcs
            nv_pts = []
            for r in np.linspace(rmax, 0, Ny + 1)[0:-1]:
                for theta in np.linspace(angle_start, angle_end, Nx, endpoint=True):
                    nv_pts += [[r * np.cos(theta) + pt_center[0], r * np.sin(theta) + pt_center[1]]]

            # randomize
            if self.settings['randomize']:
                coarray = list(zip(nv_pts, np.linspace(angle_start, angle_end, Nx, endpoint=True)))
                random.shuffle(coarray)  # shuffles in place
                nv_pts, angles = zip(*coarray)
            else:
                angles = np.linspace(angle_start, angle_end, Nx, endpoint=True)
            self.data['nv_locations'] = np.array(nv_pts)
            self.data['arc_data'] = [pt_center, pt_start, pt_end]
            self.data['angles'] = np.array(angles) * 180 / np.pi
            self.stop()

if __name__ == '__main__':
    experiment, failed, instr = Experiment.load_and_append({'SelectPoints':'SelectPoints'})
    print(experiment)
    print(failed)
    print(instr)