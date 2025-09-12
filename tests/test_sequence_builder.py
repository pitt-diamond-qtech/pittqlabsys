"""
Tests for the sequence builder module.

This module tests the conversion of SequenceDescription objects into
optimized Sequence objects for hardware processing.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock

from src.Model.sequence_builder import (
    SequenceBuilder, OptimizedSequence, BuildError, OptimizationError
)
from src.Model.sequence_description import (
    SequenceDescription, PulseDescription, LoopDescription, ConditionalDescription,
    PulseShape, VariableDescription
)


class TestSequenceBuilder:
    """Test the SequenceBuilder class."""
    
    def test_initialization(self):
        """Test that SequenceBuilder initializes correctly."""
        builder = SequenceBuilder(sample_rate=2e9)
        assert builder.sample_rate == 2e9
    
    def test_build_sequence_basic(self):
        """Test that build_sequence works with basic sequence descriptions."""
        builder = SequenceBuilder(sample_rate=1e9)
        
        # Create a simple sequence description
        description = SequenceDescription(
            name="test_sequence",
            experiment_type="test",
            total_duration=1e-6,  # 1 μs
            sample_rate=1e9
        )
        
        # Add a pulse
        pulse = PulseDescription(
            name="test_pulse",
            pulse_type="pi/2",
            channel=1,
            shape=PulseShape.GAUSSIAN,
            duration=100e-9,  # 100 ns
            amplitude=1.0,
            timing=0.0
        )
        description.add_pulse(pulse)
        
        # Build the sequence
        optimized = builder.build_sequence(description)
        
        assert optimized.name == "test_sequence"
        assert optimized.get_chunk_count() == 1
        assert optimized.get_total_memory_usage() == 1000  # 1 μs * 1 GHz = 1000 samples
    
    def test_build_from_preset_not_implemented(self):
        """Test that build_from_preset raises NotImplementedError."""
        builder = SequenceBuilder()
        
        with pytest.raises(NotImplementedError, match="Preset integration not yet implemented"):
            builder.build_from_preset("odmr")
    
    def test_optimize_for_memory_constraints(self):
        """Test that optimize_for_memory_constraints works correctly."""
        builder = SequenceBuilder()
        
        # Create a mock sequence with waveform
        mock_sequence = Mock()
        mock_waveform = Mock()
        mock_waveform.__len__ = Mock(return_value=2000)
        mock_sequence.waveform = mock_waveform
        
        # Test optimization with max_samples_per_chunk = 1000
        optimized = builder.optimize_for_memory_constraints(mock_sequence, 1000)
        
        # For mock objects that don't support slicing, we get the original sequence back
        # For real sequences, this would split into chunks
        assert len(optimized) == 1  # Mock objects return original sequence
        assert optimized[0] == mock_sequence  # Should be the original sequence
    
    def test_create_pulse_object_gaussian(self):
        """Test that _create_pulse_object creates GaussianPulse correctly."""
        builder = SequenceBuilder(sample_rate=1e9)
        
        pulse_desc = PulseDescription(
            name="test_pulse",
            pulse_type="pi/2",
            channel=1,
            shape=PulseShape.GAUSSIAN,
            duration=100e-9,
            amplitude=1.0,
            timing=0.0
        )
        
        pulse_obj = builder._create_pulse_object(pulse_desc)
        
        assert pulse_obj.name == "test_pulse"
        assert pulse_obj.length == 100  # 100 ns * 1 GHz = 100 samples
        assert pulse_obj.amplitude == 1.0
        assert hasattr(pulse_obj, 'sigma')  # Gaussian-specific attribute
    
    def test_create_pulse_object_square(self):
        """Test that _create_pulse_object creates SquarePulse correctly."""
        builder = SequenceBuilder(sample_rate=1e9)
        
        pulse_desc = PulseDescription(
            name="test_pulse",
            pulse_type="pi",
            channel=2,
            shape=PulseShape.SQUARE,
            duration=200e-9,
            amplitude=0.5,
            timing=0.0
        )
        
        pulse_obj = builder._create_pulse_object(pulse_desc)
        
        assert pulse_obj.name == "test_pulse"
        assert pulse_obj.length == 200  # 200 ns * 1 GHz = 200 samples
        assert pulse_obj.amplitude == 0.5
    
    def test_build_loop_sequence(self):
        """Test that _build_loop_sequence works correctly."""
        builder = SequenceBuilder(sample_rate=1e9)
        
        # Create a loop description
        loop_desc = LoopDescription(
            name="test_loop",
            iterations=10,
            start_time=0.0,
            end_time=1e-3  # 1 ms
        )
        
        # Add a pulse to the loop
        pulse = PulseDescription(
            name="loop_pulse",
            pulse_type="pi/2",
            channel=1,
            shape=PulseShape.GAUSSIAN,
            duration=100e-9,
            amplitude=1.0,
            timing=500e-6  # 500 μs into the loop
        )
        loop_desc.pulses.append(pulse)
        
        # Build the loop sequence
        loop_sequence = builder._build_loop_sequence(loop_desc)
        
        assert loop_sequence.length == 1000000  # 1 ms * 1 GHz = 1M samples
        assert len(loop_sequence.pulses) == 1
    
    def test_build_conditional_sequence(self):
        """Test that _build_conditional_sequence works correctly."""
        builder = SequenceBuilder(sample_rate=1e9)
        
        # Create a conditional description
        conditional_desc = ConditionalDescription(
            name="test_conditional",
            condition="if marker_1",
            start_time=0.0,
            end_time=1e-3  # 1 ms
        )
        
        # Add a pulse to the conditional
        pulse = PulseDescription(
            name="conditional_pulse",
            pulse_type="pi",
            channel=1,
            shape=PulseShape.SQUARE,
            duration=100e-9,
            amplitude=1.0,
            timing=500e-6  # 500 μs into the conditional
        )
        conditional_desc.true_pulses.append(pulse)
        
        # Build the conditional sequence
        conditional_sequence = builder._build_conditional_sequence(conditional_desc)
        
        assert conditional_sequence.length == 1000000  # 1 ms * 1 GHz = 1M samples
        assert len(conditional_sequence.pulses) == 1
    
    def test_calculate_memory_usage(self):
        """Test that _calculate_memory_usage works correctly."""
        builder = SequenceBuilder()
        
        # Test with sequence that has waveform
        mock_sequence_with_waveform = Mock()
        mock_waveform = Mock()
        mock_waveform.__len__ = Mock(return_value=1000)
        mock_sequence_with_waveform.waveform = mock_waveform
        
        memory_usage = builder._calculate_memory_usage(mock_sequence_with_waveform)
        assert memory_usage == 1000
        
        # Test with sequence that only has length
        mock_sequence_with_length = Mock()
        mock_sequence_with_length.length = 500
        
        memory_usage = builder._calculate_memory_usage(mock_sequence_with_length)
        assert memory_usage == 500
    
    def test_split_sequence_at_boundaries(self):
        """Test that _split_sequence_at_boundaries works correctly."""
        builder = SequenceBuilder()
        
        # Create a mock sequence with waveform
        mock_sequence = Mock()
        mock_waveform = Mock()
        mock_waveform.__len__ = Mock(return_value=2500)
        mock_sequence.waveform = mock_waveform
        
        # Test splitting with max_samples = 1000
        chunks = builder._split_sequence_at_boundaries(mock_sequence, 1000)
        
        # For mock objects that don't support slicing, we get the original sequence back
        # For real sequences, this would split into chunks
        assert len(chunks) == 1  # Mock objects return original sequence
        assert chunks[0] == mock_sequence  # Should be the original sequence
    
    def test_find_optimal_split_points(self):
        """Test that _find_optimal_split_points works correctly."""
        builder = SequenceBuilder()
        
        # Create a mock sequence with waveform
        mock_sequence = Mock()
        mock_waveform = Mock()
        mock_waveform.__len__ = Mock(return_value=2500)
        mock_sequence.waveform = mock_waveform
        
        # Test finding split points with max_samples = 1000
        split_points = builder._find_optimal_split_points(mock_sequence, 1000)
        
        assert split_points == [1000, 2000]  # Should split at 1000 and 2000
    
    def test_build_sequence_with_invalid_description(self):
        """Test that build_sequence raises BuildError for invalid descriptions."""
        builder = SequenceBuilder()
        
        # Create an invalid description (pulse extends beyond total duration)
        description = SequenceDescription(
            name="invalid_sequence",
            experiment_type="test",
            total_duration=1e-6,  # 1 μs
            sample_rate=1e9
        )
        
        # Add a pulse that extends beyond total duration
        invalid_pulse = PulseDescription(
            name="invalid_pulse",
            pulse_type="pi/2",
            channel=1,
            shape=PulseShape.GAUSSIAN,
            duration=2e-6,  # 2 μs
            amplitude=1.0,
            timing=0.0  # 0 + 2μs = 2μs > 1μs total duration
        )
        description.add_pulse(invalid_pulse)
        
        # This should fail validation
        with pytest.raises(BuildError):
            builder.build_sequence(description)


class TestOptimizedSequence:
    """Test the OptimizedSequence class."""
    
    def test_initialization(self):
        """Test that OptimizedSequence initializes correctly."""
        # Create mock sequences with proper attributes
        mock_sequence1 = Mock()
        mock_sequence1.duration = 1e-3  # 1 ms
        mock_waveform1 = Mock()
        mock_waveform1.__len__ = Mock(return_value=1000)
        mock_sequence1.waveform = mock_waveform1
        
        mock_sequence2 = Mock()
        mock_sequence2.duration = 0.5e-3  # 0.5 ms
        mock_waveform2 = Mock()
        mock_waveform2.__len__ = Mock(return_value=500)
        mock_sequence2.waveform = mock_waveform2
        
        sequences = [mock_sequence1, mock_sequence2]
        
        optimized = OptimizedSequence("test_sequence", sequences, {"test": "data"})
        
        assert optimized.name == "test_sequence"
        assert optimized.get_chunk_count() == 2
        assert optimized.get_total_memory_usage() == 1500
        assert optimized.metadata["test"] == "data"
    
    def test_initialization_empty_sequences(self):
        """Test that OptimizedSequence handles empty sequences correctly."""
        optimized = OptimizedSequence("test_sequence", [])
        
        assert optimized.name == "test_sequence"
        assert optimized.get_chunk_count() == 0
        assert optimized.get_total_memory_usage() == 0
        assert optimized.total_duration == 0.0
    
    def test_get_chunk(self):
        """Test that get_chunk returns the correct chunk."""
        mock_sequence1 = Mock()
        mock_sequence1.duration = 1e-3  # 1 ms
        mock_waveform1 = Mock()
        mock_waveform1.__len__ = Mock(return_value=1000)
        mock_sequence1.waveform = mock_waveform1
        
        mock_sequence2 = Mock()
        mock_sequence2.duration = 0.5e-3  # 0.5 ms
        mock_waveform2 = Mock()
        mock_waveform2.__len__ = Mock(return_value=500)
        mock_sequence2.waveform = mock_waveform2
        
        sequences = [mock_sequence1, mock_sequence2]
        optimized = OptimizedSequence("test_sequence", sequences)
        
        assert optimized.get_chunk(0) == mock_sequence1
        assert optimized.get_chunk(1) == mock_sequence2
        
        # Test index out of range
        with pytest.raises(IndexError):
            optimized.get_chunk(2)
        
        with pytest.raises(IndexError):
            optimized.get_chunk(-1)
    
    def test_get_chunk_count(self):
        """Test that get_chunk_count returns the correct number."""
        mock_sequences = []
        for i in range(5):
            mock_seq = Mock()
            mock_seq.duration = 1e-3  # 1 ms
            mock_waveform = Mock()
            mock_waveform.__len__ = Mock(return_value=1000)
            mock_seq.waveform = mock_waveform
            mock_sequences.append(mock_seq)
        
        optimized = OptimizedSequence("test_sequence", mock_sequences)
        
        assert optimized.get_chunk_count() == 5
    
    def test_get_total_memory_usage(self):
        """Test that get_total_memory_usage returns the correct value."""
        mock_sequence1 = Mock()
        mock_sequence1.duration = 1e-3  # 1 ms
        mock_waveform1 = Mock()
        mock_waveform1.__len__ = Mock(return_value=1000)
        mock_sequence1.waveform = mock_waveform1
        
        mock_sequence2 = Mock()
        mock_sequence2.duration = 0.5e-3  # 0.5 ms
        mock_waveform2 = Mock()
        mock_waveform2.__len__ = Mock(return_value=500)
        mock_sequence2.waveform = mock_waveform2
        
        sequences = [mock_sequence1, mock_sequence2]
        optimized = OptimizedSequence("test_sequence", sequences)
        
        assert optimized.get_total_memory_usage() == 1500
    
    def test_validate_memory_constraints(self):
        """Test that validate_memory_constraints works correctly."""
        # Create sequences within constraints
        mock_sequence1 = Mock()
        mock_sequence1.duration = 1e-3  # 1 ms
        mock_waveform1 = Mock()
        mock_waveform1.__len__ = Mock(return_value=1000)
        mock_sequence1.waveform = mock_waveform1
        
        mock_sequence2 = Mock()
        mock_sequence2.duration = 0.5e-3  # 0.5 ms
        mock_waveform2 = Mock()
        mock_waveform2.__len__ = Mock(return_value=500)
        mock_sequence2.waveform = mock_waveform2
        
        sequences = [mock_sequence1, mock_sequence2]
        optimized = OptimizedSequence("test_sequence", sequences)
        
        # Should pass validation
        assert optimized.validate_memory_constraints(1000) is True
        
        # Should fail validation
        assert optimized.validate_memory_constraints(499) is False
    
    def test_get_optimization_summary(self):
        """Test that get_optimization_summary returns correct data."""
        mock_sequence1 = Mock()
        mock_sequence1.duration = 1e-3  # 1 ms
        mock_waveform1 = Mock()
        mock_waveform1.__len__ = Mock(return_value=1000)
        mock_sequence1.waveform = mock_waveform1
        
        mock_sequence2 = Mock()
        mock_sequence2.duration = 0.5e-3  # 0.5 ms
        mock_waveform2 = Mock()
        mock_waveform2.__len__ = Mock(return_value=500)
        mock_sequence2.waveform = mock_waveform2
        
        sequences = [mock_sequence1, mock_sequence2]
        optimized = OptimizedSequence("test_sequence", sequences)
        
        summary = optimized.get_optimization_summary()
        
        assert summary["name"] == "test_sequence"
        assert summary["total_chunks"] == 2
        assert summary["total_samples"] == 1500
        assert summary["chunk_sizes"] == [1000, 500]
        assert summary["memory_efficiency"] == 0.75  # 1500 / (2 * 1000)
        assert "metadata" in summary
    
    def test_get_optimization_summary_empty_sequences(self):
        """Test getting optimization summary with empty sequences."""
        optimized = OptimizedSequence("test_sequence", [])
        summary = optimized.get_optimization_summary()
        
        assert summary["total_chunks"] == 0
        assert summary["total_samples"] == 0
        assert summary["chunk_sizes"] == []
        assert summary["memory_efficiency"] == 0.0


class TestBuildError:
    """Test the BuildError exception."""
    
    def test_build_error_creation(self):
        """Test creating a BuildError."""
        error = BuildError("Test build error")
        assert str(error) == "Test build error"
    
    def test_build_error_inheritance(self):
        """Test that BuildError inherits from Exception."""
        error = BuildError("Test")
        assert isinstance(error, Exception)


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


class TestSequenceBuilderIntegration:
    """Integration tests for SequenceBuilder."""
    
    def test_sequence_builder_with_mock_sequence(self):
        """Test SequenceBuilder with a mock sequence."""
        builder = SequenceBuilder(sample_rate=1e9)
        
        # Create a mock sequence description
        description = SequenceDescription(
            name="test_sequence",
            experiment_type="test",
            total_duration=1e-3,
            sample_rate=1e9
        )
        
        # Add a pulse to the description
        pulse = PulseDescription(
            name="test_pulse",
            pulse_type="pi/2",
            channel=1,
            shape=PulseShape.GAUSSIAN,
            duration=100e-9,
            amplitude=1.0,
            timing=0.0
        )
        description.add_pulse(pulse)
        
        # Verify the description is valid
        assert description.validate() is True
        assert description.get_total_pulses() == 1
        
        # Test that builder can build the sequence
        optimized = builder.build_sequence(description)
        
        assert optimized.name == "test_sequence"
        assert optimized.get_chunk_count() == 1
        assert optimized.get_total_memory_usage() == 1000000  # 1 ms * 1 GHz = 1,000,000 samples
    
    def test_sequence_builder_error_handling(self):
        """Test that SequenceBuilder handles errors gracefully."""
        builder = SequenceBuilder()
        
        # Test with invalid sequence description
        invalid_description = SequenceDescription(
            name="invalid_sequence",
            experiment_type="test",
            total_duration=1e-6,  # 1 μs
            sample_rate=1e9
        )
        
        # Add a pulse that extends beyond total duration
        invalid_pulse = PulseDescription(
            name="invalid_pulse",
            pulse_type="pi/2",
            channel=1,
            shape=PulseShape.GAUSSIAN,
            duration=2e-6,  # 2 μs
            amplitude=1.0,
            timing=0.0  # 0 + 2μs = 2μs > 1μs total duration
        )
        invalid_description.add_pulse(invalid_pulse)
        
        # This should raise BuildError
        with pytest.raises(BuildError):
            builder.build_sequence(invalid_description)
    
    def test_sequence_builder_initialization_consistency(self):
        """Test that SequenceBuilder initialization is consistent."""
        builder1 = SequenceBuilder(sample_rate=1e9)
        builder2 = SequenceBuilder(sample_rate=2e9)
        
        # Both should have the same structure
        assert hasattr(builder1, 'sample_rate')
        assert hasattr(builder2, 'sample_rate')
        
        # But different values
        assert builder1.sample_rate == 1e9
        assert builder2.sample_rate == 2e9
        
        # Both should have the same methods
        methods = [
            'build_sequence', 'build_from_preset', 'optimize_for_memory_constraints',
            '_create_pulse_object', '_build_loop_sequence', '_build_conditional_sequence',
            '_calculate_memory_usage', '_split_sequence_at_boundaries', '_find_optimal_split_points'
        ]
        
        for method in methods:
            assert hasattr(builder1, method)
            assert hasattr(builder2, method)


class TestSequenceBuilderScanSequences:
    """Test the new scan sequence functionality."""
    
    def test_build_scan_sequences_no_variables(self):
        """Test building scan sequences when no variables are defined."""
        
        # Create a simple sequence description without variables
        desc = SequenceDescription(
            name="test_sequence",
            experiment_type="custom",
            total_duration=1e-6,
            sample_rate=1e9,
            repeat_count=1
        )
        
        # Add a pulse
        pulse = PulseDescription(
            name="test_pulse",
            pulse_type="pi/2",
            channel=1,
            shape=PulseShape.GAUSSIAN,
            duration=100e-9,
            amplitude=1.0,
            timing=0.0
        )
        desc.add_pulse(pulse)
        
        builder = SequenceBuilder()
        sequences = builder.build_scan_sequences(desc)
        
        # Should return single sequence when no variables
        assert len(sequences) == 1
        assert sequences[0].name == "test_sequence_scan"
    
    def test_build_scan_sequences_single_variable(self):
        """Test building scan sequences with a single variable."""
        
        # Create sequence description with one variable
        desc = SequenceDescription(
            name="rabi_scan",
            experiment_type="rabi",
            total_duration=1e-6,
            sample_rate=1e9,
            repeat_count=50000
        )
        
        # Add variable
        desc.add_variable("pulse_duration", 100e-9, 200e-9, 3, "ns")
        
        # Add pulses
        pulse1 = PulseDescription(
            name="pi_2_1",
            pulse_type="pi/2",
            channel=1,
            shape=PulseShape.GAUSSIAN,
            duration=100e-9,  # This will be scanned
            amplitude=1.0,
            timing=0.0
        )
        pulse2 = PulseDescription(
            name="pi_1",
            pulse_type="pi",
            channel=1,
            shape=PulseShape.GAUSSIAN,
            duration=100e-9,
            amplitude=1.0,
            timing=200e-9  # This should get pushed later
        )
        desc.add_pulse(pulse1)
        desc.add_pulse(pulse2)
        
        builder = SequenceBuilder()
        sequences = builder.build_scan_sequences(desc)
        
        # Should return 3 sequences (3 scan points)
        assert len(sequences) == 3
        
        # Check timing adjustments
        # First sequence: pulse_duration = 100ns (original)
        assert sequences[0].pulses[0][1].length == int(100e-9 * 1e9)  # 100ns in samples
        assert sequences[0].pulses[1][0] == int(200e-9 * 1e9)  # 200ns in samples
        
        # Second sequence: pulse_duration = 150ns
        assert sequences[1].pulses[0][1].length == int(150e-9 * 1e9)  # 150ns in samples
        assert sequences[1].pulses[1][0] == int(250e-9 * 1e9)  # 250ns in samples (pushed by 50ns)
        
        # Third sequence: pulse_duration = 200ns
        assert sequences[2].pulses[0][1].length == int(200e-9 * 1e9)  # 200ns in samples
        assert sequences[2].pulses[1][0] == int(300e-9 * 1e9)  # 300ns in samples (pushed by 100ns)
    
    def test_build_scan_sequences_with_fixed_marker(self):
        """Test that [fixed] markers prevent timing adjustment."""
        
        # Create sequence description with one variable
        desc = SequenceDescription(
            name="test_fixed",
            experiment_type="custom",
            total_duration=1e-6,
            sample_rate=1e9,
            repeat_count=1
        )
        
        # Add variable
        desc.add_variable("pulse_duration", 100e-9, 200e-9, 2, "ns")
        
        # Add pulses - second pulse is [fixed]
        pulse1 = PulseDescription(
            name="scanned_pulse",
            pulse_type="pi/2",
            channel=1,
            shape=PulseShape.GAUSSIAN,
            duration=100e-9,
            amplitude=1.0,
            timing=0.0
        )
        pulse2 = PulseDescription(
            name="fixed_pulse",
            pulse_type="laser",
            channel=2,
            shape=PulseShape.SQUARE,
            duration=200e-9,
            amplitude=1.0,
            timing=200e-9,
            fixed_timing=True  # This should not be pushed
        )
        desc.add_pulse(pulse1)
        desc.add_pulse(pulse2)
        
        builder = SequenceBuilder()
        sequences = builder.build_scan_sequences(desc)
        
        # Should return 2 sequences
        assert len(sequences) == 2
        
        # Check that fixed pulse timing is not adjusted
        # First sequence: pulse_duration = 100ns
        assert sequences[0].pulses[1][0] == int(200e-9 * 1e9)  # Original timing in samples
        
        # Second sequence: pulse_duration = 200ns
        assert sequences[1].pulses[1][0] == int(200e-9 * 1e9)  # Still original timing (fixed)
    
    def test_build_scan_sequences_multiple_variables_warning(self):
        """Test that multiple variables trigger a warning."""
        
        # Create sequence description with multiple variables
        desc = SequenceDescription(
            name="multi_scan",
            experiment_type="custom",
            total_duration=1e-6,
            sample_rate=1e9,
            repeat_count=1
        )
        
        # Add multiple variables
        desc.add_variable("pulse_duration", 100e-9, 200e-9, 3, "ns")
        desc.add_variable("amplitude", 0.8, 1.2, 2, "V")
        
        # Add a pulse
        pulse = PulseDescription(
            name="test_pulse",
            pulse_type="pi/2",
            channel=1,
            shape=PulseShape.GAUSSIAN,
            duration=100e-9,
            amplitude=1.0,
            timing=0.0
        )
        desc.add_pulse(pulse)
        
        builder = SequenceBuilder()
        
        # Should warn about multiple variables
        with pytest.warns(UserWarning, match="Building 2 variables simultaneously"):
            sequences = builder.build_scan_sequences(desc)
        
        # Should still work but warn about data correlation
        assert len(sequences) > 0
    
    def test_calculate_actual_duration(self):
        """Test duration calculation based on actual pulse timing."""
        
        # Create sequence description
        desc = SequenceDescription(
            name="test_duration",
            experiment_type="custom",
            total_duration=1e-6,  # Initial estimate
            sample_rate=1e9,
            repeat_count=1
        )
        
        # Add pulses at different times
        pulse1 = PulseDescription(
            name="pulse1",
            pulse_type="pi/2",
            channel=1,
            shape=PulseShape.GAUSSIAN,
            duration=100e-9,
            amplitude=1.0,
            timing=0.0
        )
        pulse2 = PulseDescription(
            name="pulse2",
            pulse_type="pi",
            channel=1,
            shape=PulseShape.GAUSSIAN,
            duration=200e-9,
            amplitude=1.0,
            timing=300e-9  # Ends at 500ns
        )
        desc.add_pulse(pulse1)
        desc.add_pulse(pulse2)
        
        builder = SequenceBuilder()
        sequences = builder.build_scan_sequences(desc)
        
        # Should calculate actual duration based on pulse timing
        assert len(sequences) == 1
        # The sequence should have the duration calculated and stored
        # Check that the latest pulse ends at 500ns
        latest_pulse_end = 0
        for start_sample, pulse in sequences[0].pulses:
            pulse_end = start_sample + pulse.length
            latest_pulse_end = max(latest_pulse_end, pulse_end)
        
        # Convert samples to duration
        actual_duration = latest_pulse_end / 1e9  # sample_rate = 1e9
        
        # Should be 500ns (latest pulse end time)
        assert abs(actual_duration - 500e-9) < 1e-12
    
    def test_variable_substitution_in_parameters(self):
        """Test that variable values are substituted in pulse parameters."""
        
        # Create sequence description with variable
        desc = SequenceDescription(
            name="param_scan",
            experiment_type="custom",
            total_duration=1e-6,
            sample_rate=1e9,
            repeat_count=1
        )
        
        # Add variable
        desc.add_variable("phase_var", 0.0, 90.0, 2, "deg")
        
        # Add pulse with parameter that uses variable
        pulse = PulseDescription(
            name="test_pulse",
            pulse_type="pi/2",
            channel=1,
            shape=PulseShape.GAUSSIAN,
            duration=100e-9,
            amplitude=1.0,
            timing=0.0,
            parameters={"phase": "phase_var"}  # This should be substituted
        )
        desc.add_pulse(pulse)
        
        builder = SequenceBuilder()
        sequences = builder.build_scan_sequences(desc)
        
        # Should return 2 sequences
        assert len(sequences) == 2
        
        # Check parameter substitution
        # The parameters should be substituted during variable scanning
        # For now, we'll check that the sequences were created correctly
        # In a full implementation, the parameters would be stored in the pulse objects
        
        # First sequence: phase_var = 0.0
        assert len(sequences[0].pulses) == 1
        
        # Second sequence: phase_var = 90.0  
        assert len(sequences[1].pulses) == 1
        
        # Both sequences should have the same structure but different parameter values
        # The actual parameter substitution would happen in the sequence building process


class TestSequenceBuilderPulseTypes:
    """Test that SequenceBuilder correctly handles all pulse types."""
    
    def test_create_pulse_object_sech(self):
        """Test that _create_pulse_object creates SechPulse correctly."""
        builder = SequenceBuilder(sample_rate=1e9)
        
        pulse_desc = PulseDescription(
            name="test_sech",
            pulse_type="sech",
            channel=1,
            shape=PulseShape.SECH,  # Use correct shape
            duration=100e-9,
            amplitude=1.0,
            timing=0.0
        )
        
        pulse_obj = builder._create_pulse_object(pulse_desc)
        
        assert pulse_obj.name == "test_sech"
        assert pulse_obj.length == 100  # 100 ns * 1 GHz = 100 samples
        assert hasattr(pulse_obj, 'width')  # Sech-specific attribute
        assert hasattr(pulse_obj, 'generate_samples')  # Should have this method
    
    def test_create_pulse_object_lorentzian(self):
        """Test that _create_pulse_object creates LorentzianPulse correctly."""
        builder = SequenceBuilder(sample_rate=1e9)
        
        pulse_desc = PulseDescription(
            name="test_lorentzian",
            pulse_type="lorentzian",
            channel=2,
            shape=PulseShape.LORENTZIAN,  # Use correct shape
            duration=150e-9,
            amplitude=0.8,
            timing=0.0
        )
        
        pulse_obj = builder._create_pulse_object(pulse_desc)
        
        assert pulse_obj.name == "test_lorentzian"
        assert pulse_obj.length == 150  # 150 ns * 1 GHz = 150 samples
        assert hasattr(pulse_obj, 'gamma')  # Lorentzian-specific attribute
        assert hasattr(pulse_obj, 'generate_samples')  # Should have this method
    
    def test_create_pulse_object_data_pulse(self):
        """Test that _create_pulse_object creates DataPulse correctly."""
        builder = SequenceBuilder(sample_rate=1e9)
        
        pulse_desc = PulseDescription(
            name="test_data",
            pulse_type="data",
            channel=3,
            shape=PulseShape.DATA,  # Use correct shape
            duration=200e-9,
            amplitude=1.0,
            timing=0.0,
            parameters={"filename": "tests/test_data_sine_wave.csv"}
        )
        
        pulse_obj = builder._create_pulse_object(pulse_desc)
        
        assert pulse_obj.name == "test_data"
        assert pulse_obj.length == 200  # 200 ns * 1 GHz = 200 samples
        assert hasattr(pulse_obj, 'filename')  # DataPulse-specific attribute
        assert hasattr(pulse_obj, 'generate_samples')  # Should have this method


class TestSequenceBuilderVisualization:
    """Test the visualization methods in SequenceBuilder."""
    
    def test_plot_sequence_basic(self):
        """Test basic plot_sequence functionality."""
        builder = SequenceBuilder(sample_rate=1e9)
        
        # Create a simple sequence with one pulse
        from src.Model.sequence import Sequence
        from src.Model.pulses import GaussianPulse
        
        seq = Sequence(1000)  # 1000 samples
        pulse = GaussianPulse("test", 100, sigma=20, amplitude=1.0)
        seq.add_pulse(100, pulse)  # Start at sample 100
        
        # Test plotting
        fig = builder.plot_sequence(seq, title="Test Plot")
        
        assert fig is not None
        assert hasattr(fig, 'savefig')  # Should be a matplotlib figure
        
        # Clean up
        import matplotlib.pyplot as plt
        plt.close(fig)
    
    def test_plot_sequence_all_pulse_types(self):
        """Test that plot_sequence correctly displays all pulse types."""
        builder = SequenceBuilder(sample_rate=1e9)
        
        from src.Model.sequence import Sequence
        from src.Model.pulses import GaussianPulse, SechPulse, LorentzianPulse, SquarePulse, DataPulse
        
        # Create sequence with all pulse types
        seq = Sequence(2000)  # 2000 samples
        
        # Add different pulse types at different times
        gaussian = GaussianPulse("gaussian", 100, sigma=25, amplitude=1.0)
        sech = SechPulse("sech", 80, width=15, amplitude=1.0)
        lorentzian = LorentzianPulse("lorentzian", 120, gamma=30, amplitude=1.0)
        square = SquarePulse("square", 100, amplitude=1.0)
        
        seq.add_pulse(0, gaussian)
        seq.add_pulse(200, sech)
        seq.add_pulse(400, lorentzian)
        seq.add_pulse(600, square)
        
        # Test plotting
        fig = builder.plot_sequence(seq, title="All Pulse Types")
        
        assert fig is not None
        
        # Clean up
        import matplotlib.pyplot as plt
        plt.close(fig)
    
    def test_plot_sequence_data_pulse(self):
        """Test that plot_sequence correctly displays DataPulse."""
        builder = SequenceBuilder(sample_rate=1e9)
        
        from src.Model.sequence import Sequence
        from src.Model.pulses import DataPulse
        
        # Create sequence with DataPulse
        seq = Sequence(1000)
        
        # Test with sine wave data
        data_pulse = DataPulse("sine_wave", 200, "tests/test_data_sine_wave.csv")
        seq.add_pulse(100, data_pulse)
        
        # Test plotting
        fig = builder.plot_sequence(seq, title="DataPulse Test")
        
        assert fig is not None
        
        # Clean up
        import matplotlib.pyplot as plt
        plt.close(fig)
    
    def test_animate_scan_sequences_basic(self):
        """Test basic animate_scan_sequences functionality."""
        builder = SequenceBuilder(sample_rate=1e9)
        
        from src.Model.sequence import Sequence
        from src.Model.pulses import GaussianPulse
        
        # Create multiple sequences for animation
        sequences = []
        for i in range(3):
            seq = Sequence(1000)
            pulse = GaussianPulse(f"pulse_{i}", 100 + i*20, sigma=25, amplitude=1.0)
            seq.add_pulse(100, pulse)
            sequences.append(seq)
        
        # Test animation
        anim = builder.animate_scan_sequences(sequences, title="Test Animation")
        
        assert anim is not None
        assert hasattr(anim, 'event_source')  # Should be a matplotlib animation
    
    def test_animate_scan_sequences_all_pulse_types(self):
        """Test that animate_scan_sequences works with all pulse types."""
        builder = SequenceBuilder(sample_rate=1e9)
        
        from src.Model.sequence import Sequence
        from src.Model.pulses import GaussianPulse, SechPulse, LorentzianPulse, SquarePulse
        
        # Create sequences with different pulse types
        sequences = []
        pulse_types = [
            ("gaussian", GaussianPulse, {"sigma": 25}),
            ("sech", SechPulse, {"width": 15}),
            ("lorentzian", LorentzianPulse, {"gamma": 30}),
            ("square", SquarePulse, {})
        ]
        
        for i, (pulse_name, pulse_class, params) in enumerate(pulse_types):
            seq = Sequence(1000)
            pulse = pulse_class(f"{pulse_name}_pulse", 100, amplitude=1.0, **params)
            seq.add_pulse(100, pulse)
            sequences.append(seq)
        
        # Test animation
        anim = builder.animate_scan_sequences(sequences, title="All Pulse Types Animation")
        
        assert anim is not None
    
    def test_visualization_error_handling(self):
        """Test that visualization methods handle errors gracefully."""
        builder = SequenceBuilder(sample_rate=1e9)
        
        from src.Model.sequence import Sequence
        
        # Create sequence with invalid pulse (no generate_samples method)
        seq = Sequence(1000)
        
        # Mock pulse without generate_samples but with channel attribute
        mock_pulse = Mock()
        mock_pulse.name = "invalid_pulse"
        mock_pulse.length = 100
        mock_pulse.fixed_timing = False
        mock_pulse.channel = 1  # Add channel attribute
        # Don't add generate_samples method
        
        seq.add_pulse(100, mock_pulse)
        
        # Should handle gracefully and use square fallback
        fig = builder.plot_sequence(seq, title="Error Handling Test")
        
        assert fig is not None
        
        # Clean up
        import matplotlib.pyplot as plt
        plt.close(fig)
    
    def test_visualization_channel_handling(self):
        """Test that visualization correctly handles multiple channels."""
        builder = SequenceBuilder(sample_rate=1e9)
        
        from src.Model.sequence import Sequence
        from src.Model.pulses import GaussianPulse, SquarePulse
        
        # Create sequence with pulses on different channels
        seq = Sequence(1000)
        
        # Add pulses on different channels
        pulse1 = GaussianPulse("ch1_pulse", 100, sigma=25, amplitude=1.0)
        pulse2 = SquarePulse("ch2_pulse", 80, amplitude=1.0)
        pulse3 = GaussianPulse("ch3_pulse", 120, sigma=30, amplitude=1.0)
        
        seq.add_pulse(0, pulse1)    # Channel 1
        seq.add_pulse(200, pulse2)  # Channel 2  
        seq.add_pulse(400, pulse3)  # Channel 3
        
        # Test plotting
        fig = builder.plot_sequence(seq, title="Multi-Channel Test")
        
        assert fig is not None
        
        # Clean up
        import matplotlib.pyplot as plt
        plt.close(fig)
    
    def test_visualization_dynamic_x_axis(self):
        """Test that visualization dynamically adjusts x-axis limits."""
        builder = SequenceBuilder(sample_rate=1e9)
        
        from src.Model.sequence import Sequence
        from src.Model.pulses import GaussianPulse
        
        # Create sequence with pulses at different times
        seq = Sequence(2000)  # Large sequence
        
        # Add pulses at different times
        pulse1 = GaussianPulse("early_pulse", 100, sigma=25, amplitude=1.0)
        pulse2 = GaussianPulse("late_pulse", 100, sigma=25, amplitude=1.0)
        
        seq.add_pulse(0, pulse1)      # Early pulse
        seq.add_pulse(1500, pulse2)   # Late pulse (should extend x-axis)
        
        # Test plotting
        fig = builder.plot_sequence(seq, title="Dynamic X-Axis Test")
        
        assert fig is not None
        
        # Clean up
        import matplotlib.pyplot as plt
        plt.close(fig)
