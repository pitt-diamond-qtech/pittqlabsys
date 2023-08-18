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
from src.View.windows_and_widgets.main_window import MainWindow
from PyQt5 import QtWidgets
import sys

def launch_gui(filepath=None):
    """ this is the main class for the GUI.

       """

    app = QtWidgets.QApplication(sys.argv)

    try:
        ex = MainWindow(filepath)
        ex.show()
        ex.raise_()
        sys.exit(app.exec_())

    except ValueError as e:
        if not e in ['No config file was provided. abort loading gui...', '']:
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