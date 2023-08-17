# Created by Gurudev Dutt <gdutt@pitt.edu> on 2023-08-17
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


from PyQt5.QtCore import pyqtSignal, QThread
from src.core import Device,Probe
from src.Controller import ExampleDevice


class ReadProbes(QThread):
    # This is the signal that will be emitted during the processing.
    # By including int as an argument, it lets the signal know to expect
    # an integer argument when emitting.
    # updateProgress = QtCore.Signal(int)

    _DEFAULT_SETTINGS = None

    updateProgress = pyqtSignal(int)

    def __init__(self, probes, refresh_interval=2.0):
        """
        probes: dictionary of probes where keys are device names and values are dictonaries where key is probe name and value is Probe objects
        refresh_interval: time between reads in s
        """
        assert isinstance(probes, dict)
        assert isinstance(refresh_interval, float)

        self.refresh_interval = refresh_interval
        self._running = False
        self.probes = probes
        self.probes_values = None
        self._stop = False

        QThread.__init__(self)

    def run(self):
        """
        this is the actual execution of the ReadProbes thread: continuously read values from the probes
        """
        if self.probes is None:
            self._stop = True
        while True:

            if self._stop:
                break

            self.probes_values = {
                device_name:
                    {probe_name: probe_instance.value for probe_name, probe_instance in probe.items()}
                for device_name, probe in self.probes.items()
            }

            self.updateProgress.emit(1)

            self.msleep(int(1e3 * self.refresh_interval))

    def start(self, *args, **kwargs):
        """
        start the read_probe thread
        """
        self._stop = False
        super(ReadProbes, self).start(*args, **kwargs)

    def quit(self, *args, **kwargs):  # real signature unknown
        """
        quit the  read_probe thread
        """
        self._stop = True
        super(ReadProbes, self).quit(*args, **kwargs)


if __name__ == '__main__':

    devices = {'inst_dummy': ExampleDevice}

    devices = Device.load_and_append(devices)
    print(devices)
    probes = {
        'random': {'probe_name': 'value1', 'device_name': 'inst_dummy'},
        'value2': {'probe_name': 'value2', 'device_name': 'inst_dummy'},
    }

    probes = Probe.load_and_append(probes,probes)

    r = ReadProbes(probes)
    r.run()
