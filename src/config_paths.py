# Created by Gurudev Dutt <gdutt@pitt.edu> on 7/29/25
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
# config_paths.py

from pathlib import Path
import json
import sys

# Default base folder under the user's home
HOME = Path.home()

# Windows-specific path detection for lab PCs
if sys.platform.startswith('win'):
    # Check if we're on a lab PC with D: drive
    if Path("D:/").exists():
        # Try to use D:\Duttlab\Experiments\ if it exists
        lab_path = Path("D:/Duttlab/Experiments")
        if lab_path.exists():
            DEFAULT_BASE = lab_path / "AQuISS_default_save_location"
        else:
            # Fallback to user directory
            DEFAULT_BASE = HOME / "Experiments" / "AQuISS_default_save_location"
    else:
        # No D: drive, use user directory
        DEFAULT_BASE = HOME / "Experiments" / "AQuISS_default_save_location"
else:
    # Unix/Mac - use standard home directory
    DEFAULT_BASE = HOME / "Experiments" / "AQuISS_default_save_location"

_DEFAULTS = {
    "data_folder":        DEFAULT_BASE / "data",
    "probes_folder":      DEFAULT_BASE / "probes_auto_generated",
    "device_folder":      DEFAULT_BASE / "devices_auto_generated",
    "experiments_folder": DEFAULT_BASE / "experiments_auto_generated",
    "probes_log_folder":  DEFAULT_BASE / "aqs_tmp",
    "workspace_config_dir": DEFAULT_BASE / "workspace_configs",
}

def load_json(path: Path) -> dict:
    """
    Load JSON data from a file with error handling.
    
    Args:
        path: Path to the JSON file
        
    Returns:
        Dictionary containing the JSON data, or empty dict if file doesn't exist
        or contains invalid JSON
    """
    if not path.exists():
        return {}
    
    content = path.read_text().strip()
    if not content:
        return {}
    
    try:
        return json.loads(content) or {}
    except json.JSONDecodeError:
        # Return empty dict for invalid JSON instead of raising
        return {}

def resolve_paths(config_path: Path = None) -> dict:
    """
    Resolve configuration paths by merging defaults with overrides from config file.
    
    This function takes the default paths and merges them with any overrides
    specified in a configuration file. It automatically creates missing directories
    for all paths except the gui_settings file.
    
    Args:
        config_path: Optional path to configuration file containing path overrides
        
    Returns:
        Dictionary mapping path keys to resolved Path objects
        
    Example:
        >>> paths = resolve_paths()
        >>> print(paths["data_folder"])
        /home/user/Experiments/AQuISS_default_save_location/data
        
        >>> # With custom config file
        >>> custom_config = Path("custom_config.json")
        >>> custom_config.write_text('{"paths": {"data_folder": "/custom/data"}}')
        >>> paths = resolve_paths(custom_config)
        >>> print(paths["data_folder"])
        /custom/data
    """
    overrides = {}
    if config_path and config_path.exists():
        overrides = load_json(config_path).get("paths", {})

    final = {}
    for key, default in _DEFAULTS.items():
        val = overrides.get(key)
        p = Path(val) if val else default
        # Create all directories including workspace_config_dir
        p.mkdir(parents=True, exist_ok=True)
        final[key] = p
    
    # Automatically create default workspace configuration if none exists
    workspace_dir = final.get('workspace_config_dir', _DEFAULTS['workspace_config_dir'])
    default_workspace_file = workspace_dir / "default_workspace.json"
    
    if not default_workspace_file.exists():
        default_config = {
            "workspace_name": "Default Pitt AQuISS Workspace",
            "description": "Default workspace configuration for Pitt AQuISS laboratory setup",
            "created_date": "2025-08-14",
            "version": "1.0",
            "gui_settings": {
                "experiments_folder": str(final.get('experiments_folder', '')),
                "data_folder": str(final.get('data_folder', '')),
                "device_folder": str(final.get('device_folder', '')),
                "probes_folder": str(final.get('probes_folder', '')),
                "probes_log_folder": str(final.get('probes_log_folder', ''))
            },
            "gui_settings_hidden": {
                "experiments_source_folder": "",
                "experiments_hidden_parameters": {}
            },
            "devices": {},
            "experiments": {},
            "probes": {},
            "paths": {
                "data_folder": str(final.get('data_folder', '')),
                "probes_folder": str(final.get('probes_folder', '')),
                "device_folder": str(final.get('device_folder', '')),
                "experiments_folder": str(final.get('experiments_folder', '')),
                "probes_log_folder": str(final.get('probes_log_folder', '')),
                "workspace_config_dir": str(final.get('workspace_config_dir', ''))
            }
        }
        
        try:
            with open(default_workspace_file, 'w') as f:
                json.dump(default_config, f, indent=4)
        except Exception as e:
            print(f"Warning: Could not create default workspace file: {e}")
    
    return final
