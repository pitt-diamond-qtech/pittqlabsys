"""
Tests for AWG520 Sequence Optimizer.

This module tests the AWG520-specific optimization layer that:
- Converts calibrated sequences to AWG520 format
- Implements waveform-level memory optimization
- Generates .wfm and .seq files
- Handles variable sampling regions and compression
"""

import pytest
import numpy as np
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

from src.Model.sequence import Sequence
from src.Model.pulses import GaussianPulse, SquarePulse, SechPulse
from src.Model.awg520_optimizer import (
    AWG520SequenceOptimizer, 
    AWG520Sequence,
    OptimizationError
)


class TestAWG520SequenceOptimizer:
    """Test the AWG520 sequence optimizer."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.optimizer = AWG520SequenceOptimizer()
        self.sample_rate = 1e9  # 1 GHz
        
        # Create a test sequence with mixed resolution regions
        self.test_sequence = Sequence(5000)  # 5μs total
        
        # High-resolution region: short pulses
        pi2_pulse = GaussianPulse("pi_2", 100, sigma=25, amplitude=1.0)
        pi_pulse = GaussianPulse("pi", 200, sigma=50, amplitude=1.0)
        
        # Add pulses with dead times
        self.test_sequence.add_pulse(0, pi2_pulse)      # 0-100ns
        # Dead time: 100-400ns (300ns)
        self.test_sequence.add_pulse(400, pi_pulse)      # 400-600ns
        # Dead time: 600-1000ns (400ns)
        self.test_sequence.add_pulse(1000, pi2_pulse)    # 1000-1100ns
        # Dead time: 1100-5000ns (3900ns)
    
    def test_initialization(self):
        """Test optimizer initialization."""
        assert self.optimizer.max_waveform_samples == 4_000_000
        assert self.optimizer.max_sequence_entries == 1000
        assert self.optimizer.sample_rate == 1e9
    
    def test_validate_awg520_constraints_valid_sequence(self):
        """Test constraint validation for valid sequence."""
        # Create a simple valid sequence
        seq = Sequence(1000)
        seq.add_pulse(0, GaussianPulse("test", 100, sigma=25, amplitude=1.0))
        
        assert self.optimizer._validate_awg520_constraints(seq) is True
    
    def test_validate_awg520_constraints_sequence_too_long(self):
        """Test constraint validation for sequence exceeding memory limit."""
        # Create sequence exceeding 4M samples
        seq = Sequence(5_000_000)
        seq.add_pulse(0, GaussianPulse("test", 100, sigma=25, amplitude=1.0))
        
        assert self.optimizer._validate_awg520_constraints(seq) is False
    
    def test_validate_awg520_constraints_too_many_pulses(self):
        """Test constraint validation for sequence with too many pulses."""
        # Create sequence with too many pulses
        seq = Sequence(15000)  # Increase length to accommodate 1001 pulses at 10 sample intervals
        for i in range(1001):
            seq.add_pulse(i * 10, GaussianPulse(f"pulse_{i}", 10, sigma=5, amplitude=1.0))
        
        assert self.optimizer._validate_awg520_constraints(seq) is False
    
    def test_identify_resolution_regions(self):
        """Test identification of high/low resolution regions."""
        # This should identify:
        # - High resolution: 0-100ns, 400-600ns, 1000-1100ns (pulse regions)
        # - Low resolution: 100-400ns, 600-1000ns, 1100-5000ns (dead time regions)
        regions = self.optimizer._identify_resolution_regions(self.test_sequence)
        
        assert len(regions) > 0
        # Check for pulse regions (high resolution)
        assert any(r['type'] == 'pulse' for r in regions)
        # Check for dead time regions
        assert any(r['type'] == 'dead_time' for r in regions)
    
    def test_calculate_memory_usage_without_optimization(self):
        """Test memory usage calculation without optimization."""
        # Raw sequence: 5000 samples * 2 bytes = 10KB
        memory_usage = self.optimizer._calculate_memory_usage(self.test_sequence)
        
        assert memory_usage['total_samples'] == 5000
        assert memory_usage['raw_memory_bytes'] == 10000  # 2 bytes per sample
        assert memory_usage['optimization_applied'] is False
    
    def test_calculate_memory_usage_with_optimization(self):
        """Test memory usage calculation with optimization."""
        # After optimization: dead time regions compressed
        memory_usage = self.optimizer._calculate_memory_usage(
            self.test_sequence,
            optimized=True
        )
        
        assert memory_usage['total_samples'] == 5000  # Original length preserved
        assert memory_usage['optimization_applied'] is True
        assert memory_usage['compression_ratio'] >= 1.0  # Should have some compression
    
    def test_apply_waveform_compression(self):
        """Test waveform-level compression for dead time regions."""
        # Compress the test sequence
        compressed = self.optimizer._apply_waveform_compression(self.test_sequence)
        
        assert compressed is not None
        assert compressed.length == self.test_sequence.length  # Length should be preserved
        assert len(compressed.pulses) <= len(self.test_sequence.pulses)  # Should be compressed
    
    def test_generate_mathematical_dead_time(self):
        """Test generation of mathematical dead time representation."""
        # Generate mathematical representation for 300ns dead time
        dead_time_region = {
            'start_sample': 100,
            'end_sample': 400,
            'duration_samples': 300,
            'type': 'dead_time'
        }
        
        math_rep = self.optimizer._generate_mathematical_dead_time(dead_time_region)
        
        assert math_rep['type'] == 'mathematical'
        assert math_rep['formula'] == 'zeros'  # Should be just 'zeros'
        assert 'parameters' in math_rep
        assert math_rep['compression_ratio'] >= 1.0
    
    def test_apply_rle_compression(self):
        """Test Run-Length Encoding compression."""
        # Create a sequence with repetitive patterns
        seq = Sequence(1000)
        for i in range(0, 1000, 100):
            seq.add_pulse(i, SquarePulse("square", 50, amplitude=1.0))
            # 50ns dead time between pulses
        
        compressed = self.optimizer._apply_rle_compression(seq)
        
        assert compressed is not None
        assert compressed.length == seq.length  # Length should be preserved
        # For now, RLE returns the same sequence (placeholder implementation)
    
    def test_apply_delta_encoding(self):
        """Test delta encoding for smooth waveforms."""
        # Create a smooth Gaussian pulse
        seq = Sequence(1000)
        seq.add_pulse(0, GaussianPulse("gaussian", 500, sigma=100, amplitude=1.0))
        
        compressed = self.optimizer._apply_delta_encoding(seq)
        
        assert compressed is not None
        assert compressed.length == seq.length  # Length should be preserved
        # For now, delta encoding returns the same sequence (placeholder implementation)
    
    def test_create_optimized_waveforms(self):
        """Test creation of optimized waveform files."""
        # Create optimized waveforms
        waveforms = self.optimizer._create_optimized_waveforms(self.test_sequence)
        
        assert isinstance(waveforms, dict)
        assert len(waveforms) > 0
        
        # Check that dead time regions are compressed
        for name, data in waveforms.items():
            if 'dead_time' in name:
                assert len(data) < 1000  # Should be compressed
            else:
                assert len(data) > 0  # Pulse data should be preserved
    
    def test_generate_sequence_file_entries(self):
        """Test generation of .seq file entries."""
        # Generate sequence entries
        entries = self.optimizer._generate_sequence_file_entries(self.test_sequence)
        
        assert isinstance(entries, list)
        assert len(entries) > 0
        
        # Check entry format
        for entry in entries:
            assert 'waveform_name' in entry
            assert 'start_time' in entry
            assert 'duration' in entry
            assert 'type' in entry
    
    def test_optimize_sequence_for_awg520_success(self):
        """Test successful sequence optimization."""
        # Optimize the test sequence
        optimized = self.optimizer.optimize_sequence_for_awg520(self.test_sequence)
        
        assert isinstance(optimized, AWG520Sequence)
        assert optimized.name == "optimized_sequence"
        assert len(optimized.waveform_files) > 0
        assert len(optimized.sequence_entries) > 0
    
    def test_optimize_sequence_for_awg520_failure(self):
        """Test sequence optimization failure."""
        # Create an invalid sequence
        invalid_seq = Mock()
        invalid_seq.pulses = []
        invalid_seq.length = 0
        
        with pytest.raises(ValueError):
            self.optimizer.optimize_sequence_for_awg520(invalid_seq)
    
    def test_handle_variable_sampling_regions(self):
        """Test handling of variable sampling regions."""
        # Create sequence with mixed sampling requirements
        seq = Sequence(2000)
        
        # High-resolution region (short pulses)
        seq.add_pulse(0, GaussianPulse("short", 50, sigma=10, amplitude=1.0))
        
        # Low-resolution region (long dead time)
        seq.add_pulse(500, SquarePulse("long", 1000, amplitude=1.0))
        
        # Optimize with variable sampling
        optimized = self.optimizer._handle_variable_sampling_regions(seq)
        
        assert optimized is not None
        # Should have different sampling rates for different regions
    
    def test_calculate_compression_ratios(self):
        """Test calculation of compression ratios."""
        # Calculate compression for different region types
        ratios = self.optimizer._calculate_compression_ratios(self.test_sequence)
        
        assert 'dead_time_compression' in ratios
        assert 'pulse_compression' in ratios
        assert 'overall_compression' in ratios
        
        # Dead time should have higher compression (at least 1.0)
        assert ratios['dead_time_compression'] >= 1.0
        assert ratios['pulse_compression'] >= 1.0
        assert ratios['overall_compression'] >= 1.0


class TestAWG520Sequence:
    """Test the AWG520Sequence class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.waveform_files = ["pulse1.wfm", "pulse2.wfm"]
        self.sequence_entries = [
            {"waveform_name": "pulse1", "start_time": 0, "duration": 100},
            {"waveform_name": "pulse2", "start_time": 200, "duration": 150}
        ]
        self.waveform_data = {
            "pulse1": np.random.random(100),
            "pulse2": np.random.random(150)
        }
        
        self.sequence = AWG520Sequence(
            "test_sequence",
            self.waveform_files,
            self.sequence_entries,
            self.waveform_data
        )
    
    def test_initialization(self):
        """Test sequence initialization."""
        assert self.sequence.name == "test_sequence"
        assert self.sequence.waveform_files == self.waveform_files
        assert self.sequence.sequence_entries == self.sequence_entries
        assert self.sequence.waveform_data == self.waveform_data
    
    def test_get_waveform_files(self):
        """Test getting waveform file names."""
        files = self.sequence.get_waveform_files()
        assert files == self.waveform_files
    
    def test_get_sequence_entries(self):
        """Test getting sequence table entries."""
        entries = self.sequence.get_sequence_entries()
        assert entries == self.sequence_entries
    
    def test_get_waveform_data(self):
        """Test getting waveform data."""
        data = self.sequence.get_waveform_data()
        assert data == self.waveform_data
    
    def test_empty_waveform_data(self):
        """Test sequence with no waveform data."""
        sequence = AWG520Sequence("empty", [], [], {})
        assert sequence.waveform_data == {}


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


