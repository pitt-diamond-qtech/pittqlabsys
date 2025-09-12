this iskippedur # Created by Gurudev Dutt <gdutt@pitt.edu> on 2023-08-03
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

from src.core import Experiment,Parameter
from src.Controller.example_device import Plant,PIController,ExampleDevice
import pytest
import matplotlib.pyplot as plt
import numpy as np

"""This test file creates different Experiment classes and writes the test functions to pass them.
I have already moved all these definitions to the example_experiment module. Should rewrite the 
 test to import from there at a later date and remove all the definitions from this file or better yet to use a fixture 
 similar to the ones written for the NIDAQ test file. the tests in this file have passed successfully as of 08/16/2023
"""
class MinimalExperiment(Experiment):
    """
Minimal Example Experiment that has only a single parameter (execution time)
    """

    _DEFAULT_SETTINGS = [
        Parameter('execution_time', 0.1, float, 'execution time of experiment (s)'),
        Parameter('p1', 0.1, float, 'dummy param')
    ]

    _DEVICES = {}
    _EXPERIMENTS = {}

    def __init__(self, name=None, settings=None, devices=None, sub_experiments=None, log_function = None, data_path = None):
        """
        Example of a experiment
        Args:
            name (optional): name of experiment, if empty same as class name
            settings (optional): settings for this experiment, if empty same as default settings
            devices (optional): devices required for this experiment
            sub_experiments (optional): sub-experiments for this experiment
        """
        #Experiment.__init__(self, name, settings, log_function= log_function, data_path = data_path)
        super().__init__(name, settings, devices, sub_experiments, log_function= log_function, data_path = data_path)


    def _function(self):
        """
        This is the actual function that will be executed. It uses only information that is provided in the settings property
        will be overwritten in the __init__
        """
        import time
        print("Experiment test is running...")
        self.data = {'empty_data': []}
        time.sleep(self.settings['execution_time'])

class ExampleExperiment(Experiment):
    """
Example Experiment that has all different types of parameters (integer, str, fload, point, list of parameters). Plots 1D and 2D data.
    """

    _DEFAULT_SETTINGS = [
        Parameter('count', 3, int),
        Parameter('name', 'this is a counter'),
        Parameter('wait_time', 0.1, float),
        Parameter('point2',
                  [Parameter('x', 0.1, float, 'x-coordinate'),
                   Parameter('y', 0.1, float, 'y-coordinate')
                   ]),
        Parameter('plot_style', 'main', ['main', 'aux', '2D', 'two'])
    ]

    _DEVICES = {}
    _EXPERIMENTS = {}

    def __init__(self, name=None, settings=None, devices=None, sub_experiments=None, log_function=None, data_path=None):
        """
        Example of a experiment
        parameter name
        Args:
            name (optional): name of experiment, if empty same as class name
            settings (optional): settings for this experiment, if empty same as default settings
            devices (optional): devices required for this experiment
            sub_experiments (optional): sub-experiments for this experiment
        """
        #Experiment.__init__(self, name, settings, log_function=log_function, data_path=data_path)
        super().__init__(name, settings, devices, sub_experiments, log_function= log_function, data_path = data_path)

    def _function(self):
        """
        This is the actual function that will be executed. It uses only information that is provided in the settings property
        will be overwritten in the __init__
        """

        # some generic function
        import time
        import random
        self.data['random data'] = None
        self.data['image data'] = None
        count = self.settings['count']
        name = self.settings['name']
        wait_time = self.settings['wait_time']

        data = []
        self.log('I ({:s}) am a test function counting to {:d} and creating random values'.format(self.name, count))
        for i in range(count):
            time.sleep(wait_time)
            self.log('{:s} count {:02d}'.format(self.name, i))
            data.append(random.random())
            self.data = {'random data': data}
            self.progress = 100. * (i + 1) / count
            self.updateProgress.emit(self.progress)

        self.data = {'random data': data}

        # create image data
        Nx = int(np.sqrt(len(self.data['random data'])))
        img = np.array(self.data['random data'][0:Nx ** 2])
        img = img.reshape((Nx, Nx))
        self.data.update({'image data': img})

    def _plot(self, axes_list, data=None):
        """
        plots the data only the axes objects that are provided in axes_list
        Args:
            axes_list: a list of axes objects, this should be implemented in each subexperiment
            data: data to be plotted if empty take self.data
        Returns: None

        """

        plot_type = self.settings['plot_style']
        if data is None:
            data = self.data

        if data is not None and data is not {}:
            if plot_type in ('main', 'two'):
                if not data['random data'] is None:
                    axes_list[0].plot(data['random data'])
                    # 20230816 GD : next line removed because hold has been deprecated
                    #axes_list[0].hold(False)
            if plot_type in ('aux', 'two', '2D'):
                if not data['random data'] is None:
                    axes_list[1].plot(data['random data'])
                    # 20230816 GD : next line removed because hold has been deprecated
                    #axes_list[1].hold(False)
            if plot_type == '2D':
                if 'image data' in data and not data['image data'] is None:
                    fig = axes_list[0].get_figure()
                    implot = axes_list[0].imshow(data['image data'], cmap='pink', interpolation="nearest",
                                                 extent=[-1, 1, 1, -1])
                    fig.colorbar(implot, label='kcounts/sec')

    def _update(self, axes_list):
        """
        updates the data in already existing plots. the axes objects are provided in axes_list
        Args:
            axes_list: a list of axes objects, this should be implemented in each subexperiment

        Returns: None

        """
        plot_type = self.settings['plot_style']
        if plot_type == '2D':
            # we expect exactely one image in the axes object (see ExperimentDummy.plot)
            implot = axes_list[1].get_images()[0]
            # now update the data
            implot.set_data(self.data['random data'])

            colorbar = implot.colorbar

            if not colorbar is None:
                colorbar.update_bruteforce(implot)

        else:
            # fall back to default behaviour
            Experiment._update(self, axes_list)

