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
# config_store.py
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, Optional

def load_config(path: Path) -> Dict[str, Any]:
    """
    Load configuration from a JSON file.
    
    Args:
        path: Path to the JSON configuration file
        
    Returns:
        Dictionary containing the configuration data
        
    Raises:
        json.JSONDecodeError: If the file contains invalid JSON
    """
    if not path.exists():
        return {}
    
    content = path.read_text().strip()
    if not content:
        return {}
    
    try:
        return json.loads(content) or {}
    except json.JSONDecodeError:
        # Re-raise with more context
        raise json.JSONDecodeError(
            f"Invalid JSON in config file: {path}", 
            content, 
            0
        )

def save_config(path: Path, data: Dict[str, Any]) -> None:
    """
    Atomically write data as JSON to path, creating parent directories.
    
    This function ensures that the file is written atomically to prevent
    corruption if the process is interrupted during writing.
    
    Args:
        path: Path where the configuration file should be saved (can be string or Path object)
        data: Dictionary containing the configuration data to save
        
    Raises:
        OSError: If the file cannot be written or directories cannot be created
        TypeError: If the data contains non-serializable objects
    """
    # Convert string to Path if needed
    if isinstance(path, str):
        path = Path(path)
    
    try:
        # Create parent directories if they don't exist
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create temporary file for atomic write
        tmp = path.with_suffix(path.suffix + ".tmp")
        
        # Write data to temporary file
        tmp.write_text(json.dumps(data, indent=4))
        
        # Atomically replace the original file
        tmp.replace(path)
        
    except (OSError, TypeError) as e:
        # Clean up temporary file if it exists
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass  # Ignore cleanup errors
        raise

def merge_config(
    base: Dict[str, Any],
    *,
    gui_settings: Optional[Dict[str, Any]] = None,
    hidden_params: Optional[Dict[str, Any]] = None,
    devices: Optional[Dict[str, Any]] = None,
    experiments: Optional[Dict[str, Any]] = None,
    probes: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Merge various configuration sections into one JSON-serializable dictionary.
    
    This function takes a base configuration dictionary and optionally adds
    new sections for GUI settings, hidden parameters, devices, experiments,
    and probes. Only sections that are not None are added to the result.
    
    Args:
        base: Base configuration dictionary
        gui_settings: Optional GUI settings dictionary
        hidden_params: Optional hidden parameters dictionary (stored as "experiments_hidden_parameters")
        devices: Optional devices configuration dictionary
        experiments: Optional experiments configuration dictionary
        probes: Optional probes configuration dictionary
        
    Returns:
        Merged configuration dictionary with all specified sections
        
    Example:
        >>> base = {"version": "1.0"}
        >>> merged = merge_config(
        ...     base,
        ...     gui_settings={"theme": "dark"},
        ...     devices={"microwave": {"type": "MicrowaveGenerator"}}
        ... )
        >>> print(merged)
        {'version': '1.0', 'gui_settings': {'theme': 'dark'}, 'devices': {'microwave': {'type': 'MicrowaveGenerator'}}}
    """
    out = dict(base)  # shallow copy to avoid modifying the original

    if gui_settings is not None:
        out["gui_settings"] = gui_settings

    if hidden_params is not None:
        out["experiments_hidden_parameters"] = hidden_params

    if devices is not None:
        out["devices"] = devices

    if experiments is not None:
        out["experiments"] = experiments

    if probes is not None:
        out["probes"] = probes

    return out
