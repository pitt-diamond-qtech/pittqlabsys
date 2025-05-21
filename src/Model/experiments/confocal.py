'''
This file has the experiment classes relevant to using a confocal microscope. So far this includes:

- Confocal Scan (old method) for larger images
- Confocal Point: Gets counts 1 point continuously or once
- Confocal Point-by-Point: a slow method that ensures image is accurate

'''

import numpy as np
from PyQt5.QtCore import QSettings

from src.Controller import MCLNanoDrive, ADwinGold
from src.core import Parameter, Experiment
import os
from time import sleep
import pyqtgraph as pg


class ConfocalScan_NewFast(Experiment):
    '''
    This class runs a confocal microscope scan using the MCL NanoDrive to move the sample stage and the ADwin Gold II to get count data.
    The code loads a waveform on the nanodrive, starts the Adwin process, triggers a waveform aquisition, then reads the data array from the Adwin.

    To get accurate counts, the loaded waveforms are extended to compensate for 'warm up' and 'cool down' movements. The data arrays are then
    manipulated to get the counts for the inputed region.
    '''

    _DEFAULT_SETTINGS = [
        Parameter('point_a',
                  [Parameter('x',35.0,float,'x-coordinate start in microns'),
                   Parameter('y',35.0,float,'y-coordinate start in microns')
                   ]),
        Parameter('point_b',
                  [Parameter('x',95.0,float,'x-coordinate end in microns'),
                   Parameter('y', 95.0, float, 'y-coordinate end in microns')
                   ]),
        Parameter('resolution', 1.0, float, 'Resolution of each pixel in microns'),
        Parameter('time_per_pt', 5.0, [2.0,5.0], 'Time in ms at each point to get counts; same as load_rate for nanodrive. Wroking values 2 or 5 ms'),
        Parameter('read_rate',2.0,[2.0],'Time in ms. Same as read_rate for nanodrive'),
        Parameter('return_to_start',True,bool,'If true will return to position of stage before scan started'),
        #!!! If you see horizontial lines in the confocal image, the adwin arrays likely are corrupted. The fix is to reboot the adwin. You will nuke all
        #other process, variables, and arrays in the adwin. This parameter is added to make that easy to do in the GUI.
        Parameter('reboot_adwin',False,bool,'Will reboot adwin when experiment is executed. Useful is data looks fishy'),
        #clocks currently not implemented
        Parameter('correlate_clock', 'Aux', ['Pixel','Line','Frame','Aux'], 'Nanodrive clocked used for correlating points with counts (Connected to Digital Input 1 on Adwin)'),
        Parameter('laser_clock', 'Pixel', ['Pixel','Line','Frame','Aux'], 'Nanodrive clocked used for turning laser on and off'),
        Parameter('crop_options',
                  [Parameter('crop',False,bool,'Flag to crop image or not in GUI'),
                  Parameter('pixels',20,int,'number of pixels to crop'),
                  Parameter('display_crop',True,bool,'if image is not cropped, can display cropped region'),
                  Parameter('numpy_crop',True,bool,'Use np.where to crop'),
                  Parameter('numpy_flip',True,bool,'Flip index of numpy crop'),
                  Parameter('numpy_type','upper',['lower','upper'],'Use lower or upper index to crop'),
                  Parameter('index_mode',True,bool,'Use mode of index to crop')
                  ])
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

    def _function(self):
        """
        This is the actual function that will be executed. It uses only information that is provided in the settings property
        will be overwritten in the __init__
        """
        if self.settings['reboot_adwin'] == True:
            self.adw.reboot_adwin()
        self.setup_scan()

        #scanning range is 5 to 95 to compinsate for warm up time
        x_min = max(self.settings['point_a']['x'], 5.0)
        y_min = max(self.settings['point_a']['y'], 5.0)
        x_max = min(self.settings['point_b']['x'], 95.0)
        y_max = min(self.settings['point_b']['y'], 95.0)

        step = self.settings['resolution']
        #array form point_a x,y to point_b x,y with step of resolution
        x_array = np.arange(x_min, x_max + step, step)
        y_array = np.arange(y_min, y_max+step, step)

        #adds point 5 um before and after
        y_before = np.arange(y_min-5.0,y_min,step)
        y_after = np.arange(y_max + step, y_max + 5.0 + step, step)
        y_array_adj = np.insert(y_array, 0, y_before)
        y_array_adj = np.append(y_array_adj, y_after)

        x_inital = self.nd.read_probes('x_pos')
        y_inital = self.nd.read_probes('y_pos')

        #makes sure data is getting recorded. If still equal none after running experiment data is not being stored or not measured
        self.data['x_pos'] = None
        self.data['y_pos'] = None
        self.data['raw_counts'] = None
        self.data['counts'] = None
        self.data['count_img'] = None
        #local lists to store data and append to global self.data lists
        x_data = []
        y_data = []
        raw_count_data = []
        count_rate_data = []
        index_list = []

        # set data to zero so plotting happens while experiment runs
        Nx = len(x_array)

        if self.settings['crop_options']['crop'] == True:
            Ny = len(y_array)
            self.data['count_img'] = np.zeros((Nx, Ny))
        elif self.settings['crop_options']['crop'] == False:
            Ny = len(y_array_adj)
            self.data['count_img'] = np.zeros((Nx, Ny+self.settings['crop_options']['pixels']))

        full_image = np.zeros((Nx, len(y_array_adj)+self.settings['crop_options']['pixels']))

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
        load_read_ratio = self.settings['time_per_pt']/self.settings['read_rate'] #used for scaling when rates are different
        num_points_read = int(load_read_ratio*len_wf + self.settings['crop_options']['pixels']) #50 is added to compensate for start and end lack each producing ~15 points of unwanted values

        #set inital x and y and set nanodrive stage to that position
        self.nd.update({'x_pos':x_min,'y_pos':y_min-5.0,'num_datapoints':len_wf,'read_rate':self.settings['read_rate'],'load_rate':self.settings['time_per_pt']})
        #load_rate is time_per_pt; 2.0ms = 5000Hz
        self.adw.update({'process_2':{'delay':adwin_delay}})
        sleep(0.1)  #time for stage to move to starting posiition and adwin process to initilize


        for i, x in enumerate(x_array):
            if self._abort == True:
                break
            img_row = []
            x = float(x)

            self.nd.update({'x_pos':x,'y_pos':y_min-5.0})     #goes to x position
            sleep(0.1)
            x_pos = self.nd.read_probes('x_pos')
            x_data.append(x_pos)
            self.data['x_pos'] = x_data     #adds x postion to data


            #The two different code lines to start counting seem to work for cropping. Honestly cant give a precise explaination, it seems to be related to
            #hardware delay. If the time_per_pt is 5.0 starting counting before waveform set up works to within 1 pixel with numpy cropping. If the
            #time_per_pt is 2.0 starting counting after waveform set up matches slow scan to a pixel. Sorry for a lack of explaination but this just seems to work.
            #See dylan_staples/confocal scans w resolution target in the data folder for images and additional details
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

            print('np.where index L: ', lower_index, 'Index U: ', upper_index, '\n')
            for j in range(len(upper_index)):
                print('All upper count index ',int(upper_index[j] / load_read_ratio))


            # get count data from adwin and record it
            raw_counts = np.array(list(self.adw.read_probes('int_array', id=1, length=len_wf+self.settings['crop_options']['pixels'])))
            raw_counts_cropped = list(raw_counts[counts_lower_index:counts_upper_index+1])
            raw_count_data.extend(raw_counts_cropped)
            self.data['raw_counts'] = raw_count_data
            #print('C_L: ', counts_lower_index, 'C_U: ', counts_upper_index)

            '''# units of count/seconds
            count_rate = list(np.array(raw_counts_cropped) * 1e3 / self.settings['time_per_pt'])
            count_rate_data.extend(count_rate)
            img_row.extend(count_rate)
            self.data['counts'] = count_rate_data'''

            #optional get full or cropped image
            count_rate = list(np.array(raw_counts) * 1e3 / self.settings['time_per_pt'])
            '''if self.settings['crop_options']['crop'] == True:
                if self.settings['crop_options']['numpy_crop'] == True:
                    if self.settings['crop_options']['numpy_type'] == 'upper':
                        #minus 1 so the crop is inclusive
                        if self.settings['time_per_pt'] == 2.0:
                            #minus 1 for inclusive crop and the 2.0 option needs 1 extra pixel
                            crop_index = -counts_upper_index-1-1
                        elif self.settings['time_per_pt'] == 5.0:
                            #minus 1 for inclusive crop and the 5.0 option needs 2 extra pixels
                            crop_index = -counts_upper_index-1-2
                        cropped_count_rate = count_rate[crop_index:crop_index + len(y_array)]
                        count_rate_data.extend(cropped_count_rate)
                        img_row.extend(cropped_count_rate)
                        self.data['counts'] = count_rate_data
                    elif self.settings['crop_options']['numpy_type'] == 'lower':
                        cropped_count_rate = count_rate[-counts_lower_index + 1:(-counts_upper_index + 1) + len(y_array)]
                        count_rate_data.extend(cropped_count_rate)
                        img_row.extend(cropped_count_rate)
                        self.data['counts'] = count_rate_data

                elif self.settings['crop_options']['numpy_crop'] == False:
                    pixels = self.settings['crop_options']['pixels']
                    cropped_count_rate = count_rate[pixels:pixels + len(y_array)]
                    count_rate_data.extend(cropped_count_rate)
                    img_row.extend(cropped_count_rate)
                    self.data['counts'] = count_rate_data

            elif self.settings['crop_options']['crop'] == False:
                count_rate_data.extend(count_rate)
                img_row.extend(count_rate)
                self.data['counts'] = count_rate_data'''

            if self.settings['crop_options']['index_mode'] == True:
                index_mode = max(set(index_list), key=index_list.count)
                print('mode of index: ',index_mode)
                index_diff = abs(counts_upper_index - index_mode)
                #index starts at 0 so need to add 1 if there is an index difference
                if index_diff > 0:
                    index_diff = index_diff + 1

                crop_index = -index_mode - 1 - index_diff
                cropped_count_rate = count_rate[crop_index:crop_index + len(y_array)]
                count_rate_data.extend(cropped_count_rate)
                img_row.extend(cropped_count_rate)
                self.data['counts'] = count_rate_data
                #full_image[i, :] = img_row
                self.data[('count_img')][i, :] = img_row #add previous scan data so image plots

                #self.data['count_img'] = full_image[:, crop_index:crop_index + len(y_array)]

            elif self.settings['crop_options']['index_mode'] == False:
                index_mode = counts_upper_index

                crop_index = -index_mode - 1
                cropped_count_rate = count_rate[crop_index:crop_index + len(y_array)]
                count_rate_data.extend(cropped_count_rate)
                img_row.extend(cropped_count_rate)
                self.data['counts'] = count_rate_data

                self.data[('count_img')][i, :] = img_row #add previous scan data so image plots



            # updates process bar and plots count_img so far
            interation_num = interation_num + len(y_array)
            self.progress = 100. * (interation_num +1) / total_interations
            self.updateProgress.emit(self.progress)

        print('Data collected')

        self.data['x_pos'] = x_data
        self.data['y_pos'] = y_data
        self.data['raw_counts'] = raw_count_data
        self.data['counts'] = count_rate_data
        #print('Position Data: ','\n',self.data['x_pos'],'\n',self.data['y_pos'],'\n','Max x: ',np.max(self.data['x_pos']),'Max y: ',np.max(self.data['y_pos']))
        #print('Counts: ','\n',self.count_data)
        #print('All data: ',self.data)


        '''if self.settings['crop_options']['display_crop'] == True:
            if self.settings['crop_options']['numpy_crop'] == True:
                if self.settings['crop_options']['numpy_flip'] == True:
                    q = -1
                else:
                    q = 1
                self.data['count_img'][0, counts_upper_index*q-1 + len(y_array)] = 0
                self.data['count_img'][0, counts_upper_index*q-1] = 0
                self.data['count_img'][Nx - 1, counts_upper_index*q-1 + len(y_array)] = 0
                self.data['count_img'][Nx - 1, counts_upper_index*q-1] = 0
                print('L index: ',counts_lower_index,'U index: ',counts_upper_index,
                    '\n','Numpy cropped length = ',counts_upper_index-counts_lower_index, 'Length array = ',len(y_array))
            elif self.settings['crop_options']['numpy_crop'] == False:
                pixel = self.settings['crop_options']['pixels']
                self.data['count_img'][0, pixel - 1] = 0
                self.data['count_img'][Nx - 1, pixel - 1] = 0
                self.data['count_img'][0, pixel - 1 + len(y_array)] = 0
                self.data['count_img'][Nx - 1, pixel - 1 + len(y_array)] = 0'''

        #clearing process to aviod memory fragmentation when running different experiments in GUI
        self.adw.stop_process(2)
        sleep(0.1)
        self.adw.clear_process(2)
        if self.settings['return_to_start'] == True:
            self.nd.update({'x_pos':x_inital,'y_pos':y_inital})



    def _plot(self, axes_list, data=None):
        '''
        This function plots the data. It is triggered when the updateProgress signal is emited and when after the _function is executed.
        For the scan, image can only be plotted once all data is gathered so self.running prevents a plotting call for the updateProgress signal.
        '''
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
            if self._plot_refresh == True:

                if self.settings['crop_options']['crop'] == True:
                    extent = [self.settings['point_a']['x'], self.settings['point_b']['x'], self.settings['point_a']['y'],self.settings['point_b']['y']]
                elif self.settings['crop_options']['crop'] == False:
                    extent = [self.settings['point_a']['x'], self.settings['point_b']['x'],self.settings['point_a']['y']-5, self.settings['point_b']['y']+5]
                #extent = [np.min(data['x_pos']), np.max(data['x_pos']), np.min(data['y_pos']), np.max(data['y_pos'])]
                self.image = pg.ImageItem(data['count_img'], interpolation='nearest')
                self.image.setLevels(levels)
                self.image.setRect(pg.QtCore.QRectF(extent[0], extent[2], extent[1] - extent[0], extent[3] - extent[2]))
                axes_list[0].addItem(self.image)
                self.colorbar = axes_list[0].addColorBar(self.image, values=(levels[0], levels[1]), label='counts/sec',colorMap='viridis')

                axes_list[0].setAspectLocked(True)
                axes_list[0].setLabel('left', 'y (µm)')
                axes_list[0].setLabel('bottom', 'x (µm)')

                axes_list[1].plot(data['y_pos'])
                axes_list[1].addLine(y=self.settings['point_a']['y'])
                axes_list[1].addLine(y=self.settings['point_b']['y'])
            else:
                self.image.setImage(data['count_img'], autoLevels=False)
                self.image.setLevels(levels)
                self.colorbar.setLevels(levels)

                #extent = [np.min(data['x_pos']), np.max(data['x_pos']), np.min(data['y_pos']), np.max(data['y_pos'])]
                #self.image.setRect(pg.QtCore.QRectF(extent[0], extent[2], extent[1] - extent[0], extent[3] - extent[2]))
                #axes_list[0].setAspectLocked(True)


    def _update(self,axes_list):
        '''all_plot_items = axes_list[0].getViewBox().allChildren()
        image = None
        for item in all_plot_items:
            if isinstance(item, pg.ImageItem):
                image = item
                break'''

        self.image.setImage(self.data['count_img'], autoLevels=False)
        self.image.setLevels([np.min(self.data['count_img']), np.max(self.data['count_img'])])
        self.colorbar.setLevels([np.min(self.data['count_img']), np.max(self.data['count_img'])])


class ConfocalScan_OldMethod(Experiment):
    '''
    This class runs a confocal microscope scan using the MCL NanoDrive to move the sample stage and the ADwin Gold II to get count data.
    The code loads a waveform on the nanodrive, starts the Adwin process, triggers a waveform aquisition, then reads the data array from the Adwin.

    Note: This method relies on lining up timing between the NanoDrive and Adwin. A point is loaded to the nanodrive say every 2.0 ms and the Adwin records
    count data every 2.0 ms (time is variable using time_per_pt setting). However while it seems to work there is nothing explicitly correlating both instruments.
    I tried to make a method that would correlated the instruments but it had artifacts in the count data. The method is commented at the end of this file.
    '''

    _DEFAULT_SETTINGS = [
        Parameter('point_a',
                  [Parameter('x',0,float,'x-coordinate start in microns'),
                   Parameter('y',0,float,'y-coordinate start in microns')
                   ]),
        Parameter('point_b',
                  [Parameter('x',10,float,'x-coordinate end in microns'),
                   Parameter('y', 10, float, 'y-coordinate end in microns')
                   ]),
        Parameter('resolution', 0.1, float, 'Resolution of each pixel in microns'),
        Parameter('time_per_pt', 2.0, float, 'Time in ms at each point to get counts; same as load_rate for nanodrive. Valid values 1/6-5 ms'),
        Parameter('read_rate',2.0,[0.267,0.5,1.0,2.0,10.0,17.0,20.0],'Time in ms. Same as read_rate for nanodrive. Should match with time_per_pt for accurate position data'),
        Parameter('return_to_start',True,bool,'If true will return to position of stage before scan started'),
        #clocks currently not implemented
        Parameter('correlate_clock', 'Aux', ['Pixel','Line','Frame','Aux'], 'Nanodrive clocked used for correlating points with counts (Connected to Digital Input 1 on Adwin)'),
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


    def _function(self):
        """
        This is the actual function that will be executed. It uses only information that is provided in the settings property
        will be overwritten in the __init__
        """
        #Gets paths for adbasic file and loads them onto ADwin.
        self.adw.stop_process(2)
        self.adw.clear_process(2)
        one_d_scan_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'Controller','binary_files', 'ADbasic', 'One_D_Scan.TB2')
        one_d_scan = os.path.normpath(one_d_scan_path)
        self.adw.update({'process_2': {'load': one_d_scan}})
        # one_d_scan script increments an index then adds count values to an array in a constant time interval
        self.nd.clock_functions('Frame', reset=True)  # reset ALL clocks to default settings

        x_min = self.settings['point_a']['x']
        x_max = self.settings['point_b']['x']
        y_min = self.settings['point_a']['y']
        y_max = self.settings['point_b']['y']
        step = self.settings['resolution']
        # array form point_a x,y to point_b x,y with step of resolution
        x_array = np.arange(x_min, x_max + step, step)
        y_array = np.arange(y_min, y_max + step, step)

        x_inital = self.nd.read_probes('x_pos')
        y_inital = self.nd.read_probes('y_pos')

        #makes sure data is getting recorded. If still equal none after running experiment data is not being stored or not measured
        self.data['x_pos'] = None
        self.data['y_pos'] = None
        self.data['raw_counts'] = None
        self.data['counts'] = None
        self.data['count_img'] = None
        #local lists to store data and append to global self.data lists
        x_data = []
        y_data = []
        raw_count_data = []
        count_rate_data = []

        #set data to zero so plotting happens while experiment runs
        Nx = len(x_array)
        Ny = len(y_array)
        self.data['count_img'] = np.zeros((Nx, Ny))

        interation_num = 0 #number to track progress
        total_interations = ((x_max - x_min)/step + 1)*((y_max - y_min)/step + 1)       #plus 1 because in total_iterations because range is inclusive ie. [0,10]
        #print('total_interations=',total_interations)

        #formula to set adwin to count for correct time frame. The event section is run every delay*3.3ns so the counter increments for that time then is read and clear
        #time_per_pt is in millisecond and the adwin delay time is delay_value*3.3ns
        adwin_delay = round((self.settings['time_per_pt']*1e6) / (3.3))
        #print('adwin delay: ',delay)

        wf = list(y_array)
        len_wf = len(y_array)


        #set inital x and y and set nanodrive stage to that position
        self.nd.update({'x_pos':x_min,'y_pos':y_min,'num_datapoints':len_wf,'read_rate':self.settings['read_rate'],'load_rate':self.settings['time_per_pt']})
        #load_rate is time_per_pt; 2.0ms = 5000Hz
        self.adw.update({'process_2':{'delay':adwin_delay}})
        sleep(0.1)  #time for stage to move to starting posiition and adwin process to initilize


        for i, x in enumerate(x_array):
            if self._abort == True:
                break
            img_row = []
            x = float(x)
            self.nd.update({'x_pos':x,'y_pos':y_min})     #goes to x position
            sleep(0.1)
            x_pos = self.nd.read_probes('x_pos')
            x_data.append(x_pos)
            self.data['x_pos'] = x_data     #adds x postion to data

            self.adw.update({'process_2':{'running':True}})
            #trigger waveform on y-axis and record position data
            self.nd.setup(settings={'num_datapoints': len_wf, 'load_waveform': wf}, axis='y')
            self.nd.setup(settings={'read_waveform': self.nd.empty_waveform},axis='y')
            y_pos = self.nd.waveform_acquisition(axis='y')
            sleep(self.settings['time_per_pt']*len_wf/1000)

            y_data.append(y_pos)
            self.data['y_pos'] = y_data
            self.adw.update({'process_2':{'running':False}})

            # get count data from adwin and record it
            raw_counts = list(self.adw.read_probes('int_array', id=1, length=len_wf))
            raw_count_data.extend(raw_counts)
            self.data['raw_counts'] = raw_count_data

            # units of count/seconds
            count_rate = list(np.array(raw_counts) * 1e3 / self.settings['time_per_pt'])
            count_rate_data.extend(count_rate)
            img_row.extend(count_rate)
            self.data['counts'] = count_rate_data


            # updates process bar and plots with new count img
            self.data[('count_img')][i, :] = img_row  # add previous scan data so image plots
            interation_num = interation_num + len_wf
            self.progress = 100. * (interation_num +1) / total_interations
            self.updateProgress.emit(self.progress)

        print('Data collected')

        self.data['x_pos'] = x_data
        self.data['y_pos'] = y_data
        self.data['raw_counts'] = raw_count_data
        self.data['counts'] = count_rate_data
        #print('Position Data: ','\n',self.data['x_pos'],'\n',self.data['y_pos'],'\n','Max x: ',np.max(self.data['x_pos']),'Max y: ',np.max(self.data['y_pos']))
        #print('Counts: ','\n',self.count_data)
        #print('All data: ',self.data)

        #clearing process to aviod memory fragmentation when running different experiments in GUI
        self.adw.clear_process(2)
        if self.settings['return_to_start'] == True:
            self.nd.update({'x_pos':x_inital,'y_pos':y_inital})



    def _plot(self, axes_list, data=None):
        '''
        This function plots the data. It is triggered when the updateProgress signal is emited and when after the _function is executed.
        For the scan, image can only be plotted once all data is gathered so self.running prevents a plotting call for the updateProgress signal.
        '''
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
            if self._plot_refresh == True:
                extent = [self.settings['point_a']['x'], self.settings['point_b']['x'], self.settings['point_a']['y'],self.settings['point_b']['y']]
                #extent = [np.min(data['x_pos']), np.max(data['x_pos']), np.min(data['y_pos']), np.max(data['y_pos'])]
                self.image = pg.ImageItem(data['count_img'], interpolation='nearest')
                self.image.setLevels(levels)
                self.image.setRect(pg.QtCore.QRectF(extent[0], extent[2], extent[1] - extent[0], extent[3] - extent[2]))
                axes_list[0].addItem(self.image)
                self.colorbar = axes_list[0].addColorBar(self.image, values=(levels[0], levels[1]), label='counts/sec',colorMap='viridis')

                axes_list[0].setAspectLocked(True)
                axes_list[0].setLabel('left', 'y (µm)')
                axes_list[0].setLabel('bottom', 'x (µm)')
            else:
                self.image.setImage(data['count_img'], autoLevels=False)
                self.image.setLevels(levels)
                self.colorbar.setLevels(levels)

                #extent = [np.min(data['x_pos']), np.max(data['x_pos']), np.min(data['y_pos']), np.max(data['y_pos'])]
                #self.image.setRect(pg.QtCore.QRectF(extent[0], extent[2], extent[1] - extent[0], extent[3] - extent[2]))
                #axes_list[0].setAspectLocked(True)


    def _update(self,axes_list):
        '''all_plot_items = axes_list[0].getViewBox().allChildren()
        image = None
        for item in all_plot_items:
            if isinstance(item, pg.ImageItem):
                image = item
                break'''

        self.image.setImage(self.data['count_img'], autoLevels=False)
        self.image.setLevels([np.min(self.data['count_img']), np.max(self.data['count_img'])])
        self.colorbar.setLevels([np.min(self.data['count_img']), np.max(self.data['count_img'])])



'''
Idea for improved method:
A clock on the nanodrive can be bound to read_waveform. When a waveform_aquisition is triggered the nanodrive executes both movement and reading. A TTL pulse will then be generated
at every point if load_rate and read_rate are equal (note this would limit time_per_pt to be 0.5 or 2.0 ms only since read_rate is a table of values). The pulse is then 
connected to a digital input on the Adwin. The Adwin automatically checks if an edge has occured at the digital inputs every 10ns so, the counter is read if a pulse is detected 
and subsiquently cleared. This idea SHOULD result in the counting time being the time betweeen pulse which is approximatly the time at each point (minus the time it takes 
nanodrive to move which is << 2.0ms.

The only changes to the code are loading a different ADbasic file and sending a command to bind the nanodrive clock.

In setup_scan:
    digin_counter_idea_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..','..','Controller','binary_files','ADbasic','Digin_Counter_Idea.TB2')
    digin_counter_idea = os.path.normpath(digin_counter_idea_path)
Before while loop:
    self.nd.clock_functions(self.settings['control_clock'],polarity='low-to-high',binding='read')
    
The Adbasic file is more complicated then the One_D_Scan script but should house the necceary components to acheive the improved method. I am unsure the reason, 
but the issue with this improved method is artifacts in the count data. Specifically there are points when counting is skipped and points of double counting. These points seem 
to be random. 

In theory this method should work given my understanding of the Nanodrive and Adwin. I will continue to try and get the method to work, but if it is a task for 
someone else my lab notebook will have more information on the idea and my testing of it. - Dylan Staples    


Add macro and have nanodrive send pulse prior to first point. Macro will clear clock and then process procedes as normal with the time and point windows aligned. 
'''

class ConfocalScan_PointByPoint(Experiment):
    '''
    Slow method for confocal scan that goes point by point. Should ensure the scan is precise and accurate at the cost of time
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
        Parameter('resolution', 1, float, 'Resolution of each pixel in microns'),
        Parameter('time_per_pt', 5.0, float, 'Time in ms at each point to get counts'),
        Parameter('settle_time',0.2,float,'Time in seconds to allow NanoDrive to settle to correct position'),
        Parameter('return_to_start', True, bool, 'If true will return to position of stage before scan started'),
        Parameter('correlate_clock', 'Aux', ['Pixel','Line','Frame','Aux'], 'Nanodrive clock'),
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

    def _function(self):
        """
        This is the actual function that will be executed. It uses only information that is provided in the settings property
        will be overwritten in the __init__
        """
        # gets an 'overlaping' path to trial counter in binary_files folder
        self.adw.stop_process(1)
        self.adw.clear_process(1)
        trial_counter_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'Controller','binary_files', 'ADbasic', 'Trial_Counter.TB1')
        trial_counter = os.path.normpath(trial_counter_path)
        self.adw.update({'process_1': {'load': trial_counter}})
        self.nd.clock_functions('Frame', reset=True)  # reset ALL clocks to default settings

        x_min = self.settings['point_a']['x']
        x_max = self.settings['point_b']['x']
        y_min = self.settings['point_a']['y']
        y_max = self.settings['point_b']['y']
        step = self.settings['resolution']
        #array form point_a x,y to point_b x,y with step of resolution
        x_array = np.arange(x_min, x_max+step, step)
        y_array = np.arange(y_min, y_max + step, step)
        reversed_y_array = y_array[::-1]

        x_inital = self.nd.read_probes('x_pos')
        y_inital = self.nd.read_probes('y_pos')

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
        #for x in x_array:
        for i, x in enumerate(x_array):
            x = float(x)
            img_row = []  #used for tracking image rows and adding to count_img; list not saved
            self.nd.update({'x_pos':x})
            if forward == True:
                for y in y_array:
                    if self._abort:  # halts loop (and experiment) if stop button is pressed
                        break
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
                    count_rate = raw_counts*1e3/self.settings['time_per_pt'] # in units of counts/second

                    img_row.append(count_rate)
                    raw_counts_data.append(raw_counts)
                    count_rate_data.append(count_rate)
                    self.data['raw_counts'] = raw_counts_data
                    self.data['counts'] = count_rate_data

            else:
                for y in reversed_y_array:
                    if self._abort:  # halts loop (and experiment) if stop button is pressed
                        break
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
                    count_rate = raw_counts*1e3/self.settings['time_per_pt'] # in units of counts/second

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

        print('Data collected')

        self.data['x_pos'] = x_data
        self.data['y_pos'] = y_data
        self.data['raw_counts'] = raw_counts_data
        self.data['counts'] = count_rate_data

        #print('Position Data: ', '\n', self.data['x_pos'], '\n', self.data['y_pos'], '\n', 'Max x: ',np.max(self.data['x_pos']), 'Max y: ', np.max(self.data['y_pos']))
        #print('All data: ',self.data)

        self.adw.update({'process_2': {'running': False}})
        self.adw.clear_process(1)
        if self.settings['return_to_start'] == True:
            self.nd.update({'x_pos': x_inital, 'y_pos': y_inital})



    def _plot(self, axes_list, data=None):
        '''
        This function plots the data. It is triggered when the updateProgress signal is emited and when after the _function is executed.
        For the scan, image can only be plotted once all data is gathered so self.running prevents a plotting call for the updateProgress signal.
        '''
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
            if self._plot_refresh == True:
                #extent = [self.settings['point_a']['x'], self.settings['point_b']['x'], self.settings['point_a']['y'],self.settings['point_b']['y']]
                extent = [np.min(data['x_pos']), np.max(data['x_pos']), np.min(data['y_pos']), np.max(data['y_pos'])]
                self.image = pg.ImageItem(data['count_img'], interpolation='nearest')
                self.image.setLevels(levels)
                self.image.setRect(pg.QtCore.QRectF(extent[0], extent[2],extent[1] - extent[0], extent[3] - extent[2]))
                axes_list[0].addItem(self.image)
                self.colorbar = axes_list[0].addColorBar(self.image,values=(levels[0], levels[1]),label='counts/sec',colorMap='viridis')

                axes_list[0].setAspectLocked(True)
                axes_list[0].setLabel('left', 'y (µm)')
                axes_list[0].setLabel('bottom', 'x (µm)')

            else:
                self.image.setImage(data['count_img'], autoLevels=False)
                self.image.setLevels(levels)
                self.colorbar.setLevels(levels)

                extent = [np.min(data['x_pos']), np.max(data['x_pos']), np.min(data['y_pos']), np.max(data['y_pos'])]
                self.image.setRect(pg.QtCore.QRectF(extent[0], extent[2], extent[1] - extent[0], extent[3] - extent[2]))
                axes_list[0].setAspectLocked(True)


    def _update(self,axes_list):
        '''
        all_plot_items = axes_list[0].getViewBox().allChildren()
        image = None
        for item in all_plot_items:
            if isinstance(item, pg.ImageItem):
                image = item
                break
        '''

        self.image.setImage(self.data['count_img'])
        self.image.setLevels([np.min(self.data['count_img']),np.max(self.data['count_img'])])
        self.colorbar.setLevels([np.min(self.data['count_img']),np.max(self.data['count_img'])])


class ConfocalPoint(Experiment):
    '''
    This class implements a confocal microscope to get the counts at a single point. It uses the MCL NanoDrive to move the sample stage and the ADwin Gold to get count data.
    The 'continuous' parameter if false will return 1 data point. If true it offers live counting that continues until the stop button is clicked.

    Could add a small scan radius to search for points of high counts ie NV centers then go to that point
    '''

    _DEFAULT_SETTINGS = [
        Parameter('point',
                  [Parameter('x',0,float,'x-coordinate start in microns'),
                   Parameter('y',0,float,'y-coordinate start in microns')
                   ]),
        Parameter('count_time', 2.0, float, 'Time in ms at  point to get count data'),
        Parameter('continuous', False, bool,'If experiment should return 1 value or continuously plot for optics optimization'),
        #clocks currently not implemented
        Parameter('correlate_clock', 'Aux', ['Pixel','Line','Frame','Aux'], 'Nanodrive clocked used for correlating points with counts'),
        Parameter('laser_clock', 'Pixel', ['Pixel','Line','Frame','Aux'], 'Nanodrive clocked used for turning laser on and off'),
        Parameter('plot_style', 'aux', ['main','aux','two'],'Main is bottom graph (axes_list[0]), aux is top graph (axes_list[1]), two is plot on both'),
        Parameter('graph_params',
                  [Parameter('refresh_rate',0.01,float,'For continuous counting this is the refresh rate of the graph in seconds (= 1/frames per second)'),
                   Parameter('length_data',2500,int,'After so many data points matplotlib freezes GUI. Data dic will be cleared after this many entries'),
                   #BOTH graph_params above effect the stability of GUI. The values here should be optimized and then left unchanged
                   Parameter('font_size',32,int,'font size to make it easier to see on the fly if needed')
                   ])
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


    def _function(self):
        """
        This is the actual function that will be executed. It uses only information that is provided in the settings property
        will be overwritten in the __init__
        """
        #gets an 'overlaping' path to trial counter in binary_files folder
        self.adw.stop_process(1)
        self.adw.clear_process(1)
        trial_counter_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..','..','Controller','binary_files','ADbasic','Trial_Counter.TB1')
        trial_counter = os.path.normpath(trial_counter_path)
        self.adw.update({'process_1':{'load':trial_counter}})
        self.nd.clock_functions('Frame',reset=True)     #reset ALL clocks to default settings

        self.data['counts'] = None
        self.data['raw_counts'] = None
        count_rate_data = []
        raw_counts_data =[]

        x = self.settings['point']['x']
        y = self.settings['point']['y']

        #set adwin delay which determines the counting time
        adwin_delay = round((self.settings['count_time']*1e6) / (3.3))
        self.adw.update({'process_1':{'delay':adwin_delay,'running':True}})
        self.nd.update({'x_pos':x,'y_pos':y})
        sleep(0.1)  #time for stage to move and adwin process to initilize

        if self.settings['continuous'] == False:
            sleep((self.settings['count_time']*1.5)/1000)    #sleep for 1.2 times the count time to ensure enough time for counts. note this does not affect actually counting
            # window
            raw_counts = self.adw.read_probes('int_var',id=1)
            counts = raw_counts*1e3/self.settings['count_time']
            for i in range(0,2):        #just want the 1 number to be viewable so will plot a straight line (with 2 points) of its value
                raw_counts_data.append(raw_counts)
                count_rate_data.append(counts)
            self.data['raw_counts'] = raw_counts_data
            self.data['counts'] = count_rate_data

        elif self.settings['continuous'] == True:
            while self._abort == False:     #self._abort is defined in experiment.py and is true false while running and set false when stop button is hit
                sleep(self.settings['graph_params']['refresh_rate'])    #effictivly this sleep is the time interval the graph is refreshed (1/fps)
                # counting window
                raw_counts = self.adw.read_probes('int_var',id=1)           #read variable from adwin
                counts = raw_counts*1e3/self.settings['count_time']

                raw_counts_data.append(raw_counts)
                count_rate_data.append(counts)
                self.data['raw_counts'] = raw_counts_data
                self.data['counts'] = count_rate_data
                #print('Current count rate', self.data['counts'][-1])

                self.progress = 1   #this is a infinite loop till stop button is hit; progress & updateProgress is only here to update plot
                self.updateProgress.emit(self.progress)     #calling updateProgress.emit triggers _plot

                if len(self.data['counts']) > self.settings['graph_params']['length_data']:
                    count_rate_data.clear()
                    self.data['counts'].clear()
                    raw_counts_data.clear()
                    self.data['raw_counts'].clear()

        self.adw.update({'process_1': {'running': False}})
        self.adw.clear_process(1)



    def _plot(self, axes_list, data=None):
        '''
        This function plots the data. It is triggered when the updateProgress signal is emited and when after the _function is executed.
        '''
        if data is None:
            data = self.data

        if data is not None and data is not {}:
            axes_list[0].clear()
            #axes_list[0].plot(data['counts'])
            axes_list[0].plot(data['raw_counts'])
            axes_list[0].showGrid(x=True,y=True)
            axes_list[0].setLabel('left','counts/sec')  #units='counts/sec'
            axes_list[0].setXRange(0,self.settings['graph_params']['length_data']+100)

            #axes_list[1].setText(f'{data["counts"][-1]/1000:.3f} kcounts/sec')
            axes_list[1].setText(f'{data["raw_counts"][-1]} counts/sec')

            '''
            Might be useful to include a max count number display
            '''

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