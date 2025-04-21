'''
This file has the experiment classes relevant to using a confocal microscope. So far this includes:

- Confocal Scan (old method) for larger images
- Confocal Point for counting at 1 point

'''

import numpy as np
from src.Controller import MCLNanoDrive, ADwinGold
from src.core import Parameter, Experiment
import os
from time import sleep
import pyqtgraph as pg


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

        self.setup_scan()



    def setup_scan(self):
        '''
        Gets paths for adbasic file and loads them onto ADwin.
        Resets Nanodrive clock settings to default.
        '''
        #one_d_scan script increments an index then adds count values to an array in a constant time interval
        one_d_scan_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..','..','Controller','binary_files','ADbasic','One_D_Scan.TB2')
        one_d_scan = os.path.normpath(one_d_scan_path)

        self.adw.update({'process_2':{'load':one_d_scan}})
        self.nd.clock_functions('Frame',reset=True)     #reset ALL clocks to default settings

        #print('scan setup')

    def _function(self):
        """
        This is the actual function that will be executed. It uses only information that is provided in the settings property
        will be overwritten in the __init__
        """
        x_min = self.settings['point_a']['x']
        x_max = self.settings['point_b']['x']
        y_min = self.settings['point_a']['y']
        y_max = self.settings['point_b']['y']
        step = self.settings['resolution']
        #array form point_a x,y to point_b x,y with step of resolution
        x_array = np.arange(x_min, x_max + step, step)
        y_array = np.arange(y_min, y_max+step, step)
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
        raw_count_data = []
        count_rate_data = []

        Nx = len(x_array)
        Ny = len(y_array)
        self.data['count_img'] = np.zeros((Nx, Ny))

        interation_num = 0 #number to track progress
        total_interations = ((x_max - x_min)/step + 1)*((y_max - y_min)/step + 1)       #plus 1 because in total_iterations because range is inclusive ie. [0,10]
        #print('total_interations=',total_interations)

        #print('process: ', self.adw.read_probes('process_status', id=2))
        #print('nd connectd? ',self.nd.is_connected)

        #formula to set adwin to count for correct time frame. The event section is run every delay*3.3ns so the counter increments for that time then is read and clear
        #time_per_pt is in millisecond and the adwin delay time is delay_value*3.3ns
        adwin_delay = round((self.settings['time_per_pt']*1e6) / (3.3))
        #print('adwin delay: ',delay)

        wf = list(y_array)
        wf_reversed = list(reversed_y_array)
        len_wf = len(y_array)
        #print(len_wf,wf)


        #set inital x and y and set nanodrive stage to that position
        self.nd.update({'x_pos':x_min,'y_pos':y_min,'read_rate':self.settings['read_rate'],'num_datapoints':len_wf,'load_rate':self.settings['time_per_pt']})
        #load_rate is time_per_pt; 2.0ms = 5000Hz
        self.adw.update({'process_2':{'delay':adwin_delay}})
        sleep(0.1)  #time for stage to move to starting posiition and adwin process to initilize

        self._first_plot = True #useed to create pg.image only once
        forward = True #used to rasterize more efficently
        for i, x in enumerate(x_array):
            if self._abort == True:
                break
            img_row = []
            x = float(x)
            if forward == True:
                self.nd.update({'x_pos':x,'y_pos':y_min})     #goes to x position
                sleep(0.1)
                x_pos = self.nd.read_probes('x_pos')
                x_data.append(x_pos)
                self.data['x_pos'] = x_data     #adds x postion to data

                self.adw.update({'process_2':{'running':True}})
                #trigger waveform on y-axis and record position data
                self.nd.setup(settings={'read_waveform':self.nd.empty_waveform,'load_waveform':wf},axis='y')
                y_pos = self.nd.waveform_acquisition(axis='y')
                sleep(self.settings['time_per_pt']*len_wf/1000)
                y_data.append(y_pos)
                self.data['y_pos'] = y_data
                self.adw.update({'process_2':{'running':False}})

                # get count data from adwin and record it
                raw_counts = list(self.adw.read_probes('int_array', id=1, length=len(y_array)))
                raw_count_data.extend(raw_counts)
                self.data['raw_counts'] = raw_count_data

                # units of count/seconds
                count_rate = list(np.array(raw_counts) * 1e3 / self.settings['time_per_pt'])
                count_rate_data.extend(count_rate)
                img_row.extend(count_rate)
                self.data['counts'] = count_rate_data

            else:
                self.nd.update({'x_pos': x, 'y_pos': y_max})  # goes to x position
                sleep(0.1)
                x_pos = self.nd.read_probes('x_pos')
                x_data.append(x_pos)
                self.data['x_pos'] = x_data  # adds x postion to data

                self.adw.update({'process_2': {'running': True}})
                # trigger waveform on y-axis and record position data
                self.nd.setup(settings={'read_waveform': self.nd.empty_waveform, 'load_waveform': wf_reversed}, axis='y')
                y_pos = self.nd.waveform_acquisition(axis='y')
                y_data.append(y_pos)
                self.data['y_pos'] = y_data
                self.adw.update({'process_2': {'running': False}})

                # get count data from adwin and record it
                raw_counts = list(self.adw.read_probes('int_array', id=1, length=len(y_array)))
                raw_count_data.extend(raw_counts)
                self.data['raw_counts'] = raw_count_data

                # units of count/seconds
                count_rate = list(np.array(raw_counts) * 1e3 / self.settings['time_per_pt'])
                count_rate.reverse()
                count_rate_data.extend(count_rate)
                img_row.extend(count_rate)
                self.data['counts'] = count_rate_data

            self.data[('count_img')][i, :] = img_row #add previous scan data so image plots
            #forward = not forward

            # updates process bar to see experiment is running
            interation_num = interation_num + len_wf
            self.progress = 100. * (interation_num +1) / total_interations
            self.updateProgress.emit(self.progress)

        print('Data collected')

        self.data['x_pos'] = x_data
        self.data['y_pos'] = y_data
        self.data['raw_counts'] = raw_count_data
        self.data['counts'] = count_rate_data
        print('Position Data: ','\n',self.data['x_pos'],'\n',self.data['y_pos'],'\n','Max x: ',np.max(self.data['x_pos']),'Max y: ',np.max(self.data['y_pos']))
        #print('Counts: ','\n',self.count_data)

        #print('All data: ',self.data)
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

            levels = [np.min(data['count_img']), np.max(data['count_img'])]
            if self._first_plot == True:
                #extent = [self.settings['point_a']['x'], self.settings['point_b']['x'], self.settings['point_a']['y'],self.settings['point_b']['y']]
                extent = [np.min(data['x_pos']), np.max(data['x_pos']), np.min(data['y_pos']), np.max(data['y_pos'])]
                self.image = pg.ImageItem(data['count_img'], interpolation='nearest')
                self.image.setLevels(levels)
                self.image.setRect(pg.QtCore.QRectF(extent[0], extent[2], extent[1] - extent[0], extent[3] - extent[2]))
                axes_list[0].addItem(self.image)
                self.colorbar = axes_list[0].addColorBar(self.image, values=(levels[0], levels[1]), label='counts/sec',colorMap='viridis')

                axes_list[0].setAspectLocked(True)
                axes_list[0].setLabel('left', 'y (µm)')
                axes_list[0].setLabel('bottom', 'x (µm)')

                self._first_plot = False  # flip the flag so future updates use the else
            else:
                self.image.setImage(data['count_img'], autoLevels=False)
                self.image.setLevels(levels)
                self.colorbar.setLevels(levels)

                extent = [np.min(data['x_pos']), np.max(data['x_pos']), np.min(data['y_pos']), np.max(data['y_pos'])]
                self.image.setRect(pg.QtCore.QRectF(extent[0], extent[2], extent[1] - extent[0], extent[3] - extent[2]))
                axes_list[0].setAspectLocked(True)


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

    def get_axes_layout(self, figure_list):
        """
        overrides method so image item isnt cleared when last _plot is called
        """
        axes_list = []
        if self._plot_refresh is True and self._first_plot is True:
            for graph in figure_list:
                graph.clear()
                axes_list.append(graph.addPlot(row=0,col=0))


        else:
            for graph in figure_list:
                axes_list.append(graph.getItem(row=0,col=0))

        return axes_list

