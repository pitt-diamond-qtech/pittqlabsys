# Created by Gurudev Dutt <gdutt@pitt.edu> on 2023-08-03
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

# from src.Model.experiments.example_experiment import ExampleExperiment,ExampleExperimentWrapper
# from src.Controller import ExampleDevice,Plant
from src.core import Experiment,Parameter
import pytest

#@pytest.mark.xfail

class ExperimentTest(Experiment):
    """
Minimal Example Experiment that has only a single parameter (execution time)
    """

    _DEFAULT_SETTINGS = [
        Parameter('execution_time', 0.1, float, 'execution time of experiment (s)'),
        Parameter('p1', 0.1, float, 'dummy param')
    ]

    _DEVICES = {}
    _EXPERIMENTS = {}

    def __init__(self, name=None, settings=None, log_function = None, data_path = None):
        """
        Example of a experiment
        Args:
            name (optional): name of experiment, if empty same as class name
            settings (optional): settings for this experiment, if empty same as default settings
        """
        Experiment.__init__(self, name, settings, log_function= log_function, data_path = data_path)


    def _function(self):
        """
        This is the actual function that will be executed. It uses only information that is provided in the settings property
        will be overwritten in the __init__
        """
        import time
        print("Experiment test is running...")
        time.sleep(self.settings['execution_time'])
def test_example_experiment():
    # expt = {}
    # instr = {"DummyDev":Plant}
    # expt,failed,instr = ExampleExperiment.load_and_append({'Example_Expt':'ExampleExperiment'},expt,instr)
    # assert failed == {}
    e = ExperimentTest()
    e.run()
    print(e)