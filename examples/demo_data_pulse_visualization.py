#!/usr/bin/env python3
"""
Demo script to show DataPulse visualization working.

This script demonstrates how DataPulse loads CSV data and displays it
in the visualization system.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.Model.sequence_builder import SequenceBuilder
from src.Model.sequence import Sequence
from src.Model.pulses import DataPulse, GaussianPulse, SechPulse, LorentzianPulse, SquarePulse
import matplotlib.pyplot as plt

def demo_data_pulse():
    """Demonstrate DataPulse loading and visualization."""
    print("=== DataPulse Demo ===")
    
    # Create sequence with DataPulse
    seq = Sequence(2000)  # 2000 samples
    
    # Load sine wave data from CSV
    data_pulse = DataPulse("sine_wave", 200, "tests/test_data_sine_wave.csv")
    seq.add_pulse(100, data_pulse)
    
    # Add other pulse types for comparison
    gaussian = GaussianPulse("gaussian", 100, sigma=25, amplitude=1.0)
    sech = SechPulse("sech", 80, width=15, amplitude=1.0)
    lorentzian = LorentzianPulse("lorentzian", 120, gamma=30, amplitude=1.0)
    square = SquarePulse("square", 100, amplitude=1.0)
    
    seq.add_pulse(400, gaussian)
    seq.add_pulse(600, sech)
    seq.add_pulse(800, lorentzian)
    seq.add_pulse(1000, square)
    
    # Create builder and plot
    builder = SequenceBuilder(sample_rate=1e9)
    
    print("Creating plot with DataPulse and other pulse types...")
    fig = builder.plot_sequence(
        seq, 
        title="DataPulse Demo - Sine Wave + Other Pulse Types",
        save_path="data_pulse_demo.png"
    )
    
    print("✓ Plot created and saved as 'data_pulse_demo.png'")
    print("✓ DataPulse loaded sine wave from CSV file")
    print("✓ All pulse types displayed correctly")
    
    # Show the plot
    plt.show()
    
    return fig

def demo_ramp_data_pulse():
    """Demonstrate DataPulse with ramp data."""
    print("\n=== Ramp DataPulse Demo ===")
    
    # Create sequence with ramp DataPulse
    seq = Sequence(1500)
    
    # Load ramp data from CSV
    ramp_pulse = DataPulse("ramp", 150, "tests/test_data_ramp.csv")
    seq.add_pulse(200, ramp_pulse)
    
    # Create builder and plot
    builder = SequenceBuilder(sample_rate=1e9)
    
    print("Creating plot with ramp DataPulse...")
    fig = builder.plot_sequence(
        seq,
        title="Ramp DataPulse Demo",
        save_path="ramp_data_pulse_demo.png"
    )
    
    print("✓ Plot created and saved as 'ramp_data_pulse_demo.png'")
    print("✓ DataPulse loaded ramp data from CSV file")
    
    # Show the plot
    plt.show()
    
    return fig

def demo_animation():
    """Demonstrate animation with DataPulse."""
    print("\n=== Animation Demo ===")
    
    # Create multiple sequences for animation
    sequences = []
    
    # Sequence 1: Original sine wave
    seq1 = Sequence(1000)
    data_pulse1 = DataPulse("sine_1", 150, "tests/test_data_sine_wave.csv")
    seq1.add_pulse(100, data_pulse1)
    sequences.append(seq1)
    
    # Sequence 2: Sine wave with different timing
    seq2 = Sequence(1000)
    data_pulse2 = DataPulse("sine_2", 150, "tests/test_data_sine_wave.csv")
    seq2.add_pulse(200, data_pulse2)
    sequences.append(seq2)
    
    # Sequence 3: Sine wave with different timing
    seq3 = Sequence(1000)
    data_pulse3 = DataPulse("sine_3", 150, "tests/test_data_sine_wave.csv")
    seq3.add_pulse(300, data_pulse3)
    sequences.append(seq3)
    
    # Create builder and animate
    builder = SequenceBuilder(sample_rate=1e9)
    
    print("Creating animation with DataPulse sequences...")
    anim = builder.animate_scan_sequences(
        sequences,
        title="DataPulse Animation Demo",
        interval=2000  # 2 seconds per frame
    )
    
    print("✓ Animation created with 3 DataPulse sequences")
    print("✓ Each sequence shows sine wave at different timing")
    
    return anim

def main():
    """Run all demos."""
    print("DataPulse Visualization Demo")
    print("=" * 40)
    
    try:
        # Demo 1: DataPulse with other pulse types
        fig1 = demo_data_pulse()
        
        # Demo 2: Ramp DataPulse
        fig2 = demo_ramp_data_pulse()
        
        # Demo 3: Animation
        anim = demo_animation()
        
        print("\n" + "=" * 40)
        print("🎉 All demos completed successfully!")
        print("\nWhat you should see:")
        print("1. **DataPulse Demo**: Sine wave loaded from CSV + other pulse types")
        print("2. **Ramp Demo**: Ramp data loaded from CSV")
        print("3. **Animation**: 3 sequences showing sine waves at different times")
        
        print("\nKey features demonstrated:")
        print("✅ CSV file loading and parsing")
        print("✅ Automatic resampling to fit pulse length")
        print("✅ Proper visualization integration")
        print("✅ Animation support")
        
        print("\nFiles saved:")
        print("- data_pulse_demo.png")
        print("- ramp_data_pulse_demo.png")
        
        print("\nPlots should now be visible!")
        print("If you can see them, press Enter to continue...")
        print("If you can't see them, check for minimized windows or try:")
        print("1. Look for plot windows in your dock/taskbar")
        print("2. Check if they're behind other windows")
        print("3. Try Cmd+Tab to cycle through windows")
        
        input("Press Enter to close plots and continue...")
        
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
