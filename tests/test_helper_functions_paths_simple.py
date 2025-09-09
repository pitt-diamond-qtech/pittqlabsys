"""
Simple test cases for path-related helper functions in src.core.helper_functions.

Tests the get_configured_data_folder and get_configured_confocal_scans_folder functions
to ensure they correctly read paths from the config file and handle fallbacks properly.
"""

import pytest
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import patch

from src.core.helper_functions import (
    get_configured_data_folder,
    get_configured_confocal_scans_folder
)


class TestPathHelperFunctionsSimple:
    """Simple test cases for path helper functions."""
    
    def test_get_configured_data_folder_current_config(self):
        """Test that get_configured_data_folder reads from current config.json."""
        result = get_configured_data_folder()
        # Should return the D: drive path we set in config.json
        assert "D:" in str(result) or "Experiments" in str(result)
        assert "AQuISS_default_save_location" in str(result)
        assert "data" in str(result)
    
    def test_get_configured_confocal_scans_folder_current_config(self):
        """Test that get_configured_confocal_scans_folder uses configured data folder."""
        result = get_configured_confocal_scans_folder()
        # Should return the D: drive path with confocal_scans subfolder
        assert "D:" in str(result) or "Experiments" in str(result)
        assert "AQuISS_default_save_location" in str(result)
        assert "confocal_scans" in str(result)
    
    def test_confocal_scans_folder_construction(self):
        """Test that confocal scans folder is correctly constructed from data folder."""
        # Test with a known data folder path
        test_data_folder = Path("/test/data/folder")
        
        with patch("src.core.helper_functions.get_configured_data_folder", return_value=test_data_folder):
            result = get_configured_confocal_scans_folder()
            expected = test_data_folder / "confocal_scans"
            assert result == expected
    
    def test_functions_return_path_objects(self):
        """Test that functions return Path objects."""
        data_folder = get_configured_data_folder()
        confocal_folder = get_configured_confocal_scans_folder()
        
        assert isinstance(data_folder, Path)
        assert isinstance(confocal_folder, Path)
    
    def test_confocal_folder_contains_data_folder(self):
        """Test that confocal scans folder is a subfolder of data folder."""
        data_folder = get_configured_data_folder()
        confocal_folder = get_configured_confocal_scans_folder()
        
        # The confocal folder should be a subfolder of the data folder
        assert confocal_folder.parent == data_folder
        assert confocal_folder.name == "confocal_scans"


if __name__ == "__main__":
    pytest.main([__file__])
