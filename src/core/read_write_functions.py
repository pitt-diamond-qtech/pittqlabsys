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


import yaml, json
import os, inspect
from importlib import import_module
import platform
from typing import Optional, Dict, Any
from src.config_store import load_config, save_config, merge_config
from pathlib import Path

def import_sub_modules(module_type):
    """
    imports all the module_type from additional modules that contain module_type
    This name of those modules is in the config file that is located in the main directory
    module_type: str that specifies the type of module to be loaded (experiments / devices)

    :return: module_list: a list with modules that contain module_type
    """

    assert module_type in ('experiments', 'devices')

    path_to_config = '/'.join(
        os.path.normpath(os.path.dirname(inspect.getfile(import_sub_modules))).split('\\')[0:-2]) + '/config.txt'
    module_list = get_config_value('EXPERIMENT_MODULES', path_to_config).split(';')
    module_list = [import_module(module_name + module_type) for module_name in module_list]

    return module_list


def get_config_value(name, path_to_file='config.txt'):
    """
    gets the value for "name" from "path_to_file" config file
    Args:
        name: name of varibale in config file
        path_to_file: path to config file

    Returns: path to dll if name exists in the file; otherwise, returns None

    """

    # if the function is called from gui then the file has to be located with respect to the gui folder
    if not os.path.isfile(path_to_file):
        path_to_file = os.path.join('../Controller/', path_to_file)

    path_to_file = os.path.abspath(path_to_file)

    if not os.path.isfile(path_to_file):
        print(('path_to_file', path_to_file))
        # raise IOError('{:s}: config file is not valid'.format(path_to_file))
        return None

    f = open(path_to_file, 'r')
    string_of_file_contents = f.read()

    if name[-1] != ':':
        name += ':'

    if name not in string_of_file_contents:
        return None
    else:
        config_value = [line.split(name)[1] for line in string_of_file_contents.split('\n')
                        if len(line.split(name)) > 1][0].strip()
        return config_value


def convert_cross_platform_paths(data_dict):
    """
    Convert Windows-style paths to current platform paths in loaded data.
    This handles cases where .aqs files created on Windows are loaded on macOS/Linux.
    
    Args:
        data_dict: Dictionary loaded from .aqs file
        
    Returns:
        Dictionary with converted paths
    """
    import platform
    
    def convert_path(path_str):
        """Convert a single path string to current platform format"""
        if not isinstance(path_str, str):
            return path_str
            
        # Check if this is a Windows path
        if path_str.startswith(('C:', 'D:', 'E:', 'F:', 'G:', 'H:', 'I:', 'J:', 'K:', 'L:', 'M:', 'N:', 'O:', 'P:', 'Q:', 'R:', 'S:', 'T:', 'U:', 'V:', 'W:', 'X:', 'Y:', 'Z:')):
            # Convert Windows path to Unix-style
            # Remove drive letter and convert backslashes to forward slashes
            path_str = path_str[2:].replace('\\', '/')
            
            # Map common Windows paths to Unix equivalents
            if path_str.startswith('/Users/'):
                # Already Unix-style, just clean up
                return path_str
            elif path_str.startswith('/Program Files/'):
                # Windows system path - suggest alternative
                return f"~/Experiments/AQuISS_default_save_location{path_str}"
            elif path_str.startswith('/Documents/'):
                # Windows user documents - suggest alternative
                return f"~/Experiments/AQuISS_default_save_location{path_str}"
            else:
                # Generic Windows path - suggest alternative
                return f"~/Experiments/AQuISS_default_save_location{path_str}"
        
        return path_str
    
    def convert_dict_paths(obj):
        """Recursively convert paths in nested dictionaries and lists"""
        if isinstance(obj, dict):
            converted = {}
            for key, value in obj.items():
                if key in ['data_folder', 'probes_folder', 'device_folder', 'experiments_folder', 'probes_log_folder', 'workspace_config_dir']:
                    converted[key] = convert_path(value)
                else:
                    converted[key] = convert_dict_paths(value)
            return converted
        elif isinstance(obj, list):
            return [convert_dict_paths(item) for item in obj]
        else:
            return obj
    
    return convert_dict_paths(data_dict)

