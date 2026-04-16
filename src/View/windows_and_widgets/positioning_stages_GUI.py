# Created by Jannet Trabelsi on 2025-09-02
# Please note: the controller class raises errors. However, the GUI sets default values to solve for invalid inputs
import time
from PyQt5.QtWidgets import QMessageBox, QWidget
from src.Controller.newport_conex_cc import Newport_CONEX_CC_xy_stage
from src.Controller.nanodrive import MCLNanoDrive
from src.Controller.MCL_z_microdrive import MCLZMicroDrive
from .positioning_stages_design import Ui_Form
from datetime import datetime
import os
from PyQt5.QtWidgets import QFileDialog
from src.core.struct_hdf5 import StructArray, MyStruct, save_data, load_data
import numpy as np
import cv2
from typing import List, Tuple
from PyQt5.QtWidgets import QMessageBox, QPushButton
# Assuming the .ui file is converted to design.py
#To convert positioning_stages_design.ui to .py, paste this into the terminal:
# pyuic5 -x positioning_stages_design.ui -o positioning_stages_design.py

# constants:
_MAX_X_1 = 100
_MIN_X_1 = 0
_MAX_Y_1 = 100
_MIN_Y_1 = 0
_MAX_Z_1 = 100
_MIN_Z_1 = 0
_MAX_X_2 = 100
_MIN_X_2 = 0
_MAX_Y_2 = 100
_MIN_Y_2 = 0
_MAX_Z_2 = 100
_MIN_Z_2 = 0
_MAX_Z_3 = 25000
_MIN_Z_3 = -25000
_MAX_MCL_nanodrive_X = 100
_MIN_MCL_nanodrive_X = 0
_MAX_MCL_nanodrive_Y = 100
_MIN_MCL_nanodrive_Y = 0
_MAX_MCL_nanodrive_Z =100
_MIN_MCL_nanodrive_Z = 0
_MAX_MCL_microdrive_Z = 50000
_MIN_MCL_microdrive_Z = 0
from PyQt5.QtCore import pyqtSignal

