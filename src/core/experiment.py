# Created by Gurudev Dutt <gdutt@pitt.edu> on 2023-07-27
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

import datetime
from copy import deepcopy
import traceback

from src.core.device import Device
from src.core.parameter import Parameter
from src.core.read_write_functions import save_aqs_file, load_aqs_file
from src.core.helper_functions import module_name_from_path, MatlabSaver

from collections import deque
import os
import sys
import pandas as pd
import glob
import inspect
import warnings
import platform
from PyQt5.QtCore import pyqtSignal, QObject, pyqtSlot
from scipy.io import savemat

import numpy as np
from builtins import len as builtin_len
from matplotlib.backends.backend_pdf import \
    FigureCanvasPdf as FigureCanvas  # use this to avoid error that plotting should only be done on main thread
from matplotlib.figure import Figure
from importlib import import_module

import pyqtgraph as pg
from pyqtgraph.exporters import ImageExporter

# cPickle module implements the same algorithm as pickle, in C instead of Python.
# It is many times faster than the Python implementation, but does not allow the user to subclass from Pickle.
import pickle


class Experiment(QObject):
    # This is the signal that will be emitted during the processing.
    # By including int as an argument, it lets the signal know to expect
    # an integer argument when emitting. these must all be defined at the class level
    updateProgress = pyqtSignal(int)  # emits a progress update in percent
    started = pyqtSignal()  # signals the begin of the experiment
    finished = pyqtSignal()  # signals the end of the experiment

    _DEFAULT_SETTINGS = [
        Parameter('path', '', str, 'path to folder where data is saved'),
        Parameter('tag', 'default_tag'),
        Parameter('save', False, bool, 'check to automatically save data'),
    ]

    RAW_DATA_DIR = 'raw_data'  # dir name for rawdata
    SUBEXPERIMENT_DATA_DIR = 'subexperiments_data'  # dir name for subexperiment data

    def __init__(self, name=None, settings=None, devices=None, sub_experiments =None, log_function=None, data_path=None):
        """
        executes experiments and stores experiment parameters and settings
        Args:
            name (optional):  name of experiment, if not provided take name of function
            settings (optional): a Parameter object that contains all the information needed in the experiment
            devices (optional): pass in a dictionary with instances of the devices used in the experiment, e.g. {"mw":SRS386()}
            sub_experiments (optional):  sub_experiments used in the experiment
            log_function(optional): function reference that takes a string
        """
        QObject.__init__(self) # must call this way for pyqtSignal and pyqtSlot
        #super().__init__(self)

        self._experiment_class = self.__class__.__name__
        print('experiment_class',self._experiment_class)

        if name is None:
            name = self.__class__.__name__
        self.name = name

        self._devices = {}
        if devices is None:
            devices = {}
        else:
            assert isinstance(devices, dict)
            assert set(self._DEVICES.keys()) <= set(devices.keys())

        self.data_path = data_path
        # GD 20230817: had to change the line below to directly assign to self._devices rather than self.devices
        # self.devices = {key: devices[key] for key in list(devices.keys())}
        self._devices = {key: devices[key] for key in list(devices.keys())}
        # debugging lines below , commented out after it looks like things are working
        # debug_devs = {key: devices[key] for key in list(devices.keys())}
        # print("Debugging devices....",debug_devs)
        #self.devices = devices

        self._experiments = {}
        if sub_experiments is None:
            sub_experiments = {}
        self.experiments = sub_experiments

        # set end time to be before start time -- tells us if experiment hasn't been excecuted
        self.start_time = datetime.datetime.now()
        self.end_time = self.start_time - datetime.timedelta(seconds=1)

        self._settings = deepcopy(Parameter(self._DEFAULT_SETTINGS + Experiment._DEFAULT_SETTINGS))
        self._settings.update({'tag': self.name.lower()})
        if settings is not None:
            self.update(settings)
        self._abort = False
        self.is_running = False

        # data hold the data generated by the experiment,
        # this should either be a dictionary or a deque of dictionaries
        self.data = {}

        # a log for status outputs
        self.log_data = deque()
        # this can be overwritten
        self.log_function = log_function

        # default value is 'none', overwrite this in experiment if it has plotting capabilities
        self._plot_refresh = True

        self.progress = None

        self._current_subexperiment_stage = {
            'current_subexperiment': None,
            'subexperiment_exec_count': {},
            'subexperiment_exec_duration': {}
        }


    @property
    def data_path(self):
        return self._data_path

    @data_path.setter
    def data_path(self, path):
        # check is path is a valid path string
        # if path is not None and path is not '':
        #     if not os.path.isdir(path):
        #         print('{:s} created'.format(path))
        #         os.makedirs(path)

        self._data_path = path

    @pyqtSlot(bool)
    def _set_current_subexperiment(self, active):
        """
        sets the current subexperiment and keeps a counter of how ofter a particular subexperiment has been executed
        this information is usefull when implementing a status update or plotting functions that depend on which subexperiment is being executed

        keeps track of the following dictionary:
        self._current_subexperiment_stage = {
            'current_subexperiment' : reference to the current subscrit
            'subexperiment_exec_count' : dictionary where key is the subexperiment name and value how often is has been executed
            'subexperiment_exec_duration' : dictionary where key is the subexperiment name and value the average duration of executing the subexperiment
        }

        Args:
            active: True if the current subexperiment is just started, False if it just finished
        """

        current_subexperiment = self.sender()

        if active:
            for subexperiment_name in list(self._current_subexperiment_stage['subexperiment_exec_count'].keys()):
                if subexperiment_name == current_subexperiment.name:
                    self._current_subexperiment_stage['subexperiment_exec_count'][subexperiment_name] += 1
            self._current_subexperiment_stage['current_subexperiment'] = current_subexperiment
        else:
            self._current_subexperiment_stage['current_subexperiment'] = current_subexperiment
            for subexperiment_name in list(self._current_subexperiment_stage['subexperiment_exec_count'].keys()):
                # calculate the average duration to execute the subexperiment
                if subexperiment_name == current_subexperiment.name:
                    duration = current_subexperiment.end_time - current_subexperiment.start_time
                    if subexperiment_name in self._current_subexperiment_stage['subexperiment_exec_duration']:
                        duration_old = self._current_subexperiment_stage['subexperiment_exec_duration'][subexperiment_name]
                    else:
                        duration_old = datetime.timedelta(0)
                    exec_count = self._current_subexperiment_stage['subexperiment_exec_count'][subexperiment_name]

                    duration_new = (duration_old * (exec_count - 1) + duration)
                    self._current_subexperiment_stage['subexperiment_exec_duration'][subexperiment_name] = (duration_old * (
                            exec_count - 1) + duration) / exec_count

    def _function(self):
        """
        This is the actual function that will be executed. It uses only information that is provided in the settings property
        will be overwritten in the __init__
        """
        # some generic function
        raise NotImplementedError

    # todo: 20230801GD (search for this to find related todos)
    # make this a slot
    # @pyqtSlot(bool)
    def log(self, string):
        """
        appends input string to log file and sends it to log function (self.log_function)
        Returns:

        """

        self.log_data.append(string)
        if self.log_function is None:
            print(string)
        else:
            self.log_function(string)

    # @property
    # def _DEFAULT_SETTINGS(self):
    #     """
    #     returns the default parameter_list of the experiment this function should be over written in any subclass
    #     """
    #     raise NotImplementedError("Subclass did not implement _DEFAULT_SETTINGS")

    @property
    def _DEVICES(self):
        """

        Returns: a dictionary of the devices, where key is the device name and value is the device class
        if there is not device it should return an empty dict

        """
        raise NotImplementedError("Subclass did not implement _DEVICES")

    @property
    def _EXPERIMENTS(self):
        """

        Returns: a dictionary of the experiments, where the key is the experiment name and value is the experiment class
        if there is not experiment it should return an empty dict

        """
        raise NotImplementedError("Subclass did not implement _EXPERIMENTS")

    def __str__(self):
        """
        :return: a description of the experiment in form of a string
        """

        output_string = '{:s} (class type: {:s})\n'.format(self.name, self.__class__.__name__)

        output_string += 'settings:\n'
        for key, value in self.settings.items():
            output_string += "{:s} : {:s}\n".format(key, str(value))
        return output_string

    @property
    def name(self):
        """
        experiment name
        """
        return self._name

    @name.setter
    def name(self, value):
        if isinstance(value, str):
            value = str(value)

        assert isinstance(value, str), str(value) + ' is not a string'
        self._name = value

    @property
    def devices(self):
        """
        :return: devices that the experiment uses as a dictionary
        """
        return self._devices

    @devices.setter
    def devices(self, device_dict):
        assert isinstance(device_dict, dict)
        # checks if all the keys in _DEVICES are contained in device_dict
        assert set(self._DEVICES.keys()) <= set(
            device_dict.keys()), "{:s}: needs devices {:s} but received {:s}".format(self.name, str(list(
            self._DEVICES.keys())), str(list(device_dict.keys())))
        for key, value in self._DEVICES.items():
            self._devices.update({key: device_dict[key]})

    @property
    def experiments(self):
        """
        :return: sub_experiments that the experiment uses as a dictionary
        """
        return self._experiments

    @experiments.setter
    def experiments(self, experiment_dict):
        assert isinstance(experiment_dict, dict)
        assert set(experiment_dict.keys()) == set(self._EXPERIMENTS.keys()), "{:s}: set subexperiments {:s}, received {:s}".format(
            self.name, str(list(experiment_dict.keys())), str(list(self._EXPERIMENTS.keys())))

        for key, value in self._EXPERIMENTS.items():
            #assert isinstance(experiment_dict[key], self._EXPERIMENTS[key])
            self._experiments.update({key: experiment_dict[key]})

    @property
    def settings(self):
        '''
        :return: returns the settings of the experiment
        settings contain Parameters, devices and experiments
        '''
        return self._settings

    def update(self, settings):
        '''
        updates the internal dictionary
        Args:
            settings: parameters to be set
        # mabe in the future:
        # Returns: boolean that is true if update successful

        '''
        if 'settings' in settings:
            self._settings.update(settings['settings'])
        else:
            self._settings.update(settings)

        if 'devices' in settings:
            for device_name, device_setting in settings['devices'].items():
                self.devices[device_name]['settings'].update(device_setting['settings'])

        if 'experiments' in settings:
            for experiment_name, experiment_setting in settings['experiments'].items():
                self.experiments[experiment_name].update(experiment_setting)

    @property
    def end_time(self):
        """
        time when experiment execution ended
        :return:
        """
        return self._time_stop

    @end_time.setter
    def end_time(self, value):
        assert isinstance(value, datetime.datetime)
        self._time_stop = value

    @property
    def remaining_time(self):
        """
        estimates the time remaining until experiment is finished
        """
        elapsed_time = (datetime.datetime.now() - self.start_time).total_seconds()
        # safety to avoid devision by zero
        if self.progress == 0:
            self.progress = 1

        estimated_total_time = 100. / self.progress * elapsed_time

        return datetime.timedelta(seconds=max(estimated_total_time - elapsed_time, 0))

    @property
    def start_time(self):
        """
        time when experiment execution started
        """
        return self._time_start

    @start_time.setter
    def start_time(self, value):
        assert isinstance(value, datetime.datetime)
        self._time_start = value

    @property
    def excecution_time(self):
        """
        :return: experiment excecition time as time_delta object to get time in seconds use .total_seconds()
        """
        return self.end_time - self.start_time

    @pyqtSlot(int)
    def _receive_signal(self, progress):
        """
        this function takes care of signals emitted by the subexperiments
        the default behaviour is that it just reemits the signal
        Args:
            progress: progress of subexperiment
        """
        # print(datetime.datetime.now().strftime("%B %d, %Y %H:%M:%S"), self.name,QtCore.QThread.currentThread(), self._current_subexperiment_stage['current_subexperiment'].name,
        #       'received signal. emitting....')

        self.progress = progress
        self.updateProgress.emit(progress)

    def run(self):
        """
        executes the experiment
        :return: boolean if execution of experiment finished succesfully
        """
        self.log_data.clear()
        self._plot_refresh = True  # flag that requests that plot axes are refreshed when self.plot is called next time
        self.is_running = True
        self.start_time = datetime.datetime.now()

        self._current_subexperiment_stage = {
            'current_subexperiment': None,
            'subexperiment_exec_count': {},
            'subexperiment_exec_duration': {}
        }

        # update the datapath of the subexperiments, connect their progress signal to the receive slot
        for subexperiment in list(self.experiments.values()):
            subexperiment.data_path = os.path.join(self.filename(create_if_not_existing=False), self.SUBEXPERIMENT_DATA_DIR)
            subexperiment.updateProgress.connect(self._receive_signal)
            subexperiment.started.connect(lambda: self._set_current_subexperiment(True))
            subexperiment.finished.connect(lambda: self._set_current_subexperiment(False))
            self._current_subexperiment_stage['subexperiment_exec_count'].update({subexperiment.name: 0})
            self._current_subexperiment_stage['subexperiment_exec_duration'].update({subexperiment.name: datetime.timedelta(0)})

            # todo: 20230801GD (search for this to find related todos) need to test this:
            # do we need to connect the log functions of the subexperiment to the mother experiment?, e.g
            # subexperiment.log.connect(self.log)

        self.log('starting experiment {:s} at {:s} on {:s}'.format(self.name, self.start_time.strftime('%H:%M:%S'),
                                                               self.start_time.strftime('%d/%m/%y')))
        self._abort = False

        # saves standard to disk
        if self.settings['save']:
            self.save_aqs()

        self.started.emit()

        self._function()
        self.end_time = datetime.datetime.now()
        self.log('experiment {:s} finished at {:s} on {:s}'.format(self.name, self.end_time.strftime('%H:%M:%S'),
                                                               self.end_time.strftime('%d/%m/%y')))

        # saves standard to disk
        if self.settings['save']:
            self.save_data()
            self.save_log()
            self.save_image_to_disk()
            self.save_data_to_matlab()

        success = not self._abort

        # disconnect subexperiments
        for subexperiment in list(self.experiments.values()):
            subexperiment.started.disconnect()
            subexperiment.updateProgress.disconnect()
            subexperiment.finished.disconnect()
        self.is_running = False
        self.finished.emit()

    def stop(self):
        """
        stops itself and all the subexperiment
        """
        for subexperiment in list(self.experiments.values()):
            subexperiment.stop()
        print(('--- stopping: ', self.name))
        self._abort = True

    def is_valid(self):
        """
        function to validate of the experiment parameters are valid:
         - check if the filename is too long (pandas can't write files if the total filepath is longer than 259 characters)

        :return: boolean
        """
        # validate = True
        # # check if filename is longer than 220, this leaves a buffer of 39 for dynamically created extentions
        # if len(self.filename()) > 220:
        #     validate = False
        #     self.log('Validation failed. Detected long filename in ', self.name)
        #
        # for s in self.experiments:
        #     if s.validate == False:
        #         validate = False
        #
        # return validate
        pass

    def filename(self, appendix=None, create_if_not_existing=False):
        """
        creates a filename based
        Args:
            appendix: appendix for file

        Returns: filename

        """

        # if provided path is a relative path and self.data_path exists, build path
        if os.path.isabs(self.settings['path']) == False and self.data_path is not None:
            path = os.path.join(self.data_path, self.settings['path'])
        else:
            path = self.settings['path']

        tag = self.settings['tag']  # .replace('.','-')

        filename = os.path.join(path, "{:s}_{:s}".format(self.start_time.strftime('%y%m%d-%H_%M_%S'), tag))

        if os.path.exists(filename) == False and create_if_not_existing:
            os.makedirs(filename)

        if appendix is not None:
            filename = os.path.join(filename,
                                    "{:s}_{:s}{:s}".format(self.start_time.strftime('%y%m%d-%H_%M_%S'), tag, appendix))

        # windows can't deal with long filenames so we have to use the prefix '\\\\?\\'
        # if len(filename.split('\\\\?\\')) == 1:
        #     filename = '\\\\?\\' + filename

        return filename

    @staticmethod
    def check_filename(filename):
        if os.name == 'nt':
            if builtin_len(filename) >= 256 and not filename[0:4] == '\\\\?\\':
                # when using this long filename prefix, we must use only \ slashes as windows handles these differently
                filename = os.path.normpath(filename)
                filename = '\\\\?\\' + filename
        return filename

    def to_dict(self):
        """

        Returns: itself as a dictionary

        """

        from src.core.experiment_iterator import ExperimentIterator

        if 'experiment_iterator' in self.__module__.split('.'):
            # experiment iterator module is of the form
            # 'AQuISS.src.core.experiment_iterator.dynamic_experiment_iterator0'
            # and the class name if of the form package.dynamic_experiment_iterator0
            package = self.__class__.__name__.split('.')[0]
        else:
            # if it is not a experiment iterator the package is the highest level of the module
            package = self.__module__.split('.')[0]

        dictator = {self.name: {
            'class': self.__class__.__name__,
            'filepath': inspect.getfile(self.__class__),
            'info': self.__doc__,
            'package': package
        }}


        # if isinstance(self, ExperimentIterator):
        #     dictator['filepath'] = inspect.getfile(self.__class__),

        if self.experiments != {}:
            dictator[self.name].update({'experiments': {}})
            for subexperiment_name, subexperiment in self.experiments.items():
                dictator[self.name]['experiments'].update(subexperiment.to_dict())

        if self.devices != {}:
            # dictator[self.name].update({'devices': self.devices})
            # dictator[self.name].update({'devices': {} })
            # for device_name, device in self.devices.iteritems():
            #     dictator[self.name]['devices'].update(device.to_dict())

            dictator[self.name].update({'devices': {
                device_name: {'class': device['instance'].__class__.__name__,
                                  'settings': device['settings']}
                for device_name, device in self.devices.items()
            }})

        dictator[self.name]['settings'] = self.settings

        return dictator

    def save_data(self, filename=None, data_tag=None, verbose=False):
        """
        saves the experiment data to a file
        filename: target filename, if not provided, it is created from internal function
        data_tag: string, if provided save only the data that matches the tag, otherwise save all data
        verbose: if true print additional info to std out
        Returns:

        """

        def len(x):
            """
            overwrite the buildin len function to cover cases that don't have a length, like int or float
            and to catch string as objects of length 0
            Args:
                x: quantity of which we want to find the length
            Returns: length of x

            """
            if isinstance(x, (int, float, str)) or x is None:
                result = 0
            else:
                result = builtin_len(x)
            return result

        if filename is None:
            filename = self.filename('.csv')

        filename = os.path.join(os.path.join(os.path.dirname(filename), self.RAW_DATA_DIR), os.path.basename(filename))

        # windows can't deal with long filenames so we have to use the prefix '\\\\?\\'
        # if len(filename.split('\\\\?\\')) == 1:
        filename = self.check_filename(filename)

        if not os.path.exists(os.path.dirname(filename)):
            os.makedirs(os.path.dirname(filename))

        # if deque object, take the last dataset, which is the most recent
        if isinstance(self.data, deque):
            data = self.data[-1]
        elif isinstance(self.data, dict):
            data = self.data
        else:
            raise TypeError("experiment data variable has an invalid datatype! Must be deque or dict.")

        if data_tag is None:
            if verbose:
                print('data_tag is None')

            if len(set([len(v) for v in list(data.values())])) == 1 and set(
                    [len(np.shape(list(data.values())[i])) for i in range(len(list(data.values())))]) == set([0, 1]):
                # if all entries of the dictionary are the same length and single column we can write the data into a single file

                if len(np.shape(list(data.values())[0])) == 1:
                    df = pd.DataFrame(data)
                else:
                    df = pd.DataFrame.from_records([data])

                if len(df) == 0 or df.empty:
                    print('warning! Data seems to be empty. Not saved', df)
                else:
                    df.to_csv(filename, index=False)

            else:
                # otherwise, we write each entry into a separate file
                for key, value in data.items():

                    if verbose:
                        print('current data', key)

                    if len(value) == 0:
                        df = pd.DataFrame([value])
                    else:
                        if isinstance(value, dict) and isinstance(list(value.values())[0], (int, float)):
                            # if dictionary values are single numbers
                            df = pd.DataFrame.from_dict({k: [v] for k, v in value.items()})
                        elif isinstance(value, dict) and isinstance(list(value.values())[0], (list, np.ndarray)):
                            # if dictionary values are lists or arrays
                            df = pd.DataFrame.from_dict(value)
                        else:
                            # if not a dictionary
                            df = pd.DataFrame(value)

                    if len(df) == 0 or df.empty:
                        print('warning! Data ({:s}) seems to be empty. Not saved'.format(key), df)
                    else:
                        df.to_csv(filename.replace('.csv', '-{:s}.csv'.format(key)), index=False)

        else:

            # save only the data for which a key has been provided
            assert data_tag in list(data.keys())

            if verbose:
                print('data_tag', data_tag)

            value = data[data_tag]
            if len(value) == 0:
                df = pd.DataFrame([value])
            else:
                df = pd.DataFrame(value)

            if len(df) == 0 or df.empty:
                print('warning! Data seems to be empty. Not saved', df)
            else:
                df.to_csv(filename, index=False)

    def save_log(self, filename=None):
        """
        save log to file
        Returns:

        """
        if filename is None:
            filename = self.filename('-info.txt')
        filename = self.check_filename(filename)
        # filename = self.check_filename(filename)
        # windows can't deal with long filenames so we have to use the prefix '\\\\?\\'
        # if len(filename.split('\\\\?\\')) == 1:
        #     filename = '\\\\?\\' + filename
        with open(filename, 'w') as outfile:
            for item in self.log_data:
                outfile.write("%s\n" % item)

    def save_aqs(self, filename=None):
        """
        saves the experiment settings to a file: filename is filename is not provided, it is created from internal function
        """
        if filename is None:
            filename = self.filename('.aqs')
        filename = self.check_filename(filename)
        # if platform.system() == 'Windows':
        #     # windows can't deal with long filenames so we have to use the prefix '\\\\?\\'
        #     if len(filename.split('\\\\?\\')) == 1:
        #         filename = '\\\\?\\' + filename
        save_aqs_file(filename, experiments=self.to_dict(), overwrite=True)

    def save_image_to_disk(self, filename_1=None, filename_2=None):
        """
        creates an image using the experiments plot function and writes it to the disk
        for single plots (plot_type: 'main', 'aux')
            - if no filname provided take default name
        for double plots (plot_type: 'main', 'aux')
            - if no filnames provided take default name
            - if only one filname provided save only the plot for which name is provided
        Args:
            filename_1: filname for figure 1
            filename_2: filname for figure 1

        Returns: None

        """

        def check_nonempty(graph):
            """
            takes a GrachicsLayoutWidget (a graph) and checks if the plots it contains have data
            the graph is considered non-empty if it has
                -a PlotItem with data
                -any ImageItem ie. it could be blank

            a picture will be saved of the entire graph if ANY PlotItems are none empty
            """
            if graph is not None:
                rows = graph.ci.rows
                for row_index in rows:
                    for item in rows[row_index].values():
                        #item is any plot, image, label, etc item added to GraphicsLayoutWidget
                        if isinstance(item, pg.PlotItem):
                            for curve in item.listDataItems():
                                #curve is any data that has been plotted on a PlotItem
                                if curve.xData is not None and len(curve.xData) > 0:
                                    return False
                            for subitem in item.items:
                                if isinstance(subitem, pg.ImageItem) and subitem.image is not None:
                                    return False
            return True

        # create and save images
        if (filename_1 is None):
            filename_1 = self.filename('-plt1.png')

        if (filename_2 is None):
            filename_2 = self.filename('-plt2.png')

        # windows can't deal with long filenames so we have to use the prefix '\\\\?\\'
        # if len(filename_1.split('\\\\?\\')) == 1:
        #     filename_1 = '\\\\?\\' + filename_1
        # if len(filename_2.split('\\\\?\\')) == 1:
        #     filename_2 = '\\\\?\\' + filename_2

        filename_1 = self.check_filename(filename_1)
        filename_2 = self.check_filename(filename_2)

        if os.path.exists(os.path.dirname(filename_1)) is False:
            os.makedirs(os.path.dirname(filename_1))
        if os.path.exists(os.path.dirname(filename_2)) is False:
            os.makedirs(os.path.dirname(filename_2))

        graph_1 = pg.GraphicsLayoutWidget()  #graph is the space/object you add plots to
        scene_1 = graph_1.scene()            #scene houses all the plots; we want to save all plots if nonempty

        graph_2 = pg.GraphicsLayoutWidget()
        scene_2 = graph_2.scene()

        self.force_update()
        self.plot([graph_1, graph_2])

        if filename_1 is not None and not check_nonempty(graph_1):
            exporter = ImageExporter(scene_1)
            exporter.export(filename_1)
        if filename_2 is not None and not check_nonempty(graph_2):
            exporter = ImageExporter(scene_2)
            exporter.export(filename_2)

    def save(self, filename):
        """
        saves the instance of the experiment to a file using pickle
        Args:
            filename: target filename

        """

        if filename is None:
            filename = self.filename('.aqs')
        # if len(filename.split('\\\\?\\')) == 1:
        #     filename = '\\\\?\\' + filename
        filename = self.check_filename(filename)
        with open(filename, 'w') as outfile:
            outfile.write(pickle.dumps(self.__dict__))

    def save_data_to_matlab(self, filename=None):
        if filename is None:
            filename = self.filename('.mat')
        filename = self.check_filename(filename)

        tag = self.settings['tag']
        if ' ' in tag or '.' in tag or '+' in tag or '-' in tag:
            good_tag = tag.replace(' ', '_').replace('.', '_').replace('+', 'P').replace('-', 'M')
            #matlab structs cant include spaces, dots, or plus/minus so replace with other characters
            #other disallowed characters but not used in our naming schemes so checks as of now
        else:
            good_tag = tag

        mat_saver = MatlabSaver(tag=good_tag)
        mat_saver.add_experiment_data(self.data,self.settings)
        structured_data = mat_saver.get_structured_data()
        savemat(filename, structured_data)

    @staticmethod
    def load(filename, devices=None):
        """
        loads an experiment instance using pickle
        Args:
            filename: source filename
            devices:
                optional - only needed if experiment requires devices
                dictionary of form

                devices = {
                name_of_device_1 : instance_of_device_1,
                name_of_device_2 : instance_of_device_2,
                ...
                }
        Returns:
            experiment_instance
            updated_devices
        """
        filename = Experiment.check_filename(filename)
        with open(filename, 'r') as infile:
            dataPickle = infile.read()

        experiment_as_dict = pickle.loads(dataPickle)
        experiment_class = experiment_as_dict['_experiment_class']

        experiment_instance, _, updated_devices = Experiment.load_and_append({'experiment': experiment_class},
                                                                         devices=devices)
        experiment_instance = experiment_instance['experiment']

        # save references to devices
        devices = experiment_instance._devices

        # update the experiment instance
        experiment_instance.__dict__ = experiment_as_dict

        # update references to devices
        experiment_instance._devices = devices

        return experiment_instance, updated_devices

    @staticmethod
    def load_time(filename):
        """
        Args:
            filename: source filename
        Returns:
            time when experiment started as datetime object

        """
        return datetime.datetime.strptime(os.path.basename(filename)[0:15], '%y%m%d-%H_%M_%S')

    @staticmethod
    def load_data(path, verbose=False, raise_errors=False):
        """
        loads the data that has been save with experiment.save.
        Args:
            path: path to folder saved by experiment.save or raw_data folder within
            verbose: if true print additional information
            raise_errors: if true raise errors if false just print to std out
        Returns:
            a dictionary with the data of form
            data = {param_1_name: param_1_data, ...}
        """

        # check that path exists
        if not os.path.exists(path):
            if raise_errors:
                raise AttributeError('Path given does not exist!')
            else:
                print('Path given does not exist!')
                return

        # windows can't deal with long filenames (>260 chars) so we have to use the prefix '\\\\?\\'
        # if len(path.split('\\\\?\\')) == 1:
        #     path = '\\\\?\\' + os.path.abspath(path)
        path = Experiment.check_filename(path)

        if verbose:
            print('experiment path', path)

        # if raw_data folder exists, get a list of directories from within it; otherwise, get names of all .csv files in
        # current directory
        data = {}
        # if self.RAW_DATA_DIR in os.listdir(path): #8/26/16 AK: self not defined in static context
        #     data_files = os.listdir(os.path.join(path, self.RAW_DATA_DIR + '/'))
        #     path = os.path.join(path, self.RAW_DATA_DIR + '/')
        #
        # else:
        if 'raw_data' in os.listdir(path):  # temporarily hardcoded

            if verbose:
                print('raw_data subfolder found')
            data_files = os.listdir(os.path.join(path, 'raw_data' + '/'))
            path = os.path.join(path, 'raw_data' + '/')

        else:
            data_files = glob.glob(os.path.join(path, '*.csv'))

        if verbose:
            print('data_files found', data_files)

        # If no data files were found, raise error
        if not data_files:

            if raise_errors:
                raise AttributeError('Could not find data files in {:s}'.format(path))
            else:
                print('Could not find data files in {:s}'.format(path))
                return

        # import data from each csv
        for data_file in data_files:
            # get data name, read the data from the csv, and save it to dictionary
            data_name = data_file.split('-')[-1][0:-4]  # JG: why do we strip of the date?

            try:
                imported_data_df = pd.read_csv(os.path.join(path, data_file))

                # check if there are real headers, if the headers are digits than we ignore them because then they are just indecies
                # real headers are strings (however, the digits are also of type str! that why we use the isdigit method)
                column_headers = list(imported_data_df.columns.values)
                if sum([int(x.isdigit()) for x in column_headers]) != len(column_headers):
                    data[data_name] = {h: imported_data_df[h].values for h in column_headers}
                else:
                    # note, np.squeeze removes extraneous length-1 dimensions from the returned 'matrix' from the dataframe
                    data[data_name] = np.squeeze(imported_data_df.values)
            except pd.errors.EmptyDataError as err:

                if raise_errors:
                    raise err('data file ' + data_file + ' is empty: did not load!')
                else:
                    print('data file ' + data_file + ' is empty: did not load!')

        return data

    @staticmethod
    def load_settings(path, setttings_only=True):
        """
        loads the settings that has been save with experiment.save_aqs.
        Args:
            path: path to folder saved by experiment.save_aqs
            setttings_only: if true returns only the settings if the .aqs file contains only a single experiment
        Returns:
            a dictionary with the settings
        """

        # check that path exists
        if not os.path.exists(path):
            print(path)
            raise AttributeError('Path given does not exist!')

        tag = '_'.join(os.path.basename(os.path.dirname(os.path.abspath(path) + '/')).split('_')[3:])

        search_str = os.path.abspath(path) + '/*' + tag + '.aqs'
        fname = glob.glob(search_str)
        if len(fname) > 1:
            print(('warning more than one .aqs file found, loading ', fname[0]))
        elif len(fname) == 0:
            print(('no .aqs file found in folder {:s},  check path !'.format(search_str)))
            return
        fname = fname[0]
        fname = Experiment.check_filename(fname)
        settings = load_aqs_file(fname)['experiments']

        if len(list(settings.keys())) == 1 and setttings_only:
            settings = settings[list(settings.keys())[0]]['settings']

        return settings

    @staticmethod
    def load_and_append(experiment_dict, experiments=None, devices=None, log_function=None, data_path=None,
                        raise_errors=False, verbose=False, package=None):
        """
        load experiment from experiment_dict and append to experiments, if additional devices are required create them and add them to devices

        Args:
            experiment_dict: dictionary of form

                experiment_dict = {
                name_of_experiment_1 :
                    {"settings" : settings_dictionary, "class" : name_of_class}
                name_of_device_2 :
                    {"settings" : settings_dictionary, "class" : name_of_class}
                ...
                }

            or

                experiment_dict = {
                name_of_experiment_1 : name_of_class,
                name_of_experiment_2 : name_of_class
                ...
                }

            where name_of_class is either a class or the name of a class

            experiments: dictionary of form

                experiments = {
                name_of_experiment_1 : instance_of_experiment_1,
                name_of_experiment_2 : instance_of_experiment_2,
                ...
                }

            devices: dictionary of form

                devices = {
                name_of_device_1 : instance_of_device_1,
                name_of_device_2 : instance_of_device_2,
                ...
                }
            log_function: function that takes a string

            data_path: absolute path where data is saved, in case the path in the experiment is definded as a relative path

            raise_errors: if True errors are raised
            package: package where experiment will be found
        Returns:
                dictionary of form
                experiment_dict = { name_of_experiment_1 : experiment_1_instance, name_of_experiment_2 : experiment_2_instance, ...}
                load_failed = {name_of_experiment_1: exception_1, name_of_experiment_2: exception_2, ....}
                updated_devices = {name_of_device_1 : instance_of_device_1, ..}

        """
        if experiments is None:
            experiments = {}
        if devices is None:
            devices = {}
        if package is None:
            package = "src.Model"

        load_failed = {}
        updated_experiments = {}
        updated_experiments.update(experiments)
        updated_devices = {}
        updated_devices.update(devices)

        if verbose:
            print(('experiment_dict', experiment_dict))

        def get_devices(class_of_experiment, experiment_devices, devices):
            """

            creates the dictionary with the devices needed for the experiment and update the device dictionary if new devices are required

            Args:
                class_of_experiment: the class of the experiment
                devices: the devices that have been loaded already

            Returns: dictionary with the devices that the experiment needs and the updated devices dictionary

            """

            default_devices = getattr(class_of_experiment, '_DEVICES')
            # default_devices = getattr(class_of_experiment,devices)
            #default_devices = class_of_experiment.devices
            device_dict = {}
            devices_updated = {}
            devices_updated.update(devices)

            # check if devices needed by experiment already exist, if not create an instance
            for device_name, device_instance in default_devices.items():
                # check if devices needed by experiment already exist
                # device = [instance for name, instance in devices_updated.items() if
                #               isinstance(instance, device_instance) and name == device_name]
                device = [instance for name,instance in devices_updated.items() if name == device_name and type(instance) == type(device_instance)]

                if len(device) == 0:
                    # create new instance of device
                    devices_updated, __ = Device.load_and_append({device_name: device_instance},
                                                                         devices_updated, raise_errors)
                    # MODIFIED to see if I can get rid of the errors in loading galvoscan from the main app
                    # has not worked so far.
                    # GD : 20230828
                    #devices_updated,__ = Device.load_and_append({device_name:device_instance.__class__},devices_updated,raise_errors)

                if experiment_devices is not None and device_name in experiment_devices:
                    device_settings_dict = experiment_devices[device_name]['settings']
                else:
                    device_settings_dict = devices_updated[device_name].settings

                device_instance = devices_updated[device_name]

                # make a deepcopy of _DEFAULT_SETTINGS to get a parameter object
                device_settings = deepcopy(device_instance._DEFAULT_SETTINGS)

                # now update parameter object with new values
                device_settings.update(device_settings_dict)
                #
                # Essentially, the logic of this statement is that it returns a dictionary
                # of form {device_name: {"instance": device_instance, "settings": device_settings"}
                # in that case, when we pass devices directly to the experiment
                # for instance by creating an instance of that device we will need to supply it in a dictionary
                # of this same form for any code that uses that instance to correctly execute.
                device_dict.update(
                    {device_name: {"instance": device_instance, "settings": device_settings}})

            return device_dict, devices_updated

        def get_sub_experiments(class_of_experiment, devices, sub_experiments_dict, log_function=None):
            """

            creates the dictionary with the sub experiments needed by the experiment and updates the device dictionary if new devices are required

            Args:
                class_of_experiment: the class of the experiment
                devices: the devices that have been loaded already
                sub_experiments_dict: settings of experiment in dictionary form

            Returns:dictionary with the sub experiments that the experiment needs

            """

            default_experiments = getattr(class_of_experiment, '_EXPERIMENTS')
            # default_experiments = getattr(class_of_experiment,experiments)
            #
            # create devices that experiment needs
            sub_experiments = {}
            sub_experiments, experiments_failed, devices_updated = Experiment.load_and_append(default_experiments, sub_experiments,
                                                                                      devices,
                                                                                      log_function=log_function,
                                                                                      raise_errors=raise_errors)
            try:
                if sub_experiments_dict is not None:
                    for k, v in sub_experiments_dict.items():
                        # update settings, updates device and settings
                        sub_experiments[k].update(v)
            except TypeError:  # if actually an object, as with dynamic experiments
                pass

            if len(experiments_failed) > 0:
                raise ImportError('experiment {:s}: failed to load subexperiments'.format(class_of_experiment))
            return sub_experiments, devices_updated

        for experiment_name, experiment_info in experiment_dict.items():
            # check if experiment already exists
            if experiment_name in list(experiments.keys()):
                print(('WARNING: experiment {:s} already exists. Did not load!'.format(experiment_name)))
                load_failed[experiment_name] = ValueError('experiment {:s} already exists. Did not load!'.format(experiment_name))
            else:
                module, experiment_class_name, experiment_settings, experiment_devices, experiment_sub_experiments, experiment_doc, package = Experiment.get_experiment_information(
                    experiment_info, package=package)
                # creates all dynamic experiments so they can be imported following the if statement
                # if experiment_class_name == 'ExperimentIterator':
                if 'ExperimentIterator' in experiment_class_name:
                    # creates all the dynamic classes in the experiment and the class of the experiment itself
                    # and updates the experiment info with these new classes
                    from src.core.experiment_iterator import \
                        ExperimentIterator  # CAUTION: imports ExperimentIterator, which inherits from experiment. Local scope should avoid circular imports.

                    experiment_info, _ = ExperimentIterator.create_dynamic_experiment_class(experiment_info)

                    # now get the info for the dynamically created class
                    module, experiment_class_name, experiment_settings, experiment_devices, experiment_sub_experiments, experiment_doc, package = Experiment.get_experiment_information(
                        experiment_info)
                if verbose:
                    print(('load_and_append.module', module))
                    print(('load_and_append.experiment_info', experiment_info))
                    print(('load_and_append.package', package))

                if module is None and inspect.isclass(experiment_info):
                    class_of_experiment = experiment_info
                else:
                    class_of_experiment = getattr(module, experiment_class_name)

                #  ========= create the devices that are needed by the experiment =========
                try:
                    experiment_devices, updated_devices = get_devices(class_of_experiment, experiment_devices,
                                                                              updated_devices)
                except Exception as err:
                    print(('loading experiment {:s} failed. Could not load devices!'.format(experiment_name)))
                    load_failed[experiment_name] = err
                    if raise_errors:
                        raise err
                    continue
                #  ========= create the subexperiments that are needed by the experiment =========
                try:
                    sub_experiments, updated_devices = get_sub_experiments(class_of_experiment, updated_devices,
                                                                       experiment_sub_experiments, log_function=log_function)
                except Exception as err:
                    print(('loading experiment {:s} failed. Could not load subexperiments!'.format(experiment_name)))
                    load_failed[experiment_name] = err
                    if raise_errors:
                        raise err
                    continue

                #  ========= create the experiment if devices and subexperiments have been loaded successfully =========
                class_creation_string = ''
                if experiment_devices:
                    class_creation_string += ', devices = experiment_devices'
                if sub_experiments:
                    class_creation_string += ', experiments = sub_experiments'
                if experiment_settings:
                    class_creation_string += ', settings = experiment_settings'
                if log_function:
                    class_creation_string += ', log_function = log_function'
                if data_path:
                    class_creation_string += ', data_path = data_path'
                class_creation_string = 'class_of_experiment(name=experiment_name{:s})'.format(class_creation_string)
                #print("Will create instance of",class_creation_string)
                #class_creation_string = '{:s}(name={:s}{:s})'.format(experiment_class_name,experiment_name,class_creation_string)

                if verbose:
                    print(('class_creation_string', class_creation_string))
                    print(('class_of_experiment', class_of_experiment))
                    print(('experiments', sub_experiments))

                try:
                    experiment_instance = eval(class_creation_string)
                except Exception as err:
                    #print('loading ' + experiment_name + ' failed:')
                    print(('loading experiment {0} failed. Could not create instance from {1} from experiment!'.format(
                        experiment_name,class_of_experiment)))
                    print(traceback.format_exc())

                    load_failed[experiment_name] = err
                    if raise_errors:
                        raise err
                    continue

                if experiment_doc:
                    experiment_instance.__doc__ = experiment_doc
                # added below 2 lines because original update was breaking updated_experiments in debugging mode?
                if updated_experiments:
                    updated_experiments.update({experiment_name: experiment_instance})
                else:
                    updated_experiments[experiment_name] = experiment_instance
                print(updated_experiments)

        return updated_experiments, load_failed, updated_devices

    @staticmethod
    def get_experiment_information(experiment_information, package='src.Model', verbose=False):
        """
        extracts all the relevant information from experiment_information and returns it as individual variables
        Args:
            experiment_information: information of the experiment. This can be
                - a dictionary
                - a experiment instance
                - name of experiment class
            package (optional): name of the package to which the experiment belongs, i.e. AQuISS .
                                Only used when experiment_information is a string
        Returns:
            module, experiment_class_name, experiment_settings, experiment_devices, experiment_sub_experiments, experiment_info, package
        """

        experiment_settings = None
        experiment_devices = None
        experiment_sub_experiments = None
        experiment_class_name = None
        module = None  # this is the module that contains the experiment where we look for experiments
        experiment_info = None  # this is the docstring that describes the experiment
        module_path = package + '.experiments'
        experiment_filepath = None
        module_file = None

        if isinstance(experiment_information, dict):
            if 'settings' in experiment_information:
                experiment_settings = experiment_information['settings']
            if 'filepath' in experiment_information:
                experiment_filepath = str(experiment_information['filepath'])
                module_path, module_file = module_name_from_path(experiment_filepath, verbose=False)
            if 'package' in experiment_information:
                package = experiment_information['package']
            else:
                assert 'filepath' in experiment_information  # there should be a filepath if we load form a aqs file
                # in the case that we generate the experiment_information from a .py file the package is given by the name of the highest module
                if 'filepath' in experiment_information:
                    package = module_path.split('.')[0]

            experiment_class_name = str(experiment_information['class'])
            if 'ExperimentIterator' in experiment_class_name:
                module_path = package + '.core.experiment_iterator'
            if 'devices' in experiment_information:
                experiment_devices = experiment_information['devices']
            if 'experiments' in experiment_information:
                experiment_sub_experiments = experiment_information['experiments']
            if 'info' in experiment_information:
                experiment_info = experiment_information['info']

        elif isinstance(experiment_information, str):
            experiment_class_name = experiment_information


        elif issubclass(experiment_information, Experiment):
            # watch out when testing this code from __main__, then classes might not be identified correctly because the path is different
            # to avoid this problem call from AQuISS.src.core import experiment (otherwise the path to experiment is __main__.experiment)
            experiment_class_name = experiment_information.__name__
            package = experiment_information.__module__.split('.')[0]
            module_path = experiment_information.__module__

        assert isinstance(package, str)

        # if the experiment has not been created yet, i.e. experiment_class_name: ExperimentIteratorAQ or ExperimentIterator
        if verbose:
            print(('experiment_filepath', experiment_filepath))
            print(('path_to_module', module_path))

        if experiment_filepath is not None:
            # experimentiterator loaded from file
            if os.path.basename(experiment_filepath.split('.pyc')[0].split('.py')[0]) == 'experiment_iterator':
                module_path = package + '.core.experiment_iterator'

        # if the experiment has been created already, i.e. experiment_class_name: package.dynamic_experiment_iterator
        # todo: now there is the prefix package
        if len(experiment_class_name.split('dynamic_experiment_iterator')) == 2 and \
                experiment_class_name.split('dynamic_experiment_iterator')[1].isdigit():
            # package = 'AQuISS' # all the dynamic iterator experiments are defined in the name space of AQuISS
            # all the dynamic iterator experiments are defined in the name space of package.AQuISS.src.core.experiment_iterator
            # module = import_module(package + '.AQuISS.src.core.experiment_iterator')
            module_path = package

        # the package should be the highest level of the module path
        # assert module_path.split('.')[0] == package
        # assert isinstance(module_path, str)  # in that case we should have defined a module_path to load the module
        # assert module is None  # we haven't loaded the module yet

        # try:
        #     print(module_path)
        #     module = import_module(module_path)
        #     print(module)
        # except ImportError:
        #     pass
        # print('module', module_path)

        # appends path to this module to the python path if it is not present so it can be used
        if module_file and (module_file not in sys.path):
            sys.path.append(module_file)

        module = import_module(module_path)
        # check if module was found!
        if module is None or not hasattr(module, experiment_class_name):
            # import sys
            print('here is the pythonpath')
            for path in sys.path:
                print(path)
            import time
            time.sleep(1)
            print(('Could not find the module that contains ' + experiment_class_name + ' in module ' + module_path))
            raise ImportError(
                'Could not find the module that contains ' + experiment_class_name + ' in module ' + module_path)

        # if the module has a name of type dynamic_experiment_iteratorX where X is a number the module is experiment iterator
        return module, experiment_class_name, experiment_settings, experiment_devices, experiment_sub_experiments, experiment_info, package

    @staticmethod
    def get_experiment_module(experiment_information, package='src.Model', verbose=False):
        """
        wrapper to get the module for a experiment

        Args:
            experiment_information: information of the experiment. This can be
                - a dictionary
                - a experiment instance
                - name of experiment class
            package (optional): name of the package to which the experiment belongs, i.e. AQuISS  only used when experiment_information is a string
        Returns:
            module

        """

        module, _, _, _, _, _, _ = Experiment.get_experiment_information(experiment_information=experiment_information, package=package,
                                                                     verbose=verbose)

        return module

    def duplicate(self):
        """
        create an copy of the experiment

        Returns:

        """

        # get settings of experiment
        class_of_experiment = self.__class__
        experiment_name = self.name
        experiment_devices = self.devices
        sub_experiments = self.experiments
        experiment_settings = self.settings
        log_function = self.log_function
        data_path = self.data_path

        # create a new instance of same experiment type
        class_creation_string = ''
        if experiment_devices != {}:
            class_creation_string += ', devices = experiment_devices'
        if sub_experiments != {}:
            class_creation_string += ', experiments = sub_experiments'
        if experiment_settings != {}:
            class_creation_string += ', settings = experiment_settings'
        if log_function is not None:
            class_creation_string += ', log_function = log_function'
        if data_path is not None:
            class_creation_string += ', data_path = data_path'
        class_creation_string = 'class_of_experiment(name=experiment_name{:s})'.format(class_creation_string)
        # class_creation_string = '{:s}(name={:s}{:s})'.format(experiment_class_name, experiment_name,
        #                                                      class_creation_string)
        # create instance
        experiment_instance = eval(class_creation_string)

        # copy some other properties that might be checked later for the duplicated experiment
        experiment_instance.data = deepcopy(self.data)
        experiment_instance.start_time = self.start_time
        experiment_instance.end_time = self.end_time
        experiment_instance.is_running = self.is_running

        return experiment_instance


    def _plot(self, axes_list):
        """
        plots the data only the axes objects that are provided in axes_list
        Args:
            axes_list: a list of axes objects, this should be implemented in each subexperiment

        Returns: None
        """
        pass
        # not sure if to raise a not implemented error or just give a warning. For now just warning
        print(('INFO: {:s} called _plot even though it is not implemented'.format(self.name)))

    def _update_plot(self, axes_list):
        """
        updates the data in already existing plots. the axes objects are provided in axes_list
        Args:
            axes_list: a list of axes objects, this should be implemented in each subexperiment

        Returns: None
        """

        # default behaviour just calls the standard plot function that creates a new image everytime it is called
        # for heavier plots such as images implement a function here that updates only the date of the plot
        # but doesn't create a whole new image
        self._plot(axes_list)

    def force_update(self):
        """
        forces the plot to refresh
        Returns:
        """
        self._plot_refresh = True

    def plot(self, figure_list):
        """
        plots the data contained in self.data, which should be a dictionary or a deque of dictionaries
        for the latter use the last entry
        Args:
            figure_list: list of figure objects that are passed to self.get_axes_layout to get axis objects for plotting
        """
        # if there is not data we do not plot anything
        if not self.data:
            return

        # if plot function is called when experiment is not running we request a plot refresh
        if not self.is_running:
            self._plot_refresh = True

        axes_list = self.get_axes_layout(figure_list)
        if self._plot_refresh is True:
            self._plot(axes_list)
            self._plot_refresh = False
        else:
            self._update_plot(axes_list)

    #changed this method
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
        axes_list = []
        if self._plot_refresh is True:
            for graph in figure_list:
                graph.clear()
                axes_list.append(graph.addPlot(row=0,col=0))
        else:
            for graph in figure_list:
                axes_list.append(graph.getItem(row=0,col=0))

        return axes_list

    def plot_validate(self, figure_list):
        """
        plots the data contained in self.data, which should be a dictionary or a deque of dictionaries
        for the latter use the last entry
        """
        axes_list = self.get_axes_layout_validate(figure_list)
        self._plot_validate(axes_list)

    def _plot_validate(self, axes_list):
        """
        plot some visual output as a result of the validation (see self.validate)
        This will most likely be removed in future version: instead preview function, maybe
        :param axes_list: list of axes objects on which to plot
        """
        pass

    def get_axes_layout_validate(self, figure_list):
        """
        creates the axes layout for the validation plots
        :param figure_list: list of figures
        :return: list of axes objects
        """
        return self.get_axes_layout(figure_list)


if __name__ == '__main__':
    expt = {}
    instr = {}
    expt,failed,instr = Experiment.load_and_append({"DummyExpt":"ExampleExperiment"},experiments=expt,devices=instr,verbose=True)
    if failed:
        print("Expt failed to load")
    else:
        print("Success !")


