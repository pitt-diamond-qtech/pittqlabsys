#!/usr/bin/env python3
"""
Parameter Widget for GUI integration.

This module provides GUI widgets for the Parameter class, including:
- Unit-aware parameter input widgets
- Multi-unit display widgets
- Parameter editing dialogs
"""

try:
    from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLineEdit, 
                                QLabel, QComboBox, QPushButton, QDialog, 
                                QFormLayout, QSpinBox, QDoubleSpinBox, 
                                QCheckBox, QApplication)
    from PyQt5.QtCore import pyqtSignal, Qt
    PYQT5_AVAILABLE = True
except ImportError:
    PYQT5_AVAILABLE = False


class ParameterWidget(QWidget):
    """
    Unit-aware parameter input widget.
    
    This widget provides a GUI interface for editing Parameter objects,
    with automatic unit conversion and validation.
    """
    
    valueChanged = pyqtSignal(str, object)  # key, new_value
    
    def __init__(self, parameter, key=None, parent=None):
        """
        Initialize the parameter widget.
        
        Args:
            parameter: Parameter object to edit
            key: Parameter key (if None, uses first parameter)
            parent: Parent widget
        """
        if not PYQT5_AVAILABLE:
            raise ImportError("PyQt5 is required for ParameterWidget")
        
        super().__init__(parent)
        
        self.parameter = parameter
        self.key = key or list(parameter.keys())[0] if parameter else None
        
        if self.key is None:
            raise ValueError("No parameter key specified")
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Set up the user interface."""
        layout = QHBoxLayout()
        
        # Parameter name label
        name_label = QLabel(f"{self.key}:")
        layout.addWidget(name_label)
        
        # Value input
        self.value_edit = QLineEdit()
        
        # Display magnitude for pint quantities, full value for others
        current_value = self.parameter[self.key]
        if hasattr(current_value, 'magnitude') and hasattr(current_value, 'units'):
            self.value_edit.setText(f"{current_value.magnitude:.6g}")
        else:
            self.value_edit.setText(str(current_value))
        
        layout.addWidget(self.value_edit)
        
        # Unit selector (if pint quantity)
        self.unit_combo = None
        if self.parameter.is_pint_quantity(self.key):
            self.unit_combo = QComboBox()
            compatible_units = self.parameter.get_compatible_units(self.key)
            self.unit_combo.addItems(compatible_units)
            
            # Set current unit to best display unit
            from src.core.unit_utils import get_best_display_unit
            current_unit = get_best_display_unit(self.parameter[self.key])
            if current_unit in compatible_units:
                self.unit_combo.setCurrentText(current_unit)
            else:
                # For frequency, default to GHz for display
                if self.parameter[self.key].dimensionality == ur.Hz.dimensionality:
                    self.unit_combo.setCurrentText('GHz')
                else:
                    self.unit_combo.setCurrentText(str(self.parameter[self.key].units))
            
            layout.addWidget(self.unit_combo)
        
        # Unit display (for non-pint quantities)
        elif self.parameter.units.get(self.key):
            unit_label = QLabel(self.parameter.units[self.key])
            layout.addWidget(unit_label)
        
        self.setLayout(layout)
    
    def _connect_signals(self):
        """Connect widget signals."""
        self.value_edit.textChanged.connect(self._on_value_changed)
        if self.unit_combo:
            self.unit_combo.currentTextChanged.connect(self._on_unit_changed)
    
    def _on_value_changed(self, text):
        """Handle value changes."""
        try:
            # Try to convert to appropriate type
            current_value = self.parameter[self.key]
            
            # Handle pint quantities
            if hasattr(current_value, 'magnitude') and hasattr(current_value, 'units'):
                # For pint quantities, create a new quantity with the same units
                try:
                    new_magnitude = float(text)
                    new_value = new_magnitude * current_value.units
                except ValueError:
                    # Invalid number, ignore
                    return
            elif isinstance(current_value, (int, float)):
                new_value = type(current_value)(text)
            else:
                new_value = text
            
            # Update parameter
            self.parameter[self.key] = new_value
            self.valueChanged.emit(self.key, new_value)
        except (ValueError, TypeError):
            # Invalid value, ignore
            pass
    
    def _on_unit_changed(self, unit_text):
        """Handle unit changes."""
        try:
            # Use unit utilities for conversion
            from src.core.unit_utils import convert_to_common_unit
            current_value = self.parameter[self.key]
            new_value = convert_to_common_unit(current_value, unit_text)
            
            # Update the parameter with the converted value
            self.parameter[self.key] = new_value
            self.valueChanged.emit(self.key, new_value)
            
            # Update display to show the new magnitude
            self.value_edit.setText(f"{new_value.magnitude:.6g}")
        except Exception as e:
            # Conversion failed, ignore but print for debugging
            print(f"Unit conversion failed: {e}")
            pass
    
    def get_value(self):
        """Get the current parameter value."""
        return self.parameter[self.key]
    
    def set_value(self, value):
        """Set the parameter value."""
        self.parameter[self.key] = value
        
        # Display the magnitude for pint quantities
        if hasattr(value, 'magnitude') and hasattr(value, 'units'):
            self.value_edit.setText(f"{value.magnitude:.6g}")
        else:
            self.value_edit.setText(str(value))


class ParameterDisplay(QWidget):
    """
    Multi-unit parameter display widget.
    
    This widget displays parameter values with automatic unit conversion
    and multiple unit display options.
    """
    
    def __init__(self, parameter, key=None, target_units=None, parent=None):
        """
        Initialize the parameter display widget.
        
        Args:
            parameter: Parameter object to display
            key: Parameter key (if None, uses first parameter)
            target_units: Target units for display
            parent: Parent widget
        """
        if not PYQT5_AVAILABLE:
            raise ImportError("PyQt5 is required for ParameterDisplay")
        
        super().__init__(parent)
        
        self.parameter = parameter
        self.key = key or list(parameter.keys())[0] if parameter else None
        self.target_units = target_units
        
        if self.key is None:
            raise ValueError("No parameter key specified")
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the user interface."""
        layout = QHBoxLayout()
        
        # Parameter name label
        name_label = QLabel(f"{self.key}:")
        layout.addWidget(name_label)
        
        # Value display
        self.value_label = QLabel()
        self._update_display()
        layout.addWidget(self.value_label)
        
        self.setLayout(layout)
    
    def _update_display(self):
        """Update the display text."""
        if self.parameter.is_pint_quantity(self.key):
            if self.target_units:
                converted = self.parameter.get_value_in_units(self.target_units, self.key)
                display_text = f"{converted.magnitude:.3f} {converted.units}"
            else:
                # Show in multiple common units
                value = self.parameter[self.key]
                display_text = f"{value.magnitude:.3f} {value.units}"
                
                # Add common conversions
                try:
                    if hasattr(value, 'to'):
                        if 'Hz' in str(value.units):
                            ghz = value.to('GHz')
                            display_text += f" ({ghz.magnitude:.3f} GHz)"
                        elif 'K' in str(value.units):
                            celsius = value.to('degC')
                            display_text += f" ({celsius.magnitude:.1f} °C)"
                        elif 'V' in str(value.units):
                            mv = value.to('mV')
                            display_text += f" ({mv.magnitude:.1f} mV)"
                except:
                    pass
        else:
            display_text = str(self.parameter[self.key])
            if self.parameter.units.get(self.key):
                display_text += f" {self.parameter.units[self.key]}"
        
        self.value_label.setText(display_text)
    
    def update_display(self):
        """Update the display (call when parameter changes)."""
        self._update_display()
    
    def set_target_units(self, target_units):
        """Set target units for display."""
        self.target_units = target_units
        self._update_display()


