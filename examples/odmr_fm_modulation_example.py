#!/usr/bin/env python3
"""
ODMR Frequency Modulation Example

This example demonstrates how to run an ODMR frequency modulation scan using the new
ODMRFMModulationExperiment that uses SG384 FM modulation for high-speed fine frequency sweeps.

Usage:
    python odmr_fm_modulation_example.py --real-hardware    # Use real hardware
    python odmr_fm_modulation_example.py --mock-hardware    # Use mock hardware (default)
    python odmr_fm_modulation_example.py --help             # Show help
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

from src.Model.experiments.odmr_fm_modulation import ODMRFMModulationExperiment


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
                'microwave': SG384Generator(),
                'adwin': AdwinGoldDevice(),
                'nanodrive': MCLNanoDrive(settings={'serial': 2849})
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
        from src.Controller import MockAdwinGoldDevice, MockSG384Generator, MockMCLNanoDrive
        devices = {
            'microwave': MockSG384Generator(),
            'adwin': MockAdwinGoldDevice(),
            'nanodrive': MockMCLNanoDrive(settings={'serial': 2849})
        }
        print("✅ Mock hardware initialized successfully")
        return devices
    except Exception as e:
        print(f"❌ Failed to initialize mock hardware: {e}")
        raise


def run_odmr_fm_scan(use_real_hardware=False, save_data=True):
    """
    Run an ODMR frequency modulation scan experiment.
    
    Args:
        use_real_hardware (bool): Whether to use real hardware
        save_data (bool): Whether to save the scan data
        
    Returns:
        dict: Scan results and data
    """
    print("\n" + "="*60)
    print("ODMR FREQUENCY MODULATION SCAN")
    print("="*60)
    
    # Check if we can import the experiment class
    try:
        from src.Model.experiments.odmr_fm_modulation import ODMRFMModulationExperiment
    except Exception as e:
        print(f"❌ Cannot import ODMRFMModulationExperiment: {e}")
        print("This usually means required hardware devices are not available on this platform.")
        return None
    
    # Create devices
    devices = create_devices(use_real_hardware)
    
    # Create experiment with optimized settings for FM modulation
    experiment = ODMRFMModulationExperiment(
        devices=devices,
        name="ODMR_FM_Modulation_Scan",
        settings={
            'frequency': {
                'center': 2.87e9,           # 2.87 GHz (NV center resonance)
                'modulation_depth': 10e6,    # 10 MHz modulation depth
                'modulation_rate': 1e3       # 1 kHz modulation rate
            },
            'microwave': {
                'power': -10.0,              # -10 dBm
                'modulation_function': 'Sine'  # Sine wave modulation
            },
            'acquisition': {
                'integration_time': 0.001,     # 1 ms per cycle
                'averages': 100,               # 100 modulation cycle averages
                'cycles_per_average': 10,      # 10 cycles per average
                'settle_time': 0.001           # 1 ms between averages
            },
            'laser': {
                'power': 1.0,        # 1 mW
                'wavelength': 532.0  # 532 nm
            },
            'analysis': {
                'auto_fit': True,
                'smoothing': True,
                'smooth_window': 5,
                'background_subtraction': True,
                'lock_in_detection': True
            }
        }
    )
    
    print(f"✅ Experiment created: {experiment.name}")
    print(f"📊 Center frequency: {experiment.settings['frequency']['center']/1e9:.3f} GHz")
    print(f"📊 Modulation depth: ±{experiment.settings['frequency']['modulation_depth']/1e6:.1f} MHz")
    print(f"📊 Modulation rate: {experiment.settings['frequency']['modulation_rate']/1e3:.1f} kHz")
    print(f"📊 Modulation function: {experiment.settings['microwave']['modulation_function']}")
    print(f"📊 Integration time: {experiment.settings['acquisition']['integration_time']*1000:.1f} ms per cycle")
    print(f"📊 Averages: {experiment.settings['acquisition']['averages']}")
    
    try:
        # Setup experiment
        print("\n🔧 Setting up experiment...")
        experiment.setup()
        
        # Run experiment
        print("\n🚀 Running ODMR frequency modulation scan...")
        start_time = time.time()
        experiment.run()
        end_time = time.time()
        
        print(f"✅ Scan completed in {end_time - start_time:.1f} seconds")
        
        # Get results
        results = experiment.data
        
        # Save data if requested
        if save_data:
            save_odmr_data(results, "fm_modulation")
        
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
            'counts': results['counts'],
            'modulation_phase': results['modulation_phase'],
            'powers': results['powers']
        })
        df.to_csv(csv_file, index=False)
        print(f"💾 Data saved as CSV: {csv_file}")
        
        # Save settings
        settings_file = output_dir / f"odmr_{scan_type}_{timestamp}_settings.txt"
        with open(settings_file, 'w') as f:
            f.write(f"ODMR {scan_type.upper()} Scan Settings\n")
            f.write("=" * 40 + "\n")
            f.write(f"Timestamp: {timestamp}\n")
            f.write(f"Center Frequency: {results['settings']['frequency']['center']/1e9:.3f} GHz\n")
            f.write(f"Modulation Depth: ±{results['settings']['frequency']['modulation_depth']/1e6:.1f} MHz\n")
            f.write(f"Modulation Rate: {results['settings']['frequency']['modulation_rate']/1e3:.1f} kHz\n")
            f.write(f"Modulation Function: {results['settings']['microwave']['modulation_function']}\n")
            f.write(f"Integration Time: {results['settings']['acquisition']['integration_time']*1000:.1f} ms\n")
            f.write(f"Averages: {results['settings']['acquisition']['averages']}\n")
            f.write(f"Microwave Power: {results['settings']['microwave']['power']} dBm\n")
            f.write(f"Cycle Time: {results['cycle_time']*1000:.1f} ms\n")
            f.write(f"Points per Cycle: {results['points_per_cycle']}\n")
            if results['lock_in_signal']:
                f.write(f"Lock-in Signal Magnitude: {results['lock_in_signal']:.2f}\n")
            if results['resonance_frequencies']:
                f.write(f"Resonances Found: {len(results['resonance_frequencies'])}\n")
                for i, freq in enumerate(results['resonance_frequencies']):
                    f.write(f"  Resonance {i+1}: {freq/1e9:.3f} GHz\n")
        print(f"💾 Settings saved: {settings_file}")
        
    except Exception as e:
        print(f"❌ Error saving data: {e}")


def plot_odmr_results(results):
    """Plot ODMR FM modulation results."""
    try:
        # Create figure
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 12))
        
        # Plot 1: Main ODMR FM spectrum
        frequencies_ghz = results['frequencies'] / 1e9
        
        # Plot frequency vs counts
        ax1.plot(frequencies_ghz, results['counts'], 'b-', linewidth=2, 
                label='ODMR FM Spectrum')
        
        # Plot resonance frequencies if available
        if results['resonance_frequencies']:
            for i, freq in enumerate(results['resonance_frequencies']):
                ax1.axvline(x=freq/1e9, color='r', linestyle='--', 
                           label=f'Resonance {i+1}: {freq/1e9:.3f} GHz')
        
        ax1.set_xlabel('Frequency (GHz)')
        ax1.set_ylabel('Photon Counts')
        ax1.set_title('ODMR Frequency Modulation Spectrum')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Modulation phase vs frequency
        ax2.plot(frequencies_ghz, results['modulation_phase'], 'g-', linewidth=2, 
                label='Modulation Phase')
        ax2.set_xlabel('Frequency (GHz)')
        ax2.set_ylabel('Phase (radians)')
        ax2.set_title('Frequency Modulation Phase')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # Plot 3: Raw data vs averaged data
        if 'counts_raw' in results and results['counts_raw'] is not None:
            ax3.plot(frequencies_ghz, results['counts_raw'].T, 'k-', alpha=0.3, linewidth=0.5)
            ax3.plot(frequencies_ghz, results['counts'], 'r-', linewidth=2, label='Averaged Data')
            ax3.set_xlabel('Frequency (GHz)')
            ax3.set_ylabel('Photon Counts')
            ax3.set_title('Raw Data vs Averaged FM Spectrum')
            ax3.legend()
            ax3.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Save plot
        output_dir = Path("examples/odmr_data")
        output_dir.mkdir(exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        plot_file = output_dir / f"odmr_fm_modulation_{timestamp}.png"
        plt.savefig(plot_file, dpi=300, bbox_inches='tight')
        print(f"📊 Plot saved: {plot_file}")
        
        # Show plot
        plt.show()
        
    except Exception as e:
        print(f"❌ Error plotting results: {e}")


def main():
    """Main function to run the ODMR FM modulation example."""
    parser = argparse.ArgumentParser(description='Run ODMR Frequency Modulation Scan')
    parser.add_argument('--real-hardware', action='store_true', 
                       help='Use real hardware instead of mock hardware')
    parser.add_argument('--mock-hardware', action='store_true', 
                       help='Use mock hardware (default)')
    parser.add_argument('--no-save', action='store_true',
                       help='Do not save data to files')
    
    args = parser.parse_args()
    
    # Determine hardware mode
    use_real_hardware = args.real_hardware
    save_data = not args.no_save
    
    print("🎯 ODMR Frequency Modulation Scan Example")
    print(f"🔧 Hardware mode: {'Real' if use_real_hardware else 'Mock'}")
    print(f"💾 Data saving: {'Enabled' if save_data else 'Disabled'}")
    
    # Run the scan
    results = run_odmr_fm_scan(use_real_hardware, save_data)
    
    if results:
        print("\n✅ Example completed successfully!")
        print(f"📊 Data points: {len(results['frequencies'])}")
        print(f"📊 Cycle time: {results['cycle_time']*1000:.1f} ms")
        print(f"📊 Points per cycle: {results['points_per_cycle']}")
        if results['lock_in_signal']:
            print(f"📊 Lock-in signal magnitude: {results['lock_in_signal']:.2f}")
        print(f"📊 Resonances found: {len(results['resonance_frequencies']) if results['resonance_frequencies'] else 0}")
    else:
        print("\n❌ Example failed!")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main()) 