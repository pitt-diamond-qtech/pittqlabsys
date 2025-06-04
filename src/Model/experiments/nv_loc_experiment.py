from src.core import Parameter, Experiment
import numpy as np
import time
import pyqtgraph as pg

class NV_Locations(Experiment):
    """
    Minimal Example Experiment that has only a single parameter (execution time)
    """

    _DEFAULT_SETTINGS = [
        Parameter('point',
                  [Parameter('x', 5.0, float, 'x-coordinate microns'),
                   Parameter('y', 5.0, float, 'y-coordinate microns')
                   ]),
        Parameter('execution_time', 0.1, float, 'dummy param')
    ]

    _DEVICES = {}
    _EXPERIMENTS = {}

    def __init__(self, devices=None, experiments=None, name=None, settings=None, log_function=None, data_path=None):
        """
        Example of a experiment
        Args:
            name (optional): name of experiment, if empty same as class name
            settings (optional): settings for this experiment, if empty same as default settings
        """
        #Experiment.__init__(self, name, settings, log_function= log_function, data_path = data_path)
        super().__init__(name, settings=settings, sub_experiments=experiments, devices=devices,log_function=log_function, data_path=data_path)

    def _function(self):
        """
        This is the actual function that will be executed. It uses only information that is provided in the settings property
        will be overwritten in the __init__
        """
        nv_loc = self.settings['point']
        print(nv_loc)
        time.sleep(self.settings['execution_time'])