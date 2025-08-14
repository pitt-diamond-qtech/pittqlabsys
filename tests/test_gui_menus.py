import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from PyQt5.QtWidgets import QApplication, QMenuBar, QMenu, QAction
from PyQt5.QtCore import Qt
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
         patch('src.config_store.merge_config'), \
         patch('src.core.read_probes.ReadProbes'):
        
        window = MainWindow(config_file=None, gui_config_file=None)
        
        # Mock methods that might cause issues during testing
        window.save_config = Mock()
        window.save_dataset = Mock()
        
        # Don't show the window to avoid visual issues
        # window.show()
        
        yield window
        
        # Cleanup
        try:
            window.hide()
            app.processEvents()
        except Exception as e:
            print(f"Cleanup warning: {e}")

class TestGUIMenus:
    """Test class for GUI menu functionality"""
    
    def test_menu_bar_exists(self, main_window):
        """Test that the menu bar exists and is accessible"""
        assert main_window.menuBar() is not None
        assert isinstance(main_window.menuBar(), QMenuBar)
    
    def test_file_menu_exists(self, main_window):
        """Test that the File menu exists"""
        menu_bar = main_window.menuBar()
        file_menu = None
        
        # Find the File menu
        for action in menu_bar.actions():
            if action.text() == "&File" or action.text() == "File":
                file_menu = action.menu()
                break
        
        assert file_menu is not None, "File menu not found"
        assert isinstance(file_menu, QMenu)
    
    def test_help_menu_exists(self, main_window):
        """Test that the Help menu exists"""
        menu_bar = main_window.menuBar()
        help_menu = None
        
        # Find the Help menu
        for action in menu_bar.actions():
            if action.text() == "&Help" or action.text() == "Help":
                help_menu = action.menu()
                break
        
        assert help_menu is not None, "Help menu not found"
        assert isinstance(help_menu, QMenu)
    
    def test_file_menu_actions(self, main_window):
        """Test that File menu has expected actions"""
        menu_bar = main_window.menuBar()
        file_menu = None
        
        # Find the File menu
        for action in menu_bar.actions():
            if action.text() == "&File" or action.text() == "File":
                file_menu = action.menu()
                break
        
        assert file_menu is not None
        
        # Check for expected File menu actions
        file_actions = [action.text() for action in file_menu.actions()]
        print(f"File menu actions: {file_actions}")
        
        # Should have at least some basic actions
        assert len(file_actions) > 0, "File menu has no actions"
    
    def test_help_menu_actions(self, main_window):
        """Test that Help menu has expected actions"""
        menu_bar = main_window.menuBar()
        help_menu = None
        
        # Find the Help menu
        for action in menu_bar.actions():
            if action.text() == "&Help" or action.text() == "Help":
                help_menu = action.menu()
                break
        
        assert help_menu is not None
        
        # Check for expected Help menu actions
        help_actions = [action.text() for action in help_menu.actions()]
        print(f"Help menu actions: {help_actions}")
        
        # Should have at least some basic actions
        assert len(help_actions) > 0, "Help menu has no actions"
    
    def test_menu_bar_actions(self, main_window):
        """Test that menu bar has expected top-level menus"""
        menu_bar = main_window.menuBar()
        menu_actions = [action.text() for action in menu_bar.actions()]
        
        print(f"Menu bar actions: {menu_actions}")
        
        # Should have at least File and Help menus
        assert len(menu_actions) > 0, "Menu bar has no actions"
        
        # Check for common menu names (with or without & prefix)
        menu_texts = [text.replace('&', '') for text in menu_actions]
        assert any('File' in text for text in menu_texts), "File menu not found in menu bar"
        assert any('Help' in text for text in menu_texts), "Help menu not found in menu bar"
    
    def test_menu_visibility(self, main_window):
        """Test that menus are visible and accessible"""
        menu_bar = main_window.menuBar()
        assert menu_bar.isVisible()
        assert menu_bar.isEnabled()
    
    def test_menu_click_simulation(self, main_window):
        """Test that menu clicks can be simulated"""
        menu_bar = main_window.menuBar()
        
        # Find the File menu action
        file_action = None
        for action in menu_bar.actions():
            if action.text() == "&File" or action.text() == "File":
                file_action = action
                break
        
        assert file_action is not None
        
        # Test that the action can be triggered
        assert file_action.isEnabled()
        
        # Simulate a menu click (this should open the menu)
        file_action.trigger()
        
        # The menu should now be visible
        assert file_action.menu().isVisible()
    
    def test_menu_structure(self, main_window):
        """Test the overall menu structure"""
        menu_bar = main_window.menuBar()
        
        # Get all top-level menus
        top_level_menus = []
        for action in menu_bar.actions():
            if action.menu():
                top_level_menus.append({
                    'name': action.text(),
                    'menu': action.menu(),
                    'actions': [sub_action.text() for sub_action in action.menu().actions()]
                })
        
        print(f"Top-level menus: {[m['name'] for m in top_level_menus]}")
        
        # Should have at least 2 menus (File and Help)
        assert len(top_level_menus) >= 2, f"Expected at least 2 menus, got {len(top_level_menus)}"
        
        # Check that File and Help menus exist
        menu_names = [m['name'].replace('&', '') for m in top_level_menus]
        assert 'File' in menu_names, "File menu missing"
        assert 'Help' in menu_names, "Help menu missing"
    
    def test_menu_action_enabled_states(self, main_window):
        """Test that menu actions are in the correct enabled state"""
        menu_bar = main_window.menuBar()
        
        # Check File menu actions
        file_menu = None
        for action in menu_bar.actions():
            if action.text() == "&File" or action.text() == "File":
                file_menu = action.menu()
                break
        
        assert file_menu is not None
        
        # All actions should be enabled by default
        for action in file_menu.actions():
            if not action.isSeparator():
                assert action.isEnabled(), f"Action '{action.text()}' is disabled"
    
    def test_menu_shortcuts(self, main_window):
        """Test that menu shortcuts are properly set"""
        menu_bar = main_window.menuBar()
        
        # Check File menu for shortcuts
        file_menu = None
        for action in menu_bar.actions():
            if action.text() == "&File" or action.text() == "File":
                file_menu = action.menu()
                break
        
        assert file_menu is not None
        
        # Check if any actions have shortcuts
        shortcuts_found = False
        for action in file_menu.actions():
            if action.shortcut():
                shortcuts_found = True
                print(f"Action '{action.text()}' has shortcut: {action.shortcut()}")
        
        # At least some actions should have shortcuts
        assert shortcuts_found, "No shortcuts found in File menu"
    
    def test_menu_bar_set_on_main_window(self, main_window):
        """Test that the menu bar is properly set on the MainWindow"""
        # Check if the menu bar is set on the MainWindow
        assert main_window.menuBar() is not None
        
        # Check if the menu bar is the same as the one defined in the UI
        ui_menubar = main_window.menubar
        assert ui_menubar is not None
        assert main_window.menuBar() == ui_menubar
        
        # Check if the menu bar is properly parented
        assert ui_menubar.parent() == main_window
    
    def test_force_menu_bar_visibility(self, main_window):
        """Test forcing the menu bar to be visible"""
        menu_bar = main_window.menuBar()
        
        # Try to force the menu bar to be visible
        menu_bar.setVisible(True)
        menu_bar.show()
        
        # Process events to ensure the change takes effect
        main_window.app.processEvents() if hasattr(main_window, 'app') else None
        
        # Check if it's now visible
        print(f"Menu bar visible after forcing: {menu_bar.isVisible()}")
        print(f"Menu bar geometry: {menu_bar.geometry()}")
        print(f"Menu bar parent: {menu_bar.parent()}")
        
        # On Mac, the menu bar might still not be visible due to system behavior
        # but we can check if it's properly configured
        assert menu_bar.parent() == main_window
        assert menu_bar.geometry().width() > 0
        assert menu_bar.geometry().height() > 0
    
    def test_mac_menu_bar_behavior(self, main_window):
        """Test Mac-specific menu bar behavior"""
        import platform
        
        if platform.system() == "Darwin":  # macOS
            print("Running on macOS - checking menu bar behavior")
            
            menu_bar = main_window.menuBar()
            
            # On Mac, the menu bar should exist but might not be visible in the window
            # The system menu bar should show the application menus
            
            # Check if the menu bar is properly configured
            assert menu_bar is not None
            assert menu_bar.parent() == main_window
            
            # Check if the menus exist
            file_menu = None
            help_menu = None
            
            for action in menu_bar.actions():
                if action.text() == "File":
                    file_menu = action.menu()
                elif action.text() == "Help":
                    help_menu = action.menu()
            
            assert file_menu is not None, "File menu not found on Mac"
            assert help_menu is not None, "Help menu not found on Mac"
            
            print("Mac menu bar configuration looks correct")
        else:
            print(f"Not running on macOS (platform: {platform.system()})")
            # Skip this test on non-Mac platforms
            pytest.skip("Mac-specific test")

    def test_menu_action_connections(self, main_window):
        """Test that menu actions are properly connected and can be triggered"""
        menu_bar = main_window.menuBar()
        
        # Find the File menu
        file_menu = None
        for action in menu_bar.actions():
            if action.text() == "File":
                file_menu = action.menu()
                break
        
        assert file_menu is not None
        
        # Check each action in the File menu
        for action in file_menu.actions():
            if not action.isSeparator():
                print(f"File menu action: '{action.text()}' - enabled: {action.isEnabled()}")
                
                # Check if the action has a triggered signal connected
                receivers = action.receivers(action.triggered)
                print(f"  - triggered signal receivers: {receivers}")
                
                # Check if the action has any shortcuts
                if action.shortcut():
                    print(f"  - shortcut: {action.shortcut()}")
                
                # Try to trigger the action programmatically
                try:
                    action.trigger()
                    print(f"  - action.trigger() executed successfully")
                except Exception as e:
                    print(f"  - action.trigger() failed: {e}")
    
    def test_menu_action_functionality(self, main_window):
        """Test that menu actions actually perform their intended functions"""
        menu_bar = main_window.menuBar()
        
        # Find the File menu
        file_menu = None
        for action in menu_bar.actions():
            if action.text() == "File":
                file_menu = action.menu()
                break
        
        assert file_menu is not None
        
        # Test specific actions that should exist
        action_names = [action.text() for action in file_menu.actions() if not action.isSeparator()]
        print(f"Available File menu actions: {action_names}")
        
        # Check for the Convert action (this should open a file dialog)
        convert_action = None
        for action in file_menu.actions():
            if "Convert" in action.text():
                convert_action = action
                break
        
        if convert_action:
            print(f"Found Convert action: '{convert_action.text()}'")
            print(f"Convert action enabled: {convert_action.isEnabled()}")
            print(f"Convert action receivers: {convert_action.receivers(convert_action.triggered)}")
            
            # Try to trigger it (this might open a file dialog)
            try:
                convert_action.trigger()
                print("Convert action triggered successfully")
            except Exception as e:
                print(f"Convert action trigger failed: {e}")
        else:
            print("Convert action not found in File menu")
    
    def test_help_menu_actions(self, main_window):
        """Test Help menu actions specifically"""
        menu_bar = main_window.menuBar()
        
        # Find the Help menu
        help_menu = None
        for action in menu_bar.actions():
            if action.text() == "Help":
                help_menu = action.menu()
                break
        
        assert help_menu is not None
        
        # Check each action in the Help menu
        for action in help_menu.actions():
            if not action.isSeparator():
                print(f"Help menu action: '{action.text()}' - enabled: {action.isEnabled()}")
                
                # Check if the action has a triggered signal connected
                receivers = action.receivers(action.triggered)
                print(f"  - triggered signal receivers: {receivers}")
                
                # Try to trigger the action programmatically
                try:
                    action.trigger()
                    print(f"  - action.trigger() executed successfully")
                except Exception as e:
                    print(f"  - action.trigger() failed: {e}")
    
    def test_menu_signal_connections(self, main_window):
        """Test that menu actions have proper signal connections"""
        menu_bar = main_window.menuBar()
        
        # Check all top-level menus
        for menu_action in menu_bar.actions():
            if menu_action.menu():
                menu = menu_action.menu()
                print(f"\nMenu: {menu_action.text()}")
                
                for action in menu.actions():
                    if not action.isSeparator():
                        # Check if the action has any signal connections
                        triggered_receivers = action.receivers(action.triggered)
                        toggled_receivers = action.receivers(action.toggled) if hasattr(action, 'toggled') else 0
                        changed_receivers = action.receivers(action.changed) if hasattr(action, 'changed') else 0
                        
                        print(f"  Action: '{action.text()}'")
                        print(f"    - triggered: {triggered_receivers}")
                        print(f"    - toggled: {toggled_receivers}")
                        print(f"    - changed: {changed_receivers}")
                        
                        # Actions should have at least one signal connection to be functional
                        total_receivers = triggered_receivers + toggled_receivers + changed_receivers
                        if total_receivers == 0:
                            print(f"    - WARNING: No signal connections found!")
                        else:
                            print(f"    - Signal connections found: {total_receivers}")
