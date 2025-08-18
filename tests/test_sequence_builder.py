"""
Tests for the sequence builder module.

This module tests the conversion of SequenceDescription objects into
optimized Sequence objects for generic hardware processing.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch

from src.Model.sequence_builder import (
    SequenceBuilder, OptimizedSequence, BuildError, OptimizationError
)
from src.Model.sequence_description import (
    SequenceDescription, PulseDescription, PulseShape, TimingType,
    LoopDescription, ConditionalDescription
)


class TestSequenceBuilder:
    """Test the SequenceBuilder class."""
    
    def test_initialization(self):
        """Test that SequenceBuilder initializes correctly."""
        builder = SequenceBuilder(sample_rate=2e9)
        
        assert builder.sample_rate == 2e9
    
    def test_initialization_default_sample_rate(self):
        """Test that SequenceBuilder uses default sample rate."""
        builder = SequenceBuilder()
        
        assert builder.sample_rate == 1e9  # 1 GHz default
    
    def test_build_sequence_not_implemented(self):
        """Test that build_sequence raises NotImplementedError."""
        builder = SequenceBuilder()
        
        description = SequenceDescription(
            name="test_sequence",
            experiment_type="test",
            total_duration=1e-3,
            sample_rate=1e9
        )
        
        with pytest.raises(NotImplementedError, match="build_sequence method not implemented"):
            builder.build_sequence(description)
    
    def test_build_from_preset_not_implemented(self):
        """Test that build_from_preset raises NotImplementedError."""
        builder = SequenceBuilder()
        
        with pytest.raises(NotImplementedError, match="build_from_preset method not implemented"):
            builder.build_from_preset("odmr")
    
    def test_optimize_for_memory_constraints_not_implemented(self):
        """Test that optimize_for_memory_constraints raises NotImplementedError."""
        builder = SequenceBuilder()
        
        # Mock sequence object
        mock_sequence = Mock()
        mock_sequence.waveform = np.zeros(1000)
        
        with pytest.raises(NotImplementedError, match="optimize_for_memory_constraints method not implemented"):
            builder.optimize_for_memory_constraints(mock_sequence, 1000)
    
    def test_create_pulse_object_not_implemented(self):
        """Test that _create_pulse_object raises NotImplementedError."""
        builder = SequenceBuilder()
        
        pulse_desc = PulseDescription(
            name="test_pulse",
            pulse_type="pi/2",
            channel=1,
            shape=PulseShape.GAUSSIAN,
            duration=100e-9,
            amplitude=1.0
        )
        
        with pytest.raises(NotImplementedError, match="_create_pulse_object method not implemented"):
            builder._create_pulse_object(pulse_desc)
    
    def test_build_loop_sequence_not_implemented(self):
        """Test that _build_loop_sequence raises NotImplementedError."""
        builder = SequenceBuilder()
        
        loop_desc = LoopDescription(
            name="test_loop",
            iterations=10,
            start_time=0.0,
            end_time=1e-3
        )
        
        with pytest.raises(NotImplementedError, match="_build_loop_sequence method not implemented"):
            builder._build_loop_sequence(loop_desc)
    
    def test_build_conditional_sequence_not_implemented(self):
        """Test that _build_conditional_sequence raises NotImplementedError."""
        builder = SequenceBuilder()
        
        conditional_desc = ConditionalDescription(
            name="test_conditional",
            condition="if marker_1",
            start_time=0.0,
            end_time=1e-3
        )
        
        with pytest.raises(NotImplementedError, match="_build_conditional_sequence method not implemented"):
            builder._build_conditional_sequence(conditional_desc)
    
    def test_calculate_memory_usage_not_implemented(self):
        """Test that _calculate_memory_usage raises NotImplementedError."""
        builder = SequenceBuilder()
        
        mock_sequence = Mock()
        
        with pytest.raises(NotImplementedError, match="_calculate_memory_usage method not implemented"):
            builder._calculate_memory_usage(mock_sequence)
    
    def test_split_sequence_at_boundaries_not_implemented(self):
        """Test that _split_sequence_at_boundaries raises NotImplementedError."""
        builder = SequenceBuilder()
        
        mock_sequence = Mock()
        
        with pytest.raises(NotImplementedError, match="_split_sequence_at_boundaries method not implemented"):
            builder._split_sequence_at_boundaries(mock_sequence, 1000)
    
    def test_find_optimal_split_points_not_implemented(self):
        """Test that _find_optimal_split_points raises NotImplementedError."""
        builder = SequenceBuilder()
        
        mock_sequence = Mock()
        
        with pytest.raises(NotImplementedError, match="_find_optimal_split_points method not implemented"):
            builder._find_optimal_split_points(mock_sequence, 1000)


class TestOptimizedSequence:
    """Test the OptimizedSequence class."""
    
    def test_initialization(self):
        """Test that OptimizedSequence initializes correctly."""
        # Mock sequence objects
        mock_seq1 = Mock()
        mock_seq1.duration = 1e-3
        mock_seq1.waveform = np.zeros(1000)
        
        mock_seq2 = Mock()
        mock_seq2.duration = 2e-3
        mock_seq2.waveform = np.zeros(2000)
        
        sequences = [mock_seq1, mock_seq2]
        metadata = {"test": "value"}
        
        optimized = OptimizedSequence("test_sequence", sequences, metadata)
        
        assert optimized.name == "test_sequence"
        assert optimized.sequences == sequences
        assert optimized.metadata == metadata
        assert optimized.total_duration == 3e-3  # 1ms + 2ms
        assert optimized.total_samples == 3000   # 1000 + 2000
    
    def test_initialization_no_metadata(self):
        """Test that OptimizedSequence initializes without metadata."""
        mock_seq = Mock()
        mock_seq.duration = 1e-3
        mock_seq.waveform = np.zeros(1000)
        
        sequences = [mock_seq]
        
        optimized = OptimizedSequence("test_sequence", sequences)
        
        assert optimized.metadata == {}
        assert optimized.total_duration == 1e-3
        assert optimized.total_samples == 1000
    
    def test_get_chunk_valid_index(self):
        """Test getting a valid chunk."""
        mock_seq1 = Mock()
        mock_seq1.duration = 1e-3
        mock_seq1.waveform = np.zeros(1000)
        
        mock_seq2 = Mock()
        mock_seq2.duration = 2e-3
        mock_seq2.waveform = np.zeros(2000)
        
        sequences = [mock_seq1, mock_seq2]
        optimized = OptimizedSequence("test_sequence", sequences)
        
        chunk = optimized.get_chunk(0)
        assert chunk == mock_seq1
        
        chunk = optimized.get_chunk(1)
        assert chunk == mock_seq2
    
    def test_get_chunk_invalid_index_negative(self):
        """Test that getting chunk with negative index raises IndexError."""
        mock_seq = Mock()
        mock_seq.duration = 1e-3
        mock_seq.waveform = np.zeros(1000)
        
        sequences = [mock_seq]
        optimized = OptimizedSequence("test_sequence", sequences)
        
        with pytest.raises(IndexError, match="Chunk index -1 out of range"):
            optimized.get_chunk(-1)
    
    def test_get_chunk_invalid_index_too_large(self):
        """Test that getting chunk with too large index raises IndexError."""
        mock_seq = Mock()
        mock_seq.duration = 1e-3
        mock_seq.waveform = np.zeros(1000)
        
        sequences = [mock_seq]
        optimized = OptimizedSequence("test_sequence", sequences)
        
        with pytest.raises(IndexError, match="Chunk index 1 out of range"):
            optimized.get_chunk(1)
    
    def test_get_chunk_count(self):
        """Test getting chunk count."""
        mock_seq1 = Mock()
        mock_seq1.duration = 1e-3
        mock_seq1.waveform = np.zeros(1000)
        
        mock_seq2 = Mock()
        mock_seq2.duration = 2e-3
        mock_seq2.waveform = np.zeros(2000)
        
        sequences = [mock_seq1, mock_seq2]
        optimized = OptimizedSequence("test_sequence", sequences)
        
        assert optimized.get_chunk_count() == 2
    
    def test_get_total_memory_usage(self):
        """Test getting total memory usage."""
        mock_seq1 = Mock()
        mock_seq1.duration = 1e-3
        mock_seq1.waveform = np.zeros(1000)
        
        mock_seq2 = Mock()
        mock_seq2.duration = 2e-3
        mock_seq2.waveform = np.zeros(2000)
        
        sequences = [mock_seq1, mock_seq2]
        optimized = OptimizedSequence("test_sequence", sequences)
        
        assert optimized.get_total_memory_usage() == 3000
    
    def test_validate_memory_constraints_all_valid(self):
        """Test memory constraint validation when all chunks are valid."""
        mock_seq1 = Mock()
        mock_seq1.duration = 1e-3
        mock_seq1.waveform = np.zeros(1000)
        
        mock_seq2 = Mock()
        mock_seq2.duration = 2e-3
        mock_seq2.waveform = np.zeros(2000)
        
        sequences = [mock_seq1, mock_seq2]
        optimized = OptimizedSequence("test_sequence", sequences)
        
        assert optimized.validate_memory_constraints(3000) is True
        assert optimized.validate_memory_constraints(2000) is True
    
    def test_validate_memory_constraints_some_invalid(self):
        """Test memory constraint validation when some chunks are invalid."""
        mock_seq1 = Mock()
        mock_seq1.duration = 1e-3
        mock_seq1.waveform = np.zeros(1000)
        
        mock_seq2 = Mock()
        mock_seq2.duration = 2e-3
        mock_seq2.waveform = np.zeros(4000)  # Exceeds 3000 limit
        
        sequences = [mock_seq1, mock_seq2]
        optimized = OptimizedSequence("test_sequence", sequences)
        
        assert optimized.validate_memory_constraints(3000) is False
        assert optimized.validate_memory_constraints(5000) is True
    
    def test_get_optimization_summary(self):
        """Test getting optimization summary."""
        mock_seq1 = Mock()
        mock_seq1.duration = 1e-3
        mock_seq1.waveform = np.zeros(1000)
        
        mock_seq2 = Mock()
        mock_seq2.duration = 2e-3
        mock_seq2.waveform = np.zeros(2000)
        
        sequences = [mock_seq1, mock_seq2]
        metadata = {"test": "value"}
        optimized = OptimizedSequence("test_sequence", sequences, metadata)
        
        summary = optimized.get_optimization_summary()
        
        assert summary["name"] == "test_sequence"
        assert summary["total_chunks"] == 2
        assert summary["total_duration"] == 3e-3
        assert summary["total_samples"] == 3000
        assert summary["chunk_sizes"] == [1000, 2000]
        assert summary["memory_efficiency"] == 3000 / (2 * 2000)  # 0.75
        assert summary["metadata"] == metadata
    
    def test_get_optimization_summary_empty_sequences(self):
        """Test getting optimization summary with empty sequences."""
        optimized = OptimizedSequence("test_sequence", [])
        
        summary = optimized.get_optimization_summary()
        
        assert summary["name"] == "test_sequence"
        assert summary["total_chunks"] == 0
        assert summary["total_duration"] == 0
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
    """Integration tests for SequenceBuilder with mock dependencies."""
    
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
        
        # Test that builder methods are not implemented (as expected)
        with pytest.raises(NotImplementedError):
            builder.build_sequence(description)
    
    def test_sequence_builder_sample_rate_consistency(self):
        """Test that sample rate is consistent between builder and description."""
        sample_rate = 2e9  # 2 GHz
        
        builder = SequenceBuilder(sample_rate=sample_rate)
        
        description = SequenceDescription(
            name="test_sequence",
            experiment_type="test",
            total_duration=1e-3,
            sample_rate=sample_rate
        )
        
        # Both should have the same sample rate
        assert builder.sample_rate == description.sample_rate
        assert builder.sample_rate == 2e9
