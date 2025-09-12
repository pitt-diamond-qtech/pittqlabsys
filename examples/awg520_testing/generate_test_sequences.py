#!/usr/bin/env python3
"""
AWG520 Test Sequence Generator

This script generates test sequence files (.seq) and waveform files (.wfm)
for testing AWG520 external trigger functionality and compression.
"""

import sys
import numpy as np
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.Model.awg_file import AWGFile
    from src.Model.sequence import Sequence
    from src.Model.pulses import SquarePulse, GaussianPulse, SechPulse
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please check that the required modules are available.")
    sys.exit(1)


class AWG520TestGenerator:
    """Generate test sequences and waveforms for AWG520 testing."""
    
    def __init__(self, output_dir="test_output"):
        """Initialize test generator."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # AWG520 parameters
        self.sample_rate = 1e9  # 1 GHz
        self.max_samples = 4_194_304  # 4M samples
        
        print(f"🔧 AWG520 Test Generator initialized")
        print(f"📁 Output directory: {self.output_dir}")
        print(f"⚡ Sample rate: {self.sample_rate/1e9:.1f} GHz")
        print(f"💾 Max samples: {self.max_samples:,}")
    
    def create_test_waveforms(self):
        """Create test waveform files."""
        print("\n📊 Creating Test Waveforms")
        print("=" * 40)
        
        waveforms = []
        
        # 1. Simple square pulse (100ns)
        print("Creating test_pulse_1.wfm (100ns square)...")
        seq = Sequence(int(100e-9 * self.sample_rate))
        pulse = SquarePulse("test_pulse_1", int(100e-9 * self.sample_rate), amplitude=1.0)
        seq.add_pulse(0, pulse)
        
        wfm_path = self.output_dir / "test_pulse_1.wfm"
        AWGFile.write_waveform(seq, wfm_path)
        waveforms.append(("test_pulse_1.wfm", "100ns square pulse, 1V amplitude"))
        print(f"   ✅ Saved: {wfm_path}")
        
        # 2. Gaussian pulse (200ns)
        print("Creating test_pulse_2.wfm (200ns Gaussian)...")
        seq = Sequence(int(200e-9 * self.sample_rate))
        pulse = GaussianPulse("test_pulse_2", int(200e-9 * self.sample_rate), sigma=50, amplitude=0.8)
        seq.add_pulse(0, pulse)
        
        wfm_path = self.output_dir / "test_pulse_2.wfm"
        AWGFile.write_waveform(seq, wfm_path)
        waveforms.append(("test_pulse_2.wfm", "200ns Gaussian pulse, 0.8V amplitude"))
        print(f"   ✅ Saved: {wfm_path}")
        
        # 3. Sech pulse (150ns)
        print("Creating test_pulse_3.wfm (150ns sech)...")
        seq = Sequence(int(150e-9 * self.sample_rate))
        pulse = SechPulse("test_pulse_3", int(150e-9 * self.sample_rate), amplitude=0.9)
        seq.add_pulse(0, pulse)
        
        wfm_path = self.output_dir / "test_pulse_3.wfm"
        AWGFile.write_waveform(seq, wfm_path)
        waveforms.append(("test_pulse_3.wfm", "150ns sech pulse, 0.9V amplitude"))
        print(f"   ✅ Saved: {wfm_path}")
        
        # 4. Short pulse for compression test (1ns)
        print("Creating short_pulse.wfm (1ns square)...")
        seq = Sequence(int(1e-9 * self.sample_rate))
        pulse = SquarePulse("short_pulse", int(1e-9 * self.sample_rate), amplitude=1.0)
        seq.add_pulse(0, pulse)
        
        wfm_path = self.output_dir / "short_pulse.wfm"
        AWGFile.write_waveform(seq, wfm_path)
        waveforms.append(("short_pulse.wfm", "1ns square pulse, 1V amplitude"))
        print(f"   ✅ Saved: {wfm_path}")
        
        # 5. Dead time 1μs (1000 samples of zeros)
        print("Creating dead_time_1us.wfm (1μs of zeros)...")
        seq = Sequence(int(1e-6 * self.sample_rate))
        # No pulses = all zeros
        
        wfm_path = self.output_dir / "dead_time_1us.wfm"
        AWGFile.write_waveform(seq, wfm_path)
        waveforms.append(("dead_time_1us.wfm", "1μs dead time (1000 samples of zeros)"))
        print(f"   ✅ Saved: {wfm_path}")
        
        # 6. Long pulse (1μs)
        print("Creating long_pulse.wfm (1μs square)...")
        seq = Sequence(int(1e-6 * self.sample_rate))
        pulse = SquarePulse("long_pulse", int(1e-6 * self.sample_rate), amplitude=1.0)
        seq.add_pulse(0, pulse)
        
        wfm_path = self.output_dir / "long_pulse.wfm"
        AWGFile.write_waveform(seq, wfm_path)
        waveforms.append(("long_pulse.wfm", "1μs square pulse, 1V amplitude"))
        print(f"   ✅ Saved: {wfm_path}")
        
        # 7. Dead time 10μs (10000 samples of zeros)
        print("Creating dead_time_10us.wfm (10μs of zeros)...")
        seq = Sequence(int(10e-6 * self.sample_rate))
        # No pulses = all zeros
        
        wfm_path = self.output_dir / "dead_time_10us.wfm"
        AWGFile.write_waveform(seq, wfm_path)
        waveforms.append(("dead_time_10us.wfm", "10μs dead time (10000 samples of zeros)"))
        print(f"   ✅ Saved: {wfm_path}")
        
        print(f"\n📋 Created {len(waveforms)} waveform files:")
        for wfm, desc in waveforms:
            print(f"   • {wfm}: {desc}")
        
        return waveforms
    
    def create_test_sequences(self):
        """Create test sequence files."""
        print("\n📝 Creating Test Sequence Files")
        print("=" * 40)
        
        sequences = []
        
        # 1. Basic test sequence
        print("Creating test_basic.seq...")
        basic_seq = [
            ("test_pulse_1.wfm", "test_pulse_1.wfm", 1, "ON", "goto", 2),
            ("test_pulse_2.wfm", "test_pulse_2.wfm", 1, "ON", "goto", 3),
            ("test_pulse_3.wfm", "test_pulse_3.wfm", 1, "ON", "goto", 1)
        ]
        
        seq_path = self.output_dir / "test_basic.seq"
        self._write_sequence_file(basic_seq, seq_path)
        sequences.append(("test_basic.seq", "Basic external trigger test (3 lines)"))
        print(f"   ✅ Saved: {seq_path}")
        
        # 2. Compression test sequence
        print("Creating test_compression.seq...")
        compression_seq = [
            ("short_pulse.wfm", "short_pulse.wfm", 1000, "ON", "goto", 2),      # 1000 reps = 1μs
            ("dead_time_1us.wfm", "dead_time_1us.wfm", 10000, "ON", "goto", 3), # 10000 reps = 10μs
            ("long_pulse.wfm", "long_pulse.wfm", 1000, "ON", "goto", 4),        # 1000 reps = 1μs
            ("dead_time_10us.wfm", "dead_time_10us.wfm", 100000, "ON", "goto", 1) # 100000 reps = 100μs
        ]
        
        seq_path = self.output_dir / "test_compression.seq"
        self._write_sequence_file(compression_seq, seq_path)
        sequences.append(("test_compression.seq", "Compression test with repeat field (4 lines)"))
        print(f"   ✅ Saved: {seq_path}")
        
        # 3. Memory test sequence (test limits)
        print("Creating test_memory.seq...")
        memory_seq = []
        for i in range(100):  # 100 lines to test memory usage
            memory_seq.append((
                "short_pulse.wfm", 
                "short_pulse.wfm", 
                1000, 
                "ON", 
                "goto", 
                (i + 1) % 100 + 1
            ))
        
        seq_path = self.output_dir / "test_memory.seq"
        self._write_sequence_file(memory_seq, seq_path)
        sequences.append(("test_memory.seq", "Memory usage test (100 lines)"))
        print(f"   ✅ Saved: {seq_path}")
        
        print(f"\n📋 Created {len(sequences)} sequence files:")
        for seq, desc in sequences:
            print(f"   • {seq}: {desc}")
        
        return sequences
    
    def _write_sequence_file(self, sequence_data, file_path):
        """Write sequence data to .seq file."""
        with open(file_path, 'w') as f:
            for line in sequence_data:
                f.write(f"{line[0]},{line[1]},{line[2]},{line[3]},{line[4]},{line[5]}\n")
    
    def create_compression_analysis(self):
        """Analyze compression effectiveness."""
        print("\n📊 Compression Analysis")
        print("=" * 40)
        
        # Calculate memory usage for different approaches
        print("Memory usage analysis for different compression strategies:")
        
        # Original approach (no compression)
        dead_time_10ms_samples = int(10e-3 * self.sample_rate)  # 10ms = 10M samples
        original_memory_mb = (dead_time_10ms_samples * 2) / (1024 * 1024)  # 2 bytes per sample
        
        print(f"   Original approach (10ms dead time): {original_memory_mb:.1f} MB")
        
        # Repeat field approach
        dead_time_1us_samples = int(1e-6 * self.sample_rate)  # 1μs = 1000 samples
        repeat_count = dead_time_10ms_samples // dead_time_1us_samples  # 10,000 repeats
        compressed_memory_mb = (dead_time_1us_samples * 2) / (1024 * 1024)  # 1μs waveform
        
        print(f"   Repeat field approach (1μs × {repeat_count:,} reps): {compressed_memory_mb:.3f} MB")
        
        compression_ratio = original_memory_mb / compressed_memory_mb
        print(f"   Compression ratio: {compression_ratio:.0f}:1")
        
        # Check if it fits in AWG520 memory
        if compressed_memory_mb <= 8:  # 8MB limit
            print(f"   ✅ Fits in AWG520 memory ({compressed_memory_mb:.3f} MB ≤ 8 MB)")
        else:
            print(f"   ❌ Exceeds AWG520 memory limit ({compressed_memory_mb:.3f} MB > 8 MB)")
        
        # Test different dead time resolutions
        print(f"\nCompression analysis for different dead time resolutions:")
        resolutions = [1e-6, 10e-6, 100e-6, 1e-3, 10e-3]  # 1μs to 10ms
        
        for resolution in resolutions:
            samples = int(resolution * self.sample_rate)
            memory_mb = (samples * 2) / (1024 * 1024)
            repeats_needed = dead_time_10ms_samples // samples
            
            print(f"   {resolution*1000:.1f}ms resolution: {memory_mb:.3f} MB, {repeats_needed:,} reps")
    
    def create_test_instructions(self):
        """Create test instructions file."""
        print("\n📖 Creating Test Instructions")
        print("=" * 40)
        
        instructions = f"""# AWG520 + ADwin Integration Test Instructions

