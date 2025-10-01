#!/usr/bin/env python3
"""
ADwin Script Diagnostic Tool

This script helps diagnose issues with ADbasic scripts by:
1. Attempting to load the script
2. Checking compilation errors
3. Verifying basic functionality
4. Comparing with working debug version

Usage:
    python diagnose_adwin_script.py --real-hardware --script ODMR_Sweep_Counter.TB1
"""

import argparse
import sys
import time
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).parent / '..'))

from src.core.device_config import load_devices_from_config
from src.core.adwin_helpers import get_adwin_binary_path


def diagnose_adwin_script(use_real_hardware=False, config_path=None, script_name='ODMR_Sweep_Counter.TB1'):
    """
    Diagnose ADwin script loading and compilation issues.
    
    Args:
        use_real_hardware (bool): Use real hardware (required)
        config_path (str): Path to config.json
        script_name (str): Name of TB1 file to diagnose
        
    Returns:
        bool: True if diagnosis successful, False otherwise
    """
    print("\n" + "=" * 60)
    print(f"ADWIN SCRIPT DIAGNOSTIC: {script_name}")
    print("=" * 60)
    
    if not use_real_hardware:
        print("❌ This diagnostic requires real hardware (--real-hardware)")
        return False
    
    # Load ADwin device
    print("🔧 Loading ADwin hardware...")
    try:
        config_path = Path(config_path) if config_path else Path(__file__).parent.parent / "src" / "config.json"
        loaded_devices, failed_devices = load_devices_from_config(config_path)
        
        if not loaded_devices or 'adwin' not in loaded_devices:
            print("❌ No ADwin device loaded.")
            return False
        
        adwin = loaded_devices['adwin']
        print(f"✅ ADwin loaded: {type(adwin)}")
        print(f"✅ Connected: {adwin.is_connected}")
        
    except Exception as e:
        print(f"❌ Failed to load ADwin hardware: {e}")
        return False
    
    # Check if script file exists
    print(f"\n📁 Checking script file: {script_name}")
    try:
        script_path = get_adwin_binary_path(script_name)
        print(f"📁 Script path: {script_path}")
        
        if not script_path.exists():
            print(f"❌ Script file does not exist: {script_path}")
            return False
        else:
            print(f"✅ Script file exists")
            
    except Exception as e:
        print(f"❌ Error checking script file: {e}")
        return False
    
    # Stop and clear any existing process
    print("\n🧹 Cleaning up existing processes...")
    try:
        try:
            adwin.stop_process(1)
            time.sleep(0.1)
        except Exception:
            pass
        try:
            adwin.clear_process(1)
        except Exception:
            pass
        print("✅ Existing processes cleared")
    except Exception as e:
        print(f"⚠️  Error clearing processes: {e}")
    
    # Attempt to load the script
    print(f"\n📥 Attempting to load {script_name}...")
    try:
        adwin.update({'process_1': {'load': str(script_path)}})
        print("✅ Script loaded successfully")
    except Exception as e:
        print(f"❌ Failed to load script: {e}")
        print("   This usually indicates a compilation error in the ADbasic code")
        return False
    
    # Check if we can get basic information about the loaded script
    print("\n🔍 Checking loaded script information...")
    try:
        # Try to get process status
        try:
            process_status = adwin.get_process_status(1)
            print(f"   Process status: {process_status}")
        except Exception as e:
            print(f"   ⚠️  Could not get process status: {e}")
        
        # Try to read some basic parameters
        try:
            # Check if we can read any parameters
            par_80 = adwin.get_int_var(80)  # Signature
            print(f"   Par_80 (signature): {par_80}")
        except Exception as e:
            print(f"   ⚠️  Could not read Par_80: {e}")
        
        try:
            par_25 = adwin.get_int_var(25)  # Heartbeat
            print(f"   Par_25 (heartbeat): {par_25}")
        except Exception as e:
            print(f"   ⚠️  Could not read Par_25: {e}")
        
        try:
            par_71 = adwin.get_int_var(71)  # Processdelay
            print(f"   Par_71 (processdelay): {par_71}")
        except Exception as e:
            print(f"   ⚠️  Could not read Par_71: {e}")
            
    except Exception as e:
        print(f"❌ Error checking script information: {e}")
    
    # Try to start the process
    print("\n▶️  Attempting to start process...")
    try:
        adwin.start_process(1)
        time.sleep(0.2)  # Give more time for startup
        
        # Check process status after starting
        try:
            process_status = adwin.get_process_status(1)
            print(f"   Process status after start: {process_status}")
            
            if process_status == "Running":
                print("✅ Process started successfully!")
                
                # Check signature and processdelay
                try:
                    signature = adwin.get_int_var(80)
                    processdelay = adwin.get_int_var(71)
                    print(f"   Signature: {signature}")
                    print(f"   Processdelay: {processdelay}")
                    if signature == 7777:
                        print("✅ Correct signature detected!")
                    else:
                        print(f"⚠️  Unexpected signature: {signature}")
                except Exception as e:
                    print(f"   ⚠️  Could not read signature/processdelay: {e}")
                
                # Check debug parameters (Par_22, Par_23, Par_24, Par_72, Par_73)
                try:
                    par_22 = adwin.get_int_var(22)  # Current step index
                    par_23 = adwin.get_int_var(23)  # Current triangle position
                    par_24 = adwin.get_float_var(24)  # Current volts
                    par_72 = adwin.get_int_var(72)  # Calculated µs
                    par_73 = adwin.get_int_var(73)  # Calculated ticks
                    print(f"   Debug params - Step: {par_22}, Pos: {par_23}, Volts: {par_24:.3f}")
                    print(f"   Debug params - µs: {par_72}, Ticks: {par_73}")
                except Exception as e:
                    print(f"   ⚠️  Could not read debug parameters: {e}")
                
                # Check heartbeat and state
                try:
                    heartbeat = adwin.get_int_var(25)
                    state = adwin.get_int_var(26)
                    print(f"   Initial heartbeat: {heartbeat}")
                    print(f"   Initial state: {state}")
                    
                    # Wait a bit and check if heartbeat advances
                    time.sleep(0.5)
                    new_heartbeat = adwin.get_int_var(25)
                    new_state = adwin.get_int_var(26)
                    if new_heartbeat > heartbeat:
                        print(f"✅ Heartbeat advancing: {heartbeat} → {new_heartbeat}")
                    else:
                        print(f"⚠️  Heartbeat not advancing: {heartbeat}")
                    
                    if new_state != state:
                        print(f"✅ State changing: {state} → {new_state}")
                    else:
                        print(f"ℹ️  State stable: {state}")
                        
                except Exception as e:
                    print(f"   ⚠️  Could not check heartbeat/state: {e}")
                
            else:
                print(f"❌ Process failed to start! Status: {process_status}")
                return False
                
        except Exception as e:
            print(f"❌ Error checking process status: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Failed to start process: {e}")
        return False
    
    # Cleanup
    print("\n🧹 Cleaning up...")
    try:
        adwin.stop_process(1)
        time.sleep(0.1)
        adwin.clear_process(1)
        print("✅ Cleanup completed")
    except Exception as e:
        print(f"⚠️  Cleanup error: {e}")
    
    print("\n✅ Script diagnostic completed successfully!")
    return True


def main():
    parser = argparse.ArgumentParser(description='Diagnose ADwin Script Issues')
    parser.add_argument('--real-hardware', action='store_true', 
                       help='Use real hardware (required)')
    parser.add_argument('--config', type=str, default=None,
                       help='Path to config.json (default: src/config.json)')
    parser.add_argument('--script', type=str, default='ODMR_Sweep_Counter.TB1',
                       help='TB1 script name to diagnose (default: ODMR_Sweep_Counter.TB1)')
    
    args = parser.parse_args()
    
    print("🔍 ADwin Script Diagnostic Tool")
    print(f"📄 Script: {args.script}")
    print(f"🔧 Hardware mode: {'Real' if args.real_hardware else 'Mock'}")
    
    success = diagnose_adwin_script(
        use_real_hardware=args.real_hardware,
        config_path=args.config,
        script_name=args.script
    )
    
    if success:
        print("\n🎉 Script diagnostic passed!")
        return 0
    else:
        print("\n❌ Script diagnostic failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
