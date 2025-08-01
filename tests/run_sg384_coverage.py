#!/usr/bin/env python3
"""
Simple script to generate coverage for SG384 module.
This script directly imports and uses the SG384 class.
"""

import sys
import os
from unittest.mock import patch

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Import the SG384 module
from Controller.sg384 import SG384Generator


def main():
    """Main function to test SG384 functionality and generate coverage."""
    
    print("Testing SG384 module...")
    
    # Mock both _query and _send methods to avoid connection issues
    with patch('Controller.sg384.SG384Generator._query', return_value="Stanford Research Systems,SG384,12345,1.0"), \
         patch('Controller.sg384.SG384Generator._send'):
        
        # Create instance with minimal settings
        settings = {
            'connection_type': 'LAN',
            'ip_address': '127.0.0.1',
            'port': 5025,
        }
        
        # Create SG384 instance
        sg384 = SG384Generator(settings=settings)
        
        print("✓ SG384 instance created successfully")
        
        # Test parameter mapping
        assert sg384._param_to_internal('frequency') == 'FREQ'
        assert sg384._param_to_internal('amplitude') == 'AMPR'
        print("✓ Parameter mapping works")
        
        # Test modulation type mapping
        assert sg384._mod_type_to_internal('AM') == 0
        assert sg384._mod_type_to_internal('FM') == 1
        assert sg384._internal_to_mod_type(0) == 'AM'
        assert sg384._internal_to_mod_type(1) == 'FM'
        print("✓ Modulation type mapping works")
        
        # Test modulation function mapping
        assert sg384._mod_func_to_internal('Sine') == 0
        assert sg384._mod_func_to_internal('Square') == 3
        assert sg384._internal_to_mod_func(0) == 'Sine'
        assert sg384._internal_to_mod_func(3) == 'Square'
        print("✓ Modulation function mapping works")
        
        # Test pulse modulation function mapping
        assert sg384._pulse_mod_func_to_internal('Square') == 3
        assert sg384._pulse_mod_func_to_internal('External') == 5
        assert sg384._internal_to_pulse_mod_func(3) == 'Square'
        assert sg384._internal_to_pulse_mod_func(5) == 'External'
        print("✓ Pulse modulation function mapping works")
        
        # Test dispatch update
        test_settings = {'frequency': 3.0e9, 'power': -5.0}
        sg384._dispatch_update(test_settings)
        print("✓ Dispatch update works")
        
        # Test read probes
        sg384._query = lambda cmd: '1' if 'ENBR' in cmd else '0'
        assert sg384.read_probes('enable_output') is True
        print("✓ Read probes works")
        
        print("\n🎉 All SG384 functionality tests passed!")


if __name__ == '__main__':
    main() 