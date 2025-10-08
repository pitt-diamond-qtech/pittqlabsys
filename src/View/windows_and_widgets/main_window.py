# Created by Gurudev Dutt <gdutt@pitt.edu> on 2023-08-17
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
from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.uic import loadUiType
from PyQt5.QtCore import QThread, pyqtSlot, Qt, QTimer, QSignalBlocker
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import pyqtgraph as pg

from src.core import Parameter, Device, Experiment, Probe
from src.core.experiment_iterator import ExperimentIterator
from src.core.read_probes import ReadProbes
from src.View.windows_and_widgets import AQuISSQTreeItem, LoadDialog, LoadDialogProbes, ExportDialog, PyQtgraphWidget, PyQtCoordinatesBar
from src.Model.experiments.select_points import SelectPoints
from src.core.read_write_functions import load_aqs_file
from src.core.helper_functions import get_project_root
from src.config_store import load_config, merge_config, save_config
from pathlib import Path
from src.config_paths import resolve_paths
import os, io, json, webbrowser, datetime, operator
import numpy as np
from collections import deque
from functools import reduce
import logging
import traceback
import sys

# Set up logging for GUI operations
def setup_gui_logging():
    """Set up comprehensive logging for GUI operations"""
    logger = logging.getLogger('AQuISS_GUI')
    logger.setLevel(logging.DEBUG)
    
    # Remove existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create handlers
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    # Create logs directory if it doesn't exist
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    # Create timestamped log file
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = log_dir / f'gui_debug_{timestamp}.log'
    
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    
    # Create formatters and add it to handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s')
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    # Add handlers to the logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    # Log initial setup
    logger.info(f"GUI logging initialized. Debug log: {log_file}")
    
    return logger

# Initialize GUI logger
gui_logger = setup_gui_logging()


# load the basic old_gui either from .ui file or from precompiled .py file
# load your global config.json (adjust the filename/path as needed)
_CONFIG_PATH = get_project_root() / "src" / "config.json"

# this gives you a dict of real Path objects for data_folder, experiments_folder, etc.
paths = resolve_paths(_CONFIG_PATH)

# now you can inspect any one, for example:
print(f"Experiments folder: {paths['experiments_folder']}")
try:
    thisdir = get_project_root()
    #qtdesignerfile = thisdir / 'View/ui_files/main_window.ui'  # this is the .ui file created in QtCreator
    ui_file_path = thisdir / 'src/View/ui_files/main_window.ui'
    Ui_MainWindow, QMainWindow = loadUiType(ui_file_path) # with this we don't have to convert the .ui file into a python file!
except (ImportError, IOError):
    # load precompiled old_gui, to compile run pyuic5 main_window.ui -o gui_compiled_main_window.py
    from ..compiled_ui_files.gui_compiled_main_window import Ui_MainWindow
    from PyQt5.QtWidgets import QMainWindow
    print('Warning: on-the-fly conversion of main_window.ui file failed, loaded .py file instead.\n')


class CustomEventFilter(QtCore.QObject):
    def eventFilter(self, QObject, QEvent):
        if (QEvent.type() == QtCore.QEvent.Wheel):
            QEvent.ignore()
            return True

        return QtWidgets.QWidget.eventFilter(QObject, QEvent)


