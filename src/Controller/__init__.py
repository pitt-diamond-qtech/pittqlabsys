"""
Controller module for hardware device management.

This module provides access to hardware devices and mock implementations
for cross-platform compatibility.
"""

import sys
from pathlib import Path
import numpy as np

# Import basic device classes that don't have platform dependencies
from .pulse_blaster import PulseBlaster
from .awg520 import AWG520Device
from .sg384 import SG384Generator
from .windfreak_synth_usbii import WindfreakSynthUSBII
from .example_device import ExampleDevice, Plant, PIController

# Import the base Device class
from src.core.device import Device
from src.core.parameter import Parameter

# Mock device classes for cross-platform compatibility
class MockNI6229(Device):
    """Mock NI6229 device that subclasses from Device."""
    
    _DEFAULT_SETTINGS = Parameter([
        Parameter('device', 'Dev1', ['Dev1'], 'Name of NI-DAQ device'),
        Parameter('sample_rate', 1000000, float, 'Sample rate in Hz'),
        Parameter('num_samples', 1000, int, 'Number of samples to acquire'),
        Parameter('voltage_range', [-10.0, 10.0], list, 'Voltage range for acquisition'),
        Parameter('analog_output', [
            Parameter('ao0', [
                Parameter('channel', 0, [0, 1, 2, 3], 'output channel'),
                Parameter('sample_rate', 1000.0, float, 'output sample rate (Hz)', units="Hz"),
                Parameter('min_voltage', -10.0, float, 'minimum output voltage (V)', units="V"),
                Parameter('max_voltage', 10.0, float, 'maximum output voltage (V)', units="V")
            ]),
            Parameter('ao1', [
                Parameter('channel', 1, [0, 1, 2, 3], 'output channel'),
                Parameter('sample_rate', 1000.0, float, 'output sample rate (Hz)', units="Hz"),
                Parameter('min_voltage', -10.0, float, 'minimum output voltage (V)', units="V"),
                Parameter('max_voltage', 10.0, float, 'maximum output voltage (V)', units="V")
            ]),
            Parameter('ao2', [
                Parameter('channel', 2, [0, 1, 2, 3], 'output channel'),
                Parameter('sample_rate', 1000.0, float, 'output sample rate (Hz)', units="Hz"),
                Parameter('min_voltage', -10.0, float, 'minimum output voltage (V)', units="V"),
                Parameter('max_voltage', 10.0, float, 'maximum output voltage (V)', units="V")
            ]),
            Parameter('ao3', [
                Parameter('channel', 3, [0, 1, 2, 3], 'output channel'),
                Parameter('sample_rate', 1000.0, float, 'output sample rate (Hz)', units="Hz"),
                Parameter('min_voltage', -10.0, float, 'minimum output voltage (V)', units="V"),
                Parameter('max_voltage', 10.0, float, 'maximum output voltage (V)', units="V")
            ])
        ]),
        Parameter('analog_input', [
            Parameter('ai0', [
                Parameter('channel', 0, list(range(0, 32)), 'input channel'),
                Parameter('sample_rate', 1000.0, float, 'input sample rate (Hz)', units="Hz"),
                Parameter('min_voltage', -10.0, float, 'minimum input voltage'),
                Parameter('max_voltage', 10.0, float, 'maximum input voltage')
            ]),
            Parameter('ai1', [
                Parameter('channel', 1, list(range(0, 32)), 'input channel'),
                Parameter('sample_rate', 1000.0, float, 'input sample rate', units="Hz"),
                Parameter('min_voltage', -10.0, float, 'minimum input voltage'),
                Parameter('max_voltage', 10.0, float, 'maximum input voltage')
            ])
        ])
    ])
    
    _PROBES = {
        'voltage': 'Current voltage reading',
        'counts': 'Current count reading',
        'frequency': 'Current frequency reading'
    }
    
    def __init__(self, settings=None):
        self._voltage = 0.0
        self._counts = 0
        self._frequency = 1000.0
        self._tasks = {} # Added for new methods
        super().__init__(settings=settings)
        print(f"Mock NI6229: Initialized")
    
    def update(self, settings):
        """Update device settings."""
        super().update(settings)
        # Only print for significant updates
        if len(settings) > 2:
            print(f"Mock NI6229: Updated settings")
    
    def read_probes(self, key):
        """Read probe values."""
        if key == 'voltage':
            return self._voltage + np.random.normal(0, 0.1)
        elif key == 'counts':
            return self._counts + np.random.poisson(100)
        elif key == 'frequency':
            return self._frequency + np.random.normal(0, 10)
        else:
            return 0.0
    
    @property
    def is_connected(self):
        return True
    
    def setup_AO(self, channels, data, clk_source=None):
        """Setup analog output task."""
        task_id = f"mock_ao_task_{len(self._tasks)}"
        self._tasks[task_id] = {
            'type': 'AO',
            'channels': channels,
            'data': data,
            'clk_source': clk_source
        }
        print(f"Mock NI6229: Setup AO {channels} with {len(data)} points")
        return task_id
    
    def setup_counter(self, channel, length, use_external_clock=False):
        """Setup counter task."""
        task_id = f"mock_ctr_task_{len(self._tasks)}"
        self._tasks[task_id] = {
            'type': 'counter',
            'channel': channel,
            'length': length,
            'use_external_clock': use_external_clock
        }
        print(f"Mock NI6229: Setup counter {channel} with length {length}")
        return task_id
    
    def run(self, task):
        """Run task."""
        print(f"Mock NI6229: Run task {task}")
    
    def stop(self, task):
        """Stop task."""
        print(f"Mock NI6229: Stop task {task}")
    
    def AO_waitToFinish(self):
        """Wait for AO task to finish."""
        print("Mock NI6229: AO wait to finish")
    
    def read(self, task):
        """Read data from task."""
        import numpy as np
        # Return mock data that looks like counter data
        data = np.cumsum(np.random.poisson(100, 1000))
        return data, None

