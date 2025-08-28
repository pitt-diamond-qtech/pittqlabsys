
import inspect
import os
import sys
from pathlib import Path

# CRITICAL: Fix working directory for GUI context
# When running from GUI, we need to be in the project root for imports to work
current_dir = Path.cwd()
project_root = Path(__file__).parent.parent.parent

# If we're not in the project root, change to it
if current_dir != project_root:
    print(f"🔧 Changing working directory from {current_dir} to {project_root}")
    os.chdir(project_root)
    print(f"✅ Working directory changed to: {os.getcwd()}")

# Ensure project root is in Python path for imports
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
    print(f"🔧 Added project root to Python path: {project_root}")

# SAFEGUARD: Create backup reference to os module to prevent shadowing
_os_module = os

from src.core import Device,Experiment,ExperimentIterator
from importlib import import_module
from src.core.helper_functions import module_name_from_path
import glob
import json
import numpy as np



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
    if not _os_module.path.isdir(folder_name):
        try:
            folder_name = _os_module.path.dirname(inspect.getfile(import_module(folder_name)))
        except ImportError:
            raise ImportError('could not find module ' + folder_name)

    subdirs = [_os_module.path.join(folder_name, x) for x in _os_module.listdir(folder_name) if
               _os_module.path.isdir(_os_module.path.join(folder_name, x)) and not x.startswith('.')]

    classes_dict = {}
    # if there are subdirs in the folder recursively check all the subfolders for experiments
    for subdir in subdirs:
        classes_dict.update(find_exportable_in_python_files(subdir, class_type))

    if class_type.lower() == 'device':
        class_type = Device
    elif class_type.lower() == 'experiment':
        class_type = Experiment

    for python_file in [file_path for file_path in glob.glob(_os_module.path.join(folder_name, "*.py"))if '__init__' not in file_path and 'setup' not in file_path]:
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
        import json
        from pathlib import Path
        
        # FIRST PRIORITY: Check environment-specific config files
        config_dir = Path(__file__).parent.parent
        
        # Look for environment-specific config files first
        env_config_files = [
            config_dir / "config.lab.json",      # Lab PC specific
            config_dir / "config.dev.json",      # Development specific
            config_dir / "config.json"           # Fallback to base config
        ]
        
        config_loaded = False
        for config_path in env_config_files:
            if config_path.exists():
                try:
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                    
                    env_config = config.get('environment', {})
                    config_loaded = True
                    
                    # If explicitly set to development/mock, respect that setting
                    if env_config.get('is_development', False):
                        mock_devices.append(f"Development environment ({config_path.name})")
                        return mock_devices, f"⚠️  Development environment detected via {config_path.name}"
                        
                    if env_config.get('is_mock', False):
                        mock_devices.append(f"Mock environment ({config_path.name})")
                        return mock_devices, f"⚠️  Mock environment detected via {config_path.name}"
                        
                    if env_config.get('force_mock_devices', False):
                        mock_devices.append(f"Mock devices forced ({config_path.name})")
                        return mock_devices, f"⚠️  Mock devices forced via {config_path.name}"
                        
                    # If hardware detection is disabled, assume mock
                    if not env_config.get('hardware_detection_enabled', True):
                        mock_devices.append(f"Hardware detection disabled ({config_path.name})")
                        return mock_devices, f"⚠️  Hardware detection disabled via {config_path.name}"
                    
                    # If we get here, config was loaded but no special flags set
                    # This means it's a production/lab environment
                    break
                        
                except Exception as e:
                    print(f"Warning: Could not read {config_path.name}: {e}")
                    continue
        
        if not config_loaded:
            print("Warning: No valid config files found, using fallback detection methods")
        
        # SECOND PRIORITY: Check for testing environment variables
        test_indicators = [
                    'PYTEST_CURRENT_TEST' in _os_module.environ,
        'RUN_HARDWARE_TESTS' in _os_module.environ,
            # Only check for actual pytest commands, not script execution
            any('pytest' in arg.lower() for arg in sys.argv),
            any('mock' in arg.lower() for arg in sys.argv)
        ]
        
        if any(test_indicators):
            mock_devices.append("Testing environment detected")
        
        # THIRD PRIORITY: Check for actual mock instances in loaded modules
        try:
            from src.core import Device
            
            for module_name, module in sys.modules.items():
                if module_name.startswith('src.Controller') and module is not None:
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name, None)
                        if (inspect.isclass(attr) and 
                            issubclass(attr, Device) and 
                            attr != Device):
                            
                            # Check if it's a mock class
                            if (hasattr(attr, '_mock_name') or 
                                hasattr(attr, '_mock_return_value')):
                                mock_devices.append(f"{attr_name} (mock class)")
                                
        except ImportError:
            pass
        
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


