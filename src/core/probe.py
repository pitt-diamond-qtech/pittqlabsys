# Created by Gurudev Dutt <gdutt@pitt.edu> on 2020-07-23
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

from src.core.device import Device
#from src.Controller import ExampleDevice
from collections import deque
from src.core.read_write_functions import save_aqs_file


class Probe(object):

    def __init__(self, device, probe_name, name=None, info=None, buffer_length=100):
        """
        creates a probe...
        Args:
            name (optinal):  name of probe, if not provided take name of function
            settings (optinal): a Parameter object that contains all the information needed in the script
        """

        assert isinstance(device, Device)
        assert isinstance(probe_name, str)
        assert probe_name in device._PROBES

        if name is None:
            name = probe_name
        assert isinstance(name, str)

        if info is None:
            info = ''
        assert isinstance(info, str)

        self.name = name
        self.info = info
        self.device = device
        self.probe_name = probe_name

        self.buffer = deque(maxlen=buffer_length)

    @property
    def value(self):
        """
        reads the value from the device
        """

        value = getattr(self.device, self.probe_name)
        self.buffer.append(value)

        return value

    def __str__(self):
        output_string = '{:s} (class type: {:s})\n'.format(self.name, self.__class__.__name__)
        return output_string

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        assert isinstance(value, str)
        self._name = value

    def plot(self, axes):
        axes.plot(self.buffer)
        axes.hold(False)

    def to_dict(self):
        """

        Returns: itself as a dictionary

        """

        # dictator = {self.name: {'probe_name': self.probe_name, 'device_name': self.device.name}}
        dictator = {self.device.name: self.probe_name}

        return dictator

    def save(self, filename):
        """
        save the device to path as a .json file (default) or .aqs file
        Now saves as JSON by default, but maintains backward compatibility for .aqs files

        Args:
            filename: path of file
        """
        save_aqs_file(filename, probes=self.to_dict())

    @staticmethod
    def load_and_append(probe_dict, probes, devices={}):
        """
        load probes from probe_dict and append to probes, if additional devices are required create them and add them to devices

        Args:
            probe_dict: dictionary of form

                probe_dict = {
                    device1_name : probe1_of_device1, probe2_of_device1, ...
                    device2_name : probe1_of_device2, probe2_of_device2, ...
                }

            where probe1_of_device1 is a valid name of a probe in device of class device1_name

            # optional arguments (as key value pairs):
            #     probe_name
            #     device_name
            #     probe_info
            #     buffer_length
            #
            #
            # or
            #     probe_dict = {
            #     name_of_probe_1 : device_class_1
            #     name_of_probe_2 : device_class_2
            #     ...
            #     }


            probes: dictionary of form
                probe_dict = {
                    device1_name:
                        {name_of_probe_1_of_device1 : probe_1_instance,
                         name_of_probe_2_device1 : probe_2_instance
                         }
                         , ...}

            devices: dictionary of form

                devices = {
                name_of_device_1 : instance_of_device_1,
                name_of_device_2 : instance_of_device_2,
                ...
                }
    Returns:
                updated_probes = { name_of_probe_1 : probe_1_instance, name_of_probe_2 : probe_2_instance, ...}
                loaded_failed = {name_of_probe_1: exception_1, name_of_probe_2: exception_2, ....}
                updated_devices
        """

        loaded_failed = {}
        updated_probes = {}
        updated_probes.update(probes)
        updated_devices = {}
        updated_devices.update(devices)

        # =====  load new devices =======
        new_devices = list(set(probe_dict.keys()) - set(probes.keys()))
        if new_devices:
            updated_devices, failed = Device.load_and_append({device_name: device_name for device_name in new_devices},
                                                             devices)

            if failed:
                # if loading an device fails all the probes that depend on that device also fail
                # ignore the failed device that did exist already because they failed because they did exist
                for failed_device in set(failed) - set(devices.keys()):
                    for probe_name in probe_dict[failed_device]:
                        loaded_failed[probe_name] = ValueError(
                            'failed to load device {:s} already exists. Did not load!'.format(failed_device))
                    del probe_dict[failed_device]

        # =====  now we are sure that all the devices that we need for the probes already exist

        for device_name, probe_names in probe_dict.items():
            if not device_name in updated_probes:
                updated_probes.update({device_name: {}})

            for probe_name in probe_names.split(','):
                if probe_name in updated_probes[device_name]:
                    loaded_failed[probe_name] = ValueError(
                        'failed to load probe {:s} already exists. Did not load!'.format(probe_name))
                else:
                    probe_instance = Probe(updated_devices[device_name], probe_name)
                    updated_probes[device_name].update({probe_name: probe_instance})

        return updated_probes, loaded_failed, updated_devices


if __name__ == '__main__':
    pass
    # probe_dict = {'DummyDevice': 'internal,value1'}
    # devices, __ = Device.load_and_append({'DummyDevice': ExampleDevice})
    # print(devices)
    # # probe load and append still has bugs....could this be an issue?
    # probes_obj, failed, devices = Probe.load_and_append(
    #     probe_dict=probe_dict,
    #     probes={},
    #     devices=devices)
    # print(('fffff', probes_obj))
