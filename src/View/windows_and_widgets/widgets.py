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

from PyQt5 import QtCore, QtWidgets, QtGui
from src.core import Parameter, Device, Experiment
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as Canvas
from matplotlib.figure import Figure
import pyqtgraph as pg
import logging

# Set up logging for GUI operations
gui_logger = logging.getLogger('AQuISS_GUI')


# ======== AQuISSQTreeItem ==========
class AQuISSQTreeItem(QtWidgets.QTreeWidgetItem):
    """
    Custom QTreeWidgetItem with Widgets
    """
    
    # Custom signal that only fires when user finishes editing
    editingFinished = QtCore.pyqtSignal(object)  # emits the item itself

    def __init__(self, parent, name, value, valid_values, info, visible=None):
        """
        Args:
            name:
            value:
            valid_values:
            info:
            visible (optional):

        Returns:

        """

        super().__init__(parent)


        self.ui_type = None
        self.name = name
        self.valid_values = valid_values
        self._value = value
        self.info = info
        self._visible = visible

        self.setData(0, 0, self.name)

        if isinstance(self.valid_values, list):
            self.ui_type = 'combo_box'
            self.combo_box = QtWidgets.QComboBox()
            for item in self.valid_values:
                self.combo_box.addItem(str(item))
            self.combo_box.setCurrentIndex(self.combo_box.findText(str(self.value)))
            self.treeWidget().setItemWidget(self, 1, self.combo_box)
            self.combo_box.currentIndexChanged.connect(lambda: self.setData(1, 2, self.combo_box))
            self.combo_box.setFocusPolicy(QtCore.Qt.StrongFocus)
            self._visible = False

        elif self.valid_values is bool:
            self.ui_type = 'checkbox'
            self.checkbox = QtWidgets.QCheckBox()
            self.checkbox.setChecked(self.value)
            self.treeWidget().setItemWidget( self, 1, self.checkbox )
            self.checkbox.stateChanged.connect(lambda: self.setData(1, 2, self.checkbox))
            self._visible = False

        elif isinstance(self.value, Parameter):
            for key, value in self.value.items():
                AQuISSQTreeItem(self, key, value, self.value.valid_values[key], self.value.info[key])

        elif isinstance(self.value, dict):
            for key, value in self.value.items():
                if self.valid_values == dict:
                    AQuISSQTreeItem(self, key, value, type(value), '')
                else:
                    AQuISSQTreeItem(self, key, value, self.valid_values[key], self.info[key])

        elif isinstance(self.value, Device):
            index_top_level_item = self.treeWidget().indexOfTopLevelItem(self)
            top_level_item = self.treeWidget().topLevelItem(index_top_level_item)
            if top_level_item == self:
                # device is on top level, thus we are in the device tab
                for key, value in self.value.settings.items():
                    AQuISSQTreeItem(self, key, value, self.value.settings.valid_values[key], self.value.settings.info[key])
            else:
                self.valid_values = [self.value.name]
                self.value = self.value.name
                self.combo_box = QtWidgets.QComboBox()
                for item in self.valid_values:
                    self.combo_box.addItem(item)
                self.combo_box.setCurrentIndex(self.combo_box.findText(str(self.value)))
                self.treeWidget().setItemWidget(self, 1, self.combo_box)
                self.combo_box.currentIndexChanged.connect(lambda: self.setData(1, 2, self.combo_box))
                self.combo_box.setFocusPolicy(QtCore.Qt.StrongFocus)

        elif isinstance(self.value, Experiment):
            for key, value in self.value.settings.items():
                AQuISSQTreeItem(self, key, value, self.value.settings.valid_values[key], self.value.settings.info[key])

            for key, value in self.value.devices.items():
                AQuISSQTreeItem(self, key, self.value.devices[key],  type(self.value.devices[key]), '')

            for key, value in self.value.experiments.items():
                AQuISSQTreeItem(self, key, self.value.experiments[key],  type(self.value.experiments[key]), '')

            self.info = self.value.__doc__

        else:
            self.setData(1, 0, self.value)
            self._visible = False

        self.setToolTip(1, str(self.info if isinstance(self.info, str) else ''))

        if self._visible is not None:
            self.check_show = QtWidgets.QCheckBox()
            self.check_show.setChecked(self.visible)
            self.treeWidget().setItemWidget(self, 2, self.check_show)

        self.setFlags(self.flags() | QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable)

    @property
    def value(self):
        """
        item value
        """
        return self._value

    @value.setter
    def value(self, value):
        if Parameter.is_valid(value, self.valid_values):
            self._value = value
            # check if there is a special case for setting such as a checkbox or combobox
            if self.ui_type == 'checkbox':
                self.checkbox.setChecked(value)
            elif self.ui_type == 'combo_box':
                self.combo_box.setCurrentIndex(self.combo_box.findText(str(self.value)))
            else:  # for standard values
                self.setData(1, 0, value)
        else:
            if value is not None:
                raise TypeError("wrong type {:s}, expected {:s}".format(str(type(value)), str(self.valid_values)))

    @property
    def visible(self):
        """

        Returns: boolean (True: item is visible) (False: item is hidden)

        """
        if self._visible is not None:
            return self.check_show.isChecked()

        elif isinstance(self._value, (Parameter, dict)):
            # check if any of the children is visible
            for i in range(self.childCount()):
                if self.child(i).visible:
                    return True
            # if none of the children is visible hide this parameter
            return False
        else:
            return True

    @visible.setter
    def visible(self, value):
        if self._visible is not None:
            self._visible = value
            self.check_show.setChecked(self._visible)

    def setData(self, column, role, value):
        """
        if value is valid sets the data to value
        Args:
            column: column of item
            role: role of item (see Qt doc)
            value: value to be set
        """
        assert isinstance(column, int)
        assert isinstance(role, int)

        # make sure that the right row is selected, this is not always the case for checkboxes and
        # combo boxes because they are items on top of the tree structure
        if isinstance(value, (QtWidgets.QComboBox, QtWidgets.QCheckBox)):
            self.treeWidget().setCurrentItem(self)

        # if row 2 (editrole, value has been entered)
        if role == 2 and column == 1:
            # This is user editing - emit our custom signal
            user_editing = True

            if isinstance(value, str):
                value = self.cast_type(value) # cast into same type as valid values

            if isinstance(value, QtCore.QVariant):
                value = self.cast_type(value.toString())  # cast into same type as valid values

            if isinstance(value, QtWidgets.QComboBox):
                value = self.cast_type(value.currentText())

            if isinstance(value, QtWidgets.QCheckBox):
                value = bool(int(value.checkState()))  # checkState() gives 2 (True) and 0 (False)

            # save value in internal variable
            self.value = value
        elif column == 0:
            # labels should not be changed so we set it back
            value = self.name
            user_editing = False
        else:
            user_editing = False

        if value is None:
            value = self.value

        # 180327(asafira) --- why do we need to do the following lines? Why not just always call super or always
        # emitDataChanged()?
        if not isinstance(value, bool):
            super(AQuISSQTreeItem, self).setData(column, role, value)

        else:
            self.emitDataChanged()
        
        # Emit our custom signal only when user finishes editing
        # Note: Currently not connected anywhere, so commented out to avoid errors
        # if user_editing:
        #     self.editingFinished.emit(None)

    def cast_type(self, var, cast_type=None):
        """
        cast the value into the type typ
        if type is not provided it is set to self.valid_values
        Args:
            var: variable to be cast
            type: target type

        Returns: the variable var csat into type typ

        """

        if cast_type is None:
            cast_type = self.valid_values

        try:
            if cast_type == int:
                return int(var)
            elif cast_type == float:
                return float(var)
            elif cast_type == str:
                return str(var)
            elif isinstance(cast_type, list):
                # cast var to be of the same type as those in the list
                return type(cast_type[0])(var)
            else:
                return None
        except ValueError:
            return None

        return var

    def get_device(self):
        """
        Returns: the device and the path to the device to which this item belongs
        """

        if isinstance(self.value, Device):
            device = self.value
            path_to_device = []
        else:
            device = None
            parent = self.parent()
            path_to_device = [self.name]
            while parent is not None:
                if isinstance(parent.value, Device):
                    device = parent.value
                    parent = None
                else:
                    path_to_device.append(parent.name)
                    parent = parent.parent()

        return device, path_to_device

    def get_experiment(self):
        """

        Returns: the experiment and the path to the experiment to which this item belongs

        """

        if isinstance(self.value, Experiment):
            experiment = self.value
            path_to_experiment = []
            experiment_item = self

        else:
            experiment = None
            parent = self.parent()
            path_to_experiment = [self.name]
            while parent is not None:
                if isinstance(parent.value, Experiment):
                    experiment = parent.value
                    experiment_item = parent
                    parent = None
                else:
                    path_to_experiment.append(parent.name)
                    parent = parent.parent()

        return experiment, path_to_experiment, experiment_item

    def get_subexperiment(self, sub_experiment_name):
        """
        finds the item that contains the sub_experiment with name sub_experiment_name
        Args:
            sub_experiment_name: name of subexperiment
        Returns: AQuISSQTreeItem in QTreeWidget which is a experiment

        """

        # get tree of item
        tree = self.treeWidget()

        items = tree.findItems(sub_experiment_name, QtCore.Qt.MatchExactly | QtCore.Qt.MatchRecursive)

        if len(items) >= 1:
            # identify correct experiment by checking that it is a sub_element of the current experiment
            subexperiment_item = [sub_item for sub_item in items if isinstance(sub_item.value, Experiment)
                               and sub_item.parent() is self]

            subexperiment_item = subexperiment_item[0]
        else:
            raise ValueError('several elements with name ' + sub_experiment_name)


        return subexperiment_item

    def is_point(self):
        """
        figures out if item is a point, that is if it has two subelements of type float
        Args:
            self:

        Returns: if item is a point (True) or not (False)

        """

        if self.childCount() == 2:
                if self.child(0).valid_values == float and self.child(1).valid_values == float:
                    return True
        else:
            return False

    def to_dict(self):
        """

        Returns: the tree item as a dictionary

        """
        if self.childCount() > 0:
            value = {}
            for index in range(self.childCount()):
                value.update(self.child(index).to_dict())
        else:
            value = self.value

        return {self.name: value}

