#!/usr/bin/env python3
"""
Confocal Scan Slow Example

This script demonstrates how to run a slow, high-precision confocal microscope scan 
using the NanodriveAdwinConfocalScanSlow experiment class. It can run with either 
real hardware or mock hardware.

Usage:
    python confocal_scan_slow_example.py [--real-hardware] [--no-plot]

Examples:
    # Run with mock hardware (default)
    python confocal_scan_slow_example.py
    
    # Run with real hardware (if available)
    python confocal_scan_slow_example.py --real-hardware
    
    # Run without plotting
    python confocal_scan_slow_example.py --no-plot
"""

import sys
import argparse
import numpy as np
from pathlib import Path
import time

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent / '..'))


def create_devices(use_real_hardware=False, config_path=None):
    """
    Create device instances using the device config manager.
    
    Args:
        use_real_hardware (bool): If True, use real hardware; if False, use mock hardware
        config_path (str): Path to config.json file. If None, uses default.
        
    Returns:
        dict: Dictionary of device instances in the correct format
    """
    if use_real_hardware:
        print("Using real hardware from config...")
        try:
            from src.core.device_config import load_devices_from_config
            from pathlib import Path
            
            # Use provided config path or default
            if config_path is None:
                config_path = Path(__file__).parent.parent / "src" / "config.json"
            
            # Load devices from config
            loaded_devices, failed_devices = load_devices_from_config(config_path)
            
            if failed_devices:
                print(f"⚠️  Some devices failed to load: {list(failed_devices.keys())}")
                for device_name, error in failed_devices.items():
                    print(f"  - {device_name}: {error}")
            
            if not loaded_devices:
                print("❌ No devices loaded from config, falling back to mock hardware...")
                return create_mock_devices()
            
            # Convert to the format expected by experiments
            # Map device names to the keys expected by NanodriveAdwinConfocalScanSlow
            device_mapping = {
                'nanodrive': 'nanodrive',
                'adwin': 'adwin'
            }
            
            devices = {}
            for device_name, device_instance in loaded_devices.items():
                if device_name in device_mapping:
                    mapped_name = device_mapping[device_name]
                    devices[mapped_name] = {'instance': device_instance}
                else:
                    # Keep other devices with their original names for compatibility
                    devices[device_name] = {'instance': device_instance}
            
            print(f"✅ Real hardware initialized successfully: {list(devices.keys())}")
            return devices
            
        except Exception as e:
            print(f"❌ Failed to load real hardware from config: {e}")
            print("Falling back to mock hardware...")
            return create_mock_devices()
    else:
        print("Using mock hardware...")
        return create_mock_devices()


def create_mock_devices():
    """Create mock device instances using our refactored mock devices."""
    try:
        from src.Controller import MockMCLNanoDrive, MockAdwinGoldDevice
        devices = {
            'nanodrive': {'instance': MockMCLNanoDrive(settings={'serial': 2849})},
            'adwin': {'instance': MockAdwinGoldDevice()}
        }
        print("✅ Mock hardware initialized successfully")
        return devices
    except Exception as e:
        print(f"❌ Failed to initialize mock hardware: {e}")
        raise


