#!/usr/bin/env python3
"""
Run the visual feedback test.
This script sets up the Python path and runs the test.
"""

import sys
import os

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# Import and run the test
from examples.debug.test_visual_feedback import main

if __name__ == "__main__":
    main()