class ExampleExperimentDevice(Experiment):
    """
Example Experiment that has all different types of parameters (integer, str, fload, point, list of parameters). Plots 1D and 2D data.
also loads an instrument.
    """

    _DEFAULT_SETTINGS = [
        Parameter('count', 3, int),
        Parameter('name', 'this is a counter'),
        Parameter('wait_time', 0.1, float),
        Parameter('point2',
                  [Parameter('x', 0.1, float, 'x-coordinate'),
                   Parameter('y', 0.1, float, 'y-coordinate')
                   ]),
        Parameter('plot_style', 'main', ['main', 'aux', '2D', 'two'])
    ]

    _DEVICES = {}
    _EXPERIMENTS = {}

    def __init__(self, name=None, devices=None, settings=None, log_function=None, data_path=None):
        """
        Example of a experiment
        Args:
            name (optional): name of experiment, if empty same as class name
            settings (optional): settings for this experiment, if empty same as default settings
        """
        #Experiment.__init__(self, name, settings, log_function=log_function, data_path=data_path)
        super().__init__(name,settings,devices=devices,log_function= log_function, data_path = data_path)
        self.devices = devices

    def _function(self):
        """
        This is the actual function that will be executed. It uses only information that is provided in the settings property
        will be overwritten in the __init__
        """

        # some generic function
        import time
        import random
        self.data['random data'] = None
        self.data['image data'] = None
        count = self.settings['count']
        name = self.settings['name']
        wait_time = self.settings['wait_time']

        data = []
        self.log('I ({:s}) am a test function counting to {:d} and creating random values'.format(self.name, count))
        for i in range(count):
            time.sleep(wait_time)
            self.log('{:s} count {:02d}'.format(self.name, i))
            data.append(random.random())
            self.data = {'random data': data}
            self.progress = 100. * (i + 1) / count
            self.updateProgress.emit(self.progress)

        self.data = {'random data': data}

        # create image data
        Nx = int(np.sqrt(len(self.data['random data'])))
        img = np.array(self.data['random data'][0:Nx ** 2])
        img = img.reshape((Nx, Nx))
        self.data.update({'image data': img})

    def _plot(self, axes_list, data=None):
        """
        plots the data only the axes objects that are provided in axes_list
        Args:
            axes_list: a list of axes objects, this should be implemented in each subexperiment
            data: data to be plotted if empty take self.data
        Returns: None

        """

        plot_type = self.settings['plot_style']
        if data is None:
            data = self.data

        if data is not None and data is not {}:
            if plot_type in ('main', 'two'):
                if not data['random data'] is None:
                    axes_list[0].plot(data['random data'])
                    # 20230816 GD : next line removed because hold has been deprecated
                    #axes_list[0].hold(False)
            if plot_type in ('aux', 'two', '2D'):
                if not data['random data'] is None:
                    axes_list[1].plot(data['random data'])
                    # 20230816 GD : next line removed because hold has been deprecated
                    #axes_list[1].hold(False)
            if plot_type == '2D':
                if 'image data' in data and not data['image data'] is None:
                    fig = axes_list[0].get_figure()
                    implot = axes_list[0].imshow(data['image data'], cmap='pink', interpolation="nearest",
                                                 extent=[-1, 1, 1, -1])
                    fig.colorbar(implot, label='kcounts/sec')

    def _update(self, axes_list):
        """
        updates the data in already existing plots. the axes objects are provided in axes_list
        Args:
            axes_list: a list of axes objects, this should be implemented in each subexperiment

        Returns: None

        """
        plot_type = self.settings['plot_style']
        if plot_type == '2D':
            # we expect exactely one image in the axes object (see ExperimentDummy.plot)
            implot = axes_list[1].get_images()[0]
            # now update the data
            implot.set_data(self.data['random data'])

            colorbar = implot.colorbar

            if not colorbar is None:
                colorbar.update_bruteforce(implot)

        else:
            # fall back to default behaviour
            Experiment._update(self, axes_list)