class positioning_stages_view(QWidget, Ui_Form):
    """
    This is the widget of the positioning stages. It allows us to control positioning devices using buttons and LineEdits
    """
    display_choice_changed = pyqtSignal(str)
    snapshot_mode_changed = pyqtSignal(int)
    snapButtonclicked = pyqtSignal(int)
    save_or_find_nv_button_clicked = pyqtSignal(int)
    take_img_signal = pyqtSignal(int)
    def __init__(self, parent = None):
        super().__init__(parent)
        self.setupUi(self)
        self.stage_1 = None
        self.stage_2 = None
        self.stage_3 = None

        self.xlineEdit_1.setEnabled(False)
        self.ylineEdit_1.setEnabled(False)
        self.zlineEdit_1.setEnabled(False)
        self.x_y_inc_lineEdit_1.setEnabled(False)
        self.z_inc_lineEdit_1.setEnabled(False)
        self.x_y_inc_lineEdit_2.setEnabled(False)
        self.z_inc_lineEdit_2.setEnabled(False)
        self.x_inc_1.setEnabled(False)
        self.y_inc_1.setEnabled(False)
        self.z_inc_1.setEnabled(False)
        self.x_dec_1.setEnabled(False)
        self.y_dec_1.setEnabled(False)
        self.z_dec_1.setEnabled(False)

        self.xlineEdit_2.setEnabled(False)
        self.ylineEdit_2.setEnabled(False)
        self.zlineEdit_2.setEnabled(False)
        self.x_inc_2.setEnabled(False)
        self.y_inc_2.setEnabled(False)
        self.z_inc_2.setEnabled(False)
        self.x_dec_2.setEnabled(False)
        self.y_dec_2.setEnabled(False)
        self.z_dec_2.setEnabled(False)
        self.confirm_x_button_1.setEnabled(False)
        self.confirm_y_button_1.setEnabled(False)
        self.confirm_z_button_1.setEnabled(False)
        self.confirm_x_button_2.setEnabled(False)
        self.confirm_y_button_2.setEnabled(False)
        self.confirm_z_button_2.setEnabled(False)
        self.home_button_3.setEnabled(False)

        self.zlineEdit_3.setEnabled(False)
        self.z_inc_3.setEnabled(False)
        self.z_dec_3.setEnabled(False)
        self.comfirm_z_3.setEnabled(False)

        # Connect buttons to functions
        self.connectButton_1.clicked.connect(self.connect_to_instrument_1)
        self.connectButton_2.clicked.connect(self.connect_to_instrument_2)
        self.connectButton_3.clicked.connect(self.connect_to_instrument_3)
        self.confirm_x_button_1.clicked.connect(lambda: self.set_position("x", 1))
        self.confirm_y_button_1.clicked.connect(lambda: self.set_position("y", 1))
        self.confirm_z_button_1.clicked.connect(lambda: self.set_position("z", 1))
        self.confirm_x_button_2.clicked.connect(lambda: self.set_position("x", 2))
        self.confirm_y_button_2.clicked.connect(lambda: self.set_position("y", 2))
        self.confirm_z_button_2.clicked.connect(lambda: self.set_position("z", 2))
        self.comfirm_z_3.clicked.connect(lambda: self.set_position("z", 3))
        self.home_button_3.clicked.connect(lambda: self.set_position("home", 3))
        self.x_inc_1.clicked.connect(lambda: self.change_position("x", 1, 1)) # 1 for inc 0 for dec
        self.x_inc_2.clicked.connect(lambda: self.change_position("x", 2, 1))
        self.x_dec_1.clicked.connect(lambda: self.change_position("x", 1, 0))
        self.x_dec_2.clicked.connect(lambda: self.change_position("x", 2, 0))
        self.y_inc_1.clicked.connect(lambda: self.change_position("y", 1, 1))
        self.y_inc_2.clicked.connect(lambda: self.change_position("y", 2, 1))
        self.y_dec_1.clicked.connect(lambda: self.change_position("y", 1, 0))
        self.y_dec_2.clicked.connect(lambda: self.change_position("y", 2, 0))
        self.z_inc_1.clicked.connect(lambda: self.change_position("z", 1, 1))
        self.z_inc_2.clicked.connect(lambda: self.change_position("z", 2, 1))
        self.z_dec_1.clicked.connect(lambda: self.change_position("z", 1, 0))
        self.z_dec_2.clicked.connect(lambda: self.change_position("z", 2, 0))
        self.z_inc_3.clicked.connect(lambda: self.change_position("z", 3, 1))
        self.z_dec_3.clicked.connect(lambda: self.change_position("z", 3, 0))
        self.save_button.clicked.connect(self.save)
        self.Find_NV_Button.clicked.connect(self.find_NV)
        self.snapButton.clicked.connexct(self.send_snapshotButtonclicked_signal)
        # Connect combobox signals to emitters
        self.display_option.currentTextChanged.connect(self.on_display_choice_changed)
        self.snapshot_live_comboBox.currentTextChanged.connect(self.on_snapshot_or_live_changed)
        self.data_saving_path = None
        self.data_reader = None
        self.frame = None

    def connect_to_instrument_1(self):
        """This function connects the devices: please make sure that your stage has the function get_position(self, axis)"""
        stage_name = self.comboBox_1.currentText()
        if stage_name == 'MCL_nanodrive':
            _MAX_X_1 = _MAX_MCL_nanodrive_X
            _MIN_X_1 = _MIN_MCL_nanodrive_X
            _MAX_Y_1 = _MAX_MCL_nanodrive_Y
            _MIN_Y_1 = _MIN_MCL_nanodrive_Y
            _MAX_Z_1 = _MAX_MCL_nanodrive_Z
            _MIN_Z_1 = _MIN_MCL_nanodrive_Z
            try:
                self.stage_1 = MCLNanoDrive()
                self.zlineEdit_1.setEnabled(True)
                self.zlineEdit_1.setText(str(self.stage_1.get_position('z')))
                self.confirm_z_button_1.setEnabled(True)
                self.z_inc_1.setEnabled(True)
                self.z_dec_1.setEnabled(True)
                self.z_inc_lineEdit_1.setEnabled(True)
                QMessageBox.information(self, 'Success', f'Connected to MCL_nanodrive')

            except Exception as e:
                QMessageBox.critical(self, 'Error', str(e))
        elif stage_name == 'Newport_Conex_microdrive':
            try:
                self.stage_1 = Newport_CONEX_CC_xy_stage()
                _MAX_X_1  = self.stage_1.get_positive_software_limit('x')
                _MIN_X_1 = self.stage_1.get_negative_software_limit('x')
                _MAX_Y_1 = self.stage_1.get_positive_software_limit('y')
                _MIN_Y_1 = self.stage_1.get_negative_software_limit('y')
                QMessageBox.information(self, 'Success', f'Connected to Newport_Conex_microdrive')

            except Exception as e:
                QMessageBox.critical(self, 'Error', str(e))
        else:
            return
        self.xlineEdit_1.setText(str(self.stage_1.get_position('x')))
        self.ylineEdit_1.setText(str(self.stage_1.get_position('y')))
        self.xlineEdit_1.setEnabled(True)
        self.ylineEdit_1.setEnabled(True)
        self.confirm_x_button_1.setEnabled(True)
        self.confirm_y_button_1.setEnabled(True)
        self.x_y_inc_lineEdit_1.setEnabled(True)
        self.x_inc_1.setEnabled(True)
        self.y_inc_1.setEnabled(True)
        self.x_dec_1.setEnabled(True)
        self.y_dec_1.setEnabled(True)

    def connect_to_instrument_2(self):
        """This function connects the devices: please make sure that your stage has the function get_position(self, axis)"""
        stage_name = self.comboBox_2.currentText()
        if stage_name == 'MCL_nanodrive':
            _MAX_X_2 = _MAX_MCL_nanodrive_X
            _MIN_X_2 = _MIN_MCL_nanodrive_X
            _MAX_Y_2 = _MAX_MCL_nanodrive_Y
            _MIN_Y_2 = _MIN_MCL_nanodrive_Y
            _MAX_Z_2 = _MAX_MCL_nanodrive_Z
            _MIN_Z_2 = _MIN_MCL_nanodrive_Z
            try:
                self.stage_2 = MCLNanoDrive()
                self.zlineEdit_2.setEnabled(True)
                self.confirm_z_button_2.setEnabled(True)
                self.zlineEdit_2.setText(str(self.stage_2.get_position('z')))
                self.z_inc_2.setEnabled(True)
                self.z_dec_2.setEnabled(True)
                self.z_inc_lineEdit_2.setEnabled(True)
                QMessageBox.information(self, 'Success', f'Connected to MCL_nanodrive')

            except Exception as e:
                QMessageBox.critical(self, 'Error', str(e))
        elif stage_name == 'Newport_Conex_microdrive':
            try:
                self.stage_2 = Newport_CONEX_CC_xy_stage()
                _MAX_X_2 = self.stage_2.get_positive_software_limit('x')
                _MIN_X_2 = self.stage_2.get_negative_software_limit('x')
                _MAX_Y_2 = self.stage_2.get_positive_software_limit('y')
                _MIN_Y_2 = self.stage_2.get_negative_software_limit('y')
                QMessageBox.information(self, 'Success', f'Connected to Newport_Conex_microdrive')

            except Exception as e:
                QMessageBox.critical(self, 'Error', str(e))
        else:
            return
        self.xlineEdit_2.setText(str(self.stage_2.get_position('x')))
        self.ylineEdit_2.setText(str(self.stage_2.get_position('y')))
        self.xlineEdit_2.setEnabled(True)
        self.ylineEdit_2.setEnabled(True)
        self.confirm_x_button_2.setEnabled(True)
        self.confirm_y_button_2.setEnabled(True)
        self.x_y_inc_lineEdit_2.setEnabled(True)
        self.x_inc_2.setEnabled(True)
        self.y_inc_2.setEnabled(True)
        self.x_dec_2.setEnabled(True)
        self.y_dec_2.setEnabled(True)

    def connect_to_instrument_3(self):
        stage_name = self.comboBox_3.currentText()
        if stage_name == 'MCL_z_microdrive':
            _MAX_Z_3 = _MAX_MCL_microdrive_Z
            _MIN_Z_3 = _MIN_MCL_microdrive_Z
            try:
                self.stage_3 = MCLZMicroDrive()
                self.zlineEdit_3.setEnabled(True)
                self.comfirm_z_3.setEnabled(True)
                self.zlineEdit_3.setText(str(self.stage_3.get_position('z')))
                self.z_inc_3.setEnabled(True)
                self.z_dec_3.setEnabled(True)
                self.z_inc_lineEdit_3.setEnabled(True)
                self.home_button_3.setEnabled(True)
                QMessageBox.information(self, 'Success', f'Connected to MCL_z_microdrive')

            except Exception as e:
                QMessageBox.critical(self, 'Error', str(e))
        else:
            return

    def close(self):
        if self.stage_1 is not None:
            print("closing stage_1")
            self.stage_1.close()
        if self.stage_2 is not None:
            print("closing stage_2")
            self.stage_2.close()
        if self.stage_3 is not None:
            print("closing stage_3")
            self.stage_3.close()

    def set_position(self, axis, instrument_id):
        if axis == "home" and instrument_id == 3:
            self.stage_3.home_axis() # please note this is specific for the z microdrive as it doesn't have encoders
            #time.sleep(15)
            self.stage_3.homed = True
            self.zlineEdit_3.setText(str(self.stage_3.get_position()))
        else:
            stage, pos, max, min, line_edit, inc = self.selector(axis, instrument_id)
            if isinstance(pos, str) or isinstance(pos, int) or isinstance(pos, float):
                try:
                    if pos:
                        pos = float(pos)
                        if min<=pos<=max:
                            print("inside set_position in positioning GUI")
                            stage.set_position(axis, pos)
                            #time.sleep(15)
                            line_edit.setText(str(stage.get_position(axis)))
                        else:
                            self.error_box(
                                "OUT OF RANGE!",
                                "Please provide a position within the range"
                            )
                            return
                    else:
                        self.error_box(
                            "INVALID POSITION!",
                            "Please provide a valid position"
                        )
                        return
                except ValueError:
                    line_edit.setText(str(stage.get_position(axis)))
                    return
            else:
                self.error_box(
                    "INVALID POSITION!",
                    "Please provide a valid position"
                )
                return

    def selector(self, axis, instrument_id):
        if instrument_id == 1:
            stage = self.stage_1
        elif instrument_id == 2:
            stage = self.stage_2
        elif instrument_id == 3:
            stage = self.stage_3
        else:
            raise Exception
        if axis == 'x':
            if instrument_id == 1:
                pos = self.xlineEdit_1.text()
                max = _MAX_X_1
                min = _MIN_X_1
                line_edit = self.xlineEdit_1
                inc_line_edit = self.x_y_inc_lineEdit_1

            elif instrument_id == 2:
                pos = self.xlineEdit_2.text()
                max = _MAX_X_2
                min = _MIN_X_2
                line_edit = self.xlineEdit_2
                inc_line_edit = self.x_y_inc_lineEdit_2
            else:
                raise Exception
        elif axis == 'y':
            if instrument_id == 1:
                pos = self.ylineEdit_1.text()
                max = _MAX_Y_1
                min = _MIN_Y_1
                line_edit = self.ylineEdit_1
                inc_line_edit = self.x_y_inc_lineEdit_1
            elif instrument_id == 2:
                pos = self.ylineEdit_2.text()
                max = _MAX_Y_2
                min = _MIN_Y_2
                line_edit = self.ylineEdit_2
                inc_line_edit = self.x_y_inc_lineEdit_2
            else:
                raise Exception
        elif axis == 'z':
            if instrument_id == 1:
                pos = self.zlineEdit_1.text()
                max = _MAX_Z_1
                min = _MIN_Z_1
                line_edit = self.zlineEdit_1
                inc_line_edit = self.z_inc_lineEdit_1
            elif instrument_id == 2:
                pos = self.zlineEdit_2.text()
                max = _MAX_Z_2
                min = _MIN_Z_2
                line_edit = self.zlineEdit_2
                inc_line_edit = self.z_inc_lineEdit_2
            elif instrument_id == 3:
                pos = self.zlineEdit_3.text()
                max = _MAX_Z_3
                min = _MIN_Z_3
                line_edit = self.zlineEdit_3
                inc_line_edit = self.z_inc_lineEdit_3
            else:
                raise Exception
        else:
            raise Exception
        return stage, pos, max, min, line_edit, inc_line_edit

    def change_position(self, axis, instrument_id, increase):
        # 1 for inc 0 for dec
        stage, pos, max, min, line_edit, inc_line_edit = self.selector(axis, instrument_id)
        inc_step = inc_line_edit.text()
        pos = float(stage.get_position(axis))
        if isinstance(inc_step, str) or isinstance(inc_step, int) or isinstance(inc_step, float):
            try:
                inc_step = float(inc_step)
                if increase:
                    new_pos = pos + inc_step
                else:
                    new_pos = pos - inc_step
                print(f'new position inc/dec: {new_pos}')
                if new_pos < max and new_pos > min:
                    stage.set_position(axis, new_pos)
                    time.sleep(1)
                    line_edit.setText(str(stage.get_position(axis)))
                else:
                    self.error_box(
                        "OUT OF RANGE!",
                        "Please provide a position within the range"
                    )
                    return
            except ValueError:
                line_edit.setText(str(stage.get_position(axis)))
                return
        else:
            line_edit.setText(str(stage.get_position(axis)))
            return

    def on_display_choice_changed(self, text):
        # This one should be handled in main window by the display
        disp = self.display_option.currentText()
        if disp == "MU300":
            self.snapshot_live_comboBox.setEnabled(True)
        print("on_display_choice_changed emitting", text)
        self.display_choice_changed.emit(text)

    def on_snapshot_or_live_changed(self, text):
        mode = 0 if text.lower() == "snapshot" else 1
        print("on_snapshot_or_live_changed emitting", mode)
        self.snapshot_mode_changed.emit(mode)

    def display_choice(self):
        disp = self.display_option.currentText()
        if disp == "MU300":
            self.snapshot_live_comboBox.setEnabled(True)
        return disp

    def snapshot_or_live(self):
        return self.snapshot_live_comboBox.currentText()

    def send_snapshotButtonclicked_signal(self):
        self.snapButtonclicked.emit(1)

    def save(self):
        print("save is pressed 1")
        self.save_or_find_nv_button_clicked.emit(1)
        print("save is pressed 2")

        # --- UI → keys ---
        sample_selection = self.Sample_Selector_comboBox.currentText()
        point_selection = self.Point_Selector_comboBox.currentText()
        point_status = self.point_status_comboBox.currentText()

        point_key = point_selection.lower().replace(" ", "_")

        if point_status == "FINAL" and point_selection == "NV":
            self.error_box(
                "YOU CANNOT SELECT FINAL NV POINT",
                "To find NV, click find NV button!"
            )
            return

        # --------------------------------------------------
        # File handling
        # --------------------------------------------------
        if sample_selection == "New Sample":
            point_status = "INITIAL"
            directory, filename = self.open_directory_dialog(self.data_saving_path)
            if filename is None:
                return

            self.data_saving_path = directory
            full_path = os.path.join(directory, filename)

            if os.path.exists(full_path):
                if not self.confirm_overwrite(filename):
                    return

            mode = "w"

        else:
            full_path = self.open_file_dialog(self.data_saving_path)
            if full_path is None:
                return
            mode = "r+"
        # new root
        root = MyStruct()

        # INITIAL / FINAL
        if not hasattr(root, point_status):
            setattr(root, point_status, MyStruct())

        point_status_object = getattr(root, point_status)

        # bottom_left / nv / etc
        if not hasattr(point_status_object, point_key):
            setattr(point_status_object, point_key, MyStruct())

        point = getattr(point_status_object, point_key)


        # --------------------------------------------------
        # Identify stages
        # --------------------------------------------------
        stage_1_name = self.comboBox_1.currentText()
        if "nanodrive" in stage_1_name.lower():
            nano = self.stage_1
            micro = self.stage_2
        else:
            nano = self.stage_2
            micro = self.stage_1

        # --------------------------------------------------
        # Snapshot metadata
        # --------------------------------------------------
        point.micro_x = self.xlineEdit_2.text()
        point.micro_y = self.ylineEdit_2.text()

        point.nano_x = self.xlineEdit_1.text()
        point.nano_y = self.ylineEdit_1.text()
        point.nano_z = self.zlineEdit_1.text()

        point.camera_x = self.x_crosshair
        point.camera_y = self.y_crosshair

        point.timestamp = datetime.utcnow().isoformat()

        # --------------------------------------------------
        # Capture camera image
        # --------------------------------------------------

        if self.snapshot_or_live() == "Snapshot":
            self.take_img_signal.emit(1)
            print("snapshot called")
            print(self.frame)
            point.camera_image = self.frame
        else:
            self.error_box("please take snapshot to save image data", "image data will not be saved for this entry")
            point.camera_image = None
        # --------------------------------------------------
        # SAVE (single call)
        # --------------------------------------------------
        save_data(
            filename=full_path,
            obj=root,
            mode=mode,
            swmr=False  # snapshot, not live
        )

    def error_box(self, text, info, title="Error"):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle(title)
        msg.setText(text)
        msg.setInformativeText(info)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.setDefaultButton(QMessageBox.Ok)

        return msg.exec() == QMessageBox.Ok

    def open_file_dialog(self, start_path):
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Open sample file",
            start_path,
            "HDF5 files (*.h5);;All files (*)"
        )

        if not filename:
            raise RuntimeError("No file selected")

        return filename

    def open_directory_dialog(self, start_path):
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Select file location",
            start_path,
            "HDF5 Files (*.h5);;All Files (*)"
        )

        # User pressed Cancel
        if not file_path:
            return None, None

        directory = os.path.dirname(file_path)
        filename = os.path.basename(file_path)

        return directory, filename

    def confirm_overwrite(self, point_key):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Overwrite point?")
        msg.setText(f"Point '{point_key}' already exists.")
        msg.setInformativeText("Do you want to overwrite it?")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.No)

        return msg.exec() == QMessageBox.Yes

    def compute_homography_from_corners(self,
            old_corners: List[np.ndarray],
            new_corners: List[np.ndarray], method) -> np.ndarray:

        if len(old_corners) != 4 or len(new_corners) != 4:
            raise ValueError("Expected 4 corners for old and new quads")

        src_pts = np.array(old_corners, dtype=np.float64)
        dst_pts = np.array(new_corners, dtype=np.float64)

        # ensure points are numpy arrays and float32
        src_pts = np.array(src_pts, dtype=np.float32)
        dst_pts = np.array(dst_pts, dtype=np.float32)

        # check number of points
        if src_pts.shape[0] < 4 or dst_pts.shape[0] < 4:
            raise ValueError("Need at least 4 points to compute homography")

        if method == "LMEDS":
            H, status = cv2.findHomography(src_pts, dst_pts, method=cv2.LMEDS)
        elif method == "RANSAC":
            H, status = cv2.findHomography(src_pts, dst_pts, method=cv2.RANSAC, ransacReprojThreshold=1.0)
        elif method == "RHOMBUS":
            H, status = cv2.findHomography(src_pts, dst_pts, method=cv2.RHO)
        else:
            H, status = cv2.findHomography(src_pts, dst_pts, cv2.USAC_MAGSAC)

        if status is not None and not np.all(status):
            print("Warning: some corners treated as outliers")

        if H is None:
            raise ValueError("Homography computation failed")

        # Optional: verify fourth corner
        tr_hom = np.array([src_pts[1, 0], src_pts[1, 1], 1.0])
        tr_pred = H @ tr_hom
        tr_pred /= tr_pred[2]
        expected = np.array([dst_pts[1, 0], dst_pts[1, 1], 1.0])
        if np.linalg.norm(tr_pred - expected) > 1e-6:
            print(f"Warning: Fourth corner verification failed. "
                  f"Expected ({expected[0]:.3f},{expected[1]:.3f}), got ({tr_pred[0]:.3f},{tr_pred[1]:.3f})")

        return H

    def map_point_with_homography(self, point: np.ndarray, H: np.ndarray) -> np.ndarray:

        if len(point) == 2:
            pt_hom = np.array([point[0], point[1], 1.0])
        else:
            pt_hom = np.array(point)

        mapped = H @ pt_hom
        mapped /= mapped[2]
        return mapped[:2]

    # affine

    def from_four_corners_to_DMT_or_DMNT(self,
            corners_microdrive: List[np.ndarray],
            reference_order: Tuple[str] = ("top_left", "top_right", "bottom_right", "bottom_left")
    ) -> np.ndarray:
        

        if len(corners_microdrive) != 4:
            raise ValueError(f"Expected 4 corners, got {len(corners_microdrive)}")

        # Extract points in the specified order
        # Assuming input order matches reference_order
        bl_idx = reference_order.index("bottom_left")
        br_idx = reference_order.index("bottom_right")
        tl_idx = reference_order.index("top_left")

        bottom_left = np.array(corners_microdrive[bl_idx], dtype=float)
        bottom_right = np.array(corners_microdrive[br_idx], dtype=float)
        top_left = np.array(corners_microdrive[tl_idx], dtype=float)

        # Diamond coordinate system definition:
        # In diamond coords:
        # bottom_left = (0, 0)
        # bottom_right = (1, 0)
        # top_left = (0, 1)
        # top_right = (1, 1)

        # Source points in microdrive coordinates (homogeneous)
        src_points = np.array([
            [bottom_left[0], bottom_left[1], 1],
            [bottom_right[0], bottom_right[1], 1],
            [top_left[0], top_left[1], 1]
        ]).T  # Shape: (3, 3)

        # Destination points in diamond coordinates (homogeneous)
        dst_points = np.array([
            [0, 0, 1],
            [1, 0, 1],
            [0, 1, 1]
        ]).T  # Shape: (3, 3)

        # Solve for transformation matrix T such that: dst = T @ src
        # T is 3x3, we need T @ src = dst
        # T = dst @ inv(src)

        try:
            T = dst_points @ np.linalg.inv(src_points)
        except np.linalg.LinAlgError:
            raise ValueError("Corners are colinear or form a degenerate shape")
        return T

    def from_DMT_and_MNV_old_get_DNV_old(self, M_point: np.ndarray, T_matrix: np.ndarray) -> np.ndarray:

        if len(M_point) == 2:
            M_hom = np.array([M_point[0], M_point[1], 1.0])
        else:
            M_hom = np.array(M_point)

        D_hom = T_matrix @ M_hom
        D_hom = D_hom / D_hom[2]  # Normalize

        return D_hom[:2]

    def choose_method(self) -> str:
        """
        Ask the user which NV mapping method to use: Affine or Homography.
        Returns:
            "affine" or "homography"
        """
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Question)
        msg.setWindowTitle("Select NV Mapping Method")
        msg.setText("Which method would you like to use for NV relocation?")
        msg.setInformativeText("Choose Affine or Homography.")

        msg.setStandardButtons(QMessageBox.NoButton)

        # Add custom buttons
        btn_affine = QPushButton("Affine")
        btn_homography = QPushButton("Homography")
        msg.addButton(btn_affine, QMessageBox.AcceptRole)
        msg.addButton(btn_homography, QMessageBox.AcceptRole)

        # Show dialog and wait for response
        ret = msg.exec()

        clicked_button = msg.clickedButton()
        if clicked_button == btn_affine:
            return "affine"
        else:
            return "homography"

    def choose_homography_method(self) -> str:
        """
        Ask the user which NV mapping method to use: LMEDS, RANSAC, RHOMBUS in Homography.
        Returns:
            "LMEDS", "RANSAC", "RHOMBUS", or "USAC_MAGSAC
        """
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Question)
        msg.setWindowTitle("Select NV Mapping Method")
        msg.setText("Which method would you like to use for NV relocation?")
        msg.setInformativeText("Choose Homography.")

        msg.setStandardButtons(QMessageBox.NoButton)

        # Add custom buttons
        btn_LMEDS = QPushButton("LMEDS")
        btn_RANSAC = QPushButton("RANSAC")
        btn_RHOMBUS = QPushButton("RHOMBUS")
        btn_USAC_MAGSAC = QPushButton("USAC_MAGSAC")
        msg.addButton(btn_LMEDS, QMessageBox.AcceptRole)
        msg.addButton(btn_RANSAC, QMessageBox.AcceptRole)
        msg.addButton(btn_RHOMBUS, QMessageBox.AcceptRole)
        msg.addButton(btn_USAC_MAGSAC, QMessageBox.AcceptRole)
        # Show dialog and wait for response
        ret = msg.exec()

        clicked_button = msg.clickedButton()
        if clicked_button == btn_LMEDS:
            return "LMEDS"
        elif clicked_button == btn_RANSAC:
            return "RANSAC"
        elif clicked_button == btn_RHOMBUS:
            return "RHOMBUS"
        else:
            return "USAC_MAGSAC"

    def find_NV(self) -> np.ndarray:

        self.save_or_find_nv_button_clicked.emit(1)
        print("find_NV is pressed")
        path = self.open_file_dialog(self.data_saving_path)
        if not path:
            return
        method = self.choose_method()
        structure = load_data(path)
        if method == "affine":
            """for i, structure in enumerate(Objects._items):"""
            print(f"struct: {structure}")

            old_corners, new_corners, MNV_old = self.extract_corners(structure)
            # Compute transformations
            DMT = self.from_four_corners_to_DMT_or_DMNT(old_corners)
            DMNT = self.from_four_corners_to_DMT_or_DMNT(new_corners)

            MNV_new_direct = self.from_DMT_and_MNV_old_get_DNV_old(MNV_old, np.linalg.inv(DMNT) @ DMT)
            print(f"affine solution: {MNV_new_direct}")
            return MNV_new_direct
        elif method == "homography":
            method = self.choose_homography_method()
            """for i, structure in enumerate(Objects._items):"""
            print(f"struct: {structure}")

            old_corners, new_corners, MNV_old = self.extract_corners(structure)
            H_direct = self.compute_homography_from_corners(old_corners, new_corners, method)
            nv_new = self.map_point_with_homography(MNV_old, H_direct)
            print(f"homography solution with {method} method: {nv_new}")
            return nv_new
        else:
            raise ValueError(f"Method {method} not implemented")

    def extract_corners(self, structure):
        order = ["top_left", "top_right", "bottom_right", "bottom_left"]

        def get_xy(block, name):
            pt = getattr(block, name)  # MyStruct directly

            if pt is None:
                raise ValueError(f"No data for {name}")

            print(f"{name} micro_x: {pt.micro_x}, micro_y: {pt.micro_y}")

            return np.array([
                float(pt.micro_x),
                float(pt.micro_y)
            ])
        print(f"structure.initial {structure.INITIAL}")
        print(f"structure.final {structure.FINAL}")
        old_corners = [get_xy(structure.INITIAL, n) for n in order]
        new_corners = [get_xy(structure.FINAL, n) for n in order]
        nv_position = get_xy(structure.INITIAL, "nv")

        return old_corners, new_corners, nv_position
