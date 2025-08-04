#!/usr/bin/env python3
"""
ODMR Scan Example

This example demonstrates how to run an ODMR (Optically Detected Magnetic Resonance) scan
with either real hardware or mock hardware. The scan sweeps microwave frequency while
monitoring fluorescence to identify NV center transitions.

Usage:
    python odmr_scan_example.py --real-hardware    # Use real hardware
    python odmr_scan_example.py --mock-hardware    # Use mock hardware (default)
    python odmr_scan_example.py --help             # Show help
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
from src.Model.experiments.odmr_experiment import ODMRExperiment


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
            from src.Controller import SG384Generator, AdwinGoldDevice, MCLNanoDrive
            devices = {
                'microwave': {'instance': SG384Generator()},
                'adwin': {'instance': AdwinGoldDevice()},
                'nanodrive': {'instance': MCLNanoDrive(settings={'serial': 2849})}
            }
            print("✅ Real hardware initialized successfully")
            return devices
        except Exception as e:
            print(f"❌ Failed to initialize real hardware: {e}")
            print("Falling back to mock hardware...")
            return create_mock_devices()
    else:
        print("Using mock hardware...")
        return create_mock_devices()


def create_mock_devices():
    """Create mock device instances using our refactored mock devices."""
    try:
        from src.Controller import SG384Generator, AdwinGoldDevice, MCLNanoDrive
        devices = {
            'microwave': {'instance': SG384Generator()},
            'adwin': {'instance': AdwinGoldDevice()},
            'nanodrive': {'instance': MCLNanoDrive(settings={'serial': 2849})}
        }
        print("✅ Mock hardware initialized successfully")
        return devices
    except Exception as e:
        print(f"❌ Failed to initialize mock hardware: {e}")
        raise


def run_odmr_scan(use_real_hardware=False, save_data=True, scan_mode='single'):
    """
    Run an ODMR scan experiment.
    
    Args:
        use_real_hardware (bool): Whether to use real hardware
        save_data (bool): Whether to save the scan data
        scan_mode (str): Scan mode ('single', 'continuous', 'averaged', '2d_scan')
        
    Returns:
        dict: Scan results and data
    """
    print("\n" + "="*60)
    print("ODMR SCAN EXAMPLE")
    print("="*60)
    
    # Check if we can import the experiment class
    try:
        from src.Model.experiments.odmr_experiment import ODMRExperiment
    except Exception as e:
        print(f"❌ Cannot import ODMRExperiment: {e}")
        print("This usually means required hardware devices are not available on this platform.")
        return None
    
    # Create devices
    devices = create_devices(use_real_hardware)
    
    # Define scan parameters - using smaller range for faster testing
    scan_settings = {
        'frequency_range': {
            'start': 2.85e9,    # Start frequency (Hz) - smaller range for testing
            'stop': 2.89e9,     # Stop frequency (Hz) - smaller range for testing
            'steps': 20         # Number of frequency points - fewer for testing
        },
        'microwave': {
            'power': -10.0,    # Microwave power (dBm)
            'modulation': False,
            'mod_depth': 1e6,  # Modulation depth (Hz)
            'mod_freq': 1e3    # Modulation frequency (Hz)
        },
        'acquisition': {
            'integration_time': 0.01,  # Integration time per point (s) - faster for testing
            'averages': 1,            # Number of sweeps to average
            'settle_time': 0.001      # Settle time after frequency change (s)
        },
        'laser': {
            'power': 1.0,      # Laser power (mW)
            'wavelength': 532.0 # Laser wavelength (nm)
        },
        'magnetic_field': {
            'enabled': False,
            'strength': 0.0,   # Magnetic field strength (G)
            'direction': [0.0, 0.0, 1.0]
        },
        'scan_mode': scan_mode,
        '2d_scan_settings': {
            'x_range': [0.0, 5.0],   # X scan range (μm) - smaller for testing
            'y_range': [0.0, 5.0],   # Y scan range (μm) - smaller for testing
            'x_steps': 3,            # Number of X positions - fewer for testing
            'y_steps': 3             # Number of Y positions - fewer for testing
        },
        'analysis': {
            'auto_fit': True,
            'smoothing': True,
            'smooth_window': 5,
            'background_subtraction': True
        }
    }
    
    # Create experiment instance
    print(f"\nInitializing ODMR experiment...")
    try:
        experiment = ODMRExperiment(
            devices=devices,
            name="ODMR_Example",
            settings=scan_settings,
            log_function=print
        )
        
        # Setup the experiment
        print("Setting up experiment...")
        experiment.setup()
        
        # Run the scan
        print(f"\nStarting ODMR scan in {scan_mode} mode...")
        print(f"Frequency range: {scan_settings['frequency_range']['start']/1e9:.3f} - "
              f"{scan_settings['frequency_range']['stop']/1e9:.3f} GHz")
        print(f"Power: {scan_settings['microwave']['power']} dBm")
        print(f"Integration time: {scan_settings['acquisition']['integration_time']*1000:.1f} ms")
        
        start_time = time.time()
        
        # Run the experiment
        experiment._function()
        
        scan_time = time.time() - start_time
        print(f"\n✅ ODMR scan completed in {scan_time:.1f} seconds")
        
        # Get the results
        results = {
            'data': experiment.data,
            'settings': experiment.settings,
            'scan_time': scan_time,
            'hardware_type': 'real' if use_real_hardware else 'mock',
            'scan_mode': scan_mode
        }
        
        # Save data if requested
        if save_data:
            save_scan_data(results, f'odmr_scan_{scan_mode}')
        
        return results
        
    except Exception as e:
        print(f"\n❌ ODMR scan failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def save_scan_data(results, scan_type):
    """Save scan data to file in examples/scan_data directory."""
    try:
        # Create output directory
        output_dir = Path(__file__).parent / "scan_data"
        output_dir.mkdir(exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = output_dir / f"{scan_type}_{timestamp}.npz"
        
        # Save data
        np.savez_compressed(
            filename,
            data=results['data'],
            settings=results['settings'],
            scan_time=results['scan_time'],
            hardware_type=results['hardware_type'],
            scan_mode=results['scan_mode']
        )
        
        print(f"📁 Scan data saved to: {filename}")
        
    except Exception as e:
        print(f"⚠️  Failed to save data: {e}")


def plot_results(results):
    """Plot the scan results."""
    try:
        import matplotlib.pyplot as plt
        
        data = results['data']
        if 'odmr_spectrum' in data:
            spectrum = data['odmr_spectrum']
            frequencies = data.get('frequencies', np.arange(len(spectrum)))
            
            plt.figure(figsize=(12, 8))
            
            # Plot ODMR spectrum
            plt.subplot(2, 1, 1)
            plt.plot(frequencies/1e9, spectrum, 'b-', linewidth=2)
            plt.xlabel('Frequency (GHz)')
            plt.ylabel('Fluorescence (counts)')
            plt.title(f'ODMR Spectrum ({results["hardware_type"]} hardware, {results["scan_mode"]} mode)')
            plt.grid(True, alpha=0.3)
            
            # Plot fit results if available
            if 'fit_parameters' in data:
                fit_params = data['fit_parameters']
                fit_spectrum = data.get('fit_spectrum', spectrum)
                plt.plot(frequencies/1e9, fit_spectrum, 'r--', linewidth=2, label='Fit')
                plt.legend()
            
            # Plot 2D scan if available
            if '2d_scan_data' in data and results['scan_mode'] == '2d_scan':
                plt.subplot(2, 1, 2)
                scan_data = data['2d_scan_data']
                plt.imshow(scan_data, cmap='hot', origin='lower')
                plt.colorbar(label='Fluorescence')
                plt.title('2D ODMR Scan')
                plt.xlabel('X Position')
                plt.ylabel('Y Position')
            
            plt.tight_layout()
            
            # Save plot
            output_dir = Path(__file__).parent / "scan_data"
            output_dir.mkdir(exist_ok=True)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            plot_filename = output_dir / f"odmr_scan_plot_{timestamp}.png"
            plt.savefig(plot_filename, dpi=150, bbox_inches='tight')
            print(f"📊 Plot saved to: {plot_filename}")
            
            plt.show()
            
    except ImportError:
        print("⚠️  matplotlib not available, skipping plot")
    except Exception as e:
        print(f"⚠️  Failed to create plot: {e}")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='ODMR Scan Example')
    parser.add_argument('--real-hardware', action='store_true',
                       help='Use real hardware (default: use mock hardware)')
    parser.add_argument('--scan-mode', choices=['single', 'continuous', 'averaged', '2d_scan'], 
                       default='single', help='ODMR scan mode (default: single)')
    parser.add_argument('--no-save', action='store_true',
                       help='Do not save scan data')
    parser.add_argument('--no-plot', action='store_true',
                       help='Do not show plot')
    
    args = parser.parse_args()
    
    try:
        # Run the scan
        results = run_odmr_scan(
            use_real_hardware=args.real_hardware,
            save_data=not args.no_save,
            scan_mode=args.scan_mode
        )
        
        if results is None:
            print("❌ Scan failed - hardware not available")
            return
        
        # Show summary
        print(f"\n📊 Scan Summary:")
        print(f"   Hardware: {results['hardware_type']}")
        print(f"   Scan mode: {results['scan_mode']}")
        print(f"   Duration: {results['scan_time']:.1f} seconds")
        
        # Show resonance information if available
        data = results['data']
        if 'resonance_frequencies' in data:
            resonances = data['resonance_frequencies']
            print(f"   Resonances found: {len(resonances)}")
            for i, freq in enumerate(resonances):
                print(f"     Resonance {i+1}: {freq/1e9:.3f} GHz")
        
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