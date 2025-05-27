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


# ======== AQuISSQTreeItem ==========
class AQuISSQTreeItem(QtWidgets.QTreeWidgetItem):
    """
    Custom QTreeWidgetItem with Widgets
    """

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

        if value is None:
            value = self.value

        # 180327(asafira) --- why do we need to do the following lines? Why not just always call super or always
        # emitDataChanged()?
        if not isinstance(value, bool):
            super(AQuISSQTreeItem, self).setData(column, role, value)

        else:
            self.emitDataChanged()

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

        self.left_label = pg.LabelItem(justify='left')
        self.left_label.setText("<span style='font-size: 10pt; color: black'> Click mouse and hold either 'Ctrl' to save point, 'Alt' to remove last point, "
                                "or 'Shift' to see all saved points.</span>")
        self.right_label = pg.LabelItem(justify='right')
        self.graph.addItem(self.left_label, row=0,col=0)
        self.graph.addItem(self.right_label, row=0,col=1)

        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.updateGeometry()

        self.connected_graph = connected_graph   #gets graphics layoutwidget of connected widget
        self.update()

        self.saved_points = []

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
            self.mouse_clicked = pg.SignalProxy(self.connected_graph.scene().sigMouseClicked, rateLimit=1, slot=self.mouseClicked)
            #clears saved points since 'new' plot is going to be loaded
            #self.saved_points.clear()
        else:
            self.viewbox = None

    def mouseMoved(self,event):
        '''
        Funtion gets the cursor coordinate and displays them in a label above graph
        '''
        self.update()
        scene_pos = event[0]
        if not self.viewbox == None:
            mousePoint = self.viewbox.mapSceneToView(scene_pos)
            self.left_label.setText("<span style='font-size: 10pt; color: black'> x = %0.2f, y = %0.2f</span>" % (mousePoint.x(), mousePoint.y()))


    def mouseClicked(self,event):
        '''
        Function saved the clicked point to list when a point on graph is clicked. List can then be accessed for later use.
        For readablity concerns should add max of 9 points. This probably could be expanded if more thought is put in to this function
        '''
        if not self.viewbox == None:
        #if control key is held saves mouse position to list
            if event[0].modifiers() & QtCore.Qt.ControlModifier:
                scene_pos = event[0].scenePos()
                mousePoint = self.viewbox.mapSceneToView(scene_pos)
                self.saved_points.append([round(mousePoint.x(),2),round(mousePoint.y(),2)])
                new_point = self.saved_points[-1]
                string = ''
                for i in range(len(self.saved_points)):
                    string = string +str(self.saved_points[i]) + ', '
                self.right_label.setText("<span style='font-size: 10pt; color: black'> x=%0.2f,y=%0.2f added.</span>" % (new_point[0],new_point[1]) + f"<span style='font-size: "
                                                                                                                                                   f"10pt; color: black'> All points: {string} </span>")
                print(self.saved_points)

            #if alt key is held removes last point
            elif event[0].modifiers() & QtCore.Qt.AltModifier:
                if len(self.saved_points) > 0:
                    last_point = self.saved_points.pop()
                    print(self.saved_points)
                    if len(self.saved_points) == 0:
                        self.right_label.setText("<span style='font-size: 10pt; color: black'> Removed x=%0.2f, y=%0.2f. No saved points</span>" % (last_point[0],last_point[1]))
                    else:
                        new_point = self.saved_points[-1]
                        string = ''
                        for i in range(len(self.saved_points)):
                            string = string +str(self.saved_points[i]) + ', '
                        self.right_label.setText("<span style='font-size: 10pt; color: black'> Removed x=%0.2f,y=%0.2f. </span>" % (last_point[0],last_point[1]) +
                                                f"<span style='font-size: 10pt; color: black'> All points: {string} </span>")

            #if shift key is held shows full list
            elif event[0].modifiers() & QtCore.Qt.ShiftModifier:
                string = ''
                for i in range(len(self.saved_points)):
                    string = string +str(self.saved_points[i]) + ', '
                self.right_label.setText(f"<span style='font-size: 10pt; color: black'> {string} </span>")

    @property
    def get_saved_points(self):
        return self.saved_points

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