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


import traceback, os
from pathlib import Path

from PyQt5 import QtGui, QtWidgets
from PyQt5.uic import loadUiType

from src.tools.export_default import find_experiments_in_python_files, python_file_to_aqs, find_devices_in_python_files
from src.core.helper_functions import module_name_from_path

# load the basic old_gui either from .ui file or from precompiled .py file
try:
    ui_file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, 'ui_files', 'import_window.ui'))
    Ui_Dialog, QDialog = loadUiType(ui_file_path) # with this we don't have to convert the .ui file into a python file!
except (ImportError, IOError):
    from src.View.compiled_ui_files.gui_compiled_import_window import Ui_Dialog
    from PyQt5.QtWidgets import QMainWindow
    from PyQt5.QtWidgets import QDialog
    print('Warning: on the fly conversion of load_dialog.ui file failed, loaded .py file instead!!\n')


class ExportDialog(QDialog, Ui_Dialog):
    """
    This launches a dialog to allow exporting of experiments to .aqs files.
    QDialog, Ui_Dialog: Define the UI and PyQt files to be used to define the dialog box
    """

    def __init__(self, existing_devices=None):
        super(ExportDialog, self).__init__()
        self.setupUi(self)
        
        # Store existing devices for use during conversion
        self.existing_devices = existing_devices or {}

        # create models for tree structures, the models reflect the data
        self.list_experiment_model = QtGui.QStandardItemModel()
        self.list_experiment.setModel(self.list_experiment_model)
        self.error_array = {}

        self.list_experiment.selectionModel().selectionChanged.connect(self.display_info)
        self.cmb_select_type.currentIndexChanged.connect(self.class_type_changed)

        #
        # # connect the buttons
        self.btn_open_source.clicked.connect(self.open_file_dialog)
        self.btn_open_target.clicked.connect(self.open_file_dialog)
        self.btn_select_all.clicked.connect(self.select_all)
        self.btn_select_none.clicked.connect(self.select_none)
        self.btn_export.clicked.connect(self.export)

        # package = get_python_package(os.getcwd())
        # package, path = module_name_from_path(os.getcwd())
        # self.source_path.setText(os.path.normpath(os.path.join(path + '\\' + package.split('.')[0] + '\\experiments')))
        # self.target_path.setText(os.path.normpath(os.path.join(path + '\\' + package.split('.')[0] + '\\user_data\\experiments_auto_generated')))
        # self.reset_avaliable(self.source_path.text())

    def open_file_dialog(self):
        """
        Opens a file dialog to get the path to a file and put tha tpath in the correct textbox
        """
        dialog = QtWidgets.QFileDialog
        sender = self.sender()
        if sender == self.btn_open_source:
            textbox = self.source_path
            # Default to src/Model folder if source path is empty
            default_dir = textbox.text() if textbox.text() else str(Path(__file__).parent.parent.parent / "Model")
        elif sender == self.btn_open_target:
            textbox = self.target_path
            default_dir = textbox.text() if textbox.text() else str(Path.home() / "Experiments" / "AQuISS_default_save_location" / "experiments_auto_generated")
        
        folder = dialog.getExistingDirectory(self, 'Select a file:', default_dir, options = QtWidgets.QFileDialog.ShowDirsOnly)
        if str(folder) != '':
            textbox.setText(folder)
            # load elements from file and display in tree
            if sender == self.btn_open_source:
                self.reset_available(folder)

    def reset_available(self, folder):
        """
        Resets the dialog box by finding all available experiments that can be imported in the input folder
        :param folder: folder in which to find experiments
        """
        try:
            self.list_experiment_model.removeRows(0, self.list_experiment_model.rowCount())
            if self.cmb_select_type.currentText() == 'Experiment':
                self.available = find_experiments_in_python_files(folder)
            elif self.cmb_select_type.currentText() == 'Device':
                self.available = find_devices_in_python_files(folder)
            self.fill_list(self.list_experiment, self.available.keys())
            for key in self.available.keys():
                self.error_array.update({key: ''})
        except Exception:
            msg = QtWidgets.QMessageBox()
            msg.setText("Unable to parse all of the files in this folder to find possible experiments and devices. There are non-python files or python files that are unreadable. Please select a folder that contains only src style python files.")
            msg.exec_()

    def class_type_changed(self):
        """
        Forces a reset if the class type is changed from devices to experiments or vice versa
        """
        if self.source_path.text():
            self.reset_available(self.source_path.text())


    def fill_list(self, list, input_list):
        """
        fills a tree with nested parameters
        Args:
            tree: QtGui.QTreeView to fill
            parameters: dictionary or Parameter object which contains the information to use to fill
        """
        for name in input_list:
            # print(index, loaded_item, loaded_item_settings)
            item = QtGui.QStandardItem(name)
            item.setSelectable(True)
            item.setEditable(False)

            list.model().appendRow(item)

    def select_none(self):
        """
        Clears all selected values
        """
        self.list_experiment.clearSelection()

    def select_all(self):
        """
        Selects all values
        """
        self.list_experiment.selectAll()

    def export(self):
        """
        Exports the selected devices or experiments to .aqs files. If successful, experiment is highlighted in green. If
        failed, experiment is highlighted in red and error is printed to the error box.
        """
        selected_index = self.list_experiment.selectionModel().selectedIndexes()
        if not selected_index:
            return

        for index in selected_index:
            item = self.list_experiment.model().itemFromIndex(index)
            name = str(item.text())
            target_path = self.target_path.text()
            try:
                # Pass existing devices to enable real hardware usage during conversion
                loaded,failed = python_file_to_aqs(
                    {name: self.available[name]}, 
                    target_path, 
                    str(self.cmb_select_type.currentText()), 
                    raise_errors=True,
                    existing_devices=self.existing_devices
                )
                # Due to the windows exceptions being thrown, I have to change this code to ignore them
                # TODO: figure out what is causing the windows exceptions and fix them instead of ignoring
                if failed == {}:
                    self.error_array.update({name:'export successful!'})
                    item.setBackground(QtGui.QColor('green'))
                else:
                    self.error_array.update({name: str(traceback.format_exc())})
                    item.setBackground(QtGui.QColor('red'))
            except Exception as e:
                self.error_array.update({name: str(traceback.format_exc())})
                print(str(traceback.format_exc()))
                raise e
            # try:
            #     loaded,failed = python_file_to_aqs({name: self.available[name]}, target_path, str(self.cmb_select_type.currentText()), raise_errors = True)
            #     self.error_array.update({name: 'export successful!'})
            #     item.setBackground(QtGui.QColor('green'))
            # except Exception:
            #     self.error_array.update({name: str(traceback.format_exc())})
            #     item.setBackground(QtGui.QColor('red'))
            QtWidgets.QApplication.processEvents()
        self.list_experiment.clearSelection()

    def display_info(self):
        """
        Displays the experiment info and, if it has been attempted to be exported, the error for a given experiment. Creates
        hyperlinks in the traceback to the appropriate .py files (to be opened in the default .py editor).
        """
        sender = self.sender()
        somelist = sender.parent()
        index = somelist.selectedIndexes()
        if index != []:
            index = index[-1]
            name = str(index.model().itemFromIndex(index).text())
            self.text_error.setText(self.error_array[name])
            # self.text_error.setText('')
            # self.text_error.setOpenExternalLinks(True)
            # split_errors = self.error_array[name].split("\"")
            # #displays error message with HTML link to file where error occured, which opens in default python editor
            # for error in split_errors:
            #     if error[-3:] == '.py':
            #         error = error.replace("\\", "/") #format paths to be opened
            #         # sets up hyperlink error with filepath as displayed text in hyperlink
            #         # in future, can use anchorClicked signal to call python function when link clicked
            #         self.text_error.insertHtml("<a href = \"" + error + "\">" + error + "</a>")
            #     else:
            #         error = error.replace("\n", "<br>") #format newlines for HTML
            #         # would like to use insertPlainText here, but this is broken and ends up being inserted as more
            #         # HTML linked to the previous insertHtml, so need to insert this as HTML instead
            #         self.text_error.insertHtml(error)
            if(self.available[name]['info'] == None):
                self.text_info.setText('No information available')
            else:
                self.text_info.setText(self.available[name]['info'])


if __name__ == '__main__':
    import sys

    app = QtWidgets.QApplication(sys.argv)
    # ex = LoadDialog(elements_type = 'devices', elements_old=instuments, filename="Z:\Lab\Cantilever\Measurements\\__tmp\\test.aqs")
    # ex = LoadDialog(elements_type='experiments', elements_old=instuments)
    ex = ExportDialog()

    ex.show()
    ex.raise_()

    if ex.exec_():
        values = ex.get_values()
        print(values)

    sys.exit(app.exec_())

    # from src.core.helper_functions import module_name_from_path
    #
    # base = '__main__'
    # fp = os.path.dirname(sys.modules[base].__file__)
    #
    # m, p = module_name_from_path(fp, verbose=True)
    # print('sys.modules[base]', m)
    # print('path', p)


