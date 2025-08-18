"""
Tests for the AWG520 optimizer module.

This module tests the conversion of optimized sequences into AWG520-specific format,
including waveform generation and sequence file creation.
"""

import pytest
import numpy as np
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.Model.awg520_optimizer import (
    AWG520SequenceOptimizer, AWG520Sequence,
    WaveformError, SequenceError, OptimizationError,
    RepetitionError, CompressionError
)
from src.Model.sequence_builder import OptimizedSequence


class TestAWG520SequenceOptimizer:
    """Test the AWG520SequenceOptimizer class."""
    
    def test_initialization(self):
        """Test that AWG520SequenceOptimizer initializes correctly."""
        optimizer = AWG520SequenceOptimizer(output_dir="test_output")
        
        assert optimizer.output_dir == Path("test_output")
        assert optimizer.max_waveform_samples == 4_000_000  # 4M words
        assert optimizer.max_sequence_entries == 1000
        assert optimizer.sample_rate == 1e9  # 1 GHz
        assert optimizer.logger is not None
    
    def test_initialization_default_output_dir(self):
        """Test that AWG520SequenceOptimizer uses default output directory."""
        optimizer = AWG520SequenceOptimizer()
        
        assert optimizer.output_dir == Path("awg520_output")
    
    def test_initialization_creates_output_dir(self, tmp_path):
        """Test that output directory is created if it doesn't exist."""
        test_dir = tmp_path / "awg520_test"
        
        optimizer = AWG520SequenceOptimizer(output_dir=str(test_dir))
        
        assert test_dir.exists()
        assert test_dir.is_dir()
    
    def test_create_waveforms_not_implemented(self):
        """Test that create_waveforms raises NotImplementedError."""
        optimizer = AWG520SequenceOptimizer()
        
        mock_optimized_sequence = Mock(spec=OptimizedSequence)
        
        with pytest.raises(NotImplementedError, match="create_waveforms method not implemented"):
            optimizer.create_waveforms(mock_optimized_sequence)
    
    def test_create_sequence_file_not_implemented(self):
        """Test that create_sequence_file raises NotImplementedError."""
        optimizer = AWG520SequenceOptimizer()
        
        mock_optimized_sequence = Mock(spec=OptimizedSequence)
        mock_waveform_files = [Path("test1.wfm"), Path("test2.wfm")]
        
        with pytest.raises(NotImplementedError, match="create_sequence_file method not implemented"):
            optimizer.create_sequence_file(mock_optimized_sequence, mock_waveform_files)
    
    def test_optimize_sequence_for_awg520_not_implemented(self):
        """Test that optimize_sequence_for_awg520 raises NotImplementedError."""
        optimizer = AWG520SequenceOptimizer()
        
        mock_optimized_sequence = Mock(spec=OptimizedSequence)
        
        with pytest.raises(NotImplementedError, match="optimize_sequence_for_awg520 method not implemented"):
            optimizer.optimize_sequence_for_awg520(mock_optimized_sequence)
    
    def test_create_repetition_patterns_not_implemented(self):
        """Test that create_repetition_patterns raises NotImplementedError."""
        optimizer = AWG520SequenceOptimizer()
        
        mock_sequence = Mock()
        
        with pytest.raises(NotImplementedError, match="create_repetition_patterns method not implemented"):
            optimizer.create_repetition_patterns(mock_sequence, 10)
    
    def test_generate_waveform_data_not_implemented(self):
        """Test that _generate_waveform_data raises NotImplementedError."""
        optimizer = AWG520SequenceOptimizer()
        
        mock_sequence = Mock()
        
        with pytest.raises(NotImplementedError, match="_generate_waveform_data method not implemented"):
            optimizer._generate_waveform_data(mock_sequence)
    
    def test_create_sequence_table_entries_not_implemented(self):
        """Test that _create_sequence_table_entries raises NotImplementedError."""
        optimizer = AWG520SequenceOptimizer()
        
        mock_optimized_sequence = Mock(spec=OptimizedSequence)
        mock_waveform_files = [Path("test1.wfm"), Path("test2.wfm")]
        
        with pytest.raises(NotImplementedError, match="_create_sequence_table_entries method not implemented"):
            optimizer._create_sequence_table_entries(mock_optimized_sequence, mock_waveform_files)
    
    def test_calculate_optimal_repetition_not_implemented(self):
        """Test that _calculate_optimal_repetition raises NotImplementedError."""
        optimizer = AWG520SequenceOptimizer()
        
        with pytest.raises(NotImplementedError, match="_calculate_optimal_repetition method not implemented"):
            optimizer._calculate_optimal_repetition(1e-3, 10e-3)
    
    def test_validate_awg520_constraints_not_implemented(self):
        """Test that _validate_awg520_constraints raises NotImplementedError."""
        optimizer = AWG520SequenceOptimizer()
        
        mock_sequence = Mock()
        
        with pytest.raises(NotImplementedError, match="_validate_awg520_constraints method not implemented"):
            optimizer._validate_awg520_constraints(mock_sequence)
    
    def test_create_compressed_sequence_not_implemented(self):
        """Test that _create_compressed_sequence raises NotImplementedError."""
        optimizer = AWG520SequenceOptimizer()
        
        mock_sequences = [Mock(), Mock()]
        
        with pytest.raises(NotImplementedError, match="_create_compressed_sequence method not implemented"):
            optimizer._create_compressed_sequence(mock_sequences)
    
    def test_hardware_constants(self):
        """Test that hardware constants are set correctly."""
        optimizer = AWG520SequenceOptimizer()
        
        # AWG520-specific constants
        assert optimizer.max_waveform_samples == 4_000_000  # 4M words
        assert optimizer.max_sequence_entries == 1000
        assert optimizer.sample_rate == 1e9  # 1 GHz
        
        # These should match the actual AWG520 specifications
        assert optimizer.max_waveform_samples == 4_000_000


