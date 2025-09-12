#!/usr/bin/env python3
"""
Galvo Scan Example

This example demonstrates how to run a galvo scan with either real hardware or mock hardware.
The scan creates a 2D image by sweeping galvo voltages while counting photons at each position.

Usage:
    python galvo_scan_example.py --real-hardware    # Use real hardware
    python galvo_scan_example.py --mock-hardware    # Use mock hardware (default)
    python galvo_scan_example.py --help             # Show help
"""

import argparse
import sys
import os
import time
import numpy as np
from pathlib import Path
# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent / '..'))

from src.core import Parameter, Experiment
# Don't import GalvoScan here - import it inside the function to handle errors gracefully


# Mock devices are now provided by the Controller module
# No need to define them here since they're handled at the import level


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
            from src.Controller import PCI6229, PCI6601
            devices = {
                'daq': {'instance': PCI6229()},
                'daq2': {'instance': PCI6601()}
            }
            print("✅ Real hardware initialized successfully")
            return devices
        except Exception as e:
            print(f"❌ Failed to initialize real hardware: {e}")
            print("Falling back to mock hardware...")
            return None  # Let GalvoScan use its default mock devices
    else:
        print("Using mock hardware...")
        return None  # Let GalvoScan use its default mock devices


def run_galvo_scan(use_real_hardware=False, save_data=True):
    """
    Run a galvo scan experiment.
    
    Args:
        use_real_hardware (bool): Whether to use real hardware
        save_data (bool): Whether to save the scan data
        
    Returns:
        dict: Scan results and data
    """
    print("\n" + "="*60)
    print("GALVO SCAN EXAMPLE")
    print("="*60)
    
    # Check if we can import the experiment class
    try:
        from src.Model.experiments.galvo_scan import GalvoScan
    except Exception as e:
        print(f"❌ Cannot import GalvoScan: {e}")
        print("This usually means NI-DAQ devices are not available on this platform.")
        return None
    
    # Create devices - use the mock devices from Controller module
    from src.Controller import PCI6229, PCI6601
    devices = {
        'daq': {'instance': PCI6229()},
        'daq2': {'instance': PCI6601()}
    }
    
    if use_real_hardware:
        # Try to use real hardware if requested
        real_devices = create_devices(use_real_hardware)
        if real_devices is not None:
            devices = real_devices
    
    # Define scan parameters
    scan_settings = {
        'point_a': {
            'x': 0.0,      # Start X position (V)
            'y': 0.0       # Start Y position (V)
        },
        'point_b': {
            'x': 1.0,      # End X position (V)
            'y': 1.0       # End Y position (V)
        },
        'num_points': {
            'x': 32,       # Number of X points
            'y': 32        # Number of Y points
        },
        'time_per_pt': 0.002,  # Time per point (s)
        'settle_time': 0.0002, # Settle time (s)
        'ending_behavior': 'return_to_start'
    }
    
    # Create experiment instance
    print(f"\nInitializing GalvoScan experiment...")
    try:
        experiment = GalvoScan(
            devices=devices,
            name="GalvoScan_Example",
            settings=scan_settings,
            log_function=print
        )
    except Exception as e:
        print(f"❌ Failed to create GalvoScan experiment: {e}")
        print("This usually means NI-DAQ devices are not available on this platform.")
        return None
    
    # Setup the scan
    print("Setting up scan...")
    experiment.setup_scan()
    
    # Run the scan
    print(f"\nStarting scan...")
    print(f"Scan area: ({scan_settings['point_a']['x']}, {scan_settings['point_a']['y']}) to "
          f"({scan_settings['point_b']['x']}, {scan_settings['point_b']['y']})")
    print(f"Resolution: {scan_settings['num_points']['x']} x {scan_settings['num_points']['y']} points")
    print(f"Time per point: {scan_settings['time_per_pt']*1000:.1f} ms")
    
    start_time = time.time()
    
    try:
        # Run the experiment
        experiment._function()
        
        scan_time = time.time() - start_time
        print(f"\n✅ Scan completed in {scan_time:.1f} seconds")
        
        # Get the results
        results = {
            'data': experiment.data,
            'settings': experiment.settings,
            'scan_time': scan_time,
            'hardware_type': 'real' if use_real_hardware else 'mock'
        }
        
        # Save data if requested
        if save_data:
            save_scan_data(results, 'galvo_scan')
        
        return results
        
    except Exception as e:
        print(f"\n❌ Scan failed: {e}")
        raise


