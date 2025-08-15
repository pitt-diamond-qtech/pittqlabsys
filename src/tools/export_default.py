
import inspect,os,sys
from src.core import Device,Experiment,ExperimentIterator
from importlib import import_module
from src.core.helper_functions import module_name_from_path
import glob
import json



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

            classes_dict.update({name: {'class': name, 'filepath': inspect.getfile(obj), 'info': inspect.getdoc(obj), 'devices': {}, 'experiments': {}} for name, obj in
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

def detect_mock_devices():
    """
    Detect if any devices are using mock implementations.
    Returns a list of mock device names and a warning message.
    """
    mock_devices = []
    warning_message = ""
    
    try:
        import sys
        import os
        
        # Check for common testing indicators
        test_indicators = [
            'PYTEST_CURRENT_TEST' in os.environ,
            'RUN_HARDWARE_TESTS' in os.environ,
            any('test' in arg.lower() for arg in sys.argv),
            any('mock' in arg.lower() for arg in sys.argv)
        ]
        
        # Check for mock devices in loaded modules
        for module_name, module in sys.modules.items():
            if module_name.startswith('src.Controller') and module is not None:
                for attr_name in dir(module):
                    attr = getattr(module, attr_name, None)
                    if (inspect.isclass(attr) and 
                        issubclass(attr, Device) and 
                        attr != Device):
                        
                        # Check if it's a mock class
                        if (hasattr(attr, '__module__') and 
                            ('mock' in attr.__module__.lower() or 
                             'test' in attr.__module__.lower())):
                            mock_devices.append(attr_name)
                        
                        # Check if it's a patched/mocked class
                        elif hasattr(attr, '_mock_name') or hasattr(attr, '_mock_return_value'):
                            mock_devices.append(attr_name)
        
        # Check for environment-based mock indicators
        if any(test_indicators):
            mock_devices.append("Environment-based testing detected")
        
        if mock_devices:
            warning_message = (
                "⚠️  WARNING: Mock devices detected during conversion!\n\n"
                f"Mock devices found: {', '.join(mock_devices)}\n\n"
                "This conversion may not reflect real hardware capabilities.\n"
                "Check device connections and try again for accurate results."
            )
        else:
            warning_message = "✅ All devices appear to be real hardware implementations."
            
    except Exception as e:
        warning_message = f"⚠️  Warning: Could not verify device status: {e}"
    
    return mock_devices, warning_message


def python_file_to_aqs(list_of_python_files, target_folder, class_type, raise_errors = False):
    # Check for mock devices and display warning
    mock_devices, warning_message = detect_mock_devices()
    print("\n" + "="*80)
    print(warning_message)
    print("="*80 + "\n")
    
    loaded = {}
    failed = {}
    
    try:
        if class_type == 'Experiment':
            loaded, failed, loaded_devices = Experiment.load_and_append(list_of_python_files, raise_errors=False)
        elif class_type == 'Device':
            loaded, failed = Device.load_and_append(list_of_python_files, raise_errors=False)
    except Exception as e:
        print(f"Error during {class_type} loading: {e}")
        # If loading fails entirely, return empty results
        return {}, list_of_python_files

    print('loaded', loaded)
    print('failed', failed)

    # Only save successfully loaded items
    for name, value in loaded.items():
        try:
            filename = os.path.join(target_folder, '{:s}.json'.format(name))  # Use .json extension
            value.save_aqs(filename)
            print(f"Successfully saved {name} to {filename}")
        except Exception as e:
            print(f"Error saving {name}: {e}")
            failed[name] = f"Save error: {e}"
            # Remove from loaded since we couldn't save it
            del loaded[name]
    
    return loaded, failed