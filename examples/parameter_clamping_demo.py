#!/usr/bin/env python3
"""
Parameter Clamping Demo

This example demonstrates how the Device class can detect when hardware
clamps requested values to physical limits, and how the GUI can alert users
to this fact.

Example scenario:
- User requests stage to move to 50mm
- Hardware clamps to 10mm (due to physical limits)
- GUI detects the difference and alerts user
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.device import Device
from src.core.parameter import Parameter
from src import ur


class ClampingDevice(Device):
    """Example device that simulates hardware clamping behavior."""
    
    def __init__(self, name="clamping_device"):
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
    
    @property
    def _PROBES(self):
        return self._probes
    
    def read_probes(self, name=None):
        return self._settings
    
    def update(self, settings):
        """Simulate hardware clamping behavior."""
        if 'position' in settings:
            # Clamp position between -10 and 10 mm
            requested = float(settings['position'])
            clamped = max(-10.0, min(10.0, requested))
            self._settings['position'] = clamped
            if clamped != requested:
                print(f"  🔧 Hardware: Position clamped from {requested}mm to {clamped}mm")
        
        if 'frequency' in settings:
            # Clamp frequency between 1 and 4 GHz
            requested = settings['frequency']
            if hasattr(requested, 'magnitude'):
                freq_hz = requested.to('Hz').magnitude
            else:
                freq_hz = float(requested)
            
            clamped_hz = max(1e9, min(4e9, freq_hz))
            self._settings['frequency'] = clamped_hz * ur.Hz
            if clamped_hz != freq_hz:
                print(f"  🔧 Hardware: Frequency clamped from {freq_hz/1e9:.2f}GHz to {clamped_hz/1e9:.2f}GHz")
        
        if 'voltage' in settings:
            # Clamp voltage between -5 and 5 V
            requested = float(settings['voltage'])
            clamped = max(-5.0, min(5.0, requested))
            self._settings['voltage'] = clamped
            if clamped != requested:
                print(f"  🔧 Hardware: Voltage clamped from {requested}V to {clamped}V")


def simulate_user_interaction():
    """Simulate a user interacting with the device through the GUI."""
    device = ClampingDevice()
    
    print("🎯 Parameter Clamping Demo")
    print("=" * 50)
    print("This demonstrates how the GUI can detect when hardware")
    print("clamps requested values to physical limits.")
    print()
    
    # Simulate user requests that will be clamped
    test_cases = [
        {
            'name': 'Stage Position',
            'requested': {'position': 50.0},  # Will be clamped to 10mm
            'description': 'User wants to move stage to 50mm'
        },
        {
            'name': 'RF Frequency', 
            'requested': {'frequency': 6e9 * ur.Hz},  # Will be clamped to 4GHz
            'description': 'User wants to set frequency to 6GHz'
        },
        {
            'name': 'DC Voltage',
            'requested': {'voltage': -8.0},  # Will be clamped to -5V
            'description': 'User wants to set voltage to -8V'
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n📋 Test Case {i}: {case['name']}")
        print(f"   {case['description']}")
        print(f"   Requested: {case['requested']}")
        
        # Use update_and_get to get actual values
        result = device.update_and_get(case['requested'])
        
        # Check if any values were clamped
        clamped_params = []
        for param, requested_value in case['requested'].items():
            actual_value = result[param]
            
            # Compare requested vs actual
            if hasattr(requested_value, 'magnitude'):
                # Pint quantity
                if actual_value.magnitude != requested_value.magnitude:
                    clamped_params.append(f"{param}: {requested_value} → {actual_value}")
            else:
                # Regular value
                if actual_value != requested_value:
                    clamped_params.append(f"{param}: {requested_value} → {actual_value}")
        
        if clamped_params:
            print("   ⚠️  CLAMPING DETECTED:")
            for param_info in clamped_params:
                print(f"      {param_info}")
            print("   💡 GUI should alert user about these changes!")
        else:
            print("   ✅ No clamping - all values set as requested")
    
    print("\n" + "=" * 50)
    print("🎉 Demo complete!")
    print("\nKey takeaway: The GUI can detect when hardware clamps")
    print("requested values and alert users to this fact, helping")
    print("them understand the actual device state.")


if __name__ == "__main__":
    simulate_user_interaction()