def test_experiment_creation():
    """Test that the experiment can be created successfully."""
    try:
        # Create mock devices
        devices = create_mock_devices()
        
        # Create experiment
        from src.Model.experiments.nanodrive_adwin_confocal_scan_slow import NanodriveAdwinConfocalScanSlow
        experiment = NanodriveAdwinConfocalScanSlow(
            devices=devices,
            name="ConfocalScanSlow_Test",
            settings={
                'scan_range': {'x_start': 30.0, 'x_stop': 40.0, 'y_start': 30.0, 'y_stop': 40.0},
                'scan_points': {'x_points': 5, 'y_points': 5},
                'integration_time': 0.1,
                'settle_time': 0.01
            }
        )
        
        print("✅ Experiment created successfully")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def run_confocal_scan_slow(use_real_hardware=False, save_data=True, show_plot=True, config_path=None):
    """
    Run a slow confocal scan experiment using NanodriveAdwinConfocalScanSlow.
    
    Args:
        use_real_hardware (bool): Whether to use real hardware
        save_data (bool): Whether to save scan data
        show_plot (bool): Whether to show the plot
        config_path (str): Path to config.json file
        
    Returns:
        dict: Scan results or None if failed
    """
    print("\n" + "="*60)
    print("CONFOCAL SCAN SLOW EXAMPLE")
    print("="*60)
    
    print("\nInitializing NanodriveAdwinConfocalScanSlow experiment...")
    
    # Check if we can import the experiment class
    try:
        from src.Model.experiments.nanodrive_adwin_confocal_scan_slow import NanodriveAdwinConfocalScanSlow
    except Exception as e:
        print(f"❌ Cannot import NanodriveAdwinConfocalScanSlow: {e}")
        print("This usually means required hardware devices are not available on this platform.")
        return None
    
    # Create devices using device config manager
    devices = create_devices(use_real_hardware, config_path)
    
    # Define scan parameters - using smaller area for faster testing
    scan_settings = {
        'point_a': {
            'x': 35.0,  # Start X position (microns)
            'y': 35.0   # Start Y position (microns)
        },
        'point_b': {
            'x': 45.0,  # End X position (microns) - small area for testing
            'y': 45.0   # End Y position (microns) - small area for testing
        },
        'z_pos': 50.0,  # Z position (microns)
        'resolution': 2.0,  # Resolution in microns - lower resolution for speed
        'time_per_pt': 5.0,  # Time per point in ms
        'settle_time': 0.1,  # Settle time in seconds - reduced for testing
        'ending_behavior': 'return_to_origin',
        '3D_scan': {
            'enable': False,
            'folderpath': str(Path.home() / 'Experiments' / 'confocal_scans')
        },
        'reboot_adwin': False,
        'laser_clock': 'Pixel'
    }
    
    print("Setting up scan...")
    
    try:
        experiment = NanodriveAdwinConfocalScanSlow(
            devices=devices,
            name="ConfocalScan_Slow_Example",
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
                
                # Debug: print experiment data structure
                print(f"🔍 Experiment data keys: {list(experiment.data.keys()) if hasattr(experiment, 'data') and experiment.data else 'No data'}")
                if hasattr(experiment, 'data') and experiment.data:
                    print(f"🔍 Data types: {[(k, type(v)) for k, v in experiment.data.items()]}")
                
                # Also save our own CSV format for easy analysis
                save_confocal_csv_data(experiment, scan_settings, use_real_hardware)
                
            if show_plot:
                # Generate our own plot for inspection
                generate_confocal_plot(experiment, scan_settings, use_real_hardware)
            
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
        print(f"❌ Failed to create NanodriveAdwinConfocalScanSlow experiment: {e}")
        print("This usually means required hardware devices are not available on this platform.")
        return None


def save_confocal_csv_data(experiment, scan_settings, use_real_hardware):
    """Save confocal scan data in CSV format for easy analysis."""
    try:
        # Use configured data folder
        from src.core.helper_functions import get_configured_data_folder
        base_data_dir = get_configured_data_folder()
        output_dir = base_data_dir / "confocal_scans"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate timestamp
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        
        # Get experiment data
        if hasattr(experiment, 'data') and experiment.data:
            # Extract image data if available - try count_img first
            image_data = None
            if 'count_img' in experiment.data:
                image_data = experiment.data['count_img']
                print(f"📊 Using count_img data with shape: {image_data.shape}")
            
            if image_data is not None:
                
                # Create coordinate arrays
                x_coords = np.linspace(
                    scan_settings['point_a']['x'], 
                    scan_settings['point_b']['x'], 
                    image_data.shape[1]
                )
                y_coords = np.linspace(
                    scan_settings['point_a']['y'], 
                    scan_settings['point_b']['y'], 
                    image_data.shape[0]
                )
                
                # Create CSV with coordinates and counts
                csv_data = []
                for i, y in enumerate(y_coords):
                    for j, x in enumerate(x_coords):
                        csv_data.append([x, y, image_data[i, j]])
                
                # Save as CSV
                import pandas as pd
                csv_filename = output_dir / f"confocal_scan_slow_{timestamp}.csv"
                df = pd.DataFrame(csv_data, columns=['X_Position_um', 'Y_Position_um', 'Counts'])
                df.to_csv(csv_filename, index=False)
                print(f"📊 CSV data saved to: {csv_filename}")
                
                # Save summary statistics
                summary_filename = output_dir / f"confocal_scan_slow_{timestamp}_summary.csv"
                summary_data = {
                    'Scan_Type': ['confocal_scan_slow'],
                    'Hardware_Type': ['real' if use_real_hardware else 'mock'],
                    'X_Start_um': [scan_settings['point_a']['x']],
                    'X_End_um': [scan_settings['point_b']['x']],
                    'Y_Start_um': [scan_settings['point_a']['y']],
                    'Y_End_um': [scan_settings['point_b']['y']],
                    'Z_Position_um': [scan_settings['z_pos']],
                    'Resolution_um': [scan_settings['resolution']],
                    'Time_Per_Point_ms': [scan_settings['time_per_pt']],
                    'Settle_Time_s': [scan_settings['settle_time']],
                    'Total_Counts': [np.sum(image_data)],
                    'Mean_Counts': [np.mean(image_data)],
                    'Max_Counts': [np.max(image_data)],
                    'Min_Counts': [np.min(image_data)]
                }
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_csv(summary_filename, index=False)
                print(f"📋 Summary saved to: {summary_filename}")
            else:
                print("⚠️  No image data found in experiment results")
                
    except Exception as e:
        print(f"⚠️  Failed to save CSV data: {e}")


def generate_confocal_plot(experiment, scan_settings, use_real_hardware):
    """Generate a PNG plot of the confocal scan results."""
    try:
        import matplotlib.pyplot as plt
        
        if hasattr(experiment, 'data') and experiment.data:
            # Try to get image data from available keys
            image_data = None
            if 'count_img' in experiment.data:
                image_data = experiment.data['count_img']
            
            if image_data is not None:
            
                plt.figure(figsize=(12, 8))
                
                # Main image plot
                plt.subplot(2, 2, 1)
                plt.imshow(image_data, cmap='hot', origin='lower')
                plt.colorbar(label='Counts')
                plt.title(f'Confocal Scan Slow Results ({("real" if use_real_hardware else "mock")} hardware)')
                plt.xlabel('X Position (μm)')
                plt.ylabel('Y Position (μm)')
                
                # Line profiles
                plt.subplot(2, 2, 2)
                center_y = image_data.shape[0] // 2
                plt.plot(image_data[center_y, :], 'b-', linewidth=2, label=f'Y = {center_y}')
                plt.xlabel('X Position')
                plt.ylabel('Counts')
                plt.title('X Line Profile')
                plt.grid(True, alpha=0.3)
                
                plt.subplot(2, 2, 3)
                center_x = image_data.shape[1] // 2
                plt.plot(image_data[:, center_x], 'r-', linewidth=2, label=f'X = {center_x}')
                plt.xlabel('Y Position')
                plt.ylabel('Counts')
                plt.title('Y Line Profile')
                plt.grid(True, alpha=0.3)
                
                # Histogram
                plt.subplot(2, 2, 4)
                plt.hist(image_data.flatten(), bins=50, alpha=0.7, color='green')
                plt.xlabel('Counts')
                plt.ylabel('Frequency')
                plt.title('Count Distribution')
                plt.grid(True, alpha=0.3)
                
                plt.tight_layout()
            
                # Save plot
                output_dir = Path(__file__).parent / "scan_data"
                output_dir.mkdir(exist_ok=True)
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                plot_filename = output_dir / f"confocal_scan_slow_plot_{timestamp}.png"
                plt.savefig(plot_filename, dpi=150, bbox_inches='tight')
                print(f"📊 Plot saved to: {plot_filename}")
                
                plt.show()
            else:
                print("⚠️  No image data found for plotting")
            
    except ImportError:
        print("⚠️  matplotlib not available, skipping plot generation")
    except Exception as e:
        print(f"⚠️  Failed to generate plot: {e}")


def main():
    """Main function to parse arguments and run the scan."""
    parser = argparse.ArgumentParser(description="Run a confocal scan slow example")
    parser.add_argument("--real-hardware", action="store_true", 
                       help="Use real hardware instead of mock hardware")
    parser.add_argument("--no-plot", action="store_true",
                       help="Skip plotting the results")
    parser.add_argument("--no-save", action="store_true",
                       help="Skip saving scan data")
    parser.add_argument("--test-only", action="store_true",
                       help="Only test experiment creation, do not run full scan")
    parser.add_argument("--config", type=str, default=None,
                       help="Path to config.json file (default: src/config.json)")
    
    args = parser.parse_args()
    
    # Test experiment creation first
    if args.test_only:
        print("🧪 Testing experiment creation...")
        if test_experiment_creation():
            print("✅ Experiment creation test passed!")
            return 0
        else:
            print("❌ Experiment creation test failed!")
            return 1
    
    # Run the scan
    results = run_confocal_scan_slow(
        use_real_hardware=args.real_hardware,
        save_data=not args.no_save,
        show_plot=not args.no_plot,
        config_path=args.config
    )
    
    if results is None:
        print("\n❌ Scan failed - hardware not available")
        sys.exit(1)
    
    print("\n✅ Confocal scan slow example completed successfully!")


if __name__ == "__main__":
    main()