## Hardware Setup
1. Connect ADwin DIO output to AWG520 TRIG IN using 50Ω BNC cable
2. Connect ADwin GND to AWG520 chassis ground
3. Optional: Use BNC T-connector for oscilloscope monitoring

## AWG520 Configuration
1. SETUP → Trigger → Source = External
2. SETUP → Trigger → Level = 2.5V (for 0→5V TTL)
3. SETUP → Trigger → Impedance = 50Ω
4. SETUP → Run Mode = Enhanced

## Test Procedure

### Test 1: Basic External Trigger
1. Load test_basic.seq into AWG520
2. Press RUN on AWG520
3. Verify AWG520 displays "Waiting"
4. Send trigger pulse from ADwin
5. Verify AWG520 outputs test_pulse_1.wfm
6. Continue for all test pulses

### Test 2: Compression Test
1. Load test_compression.seq into AWG520
2. Press RUN on AWG520
3. Send trigger pulses from ADwin
4. Verify compression works (check memory usage)

### Test 3: Memory Limits
1. Load test_memory.seq into AWG520
2. Check if sequence fits in memory
3. Monitor for memory overflow errors

## Expected Results
- AWG520 responds to external triggers within 100ns
- Waveforms output correctly after each trigger
- Memory usage reduced by repeat field compression
- Sequence fits within AWG520 memory limits

