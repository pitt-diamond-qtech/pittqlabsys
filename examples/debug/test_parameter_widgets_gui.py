#!/usr/bin/env python3
"""
Example script demonstrating Parameter widgets with QApplication.

This script shows how to use the parameter widgets in a GUI context:
- ParameterWidget: Unit-aware parameter input widget
- ParameterDisplay: Multi-unit display widget
- ParameterDialog: Parameter editing dialog
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLabel, QGroupBox
    from PyQt5.QtCore import Qt
    PYQT5_AVAILABLE = True
except ImportError:
    print("PyQt5 not available. This example requires PyQt5 to be installed.")
    sys.exit(1)

from src.core.parameter import Parameter
from src import ur
from src.View.windows_and_widgets.parameter_widget import (
    create_parameter_widget,
    create_parameter_display,
    edit_parameters_dialog
)


class ParameterWidgetDemo(QMainWindow):
    """Demo window showing parameter widgets in action."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Parameter Widget Demo")
        self.setGeometry(100, 100, 800, 600)
        
        # Create some example parameters
        self.parameters = Parameter([
            Parameter('frequency', 2.85e9 * ur.Hz, float, 'Microwave Frequency'),
            Parameter('power', -45.0, float, 'Microwave Power', units='dBm'),
            Parameter('temperature', 298.15 * ur.K, float, 'Temperature'),
            Parameter('voltage', 5.0, float, 'Voltage', min_value=0.0, max_value=10.0),
            Parameter('enabled', True, bool, 'Device Enabled'),
            Parameter('filename', 'experiment.txt', str, 'Filename', 
                     pattern=r'^[a-zA-Z0-9_]+\.txt$')
        ])
        
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("Parameter Widget Demo")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Description
        desc = QLabel("This demo shows parameter widgets with unit conversion and validation.")
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)
        
        # Input widgets section
        input_group = QGroupBox("Parameter Input Widgets")
        input_layout = QVBoxLayout()
        
        # Create input widgets for each parameter
        self.input_widgets = {}
        for key in self.parameters.keys():
            widget = create_parameter_widget(self.parameters, key)
            if widget:
                self.input_widgets[key] = widget
                input_layout.addWidget(widget)
        
        input_group.setLayout(input_layout)
        layout.addWidget(input_group)
        
        # Display widgets section
        display_group = QGroupBox("Parameter Display Widgets")
        display_layout = QVBoxLayout()
        
        # Create display widgets for each parameter
        self.display_widgets = {}
        for key in self.parameters.keys():
            display = create_parameter_display(self.parameters, key)
            if display:
                self.display_widgets[key] = display
                display_layout.addWidget(display)
        
        display_group.setLayout(display_layout)
        layout.addWidget(display_group)
        
        # Buttons section
        button_layout = QHBoxLayout()
        
        # Edit dialog button
        edit_button = QPushButton("Edit All Parameters (Dialog)")
        edit_button.clicked.connect(self.edit_parameters)
        button_layout.addWidget(edit_button)
        
        # Refresh displays button
        refresh_button = QPushButton("Refresh Displays")
        refresh_button.clicked.connect(self.refresh_displays)
        button_layout.addWidget(refresh_button)
        
        # Show current values button
        values_button = QPushButton("Show Current Values")
        values_button.clicked.connect(self.show_current_values)
        button_layout.addWidget(values_button)
        
        layout.addLayout(button_layout)
        
        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: green; margin: 10px;")
        layout.addWidget(self.status_label)
        
        central_widget.setLayout(layout)
    
    def edit_parameters(self):
        """Open the parameter editing dialog."""
        if edit_parameters_dialog(self.parameters, self):
            self.status_label.setText("Parameters updated successfully!")
            self.status_label.setStyleSheet("color: green; margin: 10px;")
            self.refresh_displays()
        else:
            self.status_label.setText("Parameter editing cancelled.")
            self.status_label.setStyleSheet("color: orange; margin: 10px;")
    
    def refresh_displays(self):
        """Refresh all display widgets."""
        for display in self.display_widgets.values():
            display.update_display()
        self.status_label.setText("Displays refreshed!")
        self.status_label.setStyleSheet("color: blue; margin: 10px;")
    
    def show_current_values(self):
        """Show current parameter values in the status."""
        values = []
        for key, value in self.parameters.items():
            if hasattr(value, 'magnitude') and hasattr(value, 'units'):
                # Pint quantity
                values.append(f"{key}: {value.magnitude:.3f} {value.units}")
            else:
                # Regular value
                values.append(f"{key}: {value}")
        
        self.status_label.setText(" | ".join(values))
        self.status_label.setStyleSheet("color: purple; margin: 10px; font-size: 10px;")


def main():
    """Main function to run the demo."""
    app = QApplication(sys.argv)
    
    # Create and show the demo window
    demo = ParameterWidgetDemo()
    demo.show()
    
    print("Parameter Widget Demo started!")
    print("Features demonstrated:")
    print("- Unit-aware parameter input widgets")
    print("- Multi-unit display widgets")
    print("- Parameter editing dialog")
    print("- Real-time validation and unit conversion")
    print("- Range and pattern validation")
    
    # Run the application
    sys.exit(app.exec_())


if __name__ == "__main__":
    main() 