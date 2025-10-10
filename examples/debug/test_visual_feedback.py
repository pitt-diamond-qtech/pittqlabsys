#!/usr/bin/env python3
"""
Minimal test case for visual feedback in QTreeWidget with custom delegate.
This isolates the background color issue from the full GUI complexity.
"""

import sys
import logging
from PyQt5 import QtWidgets, QtCore, QtGui

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('VisualFeedbackTest')

class MockDevice:
    """Mock device for testing validation"""
    def __init__(self):
        self.frequency = 1000000000.0  # 1 GHz
    
    def validate_parameter(self, path, value):
        """Mock validation that clamps frequency to 4.1 GHz max and power to +10 dBm max"""
        if path and path[-1] == 'frequency':
            if value > 4100000000.0:
                return {
                    'valid': False,
                    'message': f'Frequency {value/1e9:.1f} GHz above maximum 4.1 GHz',
                    'clamped_value': 4100000000.0
                }
        elif path and path[-1] == 'power':
            if value > 10.0:
                return {
                    'valid': False,
                    'message': f'Power {value} dBm above maximum +10 dBm',
                    'clamped_value': 10.0
                }
        return {'valid': True, 'message': 'Parameter set successfully'}

class MockTreeItem(QtWidgets.QTreeWidgetItem):
    """Mock tree item that mimics AQuISSQTreeWidgetItem"""
    def __init__(self, name, value, device=None):
        super().__init__()
        self.name = name
        self.value = value
        self.device = device
        self.setText(0, name)
        self.setText(1, str(value))
        
        # Make the value column (column 1) editable
        self.setFlags(self.flags() | QtCore.Qt.ItemIsEditable)
    
    def get_device(self):
        """Return device and path for validation"""
        if self.device:
            return self.device, [self.name]
        return None, []

