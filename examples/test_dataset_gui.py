#!/usr/bin/env python3
"""
Test script for GUI dataset functionality.

This script creates a minimal GUI test to verify that the dataset
storage and display functionality works correctly.

Usage:
    python test_dataset_gui.py
"""

import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QTreeWidget, QTreeWidgetItem, QLabel, QSplitter
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from test_gui_with_mock_data import create_mock_experiments
from src.tools.generate_mock_data import add_mock_data_to_experiment


class DatasetTestWindow(QMainWindow):
    """Simple test window for dataset functionality."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AQuISS Dataset Test")
        self.setGeometry(100, 100, 800, 600)
        
        # Data storage
        self.experiments = {}
        self.data_sets = {}
        
        # Create UI
        self.setup_ui()
        
        # Load mock experiments
        self.load_mock_experiments()
    
    def setup_ui(self):
        """Setup the user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QHBoxLayout(central_widget)
        
        # Splitter for left and right panels
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left panel - Experiments
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        left_layout.addWidget(QLabel("Experiments"))
        
        # Experiments tree
        self.tree_experiments = QTreeWidget()
        self.tree_experiments.setHeaderLabels(['Name', 'Type', 'Status'])
        left_layout.addWidget(self.tree_experiments)
        
        # Send to dataset button
        self.btn_send_to_dataset = QPushButton("Send to Datasets")
        self.btn_send_to_dataset.clicked.connect(self.send_to_dataset)
        left_layout.addWidget(self.btn_send_to_dataset)
        
        # Right panel - Datasets
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        right_layout.addWidget(QLabel("Datasets"))
        
        # Datasets tree
        self.tree_datasets = QTreeWidget()
        self.tree_datasets.setHeaderLabels(['Time', 'Name', 'Type'])
        right_layout.addWidget(self.tree_datasets)
        
        # Add panels to splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        
        # Set splitter proportions
        splitter.setSizes([400, 400])
    
    def load_mock_experiments(self):
        """Load mock experiments into the experiments tree."""
        print("Loading mock experiments...")
        
        # Create mock experiments
        self.experiments = create_mock_experiments()
        
        # Populate experiments tree
        self.tree_experiments.clear()
        for name, experiment in self.experiments.items():
            item = QTreeWidgetItem([name, experiment.name, "Ready"])
            item.experiment = experiment  # Store reference to experiment
            self.tree_experiments.addTopLevelItem(item)
        
        print(f"Loaded {len(self.experiments)} experiments")
    
    def send_to_dataset(self):
        """Send selected experiment to datasets."""
        current_item = self.tree_experiments.currentItem()
        
        if current_item is None:
            print("No experiment selected")
            return
        
        # Get experiment from item
        experiment = getattr(current_item, 'experiment', None)
        if experiment is None:
            print("Selected item does not contain an experiment")
            return
        
        try:
            # Create time tag
            time_tag = experiment.start_time.strftime('%y%m%d-%H_%M_%S')
            print(f"Storing experiment {experiment.name} with time tag {time_tag}")
            
            # Store in datasets (simulate duplicate)
            self.data_sets[time_tag] = experiment
            
            # Update datasets tree
            self.update_datasets_tree()
            
            print(f"Experiment stored successfully. Total datasets: {len(self.data_sets)}")
            
        except Exception as e:
            print(f"Error storing experiment: {e}")
    
    def update_datasets_tree(self):
        """Update the datasets tree display."""
        self.tree_datasets.clear()
        
        for time_tag, experiment in self.data_sets.items():
            # Get experiment name/tag safely
            if hasattr(experiment, 'settings') and 'tag' in experiment.settings:
                name = experiment.settings['tag']
            else:
                name = getattr(experiment, 'name', 'Unknown')
            
            type_name = getattr(experiment, 'name', 'Unknown')
            
            item = QTreeWidgetItem([time_tag, name, type_name])
            self.tree_datasets.addTopLevelItem(item)
        
        print(f"Updated datasets tree with {len(self.data_sets)} datasets")


def main():
    """Main function."""
    app = QApplication(sys.argv)
    
    # Set application font
    font = QFont("Arial", 10)
    app.setFont(font)
    
    # Create and show window
    window = DatasetTestWindow()
    window.show()
    
    print("Dataset test window opened")
    print("Instructions:")
    print("1. Select an experiment from the left panel")
    print("2. Click 'Send to Datasets' button")
    print("3. Check if the experiment appears in the right panel")
    
    # Run the application
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
