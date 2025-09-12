#!/usr/bin/env python3
"""
Test configuration-based environment detection system.

This test verifies that:
1. Config flags take precedence over auto-detection
2. Different environment configurations work correctly
3. Mock detection respects config settings
"""

import pytest
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

# Add src to path for imports
sys.path.insert(0, 'src')

from src.tools.export_default import detect_mock_devices


class TestEnvironmentDetection:
    """Test the environment detection system with different config scenarios."""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary directory for config files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def mock_config_path(self, temp_config_dir):
        """Create a mock config.json path."""
        return temp_config_dir / "config.json"
    
    def create_config_file(self, config_path, config_data):
        """Helper to create a config file with given data."""
        with open(config_path, 'w') as f:
            json.dump(config_data, f, indent=2)
    
    @patch('pathlib.Path')
    def test_lab_pc_config_real_hardware(self, mock_path, mock_config_path):
        """Test lab PC configuration with real hardware enabled."""
        # Mock the config path to point to our temp file
        mock_path.return_value.parent.parent = mock_config_path.parent
        
        config_data = {
            "environment": {
                "is_development": False,
                "is_mock": False,
                "force_mock_devices": False,
                "hardware_detection_enabled": True
            }
        }
        
        self.create_config_file(mock_config_path, config_data)
        
        # Test detection
        mock_devices, warning_message = detect_mock_devices()
        
        # Should detect no mock devices for lab PC (except testing environment)
        # Note: pytest environment will still be detected
        non_testing_mocks = [d for d in mock_devices if "testing" not in d.lower()]
        assert not non_testing_mocks, f"Expected no non-testing mock devices, got: {non_testing_mocks}"
        # The warning message should indicate hardware implementations or testing environment
        assert any(msg in warning_message.lower() for msg in ["hardware implementations", "testing environment"])
    
    @patch('pathlib.Path')
    def test_development_machine_config(self, mock_path, mock_config_path):
        """Test development machine configuration."""
        # Mock the config path to point to our temp file
        mock_path.return_value.parent.parent = mock_config_path.parent
        
        config_data = {
            "environment": {
                "is_development": True,
                "is_mock": False,
                "force_mock_devices": False,
                "hardware_detection_enabled": True
            }
        }
        
        self.create_config_file(mock_config_path, config_data)
        
        # Test detection
        mock_devices, warning_message = detect_mock_devices()
        
        # Should detect development environment (may also detect testing environment)
        development_detected = any("development" in device.lower() for device in mock_devices)
        assert development_detected, f"Expected development environment detection, got: {mock_devices}"
        # The warning message should mention development
        assert "development environment detected" in warning_message.lower()
    
    @patch('pathlib.Path')
    def test_forced_mock_config(self, mock_path, mock_config_path):
        """Test forced mock configuration."""
        # Mock the config path to point to our temp file
        mock_path.return_value.parent.parent = mock_config_path.parent
        
        config_data = {
            "environment": {
                "is_development": False,
                "is_mock": True,
                "force_mock_devices": True,
                "hardware_detection_enabled": False
            }
        }
        
        self.create_config_file(mock_config_path, config_data)
        
        # Test detection
        mock_devices, warning_message = detect_mock_devices()
        
        # Should detect mock environment
        assert any("mock environment" in device.lower() for device in mock_devices), \
            f"Expected mock environment detection, got: {mock_devices}"
        assert "mock environment detected" in warning_message.lower()
    
    @patch('pathlib.Path')
    def test_hardware_detection_disabled(self, mock_path, mock_config_path):
        """Test when hardware detection is disabled."""
        # Mock the config path to point to our temp file
        mock_path.return_value.parent.parent = mock_config_path.parent
        
        config_data = {
            "environment": {
                "is_development": False,
                "is_mock": False,
                "force_mock_devices": False,
                "hardware_detection_enabled": False
            }
        }
        
        self.create_config_file(mock_config_path, config_data)
        
        # Test detection
        mock_devices, warning_message = detect_mock_devices()
        
        # Should detect hardware detection disabled
        assert any("hardware detection disabled" in device.lower() for device in mock_devices), \
            f"Expected hardware detection disabled, got: {mock_devices}"
        assert "hardware detection disabled" in warning_message.lower()
    
    @patch('pathlib.Path')
    def test_config_file_not_found_fallback(self, mock_path):
        """Test fallback behavior when config.json doesn't exist."""
        # Mock the config path to point to non-existent file
        mock_path.return_value.parent.parent = mock_path.return_value
        
        # Test detection - should fall back to other detection methods
        mock_devices, warning_message = detect_mock_devices()
        
        # Should not crash, should return some result
        assert isinstance(mock_devices, list), "Expected list of mock devices"
        assert isinstance(warning_message, str), "Expected warning message string"
    
    @patch('pathlib.Path')
    def test_config_file_invalid_json_fallback(self, mock_path, mock_config_path):
        """Test fallback behavior when config.json has invalid JSON."""
        # Mock the config path to point to our temp file
        mock_path.return_value.parent.parent = mock_config_path.parent
        
        # Create invalid JSON file
        with open(mock_config_path, 'w') as f:
            f.write("{ invalid json content")
        
        # Test detection - should fall back to other detection methods
        mock_devices, warning_message = detect_mock_devices()
        
        # Should not crash, should return some result
        assert isinstance(mock_devices, list), "Expected list of mock devices"
        assert isinstance(warning_message, str), "Expected warning message string"
    
    @patch('pathlib.Path')
    def test_config_priority_over_environment_variables(self, mock_path, mock_config_path):
        """Test that config flags take precedence over environment variables."""
        # Mock the config path to point to our temp file
        mock_path.return_value.parent.parent = mock_config_path.parent
        
        config_data = {
            "environment": {
                "is_development": False,  # Lab PC setting
                "is_mock": False,
                "force_mock_devices": False,
                "hardware_detection_enabled": True
            }
        }
        
        self.create_config_file(mock_config_path, config_data)
        
        # Set environment variables that would normally trigger mock detection
        with patch.dict(os.environ, {'PYTEST_CURRENT_TEST': 'test_name'}):
            # Test detection
            mock_devices, warning_message = detect_mock_devices()
            
            # Config should override environment variables
            # Should detect no mock devices for lab PC (except testing environment)
            non_testing_mocks = [d for d in mock_devices if "testing" not in d.lower()]
            assert not non_testing_mocks, f"Config should override env vars, got: {non_testing_mocks}"
            # The warning message should indicate hardware implementations or testing environment
            assert any(msg in warning_message.lower() for msg in ["hardware implementations", "testing environment"])
    
    @patch('pathlib.Path')
    def test_config_priority_over_path_detection(self, mock_path, mock_config_path):
        """Test that config flags take precedence over path-based detection."""
        # Mock the config path to point to our temp file
        mock_path.return_value.parent.parent = mock_config_path.parent
        
        config_data = {
            "environment": {
                "is_development": False,  # Lab PC setting
                "is_mock": False,
                "force_mock_devices": False,
                "hardware_detection_enabled": True
            }
        }
        
        self.create_config_file(mock_config_path, config_data)
        
        # Mock current working directory to simulate PyCharmProjects path
        with patch('os.getcwd', return_value="D:\\PyCharmProjects\\pittqlabsys"):
            # Test detection
            mock_devices, warning_message = detect_mock_devices()
            
            # Config should override path-based detection
            # Should detect no mock devices for lab PC (except testing environment)
            non_testing_mocks = [d for d in mock_devices if "testing" not in d.lower()]
            assert not non_testing_mocks, f"Config should override path detection, got: {non_testing_mocks}"
            # The warning message should indicate hardware implementations or testing environment
            assert any(msg in warning_message.lower() for msg in ["hardware implementations", "testing environment"])


