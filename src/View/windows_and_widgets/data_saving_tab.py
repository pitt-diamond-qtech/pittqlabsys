from PyQt5.QtWidgets import (
    QWidget, QTreeView, QVBoxLayout, QHBoxLayout,
    QLineEdit, QFileSystemModel, QToolButton
)
from PyQt5.QtCore import QModelIndex, QDir
from PyQt5.QtGui import QIcon
from .data_saving_tab_design import Ui_Form
import os
from PyQt5.QtWidgets import QMenu, QInputDialog
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QPushButton
from pathlib import Path
from PyQt5.QtWidgets import QMessageBox, QFileDialog
from src.core.struct_hdf5 import load_data, iter_struct, is_image_array, is_scalar_or_small, normalize_value
from PyQt5.QtWidgets import QDialog, QLabel, QVBoxLayout
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtGui import QStandardItemModel, QStandardItem
import numpy as np

class data_saving_tab_view(QWidget, Ui_Form):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        # --- Navigation history ---
        self.back_stack = []
        self.forward_stack = []

        # --- File system model ---
        self.model = QFileSystemModel()
        self.model.setRootPath("")
        self.model.setFilter(QDir.AllDirs | QDir.Files | QDir.NoDotAndDotDot)

        # --- Tree view ---
        self.tree = QTreeView()
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.open_context_menu)

        self.tree.setModel(self.model)
        self.tree.doubleClicked.connect(self.on_item_double_clicked)
        self.tree.setColumnWidth(0, 280)

        # --- Header widgets ---
        self.back_btn = QToolButton()
        self.back_btn.setText("◀")
        self.back_btn.clicked.connect(self.go_back)

        self.forward_btn = QToolButton()
        self.forward_btn.setText("▶")
        self.forward_btn.clicked.connect(self.go_forward)


        self.path_header = QLineEdit()
        self.path_header.returnPressed.connect(self.on_path_entered)

        # --- Header layout ---
        header_layout = QHBoxLayout()
        header_layout.addWidget(self.back_btn)
        header_layout.addWidget(self.forward_btn)
        header_layout.addWidget(self.path_header)

        # --- Main layout ---
        layout = QVBoxLayout(self)
        layout.addLayout(header_layout)
        layout.addWidget(self.tree)
        # --- Read Data button ---
        self.read_data_btn = QPushButton("Read Data")
        self.read_data_btn.setEnabled(False)
        self.read_data_btn.clicked.connect(self.read_selected_file)

        layout.addWidget(self.read_data_btn)

        self.setLayout(layout)

        # --- Initial directory ---
        start_path = r"D:\Data"
        self.set_directory(start_path, record_history=False)
        self.data_reader = None

    # =========================
    # Navigation logic
    # =========================

    def set_directory(self, path, record_history=True):
        if not os.path.isdir(path):
            return

        current = self.current_path()
        if record_history and current:
            self.back_stack.append(current)
            self.forward_stack.clear()

        index = self.model.index(path)
        self.tree.setRootIndex(index)
        self.path_header.setText(path)

    def current_path(self):
        index = self.tree.rootIndex()
        return self.model.filePath(index)

    def go_back(self):
        if not self.back_stack:
            return
        self.forward_stack.append(self.current_path())
        path = self.back_stack.pop()
        self.set_directory(path, record_history=False)

    def go_forward(self):
        if not self.forward_stack:
            return
        self.back_stack.append(self.current_path())
        path = self.forward_stack.pop()
        self.set_directory(path, record_history=False)


    # =========================
    # User actions
    # =========================

    def on_item_double_clicked(self, index: QModelIndex):
        path = self.model.filePath(index)

        if os.path.isdir(path):
            self.set_directory(path)
            self.read_data_btn.setEnabled(False)
        else:
            print(f"File selected: {path}")
            self.read_data_btn.setEnabled(True)

    def on_path_entered(self):
        path = self.path_header.text()
        self.set_directory(path)

    def open_context_menu(self, position):
        index = self.tree.indexAt(position)

        menu = QMenu(self)

        new_folder_action = menu.addAction("New Folder")
        new_file_action = menu.addAction("New File")

        if index.isValid():
            menu.addSeparator()
            rename_action = menu.addAction("Rename")
            delete_action = menu.addAction("Delete")

        action = menu.exec_(self.tree.viewport().mapToGlobal(position))

        if action == new_folder_action:
            self.create_new_folder(index, auto_rename=True)
        elif action == new_file_action:
            self.create_new_file(index)
        elif index.isValid() and action == rename_action:
            self.rename_item(index)
        elif index.isValid() and action == delete_action:
            self.delete_item(index)

    def get_target_directory(self, index):
        if index.isValid():
            path = Path(self.model.filePath(index))
            if path.is_file():
                return path.parent
            return path
        return Path(self.current_path())

    def create_new_folder(self, index, auto_rename=False):
        target_dir = self.get_target_directory(index)

        if auto_rename:
            base_name = "New Folder"
            name = base_name
            counter = 1

            while (target_dir / name).exists():
                counter += 1
                name = f"{base_name} ({counter})"

            new_path = target_dir / name
            new_path.mkdir()

            # Select & start rename
            new_index = self.model.index(str(new_path))
            self.tree.setCurrentIndex(new_index)
            self.tree.edit(new_index)
            return

        # Manual naming fallback
        name, ok = QInputDialog.getText(self, "New Folder", "Folder name:")
        if not ok or not name:
            return

        new_path = target_dir / name
        if new_path.exists():
            QMessageBox.warning(self, "Error", "Folder already exists.")
            return

        new_path.mkdir()

    def create_new_file(self, index):
        target_dir = self.get_target_directory(index)

        name, ok = QInputDialog.getText(
            self, "New File", "File name:"
        )
        if not ok or not name:
            return

        new_path = target_dir / name

        if new_path.exists():
            QMessageBox.warning(self, "Error", "File already exists.")
            return

        try:
            new_path.touch()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def rename_item(self, index):
        path = Path(self.model.filePath(index))
        old_suffix = path.suffix if path.is_file() else ""

        new_name, ok = QInputDialog.getText(
            self, "Rename", "New name:", text=path.name
        )
        if not ok or not new_name or new_name == path.name:
            return

        if path.is_file() and Path(new_name).suffix == "":
            new_name += old_suffix

        new_path = path.parent / new_name

        if new_path.exists():
            QMessageBox.warning(self, "Error", "A file or folder with this name already exists.")
            return

        try:
            path.rename(new_path)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def delete_item(self, index):
        path = Path(self.model.filePath(index))

        reply = QMessageBox.question(
            self,
            "Delete",
            f"Are you sure you want to delete:\n\n{path.name}?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        try:
            if path.is_dir():
                import shutil
                shutil.rmtree(path)
            else:
                path.unlink()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def read_selected_file(self):
        index = self.tree.currentIndex()
        if not index.isValid():
            QMessageBox.warning(self, "No selection", "Please select a file.")
            return

        path = self.model.filePath(index)

        if os.path.isdir(path):
            QMessageBox.warning(self, "Invalid selection", "Please select a file.")
            return

        ext = Path(path).suffix.lower()
        if ext not in [".h5", ".hdf5"]:
            QMessageBox.warning(
                self,
                "Unsupported file",
                "Only .h5 and .hdf5 files are supported."
            )
            return

        try:
            # --- Load the whole file into a StructArray ---
            self.data_reader = load_data(path)
            self.show_hdf5_browser()
            print(f"File loaded successfully: {path}")
            print(f"self.data_reader {self.data_reader}")

            for path, value in iter_struct(self.data_reader):
                if is_image_array(value):
                    print("IMAGE:", path, value.shape)

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error loading file",
                f"Failed to load file:\n{e}"
            )
            self.data_reader = None

    def build_hdf5_tree(self):
        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(["HDF5 Content", "Value"])

        root = model.invisibleRootItem()

        for path, value in iter_struct(self.data_reader):
            parts = path.split("/")
            parent = root

            for p in parts:
                found = None
                for i in range(parent.rowCount()):
                    if parent.child(i).text() == p:
                        found = parent.child(i)
                        break
                if not found:
                    found = QStandardItem(p)
                    parent.appendRow(found)
                parent = found

            # Store the actual value
            parent.setData(value, Qt.UserRole)

            # --- ICONS ---
            if is_image_array(value):
                parent.setIcon(QIcon("icons/image.png"))
                # Add size info in second column
                second_col = QStandardItem(f"{value.shape[0]}x{value.shape[1]}")
                parent.parent().setChild(parent.row(), 1, second_col)
            elif isinstance(value, np.ndarray) and not is_image_array(value):
                # Vector or matrix (non-image array)
                if len(value.shape) == 1:
                    # 1D array (vector)
                    if value.shape[0] == 1:
                        # Single element array - show as "[value]" to distinguish from scalar
                        second_col = QStandardItem(f"[{normalize_value(value[0])}]")
                    else:
                        # Multi-element vector - show length
                        second_col = QStandardItem(f"Vector ({len(value)})")
                elif len(value.shape) == 2:
                    # 2D matrix
                    if value.shape[0] == 1 and value.shape[1] == 1:
                        # 1x1 matrix - show as "[[value]]"
                        second_col = QStandardItem(f"[[{normalize_value(value[0, 0])}]]")
                    else:
                        # Normal matrix - show dimensions
                        second_col = QStandardItem(f"{value.shape[0]}x{value.shape[1]}")
                else:
                    # Higher dimensional arrays
                    second_col = QStandardItem(f"{'x'.join(str(d) for d in value.shape)}")
                parent.parent().setChild(parent.row(), 1, second_col)

            elif isinstance(value, str):
                parent.setIcon(QIcon("icons/text.png"))
                # Display string directly in second column
                second_col = QStandardItem(value[:50] + "..." if len(value) > 50 else value)
                parent.parent().setChild(parent.row(), 1, second_col)
            elif np.isscalar(value):
                parent.setIcon(QIcon("icons/number.png"))
                # Display scalar directly - no brackets
                second_col = QStandardItem(str(normalize_value(value)))
                parent.parent().setChild(parent.row(), 1, second_col)
        else:
                # Other types (lists, dicts, etc.)
                second_col = QStandardItem(f"<{type(value).__name__}>")
                parent.parent().setChild(parent.row(), 1, second_col)

        return model

    def open_hdf5_context_menu(self, pos):
        index = self.hdf5_tree.indexAt(pos)
        if not index.isValid():
            return

        item = self.hdf5_model.itemFromIndex(index)
        value = item.data(Qt.UserRole)

        menu = QMenu(self)

        # --- IMAGE ---
        if is_image_array(value):
            view_action = menu.addAction("View Image")
            save_action = menu.addAction("Export as PNG")

            action = menu.exec_(self.hdf5_tree.viewport().mapToGlobal(pos))

            if action == view_action:
                ImageViewer(value, title=item.text(), parent=self).exec_()
            elif action == save_action:
                self.export_png(value)

        # --- VECTORS AND MATRICES (non-image arrays) ---
        elif isinstance(value, np.ndarray) and not is_image_array(value):
            view_value_action = menu.addAction("View Array Details")

            action = menu.exec_(self.hdf5_tree.viewport().mapToGlobal(pos))

            if action == view_value_action:
                ValueViewer(item.text(), f"Shape: {value.shape}\n\nData:\n{value}", parent=self).exec_()

        # --- STRINGS ---
        elif isinstance(value, str):
            view_string_action = menu.addAction("View Full String")

            action = menu.exec_(self.hdf5_tree.viewport().mapToGlobal(pos))

            if action == view_string_action:
                ValueViewer(item.text(), value, parent=self).exec_()

        # --- SCALARS (ints, floats, etc.) ---
        elif np.isscalar(value):
            view_value_action = menu.addAction("View Value")

            action = menu.exec_(self.hdf5_tree.viewport().mapToGlobal(pos))

            if action == view_value_action:
                ValueViewer(item.text(), str(normalize_value(value)), parent=self).exec_()

    def export_png(self, img):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Image", "", "PNG (*.png)"
        )
        if not path:
            return

        from PIL import Image
        Image.fromarray(img).save(path)

    def show_hdf5_browser(self):
        # Create tree
        if not hasattr(self, "hdf5_tree"):
            self.hdf5_tree = QTreeView()
            self.hdf5_tree.setContextMenuPolicy(Qt.CustomContextMenu)
            self.hdf5_tree.customContextMenuRequested.connect(
                self.open_hdf5_context_menu
            )
            self.hdf5_tree.setHeaderHidden(False)

            self.layout().addWidget(self.hdf5_tree)

        self.hdf5_model = self.build_hdf5_tree()
        self.hdf5_tree.setModel(self.hdf5_model)
        self.hdf5_tree.expandAll()

        # Set column widths
        self.hdf5_tree.setColumnWidth(0, 300)  # Name column
        self.hdf5_tree.setColumnWidth(1, 200)  # Value column


class ImageViewer(QDialog):
    def __init__(self, img: np.ndarray, title="Image", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)

        h, w = img.shape[:2]

        if img.ndim == 2:
            qimg = QImage(
                img.data, w, h, w,
                QImage.Format_Grayscale8
            )
        else:
            qimg = QImage(
                img.data, w, h, 3 * w,
                QImage.Format_RGB888
            )

        label = QLabel()
        label.setPixmap(QPixmap.fromImage(qimg))
        label.setScaledContents(True)

        layout = QVBoxLayout(self)
        layout.addWidget(label)
        self.resize(min(w, 1000), min(h, 800))

class ValueViewer(QDialog):
    def __init__(self, name, value, parent=None):
        super().__init__(parent)
        self.setWindowTitle(name)

        label = QLabel(str(value))
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        label.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.addWidget(label)

        self.resize(500, 300)

