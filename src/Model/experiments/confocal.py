'''
This file has the experiment classes relevant to prefroming a scan with the confocal microscope. So far this includes:

- Confocal Scan Fast for larger images
- Confocal Scan Slow: a slow method that ensures image is accurate
- Confocal Point: Gets counts 1 point one time or continuously
'''

import numpy as np
from pyqtgraph.exporters import ImageExporter

from src.Controller import MCLNanoDrive, ADwinGold
from src.core import Parameter, Experiment
import os
from time import sleep
import pyqtgraph as pg

class ConfocalScan_Fast(Experiment):
    '''
    This class runs a confocal microscope scan using the MCL NanoDrive to move the sample stage and the ADwin Gold II to get count data.
    The code loads a waveform on the nanodrive, starts the Adwin process, triggers a waveform aquisition, then reads the count data array from the Adwin.

    To get accurate counts, the loaded waveforms are extended to compensate for 'warm up' and 'cool down' movements. The data arrays are then
    manipulated to get the counts for the inputed region.
    '''

    _DEFAULT_SETTINGS = [
        Parameter('point_a',
                  [Parameter('x',5.0,float,'x-coordinate start in microns'),
                   Parameter('y',5.0,float,'y-coordinate start in microns')
                   ]),
        Parameter('point_b',
                  [Parameter('x',95.0,float,'x-coordinate end in microns'),
                   Parameter('y', 95.0, float, 'y-coordinate end in microns')
                   ]),
        Parameter('z_pos',50.0,float,'z position of nanodrive; useful for z-axis sweeps to find NVs'),
        Parameter('resolution', 1.0, [2.0,1.0,0.5,0.25,0.1,0.05,0.025,0.001], 'Resolution of each pixel in microns. Limited to give '),
        Parameter('time_per_pt', 2.0, [2.0,5.0], 'Time in ms at each point to get counts; same as load_rate for nanodrive. Wroking values 2 or 5 ms'),
        Parameter('ending_behavior', 'return_to_origin', ['return_to_inital_pos', 'return_to_origin', 'leave_at_corner'],'Nanodrive position after scan'),
        Parameter('3D_scan',#using experiment iterator to sweep z-position can give an effective 3D scan as successive images. Useful for finding where NVs are in focal plane
                  [Parameter('enable',False,bool,'T/F to enable 3D scan'),
                         Parameter('folderpath','D:\Data\dylan_staples\image_NV_confocal_scans',str,'folder location to save images at each z-value')]),
        #!!! If you see horizontial lines in the confocal image, the adwin arrays likely are corrupted. The fix is to reboot the adwin. You will nuke all
        #other process, variables, and arrays in the adwin. This parameter is added to make that easy to do in the GUI.
        Parameter('reboot_adwin',False,bool,'Will reboot adwin when experiment is executed. Useful is data looks fishy'),
        Parameter('cropping', #nested cause it does not need changed often
                  [Parameter('crop_data',True,bool,'Current logic scans over a larger area then crops data to requested size. Added for ease of seeing full image')]),
        #clocks currently not implemented
        Parameter('laser_clock', 'Pixel', ['Pixel','Line','Frame','Aux'], 'Nanodrive clocked used for turning laser on and off')
    ]

    #For actual experiment use LP100 [MCL_NanoDrive({'serial':2849})]. For testing using HS3 ['serial':2850]
    _DEVICES = {'nanodrive': MCLNanoDrive(settings={'serial':2849}), 'adwin':ADwinGold()}
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
        self.adw.stop_process(2)
        sleep(0.1)
        self.adw.clear_process(2)
        one_d_scan_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'Controller','binary_files', 'ADbasic', 'One_D_Scan.TB2')
        one_d_scan = os.path.normpath(one_d_scan_path)
        self.adw.update({'process_2': {'load': one_d_scan}})
        # one_d_scan script increments an index then adds count values to an array in a constant time interval
        self.nd.clock_functions('Frame', reset=True)  # reset ALL clocks to default settings

        z_pos = self.settings['z_pos']
        #maz range is 0 to 100
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
        self.adw.stop_process(2)    #neccesary if process is does not stop for some reason
        sleep(0.1)
        self.adw.clear_process(2)
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

        #y scanning range is 5 to 95 to compensate for warm up time
        x_min = max(self.settings['point_a']['x'], 0.0)
        y_min = max(self.settings['point_a']['y'], 5.0)
        x_max = min(self.settings['point_b']['x'], 100.0)
        y_max = min(self.settings['point_b']['y'], 95.0)

        step = self.settings['resolution']
        num_points = (y_max - y_min) / step + 1
        print('num_points',num_points)
        if num_points < 91:
            new_step = self.correct_step(step)
            self.log(f'Works best with minimum 91 pixel resolution in y-direction. You are getting a free resolution upgrade to {new_step} um!')

        #array form point_a x,y to point_b x,y with step of resolution
        x_array = np.arange(x_min, x_max + step, step)
        y_array = np.arange(y_min, y_max+step, step)

        #adds point 5 um before and after
        y_before = np.arange(y_min-5.0,y_min,step)
        y_after = np.arange(y_max + step, y_max + 5.0 + step, step)
        y_array_adj = np.insert(y_array, 0, y_before)
        y_array_adj = np.append(y_array_adj, y_after)

        self.x_inital = self.nd.read_probes('x_pos')
        self.y_inital = self.nd.read_probes('y_pos')
        self.z_inital = self.nd.read_probes('z_pos')

        #makes sure data is getting recorded. If still equal none after running experiment data is not being stored or not measured
        self.data['x_pos'] = None
        self.data['y_pos'] = None
        self.data['raw_counts'] = None
        self.data['count_rate'] = None
        self.data['count_img'] = None
        self.data['raw_img'] = None
        #local lists to store data and append to global self.data lists
        x_data = []
        y_data = []
        raw_count_data = []
        count_rate_data = []
        index_list = []

        # set data to zero and update to plot while experiment runs
        Nx = len(x_array)
        Ny = len(y_array)
        self.data['count_img'] = np.zeros((Nx, Ny))
        self.data['raw_img'] = np.zeros((Nx, len(y_array_adj)+20))

        interation_num = 0 #number to track progress
        total_interations = ((x_max - x_min)/step + 1)*((y_max - y_min)/step + 1)       #plus 1 because in total_iterations because range is inclusive ie. [0,10]
        #print('total_interations=',total_interations)

        #formula to set adwin to count for correct time frame. The event section is run every delay*3.3ns so the counter increments for that time then is read and clear
        #time_per_pt is in millisecond and the adwin delay time is delay_value*3.3ns
        adwin_delay = round((self.settings['time_per_pt']*1e6) / (3.3))
        #print('adwin delay: ',delay)

        wf = list(y_array_adj)
        len_wf = len(y_array_adj)
        #print(len_wf,wf)
        load_read_ratio = self.settings['time_per_pt']/2.0 #used for scaling when rates are different
        num_points_read = int(load_read_ratio*len_wf + 20) #20 is added to compensate for start warm up producing ~15 points of unwanted values

        #set inital x and y and set nanodrive stage to that position
        self.nd.update({'x_pos':x_min,'y_pos':y_min-5.0,'num_datapoints':len_wf,'read_rate':2.0,'load_rate':self.settings['time_per_pt']})
        #load_rate is time_per_pt; 2.0ms = 5000Hz
        self.adw.update({'process_2':{'delay':adwin_delay}})
        sleep(0.1)  #time for stage to move to starting posiition and adwin process to initilize


        for i, x in enumerate(x_array):
            if self._abort == True:
                break
            img_row = []
            raw_img_row = []
            x = float(x)

            self.nd.update({'x_pos':x,'y_pos':y_min-5.0})     #goes to x position
            sleep(0.1)
            x_pos = self.nd.read_probes('x_pos')
            x_data.append(x_pos)
            self.data['x_pos'] = x_data     #adds x postion to data

            #The two different code lines to start counting seem to work for cropping. Honestly cant give a precise explaination, it seems to be related to
            #hardware delay. If the time_per_pt is 5.0 starting counting before waveform set up works to within 1 pixel with numpy cropping. If the
            #time_per_pt is 2.0 starting counting after waveform set up matches slow scan to a pixel. Sorry for a lack of explaination but this just seems to work.
            #See data/dylan_staples/confocal_scans_w_resolution_target for images and additional details
            if self.settings['time_per_pt'] == 5.0:
                self.adw.update({'process_2': {'running': True}})

            #trigger waveform on y-axis and record position data
            self.nd.setup(settings={'num_datapoints': len_wf, 'load_waveform': wf}, axis='y')
            self.nd.setup(settings={'num_datapoints': num_points_read, 'read_waveform': self.nd.empty_waveform},axis='y')

            #restricted load_rate and read_rate to ensure cropping works. 2ms and 5ms count times are good as smaller window for speed and a larger window if more counts are needed
            if  self.settings['time_per_pt'] == 2.0:
                self.adw.update({'process_2': {'running': True}})

            y_pos = self.nd.waveform_acquisition(axis='y')
            sleep(self.settings['time_per_pt']*len_wf/1000)

            #want to get data only in desired range not range±5um
            y_pos_array = np.array(y_pos)
            # index for the points of the read array when at y_min and y_max. Scale step by load_read_ratio to get points closest to y_min & y_max
            lower_index = np.where((y_pos_array > y_min - step / load_read_ratio) & (y_pos_array < y_min + step / load_read_ratio))[0]
            upper_index = np.where((y_pos_array > y_max - step / load_read_ratio) & (y_pos_array < y_max + step / load_read_ratio))[0]
            y_pos_cropped = list(y_pos_array[lower_index[0]:upper_index[0]])

            #y_data.extend(y_pos_cropped)
            y_data.extend(list(y_pos))
            self.data['y_pos'] = y_data
            self.adw.update({'process_2':{'running':False}})

            #different index for count data if read and load rates are different
            counts_lower_index = int(lower_index[0] / load_read_ratio)
            counts_upper_index = int(upper_index[-1] / load_read_ratio)
            index_list.append(counts_upper_index)

            #get mode of index list and difference between mode and previous value
            index_mode = max(set(index_list), key=index_list.count)
            index_diff = abs(counts_upper_index - index_mode)
            # index starts at 0 so need to add 1 if there is an index difference
            if index_diff > 0:
                index_diff = index_diff + 1

            # get count data from adwin and record it
            raw_counts = np.array(list(self.adw.read_probes('int_array', id=1, length=len_wf+20)))
            # units of count/seconds
            count_rate = list(np.array(raw_counts) * 1e3 / self.settings['time_per_pt'])

            crop_index = -index_mode - 1 - index_diff
            if self.settings['time_per_pt'] == 5.0:
                crop_index = crop_index-2
            cropped_raw_counts = list(raw_counts[crop_index::crop_index + len(y_array)])
            cropped_count_rate = count_rate[crop_index:crop_index + len(y_array)]

            raw_count_data.extend(cropped_raw_counts)
            self.data['raw_counts'] = raw_count_data

            count_rate_data.extend(cropped_count_rate)
            self.data['count_rate'] = count_rate_data

            #adds count rate data to raw img and cropped count img
            raw_img_row.extend(count_rate)
            self.data['raw_img'][i, :] = raw_img_row
            img_row.extend(cropped_count_rate)
            self.data['count_img'][i, :] = img_row  # add previous scan data so image plots

            # updates process bar and plots count_img so far
            interation_num = interation_num + len(y_array)
            self.progress = 100. * (interation_num +1) / total_interations
            self.updateProgress.emit(self.progress)

        #tracker to only save test image once
        self.data_collected = True

        print('Data collected')
        self.data['x_pos'] = x_data
        self.data['y_pos'] = y_data
        self.data['raw_counts'] = raw_count_data
        self.data['count_rate'] = count_rate_data
        #print('Position Data: ','\n',self.data['x_pos'],'\n',self.data['y_pos'],'\n','Max x: ',np.max(self.data['x_pos']),'Max y: ',np.max(self.data['y_pos']))
        #print('Counts: ','\n',self.count_data)
        #print('All data: ',self.data)

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
            self.count_image = pg.ImageItem(data['count_img'], interpolation='nearest')
            self.count_image.setLevels(levels)
            self.count_image.setRect(pg.QtCore.QRectF(extent[0], extent[2], extent[1] - extent[0], extent[3] - extent[2]))
            axes_list[0].addItem(self.count_image)

            axes_list[0].setAspectLocked(True)
            axes_list[0].setLabel('left', 'y (µm)')
            axes_list[0].setLabel('bottom', 'x (µm)')
            axes_list[0].setTitle(f"Confocal Scan with z = {self.z_inital:.2f}")

            if add_colobar:
                self.colorbar = pg.ColorBarItem(values=(levels[0], levels[1]), label='counts/sec', colorMap='viridis')
                # layout is housing the PlotItem that houses the ImageItem. Add colorbar to layout so it is properly saved when saving dataset
                layout = axes_list[0].parentItem()
                layout.addItem(self.colorbar)
            self.colorbar.setImageItem(self.count_image)

        if data is None:
            data = self.data
        if data is not None or data is not {}:

            #for colorbar to display graident without artificial zeros
            non_zero_values = data['count_img'][data['count_img'] > 0]
            if non_zero_values.size > 0:
                min = np.min(non_zero_values)
            else: #if else to aviod ValueError
                min = 0

            levels = [min, np.max(data['count_img'])]
            extent = [self.settings['point_a']['x'], self.settings['point_b']['x'], self.settings['point_a']['y'],self.settings['point_b']['y']]

            if self._plot_refresh == True:
                # if plot refresh is true the ImageItem has been deleted and needs recreated
                create_img()
            else:
                try:
                    self.count_image.setImage(data['count_img'], autoLevels=False)
                    self.count_image.setLevels(levels)
                    self.colorbar.setLevels(levels)

                    if self.settings['3D_scan']['enable'] and self.data_collected:
                        print('z =', self.z_inital, 'max counts =', levels[1])
                        axes_list[0].setTitle(f"Confocal Scan with z = {self.z_inital:.2f}")
                        scene = axes_list[0].scene()
                        exporter = ImageExporter(scene)
                        filename = os.path.join(self.settings['3D_scan']['folderpath'], f'confocal_scan_z_{self.z_inital:.2f}.png')
                        exporter.export(filename)

                except RuntimeError:
                    # sometimes when clicking other experiments ImageItem is deleted but _plot_refresh is false. This ensures the image can be replotted
                    create_img(add_colobar=False)

    def _update(self,axes_list):
        self.count_image.setImage(self.data['count_img'], autoLevels=False)
        self.count_image.setLevels([np.min(self.data['count_img']), np.max(self.data['count_img'])])
        self.colorbar.setLevels([np.min(self.data['count_img']), np.max(self.data['count_img'])])

    def correct_step(self, old_step):
        '''
        Increases resolution by one threshold if the step size does not give enough points for a good y-array.
        For good y-array len() > 90
         '''
        if old_step == 1.0:
            return 0.5
        elif old_step > 1.0:
            return 1.0
        elif old_step == 0.5:
            return 0.25
        elif old_step == 0.25:
            return 0.1
        elif old_step == 0.1:
            return 0.05
        elif old_step == 0.05:
            return 0.025
        elif old_step == 0.025:
            return 0.001
        else:
            raise KeyError



