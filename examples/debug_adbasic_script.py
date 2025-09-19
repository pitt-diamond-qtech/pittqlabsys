#!/usr/bin/env python3
"""
ADbasic Script Debugger

Systematically tests different parts of ADbasic functionality to identify
what's causing the ODMR script to crash during initialization.

Usage:
    python debug_adbasic_script.py --real-hardware
"""

import argparse
import sys
import time
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent / '..'))

from src.core.device_config import load_devices_from_config


def create_test_scripts():
    """Create various test ADbasic scripts."""
    
    # Test 1: Minimal script (no hardware)
    minimal_script = """'<ADbasic Header, Headerversion 001.001>
' Process_Number                 = 1
' Initial_Processdelay           = 1000000
' Eventsource                    = Timer
' Control_long_Delays_for_Stop   = No
' Priority                       = High
' Version                        = 1
' ADbasic_Version                = 6.3.0
' Optimize                       = Yes
' Optimize_Level                 = 1
' Stacksize                      = 1000
'<Header End>

#Include ADwinGoldII.inc

' Internal variables only (Par_n and FPar_n are reserved by ADbasic)
' No Dim statements needed for Par_n or FPar_n variables

Init:
  Par_20 = 1
  Par_10 = 0
  Par_20 = 0
  Par_25 = 0

Event:
  Par_25 = Par_25 + 1
  Goto Event

Finish:
  End"""
    counter_script = """'<ADbasic Header, Headerversion 001.001>
' Process_Number                 = 1
' Initial_Processdelay           = 1000000
' Eventsource                    = Timer
' Control_long_Delays_for_Stop   = No
' Priority                       = High
' Version                        = 1
' ADbasic_Version                = 6.3.0
' Optimize                       = Yes
' Optimize_Level                 = 1
' Stacksize                      = 1000
'<Header End>

#Include ADwinGoldII.inc

' Internal variables only (Par_n and FPar_n are reserved by ADbasic)
' No Dim statements needed for Par_n or FPar_n variables

Init:
  ' Test counter setup
  Cnt_Enable(0)
  Cnt_Clear(0001b)
  Cnt_Mode(1, 00000100b)
  Cnt_SE_Diff(0000b)
  Cnt_Enable(0001b)
  Par_20 = 1
  Par_10 = 0
  Par_20 = 0
  Par_25 = 0

Event:
  Par_25 = Par_25 + 1
  Goto Event

Finish:
  End"""


    # Test 3: DAC setup only
    dac_script = """'<ADbasic Header, Headerversion 001.001>
' Process_Number                 = 1
' Initial_Processdelay           = 1000000
' Eventsource                    = Timer
' Control_long_Delays_for_Stop   = No
' Priority                       = High
' Version                        = 1
' ADbasic_Version                = 6.3.0
' Optimize                       = Yes
' Optimize_Level                 = 1
' Stacksize                      = 1000
'<Header End>

#Include ADwinGoldII.inc

' Internal variables only (Par_n and FPar_n are reserved by ADbasic)
' No Dim statements needed for Par_n or FPar_n variables

Init:
  ' Test DAC setup
  Write_DAC(1, 32768)  ' Mid-range value
  Start_DAC()
  Par_20 = 1
  Par_10 = 0
  Par_20 = 0
  Par_25 = 0

Event:
  Par_25 = Par_25 + 1
  Goto Event

Finish:
  End"""

    # Test 4: Both counter and DAC
    combined_script = """'<ADbasic Header, Headerversion 001.001>
' Process_Number                 = 1
' Initial_Processdelay           = 1000000
' Eventsource                    = Timer
' Control_long_Delays_for_Stop   = No
' Priority                       = High
' Version                        = 1
' ADbasic_Version                = 6.3.0
' Optimize                       = Yes
' Optimize_Level                 = 1
' Stacksize                      = 1000
'<Header End>

#Include ADwinGoldII.inc

' Internal variables only (Par_n and FPar_n are reserved by ADbasic)
' No Dim statements needed for Par_n or FPar_n variables

Init:
  ' Test both counter and DAC
  Cnt_Enable(0)
  Cnt_Clear(0001b)
  Cnt_Mode(1, 00000100b)
  Cnt_SE_Diff(0000b)
  Cnt_Enable(0001b)
  
  Write_DAC(1, 32768)
  Start_DAC()
  
  Par_20 = 1
  Par_10 = 0
  Par_20 = 0
  Par_25 = 0

Event:
  Par_25 = Par_25 + 1
  Goto Event

Finish:
  End"""

    # Write all test scripts
    scripts = {
        'Minimal_Test.bas': minimal_script,
        'Counter_Test.bas': counter_script,
        'DAC_Test.bas': dac_script,
        'Combined_Test.bas': combined_script
    }
    
    # Also check for existing test scripts
    existing_scripts = ['Simple_Test.bas', 'ODMR_Minimal_Test.bas']
    for script_name in existing_scripts:
        script_path = Path("src/Controller/binary_files/ADbasic") / script_name
        if script_path.exists():
            print(f"✅ Found existing script: {script_name}")
        else:
            print(f"⚠️  Existing script not found: {script_name}")
    
    # Add existing scripts to the list for testing
    all_scripts = list(scripts.keys()) + existing_scripts
    
    for filename, content in scripts.items():
        script_path = Path("src/Controller/binary_files/ADbasic") / filename
        with open(script_path, 'w') as f:
            f.write(content)
        print(f"✅ Created {filename}")
    
    print("\n📋 COMPILATION REQUIRED:")
    print("=" * 50)
    print("You need to compile these .bas files to .TB1 files using ADbasic compiler:")
    for filename in all_scripts:
        bas_name = filename
        tb1_name = filename.replace('.bas', '.TB1')
        print(f"  {bas_name} → {tb1_name}")
    print("\nAfter compilation, run this script again to test the .TB1 files.")
    
    return all_scripts


