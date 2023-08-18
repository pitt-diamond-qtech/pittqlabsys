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
from src.core import Device, Experiment, ExperimentIterator
from importlib import import_module
import glob
import pkgutil

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




def find_exportable_in_python_files(folder_name, class_type, verbose = True):
    """
    load all the devices or experiment objects that are located in folder_name and
    return a dictionary with the experiment class name and path_to_python_file
    Args:
        folder_name (string): folder in which to search for class objects / or name of module
        class_type (string or class): class type for which to look for

    Returns:
        a dictionary with the class name and path_to_python_file:
        {
        'class': class_of_devices,
        'filepath': path_to_python_file
        }
    """

    # if the module name was passed instead of a filename, figure out the path to the module
    if not os.path.isdir(folder_name):
        try:
            folder_name = os.path.dirname(inspect.getfile(import_module(folder_name)))
        except ImportError:
            raise ImportError('could not find module ' + folder_name)

    subdirs = [os.path.join(folder_name, x) for x in os.listdir(folder_name) if
               os.path.isdir(os.path.join(folder_name, x)) and not x.startswith('.')]

    classes_dict = {}
    # if there are subdirs in the folder recursively check all the subfolders for experiments
    for subdir in subdirs:
        classes_dict.update(find_exportable_in_python_files(subdir, class_type))

    if class_type.lower() == 'device':
        class_type = Device
    elif class_type.lower() == 'experiment':
        class_type = Experiment

    for python_file in [f for f in glob.glob(os.path.join(folder_name, "*.py"))if '__init__' not in f and 'setup' not in f]:
        module, path = module_name_from_path(python_file)

        #appends path to this module to the python path if it is not present so it can be used
        if path not in sys.path:
            sys.path.append(path)

        try:
            module = import_module(module)

            classes_dict.update({name: {'class': name, 'filepath': inspect.getfile(obj), 'info': inspect.getdoc(obj)} for name, obj in
                               inspect.getmembers(module) if inspect.isclass(obj) and issubclass(obj, class_type)
                             and not obj in (Device, Experiment, ExperimentIterator)})

        except (ImportError, ModuleNotFoundError) as e:
            print(e)
            if verbose:
                print('Could not import module', module)

    return classes_dict

def find_experiments_in_python_files(folder_name, verbose = False):
    return find_exportable_in_python_files(folder_name, 'Experiment', verbose)

def find_devices_in_python_files(folder_name, verbose = False):
    return find_exportable_in_python_files(folder_name, 'device', verbose)

def python_file_to_aqs(list_of_python_files, target_folder, class_type, raise_errors = False):
    if class_type == 'Experiment':
        loaded, failed, loaded_devices = Experiment.load_and_append(list_of_python_files, raise_errors=raise_errors)
    elif class_type == 'device':
        loaded, failed = Device.load_and_append(list_of_python_files, raise_errors=raise_errors)

    print('loaded', loaded)

    for name, value in loaded.items():
        filename = os.path.join(target_folder, '{:s}.aqs'.format(name))
        value.save_aqs(filename)


if __name__ == '__main__':
    print(explore_package('src.core'))
