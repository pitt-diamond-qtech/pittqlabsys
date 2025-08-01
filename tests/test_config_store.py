"""
Tests for config_store module.

This module tests the configuration storage and path management functionality
for the AQuISS system.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open
import pytest
from src.core.helper_functions import get_project_root

# Import the module under test
import sys
project_root = get_project_root()
sys.path.insert(0, str(project_root))
from src.config_store import load_config, merge_config, save_config
from src.config_paths import load_json, resolve_paths, _DEFAULTS, DEFAULT_BASE


class TestLoadConfig:
    """Test cases for load_config function."""
    
    def test_load_config_nonexistent_returns_empty(self, tmp_path):
        """Test loading non-existent config file returns empty dict."""
        p = tmp_path / "does_not_exist.json"
        assert not p.exists()
        data = load_config(p)
        assert data == {}
    
    def test_load_config_parses_valid_json(self, tmp_path):
        """Test loading valid JSON config file."""
        p = tmp_path / "cfg.json"
        payload = {"foo": 123, "nested": {"a": 1}}
        p.write_text(json.dumps(payload))
        data = load_config(p)
        assert data == payload
    
    def test_load_config_handles_empty_file(self, tmp_path):
        """Test loading empty file returns empty dict."""
        p = tmp_path / "empty.json"
        p.write_text("")
        data = load_config(p)
        assert data == {}
    
    def test_load_config_handles_whitespace_only(self, tmp_path):
        """Test loading file with only whitespace returns empty dict."""
        p = tmp_path / "whitespace.json"
        p.write_text("   \n\t  ")
        data = load_config(p)
        assert data == {}
    
    def test_load_config_handles_invalid_json(self, tmp_path):
        """Test loading invalid JSON raises appropriate exception."""
        p = tmp_path / "invalid.json"
        p.write_text("{invalid json")
        
        with pytest.raises(json.JSONDecodeError):
            load_config(p)
    
    def test_load_config_handles_complex_nested_data(self, tmp_path):
        """Test loading complex nested JSON data."""
        p = tmp_path / "complex.json"
        payload = {
            "devices": {
                "microwave": {
                    "type": "sg384",
                    "settings": {
                        "frequency": 2.87e9,
                        "power": -10.0
                    }
                }
            },
            "experiments": {
                "odmr": {
                    "frequency_range": [2.7e9, 3.0e9],
                    "averages": 10
                }
            },
            "gui_settings": {
                "theme": "dark",
                "window_size": [1024, 768]
            }
        }
        p.write_text(json.dumps(payload))
        data = load_config(p)
        assert data == payload


class TestSaveConfig:
    """Test cases for save_config function."""
    
    def test_save_config_creates_file(self, tmp_path):
        """Test saving config creates the file."""
        p = tmp_path / "test_config.json"
        data = {"test": "value"}
        
        save_config(p, data)
        
        assert p.exists()
        loaded_data = json.loads(p.read_text())
        assert loaded_data == data
    
    def test_save_config_creates_parent_dirs(self, tmp_path):
        """Test saving config creates parent directories."""
        nested = tmp_path / "sub" / "sub2" / "cfg.json"
        assert not nested.parent.exists()
        
        save_config(nested, {"x": "y"})
        
        assert nested.parent.exists()
        assert nested.exists()
    
    def test_save_config_atomic_write(self, tmp_path):
        """Test atomic write prevents corruption on partial writes."""
        p = tmp_path / "atomic_test.json"
        
        # Write initial data
        save_config(p, {"v": 1})
        
        # Manually create a stale .tmp to simulate crash
        tmp = p.with_suffix(".json.tmp")
        tmp.write_text("corrupted")
        
        # Save new data
        save_config(p, {"v": 2})
        
        # The .tmp from before should have been replaced/removed
        assert not tmp.exists()
        
        # File contains the new data
        assert load_config(p) == {"v": 2}
    
    def test_save_config_preserves_json_formatting(self, tmp_path):
        """Test saved JSON is properly formatted."""
        p = tmp_path / "formatted.json"
        data = {"a": 1, "b": {"c": 2, "d": 3}}
        
        save_config(p, data)
        
        # Check that the file is properly formatted
        content = p.read_text()
        parsed = json.loads(content)
        assert parsed == data
        
        # Check that it's indented (has multiple lines)
        lines = content.split('\n')
        assert len(lines) > 1
    
    def test_save_config_overwrites_existing(self, tmp_path):
        """Test saving overwrites existing file."""
        p = tmp_path / "overwrite.json"
        
        # Write initial data
        save_config(p, {"old": "data"})
        
        # Overwrite with new data
        save_config(p, {"new": "data"})
        
        # Should contain new data
        assert load_config(p) == {"new": "data"}
    
    def test_save_config_handles_empty_dict(self, tmp_path):
        """Test saving empty dictionary."""
        p = tmp_path / "empty.json"
        
        save_config(p, {})
        
        assert p.exists()
        assert load_config(p) == {}


class TestMergeConfig:
    """Test cases for merge_config function."""
    
    def test_merge_config_adds_new_sections(self):
        """Test merging adds new configuration sections."""
        base = {"keep": "this"}
        merged = merge_config(
            base,
            gui_settings={"ui": True},
            hidden_params={"exp1": {"p": False}},
            devices={"devA": {"type": "x"}},
            experiments={"expA": {"param": 1}},
            probes={"devA": "pr1,pr2"}
        )
        
        # Base keys remain
        assert merged["keep"] == "this"
        
        # New sections exist
        assert merged["gui_settings"] == {"ui": True}
        assert merged["experiments_hidden_parameters"] == {"exp1": {"p": False}}
        assert merged["devices"]["devA"]["type"] == "x"
        assert merged["experiments"]["expA"]["param"] == 1
        assert merged["probes"]["devA"] == "pr1,pr2"
    
    def test_merge_config_does_not_modify_base(self):
        """Test merging doesn't modify the original base dictionary."""
        base = {}
        merged = merge_config(base, devices={"d1": 1})
        
        # Base dict must remain unchanged
        assert base == {}
    
    def test_merge_config_handles_none_values(self):
        """Test merging with None values doesn't add sections."""
        base = {"existing": "value"}
        merged = merge_config(
            base,
            gui_settings=None,
            hidden_params=None,
            devices=None,
            experiments=None,
            probes=None
        )
        
        # Should only contain base values
        assert merged == {"existing": "value"}
    
    def test_merge_config_handles_empty_dicts(self):
        """Test merging with empty dictionaries."""
        base = {"base": "value"}
        merged = merge_config(
            base,
            gui_settings={},
            devices={},
            experiments={}
        )
        
        assert merged["gui_settings"] == {}
        assert merged["devices"] == {}
        assert merged["experiments"] == {}
        assert merged["base"] == "value"
    
    def test_merge_config_complex_nested_data(self):
        """Test merging complex nested data structures."""
        base = {"version": "1.0"}
        
        complex_gui = {
            "theme": "dark",
            "window": {
                "size": [1024, 768],
                "position": [100, 100]
            }
        }
        
        complex_devices = {
            "microwave": {
                "type": "sg384",
                "settings": {
                    "frequency": 2.87e9,
                    "power": -10.0
                }
            }
        }
        
        merged = merge_config(
            base,
            gui_settings=complex_gui,
            devices=complex_devices
        )
        
        assert merged["version"] == "1.0"
        assert merged["gui_settings"]["theme"] == "dark"
        assert merged["gui_settings"]["window"]["size"] == [1024, 768]
        assert merged["devices"]["microwave"]["type"] == "sg384"
        assert merged["devices"]["microwave"]["settings"]["frequency"] == 2.87e9


