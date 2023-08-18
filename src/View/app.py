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
from PyQt5 import QtCore, QtWidgets, QtGui,uic
from src.core.helper_functions import get_project_root
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.animation import FuncAnimation
from pathlib import Path
import sys,numpy,datetime,os
"""
if I import the Ui_Pulseshaper class from the python file, then I will have to inherit from it in the main appGUI class from appgui, load Ui_Pulseshaper. Instead I use the uic
module to directly load GUI. Then I dont have to inherit from it and can assign a ui variable inside the appGUI class. Either method is fine.
"""

thisdir = get_project_root()
qtdesignerfile = thisdir / 'View/ui_files/main_window.ui'  # this is the .ui file created in QtCreator


Ui_main, junk = uic.loadUiType(qtdesignerfile)

def launch_gui(filepath=None):
    """ this is the main class for the GUI.

       """

    try:
        app = Ui_main(filepath)
        app.setupUI()
        app.show()
        app.raise_()
        sys.exit(app.exec_())
    except ValueError as e:
        if not e.message in ['No config file was provided. abort loading gui...']:
            raise e


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Launch AQuISS GUI')
    parser.add_argument("filepath", help="filepath to gui config file", nargs='?', default=None, action="store")
    # print(parser)
    args = parser.parse_args()
    if args.filepath is None:
        print('launch new')
        launch_gui()
    else:
        print('launch gui with ', args.filepath)
        launch_gui(args.filepath)