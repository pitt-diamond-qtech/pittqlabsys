# Created by Gurudev Dutt <gdutt@pitt.edu> on 7/28/25
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
import matplotlib
matplotlib.use("Agg")  # non-interactive, no window pops up
import pytest

# Pytest configuration for hardware tests
def pytest_configure(config):
    """Configure pytest to handle hardware tests."""
    config.addinivalue_line(
        "markers", "hardware: marks tests as requiring hardware (deselect with '-m \"not hardware\"')"
    )

def pytest_collection_modifyitems(config, items):
    """Automatically skip hardware tests if no hardware is available."""
    # You can set this environment variable to force hardware tests
    import os
    if not os.getenv('RUN_HARDWARE_TESTS'):
        skip_hardware = pytest.mark.skip(reason="Hardware tests disabled by default. Set RUN_HARDWARE_TESTS=1 to enable.")
        for item in items:
            if "hardware" in item.keywords:
                item.add_marker(skip_hardware)