class TestLoadJson:
    """Test cases for load_json function from config_paths."""
    
    def test_load_json_nonexistent_returns_empty(self, tmp_path):
        """Test loading non-existent JSON file returns empty dict."""
        p = tmp_path / "nonexistent.json"
        assert not p.exists()
        data = load_json(p)
        assert data == {}
    
    def test_load_json_valid_file(self, tmp_path):
        """Test loading valid JSON file."""
        p = tmp_path / "valid.json"
        payload = {"key": "value", "number": 42}
        p.write_text(json.dumps(payload))
        data = load_json(p)
        assert data == payload
    
    def test_load_json_empty_file(self, tmp_path):
        """Test loading empty file returns empty dict."""
        p = tmp_path / "empty.json"
        p.write_text("")
        data = load_json(p)
        assert data == {}


class TestResolvePaths:
    """Test cases for resolve_paths function."""
    
    def test_resolve_paths_uses_defaults_when_no_config(self):
        """Test resolving paths uses defaults when no config file provided."""
        paths = resolve_paths()
        
        assert paths["data_folder"] == _DEFAULTS["data_folder"]
        assert paths["probes_folder"] == _DEFAULTS["probes_folder"]
        assert paths["device_folder"] == _DEFAULTS["device_folder"]
        assert paths["experiments_folder"] == _DEFAULTS["experiments_folder"]
        assert paths["probes_log_folder"] == _DEFAULTS["probes_log_folder"]
        assert paths["gui_settings"] == _DEFAULTS["gui_settings"]
    
    def test_resolve_paths_with_config_overrides(self, tmp_path):
        """Test resolving paths with config file overrides."""
        config_file = tmp_path / "config.json"
        override_path = tmp_path / "custom_data"
        
        config_data = {
            "paths": {
                "data_folder": str(override_path)
            }
        }
        config_file.write_text(json.dumps(config_data))
        
        paths = resolve_paths(config_file)
        
        assert paths["data_folder"] == override_path
        # Other paths should still be defaults
        assert paths["probes_folder"] == _DEFAULTS["probes_folder"]
    
    def test_resolve_paths_creates_directories(self, tmp_path):
        """Test resolving paths creates missing directories."""
        config_file = tmp_path / "config.json"
        custom_path = tmp_path / "custom" / "data"
        
        config_data = {
            "paths": {
                "data_folder": str(custom_path)
            }
        }
        config_file.write_text(json.dumps(config_data))
        
        assert not custom_path.exists()
        paths = resolve_paths(config_file)
        
        assert custom_path.exists()
        assert paths["data_folder"] == custom_path
    
    def test_resolve_paths_does_not_create_gui_settings_dir(self, tmp_path):
        """Test resolving paths doesn't create directory for gui_settings file."""
        config_file = tmp_path / "config.json"
        gui_file = tmp_path / "custom" / "settings.json"
        
        config_data = {
            "paths": {
                "gui_settings": str(gui_file)
            }
        }
        config_file.write_text(json.dumps(config_data))
        
        paths = resolve_paths(config_file)
        
        # Should not create the directory for gui_settings file
        assert not gui_file.parent.exists()
        assert paths["gui_settings"] == gui_file
    
    def test_resolve_paths_handles_invalid_config(self, tmp_path):
        """Test resolving paths handles invalid config file gracefully."""
        config_file = tmp_path / "invalid.json"
        config_file.write_text("{invalid json")
        
        # Should not raise exception, should use defaults
        paths = resolve_paths(config_file)
        
        assert paths["data_folder"] == _DEFAULTS["data_folder"]
        assert paths["probes_folder"] == _DEFAULTS["probes_folder"]


