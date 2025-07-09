# Created by Gurudev Dutt <gdutt@pitt.edu> on 2023-07-20
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

from pathlib import Path
import functools, logging
import os, inspect,sys
import psycopg2 as pg2
import datetime
from importlib import import_module
import glob
import pkgutil
import numpy as np
import h5py
from pyparsing import empty
from sympy.codegen import Print


def get_project_root() -> Path:  # new feature in Python 3.x i.e. annotations
    """Returns project root folder."""
    return Path(__file__).parent.parent


def module_name_from_path(folder_name, verbose=False):
    """
    takes in a path to a folder or file and return the module path and the path to the module

    the module is idenitified by
        the path being in os.path, e.g. if /Users/Projects/Python/ is in os.path,
        then folder_name = '/Users/PycharmProjects/AQuISS/src/experiments/experiment_dummy.pyc'
        returns '/Users/PycharmProjects/' as the path and AQuISS.src.experiment_dummy as the module

    Args:
        folder_name: path to a file of the form
        '/Users/PycharmProjects/AQuISS/AQuISS/experiments/experiment_dummy.pyc'

    Returns:
        module: a string of the form, e.g. AQuISS.experiments.experiment_dummy ...
        path: a string with the path to the module, e.g. /Users/PycharmProjects/

    """
    # strip off endings
    folder_name = folder_name.split('.pyc')[0]
    folder_name = folder_name.split('.py')[0]

    folder_name = os.path.normpath(folder_name)

    path = folder_name + '/'

    package = get_python_package(path)
    # path = folder_name
    module = []

    if verbose:
        print(('folder_name', folder_name))
    while True:

        path = os.path.dirname(path)

        module.append(os.path.basename(path))
        if os.path.basename(path) == package:
            path = os.path.dirname(path)
            break

        # failed to identify the module
        if os.path.dirname(path) == path:
            path, module = None, None
            break

        if verbose:
            print(('path', path, os.path.dirname(path)))

        if verbose:
            print(('module', module))

    if verbose:
        print(('module', module))

    # occurs if module not found in this path
    if (not module):
        raise ModuleNotFoundError('The path in the .aq file to this package is not valid')

    # module = module[:-1]
    # print('mod', module)
    # from the list construct the path like AQuISS.experiments and load it
    module.reverse()
    module = '.'.join(module)

    return module, path


def is_python_package(path):
    """
    checks if folder is a python package or not, i.e. does the folder contain a file __init__.py


    Args:
        path:

    Returns:

        True if path points to a python package
    """

    return os.path.isfile(os.path.join(path, '__init__.py'))


def get_python_package(filename):
    """

    retuns the name of the python package to which the file filename belongs. If file is not in a package returns None

    Note that if the file is in a subpackage, the highest lying package gets returned

    Args:   filename of file for which we would like to find the package
        filename:

    Returns:
        the name of the python package

    """

    package_found = False

    path = os.path.dirname(filename)

    # turn path to file into an array
    path_array = []
    while True:
        path = os.path.dirname(path)
        if path == os.path.dirname(path):
            break
        path_array.append(os.path.basename(path))

    # now successively build up the path and check if its a package
    path = os.path.normpath('/')
    for p in path_array[::-1]:
        path = os.path.join(path, p)

        if is_python_package(path):
            package_found = True
            break

    if package_found:
        return os.path.basename(path)
    else:
        None


def datetime_from_str(string):
    """

    Args:
        string: string of the form YYMMDD-HH_MM_SS, e.g 160930-18_43_01

    Returns: a datetime object

    """

    return datetime.datetime(year=2000 + int(string[0:2]), month=int(string[2:4]), day=int(string[4:6]),
                             hour=int(string[7:9]), minute=int(string[10:12]), second=int(string[13:15]))


def explore_package(module_name):
    """
    returns all the packages in the module

    Args:
        module_name: name of module

    Returns:

    """

    packages = []
    loader = pkgutil.get_loader(module_name)
    for sub_module in pkgutil.walk_packages([os.path.dirname(loader.get_filename())],
                                            prefix=module_name + '.'):
        _, sub_module_name, _ = sub_module
        packages.append(sub_module_name)

    return packages


