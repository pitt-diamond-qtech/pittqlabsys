
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
        
        # Check for environment-based mock indicators FIRST (most reliable)
        if any(test_indicators):
            mock_devices.append("Environment-based testing detected")
        
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
        
        # ADDITIONAL CHECKS: Look for actual mock instances in sys.modules
        # Create a copy to avoid iteration issues
        modules_copy = dict(sys.modules)
        for module_name, module in modules_copy.items():
            if module is not None:
                try:
                    # Get a copy of dir() to avoid iteration issues
                    attr_names = list(dir(module))
                    for attr_name in attr_names:
                        try:
                            attr = getattr(module, attr_name, None)
                            # Check if it's a mock instance (not just class)
                            # Filter out PyQt proxy objects and other false positives
                            if (hasattr(attr, '_mock_name') or 
                                hasattr(attr, '_mock_return_value') or
                                str(type(attr)).find('Mock') != -1):
                                
                                # Skip PyQt proxy objects and other false positives
                                skip_objects = [
                                    'QtCore', 'QtGui', 'QtWidgets', 'QtNetwork', 'QtSql',
                                    'ProxyBase', 'LiteralProxyClass', 'ProxyClass', 'ProxyNamespace',
                                    'QObject', 'QWidget', 'QApplication'
                                ]
                                
                                if not any(skip_name in str(attr) or skip_name in str(type(attr)) 
                                          for skip_name in skip_objects):
                                    if attr_name not in mock_devices:
                                        mock_devices.append(f"{attr_name} (mock instance)")
                        except Exception:
                            # Skip problematic attributes
                            continue
                except Exception:
                    # Skip problematic modules
                    continue
        
        # DEVELOPMENT MACHINE DETECTION: Check if we're likely on a dev machine
        dev_indicators = [
            'CursorProjects' in os.getcwd(),  # Cursor IDE
            'PyCharmProjects' in os.getcwd(),  # PyCharm IDE
            'VSCode' in os.getcwd(),  # VS Code
            'venv' in os.getcwd(),  # Virtual environment in project
            os.path.exists('tests/'),  # Test directory exists
            os.path.exists('src/'),   # Source directory exists
        ]
        
        if any(dev_indicators) and not mock_devices:
            mock_devices.append("Development environment detected (likely using mock devices)")
        
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
            # Handle both file paths and experiment metadata
            loaded = {}
            failed = {}
            
            # Check if we received a dict of experiment metadata or list of file paths
            if isinstance(list_of_python_files, dict):
                # We have experiment metadata from ExportDialog
                print(f"Processing {len(list_of_python_files)} experiments from metadata")
                for name, metadata in list_of_python_files.items():
                    try:
                        if 'filepath' in metadata:
                            # Extract file path from metadata
                            filepath = metadata['filepath']
                            print(f"Processing {name} from file: {filepath}")
                            
                            # Add src to path for import
                            sys.path.insert(0, 'src')
                            
                            # Try to import the module
                            # Handle both absolute and relative paths, normalize for cross-platform
                            import os
                            # Normalize path separators
                            normalized_path = os.path.normpath(filepath)
                            
                            # Convert to forward slashes for consistent processing
                            forward_path = normalized_path.replace('\\', '/')
                            
                            if 'src/' in forward_path:
                                # Extract the part after 'src/' and before '.py'
                                src_index = forward_path.find('src/')
                                module_path = forward_path[src_index + 4:-3].replace('/', '.')
                            elif forward_path.startswith('src/'):
                                module_path = forward_path[4:-3].replace('/', '.')
                            else:
                                module_path = forward_path.replace('.py', '').replace('/', '.')
                            
                            print(f"Importing module: {module_path}")
                            module = __import__(module_path, fromlist=['*'])
                            
                            # Look for the specific experiment class
                            if hasattr(module, name):
                                attr = getattr(module, name)
                                if (inspect.isclass(attr) and 
                                    issubclass(attr, Experiment) and 
                                    attr != Experiment):
                                    
                                    # Create instance and save
                                    try:
                                        # Check if experiment requires devices
                                        if hasattr(attr, '_DEVICES') and attr._DEVICES:
                                            print(f"⚠️  {name} requires devices: {attr._DEVICES}")
                                            # Create mock device substitutes
                                            mock_devices = {}
                                            for device_name, device_class in attr._DEVICES.items():
                                                try:
                                                    # Create a simple mock device
                                                    mock_device = type(f'Mock{device_name}', (), {
                                                        '__init__': lambda self: None,
                                                        'name': device_name,
                                                        'settings': {},
                                                        'info': f'Mock {device_name} for conversion'
                                                    })()
                                                    mock_devices[device_name] = mock_device
                                                    print(f"  ✅ Created mock device: {device_name}")
                                                except Exception as e:
                                                    print(f"  ❌ Failed to create mock {device_name}: {e}")
                                            
                                            # Try to create experiment with mock devices
                                            instance = attr(devices=mock_devices)
                                        else:
                                            # Check if constructor requires 'devices' parameter
                                            sig = inspect.signature(attr.__init__)
                                            if 'devices' in sig.parameters:
                                                print(f"⚠️  {name} constructor requires 'devices' parameter")
                                                # Create basic mock devices based on common requirements
                                                mock_devices = {}
                                                # Common device names that experiments might need
                                                common_devices = ['nanodrive', 'adwin', 'daq', 'microwave', 'awg', 'sg384']
                                                for device_name in common_devices:
                                                    try:
                                                        # Create mock device with expected structure
                                                        mock_instance = type(f'Mock{device_name}', (), {
                                                            '__init__': lambda self: None,
                                                            'name': device_name,
                                                            'settings': {},
                                                            'info': f'Mock {device_name} for conversion'
                                                        })()
                                                        mock_device = {
                                                            'instance': mock_instance,
                                                            'name': device_name,
                                                            'info': f'Mock {device_name} for conversion',
                                                            'settings': {}  # Add settings at top level
                                                        }
                                                        mock_devices[device_name] = mock_device
                                                        print(f"  ✅ Created mock device: {device_name}")
                                                    except Exception as e:
                                                        print(f"  ❌ Failed to create mock {device_name}: {e}")
                                                
                                                # Try to create experiment with mock devices
                                                instance = attr(devices=mock_devices)
                                            else:
                                                # No devices required, create normally
                                                instance = attr()
                                        
                                        loaded[name] = instance
                                        print(f"✅ Successfully loaded {name}")
                                    except Exception as e:
                                        failed[name] = f"Instance creation failed: {e}"
                                        print(f"❌ Failed to create {name}: {e}")
                                else:
                                    failed[name] = f"Not a valid experiment class: {type(attr)}"
                                    print(f"❌ {name} is not a valid experiment class")
                            else:
                                failed[name] = f"Class {name} not found in module"
                                print(f"❌ Class {name} not found in module")
                        else:
                            failed[name] = "No filepath in metadata"
                            print(f"❌ No filepath for {name}")
                            
                    except Exception as e:
                        failed[name] = f"File processing failed: {e}"
                        print(f"❌ Failed to process {name}: {e}")
                        
            else:
                # We have a list of file paths (direct usage)
                print(f"Processing {len(list_of_python_files)} files directly")
                for python_file in list_of_python_files:
                    try:
                        # Extract filename without extension
                        filename = os.path.basename(python_file)
                        name = os.path.splitext(filename)[0]
                        
                        # Add src to path for import
                        sys.path.insert(0, 'src')
                        
                        # Try to import the module
                        # Handle both absolute and relative paths, normalize for cross-platform
                        # Normalize path separators
                        normalized_path = os.path.normpath(python_file)
                        
                        # Convert to forward slashes for consistent processing
                        forward_path = normalized_path.replace('\\', '/')
                        
                        if 'src/' in forward_path:
                            # Extract the part after 'src/' and before '.py'
                            src_index = forward_path.find('src/')
                            module_path = forward_path[src_index + 4:-3].replace('/', '.')
                        elif forward_path.startswith('src/'):
                            module_path = forward_path[4:-3].replace('/', '.')
                        else:
                            module_path = forward_path.replace('.py', '').replace('/', '.')
                        
                        print(f"Importing module: {module_path}")
                        module = __import__(module_path, fromlist=['*'])
                        
                        # Look for experiment classes
                        for attr_name in dir(module):
                            attr = getattr(module, attr_name, None)
                            if (inspect.isclass(attr) and 
                                issubclass(attr, Experiment) and 
                                attr != Experiment):
                                
                                # Create instance and save
                                try:
                                    instance = attr()
                                    loaded[attr_name] = instance
                                    print(f"✅ Successfully loaded {attr_name}")
                                except Exception as e:
                                    failed[attr_name] = f"Instance creation failed: {e}"
                                    print(f"❌ Failed to create {attr_name}: {e}")
                        
                    except Exception as e:
                        failed[os.path.basename(python_file)] = f"File processing failed: {e}"
                        print(f"❌ Failed to process {python_file}: {e}")
                    
            loaded_devices = {}  # No devices loaded in this approach
            
        elif class_type == 'Device':
            # Similar approach for devices
            loaded = {}
            failed = {}
            
            for python_file in list_of_python_files:
                try:
                    # Extract filename without extension
                    filename = os.path.basename(python_file)
                    name = os.path.splitext(filename)[0]
                    
                    # Add src to path for import
                    sys.path.insert(0, 'src')
                    
                    # Try to import the module
                    module_path = python_file.replace('src/', '').replace('.py', '').replace('/', '.')
                    module = __import__(module_path, fromlist=['*'])
                    
                    # Look for device classes
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name, None)
                        if (inspect.isclass(attr) and 
                            issubclass(attr, Device) and 
                            attr != Device):
                            
                            # Create instance and save
                            try:
                                instance = attr()
                                loaded[attr_name] = instance
                                print(f"✅ Successfully loaded {attr_name}")
                            except Exception as e:
                                failed[attr_name] = f"Instance creation failed: {e}"
                                print(f"❌ Failed to create {attr_name}: {e}")
                    
                except Exception as e:
                    failed[os.path.basename(python_file)] = f"File processing failed: {e}"
                    print(f"❌ Failed to process {python_file}: {e}")
                    
    except Exception as e:
        print(f"Error during {class_type} loading: {e}")
        import traceback
        traceback.print_exc()
        # If loading fails entirely, return empty results
        return {}, list_of_python_files

    print('loaded', loaded)
    print('failed', failed)

    # Only save successfully loaded items
    # Create a copy to avoid iteration issues
    loaded_copy = dict(loaded)
    for name, value in loaded_copy.items():
        try:
            filename = os.path.join(target_folder, '{:s}.json'.format(name))  # Use .json extension
            value.save_aqs(filename)
            print(f"Successfully saved {name} to {filename}")
        except Exception as e:
            print(f"Error saving {name}: {e}")
            failed[name] = f"Save error: {e}"
            # Remove from loaded since we couldn't save it
            if name in loaded:
                del loaded[name]
    
    return loaded, failed