class ConfocalPoint(Experiment):
    '''
    This class implements a confocal microscope to get the counts at a point. It uses the MCL NanoDrive to move the sample stage and the ADwin Gold to get count data.
    The 'continuous' parameter if false will return 1 data point. If true it offers live counting that continues until the stop button is clicked.
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

        self.setup()

    def setup(self):
        '''
        Gets paths for adbasic files and loads them onto ADwin.
        Resets Nanodrive clock settings to default.
        '''
        #gets an 'overlaping' path to trial counter in binary_files folder
        trial_counter_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..','..','Controller','binary_files','ADbasic','Trial_Counter.TB1')
        trial_counter = os.path.normpath(trial_counter_path)

        self.adw.update({'process_1':{'load':trial_counter}})
        self.nd.clock_functions('Frame',reset=True)     #reset ALL clocks to default settings

    def _function(self):
        """
        This is the actual function that will be executed. It uses only information that is provided in the settings property
        will be overwritten in the __init__
        """
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
                if len(self.data['counts']) > self.settings['graph_params']['length_data']:         #once matplotlib gets above a certain number of data point GUI starts to lag and freeze
                    count_rate_data.clear()
                    self.data['counts'].clear()
                    raw_counts_data.clear()
                    self.data['raw_counts'].clear()

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
    Slow method for confocal scan that goes point by point. Should ensure the scan is precise and accurate at the cost of computation time
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

        self.setup_scan()


    def setup_scan(self):
        '''
        Gets paths for adbasic file and loads them onto ADwin.
        Resets Nanodrive clock settings to default.
        '''
        # gets an 'overlaping' path to trial counter in binary_files folder
        trial_counter_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'Controller','binary_files', 'ADbasic', 'Trial_Counter.TB1')
        trial_counter = os.path.normpath(trial_counter_path)

        self.adw.update({'process_1': {'load': trial_counter}})
        self.nd.clock_functions('Frame',reset=True)     #reset ALL clocks to default settings

        #print('scan setup')

    def _function(self):
        """
        This is the actual function that will be executed. It uses only information that is provided in the settings property
        will be overwritten in the __init__
        """
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

        self._first_plot = True #used to first create pg.image
        forward = True #used to rasterize more efficently going forward then back
        #for x in x_array:
        for i, x in enumerate(x_array):
            if self._abort:  #halts loop (and experiment) if stop button is pressed
                break
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
                    count_rate = raw_counts*1e3/self.settings['time_per_pt'] # in units of counts/second

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

        print('Position Data: ', '\n', self.data['x_pos'], '\n', self.data['y_pos'], '\n', 'Max x: ',np.max(self.data['x_pos']), 'Max y: ', np.max(self.data['y_pos']))
        #print('All data: ',self.data)
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

            levels = [np.min(data['count_img']), np.max(data['count_img'])]
            if self._first_plot == True:
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

                self._first_plot = False  # flip the flag so future updates use the else
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

    def get_axes_layout(self, figure_list):
        """
        overrides method so image item isnt cleared when last _plot is called
        """
        axes_list = []
        if self._plot_refresh is True and self._first_plot is True:
            for graph in figure_list:
                graph.clear()
                axes_list.append(graph.addPlot(row=0,col=0))


        else:
            for graph in figure_list:
                axes_list.append(graph.getItem(row=0,col=0))

        return axes_list