def test_script(adwin, script_name, description):
    """Test a specific ADbasic script."""
    print(f"\n🧪 Testing {description}")
    print("=" * 50)
    
    script_path = Path(f"src/Controller/binary_files/ADbasic/{script_name}")
    tb1_path = script_path.with_suffix('.TB1')
    
    print(f"📁 Script: {script_name}")
    print(f"📁 Binary: {tb1_path}")
    print(f"📁 Binary exists: {tb1_path.exists()}")
    
    if not tb1_path.exists():
        print(f"❌ Binary file not found: {tb1_path}")
        print("   Please compile the .bas file to .TB1 first using ADbasic compiler")
        print(f"   Compile: {script_path} → {tb1_path}")
        return False
    
    try:
        # Stop any existing process
        adwin.stop_process(1)
        time.sleep(0.1)
        adwin.clear_process(1)
        
        # Load the script
        adwin.update({'process_1': {'load': str(tb1_path)}})
        print("✅ Script loaded")
        
        # Check status after loading
        status = adwin.get_process_status(1)
        print(f"📊 Status after load: {status}")
        
        # Try to start the process
        adwin.start_process(1)
        print("✅ Start command sent")
        
        # Check status after starting
        status = adwin.get_process_status(1)
        print(f"📊 Status after start: {status}")
        
        if status == "Running":
            print("✅ Process is running!")
            
            # Test parameter reading
            try:
                par_25 = adwin.get_int_var(25)
                print(f"✅ Par_25 (event counter): {par_25}")
                
                # Wait a moment and check again
                time.sleep(0.5)
                par_25_new = adwin.get_int_var(25)
                print(f"✅ Par_25 after 0.5s: {par_25_new}")
                
                if par_25_new > par_25:
                    print("✅ Event counter is incrementing - script is working!")
                    return True
                else:
                    print("⚠️  Event counter not incrementing")
                    return False
                    
            except Exception as e:
                print(f"❌ Error reading parameters: {e}")
                return False
        else:
            print(f"❌ Process not running: {status}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing script: {e}")
        return False


