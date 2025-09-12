"""
Tests for pathlib and path handling improvements in confocal.py

This test suite validates the recent changes to confocal.py that:
1. Replace os.path with pathlib for cross-platform compatibility
2. Use get_project_root() helper function for consistent path resolution
3. Add robust error handling for file operations
4. Centralize binary file path resolution with get_binary_file_path()
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.Model.experiments.confocal import get_binary_file_path, ConfocalScan_Fast, ConfocalScan_Slow, Confocal_Point
from src.core.helper_functions import get_project_root


class TestGetBinaryFilePath:
    """Test the get_binary_file_path helper function"""
    
    def test_get_binary_file_path_success(self):
        """Test successful binary file path resolution"""
        # Test with existing binary files
        for filename in ['One_D_Scan.TB2', 'Trial_Counter.TB1', 'Averagable_Trial_Counter.TB1']:
            path = get_binary_file_path(filename)
            assert isinstance(path, Path)
            assert path.name == filename
            assert 'ADbasic' in str(path)
            assert path.exists(), f"Binary file {filename} should exist"
    
    def test_get_binary_file_path_nonexistent_file(self):
        """Test FileNotFoundError for non-existent binary files"""
        with pytest.raises(FileNotFoundError) as exc_info:
            get_binary_file_path('NonexistentFile.TB1')
        
        assert 'Binary file not found' in str(exc_info.value)
        assert 'NonexistentFile.TB1' in str(exc_info.value)
    
    def test_get_binary_file_path_empty_filename(self):
        """Test behavior with empty filename"""
        with pytest.raises(FileNotFoundError):
            get_binary_file_path('')
    
    def test_get_binary_file_path_project_root_integration(self):
        """Test that get_binary_file_path uses get_project_root correctly"""
        project_root = get_project_root()
        expected_path = project_root / 'src' / 'Controller' / 'binary_files' / 'ADbasic' / 'One_D_Scan.TB2'
        
        actual_path = get_binary_file_path('One_D_Scan.TB2')
        assert actual_path == expected_path
    
    @patch('src.Model.experiments.confocal.get_project_root')
    def test_get_binary_file_path_mocked_project_root(self, mock_get_project_root):
        """Test get_binary_file_path with mocked project root"""
        # Mock project root to return a temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_get_project_root.return_value = Path(temp_dir)
            
            # Create the expected directory structure
            adbasic_dir = Path(temp_dir) / 'src' / 'Controller' / 'binary_files' / 'ADbasic'
            adbasic_dir.mkdir(parents=True, exist_ok=True)
            
            # Create a test binary file
            test_file = adbasic_dir / 'TestFile.TB1'
            test_file.write_text('test content')
            
            # Test the function
            result = get_binary_file_path('TestFile.TB1')
            assert result == test_file
            assert result.exists()


class TestConfocalPathlibIntegration:
    """Test pathlib integration in confocal experiment classes"""
    
    def test_confocal_scan_fast_default_settings_path(self):
        """Test that ConfocalScan_Fast uses pathlib in default settings"""
        # Check that the default folderpath uses Path.home()
        fast_scan = ConfocalScan_Fast(devices={})
        
        # Find the 3D_scan parameter
        for param in fast_scan.settings:
            if param.name == '3D_scan':
                for subparam in param.value:
                    if subparam.name == 'folderpath':
                        folderpath = subparam.value
                        assert isinstance(folderpath, str)
                        # Should contain Path.home() structure
                        assert 'Experiments' in folderpath
                        assert 'AQuISS_default_save_location' in folderpath
                        assert 'confocal_scans' in folderpath
                        break
    
    def test_confocal_scan_slow_default_settings_path(self):
        """Test that ConfocalScan_Slow uses pathlib in default settings"""
        # Check that the default folderpath uses Path.home()
        slow_scan = ConfocalScan_Slow(devices={})
        
        # Find the 3D_scan parameter
        for param in slow_scan.settings:
            if param.name == '3D_scan':
                for subparam in param.value:
                    if subparam.name == 'folderpath':
                        folderpath = subparam.value
                        assert isinstance(folderpath, str)
                        # Should contain Path.home() structure
                        assert 'Experiments' in folderpath
                        assert 'AQuISS_default_save_location' in folderpath
                        assert 'confocal_scans' in folderpath
                        break
    
    @patch('src.Model.experiments.confocal.get_binary_file_path')
    def test_confocal_scan_fast_setup_scan_uses_helper(self, mock_get_binary_path):
        """Test that ConfocalScan_Fast.setup_scan uses get_binary_file_path"""
        mock_path = Path('/mock/path/One_D_Scan.TB2')
        mock_get_binary_path.return_value = mock_path
        
        # Create mock devices
        mock_devices = {
            'nanodrive': {'instance': MagicMock()},
            'adwin': {'instance': MagicMock()}
        }
        
        fast_scan = ConfocalScan_Fast(devices=mock_devices)
        
        # Call setup_scan
        fast_scan.setup_scan()
        
        # Verify get_binary_file_path was called
        mock_get_binary_path.assert_called_once_with('One_D_Scan.TB2')
    
    @patch('src.Model.experiments.confocal.get_binary_file_path')
    def test_confocal_scan_slow_setup_scan_uses_helper(self, mock_get_binary_path):
        """Test that ConfocalScan_Slow.setup_scan uses get_binary_file_path"""
        mock_path = Path('/mock/path/Trial_Counter.TB1')
        mock_get_binary_path.return_value = mock_path
        
        # Create mock devices
        mock_devices = {
            'nanodrive': {'instance': MagicMock()},
            'adwin': {'instance': MagicMock()}
        }
        
        slow_scan = ConfocalScan_Slow(devices=mock_devices)
        
        # Call setup_scan
        slow_scan.setup_scan()
        
        # Verify get_binary_file_path was called
        mock_get_binary_path.assert_called_once_with('Trial_Counter.TB1')
    
    @patch('src.Model.experiments.confocal.get_binary_file_path')
    def test_confocal_point_setup_uses_helper(self, mock_get_binary_path):
        """Test that Confocal_Point.setup uses get_binary_file_path"""
        mock_path = Path('/mock/path/Averagable_Trial_Counter.TB1')
        mock_get_binary_path.return_value = mock_path
        
        # Create mock devices
        mock_devices = {
            'nanodrive': {'instance': MagicMock()},
            'adwin': {'instance': MagicMock()}
        }
        
        confocal_point = Confocal_Point(devices=mock_devices)
        
        # Call setup
        confocal_point.setup()
        
        # Verify get_binary_file_path was called
        mock_get_binary_path.assert_called_once_with('Averagable_Trial_Counter.TB1')


class TestPathlibCrossPlatformCompatibility:
    """Test cross-platform path compatibility"""
    
    def test_pathlib_handles_windows_paths(self):
        """Test that pathlib correctly handles Windows-style paths"""
        # Simulate Windows path
        windows_path = Path('C:\\Users\\User\\Experiments\\AQuISS_default_save_location\\confocal_scans')
        
        # Should work correctly regardless of platform
        assert isinstance(windows_path, Path)
        assert 'confocal_scans' in str(windows_path)
    
    def test_pathlib_handles_unix_paths(self):
        """Test that pathlib correctly handles Unix-style paths"""
        # Simulate Unix path
        unix_path = Path('/home/user/Experiments/AQuISS_default_save_location/confocal_scans')
        
        # Should work correctly regardless of platform
        assert isinstance(unix_path, Path)
        assert 'confocal_scans' in str(unix_path)
    
    def test_pathlib_path_joining(self):
        """Test pathlib path joining operations"""
        base_path = Path('/base/path')
        sub_path = Path('subdirectory')
        filename = 'test.txt'
        
        # Test path joining
        full_path = base_path / sub_path / filename
        assert str(full_path) == '/base/path/subdirectory/test.txt'
        
        # Test with string components
        full_path_str = base_path / 'subdirectory' / 'test.txt'
        assert str(full_path_str) == '/base/path/subdirectory/test.txt'


class TestErrorHandling:
    """Test error handling in file operations"""
    
    @patch('src.Model.experiments.confocal.Path')
    @patch('builtins.print')
    def test_error_handling_directory_creation_failure(self, mock_print, mock_path_class):
        """Test error handling when directory creation fails"""
        # Mock Path to raise exception on mkdir
        mock_path = MagicMock()
        mock_path.mkdir.side_effect = PermissionError("Permission denied")
        mock_path_class.return_value = mock_path
        
        # Create a minimal experiment instance for testing
        mock_devices = {
            'nanodrive': {'instance': MagicMock()},
            'adwin': {'instance': MagicMock()}
        }
        
        fast_scan = ConfocalScan_Fast(devices=mock_devices)
        
        # Mock the _plot method context
        fast_scan.settings = {
            '3D_scan': {
                'enable': True,
                'folderpath': '/test/path'
            }
        }
        fast_scan.data_collected = True
        fast_scan.z_inital = 50.0
        
        # Mock axes_list and data
        mock_axes = [MagicMock()]
        mock_data = {'count_img': [[1, 2], [3, 4]]}
        
        # This should not raise an exception due to try-except
        try:
            fast_scan._plot(mock_axes, mock_data)
        except Exception as e:
            pytest.fail(f"_plot method should handle errors gracefully, but raised: {e}")
        
        # Verify error message was printed
        mock_print.assert_any_call("Warning: Failed to save 3D scan image: Permission denied")
    
    @patch('src.Model.experiments.confocal.ImageExporter')
    @patch('builtins.print')
    def test_error_handling_export_failure(self, mock_print, mock_exporter_class):
        """Test error handling when image export fails"""
        # Mock ImageExporter to raise exception
        mock_exporter = MagicMock()
        mock_exporter.export.side_effect = OSError("Export failed")
        mock_exporter_class.return_value = mock_exporter
        
        # Create a minimal experiment instance for testing
        mock_devices = {
            'nanodrive': {'instance': MagicMock()},
            'adwin': {'instance': MagicMock()}
        }
        
        fast_scan = ConfocalScan_Fast(devices=mock_devices)
        
        # Mock the _plot method context
        fast_scan.settings = {
            '3D_scan': {
                'enable': True,
                'folderpath': '/test/path'
            }
        }
        fast_scan.data_collected = True
        fast_scan.z_inital = 50.0
        
        # Mock axes_list and data
        mock_axes = [MagicMock()]
        mock_axes[0].scene.return_value = MagicMock()
        mock_data = {'count_img': [[1, 2], [3, 4]]}
        
        # This should not raise an exception due to try-except
        try:
            fast_scan._plot(mock_axes, mock_data)
        except Exception as e:
            pytest.fail(f"_plot method should handle errors gracefully, but raised: {e}")
        
        # Verify error message was printed
        mock_print.assert_any_call("Warning: Failed to save 3D scan image: Export failed")


class TestIntegrationWithExistingCode:
    """Test integration with existing codebase"""
    
    def test_imports_work_correctly(self):
        """Test that all necessary imports work correctly"""
        # Test that pathlib is imported
        from pathlib import Path
        assert Path is not None
        
        # Test that get_project_root is available
        from src.core.helper_functions import get_project_root
        assert get_project_root is not None
        
        # Test that confocal classes can be imported
        from src.Model.experiments.confocal import (
            ConfocalScan_Fast, 
            ConfocalScan_Slow, 
            Confocal_Point,
            get_binary_file_path
        )
        assert all([ConfocalScan_Fast, ConfocalScan_Slow, Confocal_Point, get_binary_file_path])
    
    def test_binary_files_exist(self):
        """Test that all required binary files exist"""
        required_files = [
            'One_D_Scan.TB2',
            'Trial_Counter.TB1', 
            'Averagable_Trial_Counter.TB1'
        ]
        
        for filename in required_files:
            path = get_binary_file_path(filename)
            assert path.exists(), f"Required binary file {filename} does not exist at {path}"
    
    def test_project_root_is_valid(self):
        """Test that get_project_root returns a valid project root"""
        project_root = get_project_root()
        assert project_root.exists()
        assert (project_root / 'src').exists()
        assert (project_root / 'src' / 'Model' / 'experiments' / 'confocal.py').exists()


if __name__ == '__main__':
    pytest.main([__file__]) 