## Troubleshooting
- No trigger response: Check trigger level, impedance, source settings
- Waveform corruption: Verify BNC connections and grounding
- Memory overflow: Reduce repeat counts or sequence complexity
- Timing issues: Check sample rate and sequence configuration

## Files Generated
- test_pulse_*.wfm: Test waveform files
- test_basic.seq: Basic external trigger test
- test_compression.seq: Compression test with repeat field
- test_memory.seq: Memory usage test
"""
        
        instructions_path = self.output_dir / "TEST_INSTRUCTIONS.md"
        with open(instructions_path, 'w') as f:
            f.write(instructions)
        
        print(f"   ✅ Saved: {instructions_path}")
    
    def run_all_tests(self):
        """Run all test generation steps."""
        print("🚀 AWG520 Test Generation Suite")
        print("=" * 60)
        
        try:
            # Create test waveforms
            waveforms = self.create_test_waveforms()
            
            # Create test sequences
            sequences = self.create_test_sequences()
            
            # Analyze compression
            self.create_compression_analysis()
            
            # Create test instructions
            self.create_test_instructions()
            
            print(f"\n🎉 Test generation completed successfully!")
            print(f"📁 All files saved to: {self.output_dir}")
            print(f"📊 Generated {len(waveforms)} waveforms and {len(sequences)} sequences")
            
            return True
            
        except Exception as e:
            print(f"❌ Test generation failed: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """Main function."""
    print("🔧 AWG520 Test Sequence Generator")
    print("=" * 60)
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        output_dir = sys.argv[1]
    else:
        output_dir = "test_output"
    
    # Create generator and run tests
    generator = AWG520TestGenerator(output_dir)
    success = generator.run_all_tests()
    
    if success:
        print(f"\n📋 Next steps:")
        print(f"   1. Transfer files to AWG520")
        print(f"   2. Configure AWG520 for external trigger")
        print(f"   3. Run ADwin trigger tests")
        print(f"   4. Test AWG520 response to triggers")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