def load_aqs_file(file_name):
    """
    loads a .aqs or .json file into a dictionary
    Supports both JSON and YAML formats for backward compatibility
    Handles cross-platform path conversion automatically

    Args:
        file_name: Path to the file to load

    Returns: dictionary with keys device, experiments, probes

    """
    assert os.path.exists(file_name)

    with open(file_name, 'r') as infile:
        content = infile.read().strip()
        
    # Try JSON first (new format)
    try:
        import json
        data_dict = json.loads(content)
        # Convert cross-platform paths
        return convert_cross_platform_paths(data_dict)
    except json.JSONDecodeError:
        # Fall back to YAML (old format)
        try:
            import yaml
            data_dict = yaml.safe_load(content)
            # Convert cross-platform paths
            return convert_cross_platform_paths(data_dict)
        except Exception as e:
            raise ValueError(f"File {file_name} is neither valid JSON nor YAML: {e}")


# def save_aqs_file(filename, devices=None, experiments=None, probes=None, overwrite=False, verbose=False):
#     """
#     save devices, experiments and probes as a json file
#     Args:
#         filename:
#         devices:
#         experiments:
#         probes: dictionary of the form {device_name : probe_1_of_device, probe_2_of_device, ...}
#
#     Returns:
#
#     """
#
#     # if overwrite is false load existing data and append to new devices
#     if os.path.isfile(filename) and overwrite is False:
#         data_dict = load_aqs_file(filename)
#     else:
#         data_dict = {}
#
#     if devices is not None:
#         if 'devices' in data_dict:
#             data_dict['devices'].update(devices)
#         else:
#             data_dict['devices'] = devices
#
#     if experiments is not None:
#         if 'experiments' in data_dict:
#             data_dict['experiments'].update(experiments)
#         else:
#             data_dict['experiments'] = experiments
#
#     if probes is not None:
#         probe_devices = list(probes.keys())
#         if 'probes' in data_dict:
#             # all the devices required for old and new probes
#             probe_devices = set(probe_devices + list(data_dict['probes'].keys()))
#         else:
#             data_dict.update({'probes': {}})
#
#         for device in probe_devices:
#             if device in data_dict['probes'] and device in probes:
#                 # update the data_dict
#                 data_dict['probes'][device] = ','.join(
#                     set(data_dict['probes'][device].split(',') + probes[device].split(',')))
#             else:
#                 data_dict['probes'].update(probes)
#
#     if verbose:
#         print(('writing ', filename))
#
#     if data_dict != {}:
#
#         # if platform == 'Windows':
#         #     # windows can't deal with long filenames so we have to use the prefix '\\\\?\\'
#         #     if len(filename.split('\\\\?\\')) == 1:
#         #         filename = '\\\\?\\'+ filename
#         # create folder if it doesn't exist
#         if verbose:
#             print(('filename', filename))
#             print(('exists', os.path.exists(os.path.dirname(filename))))
#
#         if os.path.exists(os.path.dirname(filename)) is False:
#             # print(('creating', os.path.dirname(filename)))
#             os.makedirs(os.path.dirname(filename))
#
#         with open(filename, 'w') as outfile:
#             json.dump(data_dict, outfile, indent=4)
#             #outfile.write(yaml.dump(data_dict,default_flow_style=False))

def save_aqs_file(
    filename: str,
    devices:     Optional[Dict[str, Any]] = None,
    experiments: Optional[Dict[str, Any]] = None,
    probes:      Optional[Dict[str, str]] = None,
    overwrite:   bool = False
):
    path = Path(filename)
    base = {} if overwrite or not path.exists() else load_config(path)
    merged = merge_config(base,
                          devices=devices,
                          experiments=experiments,
                          probes=probes)
    if merged:
        save_config(path, merged)