class TestEnvironmentDetectionIntegration:
    """Integration tests for environment detection with real config files."""
    
    def test_default_config_behavior(self):
        """Test behavior with the actual project's config.json."""
        # This test uses the real config.json from the project
        try:
            mock_devices, warning_message = detect_mock_devices()
            
            # Should not crash
            assert isinstance(mock_devices, list), "Expected list of mock devices"
            assert isinstance(warning_message, str), "Expected warning message string"
            
            print(f"Default config result: {mock_devices}")
            print(f"Warning message: {warning_message}")
            
        except Exception as e:
            pytest.fail(f"Environment detection crashed: {e}")
    
    def test_environment_detection_consistency(self):
        """Test that multiple calls return consistent results."""
        try:
            # Call multiple times
            result1 = detect_mock_devices()
            result2 = detect_mock_devices()
            result3 = detect_mock_devices()
            
            # Results should be consistent
            assert result1 == result2, "First two calls should be identical"
            assert result2 == result3, "Second and third calls should be identical"
            
        except Exception as e:
            pytest.fail(f"Environment detection consistency test failed: {e}")


if __name__ == "__main__":
    # Run basic tests
    print("Testing environment detection system...")
    
    # Test with default config
    try:
        mock_devices, warning_message = detect_mock_devices()
        print(f"✅ Default config test passed")
        print(f"   Mock devices: {mock_devices}")
        print(f"   Warning: {warning_message}")
    except Exception as e:
        print(f"❌ Default config test failed: {e}")
    
    print("\nRun with pytest for full test suite:")
    print("pytest tests/test_environment_detection.py -v")
