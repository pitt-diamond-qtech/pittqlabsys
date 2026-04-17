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
from src.core.adwin_helpers import get_adwin_binary_path
from time import sleep
import pyqtgraph as pg
import keyboard




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
        Parameter('keyboard_control_nanodrive',
                  [Parameter('keyboard_control_on', False, bool, 'turn on for keyboard control of the nanodrive'),
                   Parameter('x_neg_key', 'a', str, 'negative x direction key'),
                   Parameter('x_pos_key', 'd', str, 'positive x direction key'),
                   Parameter('x_step', 0.1, float, 'step size in x direction'),
                   Parameter('y_neg_key', 's', str, 'negative y direction key'),
                   Parameter('y_pos_key', 'w', str, 'positive y direction key'),
                   Parameter('y_step', 0.1, float, 'step size in y direction'),
                   Parameter('z_pos_key', 'j', str, 'positive x direction key'),
                   Parameter('z_neg_key', 'k', str, 'negative x direction key'),
                   Parameter('z_step', 0.1, float, 'step size in x direction'),
                   Parameter('return_to_start_key', 'o', str, 'key to return to starting location'),
                   Parameter('settle_time', 0.2, float,
                             'Time in seconds to allow NanoDrive to settle to correct position'),
                   ]),
        Parameter('automated_optimization',
                  [Parameter('automated_optimization_on', False, bool,
                             'turn on for automated optimization of the counts'),
                   Parameter('xstep', 0.1, float, 'step size in x direction'),
                   Parameter('ystep', 0.1, float, 'step size in y direction'),
                   Parameter('zstep', 0.1, float, 'step size in x direction'),
                   Parameter('settle_time', 2.0, float,
                             'Time in seconds to allow NanoDrive to settle to correct position'),
                   Parameter('min_retention_ratio', 0.5, float,
                             'Minimum retention ratio: if optimized counts<min_retention_ratio*highest counts, go back to highest counts position'),
                   Parameter('damping_ratio', 0.9, float, 'damping ratio: go to x+damping_ratio*∆x instead of x+∆x'),
                   Parameter('Continuous_optimization_on', False, bool,
                             'turn on for continuous automated optimization of the counts'),
                   Parameter('acceptable_counts', 2500000, float,
                             'acceptable counts reference to make sure that we do not update our highest counts if they are too high (not reasonable)'),
                   # this is to make sure that we don't run optimization when it is not necessary especially that the nanodrive drifts the more you move it
                   Parameter('acceptable_counts_ratio', 1.1, float,
                             'acceptable counts ratio reference to make sure that we do not update our highest counts if they are too high (not reasonable)'),
                   Parameter('min_reoptimize_ratio', 0.5, float,
                             'Minimum reoptimize ratio: if optimized counts<min_reoptimize_ratio*highest_counts, optimize again (this is only if Continuous_optimization_on is False)')
                   ]),
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
        trial_counter_path = get_adwin_binary_path('Averagable_Trial_Counter.TB1')
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
        # get the current xyz positions
        original_x = self.nd.read_probes('x_pos')
        original_y = self.nd.read_probes('y_pos')
        original_z = self.nd.read_probes('z_pos')
        print(f'nanodrive at x = {original_x}, y = {original_y}, z = {original_z}')

        sleep(0.1)  # time for stage to move and adwin process to initilize

        # determine if keyboard controls are on
        # if it is break out the parameters for keyboard tuning of the nanodrive
        if self.settings['keyboard_control_nanodrive']['keyboard_control_on']:
            keyboard_control_on = True
            x_neg_key = self.settings['keyboard_control_nanodrive']['x_neg_key']
            x_pos_key = self.settings['keyboard_control_nanodrive']['x_pos_key']
            x_step = self.settings['keyboard_control_nanodrive']['x_step']
            y_neg_key = self.settings['keyboard_control_nanodrive']['y_neg_key']
            y_pos_key = self.settings['keyboard_control_nanodrive']['y_pos_key']
            y_step = self.settings['keyboard_control_nanodrive']['y_step']
            z_neg_key = self.settings['keyboard_control_nanodrive']['z_neg_key']
            z_pos_key = self.settings['keyboard_control_nanodrive']['z_pos_key']
            z_step = self.settings['keyboard_control_nanodrive']['z_step']
            return_to_start_key = self.settings['keyboard_control_nanodrive']['return_to_start_key']
            settle_time = self.settings['keyboard_control_nanodrive']['settle_time']
        else:
            keyboard_control_on = False

        if self.settings['automated_optimization']['automated_optimization_on']:
            automated_optimization_on = True
            xstep = self.settings['automated_optimization']['xstep']
            ystep = self.settings['automated_optimization']['ystep']
            zstep = self.settings['automated_optimization']['zstep']
            settle_time = self.settings['keyboard_control_nanodrive']['settle_time']
            min_retention_ratio = self.settings['automated_optimization'][
                'min_retention_ratio']  # Minimum retention ratio: if optimized counts<min_retention_ratio*highest counts, go back to highest counts position
            damping_ratio = self.settings['automated_optimization']['damping_ratio']
            acceptable_counts = self.settings['automated_optimization']['acceptable_counts']
            acceptable_counts_ratio = self.settings['automated_optimization']['acceptable_counts_ratio']
            x_highest = self.nd.read_probes('x_pos')
            y_highest = self.nd.read_probes('y_pos')
            z_highest = self.nd.read_probes('z_pos')
            countsoriginal = self.adw.read_probes('int_var', id=1)  # read variable from adwin
            highest_counts = countsoriginal * 1e3 / self.settings['count_time']
            min_reoptimize_ratio = self.settings['automated_optimization']['min_reoptimize_ratio']
            if self.settings['automated_optimization']['Continuous_optimization_on']:
                Continuous_optimization_on = True
            else:
                Continuous_optimization_on = False
                # Minimum reoptimize ratio: if optimized counts<min_reoptimize_ratio*highest_counts, optimize again (this is only if Continuous_optimization_on is False)
        else:
            automated_optimization_on = False

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
                # if keyboard tuning is on, look for keyboard presses, and move nanodrive accordingly
                if keyboard_control_on:
                    if keyboard.is_pressed(x_neg_key):
                        self.nd.update({'x_pos': self.nd.read_probes('x_pos') - x_step})
                        sleep(settle_time)
                        print(f"x is decreased to {self.nd.read_probes('x_pos')}")
                    if keyboard.is_pressed(x_pos_key):
                        self.nd.update({'x_pos': self.nd.read_probes('x_pos') + x_step})
                        sleep(settle_time)
                        print(f"x is increased to {self.nd.read_probes('x_pos')}")
                    if keyboard.is_pressed(y_neg_key):
                        self.nd.update({'y_pos': self.nd.read_probes('y_pos') - y_step})
                        sleep(settle_time)
                        print(f"y is decreased to {self.nd.read_probes('y_pos')}")
                    if keyboard.is_pressed(y_pos_key):
                        self.nd.update({'y_pos': self.nd.read_probes('y_pos') + y_step})
                        sleep(settle_time)
                        print(f"y is increased to {self.nd.read_probes('y_pos')}")
                    if keyboard.is_pressed(z_neg_key):
                        self.nd.update({'z_pos': self.nd.read_probes('z_pos') - z_step})
                        sleep(settle_time)
                        print(f"z is decreased to {self.nd.read_probes('z_pos')}")
                    if keyboard.is_pressed(z_pos_key):
                        self.nd.update({'z_pos': self.nd.read_probes('z_pos') + z_step})
                        sleep(settle_time)
                        print(f"z is increased to {self.nd.read_probes('z_pos')}")
                    if keyboard.is_pressed(return_to_start_key):
                        self.nd.update({'x_pos': original_x, 'y_pos': original_y, 'z_pos': original_z})
                        sleep(10 * settle_time)
                        print(f"return_to_start_key is pressed. Moved to x = {self.nd.read_probes('x_pos')}, y = {self.nd.read_probes('y_pos')}, z = {self.nd.read_probes('z_pos')}")

                # Plot solution to make sure that the code and theory match
                # Play with parameters: step size and settle time
                # Go back 2 steps and then move in one direction to solve backlash
                # Add damping: x+ damping_ratio*∆x instead of x+∆x
                # Use: Try except to avoid crashing if there is an out of range error 
                # Skip optimization for certain axis if we get an out of range error: no assumptions
                # Go back to highest counts point if optimized counts are less than min_retention_ratio of the highest counts one 
                # 2 cases to run optimization: continuous optimization is on OR optimized_counts < min_reoptimize ratio * (original counts or highest_counts)
                # (User has to optimize manually (or with keyboard) and then add coordinates before restarting confocal point experiment with auto optimization:
                # This also ensures that we are getting counts from the same nanodiamond that we started measuring)
                if automated_optimization_on:
                    current_counts = (self.adw.read_probes('int_var', id=1) * 1e3) / self.settings['count_time']
                    print('current counts:', current_counts)
                    print('cutoff counts:', (min_reoptimize_ratio * highest_counts))
                    if Continuous_optimization_on or (
                            ((self.adw.read_probes('int_var', id=1) * 1e3) / self.settings['count_time']) < (
                            min_reoptimize_ratio * highest_counts)):
                        xminus, countsxminus = None, None
                        xpos, countsxold = None, None
                        xplus, countsxplus = None, None
                        yminus, countsyminus = None, None
                        ypos, countsyold = None, None
                        yplus, countsyplus = None, None
                        zminus, countszminus = None, None
                        zpos, countszold = None, None
                        zplus, countszplus = None, None
                        # x optimization
                        # go to x minus 2 steps (this way it solves backlash)
                        try:
                            self.nd.update({'x_pos': self.nd.read_probes('x_pos') - 2 * xstep})
                        except Exception as e:
                            if "ARGUMENT_ERROR" in str(e):
                                print(f"Warning: Skipping update due to out-of-range error: {e}")
                            else:
                                raise Exception
                        sleep(settle_time)
                        # increase x (this will be x minus)
                        try:
                            self.nd.update({'x_pos': self.nd.read_probes('x_pos') + xstep})
                            sleep(settle_time)
                            xminus = self.nd.read_probes('x_pos')
                            # read
                            x_counts = self.adw.read_probes('int_var', id=1)  # read variable from adwin
                            countsxminus = x_counts * 1e3 / self.settings['count_time']
                        except Exception as e:
                            if "ARGUMENT_ERROR" in str(e):
                                print(f"Warning: Skipping update due to out-of-range error: {e}")
                            else:
                                raise Exception
                        # increase x (this will be x old)
                        try:
                            self.nd.update({'x_pos': self.nd.read_probes('x_pos') + xstep})
                            sleep(settle_time)
                            xpos = self.nd.read_probes('x_pos')
                            # read
                            x_counts = self.adw.read_probes('int_var', id=1)  # read variable from adwin
                            countsxold = x_counts * 1e3 / self.settings['count_time']
                        except Exception as e:
                            if "ARGUMENT_ERROR" in str(e):
                                print(f"Warning: Skipping update due to out-of-range error: {e}")
                            else:
                                raise Exception
                        # increase x (this will be x plus)
                        try:
                            self.nd.update({'x_pos': self.nd.read_probes('x_pos') + xstep})
                            sleep(settle_time)
                            xplus = self.nd.read_probes('x_pos')
                            # read
                            x_counts = self.adw.read_probes('int_var', id=1)  # read variable from adwin
                            countsxplus = x_counts * 1e3 / self.settings['count_time']
                        except Exception as e:
                            if "ARGUMENT_ERROR" in str(e):
                                print(f"Warning: Skipping update due to out-of-range error: {e}")
                            else:
                                raise Exception
                        # find max:
                        x_points = [(xminus, countsxminus), (xpos, countsxold), (xplus, countsxplus)]
                        x_points_valid = [(x, c) for (x, c) in x_points if x is not None and c is not None]

                        if len(x_points_valid) < 3:
                            print("Skipping x-optimization: insufficient valid points.")
                        else:
                            x_pos_coords = np.array([p[0] for p in x_points])
                            x_count_coords = np.array([p[1] for p in x_points])
                            x_coefficients = np.polyfit(x_pos_coords, x_count_coords, 2)
                            ax, bx, cx = x_coefficients
                            # a * x**2 + b * x + c
                            xmax = float((-bx) / (2 * ax))
                            # x_counts = self.adw.read_probes('int_var', id=1)  #remove comment if you need to plot xyz
                            # countsxmax = x_counts * 1e3 / self.settings['count_time'] #remove comment if you need to plot xyz
                            try:
                                self.nd.update({'x_pos': xmax})
                                sleep(settle_time)
                                xmax = self.nd.read_probes('x_pos')
                                x_counts = self.adw.read_probes('int_var', id=1)  # read variable from adwin
                                countsxmax = x_counts * 1e3 / self.settings['count_time']
                            except Exception as e:
                                if "ARGUMENT_ERROR" in str(e):
                                    print(f"Warning: Skipping update due to out-of-range error: {e}")
                                else:
                                    raise Exception
                            # last position measured is x max so we will move from x max
                            if (countsxminus > countsxmax):
                                try:
                                    self.nd.update({'x_pos': xmax + (damping_ratio * (xminus - xmax))})
                                except Exception as e:
                                    if "ARGUMENT_ERROR" in str(e):
                                        print(f"Warning: Skipping update due to out-of-range error: {e}")
                                    else:
                                        raise Exception
                            elif (countsxold > countsxmax):
                                try:
                                    self.nd.update({'x_pos': xmax + (damping_ratio * (xpos - xmax))})
                                except Exception as e:
                                    if "ARGUMENT_ERROR" in str(e):
                                        print(f"Warning: Skipping update due to out-of-range error: {e}")
                                    else:
                                        raise Exception
                            elif (countsxplus > countsxmax):
                                try:
                                    self.nd.update({'x_pos': xmax + (damping_ratio * (xplus - xmax))})
                                except Exception as e:
                                    if "ARGUMENT_ERROR" in str(e):
                                        print(f"Warning: Skipping update due to out-of-range error: {e}")
                                    else:
                                        raise Exception
                            sleep(settle_time)

                        # y optimization
                        # decrease y by 2
                        try:
                            self.nd.update({'y_pos': self.nd.read_probes('y_pos') - 2 * ystep})
                        except Exception as e:
                            if "ARGUMENT_ERROR" in str(e):
                                print(f"Warning: Skipping update due to out-of-range error: {e}")
                            else:
                                raise Exception
                        sleep(settle_time)
                        # increase y (this will be y minus)
                        try:
                            self.nd.update({'y_pos': self.nd.read_probes('y_pos') + ystep})
                            sleep(settle_time)
                            yminus = self.nd.read_probes('y_pos')
                            # read
                            y_counts = self.adw.read_probes('int_var', id=1)  # read variable from adwin
                            countsyminus = y_counts * 1e3 / self.settings['count_time']
                        except Exception as e:
                            if "ARGUMENT_ERROR" in str(e):
                                print(f"Warning: Skipping update due to out-of-range error: {e}")
                            else:
                                raise Exception
                        # increase y (this will be y old)
                        try:
                            self.nd.update({'y_pos': self.nd.read_probes('y_pos') + ystep})
                            sleep(settle_time)
                            ypos = self.nd.read_probes('y_pos')
                            # read
                            y_counts = self.adw.read_probes('int_var', id=1)  # read variable from adwin
                            countsyold = y_counts * 1e3 / self.settings['count_time']
                        except Exception as e:
                            if "ARGUMENT_ERROR" in str(e):
                                print(f"Warning: Skipping update due to out-of-range error: {e}")
                            else:
                                raise Exception
                        # increase y (this will be y plus)
                        try:
                            self.nd.update({'y_pos': self.nd.read_probes('y_pos') + ystep})
                            sleep(settle_time)
                            yplus = self.nd.read_probes('y_pos')
                            # read
                            y_counts = self.adw.read_probes('int_var', id=1)  # read variable from adwin
                            countsyplus = y_counts * 1e3 / self.settings['count_time']
                        except Exception as e:
                            if "ARGUMENT_ERROR" in str(e):
                                print(f"Warning: Skipping update due to out-of-range error: {e}")
                            else:
                                raise Exception
                        # find max:
                        y_points = [(yminus, countsyminus), (ypos, countsyold), (yplus, countsyplus)]
                        y_points_valid = [(y, c) for (y, c) in y_points if y is not None and c is not None]

                        if len(y_points_valid) < 3:
                            print("Skipping y-optimization: insufficient valid points.")
                        else:
                            y_pos_coords = np.array([p[0] for p in y_points])
                            y_count_coords = np.array([p[1] for p in y_points])
                            y_coefficients = np.polyfit(y_pos_coords, y_count_coords, 2)
                            ay, by, cy = y_coefficients
                            # a * x**2 + b * x + c
                            ymax = float((-by) / (2 * ay))
                            # y_counts = self.adw.read_probes('int_var', id=1)  #remove comment if you need to plot xyz
                            # countsymax = y_counts * 1e3 / self.settings['count_time'] #remove comment if you need to plot xyz
                            try:
                                self.nd.update({'y_pos': ymax})
                                sleep(settle_time)
                                ymax = self.nd.read_probes('y_pos')
                                y_counts = self.adw.read_probes('int_var', id=1)  # read variable from adwin
                                countsymax = y_counts * 1e3 / self.settings['count_time']
                            except Exception as e:
                                if "ARGUMENT_ERROR" in str(e):
                                    print(f"Warning: Skipping update due to out-of-range error: {e}")
                                else:
                                    raise Exception
                            # last position measured is y max so we will move from y max
                            if (countsyminus > countsymax):
                                try:
                                    self.nd.update({'y_pos': ymax + (damping_ratio * (yminus - ymax))})
                                except Exception as e:
                                    if "ARGUMENT_ERROR" in str(e):
                                        print(f"Warning: Skipping update due to out-of-range error: {e}")
                                    else:
                                        raise Exception
                            elif (countsyold > countsymax):
                                try:
                                    self.nd.update({'y_pos': ymax + (damping_ratio * (ypos - ymax))})
                                except Exception as e:
                                    if "ARGUMENT_ERROR" in str(e):
                                        print(f"Warning: Skipping update due to out-of-range error: {e}")
                                    else:
                                        raise Exception
                            elif (countsyplus > countsymax):
                                try:
                                    self.nd.update({'y_pos': ymax + (damping_ratio * (yplus - ymax))})
                                except Exception as e:
                                    if "ARGUMENT_ERROR" in str(e):
                                        print(f"Warning: Skipping update due to out-of-range error: {e}")
                                    else:
                                        raise Exception
                            sleep(settle_time)
                        # z optimization
                        # decrease z 2 steps
                        try:
                            self.nd.update({'z_pos': self.nd.read_probes('z_pos') - 2 * zstep})
                        except Exception as e:
                            if "ARGUMENT_ERROR" in str(e):
                                print(f"Warning: Skipping update due to out-of-range error: {e}")
                            else:
                                raise Exception
                        sleep(settle_time)
                        # increase z (this will be z minus)
                        try:
                            self.nd.update({'z_pos': self.nd.read_probes('z_pos') + zstep})
                            sleep(settle_time)
                            zminus = self.nd.read_probes('z_pos')
                            # read
                            z_counts = self.adw.read_probes('int_var', id=1)  # read variable from adwin
                            countszminus = z_counts * 1e3 / self.settings['count_time']
                        except Exception as e:
                            if "ARGUMENT_ERROR" in str(e):
                                print(f"Warning: Skipping update due to out-of-range error: {e}")
                            else:
                                raise Exception
                        # increase z (this will be z old)
                        try:
                            self.nd.update({'z_pos': self.nd.read_probes('z_pos') + zstep})
                            sleep(settle_time)
                            zpos = self.nd.read_probes('z_pos')
                            # read
                            z_counts = self.adw.read_probes('int_var', id=1)  # read variable from adwin
                            countszold = z_counts * 1e3 / self.settings['count_time']
                        except Exception as e:
                            if "ARGUMENT_ERROR" in str(e):
                                print(f"Warning: Skipping update due to out-of-range error: {e}")
                            else:
                                raise Exception
                        # increase z (this will be z plus)
                        try:
                            self.nd.update({'z_pos': self.nd.read_probes('z_pos') + zstep})
                            sleep(settle_time)
                            zplus = self.nd.read_probes('z_pos')
                            # read
                            z_counts = self.adw.read_probes('int_var', id=1)  # read variable from adwin
                            countszplus = z_counts * 1e3 / self.settings['count_time']
                        except Exception as e:
                            if "ARGUMENT_ERROR" in str(e):
                                print(f"Warning: Skipping update due to out-of-range error: {e}")
                            else:
                                raise Exception
                        # find max:
                        z_points = [(zminus, countszminus), (zpos, countszold), (zplus, countszplus)]
                        z_points_valid = [(z, c) for (z, c) in z_points if z is not None and c is not None]

                        if len(z_points_valid) < 3:
                            print("Skipping z-optimization: insufficient valid points.")
                        else:
                            z_pos_coords = np.array([p[0] for p in z_points])
                            z_count_coords = np.array([p[1] for p in z_points])
                            z_coefficients = np.polyfit(z_pos_coords, z_count_coords, 2)
                            az, bz, cz = z_coefficients
                            # a * z**2 + b * z + c
                            zmax = float((-bz) / (2 * az))
                            # z_counts = self.adw.read_probes('int_var', id=1)  # read variable from adwin
                            # countszmax = z_counts * 1e3 / self.settings['count_time']
                            try:
                                self.nd.update({'z_pos': zmax})
                                sleep(settle_time)
                                zmax = self.nd.read_probes('z_pos')
                                z_counts = self.adw.read_probes('int_var', id=1)  # read variable from adwin
                                countszmax = z_counts * 1e3 / self.settings['count_time']
                            except Exception as e:
                                if "ARGUMENT_ERROR" in str(e):
                                    print(f"Warning: Skipping update due to out-of-range error: {e}")
                                else:
                                    raise Exception
                            # last position measured is zmax so we will move from zmax
                            if (countszminus > countszmax):
                                try:
                                    self.nd.update({'z_pos': zmax + (damping_ratio * (zminus - zmax))})
                                except Exception as e:
                                    if "ARGUMENT_ERROR" in str(e):
                                        print(f"Warning: Skipping update due to out-of-range error: {e}")
                                    else:
                                        raise Exception
                            elif (countszold > countszmax):
                                try:
                                    self.nd.update({'z_pos': zmax + (damping_ratio * (zpos - zmax))})
                                except Exception as e:
                                    if "ARGUMENT_ERROR" in str(e):
                                        print(f"Warning: Skipping update due to out-of-range error: {e}")
                                    else:
                                        raise Exception
                            elif (countszplus > countszmax):
                                try:
                                    self.nd.update({'z_pos': zmax + (damping_ratio * (zplus - zmax))})
                                except Exception as e:
                                    if "ARGUMENT_ERROR" in str(e):
                                        print(f"Warning: Skipping update due to out-of-range error: {e}")
                                    else:
                                        raise Exception
                            sleep(settle_time)
                        # Check if optimized counts<min_retention_ratio*highest counts, go back to highest counts position
                        optimized_counts = (self.adw.read_probes('int_var', id=1) * 1e3) / self.settings['count_time']
                        if optimized_counts > highest_counts:
                            if optimized_counts < acceptable_counts * acceptable_counts_ratio:
                                highest_counts = optimized_counts
                                x_highest = self.nd.read_probes('x_pos')
                                y_highest = self.nd.read_probes('y_pos')
                                z_highest = self.nd.read_probes('z_pos')
                                # the above section makes sure that the highest_counts can only be updated if they are reasonable (if they are higher than expected, they are probably just a fluctuation and therefore, they won't be a good reference)
                        elif optimized_counts < (min_retention_ratio * highest_counts):
                            xpos = self.nd.read_probes('x_pos')
                            ypos = self.nd.read_probes('y_pos')
                            zpos = self.nd.read_probes('z_pos')
                            self.nd.update({'x_pos': xpos + damping_ratio * (x_highest - xpos),
                                            'y_pos': ypos + damping_ratio * (y_highest - ypos),
                                            'z_pos': zpos + damping_ratio * (z_highest - zpos)})
                            sleep(settle_time)

                        """
                        # PyQtGraph plot setup
                        app = QApplication(sys.argv)
                        win = pg.plot(title="XMAX")
                        win.setLabel('bottom', 'x')
                        win.setLabel('left', 'f(x)')
                        win.showGrid(x=True, y=True)

                        # plot polyfit curve
                        x_range = np.linspace(min(x_pos_coords) - 2, max(x_pos_coords) + 2, 200)
                        y_fit = np.polyval(x_coefficients, x_range)
                        win.plot(x_range, y_fit, pen=pg.mkPen('w', width=2), name="Polyfit")

                        # plot sampled red points
                        win.plot(x_pos_coords, x_count_coords, pen=None, symbol='o', symbolBrush='r', symbolSize=10, name="Sampled points")

                        # plot xmax yellow point
                        win.plot([xmax], [countsxmax], pen=None, symbol='o', symbolBrush='y', symbolPen='w', symbolSize=12, name="xmax")

                        # PyQtGraph plot setup
                        win2 = pg.plot(title="YMAX")
                        win2.setLabel('bottom', 'y')
                        win2.setLabel('left', 'f(y)')
                        win2.showGrid(x=True, y=True)

                        # plot polyfit curve
                        y_range = np.linspace(min(y_pos_coords) - 2, max(y_pos_coords) + 2, 200)
                        y_fit = np.polyval(y_coefficients, y_range)
                        win2.plot(y_range, y_fit, pen=pg.mkPen('w', width=2), name="Polyfit")

                        # plot sampled red points
                        win2.plot(y_pos_coords, y_count_coords, pen=None, symbol='o', symbolBrush='r', symbolSize=10,
                                 name="Sampled points")

                        # plot ymax yellow point
                        win2.plot([ymax], [countsymax], pen=None, symbol='o', symbolBrush='y', symbolPen='w', symbolSize=12,
                                 name="ymax")

                        # PyQtGraph plot setup
                        win3 = pg.plot(title="ZMAX")
                        win3.setLabel('bottom', 'z')
                        win3.setLabel('left', 'f(z)')
                        win3.showGrid(x=True, y=True)

                        # plot polyfit curve
                        z_range = np.linspace(min(z_pos_coords) - 2, max(z_pos_coords) + 2, 200)
                        z_fit = np.polyval(z_coefficients, z_range)
                        win3.plot(z_range, z_fit, pen=pg.mkPen('w', width=2), name="Polyfit")

                        # plot sampled red points
                        win3.plot(z_pos_coords, z_count_coords, pen=None, symbol='o', symbolBrush='r', symbolSize=10,
                                  name="Sampled points")

                        # plot zmax yellow point
                        win3.plot([zmax], [countszmax], pen=None, symbol='o', symbolBrush='y', symbolPen='w', symbolSize=12,
                                  name="zmax")
                        sys.exit(app.exec_())
                        return
                    """
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