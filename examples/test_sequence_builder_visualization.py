#!/usr/bin/env python3
"""
Test script for SequenceBuilder visualization methods.

This script demonstrates how to use the new plot_sequence and 
animate_scan_sequences methods from SequenceBuilder.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.Model.sequence_parser import SequenceTextParser
from src.Model.sequence_builder import SequenceBuilder
import matplotlib.pyplot as plt

def test_static_plot():
    """Test the plot_sequence method."""
    print("Testing static plot...")
    
    # Create a simple sequence description
    sequence_text = """
    sequence: test_sequence, type=custom, duration=1000ns, sample_rate=1GHz, repeat_count=50000
    
    pi/2 pulse on channel 1 at 0ns, gaussian, 100ns, 1.0
    laser pulse on channel 2 at 200ns, square, 50ns, 1.0 [fixed]
    counter pulse on channel 3 at 300ns, square, 100ns, 1.0
    """
    
    # Parse and build
    parser = SequenceTextParser()
    description = parser.parse_text(sequence_text)
    
    builder = SequenceBuilder(sample_rate=1e9)
    sequences = builder.build_scan_sequences(description)
    
    # Test static plot
    fig = builder.plot_sequence(sequences[0], title="Test Sequence")
    print("✓ Static plot created successfully")
    
    # Save the plot
    fig.savefig("test_sequence_plot.png", dpi=300, bbox_inches='tight')
    print("✓ Plot saved as test_sequence_plot.png")
    
    return fig

def test_animation():
    """Test the animate_scan_sequences method."""
    print("Testing animation...")
    
    # Create a sequence with variable scanning
    sequence_text = """
    sequence: variable_scan, type=custom, duration=1000ns, sample_rate=1GHz, repeat_count=50000
    
    variable: pulse_duration, start=100ns, stop=500ns, steps=5
    
    pi/2 pulse on channel 1 at 0ns, gaussian, pulse_duration, 1.0
    laser pulse on channel 2 at 200ns, square, 50ns, 1.0 [fixed]
    counter pulse on channel 3 at 300ns, square, 100ns, 1.0
    trigger pulse on channel 5 at 600ns, square, 50ns, 1.0
    """
    
    # Parse and build
    parser = SequenceTextParser()
    description = parser.parse_text(sequence_text)
    
    builder = SequenceBuilder(sample_rate=1e9)
    sequences = builder.build_scan_sequences(description)
    
    # Test animation
    anim = builder.animate_scan_sequences(sequences, title="Variable Scan Test", interval=1500)
    print("✓ Animation created successfully")
    
    # Show the animation
    plt.show()
    
    return anim

def main():
    """Run all tests."""
    print("Testing SequenceBuilder visualization methods...")
    print("=" * 50)
    
    try:
        # Test static plotting
        fig = test_static_plot()
        
        # Test animation
        anim = test_animation()
        
        print("\n" + "=" * 50)
        print("✓ All visualization tests passed!")
        print("\nUsage examples:")
        print("1. Static plot: builder.plot_sequence(sequence, title='My Sequence')")
        print("2. Animation: builder.animate_scan_sequences(sequences, title='Scan')")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
