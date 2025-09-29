#!/usr/bin/env python3
"""
Notification Demo

This example demonstrates the different types of notifications that the GUI
provides when parameters are updated, including both log messages and popup dialogs.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.device import Device
from src.core.parameter import Parameter
from src import ur


class NotificationDemoDevice(Device):
    """Demo device that triggers different types of notifications."""
    
    def __init__(self, name="notification_demo"):
        super().__init__()
        self.name = name
        self._settings = Parameter([
            Parameter('position', 0.0, float, 'Stage position', units='mm'),
            Parameter('frequency', 2.85e9 * ur.Hz, float, 'RF frequency', units='Hz'),
        ])
        self._probes = {
            'position': 'Stage position in mm',
            'frequency': 'RF frequency in Hz'
        }
        self._last_error = None
    
    @property
    def _PROBES(self):
        return self._probes
    
    def read_probes(self, name=None):
        return self._settings
    
    def update(self, settings):
        """Simulate different notification scenarios."""
        if 'position' in settings:
            requested = float(settings['position'])
            
            if requested == 50.0:
                # Simulate hardware error
                self._settings['position'] = 45.0
                self._last_error = f"Stage error: requested {requested}mm, moved to 45mm (mechanical fault)"
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


def simulate_notifications():
    """Simulate the different types of notifications."""
    device = NotificationDemoDevice()
    
    print("🔔 Notification Demo - GUI Feedback System")
    print("=" * 60)
    print("This demonstrates the different types of notifications users will see.")
    print()
    
    # Test scenarios
    test_cases = [
        {
            'name': 'Success Notification',
            'settings': {'position': 5.0},
            'description': 'Parameter set successfully - shows info popup'
        },
        {
            'name': 'Clamping Warning',
            'settings': {'position': 15.0},
            'description': 'Parameter clamped - shows warning popup'
        },
        {
            'name': 'Hardware Error',
            'settings': {'position': 50.0},
            'description': 'Hardware error - shows critical error popup'
        },
        {
            'name': 'Frequency Clamping',
            'settings': {'frequency': 6e9 * ur.Hz},
            'description': 'Frequency clamped - shows warning popup'
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"📋 Test Case {i}: {case['name']}")
        print(f"   {case['description']}")
        print(f"   Requested: {case['settings']}")
        
        # Get feedback
        feedback = device.get_feedback_only(case['settings'])
        
        # Simulate GUI notification behavior
        for param_name, param_feedback in feedback.items():
            print(f"\n   🔍 Parameter: {param_name}")
            print(f"      Requested: {param_feedback['requested']}")
            print(f"      Actual: {param_feedback['actual']}")
            print(f"      Reason: {param_feedback['reason']}")
            print(f"      Message: {param_feedback['message']}")
            
            # Simulate notification behavior
            if not param_feedback['changed']:
                print(f"      📝 LOG: INFO - Parameter notification: {param_feedback['message']}")
                print(f"      🎨 VISUAL: Green background on tree item")
                print(f"      🪟 POPUP: None (success messages don't need popups)")
            elif param_feedback['reason'] == 'error':
                print(f"      📝 LOG: ERROR - Parameter notification (ERROR): {param_feedback['message']}")
                print(f"      🎨 VISUAL: Red background on tree item")
                print(f"      🪟 POPUP: Critical dialog - 'Hardware Error Detected'")
                print(f"      ⏰ MODAL: User must click OK to dismiss")
            elif param_feedback['reason'] == 'clamped':
                print(f"      📝 LOG: INFO - Parameter notification: {param_feedback['message']}")
                print(f"      🎨 VISUAL: Yellow background on tree item")
                print(f"      🪟 POPUP: None (clamping is normal, just visual feedback)")
        
        print()
    
    print("=" * 60)
    print("🎉 Notification Types Summary:")
    print()
    print("📝 LOG MESSAGES:")
    print("  - All notifications are logged to the application log")
    print("  - Errors: ERROR level (red in log)")
    print("  - Warnings/Success: INFO level (normal in log)")
    print()
    print("🪟 POPUP DIALOGS:")
    print("  - ✅ SUCCESS: No popup (just log + visual feedback)")
    print("  - ⚠️  CLAMPING: No popup (just log + visual feedback)")
    print("  - ❌ ERROR: Critical dialog, user must click OK")
    print()
    print("🎨 VISUAL FEEDBACK:")
    print("  - Tree items get colored backgrounds")
    print("  - Green: Success, Yellow: Warning, Red: Error")
    print("  - Backgrounds auto-clear after a few seconds")


if __name__ == "__main__":
    simulate_notifications()
