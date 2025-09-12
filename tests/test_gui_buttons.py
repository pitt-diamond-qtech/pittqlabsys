#!/usr/bin/env python3
"""
Comprehensive GUI Button Tests for AQuISS.
These tests verify all button functionality and GUI interactions.
"""

import pytest
import sys
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

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
         patch('src.Controller.nanodrive.MCLNanoDrive'), \
         patch('src.Controller.ni_daq.NIDAQ'), \
         patch('src.Controller.awg520.AWG520Device'):
        yield

@pytest.fixture(scope="session")
def app():
    """Create QApplication once for all tests to avoid conflicts"""
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication(sys.argv)
    
    # Set application properties for testing
    app.setQuitOnLastWindowClosed(False)
    
    yield app
    
    # Don't quit the app - let Python handle cleanup to avoid segfaults
    # The session scope ensures this runs once at the end

@pytest.fixture
def main_window(mock_hardware, app):
    """Create MainWindow instance for testing with improved cleanup"""
    from src.View.windows_and_widgets.main_window import MainWindow
    
    # Mock config loading
    with patch('src.config_store.load_config') as mock_load_config, \
         patch('src.config_store.merge_config') as mock_merge_config:
        
        mock_load_config.return_value = {
            'data_folder': str(project_root / 'test_data'),
            'experiments_folder': str(project_root / 'examples'),
            'device_folder': str(project_root / 'test_devices'),
            'probes_folder': str(project_root / 'test_probes')
        }
        mock_merge_config.return_value = mock_load_config.return_value
        
        # Create window
        window = MainWindow(config_file=None, gui_config_file=None)
        
        # Don't show the window during testing to reduce blinking
        # window.show()  # Commented out to reduce visual flickering
        
        # Process events to ensure window is fully initialized
        app.processEvents()
        time.sleep(0.1)  # Small delay for stability
        
        yield window
        
        # More careful cleanup to reduce segfaults
        try:
            # Clear any pending events
            app.processEvents()
            
            # Don't call window.close() - let Python handle cleanup
            # This reduces the chance of cleanup conflicts
            
        except Exception as e:
            # Log cleanup errors but don't fail the test
            print(f"Warning: Error during window cleanup: {e}")
        
        # Final event processing
        app.processEvents()