class ExampleExperimentWrapper(Experiment):
    """
Example Experiment wrapper that shows how to load sub-experiments
    """

    _DEFAULT_SETTINGS = [Parameter('plot_style', 'main', ['main', 'aux', '2D', 'two'])]

    _DEVICES = {}
    _EXPERIMENTS = {'ExptDummy':ExampleExperiment}
    #_EXPERIMENTS = {}

    def __init__(self,  name=None, settings=None, devices=None, sub_experiments=None, log_function=None, data_path=None):
        """
        Example of a experiment
        Args:
            name (optional): name of experiment, if empty same as class name
            settings (optional): settings for this experiment, if empty same as default settings
        """
        #super(ExampleExperimentWrapper, self).__init__(self, name, settings, devices, sub_experiments, log_function, data_path)
        super().__init__(name,settings,devices,sub_experiments,log_function,data_path)

    def _function(self):
        """
        This is the actual function that will be executed. It uses only information that is provided in the settings property
        will be overwritten in the __init__
        """

        self.experiments['ExptDummy'].run()

    def _plot(self, axes_list, data=None):
        """
        plots the data only the axes objects that are provided in axes_list
        Args:
            axes_list: a list of axes objects, this should be implemented in each subexperiment
            data: data to be plotted if empty take self.data
        Returns: None

        """

        self.experiments['ExptDummy']._plot(axes_list)

    def _update(self, axes_list):
        """
        updates the data in already existing plots. the axes objects are provided in axes_list
        Args:
            axes_list: a list of axes objects, this should be implemented in each subexperiment

        Returns: None

        """
        self.experiments['ExptDummy']._update(axes_list)

def test_minimal_experiment(capsys):
    """ Test passed . - GD 08/16/2023"""
    e = MinimalExperiment()
    with capsys.disabled():
        e.run()

def test_example_experiment(capsys):
    """ Test passed . - GD 08/16/2023"""
    e = ExampleExperiment()
    fig,ax = plt.subplots(2,1)
    e.settings['plot_style'] = "2D"
    with capsys.disabled():
        e.run()
        e._plot(axes_list=[ax[0],ax[1]])
        plt.show()

def test_example_experiment_wrapper(capsys):
    """ Test passed . - GD 08/16/2023"""
    expt = {'ExptDummy':ExampleExperiment()}
    instr = {"DummyDev":Plant}
    ew = ExampleExperimentWrapper(devices=instr,sub_experiments=expt)
    assert ew is not None
    fig, ax = plt.subplots(2, 1)
    ew.settings['plot_style'] = "2D"
    with capsys.disabled():
        ew.run()
        ew._plot(axes_list=[ax[0], ax[1]])
        plt.show()

def test_load_and_append(capsys):
    """ Test passed . - GD 08/16/2023"""
    ew,failed,instr = Experiment.load_and_append({'Example_Expt':MinimalExperiment})
    with capsys.disabled():
        print(failed)
        print(ew)
    assert failed == {}
    # fig, ax = plt.subplots(2, 1)
    # ew.settings['plot_style'] = "2D"
    # with capsys.disabled():
    #     ew.run()
    #     ew._plot(axes_list=[ax[0], ax[1]])
    #     plt.show()

def test_load_experiment_device(capsys):
    expt = {'ExptDummy': ExampleExperiment()}
    instr = {"DummyDev": Plant}
    ew = ExampleExperimentDevice(devices=instr)
    assert ew is not None
    assert len(ew.devices) != 0
    with capsys.disabled():
        print("Example experiment device has devices",ew.devices)