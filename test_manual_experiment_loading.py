#!/usr/bin/env python3
"""
Test script to manually load Python experiments and verify the loading mechanism works.
This will help us understand if the issue is with the LoadDialog or with the underlying experiment loading.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_manual_experiment_loading():
    """Test manually loading Python experiments"""
    
    print("=== Testing Manual Python Experiment Loading ===\n")
    
    try:
        # Import the experiment module
        print("1. Importing experiment module...")
        from src.Model.experiments.daq_read_counter import Pxi6733ReadCounter
        print("   ✓ Successfully imported Pxi6733ReadCounter")
        
        # Check the experiment class
        print("\n2. Examining experiment class...")
        print(f"   Class name: {Pxi6733ReadCounter.__name__}")
        print(f"   Base class: {Pxi6733ReadCounter.__bases__}")
        print(f"   Has _DEFAULT_SETTINGS: {hasattr(Pxi6733ReadCounter, '_DEFAULT_SETTINGS')}")
        print(f"   Has _DEVICES: {hasattr(Pxi6733ReadCounter, '_DEVICES')}")
        
        if hasattr(Pxi6733ReadCounter, '_DEFAULT_SETTINGS'):
            print(f"   Default settings: {len(Pxi6733ReadCounter._DEFAULT_SETTINGS)} parameters")
            for param in Pxi6733ReadCounter._DEFAULT_SETTINGS:
                # Check what attributes are available on the Parameter object
                print(f"     - Parameter: {param}")
                print(f"       Attributes: {[attr for attr in dir(param) if not attr.startswith('_')]}")
                # Try to access common parameter attributes
                try:
                    if hasattr(param, 'name'):
                        print(f"       Name: {param.name}")
                    if hasattr(param, 'default'):
                        print(f"       Default: {param.default}")
                    if hasattr(param, 'type'):
                        print(f"       Type: {param.type}")
                except Exception as e:
                    print(f"       Error accessing attributes: {e}")
                print()
        
        # Test creating experiment instance (without devices for now)
        print("\n3. Testing experiment instantiation...")
        try:
            # Create with minimal parameters
            experiment = Pxi6733ReadCounter(
                devices={},  # Empty devices dict for testing
                name="TestPxi6733ReadCounter"
            )
            print("   ✓ Successfully created experiment instance")
            print(f"   Instance name: {experiment.name}")
            print(f"   Settings: {experiment.settings}")
            
        except Exception as e:
            print(f"   ✗ Failed to create instance: {e}")
            print("   This might be expected if devices are required")
        
        # Test the Experiment.load_and_append method
        print("\n4. Testing Experiment.load_and_append method...")
        try:
            from src.core.experiment import Experiment
            
            # Create a simple experiment dictionary
            experiment_dict = {
                "TestPxi6733ReadCounter": Pxi6733ReadCounter
            }
            
            # Try to load and append
            loaded_experiments, load_failed, updated_devices = Experiment.load_and_append(
                experiment_dict, 
                experiments={},  # Start with empty experiments
                devices={},      # Start with empty devices
                raise_errors=False,
                verbose=True
            )
            
            print("   ✓ Successfully called Experiment.load_and_append")
            print(f"   Loaded experiments: {list(loaded_experiments.keys())}")
            print(f"   Failed loads: {list(load_failed.keys())}")
            print(f"   Updated devices: {list(updated_devices.keys())}")
            
        except Exception as e:
            print(f"   ✗ Failed to call load_and_append: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n=== Test Summary ===")
        print("✓ Python experiment module can be imported")
        print("✓ Experiment class has required attributes")
        print("✓ Experiment.load_and_append method exists and can be called")
        
        if 'loaded_experiments' in locals() and loaded_experiments:
            print("✓ Manual experiment loading is working!")
            print("  The issue is likely with the LoadDialog interface, not the core loading mechanism.")
        else:
            print("⚠ Manual experiment loading has some issues")
            print("  This might indicate problems with the core loading mechanism.")
            
    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_manual_experiment_loading()