class MainWindow(QMainWindow, Ui_MainWindow):
    # application_path = os.path.abspath(os.path.join(os.path.expanduser("~"), 'Experiments\\AQuISS_default_save_location'))
    #
    # _DEFAULT_CONFIG = {
    #     "data_folder": os.path.join(application_path, "data"),
    #     "probes_folder": os.path.join(application_path,"probes_auto_generated"),
    #     "device_folder": os.path.join(application_path, "devices_auto_generated"),
    #     "experiments_folder": os.path.join(application_path, "experiments_auto_generated"),
    #     "probes_log_folder": os.path.join(application_path, "aqs_tmp"),
    #     "gui_settings": os.path.join(application_path, "workspace_config.json")
    # }
    #
    #
    # startup_msg = '\n\n\
    # ======================================================\n\
    # =============== Starting AQuISS Python LAB  =============\n\
    # ======================================================\n\n'

    def __init__(self, config_file: str, gui_config_file: str, *args, **kwargs):
        """
        MainWindow(intruments, experiments, probes)
            - intruments: depth 1 dictionary where keys are device names and keys are device classes
            - experiments: depth 1 dictionary where keys are experiment names and keys are experiment classes
            - probes: depth 1 dictionary where to be decided....?

        MainWindow(settings_file)
            - settings_file is the path to a json file that contains all the settings for the old_gui

        Returns:

        """
        super().__init__(*args, **kwargs)
        
        # Initialize recursion guard
        self._updating_parameters = False

        # 1) Resolve your application folders from config_file:
        if config_file is None:
            # default to config.json in src directory
            cfg_path = get_project_root() / "src" / "config.json"
            gui_logger.debug(f"[DEBUG] Constructed cfg_path using get_project_root()/src: {cfg_path}")
        else:
            cfg_path = Path(config_file)
            gui_logger.debug(f"[DEBUG] Using provided config_file: {config_file}")
        
        gui_logger.debug(f"Resolving paths from config file: {cfg_path}")
        self.paths = resolve_paths(cfg_path)
        gui_logger.debug(f"Resolved paths: {self.paths}")
        # now self.paths["data_folder"], self.paths["experiments_folder"], etc.

        # 2) Load any other globals you need:
        self.global_cfg = load_config(cfg_path)

        if gui_config_file:
            gui_cfg_file = Path(gui_config_file)
        else:
            # default to gui_config.json in src directory
            gui_cfg_file = get_project_root() / "src" / "gui_config.json"

        # 3) Load the GUI config (or start fresh if it doesn't exist)
        gui_logger.debug(f"Loading GUI config from: {gui_cfg_file}")
        gui_cfg = load_config(gui_cfg_file)
        gui_logger.debug(f"Loaded GUI config: {gui_cfg}")
        self.config_filepath = gui_cfg_file
        self.gui_settings = gui_cfg.get("gui_settings", {})
        gui_logger.debug(f"GUI settings: {self.gui_settings}")
        self.gui_settings_hidden = gui_cfg.get("experiments_hidden_parameters", {})
        
        # 4) Automatically load default workspace if no specific workspace is loaded
        if not hasattr(self, 'experiments') or not self.experiments:
            gui_logger.info("No experiments loaded, attempting to load default workspace")
            try:
                self.load_config("default_workspace")
                gui_logger.info("Default workspace loaded successfully")
            except Exception as e:
                gui_logger.warning(f"Could not load default workspace: {e}")
                gui_logger.info("Starting with empty workspace")
        
        # Initialize history before any log calls
        self.history = deque(maxlen=500)  # history of executed commands
        self.history_model = None  # Will be initialized in setup_trees()
        
        # 4) Log what we loaded
        if gui_cfg:
            self.log(f"Loaded GUI configuration from {gui_cfg_file}")
        else:
            self.log(f"No GUI config found; will save new settings to {gui_cfg_file}")
        # 5) Build your startup message now that you have real paths:
        self.startup_msg = (
            "\n\n"
            "======================================================\n"
            "=============== Starting AQuISS Python LAB  =============\n"
            "======================================================\n\n"
            f"Data folder:        {self.paths['data_folder']}\n"
            f"Experiments folder: {self.paths['experiments_folder']}\n"
            f"Workspace configs:  {self.paths['workspace_config_dir']}\n"
        )
        
        self.log(self.startup_msg)
        print(self.startup_msg)
        #self.config_filepath = None
        gui_logger.debug("Calling super().__init__()")
        super(MainWindow, self).__init__()
        gui_logger.debug("Calling setupUi()")
        self.setupUi(self)
        gui_logger.debug("setupUi() completed successfully")
        
        # Fix for macOS menu bar issue - ensure menu bar is properly attached to main window
        if hasattr(self, 'menubar'):
            gui_logger.debug("Fixing menu bar attachment for macOS compatibility")
            # Remove the menu bar from centralwidget and attach it to the main window
            if self.menubar.parent() == self.centralwidget:
                self.menubar.setParent(None)
                self.setMenuBar(self.menubar)
                gui_logger.debug("Menu bar reattached to main window")
            else:
                gui_logger.debug(f"Menu bar parent is: {self.menubar.parent()}")
        else:
            gui_logger.warning("No menu bar found to fix!")

        def setup_trees():
            gui_logger.debug("Setting up trees")
            # COMMENT_ME

            # define data container
            # self.history already initialized above
            self.history_model = QtGui.QStandardItemModel(self.list_history)
            self.list_history.setModel(self.history_model)
            self.list_history.show()

            self.tree_experiments.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
            self.tree_probes.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
            self.tree_settings.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)

            self.tree_gui_settings.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
            self.tree_gui_settings.doubleClicked.connect(self.edit_tree_item)

            self.current_experiment = None
            self.previous_data = None
            self.probe_to_plot = None

            # create models for tree structures, the models reflect the data
            self.tree_dataset_model = QtGui.QStandardItemModel()
            self.tree_dataset.setModel(self.tree_dataset_model)
            self.tree_dataset_model.setHorizontalHeaderLabels(['time', 'name (tag)', 'type (experiment)'])

            # create models for tree structures, the models reflect the data
            self.tree_gui_settings_model = QtGui.QStandardItemModel()
            self.tree_gui_settings.setModel(self.tree_gui_settings_model)
            self.tree_gui_settings_model.setHorizontalHeaderLabels(['parameter', 'value'])

            self.tree_experiments.header().setStretchLastSection(True)
        def connect_controls():
            gui_logger.debug("Connecting controls")
            
            # Debug: Check if menu actions exist
            gui_logger.debug(f"actionExport exists: {hasattr(self, 'actionExport')}")
            if hasattr(self, 'actionExport'):
                gui_logger.debug(f"actionExport type: {type(self.actionExport)}")
                gui_logger.debug(f"actionExport text: {self.actionExport.text() if hasattr(self.actionExport, 'text') else 'No text'}")
            else:
                gui_logger.warning("actionExport does not exist!")
            
            gui_logger.debug(f"menuFile exists: {hasattr(self, 'menuFile')}")
            if hasattr(self, 'menuFile'):
                gui_logger.debug(f"menuFile type: {type(self.menuFile)}")
                gui_logger.debug(f"menuFile actions: {[action.text() for action in self.menuFile.actions()] if hasattr(self.menuFile, 'actions') else 'No actions'}")
            else:
                gui_logger.warning("menuFile does not exist!")
            # COMMENT_ME
            # =============================================================
            # ===== LINK WIDGETS TO FUNCTIONS =============================
            # =============================================================

            # link buttons to old_functions
            self.btn_start_experiment.clicked.connect(self.btn_clicked)
            self.btn_stop_experiment.clicked.connect(self.btn_clicked)
            self.btn_skip_subexperiment.clicked.connect(self.btn_clicked)
            self.btn_validate_experiment.clicked.connect(self.btn_clicked)
            # self.btn_plot_experiment.clicked.connect(self.btn_clicked)
            # self.btn_plot_probe.clicked.connect(self.btn_clicked)
            self.btn_store_experiment_data.clicked.connect(self.btn_clicked)
            # self.btn_plot_data.clicked.connect(self.btn_clicked)
            self.btn_save_data.clicked.connect(self.btn_clicked)
            self.btn_delete_data.clicked.connect(self.btn_clicked)
            
            # Connect the new convert button
            if hasattr(self, 'btn_convert_python_files'):
                self.btn_convert_python_files.clicked.connect(self.btn_clicked)


            self.btn_save_gui.triggered.connect(self.btn_clicked)
            self.btn_load_gui.triggered.connect(self.btn_clicked)
            self.btn_about.triggered.connect(self.btn_clicked)
            self.btn_exit.triggered.connect(self.close)

            self.actionSave.triggered.connect(self.btn_clicked)
            self.actionExport.triggered.connect(self.btn_clicked)
            self.actionGo_to_AQuISS_GitHub_page.triggered.connect(self.btn_clicked)
            self.actionSaveWorkspace.triggered.connect(self.btn_clicked)
            self.actionLoadWorkspace.triggered.connect(self.btn_clicked)

            self.btn_load_devices.clicked.connect(self.btn_clicked)
            self.btn_load_experiments.clicked.connect(self.btn_clicked)
            self.btn_load_probes.clicked.connect(self.btn_clicked)

            # Helper function to make only column 1 editable
            def onExperimentParamClick(item, column):
                tree = item.treeWidget()
                if column == 1 and not isinstance(item.value, (Experiment, Device)) and (hasattr(item, 'is_point') and not item.is_point()):
                    # self.tree_experiments.editItem(item, column)
                    tree.editItem(item, column)

            # tree structures
            self.tree_experiments.itemClicked.connect(
                lambda: onExperimentParamClick(self.tree_experiments.currentItem(), self.tree_experiments.currentColumn()))
            # Connect to itemChanged signal with proper item/column parameters
            self.tree_experiments.itemChanged.connect(
                lambda item, col: self.update_parameters(self.tree_experiments, item, col)
            )
            self.tree_experiments.itemClicked.connect(self.btn_clicked)
            # self.tree_experiments.installEventFilter(self)
            # QtWidgets.QTreeWidget.installEventFilter(self)


            self.tabWidget.currentChanged.connect(lambda : self.switch_tab())
            self.tree_dataset.clicked.connect(lambda: self.btn_clicked())

            self.tree_settings.itemClicked.connect(
                lambda: onExperimentParamClick(self.tree_settings.currentItem(), self.tree_settings.currentColumn()))
            self.tree_settings.itemChanged.connect(
                lambda item, col: self.update_parameters(self.tree_settings, item, col)
            )
            self.tree_settings.itemExpanded.connect(lambda: self.refresh_devices())


            # set the log_filename when checking loggin
            self.chk_probe_log.toggled.connect(lambda: self.set_probe_file_name(self.chk_probe_log.isChecked()))
            self.chk_probe_plot.toggled.connect(self.btn_clicked)

            self.chk_show_all.toggled.connect(self._show_hide_parameter)

        self.create_figures()


        # create a "delegate" --- an editor that uses our new Editor Factory when creating editors,
        # and use that for tree_experiments
        # needed to avoid rounding of numbers
        delegate = QtWidgets.QStyledItemDelegate()
        new_factory = CustomEditorFactory()
        delegate.setItemEditorFactory(new_factory)
        self.tree_experiments.setItemDelegate(delegate)
        gui_logger.debug("About to call setup_trees()")
        setup_trees()
        gui_logger.debug("setup_trees() completed, about to call connect_controls()")
        
        # Install NumberClampDelegate for column 1 (Value column) on both trees
        from src.View.windows_and_widgets.widgets import NumberClampDelegate
        self.tree_settings.setItemDelegateForColumn(1, NumberClampDelegate(self.tree_settings))
        self.tree_experiments.setItemDelegateForColumn(1, NumberClampDelegate(self.tree_experiments))
        gui_logger.debug("Installed NumberClampDelegate for column 1 on both trees")
        
        connect_controls()
        gui_logger.debug("connect_controls() completed")

        # if filepath is None:
        #     path_to_config = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, 'save_config.json'))
        #     if os.path.isfile(path_to_config) and os.access(path_to_config, os.R_OK):
        #         print('path_to_config', path_to_config)
        #         with open(path_to_config) as f:
        #             config_data = json.load(f)
        #         if 'last_save_path' in config_data.keys():
        #             self.config_filepath = config_data['last_save_path']
        #             self.log('Checking for previous save of GUI here: {0}'.format(self.config_filepath))
        #     else:
        #         self.log('Starting with blank GUI; configuration files will be saved here: {0}'.format(self._DEFAULT_CONFIG["gui_settings"]))

        # elif os.path.isfile(filepath) and os.access(filepath, os.R_OK):
        #     self.config_filepath = filepath

        # elif not os.path.isfile(filepath):
        #     self.log('Could not find file given to open --- starting with a blank GUI')

        self.devices = {}
        self.experiments = {}
        self.probes = {}
        self.gui_settings = {'experiments_folder': '', 'data_folder': ''}
        self.gui_settings_hidden = {'experiments_source_folder': ''}
        
        # Load devices from config file
        try:
            from src.core.device_config import load_devices_from_config
            gui_logger.info("Loading devices from config file...")
            loaded_devices, failed_devices = load_devices_from_config(cfg_path)
            
            if loaded_devices:
                self.devices.update(loaded_devices)
                gui_logger.info(f"Successfully loaded {len(loaded_devices)} devices from config")
                for device_name in loaded_devices.keys():
                    gui_logger.info(f"  [SUCCESS] Loaded device: {device_name}")
            
            if failed_devices:
                gui_logger.warning(f"Failed to load {len(failed_devices)} devices from config")
                for device_name, error in failed_devices.items():
                    gui_logger.warning(f"  [ERROR] Failed to load {device_name}: {error}")
                    
        except Exception as e:
            gui_logger.warning(f"Could not load devices from config: {e}")
            gui_logger.info("Starting with empty device list")

        # Refresh the devices tree to show loaded devices
        self.refresh_tree(self.tree_settings, self.devices)
        gui_logger.info(f"Refreshed devices tree with {len(self.devices)} devices")

        #self.load_config(self.config_filepath)

        self.data_sets = {}  # todo: load datasets from tmp folder
        self.read_probes = ReadProbes(self.probes)
        self.tabWidget.setCurrentIndex(0) # always show the experiment tab

        # == create a thread for the experiments ==
        self.experiment_thread = QThread()
        self._last_progress_update = None # used to keep track of status updates, to block updates when they occur to often

        self.chk_show_all.setChecked(True)
        self.actionSave.setShortcut(QtGui.QKeySequence.Save)
        self.actionExport.setShortcut(self.tr('Ctrl+E'))
        self.list_history.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)

        gui_logger.debug("__init__ method completed successfully")
        # if self.config_filepath is None:
        #     self.config_filepath = os.path.join(self._DEFAULT_CONFIG["gui_settings"], 'gui.aqs')

    def closeEvent(self, event):
        """
        things to be done when gui closes, like save the settings
        """

        # Save config if gui_settings key exists, otherwise save to default location
        if 'gui_settings' in self.gui_settings:
            self.save_config(self.gui_settings['gui_settings'])
        else:
            # Save to default location
            default_config_path = get_project_root() / "src" / "gui_config.json"
            self.save_config(str(default_config_path))
        
        self.experiment_thread.quit()
        self.read_probes.quit()
        event.accept()

        print('\n\n======================================================')
        print('================= Closing AQuISS Python LAB =============')
        print('======================================================\n\n')

    def eventFilter(self, object, event):
        """

        TEMPORARY / UNDER DEVELOPMENT

        THIS IS TO ALLOW COPYING OF PARAMETERS VIA DRAP AND DROP

        Args:
            object:
            event:

        Returns:

        """
        if (object is self.tree_experiments):
            # print('XXXXXXX = event in experiments', event.type(),
            #       QtCore.QEvent.DragEnter, QtCore.QEvent.DragMove, QtCore.QEvent.DragLeave)
            if (event.type() == QtCore.QEvent.ChildAdded):
                item = self.tree_experiments.selectedItems()[0]
                if not isinstance(item.value, Experiment):
                    print('ONLY EXPERIMENTS CAN BE DRAGGED')
                    return False
                print(('XXX ChildAdded', self.tree_experiments.selectedItems()[0].name))



                # if event.mimeData().hasUrls():
                #     event.accept()  # must accept the dragEnterEvent or else the dropEvent can't occur !!!
                #     print "accept"
                # else:
                #     event.ignore()
                #     print "ignore"
            if (event.type() == QtCore.QEvent.ChildRemoved):
                print(('XXX ChildRemoved', self.tree_experiments.selectedItems()[0].name))
            if (event.type() == QtCore.QEvent.Drop):
                print('XXX Drop')
                # if event.mimeData().hasUrls():  # if file or link is dropped
                #     urlcount = len(event.mimeData().urls())  # count number of drops
                #     url = event.mimeData().urls()[0]  # get first url
                #     object.setText(url.toString())  # assign first url to editline
                #     # event.accept()  # doesnt appear to be needed
            return False  # lets the event continue to the edit

        return False


    def set_probe_file_name(self, checked):
        """
        sets the filename to which the probe logging function will write
        Args:
            checked: boolean (True: opens file) (False: closes file)
        """
        if checked:
            file_name = os.path.join(self.gui_settings['probes_log_folder'], '{:s}_probes.csv'.format(datetime.datetime.now().strftime('%y%m%d-%H_%M_%S')))
            if os.path.isfile(file_name) == False:
                self.probe_file = open(file_name, 'a')
                new_values = self.read_probes.probes_values
                header = ','.join(list(np.array([['{:s} ({:s})'.format(p, instr) for p in list(p_dict.keys())] for instr, p_dict in new_values.items()]).flatten()))
                self.probe_file.write('{:s}\n'.format(header))
        else:
            self.probe_file.close()



    def switch_tab(self):
        """
        takes care of the action that happen when switching between tabs
        e.g. activates and deactives probes
        """
        current_tab = str(self.tabWidget.tabText(self.tabWidget.currentIndex()))
        if self.current_experiment is None:
            if current_tab == 'Probes':
                self.read_probes.start()
                self.read_probes.updateProgress.connect(self.update_probes)
            else:
                try:
                    self.read_probes.updateProgress.disconnect()
                    self.read_probes.quit()
                except TypeError:
                    pass

            if current_tab == 'Devices':
                self.refresh_devices()

        else:
            self.log('updating probes / devices disabled while experiment is running!')

    def refresh_devices(self):
        """
        if self.tree_settings has been expanded, ask devices for their actual values
        """
        def list_access_nested_dict(dict, somelist):
            """
            Allows one to use a list to access a nested dictionary, for example:
            listAccessNestedDict({'a': {'b': 1}}, ['a', 'b']) returns 1
            Args:
                dict:
                somelist:

            Returns:

            """
            return reduce(operator.getitem, somelist, dict)

        def update(item):
            if item.isExpanded():
                for index in range(item.childCount()):
                    child = item.child(index)

                    if child.childCount() == 0:
                        device, path_to_device = child.get_device()
                        path_to_device.reverse()
                        try: #check if item is in probes
                            value = device.read_probes(path_to_device[-1])
                        except AssertionError: #if item not in probes, get value from settings instead
                            value = list_access_nested_dict(device.settings, path_to_device)
                        child.value = value
                    else:
                        update(child)

        #need to block signals during update so that tree.itemChanged doesn't fire and the gui doesn't try to
        #reupdate the devices to their current value
        self.tree_settings.blockSignals(True)

        for index in range(self.tree_settings.topLevelItemCount()):
            device = self.tree_settings.topLevelItem(index)
            update(device)

        self.tree_settings.blockSignals(False)

    def plot_clicked(self, mouse_event):
        """
        gets activated when the user clicks on a plot
        Args:
            mouse_event:
        """
        # get viewbox and mouse coordinates from primary PlotItem
        viewbox = self.pyqtgraphwidget_1.graph.getItem(row=0, col=0).vb
        mouse_point = viewbox.mapSceneToView(mouse_event.scenePos())

        if (isinstance(self.current_experiment, SelectPoints) and self.current_experiment.is_running):
            #if running the SelectPoints experiment triggers function to plot and save NV locations
            if mouse_event.button() == Qt.LeftButton:
                pt = np.array([mouse_point.x(), mouse_point.y()])
                self.current_experiment.toggle_NV(pt)
                self.current_experiment.plot([self.pyqtgraphwidget_1.graph])

        if isinstance(self.current_experiment,ExperimentIterator) and self.current_experiment.is_running and isinstance(self.current_experiment._current_subexperiment_stage['current_subexperiment'], SelectPoints):
            #if running an ExperimentIterator and the current subexperiment is SelectPoints triggers function to plot and save NV locations
            select_points_instance = self.current_experiment._current_subexperiment_stage['current_subexperiment']
            if mouse_event.button() == Qt.LeftButton:
                pt = np.array([mouse_point.x(), mouse_point.y()])
                select_points_instance.toggle_NV(pt)
                select_points_instance.plot([self.pyqtgraphwidget_1.graph])

        item = self.tree_experiments.currentItem()

        if item is not None:
            if hasattr(item, 'is_point') and item.is_point():
               # item_x = item.child(1)
                item_x = item.child(0)
                if mouse_point.x() is not None:
                    self.tree_experiments.setCurrentItem(item_x)
                    item_x.value = float(mouse_point.x())
                    item_x.setText(1, '{:0.3f}'.format(float(mouse_point.x())))
               # item_y = item.child(0)
                item_y = item.child(1)
                if mouse_point.y() is not None:
                    self.tree_experiments.setCurrentItem(item_y)
                    item_y.value = float(mouse_point.y())
                    item_y.setText(1, '{:0.3f}'.format(float(mouse_point.y())))

                # focus back on item
                self.tree_experiments.setCurrentItem(item)
            else:
                if item.parent() is not None:
                    if hasattr(item.parent(), 'is_point') and item.parent().is_point():
                        if item == item.parent().child(1):
                            if mouse_point.x() is not None:
                                item.setData(1, 2, float(mouse_point.x()))
                        if item == item.parent().child(0):
                            if mouse_point.y() is not None:
                                item.setData(1, 2, float(mouse_point.y()))

    def get_time(self):
        """
        Returns: the current time as a formated string
        """
        return datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H:%M:%S')

    def log(self, msg):
        """
        log function
        Args:
            msg: the text message to be logged
        """

        time = self.get_time()

        msg = "{:s}\t {:s}".format(time, msg)

        self.history.append(msg)
        if self.history_model is not None:
            self.history_model.insertRow(0, QtGui.QStandardItem(msg))

    def create_figures(self):

        try:
            self.horizontalLayout_14.removeWidget(self.pyqtgraphwidget_1)
            self.pyqtgraphwidget_1.close()
        except AttributeError:
            pass
        try:
            self.horizontalLayout_15.removeWidget(self.pyqtgraphwidget_2)
            self.pyqtgraphwidget_2.close()
        except AttributeError:
            pass

        #adds 2 graphics layout widgets. _1 is top layout and _2 is bottom layout
        self.pyqtgraphwidget_2 = PyQtgraphWidget(self.plot_2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pyqtgraphwidget_2.sizePolicy().hasHeightForWidth())
        self.pyqtgraphwidget_2.setSizePolicy(sizePolicy)
        self.pyqtgraphwidget_2.setMinimumSize(QtCore.QSize(200, 200))
        self.pyqtgraphwidget_2.setObjectName("pyqtgraphwidget_2")
        self.horizontalLayout_16.addWidget(self.pyqtgraphwidget_2)
        self.pyqtgraphwidget_1 = PyQtgraphWidget(parent=self.plot_1)
        self.pyqtgraphwidget_1.setMinimumSize(QtCore.QSize(200, 200))
        self.pyqtgraphwidget_1.setObjectName("pyqtgraphwidget_1")
        self.horizontalLayout_15.addWidget(self.pyqtgraphwidget_1)

        #adds 2 coordinate bars (1 for each graphics widget)
        self.cordbar_2 = PyQtCoordinatesBar(self.pyqtgraphwidget_2.get_graph)
        self.cordbar_1 = PyQtCoordinatesBar(self.pyqtgraphwidget_1.get_graph)
        self.horizontalLayout_9.addWidget(self.cordbar_2)
        self.horizontalLayout_14.addWidget(self.cordbar_1)

        sizePolicy.setHeightForWidth(self.cordbar_2.sizePolicy().hasHeightForWidth())
        self.cordbar_2.setSizePolicy(sizePolicy)
        self.cordbar_2 .setMinimumSize(QtCore.QSize(200, 50))
        self.cordbar_2 .setObjectName('cordinatebar_2')

        sizePolicy.setHeightForWidth(self.cordbar_1.sizePolicy().hasHeightForWidth())
        self.cordbar_1.setSizePolicy(sizePolicy)
        self.cordbar_1.setMinimumSize(QtCore.QSize(200, 50))
        self.cordbar_1.setObjectName('cordinatebar_1')

        # connects plots so when clicked on the plot_clicked method triggers
        self.pyqtgraphwidget_1.graph.scene().sigMouseClicked.connect(self.plot_clicked)
        self.pyqtgraphwidget_2.graph.scene().sigMouseClicked.connect(self.plot_clicked)


    def load_experiments(self):
        """
        opens file dialog to load experiments into gui
        """
        gui_logger.info("Starting load_experiments operation")
        try:
            # update experiments so that current settings do not get lost
            gui_logger.debug(f"Updating {self.tree_experiments.topLevelItemCount()} existing experiment items")
            for index in range(self.tree_experiments.topLevelItemCount()):
                experiment_item = self.tree_experiments.topLevelItem(index)
                gui_logger.debug(f"Processing experiment item {index}: {type(experiment_item)}")
                # Only update if the item has the get_experiment method (AQuISSQTreeItem)
                if hasattr(experiment_item, 'get_experiment'):
                    gui_logger.debug(f"Updating experiment item {index}")
                    self.update_experiment_from_item(experiment_item)
                else:
                    gui_logger.warning(f"Experiment item {index} missing get_experiment method: {type(experiment_item)}")

            gui_logger.info("Opening LoadDialog for experiments")
            dialog = LoadDialog(elements_type="experiments", elements_old=self.experiments,
                                filename=self.gui_settings['experiments_folder'])
            if dialog.exec_():
                gui_logger.info("LoadDialog completed, processing selected experiments")
                # Don't modify the experiments_folder from the dialog - it should be set by user configuration
                experiments = dialog.get_values()
                gui_logger.debug(f"Dialog returned {len(experiments)} experiments: {list(experiments.keys())}")
                
                added_experiments = set(experiments.keys()) - set(self.experiments.keys())
                removed_experiments = set(self.experiments.keys()) - set(experiments.keys())
                gui_logger.info(f"Added: {len(added_experiments)}, Removed: {len(removed_experiments)}")

                if 'data_folder' in list(self.gui_settings.keys()) and os.path.exists(self.gui_settings['data_folder']):
                    data_folder_name = self.gui_settings['data_folder']
                else:
                    data_folder_name = None

                # create instances of new devices/experiments
                gui_logger.info("Loading and appending new experiments")
                self.experiments, loaded_failed, self.devices = Experiment.load_and_append(
                    experiment_dict={name: experiments[name] for name in added_experiments},
                    experiments=self.experiments,
                    devices=self.devices,
                    log_function=self.log,
                    data_path=data_folder_name,
                    raise_errors=False)

                # delete instances of new devices/experiments that have been deselected
                for name in removed_experiments:
                    gui_logger.debug(f"Removing experiment: {name}")
                    del self.experiments[name]
                    
                gui_logger.info("load_experiments operation completed successfully")
            else:
                gui_logger.info("LoadDialog was cancelled")
                
        except Exception as e:
            gui_logger.error(f"Error in load_experiments: {str(e)}")
            gui_logger.error(f"Traceback: {traceback.format_exc()}")
            # Show error to user
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to load experiments: {str(e)}")

    def convert_python_files(self):
        """
        opens export dialog to convert Python files to AQS format
        """
        gui_logger.info("Convert Python Files button clicked - opening export dialog")
        
        try:
            gui_logger.debug(f"gui_settings: {self.gui_settings}")
            gui_logger.debug(f"gui_settings_hidden: {self.gui_settings_hidden}")
            
            # Pass existing devices to enable real hardware usage during conversion
            export_dialog = ExportDialog(existing_devices=self.devices)
            gui_logger.debug("ExportDialog created successfully with existing devices")
            
            # Check for mock devices and warn user
            try:
                from src.tools.export_default import detect_mock_devices
                mock_devices, warning_message = detect_mock_devices()
                
                if mock_devices:
                    gui_logger.warning(f"Mock devices detected: {mock_devices}")
                    QtWidgets.QMessageBox.warning(
                        self,
                        "Mock Devices Detected",
                        f"⚠️  WARNING: Mock devices detected during conversion!\n\n"
                        f"Mock devices found: {', '.join(mock_devices)}\n\n"
                        "This conversion may not reflect real hardware capabilities.\n"
                        "Check device connections and try again for accurate results.",
                        QtWidgets.QMessageBox.Ok
                    )
                else:
                    gui_logger.info("All devices appear to be real hardware implementations")
                    
            except Exception as e:
                gui_logger.warning(f"Could not check for mock devices: {e}")
                # Continue with conversion even if we can't check device status
            
            if 'experiments_folder' in self.gui_settings and self.gui_settings['experiments_folder']:
                export_dialog.target_path.setText(self.gui_settings['experiments_folder'])
                gui_logger.debug(f"Set target path to: {self.gui_settings['experiments_folder']}")
            else:
                # Use resolved paths instead of empty gui_settings
                export_dialog.target_path.setText(str(self.paths['experiments_folder']))
                gui_logger.debug(f"Set target path to resolved path: {self.paths['experiments_folder']}")
                
            if 'experiments_source_folder' in self.gui_settings_hidden:
                export_dialog.source_path.setText(self.gui_settings_hidden['experiments_source_folder'])
                gui_logger.debug(f"Set source path to: {self.gui_settings_hidden['experiments_source_folder']}")
            else:
                # Set default source path to src/Controller folder for devices
                default_source_path = Path(__file__).parent.parent.parent / "Controller"
                if default_source_path.exists():
                    export_dialog.source_path.setText(str(default_source_path))
                    gui_logger.debug(f"Set default source path to: {default_source_path}")
                else:
                    gui_logger.warning(f"Default source path does not exist: {default_source_path}")
                
            if export_dialog.source_path.text():
                gui_logger.debug("Calling reset_available")
                export_dialog.reset_available(export_dialog.source_path.text())
            
            gui_logger.debug("About to exec_() the export dialog")
            # exec_() blocks while export dialog is used, subsequent code will run on dialog closing
            export_dialog.exec_()
            gui_logger.debug("Export dialog closed")
            
            self.gui_settings.update({'experiments_folder': export_dialog.target_path.text()})
            self.gui_settings_hidden.update({'experiments_source_folder': export_dialog.source_path.text()})
            
            gui_logger.info("Convert Python Files dialog completed successfully")
            
        except Exception as e:
            gui_logger.error(f"Error in convert_python_files: {str(e)}")
            gui_logger.error(f"Traceback: {traceback.format_exc()}")
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to open export dialog: {str(e)}")

    def btn_clicked(self):
        """
        slot to which connect buttons
        """
        sender = self.sender()
        self.probe_to_plot = None
        
        # Log the button click for debugging
        if sender:
            sender_name = sender.objectName() if hasattr(sender, 'objectName') else str(sender)
            gui_logger.info(f"Button clicked: {sender_name} (type: {type(sender).__name__})")
        else:
            gui_logger.warning("Button clicked but sender is None")

        def start_button():
            """
            starts the selected experiment
            """
            gui_logger.info("Start button clicked - attempting to start experiment")
            item = self.tree_experiments.currentItem()

            # BROKEN 20170109: repeatedly erases updates to gui
            # self.expanded_items = []
            # for index in range(self.tree_experiments.topLevelItemCount()):
            #     someitem = self.tree_experiments.topLevelItem(index)
            #     if someitem.isExpanded():
            #         self.expanded_items.append(someitem.name)
            self.experiment_start_time = datetime.datetime.now()

            if item is not None:
                # get experiment and update settings from tree
                self.running_item = item
                experiment, path_to_experiment, experiment_item = item.get_experiment()
                
                gui_logger.info(f"Starting experiment: {experiment.name}")

                self.update_experiment_from_item(experiment_item)

                self.log('starting {:s}'.format(experiment.name))

                # put experiment onto experiment thread
                print('================================================')
                print(('===== starting {:s}'.format(experiment.name)))
                print('================================================')
                experiment_thread = self.experiment_thread

                def move_to_worker_thread(experiment):
                    experiment.moveToThread(experiment_thread)

                    # move also the subexperiment to the worker thread
                    for subexperiment in list(experiment.experiments.values()):
                        move_to_worker_thread(subexperiment)

                move_to_worker_thread(experiment)

                experiment.updateProgress.connect(self.update_status) # connect update signal of experiment to update slot of gui
                experiment_thread.started.connect(experiment.run) # causes the experiment to start upon starting the thread
                experiment.finished.connect(experiment_thread.quit)  # clean up. quit thread after experiment is finished
                experiment.finished.connect(self.experiment_finished) # connect finished signal of experiment to finished slot of gui

                # for some experiments we want to inherit data from the previous experiment (for example NV locations from SelectPoints to use in say ODMR)
                # to use you want an inherit data parameter in the experiment settings. Could be expanded depending on use cases
                if self.previous_data is not None:
                    if 'inherit_data' in experiment.settings and experiment.settings['inherit_data']:
                        common_keys = experiment.data.keys() & self.previous_data.keys()
                        gui_logger.debug(f"Inheriting data keys: {common_keys}")
                        #print('common keys',common_keys)
                        for key in common_keys:
                            experiment.data[key] = self.previous_data[key]

                # start thread, i.e. experiment
                experiment_thread.start()
                gui_logger.info(f"Experiment thread started for {experiment.name}")

                self.current_experiment = experiment
                self.btn_start_experiment.setEnabled(False)
                # self.tabWidget.setEnabled(False)

                if isinstance(self.current_experiment, ExperimentIterator):
                    self.btn_skip_subexperiment.setEnabled(True)
                    gui_logger.debug("Skip subexperiment button enabled (ExperimentIterator detected)")

            else:
                gui_logger.warning("User tried to run an experiment without one selected")
                self.log('User tried to run a experiment without one selected.')

        def stop_button():
            """
            stops the current experiment
            """
            gui_logger.info("Stop button clicked - attempting to stop experiment")
            if self.current_experiment is not None and self.current_experiment.is_running:
                gui_logger.info(f"Stopping experiment: {self.current_experiment.name}")
                self.current_experiment.stop()
            else:
                gui_logger.warning("User clicked stop, but there isn't anything running")
                self.log('User clicked stop, but there isn\'t anything running...this is awkward. Re-enabling start button anyway.')
            self.btn_start_experiment.setEnabled(True)
            gui_logger.debug("Start button re-enabled")

        def skip_button():
            """
            Skips to the next experiment if the current experiment is a Iterator experiment
            """
            gui_logger.info("Skip button clicked - attempting to skip to next subexperiment")
            if self.current_experiment is not None and self.current_experiment.is_running and isinstance(self.current_experiment,
                                                                                                 ExperimentIterator):
                gui_logger.info(f"Skipping to next subexperiment in {self.current_experiment.name}")
                self.current_experiment.skip_next()
            else:
                gui_logger.warning("User clicked skip, but there isn't a iterator experiment running")
                self.log('User clicked skip, but there isn\'t a iterator experiment running...this is awkward.')

        def validate_button():
            """
            validates the selected experiment
            """
            gui_logger.info("Validate button clicked - attempting to validate experiment")
            item = self.tree_experiments.currentItem()

            if item is not None:
                experiment, path_to_experiment, experiment_item = item.get_experiment()
                gui_logger.info(f"Validating experiment: {experiment.name}")
                self.update_experiment_from_item(experiment_item)
                experiment.is_valid()
                experiment.plot_validate([self.pyqtgraphwidget_1.graph, self.pyqtgraphwidget_2.graph])
                #i dont think these two lines are necessary since pyqtgraph auto updates when plot_validate is called
                self.pyqtgraphwidget_1.update()
                self.pyqtgraphwidget_2.update()
                gui_logger.info(f"Experiment {experiment.name} validation completed")
            else:
                gui_logger.warning("Validate button clicked but no experiment selected")

        def store_experiment_data():
            """
            updates the internal self.data_sets with selected experiment and updates tree self.fill_dataset_tree
            """
            gui_logger.info("Store experiment data button clicked")
            item = self.tree_experiments.currentItem()
            gui_logger.debug(f"Selected item: {item}")
            
            if item is not None:
                experiment, path_to_experiment, _ = item.get_experiment()
                gui_logger.debug(f"Experiment from item: {experiment}")
                gui_logger.debug(f"Path to experiment: {path_to_experiment}")
                
                if experiment is not None:
                    try:
                        experiment_copy = experiment.duplicate()
                        time_tag = experiment.start_time.strftime('%y%m%d-%H_%M_%S')
                        
                        gui_logger.info(f"Storing experiment {experiment.name} with time tag {time_tag}")
                        self.data_sets.update({time_tag : experiment_copy})
                        self.fill_dataset_tree(self.tree_dataset, self.data_sets)
                        gui_logger.info(f"Experiment data stored successfully. Total datasets: {len(self.data_sets)}")
                    except Exception as e:
                        gui_logger.error(f"Error storing experiment: {e}")
                else:
                    gui_logger.warning("Store button clicked but selected item does not contain an experiment")
            else:
                gui_logger.warning("Store button clicked but no item selected in experiments tree")

        def save_data():
            """"
            saves the selected experiment (where is contained in the experiment itself)
            """
            gui_logger.info("Save data button clicked")
            indecies = self.tree_dataset.selectedIndexes()
            try:
                model = indecies[0].model()
            except IndexError:
                gui_logger.warning("No experiment selected for saving")
                self.log('No experiment selected.')
                return
                
            rows = list(set([index.row()for index in indecies]))
            gui_logger.info(f"Saving {len(rows)} selected experiments")

            for row in rows:
                time_tag = str(model.itemFromIndex(model.index(row, 0)).text())
                name_tag = str(model.itemFromIndex(model.index(row, 1)).text())
                path = self.gui_settings['data_folder']
                experiment = self.data_sets[time_tag]
                
                gui_logger.info(f"Saving experiment {name_tag} (time: {time_tag}) to {path}")
                experiment.update({'tag' : name_tag, 'path': path})
                experiment.save_data()
                experiment.save_image_to_disk()
                experiment.save_aqs()
                experiment.save_log()
                experiment.save_data_to_matlab()
                gui_logger.info(f"Experiment {name_tag} saved successfully")

        def delete_data():
            """
            deletes the data from the dataset
            Returns:
            """
            gui_logger.info("Delete data button clicked")
            indecies = self.tree_dataset.selectedIndexes()
            try:
                model = indecies[0].model()
            except IndexError:
                gui_logger.warning("No experiment selected for deletion")
                return
                
            rows = list(set([index.row()for index in indecies]))
            gui_logger.info(f"Deleting {len(rows)} selected experiments")

            for row in rows:
                time_tag = str(model.itemFromIndex(model.index(row, 0)).text())
                gui_logger.info(f"Deleting experiment with time tag: {time_tag}")
                del self.data_sets[time_tag]
                model.removeRows(row,1)
                
            gui_logger.info(f"Data deletion completed. Remaining datasets: {len(self.data_sets)}")



        def load_probes():
            """
            opens file dialog to load probes into gui
            """
            gui_logger.info("Load probes button clicked - opening probe selection dialog")
            
            # if the probe has never been started it can not be disconnected so we catch that error
            try:
                gui_logger.debug("Disconnecting existing probe update progress signal")
                self.read_probes.updateProgress.disconnect()
                self.read_probes.quit()
                # self.read_probes.stop()
            except RuntimeError:
                gui_logger.debug("No existing probe update progress signal to disconnect")
                pass
                
            dialog = LoadDialogProbes(probes_old=self.probes, filename=self.gui_settings['probes_folder'])
            if dialog.exec_():
                gui_logger.info("Probe selection dialog accepted")
                # Don't modify the probes_folder from the dialog - it should be set by user configuration
                probes = dialog.get_values()
                added_devices = list(set(probes.keys()) - set(self.probes.keys()))
                removed_devices = list(set(self.probes.keys()) - set(probes.keys()))
                
                gui_logger.info(f"Probe changes - Added: {added_devices}, Removed: {removed_devices}")
                
                # create instances of new probes
                self.probes, loaded_failed, self.devices = Probe.load_and_append(
                    probe_dict=probes,
                    probes={},
                    devices=self.devices)
                    
                if not loaded_failed:
                    gui_logger.warning(f"Following probes could not be loaded: {loaded_failed}")
                    print(('WARNING following probes could not be loaded', loaded_failed, len(loaded_failed)))

                # restart the readprobes thread
                gui_logger.debug("Restarting read probes thread")
                del self.read_probes
                self.read_probes = ReadProbes(self.probes)
                self.read_probes.start()
                self.tree_probes.clear() # clear tree because the probe might have changed
                self.read_probes.updateProgress.connect(self.update_probes)
                self.tree_probes.expandAll()
                gui_logger.info(f"Probes loaded successfully. Total probes: {len(self.probes)}")
            else:
                gui_logger.info("Probe selection dialog cancelled")

        def load_devices():
            """
            opens file dialog to load devices into gui
            """
            gui_logger.info("Load devices button clicked - opening device selection dialog")
            
            if 'device_folder' in self.gui_settings:
                dialog = LoadDialog(elements_type="devices", elements_old=self.devices,
                                    filename=self.gui_settings['device_folder'])
            else:
                dialog = LoadDialog(elements_type="devices", elements_old=self.devices)

            if dialog.exec_():
                gui_logger.info("Device selection dialog accepted")
                # Don't modify the device_folder from the dialog - it should be set by user configuration
                devices = dialog.get_values()
                added_devices = set(devices.keys()) - set(self.devices.keys())
                removed_devices = set(self.devices.keys()) - set(devices.keys())
                
                gui_logger.info(f"Device changes - Added: {added_devices}, Removed: {removed_devices}")
                
                # create instances of new devices
                self.devices, loaded_failed = Device.load_and_append(
                    {name: devices[name] for name in added_devices}, self.devices)
                    
                if len(loaded_failed) > 0:
                    gui_logger.warning(f"Following devices could not be loaded: {loaded_failed}")
                    print(('WARNING following device could not be loaded', loaded_failed))
                    
                # delete instances of new devices/experiments that have been deselected
                for name in removed_devices:
                    gui_logger.debug(f"Removing device: {name}")
                    del self.devices[name]
                    
                gui_logger.info(f"Devices loaded successfully. Total devices: {len(self.devices)}")
            else:
                gui_logger.info("Device selection dialog cancelled")

        def plot_data(sender):
            """
            plots the data of the selected experiment
            """
            gui_logger.info(f"Plot data requested from sender: {sender}")
            if sender == self.tree_dataset:
                index = self.tree_dataset.selectedIndexes()[0]
                model = index.model()
                time_tag = str(model.itemFromIndex(model.index(index.row(), 0)).text())
                experiment = self.data_sets[time_tag]
                gui_logger.info(f"Plotting dataset experiment: {experiment.name} (time: {time_tag})")
                self.plot_experiment(experiment)
            elif sender == self.tree_experiments:
                item = self.tree_experiments.currentItem()
                if item is not None:
                    experiment, path_to_experiment, _ = item.get_experiment()
                    # only plot if experiment has been selected but not if a parameter has been selected
                    if path_to_experiment == []:
                        gui_logger.info(f"Plotting experiment: {experiment.name}")
                        self.plot_experiment(experiment)
                    else:
                        gui_logger.debug(f"Plot request ignored - parameter selected: {path_to_experiment}")
                else:
                    gui_logger.warning("Plot requested but no experiment item selected")

        def save():
            gui_logger.info("Save GUI configuration requested")
            # Save config if gui_settings key exists, otherwise save to default location
            if 'gui_settings' in self.gui_settings:
                gui_logger.info(f"Saving to configured path: {self.gui_settings['gui_settings']}")
                self.save_config(self.gui_settings['gui_settings'])
            else:
                # Save to default location
                default_config_path = get_project_root() / "src" / "gui_config.json"
                gui_logger.info(f"Saving to default path: {default_config_path}")
                self.save_config(str(default_config_path))
                
        # Main button routing with logging
        gui_logger.debug(f"Routing button click from {sender}")
        
        if sender is self.btn_start_experiment:
            gui_logger.debug("Routing to start_button")
            start_button()
        elif sender is self.btn_stop_experiment:
            gui_logger.debug("Routing to stop_button")
            stop_button()
        elif sender is self.btn_skip_subexperiment:
            gui_logger.debug("Routing to skip_button")
            skip_button()
        elif sender is self.btn_validate_experiment:
            gui_logger.debug("Routing to validate_button")
            validate_button()
        elif sender in (self.tree_dataset, self.tree_experiments):
            gui_logger.debug("Routing to plot_data")
            plot_data(sender)
        elif sender is self.btn_store_experiment_data:
            gui_logger.debug("Routing to store_experiment_data")
            store_experiment_data()
        elif sender is self.btn_save_data:
            gui_logger.debug("Routing to save_data")
            save_data()
        elif sender is self.btn_delete_data:
            gui_logger.debug("Routing to delete_data")
            delete_data()
        # elif sender is self.btn_plot_probe:
        elif sender is self.chk_probe_plot:
            gui_logger.debug("Probe plot checkbox toggled")
            if self.chk_probe_plot.isChecked():
                item = self.tree_probes.currentItem()
                if item is not None:
                    if item.name in self.probes:
                        #selected item is an device not a probe, maybe plot all the probes...
                        gui_logger.warning("Can't plot, No probe selected. Select probe and try again!")
                        self.log('Can\'t plot, No probe selected. Select probe and try again!')
                    else:
                        device = item.parent().name
                        self.probe_to_plot = self.probes[device][item.name]
                        gui_logger.info(f"Probe plot enabled for {item.name} on device {device}")
                else:
                    gui_logger.warning("Can't plot, No probe selected. Select probe and try again!")
                    self.log('Can\'t plot, No probe selected. Select probe and try again!')
            else:
                gui_logger.info("Probe plot disabled")
                self.probe_to_plot = None
        elif sender is self.btn_save_gui:
            gui_logger.debug("Routing to save GUI configuration")
            # get filename
            filepath, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Save workspace configuration to file', self.config_filepath, filter = '*.json;*.aqs')

            #in case the user cancels during the prompt, check that the filepath is not an empty string
            if filepath:
                filename, file_extension = os.path.splitext(filepath)
                if file_extension not in ['.json', '.aqs']:
                    filepath = filename + ".json"  # Default to .json
                filepath = os.path.normpath(filepath)
                gui_logger.info(f"Saving GUI configuration to: {filepath}")
                self.save_config(filepath)
                self.gui_settings['gui_settings'] = filepath
                self.refresh_tree(self.tree_gui_settings, self.gui_settings)
            else:
                gui_logger.info("GUI save operation cancelled by user")
        elif sender is self.btn_load_gui:
            gui_logger.debug("Routing to load GUI configuration")
            # get filename
            fname = QtWidgets.QFileDialog.getOpenFileName(self, 'Load workspace configuration from file',  self.gui_settings['data_folder'], filter = '*.json;*.aqs')
            if fname[0]:
                gui_logger.info(f"Loading GUI configuration from: {fname[0]}")
                self.load_config(fname[0])
            else:
                gui_logger.info("GUI load operation cancelled by user")
        elif sender is self.btn_about:
            gui_logger.debug("About button clicked")
            msg = QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Information)
            msg.setText("Pitt AQuISS: Advanced Laboratory Equipment Control for Scientific Experiments")
            msg.setInformativeText("This enhanced software was developed by Gurudev Dutt at University of Pittsburgh "
                                   "and Jeffrey Guest at Argonne National Laboratory CNM. It is licensed under the LPGL licence. For more information, "
                                   "visit the GitHub page at github.com/pitt-diamond-qtech/pittqlabsys . We thank the Pylabcontrol and B26_Toolkit project which significantly inspired "
                                   "this project.")
            msg.setWindowTitle("About")
            # msg.setDetailedText("some stuff")
            msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
            # msg.buttonClicked.connect(msgbtn)
            retval = msg.exec_()
        # elif (sender is self.btn_load_devices) or (sender is self.btn_load_experiments):
        elif sender in (self.btn_load_devices, self.btn_load_experiments, self.btn_load_probes, self.btn_convert_python_files):
            if sender is self.btn_load_devices:
                load_devices()
            elif sender is self.btn_load_experiments:
                self.load_experiments()
            elif sender is self.btn_load_probes:
                load_probes()
            elif sender is self.btn_convert_python_files:
                self.convert_python_files()
            # refresh trees
            self.refresh_tree(self.tree_experiments, self.experiments)
            self.refresh_tree(self.tree_settings, self.devices)
        elif sender is self.actionSave:
            # Save config if gui_settings key exists, otherwise save to default location
            if 'gui_settings' in self.gui_settings:
                self.save_config(self.gui_settings['gui_settings'])
            else:
                # Save to default location
                default_config_path = get_project_root() / "src" / "gui_config.json"
                self.save_config(str(default_config_path))
        elif sender is self.actionGo_to_AQuISS_GitHub_page:
            webbrowser.open('https://github.com/pitt-diamond-qtech/pittqlabsys')
        elif sender is self.actionExport:
            # Pass existing devices to enable real hardware usage during conversion
            export_dialog = ExportDialog(existing_devices=self.devices)
            # Use resolved paths instead of empty gui_settings
            if 'experiments_folder' in self.gui_settings and self.gui_settings['experiments_folder']:
                export_dialog.target_path.setText(self.gui_settings['experiments_folder'])
            else:
                export_dialog.target_path.setText(str(self.paths['experiments_folder']))
            if self.gui_settings_hidden['experiments_source_folder']:
                export_dialog.source_path.setText(self.gui_settings_hidden['experiments_source_folder'])
            if export_dialog.source_path.text():
                export_dialog.reset_available(export_dialog.source_path.text())
            #exec_() blocks while export dialog is used, subsequent code will run on dialog closing
            export_dialog.exec_()
            self.gui_settings.update({'experiments_folder': export_dialog.target_path.text()})
            # Removed problematic fill_treeview call that was breaking the menu
            self.gui_settings_hidden.update({'experiments_source_folder': export_dialog.source_path.text()})
        elif sender is self.actionSaveWorkspace:
            # Save current workspace state
            workspace_name, ok = QtWidgets.QInputDialog.getText(self, 'Save Workspace', 'Enter workspace name:')
            if ok and workspace_name:
                self.save_config(workspace_name)
                self.log(f"Workspace '{workspace_name}' saved successfully")
        elif sender is self.actionLoadWorkspace:
            # Load workspace from workspace_configs directory
            workspace_dir = self.paths['workspace_config_dir']
            workspace_files = list(workspace_dir.glob("*.json"))
            
            if not workspace_files:
                QtWidgets.QMessageBox.information(self, "No Workspaces", "No saved workspaces found.")
                return
                
            # Create a simple dialog to select workspace
            workspace_name, ok = QtWidgets.QInputDialog.getItem(
                self, 'Load Workspace', 
                'Select workspace to load:',
                [f.stem for f in workspace_files], 0, False)
            
            if ok and workspace_name:
                self.load_config(workspace_name)
                self.log(f"Workspace '{workspace_name}' loaded successfully")

    def _show_hide_parameter(self):
        """
        shows or hides parameters
        Returns:

        """

        assert isinstance(self.sender(), QtWidgets.QCheckBox), 'this function should be connected to a check box'

        if self.sender().isChecked():
            self.tree_experiments.setColumnHidden(2, False)
            iterator = QtWidgets.QTreeWidgetItemIterator(self.tree_experiments, QtWidgets.QTreeWidgetItemIterator.Hidden)
            item = iterator.value()
            while item:
                item.setHidden(False)
                item = iterator.value()
                iterator += 1
        else:
            self.tree_experiments.setColumnHidden(2, True)

            iterator = QtWidgets.QTreeWidgetItemIterator(self.tree_experiments, QtWidgets.QTreeWidgetItemIterator.NotHidden)
            item = iterator.value()
            while item:
                if not item.visible:
                    item.setHidden(True)
                item = iterator.value()
                iterator +=1

        self.tree_experiments.setColumnWidth(0, 200)
        self.tree_experiments.setColumnWidth(1, 400)
        self.tree_experiments.setColumnWidth(2, 50)

    def _coerce_from_text(self, item, text: str):
        """
        Helper method to coerce text input to the appropriate type using regex pattern matching.
        
        Args:
            item: Tree item containing the value
            text: Raw text input from user
            
        Returns:
            Coerced value of appropriate type (int, float, bool, or str)
        """
        import re
        
        t = text.strip()
        
        # Check if it's a valid number (int or float, including scientific notation)
        if re.fullmatch(r'[+\-]?\d+(?:\.\d+)?(?:[eE][+\-]?\d+)?', t):
            if ('.' not in t) and ('e' not in t.lower()):
                return int(t)
            return float(t)
        
        # Check if it's a boolean
        if t.lower() in ('true', 'false'):
            return t.lower() == 'true'
        
        # Check if item has specific valid_values constraints
        if hasattr(item, 'valid_values'):
            expected_type = item.valid_values
            if isinstance(expected_type, list):
                # For list types, return as string if valid
                if t in expected_type:
                    return t
                else:
                    raise ValueError(f"Value '{t}' not in valid options: {expected_type}")
            elif expected_type == str:
                return str(t)
            elif expected_type == int:
                # Try to convert to int if it's a number
                try:
                    return int(float(t))
                except ValueError:
                    raise ValueError(f"Cannot convert '{t}' to integer")
            elif expected_type == float:
                # Try to convert to float if it's a number
                try:
                    return float(t)
                except ValueError:
                    raise ValueError(f"Cannot convert '{t}' to float")
        
        # Default: return as string
        return t

    def _write_clamped_value_to_cell(self, item, clamped_value):
        """
        Simplified method to write clamped value to cell.
        
        Args:
            item: Tree item to update
            clamped_value: The clamped value to write
        """
        gui_logger.info(f"Writing clamped value {clamped_value} to item {item.name}")
        
        # Block signals to prevent recursion
        view = item.treeWidget()
        view.blockSignals(True)
        try:
            # Update the item's internal value
            item.value = clamped_value
            
            # Update the display text directly
            item.setText(1, str(clamped_value))
            
            # Force a complete refresh of the tree widget
            view.repaint()
            
            gui_logger.info(f"Successfully updated item {item.name} to display {clamped_value}")
            
        finally:
            view.blockSignals(False)
            # Clear the clamped feedback flag so future updates can proceed
            if hasattr(item, '_clamped_feedback'):
                delattr(item, '_clamped_feedback')

    def update_parameters(self, treeWidget, changed_item=None, changed_col=None):
        """
        Enhanced parameter update with validation and user feedback.
        Updates the internal dictionaries for experiments and devices with values from the respective trees.
        Provides visual feedback for parameter validation, clamping, and errors.

        Args:
            treeWidget: the tree from which to update
            changed_item: the specific item that changed (if called from signal)
            changed_col: the column that changed (if called from signal)
        """
        # Prevent recursion
        if getattr(self, "_updating_parameters", False) or getattr(self, "_programmatic_update", False):
            return

        # We only care about edits in the Value column (1)
        if changed_item is None or changed_col is None or changed_col != 1:
            return

        item = changed_item
        
        self._updating_parameters = True
        try:
            # Check if this item is already being processed for clamping
            if getattr(item, '_clamped_feedback', False):
                gui_logger.debug(f"Skipping update for {item.name} - already processing clamped value")
                return

            # Parse the new value and validate against device ranges FIRST
            raw_text = item.text(1).strip()
            # Get the current value from EditRole for proper numeric comparison
            current_value = item.data(1, Qt.EditRole)
            if current_value is None:
                current_value = getattr(item, "value", "")
            value_was_clamped = False  # Track if value was clamped during validation
            
            gui_logger.debug(f"Value change check - raw_text: '{raw_text}', current_value: '{current_value}' (type: {type(current_value)})")
            
            # Try to parse the new value using helper method
            try:
                new_value = self._coerce_from_text(item, raw_text)
            except ValueError as e:
                gui_logger.warning(f"Invalid value '{raw_text}' for {item.name}: {e}")
                self._handle_parameter_error(item, str(e), "GUI")
                return
            
            # For device parameters, validate against device ranges BEFORE comparing to current value
            if treeWidget == self.tree_settings:
                device, path_to_device = item.get_device()
                if device and hasattr(device, 'validate_parameter'):
                    gui_logger.debug(f"Pre-validating parameter {item.name} = {new_value} on {device.name}")
                    validation_result = device.validate_parameter(path_to_device, new_value)
                    gui_logger.debug(f"Pre-validation result: {validation_result}")
                    
                    if not validation_result.get('valid', True):
                        # Check if there's a clamped value available
                        clamped_value = validation_result.get('clamped_value')
                        if clamped_value is not None:
                            # Use the clamped value and show warning
                            gui_logger.info(f"Parameter {item.name} was clamped from {new_value} to {clamped_value}")
                            new_value = clamped_value
                            value_was_clamped = True
                            # Set the clamped feedback flag immediately to prevent recursive calls
                            item._clamped_feedback = True
                        else:
                            # No clamped value available, show error and don't proceed
                            error_msg = validation_result.get('message', 'Parameter validation failed')
                            gui_logger.warning(f"Pre-validation failed: {item.name} on {device.name} - {error_msg}")
                            self._handle_parameter_error(item, error_msg, device.name)
                            return
                    else:
                        # Validation passed, check if value was clamped anyway
                        if validation_result.get('clamped_value') is not None:
                            clamped_value = validation_result.get('clamped_value')
                            gui_logger.info(f"Parameter {item.name} was clamped from {new_value} to {clamped_value}")
                            new_value = clamped_value
                            value_was_clamped = True
                            # Set the clamped feedback flag immediately to prevent recursive calls
                            item._clamped_feedback = True
            
            # NOW check if the parsed/validated value is actually different from current value
            # Use proper numeric comparison to avoid spurious work
            if isinstance(current_value, (int, float)) and isinstance(new_value, (int, float)):
                # For numeric values, compare the actual numbers
                if current_value == new_value:
                    gui_logger.debug(f"Value unchanged for {item.name} (numeric comparison), skipping update")
                    return
            elif current_value == new_value:
                # For non-numeric values, use direct comparison
                gui_logger.debug(f"Value unchanged for {item.name} (direct comparison), skipping update")
                return
                
            gui_logger.info(f"Value changed for {item.name}: {current_value} -> {new_value}")
            
            # Update the item's value with the parsed/validated value
            item.value = new_value
            
            # If value was clamped, update the GUI display and show visual feedback
            if value_was_clamped:
                gui_logger.info(f"Updating GUI display for clamped value: {new_value}")
                
                # Use bulletproof method to write clamped value to cell
                self._write_clamped_value_to_cell(item, new_value)
                
                # Apply background/feedback WITHOUT triggering itemChanged
                tw = item.treeWidget()
                with QSignalBlocker(tw):
                    item.setBackground(1, QtGui.QBrush(QtGui.QColor(255, 240, 200)))  # Orange for warning
                
                gui_logger.info(f"GUI display updated - text: '{item.text(1)}', value: {item.value}")
                
                # Show notification about clamping
                self._show_parameter_notification(f"Parameter {item.name} was clamped to {new_value}")
                
                # Auto-clear the visual feedback after 3 seconds
                self._clear_visual_feedback_after_delay(item, 3000)
                
                # Continue with device update using the clamped value

            gui_logger.debug(f"update_parameters called for tree: {type(treeWidget)}, item: {item.name}, column: {changed_col}")

            if treeWidget == self.tree_settings:
                gui_logger.debug("Updating parameters from tree_settings")

                device, path_to_device = item.get_device()
                gui_logger.debug(f"Updating device: {device.name}, path: {path_to_device}")
                gui_logger.info(f"Device class: {type(device).__name__}, module: {type(device).__module__}")

                # Store original values for comparison
                requested_value = item.value
                old_value = device.settings
                path_to_device_copy = path_to_device.copy()
                path_to_device_copy.reverse()
                for element in path_to_device_copy:
                    old_value = old_value[element]

                # Build nested dictionary to update device
                dictator = item.value
                for element in path_to_device:
                    dictator = {element: dictator}

                try:
                    # Use the enhanced feedback system if available
                    if hasattr(device, 'get_feedback_only'):
                        # Get detailed feedback about the update
                        # Note: get_feedback_only already updates the device internally
                        feedback = device.get_feedback_only(dictator)
                        
                        # Process feedback for each parameter
                        for param_name, param_feedback in feedback.items():
                            self._process_parameter_feedback(item, param_feedback, device.name, path_to_device)
                    else:
                        # Fallback to old method for devices without enhanced feedback
                        self._update_device_with_validation(device, dictator, item, path_to_device)
                        
                        # Get actual value after update (in case device clamped it)
                        actual_value = device.settings
                        for element in path_to_device_copy:
                            actual_value = actual_value[element]
                        
                        # Provide user feedback based on what happened
                        self._provide_parameter_feedback(item, requested_value, actual_value, old_value, device.name)
                    
                except Exception as e:
                    # Handle validation errors gracefully
                    self._handle_parameter_error(item, str(e), device.name)
                    return
                
            elif treeWidget == self.tree_experiments:
                gui_logger.debug("Updating parameters from tree_experiments")
                experiment, path_to_experiment, _ = item.get_experiment()
                gui_logger.debug(f"Updating experiment: {experiment.name}, path: {path_to_experiment}")

                # check if changes value is from an device
                device, path_to_device = item.get_device()
                if device is not None:
                    new_value = item.value
                    msg = "changed parameter {:s} to {:s} in {:s}".format(item.name,
                                                                                    str(new_value),
                                                                                    experiment.name)
                    gui_logger.info(f"Device parameter updated: {item.name} to {new_value} in {experiment.name}")
                else:
                    new_value = item.value
                    msg = "changed parameter {:s} to {:s} in {:s}".format(item.name,
                                                                                str(new_value),
                                                                                experiment.name)
                    gui_logger.info(f"Experiment parameter updated: {item.name} to {new_value} in {experiment.name}")
                self.log(msg)
            else:
                gui_logger.warning(f"Unknown tree widget type: {type(treeWidget)}")
        
        except Exception as e:
            # Handle any unexpected errors in the parameter update process
            gui_logger.error(f"Unexpected error in update_parameters: {e}")
            self.log(f"Error updating parameters: {e}")
        
        finally:
            # Always reset the recursion guard
            self._updating_parameters = False

    def _update_device_with_validation(self, device, settings_dict, item, path_to_device):
        """
        Update device with parameter validation and error handling.
        
        Args:
            device: Device instance to update
            settings_dict: Dictionary of settings to apply
            item: Tree item being updated
            path_to_device: Path to the parameter in device settings
        """
        try:
            # Check if device has validation method
            if hasattr(device, 'validate_parameter'):
                gui_logger.info(f"Calling validate_parameter on {type(device).__name__} with path: {path_to_device}, value: {item.value}")
                validation_result = device.validate_parameter(path_to_device, item.value)
                gui_logger.info(f"Validation result: {validation_result}")
                if not validation_result.get('valid', True):
                    raise ValueError(validation_result.get('message', 'Parameter validation failed'))
            else:
                gui_logger.warning(f"Device {type(device).__name__} does not have validate_parameter method")
            
            # Update the device
            device.update(settings_dict)
            
        except Exception as e:
            gui_logger.error(f"Device update failed: {str(e)}")
            raise

    def _provide_parameter_feedback(self, item, requested_value, actual_value, old_value, device_name):
        """
        Provide visual and textual feedback for parameter changes.
        
        Args:
            item: Tree item that was updated
            requested_value: Value the user requested
            actual_value: Value actually set by device
            old_value: Previous value
            device_name: Name of the device
        """
        # Determine what happened and provide appropriate feedback
        if actual_value == requested_value:
            # Value was accepted as-is
            if actual_value != old_value:
                msg = f"✅ Parameter {item.name} changed from {old_value} to {actual_value} on {device_name}"
                gui_logger.info(f"Parameter updated successfully: {item.name} on {device_name}")
                self._set_item_visual_feedback(item, 'success')
            else:
                msg = f"Parameter {item.name} unchanged on {device_name}"
                gui_logger.debug(f"Parameter unchanged: {item.name} on {device_name}")
                self._set_item_visual_feedback(item, 'normal')
        else:
            # Value was clamped by device
            msg = f"⚠️ Parameter {item.name} clamped from {requested_value} to {actual_value} on {device_name}"
            gui_logger.warning(f"Parameter clamped: {item.name} from {requested_value} to {actual_value} on {device_name}")
            self._set_item_visual_feedback(item, 'warning')
            
            # Update the tree item to show the actual value
            tw = item.treeWidget()
            blocker = QSignalBlocker(tw)
            try:
                item.value = actual_value
                item.setText(1, str(actual_value))
            finally:
                del blocker
            
            # Show notification to user
            self._show_parameter_notification(f"Parameter {item.name} was clamped to {actual_value}")
        
        self.log(msg)

    def _handle_parameter_error(self, item, error_message, device_name):
        """
        Handle parameter validation errors with user feedback.
        
        Args:
            item: Tree item that failed validation
            error_message: Error message from validation
            device_name: Name of the device
        """
        msg = f"❌ Parameter {item.name} validation failed on {device_name}: {error_message}"
        gui_logger.error(f"Parameter validation failed: {item.name} on {device_name} - {error_message}")
        
        # Set visual feedback for error
        self._set_item_visual_feedback(item, 'error')
        
        # Show error notification
        self._show_parameter_notification(f"Parameter {item.name} error: {error_message}", is_error=True)
        
        self.log(msg)

    def _process_parameter_feedback(self, item, param_feedback, device_name, path_to_device):
        """
        Process enhanced parameter feedback from device.
        
        Args:
            item: Tree item that was updated
            param_feedback: Feedback dictionary from device
            device_name: Name of the device
            path_to_device: Path to the parameter in device settings
        """
        if not param_feedback.get('changed', False):
            # Parameter was set successfully without changes
            msg = f"✅ Parameter {item.name} set to {param_feedback['actual']} on {device_name}"
            gui_logger.info(f"Parameter set successfully: {item.name} on {device_name}")
            
            # Don't override clamped feedback with success feedback
            if not getattr(item, '_clamped_feedback', False):
                self._set_item_visual_feedback(item, 'success')
            else:
                gui_logger.debug(f"Skipping success feedback for {item.name} - clamped feedback active")
            
            self._show_parameter_notification(f"Parameter {item.name} set successfully")
        else:
            # Parameter value changed - determine the reason
            reason = param_feedback.get('reason', 'unknown')
            message = param_feedback.get('message', 'Value changed')
            actual_value = param_feedback.get('actual')
            requested_value = param_feedback.get('requested')
            
            if reason == 'error':
                # Hardware error
                msg = f"❌ {device_name}: {message}"
                gui_logger.error(f"Hardware error: {item.name} on {device_name} - {message}")
                self._show_parameter_notification(f"Hardware error: {message}", is_error=True)
                
                # Update tree item to show actual value
                if actual_value is not None:
                    gui_logger.info(f"Updating GUI item {item.name} from {item.value} to {actual_value}")
                    
                    # Use improved GUI update logic
                    view = item.treeWidget()
                    index = view.indexFromItem(item, 1)

                    # Prevent re-entry while we sync editor/model
                    self._programmatic_update = True
                    try:
                        # If the cell is being edited, update the editor widget text and commit it
                        if view.state() == QtWidgets.QAbstractItemView.EditingState and index == view.currentIndex():
                            editor = view.focusWidget()
                            if editor is not None and hasattr(editor, "setText"):
                                editor.setText(str(actual_value))
                                # commit editor back to model to avoid stale overwrite
                                try:
                                    view.closeEditor(editor, QtWidgets.QAbstractItemDelegate.SubmitModelCache)
                                except AttributeError:
                                    # Fallback if closeEditor is not available
                                    view.viewport().setFocus(QtCore.Qt.OtherFocusReason)

                        # Update the model value via EditRole so the view/editor stay in sync
                        view.model().setData(index, actual_value, QtCore.Qt.EditRole)

                        # Keep your internal mirror
                        item.value = actual_value

                    finally:
                        self._programmatic_update = False
                    
                    # Set error background using QSignalBlocker for decoration only
                    with QSignalBlocker(item.treeWidget()):
                        item.setBackground(1, QtGui.QBrush(QtGui.QColor(255, 200, 200)))  # Red for error
                    
                    gui_logger.info(f"GUI item {item.name} updated successfully")
                    
            elif reason == 'clamped':
                # Value was clamped by hardware limits
                msg = f"⚠️ {device_name}: {message}"
                gui_logger.warning(f"Parameter clamped: {item.name} on {device_name} - {message}")
                self._show_parameter_notification(f"Parameter clamped: {message}")
                
                # Update tree item to show actual value
                if actual_value is not None:
                    gui_logger.info(f"Updating GUI item {item.name} from {item.value} to {actual_value}")
                    
                    # Use improved GUI update logic
                    view = item.treeWidget()
                    index = view.indexFromItem(item, 1)

                    # Prevent re-entry while we sync editor/model
                    self._programmatic_update = True
                    try:
                        # If the cell is being edited, update the editor widget text and commit it
                        if view.state() == QtWidgets.QAbstractItemView.EditingState and index == view.currentIndex():
                            editor = view.focusWidget()
                            if editor is not None and hasattr(editor, "setText"):
                                editor.setText(str(actual_value))
                                # commit editor back to model to avoid stale overwrite
                                try:
                                    view.closeEditor(editor, QtWidgets.QAbstractItemDelegate.SubmitModelCache)
                                except AttributeError:
                                    # Fallback if closeEditor is not available
                                    view.viewport().setFocus(QtCore.Qt.OtherFocusReason)

                        # Update the model value via EditRole so the view/editor stay in sync
                        view.model().setData(index, actual_value, QtCore.Qt.EditRole)

                        # Keep your internal mirror
                        item.value = actual_value

                    finally:
                        self._programmatic_update = False
                    
                    # Set warning background using QSignalBlocker for decoration only
                    with QSignalBlocker(item.treeWidget()):
                        item.setBackground(1, QtGui.QBrush(QtGui.QColor(255, 240, 200)))  # Orange for warning
                    
                    gui_logger.info(f"GUI item {item.name} updated successfully")
                    
            else:
                # Unknown reason for change
                msg = f"⚠️ {device_name}: {message}"
                gui_logger.warning(f"Parameter changed: {item.name} on {device_name} - {message}")
                self._show_parameter_notification(f"Parameter changed: {message}")
                
                # Update tree item to show actual value
                if actual_value is not None:
                    gui_logger.info(f"Updating GUI item {item.name} from {item.value} to {actual_value}")
                    
                    # Use improved GUI update logic
                    view = item.treeWidget()
                    index = view.indexFromItem(item, 1)

                    # Prevent re-entry while we sync editor/model
                    self._programmatic_update = True
                    try:
                        # If the cell is being edited, update the editor widget text and commit it
                        if view.state() == QtWidgets.QAbstractItemView.EditingState and index == view.currentIndex():
                            editor = view.focusWidget()
                            if editor is not None and hasattr(editor, "setText"):
                                editor.setText(str(actual_value))
                                # commit editor back to model to avoid stale overwrite
                                try:
                                    view.closeEditor(editor, QtWidgets.QAbstractItemDelegate.SubmitModelCache)
                                except AttributeError:
                                    # Fallback if closeEditor is not available
                                    view.viewport().setFocus(QtCore.Qt.OtherFocusReason)

                        # Update the model value via EditRole so the view/editor stay in sync
                        view.model().setData(index, actual_value, QtCore.Qt.EditRole)

                        # Keep your internal mirror
                        item.value = actual_value

                    finally:
                        self._programmatic_update = False
                    
                    # Set warning background using QSignalBlocker for decoration only
                    with QSignalBlocker(item.treeWidget()):
                        item.setBackground(1, QtGui.QBrush(QtGui.QColor(255, 240, 200)))  # Orange for warning
                    
                    gui_logger.info(f"GUI item {item.name} updated successfully")
        
        self.log(msg)

    def _set_item_visual_feedback(self, item, feedback_type):
        """
        Set visual feedback on tree item based on validation result.
        
        Args:
            item: Tree item to update
            feedback_type: 'success', 'warning', 'error', or 'normal'
        """
        tw = item.treeWidget()
        blocker = QSignalBlocker(tw)  # prevents itemChanged while we paint
        try:
            # Reset any existing styling
            item.setBackground(0, QtGui.QBrush())
            item.setBackground(1, QtGui.QBrush())
            
            if feedback_type == 'success':
                # Green background for successful updates
                item.setBackground(1, QtGui.QBrush(QtGui.QColor(200, 255, 200)))
                # Auto-clear after 2 seconds
                self._clear_visual_feedback_after_delay(item, 2000)
            elif feedback_type == 'warning':
                # Yellow background for clamped values
                item.setBackground(1, QtGui.QBrush(QtGui.QColor(255, 240, 200)))
                # Auto-clear after 3 seconds (longer for warnings)
                self._clear_visual_feedback_after_delay(item, 3000)
            elif feedback_type == 'error':
                # Red background for validation errors
                item.setBackground(1, QtGui.QBrush(QtGui.QColor(255, 200, 200)))
                # Auto-clear after 4 seconds (longer for errors)
                self._clear_visual_feedback_after_delay(item, 4000)
            # 'normal' doesn't change the background
        finally:
            del blocker

    def _show_parameter_notification(self, message, is_error=False):
        """
        Show a notification to the user about parameter changes.
        
        Args:
            message: Message to display
            is_error: Whether this is an error message
        """
        # Log the message
        if is_error:
            gui_logger.error(f"Parameter notification (ERROR): {message}")
        else:
            gui_logger.info(f"Parameter notification: {message}")
        
        # Show visual notification to user
        self._show_visual_notification(message, is_error)
    
    def _show_visual_notification(self, message, is_error=False):
        """
        Show visual notification to user (popup only for critical errors).
        
        Args:
            message: Message to display
            is_error: Whether this is an error message
        """
        try:
            if is_error:
                # Only show popup for critical hardware errors
                msg_box = QtWidgets.QMessageBox()
                msg_box.setIcon(QtWidgets.QMessageBox.Critical)
                msg_box.setWindowTitle("Hardware Error")
                msg_box.setText("Hardware Error Detected")
                msg_box.setInformativeText(message)
                msg_box.setStandardButtons(QtWidgets.QMessageBox.Ok)
                msg_box.exec_()
            else:
                # For non-critical messages, just rely on:
                # - Log messages (already handled in _show_parameter_notification)
                # - Visual feedback on tree items (colored backgrounds)
                # - Status bar updates (if available)
                pass
                
        except Exception as e:
            # Fallback to logging if GUI notification fails
            gui_logger.warning(f"Failed to show visual notification: {e}")
            gui_logger.info(f"Notification message: {message}")

    def _get_parameter_ranges(self, device, path_to_device):
        """
        Get valid parameter ranges for a device parameter.
        
        Args:
            device: Device instance
            path_to_device: Path to the parameter in device settings
            
        Returns:
            dict: Dictionary with 'min', 'max', 'valid_values' keys
        """
        try:
            if hasattr(device, 'get_parameter_ranges'):
                return device.get_parameter_ranges(path_to_device)
            
            # Fallback: try to get ranges from Parameter object
            param_obj = device.settings
            for element in path_to_device:
                if hasattr(param_obj, element):
                    param_obj = getattr(param_obj, element)
                else:
                    return {}
            
            if hasattr(param_obj, 'valid_values'):
                if isinstance(param_obj.valid_values, list):
                    return {'valid_values': param_obj.valid_values}
                elif hasattr(param_obj.valid_values, '__bases__') and param_obj.valid_values in (int, float):
                    # For numeric types, we could try to infer ranges from Parameter info
                    return {'type': param_obj.valid_values}
            
            return {}
        except Exception as e:
            gui_logger.debug(f"Could not get parameter ranges: {e}")
            return {}

    def _add_parameter_tooltip(self, item, device, path_to_device):
        """
        Add informative tooltip to parameter item showing valid ranges.
        
        Args:
            item: Tree item to add tooltip to
            device: Device instance
            path_to_device: Path to the parameter
        """
        try:
            ranges = self._get_parameter_ranges(device, path_to_device)
            tooltip_parts = [f"Parameter: {item.name}"]
            
            if 'valid_values' in ranges:
                tooltip_parts.append(f"Valid values: {ranges['valid_values']}")
            elif 'min' in ranges and 'max' in ranges:
                tooltip_parts.append(f"Range: {ranges['min']} to {ranges['max']}")
            elif 'type' in ranges:
                tooltip_parts.append(f"Type: {ranges['type'].__name__}")
            
            # Add current value
            tooltip_parts.append(f"Current: {item.value}")
            
            tooltip_text = "\n".join(tooltip_parts)
            item.setToolTip(1, tooltip_text)
            
        except Exception as e:
            gui_logger.debug(f"Could not add tooltip: {e}")

    def _clear_visual_feedback_after_delay(self, item, delay_ms=2000):
        """
        Clear visual feedback after a delay to avoid permanent highlighting.
        
        Args:
            item: Tree item to clear feedback from
            delay_ms: Delay in milliseconds before clearing
        """
        # Use QTimer to clear feedback after delay
        timer = QtCore.QTimer()
        timer.setSingleShot(True)
        # Use a lambda that checks the recursion guard before clearing
        timer.timeout.connect(lambda: self._safe_clear_visual_feedback(item))
        timer.start(delay_ms)
    
    def _safe_clear_visual_feedback(self, item):
        """
        Safely clear visual feedback, checking recursion guard first.
        
        Args:
            item: Tree item to clear feedback from
        """
        # Only clear if we're not in the middle of updating parameters
        if not self._updating_parameters:
            # Reset background to normal
            item.setBackground(0, QtGui.QBrush())
            item.setBackground(1, QtGui.QBrush())
            # Clear the clamped feedback flag
            if hasattr(item, '_clamped_feedback'):
                delattr(item, '_clamped_feedback')

    def plot_experiment(self, experiment):
        """
        Calls the plot function of the experiment, and redraws both plots
        Args:
            experiment: experiment to be plotted
        """
        gui_logger.info(f"Plotting experiment: {experiment.name}")
        try:
            experiment.plot([self.pyqtgraphwidget_1.graph, self.pyqtgraphwidget_2.graph])
            gui_logger.debug("Experiment plot completed successfully")
            #self.matplotlibwidget_1.draw()
            #self.matplotlibwidget_2.draw()
        except Exception as e:
            gui_logger.error(f"Error plotting experiment {experiment.name}: {str(e)}")
            gui_logger.error(f"Traceback: {traceback.format_exc()}")


    @pyqtSlot(int)
    def update_status(self, progress):
        """
        waits for a signal emitted from a thread and updates the gui
        Args:
            progress:
        Returns:

        """
        gui_logger.debug(f"Status update received: progress = {progress}")

        # interval at which the gui will be updated, if requests come in faster than they will be ignored
        update_interval = 0.2

        now = datetime.datetime.now()

        if not self._last_progress_update is None and now-self._last_progress_update < datetime.timedelta(seconds=update_interval):
            gui_logger.debug("Status update ignored - too frequent")
            return

        self._last_progress_update = now
        gui_logger.debug(f"Updating progress bar to {progress}")

        self.progressBar.setValue(progress)

        experiment = self.current_experiment

        # Estimate remaining time if progress has been made
        if progress:
            remaining_time = str(datetime.timedelta(seconds=experiment.remaining_time.seconds))
            self.lbl_time_estimate.setText('time remaining: {:s}'.format(remaining_time))
        if experiment is not str(self.tabWidget.tabText(self.tabWidget.currentIndex())).lower() in ['experiments', 'devices']:
            self.plot_experiment(experiment)


    @pyqtSlot()
    def experiment_finished(self):
        """
        waits for the experiment to emit the experiment_finshed signal
        """
        experiment = self.current_experiment
        self.previous_data = experiment.data
        experiment.updateProgress.disconnect(self.update_status)
        self.experiment_thread.started.disconnect()
        experiment.finished.disconnect()

        self.current_experiment = None

        self.plot_experiment(experiment)
        self.progressBar.setValue(100)
        self.btn_start_experiment.setEnabled(True)
        self.btn_skip_subexperiment.setEnabled(False)

    def plot_experiment_validate(self, experiment):
        """
        checks the plottype of the experiment and plots it accordingly
        Args:
            experiment: experiment to be plotted

        """

        experiment.plot_validate([self.pyqtgraphwidget_1.graph, self.pyqtgraphwidget_2.graph])
        #self.matplotlibwidget_1.draw()
        #self.matplotlibwidget_2.draw()

    def update_probes(self, progress):
        """
        update the probe tree
        """
        new_values = self.read_probes.probes_values
        probe_count = len(self.read_probes.probes)

        if probe_count > self.tree_probes.topLevelItemCount():
            # when run for the first time, there are no probes in the tree, so we have to fill it first
            self.fill_treewidget(self.tree_probes, new_values)
        else:
            for x in range(probe_count):
                topLvlItem = self.tree_probes.topLevelItem(x)
                for child_id in range(topLvlItem.childCount()):
                    child = topLvlItem.child(child_id)
                    child.value = new_values[topLvlItem.name][child.name]
                    child.setText(1, str(child.value))

        if self.probe_to_plot is not None:
            self.probe_to_plot.plot(self.matplotlibwidget_1.axes)
            self.matplotlibwidget_1.draw()


        if self.chk_probe_log.isChecked():
            data = ','.join(list(np.array([[str(p) for p in list(p_dict.values())] for instr, p_dict in new_values.items()]).flatten()))
            self.probe_file.write('{:s}\n'.format(data))

    def update_experiment_from_item(self, item):
        """
        updates the experiment based on the information provided in item

        Args:
            experiment: experiment to be updated
            item: AQuISSQTreeItem that contains the new settings of the experiment

        """

        experiment, path_to_experiment, experiment_item = item.get_experiment()

        # build dictionary
        # get full information from experiment
        dictator = list(experiment_item.to_dict().values())[0]  # there is only one item in the dictionary

        for device in list(experiment.devices.keys()):
            # update device
            experiment.devices[device]['settings'] = dictator[device]['settings']
            # remove device
            del dictator[device]


        for sub_experiment_name in list(experiment.experiments.keys()):
            sub_experiment_item = experiment_item.get_subexperiment(sub_experiment_name)
            self.update_experiment_from_item(sub_experiment_item)
            del dictator[sub_experiment_name]

        experiment.update(dictator)
        # update datefolder path
        experiment.data_path = self.gui_settings['data_folder']

    def fill_treewidget(self, tree, parameters):
        """
        fills a QTreeWidget with nested parameters, in future replace QTreeWidget with QTreeView and call fill_treeview
        Args:
            tree: QtWidgets.QTreeWidget
            parameters: dictionary or Parameter object
            show_all: boolean if true show all parameters, if false only selected ones
        Returns:

        """
        gui_logger.debug(f"fill_treewidget called with tree: {type(tree)}, parameters: {type(parameters)}")
        
        try:
            tree.clear()
            assert isinstance(parameters, (dict, Parameter))

            gui_logger.debug(f"Adding {len(parameters)} items to tree")
            for key, value in parameters.items():
                try:
                    if isinstance(value, Parameter):
                        gui_logger.debug(f"Creating Parameter item: {key}")
                        item = AQuISSQTreeItem(tree, key, value, value.valid_values, value.info)
                        tree.addTopLevelItem(item)
                    else:
                        gui_logger.debug(f"Creating non-Parameter item: {key} ({type(value)})")
                        item = AQuISSQTreeItem(tree, key, value, type(value), '')
                        tree.addTopLevelItem(item)
                except Exception as e:
                    gui_logger.error(f"Error creating tree item for {key}: {str(e)}")
                    gui_logger.error(f"Traceback: {traceback.format_exc()}")
                    
            gui_logger.debug(f"fill_treewidget completed successfully, tree now has {tree.topLevelItemCount()} items")
            
        except Exception as e:
            gui_logger.error(f"Error in fill_treewidget: {str(e)}")
            gui_logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    def fill_treeview(self, tree, input_dict):
        """
        fills a treeview with nested parameters
        Args:
            tree: QtWidgets.QTreeView
            parameters: dictionary or Parameter object

        Returns:

        """

        tree.model().removeRows(0, tree.model().rowCount())

        def add_element(item, key, value):
            child_name = QtGui.QStandardItem(key)

            if isinstance(value, dict):
                for key_child, value_child in value.items():
                    add_element(child_name, key_child, value_child)
                item.appendRow(child_name)
            else:
                child_value = QtGui.QStandardItem(str(value))

                item.appendRow([child_name, child_value])

        for index, (key, value) in enumerate(input_dict.items()):

            if isinstance(value, dict):
                item = QtGui.QStandardItem(key)
                for sub_key, sub_value in value.items():
                    add_element(item, sub_key, sub_value)
                tree.model().appendRow(item)
            elif isinstance(value, str):
                item = QtGui.QStandardItem(key)
                item_value = QtGui.QStandardItem(value)
                item_value.setEditable(True)
                item_value.setSelectable(True)
                tree.model().appendRow([item, item_value])

    def edit_tree_item(self):
        """
        if sender is self.tree_gui_settings this will open a filedialog and ask for a filepath
        this filepath will be updated in the field of self.tree_gui_settings that has been double clicked
        """

        def open_path_dialog_folder(path):
            """
            opens a file dialog to get the path to a file and
            """
            dialog = QtWidgets.QFileDialog()
            dialog.setFileMode(QtWidgets.QFileDialog.Directory)
            dialog.setOption(QtWidgets.QFileDialog.ShowDirsOnly, True)
            path = dialog.getExistingDirectory(self, 'Select a folder:', path)

            return path

        tree = self.sender()

        if tree == self.tree_gui_settings:

            index = tree.selectedIndexes()[0]
            model = index.model()

            if index.column() == 1:
                path = model.itemFromIndex(index).text()
                key = str(model.itemFromIndex(model.index(index.row(), 0)).text())
                if(key == 'gui_settings'):
                    path, _ = QtWidgets.QFileDialog.getSaveFileName(self, caption = 'Select a file:', directory = path, filter = '*.json;*.aqs')
                    if path:
                        name, extension = os.path.splitext(path)
                        if extension not in ['.json', '.aqs']:
                            path = name + ".json"  # Default to .json
                else:
                    path = str(open_path_dialog_folder(path))

                if path != "":
                    self.gui_settings.update({key : str(os.path.normpath(path))})
                    self.fill_treeview(tree, self.gui_settings)

    def refresh_tree(self, tree, items):
        """
        refresh trees with current settings
        Args:
            tree: a QtWidgets.QTreeWidget object or a QtWidgets.QTreeView object
            items: dictionary or Parameter items with which to populate the tree
            show_all: boolean if true show all parameters, if false only selected ones
        """

        if tree == self.tree_experiments or tree == self.tree_settings:
            tree.itemChanged.disconnect()
            self.fill_treewidget(tree, items)
            tree.itemChanged.connect(
                lambda item, col: self.update_parameters(tree, item, col)
            )
        elif tree == self.tree_gui_settings:
            self.fill_treeview(tree, items)

    def fill_dataset_tree(self, tree, data_sets):
        """
        fills the tree with data sets where datasets is a dictionary of the form
        Args:
            tree:
            data_sets: a dataset

        Returns:

        """
        gui_logger.info(f"Filling dataset tree with {len(data_sets)} datasets")
        
        tree.model().removeRows(0, tree.model().rowCount())
        for index, (time, experiment) in enumerate(data_sets.items()):
            try:
                # Get experiment name/tag safely
                if hasattr(experiment, 'settings') and 'tag' in experiment.settings:
                    name = experiment.settings['tag']
                else:
                    name = getattr(experiment, 'name', 'Unknown')
                
                type_name = getattr(experiment, 'name', 'Unknown')

                item_time = QtGui.QStandardItem(str(time))
                item_name = QtGui.QStandardItem(str(name))
                item_type = QtGui.QStandardItem(str(type_name))

                item_time.setSelectable(False)
                item_time.setEditable(False)
                item_type.setSelectable(False)
                item_type.setEditable(False)

                tree.model().appendRow([item_time, item_name, item_type])
                gui_logger.debug(f"Added dataset: {time} - {name} ({type_name})")
                
            except Exception as e:
                gui_logger.error(f"Error adding dataset {time} to tree: {e}")
                continue

    def load_config(self, filepath=None):
        """
        Loads a workspace configuration file from the workspace_configs directory
        Args:
            filepath: Name of the workspace configuration file (without .json extension) or full path

        """

        # If filepath is just a name, look for it in the workspace_configs directory
        if filepath and not Path(filepath).parent.name:
            workspace_dir = self.paths['workspace_config_dir']
            full_filepath = workspace_dir / f"{filepath}.json"
        else:
            full_filepath = filepath

        # load config or default if invalid

        def load_settings(filepath):
            """
            Loads a workspace configuration file (JSON dictionary)
            - path_to_file: path to file that contains the dictionary

            Returns:
                - devices: depth 1 dictionary where keys are device names and values are instances of devices
                - experiments:  depth 1 dictionary where keys are experiment names and values are instances of experiments
                - probes: depth 1 dictionary where to be decided....?
            """

            devices_loaded = {}
            probes_loaded = {}
            experiments_loaded = {}

            if filepath and os.path.isfile(filepath):
                in_data = load_aqs_file(filepath)

                devices = in_data['devices'] if 'devices' in in_data else {}
                experiments = in_data['experiments'] if 'experiments' in in_data else {}
                probes = in_data['probes'] if 'probes' in in_data else {}

                try:
                    devices_loaded, failed = Device.load_and_append(devices)
                    if len(failed) > 0:
                        print(('WARNING! Following devices could not be loaded: ', failed))

                    experiments_loaded, failed, devices_loaded = Experiment.load_and_append(
                        experiment_dict=experiments,
                        devices=devices_loaded,
                        log_function=self.log,
                        data_path=self.gui_settings['data_folder'])

                    if len(failed) > 0:
                        print(('WARNING! Following experiments could not be loaded: ', failed))

                    probes_loaded, failed, devices_loadeds = Probe.load_and_append(
                        probe_dict=probes,
                        probes=probes_loaded,
                        devices=devices_loaded)

                    self.log('Successfully loaded from previous save.')
                except ImportError:
                    self.log('Could not load devices or experiments from file.')
                    self.log('Opening with blank GUI.')
            return devices_loaded, experiments_loaded, probes_loaded

        config = None

        try:
            config = load_aqs_file(filepath)
            config_settings = config['gui_settings']
            if config_settings['gui_settings'] != filepath:
                print((
                'WARNING path to settings file ({:s}) in config file is different from path of settings file ({:s})'.format(
                    config_settings['gui_settings'], filepath)))
            config_settings['gui_settings'] = filepath
        except Exception as e:
            if filepath:
                self.log('The filepath was invalid --- could not load settings. Loading blank GUI.')
            config_settings = self._DEFAULT_CONFIG


            for x in self._DEFAULT_CONFIG.keys():
                if x in config_settings:
                    if not os.path.exists(config_settings[x]):
                        try:
                            os.makedirs(config_settings[x])
                        except Exception:
                            config_settings[x] = self._DEFAULT_CONFIG[x]
                            os.makedirs(config_settings[x])
                            print(('WARNING: failed validating or creating path: set to default path'.format(config_settings[x])))
                else:
                    config_settings[x] = self._DEFAULT_CONFIG[x]
                    os.makedirs(config_settings[x])
                    print(('WARNING: path {:s} not specified set to default {:s}'.format(x, config_settings[x])))

        # check if file_name is a valid filename
        if filepath is not None and os.path.exists(os.path.dirname(filepath)):
            config_settings['gui_settings'] = filepath

        self.gui_settings = config_settings
        if(config):
            self.gui_settings_hidden = config['gui_settings_hidden']
        else:
            self.gui_settings_hidden['experiment_source_folder'] = ''

        self.devices, self.experiments, self.probes = load_settings(full_filepath)


        self.refresh_tree(self.tree_gui_settings, self.gui_settings)
        self.refresh_tree(self.tree_experiments, self.experiments)
        self.refresh_tree(self.tree_settings, self.devices)

        self._hide_parameters(filepath)


    def _hide_parameters(self, file_name):
        """
        hide the parameters that had been hidden
        Args:
            file_name: config file that has the information about which parameters are hidden

        """
        try:
            in_data = load_aqs_file(file_name)
        except:
            in_data = {}

        def set_item_visible(item, is_visible):
            if isinstance(is_visible, dict):
                for child_id in range(item.childCount()):
                    child = item.child(child_id)
                    if child.name in is_visible:
                        set_item_visible(child, is_visible[child.name])
            else:
                item.visible = is_visible

        if "experiments_hidden_parameters" in in_data:
            # consistency check
            if len(list(in_data["experiments_hidden_parameters"].keys())) == self.tree_experiments.topLevelItemCount():

                for index in range(self.tree_experiments.topLevelItemCount()):
                    item = self.tree_experiments.topLevelItem(index)
                    # if item.name in in_data["experiments_hidden_parameters"]:
                    set_item_visible(item, in_data["experiments_hidden_parameters"][item.name])
            else:
                print('WARNING: settings for hiding parameters does\'t seem to match other settings')
        # else:
        #     print('WARNING: no settings for hiding parameters all set to default')

    # def save_config(self, filepath):
    #     """
    #     saves gui configuration to out_file_name
    #     Args:
    #         filepath: name of file
    #     """
    #     def get_hidden_parameter(item):
    #
    #         num_sub_elements = item.childCount()
    #
    #         if num_sub_elements == 0:
    #             dictator = {item.name : item.visible}
    #         else:
    #             dictator = {item.name:{}}
    #             for child_id in range(num_sub_elements):
    #                 dictator[item.name].update(get_hidden_parameter(item.child(child_id)))
    #         return dictator
    #
    #
    #
    #
    #     print('GD tmp filepath', filepath)
    #     try:
    #         filepath = str(filepath)
    #         if not os.path.exists(os.path.dirname(filepath)):
    #             os.makedirs(os.path.dirname(filepath))
    #             self.log('ceated dir ' + os.path.dirname(filepath))
    #
    #         # build a dictionary for the configuration of the hidden parameters
    #         dictator = {}
    #         for index in range(self.tree_experiments.topLevelItemCount()):
    #             experiment_item = self.tree_experiments.topLevelItem(index)
    #             dictator.update(get_hidden_parameter(experiment_item))
    #
    #         dictator = {"gui_settings": self.gui_settings, "gui_settings_hidden": self.gui_settings_hidden, "experiments_hidden_parameters":dictator}
    #
    #         # update the internal dictionaries from the trees in the gui
    #         for index in range(self.tree_experiments.topLevelItemCount()):
    #             experiment_item = self.tree_experiments.topLevelItem(index)
    #             self.update_experiment_from_item(experiment_item)
    #
    #         dictator.update({'devices': {}, 'experiments': {}, 'probes': {}})
    #
    #         for device in self.devices.values():
    #             dictator['devices'].update(device.to_dict())
    #         for experiment in self.experiments.values():
    #             dictator['experiments'].update(experiment.to_dict())
    #
    #         for device, probe_dict in self.probes.items():
    #             dictator['probes'].update({device: ','.join(list(probe_dict.keys()))})
    #
    #         with open(filepath, 'w') as outfile:
    #             json.dump(dictator, outfile, indent=4)
    #         self.log('Saved GUI configuration (location: {:s})'.format(filepath))
    #
    #     except Exception:
    #         msg = QtWidgets.QMessageBox()
    #         msg.setText("Saving to {:s} failed."
    #                     "Please use 'save as' to define a valid path for the gui.".format(filepath))
    #         msg.exec_()
    #     try:
    #         save_config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, 'save_config.json'))
    #         if os.path.isfile(save_config_path) and os.access(save_config_path, os.R_OK):
    #             with open(save_config_path, 'w') as outfile:
    #                 json.dump({'last_save_path': filepath}, outfile, indent=4)
    #         else:
    #             with io.open(save_config_path, 'w') as save_config_file:
    #                 save_config_file.write(json.dumps({'last_save_path': filepath}))
    #         self.log('Saved save_config.json')
    #     except Exception:
    #         msg = QtWidgets.QMessageBox()
    #         msg.setText("Saving save_config.json failed (:s). Check if use has write access to this folder.".format(save_config_path))
    #         msg.exec_()

    def save_config(self, filepath):
        """
        Save complete workspace state to a workspace configuration file in the workspace_configs directory.
        This includes devices, experiments, probes, GUI settings, and hidden parameters.
        """
        # If filepath is just a name, save it to the workspace_configs directory
        if not Path(filepath).parent.name:
            workspace_dir = self.paths['workspace_config_dir']
            fp = workspace_dir / f"{filepath}.json"
        else:
            fp = Path(filepath)
            
        try:
            # 1) Load any existing base config (preserves other keys: paths, devices, etc.)
            base = load_config(fp)

            # 2) Build your dicts
            # 2a) Hidden parameters tree
            def get_hidden(item):
                # Check if item has the required attributes (AQuISSQTreeItem)
                if not hasattr(item, 'name') or not hasattr(item, 'visible'):
                    return {}
                
                if item.childCount() == 0:
                    return {item.name: item.visible}
                d = {}
                for i in range(item.childCount()):
                    d.update(get_hidden(item.child(i)))
                return {item.name: d}

            hidden = {}
            for idx in range(self.tree_experiments.topLevelItemCount()):
                hidden.update(get_hidden(self.tree_experiments.topLevelItem(idx)))

            # 2b) Device & experiment state
            dev_dict = {}
            for dev in self.devices.values():
                dev_dict.update(dev.to_dict())

            exp_dict = {}
            for exp in self.experiments.values():
                exp_dict.update(exp.to_dict())

            probe_dict = {
                dev: ",".join(self.probes[dev].keys())
                for dev in self.probes
            }

            # 3) Merge everything
            merged = merge_config(
                base,
                gui_settings=self.gui_settings,
                hidden_params=hidden,
                devices=dev_dict,
                experiments=exp_dict,
                probes=probe_dict
            )

            # 4) Save atomic JSON
            save_config(fp, merged)
            self.log(f"Saved workspace configuration to {fp}")

            # 5) Also remember last save path
            last_cfg = get_project_root() / "src" / "gui_config.json"
            last = load_config(last_cfg)
            last["last_save_path"] = str(fp)
            save_config(last_cfg, last)
            self.log(f"Updated last_save_path in {last_cfg}")

        except Exception as e:
            gui_logger.error(f"Failed to save config: {e}")
            gui_logger.error(f"Traceback: {traceback.format_exc()}")
            QtWidgets.QMessageBox.critical(
                self,
                "Save Error",
                f"Failed to save config:\n{e}"
            )


    def save_dataset(self, out_file_name):
        """
        saves current dataset to out_file_name
        Args:
            out_file_name: name of file
        """

        for time_tag, experiment in self.data_sets.items():
            experiment.save(os.path.join(out_file_name, '{:s}.aqss'.format(time_tag)))


# In order to set the precision when editing floats, we need to override the default Editor widget that
# pops up over the text when you click. To do that, we create a custom Editor Factory so that the QTreeWidget
# uses the custom spinbox when editing floats
class CustomEditorFactory(QtWidgets.QItemEditorFactory):
    def createEditor(self, type, QWidget):
        if type == QtCore.QVariant.Double or type == QtCore.QVariant.Int:
            spin_box = QtWidgets.QLineEdit(QWidget)
            return spin_box

        if type == QtCore.QVariant.List or type == QtCore.QVariant.StringList:
            combo_box = QtWidgets.QComboBox(QWidget)
            combo_box.setFocusPolicy(QtCore.Qt.StrongFocus)
            return combo_box

        else:
            return super(CustomEditorFactory, self).createEditor(type, QWidget)