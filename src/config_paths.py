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

# Default base folder under the user’s home
HOME = Path.home()
DEFAULT_BASE = HOME / "Experiments" / "AQuISS_default_save_location"

_DEFAULTS = {
    "data_folder":        DEFAULT_BASE / "data",
    "probes_folder":      DEFAULT_BASE / "probes_auto_generated",
    "device_folder":      DEFAULT_BASE / "devices_auto_generated",
    "experiments_folder": DEFAULT_BASE / "experiments_auto_generated",
    "probes_log_folder":  DEFAULT_BASE / "aqs_tmp",
    "gui_settings":       DEFAULT_BASE / "src_config.json",
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
        if key != "gui_settings":
            p.mkdir(parents=True, exist_ok=True)
        final[key] = p
    return final
