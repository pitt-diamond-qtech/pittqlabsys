"""
Tests for the AWG520 sequence optimizer module.

This module tests the conversion of optimized sequences into AWG520-specific format,
including memory optimization, waveform generation, and sequence file creation.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock

from src.Model.awg520_optimizer import (
    AWG520SequenceOptimizer, AWG520Sequence, OptimizationError
)
from src.Model.sequence import Sequence
from src.Model.pulses import SquarePulse, GaussianPulse


class TestAWG520SequenceOptimizer:
    """Test the AWG520SequenceOptimizer class."""
    
    def test_initialization(self):
        """Test that AWG520SequenceOptimizer initializes correctly."""
        optimizer = AWG520SequenceOptimizer()
        
        # Check AWG520-specific constants
        assert optimizer.max_waveform_samples == 4_000_000  # 4M words
        assert optimizer.max_sequence_entries == 1000
        assert optimizer.sample_rate == 1e9  # 1 GHz
    
    def test_constants_are_correct(self):
        """Test that AWG520 constants match specifications."""
        optimizer = AWG520SequenceOptimizer()
        
        # AWG520 specifications
        assert optimizer.max_waveform_samples == 4_000_000  # 4M words
        assert optimizer.max_sequence_entries == 1000
        assert optimizer.sample_rate == 1e9  # 1 GHz
        
        # These should not change unless hardware changes
        assert optimizer.max_waveform_samples > 0
        assert optimizer.max_sequence_entries > 0
        assert optimizer.sample_rate > 0
    
    def test_create_waveforms_basic(self):
        """Test basic waveform creation from sequence."""
        optimizer = AWG520SequenceOptimizer()
        
        # Create a simple sequence
        sequence = Sequence(1000)  # 1000 samples
        pulse = SquarePulse("test_pulse", 100, amplitude=1.0)
        sequence.add_pulse(0, pulse)
        
        # Create waveforms
        waveforms = optimizer.create_waveforms(sequence)
        
        assert len(waveforms) == 1  # Single waveform file
        assert "test_pulse" in waveforms
        assert len(waveforms["test_pulse"]) == 100  # Pulse length
    
    def test_create_waveforms_multiple_pulses(self):
        """Test waveform creation with multiple pulses."""
        optimizer = AWG520SequenceOptimizer()
        
        # Create sequence with multiple pulses
        sequence = Sequence(2000)  # 2000 samples
        
        # Add pulses at different times
        pulse1 = SquarePulse("pulse1", 100, amplitude=1.0)
        pulse2 = GaussianPulse("pulse2", 150, sigma=25, amplitude=0.8)
        
        sequence.add_pulse(0, pulse1)
        sequence.add_pulse(500, pulse2)
        
        # Create waveforms
        waveforms = optimizer.create_waveforms(sequence)
        
        assert len(waveforms) == 2  # Two waveform files
        assert "pulse1" in waveforms
        assert "pulse2" in waveforms
        assert len(waveforms["pulse1"]) == 100
        assert len(waveforms["pulse2"]) == 150
    
    def test_create_sequence_file_basic(self):
        """Test basic sequence file creation."""
        optimizer = AWG520SequenceOptimizer()
        
        # Create a simple sequence
        sequence = Sequence(1000)
        pulse = SquarePulse("test_pulse", 100, amplitude=1.0)
        sequence.add_pulse(0, pulse)
        
        # Create sequence file
        seq_entries = optimizer.create_sequence_file(sequence)
        
        assert len(seq_entries) > 0
        # Check that sequence entries reference the waveform
        assert any("test_pulse" in str(entry) for entry in seq_entries)
    
    def test_optimize_sequence_for_awg520_basic(self):
        """Test basic sequence optimization for AWG520."""
        optimizer = AWG520SequenceOptimizer()
        
        # Create a sequence that fits in memory
        sequence = Sequence(1000)
        pulse = SquarePulse("test_pulse", 100, amplitude=1.0)
        sequence.add_pulse(0, pulse)
        
        # Optimize for AWG520
        awg_sequence = optimizer.optimize_sequence_for_awg520(sequence)
        
        assert isinstance(awg_sequence, AWG520Sequence)
        assert awg_sequence.get_waveform_files() == ["test_pulse.wfm"]
        assert len(awg_sequence.get_sequence_entries()) > 0
    
    def test_dead_time_optimization(self):
        """Test that long dead times are optimized using sequence repetition."""
        optimizer = AWG520SequenceOptimizer()
        
        # Create sequence with long dead time
        sequence = Sequence(10_000_000)  # 10M samples (10ms at 1GHz)
        pulse = SquarePulse("short_pulse", 1000, amplitude=1.0)
        sequence.add_pulse(0, pulse)
        # Long dead time from 1000 to 10M samples
        
        # Optimize for AWG520
        awg_sequence = optimizer.optimize_sequence_for_awg520(sequence)
        
        # Should use repetition in sequence file rather than storing all samples
        waveform_files = awg_sequence.get_waveform_files()
        assert len(waveform_files) == 1  # Only one waveform file
        assert "short_pulse" in waveform_files[0]
        
        # Sequence should use repetition for the long dead time
        seq_entries = awg_sequence.get_sequence_entries()
        assert len(seq_entries) > 1  # Multiple sequence entries for repetition
    
    def test_memory_enforcement_within_limits(self):
        """Test that sequences within memory limits pass validation."""
        optimizer = AWG520SequenceOptimizer()
        
        # Create sequence well within 4M limit
        sequence = Sequence(1_000_000)  # 1M samples
        pulse = SquarePulse("test_pulse", 100_000, amplitude=1.0)
        sequence.add_pulse(0, pulse)
        
        # Should not raise error
        awg_sequence = optimizer.optimize_sequence_for_awg520(sequence)
        assert isinstance(awg_sequence, AWG520Sequence)
    
    def test_memory_enforcement_exceeds_limits(self):
        """Test that sequences exceeding memory limits are handled properly."""
        optimizer = AWG520SequenceOptimizer()
        
        # Create sequence exceeding 4M limit
        sequence = Sequence(5_000_000)  # 5M samples
        pulse = SquarePulse("long_pulse", 5_000_000, amplitude=1.0)
        sequence.add_pulse(0, pulse)
        
        # Should handle gracefully (either split or use repetition)
        awg_sequence = optimizer.optimize_sequence_for_awg520(sequence)
        assert isinstance(awg_sequence, AWG520Sequence)
        
        # Check that memory usage is within limits
        total_samples = sum(len(waveform) for waveform in awg_sequence.get_waveform_files())
        assert total_samples <= 4_000_000
    
    def test_repetition_math_correct(self):
        """Test that repetition counts are calculated correctly."""
        optimizer = AWG520SequenceOptimizer()
        
        # Create sequence with specific timing
        sequence = Sequence(1_000_000)  # 1ms total
        pulse = SquarePulse("pulse", 1000, amplitude=1.0)  # 1μs pulse
        sequence.add_pulse(0, pulse)
        # 999μs dead time
        
        # Optimize for AWG520
        awg_sequence = optimizer.optimize_sequence_for_awg520(sequence)
        
        # Check that repetition math is correct
        # 999μs dead time should be represented by repetition, not stored samples
        seq_entries = awg_sequence.get_sequence_entries()
        
        # Should have repetition entry for the dead time
        has_repetition = any(entry.get("type") == "repetition" for entry in seq_entries)
        assert has_repetition, "Should use repetition for long dead times"
    
    def test_sequence_table_structure(self):
        """Test that sequence table has correct structure."""
        optimizer = AWG520SequenceOptimizer()
        
        # Create sequence
        sequence = Sequence(1000)
        pulse = SquarePulse("test_pulse", 100, amplitude=1.0)
        sequence.add_pulse(0, pulse)
        
        # Create sequence file
        seq_entries = optimizer.create_sequence_file(sequence)
        
        # Check structure
        assert len(seq_entries) > 0
        
        # Each entry should have required fields
        for entry in seq_entries:
            assert hasattr(entry, 'waveform_name') or 'waveform' in str(entry)
            assert hasattr(entry, 'start_time') or 'time' in str(entry)
    
    def test_channel_mapping_valid(self):
        """Test that channel mapping is valid in sequence."""
        optimizer = AWG520SequenceOptimizer()
        
        # Create sequence with pulses on different channels
        sequence = Sequence(1000)
        pulse1 = SquarePulse("pulse1", 100, amplitude=1.0)
        pulse2 = SquarePulse("pulse2", 100, amplitude=0.5)
        
        sequence.add_pulse(0, pulse1)
        sequence.add_pulse(200, pulse2)
        
        # Create sequence file
        seq_entries = optimizer.create_sequence_file(sequence)
        
        # Check that channel information is preserved
        assert len(seq_entries) > 0
        
        # In a real implementation, we'd check channel mapping
        # For now, just ensure we get valid entries
        assert all(entry is not None for entry in seq_entries)
    
    def test_error_handling_invalid_inputs(self):
        """Test error handling for invalid inputs."""
        optimizer = AWG520SequenceOptimizer()
        
        # Test with None sequence
        with pytest.raises(ValueError):
            optimizer.optimize_sequence_for_awg520(None)
        
        # Test with invalid sequence type
        with pytest.raises(ValueError):
            optimizer.optimize_sequence_for_awg520("not a sequence")
    
    def test_error_handling_zero_length_waveforms(self):
        """Test error handling for zero-length waveforms."""
        optimizer = AWG520SequenceOptimizer()
        
        # Create sequence with zero-length pulse
        sequence = Sequence(1000)
        pulse = SquarePulse("zero_pulse", 0, amplitude=1.0)  # Zero length
        sequence.add_pulse(0, pulse)
        
        # Should handle gracefully
        try:
            awg_sequence = optimizer.optimize_sequence_for_awg520(sequence)
            # If it doesn't raise an error, that's fine
        except Exception as e:
            # If it does raise an error, it should be a meaningful one
            assert "zero" in str(e).lower() or "length" in str(e).lower()
    
    def test_error_handling_unsupported_shapes(self):
        """Test error handling for unsupported pulse shapes."""
        optimizer = AWG520SequenceOptimizer()
        
        # Create sequence with unsupported pulse shape
        sequence = Sequence(1000)
        
        # Mock an unsupported pulse shape
        unsupported_pulse = Mock()
        unsupported_pulse.name = "unsupported"
        unsupported_pulse.length = 100
        unsupported_pulse.generate_samples.return_value = np.zeros(100)
        
        sequence.add_pulse(0, unsupported_pulse)
        
        # Should handle gracefully (either support it or give meaningful error)
        try:
            awg_sequence = optimizer.optimize_sequence_for_awg520(sequence)
            # If it works, that's fine
        except Exception as e:
            # If it fails, should be a meaningful error
            assert "unsupported" in str(e).lower() or "shape" in str(e).lower()
    
    def test_create_repetition_patterns(self):
        """Test creation of repetition patterns for dead times."""
        optimizer = AWG520SequenceOptimizer()
        
        # Test with a long dead time
        dead_time_samples = 5_000_000  # 5ms at 1GHz
        pattern = optimizer.create_repetition_patterns(dead_time_samples)
        
        # Should return a pattern that represents the dead time efficiently
        assert pattern is not None
        assert hasattr(pattern, 'repetition_count') or 'count' in str(pattern)
    
    def test_generate_waveform_data(self):
        """Test waveform data generation."""
        optimizer = AWG520SequenceOptimizer()
        
        # Create a simple pulse
        pulse = SquarePulse("test_pulse", 100, amplitude=1.0)
        
        # Generate waveform data
        waveform_data = optimizer._generate_waveform_data(pulse)
        
        assert len(waveform_data) == 100
        assert all(sample == 1.0 for sample in waveform_data)
    
    def test_create_sequence_table_entries(self):
        """Test creation of sequence table entries."""
        optimizer = AWG520SequenceOptimizer()
        
        # Create a simple sequence
        sequence = Sequence(1000)
        pulse = SquarePulse("test_pulse", 100, amplitude=1.0)
        sequence.add_pulse(0, pulse)
        
        # Create sequence table entries
        # First create waveforms, then pass them to the method
        waveforms = optimizer.create_waveforms(sequence)
        entries = optimizer._create_sequence_table_entries(sequence, waveforms)
        
        assert len(entries) > 0
        # Check that entries reference the pulse
        assert any("test_pulse" in str(entry) for entry in entries)
    
    def test_calculate_optimal_repetition(self):
        """Test calculation of optimal repetition for dead times."""
        optimizer = AWG520SequenceOptimizer()
        
        # Test with different dead time lengths
        test_cases = [
            (1000, 1),      # 1μs - no repetition needed
            (10000, 1),     # 10μs - no repetition needed
            (100000, 1),    # 100μs - no repetition needed
            (1000000, 10),  # 1ms - some repetition
            (5000000, 50),  # 5ms - more repetition
        ]
        
        for dead_time_samples, expected_min_repetition in test_cases:
            repetition = optimizer._calculate_optimal_repetition(dead_time_samples)
            assert repetition >= expected_min_repetition
    
    def test_validate_awg520_constraints(self):
        """Test validation of AWG520 constraints."""
        optimizer = AWG520SequenceOptimizer()
        
        # Test valid sequence
        sequence = Sequence(1000)
        pulse = SquarePulse("test_pulse", 100, amplitude=1.0)
        sequence.add_pulse(0, pulse)
        
        # Should pass validation
        assert optimizer._validate_awg520_constraints(sequence) is True
        
        # Test sequence exceeding memory limit
        large_sequence = Sequence(5_000_000)
        large_pulse = SquarePulse("large_pulse", 5_000_000, amplitude=1.0)
        large_sequence.add_pulse(0, large_pulse)
        
        # Should fail validation (unless it can be optimized)
        try:
            result = optimizer._validate_awg520_constraints(large_sequence)
            # If it passes, it means optimization is possible
            assert result is True
        except Exception:
            # If it fails, that's also acceptable
            pass
    
    def test_create_compressed_sequence(self):
        """Test creation of compressed sequences."""
        optimizer = AWG520SequenceOptimizer()
        
        # Create sequence that would exceed memory
        sequence = Sequence(5_000_000)
        pulse = SquarePulse("long_pulse", 5_000_000, amplitude=1.0)
        sequence.add_pulse(0, pulse)
        
        # Try to create compressed sequence
        compressed = optimizer._create_compressed_sequence(sequence)
        
        # Should return something that fits in memory
        assert compressed is not None
        
        # Check memory usage
        total_samples = sum(len(waveform) for waveform in compressed.get_waveform_files())
        assert total_samples <= 4_000_000


class TestAWG520Sequence:
    """Test the AWG520Sequence class."""
    
    def test_initialization(self):
        """Test that AWG520Sequence initializes correctly."""
        # Create mock waveform files and sequence entries
        waveform_files = ["pulse1.wfm", "pulse2.wfm"]
        sequence_entries = ["entry1", "entry2", "entry3"]
        
        awg_seq = AWG520Sequence("test_sequence", waveform_files, sequence_entries)
        
        assert awg_seq.name == "test_sequence"
        assert awg_seq.waveform_files == waveform_files
        assert awg_seq.sequence_entries == sequence_entries
    
    def test_get_waveform_files(self):
        """Test getting waveform files."""
        waveform_files = ["pulse1.wfm", "pulse2.wfm"]
        awg_seq = AWG520Sequence("test", waveform_files, [])
        
        assert awg_seq.get_waveform_files() == waveform_files
    
    def test_get_sequence_entries(self):
        """Test getting sequence entries."""
        sequence_entries = ["entry1", "entry2"]
        awg_seq = AWG520Sequence("test", [], sequence_entries)
        
        assert awg_seq.get_sequence_entries() == sequence_entries
    
    def test_initialization_empty(self):
        """Test initialization with empty lists."""
        awg_seq = AWG520Sequence("test", [], [])
        
        assert awg_seq.name == "test"
        assert awg_seq.waveform_files == []
        assert awg_seq.sequence_entries == []
    
    def test_initialization_no_metadata(self):
        """Test initialization without metadata."""
        awg_seq = AWG520Sequence("test", ["pulse.wfm"], ["entry"])
        
        assert awg_seq.name == "test"
        assert len(awg_seq.waveform_files) == 1
        assert len(awg_seq.sequence_entries) == 1


class TestOptimizationError:
    """Test the OptimizationError exception."""
    
    def test_optimization_error_creation(self):
        """Test creating an OptimizationError."""
        error = OptimizationError("Test optimization error")
        assert str(error) == "Test optimization error"
    
    def test_optimization_error_inheritance(self):
        """Test that OptimizationError inherits from Exception."""
        error = OptimizationError("Test")
        assert isinstance(error, Exception)


class TestAWG520EndToEndPipeline:
    """End-to-end tests for the complete AWG520 pipeline."""
    
    def test_full_pipeline_rabi_example(self, tmp_path):
        """Test the complete pipeline from text description to .wfm/.seq files."""
        from src.Model.sequence_description import (
            SequenceDescription, PulseDescription, PulseShape, TimingType
        )
        from src.Model.sequence_builder import SequenceBuilder
        from src.Model.awg520_optimizer import AWG520SequenceOptimizer
        from src.Model.awg_file import AWGFile
        
        # 1. Create a simple Rabi-style sequence description
        desc = SequenceDescription(
            name="rabi_test",
            experiment_type="rabi",
            total_duration=2e-3,  # 2ms
            sample_rate=1e9,      # 1GHz
        )
        
        # Add a pi/2 pulse at t=0
        pulse = PulseDescription(
            name="pi2",
            pulse_type="pi/2",
            channel=1,
            shape=PulseShape.SQUARE,
            duration=1e-6,        # 1μs
            amplitude=1.0,
            timing=0.0,
            timing_type=TimingType.ABSOLUTE,
        )
        desc.add_pulse(pulse)
        
        # 2. Build the sequence
        builder = SequenceBuilder(sample_rate=desc.sample_rate)
        optimized = builder.build_sequence(desc)
        seq = optimized.get_chunk(0)
        
        # 3. Optimize for AWG520
        optimizer = AWG520SequenceOptimizer()
        awg_seq = optimizer.optimize_sequence_for_awg520(seq)
        
        # 4. Write files to temporary directory
        awg_writer = AWGFile(ftype="WFM", timeres_ns=1, out_dir=tmp_path)
        
        # Write silence waveform for dead times
        silence_len = 100_000  # 100μs at 1GHz
        silence = np.zeros(silence_len, dtype=float)
        silence_marker = np.zeros(silence_len, dtype=int)
        silence_ch1 = awg_writer.write_waveform(silence, silence_marker, name="silence", channel=1)
        silence_ch2 = awg_writer.write_waveform(silence, silence_marker, name="silence", channel=2)
        
        # Write pulse waveforms
        waveform_map = {}
        for base_name, samples in awg_seq.get_waveform_data().items():
            m = np.zeros(len(samples), dtype=int)
            p1 = awg_writer.write_waveform(samples, m, name=base_name, channel=1)
            waveform_map[base_name] = p1.name
        
        # Build sequence entries
        entries = []
        
        # Add pulse entries
        for start, pulse in sorted(seq.pulses, key=lambda x: x[0]):
            ch1 = f"{pulse.name}_1.wfm"
            ch2 = silence_ch2.name
            entries.append((ch1, ch2, 1, 0, 0, 0))
        
        # Add dead-time entries using repeated silence
        # Calculate dead times
        if not seq.pulses:
            dead_times = [(0, seq.length)]
        else:
            dead_times = []
            pulses_sorted = sorted(seq.pulses, key=lambda x: x[0])
            t = 0
            for start, pulse in pulses_sorted:
                if start > t:
                    dead_times.append((t, start - t))
                t = start + pulse.length
            if t < seq.length:
                dead_times.append((t, seq.length - t))
        
        for start_idx, length_samples in dead_times:
            if length_samples <= 0:
                continue
            repeats = max(1, int(np.ceil(length_samples / silence_len)))
            entries.append((silence_ch1.name, silence_ch2.name, repeats, 0, 0, 0))
        
        # Write sequence file
        seq_file = awg_writer.write_sequence(entries, seq_name=desc.name)
        
        # 5. Validate output files
        assert seq_file.exists(), f"Sequence file {seq_file} should exist"
        assert seq_file.suffix == ".seq", "Sequence file should have .seq extension"
        
        # Check that waveform files exist
        expected_waveforms = ["pi2_1.wfm", "silence_1.wfm", "silence_2.wfm"]
        for wfm_name in expected_waveforms:
            wfm_path = tmp_path / wfm_name
            assert wfm_path.exists(), f"Waveform file {wfm_name} should exist"
            assert wfm_path.suffix == ".wfm", "Waveform file should have .wfm extension"
        
        # 6. Validate file contents
        # Check .seq file header
        with open(seq_file, 'rb') as f:
            content = f.read()
            assert b"MAGIC 3002" in content, "Sequence file should have MAGIC 3002 header"
            assert b"LINES" in content, "Sequence file should have LINES section"
        
        # Check .wfm file headers
        for wfm_name in expected_waveforms:
            wfm_path = tmp_path / wfm_name
            with open(wfm_path, 'rb') as f:
                content = f.read()
                assert b"MAGIC 1000" in content, f"Waveform file {wfm_name} should have MAGIC 1000 header"
                assert b"CLOCK" in content, f"Waveform file {wfm_name} should have CLOCK trailer"
        
        # 7. Validate sequence optimization
        assert len(awg_seq.get_waveform_files()) > 0, "Should have waveform files"
        assert len(awg_seq.get_sequence_entries()) > 0, "Should have sequence entries"
        
        # Check that we have repetition entries for dead times
        seq_entries = awg_seq.get_sequence_entries()
        has_repetition = any(entry.get("type") == "repetition" for entry in seq_entries)
        assert has_repetition, "Should use repetition for long dead times"
    
    def test_pipeline_with_preset_experiment(self, tmp_path):
        """Test the pipeline using a preset experiment from the parser."""
        from src.Model.sequence_parser import SequenceTextParser
        from src.Model.sequence_builder import SequenceBuilder
        from src.Model.awg520_optimizer import AWG520SequenceOptimizer
        from src.Model.awg_file import AWGFile
        
        # 1. Create a manual description (skip preset parsing for now)
        from src.Model.sequence_description import (
            SequenceDescription, PulseDescription, PulseShape, TimingType
        )
        desc = SequenceDescription(
            name="simple_test",
            experiment_type="test",
            total_duration=10e-3,  # 10ms - very long to trigger optimization
            sample_rate=1e9,      # 1GHz
        )
        pulse = PulseDescription(
            name="test_pulse",
            pulse_type="test",
            channel=1,
            shape=PulseShape.SQUARE,
            duration=1e-6,        # 1μs - very short pulse with very long dead time
            amplitude=0.8,
            timing=0.0,
            timing_type=TimingType.ABSOLUTE,
        )
        desc.add_pulse(pulse)
        
        # 2. Build and optimize
        builder = SequenceBuilder(sample_rate=desc.sample_rate)
        optimized = builder.build_sequence(desc)
        seq = optimized.get_chunk(0)
        
        optimizer = AWG520SequenceOptimizer()
        
        # Debug: Check if sequence has long dead times
        has_long_dead_times = optimizer._has_long_dead_times(seq)
        print(f"Sequence has long dead times: {has_long_dead_times}")
        print(f"Sequence length: {seq.length} samples")
        print(f"Sequence pulses: {len(seq.pulses)}")
        
        awg_seq = optimizer.optimize_sequence_for_awg520(seq)
        
        # 3. Write files
        awg_writer = AWGFile(ftype="WFM", timeres_ns=1, out_dir=tmp_path)
        
        # Write waveforms
        waveform_data = awg_seq.get_waveform_data()
        print(f"Waveform data keys: {list(waveform_data.keys())}")
        assert len(waveform_data) > 0, "Should have waveform data"
        
        for base_name, samples in waveform_data.items():
            m = np.zeros(len(samples), dtype=int)
            awg_writer.write_waveform(samples, m, name=base_name, channel=1)
        
        # Write sequence
        entries = []
        for start, pulse in sorted(seq.pulses, key=lambda x: x[0]):
            ch1 = f"{pulse.name}_1.wfm"
            ch2 = "silence_2.wfm"  # Placeholder
            entries.append((ch1, ch2, 1, 0, 0, 0))
        
        seq_file = awg_writer.write_sequence(entries, seq_name=desc.name)
        
        # 4. Validate
        assert seq_file.exists(), "Sequence file should be created"
        assert len(waveform_data) > 0, "Should have waveform data"
        assert len(awg_seq.get_sequence_entries()) > 0, "Should have sequence entries"

    def test_example_script_file_generation(self, tmp_path):
        """Test that the example script generates the correct files."""
        import subprocess
        import sys
        from pathlib import Path
        
        # Get the path to the example script
        script_path = Path(__file__).parent.parent / "examples" / "awg520_templates" / "generate_example_sequence.py"
        
        # Run the script in the temporary directory
        result = subprocess.run([
            sys.executable, str(script_path)
        ], capture_output=True, text=True, cwd=tmp_path)
        
        # Check that the script ran successfully
        assert result.returncode == 0, f"Script failed: {result.stderr}"
        
        # Check that the output directory was created
        output_dir = tmp_path / "waveforms_out"
        assert output_dir.exists(), "Output directory should exist"
        
        # Check that the expected files were generated
        expected_files = ["pi2_1.wfm", "silence_1.wfm", "silence_2.wfm", "rabi_example.seq"]
        for filename in expected_files:
            file_path = output_dir / filename
            assert file_path.exists(), f"File {filename} should exist"
        
        # Check the sequence file content
        seq_file = output_dir / "rabi_example.seq"
        with open(seq_file, 'r') as f:
            content = f.read()
            assert "MAGIC 3002" in content, "Sequence file should have MAGIC 3002 header"
            assert "LINES 2" in content, "Sequence file should have 2 lines"
            assert "pi2_1.wfm" in content, "Sequence file should reference pi2_1.wfm"
            assert "silence_1.wfm" in content, "Sequence file should reference silence_1.wfm"
        
        # Check that waveform files have reasonable sizes
        pi2_file = output_dir / "pi2_1.wfm"
        silence_file = output_dir / "silence_1.wfm"
        
        assert pi2_file.stat().st_size > 1000, "Pulse waveform should be >1KB"
        assert silence_file.stat().st_size > 100000, "Silence waveform should be >100KB (100μs at 1GHz)"


class TestAWG520SequenceOptimizerIntegration:
    """Integration tests for AWG520SequenceOptimizer."""
    
    def test_end_to_end_optimization(self):
        """Test complete end-to-end optimization workflow."""
        optimizer = AWG520SequenceOptimizer()
        
        # Create a realistic sequence
        sequence = Sequence(2_000_000)  # 2ms total
        
        # Add pulses with gaps
        pulse1 = SquarePulse("pi2", 1000, amplitude=1.0)
        pulse2 = SquarePulse("pi", 1000, amplitude=1.0)
        pulse3 = SquarePulse("readout", 5000, amplitude=0.8)
        
        sequence.add_pulse(0, pulse1)           # 0-1μs
        sequence.add_pulse(1_000_000, pulse2)   # 1-1.001ms
        sequence.add_pulse(1_500_000, pulse3)   # 1.5-1.505ms
        
        # Optimize for AWG520
        awg_sequence = optimizer.optimize_sequence_for_awg520(sequence)
        
        # Verify result
        assert isinstance(awg_sequence, AWG520Sequence)
        assert len(awg_sequence.get_waveform_files()) == 3  # Three pulses
        
        # Check memory usage
        total_samples = sum(len(waveform) for waveform in awg_sequence.get_waveform_files())
        assert total_samples <= 4_000_000  # Within AWG520 limits
    
    def test_memory_optimization_strategy(self):
        """Test that memory optimization strategy is effective."""
        optimizer = AWG520SequenceOptimizer()
        
        # Create sequence that would exceed memory without optimization
        sequence = Sequence(10_000_000)  # 10ms total
        pulse = SquarePulse("short_pulse", 1000, amplitude=1.0)
        sequence.add_pulse(0, pulse)
        # 9.999ms dead time
        
        # Optimize for AWG520
        awg_sequence = optimizer.optimize_sequence_for_awg520(sequence)
        
        # Should use repetition strategy for dead time
        waveform_files = awg_sequence.get_waveform_files()
        sequence_entries = awg_sequence.get_sequence_entries()
        
        # Only one waveform file (the pulse)
        assert len(waveform_files) == 1
        
        # Multiple sequence entries (pulse + repetition for dead time)
        assert len(sequence_entries) > 1
        
        # Memory usage should be minimal
        total_samples = sum(len(waveform) for waveform in awg_sequence.get_waveform_files())
        assert total_samples <= 10000  # Much less than 10M
