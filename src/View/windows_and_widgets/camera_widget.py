# original: Kai's code
# modified by: Jannet Trabelsi: 10_2025
from __future__ import annotations
import sys
import ctypes
import time
from typing import Optional
#from src.Controller import amcam
from src.Controller import toupcam
from src.Controller import Amscope_MU_Camera
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QTimer
from PyQt5.QtGui import QPixmap, QImage, QPainter, QPen
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QCheckBox,
    QVBoxLayout,
    QHBoxLayout,
    QDesktopWidget,
    QMessageBox,
    QSlider
)
import numpy as np
import weakref
from src.core.struct_hdf5 import save_parameters_hdf5, load_data
"""
        Parameter class for managing experiment parameters with validation and units.

        Supported initialization patterns:
        - Parameter(name, value, valid_values, info, units)
        - Parameter({name: value})
        - Parameter([Parameter(...), Parameter(...)])

        Args:
            name: Parameter name (str) or dict/list for multiple parameters
            value: Parameter value (any type)
            valid_values: Type or list of valid values
            info: Description string
            visible: Boolean for GUI visibility
            units: Units string
            min_value: Minimum allowed value (for numeric parameters)
            max_value: Maximum allowed value (for numeric parameters)
            pattern: Regex pattern for string validation
            validator: Custom validation function
        """


class SnapWin(QWidget):
    """Separate window that shows still‑image captures."""

    def __init__(self, w: int, h: int):
        super().__init__()
        self.setWindowTitle("Snapshot")
        self.setFixedSize(w, h)
        self.label = QLabel(self)
        self.label.resize(w, h)
        self.label.setScaledContents(False)

    def show_frame(self, qimg: QImage):
        self.label.setPixmap(QPixmap.fromImage(qimg))
        self.show()

