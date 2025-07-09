# Created by Gurudev Dutt <gdutt@pitt.edu> on 2023-07-31
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
import copy

from src.core import Parameter, Experiment
import numpy as np
from PyQt5.QtCore import pyqtSlot, pyqtSignal
from collections import deque
import datetime
import warnings
import inspect
from src.core import helper_functions as hf
import importlib
from functools import reduce
from src.core.helper_functions import MatlabSaver
from scipy.io import savemat

import random
from time import sleep


class ExperimentIterator(Experiment):
    '''
    This is a template class for experiments that iterate over a series of subexperiments in either a loop /
    a parameter sweep / future: list of points.
    CAUTION: This class has some circular dependencies with experiment that are avoided by only importing it in very local scope
    in experiment (since this inherits from experiment, it can't be imported globally in experiment). Use caution when making changes in
    experiment.
    '''

    _DEFAULT_SETTINGS = []

    _DEVICES = {}
    _EXPERIMENTS = {}
    # _EXPERIMENTS is populated dynamically with the required subexperiments

    _number_of_classes = 0  # keeps track of the number of dynamically created ExperimentIterator classes that have been created
    _class_list = []  # list of current dynamically created ExperimentIterator classes

    ITER_TYPES = ['loop', 'sweep']

    def __init__(self, experiments, name=None, settings=None, log_function=None, data_path=None):
        """
        Default experiment initialization
        """
        Experiment.__init__(self, name, sub_experiments=experiments, settings=settings, log_function=log_function, data_path=data_path)
        self.iterator_type = self.get_iterator_type(self.settings, experiments)

        self._current_subexperiment_stage = None
        # for multi iterator experiments tracks how many iterator levels there is; value equal num layers below
        self.iterator_level = self.detect_iterator_depth(self.experiments)
        print('iterator level',self.iterator_level)

        self._skippable = True

    @staticmethod
    def get_iterator_type(experiment_settings, subexperiments={}):
        """
        figures out the iterator type based on the experiment settings and (optionally) subexperiments
        Args:
            experiment_settings: iterator_type
            subexperiments: subexperiments
        Returns:

        """

        if 'iterator_type' in experiment_settings:
            # figure out the iterator type
            if experiment_settings['iterator_type'] == 'Loop':
                iterator_type = 'loop'
            elif experiment_settings['iterator_type'] == 'Parameter Sweep':
                iterator_type = 'sweep'
            else:
                raise TypeError('unknown iterator type')
        else:
            # asign the correct iterator experiment type
            if 'sweep_param' in experiment_settings:
                iterator_type = 'sweep'
            elif 'num_loops' in experiment_settings:
                iterator_type = 'loop'
            else:
                raise TypeError('unknown iterator type')

        return iterator_type

    def detect_iterator_depth(self, experiments, current_level=1):
        max_level = current_level
        for key, value in experiments.items():
            if hasattr(value, 'get_iterator_type'):
                print(f'Sub iterator detected at level {current_level}: {key}')
                # Recurse into sub-experiments
                sub_experiments = getattr(value, 'experiments', {})
                sub_level = self.detect_iterator_depth(sub_experiments, current_level + 1)
                max_level = max(max_level, sub_level)
        return max_level

    def _function(self):
        '''
        Runs either a loop or a parameter sweep over the subexperiments in the order defined by the parameter_list 'experiment_order'
        '''
        def get_sweep_parameters():
            """
            Returns: the paramter values over which to sweep
            """
            # in both cases, param values have tolist to make sure that they are python types (ex float) rather than numpy
            # types (ex np.float64), the latter of which can cause typing issues
            sweep_range = self.settings['sweep_range']
            param_values = np.empty(int(sweep_range['N/value_step'])).tolist()
            if self.settings['stepping_mode'] == 'N':
                param_values = np.linspace(sweep_range['min_value'], sweep_range['max_value'],
                                           int(sweep_range['N/value_step']), endpoint=True).tolist()
            elif self.settings['stepping_mode'] == 'value_step':
                param_values = np.linspace(sweep_range['min_value'], sweep_range['max_value'],
                                           int((sweep_range['max_value'] - sweep_range['min_value']) / sweep_range[
                                               'N/value_step']) + 1, endpoint=True).tolist()
            return param_values

        experiment_names = list(self.settings['experiment_order'].keys())
        experiment_indices = [self.settings['experiment_order'][name] for name in experiment_names]
        _, sorted_experiment_names = list(zip(*sorted(zip(experiment_indices, experiment_names))))

        if self.iterator_type == 'sweep':

            def get_experiment_and_settings_from_str(sweep_param):
                """
                Args:
                    sweep_param: astring with the path to the sweep parameter
                        e.g. experiment.param.subparam or experiment->subexperiment.parameter

                Returns:
                    experiment_list: a list with the experiments, e.g. [experiment] or [experiment, subexperiment]
                    parameter_list: a list with the paraemeters, e.g. [param, subparam] or [parameter] for the cases above
                """
                split_trace = sweep_param.split('.')
                experiment_list = split_trace[0].split('->')
                parameter_list = split_trace[1:]

                return experiment_list, parameter_list

            param_values = get_sweep_parameters()

            print('GD parameters before', param_values)
            if self.settings['sweep_range']['randomize'] == True:
                np.random.shuffle(param_values)
            print('GD parameters after', param_values)

            for i, value in enumerate(param_values):
                self.iterator_progress = float(i) / len(param_values)
                previous_data = None

                experiment_list, parameter_list = get_experiment_and_settings_from_str(self.settings['sweep_param'])
                experiment = self
                while len(experiment_list) > 0:
                    experiment = experiment.experiments[experiment_list[0]]
                    experiment_list = experiment_list[1:]

                curr_type = type(reduce(lambda x, y: x[y], parameter_list,
                                        experiment.settings))  # traverse nested dict to get type of variable

                update_dict = reduce(lambda y, x: {x: y}, reversed(parameter_list),
                                     curr_type(value))  # creates nested dictionary from list

                experiment.settings.update(update_dict)
                parameter_name = parameter_list[-1]
                if np.abs(value) < 1000:
                    self.log('setting parameter {:s} to {:.3g}'.format(self.settings['sweep_param'], value))
                else:
                    self.log('setting parameter {:s} to {:0.2e}'.format(self.settings['sweep_param'], value))

                for experiment_name in sorted_experiment_names:
                    if self._abort:
                        break
                    j = i if self.settings['run_all_first'] else (i + 1)

                    curr_experiment_exec_freq = self.settings['experiment_execution_freq'][experiment_name]
                    if curr_experiment_exec_freq != 0 and (j % curr_experiment_exec_freq == 0):

                        #for some experiments we want to inherit data from the previous experiment (for example NV locations from SelectPoints to use in say ODMR
                        #to use you want an inherit data parameter in the experiment settings. Could be expanded depending on use cases
                        if previous_data is not None:
                            if 'inherit_data' in self.experiments[experiment_name].settings and self.experiments[experiment_name].settings['inherit_data']:
                                common_keys = self.experiments[experiment_name].data.keys() & previous_data.keys()
                                for key in common_keys:
                                    self.experiments[experiment_name].data[key] = previous_data[key]

                        # i+1 so first execution is mth loop, not first
                        self.log('starting {:s}'.format(experiment_name))
                        tag = self.experiments[experiment_name].settings['tag']
                        self.experiments[experiment_name].settings['tag'] = '{:s}_{:s}_{:0.3e}'.format(tag, parameter_name,value)
                        #ensure settings and data are deepcopys so multiple iterations dont change old values
                        settings = copy.deepcopy(self.experiments[experiment_name].settings)
                        self.experiments[experiment_name].run()

                        it_level_str = f'_iterator_{self.iterator_level}'
                        python_scan_info_dic = {'scan_parameter'+it_level_str:parameter_name,'scan_current_value'+it_level_str:value, 'scan_all_values'+it_level_str:list(param_values)}
                        data = copy.deepcopy(self.experiments[experiment_name].data)

                        #adds to self.data a key of the current experiment tage with a value that is a lsit of [data, settings, scan_infor] for current experiment
                        self.data[self.experiments[experiment_name].settings['tag']] = [data, settings, python_scan_info_dic]

                        self.experiments[experiment_name].settings['tag'] = tag
                        previous_data = self.experiments[experiment_name].data


        elif self.iterator_type == 'loop':

            num_loops = self.settings['num_loops']
            if num_loops == 0:
                self.log('Loop set to run 0 times')
                return

            self.data = {}
            for i in range(num_loops):
                self.iterator_progress = float(i) / num_loops
                previous_data = None

                for experiment_name in sorted_experiment_names:
                    if self._abort:
                        break
                    j = i if self.settings['run_all_first'] else (i + 1)

                    curr_experiment_execution_freq = self.settings['experiment_execution_freq'][experiment_name]

                    if curr_experiment_execution_freq != 0 and (j % curr_experiment_execution_freq == 0):

                        #for some experiments we want to inherit data from the previous experiment (for example NV locations from SelectPoints to use in say ODMR
                        #to use you want an inherit data parameter in the experiment settings. Could be expanded depending on use cases
                        if previous_data is not None:
                            if 'inherit_data' in self.experiments[experiment_name].settings and self.experiments[experiment_name].settings['inherit_data']:
                                common_keys = self.experiments[experiment_name].data.keys() & previous_data.keys()
                                for key in common_keys:
                                    self.experiments[experiment_name].data[key] = previous_data[key]

                        # i+1 so first execution is mth loop, not first
                        self.log('starting {:s} \t iteration {:d} of {:d}'.format(experiment_name, i + 1, num_loops))
                        tag = self.experiments[experiment_name].settings['tag']
                        tmp = tag + '_{' + ':0{:d}'.format(len(str(num_loops))) + '}'
                        self.experiments[experiment_name].settings['tag'] = tmp.format(i)
                        self.experiments[experiment_name].run()
                        self.experiments[experiment_name].settings['tag'] = tag

                        previous_data = self.experiments[experiment_name].data

                # from the last experiment we take the average of the data as the data of the iterator experiment
                if isinstance(self.experiments[experiment_name].data, dict):
                    data = self.experiments[experiment_name].data
                elif isinstance(self.experiments[experiment_name].data, deque):
                    data = self.experiments[experiment_name].data[-1]
                if i == 0:
                    self.data.update(data)
                else:
                    if self._abort:
                        break

                    for key in list(data.keys()):

                        # can't add None values
                        if not data[key] is None:
                            # if subexperiment data have differnet length, e.g. fitparameters can be differet, depending on if there is one or two peaks
                            if len(self.data[key]) != len(data[key]):
                                print(('warning subexperiment data {:s} have different lengths'.format(key)))
                                continue

                            if isinstance(self.data[key], list):
                                self.data[key] += np.array(data[key])
                            elif isinstance(self.data[key], dict):
                                self.data[key] = {x: self.data[key].get(x, 0) + data[key].get(x, 0) for x in
                                                  list(self.data[key].keys())}
                            else:
                                self.data[key] += data[key]

            if not self._abort and num_loops > 0:
                # normalize data because we just kept adding the values
                for key in list(data.keys()):
                    if isinstance(self.data[key], list):
                        self.data[key] = np.array(self.data[key]) / num_loops
                    elif isinstance(self.data[key], dict):
                        self.data[key] = {k: v / num_loops for k, v in self.data[key].items()}
                    elif self.data[key] is None:
                        self.log('None type in data! check code')
                        pass
                    elif isinstance(self.data[key], int):
                        self.data[key] = float(self.data[
                                                   key]) / num_loops  # if int we can not devide. Thus we convert explicitely to float
                    else:
                        self.data[key] = self.data[key] / num_loops

        else:
            raise TypeError('wrong iterator type')

    def _estimate_progress(self):
        """
        estimates the current progress that is then used in _receive_signal

        :return: current progress in percent
        """
        estimate = True
        progress_subexperiment = 0
        # ==== get the current subexperiment and the time it takes to execute it =====
        current_subexperiment = self._current_subexperiment_stage['current_subexperiment']

        # ==== get the number of subexperiments =====
        num_subexperiments = len(self.experiments)

        # ==== get number of iterations and loop index ======================
        if self.iterator_type == 'loop':
            num_iterations = self.settings['num_loops']
        elif self.iterator_type == 'sweep':
            sweep_range = self.settings['sweep_range']
            if self.settings['stepping_mode'] == 'value_step':
                num_iterations = int(
                    (sweep_range['max_value'] - sweep_range['min_value']) / sweep_range['N/value_step']) + 1
                # len(np.linspace(sweep_range['min_value'], sweep_range['max_value'],
                #                                        (sweep_range['max_value'] - sweep_range['min_value']) /
                #                                        sweep_range['N/value_step'] + 1, endpoint=True).tolist())
            elif self.settings['stepping_mode'] == 'N':
                num_iterations = sweep_range['N/value_step']
            else:
                raise KeyError('unknown key' + self.settings['stepping_mode'])

        else:
            print('unknown iterator type in Iterator receive signal - can\'t estimate ramining time')
            estimate = False

        if estimate:
            # get number of loops (completed + 1)
            loop_index = self.loop_index

            if num_subexperiments > 1:
                # estimate the progress based on the duration the individual subexperiments

                loop_execution_time = 0.  # time for a single loop execution in s
                sub_progress_time = 0.  # progress of current loop iteration in s

                # ==== get typical duration of current subexperiment ======================
                if current_subexperiment is not None:
                    current_subexperiment_exec_duration = self._current_subexperiment_stage['subexperiment_exec_duration'][
                        current_subexperiment.name].total_seconds()
                else:
                    current_subexperiment_exec_duration = 0.0

                current_subexperiment_elapsed_time = (
                            datetime.datetime.now() - current_subexperiment.start_time).total_seconds()
                # estimate the duration of the current subexperiment if the experiment hasn't been executed once fully and subexperiment_exec_duration is 0
                if current_subexperiment_exec_duration == 0.0:
                    remaining_time = current_subexperiment.remaining_time.total_seconds()
                    current_subexperiment_exec_duration = remaining_time + current_subexperiment_elapsed_time

                # ==== get typical duration of one loop iteration ======================
                remaining_experiments = 0  # experiment that remain to be executed for the first time
                for subexperiment_name, duration in self._current_subexperiment_stage['subexperiment_exec_duration'].items():
                    if duration.total_seconds() == 0.0:
                        remaining_experiments += 1
                    loop_execution_time += duration.total_seconds()
                    # add the times of the subexperiments that have been executed in the current loop
                    # ignore the current subexperiment, because that will be taken care of later
                    if self._current_subexperiment_stage['subexperiment_exec_count'][subexperiment_name] == loop_index \
                            and subexperiment_name is not current_subexperiment.name:
                        # this subexperiment has already been executed in this iteration
                        sub_progress_time += duration.total_seconds()

                # add the proportional duration of the current subexperiment given by the subexperiment progress
                sub_progress_time += current_subexperiment_elapsed_time

                # if there are experiments that have not been executed yet
                # assume that all the experiments that have not been executed yet take as long as the average of the other experiments
                if remaining_experiments == num_subexperiments:
                    # none of the subexperiment has been finished. assume that all the experiments take as long as the first
                    loop_execution_time = num_subexperiments * current_subexperiment_exec_duration
                elif remaining_experiments > 1:
                    loop_execution_time = 1. * num_subexperiments / (num_subexperiments - remaining_experiments)
                elif remaining_experiments == 1:
                    # there is only one experiment left which is the current experiment
                    loop_execution_time += current_subexperiment_exec_duration

                if loop_execution_time > 0:
                    progress_subexperiment = 100. * sub_progress_time / loop_execution_time
                else:
                    progress_subexperiment = 1. * progress_subexperiment / num_subexperiments

            # print(' === experiment iterator progress estimation loop_index = {:d}/{:d}, progress_subexperiment = {:f}'.format(loop_index, number_of_iterations, progress_subexperiment))
            progress = 100. * (loop_index - 1. + 0.01 * progress_subexperiment) / num_iterations

        else:
            # if can't estimate the remaining time set to half
            progress = 50
        return progress

    @pyqtSlot(int)
    def _receive_signal(self, progress_subexperiment):
        """
        this function takes care of signals emitted by the subexperiments
        Args:
            progress_subexperiment: progress of subexperiment
        """

        self.progress = self._estimate_progress()
        self.updateProgress.emit(int(self.progress))

    def skip_next(self):
        for experiment in self.experiments.values():
            experiment.stop()

    @property
    def loop_index(self):
        loop_index = max(self._current_subexperiment_stage['subexperiment_exec_count'].values())
        return loop_index

    def save_data_to_matlab(self, filename=None):
        if self.iterator_type == 'loop':
            #for loop the experiment data is averaged so its structure is similar to a single experiment; default to normal behavior
            Experiment.save_data_to_matlab(self)

        elif self.iterator_type == 'sweep': #for sweeps need more complex structure
            #does not include the settings of each iterator level as the important info is in the inherited scan info
            def extract_data(dic, current_level, target_level, inherited_scan_info=None):
                it_level_str = f'_iterator_{target_level-current_level+1}'
                if inherited_scan_info is None:
                    inherited_scan_info = {}
                result = []
                for key, value in dic.items():
                    #sweep_1_y_1.000e+00:[{exp_1:[dic(data),dic(settings),dic(scan_params),'exp_2:[dic(data),dic(settings),dic(scan_params),'exp_3:[dic(data),dic(settings),dic(scan_params)]},
                                         #dic(settings),dic(scan_params)
                    next_dic_level = value[0]
                    current_level_settings = value[1]
                    current_level_scan_info_raw = value[2]

                    scan_variable = current_level_scan_info_raw.get('scan_parameter' + it_level_str)
                    scan_var_current_value = current_level_scan_info_raw.get('scan_current_value' + it_level_str)
                    scan_var_all_values = current_level_scan_info_raw.get('scan_all_values' + it_level_str)

                    updated_scan_info = dict(inherited_scan_info)
                    updated_scan_info['scan_parameter' + it_level_str] = scan_variable
                    updated_scan_info['scan_current_value' + it_level_str] = scan_var_current_value
                    updated_scan_info['scan_all_values' + it_level_str] = scan_var_all_values

                    if current_level < target_level:

                        if isinstance(value, list) and isinstance(value[0], dict):
                            result.extend(extract_data(next_dic_level, current_level+1, target_level, updated_scan_info))
                        else:
                            raise ValueError(f"In matlab saving: Unexpected structure at level {current_level}: {key} → {value}")

                    elif current_level == target_level:
                        if isinstance(value, list) and len(value) == 3:

                            result.append((next_dic_level, current_level_settings, updated_scan_info))
                        else:
                            raise ValueError(f"In matlab saving: Invalid leaf data at level {current_level}: {key} → {value}")

                return result


            if filename is None:
                filename = self.filename('.mat')
            filename = self.check_filename(filename)

            tag = self.settings['tag']
            if ' ' in tag or '.' in tag or '+' in tag or '-' in tag:
                good_tag = tag.replace(' ', '_').replace('.', '_').replace('+', 'P').replace('-', 'M')
                # matlab structs cant include spaces, dots, or plus/minus so replace with other characters
                # other disallowed characters but not used in our naming schemes so checks as of now
            else:
                good_tag = tag
            #add 'data_' to ensure field name does not start with a number
            good_tag = 'data_' + good_tag

            mat_saver = MatlabSaver(tag=good_tag)
            data_tuples = extract_data(self.data, current_level=1, target_level=self.iterator_level)
            #print('data_tuples',data_tuples)
            for data, settings, combined_scan_info in data_tuples:
                mat_saver.add_experiment_data(data, settings, iterator_info_dic=combined_scan_info)

            structured_data = mat_saver.get_structured_data()
            savemat(filename, structured_data)

        else:
            raise TypeError('wrong iterator type')

    def plot(self, figure_list):
        '''
        When each subexperiment is called, uses its standard plotting

        Args:
            figure_list: list of figures passed from the guit

        '''

        # TODO: be smarter about how we plot ExperimentIterator
        if self._current_subexperiment_stage is not None:
            if self._current_subexperiment_stage['current_subexperiment'] is not None:
                self._current_subexperiment_stage['current_subexperiment'].plot(figure_list)

        if (self.is_running is False) and not (self.data == {} or self.data is None):

            experiment_names = list(self.settings['experiment_order'].keys())
            experiment_indices = [self.settings['experiment_order'][name] for name in experiment_names]
            _, sorted_experiment_names = list(zip(*sorted(zip(experiment_indices, experiment_names))))

            last_experiment = self.experiments[sorted_experiment_names[-1]]

            last_experiment.force_update()  # since we use the last experiment plot function we force it to refresh

            axes_list = last_experiment.get_axes_layout(figure_list)

            # catch error is _plot function doens't take optional data argument
            try:
                #new structure of iterator data so just default to use last experiments data dic instead of the iterators data dic
                last_experiment._plot(axes_list)#, self.data)
            except TypeError as err:
                print((warnings.warn(
                    'can\'t plot average experiment data because experiment.plot function doens\'t take data as optional argument. Plotting last data set instead')))
                print((str(err)))
                last_experiment.plot(figure_list)

    def to_dict(self):
        """
        Returns: itself as a dictionary
        """
        dictator = Experiment.to_dict(self)
        # the dynamically created ExperimentIterator classes have a generic name
        # replace this with ExperimentIterator to indicate that this class is of type ExperimentIterator
        dictator[self.name]['class'] = 'ExperimentIterator'

        return dictator

    @staticmethod
    def get_iterator_default_experiment(iterator_type):
        """
        This function might be overwritten by functions that inherit from ExperimentIterator
        Returns:
            sub_experiments: a dictionary with the default experiments for the experiment_iterator
            experiment_settings: a dictionary with the experiment_settings for the default experiments

        """

        sub_experiments = {}
        experiment_settings = {}
        return sub_experiments, experiment_settings

    @staticmethod
    def get_experiment_order(experiment_order):
        """

        Args:
            experiment_order:
                a dictionary giving the order that the experiments in the ExperimentIterator should be executed.
                Must be in the form {'experiment_name': int}. experiments are executed from lowest number to highest

        Returns:
            experiment_order_parameter:
                A list of parameters giving the order that the experiments in the ExperimentIterator should be executed.
            experiment_execution_freq:
                A list of parameters giving the frequency with which each experiment should be executed,
                e.g. 1 is every loop, 3 is every third loop, 0 is never

        """
        experiment_order_parameter = []
        experiment_execution_freq = []
        # update the experiment order
        for sub_experiment_name in list(experiment_order.keys()):
            experiment_order_parameter.append(Parameter(sub_experiment_name, experiment_order[sub_experiment_name], int,
                                                        'Order in queue for this experiment'))

            experiment_execution_freq.append(Parameter(sub_experiment_name, 1, int,
                                                       'How often the experiment gets executed ex. 1 is every loop, 3 is every third loop, 0 is never'))

        return experiment_order_parameter, experiment_execution_freq

    @staticmethod
    def get_default_settings(sub_experiments, experiment_order, experiment_execution_freq, iterator_type):
        """
        assigning the actual experiment settings depending on the iterator type

        this might be overwritten by classes that inherit form ExperimentIterator

        Args:
            sub_experiments: dictionary with the subexperiments
            experiment_order: execution order of subexperiments
            experiment_execution_freq: execution frequency of subexperiments

        Returns:
            the default setting for the iterator

        """

        def populate_sweep_param(experiments, parameter_list, trace=''):
            '''

            Args:
                experiments: a dict of {'class name': <class object>} pairs

            Returns: A list of all parameters of the input experiments

            '''

            def get_parameter_from_dict(trace, dic, parameter_list, valid_values=None):
                """
                appends keys in the dict to a list in the form trace.key.subkey.subsubkey...
                Args:
                    trace: initial prefix (path through experiments and parameters to current location)
                    dic: dictionary
                    parameter_list: list to which append the parameters

                    valid_values: valid values of dictionary values if None dic should be a dictionary

                Returns:

                """
                if valid_values is None and isinstance(dic, Parameter):
                    valid_values = dic.valid_values

                for key, value in dic.items():
                    if isinstance(value, dict):  # for nested parameters ex {point: {'x': int, 'y': int}}
                        parameter_list = get_parameter_from_dict(trace + '.' + key, value, parameter_list,
                                                                 dic.valid_values[key])
                    elif (valid_values[key] in (float, int)) or \
                            (isinstance(valid_values[key], list) and valid_values[key][0] in (float, int)):
                        parameter_list.append(trace + '.' + key)
                    else:  # once down to the form {key: value}
                        # in all other cases ignore parameter
                        print(('ignoring sweep parameter', key))

                return parameter_list

            for experiment_name in list(experiments.keys()):
                from src.core import ExperimentIterator
                experiment_trace = trace
                if experiment_trace == '':
                    experiment_trace = experiment_name
                else:
                    experiment_trace = experiment_trace + '->' + experiment_name
                if issubclass(experiments[experiment_name], ExperimentIterator):  # gets subexperiments of ExperimentIterator objects
                    populate_sweep_param(vars(experiments[experiment_name])['_EXPERIMENTS'], parameter_list=parameter_list,
                                         trace=experiment_trace)
                else:
                    # use inspect instead of vars to get _DEFAULT_SETTINGS also for classes that inherit _DEFAULT_SETTINGS from a superclass
                    for setting in \
                            [elem[1] for elem in inspect.getmembers(experiments[experiment_name]) if
                             elem[0] == '_DEFAULT_SETTINGS'][0]:
                        parameter_list = get_parameter_from_dict(experiment_trace, setting, parameter_list)

            return parameter_list

        if iterator_type == 'loop':
            experiment_default_settings = [
                Parameter('experiment_order', experiment_order),
                Parameter('experiment_execution_freq', experiment_execution_freq),
                Parameter('num_loops', 0, int, 'times the subexperiments will be executed'),
                Parameter('run_all_first', True, bool, 'Run all experiments with nonzero frequency in first pass')
            ]

        elif iterator_type == 'sweep':

            sweep_params = populate_sweep_param(sub_experiments, [])

            experiment_default_settings = [
                Parameter('experiment_order', experiment_order),
                Parameter('experiment_execution_freq', experiment_execution_freq),
                Parameter('sweep_param', sweep_params[0], sweep_params, 'variable over which to sweep'),
                Parameter('sweep_range', [Parameter('min_value', 0, float, 'min parameter value'),
                                          Parameter('max_value', 0, float, 'max parameter value'),
                                          Parameter('N/value_step', 0, float,
                                                    'either number of steps or parameter value step, depending on mode'),
                                          Parameter('randomize', False, bool, 'randomize the sweep parameters')]),
                Parameter('stepping_mode', 'N', ['N', 'value_step'], 'Switch between number of steps and step amount'),
                Parameter('run_all_first', True, bool, 'Run all experiments with nonzero frequency in first pass')
            ]
        else:
            print(('unknown iterator type ' + iterator_type))
            raise TypeError('unknown iterator type ' + iterator_type)

        return experiment_default_settings

    @staticmethod
    def create_dynamic_experiment_class(experiment_information, experiment_iterators={}, verbose=False):
        '''
        creates all the dynamic classes in the experiment and the class of the experiment itself
        and updates the experiment info with these new classes

        Args:
            experiment_information: A dictionary describing the ExperimentIterator, or an existing object
            experiment_iterators: dictionary with the Experimentiterators (optional)

        Returns:
            experiment_information:  The updated dictionary describing the newly created ExperimentIterator class
            experiment_iterators: updated dictionary with the Experimentiterators
        Poststate: Dynamically created classes inheriting from ExperimentIterator are added to AQuISS.experiments

        '''

        def set_up_dynamic_experiment(experiment_information, experiment_iterators, verbose=verbose):
            '''

            Args:
                experiment_information: information about the experiment as required by experiment.get_experiment_information()

            Returns:
                experiment_default_settings: the default settings of the dynamically created experiment as a list of parameters
                sub_experiments

                experiment_iterators: dictionary of the experiment_iterator classes of the form {'package_name': <experiment_iterator_classe>}
                package: name of the package of the experiment_iterator

            '''

            if verbose:
                print(('experiment_information', experiment_information))
            sub_experiments = {}  # dictonary of experiment classes that are to be subexperiments of the dynamic class. Should be in the dictionary form {'class_name': <class_object>} (btw. class_object is not the instance)
            experiment_order = []  # A list of parameters giving the order that the experiments in the ExperimentIterator should be executed. Must be in the form {'experiment_name': int}. experiments are executed from lowest number to highest
            experiment_execution_freq = []  # A list of parameters giving the frequency with which each experiment should be executed
            _, experiment_class_name, experiment_settings, _, experiment_sub_experiments, _, package = Experiment.get_experiment_information(
                experiment_information)

            if package not in experiment_iterators:
                experiment_iterators.update(ExperimentIterator.get_experiment_iterator(package))

            assert package in experiment_iterators

            iterator_type = getattr(experiment_iterators[package], 'get_iterator_type')(experiment_settings, experiment_sub_experiments)
            if verbose:
                print(('iterator_type  GD', iterator_type))

            if isinstance(experiment_information, dict):

                for sub_experiment_name, sub_experiment_class in experiment_sub_experiments.items():
                    if isinstance(sub_experiment_class, Experiment):
                        # experiment already exists

                        # To implement: add a function to experiments that outputs a experiment_information dict corresponding
                        # to the current settings. This can then be fed into experiment.get_experiment_information and things
                        # can proceed as below. We may also need to add an additional tracker to the dialogue window
                        # to differentiate between the case of wanting a new experiment from scratch when there is an
                        # identically named one already loaded, vs using that loaded experiment

                        raise NotImplementedError
                    elif experiment_sub_experiments[sub_experiment_name]['class'] == 'ExperimentIterator':
                        # raise NotImplementedError # has to be dynamic maybe???
                        experiment_information_subclass, experiment_iterators = ExperimentIterator.create_dynamic_experiment_class(
                            experiment_sub_experiments[sub_experiment_name], experiment_iterators)
                        subexperiment_class_name = experiment_information_subclass['class']

                        experiment_iterator_module = __import__('src.core.experiment_iterator')
                        sub_experiments.update({sub_experiment_name: getattr(experiment_iterator_module, subexperiment_class_name)})
                    else:
                        if verbose:
                            print(('experiment_sub_experiments[sub_experiment_name]', sub_experiment_class))

                        module = Experiment.get_experiment_module(sub_experiment_class, verbose=verbose)

                        if verbose:
                            print(('module', module))
                        new_subexperiment = getattr(module, experiment_sub_experiments[sub_experiment_name]['class'])
                        sub_experiments.update({sub_experiment_name: new_subexperiment})

                # for some iterators have default experiments, e.g. point iteration has select points
                default_sub_experiments, default_experiment_settings = getattr(experiment_iterators[package],
                                                                       'get_iterator_default_experiment')(iterator_type)

                sub_experiments.update(default_sub_experiments)

                for k, v in default_experiment_settings.items():
                    if k in experiment_settings:
                        experiment_settings[k].update(v)



            elif isinstance(experiment_information, Experiment):

                print('old code - DOUBLE CHECK')
                raise NotImplementedError
                # if the experiment already exists, just update the experiment order parameter
                sub_experiments.update({experiment_class_name: experiment_information})
            else:
                raise TypeError('create_dynamic_experiment_class: unknown type of experiment_information')

            experiment_order, experiment_execution_freq = getattr(experiment_iterators[package], 'get_experiment_order')(
                experiment_settings['experiment_order'])
            experiment_default_settings = getattr(experiment_iterators[package], 'get_default_settings')(sub_experiments,
                                                                                                 experiment_order,
                                                                                                 experiment_execution_freq,
                                                                                                 iterator_type)
            return experiment_default_settings, sub_experiments, experiment_iterators, package

        def create_experiment_iterator_class(sub_experiments, experiment_settings, experiment_iterator_base_class, verbose=verbose):
            """
            A 'factory' to create a ExperimentIterator class at runtime with the given inputs.

            Args:
                sub_experiments: dictonary of experiment classes that are to be subexperiments of the dynamic class. Should be in the dictionary
                         form {'class_name': <class_object>} (btw. class_object is not the instance)
                experiment_default_settings: the default settings of the dynamically created object. Should be a list of Parameter objects.

            Returns: A newly created class inheriting from ExperimentIterator, with the given subexperiments and default settings

            """

            # dynamically import the module, i.e. the namespace for the Experimentiterator
            experiment_iterator_module = __import__(experiment_iterator_base_class.__module__)

            if verbose:
                print('\n\n======== create_experiment_iterator_class ========\n')
                print(('sub_experiments', sub_experiments))
                print(('experiment_settings', experiment_settings))
                print(('experiment_iterator_base_class', experiment_iterator_base_class))

                print((experiment_iterator_base_class.__module__.split('.')[0]))

            class_name = experiment_iterator_base_class.__module__.split('.')[0] + '.dynamic_experiment_iterator' + str(
                experiment_iterator_base_class._number_of_classes)

            if verbose:
                print(('class_name', class_name))

            # If three parameters are passed to type(), it returns a new type object.
            # Three parameters to the type() function are:
            #
            #     name - class name which becomes __name__ attribute
            #     bases - a tuple that itemizes the base class, becomes __bases__ attribute
            #     dict - a dictionary which is the namespace containing definitions for class body; becomes __dict__ attribute
            dynamic_class = type(class_name, (experiment_iterator_base_class,),
                                 {'_EXPERIMENTS': sub_experiments, '_DEFAULT_SETTINGS': experiment_settings, '_DEVICES': {}})

            if verbose:
                print(('dynamic_class', dynamic_class))
                print(('__bases__', dynamic_class.__bases__))

                print(('dynamic_class.__name__', dynamic_class.__name__))
                print(('dynamic_class.__bases__', dynamic_class.__bases__))
                print(('dynamic_class.__dict__', dynamic_class.__dict__))

            # Now we place the dynamic experiment into the scope of AQuISS.
            setattr(experiment_iterator_module, class_name, dynamic_class)

            if verbose:
                print(('dynamic_class', dynamic_class))
                print(('__bases__', dynamic_class.__bases__))

                print(('dynamic_class.__name__', dynamic_class.__name__))
                print(('dynamic_class.__bases__', dynamic_class.__bases__))
                print(('dynamic_class.__dict__', dynamic_class.__dict__))

            experiment_iterator_base_class._class_list.append(dynamic_class)
            experiment_iterator_base_class._number_of_classes += 1

            return class_name, dynamic_class

            # todo: prevent multiple importation of the same experiment with different names
            # for someclass in cls._class_list:
            #     if (vars(ss)['_EXPERIMENTS'] == vars(someclass)['_EXPERIMENTS']):
            #         print('CLASSNAME', vars(someclass)['_CLASS'])
            #         return vars(someclass)['_CLASS']

        # get default setting, load subexperiments, load the experiment_iterators and identify the package
        experiment_default_settings, sub_experiments, experiment_iterators, package = set_up_dynamic_experiment(experiment_information,
                                                                                                experiment_iterators,
                                                                                                verbose=verbose)

        # now actually create the classs
        class_name, dynamic_class = create_experiment_iterator_class(sub_experiments, experiment_default_settings,
                                                                 experiment_iterators[package], verbose=verbose)

        # update the generic name (e.g. ExperimentIterator) to a unique name  (e.g. ExperimentIterator_01)
        experiment_information['class'] = class_name

        if 'iterator_type' in experiment_information['settings']:

            if verbose:
                print('WONDER IF WE EVER HAVE THIS CASE: iterator_type in experiment_information[setting]')
            experiment_settings = {}
            for elem in experiment_default_settings:
                experiment_settings.update(elem)
            experiment_information['settings'] = experiment_settings

            if verbose:
                print('\n\n======== create_dynamic_experiment_class ========\n')

                print(('dynamic_class', dynamic_class))
                print(('sub_experiments', sub_experiments))
                print(('experiment_settings', experiment_settings))

        if verbose:
            print('\n======== end create_dynamic_experiment_class ========\n')

        return experiment_information, experiment_iterators

    @staticmethod
    def get_experiment_iterator(package_name, verbose=False):
        """
        Args:
            package_name: name of package

        Returns: the experiment_iterators of the package as a dictionary

        """

        packs = hf.explore_package(package_name + '.core')
        print(packs)
        experiment_iterator = {}

        for p in packs:
            for name, c in inspect.getmembers(importlib.import_module(p), inspect.isclass):
                if verbose:
                    print(p, name, c)

                if issubclass(c, ExperimentIterator):
                    # update dictionary with 'Package name , e.g. AQuISS or b103_toolkit': <ExperimentIterator_class>
                    experiment_iterator.update({c.__module__.split('.')[0]: c})

        return experiment_iterator


if __name__ == '__main__':
    # test get_experiment_iterator
    package = 'AQuISS'

    experiment_iterator = ExperimentIterator.get_experiment_iterator(package, verbose=True)
    print(('experiment_iterator', experiment_iterator))
