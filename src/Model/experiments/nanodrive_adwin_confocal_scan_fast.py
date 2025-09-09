'''
Nanodrive ADwin Confocal Scan Fast Module

This module implements fast raster scanning for confocal microscopy using:
- MCL NanoDrive for sample stage positioning
- ADwin Gold II for photon counting and timing
- Optimized waveform-based scanning for speed

The fast method uses pre-loaded waveforms and compensates for warm-up/cool-down
movements to achieve accurate positioning while maintaining high scan rates.
'''

import numpy as np
from pyqtgraph.exporters import ImageExporter
from pathlib import Path

from src.core import Parameter, Experiment
from src.core.helper_functions import get_project_root, get_configured_confocal_scans_folder
from time import sleep
import pyqtgraph as pg


def get_binary_file_path(filename: str) -> Path:
    """
    Get the path to a binary file in the Controller/binary_files/ADbasic directory.
    
    Args:
        filename: Name of the binary file (e.g., 'One_D_Scan.TB2')
        
    Returns:
        Path object pointing to the binary file
        
    Raises:
        FileNotFoundError: If the binary file doesn't exist
    """
    project_root = get_project_root()
    binary_path = project_root / 'src' / 'Controller' / 'binary_files' / 'ADbasic' / filename
    
    if not binary_path.exists():
        # Try to provide helpful error message
        print(f"Warning: Binary file not found: {binary_path}")
        print(f"Project root: {project_root}")
        print(f"Expected location: {binary_path}")
        print(f"Available files in ADbasic directory:")
        adbasic_dir = project_root / 'src' / 'Controller' / 'binary_files' / 'ADbasic'
        if adbasic_dir.exists():
            for file in adbasic_dir.iterdir():
                if file.is_file():
                    print(f"  - {file.name}")
        else:
            print(f"  ADbasic directory does not exist: {adbasic_dir}")
        raise FileNotFoundError(f"Binary file not found: {binary_path}")
    
    return binary_path


class NanodriveAdwinConfocalScanFast(Experiment):
    '''
    Fast confocal microscope scan using MCL NanoDrive and ADwin Gold II.
    
    This class runs a confocal microscope scan using the MCL NanoDrive to move 
    the sample stage and the ADwin Gold II to get count data. The code loads a 
    waveform on the nanodrive, starts the Adwin process, triggers a waveform 
    acquisition, then reads the count data array from the Adwin.

    To get accurate counts, the loaded waveforms are extended to compensate for 
    'warm up' and 'cool down' movements. The data arrays are then manipulated 
    to get the counts for the inputed region.

    Hardware Dependencies:
    - MCL NanoDrive: For precise sample stage positioning
    - ADwin Gold II: For photon counting and timing control
    - ADbasic Binary: One_D_Scan.TB2 for counter operations
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
                         Parameter('folderpath',str(get_configured_confocal_scans_folder()),str,'folder location to save images at each z-value')]),
        #!!! If you see horizontial lines in the confocal image, the adwin arrays likely are corrupted. The fix is to reboot the adwin. You will nuke all
        #other process, variables, and arrays in the adwin. This parameter is added to make that easy to do in the GUI.
        Parameter('reboot_adwin',False,bool,'Will reboot adwin when experiment is executed. Useful is data looks fishy'),
        Parameter('cropping', #nested cause it does not need changed often
                  [Parameter('crop_data',True,bool,'Current logic scans over a larger area then crops data to requested size. Added for ease of seeing full image')]),
        #clocks currently not implemented
        Parameter('laser_clock', 'Pixel', ['Pixel','Line','Frame','Aux'], 'Nanodrive clocked used for turning laser on and off')
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
        super().__init__(name, settings=settings, sub_experiments=sub_experiments, devices=devices, log_function=log_function, data_path=data_path)
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
        
        # Use the helper function to find the binary file
        one_d_scan_path = get_binary_file_path('One_D_Scan.TB2')
        self.adw.update({'process_2': {'load': str(one_d_scan_path)}})
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
        sleep(0.1)

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
        self.settings['z_pos'] = self.z_inital

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
            y_data.append(list(y_pos))
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
            cropped_raw_counts = list(raw_counts[crop_index:crop_index + len(y_array)])
            cropped_count_rate = count_rate[crop_index:crop_index + len(y_array)]

            raw_count_data.append(cropped_raw_counts)
            self.data['raw_counts'] = raw_count_data

            count_rate_data.append(cropped_count_rate)
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
        self.data['y_pos'] = np.array(y_data)
        self.data['raw_counts'] = np.array(raw_count_data)
        self.data['count_rate'] = np.array(count_rate_data)
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
            axes_list[0].setTitle(f"Confocal Scan with z = {self.settings['z_pos']:.2f}")

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
            try: #sometimes when data is inputted as argument it does not have 'count_img' key; this try/except prevents error if that happens
                non_zero_values = data['count_img'][data['count_img'] > 0]
            except KeyError:
                data['count_img'] = self.data['count_img']
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