class MockPCI6601(Device):
    """Mock PCI6601 device that subclasses from Device."""
    
    _DEFAULT_SETTINGS = Parameter([
        Parameter('device', 'Dev1', ['Dev1'], 'Name of NI-DAQ device'),
        Parameter('clock_rate', 1000000, float, 'Clock rate in Hz'),
        Parameter('num_channels', 8, int, 'Number of counter channels'),
        Parameter('digital_input', [
            Parameter('ctr0', [
                Parameter('channel', 0, [0, 1], 'counter channel'),
                Parameter('sample_rate', 1000000.0, float, 'counter sample rate (Hz)', units="Hz")
            ]),
            Parameter('ctr1', [
                Parameter('channel', 1, [0, 1], 'counter channel'),
                Parameter('sample_rate', 1000000.0, float, 'counter sample rate (Hz)', units="Hz")
            ])
        ])
    ])
    
    _PROBES = {
        'counts': 'Current count reading',
        'frequency': 'Current frequency reading'
    }
    
    def __init__(self, settings=None):
        self._counts = 0
        self._frequency = 1000.0
        self._tasks = {}  # Added for new methods
        super().__init__(settings=settings)
        print(f"Mock PCI6601: Initialized")
    
    def update(self, settings):
        """Update device settings."""
        super().update(settings)
        # Only print for significant updates
        if len(settings) > 2:
            print(f"Mock PCI6601: Updated settings")
    
    def read_probes(self, key):
        """Read probe values."""
        if key == 'counts':
            return self._counts + np.random.poisson(100)
        elif key == 'frequency':
            return self._frequency + np.random.normal(0, 10)
        else:
            return 0.0
    
    @property
    def is_connected(self):
        return True
    
    def setup_counter(self, channel, length, use_external_clock=False):
        """Setup counter task."""
        task_id = f"mock_ctr_task_{len(self._tasks)}"
        self._tasks[task_id] = {
            'type': 'counter',
            'channel': channel,
            'length': length,
            'use_external_clock': use_external_clock
        }
        print(f"Mock PCI6601: Setup counter {channel} with length {length}")
        return task_id
    
    def run(self, task):
        """Run task."""
        print(f"Mock PCI6601: Run task {task}")
    
    def stop(self, task):
        """Stop task."""
        print(f"Mock PCI6601: Stop task {task}")
    
    def read(self, task):
        """Read data from task."""
        import numpy as np
        # Return mock data that looks like counter data
        data = np.cumsum(np.random.poisson(100, 1000))
        return data, None

