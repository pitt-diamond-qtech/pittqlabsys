#!/usr/bin/env python3
"""
GUI Feedback Demo

This example demonstrates how the enhanced parameter feedback system
integrates with the GUI to provide detailed user feedback about parameter
changes, distinguishing between errors, clamping, and successful updates.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.device import Device
from src.core.parameter import Parameter
from src import ur


class SmartStageDevice(Device):
    """Example stage device with enhanced feedback capabilities."""
    
    def __init__(self, name="smart_stage"):
        super().__init__()
        self.name = name
        self._settings = Parameter([
            Parameter('position', 0.0, float, 'Stage position', units='mm'),
            Parameter('speed', 1.0, float, 'Stage speed', units='mm/s'),
        ])
        self._probes = {
            'position': 'Stage position in mm',
            'speed': 'Stage speed in mm/s'
        }
        self._last_error = None
        self._position_limits = (-10.0, 10.0)  # mm
        self._speed_limits = (0.1, 10.0)  # mm/s
    
    @property
    def _PROBES(self):
        return self._probes
    
    def read_probes(self, name=None):
        return self._settings
    
    def update(self, settings):
        """Simulate smart stage with different behaviors."""
        if 'position' in settings:
            requested = float(settings['position'])
            
            # Simulate different scenarios based on requested value
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
                # Speed too high - clamp to max
                clamped = self._speed_limits[1]
                self._settings['speed'] = clamped
                self._last_error = f"Speed clamped: {requested}mm/s exceeds max limit of {clamped}mm/s"
            elif requested < self._speed_limits[0]:
                # Speed too low - clamp to min
                clamped = self._speed_limits[0]
                self._settings['speed'] = clamped
                self._last_error = f"Speed clamped: {requested}mm/s below min limit of {clamped}mm/s"
            else:
                # Normal operation
                self._settings['speed'] = requested
                self._last_error = None
    
    def _update_and_get_with_feedback(self, settings):
        """Enhanced feedback method for this device."""
        # Store original values
        original_values = {}
        for key in settings.keys():
            if key in self._settings:
                original_values[key] = self._settings[key]
        
        # Update the device
        self.update(settings)
        
        # Get actual values
        actual_values = self.read_probes()
        
        # Generate detailed feedback
        feedback = {}
        for key, requested_value in settings.items():
            if key in actual_values:
                actual_value = actual_values[key]
                changed = requested_value != actual_value
                
                if changed:
                    # Determine the reason for the change
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


def simulate_gui_feedback():
    """Simulate how the GUI would handle different parameter update scenarios."""
    device = SmartStageDevice()
    
    print("🎯 GUI Feedback Demo - Smart Stage Device")
    print("=" * 60)
    print("This demonstrates how the GUI would provide feedback for different scenarios.")
    print()
    
    # Test scenarios
    test_cases = [
        {
            'name': 'Normal Operation',
            'settings': {'position': 5.0, 'speed': 2.0},
            'description': 'User sets reasonable values'
        },
        {
            'name': 'Position Clamping (Too High)',
            'settings': {'position': 15.0},
            'description': 'User requests position beyond limits'
        },
        {
            'name': 'Position Clamping (Too Low)',
            'settings': {'position': -15.0},
            'description': 'User requests position below limits'
        },
        {
            'name': 'Speed Clamping',
            'settings': {'speed': 15.0},
            'description': 'User requests speed beyond limits'
        },
        {
            'name': 'Hardware Error',
            'settings': {'position': 50.0},
            'description': 'Stage has mechanical fault'
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"📋 Test Case {i}: {case['name']}")
        print(f"   {case['description']}")
        print(f"   Requested: {case['settings']}")
        
        # Simulate GUI getting feedback
        feedback = device.get_feedback_only(case['settings'])
        
        # Simulate GUI processing feedback
        for param_name, param_feedback in feedback.items():
            print(f"\n   🔍 Parameter: {param_name}")
            print(f"      Requested: {param_feedback['requested']}")
            print(f"      Actual: {param_feedback['actual']}")
            print(f"      Changed: {param_feedback['changed']}")
            print(f"      Reason: {param_feedback['reason']}")
            print(f"      Message: {param_feedback['message']}")
            
            # Simulate GUI visual feedback
            if not param_feedback['changed']:
                print(f"      🎨 GUI: Green background (success)")
                print(f"      📢 GUI: 'Parameter {param_name} set successfully'")
            elif param_feedback['reason'] == 'error':
                print(f"      🎨 GUI: Red background (error)")
                print(f"      📢 GUI: 'Hardware error: {param_feedback['message']}'")
            elif param_feedback['reason'] == 'clamped':
                print(f"      🎨 GUI: Yellow background (warning)")
                print(f"      📢 GUI: 'Parameter clamped: {param_feedback['message']}'")
                print(f"      🔄 GUI: Update tree item to show actual value")
            else:
                print(f"      🎨 GUI: Yellow background (warning)")
                print(f"      📢 GUI: 'Parameter changed: {param_feedback['message']}'")
        
        print()
    
    print("=" * 60)
    print("🎉 Demo complete!")
    print("\nKey benefits of enhanced feedback:")
    print("  ✅ Distinguishes between errors and intentional clamping")
    print("  ✅ Provides specific error messages from hardware")
    print("  ✅ Updates GUI to show actual values when clamped")
    print("  ✅ Gives students clear understanding of what happened")


if __name__ == "__main__":
    simulate_gui_feedback()
