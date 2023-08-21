
import inspect,os,sys
from src.core import Device,Experiment,ExperimentIterator
from importlib import import_module
from src.core.helper_functions import module_name_from_path
import glob

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
    return find_exportable_in_python_files(folder_name, 'Device', verbose)

def python_file_to_aqs(list_of_python_files, target_folder, class_type, raise_errors = False):
    loaded = {}
    failed = {}
    if class_type == 'Experiment':
        loaded, failed, loaded_devices = Experiment.load_and_append(list_of_python_files, raise_errors=raise_errors)
    elif class_type == 'Device':
        loaded, failed = Device.load_and_append(list_of_python_files, raise_errors=raise_errors)

    print('loaded', loaded)

    for name, value in loaded.items():
        filename = os.path.join(target_folder, '{:s}.aqs'.format(name))
        value.save_aqs(filename)
    return loaded,failed