def python_file_to_aqs(list_of_python_files, target_folder, class_type, raise_errors = False, existing_devices=None):
    """
    Convert Python files to AQS format, integrating with existing device loading system.
    
    Args:
        list_of_python_files: List of Python files or dict of experiment metadata
        target_folder: Target folder for AQS files
        class_type: 'Experiment' or 'Device'
        raise_errors: Whether to raise errors
        existing_devices: Dictionary of already loaded devices from GUI (optional)
    """
    # Check for mock devices and display warning
    mock_devices, warning_message = detect_mock_devices()
    print("\n" + "="*80)
    print(warning_message)
    print("="*80 + "\n")
    
    # If we have existing devices, use them instead of creating new mocks
    if existing_devices:
        print(f"🔧 Using {len(existing_devices)} existing devices from GUI:")
        for device_name, device in existing_devices.items():
            device_type = type(device).__name__
            print(f"  ✅ {device_name}: {device_type}")
    else:
        print("⚠️  No existing devices provided from GUI")
        print("🔍 Attempting to load real hardware devices...")
        
        # Try to load real devices
        try:
            from src.Controller.sg384 import SG384Generator
            from src.Controller.adwin_gold import AdwinGoldDevice
            from src.Controller.nanodrive import MCLNanoDrive
            
            # Attempt to create real device instances
            real_devices = {}
            device_attempts = [
                ('sg384', SG384Generator, {}),
                ('adwin', AdwinGoldDevice, {}),
                ('nanodrive', MCLNanoDrive, {})
            ]
            
            for device_name, device_class, device_settings in device_attempts:
                try:
                    print(f"  🔧 Attempting to connect to {device_name}...")
                    device_instance = device_class(settings=device_settings)
                    real_devices[device_name] = device_instance
                    print(f"  ✅ Successfully connected to {device_name}")
                except Exception as e:
                    print(f"  ❌ Failed to connect to {device_name}: {e}")
                    real_devices[device_name] = None
            
            if any(real_devices.values()):
                print(f"🔧 Successfully loaded {sum(1 for d in real_devices.values() if d is not None)} real devices")
                existing_devices = {k: v for k, v in real_devices.items() if v is not None}
            else:
                print("⚠️  No real devices could be loaded - will create mock devices as needed")
                existing_devices = {}
                
        except Exception as e:
            print(f"⚠️  Error during device loading: {e}")
            print("⚠️  Will create mock devices as needed")
            existing_devices = {}
    
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
                            normalized_path = _os_module.path.normpath(filepath)
                            
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
                                            
                                            # Build device dictionary using existing devices when possible
                                            experiment_devices = {}
                                            missing_devices = []
                                            
                                            for device_name, device_class in attr._DEVICES.items():
                                                if device_name in existing_devices:
                                                    # Use existing real device
                                                    experiment_devices[device_name] = existing_devices[device_name]
                                                    print(f"  ✅ Using existing device: {device_name}")
                                                else:
                                                    # Create mock device for missing one
                                                    missing_devices.append(device_name)
                                                    try:
                                                        # Create a simple mock device
                                                        mock_device = type(f'Mock{device_name}', (), {
                                                            '__init__': lambda self: None,
                                                            'name': device_name,
                                                            'settings': {},
                                                            'info': f'Mock {device_name} for conversion'
                                                        })()
                                                        # Wrap in the expected {'instance': device} format
                                                        experiment_devices[device_name] = {'instance': mock_device}
                                                        print(f"  ⚠️  Created mock device: {device_name} (not available)")
                                                    except Exception as e:
                                                        print(f"  ❌ Failed to create mock {device_name}: {e}")
                                                        failed[name] = f"Mock device creation failed: {e}"
                                                        continue
                                            
                                            if missing_devices:
                                                print(f"  ⚠️  Missing devices (using mocks): {missing_devices}")
                                            
                                            # Try to create experiment with devices
                                            instance = attr(devices=experiment_devices)
                                        else:
                                            # Check if constructor requires 'devices' parameter
                                            sig = inspect.signature(attr.__init__)
                                            if 'devices' in sig.parameters:
                                                print(f"⚠️  {name} constructor requires 'devices' parameter")
                                                
                                                # Build device dictionary using existing devices when possible
                                                experiment_devices = {}
                                                missing_devices = []
                                                
                                                # Common device names that experiments might need
                                                common_devices = ['nanodrive', 'adwin', 'daq', 'microwave', 'awg', 'sg384']
                                                for device_name in common_devices:
                                                    if device_name in existing_devices:
                                                        # Use existing real device
                                                        experiment_devices[device_name] = existing_devices[device_name]
                                                        print(f"  ✅ Using existing device: {device_name}")
                                                    else:
                                                        # Create mock device for missing one
                                                        missing_devices.append(device_name)
                                                        try:
                                                            # Create simple mock device instance with common methods
                                                            mock_device = type(f'Mock{device_name}', (), {
                                                                '__init__': lambda self: None,
                                                                'name': device_name,
                                                                'settings': {},
                                                                'info': f'Mock {device_name} for conversion',
                                                                'is_connected': True,  # Add common device attributes
                                                                'connect': lambda self: None,
                                                                'disconnect': lambda self: None,
                                                                # Common methods that experiments might call
                                                                'update': lambda self, settings: None,
                                                                'read_probes': lambda self, probe_name: 0.0,
                                                                'stop_process': lambda self, process_id: None,
                                                                'clear_process': lambda self, process_id: None,
                                                                'reboot_adwin': lambda self: None,
                                                                'clock_functions': lambda self, clock_type, reset=False: None,
                                                                'setup': lambda self, settings, axis: None,
                                                                'waveform_acquisition': lambda self, axis: 0.0,
                                                                'empty_waveform': np.zeros(100)  # Default empty waveform
                                                            })()
                                                            # Wrap in the expected {'instance': device} format
                                                            experiment_devices[device_name] = {'instance': mock_device}
                                                            print(f"  ⚠️  Created mock device: {device_name} (not available)")
                                                        except Exception as e:
                                                            print(f"  ❌ Failed to create mock {device_name}: {e}")
                                                            continue
                                                
                                                if missing_devices:
                                                    print(f"  ⚠️  Missing devices (using mocks): {missing_devices}")
                                                
                                                # Try to create experiment with devices
                                                instance = attr(devices=experiment_devices)
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
                        filename = _os_module.path.basename(python_file)
                        name = _os_module.path.splitext(filename)[0]  # Remove .py extension
                        
                        # Add src to path for import
                        sys.path.insert(0, 'src')
                        
                        # Try to import the module
                        # Handle both absolute and relative paths, normalize for cross-platform
                        # Normalize path separators
                        normalized_path = _os_module.path.normpath(python_file)
                        
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
                        
                        print(f"🔍 Processing experiment file: {python_file}")
                        print(f"🔍 Generated module path: {module_path}")
                        print(f"🔍 Attempting to import module...")
                        try:
                            module = __import__(module_path, fromlist=['*'])
                            print(f"✅ Successfully imported module: {module_path}")
                        except ImportError as import_error:
                            print(f"❌ Import failed for {module_path}: {import_error}")
                            print(f"🔍 Current sys.path: {sys.path[:3]}...")  # Show first 3 paths
                            raise import_error
                        
                        # Look for experiment classes
                        for attr_name in dir(module):
                            attr = getattr(module, attr_name, None)
                            if (inspect.isclass(attr) and 
                                issubclass(attr, Experiment) and 
                                attr != Experiment):
                                
                                # Create instance and save
                                try:
                                    # Check if this experiment requires specific devices
                                    if hasattr(attr, '_DEVICES') and attr._DEVICES:
                                        print(f"⚠️  {attr_name} requires devices: {list(attr._DEVICES.keys())}")
                                        print(f"  ⚠️  Created mock device: {list(attr._DEVICES.keys())[0]} (not available)")
                                        # Create mock devices for required devices
                                        mock_devices = {}
                                        for device_name in attr._DEVICES.keys():
                                            mock_devices[device_name] = f"Mock{device_name}"
                                        print(f"  ⚠️  Missing devices (using mocks): {list(mock_devices.keys())}")
                                        
                                        # Try to create instance with mock devices
                                        try:
                                            instance = attr(devices=mock_devices)
                                            loaded[attr_name] = instance
                                            print(f"✅ Successfully loaded {attr_name} with mock devices")
                                        except Exception as e2:
                                            failed[attr_name] = f"Instance creation failed with mock devices: {e2}"
                                            print(f"❌ Failed to create {attr_name} with mock devices: {e2}")
                                    else:
                                        # No devices required, create instance normally
                                        instance = attr()
                                        loaded[attr_name] = instance
                                        print(f"✅ Successfully loaded {attr_name}")
                                except Exception as e:
                                    failed[attr_name] = f"Instance creation failed: {e}"
                                    print(f"❌ Failed to create {attr_name}: {e}")
                        
                    except Exception as e:
                        failed[_os_module.path.basename(python_file)] = f"File processing failed: {e}"
                        print(f"❌ Failed to process {python_file}: {e}")
                    
            loaded_devices = {}  # No devices loaded in this approach
            
        elif class_type == 'Device':
            # Similar approach for devices
            loaded = {}
            failed = {}
            
            for python_file in list_of_python_files:
                try:
                    # Extract filename without extension
                    filename = _os_module.path.basename(python_file)
                    name = _os_module.path.splitext(filename)[0]  # Remove .py extension
                    
                    # Add src to path for import
                    sys.path.insert(0, 'src')
                    
                    # Try to import the module
                    module_path = python_file.replace('src/', '').replace('.py', '').replace('/', '.')
                    print(f"🔍 Processing device file: {python_file}")
                    print(f"🔍 Generated module path: {module_path}")
                    print(f"🔍 Attempting to import module...")
                    try:
                        module = __import__(module_path, fromlist=['*'])
                        print(f"✅ Successfully imported module: {module_path}")
                    except ImportError as import_error:
                        print(f"❌ Import failed for {module_path}: {import_error}")
                        print(f"🔍 Current sys.path: {sys.path[:3]}...")  # Show first 3 paths
                        raise import_error
                    
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
                                print(f"❌ Failed to create {attr_name}")
                    
                except Exception as e:
                    failed[_os_module.path.basename(python_file)] = f"File processing failed: {e}"
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
            filename = _os_module.path.join(target_folder, '{:s}.json'.format(name))  # Use .json extension
            value.save_aqs(filename)
            print(f"Successfully saved {name} to {filename}")
        except Exception as e:
            print(f"Error saving {name}: {e}")
            failed[name] = f"Save error: {e}"
            # Remove from loaded since we couldn't save it
            if name in loaded:
                del loaded[name]
    
    return loaded, failed