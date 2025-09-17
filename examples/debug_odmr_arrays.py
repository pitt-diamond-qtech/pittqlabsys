#!/usr/bin/env python3
"""
Debug ODMR Arrays Script

This script waits for a complete ODMR sweep and then reads all the data arrays
from the Adwin to verify step progression and data capture.

Usage:
    python debug_odmr_arrays.py --real-hardware
"""

import argparse
import sys
import time
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent / '..'))

from src.core.device_config import load_devices_from_config


def debug_odmr_arrays(use_real_hardware=False, config_path=None):
    """
    Debug the ODMR arrays by waiting for complete sweep and reading all data.
    
    Args:
        use_real_hardware (bool): Whether to use real hardware
        config_path (str): Path to config.json file
    """
    print("\n" + "="*60)
    print("ODMR ARRAYS DEBUG SESSION")
    print("="*60)
    
    if use_real_hardware:
        print("🔧 Loading real hardware...")
        try:
            if config_path is None:
                config_path = Path(__file__).parent.parent / "src" / "config.json"
            else:
                config_path = Path(config_path)
            
            loaded_devices, failed_devices = load_devices_from_config(config_path)
            
            if failed_devices:
                print(f"⚠️  Some devices failed to load: {list(failed_devices.keys())}")
                for device_name, error in failed_devices.items():
                    print(f"  - {device_name}: {error}")
            
            if not loaded_devices:
                print("❌ No devices loaded, falling back to mock hardware")
                return debug_mock_arrays()
            
            adwin = loaded_devices['adwin']
            print(f"✅ Adwin loaded: {type(adwin)}")
            print(f"✅ Connected: {adwin.is_connected}")
            
        except Exception as e:
            print(f"❌ Failed to load real hardware: {e}")
            return debug_mock_arrays()
    else:
        print("🔧 Using mock hardware...")
        return debug_mock_arrays()
    
    print("\n🔍 Starting array diagnostics...")
    
    # Use the compiled debug version for detailed diagnostics
    from src.core.adwin_helpers import get_adwin_binary_path
    
    try:
        # Stop any running process
        adwin.stop_process(1)
        time.sleep(0.1)
        adwin.clear_process(1)
        
        # Load the debug ODMR script (with detailed diagnostics)
        script_path = get_adwin_binary_path('ODMR_Sweep_Counter_Debug.TB1')
        print(f"📁 Loading debug ODMR script: {script_path}")
        adwin.update({'process_1': {'load': str(script_path)}})
        
        # Set up parameters for a complete sweep
        print("⚙️  Setting up test parameters...")
        adwin.set_int_var(2, 5)      # Par_2: Integration time (5 cycles = ~5ms)
        adwin.set_int_var(3, 10)     # Par_3: Number of steps (10 steps)
        adwin.set_int_var(11, 1)     # Par_11: Settle time (1 cycle = ~1ms)
        
        print("🚀 Starting counter process...")
        adwin.update({'process_1': {'running': True}})
        
        # Wait for sweep to complete (monitor Par_7 = sweep complete flag)
        print("\n⏳ Waiting for sweep to complete...")
        print("Monitoring Par_7 (sweep complete flag)...")
        
        start_time = time.time()
        timeout = 10  # 10 second timeout
        
        while time.time() - start_time < timeout:
            try:
                par_7 = adwin.get_int_var(7)    # Sweep complete flag
                par_9 = adwin.get_int_var(9)    # Sweep cycle
                par_16 = adwin.get_int_var(16)  # Total captured steps
                
                elapsed = time.time() - start_time
                print(f"  {elapsed:5.1f}s | Par_7={par_7} | Par_9={par_9} | Par_16={par_16}")
                
                if par_7 == 1:  # Sweep complete
                    print("✅ Sweep completed!")
                    break
                    
                time.sleep(0.1)  # Check every 100ms
                
            except Exception as e:
                print(f"❌ Error reading parameters: {e}")
                break
        else:
            print("⏰ Timeout waiting for sweep completion")
            return False
        
        # Read all the data arrays
        print("\n📊 Reading data arrays...")
        
        # Read the main data arrays using the correct method
        try:
            # Read arrays using read_probes with correct array types
            forward_counts = adwin.read_probes('int_array', 1, 20)  # Data_1: Forward sweep counts
            reverse_counts = adwin.read_probes('int_array', 2, 20)  # Data_2: Reverse sweep counts
            forward_voltages = adwin.read_probes('float_array', 3, 20)  # Data_3: Forward sweep voltages
            reverse_voltages = adwin.read_probes('float_array', 4, 20)  # Data_4: Reverse sweep voltages
            
            # Read the debug capture arrays
            step_indices = adwin.read_probes('int_array', 5, 20)    # Data_5: Step indices
            sweep_directions = adwin.read_probes('int_array', 6, 20)  # Data_6: Sweep directions
            integration_cycles = adwin.read_probes('int_array', 7, 20)  # Data_7: Integration cycles
            event_cycles = adwin.read_probes('int_array', 8, 20)    # Data_8: Event cycles
            
        except Exception as e:
            print(f"⚠️  Error reading arrays with read_probes: {e}")
            print("   Trying alternative method...")
            
            # Fallback: try reading individual elements
            forward_counts = []
            reverse_counts = []
            forward_voltages = []
            reverse_voltages = []
            step_indices = []
            sweep_directions = []
            integration_cycles = []
            event_cycles = []
            
            # Read first 20 elements of each array
            for i in range(20):
                try:
                    forward_counts.append(adwin.get_int_var(1 + i))
                    reverse_counts.append(adwin.get_int_var(1001 + i))
                    forward_voltages.append(adwin.get_float_var(1 + i))
                    reverse_voltages.append(adwin.get_float_var(1001 + i))
                    step_indices.append(adwin.get_int_var(2001 + i))
                    sweep_directions.append(adwin.get_int_var(3001 + i))
                    integration_cycles.append(adwin.get_int_var(4001 + i))
                    event_cycles.append(adwin.get_int_var(5001 + i))
                except:
                    break
        
        # Get final parameters
        total_captured = adwin.get_int_var(16)
        
        print(f"📊 Total captured steps: {total_captured}")
        print(f"📊 Forward counts array length: {len(forward_counts)}")
        print(f"📊 Reverse counts array length: {len(reverse_counts)}")
        print(f"📊 Forward voltages array length: {len(forward_voltages)}")
        print(f"📊 Reverse voltages array length: {len(reverse_voltages)}")
        print(f"📊 Step indices array length: {len(step_indices)}")
        print(f"📊 Sweep directions array length: {len(sweep_directions)}")
        
        # Analyze the captured data
        print("\n📋 Analysis of Captured Data:")
        print("=" * 50)
        
        if total_captured > 0:
            print(f"✅ Successfully captured {total_captured} steps")
            
            # Show first 20 captured steps
            print("\nFirst 20 captured steps:")
            print("Index | Step | Direction | Integration | Event")
            print("-" * 50)
            for i in range(min(20, total_captured)):
                step = step_indices[i] if i < len(step_indices) else 0
                direction = sweep_directions[i] if i < len(sweep_directions) else 0
                integration = integration_cycles[i] if i < len(integration_cycles) else 0
                event = event_cycles[i] if i < len(event_cycles) else 0
                print(f"{i:5d} | {step:4d} | {direction:9d} | {integration:11d} | {event:5d}")
            
            # Check for expected pattern
            print("\nPattern Analysis:")
            if total_captured >= 20:  # Should have 10 forward + 10 reverse steps
                print("✅ Captured enough steps for complete sweep")
                
                # Check forward sweep (first 10 steps)
                forward_steps = step_indices[:10]
                forward_dirs = sweep_directions[:10]
                print(f"Forward sweep steps: {forward_steps}")
                print(f"Forward sweep directions: {forward_dirs}")
                
                # Check reverse sweep (next 10 steps)
                if total_captured >= 20:
                    reverse_steps = step_indices[10:20]
                    reverse_dirs = sweep_directions[10:20]
                    print(f"Reverse sweep steps: {reverse_steps}")
                    print(f"Reverse sweep directions: {reverse_dirs}")
                
                # Verify step progression
                expected_forward = list(range(10))
                expected_reverse = list(range(10))
                
                if forward_steps == expected_forward:
                    print("✅ Forward sweep step progression correct (0,1,2,3,4,5,6,7,8,9)")
                else:
                    print(f"❌ Forward sweep step progression incorrect: {forward_steps}")
                
                if total_captured >= 20 and reverse_steps == expected_reverse:
                    print("✅ Reverse sweep step progression correct (0,1,2,3,4,5,6,7,8,9)")
                elif total_captured >= 20:
                    print(f"❌ Reverse sweep step progression incorrect: {reverse_steps}")
                
            else:
                print(f"⚠️  Only captured {total_captured} steps, expected 20 (10 forward + 10 reverse)")
        else:
            print("❌ No steps captured!")
        
        # Check data arrays
        print("\nData Array Analysis:")
        print(f"Forward counts: {forward_counts[:10]}...")
        print(f"Reverse counts: {reverse_counts[:10]}...")
        print(f"Forward voltages: {forward_voltages[:10]}...")
        print(f"Reverse voltages: {reverse_voltages[:10]}...")
        
        print("\n🛑 Stopping process...")
        adwin.update({'process_1': {'running': False}})
        adwin.stop_process(1)
        time.sleep(0.1)
        adwin.clear_process(1)
        
        return True
        
    except Exception as e:
        print(f"❌ Error during debug session: {e}")
        import traceback
        traceback.print_exc()
        return False


def debug_mock_arrays():
    """Debug with mock hardware."""
    print("🔧 Mock hardware debug not implemented yet")
    print("   (This would simulate the array behavior)")
    return True


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Debug ODMR Arrays')
    parser.add_argument('--real-hardware', action='store_true',
                       help='Use real hardware instead of mock hardware')
    parser.add_argument('--config', type=str, default=None,
                       help='Path to config.json file (default: src/config.json)')
    
    args = parser.parse_args()
    
    print("🎯 ODMR Arrays Debug Tool")
    print(f"🔧 Hardware mode: {'Real' if args.real_hardware else 'Mock'}")
    
    success = debug_odmr_arrays(args.real_hardware, args.config)
    
    if success:
        print("\n✅ Debug session completed!")
    else:
        print("\n❌ Debug session failed!")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
