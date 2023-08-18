# Created by Gurudev Dutt <gdutt@pitt.edu> on 2023-08-18
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

from src.tools.export_default import python_file_to_aqs,find_devices_in_python_files,find_experiments_in_python_files,find_exportable_in_python_files
import pytest

@pytest.mark.parametrize("folder,cls",[("C:\\Users\\l00055843\\PycharmProjects\\AQuISS\\src\\Controller","Device")])
def test_find_exportable_devs(capsys,folder,cls):
    dev_dict = find_exportable_in_python_files(folder,class_type=cls)
    with capsys.disabled():
        for key,val in dev_dict.items():
            print("{:s}:{:s}".format(key,val))