class TestAWG520Sequence:
    """Test the AWG520Sequence class."""
    
    def test_initialization(self):
        """Test that AWG520Sequence initializes correctly."""
        # Mock sequence objects
        mock_seq1 = Mock()
        mock_seq1.duration = 1e-3
        mock_seq1.waveform = np.zeros(1000)
        
        mock_seq2 = Mock()
        mock_seq2.duration = 2e-3
        mock_seq2.waveform = np.zeros(2000)
        
        sequences = [mock_seq1, mock_seq2]
        repetition_patterns = [{"type": "loop", "iterations": 10}]
        
        awg_seq = AWG520Sequence("test_sequence", sequences, repetition_patterns)
        
        assert awg_seq.name == "test_sequence"
        assert awg_seq.sequences == sequences
        assert awg_seq.repetition_patterns == repetition_patterns
        assert awg_seq.total_duration == 3e-3  # 1ms + 2ms
        assert awg_seq.memory_usage == 3000   # 1000 + 2000
    
    def test_initialization_no_repetition_patterns(self):
        """Test that AWG520Sequence initializes without repetition patterns."""
        mock_seq = Mock()
        mock_seq.duration = 1e-3
        mock_seq.waveform = np.zeros(1000)
        
        sequences = [mock_seq]
        
        awg_seq = AWG520Sequence("test_sequence", sequences)
        
        assert awg_seq.repetition_patterns == []
        assert awg_seq.total_duration == 1e-3
        assert awg_seq.memory_usage == 1000
    
    def test_get_waveform_files_not_implemented(self):
        """Test that get_waveform_files raises NotImplementedError."""
        mock_seq = Mock()
        mock_seq.duration = 1e-3
        mock_seq.waveform = np.zeros(1000)
        
        awg_seq = AWG520Sequence("test_sequence", [mock_seq])
        
        with pytest.raises(NotImplementedError, match="get_waveform_files method not implemented"):
            awg_seq.get_waveform_files()
    
    def test_get_sequence_entries_not_implemented(self):
        """Test that get_sequence_entries raises NotImplementedError."""
        mock_seq = Mock()
        mock_seq.duration = 1e-3
        mock_seq.waveform = np.zeros(1000)
        
        awg_seq = AWG520Sequence("test_sequence", [mock_seq])
        
        with pytest.raises(NotImplementedError, match="get_sequence_entries method not implemented"):
            awg_seq.get_sequence_entries()
    
    def test_get_memory_usage(self):
        """Test getting memory usage."""
        mock_seq1 = Mock()
        mock_seq1.duration = 1e-3
        mock_seq1.waveform = np.zeros(1000)
        
        mock_seq2 = Mock()
        mock_seq2.duration = 2e-3
        mock_seq2.waveform = np.zeros(2000)
        
        sequences = [mock_seq1, mock_seq2]
        awg_seq = AWG520Sequence("test_sequence", sequences)
        
        assert awg_seq.get_memory_usage() == 3000
    
    def test_get_compression_ratio_no_patterns(self):
        """Test compression ratio calculation with no repetition patterns."""
        mock_seq = Mock()
        mock_seq.duration = 1e-3
        mock_seq.waveform = np.zeros(1000)
        
        awg_seq = AWG520Sequence("test_sequence", [mock_seq])
        
        assert awg_seq.get_compression_ratio() == 1.0
    
    def test_get_compression_ratio_with_patterns(self):
        """Test compression ratio calculation with repetition patterns."""
        mock_seq = Mock()
        mock_seq.duration = 1e-3
        mock_seq.waveform = np.zeros(1000)
        
        repetition_patterns = [
            {"original_samples": 10000, "compressed_samples": 1000},
            {"original_samples": 5000, "compressed_samples": 500}
        ]
        
        awg_seq = AWG520Sequence("test_sequence", [mock_seq], repetition_patterns)
        
        # (10000 + 5000) / (1000 + 500) = 15000 / 1500 = 10.0
        assert awg_seq.get_compression_ratio() == 10.0
    
    def test_get_compression_ratio_zero_compressed(self):
        """Test compression ratio calculation when compressed samples is zero."""
        mock_seq = Mock()
        mock_seq.duration = 1e-3
        mock_seq.waveform = np.zeros(1000)
        
        repetition_patterns = [
            {"original_samples": 10000, "compressed_samples": 0}
        ]
        
        awg_seq = AWG520Sequence("test_sequence", [mock_seq], repetition_patterns)
        
        # Should return 1.0 when compressed_samples is 0
        assert awg_seq.get_compression_ratio() == 1.0
    
    def test_validate_hardware_constraints_all_valid(self):
        """Test hardware constraint validation when all sequences are valid."""
        mock_seq1 = Mock()
        mock_seq1.duration = 1e-3
        mock_seq1.waveform = np.zeros(1000)
        
        mock_seq2 = Mock()
        mock_seq2.duration = 2e-3
        mock_seq2.waveform = np.zeros(2000)
        
        sequences = [mock_seq1, mock_seq2]
        awg_seq = AWG520Sequence("test_sequence", sequences)
        
        # Mock get_sequence_entries to return valid number of entries
        with patch.object(awg_seq, 'get_sequence_entries', return_value=[1, 2, 3]):
            assert awg_seq.validate_hardware_constraints() is True
    
    def test_validate_hardware_constraints_sequence_too_large(self):
        """Test hardware constraint validation when a sequence is too large."""
        mock_seq1 = Mock()
        mock_seq1.duration = 1e-3
        mock_seq1.waveform = np.zeros(1000)
        
        mock_seq2 = Mock()
        mock_seq2.duration = 2e-3
        mock_seq2.waveform = np.zeros(5_000_000)  # Exceeds 4M limit
        
        sequences = [mock_seq1, mock_seq2]
        awg_seq = AWG520Sequence("test_sequence", sequences)
        
        assert awg_seq.validate_hardware_constraints() is False
    
    def test_validate_hardware_constraints_too_many_entries(self):
        """Test hardware constraint validation when there are too many sequence entries."""
        mock_seq = Mock()
        mock_seq.duration = 1e-3
        mock_seq.waveform = np.zeros(1000)
        
        sequences = [mock_seq]
        awg_seq = AWG520Sequence("test_sequence", sequences)
        
        # Mock get_sequence_entries to return too many entries
        with patch.object(awg_seq, 'get_sequence_entries', return_value=list(range(1001))):
            assert awg_seq.validate_hardware_constraints() is False


