# Created by Gurudev Dutt on 2023-07-20
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
import os, inspect
from src.core.parameter import Parameter
import traceback
from copy import deepcopy
from importlib import import_module
from src.core.helper_functions import module_name_from_path
from src.core.read_write_functions import save_aqs_file


class Device:
    """
    generic device class
    for subclass overwrite following old_functions/properties:
        - default_settings => parameter object, that is alist of parameters that can be set to configure the device
        - update => function that sends parameter changes to the device
        - values => dictionary that contains all the values that can be read from the device
        - read_probes => function that actually requests the values from the device
        - is_connected => property that checks if the device is actually connected

    """
    _DEFAULT_SETTINGS = Parameter("default", 0, int, "some int parameter")

    @classmethod
    def _get_base_settings(cls):
        """
        Get the base class settings as a list of Parameter objects.
        This can be used by subclasses to ensure they inherit all base parameters.
        
        Returns:
            List of Parameter objects from the base class
        """
        base_settings = []
        for key in cls._DEFAULT_SETTINGS.keys():
            base_settings.append(Parameter(
                key, 
                cls._DEFAULT_SETTINGS[key], 
                cls._DEFAULT_SETTINGS.valid_values[key],
                cls._DEFAULT_SETTINGS.info[key],
                cls._DEFAULT_SETTINGS.visible[key],
                cls._DEFAULT_SETTINGS.units[key] if hasattr(cls._DEFAULT_SETTINGS, 'units') else None
            ))
        return base_settings

    def __init__(self, name=None, settings=None):
        self._initialized = True
        self._settings_initialized = False

        # make a deepcopy of the default settings
        # because _DEFAULT_SETTINGS is a class variable and thus shared among the instances
        self._settings = deepcopy(self._DEFAULT_SETTINGS)
        if name is None:
            name = self.__class__.__name__

        self.name = name

        self._is_connected = False  # internal flag that indicated if device is actually connected

        if settings is not None:
            self.update(settings)

        self._settings_initialized = True

        # apply settings to device should be carried out in derived class

    def default_settings(self):
        """
        returns the default parameter_list of the device this function should be over written in any subclass
        """
        return NotImplementedError

    def update(self, settings):
        """
        updates the internal dictionary and sends changed values to device
        Args:
            settings: parameters to be set
        # mabe in the future:
        # Returns: boolean that is true if update successful

        """
        self._settings.update(settings)

    def update_and_get(self, settings):
        """
        Update device settings and return the actual values from hardware.
        This is useful for students to see what values the device actually accepted,
        especially when the device clamps values to valid ranges.
        
        Args:
            settings: parameters to be set
            
        Returns:
            dict: Dictionary of the actual hardware values after update
        """
        # Use the enhanced feedback method internally, but only return actual values
        result = self._update_and_get_with_feedback(settings)
        return result['actual_values']
    
    def _update_and_get_with_feedback(self, settings):
        """Update device settings and return detailed feedback about changes.
        
        This enhanced version provides context about why values changed,
        distinguishing between clamping, errors, and successful updates.
        
        Note: This is an internal method. update_and_get() calls this method internally 
        and returns only actual_values. Users should not call this method directly.
        
        Args:
            settings: Dictionary of parameter values to update
            
        Returns:
            Dictionary with 'actual_values' and 'feedback' keys:
            - actual_values: Dictionary of actual parameter values
            - feedback: Dictionary of feedback for each parameter
        """
        # Store original values for comparison
        original_values = {}
        for key in settings.keys():
            if key in self._settings:
                original_values[key] = self._settings[key]
        
        # Update the device
        self.update(settings)
        
        # Get actual values
        if '_PROBES' in self.__dict__ and self._PROBES:
            actual_values = self.read_probes()
        else:
            actual_values = dict(self._settings)
        
        # Generate feedback for each parameter
        feedback = {}
        for key, requested_value in settings.items():
            if key in actual_values:
                actual_value = actual_values[key]
                
                # Check if value changed
                if hasattr(requested_value, 'magnitude') and hasattr(actual_value, 'magnitude'):
                    # Pint quantities
                    changed = requested_value.magnitude != actual_value.magnitude
                else:
                    # Regular values
                    changed = requested_value != actual_value
                
                if changed:
                    # Value changed - need to determine why
                    feedback[key] = {
                        'changed': True,
                        'requested': requested_value,
                        'actual': actual_value,
                        'reason': 'unknown',  # Subclasses should override to provide specific reasons
                        'message': f'Value changed from {requested_value} to {actual_value}'
                    }
                else:
                    # Value unchanged
                    feedback[key] = {
                        'changed': False,
                        'requested': requested_value,
                        'actual': actual_value,
                        'reason': 'success',
                        'message': 'Value set successfully'
                    }
            else:
                # Parameter not found
                feedback[key] = {
                    'changed': True,
                    'requested': requested_value,
                    'actual': None,
                    'reason': 'not_found',
                    'message': f'Parameter {key} not found in device'
                }
        
        return {
            'actual_values': actual_values,
            'feedback': feedback
        }
    
    def get_feedback_only(self, settings):
        """Update device settings and return only the feedback about changes.
        
        Convenience method that calls _update_and_get_with_feedback() but returns
        only the feedback dictionary. Useful when you only need to know why values
        changed but don't need the actual values.
        
        Args:
            settings: Dictionary of parameter values to update
            
        Returns:
            Dictionary of feedback for each parameter
        """
        result = self._update_and_get_with_feedback(settings)
        return result['feedback']

    def validate_parameter(self, path, value):
        """
        Validate a parameter value before setting it.
        This method can be overridden by device subclasses to provide custom validation.
        
        Args:
            path: List of strings representing the path to the parameter in device settings
            value: The value to validate
            
        Returns:
            dict: Validation result with keys:
                - 'valid': bool - Whether the value is valid
                - 'message': str - Error message if invalid
                - 'clamped_value': Any - Suggested clamped value if applicable
        """
        try:
            # Basic validation - check if the parameter exists
            current_settings = self._settings
            for i, element in enumerate(path):
                if i == len(path) - 1:
                    # Last element - check if it's a key in the current settings
                    if element in current_settings:
                        # Get the actual parameter object for validation
                        param_value = current_settings[element]
                        # For Parameter objects, we need to check if the value is a pint quantity
                        if hasattr(param_value, 'magnitude') and hasattr(param_value, 'units'):
                            # This is a pint quantity - create a mock parameter for validation
                            from src.core.parameter import Parameter
                            mock_param = Parameter(element, param_value, float, 'Parameter', units=str(param_value.units))
                            return self._validate_pint_parameter(mock_param, value)
                        else:
                            # Regular parameter validation
                            return {'valid': True, 'message': 'Parameter validation passed'}
                    else:
                        return {
                            'valid': False,
                            'message': f"Parameter path {'.'.join(path)} not found in device settings"
                        }
                else:
                    # Intermediate element - check if it's a key
                    if element in current_settings:
                        current_settings = current_settings[element]
                    else:
                        return {
                            'valid': False,
                            'message': f"Parameter path {'.'.join(path)} not found in device settings"
                        }
            
        except Exception as e:
            return {
                'valid': False,
                'message': f"Validation error: {str(e)}"
            }
    
    def _validate_pint_parameter(self, parameter, value):
        """
        Validate a pint quantity parameter.
        
        Args:
            parameter: Parameter object with pint quantity
            value: Value to validate (can be pint.Quantity, number, or string with units)
            
        Returns:
            dict: Validation result
        """
        try:
            from src import ur
            
            # Convert value to pint quantity if needed
            if not hasattr(value, 'magnitude') or not hasattr(value, 'units'):
                if isinstance(value, (int, float)):
                    # Assume same units as current parameter
                    current_value = parameter[list(parameter.keys())[0]]
                    if hasattr(current_value, 'units'):
                        value = value * current_value.units
                    else:
                        # No units specified, use dimensionless
                        value = value * ur.dimensionless
                elif isinstance(value, str):
                    # Try to parse as pint quantity
                    try:
                        value = ur.Quantity(value)
                    except:
                        return {
                            'valid': False,
                            'message': f"Cannot parse '{value}' as a quantity with units"
                        }
            
            # Check unit compatibility
            current_value = parameter[list(parameter.keys())[0]]
            if hasattr(current_value, 'dimensionality') and hasattr(value, 'dimensionality'):
                if current_value.dimensionality != value.dimensionality:
                    try:
                        # Try to convert to show what the value would be
                        converted_value = value.to(current_value.units)
                        return {
                            'valid': False,
                            'message': f"Unit dimensionality mismatch: {value.dimensionality} vs {current_value.dimensionality}",
                            'clamped_value': converted_value
                        }
                    except:
                        # If conversion fails, just return the error without clamped_value
                        return {
                            'valid': False,
                            'message': f"Unit dimensionality mismatch: {value.dimensionality} vs {current_value.dimensionality}"
                        }
            
            return {
                'valid': True,
                'message': f"Valid pint quantity: {value}",
                'clamped_value': value
            }
            
        except Exception as e:
            return {
                'valid': False,
                'message': f"Pint validation error: {str(e)}"
            }

    def get_parameter_ranges(self, path):
        """
        Get valid parameter ranges for a device parameter.
        This method can be overridden by device subclasses to provide custom range information.
        
        Args:
            path: List of strings representing the path to the parameter in device settings
            
        Returns:
            dict: Dictionary with parameter range information:
                - 'min': minimum valid value (if applicable)
                - 'max': maximum valid value (if applicable)  
                - 'valid_values': list of valid values (if applicable)
                - 'type': expected data type
        """
        try:
            current_settings = self._settings
            for element in path:
                if hasattr(current_settings, element):
                    current_settings = getattr(current_settings, element)
                else:
                    return {}
            
            result = {}
            
            if hasattr(current_settings, 'valid_values'):
                valid_values = current_settings.valid_values
                
                if isinstance(valid_values, list):
                    result['valid_values'] = valid_values
                elif valid_values in (int, float):
                    result['type'] = valid_values
                    # Try to get min/max from Parameter info if available
                    if hasattr(current_settings, 'info') and isinstance(current_settings.info, str):
                        info = current_settings.info.lower()
                        # Look for range hints in the info string
                        if 'range' in info or 'between' in info:
                            result['info'] = current_settings.info
            
            return result
            
        except Exception as e:
            return {}

    @property
    def _PROBES(self):
        """

        Returns: a dictionary that contains the values that can be read from the device
        the key is the name of the value and the value of the dictionary is an info

        """
        raise NotImplementedError

    def read_probes(self, key=None):
        """
        function is overloaded:
            - read_probes()
            - read_probes(key)

        Args:
            key: name of requested value

        Returns:
            - if called without argument: returns the values of all probes in dictionary form
            - if called with argument: returns the value the requested key

        """

        #        print(('xxxxx probes', key, self._PROBES()))

        if key is None:
            # return the value all probe in dictionary form
            d = {}
            for k in list(self._PROBES.keys()):
                d[k] = self.read_probes(k)
            return d
        else:
            # return the value of the requested key if the key corresponds to a valid probe
            assert key in list(self._PROBES.keys())

            value = None

            return value

    @property
    def is_connected(self):
        '''
        check if device is active and connected and return True in that case
        :return: bool
        '''
        return self._is_connected

    # ========================================================================================
    # ======= Following old_functions are generic ================================================
    # ========================================================================================
    # do not override this, override read_probes instead
    def __getattr__(self, name):
        """
        allows to read device inputs in the form value = device.input
        Args:
            name: name of input channel

        Returns: value of input channel
        """

        # Only intercept probe-related attributes, not normal attributes
        if '_PROBES' in self.__dict__ and name in self._PROBES:
            try:
                return self.read_probes(name)
            except:
                # If probe reading fails, still raise AttributeError
                raise AttributeError(f'class {type(self).__name__} has no attribute {str(name)}')
        
        # For non-probe attributes, raise AttributeError normally
        # This allows normal attribute access to work without interference
        raise AttributeError(f'class {type(self).__name__} has no attribute {str(name)}')

    def __setattr__(self, key, value):
        """
        this allows to address device outputs of the form device.output = value
        """
        try:
            # Check if _initialized exists and is True
            if not hasattr(self, '_initialized') or not self._initialized:
                # fall back to regular behaviour of the parent class
                object.__setattr__(self, key, value)
            else:
                # Check if this is a settings parameter or an internal attribute
                if hasattr(self, '_settings') and key in self._settings:
                    # This is a settings parameter, update it
                    self.update({key: value})
                else:
                    # This is an internal attribute, set it directly
                    object.__setattr__(self, key, value)
        except (AttributeError, KeyError):
            object.__setattr__(self, key, value)

    def __repr__(self):
        """

        Returns: the device as a string  for display

        """

        output_string = '{:s} (class type: {:s})'.format(self.name, self.__class__.__name__)

        return output_string

    def __str__(self):
        return "Device class with name {}".format(self.name)

    @property
    def name(self):
        """
        Returns:
            device name

        """
        return self._name

    @name.setter
    def name(self, value):
        """
        check if value is a string and if so set name = value
        """
        if isinstance(value, str):
            value = str(value)
        assert isinstance(value, str), "{:s}".format(str(value))
        self._name = value

    @property
    def settings(self):
        """
        Returns:
            device settings

        """
        return self._settings

    def to_dict(self):
        """

        Returns: the device itself as a dictionary

        """

        dictator = {self.name: {'class': self.__class__.__name__,
                                'filepath': inspect.getfile(self.__class__),
                                'info': self.__doc__,
                                'settings': self.settings}}

        return dictator

    def save_aqs(self, filename):
        """
        saves the device to path as a .json file (default) or .aqs file
        Now saves as JSON by default, but maintains backward compatibility for .aqs files

        Args:
            filename: path of file
        """

        save_aqs_file(filename, devices=self.to_dict())

    @staticmethod
    def load_and_append(device_dict, devices=None, raise_errors=False):
        """
        load device from device_dict and append to devices

        Args:
            device_dict: dictionary of form

                device_dict = {
                name_of_device_1 :
                    {"settings" : settings_dictionary, "class" : name_of_class}
                name_of_device_2 :
                    {"settings" : settings_dictionary, "class" : name_of_class}
                ...
                }

            or

                device_dict = {
                name_of_device_1 : name_of_class,
                name_of_device_2 : name_of_class
                ...
                }

            where name_of_class is either a class or a dictionary of the form {class: name_of__class, filepath: path_to_instr_file}

            devices: dictionary of form

                devices = {
                name_of_device_1 : instance_of_device_1,
                name_of_device_2 : instance_of_device_2,
                ...
                }

            raise_errors: if true errors are raised, if False they are caught but not raised



        Returns:
                dictionary updated_devices that contains the old and the new devices

                and list loaded_failed = [name_of_device_1, name_of_device_2, ....] that contains the devices that
                were requested but could not be loaded

        """
        if devices is None:
            devices = {}

        updated_devices = {}
        updated_devices.update(devices)
        loaded_failed = {}

        for device_name, device_class_name in device_dict.items():
            device_settings = None
            module = None

            # check if device already exists
            if device_name in list(devices.keys()) \
                    and device_class_name == devices[device_name].__name__:
                print(('WARNING: device {:s} already exists. Did not load!'.format(device_name)))
                loaded_failed[device_name] = device_name
            else:
                device_instance = None

                if device_class_name is None:
                    loaded_failed[device_name] = "device class name returned None."
                elif isinstance(device_class_name, dict):
                    if 'settings' in device_class_name:
                        device_settings = device_class_name['settings']
                    device_filepath = str(device_class_name['filepath'])
                    device_class_name = str(device_class_name['class'])
                    path_to_module, _ = module_name_from_path(device_filepath, verbose=False)
                    module = import_module(path_to_module)
                    class_of_device = getattr(module, device_class_name)
                    try:
                        if device_settings is None:
                            # this creates an instance of the class with default settings
                            device_instance = class_of_device(name=device_name)
                        else:
                            # this creates an instance of the class with custom settings
                            device_instance = class_of_device(name=device_name,
                                                              settings=device_settings)
                    except Exception as e:
                        loaded_failed[device_name] = e
                        print('loading ' + device_name + ' failed:')
                        print(traceback.format_exc())
                        if raise_errors:
                            raise e
                        continue
                elif isinstance(device_class_name, Device):
                    class_of_device = device_class_name.__class__
                    device_filepath = os.path.dirname(inspect.getfile(class_of_device))
                    device_instance = device_class_name
                    #raise NotImplementedError
                elif issubclass(device_class_name, Device):
                    class_of_device = device_class_name
                    try:
                        if device_settings is None:
                            # this creates an instance of the class with default settings
                            device_instance = class_of_device(name=device_name)
                        else:
                            # this creates an instance of the class with custom settings
                            device_instance = class_of_device(name=device_name,
                                                              settings=device_settings)
                    except Exception as e:
                        loaded_failed[device_name] = e
                        # print(device_name, ': ', str(e))
                        print('loading ' + device_name + ' failed:')
                        print(traceback.format_exc())
                        if raise_errors:
                            raise e
                        continue


                updated_devices[device_name] = device_instance

        return updated_devices, loaded_failed


if __name__ == '__main__':
    dummy_dev = Device()
    print("Dummy device has default settings", dummy_dev.settings)
    # devices, __ = Device.load_and_append({'DummyDevice': DummyDevice})
    # for dev in devices:
    #     print("-----")
    #     print("Device %s is of class %s",dev,dev.device_class_name)
    # folder_name = ''
    #
    # x = Device.get_devices_in_path(folder_name)
    #
    # for k, v in x.items():
    #     print((k, issubclass(v['x'], Script), issubclass(v['x'], Device)))
