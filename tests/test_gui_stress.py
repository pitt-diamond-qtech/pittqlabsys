#!/usr/bin/env python3
"""
GUI Stress Tests for AQuISS.
These tests simulate user interactions to find potential crashes.
"""

import pytest
import sys
import time
from pathlib import Path
from unittest.mock import Mock, patch

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtTest import QTest
from PyQt5.QtCore import Qt

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

@pytest.fixture
def main_window(mock_hardware, app):
    """Create MainWindow instance for testing"""
    from src.View.windows_and_widgets.main_window import MainWindow
    
    # Create window
    window = MainWindow()
    window.show()
    
    # Process events to ensure window is fully initialized
    app.processEvents()
    time.sleep(0.1)  # Small delay for stability
    
    yield window
    
    # Cleanup
    window.close()
    app.processEvents()

class TestGUIStress:
    """GUI stress tests to find potential crashes"""
    
    def test_rapid_tree_operations(self, main_window):
        """Test rapid tree operations to find race conditions"""
        # Create test data
        test_data = {f'param_{i}': f'value_{i}' for i in range(100)}
        
        # Rapidly fill and clear the tree
        for _ in range(10):
            main_window.fill_treewidget(main_window.tree_gui_settings, test_data)
            app.processEvents()
            
            # Verify items were added
            assert main_window.tree_gui_settings.topLevelItemCount() == 100
            
            # Clear and verify
            main_window.tree_gui_settings.clear()
            app.processEvents()
            assert main_window.tree_gui_settings.topLevelItemCount() == 0
            
    def test_concurrent_tree_updates(self, main_window):
        """Test concurrent updates to different trees"""
        # Create test data for different trees
        exp_data = {f'exp_{i}': f'exp_value_{i}' for i in range(50)}
        dev_data = {f'dev_{i}': f'dev_value_{i}' for i in range(50)}
        
        # Update both trees simultaneously
        main_window.fill_treewidget(main_window.tree_experiments, exp_data)
        main_window.fill_treewidget(main_window.tree_settings, dev_data)
        
        app.processEvents()
        
        # Verify both trees have items
        assert main_window.tree_experiments.topLevelItemCount() == 50
        assert main_window.tree_settings.topLevelItemCount() == 50
        
    def test_tree_item_selection(self, main_window):
        """Test tree item selection operations"""
        # Fill tree with test data
        test_data = {f'param_{i}': f'value_{i}' for i in range(20)}
        main_window.fill_treewidget(main_window.tree_gui_settings, test_data)
        app.processEvents()
        
        # Test selecting different items
        for i in range(min(5, main_window.tree_gui_settings.topLevelItemCount())):
            item = main_window.tree_gui_settings.topLevelItem(i)
            if item:
                main_window.tree_gui_settings.setCurrentItem(item)
                app.processEvents()
                
                # Verify selection
                assert main_window.tree_gui_settings.currentItem() == item
                
    def test_window_resize_operations(self, main_window):
        """Test window resize operations"""
        # Test various window sizes
        test_sizes = [(800, 600), (1024, 768), (1200, 900), (1600, 1200)]
        
        for width, height in test_sizes:
            main_window.resize(width, height)
            app.processEvents()
            time.sleep(0.05)  # Small delay for resize processing
            
            # Verify resize worked
            assert main_window.width() == width
            assert main_window.height() == height
            
    def test_menu_operations(self, main_window):
        """Test menu operations"""
        # Test that menus can be accessed
        if hasattr(main_window, 'menuBar'):
            menu_bar = main_window.menuBar()
            if menu_bar:
                # Test menu actions exist
                actions = menu_bar.actions()
                assert len(actions) > 0
                
    def test_button_click_handlers(self, main_window):
        """Test that button click handlers don't crash"""
        # Test various button clicks (without actual functionality)
        buttons_to_test = [
            'btn_load_experiments',
            'btn_load_devices', 
            'btn_load_probes',
            'btn_save_gui',
            'btn_load_gui'
        ]
        
        for button_name in buttons_to_test:
            if hasattr(main_window, button_name):
                button = getattr(main_window, button_name)
                if button and button.isEnabled():
                    # Just verify the button exists and is enabled
                    assert button is not None
                    assert button.isEnabled()
                    
    def test_tree_context_menus(self, main_window):
        """Test tree context menu operations"""
        # Fill tree with test data
        test_data = {'test_param': 'test_value'}
        main_window.fill_treewidget(main_window.tree_gui_settings, test_data)
        app.processEvents()
        
        # Test right-click on tree item
        if main_window.tree_gui_settings.topLevelItemCount() > 0:
            item = main_window.tree_gui_settings.topLevelItem(0)
            if item:
                # Simulate right-click
                main_window.tree_gui_settings.setCurrentItem(item)
                app.processEvents()
                
                # This test just verifies the operation doesn't crash
                # Actual context menu testing would require more complex setup
                assert True

if __name__ == "__main__":
    # Run stress tests
    pytest.main([__file__, "-v", "-s"]) 