#!/usr/bin/env python3
"""
Setup script for AWG520 hardware connections.

This script helps you set up your lab-specific connection configuration
by copying the template and guiding you through customization.
"""

import json
import os
import shutil
from pathlib import Path

def setup_awg520_connections():
    """Set up AWG520 connection files for your lab."""
    
    print("🔧 AWG520 Connection Setup")
    print("=" * 50)
    
    # Define paths
    # __file__ is src/Controller/setup_awg520_connections.py
    # When run from project root, we need to go up two levels to get to project root
    project_root = Path(__file__).parent.parent.parent
    template_path = project_root / "src" / "Controller" / "awg520_connection.template.json"
    connection_path = project_root / "src" / "Controller" / "awg520_connection.json"
    
    # Check if template exists
    if not template_path.exists():
        print(f"❌ Template file not found: {template_path}")
        print("Please ensure you're running this from the project root directory.")
        return False
    
    # Check if connection file already exists
    if connection_path.exists():
        print(f"⚠️  Connection file already exists: {connection_path}")
        response = input("Do you want to overwrite it? (y/N): ").strip().lower()
        if response != 'y':
            print("Setup cancelled.")
            return False
    
    try:
        # Copy template to connection file
        shutil.copy2(template_path, connection_path)
        print(f"✅ Template copied to: {connection_path}")
        
        # Load the connection file for customization
        with open(connection_path, 'r') as f:
            connections = json.load(f)
        
        print("\n📋 Current Configuration:")
        print(f"  - Channels: {len(connections['awg520_connections']['channels'])}")
        print(f"  - Markers: {len(connections['awg520_connections']['markers'])}")
        print(f"  - Calibration delays: {len(connections['calibration_delays'])}")
        
        print("\n🔧 Next Steps:")
        print("1. Edit the connection file:")
        print(f"   {connection_path}")
        print("2. Update connection descriptions for your lab")
        print("3. Measure and set calibration delays")
        print("4. Verify physical connections match")
        
        print("\n📖 For experiment-specific connections:")
        print("   - Copy this file to your experiment directory")
        print("   - Rename to {experiment}_connection.json")
        print("   - Customize for your specific experiment needs")
        print("   - Example: src/Model/experiments/odmr_pulsed_connection.json")
        
        print("\n📖 For detailed instructions, see:")
        print("   docs/README_AWG520.md")
        
        # Show example of what to customize
        print("\n💡 Example Customizations:")
        print("   - Update 'connection' fields with your actual hardware names")
        print("   - Set 'calibration_delays' to measured values")
        print("   - Modify 'description' fields for clarity")
        print("   - Add/remove connections as needed")
        
        return True
        
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        return False

def validate_connection_file():
    """Validate the connection file format."""
    
    print("\n🔍 Validating Connection File")
    print("-" * 30)
    
    project_root = Path(__file__).parent.parent.parent
    connection_path = project_root / "src" / "Controller" / "awg520_connection.json"
    
    if not connection_path.exists():
        print("❌ Connection file not found. Run setup first.")
        return False
    
    try:
        with open(connection_path, 'r') as f:
            connections = json.load(f)
        
        # Basic validation
        required_sections = ['awg520_connections', 'calibration_delays', 'experiment_types']
        for section in required_sections:
            if section not in connections:
                print(f"❌ Missing required section: {section}")
                return False
        
        print("✅ Connection file format is valid")
        
        # Check for common issues
        if connections['calibration_delays'].get('laser_delay') == 50.0:
            print("⚠️  Using default laser_delay (50.0ns) - consider measuring your actual delay")
        
        if connections['calibration_delays'].get('iq_delay') == 30.0:
            print("⚠️  Using default iq_delay (30.0ns) - consider measuring your actual delay")
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON format: {e}")
        return False
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        return False

def main():
    """Main setup function."""
    
    print("🚀 AWG520 Hardware Connection Setup")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path("src/Controller/awg520_connection.template.json").exists():
        print("❌ Please run this script from the project root directory")
        print("   (where src/Controller/awg520_connection.template.json exists)")
        return
    
    # Run setup
    if setup_awg520_connections():
        print("\n" + "=" * 50)
        print("🎉 Setup completed successfully!")
        
        # Offer validation
        validate = input("\nWould you like to validate the connection file? (Y/n): ").strip().lower()
        if validate != 'n':
            validate_connection_file()
        
        print("\n📝 Remember:")
        print("   - The connection file is NOT tracked in git")
        print("   - Update delays based on your hardware measurements")
        print("   - Test with simple sequences before complex experiments")
        
    else:
        print("\n❌ Setup failed. Please check the error messages above.")

if __name__ == "__main__":
    main()
