# AQuISS
This repo is the python code for AQuISS device

PyQt Graph Version:

This repository uses pyqt graph instead of matplot lib. The following files have been changed:

  widgets.py - Added PyQtgraphWidget for use in GUI
  
  main_window.py - Swapped matplotwidget for pyqt one
  
  experiment.py - Changed initilization of figures to be comparible with pyqt widget
  
  confocal.py - Incorporated pyqt for live plotting counts and a plotting a scan as a 2D image.
  
Note not all matplotlib funtionality has been removed. The GUI still runs but some sepecific actions might casue errors and crashing.
