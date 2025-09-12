"""
End-to-end example: Variable scanning with timing adjustments and fixed markers.

This demonstrates the complete variable scanning pipeline:
1. User writes text description with variables and [fixed] markers
2. SequenceTextParser parses it with variable definitions
3. SequenceBuilder builds multiple sequences for each scan point
4. Timing adjustments are applied while respecting [fixed] markers
5. Visualize the sequences with matplotlib animations

This shows how the timing adjusts as variables change while respecting [fixed] markers.
"""

from __future__ import annotations
from pathlib import Path
from typing import List, Tuple
import sys
import os
import numpy as np

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.Model.sequence_parser import SequenceTextParser
from src.Model.sequence_builder import SequenceBuilder
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.patches import Rectangle


def get_user_sequence_text() -> str:
    """Get the user's sequence description with variable scanning.
    
    This demonstrates:
    - Variable scanning with range-based syntax
    - [fixed] markers to prevent timing adjustment
    - Extended pulse parameters (amplitude, phase)
    - Repeat count for experiment statistics
    """
    return """
# Rabi-style sequence with variable scanning
# Scan the pi/2 pulse duration while keeping laser timing fixed
sequence: name=rabi_variable_scan, duration=2ms, sample_rate=1000000000, repeat=50000

# Define scan variable: pulse duration from 100ns to 300ns in 5 steps
variable: pulse_duration, start=100ns, stop=300ns, steps=5

# Pi/2 pulse at t=0 on channel 1 - duration will be scanned
pi/2 pulse on channel 1 at 0ns, gaussian, 100ns, 1.0, amplitude=0.8, phase=45deg

# Laser pulse at t=400ns on channel 2 - timing is [fixed] so it won't move
laser pulse on channel 2 at 400ns, square, 200ns, 1.0 [fixed]

# Counter gate at t=600ns on channel 3 - timing will be adjusted
counter pulse on channel 3 at 600ns, square, 100ns, 1.0

# Extra trigger on channel 5 - to demonstrate flexibility
trigger pulse on channel 5 at 900ns, square, 50ns, 1.0
"""


def main():
    print("=== Variable Scanning Pipeline Demo ===")
    print()

    # 1) USER INTERFACE: Parse user's text description
    print("1. Parsing user text sequence with variables...")
    user_text = get_user_sequence_text()
    print(f"User input:\n{user_text}")
    
    parser = SequenceTextParser()
    desc = parser.parse_text(user_text)
    print(f"✓ Parsed to SequenceDescription: {desc.name} ({desc.experiment_type})")
    print(f"  - Total duration: {desc.total_duration*1000:.1f}ms")
    print(f"  - Sample rate: {desc.sample_rate/1e9:.1f}GHz")
    print(f"  - Pulses: {len(desc.pulses)}")
    print(f"  - Variables: {len(desc.variables)}")
    print(f"  - Repeat count: {desc.repeat_count:,}")
    
    # Show variable details
    for var_name, var_desc in desc.variables.items():
        print(f"    Variable '{var_name}': {var_desc.start_value} to {var_desc.stop_value} in {var_desc.steps} steps")
    print()

    # 2) SEQUENCE BUILDING: Build multiple sequences for each scan point
    print("2. Building scan sequences...")
    builder = SequenceBuilder(sample_rate=desc.sample_rate)
    scan_sequences = builder.build_scan_sequences(desc)
    
    print(f"✓ Built {len(scan_sequences)} sequences for scan points")
    
    # Show details of each sequence
    for i, seq in enumerate(scan_sequences):
        print(f"  Sequence {i}:")
        print(f"    - Length: {seq.length:,} samples")
        print(f"    - Pulses: {len(seq.pulses)}")
        
        # Show pulse timing details
        for j, (start_sample, pulse) in enumerate(seq.pulses):
            start_time_ns = start_sample / 1e9 * 1e9  # Convert to ns
            duration_ns = pulse.length / 1e9 * 1e9
            fixed_marker = " [fixed]" if getattr(pulse, 'fixed_timing', False) else ""
            print(f"      Pulse {j}: {pulse.name} at {start_time_ns:.0f}ns, duration {duration_ns:.0f}ns{fixed_marker}")
    print()

    # 3) VISUALIZATION: Create animated plot of the sequences
    print("3. Creating animated visualization...")
    create_sequence_animation(scan_sequences, desc)
    
    print("✓ Visualization complete! Check the matplotlib window.")
    print("Press 'q' to close the animation.")


def create_sequence_animation(scan_sequences, description):
    """Create an animated visualization of the scan sequences using SequenceBuilder."""
    # Use the new SequenceBuilder animation method
    builder = SequenceBuilder(sample_rate=1e9)
    anim = builder.animate_scan_sequences(
        scan_sequences, 
        title=f"Variable Scan: {description.name}", 
        interval=1000
    )
    
    # Show the animation
    plt.show()
    
    return anim


if __name__ == "__main__":
    main()
