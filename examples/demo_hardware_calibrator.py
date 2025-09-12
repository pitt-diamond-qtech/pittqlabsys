#!/usr/bin/env python3
"""
Demo script for HardwareCalibrator functionality.

This script demonstrates how the HardwareCalibrator applies hardware-specific
timing delays to ensure pulses arrive at the experiment at the intended times.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.Model.hardware_calibrator import HardwareCalibrator
from src.Model.sequence import Sequence
from src.Model.pulses import GaussianPulse, SquarePulse
from src.Model.sequence_builder import SequenceBuilder
import matplotlib.pyplot as plt

def demo_hardware_calibration():
    """Demonstrate hardware calibration with timing delays."""
    print("=== Hardware Calibrator Demo ===")
    
    # Create a realistic qubit sequence
    seq = Sequence(2000)
    
    # Add typical qubit experiment pulses
    pi2_pulse = GaussianPulse("pi_2_pulse", 100, sigma=25, amplitude=1.0)
    laser_pulse = SquarePulse("laser_pulse", 200, amplitude=1.0)
    counter_pulse = SquarePulse("counter_pulse", 150, amplitude=1.0)
    
    # Add pulses at specific times
    seq.add_pulse(0, pi2_pulse)      # Microwave pulse at 0ns
    seq.add_pulse(300, laser_pulse)   # Laser pulse at 300ns
    seq.add_pulse(600, counter_pulse) # Counter trigger at 600ns
    
    print("Original sequence timing:")
    for start_sample, pulse in seq.pulses:
        time_ns = start_sample / 1e9 * 1e9  # Convert samples to ns
        print(f"  {pulse.name}: {time_ns:.0f}ns")
    
    # Create hardware calibrator with default settings
    calibrator = HardwareCalibrator()
    
    print(f"\nCalibration delays:")
    for delay_name, delay_value in calibrator.calibration_delays.items():
        if isinstance(delay_value, (int, float)):
            print(f"  {delay_name}: {delay_value}ns")
    
    # Apply hardware calibration
    calibrated_seq = calibrator.calibrate_sequence(seq, sample_rate=1e9)
    
    print(f"\nCalibrated sequence timing:")
    for start_sample, pulse in calibrated_seq.pulses:
        time_ns = start_sample / 1e9 * 1e9  # Convert samples to ns
        print(f"  {pulse.name}: {time_ns:.0f}ns")
    
    # Show the calibration summary
    summary = calibrator.get_calibration_summary()
    print(f"\nCalibration summary:")
    print(f"  Total connections: {summary['total_connections']}")
    print(f"  Connection file: {summary['connection_file']}")
    
    return seq, calibrated_seq, calibrator

def demo_connection_validation():
    """Demonstrate connection validation for different experiment types."""
    print("\n=== Connection Validation Demo ===")
    
    calibrator = HardwareCalibrator()
    
    # Test different experiment types
    experiment_types = ["odmr", "rabi", "spin_echo"]
    
    for exp_type in experiment_types:
        result = calibrator.validate_connections(exp_type)
        
        print(f"\n{exp_type.upper()} experiment:")
        print(f"  Required: {result['required']}")
        print(f"  Available: {result['available']}")
        print(f"  Missing: {result['missing']}")
        
        if result['missing']:
            print(f"  ⚠️  Missing connections: {result['missing']}")
        else:
            print(f"  ✅ All required connections available")

def demo_visualization_comparison():
    """Demonstrate the difference between original and calibrated sequences."""
    print("\n=== Visualization Comparison Demo ===")
    
    # Get the sequences from the calibration demo
    original_seq, calibrated_seq, calibrator = demo_hardware_calibration()
    
    # Create sequence builder for visualization
    builder = SequenceBuilder(sample_rate=1e9)
    
    # Plot original sequence
    print("Creating plot of original sequence...")
    fig1 = builder.plot_sequence(
        original_seq, 
        title="Original Sequence (No Hardware Calibration)",
        save_path="original_sequence.png"
    )
    plt.show()
    
    # Plot calibrated sequence
    print("Creating plot of calibrated sequence...")
    fig2 = builder.plot_sequence(
        calibrated_seq, 
        title="Calibrated Sequence (With Hardware Delays Applied)",
        save_path="calibrated_sequence.png"
    )
    plt.show()
    
    print("✓ Both plots created and saved")
    print("✓ Notice how pulses are shifted backward in time")
    print("✓ This ensures they arrive at the experiment at the intended times")
    
    return fig1, fig2

def main():
    """Run all demos."""
    print("Hardware Calibrator Demo")
    print("=" * 40)
    
    try:
        # Demo 1: Basic calibration
        original_seq, calibrated_seq, calibrator = demo_hardware_calibration()
        
        # Demo 2: Connection validation
        demo_connection_validation()
        
        # Demo 3: Visualization comparison
        fig1, fig2 = demo_visualization_comparison()
        
        print("\n" + "=" * 40)
        print("🎉 Hardware Calibrator demo completed successfully!")
        print("\nKey features demonstrated:")
        print("✅ Hardware-specific timing delays")
        print("✅ Connection map loading and validation")
        print("✅ Automatic pulse timing adjustment")
        print("✅ Experiment type validation")
        print("✅ Visual comparison of original vs calibrated sequences")
        
        print("\nHow it works:")
        print("1. Loads connection map (channels, markers, delays)")
        print("2. Identifies pulse types and their connections")
        print("3. Applies appropriate delays (shifts backward in time)")
        print("4. Ensures pulses arrive at experiment at intended times")
        
        print("\nFiles saved:")
        print("- original_sequence.png")
        print("- calibrated_sequence.png")
        
        print("\nPress Enter to close plots and continue...")
        input()
        
        # Close plots
        plt.close(fig1)
        plt.close(fig2)
        
        print("✓ Demo completed!")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
