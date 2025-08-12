#!/usr/bin/env python3
"""
Simple launcher script for the AQuISS GUI.
This script sets up the Python path correctly and launches the GUI.
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Now import and run the app
from src.app import launch_gui

if __name__ == "__main__":
    launch_gui() 