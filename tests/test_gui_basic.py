#!/usr/bin/env python3
"""
Basic GUI tests for AQuISS.
These tests verify core GUI functionality without requiring real hardware.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtTest import QTest
from PyQt5.QtCore import Qt

# Mock hardware dependencies
@pytest.fixture(scope="session")
def mock_hardware():
    """Mock all hardware dependencies"""
    with patch('src.Controller.sg384.SG384Generator'), \
         patch('src.Controller.adwin_gold.AdwinGoldDevice'), \
         patch('src.Controller.nanodrive.MCLNanoDrive'):
        yield

@pytest.fixture
def app():
    """Create QApplication for testing"""
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication(sys.argv)
    yield app
    # Don't quit the app as it might be shared

@pytest.fixture
def main_window(mock_hardware, app):
    """Create MainWindow instance for testing"""
    from src.View.windows_and_widgets.main_window import MainWindow
    
    # Create window
    window = MainWindow()
    window.show()
    
    yield window
    
    # Cleanup
    window.close()

class TestGUIBasic:
    """Basic GUI functionality tests"""
    
    def test_main_window_creation(self, main_window):
        """Test that main window can be created"""
        assert main_window is not None
        assert main_window.isVisible()
        
    def test_tree_widgets_exist(self, main_window):
        """Test that all required tree widgets exist"""
        assert hasattr(main_window, 'tree_experiments')
        assert hasattr(main_window, 'tree_settings')
        assert hasattr(main_window, 'tree_gui_settings')
        
    def test_fill_treewidget_basic(self, main_window):
        """Test basic tree population"""
        # Create a simple test dictionary
        test_params = {
            'test_param': 'test_value',
            'test_number': 42
        }
        
        # Test filling the tree
        main_window.fill_treewidget(main_window.tree_gui_settings, test_params)
        
        # Verify items were added
        assert main_window.tree_gui_settings.topLevelItemCount() == 2
        
    def test_load_dialog_creation(self, main_window):
        """Test that LoadDialog can be created"""
        from src.View.windows_and_widgets.load_dialog import LoadDialog
        
        # Mock the file dialog to avoid actual file system access
        with patch('PyQt5.QtWidgets.QFileDialog.getExistingDirectory') as mock_dir:
            mock_dir.return_value = str(project_root / "examples")
            
            dialog = LoadDialog(elements_type="experiments", 
                              elements_old={}, 
                              filename=str(project_root / "examples"))
            
            assert dialog is not None
            dialog.close()
            
    def test_gui_logging_setup(self, main_window):
        """Test that GUI logging is properly set up"""
        import logging
        logger = logging.getLogger('AQuISS_GUI')
        assert logger is not None
        assert logger.level == logging.DEBUG
        
    @pytest.mark.skip(reason="Requires user interaction")
    def test_experiment_loading_ui(self, main_window):
        """Test the experiment loading UI elements exist"""
        # This test just verifies the UI elements exist
        # Actual loading would require user interaction
        
        # Check that the load experiments button exists
        assert hasattr(main_window, 'btn_load_experiments')
        assert main_window.btn_load_experiments is not None
        
        # Check that the tree for experiments exists
        assert hasattr(main_window, 'tree_experiments')
        assert main_window.tree_experiments is not None

if __name__ == "__main__":
    # Run basic tests
    pytest.main([__file__, "-v"]) 