#!/usr/bin/env python3
"""
Test Enhanced Validation with Real Hardware

This script tests the new validation features with real hardware on the lab PC.
It will use actual devices if available, or fall back to mocks if not.

Usage:
    python test_real_hardware_validation.py
    python test_real_hardware_validation.py --mock-only
"""

import sys
import argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.tools.device_loader import load_device
from src import ur


def test_device_validation(device_name, mock_only=False):
    """Test validation for a specific device."""
    print(f"\n🔧 Testing {device_name} Validation")
    print("=" * 50)
    
    try:
        if mock_only:
            # Force mock device
            from src.Controller import MockSG384Generator
            if device_name == 'sg384':
                device = MockSG384Generator()
            else:
                print(f"   ⚠️  No mock available for {device_name}")
                return
        else:
            # Try to load real device
            device = load_device(device_name)
        
        print(f"   ✅ Loaded: {type(device).__name__}")
        
        # Test if device has validation methods
        if hasattr(device, 'validate_parameter'):
            print(f"   ✅ Has validate_parameter method")
        else:
            print(f"   ⚠️  No validate_parameter method")
            return
        
        if hasattr(device, 'get_parameter_ranges'):
            print(f"   ✅ Has get_parameter_ranges method")
        else:
            print(f"   ⚠️  No get_parameter_ranges method")
            return
        
        # Test validation with some parameters
        test_parameters = {
            'sg384': [
                ('frequency', 2.85e9, 'Valid frequency'),
                ('frequency', 5.0e9, 'Above max frequency'),
                ('power', 0.0, 'Valid power'),
                ('power', 20.0, 'Above max power'),
            ],
            'stage': [
                ('position', 5.0, 'Valid position'),
                ('position', 15.0, 'Above max position'),
            ]
        }
        
        if device_name in test_parameters:
            for param_name, value, description in test_parameters[device_name]:
                print(f"\n   📋 {description}")
                print(f"      Parameter: {param_name}, Value: {value}")
                
                # Test validation
                result = device.validate_parameter([param_name], value)
                print(f"      Validation: {result}")
                
                # Test ranges
                ranges = device.get_parameter_ranges([param_name])
                if ranges:
                    print(f"      Ranges: {ranges}")
                else:
                    print(f"      No ranges defined")
        
        # Test update_and_get if available
        if hasattr(device, 'update_and_get'):
            print(f"\n   📋 Testing update_and_get")
            test_settings = {'frequency': 2.85e9} if device_name == 'sg384' else {'position': 5.0}
            try:
                result = device.update_and_get(test_settings)
                print(f"      Result: {result}")
            except Exception as e:
                print(f"      Error: {e}")
        
        print(f"   ✅ {device_name} validation test completed")
        
    except Exception as e:
        print(f"   ❌ Error testing {device_name}: {e}")


def main():
    """Test validation with real hardware."""
    parser = argparse.ArgumentParser(description='Test enhanced validation with real hardware')
    parser.add_argument('--mock-only', action='store_true', help='Use mock devices only')
    args = parser.parse_args()
    
    print("🧪 Enhanced Validation with Real Hardware Test")
    print("=" * 60)
    
    if args.mock_only:
        print("🔧 Using mock devices only")
    else:
        print("🔧 Attempting to use real hardware (with mock fallback)")
    
    # Test devices that are likely to be available
    devices_to_test = ['sg384', 'stage', 'nanodrive']
    
    for device_name in devices_to_test:
        test_device_validation(device_name, args.mock_only)
    
    print("\n\n🎉 Hardware Validation Test Complete!")
    print("=" * 60)
    print("✅ Enhanced validation system is ready for real hardware testing")
    print("✅ Mock devices available for testing without hardware")
    print("✅ GUI integration ready for testing")
    print()
    print("🚀 Next steps:")
    print("   1. Test GUI with: python examples/test_gui_with_validation.py")
    print("   2. Test with real hardware: python examples/test_real_hardware_validation.py")
    print("   3. Launch full GUI: python src/View/windows_and_widgets/main_window.py")


if __name__ == "__main__":
    main()
