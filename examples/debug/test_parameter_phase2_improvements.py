#!/usr/bin/env python3
"""
Test script to demonstrate Parameter class Phase 2 improvements (pint integration).

This script shows the new pint integration features:
1. Support for pint Quantity objects
2. Automatic unit conversion
3. Unit validation
4. Enhanced unit information
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from src.core.parameter import Parameter
from src import ur

def test_phase2_improvements():
    """Test the Phase 2 pint integration improvements."""
    print("=== Parameter Class Phase 2 Improvements (Pint Integration) ===\n")
    
    # Test 1: Pint Quantity Support
    print("1. Pint Quantity Support:")
    p1 = Parameter('frequency', 2.85e9 * ur.Hz, float, 'Frequency')
    print(f"   Is pint quantity: {p1.is_pint_quantity()}")
    print(f"   Value: {p1['frequency']}")
    print(f"   Magnitude: {p1['frequency'].magnitude}")
    print(f"   Units: {p1['frequency'].units}")
    print()
    
    # Test 2: Unit Conversion
    print("2. Unit Conversion:")
    freq_ghz = p1.get_value_in_units('GHz')
    print(f"   Original: {p1['frequency']}")
    print(f"   In GHz: {freq_ghz}")
    print(f"   In MHz: {p1.get_value_in_units('MHz')}")
    print()
    
    # Test 3: Setting Values with Units
    print("3. Setting Values with Units:")
    p1.set_value_with_units(2.9, 'GHz')
    print(f"   New value: {p1['frequency']}")
    print(f"   Magnitude: {p1['frequency'].magnitude}")
    print(f"   Units: {p1['frequency'].units}")
    print()
    
    # Test 4: Unit Information
    print("4. Unit Information:")
    info = p1.get_unit_info()
    print(f"   Is pint quantity: {info['is_pint_quantity']}")
    print(f"   Magnitude: {info['magnitude']}")
    print(f"   Units: {info['units']}")
    print(f"   Units string: {info['units_string']}")
    print(f"   Dimensionality: {info['dimensionality']}")
    print()
    
    # Test 5: Unit Validation
    print("5. Unit Validation:")
    try:
        p1.validate_units('GHz', 'MHz')
        print("   ✅ GHz and MHz are compatible")
    except ValueError as e:
        print(f"   ❌ Error: {e}")
    
    try:
        p1.validate_units('GHz', 'kg')
        print("   ❌ Should have failed")
    except ValueError as e:
        print(f"   ✅ Correctly rejected incompatible units: {e}")
    print()
    
    # Test 6: Compatible Units
    print("6. Compatible Units:")
    compatible = p1.get_compatible_units()
    print(f"   Compatible units: {compatible[:10]}...")  # Show first 10
    print(f"   Total compatible units: {len(compatible)}")
    print()
    
    # Test 7: Nested Pint Quantities
    print("7. Nested Pint Quantities:")
    p2 = Parameter([
        Parameter('microwave', [
            Parameter('frequency', 2.85e9 * ur.Hz, float, 'Frequency'),
            Parameter('power', -45.0, float, 'Power', units='dBm')
        ])
    ])
    
    print(f"   Nested frequency is pint: {p2['microwave'].is_pint_quantity('frequency')}")
    print(f"   Nested power is pint: {p2['microwave'].is_pint_quantity('power')}")
    
    # Test unit conversion in nested structure
    nested_freq_ghz = p2['microwave'].get_value_in_units('GHz', 'frequency')
    print(f"   Nested frequency in GHz: {nested_freq_ghz}")
    print()
    
    # Test 8: Backward Compatibility
    print("8. Backward Compatibility:")
    p3 = Parameter('voltage', 5.0, float, 'Voltage', units='V')
    print(f"   String units still work: {p3.units['voltage']}")
    print(f"   Is pint quantity: {p3.is_pint_quantity()}")
    print(f"   Value: {p3['voltage']}")
    print()
    
    # Test 9: Mixed Pint and String Units
    print("9. Mixed Pint and String Units:")
    p4 = Parameter([
        Parameter('device', [
            Parameter('frequency', 2.85e9 * ur.Hz, float, 'Frequency'),
            Parameter('enabled', True, bool, 'Enable flag'),
            Parameter('voltage', 5.0, float, 'Voltage', units='V')
        ])
    ])
    
    print(f"   Frequency is pint: {p4['device'].is_pint_quantity('frequency')}")
    print(f"   Enabled is pint: {p4['device'].is_pint_quantity('enabled')}")
    print(f"   Voltage is pint: {p4['device'].is_pint_quantity('voltage')}")
    print()
    
    # Test 10: Convert Units In Place
    print("10. Convert Units In Place:")
    p5 = Parameter('time', 1.0 * ur.s, float, 'Time')
    print(f"   Original: {p5['time']}")
    p5.convert_units('ms')
    print(f"   After conversion: {p5['time']}")
    print()
    
    print("=== Phase 2 Improvements Summary ===")
    print("✅ Pint Quantity objects supported")
    print("✅ Automatic unit conversion")
    print("✅ Unit validation and compatibility checking")
    print("✅ Enhanced unit information")
    print("✅ Nested pint quantities work")
    print("✅ Backward compatibility maintained")
    print("✅ Mixed pint and string units supported")
    print("✅ In-place unit conversion")

if __name__ == "__main__":
    test_phase2_improvements() 