class TestIntegration:
    """Integration tests for the config system."""
    
    def test_save_and_load_roundtrip(self, tmp_path):
        """Test complete save and load roundtrip."""
        p = tmp_path / "roundtrip.json"
        data = {"a": 42, "b": [1, 2, 3], "nested": {"x": "y"}}
        
        # Save
        save_config(p, data)
        
        # File should exist, and no .tmp hanging around
        assert p.exists()
        assert not Path(str(p) + ".tmp").exists()
        
        # Load back
        loaded = load_config(p)
        assert loaded == data
    
    def test_merge_and_save_workflow(self, tmp_path):
        """Test complete workflow of merging and saving config."""
        base_config = {"version": "1.0"}
        
        # Merge with new sections
        merged = merge_config(
            base_config,
            gui_settings={"theme": "dark"},
            devices={"microwave": {"type": "sg384"}}
        )
        
        # Save merged config
        config_file = tmp_path / "workflow.json"
        save_config(config_file, merged)
        
        # Load and verify
        loaded = load_config(config_file)
        assert loaded["version"] == "1.0"
        assert loaded["gui_settings"]["theme"] == "dark"
        assert loaded["devices"]["microwave"]["type"] == "sg384"
    
    def test_paths_and_config_integration(self, tmp_path):
        """Test integration between path resolution and config loading."""
        # Create a config file with custom paths
        config_file = tmp_path / "paths_config.json"
        custom_data_path = tmp_path / "custom_data"
        
        config_data = {
            "paths": {
                "data_folder": str(custom_data_path)
            },
            "gui_settings": {
                "theme": "dark"
            }
        }
        config_file.write_text(json.dumps(config_data))
        
        # Resolve paths
        paths = resolve_paths(config_file)
        
        # Verify custom path was created
        assert custom_data_path.exists()
        assert paths["data_folder"] == custom_data_path
        
        # Load the config
        loaded_config = load_config(config_file)
        assert loaded_config["gui_settings"]["theme"] == "dark"


if __name__ == "__main__":
    pytest.main([__file__])