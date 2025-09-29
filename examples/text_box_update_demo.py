#!/usr/bin/env python3
"""
Text Box Update Demo

This example demonstrates how the GUI updates the text box to show the actual
value when hardware changes the requested value (e.g., stage returns 45mm when
user requested 50mm).
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.device import Device
from src.core.parameter import Parameter
from src import ur


class TextBoxUpdateDemoDevice(Device):
    """Demo device that changes values to show text box updates."""
    
    def __init__(self, name="text_box_demo"):
        super().__init__()
        self.name = name
        self._settings = Parameter([
            Parameter('position', 0.0, float, 'Stage position', units='mm'),
            Parameter('frequency', 2.85e9 * ur.Hz, float, 'RF frequency', units='Hz'),
            Parameter('voltage', 0.0, float, 'DC voltage', units='V'),
        ])
        self._probes = {
            'position': 'Stage position in mm',
            'frequency': 'RF frequency in Hz',
            'voltage': 'DC voltage in V'
        }
        self._last_error = None
    
    @property
    def _PROBES(self):
        return self._probes
    
    def read_probes(self, name=None):
        return self._settings
    
    def update(self, settings):
        """Simulate hardware that changes values."""
        if 'position' in settings:
            requested = float(settings['position'])
            
            if requested == 50.0:
                # Simulate stage error - moves to wrong position
                self._settings['position'] = 45.0
                self._last_error = f"Stage error: requested {requested}mm, moved to 45mm"
            elif requested > 10.0:
                # Simulate clamping
                self._settings['position'] = 10.0
                self._last_error = f"Position clamped: {requested}mm exceeds max limit of 10mm"
            else:
                # Normal operation
                self._settings['position'] = requested
                self._last_error = None
        
        if 'frequency' in settings:
            requested = settings['frequency']
            if hasattr(requested, 'magnitude'):
                freq_hz = requested.to('Hz').magnitude
            else:
                freq_hz = float(requested)
            
            if freq_hz > 4e9:
                # Simulate frequency clamping
                clamped_hz = 4e9
                self._settings['frequency'] = clamped_hz * ur.Hz
                self._last_error = f"Frequency clamped: {freq_hz/1e9:.2f}GHz exceeds max limit of 4GHz"
            else:
                # Normal operation
                self._settings['frequency'] = requested
                self._last_error = None
        
        if 'voltage' in settings:
            requested = float(settings['voltage'])
            
            if requested > 5.0:
                # Simulate voltage clamping
                self._settings['voltage'] = 5.0
                self._last_error = f"Voltage clamped: {requested}V exceeds max limit of 5V"
            else:
                # Normal operation
                self._settings['voltage'] = requested
                self._last_error = None
    
    def _update_and_get_with_feedback(self, settings):
        """Enhanced feedback method."""
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


def simulate_text_box_updates():
    """Simulate how the GUI updates text boxes when hardware changes values."""
    device = TextBoxUpdateDemoDevice()
    
    print("📝 Text Box Update Demo - GUI Value Correction")
    print("=" * 60)
    print("This demonstrates how the GUI updates text boxes to show actual")
    print("hardware values when they differ from what the user requested.")
    print()
    
    # Test scenarios
    test_cases = [
        {
            'name': 'Stage Error (50mm → 45mm)',
            'settings': {'position': 50.0},
            'description': 'User requests 50mm, stage moves to 45mm due to error'
        },
        {
            'name': 'Position Clamping (15mm → 10mm)',
            'settings': {'position': 15.0},
            'description': 'User requests 15mm, hardware clamps to 10mm'
        },
        {
            'name': 'Frequency Clamping (6GHz → 4GHz)',
            'settings': {'frequency': 6e9 * ur.Hz},
            'description': 'User requests 6GHz, hardware clamps to 4GHz'
        },
        {
            'name': 'Voltage Clamping (8V → 5V)',
            'settings': {'voltage': 8.0},
            'description': 'User requests 8V, hardware clamps to 5V'
        },
        {
            'name': 'Normal Operation (No Change)',
            'settings': {'position': 5.0, 'voltage': 3.0},
            'description': 'User requests valid values, hardware accepts them'
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"📋 Test Case {i}: {case['name']}")
        print(f"   {case['description']}")
        print(f"   User types in text box: {case['settings']}")
        
        # Get feedback
        feedback = device.get_feedback_only(case['settings'])
        
        # Simulate GUI text box updates
        for param_name, param_feedback in feedback.items():
            requested_value = param_feedback['requested']
            actual_value = param_feedback['actual']
            changed = param_feedback['changed']
            
            print(f"\n   🔍 Parameter: {param_name}")
            print(f"      User typed: {requested_value}")
            print(f"      Hardware set: {actual_value}")
            print(f"      Value changed: {changed}")
            
            if changed:
                print(f"      📝 GUI ACTION:")
                print(f"         - item.value = {actual_value}")
                print(f"         - item.setText(1, '{actual_value}')")
                print(f"         - Text box now shows: {actual_value}")
                print(f"         - User sees corrected value, not what they typed")
            else:
                print(f"      📝 GUI ACTION:")
                print(f"         - Text box shows: {actual_value}")
                print(f"         - No change needed (value accepted)")
        
        print()
    
    print("=" * 60)
    print("🎉 Text Box Update Summary:")
    print()
    print("✅ IMPLEMENTED: Text boxes are automatically updated to show actual values")
    print("   - When hardware changes a value, the GUI updates the text box")
    print("   - User sees what the hardware actually did, not what they requested")
    print("   - This prevents confusion about the actual device state")
    print()
    print("🔧 IMPLEMENTATION:")
    print("   - item.value = actual_value")
    print("   - item.setText(1, str(actual_value))")
    print("   - Works for both enhanced and fallback feedback systems")
    print()
    print("💡 BENEFITS:")
    print("   - Students see the true hardware state")
    print("   - No confusion between requested vs actual values")
    print("   - Clear visual feedback about what actually happened")


if __name__ == "__main__":
    simulate_text_box_updates()
