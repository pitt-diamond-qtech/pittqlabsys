"""
End-to-end example: parse user text, build sequence, optimize for AWG520, and
write .wfm and .seq files.

This demonstrates the complete pipeline that users would actually use:
1. User writes text description
2. SequenceTextParser parses it
3. SequenceBuilder builds Sequence
4. AWG520SequenceOptimizer optimizes for hardware
5. AWGFile writes output files

Outputs are written to examples/awg520_templates/waveforms_out/
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
from src.Model.awg520_optimizer import AWG520SequenceOptimizer
from src.Model.awg_file import AWGFile


def get_user_sequence_text() -> str:
    """Get the user's sequence description in text format.
    
    This is what users would actually write - a simple, human-readable
    description of their pulse sequence.
    """
    return """
# Simple Rabi-style sequence
# One pi/2 pulse followed by a long dead time
sequence: name=rabi_example, duration=2ms, sample_rate=1000000000

# Pi/2 pulse at t=0 on channel 1
pi/2 pulse on channel 1 at 0ms, square, 1us, 1.0
"""


def main():
    # Create output directory relative to current working directory
    out_dir = Path.cwd() / "waveforms_out"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=== AWG520 End-to-End Pipeline Demo ===")
    print()

    # 1) USER INTERFACE: Parse user's text description
    print("1. Parsing user text sequence...")
    user_text = get_user_sequence_text()
    print(f"User input:\n{user_text}")
    
    parser = SequenceTextParser()
    desc = parser.parse_text(user_text)
    print(f"✓ Parsed to SequenceDescription: {desc.name} ({desc.experiment_type})")
    print(f"  - Total duration: {desc.total_duration*1000:.1f}ms")
    print(f"  - Sample rate: {desc.sample_rate/1e9:.1f}GHz")
    print(f"  - Pulses: {len(desc.pulses)}")
    print()

    # 2) SEQUENCE BUILDING: Convert to Sequence object
    print("2. Building sequence...")
    builder = SequenceBuilder(sample_rate=desc.sample_rate)
    optimized = builder.build_sequence(desc)
    seq = optimized.get_chunk(0)
    print(f"✓ Built Sequence: {seq.length:,} samples")
    print(f"  - Pulses: {len(seq.pulses)}")
    print()

    # 3) HARDWARE OPTIMIZATION: Optimize for AWG520
    print("3. Optimizing for AWG520...")
    optimizer = AWG520SequenceOptimizer()
    awg_seq = optimizer.optimize_sequence_for_awg520(seq)
    print(f"✓ Optimized for AWG520")
    print(f"  - Waveform files: {len(awg_seq.get_waveform_files())}")
    print(f"  - Sequence entries: {len(awg_seq.get_sequence_entries())}")
    
    # Debug: Show sequence entries
    print("  - Sequence entries details:")
    for i, entry in enumerate(awg_seq.get_sequence_entries()):
        print(f"    Entry {i}: {entry}")
    print()

    # 4) FILE GENERATION: Write .wfm and .seq files
    print("4. Writing output files...")
    awg_writer = AWGFile(ftype="WFM", timeres_ns=1, out_dir=out_dir)

    # Write pulse waveforms
    waveform_data = awg_seq.get_waveform_data()
    for base_name, samples in waveform_data.items():
        m = np.zeros(len(samples), dtype=int)
        awg_writer.write_waveform(samples, m, name=base_name, channel=1)
        print(f"  ✓ Wrote {base_name}.wfm ({len(samples):,} samples)")

    # Write sequence file
    # Convert dictionary entries to tuple format expected by AWGFile.write_sequence
    # Format: (wfm1, wfm2, repeat, wait, goto, logic)
    seq_entries = []
    for entry in awg_seq.get_sequence_entries():
        if entry.get("type") == "repetition":
            # For repetition entries, use silence waveforms
            wfm1 = "silence_1.wfm"
            wfm2 = "silence_2.wfm"
            repeat = entry.get("repetitions", 1)
        else:
            # For pulse entries, use the actual pulse waveform
            wfm1 = f"{entry.get('waveform_name', 'unknown')}.wfm"
            wfm2 = "silence_2.wfm"  # Channel 2 not used for pulses
            repeat = 1
        
        # Default values for wait, goto, logic
        wait = 0
        goto = 0
        logic = 0
        
        seq_entries.append((wfm1, wfm2, repeat, wait, goto, logic))
    
    seq_file = awg_writer.write_sequence(seq_entries, seq_name=desc.name)
    print(f"  ✓ Wrote {seq_file.name}")

    print()
    print(f"=== Pipeline Complete! ===")
    print(f"Output directory: {out_dir}")
    print(f"Generated files:")
    for file_path in out_dir.glob("*"):
        size_kb = file_path.stat().st_size / 1024
        print(f"  - {file_path.name} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
