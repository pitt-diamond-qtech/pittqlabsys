#!/usr/bin/env python3
"""
Demo script for SequenceBuilder visualization methods.

This script demonstrates how easy it is to create visualizations
using the new methods in SequenceBuilder.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.Model.sequence_parser import SequenceTextParser
from src.Model.sequence_builder import SequenceBuilder
import matplotlib.pyplot as plt

def demo_static_plot():
    """Demonstrate static plotting."""
    print("=== Static Plot Demo ===")
    
    # Simple sequence
    sequence_text = """
    sequence: simple_demo, type=custom, duration=1000ns, sample_rate=1GHz
    
    pi/2 pulse on channel 1 at 0ns, gaussian, 100ns, 1.0
    laser pulse on channel 2 at 200ns, square, 50ns, 1.0
    counter pulse on channel 3 at 400ns, square, 100ns, 1.0
    """
    
    # Parse and build
    parser = SequenceTextParser()
    description = parser.parse_text(sequence_text)
    
    builder = SequenceBuilder(sample_rate=1e9)
    sequences = builder.build_scan_sequences(description)
    
    # Create static plot
    fig = builder.plot_sequence(
        sequences[0], 
        title="Simple Sequence Demo",
        save_path="demo_static_plot.png"
    )
    
    print("✓ Static plot created and saved as 'demo_static_plot.png'")
    print("✓ Use: builder.plot_sequence(sequence, title='My Title')")
    
    return fig

def demo_animation():
    """Demonstrate animation."""
    print("\n=== Animation Demo ===")
    
    # Sequence with variable scanning
    sequence_text = """
    sequence: animation_demo, type=custom, duration=1000ns, sample_rate=1GHz
    
    variable: pulse_width, start=50ns, stop=150ns, steps=4
    
    pi/2 pulse on channel 1 at 0ns, gaussian, pulse_width, 1.0
    laser pulse on channel 2 at 200ns, square, 50ns, 1.0 [fixed]
    counter pulse on channel 3 at 300ns, square, 100ns, 1.0
    """
    
    # Parse and build
    parser = SequenceTextParser()
    description = parser.parse_text(sequence_text)
    
    builder = SequenceBuilder(sample_rate=1e9)
    sequences = builder.build_scan_sequences(description)
    
    # Create animation
    anim = builder.animate_scan_sequences(
        sequences, 
        title="Animation Demo - Variable Scanning",
        interval=1200  # 1.2 seconds per frame
    )
    
    print("✓ Animation created with 4 scan points")
    print("✓ Use: builder.animate_scan_sequences(sequences, title='My Animation')")
    
    return anim

def demo_gui_integration():
    """Show how this would integrate with a GUI."""
    print("\n=== GUI Integration Demo ===")
    
    # Simulate what a GUI might do
    sequences = []
    titles = []
    
    # Create multiple sequences (like different experiments)
    experiment_configs = [
        ("Rabi Experiment", "rabi_sequence, type=rabi, duration=500ns"),
        ("Spin Echo", "spin_echo, type=echo, duration=1000ns"),
        ("Ramsey", "ramsey, type=ramsey, duration=800ns")
    ]
    
    for exp_name, config in experiment_configs:
        sequence_text = f"""
        sequence: {config}, sample_rate=1GHz
        
        pi/2 pulse on channel 1 at 0ns, gaussian, 100ns, 1.0
        laser pulse on channel 2 at 200ns, square, 50ns, 1.0
        """
        
        parser = SequenceTextParser()
        description = parser.parse_text(sequence_text)
        
        builder = SequenceBuilder(sample_rate=1e9)
        seq_list = builder.build_scan_sequences(description)
        sequences.extend(seq_list)
        titles.extend([f"{exp_name} - {i+1}" for i in range(len(seq_list))])
    
    print(f"✓ Created {len(sequences)} sequences for GUI")
    print("✓ GUI can now:")
    print("  - Show static plots: builder.plot_sequence(seq, title='...')")
    print("  - Create animations: builder.animate_scan_sequences(seqs, title='...')")
    print("  - Save plots: builder.plot_sequence(seq, save_path='...')")
    
    return sequences, titles

def main():
    """Run all demos."""
    print("SequenceBuilder Visualization Demo")
    print("=" * 40)
    
    try:
        # Demo 1: Static plotting
        fig1 = demo_static_plot()
        
        # Demo 2: Animation
        anim = demo_animation()
        
        # Demo 3: GUI integration
        sequences, titles = demo_gui_integration()
        
        print("\n" + "=" * 40)
        print("🎉 All demos completed successfully!")
        print("\nKey Benefits:")
        print("✅ Reusable visualization methods")
        print("✅ Consistent styling across the application")
        print("✅ Easy integration with GUI and other modules")
        print("✅ Hardware-agnostic (works with any sequence)")
        print("✅ Built-in error handling and matplotlib dependency checks")
        
        print("\nNext Steps:")
        print("1. Use these methods in your GUI")
        print("2. Customize colors and styles as needed")
        print("3. Add more visualization features to SequenceBuilder")
        
        # Show the animation
        plt.show()
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
