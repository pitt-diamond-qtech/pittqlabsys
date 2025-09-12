'''
Nanodrive ADwin Confocal Scan Slow Module

This module implements slow, high-resolution scanning for confocal microscopy using:
- MCL NanoDrive for sample stage positioning
- ADwin Gold II for photon counting and timing
- Point-by-point scanning for maximum precision

The slow method goes point by point to ensure the scan is precise and accurate 
at the cost of execution time, but provides the highest quality images.
'''

import numpy as np
from pyqtgraph.exporters import ImageExporter
from pathlib import Path

from src.core import Parameter, Experiment
from src.core.helper_functions import get_configured_confocal_scans_folder
from src.core.adwin_helpers import get_adwin_binary_path
from time import sleep
import pyqtgraph as pg




class NanodriveAdwinConfocalScanSlow(Experiment):
    '''
    Slow, high-precision confocal microscope scan using MCL NanoDrive and ADwin Gold II.
    
    This class runs a confocal microscope scan using the MCL NanoDrive to move 
    the sample stage and the ADwin Gold II to get count data. The slow method 
    goes point by point to ensure the scan is precise and accurate at the cost 
    of execution time.

    Hardware Dependencies:
    - MCL NanoDrive: For precise sample stage positioning
    - ADwin Gold II: For photon counting and timing control
    - ADbasic Binary: Trial_Counter.TB1 for counter operations
    '''

    _DEFAULT_SETTINGS = [
        Parameter('point_a',
                  [Parameter('x',35,float,'x-coordinate start in microns'),
                   Parameter('y',35,float,'y-coordinate start in microns')
                   ]),
        Parameter('point_b',
                  [Parameter('x',95,float,'x-coordinate end in microns'),
                   Parameter('y', 95, float, 'y-coordinate end in microns')
                   ]),
        Parameter('z_pos', 50.0, float, 'z position of nanodrive; useful for z-axis sweeps to find NVs'),
        Parameter('resolution', 1, float, 'Resolution of each pixel in microns'),
        Parameter('time_per_pt', 5.0, float, 'Time in ms at each point to get counts'),
        Parameter('settle_time',0.2,float,'Time in seconds to allow NanoDrive to settle to correct position'),
        Parameter('ending_behavior', 'return_to_origin', ['return_to_inital_pos', 'return_to_origin', 'leave_at_corner'],'Nanodrive position after scan'),
        Parameter('3D_scan',# using experiment iterator to sweep z-position can give an effective 3D scan as successive images. Useful for finding where NVs are in focal plane
                  [Parameter('enable', False, bool, 'T/F to enable 3D scan'),
                   Parameter('folderpath', str(get_configured_confocal_scans_folder()), str,'folder location to save images at each z-value')]),
        # !!! If you see horizontial lines in the confocal image, the adwin arrays likely are corrupted. The fix is to reboot the adwin. You will nuke all
        # other process, variables, and arrays in the adwin. This parameter is added to make that easy to do in the GUI.
        Parameter('reboot_adwin', False, bool,'Will reboot adwin when experiment is executed. Useful is data looks fishy'),
        # clocks currently not implemented
        Parameter('laser_clock', 'Pixel', ['Pixel','Line','Frame','Aux'], 'Nanodrive clock used for turning laser on and off')
    ]

    #For actual experiment use LP100 [MCL_NanoDrive({'serial':2849})]. For testing using HS3 ['serial':2850]
    #_DEVICES = {'nanodrive': MCLNanoDrive(settings={'serial':2849}), 'adwin':AdwinGoldDevice()}  # Removed - devices now passed via constructor
    _DEVICES = {
        'nanodrive': 'nanodrive',
        'adwin': 'adwin'
    }
    _EXPERIMENTS = {}

    def __init__(self, devices, experiments=None, name=None, settings=None, log_function=None, data_path=None):
        """
        Initializes and connects to devices
        Args:
            name (optional): name of experiment, if empty same as class name
            settings (optional): settings for this experiment, if empty same as default settings
        """
        super().__init__(name, settings=settings, sub_experiments=experiments, devices=devices, log_function=log_function, data_path=data_path)
        #get instances of devices
        self.nd = self.devices['nanodrive']['instance']
        self.adw = self.devices['adwin']['instance']

    def setup_scan(self):
        '''
        Gets paths for adbasic file and loads them onto ADwin.
        '''
        self.adw.stop_process(1)
        sleep(0.1)
        self.adw.clear_process(1)
        
        # Use the helper function to find the binary file
        trial_counter_path = get_adwin_binary_path('Trial_Counter.TB1')
        self.adw.update({'process_1': {'load': str(trial_counter_path)}})
        #trial counter simply reads the counter value
        self.nd.clock_functions('Frame', reset=True)  # reset ALL clocks to default settings

        z_pos = self.settings['z_pos']
        if self.settings['z_pos'] < 0.0:
            z_pos = 0.0
        elif z_pos > 100.0:
            z_pos = 100.0
        self.nd.update({'z_pos': z_pos})

        # tracker to only save 3D image slice once
        self.data_collected = False

    def after_scan(self):
        '''
        Cleans up adwin and moves nanodrive to specified position
        '''
        # clearing process to aviod memory fragmentation when running different experiments in GUI
        self.adw.stop_process(1)    #neccesary if process is does not stop for some reason
        sleep(0.1)
        self.adw.clear_process(1)
        if self.settings['ending_behavior'] == 'return_to_inital_pos':
            self.nd.update({'x_pos': self.x_inital, 'y_pos': self.y_inital})
        elif self.settings['ending_behavior'] == 'return_to_origin':
            self.nd.update({'x_pos': 0.0, 'y_pos': 0.0})

    def _function(self):
        """
        This is the actual function that will be executed. It uses only information that is provided in the settings property
        will be overwritten in the __init__
        """
        if self.settings['reboot_adwin'] == True:
            self.adw.reboot_adwin()
        self.setup_scan()
        sleep(0.1)

        x_min = self.settings['point_a']['x']
        x_max = self.settings['point_b']['x']
        y_min = self.settings['point_a']['y']
        y_max = self.settings['point_b']['y']
        step = self.settings['resolution']
        #array form point_a x,y to point_b x,y with step of resolution
        x_array = np.arange(x_min, x_max+step, step)
        y_array = np.arange(y_min, y_max + step, step)
        reversed_y_array = y_array[::-1]

        self.x_inital = self.nd.read_probes('x_pos')
        self.y_inital = self.nd.read_probes('y_pos')
        self.z_inital = self.nd.read_probes('z_pos')
        self.settings['z_pos'] = self.z_inital

        #makes sure data is getting recorded. If still equal none after running experiment data is not being stored or not measured
        self.data['x_pos'] = None
        self.data['y_pos'] = None
        self.data['raw_counts'] = None
        self.data['counts'] = None
        self.data['count_img'] = None
        #local lists to store data and append to global self.data lists
        x_data = []
        y_data = []
        raw_counts_data = []
        count_rate_data = []

        Nx = len(x_array)
        Ny = len(y_array)
        self.data['count_img'] = np.zeros((Nx, Ny))

        interation_num = 0 #number to track progress
        total_interations = ((x_max - x_min)/step + 1)*((y_max - y_min)/step + 1)       #plus 1 because in total_iterations range is inclusive ie. [0,10]
        #print('total_interations=',total_interations)

        #formula to set adwin to count for correct time frame. The event section is run every delay*3.3ns so the counter increments for that time then is read and clear
        #time_per_pt is in millisecond and the adwin delay time is delay_value*3.3ns
        adwin_delay = round((self.settings['time_per_pt']*1e6) / (3.3))
        #print('adwin delay: ',adwin_delay)  606061 for 2ms and 606061*3.3 ns ~= 2 ms

        self.adw.update({'process_1': {'delay': adwin_delay, 'running': True}})
        # print(adwin_delay * 3.3 * 1e-9)
        # set inital x and y and set nanodrive stage to that position
        self.nd.update({'x_pos': x_min, 'y_pos': y_min})
        sleep(0.1)  # time for stage to move and adwin process to initilize

        forward = True #used to rasterize more efficently going forward then back
        for i, x in enumerate(x_array):
            if self._abort:  # halts loop (and experiment) if stop button is pressed
                break #need to put break in x for loop which takes some time to stop but if stopped in y loop array sizes may mismatch and require a GUI restart
            x = float(x)
            img_row = []  #used for tracking image rows and adding to count_img; list not saved
            self.nd.update({'x_pos':x})

            if forward == True:
                for y in y_array:
                    y = float(y)
                    print(x,y)
                    self.nd.update({'y_pos':y})
                    sleep(self.settings['settle_time'])

                    x_pos = self.nd.read_probes('x_pos')
                    x_data.append(x_pos)
                    self.data['x_pos'] = x_data  # adds x postion to data
                    y_pos = self.nd.read_probes('y_pos')
                    y_data.append(y_pos)
                    self.data['y_pos'] = y_data  # adds y postion to data

                    raw_counts = self.adw.read_probes('int_var',id=1)   #raw number of counter triggers
                    count_rate = raw_counts*1e3 / self.settings['time_per_pt'] # in units of counts/second

                    img_row.append(count_rate)
                    raw_counts_data.append(raw_counts)
                    count_rate_data.append(count_rate)
                    self.data['raw_counts'] = raw_counts_data
                    self.data['counts'] = count_rate_data

            else:
                for y in reversed_y_array:
                    y = float(y)
                    print(x,y)
                    self.nd.update({'y_pos':y})
                    sleep(self.settings['settle_time'])

                    x_pos = self.nd.read_probes('x_pos')
                    x_data.append(x_pos)
                    self.data['x_pos'] = x_data  # adds x postion to data
                    y_pos = self.nd.read_probes('y_pos')
                    y_data.append(y_pos)
                    self.data['y_pos'] = y_data  # adds y postion to data

                    raw_counts = self.adw.read_probes('int_var', id=1)  # raw number of counter triggers
                    count_rate = raw_counts*1e3 / self.settings['time_per_pt'] # in units of counts/second

                    img_row.append(count_rate)
                    raw_counts_data.append(raw_counts)
                    count_rate_data.append(count_rate)
                    self.data['raw_counts'] = raw_counts_data
                    self.data['counts'] = count_rate_data
                img_row.reverse() #reversed since going from y_max --> y_min

            self.data['count_img'][i, :] = img_row
            forward = not forward

            interation_num = interation_num + len(y_array)
            self.progress = 100. * (interation_num + 1) / total_interations
            self.updateProgress.emit(self.progress)

        # tracker to only save test image once
        self.data_collected = True

        print('Data collected')
        self.data['x_pos'] = x_data
        self.data['y_pos'] = y_data
        self.data['raw_counts'] = raw_counts_data
        self.data['counts'] = count_rate_data

        #print('Position Data: ', '\n', self.data['x_pos'], '\n', self.data['y_pos'], '\n', 'Max x: ',np.max(self.data['x_pos']), 'Max y: ', np.max(self.data['y_pos']))
        #print('All data: ',self.data)

        self.adw.update({'process_2': {'running': False}})
        self.after_scan()

    def _plot(self, axes_list, data=None):
        '''
        This function plots the data. It is triggered when the updateProgress signal is emited and when after the _function is executed.
        For the scan, image can only be plotted once all data is gathered so self.running prevents a plotting call for the updateProgress signal.
        '''
        def create_img(add_colobar=True):
            '''
            Creates a new image and ImageItem. Optionally create colorbar
            '''
            axes_list[0].clear()
            self.slow_count_image = pg.ImageItem(data['count_img'], interpolation='nearest')
            self.slow_count_image.setLevels(levels)
            self.slow_count_image.setRect(pg.QtCore.QRectF(extent[0], extent[2], extent[1] - extent[0], extent[3] - extent[2]))
            axes_list[0].addItem(self.slow_count_image)

            axes_list[0].setAspectLocked(True)
            axes_list[0].setLabel('left', 'y (µm)')
            axes_list[0].setLabel('bottom', 'x (µm)')
            axes_list[0].setTitle(f"Confocal Scan with z = {self.z_inital:.2f}")

            if add_colobar:
                self.colorbar = pg.ColorBarItem(values=(levels[0], levels[1]), label='counts/sec', colorMap='viridis')
                # layout is housing the PlotItem that houses the ImageItem. Add colorbar to layout so it is properly saved when saving dataset
                layout = axes_list[0].parentItem()
                layout.addItem(self.colorbar)
            self.colorbar.setImageItem(self.slow_count_image)

        if data is None:
            data = self.data
        if data is not None or data is not {}:

            # for colorbar to display graident without artificial zeros
            non_zero_values = data['count_img'][data['count_img'] > 0]
            if non_zero_values.size > 0:
                min = np.min(non_zero_values)
            else:  # if else to aviod ValueError
                min = 0

            levels = [min, np.max(data['count_img'])]
            extent = [self.settings['point_a']['x'], self.settings['point_b']['x'], self.settings['point_a']['y'],self.settings['point_b']['y']]
            # extent = [np.min(data['x_pos']), np.max(data['x_pos']), np.min(data['y_pos']), np.max(data['y_pos'])]

            if self._plot_refresh == True:
                # if plot refresh is true the ImageItem has been deleted and needs recreated
                create_img()
            else:
                try:
                    self.slow_count_image.setImage(data['count_img'], autoLevels=False)
                    self.slow_count_image.setLevels(levels)
                    self.colorbar.setLevels(levels)

                    if self.settings['3D_scan']['enable'] and self.data_collected:
                        print('z =', self.z_inital, 'max counts =', levels[1])
                        axes_list[0].setTitle(f"Confocal Scan with z = {self.z_inital:.2f}")
                        scene = axes_list[0].scene()
                        exporter = ImageExporter(scene)
                        
                        # Use pathlib for cross-platform path handling
                        folder_path = Path(self.settings['3D_scan']['folderpath'])
                        try:
                            folder_path.mkdir(parents=True, exist_ok=True)  # Create directory if it doesn't exist
                            filename = folder_path / f'confocal_scan_z_{self.z_inital:.2f}.png'
                            exporter.export(str(filename))
                            print(f"Saved 3D scan image to: {filename}")
                        except Exception as e:
                            print(f"Warning: Failed to save 3D scan image: {e}")
                            print(f"Attempted to save to: {folder_path}")

                except RuntimeError:
                    # sometimes when clicking other experiments ImageItem is deleted but _plot_refresh is false. This ensures the image can be replotted
                    create_img(add_colobar=False)

    def _update(self,axes_list):
        self.slow_count_image.setImage(self.data['count_img'], autoLevels=False)
        self.slow_count_image.setLevels([np.min(self.data['count_img']),np.max(self.data['count_img'])])
        self.colorbar.setLevels([np.min(self.data['count_img']),np.max(self.data['count_img'])]) 