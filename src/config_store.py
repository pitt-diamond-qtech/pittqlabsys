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
    if path.exists():
        return json.loads(path.read_text()) or {}
    return {}

def save_config(path: Path, data: Dict[str, Any]) -> None:
    """
    Atomically write `data` as JSON to `path`, creating parent dirs.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=4))
    tmp.replace(path)

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
    Merge the various pieces into one JSON‐serializable dict.
    """
    out = dict(base)  # shallow copy

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