class TestWaveformError:
    """Test the WaveformError exception."""
    
    def test_waveform_error_creation(self):
        """Test creating a WaveformError."""
        error = WaveformError("Test waveform error")
        assert str(error) == "Test waveform error"
    
    def test_waveform_error_inheritance(self):
        """Test that WaveformError inherits from Exception."""
        error = WaveformError("Test")
        assert isinstance(error, Exception)


class TestSequenceError:
    """Test the SequenceError exception."""
    
    def test_sequence_error_creation(self):
        """Test creating a SequenceError."""
        error = SequenceError("Test sequence error")
        assert str(error) == "Test sequence error"
    
    def test_sequence_error_inheritance(self):
        """Test that SequenceError inherits from Exception."""
        error = SequenceError("Test")
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


class TestRepetitionError:
    """Test the RepetitionError exception."""
    
    def test_repetition_error_creation(self):
        """Test creating a RepetitionError."""
        error = RepetitionError("Test repetition error")
        assert str(error) == "Test repetition error"
    
    def test_repetition_error_inheritance(self):
        """Test that RepetitionError inherits from Exception."""
        error = RepetitionError("Test")
        assert isinstance(error, Exception)


class TestCompressionError:
    """Test the CompressionError exception."""
    
    def test_compression_error_creation(self):
        """Test creating a CompressionError."""
        error = CompressionError("Test compression error")
        assert str(error) == "Test compression error"
    
    def test_compression_error_inheritance(self):
        """Test that CompressionError inherits from Exception."""
        error = CompressionError("Test")
        assert isinstance(error, Exception)