class TestDelegate(QtWidgets.QStyledItemDelegate):
    """Test delegate for visual feedback"""
    
    # Custom role for storing feedback state
    FEEDBACK_ROLE = QtCore.Qt.UserRole + 42
    
    def __init__(self, parent=None):
        super().__init__(parent)
        logger.debug("TestDelegate initialized")
    
    def _color_index(self, view, index, reason):
        """Set visual feedback on an index using model-based approach"""
        logger.debug(f"DELEGATE: _color_index called with reason '{reason}' for index {index.row()},{index.column()}")
        
        model = index.model()
        
        # Remember state in custom role
        model.setData(index, reason, self.FEEDBACK_ROLE)
        logger.debug(f"DELEGATE: Set FEEDBACK_ROLE to '{reason}'")
        
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
            logger.debug(f"DELEGATE: Set BackgroundRole to {brush.color().name()}")
        
        # Make it visible now - use viewport().update() for QTreeWidget
        if hasattr(view, 'viewport'):
            view.viewport().update(view.visualRect(index))
            logger.debug(f"DELEGATE: Called viewport().update() for visual rect")
        else:
            view.update(view.visualRect(index))
            logger.debug(f"DELEGATE: Called view.update() for visual rect")
        
        # Auto-clear after delay
        QtCore.QTimer.singleShot(3000, lambda: self._clear_feedback(view, index))
    
    def _clear_feedback(self, view, index):
        """Clear visual feedback from an index"""
        logger.debug(f"DELEGATE: Clearing feedback for index {index.row()},{index.column()}")
        model = index.model()
        model.setData(index, None, self.FEEDBACK_ROLE)
        model.setData(index, None, QtCore.Qt.BackgroundRole)
        
        # Make it visible now - use viewport().update() for QTreeWidget
        if hasattr(view, 'viewport'):
            view.viewport().update(view.visualRect(index))
        else:
            view.update(view.visualRect(index))
    
    def createEditor(self, parent, option, index):
        """Create editor for editing"""
        logger.debug(f"DELEGATE: Creating editor for index {index.row()},{index.column()}")
        editor = QtWidgets.QLineEdit(parent)
        editor.setFrame(False)
        # Connect editingFinished to commitData
        editor.editingFinished.connect(lambda: self.commitData.emit(editor))
        logger.debug(f"DELEGATE: Editor created and connected")
        return editor
    
    def setEditorData(self, editor, index):
        """Set editor data"""
        val = index.data(QtCore.Qt.EditRole)
        if val is None:
            val = index.data(QtCore.Qt.DisplayRole)
        if val is None:
            val = ""
        editor.setText(str(val))
        editor.selectAll()
        logger.debug(f"DELEGATE: Set editor data to '{val}'")
    
    def setModelData(self, editor, model, index):
        """Set model data with validation"""
        raw = editor.text().strip()
        logger.debug(f"DELEGATE: setModelData called with text '{raw}'")
        
        # Check if we already have feedback for this index
        existing_feedback = index.data(self.FEEDBACK_ROLE)
        if existing_feedback:
            logger.debug(f"DELEGATE: Already have feedback '{existing_feedback}', skipping validation")
            # Just write the value without validation
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
                logger.debug(f"DELEGATE: Wrote value {num} without validation")
            except ValueError:
                logger.debug("DELEGATE: Invalid number in second call, ignoring")
            return
        
        if not raw:
            logger.debug("DELEGATE: Empty string, reverting editor")
            current_value = index.data(QtCore.Qt.EditRole)
            if current_value is not None:
                editor.setText(str(current_value))
            return
        
        try:
            num = float(raw)
            logger.debug(f"DELEGATE: Parsed number: {num}")
        except ValueError:
            logger.debug("DELEGATE: Invalid number, reverting editor")
            current_value = index.data(QtCore.Qt.EditRole)
            if current_value is not None:
                editor.setText(str(current_value))
            return
        
        # Get the tree item
        view = editor.parent()
        while view and not isinstance(view, QtWidgets.QAbstractItemView):
            view = view.parent()
        
        if isinstance(view, QtWidgets.QAbstractItemView):
            tw_item = view.itemFromIndex(index)
            logger.debug(f"DELEGATE: Found tree item: {tw_item}")
        else:
            tw_item = None
            logger.debug("DELEGATE: Could not find tree item")
        
        if tw_item is None:
            # Fallback: just write the number
            model.setData(index, num, QtCore.Qt.EditRole)
            logger.debug("DELEGATE: Fallback - just setting number")
            return
        
        # Try device validation
        final_value = num
        feedback_applied = False
        
        if hasattr(tw_item, 'get_device'):
            device, path_to_device = tw_item.get_device()
            logger.debug(f"DELEGATE: Got device {device} and path {path_to_device}")
            
            if device and hasattr(device, 'validate_parameter'):
                validation_result = device.validate_parameter(path_to_device, num)
                logger.debug(f"DELEGATE: Validation result: {validation_result}")
                
                if not validation_result.get('valid', True):
                    clamped_value = validation_result.get('clamped_value', num)
                    if clamped_value != num:
                        logger.debug(f"DELEGATE: Value clamped from {num} to {clamped_value}")
                        final_value = clamped_value
                        # Apply visual feedback for clamping
                        self._apply_feedback(view, index, "clamped")
                        feedback_applied = True
                    else:
                        logger.debug("DELEGATE: Validation failed, no clamped value")
                        self._apply_feedback(view, index, "error")
                        feedback_applied = True
                        return
        
        # Only apply success feedback if no other feedback was applied
        if not feedback_applied:
            logger.debug("DELEGATE: Validation passed")
            self._apply_feedback(view, index, "success")
        
        # Write the final value
        model.setData(index, final_value, QtCore.Qt.EditRole)
        model.setData(index, "{:.3g}".format(final_value), QtCore.Qt.DisplayRole)
        
        # Update the item's internal value
        if hasattr(tw_item, 'value'):
            tw_item.value = final_value
        
        logger.debug(f"DELEGATE: Final value set to {final_value}")
        
        # If the value was clamped, don't call setModelData again
        if final_value != num:
            logger.debug(f"DELEGATE: Value was clamped, skipping second setModelData call")
            return
    
    def _apply_feedback(self, view, index, reason):
        """Apply visual feedback"""
        logger.debug(f"DELEGATE: Applying feedback '{reason}' to index {index.row()},{index.column()}")
        self._color_index(view, index, reason)
    
    def paint(self, painter: QtGui.QPainter, option: QtWidgets.QStyleOptionViewItem, index: QtCore.QModelIndex):
        """Paint the item with manual background handling"""
        logger.debug(f"DELEGATE: paint called for index {index.row()},{index.column()}")
        
        # Check if there's a background color set
        bg_brush = index.data(QtCore.Qt.BackgroundRole)
        if bg_brush:
            logger.debug(f"DELEGATE: Found background brush: {bg_brush}")
            # Fill the background manually first
            painter.fillRect(option.rect, bg_brush)
            logger.debug(f"DELEGATE: Manually filled background with {bg_brush.color().name()}")
        
        # Create a copy of the option and initialize it
        opt = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        
        # Clear the background brush so the style doesn't override our manual fill
        if bg_brush:
            opt.backgroundBrush = QtGui.QBrush()
        
        # Let the style system handle the text and other elements
        style = opt.widget.style() if opt.widget else QtWidgets.QApplication.style()
        style.drawControl(QtWidgets.QStyle.CE_ItemViewItem, opt, painter, opt.widget)

