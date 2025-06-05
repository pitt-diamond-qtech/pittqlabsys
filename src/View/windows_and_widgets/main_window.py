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
from PyQt5.QtCore import QThread, pyqtSlot, Qt
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import pyqtgraph as pg

from src.core import Parameter, Device, Experiment, Probe
from src.core.experiment_iterator import ExperimentIterator
from src.core.read_probes import ReadProbes
from src.View.windows_and_widgets import AQuISSQTreeItem, LoadDialog, LoadDialogProbes, ExportDialog, PyQtgraphWidget, PyQtCoordinatesBar
from src.Model.experiments.select_points import SelectPoints
from src.core.read_write_functions import load_aqs_file
from src.core.helper_functions import get_project_root

import os, io, json, webbrowser, datetime, operator
import numpy as np
from collections import deque
from functools import reduce
from pathlib import Path




# load the basic old_gui either from .ui file or from precompiled .py file
print(os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
try:
    thisdir = get_project_root()
    #qtdesignerfile = thisdir / 'View/ui_files/main_window.ui'  # this is the .ui file created in QtCreator
    ui_file_path = thisdir / 'View/ui_files/main_window.ui'
    Ui_MainWindow, QMainWindow = loadUiType(ui_file_path) # with this we don't have to convert the .ui file into a python file!
except (ImportError, IOError):
    # load precompiled old_gui, to complite run pyqt_uic main_window.ui -o main_window.py
    from src.View.compiled_ui_files.main_window import Ui_MainWindow
    from PyQt5.QtWidgets import QMainWindow
    print('Warning: on-the-fly conversion of main_window.ui file failed, loaded .py file instead.\n')


class CustomEventFilter(QtCore.QObject):
    def eventFilter(self, QObject, QEvent):
        if (QEvent.type() == QtCore.QEvent.Wheel):
            QEvent.ignore()
            return True

        return QtWidgets.QWidget.eventFilter(QObject, QEvent)


class MainWindow(QMainWindow, Ui_MainWindow):
    application_path = os.path.abspath(os.path.join(os.path.expanduser("~"), 'Experiments\\AQuISS_default_save_location'))

    _DEFAULT_CONFIG = {
        "data_folder": os.path.join(application_path, "data"),
        "probes_folder": os.path.join(application_path,"probes_auto_generated"),
        "device_folder": os.path.join(application_path, "devices_auto_generated"),
        "experiments_folder": os.path.join(application_path, "experiments_auto_generated"),
        "probes_log_folder": os.path.join(application_path, "aqs_tmp"),
        "gui_settings": os.path.join(application_path, "src_config.aqs")
    }


    startup_msg = '\n\n\
    ======================================================\n\
    =============== Starting AQuISS Python LAB  =============\n\
    ======================================================\n\n'

    def __init__(self, filepath=None):
        """
        MainWindow(intruments, experiments, probes)
            - intruments: depth 1 dictionary where keys are device names and keys are device classes
            - experiments: depth 1 dictionary where keys are experiment names and keys are experiment classes
            - probes: depth 1 dictionary where to be decided....?

        MainWindow(settings_file)
            - settings_file is the path to a json file that contains all the settings for the old_gui

        Returns:

        """

        print(self.startup_msg)
        self.config_filepath = None
        super(MainWindow, self).__init__()
        self.setupUi(self)

        def setup_trees():
            # COMMENT_ME

            # define data container
            self.history = deque(maxlen=500)  # history of executed commands
            self.history_model = QtGui.QStandardItemModel(self.list_history)
            self.list_history.setModel(self.history_model)
            self.list_history.show()

            self.tree_experiments.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
            self.tree_probes.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
            self.tree_settings.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)

            self.tree_gui_settings.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
            self.tree_gui_settings.doubleClicked.connect(self.edit_tree_item)

            self.current_experiment = None
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


            self.btn_save_gui.triggered.connect(self.btn_clicked)
            self.btn_load_gui.triggered.connect(self.btn_clicked)
            self.btn_about.triggered.connect(self.btn_clicked)
            self.btn_exit.triggered.connect(self.close)

            self.actionSave.triggered.connect(self.btn_clicked)
            self.actionExport.triggered.connect(self.btn_clicked)
            self.actionGo_to_AQuISS_GitHub_page.triggered.connect(self.btn_clicked)

            self.btn_load_devices.clicked.connect(self.btn_clicked)
            self.btn_load_experiments.clicked.connect(self.btn_clicked)
            self.btn_load_probes.clicked.connect(self.btn_clicked)

            # Helper function to make only column 1 editable
            def onExperimentParamClick(item, column):
                tree = item.treeWidget()
                if column == 1 and not isinstance(item.value, (Experiment, Device)) and not item.is_point():
                    # self.tree_experiments.editItem(item, column)
                    tree.editItem(item, column)

            # tree structures
            self.tree_experiments.itemClicked.connect(
                lambda: onExperimentParamClick(self.tree_experiments.currentItem(), self.tree_experiments.currentColumn()))
            self.tree_experiments.itemChanged.connect(lambda: self.update_parameters(self.tree_experiments))
            self.tree_experiments.itemClicked.connect(self.btn_clicked)
            # self.tree_experiments.installEventFilter(self)
            # QtWidgets.QTreeWidget.installEventFilter(self)


            self.tabWidget.currentChanged.connect(lambda : self.switch_tab())
            self.tree_dataset.clicked.connect(lambda: self.btn_clicked())

            self.tree_settings.itemClicked.connect(
                lambda: onExperimentParamClick(self.tree_settings.currentItem(), self.tree_settings.currentColumn()))
            self.tree_settings.itemChanged.connect(lambda: self.update_parameters(self.tree_settings))
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
        setup_trees()

        connect_controls()

        if filepath is None:
            path_to_config = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, 'save_config.json'))
            if os.path.isfile(path_to_config) and os.access(path_to_config, os.R_OK):
                print('path_to_config', path_to_config)
                with open(path_to_config) as f:
                    config_data = json.load(f)
                if 'last_save_path' in config_data.keys():
                    self.config_filepath = config_data['last_save_path']
                    self.log('Checking for previous save of GUI here: {0}'.format(self.config_filepath))
            else:
                self.log('Starting with blank GUI; configuration files will be saved here: {0}'.format(self._DEFAULT_CONFIG["gui_settings"]))

        elif os.path.isfile(filepath) and os.access(filepath, os.R_OK):
            self.config_filepath = filepath

        elif not os.path.isfile(filepath):
            self.log('Could not find file given to open --- starting with a blank GUI')

        self.devices = {}
        self.experiments = {}
        self.probes = {}
        self.gui_settings = {'experiments_folder': '', 'data_folder': ''}
        self.gui_settings_hidden = {'experiments_source_folder': ''}

        self.load_config(self.config_filepath)

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

        if self.config_filepath is None:
            self.config_filepath = os.path.join(self._DEFAULT_CONFIG["gui_settings"], 'gui.aqs')

    def closeEvent(self, event):
        """
        things to be done when gui closes, like save the settings
        """

        self.save_config(self.gui_settings['gui_settings'])
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
            if item.is_point():
               # item_x = item.child(1)
                item_x = item.child(0)
                if mouse_event.xdata is not None:
                    self.tree_experiments.setCurrentItem(item_x)
                    item_x.value = float(mouse_point.x())
                    item_x.setText(1, '{:0.3f}'.format(float(mouse_point.x())))
               # item_y = item.child(0)
                item_y = item.child(1)
                if mouse_event.ydata is not None:
                    self.tree_experiments.setCurrentItem(item_y)
                    item_y.value = float(mouse_point.y())
                    item_y.setText(1, '{:0.3f}'.format(float(mouse_point.y())))

                # focus back on item
                self.tree_experiments.setCurrentItem(item)
            else:
                if item.parent() is not None:
                    if item.parent().is_point():
                        if item == item.parent().child(1):
                            if mouse_event.xdata is not None:
                                item.setData(1, 2, float(mouse_point.x()))
                        if item == item.parent().child(0):
                            if mouse_event.ydata is not None:
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


            # update experiments so that current settings do not get lost
            for index in range(self.tree_experiments.topLevelItemCount()):
                experiment_item = self.tree_experiments.topLevelItem(index)
                self.update_experiment_from_item(experiment_item)


            dialog = LoadDialog(elements_type="experiments", elements_old=self.experiments,
                                filename=self.gui_settings['experiments_folder'])
            if dialog.exec_():
                self.gui_settings['experiments_folder'] = str(dialog.txt_probe_log_path.text())
                experiments = dialog.get_values()
                added_experiments = set(experiments.keys()) - set(self.experiments.keys())
                removed_experiments = set(self.experiments.keys()) - set(experiments.keys())

                if 'data_folder' in list(self.gui_settings.keys()) and os.path.exists(self.gui_settings['data_folder']):
                    data_folder_name = self.gui_settings['data_folder']
                else:
                    data_folder_name = None

                # create instances of new devices/experiments
                self.experiments, loaded_failed, self.devices = Experiment.load_and_append(
                    experiment_dict={name: experiments[name] for name in added_experiments},
                    experiments=self.experiments,
                    devices=self.devices,
                    log_function=self.log,
                    data_path=data_folder_name,
                    raise_errors=False)

                # delete instances of new devices/experiments that have been deselected
                for name in removed_experiments:
                    del self.experiments[name]

    def btn_clicked(self):
        """
        slot to which connect buttons
        """
        sender = self.sender()
        self.probe_to_plot = None

        def start_button():
            """
            starts the selected experiment
            """
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

                # start thread, i.e. experiment
                experiment_thread.start()

                self.current_experiment = experiment
                self.btn_start_experiment.setEnabled(False)
                # self.tabWidget.setEnabled(False)

                if isinstance(self.current_experiment, ExperimentIterator):
                    self.btn_skip_subexperiment.setEnabled(True)


            else:
                self.log('User tried to run a experiment without one selected.')

        def stop_button():
            """
            stops the current experiment
            """
            if self.current_experiment is not None and self.current_experiment.is_running:
                self.current_experiment.stop()
            else:
                self.log('User clicked stop, but there isn\'t anything running...this is awkward. Re-enabling start button anyway.')
            self.btn_start_experiment.setEnabled(True)

        def skip_button():
            """
            Skips to the next experiment if the current experiment is a Iterator experiment
            """
            if self.current_experiment is not None and self.current_experiment.is_running and isinstance(self.current_experiment,
                                                                                                 ExperimentIterator):
                self.current_experiment.skip_next()
            else:
                self.log('User clicked skip, but there isn\'t a iterator experiment running...this is awkward.')

        def validate_button():
            """
            validates the selected experiment
            """
            item = self.tree_experiments.currentItem()

            if item is not None:
                experiment, path_to_experiment, experiment_item = item.get_experiment()
                self.update_experiment_from_item(experiment_item)
                experiment.is_valid()
                experiment.plot_validate([self.pyqtgraphwidget_1.graph, self.pyqtgraphwidget_2.graph])
                #the following 2 lines dont seem to do what I want ie they dont change the viewbox so that mouse position tracking updates for the new plots
                self.pyqtgraphwidget_1.update()
                self.pyqtgraphwidget_2.update()
                print('validate button presss triggered')

        def store_experiment_data():
            """
            updates the internal self.data_sets with selected experiment and updates tree self.fill_dataset_tree
            """
            item = self.tree_experiments.currentItem()
            if item is not None:
                experiment, path_to_experiment, _ = item.get_experiment()
                experiment_copy = experiment.duplicate()
                time_tag = experiment.start_time.strftime('%y%m%d-%H_%M_%S')

                self.data_sets.update({time_tag : experiment_copy})

                self.fill_dataset_tree(self.tree_dataset, self.data_sets)

        def save_data():
            """"
            saves the selected experiment (where is contained in the experiment itself)
            """
            indecies = self.tree_dataset.selectedIndexes()
            model = indecies[0].model()
            rows = list(set([index.row()for index in indecies]))

            for row in rows:
                time_tag = str(model.itemFromIndex(model.index(row, 0)).text())
                name_tag = str(model.itemFromIndex(model.index(row, 1)).text())
                path = self.gui_settings['data_folder']
                experiment = self.data_sets[time_tag]
                experiment.update({'tag' : name_tag, 'path': path})
                experiment.save_data()
                experiment.save_image_to_disk()
                experiment.save_aqs()
                experiment.save_log()

        def delete_data():
            """
            deletes the data from the dataset
            Returns:
            """
            indecies = self.tree_dataset.selectedIndexes()
            model = indecies[0].model()
            rows = list(set([index.row()for index in indecies]))

            for row in rows:
                time_tag = str(model.itemFromIndex(model.index(row, 0)).text())
                del self.data_sets[time_tag]

                model.removeRows(row,1)

        def load_probes():
            """
            opens file dialog to load probes into gui
            """

            # if the probe has never been started it can not be disconnected so we catch that error
            try:
                self.read_probes.updateProgress.disconnect()
                self.read_probes.quit()
                # self.read_probes.stop()
            except RuntimeError:
                pass
            dialog = LoadDialogProbes(probes_old=self.probes, filename=self.gui_settings['probes_folder'])
            if dialog.exec_():
                self.gui_settings['probes_folder'] = str(dialog.txt_probe_log_path.text())
                probes = dialog.get_values()
                added_devices = list(set(probes.keys()) - set(self.probes.keys()))
                removed_devices = list(set(self.probes.keys()) - set(probes.keys()))
                # create instances of new probes
                self.probes, loaded_failed, self.devices = Probe.load_and_append(
                    probe_dict=probes,
                    probes={},
                    devices=self.devices)
                if not loaded_failed:
                    print(('WARNING following probes could not be loaded', loaded_failed, len(loaded_failed)))


                # restart the readprobes thread
                del self.read_probes
                self.read_probes = ReadProbes(self.probes)
                self.read_probes.start()
                self.tree_probes.clear() # clear tree because the probe might have changed
                self.read_probes.updateProgress.connect(self.update_probes)
                self.tree_probes.expandAll()

        def load_devices():
            """
            opens file dialog to load devices into gui
            """
            if 'device_folder' in self.gui_settings:
                dialog = LoadDialog(elements_type="devices", elements_old=self.devices,
                                    filename=self.gui_settings['device_folder'])

            else:
                dialog = LoadDialog(elements_type="devices", elements_old=self.devices)

            if dialog.exec_():
                self.gui_settings['device_folder'] = str(dialog.txt_probe_log_path.text())
                devices = dialog.get_values()
                added_devices = set(devices.keys()) - set(self.devices.keys())
                removed_devices = set(self.devices.keys()) - set(devices.keys())
                # print('added_devices', {name: devices[name] for name in added_devices})

                # create instances of new devices
                self.devices, loaded_failed = Device.load_and_append(
                    {name: devices[name] for name in added_devices}, self.devices)
                if len(loaded_failed)>0:
                    print(('WARNING following device could not be loaded', loaded_failed))
                # delete instances of new devices/experiments that have been deselected
                for name in removed_devices:
                    del self.devices[name]

        def plot_data(sender):
            """
            plots the data of the selected experiment
            """
            if sender == self.tree_dataset:
                index = self.tree_dataset.selectedIndexes()[0]
                model = index.model()
                time_tag = str(model.itemFromIndex(model.index(index.row(), 0)).text())
                experiment = self.data_sets[time_tag]
                self.plot_experiment(experiment)
            elif sender == self.tree_experiments:
                item = self.tree_experiments.currentItem()
                if item is not None:
                    experiment, path_to_experiment, _ = item.get_experiment()
                # only plot if experiment has been selected but not if a parameter has been selected
                if path_to_experiment == []:
                    self.plot_experiment(experiment)

        def save():
            self.save_config(self.gui_settings['gui_settings'])
        if sender is self.btn_start_experiment:
            start_button()
        elif sender is self.btn_stop_experiment:
            stop_button()
        elif sender is self.btn_skip_subexperiment:
            skip_button()
        elif sender is self.btn_validate_experiment:
            validate_button()
        elif sender in (self.tree_dataset, self.tree_experiments):
            plot_data(sender)
        elif sender is self.btn_store_experiment_data:
            store_experiment_data()
        elif sender is self.btn_save_data:
            save_data()
        elif sender is self.btn_delete_data:
            delete_data()
        # elif sender is self.btn_plot_probe:
        elif sender is self.chk_probe_plot:
            if self.chk_probe_plot.isChecked():
                item = self.tree_probes.currentItem()
                if item is not None:
                    if item.name in self.probes:
                        #selected item is an device not a probe, maybe plot all the probes...
                        self.log('Can\'t plot, No probe selected. Select probe and try again!')
                    else:
                        device = item.parent().name
                        self.probe_to_plot = self.probes[device][item.name]
                else:
                    self.log('Can\'t plot, No probe selected. Select probe and try again!')
            else:
                self.probe_to_plot = None
        elif sender is self.btn_save_gui:
            # get filename
            filepath, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Save gui settings to file', self.config_filepath, filter = '*.aqs')

            #in case the user cancels during the prompt, check that the filepath is not an empty string
            if filepath:
                filename, file_extension = os.path.splitext(filepath)
                if file_extension != '.aqs':
                    filepath = filename + ".aqs"
                filepath = os.path.normpath(filepath)
                self.save_config(filepath)
                self.gui_settings['gui_settings'] = filepath
                self.refresh_tree(self.tree_gui_settings, self.gui_settings)
        elif sender is self.btn_load_gui:
            # get filename
            fname = QtWidgets.QFileDialog.getOpenFileName(self, 'Load gui settings from file',  self.gui_settings['data_folder'], filter = '*.aqs')
            self.load_config(fname[0])
        elif sender is self.btn_about:
            msg = QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Information)
            msg.setText("src: AQuISS Laboratory Equipment Control for Scientific Experiments")
            msg.setInformativeText("This software was developed by Gurudev Dutt and Jeffrey Guest at"
                                   "University of Pittsburgh and Argonne National Laboratory. It is licensed under the LPGL licence. For more information,"
                                   "visit the GitHub page at github.com/gurudevdutt/AQuISS . We thank the Pylabcontrol and B26_Toolkit project which significantly inspired "
                                   "this project.")
            msg.setWindowTitle("About")
            # msg.setDetailedText("some stuff")
            msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
            # msg.buttonClicked.connect(msgbtn)
            retval = msg.exec_()
        # elif (sender is self.btn_load_devices) or (sender is self.btn_load_experiments):
        elif sender in (self.btn_load_devices, self.btn_load_experiments, self.btn_load_probes):
            if sender is self.btn_load_devices:
                load_devices()
            elif sender is self.btn_load_experiments:
                self.load_experiments()
            elif sender is self.btn_load_probes:
                load_probes()
            # refresh trees
            self.refresh_tree(self.tree_experiments, self.experiments)
            self.refresh_tree(self.tree_settings, self.devices)
        elif sender is self.actionSave:
            self.save_config(self.gui_settings['gui_settings'])
        elif sender is self.actionGo_to_AQuISS_GitHub_page:
            webbrowser.open('https://github.com/gurudevdutt/AQuISS')
        elif sender is self.actionExport:
            export_dialog = ExportDialog()
            export_dialog.target_path.setText(self.gui_settings['experiments_folder'])
            if self.gui_settings_hidden['experiments_source_folder']:
                export_dialog.source_path.setText(self.gui_settings_hidden['experiments_source_folder'])
            if export_dialog.source_path.text():
                export_dialog.reset_available(export_dialog.source_path.text())
            #exec_() blocks while export dialog is used, subsequent code will run on dialog closing
            export_dialog.exec_()
            self.gui_settings.update({'experiments_folder': export_dialog.target_path.text()})
            self.fill_treeview(self.tree_gui_settings, self.gui_settings)
            self.gui_settings_hidden.update({'experiments_source_folder': export_dialog.source_path.text()})

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
    def update_parameters(self, treeWidget):
        """
        updates the internal dictionaries for experiments and devices with values from the respective trees

        treeWidget: the tree from which to update

        """

        if treeWidget == self.tree_settings:

            item = treeWidget.currentItem()



            device, path_to_device = item.get_device()

            # build nested dictionary to update device
            dictator = item.value
            for element in path_to_device:
                dictator = {element: dictator}

            # get old value from device
            old_value = device.settings
            path_to_device.reverse()
            for element in path_to_device:
                old_value = old_value[element]

            # send new value from tree to device
            device.update(dictator)

            new_value = item.value
            if new_value is not old_value:
                msg = "changed parameter {:s} from {:s} to {:s} on {:s}".format(item.name, str(old_value),
                                                                                str(new_value), device.name)
            else:
                msg = "did not change parameter {:s} on {:s}".format(item.name, device.name)

            self.log(msg)
        elif treeWidget == self.tree_experiments:

            item = treeWidget.currentItem()
            experiment, path_to_experiment, _ = item.get_experiment()

            # check if changes value is from an device
            device, path_to_device = item.get_device()
            if device is not None:

                new_value = item.value


                msg = "changed parameter {:s} to {:s} in {:s}".format(item.name,
                                                                                str(new_value),
                                                                                experiment.name)
            else:
                new_value = item.value
                msg = "changed parameter {:s} to {:s} in {:s}".format(item.name,
                                                                            str(new_value),
                                                                            experiment.name)
            self.log(msg)

    def plot_experiment(self, experiment):
        """
        Calls the plot function of the experiment, and redraws both plots
        Args:
            experiment: experiment to be plotted
        """

        experiment.plot([self.pyqtgraphwidget_1.graph, self.pyqtgraphwidget_2.graph])
        #self.matplotlibwidget_1.draw()
        #self.matplotlibwidget_2.draw()


    @pyqtSlot(int)
    def update_status(self, progress):
        """
        waits for a signal emitted from a thread and updates the gui
        Args:
            progress:
        Returns:

        """

        # interval at which the gui will be updated, if requests come in faster than they will be ignored
        update_interval = 0.2

        now = datetime.datetime.now()

        if not self._last_progress_update is None and now-self._last_progress_update < datetime.timedelta(seconds=update_interval):
            return

        self._last_progress_update = now

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

        tree.clear()
        assert isinstance(parameters, (dict, Parameter))

        for key, value in parameters.items():
            if isinstance(value, Parameter):
                AQuISSQTreeItem(tree, key, value, parameters.valid_values[key], parameters.info[key])
            else:
                AQuISSQTreeItem(tree, key, value, type(value), '')

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
            child_name = QtWidgets.QStandardItem(key)

            if isinstance(value, dict):
                for key_child, value_child in value.items():
                    add_element(child_name, key_child, value_child)
                item.appendRow(child_name)
            else:
                child_value = QtWidgets.QStandardItem(str(value))

                item.appendRow([child_name, child_value])

        for index, (key, value) in enumerate(input_dict.items()):

            if isinstance(value, dict):
                item = QtWidgets.QStandardItem(key)
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
                    path, _ = QtWidgets.QFileDialog.getSaveFileName(self, caption = 'Select a file:', directory = path, filter = '*.aqs')
                    if path:
                        name, extension = os.path.splitext(path)
                        if extension != '.aqs':
                            path = name + ".aqs"
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
            tree.itemChanged.connect(lambda: self.update_parameters(tree))
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

        tree.model().removeRows(0, tree.model().rowCount())
        for index, (time, experiment) in enumerate(data_sets.items()):
            name = experiment.settings['tag']
            type = experiment.name

            item_time = QtGui.QStandardItem(str(time))
            item_name = QtGui.QStandardItem(str(name))
            item_type = QtGui.QStandardItem(str(type))

            item_time.setSelectable(False)
            item_time.setEditable(False)
            item_type.setSelectable(False)
            item_type.setEditable(False)

            tree.model().appendRow([item_time, item_name, item_type])

    def load_config(self, filepath=None):
        """
        checks if the file is a valid config file
        Args:
            filepath:

        """

        # load config or default if invalid

        def load_settings(filepath):
            """
            loads a old_gui settings file (a json dictionary)
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

        self.devices, self.experiments, self.probes = load_settings(filepath)


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

    def save_config(self, filepath):
        """
        saves gui configuration to out_file_name
        Args:
            filepath: name of file
        """
        def get_hidden_parameter(item):

            num_sub_elements = item.childCount()

            if num_sub_elements == 0:
                dictator = {item.name : item.visible}
            else:
                dictator = {item.name:{}}
                for child_id in range(num_sub_elements):
                    dictator[item.name].update(get_hidden_parameter(item.child(child_id)))
            return dictator




        print('GD tmp filepath', filepath)
        try:
            filepath = str(filepath)
            if not os.path.exists(os.path.dirname(filepath)):
                os.makedirs(os.path.dirname(filepath))
                self.log('ceated dir ' + os.path.dirname(filepath))

            # build a dictionary for the configuration of the hidden parameters
            dictator = {}
            for index in range(self.tree_experiments.topLevelItemCount()):
                experiment_item = self.tree_experiments.topLevelItem(index)
                dictator.update(get_hidden_parameter(experiment_item))

            dictator = {"gui_settings": self.gui_settings, "gui_settings_hidden": self.gui_settings_hidden, "experiments_hidden_parameters":dictator}

            # update the internal dictionaries from the trees in the gui
            for index in range(self.tree_experiments.topLevelItemCount()):
                experiment_item = self.tree_experiments.topLevelItem(index)
                self.update_experiment_from_item(experiment_item)

            dictator.update({'devices': {}, 'experiments': {}, 'probes': {}})

            for device in self.devices.values():
                dictator['devices'].update(device.to_dict())
            for experiment in self.experiments.values():
                dictator['experiments'].update(experiment.to_dict())

            for device, probe_dict in self.probes.items():
                dictator['probes'].update({device: ','.join(list(probe_dict.keys()))})

            with open(filepath, 'w') as outfile:
                json.dump(dictator, outfile, indent=4)
            self.log('Saved GUI configuration (location: {:s})'.format(filepath))

        except Exception:
            msg = QtWidgets.QMessageBox()
            msg.setText("Saving to {:s} failed."
                        "Please use 'save as' to define a valid path for the gui.".format(filepath))
            msg.exec_()
        try:
            save_config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, 'save_config.json'))
            if os.path.isfile(save_config_path) and os.access(save_config_path, os.R_OK):
                with open(save_config_path, 'w') as outfile:
                    json.dump({'last_save_path': filepath}, outfile, indent=4)
            else:
                with io.open(save_config_path, 'w') as save_config_file:
                    save_config_file.write(json.dumps({'last_save_path': filepath}))
            self.log('Saved save_config.json')
        except Exception:
            msg = QtWidgets.QMessageBox()
            msg.setText("Saving save_config.json failed (:s). Check if use has write access to this folder.".format(save_config_path))
            msg.exec_()




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