class MockMCLNanoDrive(Device):
    """Mock MCLNanoDrive device that subclasses from Device."""
    
    _DEFAULT_SETTINGS = Parameter([
        Parameter('serial', 2849, int, 'Serial number of the device'),
        Parameter('step_size', 1.0, float, 'Step size in microns'),
        Parameter('max_velocity', 1000.0, float, 'Maximum velocity in microns/s')
    ])
    
    _PROBES = {
        'x_pos': 'Current X position',
        'y_pos': 'Current Y position', 
        'z_pos': 'Current Z position'
    }
    
    def __init__(self, settings=None):
        self.x_pos = 0.0
        self.y_pos = 0.0
        self.z_pos = 0.0
        self.handle = 1
        self.DLL = None
        self.empty_waveform = [0.0]
        self.num_datapoints = 100
        super().__init__(settings=settings)
        print(f"Mock MCLNanoDrive: Initialized")
    
    def update(self, settings):
        """Update device settings."""
        super().update(settings)
        # Update position if provided - use object.__setattr__ to avoid recursion
        if 'x_pos' in settings:
            object.__setattr__(self, 'x_pos', settings['x_pos'])
        if 'y_pos' in settings:
            object.__setattr__(self, 'y_pos', settings['y_pos'])
        if 'z_pos' in settings:
            object.__setattr__(self, 'z_pos', settings['z_pos'])
        # Only print for position updates
        if any(key in settings for key in ['x_pos', 'y_pos', 'z_pos']):
            print(f"Mock MCLNanoDrive: Position updated")
    
    def read_probes(self, key):
        """Read probe values."""
        if key == 'x_pos':
            return self.x_pos
        elif key == 'y_pos':
            return self.y_pos
        elif key == 'z_pos':
            return self.z_pos
        else:
            return 0.0
    
    def move_to(self, x=None, y=None, z=None):
        """Move to specified position."""
        if x is not None:
            self.x_pos = x
        if y is not None:
            self.y_pos = y
        if z is not None:
            self.z_pos = z
        # Only print for significant moves
        if any(val is not None for val in [x, y, z]):
            print(f"Mock MCLNanoDrive: Moved to new position")
    
    def get_position(self):
        """Get current position."""
        return {'x': self.x_pos, 'y': self.y_pos, 'z': self.z_pos}
    
    def load_waveform(self, waveform_data):
        """Load waveform data."""
        # Only print for large waveforms
        if len(waveform_data) > 10:
            print(f"Mock MCLNanoDrive: Loaded waveform")
    
    def start_waveform(self):
        """Start waveform execution."""
        print("Mock MCLNanoDrive: Started waveform")
    
    def stop_waveform(self):
        """Stop waveform execution."""
        print("Mock MCLNanoDrive: Stopped waveform")
    
    def wait_for_completion(self):
        """Wait for waveform completion."""
        # No print needed for this
    
    def setup(self, settings, axis=None):
        """Setup device for operation."""
        if 'num_datapoints' in settings:
            self.num_datapoints = settings['num_datapoints']
        # Only print for significant setup changes
        if 'num_datapoints' in settings and settings['num_datapoints'] > 50:
            print(f"Mock MCLNanoDrive: Setup for {axis} axis")
    
    def waveform_acquisition(self, axis=None, num_datapoints=None):
        """Mock waveform acquisition."""
        n = num_datapoints if (num_datapoints and num_datapoints > 0) else self.num_datapoints
        
        # Return realistic position data instead of random counts
        if axis == 'y':
            # Return y positions from current y_pos to y_pos + n*step
            step = 1.0  # 1 micron step
            positions = np.linspace(self.y_pos, self.y_pos + n * step, n)
        elif axis == 'x':
            # Return x positions from current x_pos to x_pos + n*step
            step = 1.0  # 1 micron step
            positions = np.linspace(self.x_pos, self.x_pos + n * step, n)
        else:
            # Default to z positions
            step = 1.0
            positions = np.linspace(self.z_pos, self.z_pos + n * step, n)
        
        # Only print for large acquisitions
        if n > 50:
            print(f"Mock MCLNanoDrive: Acquired {n} points for {axis} axis")
        return positions
    
    def clock_functions(self, clock, mode=None, polarity=None, binding=None, reset=False, pulse=False):
        """Mock clock functions."""
        print(f"Mock MCLNanoDrive: Clock functions - {clock}, mode={mode}, polarity={polarity}")
    
    def close(self):
        """Close device connection."""
        print("Mock MCLNanoDrive: Closed")
    
    def __del__(self):
        """Cleanup on deletion."""
        pass
    
    @property
    def is_connected(self):
        return True