class ParameterDialog(QDialog):
    """
    Dialog for editing parameter values.
    
    This dialog provides a form-based interface for editing Parameter objects
    with validation and unit conversion.
    """
    
    def __init__(self, parameter, parent=None):
        """
        Initialize the parameter dialog.
        
        Args:
            parameter: Parameter object to edit
            parent: Parent widget
        """
        if not PYQT5_AVAILABLE:
            raise ImportError("PyQt5 is required for ParameterDialog")
        
        super().__init__(parent)
        
        self.parameter = parameter
        self.widgets = {}
        
        self.setWindowTitle("Edit Parameters")
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout()
        
        # Form layout for parameters
        form_layout = QFormLayout()
        
        for key, value in self.parameter.items():
            # Check if this is a pint quantity
            if hasattr(value, 'magnitude') and hasattr(value, 'units'):
                # Use ParameterWidget for pint quantities
                widget = create_parameter_widget(self.parameter, key, self)
            elif isinstance(value, (int, float)):
                # Numeric parameter
                if isinstance(value, int):
                    widget = QSpinBox()
                    widget.setRange(-999999, 999999)
                    widget.setValue(value)
                else:
                    widget = QDoubleSpinBox()
                    widget.setRange(-999999.0, 999999.0)
                    widget.setDecimals(6)
                    widget.setValue(value)
            elif isinstance(value, bool):
                # Boolean parameter
                widget = QCheckBox()
                widget.setChecked(value)
            else:
                # String or other parameter
                widget = QLineEdit()
                widget.setText(str(value))
            
            self.widgets[key] = widget
            form_layout.addRow(f"{key}:", widget)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        cancel_button = QPushButton("Cancel")
        
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def accept(self):
        """Handle dialog acceptance."""
        try:
            # Update parameter values
            for key, widget in self.widgets.items():
                if hasattr(widget, '__class__') and widget.__class__.__name__ == 'ParameterWidget':
                    # ParameterWidget handles its own updates, no need to do anything
                    pass
                elif isinstance(widget, QSpinBox):
                    self.parameter[key] = widget.value()
                elif isinstance(widget, QDoubleSpinBox):
                    self.parameter[key] = widget.value()
                elif isinstance(widget, QCheckBox):
                    self.parameter[key] = widget.isChecked()
                elif isinstance(widget, QLineEdit):
                    self.parameter[key] = widget.text()
            
            super().accept()
        except Exception as e:
            # Validation failed, show error
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Validation Error", str(e))