class ConfocalScan_Slow(Experiment):
    '''
    This class runs a confocal microscope scan using the MCL NanoDrive to move the sample stage and the ADwin Gold II to get count data.
    The slow method goes point by point to ensure the scan is precise and accurate at the cost of execution time
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
                   Parameter('folderpath', 'D:\Data\dylan_staples\image_NV_confocal_scans', str,'folder location to save images at each z-value')]),
        # !!! If you see horizontial lines in the confocal image, the adwin arrays likely are corrupted. The fix is to reboot the adwin. You will nuke all
        # other process, variables, and arrays in the adwin. This parameter is added to make that easy to do in the GUI.
        Parameter('reboot_adwin', False, bool,'Will reboot adwin when experiment is executed. Useful is data looks fishy'),
        # clocks currently not implemented
        Parameter('laser_clock', 'Pixel', ['Pixel','Line','Frame','Aux'], 'Nanodrive clock used for turning laser on and off')
    ]

    #For actual experiment use LP100 [MCL_NanoDrive({'serial':2849})]. For testing using HS3 ['serial':2850]
    _DEVICES = {'nanodrive': MCLNanoDrive(settings={'serial':2849}), 'adwin':ADwinGold()}
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
        trial_counter_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'Controller','binary_files', 'ADbasic', 'Trial_Counter.TB1')
        trial_counter = os.path.normpath(trial_counter_path)
        self.adw.update({'process_1': {'load': trial_counter}})
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

        #makes sure data is getting recorded. If still equal none after running experiment data is not being stored or measured
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
                        filename = os.path.join(self.settings['3D_scan']['folderpath'], f'confocal_scan_z_{self.z_inital:.2f}.png')
                        exporter.export(filename)

                except RuntimeError:
                    # sometimes when clicking other experiments ImageItem is deleted but _plot_refresh is false. This ensures the image can be replotted
                    create_img(add_colobar=False)

    def _update(self,axes_list):
        self.slow_count_image.setImage(self.data['count_img'], autoLevels=False)
        self.slow_count_image.setLevels([np.min(self.data['count_img']),np.max(self.data['count_img'])])
        self.colorbar.setLevels([np.min(self.data['count_img']),np.max(self.data['count_img'])])



class Confocal_Point(Experiment):
    '''
    This class implements a confocal microscope to get the counts at a single point. It uses the MCL NanoDrive to move the sample stage and the ADwin Gold to get count data.
    The 'continuous' parameter if false will return 1 data point. If true it offers live counting that continues until the stop button is clicked.
    '''

    _DEFAULT_SETTINGS = [
        Parameter('point',
                  [Parameter('x',0.0,float,'x-coordinate in microns'),
                   Parameter('y',0.0,float,'y-coordinate in microns'),
                   Parameter('z',0.0,float,'z-coordinate in microns')
                   ]),
        Parameter('count_time', 2.0, float, 'Time in ms at  point to get count data'),
        Parameter('num_cycles', 10, int, 'Number of samples to average; set as Par_10 in adbasic scirpt'),
        Parameter('plot_avg', True, bool, 'T/F to plot average count data'),
        Parameter('continuous', True, bool,'If experiment should return 1 value or continuously plot for optics optimization'),
        Parameter('graph_params',
                  [Parameter('plot_raw_counts', False, bool,'Sometimes counts/sec is rounded to zero. Check this to plot raw counts'),
                   Parameter('refresh_rate', 0.1, float,'For continuous counting this is the refresh rate of the graph in seconds (= 1/frames per second)'),
                   Parameter('length_data',500,int,'After so many data points matplotlib freezes GUI. Data dic will be cleared after this many entries'),
                   Parameter('font_size',32,int,'font size to make it easier to see on the fly if needed'),
                   ]),
        # clocks currently not implemented
        Parameter('laser_clock', 'Pixel', ['Pixel', 'Line', 'Frame', 'Aux'],'Nanodrive clocked used for turning laser on and off'),
    ]

    #For actual experiment use LP100 [MCL_NanoDrive({'serial':2849})]. For testing cautiously using HS3 ['serial':2850]
    _DEVICES = {'nanodrive': MCLNanoDrive(settings={'serial':2849}), 'adwin':ADwinGold()}
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


    def setup(self):
        '''
        Gets paths for adbasic file and loads them onto ADwin.
        '''
        self.adw.stop_process(1)
        sleep(0.1)
        self.adw.clear_process(1)
        trial_counter_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'Controller','binary_files', 'ADbasic', 'Averagable_Trial_Counter.TB1')
        trial_counter = os.path.normpath(trial_counter_path)
        self.adw.update({'process_1': {'load': trial_counter}})
        self.nd.clock_functions('Frame', reset=True)  # reset ALL clocks to default settings

    def cleanup(self):
        '''
        Cleans up adwin after experiment
        '''
        self.adw.stop_process(1)
        sleep(0.1)
        self.adw.clear_process(1)

    def _function(self):
        """
        This is the actual function that will be executed. It uses only information that is provided in the settings property
        will be overwritten in the __init__
        """
        self.setup()

        self.data['counts'] = None
        self.data['raw_counts'] = None
        # set to zero initially for smoother plotting
        count_rate_data = [0] * self.settings['graph_params']['length_data']
        raw_counts_data = [0] * self.settings['graph_params']['length_data']

        x = self.settings['point']['x']
        y = self.settings['point']['y']
        z = self.settings['point']['z']

        num_cycles = self.settings['num_cycles']
        self.adw.set_int_var(10,num_cycles)
        #set adwin delay which determines the counting time
        adwin_delay = round((self.settings['count_time']*1e6) / (3.3))
        self.adw.update({'process_1':{'delay':adwin_delay,'running':True}})
        self.nd.update({'x_pos':x,'y_pos':y,'z_pos':z})
        sleep(0.1)  #time for stage to move and adwin process to initilize

        if self.settings['continuous'] == False:
            if self.settings['plot_avg']:
                counting_time = self.settings['count_time']*self.settings['num_cycles']
            else:
                counting_time = self.settings['count_time']
            sleep((counting_time*1.5)/1000)    #sleep for 1.5 times the count time to ensure enough time for counts. Does not affect counting window

            if self.settings['plot_avg']:
                raw_counts = self.adw.read_probes('int_var', id=5) / self.settings['num_cycles']  # Par_5 stores the total counts over 'num_cycles'
                counts = raw_counts * 1e3 / self.settings['count_time']
            else:
                raw_counts = self.adw.read_probes('int_var', id=1)  # read variable from adwin
                counts = raw_counts * 1e3 / self.settings['count_time']

            for i in range(0,2):        #just want the single value to be viewable so will plot a straight line (with 2 points) of its value
                raw_counts_data.append(raw_counts)
                count_rate_data.append(counts)
            self.data['raw_counts'] = raw_counts_data
            self.data['counts'] = count_rate_data

        elif self.settings['continuous'] == True:
            while self._abort == False:     #self._abort is defined in experiment.py and is true false while running and set false when stop button is hit
                sleep(self.settings['graph_params']['refresh_rate'])    #effictivly this sleep is the time interval the graph is refreshed (1/fps) counting window

                if self.settings['plot_avg']:
                    raw_counts = self.adw.read_probes('int_var',id=5) / self.settings['num_cycles'] #Par_5 stores the total counts over 'num_cycles'
                    counts = raw_counts * 1e3 / self.settings['count_time']
                else:
                    raw_counts = self.adw.read_probes('int_var', id=1)  # read variable from adwin
                    counts = raw_counts * 1e3 / self.settings['count_time']

                #append most recent value and remove oldest value
                raw_counts_data.append(raw_counts)
                raw_counts_data.pop(0)
                count_rate_data.append(counts)
                count_rate_data.pop(0)
                self.data['raw_counts'] = raw_counts_data
                self.data['counts'] = count_rate_data
                #print('Current count rate', self.data['counts'][-1])

                self.progress = 50   #this is a infinite loop till stop button is hit; progress & updateProgress is only here to update plot
                self.updateProgress.emit(self.progress)     #calling updateProgress.emit triggers _plot

        self.adw.update({'process_1': {'running': False}})
        self.cleanup()

    def _plot(self, axes_list, data=None):
        '''
        This function plots the data. It is triggered when the updateProgress signal is emited and when after the _function is executed.
        '''
        if data is None:
            data = self.data
        if data is not None and data is not {}:

            if self.settings['graph_params']['plot_raw_counts'] == True:
                # sometimes counts are so low it rounds to zero. Plotting raw counts can be useful
                plot_counts = self.data['raw_counts']
                axes_label = 'counts'
            else:
                plot_counts = self.data['counts']
                axes_label = 'counts/sec'

            axes_list[0].clear()
            axes_list[0].plot(plot_counts)
            axes_list[0].showGrid(x=True, y=True)
            axes_list[0].setLabel('left', axes_label)
            x_ax_length = int(self.settings['graph_params']['length_data']*1.1)
            axes_list[0].setXRange(0, x_ax_length)

            axes_list[1].setText(f'{plot_counts[-1]/1000:.3f} k{axes_label}')

            # todo: Might be useful to include a max count number display

    def get_axes_layout(self, figure_list):
        """
        Overwrites default get_axes_layout. Adds a plot to bottom graph and label that displays a number to top graph.
        Args:
            figure_list: a list of bottom and top PyQtgraphWidget objects
        Returns:
            axes_list: a list of item objects
            axes_list = [<Plot item>,<Label item>]
        """
        axes_list = []
        if self._plot_refresh is True:
            for graph in figure_list:
                graph.clear()
            axes_list.append(figure_list[0].addPlot(row=0,col=0))

            label = pg.LabelItem(text='',size=f'{self.settings["graph_params"]["font_size"]}pt',bold=True)
            figure_list[1].addItem(label, row=0,col=0)
            axes_list.append(label)
        else:
            for graph in figure_list:
                axes_list.append(graph.getItem(row=0,col=0))

        return axes_list

    def _update(self, axes_list):
        Experiment._update(self, axes_list)