class MockAdwinGoldDevice(Device):
    """Mock AdwinGoldDevice that subclasses from Device."""
    
    _DEFAULT_SETTINGS = Parameter([
        Parameter('process_1', {'running': False}, dict, 'Process 1 settings'),
        Parameter('process_2', {'running': False}, dict, 'Process 2 settings'),
        Parameter('array_size', 1000, int, 'Default array size')
    ])
    
    _PROBES = {
        'int_array': 'Integer array data',
        'float_array': 'Float array data'
    }
    
    def __init__(self, settings=None):
        self.processes = {}
        self.arrays = {}
        super().__init__(settings=settings)
        print("Mock AdwinGoldDevice: Initialized")
    
    def update(self, settings):
        """Update device settings."""
        super().update(settings)
        # Only print for process updates
        if any('process' in key for key in settings.keys()):
            print(f"Mock AdwinGoldDevice: Process settings updated")
    
    def read_probes(self, key, id=None, length=None):
        """Read probe data."""
        n = length if (length and length > 0) else 100
        # Return mock count data
        data = np.random.poisson(100, n)
        # Only print for large reads
        if n > 50:
            print(f"Mock AdwinGoldDevice: Read {n} points")
        return data
    
    def load_process(self, process_name, binary_file):
        """Load process into device."""
        self.processes[process_name] = {'loaded': True, 'running': False}
        print(f"Mock AdwinGoldDevice: Loaded process '{process_name}'")
    
    def start_process(self, process_name):
        """Start process execution."""
        if process_name in self.processes:
            self.processes[process_name]['running'] = True
        print(f"Mock AdwinGoldDevice: Started process '{process_name}'")
    
    def stop_process(self, process_name):
        """Stop process execution."""
        if process_name in self.processes:
            self.processes[process_name]['running'] = False
        print(f"Mock AdwinGoldDevice: Stopped process '{process_name}'")
    
    def clear_process(self, process_name):
        """Clear process from device."""
        if process_name in self.processes:
            del self.processes[process_name]
        print(f"Mock AdwinGoldDevice: Cleared process '{process_name}'")
    
    def set_parameter(self, param_num, value):
        """Set parameter value."""
        # No print needed for this
    
    def get_parameter(self, param_num):
        """Get parameter value."""
        return np.random.random()
    
    def read_array(self, array_num, length):
        """Read data array."""
        n = length if (length and length > 0) else 100
        data = np.random.poisson(100, n)
        # Only print for large arrays
        if n > 50:
            print(f"Mock AdwinGoldDevice: Read array {array_num}")
        return data
    
    def reboot(self):
        """Reboot device."""
        print("Mock AdwinGoldDevice: Rebooted")
    
    def close(self):
        """Close device connection."""
        print("Mock AdwinGoldDevice: Closed")
    
    @property
    def is_connected(self):
        return True

# Platform-specific device assignments
if sys.platform.startswith('win'):
    try:
        from .ni_daq import PXI6733, NI6281, PCI6229, PCI6601, NIDAQ
    except ImportError:
        PXI6733 = MockNI6229
        NI6281 = MockNI6229
        PCI6229 = MockNI6229
        PCI6601 = MockPCI6601
        NIDAQ = MockNI6229
    
    try:
        from .nanodrive import MCLNanoDrive
        from .adwin_gold import AdwinGoldDevice
    except ImportError:
        MCLNanoDrive = MockMCLNanoDrive
        AdwinGoldDevice = MockAdwinGoldDevice
else:
    PXI6733 = MockNI6229
    NI6281 = MockNI6229
    PCI6229 = MockNI6229
    PCI6601 = MockPCI6601
    NIDAQ = MockNI6229
    MCLNanoDrive = MockMCLNanoDrive
    AdwinGoldDevice = MockAdwinGoldDevice

_DEVICE_REGISTRY = {
    "awg520": AWG520Device, 
    "sg384": SG384Generator,
    "windfreak_synth_usbii": WindfreakSynthUSBII,
    "nanodrive": MCLNanoDrive,
    "adwin": AdwinGoldDevice,
    "pulseblaster": PulseBlaster,
    "example_device": ExampleDevice,
    "plant": Plant,
    "pi_controller": PIController,
}

_DEVICE_REGISTRY.update({
    "ni_daq": NIDAQ,
    "pxi6733": PXI6733,
    "ni6281": NI6281,
    "pci6229": PCI6229,
    "pci6601": PCI6601,
})

def create_device(kind: str, **kwargs):
    cls = _DEVICE_REGISTRY.get(kind.lower())
    if cls is None:
        raise ValueError(f"Unknown device type: {kind}")
    return cls(**kwargs)

__all__ = [
    'PXI6733', 'NI6281', 'PCI6229', 'PCI6601', 'NIDAQ',
    'MCLNanoDrive', 'AdwinGoldDevice',
    'AWG520Device', 'SG384Generator', 'WindfreakSynthUSBII',
    'PulseBlaster', 'ExampleDevice', 'Plant', 'PIController',
    'create_device',
    'MockNI6229', 'MockPCI6601', 'MockMCLNanoDrive', 'MockAdwinGoldDevice'
]