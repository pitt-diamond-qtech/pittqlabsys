#!/usr/bin/env python3
"""
Simple example demonstrating Parameter dialog functionality.

This script shows how to use the parameter editing dialog in a minimal GUI.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel, QTextEdit
    from PyQt5.QtCore import Qt
    PYQT5_AVAILABLE = True
except ImportError:
    print("PyQt5 not available. This example requires PyQt5 to be installed.")
    sys.exit(1)

from src.core.parameter import Parameter
from src import ur
from src.View.windows_and_widgets.parameter_widget import edit_parameters_dialog


class SimpleParameterDemo(QMainWindow):
    """Simple demo showing parameter dialog functionality."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simple Parameter Dialog Demo")
        self.setGeometry(100, 100, 600, 400)
        
        # Create example parameters
        self.parameters = Parameter([
            Parameter('frequency', 2.85e9 * ur.Hz, float, 'Microwave Frequency'),
            Parameter('power', -45.0, float, 'Microwave Power', units='dBm'),
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
        title = QLabel("Simple Parameter Dialog Demo")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Description
        desc = QLabel("Click the button below to edit parameters in a dialog.")
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)
        
        # Edit button
        edit_button = QPushButton("Edit Parameters")
        edit_button.setStyleSheet("font-size: 14px; padding: 10px; margin: 20px;")
        edit_button.clicked.connect(self.edit_parameters)
        layout.addWidget(edit_button)
        
        # Current values display
        self.values_display = QTextEdit()
        self.values_display.setReadOnly(True)
        self.values_display.setMaximumHeight(200)
        layout.addWidget(QLabel("Current Parameter Values:"))
        layout.addWidget(self.values_display)
        
        # Status label
        self.status_label = QLabel("Ready to edit parameters")
        self.status_label.setStyleSheet("color: green; margin: 10px;")
        layout.addWidget(self.status_label)
        
        central_widget.setLayout(layout)
        
        # Show initial values
        self.update_values_display()
    
    def edit_parameters(self):
        """Open the parameter editing dialog."""
        self.status_label.setText("Opening parameter dialog...")
        self.status_label.setStyleSheet("color: blue; margin: 10px;")
        
        if edit_parameters_dialog(self.parameters, self):
            self.status_label.setText("Parameters updated successfully!")
            self.status_label.setStyleSheet("color: green; margin: 10px;")
            self.update_values_display()
        else:
            self.status_label.setText("Parameter editing cancelled.")
            self.status_label.setStyleSheet("color: orange; margin: 10px;")
    
    def update_values_display(self):
        """Update the values display."""
        text = "Current Parameter Values:\n\n"
        for key, value in self.parameters.items():
            if hasattr(value, 'magnitude') and hasattr(value, 'units'):
                # Pint quantity
                text += f"{key}: {value.magnitude:.3f} {value.units}\n"
            else:
                # Regular value
                text += f"{key}: {value}\n"
        
        self.values_display.setText(text)


def main():
    """Main function to run the simple demo."""
    app = QApplication(sys.argv)
    
    # Create and show the demo window
    demo = SimpleParameterDemo()
    demo.show()
    
    print("Simple Parameter Dialog Demo started!")
    print("Click the 'Edit Parameters' button to see the dialog in action.")
    
    # Run the application
    sys.exit(app.exec_())


if __name__ == "__main__":
    main() 