#not using hdf5 but keeping function here if needed
def structure_data_for_hdf5(filename,data,settings=None,tag=None):
    '''
    Takes a list of data dictionaries and saves it as a HDF5 file.
    Args:
        filename: file address of hdf5 file to save
        data: list of data dictionaries (can have 1 item or sublists)
        settings: optional list of settings dictionaries that correspond to each data dictionary
        tag: name of tag to identify the experiment data; if None set to 'unamed_experiment'

    Returns:
        None

    1 layer example:
        data_1_layer = [ex_data_1, ex_data_2]
        settings_1_layer = [ex_settings_1, ex_settings_2]
        structure_data_for_hdf5(filename=filename+'.hdf5',data=data_1_layer, settings=settings_1_layer)

    #LAYERING NOT IMPLEMENTED YET
    2 layer example:
        data_2_layer = [[ex_data_1, ex_data_2],[ex_data_3, ex_data_4]]
        settings_2_layer = [[ex_settings_1, ex_settings_2],[ex_settings_3, ex_settings_4]]
        structure_data_for_hdf5(filename=filename+'.hdf5',data=data_2_layer, settings=settings_2_layer)
    '''
    def guess_numpy_dtype(value):
        '''
        Gets type of inputed value; skips dictionaries as they are recursivly unpacked
        '''
        if isinstance(value, float) or isinstance(value, list):
            return 'f8'
        elif isinstance(value, bool):  # need to put bool before int as True/False are technically 1/0
            return 'bool'
        elif isinstance(value, int):
            return 'i4'
        elif isinstance(value, str):
            return 'S{}'.format(len(value) + 1)  # +1 so empty string (S0) dont casue an error
        elif isinstance(value, np.ndarray):
            return value.dtype
        else:
            raise ValueError('hdf5 unsupported data type')

    def get_shape(value):
        if isinstance(value, np.ndarray):
            return value.shape
        elif isinstance(value, (list, tuple)):
            try:
                return np.array(value).shape
            except:
                return ()  # fallback if conversion fails
        else:
            return ()  # scalar or unknown type

    def write_dict_to_hdf5(group,dic):
        for key, value in dic.items():
            if isinstance(value, dict):
                sub_group = group.create_group(key)
                write_dict_to_hdf5(sub_group, value)
            else:
                value_type = guess_numpy_dtype(value)
                value_shape = get_shape(value)
                dset = group.create_dataset(key, shape=value_shape, dtype=value_type, data=value)

    #data and settings should be in lists
    if not isinstance(data, list):
        data = [data]
    if settings:
        if len(settings) != len(data): #should have a settings for each data dictionary
            raise ValueError("settings and data must be lists of equal length")
        if not isinstance(settings, list):
            settings = [settings]
    if tag is None:
        tag = 'unnamed_experiment'

    with h5py.File(filename, 'w') as f:
        for i, dic in enumerate(data):
            group = f.create_group(tag+f'_{i}')
            write_dict_to_hdf5(group, dic)

            if settings is not None:
                specific_settings = settings[i]
                settings_group = group.create_group('settings')
                write_dict_to_hdf5(settings_group, specific_settings)