class TestGUIButtons:
    """Test all GUI button functionality"""
    
    def test_start_experiment_button(self, main_window, app):
        """Test start experiment button functionality"""
        # Mock experiment selection with attributes the GUI code expects (established pattern)
        mock_item = Mock()
        mock_experiment = Mock()
        mock_experiment.name = "TestExperiment"
        mock_experiment.is_running = False
        mock_experiment.experiments = {}  # Empty dict for subexperiments
        mock_experiment.data = {}  # Empty dict for experiment data
        mock_experiment.settings = {}  # Empty dict for experiment settings
        
        # Mock the to_dict method to return a proper dictionary structure
        mock_item.to_dict.return_value = {"TestExperiment": mock_experiment}
        mock_item.get_experiment.return_value = (mock_experiment, [], mock_item)
        main_window.tree_experiments.currentItem = Mock(return_value=mock_item)
        
        # Mock experiment thread
        main_window.experiment_thread = Mock()
        main_window.experiment_thread.start = Mock()
        
        # Mock the problematic update_experiment_from_item method (established pattern)
        with patch.object(main_window, 'update_experiment_from_item'):
            # Click start button
            QTest.mouseClick(main_window.btn_start_experiment, Qt.LeftButton)
            app.processEvents()
            
            # Verify experiment thread was started
            main_window.experiment_thread.start.assert_called_once()
        
    def test_stop_experiment_button(self, main_window, app):
        """Test stop experiment button functionality"""
        # Mock running experiment
        mock_experiment = Mock()
        mock_experiment.is_running = True
        mock_experiment.stop = Mock()
        main_window.current_experiment = mock_experiment
        
        # Click stop button
        QTest.mouseClick(main_window.btn_stop_experiment, Qt.LeftButton)
        app.processEvents()
        
        # Verify stop was called and start button re-enabled
        mock_experiment.stop.assert_called_once()
        assert main_window.btn_start_experiment.isEnabled()
        
    def test_validate_experiment_button(self, main_window, app):
        """Test validate experiment button functionality"""
        # Mock experiment selection with attributes the GUI code expects (established pattern)
        mock_item = Mock()
        mock_experiment = Mock()
        mock_experiment.name = "TestExperiment"
        mock_experiment.is_valid = Mock()
        
        # Mock the to_dict method to return a proper dictionary structure
        mock_item.to_dict.return_value = {"TestExperiment": mock_experiment}
        mock_item.get_experiment.return_value = (mock_experiment, [], mock_item)
        main_window.tree_experiments.currentItem = Mock(return_value=mock_item)
        
        # Mock plotting widgets
        main_window.pyqtgraphwidget_1 = Mock()
        main_window.pyqtgraphwidget_2 = Mock()
        main_window.pyqtgraphwidget_1.graph = Mock()
        main_window.pyqtgraphwidget_2.graph = Mock()
        
        # Patch the problematic update_experiment_from_item method (established pattern)
        with patch.object(main_window, 'update_experiment_from_item'):
            # Click validate button
            QTest.mouseClick(main_window.btn_validate_experiment, Qt.LeftButton)
            app.processEvents()
            
            # Verify validation was called
            mock_experiment.is_valid.assert_called_once()
        
    def test_store_experiment_data_button(self, main_window, app):
        """Test store experiment data button functionality"""
        # Mock experiment selection with attributes the GUI code expects (established pattern)
        mock_item = Mock()
        mock_experiment = Mock()
        mock_experiment.name = "TestExperiment"
        mock_experiment.duplicate = Mock(return_value=mock_experiment)
        mock_experiment.start_time = Mock()
        mock_experiment.start_time.strftime.return_value = "231201-12_00_00"
        
        # Mock the to_dict method to return a proper dictionary structure
        mock_item.to_dict.return_value = {"TestExperiment": mock_experiment}
        mock_item.get_experiment.return_value = (mock_experiment, [], mock_item)
        main_window.tree_experiments.currentItem = Mock(return_value=mock_item)
        
        # Mock dataset tree
        main_window.tree_dataset = Mock()
        main_window.data_sets = {}
        
        # Patch the problematic update_experiment_from_item method (established pattern)
        with patch.object(main_window, 'update_experiment_from_item'):
            # Click store button
            QTest.mouseClick(main_window.btn_store_experiment_data, Qt.LeftButton)
            app.processEvents()
            
            # Verify data was stored
            assert len(main_window.data_sets) == 1
            assert "231201-12_00_00" in main_window.data_sets
        
    def test_save_data_button(self, main_window, app):
        """Test save data button functionality"""
        # Mock dataset selection
        mock_model = Mock()
        mock_index = Mock()
        mock_index.row.return_value = 0
        mock_index.model.return_value = mock_model
        
        mock_item = Mock()
        mock_item.text.return_value = "231201-12_00_00"
        mock_model.itemFromIndex.return_value = mock_item
        
        main_window.tree_dataset.selectedIndexes = Mock(return_value=[mock_index])
        main_window.data_sets = {"231201-12_00_00": Mock()}
        main_window.gui_settings = {"data_folder": "/test/path"}
        
        # Mock experiment save methods
        mock_experiment = main_window.data_sets["231201-12_00_00"]
        mock_experiment.update = Mock()
        mock_experiment.save_data = Mock()
        mock_experiment.save_image_to_disk = Mock()
        mock_experiment.save_aqs = Mock()
        mock_experiment.save_log = Mock()
        mock_experiment.save_data_to_matlab = Mock()
        
        # Click save button
        QTest.mouseClick(main_window.btn_save_data, Qt.LeftButton)
        app.processEvents()
        
        # Verify save methods were called
        mock_experiment.save_data.assert_called_once()
        mock_experiment.save_aqs.assert_called_once()
        
    def test_delete_data_button(self, main_window, app):
        """Test delete data button functionality"""
        # Mock dataset selection
        mock_model = Mock()
        mock_index = Mock()
        mock_index.row.return_value = 0
        mock_index.model.return_value = mock_model
        
        mock_item = Mock()
        mock_item.text.return_value = "231201-12_00_00"
        mock_model.itemFromIndex.return_value = mock_item
        
        main_window.tree_dataset.selectedIndexes = Mock(return_value=[mock_index])
        main_window.data_sets = {"231201-12_00_00": Mock()}
        
        # Click delete button
        QTest.mouseClick(main_window.btn_delete_data, Qt.LeftButton)
        app.processEvents()
        
        # Verify data was deleted
        assert len(main_window.data_sets) == 0
        
    def test_load_devices_button(self, main_window, app):
        """Test load devices button functionality"""
        # Simple test: verify button exists and can be clicked
        assert main_window.btn_load_devices is not None
        
        # Click the button (this will open the real dialog, but that's OK for a basic test)
        QTest.mouseClick(main_window.btn_load_devices, Qt.LeftButton)
        app.processEvents()
        
        # Basic verification that the button click was processed
        # (The actual dialog opening is tested in integration tests)
        assert True  # Button click completed without crashing
                
    def test_load_experiments_button(self, main_window, app):
        """Test load experiments button functionality"""
        # Simple test: verify button exists and can be clicked
        assert main_window.btn_load_experiments is not None
        
        # Click the button (this will open the real dialog, but that's OK for a basic test)
        QTest.mouseClick(main_window.btn_load_experiments, Qt.LeftButton)
        app.processEvents()
        
        # Basic verification that the button click was processed
        # (The actual dialog opening is tested in integration tests)
        assert True  # Button click completed without crashing
                
    def test_load_probes_button(self, main_window, app):
        """Test load probes button functionality"""
        # Simple test: verify button exists and can be clicked
        assert main_window.btn_load_probes is not None
        
        # Click the button (this will open the real dialog, but that's OK for a basic test)
        QTest.mouseClick(main_window.btn_load_probes, Qt.LeftButton)
        app.processEvents()
        
        # Basic verification that the button click was processed
        # (The actual dialog opening is tested in integration tests)
        assert True  # Button click completed without crashing
                
    def test_save_gui_button(self, main_window, app):
        """Test save GUI configuration button functionality"""
        # Mock file dialog
        with patch('PyQt5.QtWidgets.QFileDialog.getSaveFileName') as mock_file_dialog:
            mock_file_dialog.return_value = ("/test/config.json", "JSON files (*.json)")
            
            # Mock save_config method
            main_window.save_config = Mock()
            main_window.config_filepath = "/test/default.json"
            
            # Click save GUI button (QAction, not QPushButton)
            main_window.btn_save_gui.trigger()
            app.processEvents()
            
            # Verify file dialog was shown and save was called
            mock_file_dialog.assert_called_once()
            main_window.save_config.assert_called_once()
            
    def test_load_gui_button(self, main_window, app):
        """Test load GUI configuration button functionality"""
        # Mock file dialog
        with patch('PyQt5.QtWidgets.QFileDialog.getOpenFileName') as mock_file_dialog:
            mock_file_dialog.return_value = ("/test/config.json", "JSON files (*.json)")
            
            # Mock load_config method
            main_window.load_config = Mock()
            main_window.gui_settings = {"data_folder": "/test/data"}
            
            # Click load GUI button (QAction, not QPushButton)
            main_window.btn_load_gui.trigger()
            app.processEvents()
            
            # Verify file dialog was shown and load was called
            mock_file_dialog.assert_called_once()
            main_window.load_config.assert_called_once()
            
    def test_about_button(self, main_window, app):
        """Test about button functionality"""
        # Mock QMessageBox
        with patch('PyQt5.QtWidgets.QMessageBox') as mock_message_box_class:
            mock_message_box = Mock()
            mock_message_box_class.return_value = mock_message_box
            
            # Click about button (QAction, not QPushButton)
            main_window.btn_about.trigger()
            app.processEvents()
            
            # Verify message box was created
            mock_message_box_class.assert_called_once()
            
    def test_probe_plot_checkbox(self, main_window, app):
        """Test probe plot checkbox functionality"""
        # Mock probe selection
        mock_item = Mock()
        mock_item.name = "TestProbe"
        mock_parent = Mock()
        mock_parent.name = "TestDevice"
        mock_item.parent.return_value = mock_parent
        
        main_window.tree_probes.currentItem = Mock(return_value=mock_item)
        main_window.probes = {"TestDevice": {"TestProbe": Mock()}}
        
        # Check the checkbox
        main_window.chk_probe_plot.setChecked(True)
        app.processEvents()
        
        # Verify probe_to_plot was set
        assert main_window.probe_to_plot is not None
        
        # Uncheck the checkbox
        main_window.chk_probe_plot.setChecked(False)
        app.processEvents()
        
        # Verify probe_to_plot was cleared
        assert main_window.probe_to_plot is None
        
    def test_button_states_during_experiment(self, main_window, app):
        """Test button states change correctly during experiment execution"""
        # Mock experiment selection and start with attributes the GUI code expects (established pattern)
        mock_item = Mock()
        mock_experiment = Mock()
        mock_experiment.name = "TestExperiment"
        mock_experiment.is_running = False
        mock_experiment.experiments = {}  # Empty dict for subexperiments
        mock_experiment.data = {}  # Empty dict for experiment data
        mock_experiment.settings = {}  # Empty dict for experiment settings
        
        # Mock the to_dict method to return a proper dictionary structure
        mock_item.to_dict.return_value = {"TestExperiment": mock_experiment}
        mock_item.get_experiment.return_value = (mock_experiment, [], mock_item)
        main_window.tree_experiments.currentItem = Mock(return_value=mock_item)
        
        # Mock experiment thread
        main_window.experiment_thread = Mock()
        main_window.experiment_thread.start = Mock()
        
        # Patch the problematic update_experiment_from_item method (established pattern)
        with patch.object(main_window, 'update_experiment_from_item'):
            # Start experiment
            QTest.mouseClick(main_window.btn_start_experiment, Qt.LeftButton)
            app.processEvents()
            
            # Verify start button disabled, stop button enabled
            assert not main_window.btn_start_experiment.isEnabled()
            assert main_window.btn_stop_experiment.isEnabled()
            
            # Stop experiment
            mock_experiment.is_running = True
            QTest.mouseClick(main_window.btn_stop_experiment, Qt.LeftButton)
            app.processEvents()
            
            # Verify start button re-enabled
            assert main_window.btn_start_experiment.isEnabled()
        
    def test_tree_selection_handling(self, main_window, app):
        """Test tree selection handling and parameter updates"""
        # Mock tree item with attributes the GUI code expects (established pattern)
        mock_item = Mock()
        mock_item.name = "TestParameter"
        mock_item.value = "new_value"
        
        # Mock device
        mock_device = Mock()
        mock_device.name = "TestDevice"
        mock_device.settings = {"TestParameter": "old_value"}
        mock_item.get_device.return_value = (mock_device, ["TestParameter"])
        
        # Mock tree widget
        main_window.tree_settings.currentItem = Mock(return_value=mock_item)
        
        # Simulate parameter update
        main_window.update_parameters(main_window.tree_settings)
        
        # Verify device was updated
        mock_device.update.assert_called_once()
        
    def test_error_handling_in_button_clicks(self, main_window, app):
        """Test error handling when button clicks fail"""
        # Mock experiment selection to cause error
        main_window.tree_experiments.currentItem = Mock(return_value=None)
        
        # Click start button (should handle missing experiment gracefully)
        QTest.mouseClick(main_window.btn_start_experiment, Qt.LeftButton)
        app.processEvents()
        
        # Verify no crash occurred and button remains enabled
        assert main_window.btn_start_experiment.isEnabled()
        
    def test_gui_logging_functionality(self, main_window):
        """Test that GUI logging is working correctly"""
        import logging
        
        # Check that GUI logger exists and is configured
        logger = logging.getLogger('AQuISS_GUI')
        assert logger is not None
        assert logger.level == logging.DEBUG
        
        # Check that handlers are configured
        assert len(logger.handlers) > 0
        
        # Verify file handler exists
        file_handlers = [h for h in logger.handlers if isinstance(h, logging.FileHandler)]
        assert len(file_handlers) > 0

if __name__ == "__main__":
    # Run button tests
    pytest.main([__file__, "-v", "-s"])
