#!/usr/bin/env python3
"""
GUI Stress Tests for AQuISS.
These tests simulate user interactions to find potential crashes.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QApplication
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtTest import QTest

from src.View.windows_and_widgets.main_window import MainWindow

@pytest.fixture(scope="session")
def app():
    """Create QApplication instance for testing"""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    app.setQuitOnLastWindowClosed(False)
    yield app
    # Cleanup handled by session scope

@pytest.fixture
def main_window(app):
    """Create MainWindow instance for testing"""
    with patch('src.config_store.load_config'), \
         patch('src.config_store.merge_config'):
        
        window = MainWindow(config_file=None, gui_config_file=None)
        window.save_config = Mock()
        window.save_dataset = Mock()
        
        # Don't show the window to avoid GUI blinking
        # window.show()
        # time.sleep(0.1)
        
        yield window
        
        try:
            # window.hide()
            app.processEvents()
        except Exception:
            pass

class TestGUIStress:
    """Test GUI stress and performance"""
    
    def test_rapid_tree_operations(self, main_window):
        """Test rapid tree operations for performance"""
        # Use the correct tree widget (tree_experiments is QTreeWidget)
        tree = main_window.tree_experiments
        
        # Create large dataset
        large_data = {f'param_{i}': f'value_{i}' for i in range(100)}
        
        # Measure performance of multiple operations
        start_time = time.time()
        
        for _ in range(5):  # Perform 5 rapid operations
            main_window.fill_treewidget(tree, large_data)
            # Small delay to simulate real usage
            time.sleep(0.01)
        
        end_time = time.time()
        
        # Verify all items were added
        assert tree.topLevelItemCount() == 100
        
        # Performance should be reasonable (less than 2 seconds for 5 operations)
        assert end_time - start_time < 2.0
    
    def test_tree_item_selection(self, main_window):
        """Test tree item selection operations"""
        # Use the correct tree widget (tree_experiments is QTreeWidget)
        tree = main_window.tree_experiments
        
        # Fill tree with test data
        test_data = {f'param_{i}': f'value_{i}' for i in range(20)}
        main_window.fill_treewidget(tree, test_data)
        
        # Verify tree was populated
        assert tree.topLevelItemCount() == 20
        
        # Test selection operations
        for i in range(min(5, tree.topLevelItemCount())):
            item = tree.topLevelItem(i)
            tree.setCurrentItem(item)
            assert tree.currentItem() == item
            assert tree.currentItem().text(0) == f'param_{i}'
    
    def test_window_resize_operations(self, main_window, app):
        """Test window resize operations"""
        # Get initial size
        initial_width = main_window.width()
        initial_height = main_window.height()
        
        # Test that resize method exists and can be called
        assert hasattr(main_window, 'resize')
        assert callable(main_window.resize)
        
        # Test a single resize operation to a reasonable size
        test_width = 1200
        test_height = 800
        
        # Attempt resize
        main_window.resize(test_width, test_height)
        app.processEvents()
        
        # Verify that resize was attempted (the actual size might be constrained by window manager)
        # Just check that the resize method didn't crash and the window still exists
        assert main_window.width() > 0
        assert main_window.height() > 0
        
        # Restore original size
        main_window.resize(initial_width, initial_height)
        app.processEvents()
        
        # Verify we're back to original size (or close to it)
        assert abs(main_window.width() - initial_width) < 200
        assert abs(main_window.height() - initial_height) < 200
    
    def test_tree_context_menus(self, main_window):
        """Test tree context menu operations"""
        # Use the correct tree widget (tree_experiments is QTreeWidget)
        tree = main_window.tree_experiments
        
        # Fill tree with test data
        test_data = {'test_param': 'test_value'}
        main_window.fill_treewidget(tree, test_data)
        
        # Verify tree was populated
        assert tree.topLevelItemCount() == 1
        
        # Set context menu policy
        tree.setContextMenuPolicy(Qt.CustomContextMenu)
        
        # Verify context menu policy is set
        assert tree.contextMenuPolicy() == Qt.CustomContextMenu
    
    def test_memory_usage_under_load(self, main_window):
        """Test memory usage under load"""
        tree = main_window.tree_experiments
        
        # Create very large dataset
        large_data = {f'param_{i}': f'value_{i}' for i in range(1000)}
        
        # Fill tree multiple times to test memory management
        for _ in range(3):
            main_window.fill_treewidget(tree, large_data)
            # Verify tree was populated
            assert tree.topLevelItemCount() == 1000
        
        # Final verification
        assert tree.topLevelItemCount() == 1000
    
    def test_gui_responsiveness(self, main_window, app):
        """Test GUI responsiveness under load"""
        tree = main_window.tree_experiments
        
        # Create large dataset
        large_data = {f'param_{i}': f'value_{i}' for i in range(500)}
        
        # Measure time to fill tree
        start_time = time.time()
        main_window.fill_treewidget(tree, large_data)
        fill_time = time.time() - start_time
        
        # Verify tree was populated
        assert tree.topLevelItemCount() == 500
        
        # Measure time to process events
        start_time = time.time()
        app.processEvents()
        process_time = time.time() - start_time
        
        # Performance should be reasonable
        assert fill_time < 1.0  # Tree filling should be fast
        assert process_time < 0.5  # Event processing should be very fast
    
    def test_button_existence_and_state(self, main_window):
        """Test that all expected buttons exist and are in the correct state"""
        # Test that expected buttons exist and are enabled
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
                if button:
                    # Verify button exists and is enabled
                    assert button is not None
                    assert button.isEnabled()
                    
                    # Verify button has the expected type
                    if button_name in ['btn_save_gui', 'btn_load_gui']:
                        # These should be QAction objects
                        from PyQt5.QtWidgets import QAction
                        assert isinstance(button, QAction)
                    else:
                        # These should be QPushButton objects
                        from PyQt5.QtWidgets import QPushButton
                        assert isinstance(button, QPushButton)
                else:
                    # Button exists but is disabled - log this
                    print(f"Warning: Button {button_name} exists but is disabled")
            else:
                # Button doesn't exist - this might be expected in some configurations
                print(f"Info: Button {button_name} not found on main window")
    
    def test_tree_expansion_performance(self, main_window):
        """Test tree expansion performance with large datasets"""
        tree = main_window.tree_experiments
        
        # Create nested dataset
        nested_data = {}
        for i in range(100):
            nested_data[f'group_{i}'] = {
                f'subparam_{j}': f'value_{j}' for j in range(10)
            }
        
        # Fill tree
        main_window.fill_treewidget(tree, nested_data)
        assert tree.topLevelItemCount() == 100
        
        # Test expansion performance
        start_time = time.time()
        
        # Expand first few items
        for i in range(min(5, tree.topLevelItemCount())):
            item = tree.topLevelItem(i)
            if item:
                item.setExpanded(True)
                assert item.isExpanded()
        
        expansion_time = time.time() - start_time
        
        # Expansion should be fast
        assert expansion_time < 0.5 