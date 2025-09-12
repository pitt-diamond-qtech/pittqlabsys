#!/usr/bin/env python3
"""
Adwin Sweep Test Script

This script tests the Adwin sweep functionality independently to diagnose
data collection issues in the ODMR sweep experiment.

Usage:
    python test_adwin_sweep.py --real-hardware    # Use real hardware
    python test_adwin_sweep.py --mock-hardware    # Use mock hardware (default)
    python test_adwin_sweep.py --help             # Show help
"""

import argparse
import sys
import time
import numpy as np
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent / '..'))

from src.core.adwin_helpers import setup_adwin_for_sweep_odmr, read_adwin_sweep_odmr_data


def create_adwin_device(use_real_hardware=False, config_path=None, debug=False):
    """Create Adwin device instance."""
    if use_real_hardware:
        print("Using real Adwin hardware...")
        try:
            from src.core.device_config import load_devices_from_config
            
            # Use provided config path or default
            if config_path is None:
                config_path = Path(__file__).parent.parent / "src" / "config.json"
            else:
                config_path = Path(config_path)
            
            if debug:
                print(f"🔍 Debug: Loading devices from config: {config_path}")
                print(f"🔍 Debug: Config file exists: {config_path.exists()}")
            
            # Load devices from config
            loaded_devices, failed_devices = load_devices_from_config(config_path)
            
            if 'adwin' not in loaded_devices:
                print("❌ Adwin device not found in loaded devices")
                return None
            
            adwin = loaded_devices['adwin']
            print(f"✅ Real Adwin hardware loaded successfully")
            return adwin
            
        except Exception as e:
            print(f"❌ Failed to load real Adwin hardware: {e}")
            return None
    else:
        print("Using mock Adwin hardware...")
        try:
            from src.Controller import MockAdwinGoldDevice
            adwin = MockAdwinGoldDevice()
            print("✅ Mock Adwin hardware loaded successfully")
            return adwin
        except Exception as e:
            print(f"❌ Failed to load mock Adwin hardware: {e}")
            return None


def test_adwin_sweep_setup(adwin, num_steps=100, integration_time_ms=5.0, settle_time_ms=1.0, bidirectional=True):
    """Test Adwin sweep setup."""
    print(f"\n🔧 Testing Adwin sweep setup...")
    print(f"   Steps: {num_steps}")
    print(f"   Integration time: {integration_time_ms} ms")
    print(f"   Settle time: {settle_time_ms} ms")
    print(f"   Bidirectional: {bidirectional}")
    
    try:
        # Setup Adwin for sweep
        setup_adwin_for_sweep_odmr(
            adwin,
            integration_time_ms,
            settle_time_ms,
            num_steps,
            bidirectional
        )
        print("✅ Adwin sweep setup completed")
        
        # Check process status
        try:
            process_status = adwin.get_process_status("Process_1")
            print(f"🔍 Process_1 status: {process_status}")
        except Exception as e:
            print(f"⚠️  Could not check process status: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Adwin sweep setup failed: {e}")
        return False


def test_adwin_sweep_execution(adwin, sweep_time=2.0):
    """Test Adwin sweep execution."""
    print(f"\n🚀 Testing Adwin sweep execution...")
    print(f"   Sweep time: {sweep_time} s")
    
    try:
        # Start the process
        adwin.start_process("Process_1")
        print("✅ Adwin process started")
        
        # Check initial status
        initial_data = read_adwin_sweep_odmr_data(adwin)
        print(f"🔍 Initial Adwin data: {initial_data}")
        
        # Wait for sweep completion
        print(f"⏱️  Waiting {sweep_time}s for sweep completion...")
        time.sleep(sweep_time)
        
        # For mock Adwin, simulate sweep completion
        if hasattr(adwin, 'simulate_sweep_completion'):
            adwin.simulate_sweep_completion(100)  # Use default 100 steps
        
        # Check status during wait
        mid_data = read_adwin_sweep_odmr_data(adwin)
        print(f"🔍 Mid-sweep Adwin data: {mid_data}")
        
        # Stop the process
        adwin.stop_process("Process_1")
        print("✅ Adwin process stopped")
        
        # Check final data
        final_data = read_adwin_sweep_odmr_data(adwin)
        print(f"🔍 Final Adwin data: {final_data}")
        
        # Analyze results
        print(f"\n📊 Sweep Analysis:")
        print(f"   Sweep complete: {final_data.get('sweep_complete', 'Unknown')}")
        print(f"   Data ready: {final_data.get('data_ready', 'Unknown')}")
        print(f"   Step index: {final_data.get('step_index', 'Unknown')}")
        print(f"   Sweep cycle: {final_data.get('sweep_cycle', 'Unknown')}")
        print(f"   Total counts: {final_data.get('total_counts', 'Unknown')}")
        
        # Check data arrays
        forward_counts = final_data.get('forward_counts')
        reverse_counts = final_data.get('reverse_counts')
        forward_voltages = final_data.get('forward_voltages')
        reverse_voltages = final_data.get('reverse_voltages')
        
        if forward_counts is not None:
            print(f"   Forward counts: {len(forward_counts)} points, range: {np.min(forward_counts):.1f} - {np.max(forward_counts):.1f}")
        else:
            print(f"   Forward counts: None")
            
        if reverse_counts is not None:
            print(f"   Reverse counts: {len(reverse_counts)} points, range: {np.min(reverse_counts):.1f} - {np.max(reverse_counts):.1f}")
        else:
            print(f"   Reverse counts: None")
            
        if forward_voltages is not None:
            print(f"   Forward voltages: {len(forward_voltages)} points, range: {np.min(forward_voltages):.3f} - {np.max(forward_voltages):.3f} V")
        else:
            print(f"   Forward voltages: None")
            
        if reverse_voltages is not None:
            print(f"   Reverse voltages: {len(reverse_voltages)} points, range: {np.min(reverse_voltages):.3f} - {np.max(reverse_voltages):.3f} V")
        else:
            print(f"   Reverse voltages: None")
        
        return final_data
        
    except Exception as e:
        print(f"❌ Adwin sweep execution failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_adwin_parameters(adwin):
    """Test Adwin parameter reading/writing."""
    print(f"\n🔧 Testing Adwin parameters...")
    
    try:
        # Test reading some parameters
        print("📖 Reading Adwin parameters...")
        
        # Try to read some common parameters
        for param_num in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]:
            try:
                value = adwin.get_int_var(param_num)
                print(f"   Par_{param_num}: {value}")
            except Exception as e:
                print(f"   Par_{param_num}: Error - {e}")
        
        # Test setting some parameters
        print("📝 Testing parameter setting...")
        try:
            adwin.set_int_var(2, 5000)  # Integration time
            adwin.set_int_var(3, 100)   # Number of steps
            adwin.set_int_var(5, 1)     # Bidirectional
            print("✅ Parameters set successfully")
        except Exception as e:
            print(f"⚠️  Parameter setting failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Adwin parameter test failed: {e}")
        return False


