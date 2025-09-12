#!/usr/bin/env python3
"""
ODMR Continuous Sweep Example

This example demonstrates how to run an ODMR continuous sweep scan using the new
ODMRSweepContinuousExperiment that uses SG384 phase continuous sweep with synchronized Adwin counting.

Usage:
    python odmr_sweep_continuous_example.py --real-hardware    # Use real hardware
    python odmr_sweep_continuous_example.py --mock-hardware    # Use mock hardware (default)
    python odmr_sweep_continuous_example.py --help             # Show help
"""

import argparse
import sys
import os
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent / '..'))

from src.Model.experiments.odmr_sweep_continuous import ODMRSweepContinuousExperiment


def create_devices(use_real_hardware=False, config_path=None, debug=False):
    """
    Create device instances using the device config manager.
    
    Args:
        use_real_hardware (bool): If True, use real hardware; if False, use mock hardware
        config_path (str): Path to config.json file. If None, uses default.
        debug (bool): If True, show detailed debug information
        
    Returns:
        dict: Dictionary of device instances in the correct format
    """
    if use_real_hardware:
        print("Using real hardware from config...")
        try:
            from src.core.device_config import load_devices_from_config
            from pathlib import Path purpose 
            
            # Use provided config path or default
            if config_path is None:
                config_path = Path(__file__).parent.parent / "src" / "config.json"
            
            if debug:
                print(f"🔍 Debug: Loading devices from config: {config_path}")
                print(f"🔍 Debug: Config file exists: {config_path.exists()}")
            
            # Load devices from config
            loaded_devices, failed_devices = load_devices_from_config(config_path)
            
            if failed_devices:
                print(f"⚠️  Some devices failed to load: {list(failed_devices.keys())}")
                for device_name, error in failed_devices.items():
                    print(f"  - {device_name}: {error}")
            
            if not loaded_devices:
                print("❌ No devices loaded from config, falling back to mock hardware...")
                print("🔍 This usually means:")
                print("   - Hardware devices are not connected or powered on")
                print("   - Network connection issues (SG384 IP not reachable)")
                print("   - Driver issues (Adwin drivers not installed)")
                print("   - Port issues (COM ports in use or not available)")
                print("   - Permission issues accessing hardware")
                return create_mock_devices()
            
            # Convert to the format expected by experiments
            # Map device names to the keys expected by ODMRSweepContinuousExperiment
            device_mapping = {
                'sg384': 'microwave',
                'adwin': 'adwin', 
                'nanodrive': 'nanodrive'
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
        from src.Controller import MockSG384Generator, MockAdwinGoldDevice, MockMCLNanoDrive
        devices = {
            'microwave': {'instance': MockSG384Generator()},
            'adwin': {'instance': MockAdwinGoldDevice()},
            'nanodrive': {'instance': MockMCLNanoDrive(settings={'serial': 2849})}
        }
        print("✅ Mock hardware initialized successfully")
        return devices
    except Exception as e:
        print(f"❌ Failed to initialize mock hardware: {e}")
        raise


def run_odmr_sweep_scan(use_real_hardware=False, save_data=True, config_path=None, debug=False):
    """
    Run an ODMR continuous sweep scan experiment.
    
    Args:
        use_real_hardware (bool): Whether to use real hardware
        save_data (bool): Whether to save the scan data
        config_path (str): Path to config.json file
        debug (bool): Whether to show debug information
        
    Returns:
        dict: Scan results and data
    """
    print("\n" + "="*60)
    print("ODMR CONTINUOUS SWEEP SCAN")
    print("="*60)
    
    # Check if we can import the experiment class
    try:
        from src.Model.experiments.odmr_sweep_continuous import ODMRSweepContinuousExperiment
    except Exception as e:
        print(f"❌ Cannot import ODMRSweepContinuousExperiment: {e}")
        print("This usually means required hardware devices are not available on this platform.")
        return None
    
    # Create devices
    devices = create_devices(use_real_hardware, config_path, debug)
    
    # Create experiment with optimized settings for continuous sweeping
    experiment = ODMRSweepContinuousExperiment(
        devices=devices,
        name="ODMR_Continuous_Sweep_Scan",
        settings={
            'frequency_range': {
                'start': 2.7e9,  # 2.7 GHz
                'stop': 3.0e9    # 3.0 GHz
            },
            'microwave': {
                'power': -10.0,           # -10 dBm
                'step_freq': 1e6,         # 1 MHz step frequency
                'sweep_function': 'Triangle'  # Triangle sweep waveform
            },
            'acquisition': {
                'integration_time': 0.005,  # 1 ms per point
                'averages': 10,             # 10 sweep averages
                'settle_time': 0.001         # 10 ms between sweeps
            },
            'laser': {
                'power': 1.0,        # 1 mW
                'wavelength': 532.0  # 532 nm
            },
            'analysis': {
                'auto_fit': True,
                'smoothing': True,
                'smooth_window': 5,
                'background_subtraction': True
            }
        }
    )
    
    print(f"✅ Experiment created: {experiment.name}")
    print(f"📊 Frequency range: {experiment.settings['frequency_range']['start']/1e9:.2f} - {experiment.settings['frequency_range']['stop']/1e9:.2f} GHz")
    print(f"📊 Step frequency: {experiment.settings['microwave']['step_freq']/1e6:.2f} MHz")
    print(f"📊 Sweep function: {experiment.settings['microwave']['sweep_function']}")
    print(f"📊 Integration time: {experiment.settings['acquisition']['integration_time']*1000:.1f} ms per point")
    print(f"📊 Averages: {experiment.settings['acquisition']['averages']}")
    
    try:
        # Setup experiment
        print("\n🔧 Setting up experiment...")
        experiment.setup()
        
        # Run experiment
        print("\n🚀 Running ODMR continuous sweep scan...")
        start_time = time.time()
        experiment.run()
        end_time = time.time()
        
        print(f"✅ Scan completed in {end_time - start_time:.1f} seconds")
        
        # Get results
        results = experiment.data
        
        # Save data if requested
        if save_data:
            save_odmr_data(results, "sweep_continuous")
        
        # Plot results
        plot_odmr_results(results)
        
        return results
        
    except Exception as e:
        print(f"❌ Error during experiment: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    finally:
        # Cleanup
        print("\n🧹 Cleaning up...")
        experiment.cleanup()


def save_odmr_data(results, scan_type):
    """Save ODMR data to files."""
    try:
        # Create output directory
        output_dir = Path("examples/odmr_data")
        output_dir.mkdir(exist_ok=True)
        
        # Generate timestamp
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        
        # Save as NPZ
        npz_file = output_dir / f"odmr_{scan_type}_{timestamp}.npz"
        np.savez_compressed(npz_file, **results)
        print(f"💾 Data saved as NPZ: {npz_file}")
        
        # Save as CSV
        csv_file = output_dir / f"odmr_{scan_type}_{timestamp}.csv"
        df = pd.DataFrame({
            'frequency_ghz': results['frequencies'] / 1e9,
            'counts_forward': results['counts_forward'],
            'counts_reverse': results['counts_reverse'],
            'counts_averaged': results['counts_averaged'],
            'voltages': results['voltages']
        })
        df.to_csv(csv_file, index=False)
        print(f"💾 Data saved as CSV: {csv_file}")
        
        # Save settings
        settings_file = output_dir / f"odmr_{scan_type}_{timestamp}_settings.txt"
        with open(settings_file, 'w') as f:
            f.write(f"ODMR {scan_type.upper()} Scan Settings\n")
            f.write("=" * 40 + "\n")
            f.write(f"Timestamp: {timestamp}\n")
            f.write(f"Frequency Range: {results['settings']['frequency_range']['start']/1e9:.3f} - {results['settings']['frequency_range']['stop']/1e9:.3f} GHz\n")
            f.write(f"Step Frequency: {results['settings']['microwave']['step_freq']/1e6:.2f} MHz\n")
            f.write(f"Sweep Function: {results['settings']['microwave']['sweep_function']}\n")
            f.write(f"Integration Time: {results['settings']['acquisition']['integration_time']*1000:.1f} ms\n")
            f.write(f"Averages: {results['settings']['acquisition']['averages']}\n")
            f.write(f"Microwave Power: {results['settings']['microwave']['power']} dBm\n")
            f.write(f"Sweep Time: {results['sweep_time']:.3f} s\n")
            f.write(f"Number of Steps: {results['num_steps']}\n")
            if results['resonance_frequencies']:
                f.write(f"Resonances Found: {len(results['resonance_frequencies'])}\n")
                for i, freq in enumerate(results['resonance_frequencies']):
                    f.write(f"  Resonance {i+1}: {freq/1e9:.3f} GHz\n")
        print(f"💾 Settings saved: {settings_file}")
        
    except Exception as e:
        print(f"❌ Error saving data: {e}")


def plot_odmr_results(results):
    """Plot ODMR sweep results."""
    try:
        # Create figure
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
        
        # Plot 1: Main ODMR spectrum with forward/reverse sweeps
        frequencies_ghz = results['frequencies'] / 1e9
        
        # Plot forward and reverse sweeps
        ax1.plot(frequencies_ghz, results['counts_forward'], 'b-', linewidth=1, 
                label='Forward Sweep', alpha=0.7)
        ax1.plot(frequencies_ghz, results['counts_reverse'], 'g-', linewidth=1, 
                label='Reverse Sweep', alpha=0.7)
        
        # Plot averaged data
        ax1.plot(frequencies_ghz, results['counts_averaged'], 'r-', linewidth=2, 
                label='Averaged Spectrum')
        
        # Plot resonance frequencies if available
        if results['resonance_frequencies']:
            for i, freq in enumerate(results['resonance_frequencies']):
                ax1.axvline(x=freq/1e9, color='orange', linestyle='--', 
                           label=f'Resonance {i+1}: {freq/1e9:.3f} GHz')
        
        ax1.set_xlabel('Frequency (GHz)')
        ax1.set_ylabel('Photon Counts')
        ax1.set_title('ODMR Continuous Sweep Spectrum')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Voltage ramp vs frequency
        ax2.plot(frequencies_ghz, results['voltages'], 'purple', linewidth=2, 
                label='Voltage Ramp (SG384 FM Input)')
        ax2.set_xlabel('Frequency (GHz)')
        ax2.set_ylabel('Voltage (V)')
        ax2.set_title('SG384 FM Input Voltage Ramp')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Save plot
        output_dir = Path("examples/odmr_data")
        output_dir.mkdir(exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        plot_file = output_dir / f"odmr_sweep_continuous_{timestamp}.png"
        plt.savefig(plot_file, dpi=300, bbox_inches='tight')
        print(f"📊 Plot saved: {plot_file}")
        
        # Show plot
        plt.show()
        
    except Exception as e:
        print(f"❌ Error plotting results: {e}")


def test_experiment_creation():
    """Test that the experiment can be created and configured properly."""
    print("\n🧪 Testing experiment creation...")
    
    try:
        # Create mock devices
        devices = create_mock_devices()
        
        # Create experiment
        experiment = ODMRSweepContinuousExperiment(
            devices=devices,
            name="Test_ODMR_Sweep",
            settings={
                'frequency_range': {'start': 2.7e9, 'stop': 3.0e9},
                'microwave': {'power': -10.0, 'step_freq': 1e6, 'sweep_function': 'Triangle'},
                'acquisition': {'integration_time': 0.001, 'averages': 5, 'settle_time': 0.01},
                'laser': {'power': 1.0, 'wavelength': 532.0},
                'analysis': {
                    'auto_fit': True, 
                    'smoothing': True,
                    'smooth_window': 5,
                    'background_subtraction': True
                }
            }
        )
        
        print("✅ Experiment created successfully")
        
        # Test parameter calculation
        experiment._calculate_sweep_parameters()
        print(f"✅ Parameters calculated: {experiment.num_steps} steps, {experiment.sweep_time:.3f}s sweep time")
        
        # Test device access
        if hasattr(experiment, 'microwave') and experiment.microwave:
            print("✅ Microwave device accessible")
        if hasattr(experiment, 'adwin') and experiment.adwin:
            print("✅ Adwin device accessible")
        if hasattr(experiment, 'nanodrive') and experiment.nanodrive:
            print("✅ Nanodrive device accessible")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main function to run the ODMR continuous sweep example."""
    parser = argparse.ArgumentParser(description='Run ODMR Continuous Sweep Scan')
    parser.add_argument('--real-hardware', action='store_true', 
                       help='Use real hardware instead of mock hardware')
    parser.add_argument('--mock-hardware', action='store_true', 
                       help='Use mock hardware (default)')
    parser.add_argument('--no-save', action='store_true',
                       help='Do not save data to files')
    parser.add_argument('--test-only', action='store_true',
                       help='Only test experiment creation, do not run full scan')
    parser.add_argument('--config', type=str, default=None,
                       help='Path to config.json file (default: src/config.json)')
    parser.add_argument('--debug', action='store_true',
                       help='Show detailed debug information during device loading')
    
    args = parser.parse_args()
    
    # Determine hardware mode
    use_real_hardware = args.real_hardware
    save_data = not args.no_save
    
    print("🎯 ODMR Continuous Sweep Scan Example")
    print(f"🔧 Hardware mode: {'Real' if use_real_hardware else 'Mock'}")
    print(f"💾 Data saving: {'Enabled' if save_data else 'Disabled'}")
    
    # Test experiment creation first
    if not test_experiment_creation():
        print("\n❌ Experiment creation test failed!")
        return 1
    
    if args.test_only:
        print("\n✅ Test completed successfully!")
        return 0
    
    # Run the full scan
    results = run_odmr_sweep_scan(use_real_hardware, save_data, args.config, args.debug)
    
    if results:
        print("\n✅ Example completed successfully!")
        print(f"📊 Data points: {len(results['frequencies'])}")
        print(f"📊 Sweep time: {results['sweep_time']:.3f} s")
        print(f"📊 Resonances found: {len(results['resonance_frequencies']) if results['resonance_frequencies'] else 0}")
    else:
        print("\n❌ Example failed!")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main()) 