class TestWindow(QtWidgets.QMainWindow):
    """Test window with QTreeWidget and delegate"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Visual Feedback Test")
        self.setGeometry(100, 100, 600, 400)
        
        # Create central widget
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        
        # Create layout
        layout = QtWidgets.QVBoxLayout(central_widget)
        
        # Create tree widget
        self.tree = QtWidgets.QTreeWidget()
        self.tree.setHeaderLabels(["Parameter", "Value"])
        self.tree.setColumnWidth(0, 200)
        self.tree.setColumnWidth(1, 200)
        
        # Enable editing
        self.tree.setEditTriggers(QtWidgets.QAbstractItemView.DoubleClicked | QtWidgets.QAbstractItemView.EditKeyPressed)
        logger.debug("Tree widget configured for editing")
        
        # Add debug logging for editing events
        self.tree.itemDoubleClicked.connect(self.on_item_double_clicked)
        
        # Create delegate
        self.delegate = TestDelegate(self.tree)
        self.tree.setItemDelegateForColumn(1, self.delegate)
        
        # Create mock device
        self.device = MockDevice()
        
        # Add test items
        self.add_test_items()
        
        # Add tree to layout
        layout.addWidget(self.tree)
        
        # Add test buttons
        button_layout = QtWidgets.QHBoxLayout()
        
        test_clamped_btn = QtWidgets.QPushButton("Test Orange (Clamped)")
        test_clamped_btn.clicked.connect(self.test_clamped_feedback)
        button_layout.addWidget(test_clamped_btn)
        
        test_success_btn = QtWidgets.QPushButton("Test Green (Success)")
        test_success_btn.clicked.connect(self.test_success_feedback)
        button_layout.addWidget(test_success_btn)
        
        test_clear_btn = QtWidgets.QPushButton("Clear Feedback")
        test_clear_btn.clicked.connect(self.clear_feedback)
        button_layout.addWidget(test_clear_btn)
        
        layout.addLayout(button_layout)
        
        # Add instructions
        instructions = QtWidgets.QLabel(
            "Instructions:\n"
            "1. Double-click on a value cell to edit it\n"
            "2. Try entering a frequency > 4.1 GHz (e.g., 6.0) - should clamp to 4.1 GHz\n"
            "3. Try entering a power > +10 dBm (e.g., 15.0) - should clamp to +10 dBm\n"
            "4. Or use the test buttons to manually test colors\n"
            "5. Watch for orange background (clamped) or green (success)\n"
            "6. Colors auto-clear after 1.5 seconds\n"
            "7. Check console for debug logs"
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        logger.debug("TestWindow initialized")
    
    def add_test_items(self):
        """Add test items to the tree"""
        # Add frequency item
        freq_item = MockTreeItem("frequency", 1000000000.0, self.device)
        self.tree.addTopLevelItem(freq_item)
        
        # Add power item
        power_item = MockTreeItem("power", -10.0, self.device)
        self.tree.addTopLevelItem(power_item)
        
        # Add phase item
        phase_item = MockTreeItem("phase", 0.0, self.device)
        self.tree.addTopLevelItem(phase_item)
        
        logger.debug("Added test items to tree")
    
    def on_item_double_clicked(self, item, column):
        """Debug logging for double-click events"""
        logger.debug(f"Item double-clicked: {item.text(0)} column {column}")
        if column == 1:  # Value column
            logger.debug(f"Attempting to edit value: {item.text(1)}")
    
    def test_clamped_feedback(self):
        """Test clamped feedback (orange)"""
        logger.debug("Testing clamped feedback")
        item = self.tree.topLevelItem(0)  # frequency item
        if item:
            index = self.tree.indexFromItem(item, 1)
            if index.isValid():
                self.delegate._color_index(self.tree, index, "clamped")
                logger.debug("Applied clamped feedback to frequency item")
    
    def test_success_feedback(self):
        """Test success feedback (green)"""
        logger.debug("Testing success feedback")
        item = self.tree.topLevelItem(0)  # frequency item
        if item:
            index = self.tree.indexFromItem(item, 1)
            if index.isValid():
                self.delegate._color_index(self.tree, index, "success")
                logger.debug("Applied success feedback to frequency item")
    
    def clear_feedback(self):
        """Clear all feedback"""
        logger.debug("Clearing all feedback")
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            if item:
                index = self.tree.indexFromItem(item, 1)
                if index.isValid():
                    self.delegate._clear_feedback(self.tree, index)
        logger.debug("Cleared feedback from all items")

def main():
    """Main function"""
    app = QtWidgets.QApplication(sys.argv)
    
    # Create and show test window
    window = TestWindow()
    window.show()
    
    logger.info("Visual Feedback Test started")
    logger.info("Try editing the frequency value to a number > 4.1 GHz")
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