def debug_adbasic_scripts(use_real_hardware=False, config_path=None):
    """Main debug function."""
    print("\n" + "="*60)
    print("ADBASIC SCRIPT DEBUGGER")
    print("="*60)
    
    if use_real_hardware:
        print("🔧 Loading real hardware...")
        try:
            if config_path is None:
                config_path = Path("src/config.json")
            else:
                config_path = Path(config_path)
            
            loaded_devices, failed_devices = load_devices_from_config(config_path)
            adwin = loaded_devices['adwin']
            print(f"✅ Adwin loaded: {type(adwin)}")
            print(f"✅ Connected: {adwin.is_connected}")
            
        except Exception as e:
            print(f"❌ Failed to load hardware: {e}")
            return False
    else:
        print("❌ Mock hardware not implemented for this debugger")
        return False
    
    # Create test scripts
    print("\n📝 Creating test scripts...")
    script_names = create_test_scripts()
    
    # Check which scripts are compiled
    print("\n🔍 Checking compiled scripts...")
    compiled_scripts = []
    for script_name in script_names:
        tb1_name = script_name.replace('.bas', '.TB1')
        tb1_path = Path("src/Controller/binary_files/ADbasic") / tb1_name
        if tb1_path.exists():
            compiled_scripts.append(script_name)
            print(f"✅ {tb1_name} - Ready to test")
        else:
            print(f"⏳ {tb1_name} - Not compiled yet")
    
    if not compiled_scripts:
        print("\n❌ No compiled scripts found!")
        print("Please compile the .bas files to .TB1 files using ADbasic compiler first.")
        return False
    
    # Test only the compiled scripts
    print(f"\n🧪 Testing {len(compiled_scripts)} compiled scripts...")
    results = {}
    
    for script_name in compiled_scripts:
        description = script_name.replace('.bas', '').replace('_', ' ')
        results[script_name] = test_script(adwin, script_name, description)
        
        # Stop the process before testing the next one
        try:
            adwin.stop_process(1)
            adwin.clear_process(1)
        except:
            pass
    
    # Summary
    print("\n📋 DEBUG SUMMARY")
    print("=" * 50)
    
    for script_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {script_name}")
    
    # Analysis
    print("\n🔍 ANALYSIS:")
    
    # Test basic functionality
    basic_working = (results.get('Simple_Test.bas', False) or 
                    results.get('Minimal_Test.bas', False) or 
                    results.get('ODMR_Minimal_Test.bas', False))
    
    if basic_working:
        print("✅ Basic ADbasic functionality works")
        
        # Test hardware components
        if results.get('Counter_Test.bas', False):
            print("✅ Counter initialization works")
        else:
            print("❌ Counter initialization fails - this is likely the issue!")
            
        if results.get('DAC_Test.bas', False):
            print("✅ DAC initialization works")
        else:
            print("❌ DAC initialization fails")
            
        if results.get('Combined_Test.bas', False):
            print("✅ Combined counter + DAC works")
        else:
            print("❌ Combined counter + DAC fails")
            
        # Test existing scripts
        if results.get('Simple_Test.bas', False):
            print("✅ Simple_Test.bas works - basic parameter loop")
        if results.get('ODMR_Minimal_Test.bas', False):
            print("✅ ODMR_Minimal_Test.bas works - simulated ODMR sweep")
    else:
        print("❌ Basic ADbasic functionality fails - fundamental issue")
    
    # Cleanup
    try:
        adwin.stop_process(1)
        adwin.clear_process(1)
    except:
        pass
    
    return any(results.values())


def write_scripts_only():
    """Write test scripts without testing them."""
    print("\n" + "="*60)
    print("ADBASIC SCRIPT WRITER")
    print("="*60)
    
    print("📝 Creating test scripts...")
    script_names = create_test_scripts()
    
    print(f"\n✅ Created {len(script_names)} test scripts!")
    print("\nNext steps:")
    print("1. Compile the .bas files to .TB1 files using ADbasic compiler")
    print("2. Run: python debug_adbasic_script.py --run-real-hardware")
    
    return True


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Debug ADbasic Scripts')
    parser.add_argument('--write-scripts', action='store_true',
                       help='Write test scripts only (no testing)')
    parser.add_argument('--run-real-hardware', action='store_true',
                       help='Test compiled scripts with real hardware')
    parser.add_argument('--config', type=str, default=None,
                       help='Path to config.json file')
    
    args = parser.parse_args()
    
    # Check for conflicting arguments
    if args.write_scripts and args.run_real_hardware:
        print("❌ Error: Cannot use --write-scripts and --run-real-hardware together")
        print("   Use --write-scripts first, then --run-real-hardware")
        return 1
    
    if not args.write_scripts and not args.run_real_hardware:
        print("❌ Error: Must specify either --write-scripts or --run-real-hardware")
        print("   Use --write-scripts to create test scripts")
        print("   Use --run-real-hardware to test compiled scripts")
        return 1
    
    if args.write_scripts:
        print("🎯 ADbasic Script Writer")
        success = write_scripts_only()
    elif args.run_real_hardware:
        print("🎯 ADbasic Script Debugger")
        print("🔧 Hardware mode: Real")
        success = debug_adbasic_scripts(True, args.config)
    
    if success:
        print("\n✅ Operation completed!")
    else:
        print("\n❌ Operation failed!")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
