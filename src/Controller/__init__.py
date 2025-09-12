"""
Controller module for hardware device management.

This module provides access to hardware devices and mock implementations
for cross-platform compatibility.

Arduino firmware files (.ino) are located in the arduino/ subdirectory.
See src/Controller/arduino/ for firmware used by hardware devices.
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

# Import MicrowaveGeneratorBase for mock SG384Generator
try:
    from .mw_generator_base import MicrowaveGeneratorBase
except ImportError:
    # Fallback if the base class is not available
    MicrowaveGeneratorBase = Device

# Mock device classes for cross-platform compatibility
class MockSG384Generator(Device):
    """Mock SG384Generator that subclasses directly from Device to avoid validation issues."""
    
    _DEFAULT_SETTINGS = Parameter([
        Parameter('connection_type', 'LAN', ['LAN','GPIB','RS232'], 'Transport type'),
        Parameter('ip_address', '192.168.2.217', str, 'IP for LAN'),
        Parameter('port', 5025, int, 'Port for LAN'),
        Parameter('visa_resource', '', str, 'PyVISA resource string'),
        Parameter('baud_rate', 115200, int, 'Baud for RS232'),
        Parameter('frequency', 2.87e9, float, 'Frequency in Hz'),  # No validation constraints
        Parameter('power', -10.0, float, 'Power in dBm'),  # No validation constraints
        Parameter('phase', 0.0, float, 'Phase in degrees'),  # No validation constraints
        Parameter('amplitude', -10.0, float, 'Amplitude in dBm'),  # No validation constraints
        Parameter('enable_output', False, bool, 'Enable output'),
        Parameter('enable_modulation', False, bool, 'Enable modulation'),
        Parameter('modulation_type', 'FM', ['AM','FM','PM','Sweep'], 'Modulation type'),
        Parameter('modulation_function', 'Sine', ['Sine','Ramp','Triangle','Square','Noise','External'], 'Modulation function'),
        Parameter('modulation_depth', 1e6, float, 'Deviation in Hz'),
        Parameter('dev_width', 1e6, float, 'Deviation width in Hz'),
        Parameter('mod_rate', 1e7, float, 'Modulation rate in Hz'),
        Parameter('sweep_function', 'Triangle', ['Sine','Ramp','Triangle','Square','Noise','External'], 'Sweep function'),
        Parameter('sweep_rate', 1.0, float, 'Sweep rate in Hz'),
        Parameter('sweep_deviation', 1e6, float, 'Sweep deviation in Hz'),
        Parameter('sweep_center_frequency', 2.87e9, float, 'Sweep center frequency in Hz'),
        Parameter('sweep_max_frequency', 4.1e9, float, 'Sweep maximum frequency in Hz'),
        Parameter('sweep_min_frequency', 1.9e9, float, 'Sweep minimum frequency in Hz'),
    ])
    
    _PROBES = {
        'frequency': 'Current frequency setting',
        'power': 'Current power setting',
        'phase': 'Current phase setting',
        'amplitude': 'Current amplitude setting'
    }
    
    def __init__(self, name=None, settings=None):
        # Initialize with default settings for mock operation
        if settings is None:
            settings = {
                'connection_type': 'LAN',
                'ip_address': '192.168.2.217',
                'port': 5025,
                'frequency': 2.87e9,
                'power': -10.0,
                'phase': 0.0,
                'amplitude': -10.0
            }
        
        # Set up mock attributes
        self._inst = None
        self._addr = (settings.get('ip_address', '192.168.2.217'), settings.get('port', 5025))
        self._sock = None
        
        super().__init__(settings=settings)
        print(f"Mock SG384Generator: Initialized")
    
    def _init_transport(self):
        """Mock transport initialization - no real connection needed."""
        # Mock transport setup
        self._addr = (self.settings.get('ip_address', '192.168.2.217'), self.settings.get('port', 5025))
        self._inst = None
        print(f"Mock SG384Generator: Transport initialized for {self._addr}")
    
    def _send(self, cmd: str):
        """Mock send command."""
        print(f"Mock SG384Generator: Send command '{cmd}'")
    
    def _query(self, cmd: str) -> str:
        """Mock query command."""
        print(f"Mock SG384Generator: Query command '{cmd}'")
        # Return mock responses based on the command
        if 'FREQ?' in cmd:
            return f"{self.settings.get('frequency', 2.87e9)}"
        elif 'AMPR?' in cmd:
            return f"{self.settings.get('power', -10.0)}"
        elif 'PHAS?' in cmd:
            return f"{self.settings.get('phase', 0.0)}"
        else:
            return "0"
    
    def set_frequency(self, freq_hz: float):
        """Set frequency."""
        self.settings['frequency'] = freq_hz
        print(f"Mock SG384Generator: Set frequency to {freq_hz/1e9:.3f} GHz")
    
    def set_power(self, power_dbm: float):
        """Set power."""
        self.settings['power'] = power_dbm
        print(f"Mock SG384Generator: Set power to {power_dbm} dBm")
    
    def set_power_dbm(self, power_dbm: float):
        """Set power in dBm."""
        self.settings['power'] = power_dbm
        print(f"Mock SG384Generator: Set power to {power_dbm} dBm")
    
    def set_phase(self, phase_deg: float):
        """Set phase."""
        self.settings['phase'] = phase_deg
        print(f"Mock SG384Generator: Set phase to {phase_deg} degrees")
    
    def enable_modulation(self):
        """Enable modulation."""
        print("Mock SG384Generator: Modulation enabled")
    
    def disable_modulation(self):
        """Disable modulation."""
        print("Mock SG384Generator: Modulation disabled")
    
    def set_modulation_type(self, mtype: str):
        """Set modulation type."""
        print(f"Mock SG384Generator: Set modulation type to {mtype}")
    
    def set_modulation_depth(self, depth_hz: float):
        """Set modulation depth."""
        print(f"Mock SG384Generator: Set modulation depth to {depth_hz} Hz")
    
    def output_on(self):
        """Turn output on."""
        print("Mock SG384Generator: Output enabled")
    
    def output_off(self):
        """Turn output off."""
        print("Mock SG384Generator: Output disabled")
    
    def update(self, settings: dict):
        """Update device settings."""
        # Convert numpy types to Python types to avoid validation issues
        converted_settings = {}
        for key, value in settings.items():
            if hasattr(value, 'item'):  # numpy scalar
                converted_settings[key] = value.item()
            else:
                converted_settings[key] = value
        
        super().update(converted_settings)
        print(f"Mock SG384Generator: Updated settings")
    
    def read_probes(self, key):
        """Read probe values."""
        if key == 'frequency':
            return self.settings.get('frequency', 2.87e9)
        elif key == 'power':
            return self.settings.get('power', -10.0)
        elif key == 'phase':
            return self.settings.get('phase', 0.0)
        elif key == 'amplitude':
            return self.settings.get('amplitude', -10.0)
        else:
            return 0.0
    
    @property
    def is_connected(self):
        return True
    
    def close(self):
        """Close connection."""
        print("Mock SG384Generator: Closed")

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
    
    def get_int_var(self, param_num):
        """Get integer variable value."""
        # Return mock count data for parameter 1 (counts)
        if param_num == 1:
            return np.random.poisson(100)
        else:
            return np.random.randint(0, 1000)
    
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


class MockMUXControlDevice(Device):
    """Mock MUX Control Device for testing."""
    
    _DEFAULT_SETTINGS = Parameter([
        Parameter('port', 'COM3', str, 'Serial port for Arduino connection'),
        Parameter('baudrate', 9600, int, 'Serial baudrate'),
        Parameter('timeout', 5000, int, 'Serial timeout in milliseconds'),
        Parameter('auto_connect', True, bool, 'Automatically connect on initialization'),
    ])
    
    _PROBES = {
        'status': 'Current MUX selection status',
        'port': 'Current serial port',
        'connected': 'Connection status to Arduino',
    }
    
    def __init__(self, name=None, settings=None):
        super().__init__(name=name, settings=settings)
        self._current_selection = None
        self._is_connected = True
        print(f"Mock MUX Control Device: Initialized on {self.settings.get('port', 'COM3')}")
    
    def connect(self):
        """Mock connection."""
        self._is_connected = True
        print(f"Mock MUX Control Device: Connected to {self.settings.get('port', 'COM3')}")
        return True
    
    def disconnect(self):
        """Mock disconnection."""
        self._is_connected = False
        self._current_selection = None
        print("Mock MUX Control Device: Disconnected")
    
    def select_trigger(self, selector):
        """Mock trigger selection."""
        if selector in ['confocal', 'odmr', 'pulsed']:
            self._current_selection = selector
            print(f"Mock MUX Control Device: Selected {selector} trigger")
            return True
        else:
            print(f"Mock MUX Control Device: Invalid selector '{selector}'")
            return False
    
    def get_current_selection(self):
        """Get current selection."""
        return self._current_selection
    
    def get_hardware_mapping(self):
        """Get hardware mapping information."""
        return {
            'multiplexer': '74HC4051 8-Channel',
            'arduino_pins': {
                'S0': 2,  # Select line 0
                'S1': 3,  # Select line 1  
                'S2': 4,  # Select line 2
                'Z': 5    # Common I/O line
            },
            'channel_mapping': {
                'confocal': {
                    'command': '1',
                    'channel': 'Y0',
                    'pins': {'S0': 0, 'S1': 0, 'S2': 0}
                },
                        'odmr': {
            'command': '2', 
            'channel': 'Y1',
            'pins': {'S0': 1, 'S1': 0, 'S2': 0}
        },
                'pulsed': {
                    'command': '3',
                    'channel': 'Y2', 
                    'pins': {'S0': 0, 'S1': 1, 'S2': 0}
                }
            },
            'baudrate': self.settings.get('baudrate', 9600),
            'port': self.settings.get('port', 'COM3')
        }
    
    def get_arduino_info(self):
        """Get Arduino firmware information."""
        return {
            'firmware': {
                'name': 'MUX_control',
                'author': 'Vincent Musso, Duttlab',
                'date': 'March 25, 2019',
                'modified': 'December 12, 2019 by Gurudev',
                'description': '74HC4051 8-Channel Multiplexer Controller'
            },
            'hardware': {
                'multiplexer': '74HC4051 8-Channel',
                'arduino_pins': {
                    'S0': 2,  # Select line 0
                    'S1': 3,  # Select line 1
                    'S2': 4,  # Select line 2
                    'Z': 5    # Common I/O line
                },
                'jumpers': {
                    'JP1': 'VEE to GND (closed)'
                }
            },
            'commands': {
                '1': 'Select confocal trigger (Y0)',
                '2': 'Select ODMR trigger (Y1)',
                '3': 'Select pulsed ESR trigger (Y2)'
            },
            'responses': {
                'success': 'Input is in range',
                'failure': 'Input out of range',
                'initialization': 'Initialized...Enter 1 for Confocal, 2 for ODMR, or 3 for Pulsed.',
                'initialization_legacy': 'Initialized...Enter 1 for Confocal, 2 for CW, or 3 for Pulsed.'
            }
        }
    
    def test_connection(self):
        """Test connection to Arduino."""
        if not self._is_connected:
            return {
                'connected': False,
                'error': 'Device not connected',
                'arduino_message': None
            }
        
        # Return either old or new message format for testing compatibility
        import random
        old_message = "Initialized...Enter 1 for Confocal, 2 for CW, or 3 for Pulsed."
        new_message = "Initialized...Enter 1 for Confocal, 2 for ODMR, or 3 for Pulsed."
        
        return {
            'connected': True,
            'arduino_message': random.choice([old_message, new_message]),
            'port': self.settings.get('port', 'COM3'),
            'baudrate': self.settings.get('baudrate', 9600),
            'current_selection': self._current_selection
        }
    
    def read_probes(self, key=None):
        """Read device probes."""
        if key is None:
            return {
                'status': self._current_selection,
                'port': self.settings.get('port', 'COM3'),
                'connected': self._is_connected
            }
        elif key == 'status':
            return self._current_selection
        elif key == 'port':
            return self.settings.get('port', 'COM3')
        elif key == 'connected':
            return self._is_connected
        else:
            raise KeyError(f"Unknown probe: {key}")
    
    def update(self, settings):
        """Update device settings."""
        super().update(settings)
        print(f"Mock MUX Control Device: Updated settings")
    
    def cleanup(self):
        """Clean up device resources."""
        self.disconnect()
    
    def __del__(self):
        """Destructor."""
        self.cleanup()


# Legacy compatibility
class MockMUXControl(MockMUXControlDevice):
    """Legacy mock MUXControl class for backward compatibility."""
    
    def __init__(self, port='COM3'):
        settings = {'port': port, 'auto_connect': True}
        super().__init__(settings=settings)
    
    def run(self, selector):
        """Legacy run method."""
        if self.select_trigger(selector):
            return 0
        else:
            return -1
    
    def close(self):
        """Legacy close method."""
        self.disconnect()


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
    
    try:
        from .sg384 import SG384Generator
    except ImportError:
        SG384Generator = MockSG384Generator
    
    try:
        from .mux_control import MUXControlDevice, MUXControl
    except ImportError:
        MUXControlDevice = MockMUXControlDevice
        MUXControl = MockMUXControl
else:
    PXI6733 = MockNI6229
    NI6281 = MockNI6229
    PCI6229 = MockNI6229
    PCI6601 = MockPCI6601
    NIDAQ = MockNI6229
    MCLNanoDrive = MockMCLNanoDrive
    AdwinGoldDevice = MockAdwinGoldDevice
    SG384Generator = MockSG384Generator
    MUXControlDevice = MockMUXControlDevice
    MUXControl = MockMUXControl

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
    "mux_control": MUXControlDevice,
    "mux": MUXControl,  # Legacy alias
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
    'MUXControlDevice', 'MUXControl',
    'create_device',
    'MockNI6229', 'MockPCI6601', 'MockMCLNanoDrive', 'MockAdwinGoldDevice', 'MockSG384Generator', 'MockMUXControlDevice'
]