def main():
    """Main function to run the Adwin test."""
    parser = argparse.ArgumentParser(description='Test Adwin Sweep Functionality')
    parser.add_argument('--real-hardware', action='store_true', 
                       help='Use real hardware instead of mock hardware')
    parser.add_argument('--mock-hardware', action='store_true', 
                       help='Use mock hardware (default)')
    parser.add_argument('--config', type=str, default=None,
                       help='Path to config.json file (default: src/config.json)')
    parser.add_argument('--debug', action='store_true',
                       help='Show detailed debug information')
    parser.add_argument('--sweep-time', type=float, default=2.0,
                       help='Sweep time in seconds (default: 2.0)')
    parser.add_argument('--num-steps', type=int, default=100,
                       help='Number of steps (default: 100)')
    parser.add_argument('--integration-time', type=float, default=5.0,
                       help='Integration time in ms (default: 5.0)')
    parser.add_argument('--settle-time', type=float, default=1.0,
                       help='Settle time in ms (default: 1.0)')
    parser.add_argument('--no-bidirectional', action='store_true',
                       help='Disable bidirectional sweeps')
    
    args = parser.parse_args()
    
    # Determine hardware mode
    use_real_hardware = args.real_hardware
    bidirectional = not args.no_bidirectional
    
    print("🎯 Adwin Sweep Test")
    print(f"🔧 Hardware mode: {'Real' if use_real_hardware else 'Mock'}")
    print(f"🔄 Bidirectional: {bidirectional}")
    print(f"⏱️  Sweep time: {args.sweep_time} s")
    print(f"📊 Steps: {args.num_steps}")
    print(f"⏱️  Integration time: {args.integration_time} ms")
    print(f"⏱️  Settle time: {args.settle_time} ms")
    
    # Create Adwin device
    adwin = create_adwin_device(use_real_hardware, args.config, args.debug)
    if not adwin:
        print("\n❌ Failed to create Adwin device!")
        return 1
    
    # Test Adwin parameters
    if not test_adwin_parameters(adwin):
        print("\n❌ Adwin parameter test failed!")
        return 1
    
    # Test Adwin sweep setup
    if not test_adwin_sweep_setup(adwin, args.num_steps, args.integration_time, args.settle_time, bidirectional):
        print("\n❌ Adwin sweep setup failed!")
        return 1
    
    # Test Adwin sweep execution
    results = test_adwin_sweep_execution(adwin, args.sweep_time)
    if results is None:
        print("\n❌ Adwin sweep execution failed!")
        return 1
    
    # Summary
    print(f"\n✅ Adwin test completed!")
    print(f"📊 Final status: sweep_complete={results.get('sweep_complete')}, data_ready={results.get('data_ready')}")
    
    if results.get('forward_counts') is not None and results.get('reverse_counts') is not None:
        print(f"🎉 SUCCESS: Bidirectional data collection working!")
    elif results.get('forward_counts') is not None:
        print(f"⚠️  PARTIAL: Only forward data collected")
    else:
        print(f"❌ FAILED: No data collected")
    
    return 0


if __name__ == "__main__":
    exit(main())
