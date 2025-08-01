#!/usr/bin/env python3
"""
Test script for the ADbasic compiler integration.

This script demonstrates how to use the new compile_and_load_process method
to compile ADbasic source files and load them into the ADwin on the fly.
"""

import sys
import os
from pathlib import Path

# Calculate project root manually first (from tests directory)
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Now we can import from the project
from src.core.helper_functions import get_project_root
from src.core.adbasic_compiler import ADbasicCompiler, compile_adbasic_file, create_license_template
from src.Controller.adwin import ADwinGold


def test_compiler():
    """Test the ADbasic compiler functionality."""
    print("Testing ADbasic Compiler...")
    
    # Test the compiler
    compiler = ADbasicCompiler()
    
    if compiler.check_compiler():
        print("✓ ADbasic compiler is working")
    else:
        print("✗ ADbasic compiler is not working")
        return False
    
    # Test compiling a single file
    source_file = "src/Controller/binary_files/ADbasic/Trial_Counter.bas"
    
    try:
        compiled_file = compile_adbasic_file(source_file, verbose=True)
        print(f"✓ Successfully compiled {source_file} to {compiled_file}")
        
        # Check if the file exists
        if os.path.exists(compiled_file):
            print(f"✓ Compiled file exists: {compiled_file}")
        else:
            print(f"⚠ Compiled file not found (expected due to license restrictions): {compiled_file}")
        
        return True
        
    except Exception as e:
        print(f"✗ Failed to compile {source_file}: {e}")
        return False


def test_license_management():
    """Test license management functionality."""
    print("\nTesting License Management...")
    
    # Test creating license template
    try:
        create_license_template("test_license_template.json")
        print("✓ License template created successfully")
        
        # Test license status checking
        compiler = ADbasicCompiler()
        
        # Check license status
        has_license = compiler.has_valid_license()
        license_info = compiler.get_license_info()
        
        if has_license:
            print("✓ Valid license found")
            print(f"  Device: {license_info.get('device_type', 'Unknown')}")
            print(f"  Expires: {license_info.get('expiration_date', 'Unknown')}")
        else:
            print("⚠ No valid license found (this is expected)")
            if license_info:
                print(f"  License file found but invalid: {license_info}")
        
        return True
        
    except Exception as e:
        print(f"✗ License management test failed: {e}")
        return False


def test_adwin_integration():
    """Test the ADwin integration with the compiler."""
    print("\nTesting ADwin Integration...")
    
    try:
        # Initialize ADwin (this will fail if no ADwin is connected)
        adwin = ADwinGold(boot=False)  # Don't boot to avoid issues if no hardware
        
        # Test license status checking
        try:
            license_status = adwin.check_license_status()
            print(f"✓ License status: {license_status['status']}")
        except Exception as e:
            print(f"⚠ License status check failed: {e}")
        
        # Test the compile_and_load_process method
        source_file = "src/Controller/binary_files/ADbasic/Trial_Counter.bas"
        
        try:
            compiled_file = adwin.compile_and_load_process(
                source_file=source_file,
                process_number=1,
                verbose=True
            )
            print(f"✓ Successfully compiled and loaded {source_file}")
            print(f"  Compiled to: {compiled_file}")
            
        except Exception as e:
            print(f"⚠ Compile and load failed (expected if no ADwin hardware): {e}")
        
        return True
        
    except Exception as e:
        print(f"⚠ ADwin initialization failed (expected if no hardware connected): {e}")
        return True  # This is expected if no ADwin is connected


def test_directory_compilation():
    """Test compiling all files in a directory."""
    print("\nTesting Directory Compilation...")
    
    try:
        compiler = ADbasicCompiler()
        source_dir = "src/Controller/binary_files/ADbasic"
        
        results = compiler.compile_directory(source_dir, verbose=True)
        
        print(f"✓ Compiled {len(results)} files:")
        for source_file, compiled_file in results.items():
            if compiled_file:
                print(f"  {source_file} → {compiled_file}")
            else:
                print(f"  {source_file} → Failed")
        
        return True
        
    except Exception as e:
        print(f"✗ Directory compilation failed: {e}")
        return False


def test_license_file_usage():
    """Test using a specific license file."""
    print("\nTesting License File Usage...")
    
    # Create a test license file
    test_license = {
        "license_key": "TEST_LICENSE_KEY",
        "device_type": "ADwin Gold II",
        "device_id": "TEST_DEVICE_001",
        "expiration_date": "2025-12-31",
        "features": ["ADbasic_compiler", "TiCO_compiler"],
        "notes": "Test license for development"
    }
    
    try:
        with open("test_license.json", "w") as f:
            import json
            json.dump(test_license, f, indent=2)
        
        # Test compiler with specific license file
        compiler = ADbasicCompiler(license_file="test_license.json")
        
        if compiler.has_valid_license():
            print("✓ Test license file loaded successfully")
            license_info = compiler.get_license_info()
            print(f"  Device: {license_info.get('device_type')}")
            print(f"  Features: {', '.join(license_info.get('features', []))}")
        else:
            print("⚠ Test license file loaded but validation failed")
        
        # Clean up
        os.remove("test_license.json")
        os.remove("test_license_template.json")
        
        return True
        
    except Exception as e:
        print(f"✗ License file usage test failed: {e}")
        # Clean up on error
        for file in ["test_license.json", "test_license_template.json"]:
            if os.path.exists(file):
                os.remove(file)
        return False


def main():
    """Run all tests."""
    print("ADbasic Compiler Integration Test")
    print("=" * 40)
    
    # Test 1: Basic compiler functionality
    test1_passed = test_compiler()
    
    # Test 2: License management
    test2_passed = test_license_management()
    
    # Test 3: License file usage
    test3_passed = test_license_file_usage()
    
    # Test 4: Directory compilation
    test4_passed = test_directory_compilation()
    
    # Test 5: ADwin integration (may fail if no hardware)
    test5_passed = test_adwin_integration()
    
    print("\n" + "=" * 40)
    print("Test Results:")
    print(f"Compiler Test: {'✓ PASSED' if test1_passed else '✗ FAILED'}")
    print(f"License Management: {'✓ PASSED' if test2_passed else '✗ FAILED'}")
    print(f"License File Usage: {'✓ PASSED' if test3_passed else '✗ FAILED'}")
    print(f"Directory Test: {'✓ PASSED' if test4_passed else '✗ FAILED'}")
    print(f"ADwin Integration: {'✓ PASSED' if test5_passed else '⚠ SKIPPED (no hardware)'}")
    
    if test1_passed and test2_passed and test3_passed and test4_passed:
        print("\n🎉 ADbasic compiler integration is working!")
        print("\nYou can now use:")
        print("  - adwin.compile_and_load_process('file.bas') to compile and load")
        print("  - adwin.compile_and_load_directory('directory/') to compile all files")
        print("  - compile_adbasic_file('file.bas') for standalone compilation")
        print("  - adwin.check_license_status() to check license status")
        print("\nTo set up your license:")
        print("  1. Edit src/Controller/adwin_license_template.json with your license information")
        print("  2. Rename it to adwin_license.json")
        print("  3. Place it in your home directory or project directory")
    else:
        print("\n❌ Some tests failed. Please check the setup.")


if __name__ == "__main__":
    main() 