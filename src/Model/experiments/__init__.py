# Created by Gurudev Dutt <gdutt@pitt.edu> on 2023-08-03
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
import sys

from src.Model.experiments.example_experiment import ExampleExperimentWrapper,ExampleExperiment,MinimalExperiment

# Only import NI-DAQ dependent modules on Windows
if sys.platform.startswith('win'):
    from src.Model.experiments.daq_read_counter import Pxi6733ReadCounter
    from src.Model.experiments.galvo_scan import GalvoScan
    from .galvo_scan_generic import GalvoScanGeneric
    from .select_points import SelectPoints
        # Legacy confocal experiments (deprecated - use new focused modules instead)
    from .confocal import ConfocalScan_Fast, ConfocalScan_Slow, Confocal_Point

    # New focused confocal experiments with hardware-specific naming
    from .nanodrive_adwin_confocal_scan_fast import NanodriveAdwinConfocalScanFast
    from .nanodrive_adwin_confocal_scan_slow import NanodriveAdwinConfocalScanSlow
    from .nanodrive_adwin_confocal_point import NanodriveAdwinConfocalPoint
else:
    # On non-Windows platforms, create placeholder imports to avoid import errors
    Pxi6733ReadCounter = None
    GalvoScan = None
    GalvoScanGeneric = None
    SelectPoints = None
    ConfocalScan_Fast = None
    ConfocalScan_Slow = None
    Confocal_Point = None
    
    # New focused confocal experiments (not available on non-Windows)
    NanodriveAdwinConfocalScanFast = None
    NanodriveAdwinConfocalScanSlow = None
    NanodriveAdwinConfocalPoint = None

from .deprecated.odmr_experiment import ODMRExperiment, ODMRRabiExperiment
from .deprecated.odmr_enhanced import EnhancedODMRExperiment
from .deprecated.odmr_simple_adwin import SimpleODMRExperiment

# New focused ODMR experiments with SG384 integration
from .odmr_stepped import ODMRSteppedExperiment
from .odmr_sweep_continuous import ODMRSweepContinuousExperiment
from .odmr_fm_modulation import ODMRFMModulationExperiment

# ODMR Pulsed experiment with AWG520 integration
from .odmr_pulsed import ODMRPulsedExperiment

from src.core.experiment_iterator import ExperimentIterator