def save_scan_data(results, scan_type):
    """Save scan data to file in both NPZ and CSV formats."""
    try:
        # Create output directory
        output_dir = Path(__file__).parent / "scan_data"
        output_dir.mkdir(exist_ok=True)
        
        # Generate timestamp
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        
        # Save NPZ format (original)
        npz_filename = output_dir / f"{scan_type}_{timestamp}.npz"
        np.savez_compressed(
            npz_filename,
            data=results['data'],
            settings=results['settings'],
            scan_time=results['scan_time'],
            hardware_type=results['hardware_type']
        )
        print(f"📁 NPZ data saved to: {npz_filename}")
        
        # Save CSV format for easy analysis
        csv_filename = output_dir / f"{scan_type}_{timestamp}.csv"
        
        # Extract image data
        if 'image_data' in results['data']:
            image_data = results['data']['image_data']
            
            # Create coordinate arrays
            x_coords = np.linspace(
                results['settings']['point_a']['x'], 
                results['settings']['point_b']['x'], 
                image_data.shape[1]
            )
            y_coords = np.linspace(
                results['settings']['point_a']['y'], 
                results['settings']['point_b']['y'], 
                image_data.shape[0]
            )
            
            # Create CSV with coordinates and counts
            csv_data = []
            for i, y in enumerate(y_coords):
                for j, x in enumerate(x_coords):
                    csv_data.append([x, y, image_data[i, j]])
            
            # Save as CSV
            import pandas as pd
            df = pd.DataFrame(csv_data, columns=['X_Position', 'Y_Position', 'Counts'])
            df.to_csv(csv_filename, index=False)
            print(f"📊 CSV data saved to: {csv_filename}")
            
            # Also save summary statistics
            summary_filename = output_dir / f"{scan_type}_{timestamp}_summary.csv"
            summary_data = {
                'Scan_Type': [scan_type],
                'Hardware_Type': [results['hardware_type']],
                'Scan_Time_Seconds': [results['scan_time']],
                'X_Start': [results['settings']['point_a']['x']],
                'X_End': [results['settings']['point_b']['x']],
                'Y_Start': [results['settings']['point_a']['y']],
                'Y_End': [results['settings']['point_b']['y']],
                'X_Points': [results['settings']['num_points']['x']],
                'Y_Points': [results['settings']['num_points']['y']],
                'Time_Per_Point_ms': [results['settings']['time_per_pt'] * 1000],
                'Total_Counts': [np.sum(image_data)],
                'Mean_Counts': [np.mean(image_data)],
                'Max_Counts': [np.max(image_data)],
                'Min_Counts': [np.min(image_data)]
            }
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_csv(summary_filename, index=False)
            print(f"📋 Summary saved to: {summary_filename}")
        
    except Exception as e:
        print(f"⚠️  Failed to save data: {e}")
        import traceback
        traceback.print_exc()


def plot_results(results):
    """Plot the scan results."""
    try:
        import matplotlib.pyplot as plt
        
        data = results['data']
        if 'image_data' in data:
            image = data['image_data']
            
            plt.figure(figsize=(10, 8))
            plt.imshow(image, cmap='hot', origin='lower')
            plt.colorbar(label='Counts')
            plt.title(f'Galvo Scan Results ({results["hardware_type"]} hardware)')
            plt.xlabel('X Position')
            plt.ylabel('Y Position')
            
            # Save plot
            output_dir = Path(__file__).parent / "scan_data"
            output_dir.mkdir(exist_ok=True)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            plot_filename = output_dir / f"galvo_scan_plot_{timestamp}.png"
            plt.savefig(plot_filename, dpi=150, bbox_inches='tight')
            print(f"📊 Plot saved to: {plot_filename}")
            
            plt.show()
            
    except ImportError:
        print("⚠️  matplotlib not available, skipping plot")
    except Exception as e:
        print(f"⚠️  Failed to create plot: {e}")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Galvo Scan Example')
    parser.add_argument('--real-hardware', action='store_true',
                       help='Use real hardware (default: use mock hardware)')
    parser.add_argument('--no-save', action='store_true',
                       help='Do not save scan data')
    parser.add_argument('--no-plot', action='store_true',
                       help='Do not show plot')
    
    args = parser.parse_args()
    
    try:
        # Run the scan
        results = run_galvo_scan(
            use_real_hardware=args.real_hardware,
            save_data=not args.no_save
        )
        
        if results is None:
            print("\n❌ Scan failed - hardware not available")
            sys.exit(1)
        
        # Show summary
        print(f"\n📊 Scan Summary:")
        print(f"   Hardware: {results['hardware_type']}")
        print(f"   Duration: {results['scan_time']:.1f} seconds")
        print(f"   Data shape: {results['data'].get('image_data', 'N/A')}")
        
        # Plot results
        if not args.no_plot:
            plot_results(results)
            
    except KeyboardInterrupt:
        print("\n⚠️  Scan interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 