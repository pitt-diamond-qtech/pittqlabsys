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
        #clocks currently not implemented
        Parameter('correlate_clock', 'Aux', ['Pixel','Line','Frame','Aux'], 'Nanodrive clocked used for correlating points with counts (Connected to Digital Input 1 on Adwin)'),
        Parameter('laser_clock', 'Pixel', ['Pixel','Line','Frame','Aux'], 'Nanodrive clocked used for turning laser on and off')
    ]

    #For actual experiment use LP100 [MCL_NanoDrive({'serial':2849})]. For testing using HS3 ['serial':2850]
    _DEVICES = {'nanodrive': MCLNanoDrive(settings={'serial':2850}), 'adwin':ADwinGold()}
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
        self.running = True #use to not trigger plotting but still update progress bar
        x_min = self.settings['point_a']['x']
        x_max = self.settings['point_b']['x']
        y_min = self.settings['point_a']['y']
        y_max = self.settings['point_b']['y']
        step = self.settings['resolution']
        #array form point_a x,y to point_b x,y with step of resolution
        y_array = np.arange(y_min, y_max+step, step)

        #makes sure data is getting recorded. If still equal none after running experiment data is not being stored or measured
        self.data['x_pos'] = None
        self.data['y_pos'] = None
        self.data['counts'] = None
        self.data['count_rate'] = None
        self.data['count_img'] = None
        #local lists to store data and append to global self.data lists
        x_data = []
        y_data = []
        count_data = []
        count_rate_data = []

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
        len_wf = len(y_array)
        #print(len_wf,wf)

        #set inital x and y and set nanodrive stage to that position
        self.nd.update({'x_pos':x_min,'y_pos':y_min,'read_rate':self.settings['read_rate'],'num_datapoints':len_wf,'load_rate':self.settings['time_per_pt']})
        #load_rate is time_per_pt; 2.0ms = 5000Hz
        self.adw.update({'process_2':{'delay':adwin_delay}})
        #print('nd and adwin setup')

        sleep(0.1)  #time for stage to move to starting posiition and adwin process to initilize
        x = x_min

        while x <= x_max:
            self.nd.update({'x_pos':x,'y_pos':y_min})     #goes to x position
            sleep(0.01)
            x_pos = self.nd.read_probes('x_pos')
            x_data.append(x_pos)
            self.data['x_pos'] = x_data     #adds x postion to data

            self.adw.update({'process_2':{'running':True}})

            #trigger waveform on y-axis and record position data
            self.nd.setup(settings={'read_waveform':self.nd.empty_waveform,'load_waveform':wf},axis='y')
            y_pos = self.nd.waveform_acquisition(axis='y')
            y_data.append(y_pos)
            self.data['y_pos'] = y_data

            self.adw.update({'process_2':{'running':False}})

            #get count data from adwin and record it
            counts = list(self.adw.read_probes('int_array',id=1,length=len(y_array)))
            count_data.append(counts)
            self.data['counts'] = count_data

            #print('counts: ', counts)

            #units of counts/millisecond = kcount/seconds
            count_rate = list(np.array(counts)/self.settings['time_per_pt'])
            count_rate_data.extend(count_rate)
            self.data['count_rate'] = count_rate_data

            interation_num = interation_num + len_wf
            x = x + step

            #updates process bar to see experiment is running
            self.progress = 100. * (interation_num +1) / total_interations
            self.updateProgress.emit(self.progress)

        print('Data collected')
        self.running = False

        self.data['x_pos'] = x_data
        self.data['y_pos'] = y_data
        self.data['counts'] = count_data
        self.data['count_rate'] = count_rate_data
        #print('Position Data: ','\n',self.x_data,'\n',self.y_data)
        #print('Counts: ','\n',self.count_data)

        #convert list to square matrix of count/sec data
        Nx = int(np.sqrt(len(self.data['count_rate'])))
        count_img = np.array(self.data['count_rate'][0:Nx**2])      #converts to numpy array
        count_img = count_img.reshape((Nx, Nx)).T               #reshapes array to square matrix. Transpose to have x as horizontail

        # line to call update function in experiment parent class and triggers _plot in this class
        self.data.update({'count_img':count_img})
        #print('All data: ',self.data)



    def _plot(self, axes_list, data=None):
        '''
        This function plots the data. It is triggered when the updateProgress signal is emited and when after the _function is executed.
        For the scan, image can only be plotted once all data is gathered so self.running prevents a plotting call for the updateProgress signal.
        '''
        if self.running == True:
            pass        #does not try to plot until all data is collected
        else:
            if data is None:
                data = self.data

            if data is not None and data is not{}:
                #use axes_list[0] which is bottom graphing section
                fig_counts = axes_list[0].get_figure()
                extent = [self.settings['point_a']['x'],self.settings['point_b']['x'],self.settings['point_a']['y'],self.settings['point_b']['y']]
                implot = axes_list[0].imshow(data['count_img'],cmap='cividis', interpolation='nearest', extent=extent)
                fig_counts.colorbar(implot, label='kcounts/sec')

                axes_list[0].set_xlabel('x (µm)')
                axes_list[0].set_ylabel('y (µm)')
                #could use top graphing section for position data
                #fig_pos = axes_list[1].get_figure()



    def _update(self,axes_list):
        implot = axes_list[0].get_images()[0]
        implot.set_data(self.data['count_img'])

        colorbar = implot.colorbar



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
                   Parameter('font_size',18,int,'font size to make it easier to see on the fly if needed')
                   ])
    ]

    #For actual experiment use LP100 [MCL_NanoDrive({'serial':2849})]. For testing using HS3 ['serial':2850]
    _DEVICES = {'nanodrive': MCLNanoDrive(settings={'serial':2850}), 'adwin':ADwinGold()}
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
        counts_data = []

        x = self.settings['point']['x']
        y = self.settings['point']['y']

        #set adwin delay which determines the counting time
        adwin_delay = round((self.settings['count_time']*1e6) / (3.3))
        self.adw.update({'process_1':{'delay':adwin_delay,'running':True}})
        self.nd.update({'x_pos':x,'y_pos':y})
        sleep(0.1)  #time for stage to move and adwin process to initilize

        if self.settings['continuous'] == False:
            sleep((self.settings['count_time']*1.2)/1000)    #sleep for 1.2 times the count time to ensure enough time for counts. note this does not affect actually counting
            # window
            counts = self.adw.read_probes('int_var',id=1)
            for i in range(0,2):        #just want the 1 number to be viewable so will plot a straight line (with 2 points) of its value
                counts_data.append(counts)
            self.data['counts'] = counts_data

        elif self.settings['continuous'] == True:
            while self._abort == False:     #self._abort is defined in experiment.py and is true false while running and set false when stop button is hit
                sleep(self.settings['graph_params']['refresh_rate'])    #effictivly this sleep is the time interval the graph is refreshed (1/fps)
                # counting window
                counts = self.adw.read_probes('int_var',id=1)           #read variable from adwin
                counts_data.append(counts)
                self.data['counts'] = counts_data
                #print('Current count rate', self.data['counts'][-1])

                self.progress = 1   #this is a infinite loop till stop button is hit; progress & updateProgress is only here to update plot
                self.updateProgress.emit(self.progress)     #calling updateProgress.emit triggers _plot

                if len(self.data['counts']) > self.settings['graph_params']['length_data']:         #once matplotlib gets above a certain number of data point GUI starts to lag and freeze
                    counts_data.clear()
                    self.data['counts'].clear()


    def _plot(self, axes_list, data=None):
        '''
        This function plots the data. It is triggered when the updateProgress signal is emited and when after the _function is executed.
        '''
        if data is None:
            data = self.data

        if data is not None and data is not {}:
            #clear axes_list after each plot to get rid of previous data and legend
            axes_list[1].clear()
            axes_list[1].plot(data['counts'], label=f'{data["counts"][-1]/1000:.3f} kcounts/sec', color='blue')
            axes_list[1].set_ylabel('count rate')
            axes_list[1].grid(True)
            #legend displays current counts in top left
            axes_list[1].legend(loc='upper left',fontsize=self.settings['graph_params']['font_size'])

            #annotate can display current counts anywhere on screen; could be used instead of legend
            #latest_value = data['counts'][-1]
            #axes_list[1].annotate(f'{latest_value/1000:.3f} kcounts/sec',xy=(len(data['counts']) - 1, latest_value),xytext=(len(data['counts']) - 5, latest_value + 100),
            # fontsize=10)

            '''
            Might be useful to include a max count number display. This could be done with the legend/annotate while current count is displayed using the other option
            change latest_value to max_value but need to define max_value from entire run of experiment above
            '''


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
'''