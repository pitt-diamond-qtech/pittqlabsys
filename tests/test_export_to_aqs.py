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
from pathlib import Path
from src.core.helper_functions import get_project_root

@pytest.fixture
def get_dev_dir() -> Path:
    proj_dir = get_project_root()
    dir_path = proj_dir/"Controller"
    return str(dir_path.resolve())


@pytest.mark.parametrize("cls",["Device"])
def test_find_exportable_devs(capsys,cls,get_dev_dir):
    folder = get_dev_dir
    dev_dict = find_exportable_in_python_files(folder,class_type=cls)
    assert dev_dict != {}
    with capsys.disabled():
        for key,val in dev_dict.items():
            print("######")
            print(key)
            for k,v in val.items():
                print(f"{k:12}:{v:25}")