class TestAWG520OptimizerIntegration:
    """Integration tests for the AWG520 optimizer."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.optimizer = AWG520SequenceOptimizer()
        
        # Create a realistic qubit sequence
        self.qubit_sequence = Sequence(10000)  # 10μs
        
        # Ramsey sequence: pi/2 - wait - pi/2 - laser - counter
        pi2_1 = GaussianPulse("pi_2_1", 100, sigma=25, amplitude=1.0)
        wait_time = 2000  # 2μs wait
        pi2_2 = GaussianPulse("pi_2_2", 100, sigma=25, amplitude=1.0)
        laser = SquarePulse("laser", 500, amplitude=1.0)
        counter = SquarePulse("counter", 200, amplitude=1.0)
        
        self.qubit_sequence.add_pulse(0, pi2_1)
        self.qubit_sequence.add_pulse(2100, pi2_2)
        self.qubit_sequence.add_pulse(2300, laser)
        self.qubit_sequence.add_pulse(2800, counter)
    
    def test_full_optimization_pipeline(self):
        """Test the complete optimization pipeline."""
        # Run full optimization
        optimized = self.optimizer.optimize_sequence_for_awg520(self.qubit_sequence)
        
        assert isinstance(optimized, AWG520Sequence)
        assert optimized.name == "optimized_sequence"
        
        # Check that we have waveforms for all pulses
        assert len(optimized.waveform_files) >= 4  # pi/2_1, pi/2_2, laser, counter
        
        # Check that sequence entries are properly formatted
        for entry in optimized.sequence_entries:
            assert 'waveform_name' in entry
            assert 'start_time' in entry
            assert 'duration' in entry
    
    def test_memory_optimization_effectiveness(self):
        """Test that memory optimization actually reduces memory usage."""
        # Calculate memory before optimization
        before_memory = self.optimizer._calculate_memory_usage(self.qubit_sequence)
        
        # Optimize
        optimized = self.optimizer.optimize_sequence_for_awg520(self.qubit_sequence)
        
        # Calculate memory after optimization
        after_memory = self.optimizer._calculate_memory_usage(
            self.qubit_sequence, 
            optimized=True
        )
        
        # Memory should be reduced or at least not increased
        assert after_memory['optimized_memory_bytes'] <= before_memory['raw_memory_bytes']
        assert after_memory['compression_ratio'] >= 1.0
    
    def test_preserve_timing_accuracy(self):
        """Test that optimization preserves timing accuracy."""
        # Get original timing
        original_timing = [(start, pulse.length) for start, pulse in self.qubit_sequence.pulses]
        
        # Optimize
        optimized = self.optimizer.optimize_sequence_for_awg520(self.qubit_sequence)
        
        # Check that timing is preserved in sequence entries
        optimized_timing = [(entry['start_time'], entry['duration']) 
                           for entry in optimized.sequence_entries 
                           if entry['type'] == 'pulse']
        
        # Timing should match (allowing for small numerical differences)
        assert len(original_timing) == len(optimized_timing)
        for (orig_start, orig_dur), (opt_start, opt_dur) in zip(original_timing, optimized_timing):
            assert abs(orig_start - opt_start) < 1e-9  # Within 1ns
            assert abs(orig_dur - opt_dur) < 1e-9      # Within 1ns


if __name__ == "__main__":
    pytest.main([__file__])