class MatlabSaver:

    def __init__(self, tag = None):
        if tag is None:
            self.tag = 'unnamed_experiment'
        else:
            self.tag = tag

        #list to be populated by add_experiment_data method to check shape and alter data if needed
        self.all_dtype_list = []
        self.all_values_list = []
        self.largest_dtype_shapes = []

        self.final_dtype_list = None

        self.experiment_tuples = [] #stores a tuple with experiment data and settings for each experiment

    def add_experiment_data(self, data_dic, settings_dic, flatten_settings=False, iterator_info_dic=None, flatten_iterator_info=False):
        '''
        Args:
            data_dic: experiment data dictionary
            settings_dic: experiment settings dictionary
            expand_settings: If true will flatten settings dictionary so each key is a field in matlab file
                             If false settings will appear as a 1x1 struct in matlab file with keys as subfields
        Returns:
            value_list: List of values that can be made into an array for saving
            dtype_list: List of dtype touples for numpy array
        '''
        #ensure the inputs are dictionaries
        data_dic = dict(data_dic)
        settings_dic = dict(settings_dic)
        #list to store dictionary values
        values_list = []
        new_data_types_list = []
        field_shapes = []

        flat_data_dic = self._flatten_dic(data_dic)
        for key,value in flat_data_dic.items():
            #goes through each key and value in flattened data dictionary and gets datatype of each
            value_type = self._get_dtype(value)
            value_shape = self._get_shape(value)
            field_shapes.append(value_shape)
            new_data_types_list.append((key, value_type, value_shape))

            if value_type == 'f4' and value == None:
                values_list.append(np.nan)
            else:
                values_list.append(value)

        if flatten_settings:
            flat_settings_dic = self._flatten_dic(settings_dic)
            for key, value in flat_settings_dic.items():
                # goes through each key and value in flattend settings dictionary and gets datatype of each
                value_type = self._get_dtype(value)
                value_shape = self._get_shape(value)
                field_shapes.append(value_shape)
                new_data_types_list.append((key, value_type, value_shape))
                if value_type == 'f4' and value == None:
                    values_list.append(np.nan)
                else:
                    values_list.append(value)
        else:
            #if not flattening settings will be contained in a 1x1 struct and we just need to append 1 data type
            value_type = self._get_dtype(settings_dic)
            value_shape = self._get_shape(settings_dic)
            field_shapes.append(value_shape)
            new_data_types_list.append(('settings', value_type, value_shape))
            values_list.append(settings_dic)

        #for experiment iterators we want to know the sweep parameters; the iterator_info_dic is inputted similar to settings with optional flattening
        if iterator_info_dic is not None and flatten_iterator_info == True:
            flat_iterator_dic = self._flatten_dic(iterator_info_dic)
            for key, value in flat_iterator_dic.items():
                value_type = self._get_dtype(value)
                value_shape = self._get_shape(value)
                field_shapes.append(value_shape)
                new_data_types_list.append((key, value_type, value_shape))
                if value_type == 'f4' and value == None:
                    values_list.append(np.nan)
                else:
                    values_list.append(value)
        elif iterator_info_dic is not None:
            #iterator_info_dic has the form {'scan_param_it_#':'name','scan_current_val_it_#':value,'scan_all_vals_it_#:[...]}
            value_type = self._get_dtype(iterator_info_dic)
            value_shape = self._get_shape(iterator_info_dic)
            field_shapes.append(value_shape)
            new_data_types_list.append(('python_scan_info', value_type, value_shape))
            values_list.append(iterator_info_dic)

        self._update_largest_dtype_shapes(field_shapes) #update before checking data size so largest shapes are already calculated

        # all_dtype_list elements are lists ie the origonal data_types_list from each experiment
        self.all_dtype_list.append(new_data_types_list)
        # all_values_list elements are lists ie the values_list from each experiment
        self.all_values_list.append(values_list)

        if self.final_dtype_list is not None and new_data_types_list != self.final_dtype_list:
            if len(new_data_types_list) != len(self.final_dtype_list):
                raise ValueError("Mismatch in data field count between experiments.")
            #print('Variable data sizes..Changing shape of previous data')
            self._adjust_previous_data_shape(new_data_types_list)

        self._update_final_dtype_list(new_data_types_list)  # updates the final dtype list pasted to save function to have largest shapes

        return values_list, new_data_types_list

    def get_structured_data(self, return_array=False, verbose=False):
        '''
        Structures the values (self.all_values_list) and data type (self.final_dtype_list) as calculated by the add_experiment_data function
        to be compabile with matlab as a 1xn struct.
        Args:
            return_array: if you want the numpy array instead of the array added to a dictionary

        Returns:
            structured_data suitable for saving to matlab with scipy.io's savemat function
        '''
        if self.final_dtype_list is None:
            raise ValueError('Data type list has not been created')
        if self.all_values_list == []:
            raise ValueError('Values list is empty!')

        list_of_value_list_tuples = []
        for i in range(len(self.all_values_list)):
            list_of_value_list_tuples.append(tuple(self.all_values_list[i]))

        if verbose: #print which rows of data do not match the dtype
            for i, row in enumerate(list_of_value_list_tuples):
                if len(row) != len(self.final_dtype_list):
                    print(f"Row {i} length mismatch: {len(row)} vs expected {len(self.final_dtype_list)}")
                    print("Row data:", row)
                    print("Expected dtype keys:", [t[0] for t in self.final_dtype_list])
                else:
                    print(f"Row {i} OK (length {len(row)})")

        final_array = np.array(list_of_value_list_tuples, dtype=self.final_dtype_list)
        if return_array:  # for more complex shapes may want to get array to use in another function
            return final_array
        else:
            structured_data = {self.tag: final_array}
            return structured_data
        #unsure if savemat function has a size limit but I have tested up to 2MB and it works fine

    def _adjust_previous_data_shape(self, new_data_types_list, verbose=True):
        '''
        Goes through the experiment data values pertaining to each data type and reshapes if their shape does not match the largest.
        Only runs if the new inputted data types do not match the previous data types.
            - Does not check for name and variable type; those should be the same for sweeping a single experiment.
        Args:
            new_data_types_list: data type list of newly added data
        '''
        #print('Current dtype:', new_data_types_list, ' Previous dtype:', self.all_dtype_list[-1])

        for i in range(len(new_data_types_list)):
            target_shape = self.largest_dtype_shapes[i]
            for j, exp_data in enumerate(self.all_values_list):
                current_shape = self._get_shape(exp_data[i])
                if current_shape != target_shape:
                    if verbose:
                        print(f"Reshaping row {j}, field {i}, from {current_shape} to {target_shape}")
                    new_data = self._embed_array(exp_data[i], target_shape)
                    self.all_values_list[j][i] = new_data

    def _update_largest_dtype_shapes(self, field_shapes):
        """
        Update the stored largest shape for each field based on a new list of shapes.
        Expands self.largest_dtype_shapes as needed and updates any field whose shape grew.

        Args:
            field_shapes (List[Tuple]): A list of shapes (tuples), one for each field.
        """
        for i, shape in enumerate(field_shapes):
            if i >= len(self.largest_dtype_shapes):
                # First time seeing this field, just append
                self.largest_dtype_shapes.append(shape)
            else:
                # Update to largest shape seen so far
                current_largest = self.largest_dtype_shapes[i]
                new_largest = self._highest_common_shape(current_largest, shape)
                self.largest_dtype_shapes[i] = new_largest

    def _update_final_dtype_list(self, dtype_list):
        """
        Rebuild the final dtype list using the largest shapes seen and the most recent types.
        Uses the field names and types from dtype_list,
        but replaces shapes with the largest known shape.
        """
        self.final_dtype_list = []
        for i, (name, dtype, _) in enumerate(dtype_list):
            largest_shape = self.largest_dtype_shapes[i]
            self.final_dtype_list.append((name, dtype, largest_shape))

    def _compare_tuples(self, a, b):
        '''
        Compares two tuples and returns a list of tuples with differences
        Args:
            a: 1st tuple
            b: 2nd tuple

        Returns:
            differences: list of tuples [(index of differnece, 1st tup value, 2nd tup value),...]

        With current logic not used
        '''
        if len(a) != len(b):
            raise ValueError("Tuples must have the same length")

        differences = []
        for i, (x, y) in enumerate(zip(a, b)):
            if isinstance(x, float) and isinstance(y, float):
                if np.isnan(x) and np.isnan(y):
                    continue  # treat NaNs as equal
                if np.isposinf(x) and np.isposinf(y):
                    continue
                if np.isneginf(x) and np.isneginf(y):
                    continue
            if x != y:
                index = i
                first_tup_val = x
                second_tup_val = y
                differences.append((index, first_tup_val, second_tup_val))
        #print('tuple differences:',differences)
        return differences

    def _get_dtype(self, value):
        '''
        Checks the variable type and returns the corresponding dtype string suitable for matlab
        '''
        #print('value type:', type(value))
        if isinstance(value, np.ndarray):
            return value.dtype
        elif isinstance(value, float) or isinstance(value, list):
            return 'f8'
        elif isinstance(value, int):
            return 'i4'
        elif isinstance(value, str):
            return 'U{}'.format(len(value)+1) #+1 so empty string (U0) dont casue an error
        elif isinstance(value, bool):
            return 'O' #matlab reconizes a boolean as its logical data type
        elif value is None:
            return 'f4' #if value is None will set as np.nan which is a float data type
        elif isinstance(value, dict):
            return 'O'
        else:
            print('Value type not recognized...Defaulting to object...May corrupt data')
            return 'O'

    def _get_shape(self, value):
        '''
        Checks the variable shape and returns the corresponding dtype shape suitable for matlab
        '''
        if isinstance(value, np.ndarray):
            return value.shape
        elif isinstance(value, (list, tuple)):
            try:
                return np.array(value).shape
            except:
                return ()  # fallback if conversion fails
        else:
            return ()

    def _flatten_dic(self, d, parent_key='', sep='_'):
        '''
        Flattens a nested dictionary into a single-layer dictionary with joined keys.

        Args:
            d: the dictionary to flatten
            parent_key: used for recursion
            sep: the sperator between strung together keys

        Returns:
            the flattened dictionary
        '''
        items = {}
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else str(k)
            if isinstance(v, dict):
                items.update(self._flatten_dic(v, new_key, sep=sep))
            else:
                items[new_key] = v
        return items

    def _embed_array(self, small, target_shape, fill_value=np.nan, center=False):
        '''
        Embed a smaller array into a larger array of target_shape.

        Parameters:
            small: np.ndarray – The input array (any shape)
            target_shape: tuple – The shape of the output array (must be >= small.shape in all dims)
            fill_value: scalar – What to fill the rest with (default: np.nan)
            center: bool – Whether to center the small array in the target array

        Returns:
            np.ndarray – The larger array with the small array embedded
        '''
        small = np.asarray(small)
        target_shape = tuple(target_shape)

        if any(s > t for s, t in zip(small.shape, target_shape)):
            raise ValueError("Target shape must be >= input shape in all dimensions.")

        result = np.full(target_shape, fill_value, dtype=float)

        if center:
            # Center the small array in each dimension
            slices = tuple(
                slice((t - s) // 2, (t - s) // 2 + s)
                for s, t in zip(small.shape, target_shape)
            )
        else:
            # Top-left placement
            slices = tuple(slice(0, s) for s in small.shape)

        result[slices] = small
        return result

    def _highest_common_shape(self, shape1, shape2):
        '''
        Gets the largest common shape between two arrays.
        Works for any number of dimensions.

        Returns:
            largest shape as a tuple ex: (10,) or (40,40)
        '''
        # Convert to tuples (in case input is a NumPy array's shape)
        shape1 = tuple(shape1)
        shape2 = tuple(shape2)

        # Pad the shorter shape with 1s on the left
        max_len = max(len(shape1), len(shape2))
        shape1_padded = (1,) * (max_len - len(shape1)) + shape1
        shape2_padded = (1,) * (max_len - len(shape2)) + shape2

        # Take max dimension-wise
        result = tuple(max(a, b) for a, b in zip(shape1_padded, shape2_padded))
        return result



if __name__ == '__main__':
    print(explore_package('src.core'))

    a = ('random data', '<f8', (3,))
    b = ('random data', '<f8', (5,))

    matlab_saver = MatlabSaver()
    dif = matlab_saver._compare_tuples(a,b)

    for i in range(len(dif)):
        #loops through all differences
        print(dif[i][0])
        if dif[i][0] == 2:
            #if difference is size gets highest common shape
            shape_1 = dif[i][1]
            shape_2 = dif[i][2]
            best_shape = matlab_saver._highest_common_shape(shape_1, shape_2)
            print(best_shape)
        if dif[i][0] == 1:
            #should never be a difference in data type
            print('difference in data types..defaulting to object')
            best_dtype = 'O'

        new_dtype_tuple = tuple()



    small = np.array([1,2,3])
    large = np.array([1,2,3,4,5])

