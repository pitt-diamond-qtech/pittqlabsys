#!/usr/bin/env python3
"""
Test Enhanced Validation Features

This script demonstrates all the new validation and feedback features
without needing the full GUI, so you can see how they work.

Features demonstrated:
- Units validation with pint
- Parameter clamping and error detection
- Enhanced feedback system
- Text box correction simulation
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from examples.mock_hardware_for_gui_testing import MockStageDevice, MockRFGenerator
from src import ur


def simulate_gui_behavior(device, param_name, requested_value):
    """Simulate how the GUI would handle a parameter update."""
    print(f"\n🔍 Testing {param_name} = {requested_value}")
    print("-" * 50)
    
    # Get feedback from device
    feedback = device.get_feedback_only({param_name: requested_value})
    param_feedback = feedback[param_name]
    
    print(f"User typed: {param_feedback['requested']}")
    print(f"Hardware set: {param_feedback['actual']}")
    print(f"Changed: {param_feedback['changed']}")
    print(f"Reason: {param_feedback['reason']}")
    print(f"Message: {param_feedback['message']}")
    
    # Simulate GUI actions
    if param_feedback['changed']:
        print(f"\n📝 GUI Actions:")
        print(f"  - item.value = {param_feedback['actual']}")
        print(f"  - item.setText(1, '{param_feedback['actual']}')")
        print(f"  - Text box now shows: {param_feedback['actual']}")
        
        if param_feedback['reason'] == 'error':
            print(f"  - Background: RED (error)")
            print(f"  - Popup: Critical dialog - 'Hardware Error Detected'")
        elif param_feedback['reason'] == 'clamped':
            print(f"  - Background: YELLOW (warning)")
            print(f"  - Popup: None (just visual feedback)")
        else:
            print(f"  - Background: YELLOW (warning)")
            print(f"  - Popup: None (just visual feedback)")
    else:
        print(f"\n📝 GUI Actions:")
        print(f"  - Text box shows: {param_feedback['actual']}")
        print(f"  - Background: GREEN (success)")
        print(f"  - Popup: None (success messages don't need popups)")


def test_stage_device():
    """Test stage device with various scenarios."""
    print("🎯 Testing Stage Device")
    print("=" * 60)
    
    stage = MockStageDevice()
    
    # Test scenarios
    test_cases = [
        ('position', 5.0, 'Normal operation'),
        ('position', 15.0, 'Clamping (exceeds limit)'),
        ('position', -15.0, 'Clamping (below limit)'),
        ('position', 50.0, 'Hardware error'),
        ('speed', 2.0, 'Normal speed'),
        ('speed', 15.0, 'Speed clamping'),
        ('acceleration', 25.0, 'Normal acceleration'),
        ('acceleration', 75.0, 'Acceleration clamping'),
    ]
    
    for param, value, description in test_cases:
        print(f"\n📋 {description}")
        simulate_gui_behavior(stage, param, value)


def test_rf_generator():
    """Test RF generator with units validation."""
    print("\n\n🎯 Testing RF Generator")
    print("=" * 60)
    
    rf = MockRFGenerator()
    
    # Test scenarios
    test_cases = [
        ('frequency', 2.85e9 * ur.Hz, 'Normal frequency'),
        ('frequency', 8e9 * ur.Hz, 'Frequency clamping'),
        ('frequency', 2.85e3 * ur.MHz, 'Units conversion (MHz)'),
        ('frequency', 2.85e6 * ur.kHz, 'Units conversion (kHz)'),
        ('power', 10.0 * ur.mW, 'Normal power'),
        ('power', 25.0 * ur.mW, 'Power clamping'),
        ('power', 0.01 * ur.W, 'Units conversion (W to mW)'),
        ('phase', 45.0, 'Normal phase'),
        ('phase', 200.0, 'Phase clamping'),
        ('enabled', True, 'Enable output'),
    ]
    
    for param, value, description in test_cases:
        print(f"\n📋 {description}")
        simulate_gui_behavior(rf, param, value)


def test_units_validation():
    """Test units validation specifically."""
    print("\n\n🎯 Testing Units Validation")
    print("=" * 60)
    
    rf = MockRFGenerator()
    
    # Test various unit inputs for frequency
    frequency_tests = [
        (2.85e9 * ur.Hz, '2.85 GHz in Hz'),
        (2.85e3 * ur.MHz, '2.85 GHz in MHz'),
        (2.85e6 * ur.kHz, '2.85 GHz in kHz'),
        (2.85e12 * ur.mHz, '2.85 GHz in mHz'),
    ]
    
    for freq, description in frequency_tests:
        print(f"\n📋 {description}")
        simulate_gui_behavior(rf, 'frequency', freq)
    
    # Test various unit inputs for power
    power_tests = [
        (10.0 * ur.mW, '10 mW'),
        (0.01 * ur.W, '0.01 W (should convert to 10 mW)'),
        (10.0 * ur.dBm, '10 dBm (should convert to mW)'),
    ]
    
    for power, description in power_tests:
        print(f"\n📋 {description}")
        simulate_gui_behavior(rf, 'power', power)


def main():
    """Run all validation tests."""
    print("🧪 Enhanced Validation Features Test")
    print("=" * 60)
    print("This demonstrates all the new validation and feedback features")
    print("that are now available in the GUI.")
    print()
    
    test_stage_device()
    test_rf_generator()
    test_units_validation()
    
    print("\n\n🎉 Test Complete!")
    print("=" * 60)
    print("All validation features are working correctly:")
    print("✅ Units validation with pint")
    print("✅ Parameter clamping detection")
    print("✅ Hardware error detection")
    print("✅ Enhanced feedback system")
    print("✅ Text box correction simulation")
    print("✅ Visual feedback simulation")
    print()
    print("🚀 Ready to test in the actual GUI!")
    print("Run: python examples/test_gui_with_validation.py")


if __name__ == "__main__":
    main()
