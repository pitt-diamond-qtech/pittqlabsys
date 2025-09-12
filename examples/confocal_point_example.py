#!/usr/bin/env python3
"""
Confocal Point Example

This script demonstrates how to run single-point confocal measurements using the 
NanodriveAdwinConfocalPoint experiment class. It can run with either real hardware 
or mock hardware.

Usage:
    python confocal_point_example.py [--real-hardware] [--continuous] [--no-plot]

Examples:
    # Run with mock hardware (default)
    python confocal_point_example.py
    
    # Run with real hardware (if available)
    python confocal_point_example.py --real-hardware
    
    # Run continuous measurement
    python confocal_point_example.py --continuous
    
    # Run without plotting
    python confocal_point_example.py --no-plot
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
            # Map device names to the keys expected by NanodriveAdwinConfocalPoint
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
        from src.Model.experiments.nanodrive_adwin_confocal_point import NanodriveAdwinConfocalPoint
        experiment = NanodriveAdwinConfocalPoint(
            devices=devices,
            name="ConfocalPoint_Test",
            settings={
                'position': {'x': 35.0, 'y': 35.0},
                'integration_time': 0.1,
                'num_cycles': 100,
                'continuous': False
            }
        )
        
        print("✅ Experiment created successfully")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def run_confocal_point(use_real_hardware=False, continuous=False, save_data=True, show_plot=True, config_path=None):
    """
    Run a confocal point measurement experiment using NanodriveAdwinConfocalPoint.
    
    Args:
        use_real_hardware (bool): Whether to use real hardware
        continuous (bool): Whether to run continuous measurement
        save_data (bool): Whether to save measurement data
        show_plot (bool): Whether to show the plot
        config_path (str): Path to config.json file
        
    Returns:
        dict: Measurement results or None if failed
    """
    print("\n" + "="*60)
    print("CONFOCAL POINT EXAMPLE")
    print("="*60)
    
    print("\nInitializing NanodriveAdwinConfocalPoint experiment...")
    
    # Check if we can import the experiment class
    try:
        from src.Model.experiments.nanodrive_adwin_confocal_point import NanodriveAdwinConfocalPoint
    except Exception as e:
        print(f"❌ Cannot import NanodriveAdwinConfocalPoint: {e}")
        print("This usually means required hardware devices are not available on this platform.")
        return None
    
    # Create devices using device config manager
    devices = create_devices(use_real_hardware, config_path)
    
    # Define measurement parameters
    point_settings = {
        'point': {
            'x': 50.0,  # X position (microns)
            'y': 50.0,  # Y position (microns)
            'z': 50.0   # Z position (microns)
        },
        'count_time': 2.0,  # Time in ms at point to get count data
        'num_cycles': 10,   # Number of samples to average
        'plot_avg': True,   # Plot average count data
        'continuous': continuous,  # Continuous measurement or single point
        'graph_params': {
            'plot_raw_counts': False,  # Plot raw counts instead of counts/sec
            'refresh_rate': 0.1,       # Refresh rate for continuous mode (seconds)
            'length_data': 500,        # Data length for continuous mode
            'font_size': 32            # Font size for display
        },
        'laser_clock': 'Pixel'
    }
    
    print("Setting up measurement...")
    
    try:
        experiment = NanodriveAdwinConfocalPoint(
            devices=devices,
            name="ConfocalPoint_Example",
            settings=point_settings,
            log_function=print
        )
        
        print("Starting measurement...")
        import traceback
        try:
            if continuous:
                print("🔄 Running continuous measurement (press Ctrl+C to stop)...")
                print("   This will run until manually stopped")
            else:
                print("📍 Running single point measurement...")
            
            experiment.run()
            print("✅ Measurement completed successfully!")
            
            if save_data:
                # Save the data
                data_path = experiment.data_path
                print(f"📁 Data saved to: {data_path}")
                
                # Debug: print experiment data structure
                print(f"🔍 Experiment data keys: {list(experiment.data.keys()) if hasattr(experiment, 'data') and experiment.data else 'No data'}")
                if hasattr(experiment, 'data') and experiment.data:
                    print(f"🔍 Data types: {[(k, type(v)) for k, v in experiment.data.items()]}")
                
                # Also save our own CSV format for easy analysis
                save_confocal_point_csv_data(experiment, point_settings, use_real_hardware)
                
            if show_plot:
                # Generate our own plot for inspection
                generate_confocal_point_plot(experiment, point_settings, use_real_hardware)
            
            # Return the experiment results
            return {
                'experiment': experiment,
                'data_path': getattr(experiment, 'data_path', None),
                'point_settings': point_settings,
                'hardware_type': 'real' if use_real_hardware else 'mock'
            }
                
        except KeyboardInterrupt:
            print("\n⏹️  Measurement stopped by user")
            return None
        except Exception as e:
            print(f"❌ Measurement failed: {e}")
            print("Full traceback:")
            traceback.print_exc()
            return None
            
    except Exception as e:
        print(f"❌ Failed to create NanodriveAdwinConfocalPoint experiment: {e}")
        print("This usually means required hardware devices are not available on this platform.")
        return None


def save_confocal_point_csv_data(experiment, point_settings, use_real_hardware):
    """Save confocal point data in CSV format for easy analysis."""
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
            # Extract count data
            counts_data = None
            raw_counts_data = None
            
            if 'counts' in experiment.data:
                counts_data = experiment.data['counts']
                print(f"📊 Using counts data with length: {len(counts_data)}")
            
            if 'raw_counts' in experiment.data:
                raw_counts_data = experiment.data['raw_counts']
                print(f"📊 Using raw_counts data with length: {len(raw_counts_data)}")
            
            if counts_data is not None or raw_counts_data is not None:
                
                # Create CSV with time series data
                csv_data = []
                for i in range(max(len(counts_data) if counts_data else 0, 
                                 len(raw_counts_data) if raw_counts_data else 0)):
                    row = [i]  # Time index
                    if counts_data and i < len(counts_data):
                        row.append(counts_data[i])
                    else:
                        row.append(0)
                    if raw_counts_data and i < len(raw_counts_data):
                        row.append(raw_counts_data[i])
                    else:
                        row.append(0)
                    csv_data.append(row)
                
                # Save as CSV
                import pandas as pd
                csv_filename = output_dir / f"confocal_point_{timestamp}.csv"
                df = pd.DataFrame(csv_data, columns=['Time_Index', 'Counts_Per_Sec', 'Raw_Counts'])
                df.to_csv(csv_filename, index=False)
                print(f"📊 CSV data saved to: {csv_filename}")
                
                # Save summary statistics
                summary_filename = output_dir / f"confocal_point_{timestamp}_summary.csv"
                summary_data = {
                    'Measurement_Type': ['confocal_point'],
                    'Hardware_Type': ['real' if use_real_hardware else 'mock'],
                    'X_Position_um': [point_settings['point']['x']],
                    'Y_Position_um': [point_settings['point']['y']],
                    'Z_Position_um': [point_settings['point']['z']],
                    'Count_Time_ms': [point_settings['count_time']],
                    'Num_Cycles': [point_settings['num_cycles']],
                    'Continuous': [point_settings['continuous']],
                    'Data_Points': [len(csv_data)],
                    'Mean_Counts_Per_Sec': [np.mean(counts_data) if counts_data else 0],
                    'Max_Counts_Per_Sec': [np.max(counts_data) if counts_data else 0],
                    'Min_Counts_Per_Sec': [np.min(counts_data) if counts_data else 0],
                    'Mean_Raw_Counts': [np.mean(raw_counts_data) if raw_counts_data else 0],
                    'Max_Raw_Counts': [np.max(raw_counts_data) if raw_counts_data else 0],
                    'Min_Raw_Counts': [np.min(raw_counts_data) if raw_counts_data else 0]
                }
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_csv(summary_filename, index=False)
                print(f"📋 Summary saved to: {summary_filename}")
            else:
                print("⚠️  No count data found in experiment results")
                
    except Exception as e:
        print(f"⚠️  Failed to save CSV data: {e}")


def generate_confocal_point_plot(experiment, point_settings, use_real_hardware):
    """Generate a PNG plot of the confocal point measurement results."""
    try:
        import matplotlib.pyplot as plt
        
        if hasattr(experiment, 'data') and experiment.data:
            # Try to get count data
            counts_data = None
            raw_counts_data = None
            
            if 'counts' in experiment.data:
                counts_data = experiment.data['counts']
            if 'raw_counts' in experiment.data:
                raw_counts_data = experiment.data['raw_counts']
            
            if counts_data is not None or raw_counts_data is not None:
            
                plt.figure(figsize=(12, 8))
                
                # Time series plot
                plt.subplot(2, 2, 1)
                time_indices = range(len(counts_data) if counts_data else len(raw_counts_data))
                if counts_data:
                    plt.plot(time_indices, counts_data, 'b-', linewidth=2, label='Counts/sec')
                if raw_counts_data:
                    plt.plot(time_indices, raw_counts_data, 'r--', linewidth=1, label='Raw Counts')
                plt.xlabel('Time Index')
                plt.ylabel('Counts')
                plt.title(f'Confocal Point Measurement ({("real" if use_real_hardware else "mock")} hardware)')
                plt.legend()
                plt.grid(True, alpha=0.3)
                
                # Histogram of counts
                plt.subplot(2, 2, 2)
                if counts_data:
                    plt.hist(counts_data, bins=30, alpha=0.7, color='blue', label='Counts/sec')
                if raw_counts_data:
                    plt.hist(raw_counts_data, bins=30, alpha=0.7, color='red', label='Raw Counts')
                plt.xlabel('Counts')
                plt.ylabel('Frequency')
                plt.title('Count Distribution')
                plt.legend()
                plt.grid(True, alpha=0.3)
                
                # Current value display
                plt.subplot(2, 2, 3)
                current_counts = counts_data[-1] if counts_data else 0
                current_raw = raw_counts_data[-1] if raw_counts_data else 0
                plt.text(0.5, 0.7, f'Current Counts/sec: {current_counts:.1f}', 
                        transform=plt.gca().transAxes, fontsize=14, ha='center')
                plt.text(0.5, 0.5, f'Current Raw Counts: {current_raw:.1f}', 
                        transform=plt.gca().transAxes, fontsize=14, ha='center')
                plt.text(0.5, 0.3, f'Position: ({point_settings["point"]["x"]:.1f}, {point_settings["point"]["y"]:.1f}, {point_settings["point"]["z"]:.1f}) μm', 
                        transform=plt.gca().transAxes, fontsize=12, ha='center')
                plt.text(0.5, 0.1, f'Count Time: {point_settings["count_time"]} ms', 
                        transform=plt.gca().transAxes, fontsize=12, ha='center')
                plt.axis('off')
                plt.title('Current Status')
                
                # Statistics
                plt.subplot(2, 2, 4)
                if counts_data:
                    stats_text = f'Counts/sec Statistics:\n'
                    stats_text += f'Mean: {np.mean(counts_data):.2f}\n'
                    stats_text += f'Std: {np.std(counts_data):.2f}\n'
                    stats_text += f'Max: {np.max(counts_data):.2f}\n'
                    stats_text += f'Min: {np.min(counts_data):.2f}\n'
                    stats_text += f'Data Points: {len(counts_data)}'
                    plt.text(0.1, 0.5, stats_text, transform=plt.gca().transAxes, 
                            fontsize=10, va='center', fontfamily='monospace')
                plt.axis('off')
                plt.title('Statistics')
                
                plt.tight_layout()
            
                # Save plot
                output_dir = Path(__file__).parent / "scan_data"
                output_dir.mkdir(exist_ok=True)
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                plot_filename = output_dir / f"confocal_point_plot_{timestamp}.png"
                plt.savefig(plot_filename, dpi=150, bbox_inches='tight')
                print(f"📊 Plot saved to: {plot_filename}")
                
                plt.show()
            else:
                print("⚠️  No count data found for plotting")
            
    except ImportError:
        print("⚠️  matplotlib not available, skipping plot generation")
    except Exception as e:
        print(f"⚠️  Failed to generate plot: {e}")


def main():
    """Main function to parse arguments and run the measurement."""
    parser = argparse.ArgumentParser(description="Run a confocal point measurement example")
    parser.add_argument("--real-hardware", action="store_true", 
                       help="Use real hardware instead of mock hardware")
    parser.add_argument("--continuous", action="store_true",
                       help="Run continuous measurement (until stopped)")
    parser.add_argument("--no-plot", action="store_true",
                       help="Skip plotting the results")
    parser.add_argument("--no-save", action="store_true",
                       help="Skip saving measurement data")
    parser.add_argument("--test-only", action="store_true",
                       help="Only test experiment creation, do not run full measurement")
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
    
    # Run the measurement
    results = run_confocal_point(
        use_real_hardware=args.real_hardware,
        continuous=args.continuous,
        save_data=not args.no_save,
        show_plot=not args.no_plot,
        config_path=args.config
    )
    
    if results is None:
        print("\n❌ Measurement failed - hardware not available")
        sys.exit(1)
    
    print("\n✅ Confocal point example completed successfully!")


if __name__ == "__main__":
    main()
