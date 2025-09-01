'''
Nanodrive ADwin Confocal Point Module

This module implements single-point confocal microscopy measurements using:
- MCL NanoDrive for sample stage positioning
- ADwin Gold II for photon counting and timing
- Single point or continuous counting modes

This class implements a confocal microscope to get the counts at a single point. 
It uses the MCL NanoDrive to move the sample stage and the ADwin Gold to get 
count data. The 'continuous' parameter if false will return 1 data point. 
If true it offers live counting that continues until the stop button is clicked.
'''

import numpy as np
from pyqtgraph.exporters import ImageExporter
from pathlib import Path

from src.core import Parameter, Experiment
from src.core.helper_functions import get_project_root
from time import sleep
import pyqtgraph as pg


def get_binary_file_path(filename: str) -> Path:
    """
    Get the path to a binary file in the Controller/binary_files/ADbasic directory.
    
    Args:
        filename: Name of the binary file (e.g., 'Averagable_Trial_Counter.TB1')
        
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


class NanodriveAdwinConfocalPoint(Experiment):
    '''
    Single-point confocal microscope measurements using MCL NanoDrive and ADwin Gold II.
    
    This class implements a confocal microscope to get the counts at a single point. 
    It uses the MCL NanoDrive to move the sample stage and the ADwin Gold to get 
    count data. The 'continuous' parameter if false will return 1 data point. 
    If true it offers live counting that continues until the stop button is clicked.

    Hardware Dependencies:
    - MCL NanoDrive: For precise sample stage positioning
    - ADwin Gold II: For photon counting and timing control
    - ADbasic Binary: Averagable_Trial_Counter.TB1 for counter operations
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


    def setup(self):
        '''
        Gets paths for adbasic file and loads them onto ADwin.
        '''
        self.adw.stop_process(1)
        sleep(0.1)
        self.adw.clear_process(1)
        
        # Use the helper function to find the binary file
        trial_counter_path = get_binary_file_path('Averagable_Trial_Counter.TB1')
        self.adw.update({'process_1': {'load': str(trial_counter_path)}})
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