class Amscope_Camera_View(QWidget):
    """Live‑view window. Compatible with the legacy *app.py* launcher."""

    eventImage = pyqtSignal(int)
    mouseMoved = pyqtSignal(int, int)
    mouseClicked = pyqtSignal(int, int)

    def __init__(
        self,
        gain: int = 100,
        integration_time_us: int = 10_000,
        res: str = "low",
    ) -> None:
        super().__init__()

        self.hcam: Optional[Amscope_MU_Camera.Amscope_MU_Camera] = None
        self.buf: Optional[ctypes.Array] = None
        self.w = self.h = 0
        self.gain = gain
        self.integration = integration_time_us  # already in µs
        self.res = "low"

        # frame counter for FPS display
        self._frame_accum = 0
        self._last_tick = time.perf_counter()

        self._init_ui()
        #self._init_camera()
        self.crosshair_enabled = False
        self.crosshair_x = None
        self.crosshair_y = None
        self.crosshair_thickness = 1

    # ── UI ────────────────────────────────────────────────────────────────────

    def _init_ui(self) -> None:
        # center the window on whatever display we’re on
        #self.setFixedSize(820, 640)  # temp; corrected once cam opens
        geo = self.frameGeometry()
        geo.moveCenter(QDesktopWidget().availableGeometry().center())
        self.move(geo.topLeft())

        # widgets
        self.label = QLabel(self)
        self.label = CrosshairLabel(self)
        self.label.mouseMoved.connect(self.mouseMoved)
        self.label.mouseClicked.connect(self.mouseClicked)

        self.label.setScaledContents(False)  # don’t resample!

        self.cb_auto = QCheckBox("Auto Exposure", self)
        self.cb_auto.stateChanged.connect(self._on_auto_exp_toggled)

        self.cb_fps = QCheckBox("Show FPS", self)

        # layout
        cols = QVBoxLayout(self)
        cols.addWidget(self.label, stretch=1)
        row = QHBoxLayout()
        row.addWidget(self.cb_auto)
        row.addWidget(self.cb_fps)
        row.addStretch(1)
        cols.addLayout(row)

    # ── Camera setup ──────────────────────────────────────────────────────────

    def _init_camera(self) -> None:
        #cams = amcam.Amcam.EnumV2()
        cams = toupcam.Toupcam.EnumV2()
        if not cams:
            self.setWindowTitle("No camera found")
            self.cb_auto.setEnabled(False)
            return

        self.camname = cams[0].displayname
        self.setWindowTitle(self.camname)
        self.eventImage.connect(self._on_event_image)

        try:
            self.hcam = Amscope_MU_Camera.Amscope_MU_Camera()
        #except amcam.HRESULTException as ex:
        except toupcam.HRESULTException as ex:
            QMessageBox.warning(self, "", f"Failed to open camera (hr=0x{ex.hr:x})")
            return

        # basic settings
        self.hcam.set_ExpoAGain(self.gain)
        self._clamp_and_set_exposure(self.integration)
        self._apply_resolution(self.res)

        # negotiate RGB/BGR for zero‑copy into QImage
        if sys.platform != "win32":
            #self.hcam.put_Option(amcam.AMCAM_OPTION_BYTEORDER, 1)  # BGR on Linux/mac
            self.hcam.put_Option(toupcam.TOUPCAM_OPTION_BYTEORDER, 1)  # BGR on Linux/mac

        # internal buffer (mutable)
        stride = ((self.w * 24 + 31) // 32) * 4
        self.buf = ctypes.create_string_buffer(stride * self.h)

        # resize widget exactly to sensor size (no scaling cost)
        self.setFixedSize(self.w, self.h + 40)  # + controls bar
        self.label.setFixedSize(self.w, self.h)

        # reflect current auto‑exposure state
        self.cb_auto.setChecked(self.hcam.get_AutoExpoEnable())

        # start stream
        try:
            # Instead of:
            # self.hcam.StartPullModeWithCallback(self._camera_cb, self)
            # We use:
            self_ref = weakref.ref(self)  # weak reference
            self.hcam.StartPullModeWithCallback(self._camera_cb, self_ref)
        #except amcam.HRESULTException as ex:
        except toupcam.HRESULTException as ex:
            QMessageBox.warning(self, "", f"Stream start failed (hr=0x{ex.hr:x})")
            return

    def _clamp_and_set_exposure(self, target_us: int) -> None:
        lo, hi, _ = self.hcam.get_ExpTimeRange()
        self.hcam.put_ExpoTime(max(lo, min(target_us, hi)))

    def _apply_resolution(self, res: str) -> None:
        match res:
            case "high":
                self.hcam.put_eSize(0)  # 2048, 1536
            case "mid":
                self.hcam.put_eSize(1)
            case _:
                self.hcam.put_eSize(2)
        self.w, self.h = self.hcam.get_Size()

    # ── Toupcam callback (runs in SDK thread) ─────────────────────────────––

    @staticmethod
    def _camera_cb(event: int, ctx: "Amscope_Camera_View") -> None:
        #if event == amcam.AMCAM_EVENT_IMAGE:
        if event == toupcam.TOUPCAM_EVENT_IMAGE:
            try:
                ctx.hcam.PullImageV2(ctx.buf, 24, None)
            #except amcam.HRESULTException:
            except toupcam.HRESULTException:
                return  # drop frame
            ctx.eventImage.emit(event)
        #elif event == amcam.AMCAM_EVENT_STILLIMAGE:
        elif event == toupcam.TOUPCAM_EVENT_STILLIMAGE:
            try:
                ctx.hcam.PullStillImageV2(ctx.buf, 24, None)
            #except amcam.HRESULTException:
            except toupcam.HRESULTException:
                return
            ctx.eventImage.emit(event)

    # ── Qt slot (runs in GUI thread) ─────────────────────────────────────────

    @pyqtSlot(int)
    def _on_event_image(self, event: int) -> None:
        stride = ((self.w * 24 + 31) // 32) * 4
        qimg = QImage(self.buf, self.w, self.h, stride, QImage.Format_RGB888)
        # qimg.save("frame.png")

        #if event == amcam.AMCAM_EVENT_IMAGE:
        if event == toupcam.TOUPCAM_EVENT_IMAGE:
            pixmap = QPixmap.fromImage(qimg)
            self.label.setPixmap(pixmap)
            self._update_fps()
        else:
            pixmap = QPixmap.fromImage(qimg)
            self.label.setPixmap(pixmap)
            if not hasattr(self, "_snap_win"):
                self._snap_win = SnapWin(self.w, self.h)
            self._snap_win.show_frame(qimg)

    # ── Misc callbacks ──────────────────────────────────────────────────────

    def _on_auto_exp_toggled(self, state: int) -> None:
        if self.hcam:
            self.hcam.put_AutoExpoEnable(state == Qt.Checked)

    def _update_fps(self) -> None:
        if not self.cb_fps.isChecked():
            return
        self._frame_accum += 1
        now = time.perf_counter()
        if now - self._last_tick >= 1.0:
            fps = self._frame_accum / (now - self._last_tick)
            self.setWindowTitle(f"{self.camname} – {fps:.1f} fps")
            self._frame_accum = 0
            self._last_tick = now

    # ── API for *app.py* ────────────────────────────────────────────────────

    def snap(self):
        if self.hcam:
            self.hcam.Snap(0)

    def stop(self):
        if self.hcam is not None:
            self.hcam.close()
            self.hcam = None

    # ── Cleanup ─────────────────────────────────────────────────────────────

    def closeEvent(self, evt):  # noqa: N802 (Qt override)
        self.stop()
        super().closeEvent(evt)

    def stop_live_view(self):
        self.hcam.pause(0)
        self.hcam.stop()

    def start_live_view(self):
        self._init_camera()

    def get_latest_frame(self) -> Optional[np.ndarray]:
        """Returns the latest frame as a NumPy array."""
        if not self.buf:
            return None
        try:
            arr = np.frombuffer(self.buf, dtype=np.uint8).reshape((self.h, self.w, 3))
            return arr
        except Exception as e:
            print(f"Frame conversion error: {e}")
            return None

class CrosshairLabel(QLabel):
    mouseMoved = pyqtSignal(int, int)
    mouseClicked = pyqtSignal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self._crosshair_enabled = False
        self._crosshair_pos = None  # (x, y)
        self._crosshair_thickness = 1
        self._waiting_for_crosshair_click = False

    def enable_crosshair(self, x, y, thickness=1):
        self._crosshair_pos = (x, y)
        self._crosshair_thickness = thickness
        self._crosshair_enabled = True
        self.update()

    def disable_crosshair(self):
        self._crosshair_enabled = False
        self._crosshair_pos = None
        self.update()

    def paintEvent(self, event):
        # Paint the base image
        super().paintEvent(event)
        if self._crosshair_enabled and self._crosshair_pos:
            painter = QPainter(self)
            pen = QPen(Qt.red, 1)
            painter.setPen(pen)
            x, y = self._crosshair_pos
            x_line_len = 680
            y_line_len = 510
            half_thickness = self._crosshair_thickness//2

            painter.drawLine(x - x_line_len, y - half_thickness, x + x_line_len, y - half_thickness)
            painter.drawLine(x - x_line_len, y + half_thickness, x + x_line_len, y + half_thickness)
            painter.drawLine(x - half_thickness, y - y_line_len, x - half_thickness, y + y_line_len)
            painter.drawLine(x + half_thickness, y - y_line_len, x + half_thickness, y + y_line_len)
            painter.end()

    def mouseMoveEvent(self, event):
        self.mouseMoved.emit(event.x(), event.y())

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self._waiting_for_crosshair_click:
            self.mouseClicked.emit(event.x(), event.y())

    def waiting_for_crosshair_click(self, enable):
        self._waiting_for_crosshair_click = enable
if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = Amscope_Camera_View()
    w.show()
    sys.exit(app.exec())