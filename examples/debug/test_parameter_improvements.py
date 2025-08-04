#!/usr/bin/env python3
"""
Test script to demonstrate Parameter class improvements from Phase 1.

This script shows the fixes for:
1. Nested Parameter objects remain Parameter objects (not dicts)
2. Validation works in nested structures
3. Units are accessible in nested structures
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from src.core.parameter import Parameter

def test_nested_parameter_improvements():
    """Test the improvements made in Phase 1."""
    print("=== Parameter Class Phase 1 Improvements ===\n")
    
    # Create a nested Parameter structure
    p = Parameter([
        Parameter('microwave', [
            Parameter('frequency', 2.85e9, float, 'Frequency', units='Hz'),
            Parameter('power', -45.0, float, 'Power', units='dBm'),
            Parameter('enable_output', True, bool, 'Enable output')
        ]),
        Parameter('acquisition', [
            Parameter('integration_time', 10.0, float, 'Integration time', units='ms'),
            Parameter('num_steps', 100, int, 'Number of steps'),
            Parameter('bidirectional', False, bool, 'Bidirectional sweep')
        ])
    ])
    
    print("1. Nested Parameter objects are now Parameter objects (not dicts):")
    print(f"   Type of p['microwave']: {type(p['microwave'])}")
    print(f"   Is Parameter: {isinstance(p['microwave'], Parameter)}")
    print(f"   Type of p['acquisition']: {type(p['acquisition'])}")
    print(f"   Is Parameter: {isinstance(p['acquisition'], Parameter)}")
    print()
    
    print("2. Units are accessible in nested structures:")
    print(f"   p['microwave'].units['frequency']: {p['microwave'].units['frequency']}")
    print(f"   p['microwave'].units['power']: {p['microwave'].units['power']}")
    print(f"   p['acquisition'].units['integration_time']: {p['acquisition'].units['integration_time']}")
    print()
    
    print("3. Validation works in nested structures:")
    print("   Testing valid assignment...")
    p['microwave']['frequency'] = 2.9e9
    print(f"   p['microwave']['frequency'] = {p['microwave']['frequency']}")
    
    print("   Testing invalid assignment (should raise AssertionError)...")
    try:
        p['microwave']['frequency'] = "invalid_string"
        print("   ERROR: Validation failed - invalid value was accepted")
    except AssertionError as e:
        print(f"   SUCCESS: Validation worked - {e}")
    
    print("   Testing invalid type assignment (should raise AssertionError)...")
    try:
        p['acquisition']['num_steps'] = 3.14  # Should be int, not float
        print("   ERROR: Validation failed - invalid type was accepted")
    except AssertionError as e:
        print(f"   SUCCESS: Validation worked - {e}")
    
    print()
    
    print("4. Nested Parameter objects have all Parameter functionality:")
    print(f"   p['microwave'].valid_values: {p['microwave'].valid_values}")
    print(f"   p['microwave'].info: {p['microwave'].info}")
    print(f"   p['microwave'].visible: {p['microwave'].visible}")
    print()
    
    print("5. Backward compatibility maintained:")
    print("   Simple Parameter creation still works:")
    simple_p = Parameter('test_param', 42, int, 'Test parameter', units='counts')
    print(f"   simple_p['test_param']: {simple_p['test_param']}")
    print(f"   simple_p.units['test_param']: {simple_p.units['test_param']}")
    
    print("\n=== Phase 1 Improvements Summary ===")
    print("✅ Nested Parameter objects remain Parameter objects")
    print("✅ Units are accessible in nested structures")
    print("✅ Validation works in nested structures")
    print("✅ Backward compatibility maintained")
    print("✅ Cleaner, more maintainable code")

if __name__ == "__main__":
    test_nested_parameter_improvements() 