class TestAWG520OptimizerIntegration:
    """Integration tests for AWG520SequenceOptimizer."""
    
    def test_optimizer_with_mock_sequence(self):
        """Test AWG520SequenceOptimizer with a mock sequence."""
        optimizer = AWG520SequenceOptimizer(output_dir="test_output")
        
        # Create a mock optimized sequence
        mock_optimized_sequence = Mock(spec=OptimizedSequence)
        mock_optimized_sequence.name = "test_sequence"
        mock_optimized_sequence.get_chunk_count.return_value = 2
        
        # Test that methods are not implemented (as expected)
        with pytest.raises(NotImplementedError):
            optimizer.create_waveforms(mock_optimized_sequence)
        
        with pytest.raises(NotImplementedError):
            optimizer.create_sequence_file(mock_optimized_sequence, [])
    
    def test_optimizer_memory_constraints(self):
        """Test that AWG520SequenceOptimizer respects memory constraints."""
        optimizer = AWG520SequenceOptimizer()
        
        # Verify the memory limit is set correctly
        assert optimizer.max_waveform_samples == 4_000_000  # 4M words
        
        # This should be the same as the AWG520 hardware limit
        assert optimizer.max_waveform_samples == 4_000_000
        
        # Verify sequence entry limit
        assert optimizer.max_sequence_entries == 1000
    
    def test_optimizer_sample_rate_consistency(self):
        """Test that sample rate is consistent."""
        sample_rate = 2e9  # 2 GHz
        
        optimizer = AWG520SequenceOptimizer()
        
        # Default should be 1 GHz
        assert optimizer.sample_rate == 1e9
        
        # Could be made configurable in the future
        # assert optimizer.sample_rate == sample_rate
    
    def test_optimizer_output_directory_handling(self, tmp_path):
        """Test that output directory handling works correctly."""
        test_dir = tmp_path / "awg520_test_output"
        
        # Directory should not exist initially
        assert not test_dir.exists()
        
        # Create optimizer - should create directory
        optimizer = AWG520SequenceOptimizer(output_dir=str(test_dir))
        
        # Directory should now exist
        assert test_dir.exists()
        assert test_dir.is_dir()
        
        # Should be able to create files in the directory
        test_file = test_dir / "test.txt"
        test_file.write_text("test")
        assert test_file.exists()
    
    def test_awg520_sequence_validation_integration(self):
        """Test AWG520Sequence validation with realistic data."""
        # Create mock sequences with realistic sizes
        mock_seq1 = Mock()
        mock_seq1.duration = 1e-3
        mock_seq1.waveform = np.zeros(1_000_000)  # 1M samples
        
        mock_seq2 = Mock()
        mock_seq2.duration = 2e-3
        mock_seq2.waveform = np.zeros(2_000_000)  # 2M samples
        
        sequences = [mock_seq1, mock_seq2]
        
        # Create AWG520Sequence
        awg_seq = AWG520Sequence("test_sequence", sequences)
        
        # Test memory usage calculation
        assert awg_seq.get_memory_usage() == 3_000_000  # 3M samples
        
        # Test hardware constraints
        with patch.object(awg_seq, 'get_sequence_entries', return_value=list(range(100))):
            assert awg_seq.validate_hardware_constraints() is True
        
        # Test with too many sequence entries
        with patch.object(awg_seq, 'get_sequence_entries', return_value=list(range(1001))):
            assert awg_seq.validate_hardware_constraints() is False
