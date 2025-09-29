#!/usr/bin/env python3
"""
Mock Hardware for GUI Testing

This module provides comprehensive mock devices that support all the new
validation and feedback features for testing the GUI without real hardware.

Features tested:
- Units validation with pint
- Parameter clamping and error detection
- Enhanced feedback system
- Visual GUI updates
- Text box corrections
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.device import Device
from src.core.parameter import Parameter
from src import ur


class MockStageDevice(Device):
    """Mock stage device with enhanced feedback for GUI testing."""
    
    def __init__(self, name="mock_stage"):
        super().__init__()
        self.name = name
        self._settings = Parameter([
            Parameter('position', 0.0, float, 'Stage position', units='mm'),
            Parameter('speed', 1.0, float, 'Stage speed', units='mm/s'),
            Parameter('acceleration', 10.0, float, 'Stage acceleration', units='mm/s²'),
        ])
        self._probes = {
            'position': 'Stage position in mm',
            'speed': 'Stage speed in mm/s',
            'acceleration': 'Stage acceleration in mm/s²'
        }
        self._last_error = None
        self._position_limits = (-10.0, 10.0)  # mm
        self._speed_limits = (0.1, 10.0)  # mm/s
        self._acceleration_limits = (1.0, 50.0)  # mm/s²
    
    @property
    def _PROBES(self):
        return self._probes
    
    def read_probes(self, name=None):
        return self._settings
    
    def update(self, settings):
        """Simulate stage behavior with different scenarios."""
        if 'position' in settings:
            requested = float(settings['position'])
            
            if requested == 50.0:
                # Simulate stage error - moves to wrong position
                self._settings['position'] = 45.0
                self._last_error = f"Stage error: requested {requested}mm, moved to 45mm (mechanical fault)"
            elif requested > self._position_limits[1]:
                # Simulate clamping - exceeds physical limits
                clamped = self._position_limits[1]
                self._settings['position'] = clamped
                self._last_error = f"Position clamped: {requested}mm exceeds max limit of {clamped}mm"
            elif requested < self._position_limits[0]:
                # Simulate clamping - below minimum
                clamped = self._position_limits[0]
                self._settings['position'] = clamped
                self._last_error = f"Position clamped: {requested}mm below min limit of {clamped}mm"
            else:
                # Normal operation
                self._settings['position'] = requested
                self._last_error = None
        
        if 'speed' in settings:
            requested = float(settings['speed'])
            
            if requested > self._speed_limits[1]:
                clamped = self._speed_limits[1]
                self._settings['speed'] = clamped
                self._last_error = f"Speed clamped: {requested}mm/s exceeds max limit of {clamped}mm/s"
            elif requested < self._speed_limits[0]:
                clamped = self._speed_limits[0]
                self._settings['speed'] = clamped
                self._last_error = f"Speed clamped: {requested}mm/s below min limit of {clamped}mm/s"
            else:
                self._settings['speed'] = requested
                self._last_error = None
        
        if 'acceleration' in settings:
            requested = float(settings['acceleration'])
            
            if requested > self._acceleration_limits[1]:
                clamped = self._acceleration_limits[1]
                self._settings['acceleration'] = clamped
                self._last_error = f"Acceleration clamped: {requested}mm/s² exceeds max limit of {clamped}mm/s²"
            elif requested < self._acceleration_limits[0]:
                clamped = self._acceleration_limits[0]
                self._settings['acceleration'] = clamped
                self._last_error = f"Acceleration clamped: {requested}mm/s² below min limit of {clamped}mm/s²"
            else:
                self._settings['acceleration'] = requested
                self._last_error = None
    
    def _update_and_get_with_feedback(self, settings):
        """Enhanced feedback method for this device."""
        original_values = {}
        for key in settings.keys():
            if key in self._settings:
                original_values[key] = self._settings[key]
        
        self.update(settings)
        actual_values = self.read_probes()
        
        feedback = {}
        for key, requested_value in settings.items():
            if key in actual_values:
                actual_value = actual_values[key]
                changed = requested_value != actual_value
                
                if changed:
                    if self._last_error and 'error' in self._last_error.lower():
                        reason = 'error'
                        message = self._last_error
                    elif self._last_error and 'clamped' in self._last_error.lower():
                        reason = 'clamped'
                        message = self._last_error
                    else:
                        reason = 'unknown'
                        message = f'Value changed from {requested_value} to {actual_value}'
                    
                    feedback[key] = {
                        'changed': True,
                        'requested': requested_value,
                        'actual': actual_value,
                        'reason': reason,
                        'message': message
                    }
                else:
                    feedback[key] = {
                        'changed': False,
                        'requested': requested_value,
                        'actual': actual_value,
                        'reason': 'success',
                        'message': 'Value set successfully'
                    }
        
        return {
            'actual_values': actual_values,
            'feedback': feedback
        }


class MockRFGenerator(Device):
    """Mock RF generator with units validation for GUI testing."""
    
    def __init__(self, name="mock_rf_generator"):
        super().__init__()
        self.name = name
        self._settings = Parameter([
            Parameter('frequency', 2.85e9 * ur.Hz, float, 'RF frequency', units='Hz'),
            Parameter('power', 10.0 * ur.mW, float, 'RF power', units='mW'),
            Parameter('phase', 0.0, float, 'RF phase', units='deg'),
            Parameter('enabled', False, bool, 'RF output enabled'),
        ])
        self._probes = {
            'frequency': 'RF frequency in Hz',
            'power': 'RF power in mW',
            'phase': 'RF phase in degrees',
            'enabled': 'RF output status'
        }
        self._last_error = None
        self._frequency_limits = (1e6, 6e9)  # 1 MHz to 6 GHz
        self._power_limits = (0.0, 20.0)  # 0 to 20 mW
        self._phase_limits = (-180.0, 180.0)  # degrees
    
    @property
    def _PROBES(self):
        return self._probes
    
    def read_probes(self, name=None):
        return self._settings
    
    def update(self, settings):
        """Simulate RF generator behavior with units validation."""
        if 'frequency' in settings:
            requested = settings['frequency']
            if hasattr(requested, 'magnitude'):
                freq_hz = requested.to('Hz').magnitude
            else:
                freq_hz = float(requested)
            
            if freq_hz > self._frequency_limits[1]:
                clamped_hz = self._frequency_limits[1]
                self._settings['frequency'] = clamped_hz * ur.Hz
                self._last_error = f"Frequency clamped: {freq_hz/1e9:.2f}GHz exceeds max limit of {clamped_hz/1e9:.2f}GHz"
            elif freq_hz < self._frequency_limits[0]:
                clamped_hz = self._frequency_limits[0]
                self._settings['frequency'] = clamped_hz * ur.Hz
                self._last_error = f"Frequency clamped: {freq_hz/1e6:.2f}MHz below min limit of {clamped_hz/1e6:.2f}MHz"
            else:
                self._settings['frequency'] = requested
                self._last_error = None
        
        if 'power' in settings:
            requested = settings['power']
            if hasattr(requested, 'magnitude'):
                power_mw = requested.to('mW').magnitude
            else:
                power_mw = float(requested)
            
            if power_mw > self._power_limits[1]:
                clamped_mw = self._power_limits[1]
                self._settings['power'] = clamped_mw * ur.mW
                self._last_error = f"Power clamped: {power_mw:.1f}mW exceeds max limit of {clamped_mw:.1f}mW"
            elif power_mw < self._power_limits[0]:
                clamped_mw = self._power_limits[0]
                self._settings['power'] = clamped_mw * ur.mW
                self._last_error = f"Power clamped: {power_mw:.1f}mW below min limit of {clamped_mw:.1f}mW"
            else:
                self._settings['power'] = requested
                self._last_error = None
        
        if 'phase' in settings:
            requested = float(settings['phase'])
            
            if requested > self._phase_limits[1]:
                clamped = self._phase_limits[1]
                self._settings['phase'] = clamped
                self._last_error = f"Phase clamped: {requested}° exceeds max limit of {clamped}°"
            elif requested < self._phase_limits[0]:
                clamped = self._phase_limits[0]
                self._settings['phase'] = clamped
                self._last_error = f"Phase clamped: {requested}° below min limit of {clamped}°"
            else:
                self._settings['phase'] = requested
                self._last_error = None
        
        if 'enabled' in settings:
            self._settings['enabled'] = bool(settings['enabled'])
            self._last_error = None
    
    def _update_and_get_with_feedback(self, settings):
        """Enhanced feedback method for this device."""
        original_values = {}
        for key in settings.keys():
            if key in self._settings:
                original_values[key] = self._settings[key]
        
        self.update(settings)
        actual_values = self.read_probes()
        
        feedback = {}
        for key, requested_value in settings.items():
            if key in actual_values:
                actual_value = actual_values[key]
                
                if hasattr(requested_value, 'magnitude') and hasattr(actual_value, 'magnitude'):
                    changed = requested_value.magnitude != actual_value.magnitude
                else:
                    changed = requested_value != actual_value
                
                if changed:
                    if self._last_error and 'error' in self._last_error.lower():
                        reason = 'error'
                        message = self._last_error
                    elif self._last_error and 'clamped' in self._last_error.lower():
                        reason = 'clamped'
                        message = self._last_error
                    else:
                        reason = 'unknown'
                        message = f'Value changed from {requested_value} to {actual_value}'
                    
                    feedback[key] = {
                        'changed': True,
                        'requested': requested_value,
                        'actual': actual_value,
                        'reason': reason,
                        'message': message
                    }
                else:
                    feedback[key] = {
                        'changed': False,
                        'requested': requested_value,
                        'actual': actual_value,
                        'reason': 'success',
                        'message': 'Value set successfully'
                    }
        
        return {
            'actual_values': actual_values,
            'feedback': feedback
        }


def create_mock_devices():
    """Create a set of mock devices for GUI testing."""
    return {
        'stage': MockStageDevice(),
        'rf_generator': MockRFGenerator(),
    }


def test_mock_devices():
    """Test the mock devices to ensure they work correctly."""
    print("🧪 Testing Mock Devices for GUI")
    print("=" * 50)
    
    devices = create_mock_devices()
    
    # Test stage device
    print("\n📋 Testing Stage Device:")
    stage = devices['stage']
    
    # Test normal operation
    result = stage.update_and_get({'position': 5.0, 'speed': 2.0})
    print(f"  Normal operation: {result}")
    
    # Test clamping
    result = stage.update_and_get({'position': 15.0})
    print(f"  Clamping test: {result}")
    
    # Test error
    result = stage.update_and_get({'position': 50.0})
    print(f"  Error test: {result}")
    
    # Test RF generator
    print("\n📋 Testing RF Generator:")
    rf = devices['rf_generator']
    
    # Test normal operation
    result = rf.update_and_get({'frequency': 2.85e9 * ur.Hz, 'power': 10.0 * ur.mW})
    print(f"  Normal operation: {result}")
    
    # Test frequency clamping
    result = rf.update_and_get({'frequency': 8e9 * ur.Hz})
    print(f"  Frequency clamping: {result}")
    
    # Test power clamping
    result = rf.update_and_get({'power': 25.0 * ur.mW})
    print(f"  Power clamping: {result}")
    
    print("\n✅ Mock devices ready for GUI testing!")


if __name__ == "__main__":
    test_mock_devices()
