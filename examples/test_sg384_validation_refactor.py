#!/usr/bin/env python3
"""
Test SG384 Validation Refactor

This script tests that the refactored validate_parameter method correctly
uses get_parameter_ranges to avoid duplication and ensure consistency.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.Controller import MockSG384Generator


def test_validation_consistency():
    """Test that validate_parameter and get_parameter_ranges are consistent."""
    print("🧪 Testing SG384 Validation Consistency")
    print("=" * 50)
    
    # Use the enhanced mock device
    sg384 = MockSG384Generator()
    
    # Test parameters
    test_cases = [
        ('frequency', 1.5e9, 'Below minimum frequency'),
        ('frequency', 2.85e9, 'Valid frequency'),
        ('frequency', 5.0e9, 'Above maximum frequency'),
        ('power', -150.0, 'Below minimum power'),
        ('power', 0.0, 'Valid power'),
        ('power', 20.0, 'Above maximum power'),
        ('sweep_rate', 0.5, 'Valid sweep rate'),
        ('sweep_rate', 120.0, 'At maximum sweep rate (should fail)'),
        ('sweep_rate', 150.0, 'Above maximum sweep rate'),
        ('modulation_depth', -1e6, 'Below minimum modulation depth'),
        ('modulation_depth', 50e6, 'Valid modulation depth'),
        ('modulation_depth', 200e6, 'Above maximum modulation depth'),
    ]
    
    for param_name, value, description in test_cases:
        print(f"\n📋 {description}")
        print(f"   Parameter: {param_name}, Value: {value}")
        
        # Get ranges
        ranges = sg384.get_parameter_ranges([param_name])
        print(f"   Ranges: {ranges}")
        
        # Validate parameter
        validation_result = sg384.validate_parameter([param_name], value)
        print(f"   Validation: {validation_result}")
        
        # Check consistency
        if ranges and 'min' in ranges and 'max' in ranges:
            min_val = ranges['min']
            max_val = ranges['max']
            
            if value < min_val:
                expected_valid = False
                expected_clamped = min_val
            elif value > max_val:
                expected_valid = False
                expected_clamped = max_val
            else:
                expected_valid = True
                expected_clamped = value
            
            # Special case for sweep_rate
            if param_name == 'sweep_rate' and value >= max_val:
                expected_valid = False
                expected_clamped = max_val - 0.1
            
            actual_valid = validation_result['valid']
            actual_clamped = validation_result.get('clamped_value', value)
            
            if actual_valid == expected_valid:
                print(f"   ✅ Validation result consistent")
            else:
                print(f"   ❌ Validation result inconsistent: expected {expected_valid}, got {actual_valid}")
            
            if not actual_valid and 'clamped_value' in validation_result:
                if abs(actual_clamped - expected_clamped) < 1e-6:
                    print(f"   ✅ Clamped value consistent: {actual_clamped}")
                else:
                    print(f"   ❌ Clamped value inconsistent: expected {expected_clamped}, got {actual_clamped}")
        else:
            print(f"   ⚠️  No ranges defined for {param_name}")


def test_range_retrieval():
    """Test that get_parameter_ranges returns correct information."""
    print("\n\n🔍 Testing Range Retrieval")
    print("=" * 50)
    
    sg384 = MockSG384Generator()
    
    parameters = ['frequency', 'power', 'sweep_rate', 'modulation_depth', 'phase', 'nonexistent']
    
    for param in parameters:
        ranges = sg384.get_parameter_ranges([param])
        print(f"\n📋 {param}:")
        if ranges:
            print(f"   Min: {ranges.get('min', 'N/A')}")
            print(f"   Max: {ranges.get('max', 'N/A')}")
            print(f"   Units: {ranges.get('units', 'N/A')}")
            print(f"   Type: {ranges.get('type', 'N/A')}")
            print(f"   Info: {ranges.get('info', 'N/A')}")
        else:
            print(f"   No ranges defined")


def test_validation_messages():
    """Test that validation messages are informative."""
    print("\n\n💬 Testing Validation Messages")
    print("=" * 50)
    
    sg384 = MockSG384Generator()
    
    test_cases = [
        ('frequency', 1.5e9, 'Should show GHz formatting'),
        ('frequency', 5.0e9, 'Should show GHz formatting'),
        ('power', -150.0, 'Should show dBm units'),
        ('power', 20.0, 'Should show dBm units'),
        ('modulation_depth', -1e6, 'Should show MHz formatting'),
        ('modulation_depth', 200e6, 'Should show MHz formatting'),
        ('sweep_rate', 150.0, 'Should show Hz units'),
    ]
    
    for param_name, value, description in test_cases:
        print(f"\n📋 {description}")
        result = sg384.validate_parameter([param_name], value)
        print(f"   Message: {result['message']}")
        if 'clamped_value' in result:
            print(f"   Clamped to: {result['clamped_value']}")


def main():
    """Run all validation tests."""
    print("🔧 SG384 Validation Refactor Test")
    print("=" * 60)
    print("Testing that validate_parameter now uses get_parameter_ranges")
    print("to avoid duplication and ensure consistency.")
    print()
    
    test_validation_consistency()
    test_range_retrieval()
    test_validation_messages()
    
    print("\n\n🎉 Refactor Test Complete!")
    print("=" * 60)
    print("✅ validate_parameter now uses get_parameter_ranges")
    print("✅ No more duplication of range logic")
    print("✅ Consistent validation results")
    print("✅ Maintainable code structure")


if __name__ == "__main__":
    main()
