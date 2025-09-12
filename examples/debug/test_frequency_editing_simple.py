#!/usr/bin/env python3
"""
Simple test to isolate frequency editing issue.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel
    from PyQt5.QtCore import Qt
    PYQT5_AVAILABLE = True
except ImportError:
    print("PyQt5 not available. This test requires PyQt5 to be installed.")
    sys.exit(1)

from src.core.parameter import Parameter
from src import ur
from src.View.windows_and_widgets.parameter_widget import create_parameter_widget


class SimpleFrequencyTest(QMainWindow):
    """Simple test window for frequency editing."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simple Frequency Test")
        self.setGeometry(100, 100, 400, 300)
        
        # Create a simple parameter with frequency
        self.parameter = Parameter('frequency', 2.85e9 * ur.Hz, float, 'Test Frequency')
        
        print(f"Initial parameter: {self.parameter['frequency']} (type: {type(self.parameter['frequency'])})")
        
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("Frequency Editing Test")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Description
        desc = QLabel("Try editing the frequency value below:")
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)
        
        # Create the parameter widget
        self.freq_widget = create_parameter_widget(self.parameter, 'frequency', self)
        if self.freq_widget:
            layout.addWidget(self.freq_widget)
            print("✅ Parameter widget created successfully")
        else:
            print("❌ Failed to create parameter widget")
        
        # Status label
        self.status_label = QLabel("Ready to test frequency editing")
        self.status_label.setStyleSheet("color: green; margin: 10px;")
        layout.addWidget(self.status_label)
        
        # Test button
        test_button = QPushButton("Check Current Value")
        test_button.clicked.connect(self.check_value)
        layout.addWidget(test_button)
        
        central_widget.setLayout(layout)
    
    def check_value(self):
        """Check the current parameter value."""
        current_value = self.parameter['frequency']
        print(f"Current value: {current_value} (type: {type(current_value)})")
        
        if hasattr(current_value, 'magnitude') and hasattr(current_value, 'units'):
            self.status_label.setText(f"✅ Pint quantity: {current_value.magnitude:.6g} {current_value.units}")
            self.status_label.setStyleSheet("color: green; margin: 10px;")
        else:
            self.status_label.setText(f"❌ Not a pint quantity: {current_value} (type: {type(current_value)})")
            self.status_label.setStyleSheet("color: red; margin: 10px;")


def main():
    """Main function to run the test."""
    app = QApplication(sys.argv)
    
    # Create and show the test window
    test_window = SimpleFrequencyTest()
    test_window.show()
    
    print("Simple Frequency Test started!")
    print("Try editing the frequency value and click 'Check Current Value' to see what happens.")
    
    # Run the application
    sys.exit(app.exec_())


if __name__ == "__main__":
    main() 