class MatplotlibWidget(Canvas):
    """
    MatplotlibWidget inherits PyQt5.QtWidgets.QWidget
    and matplotlib.backend_bases.FigureCanvasBase

    Options: option_name (default_value)
    -------
    parent (None): parent widget
    title (''): figure title
    xlabel (''): X-axis label
    ylabel (''): Y-axis label
    xlim (None): X-axis limits ([min, max])
    ylim (None): Y-axis limits ([min, max])
    xscale ('linear'): X-axis scale
    yscale ('linear'): Y-axis scale
    width (4): width in inches
    height (3): height in inches
    dpi (100): resolution in dpi
    hold (False): if False, figure will be cleared each time plot is called

    Widget attributes:
    -----------------
    figure: instance of matplotlib.figure.Figure
    axes: figure axes

    Example:
    -------
    self.widget = MatplotlibWidget(self, yscale='log', hold=True)
    from numpy import linspace
    x = linspace(-10, 10)
    self.widget.axes.plot(x, x**2)
    self.wdiget.axes.plot(x, x**3)
    """
    def __init__(self, parent=None):
        self.figure = Figure(dpi=100)
        Canvas.__init__(self, self.figure)
        self.axes = self.figure.add_subplot(111)

        self.canvas = self.figure.canvas
        self.setParent(parent)

        Canvas.setSizePolicy(self, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        Canvas.updateGeometry(self)

    def sizeHint(self):
        """
        gives qt a starting point for widget size during window resizing
        """
        w, h = self.get_width_height()
        return QtCore.QSize(w, h)

    def minimumSizeHint(self):
        """
        minimum widget size during window resizing
        Returns: QSize object that specifies the size of widget
        """
        return QtCore.QSize(10, 10)

class PyQtgraphWidget(QtWidgets.QWidget):
    '''
    GraphicsView is parent class of GraphicsLayoutWidget
    '''

    def __init__(self,parent=None):
        super().__init__()

        self.layout = QtWidgets.QVBoxLayout(self)
        self.graph = pg.GraphicsLayoutWidget(parent=parent)
        #self.graph.setBackground('lightgray')
        self.layout.addWidget(self.graph)

        self.plot_item = self.graph.addPlot()   #adds a plot item to next available cell

        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.updateGeometry()

    def sizeHint(self):
        """
        gives qt a starting point for widget size during window resizing
        """
        w = self.width()
        h = self.height()
        return QtCore.QSize(w, h)

    def minimumSizeHint(self):
        """
        minimum widget size during window resizing
        Returns: QSize object that specifies the size of widget
        """
        return QtCore.QSize(10, 10)

    @property
    def get_graph(self):
        return self.graph

class PyQtCoordinatesBar(QtWidgets.QWidget):

    def __init__(self,connected_graph,parent=None):
        super().__init__()

        self.layout = QtWidgets.QVBoxLayout(self)
        self.graph = pg.GraphicsLayoutWidget(parent=parent)
        self.graph.setBackground((255, 255, 255))
        self.layout.addWidget(self.graph)

        self.label = pg.LabelItem(justify='right')
        self.graph.addItem(self.label, row=0,col=0)

        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.updateGeometry()

        self.connected_graph = connected_graph   #gets graphics layoutwidget of connected PyQtgraphWidget
        self.update()

    def update(self):
        '''
        Fucntion is called initally to set up default mouse positioning. Should be called again whenever an experiment finishes to interacte with new plot/data
        '''
        item = self.connected_graph.getItem(row=0, col=0)  # gets a plot item
        #!!!Only work if graphicslayout has 1 plot item!!!
        if isinstance(item, (pg.PlotItem, pg.ImageItem)):
            #only if the item is a PlotItem or ImageItem will it have a viewbox (and coordinates) that your cursor hovers over
            self.viewbox = item.vb
            self.mouse_movement = pg.SignalProxy(self.connected_graph.scene().sigMouseMoved, rateLimit=10, slot=self.mouseMoved)
        else:
            self.viewbox = None

    def mouseMoved(self,event):
        '''
        Funtion gets the cursor coordinate and displays them in a label above graph
        '''
        self.update()
        scene_pos = event[0]
        if self.viewbox != None:
            mousePoint = self.viewbox.mapSceneToView(scene_pos)
            self.label.setText("<span style='font-size: 10pt; color: black'> (x,y) = (%0.2f, %0.2f)</span>" % (mousePoint.x(), mousePoint.y()))

    def sizeHint(self):
        """
        gives qt a starting point for widget size during window resizing
        """
        w = self.width()
        h = self.height()
        return QtCore.QSize(w, h)

    def minimumSizeHint(self):
        """
        minimum widget size during window resizing
        Returns: QSize object that specifies the size of widget
        """
        return QtCore.QSize(10, 10)

# Number clamping delegate for tree widgets
import re

_NUM_RE = re.compile(r'[+\-]?\d+(?:\.\d+)?(?:[eE][+\-]?\d+)?$')

def _parse_number(txt: str):
    t = txt.strip()
    if _NUM_RE.match(t):
        return float(t) if ('.' in t or 'e' in t.lower()) else int(t)
    return None

class NumberClampDelegate(QtWidgets.QStyledItemDelegate):
    """
    Validates/clamps numeric edits for column 1 *inside* the editor->model commit.
    Reads min/max metadata from the item (if present) via UserRole or attributes.
    Expected per-item metadata (optional):
       - item.min_value / item.max_value   (python attrs)
       - or data(UserRole+1) / data(UserRole+2)
       - or a dict in data(UserRole) with keys 'min','max'
    If no bounds are found, passes through unchanged.
    
    Uses model-based visual feedback through BackgroundRole instead of custom painting.
    """
    parameter_feedback_signal = QtCore.pyqtSignal(object, dict) # item, feedback_dict
    validation_result_signal = QtCore.pyqtSignal(object, str, dict) # item, param_name, result_dict
    
    # Custom role for storing feedback state
    FEEDBACK_ROLE = QtCore.Qt.UserRole + 42
    
    def __init__(self, parent=None):
        super().__init__(parent)
    
    def _color_index(self, view, index, reason):
        """Set visual feedback on an index using model-based approach"""
        gui_logger.debug(f"DELEGATE: _color_index called with reason '{reason}' for index {index.row()},{index.column()}")
        
        model = index.model()
        
        # Remember state in custom role
        model.setData(index, reason, self.FEEDBACK_ROLE)
        gui_logger.debug(f"DELEGATE: Set FEEDBACK_ROLE to '{reason}'")
        
        # Choose brush color
        if reason == "success":
            brush = QtGui.QBrush(QtGui.QColor(208, 240, 192))  # light green
        elif reason == "clamped":
            brush = QtGui.QBrush(QtGui.QColor(255, 230, 170))  # light orange
        elif reason == "error":
            brush = QtGui.QBrush(QtGui.QColor(255, 204, 204))  # light red
        else:
            brush = None
        
        # Set background through model
        if brush:
            model.setData(index, brush, QtCore.Qt.BackgroundRole)
            gui_logger.debug(f"DELEGATE: Set BackgroundRole to {brush.color().name()}")
            # Verify what was actually set
            verify_bg = index.data(QtCore.Qt.BackgroundRole)
            gui_logger.debug(f"DELEGATE: Verification - BackgroundRole now contains: {verify_bg} (type: {type(verify_bg)})")
        
        # Make it visible now - use viewport().update() for QTreeWidget
        if hasattr(view, 'viewport'):
            view.viewport().update(view.visualRect(index))
        else:
            view.update(view.visualRect(index))
        
        gui_logger.debug(f"DELEGATE: Called viewport().update() for visual rect")
        
        # Auto-clear after delay
        QtCore.QTimer.singleShot(1500, lambda: self._clear_feedback(view, index))
    
    def _clear_feedback(self, view, index):
        """Clear visual feedback from an index"""
        model = index.model()
        model.setData(index, None, self.FEEDBACK_ROLE)
        model.setData(index, None, QtCore.Qt.BackgroundRole)
        
        # Make it visible now - use viewport().update() for QTreeWidget
        if hasattr(view, 'viewport'):
            view.viewport().update(view.visualRect(index))
        else:
            view.update(view.visualRect(index))
    
    def setFeedback(self, index, status):
        """
        Public method to set visual feedback for an index.
        Uses the new model-based approach.
        
        Args:
            index: QModelIndex for the cell to highlight
            status: "success", "clamped", "error", or None to clear
        """
        view = self.parent()  # the QTreeWidget
        if not isinstance(view, QtWidgets.QAbstractItemView):
            gui_logger.warning(f"DELEGATE: setFeedback - parent is not QAbstractItemView: {type(view)}")
            return
        
        if status is None:
            self._clear_feedback(view, index)
        else:
            self._color_index(view, index, status)
    
    def _is_significantly_different(self, actual_value, requested_value, device, param_name):
        """
        Check if the difference between actual and requested values is significant
        based on device-specific tolerances.
        
        Args:
            actual_value: Value reported by device
            requested_value: Value user requested
            device: Device instance
            param_name: Parameter name
            
        Returns:
            bool: True if difference is significant enough to flag
        """
        # For non-numeric values, use exact comparison
        if not isinstance(actual_value, (int, float)) or not isinstance(requested_value, (int, float)):
            return actual_value != requested_value
        
        # Get device-specific tolerance
        tolerance = self._get_device_tolerance(device, param_name)
        
        if tolerance is None:
            # Fallback to default tolerance (0.1% relative)
            if requested_value != 0:
                relative_diff = abs(actual_value - requested_value) / abs(requested_value)
                return relative_diff > 0.001
            else:
                return abs(actual_value - requested_value) > 1e-6
        
        # Use device-specific tolerance
        if tolerance['type'] == 'relative':
            if requested_value != 0:
                relative_diff = abs(actual_value - requested_value) / abs(requested_value)
                return relative_diff > tolerance['value']
            else:
                # For zero values, use absolute tolerance
                return abs(actual_value - requested_value) > tolerance.get('absolute_fallback', 1e-6)
        elif tolerance['type'] == 'absolute':
            return abs(actual_value - requested_value) > tolerance['value']
        else:
            # Unknown tolerance type, use exact comparison
            return actual_value != requested_value
    
    def _get_device_tolerance(self, device, param_name):
        """
        Get device-specific tolerance for parameter comparison.
        
        Args:
            device: Device instance
            param_name: Parameter name
            
        Returns:
            dict: Tolerance configuration or None for default
        """
        device_name = device.__class__.__name__.lower()
        
        # Device-specific tolerances
        tolerances = {
            'mclnanodrive': {
                'x_pos': {'type': 'absolute', 'value': 0.01},  # 0.01 microns
                'y_pos': {'type': 'absolute', 'value': 0.01},  # 0.01 microns  
                'z_pos': {'type': 'absolute', 'value': 0.01},  # 0.01 microns
            },
            'sg384generator': {
                'frequency': {'type': 'relative', 'value': 0.0001},  # 0.01% (very precise for frequency)
                'sweep_center_frequency': {'type': 'relative', 'value': 0.0001},
                'sweep_max_frequency': {'type': 'relative', 'value': 0.0001},
                'sweep_min_frequency': {'type': 'relative', 'value': 0.0001},
                'power': {'type': 'absolute', 'value': 0.1},  # 0.1 dBm
                'phase': {'type': 'absolute', 'value': 0.1},   # 0.1 degrees
            },
            'adwingolddevice': {
                # ADwin parameters are typically very precise
                'delay': {'type': 'absolute', 'value': 0.001},  # 0.001 seconds
            }
        }
        
        # Check if device has specific tolerance for this parameter
        if device_name in tolerances and param_name in tolerances[device_name]:
            return tolerances[device_name][param_name]
        
        # Check if device has a general tolerance method
        if hasattr(device, 'get_parameter_tolerance'):
            try:
                return device.get_parameter_tolerance(param_name)
            except:
                pass
        
        # No specific tolerance found, use default
        return None
    
    def createEditor(self, parent, option, index):
        # Clear previous color as soon as user starts editing
        self.setFeedback(index, None)
        # Use a QLineEdit so you keep your current UX (free typing + sci notation)
        editor = QtWidgets.QLineEdit(parent)
        editor.setFrame(False)
        # commit on Enter, and when focus leaves
        editor.editingFinished.connect(lambda: self.commitData.emit(editor))
        return editor

    def setEditorData(self, editor, index):
        # Prefer EditRole (numeric), then DisplayRole, then empty
        val = index.data(QtCore.Qt.EditRole)
        if val is None or val == "":
            val = index.data(QtCore.Qt.DisplayRole)
        if val is None:
            val = ""
        editor.setText(str(val))
        editor.selectAll()  # UX nicety: select existing text on focus

    def setModelData(self, editor, model, index):
        raw = editor.text().strip()
        gui_logger.debug(f"DELEGATE: setModelData called with text '{raw}'")
        
        # Check if we already have feedback for this index to prevent double validation
        existing_feedback = index.data(self.FEEDBACK_ROLE)
        if existing_feedback:
            gui_logger.debug(f"DELEGATE: Already have feedback '{existing_feedback}' (type: {type(existing_feedback)})")
            # BUG FIX: If the feedback is a number instead of a string, clear it and continue with validation
            if isinstance(existing_feedback, (int, float)):
                gui_logger.warning(f"DELEGATE: FEEDBACK_ROLE contains numeric value {existing_feedback} instead of reason string - clearing and continuing with validation")
                model.setData(index, None, self.FEEDBACK_ROLE)
                # Don't skip - fall through to continue with validation
            else:
                # Valid string feedback exists, skip validation and just write the value
                gui_logger.debug(f"DELEGATE: Valid feedback exists, skipping validation")
                try:
                    num = float(raw)
                    model.setData(index, num, QtCore.Qt.EditRole)
                    model.setData(index, "{:.3g}".format(num), QtCore.Qt.DisplayRole)
                    # Update the item's internal value
                    view = editor.parent()
                    while view and not isinstance(view, QtWidgets.QAbstractItemView):
                        view = view.parent()
                    if isinstance(view, QtWidgets.QAbstractItemView):
                        tw_item = view.itemFromIndex(index)
                        if tw_item and hasattr(tw_item, 'value'):
                            tw_item.value = num
                    gui_logger.debug(f"DELEGATE: Wrote value {num} without validation")
                except ValueError:
                    gui_logger.debug("DELEGATE: Invalid number in second call, ignoring")
                return
        
        # Handle empty string case - don't update the model
        if not raw:
            gui_logger.debug("DELEGATE: Empty string, reverting editor")
            current_value = index.data(QtCore.Qt.EditRole)
            if current_value is not None:
                editor.setText(str(current_value))
            return
        
        num = _parse_number(raw)
        if num is None:
            gui_logger.debug("DELEGATE: Invalid number, reverting editor")
            current_value = index.data(QtCore.Qt.EditRole)
            if current_value is not None:
                editor.setText(str(current_value))
            return

        gui_logger.debug(f"DELEGATE: Parsed number: {num}")

        # Get the tree item
        view = editor.parent()
        while view and not isinstance(view, QtWidgets.QAbstractItemView):
            view = view.parent()
        if isinstance(view, QtWidgets.QAbstractItemView):
            tw_item = view.itemFromIndex(index)
            gui_logger.debug(f"DELEGATE: Found tree item: {tw_item}")
        else:
            tw_item = None

        if tw_item is None:
            gui_logger.debug("DELEGATE: No tree item found, fallback write")
            # Fallback: just write the number
            model.setData(index, num, QtCore.Qt.EditRole)
            return

        # Try device validation and actual value checking
        final_value = num
        feedback_applied = False
        
        if hasattr(tw_item, 'get_device'):
            device, path_to_device = tw_item.get_device()
            gui_logger.debug(f"DELEGATE: Got device {device} and path {path_to_device}")
            
            if device and hasattr(device, 'validate_parameter'):
                validation_result = device.validate_parameter(path_to_device, num)
                param_name = path_to_device[-1] if path_to_device else tw_item.name
                gui_logger.debug(f"DELEGATE: Validation result: {validation_result}")
                
                if not validation_result.get('valid', True):
                    clamped_value = validation_result.get('clamped_value', num)
                    if clamped_value != num:
                        gui_logger.debug(f"DELEGATE: Value clamped from {num} to {clamped_value}")
                        # Value was clamped - apply visual feedback and emit signal
                        final_value = clamped_value
                        feedback = {
                            'valid': False,
                            'message': f"Parameter {param_name} was clamped from {num} to {clamped_value}",
                            'clamped_value': clamped_value,
                            'requested_value': num,
                            'actual_value': clamped_value,
                            'reason': 'clamped'
                        }
                        gui_logger.info(f"DELEGATE: Emitting clamped signal for {param_name}: {feedback}")
                        self.validation_result_signal.emit(tw_item, param_name, feedback)
                        feedback_applied = True
                    else:
                        gui_logger.debug("DELEGATE: Validation failed, no clamped value")
                        # No clamped value available - emit error signal
                        feedback = {
                            'valid': False,
                            'message': validation_result.get('message', 'Parameter validation failed'),
                            'clamped_value': None,
                            'requested_value': num,
                            'actual_value': None,
                            'reason': 'error'
                        }
                        self.validation_result_signal.emit(tw_item, param_name, feedback)
                        feedback_applied = True
                        return  # Don't update the model
                else:
                    # Validation passed - now check if device reports different actual value
                    if hasattr(device, 'update_and_get'):
                        try:
                            # Update the device and get actual values
                            actual_values = device.update_and_get({param_name: num})
                            actual_value = actual_values.get(param_name, num)
                            
                            # Check if device reported a significantly different value
                            # Use device-specific tolerance to avoid flagging tiny differences
                            is_significantly_different = self._is_significantly_different(
                                actual_value, num, device, param_name
                            )
                            
                            if is_significantly_different:
                                gui_logger.debug(f"DELEGATE: Device reported different value: {actual_value} vs {num}")
                                # Device reported significantly different value - emit signal
                                final_value = actual_value
                                feedback = {
                                    'valid': True,
                                    'message': f"Device reported {param_name} = {actual_value} (requested {num})",
                                    'clamped_value': None,
                                    'requested_value': num,
                                    'actual_value': actual_value,
                                    'reason': 'device_different'
                                }
                                self.validation_result_signal.emit(tw_item, param_name, feedback)
                                feedback_applied = True
                            else:
                                gui_logger.debug("DELEGATE: Device reported same value")
                                # Device reported same value - emit success signal
                                feedback = {
                                    'valid': True,
                                    'message': f"Parameter {param_name} set successfully",
                                    'clamped_value': None,
                                    'requested_value': num,
                                    'actual_value': num,
                                    'reason': 'success'
                                }
                                self.validation_result_signal.emit(tw_item, param_name, feedback)
                                feedback_applied = True
                        except Exception as e:
                            gui_logger.warning(f"Could not get actual value from device: {e}")
                            # Fallback to just setting the requested value
                            feedback = {
                                'valid': True,
                                'message': f"Parameter {param_name} set successfully (no actual value check)",
                                'clamped_value': None,
                                'requested_value': num,
                                'actual_value': num,
                                'reason': 'success'
                            }
                            self.validation_result_signal.emit(tw_item, param_name, feedback)
                            feedback_applied = True
                    else:
                        gui_logger.debug("DELEGATE: No update_and_get method, emitting success")
                        # No update_and_get method - emit success signal
                        feedback = {
                            'valid': True,
                            'message': f"Parameter {param_name} set successfully",
                            'clamped_value': None,
                            'requested_value': num,
                            'actual_value': num,
                            'reason': 'success'
                        }
                        self.validation_result_signal.emit(tw_item, param_name, feedback)
                        feedback_applied = True
        else:
            gui_logger.debug("DELEGATE: No device validation, using attribute-based")
            # Fallback to attribute-based validation
            min_v = getattr(tw_item, "min_value", None)
            max_v = getattr(tw_item, "max_value", None)
            
            if min_v is not None: final_value = max(final_value, float(min_v))
            if max_v is not None: final_value = min(final_value, float(max_v))

        # Only apply success feedback if no other feedback was applied
        if not feedback_applied:
            gui_logger.debug("DELEGATE: No device validation, emitting success")
            feedback = {
                'valid': True,
                'message': f"Parameter set successfully",
                'clamped_value': None,
                'requested_value': num,
                'actual_value': final_value,
                'reason': 'success'
            }
            self.validation_result_signal.emit(tw_item, tw_item.name, feedback)

        # write via EditRole so the model/view/editor stay consistent
        model.setData(index, final_value, QtCore.Qt.EditRole)
        
        # Optional: keep a consistent display string
        model.setData(index, "{:.3g}".format(final_value), QtCore.Qt.DisplayRole)

        # Update the item's internal value
        if hasattr(tw_item, 'value'):
            tw_item.value = final_value
        
        gui_logger.debug(f"DELEGATE: Final value set to {final_value}")
    
    def paint(self, painter: QtGui.QPainter, option: QtWidgets.QStyleOptionViewItem, index: QtCore.QModelIndex):
        """Paint the item with manual background handling"""
        
        # Check if there's a background color set
        bg_data = index.data(QtCore.Qt.BackgroundRole)
        if bg_data:
            gui_logger.debug(f"DELEGATE: paint found BackgroundRole data: {bg_data} (type: {type(bg_data)})")
            
            # Convert to QBrush if needed
            if isinstance(bg_data, QtGui.QBrush):
                bg_brush = bg_data
            elif isinstance(bg_data, QtGui.QColor):
                bg_brush = QtGui.QBrush(bg_data)
            elif isinstance(bg_data, (int, float)):
                # Numeric values don't make sense as background colors
                # This is likely a bug - clear the invalid background data
                gui_logger.warning(f"DELEGATE: Invalid numeric background value: {bg_data}, clearing it")
                model = index.model()
                if model:
                    model.setData(index, None, QtCore.Qt.BackgroundRole)
                bg_brush = None
            else:
                gui_logger.warning(f"DELEGATE: Unknown background data type: {type(bg_data)}")
                bg_brush = None
            
            if bg_brush:
                # Fill the background manually first
                painter.fillRect(option.rect, bg_brush)
        
        # Create a copy of the option and initialize it
        opt = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        
        # Clear the background brush so the style doesn't override our manual fill
        if bg_data:
            opt.backgroundBrush = QtGui.QBrush()
        
        # Let the style system handle the text and other elements
        style = opt.widget.style() if opt.widget else QtWidgets.QApplication.style()
        style.drawControl(QtWidgets.QStyle.CE_ItemViewItem, opt, painter, opt.widget)
