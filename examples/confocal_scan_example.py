#!/usr/bin/env python3
"""
Confocal Scan Example

This script demonstrates how to run a confocal microscope scan using the existing
ConfocalScan_Fast experiment class. It can run with either real hardware or mock hardware.

Usage:
    python confocal_scan_example.py [--real-hardware] [--no-plot]

Examples:
    # Run with mock hardware (default)
    python confocal_scan_example.py
    
    # Run with real hardware (if available)
    python confocal_scan_example.py --real-hardware
    
    # Run without plotting
    python confocal_scan_example.py --no-plot
"""

import sys
import argparse
import numpy as np
from pathlib import Path
import time

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent / '..'))


def create_devices(use_real_hardware=False):
    """
    Create device instances based on hardware flag.
    
    Args:
        use_real_hardware (bool): If True, use real hardware; if False, use mock hardware
        
    Returns:
        dict: Dictionary of device instances
    """
    if use_real_hardware:
        print("Using real hardware...")
        try:
            from src.Controller import MCLNanoDrive, AdwinGoldDevice
            devices = {
                'nanodrive': MCLNanoDrive(settings={'serial': 2849}),
                'adwin': AdwinGoldDevice()
            }
            print("✅ Real hardware initialized successfully")
            return devices
        except Exception as e:
            print(f"❌ Failed to initialize real hardware: {e}")
            print("Falling back to mock hardware...")
            return None
    else:
        print("Using mock hardware...")
        return None


def run_confocal_scan(use_real_hardware=False, save_data=True, show_plot=True):
    """
    Run a confocal scan experiment.
    
    Args:
        use_real_hardware (bool): Whether to use real hardware
        save_data (bool): Whether to save scan data
        show_plot (bool): Whether to show the plot
        
    Returns:
        dict: Scan results or None if failed
    """
    print("\n" + "="*60)
    print("CONFOCAL SCAN EXAMPLE")
    print("="*60)
    
    print("\nInitializing ConfocalScan_Fast experiment...")
    
    # Check if we can import the experiment class
    try:
        from src.Model.experiments.confocal import ConfocalScan_Fast
    except Exception as e:
        print(f"❌ Cannot import ConfocalScan_Fast: {e}")
        print("This usually means required hardware devices are not available on this platform.")
        return None
    
    # Create devices - use the mock devices from Controller module
    from src.Controller import MCLNanoDrive, AdwinGoldDevice
    devices = {
        'nanodrive': {'instance': MCLNanoDrive(settings={'serial': 2849})},
        'adwin': {'instance': AdwinGoldDevice()}
    }
    
    if use_real_hardware:
        # Try to use real hardware if requested
        real_devices = create_devices(use_real_hardware)
        if real_devices is not None:
            devices = real_devices
    
    # Define scan parameters - using smaller area for faster testing
    scan_settings = {
        'point_a': {
            'x': 5.0,  # Start X position (microns)
            'y': 5.0   # Start Y position (microns)
        },
        'point_b': {
            'x': 15.0,  # End X position (microns) - much smaller area
            'y': 15.0   # End Y position (microns) - much smaller area
        },
        'z_pos': 50.0,  # Z position (microns)
        'resolution': 2.0,  # Resolution in microns - lower resolution for speed
        'time_per_pt': 2.0,  # Time per point in ms - must be 2.0 or 5.0
        'ending_behavior': 'return_to_origin',
        '3D_scan': {
            'enable': False,
            'folderpath': str(Path.home() / 'Experiments' / 'confocal_scans')
        },
        'reboot_adwin': False,
        'cropping': {
            'crop_data': True
        },
        'laser_clock': 'Pixel'
    }
    
    print("Setting up scan...")
    
    try:
        experiment = ConfocalScan_Fast(
            devices=devices,
            name="ConfocalScan_Example",
            settings=scan_settings,
            log_function=print
        )
        
        print("Starting scan...")
        import traceback
        try:
            experiment.run()
            print("✅ Scan completed successfully!")
            
            if save_data:
                # Save the data
                data_path = experiment.data_path
                print(f"📁 Data saved to: {data_path}")
                
            if show_plot and not args.no_plot:
                # Show the results
                experiment.show_results()
            
            # Return the experiment results
            return {
                'experiment': experiment,
                'data_path': getattr(experiment, 'data_path', None),
                'scan_settings': scan_settings,
                'hardware_type': 'real' if use_real_hardware else 'mock'
            }
                
        except Exception as e:
            print(f"❌ Scan failed: {e}")
            print("Full traceback:")
            traceback.print_exc()
            return None
            
    except Exception as e:
        print(f"❌ Failed to create ConfocalScan_Fast experiment: {e}")
        print("This usually means required hardware devices are not available on this platform.")
        return None


def main():
    """Main function to parse arguments and run the scan."""
    parser = argparse.ArgumentParser(description="Run a confocal scan example")
    parser.add_argument("--real-hardware", action="store_true", 
                       help="Use real hardware instead of mock hardware")
    parser.add_argument("--no-plot", action="store_true",
                       help="Skip plotting the results")
    parser.add_argument("--no-save", action="store_true",
                       help="Skip saving scan data")
    
    args = parser.parse_args()
    
    # Run the scan
    results = run_confocal_scan(
        use_real_hardware=args.real_hardware,
        save_data=not args.no_save,
        show_plot=not args.no_plot
    )
    
    if results is None:
        print("\n❌ Scan failed - hardware not available")
        sys.exit(1)
    
    print("\n✅ Confocal scan example completed successfully!")


if __name__ == "__main__":
    main() 