def create_parameter_widget(parameter, key=None, parent=None):
    """
    Factory function to create appropriate parameter widget.
    
    Args:
        parameter: Parameter object
        key: Parameter key
        parent: Parent widget
        
    Returns:
        ParameterWidget or None if PyQt5 not available
    """
    if not PYQT5_AVAILABLE:
        return None
    
    try:
        # Check if QApplication exists
        app = QApplication.instance()
        if app is None:
            # No QApplication exists, return None to avoid crashes
            return None
        
        return ParameterWidget(parameter, key, parent)
    except Exception:
        return None


def create_parameter_display(parameter, key=None, target_units=None, parent=None):
    """
    Factory function to create parameter display widget.
    
    Args:
        parameter: Parameter object
        key: Parameter key
        target_units: Target units
        parent: Parent widget
        
    Returns:
        ParameterDisplay or None if PyQt5 not available
    """
    if not PYQT5_AVAILABLE:
        return None
    
    try:
        # Check if QApplication exists
        app = QApplication.instance()
        if app is None:
            # No QApplication exists, return None to avoid crashes
            return None
        
        return ParameterDisplay(parameter, key, target_units, parent)
    except Exception:
        return None


def edit_parameters_dialog(parameter, parent=None):
    """
    Open a dialog to edit parameters.
    
    Args:
        parameter: Parameter object to edit
        parent: Parent widget
        
    Returns:
        bool: True if accepted, False if cancelled
    """
    if not PYQT5_AVAILABLE:
        return False
    
    try:
        # Check if QApplication exists
        app = QApplication.instance()
        if app is None:
            # No QApplication exists, return False to avoid crashes
            return False
        
        dialog = ParameterDialog(parameter, parent)
        return dialog.exec_() == QDialog.Accepted
    except Exception:
        return False 