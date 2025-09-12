
# CRITICAL: Fix working directory for GUI context BEFORE any imports
# When running from GUI, we need to be in the project root for imports to work
import os
import sys
from pathlib import Path

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

# Now import after path fix
import inspect
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

def get_device_name_mapping():
    """
    Create a mapping from experiment device names to config device names.
    This maps the device names that experiments expect to the actual device names in config.
    
    ⚠️  ARCHITECTURAL LIMITATION: This function violates the principle of keeping hardware
    details out of the code. The ideal approach would be:
    
    1. Experiments define generic device roles (e.g., 'daq', 'microwave', 'positioner')
    2. Config.json defines a 'device_roles' section mapping roles to actual devices:
       {
         "device_roles": {
           "microwave": "sg384",
           "daq": "ni_daq", 
           "positioner": "nanodrive"
         }
       }
    3. The system reads this mapping from config.json instead of hardcoding it here
    
    For now, this provides a fallback mapping for backward compatibility.
    TODO: Refactor to read device role mappings from config.json
    """
    return {
        # Generic device roles that experiments expect -> actual device names in config
        'microwave': 'sg384',      # Generic microwave role -> specific SG384 device
        'awg': 'awg520',          # Generic AWG role -> specific AWG520 device  
        'positioner': 'nanodrive', # Generic positioner role -> specific nanodrive device
        'mux': 'mux_control',     # Generic mux role -> specific mux_control device
        'daq': 'ni_daq',          # Generic DAQ role -> specific NI DAQ device
        'daq2': 'ni_daq',         # Secondary DAQ role -> specific NI DAQ device
        # Direct mappings (device name matches config name)
        'awg520': 'awg520',       
        'nanodrive': 'nanodrive',  
        'adwin': 'adwin',         
        'pulse_blaster': 'pulse_blaster',
    }

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
    # Version check for debugging
    print(f"🔧 Export tool version: 2025-01-09 (with constructor parameter fixes)")
    print(f"🔧 Python path: {sys.executable}")
    print(f"🔧 Working directory: {_os_module.getcwd()}")
    print(f"🔧 Export tool file: {__file__}")
    
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
        print("🔍 No hardcoded device loading - experiments will be created without devices for cross-lab compatibility")
        print("💡 Tip: Devices should be loaded from config.json at GUI startup")
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
                                            device_mapping = get_device_name_mapping()
                                            
                                            for device_name, device_role in attr._DEVICES.items():
                                                # Map experiment device name to config device name
                                                config_device_name = device_mapping.get(device_name, device_name)
                                                
                                                if config_device_name in existing_devices:
                                                    # Use existing real device - wrap in expected structure
                                                    experiment_devices[device_name] = {'instance': existing_devices[config_device_name]}
                                                    print(f"  ✅ Using existing device: {device_name} (mapped from {config_device_name})")
                                                else:
                                                    # No device available - skip this experiment
                                                    print(f"  ❌ Required device {device_name} (config: {config_device_name}) not available")
                                                    failed[name] = f"Required device {device_name} not available"
                                                    continue
                                            
                                            # Try to create experiment with available devices
                                            try:
                                                print(f"🔧 Creating {name} with proper constructor parameters (version 2025-01-09)")
                                                # Create experiment with proper parameters
                                                instance = attr(
                                                    devices=experiment_devices,
                                                    name=name,
                                                    settings=None,  # Use default settings
                                                    log_function=None,
                                                    data_path=None
                                                )
                                                loaded[name] = instance
                                                print(f"✅ Successfully loaded {name} with available devices")
                                            except Exception as e:
                                                failed[name] = f"Instance creation failed: {e}"
                                                print(f"❌ Failed to create {name}: {e}")
                                                continue
                                        else:
                                            # Check if constructor requires 'devices' parameter
                                            sig = inspect.signature(attr.__init__)
                                            if 'devices' in sig.parameters:
                                                print(f"⚠️  {name} constructor requires 'devices' parameter")
                                                print(f"  ⚠️  No devices provided - will attempt to create instance without devices")
                                                
                                                # Try to create instance without devices (hardware-agnostic approach)
                                                try:
                                                    instance = attr(
                                                        devices={},
                                                        name=name,
                                                        settings=None,
                                                        log_function=None,
                                                        data_path=None
                                                    )
                                                    print(f"  ✅ Successfully created {name} without devices")
                                                except Exception as e:
                                                    print(f"  ❌ Failed to create {name} without devices: {e}")
                                                    failed[name] = f"Instance creation failed: {e}"
                                                    continue
                                            else:
                                                # No devices required, create normally
                                                instance = attr(
                                                    name=name,
                                                    settings=None,
                                                    log_function=None,
                                                    data_path=None
                                                )
                                        
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
                print(f"🔍 DEBUG: list_of_python_files type: {type(list_of_python_files)}")
                print(f"🔍 DEBUG: list_of_python_files content: {list_of_python_files}")
                print(f"🔍 DEBUG: list_of_python_files length: {len(list_of_python_files)}")
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
                                        print(f"  ⚠️  No devices provided - will attempt to create instance without devices")
                                        
                                        # Try to create instance without devices (hardware-agnostic approach)
                                        try:
                                            instance = attr()
                                            loaded[attr_name] = instance
                                            print(f"✅ Successfully loaded {attr_name} without devices")
                                        except Exception as e:
                                            print(f"  ❌ Failed to create {attr_name} without devices: {e}")
                                            # Try with empty devices dict as fallback
                                            try:
                                                instance = attr(devices={})
                                                loaded[attr_name] = instance
                                                print(f"✅ Successfully loaded {attr_name} with empty devices dict")
                                            except Exception as e2:
                                                failed[attr_name] = f"Instance creation failed: {e2}"
                                                print(f"❌ Failed to create {attr_name} with empty devices: {e2}")
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
            
            print(f"🔍 DEBUG: list_of_python_files type: {type(list_of_python_files)}")
            print(f"🔍 DEBUG: list_of_python_files content: {list_of_python_files}")
            print(f"🔍 DEBUG: list_of_python_files length: {len(list_of_python_files)}")
            
            for device_name, device_metadata in list_of_python_files.items():
                try:
                    # Extract the actual filepath from metadata
                    if isinstance(device_metadata, dict) and 'filepath' in device_metadata:
                        python_file = device_metadata['filepath']
                        print(f"🔍 Processing device: {device_name}")
                        print(f"🔍 Using filepath: {python_file}")
                    else:
                        # Fallback to treating it as a direct file path
                        python_file = device_name
                        print(f"🔍 Processing device file directly: {python_file}")
                    
                    # Extract filename without extension
                    filename = _os_module.path.basename(python_file)
                    name = _os_module.path.splitext(filename)[0]  # Remove .py extension
                    
                    # Add src to path for import
                    sys.path.insert(0, 'src')
                    
                    # Try to import the module
                    # Convert file path to module path
                    if 'src/' in python_file.replace('\\', '/'):
                        # Extract the part after 'src/' and before '.py'
                        forward_path = python_file.replace('\\', '/')
                        src_index = forward_path.find('src/')
                        module_path = forward_path[src_index + 4:-3].replace('/', '.')
                    else:
                        module_path = python_file.replace('.py', '').replace('/', '.').replace('\\', '.')
                    
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