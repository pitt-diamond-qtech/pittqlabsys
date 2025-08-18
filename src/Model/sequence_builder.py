"""
Sequence Builder Module

This module converts SequenceDescription objects into optimized Sequence objects
that can be processed by hardware-specific optimizers.
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional, Tuple, TYPE_CHECKING
from pathlib import Path
import numpy as np

from .sequence_description import SequenceDescription, PulseDescription, LoopDescription, ConditionalDescription
from .pulses import Pulse, GaussianPulse, SechPulse, LorentzianPulse, SquarePulse, DataPulse
if TYPE_CHECKING:
    from .sequence import Sequence


class SequenceBuilder:
    """
    Converts SequenceDescription objects to optimized Sequence objects.
    
    This class handles:
    - Building sequences from descriptions
    - Generic memory optimization (hardware-agnostic)
    - Splitting long sequences into chunks
    - Handling loops and conditionals
    """
    
    def __init__(self, sample_rate: float = 1e9):
        """
        Initialize the sequence builder.
        
        Args:
            sample_rate: Default sample rate in Hz
        """
        self.sample_rate = sample_rate
        # Note: Memory constraints are handled by hardware-specific optimizers
        # This class is hardware-agnostic
    
    def build_sequence(self, description: SequenceDescription) -> OptimizedSequence:
        """
        Build an optimized sequence from a sequence description.
        
        Args:
            description: SequenceDescription object
            
        Returns:
            OptimizedSequence object ready for hardware processing
            
        Raises:
            ValueError: If description is invalid
            BuildError: If sequence building fails
        """
        raise NotImplementedError("build_sequence method not implemented")
    
    def build_from_preset(self, preset_name: str, **parameters) -> OptimizedSequence:
        """
        Build a sequence from a preset experiment.
        
        Args:
            preset_name: Name of the preset experiment
            **parameters: Custom parameters for the preset
            
        Returns:
            OptimizedSequence object
            
        Raises:
            ValueError: If preset not found
        """
        raise NotImplementedError("build_from_preset method not implemented")
    
    def optimize_for_memory_constraints(self, sequence: Sequence, max_samples_per_chunk: int) -> List[Sequence]:
        """
        Split a sequence into memory-optimized chunks for any hardware.
        
        Args:
            sequence: Original sequence to optimize
            max_samples_per_chunk: Maximum samples allowed per chunk
            
        Returns:
            List of optimized sequences that fit within memory constraints
            
        Raises:
            OptimizationError: If optimization fails
        """
        raise NotImplementedError("optimize_for_memory_constraints method not implemented")
    
    def _create_pulse_object(self, pulse_desc: PulseDescription) -> Pulse:
        """
        Create a Pulse object from a PulseDescription.
        
        Args:
            pulse_desc: Pulse description
            
        Returns:
            Pulse object of appropriate type
        """
        raise NotImplementedError("_create_pulse_object method not implemented")
    
    def _build_loop_sequence(self, loop_desc: LoopDescription) -> Sequence:
        """
        Build a sequence for a loop block.
        
        Args:
            loop_desc: Loop description
            
        Returns:
            Sequence object for the loop
        """
        raise NotImplementedError("_build_loop_sequence method not implemented")
    
    def _build_conditional_sequence(self, conditional_desc: ConditionalDescription) -> Sequence:
        """
        Build a sequence for a conditional block.
        
        Args:
            conditional_desc: Conditional description
            
        Returns:
            Sequence object for the conditional
        """
        raise NotImplementedError("_build_conditional_sequence method not implemented")
    
    def _calculate_memory_usage(self, sequence: Sequence) -> int:
        """
        Calculate memory usage of a sequence in samples.
        
        Args:
            sequence: Sequence to analyze
            
        Returns:
            Number of samples required
        """
        raise NotImplementedError("_calculate_memory_usage method not implemented")
    
    def _split_sequence_at_boundaries(self, sequence: Sequence, max_samples: int) -> List[Sequence]:
        """
        Split a sequence at natural boundaries to fit memory constraints.
        
        Args:
            sequence: Sequence to split
            max_samples: Maximum samples per chunk
            
        Returns:
            List of split sequences
        """
        raise NotImplementedError("_split_sequence_at_boundaries method not implemented")
    
    def _find_optimal_split_points(self, sequence: Sequence, max_samples: int) -> List[int]:
        """
        Find optimal points to split a sequence for memory optimization.
        
        Args:
            sequence: Sequence to analyze
            max_samples: Maximum samples per chunk
            
        Returns:
            List of sample indices for splitting
        """
        raise NotImplementedError("_find_optimal_split_points method not implemented")


class OptimizedSequence:
    """
    An optimized sequence that has been processed for hardware compatibility.
    
    This class represents a sequence that has been:
    - Validated for memory constraints
    - Split into manageable chunks
    - Optimized for general hardware constraints
    """
    
    def __init__(self, name: str, sequences: List[Sequence], metadata: Dict[str, Any] = None):
        """
        Initialize an optimized sequence.
        
        Args:
            name: Name of the sequence
            sequences: List of sequence chunks
            metadata: Additional metadata
        """
        self.name = name
        self.sequences = sequences
        self.metadata = metadata or {}
        self.total_duration = sum(seq.duration for seq in sequences)
        self.total_samples = sum(len(seq.waveform) for seq in sequences)
    
    def get_chunk(self, index: int) -> Sequence:
        """
        Get a specific chunk of the sequence.
        
        Args:
            index: Chunk index
            
        Returns:
            Sequence object for the chunk
            
        Raises:
            IndexError: If index is out of range
        """
        if index < 0 or index >= len(self.sequences):
            raise IndexError(f"Chunk index {index} out of range")
        return self.sequences[index]
    
    def get_chunk_count(self) -> int:
        """Get the number of chunks in this sequence."""
        return len(self.sequences)
    
    def get_total_memory_usage(self) -> int:
        """Get total memory usage in samples."""
        return self.total_samples
    
    def validate_memory_constraints(self, max_samples_per_chunk: int) -> bool:
        """
        Validate that all chunks fit within memory constraints.
        
        Args:
            max_samples_per_chunk: Maximum samples allowed per chunk
            
        Returns:
            True if all chunks are within limits
        """
        return all(len(seq.waveform) <= max_samples_per_chunk for seq in self.sequences)
    
    def get_optimization_summary(self) -> Dict[str, Any]:
        """
        Get a summary of optimization results.
        
        Returns:
            Dictionary with optimization statistics
        """
        chunk_sizes = [len(seq.waveform) for seq in self.sequences]
        if len(self.sequences) == 0 or len(chunk_sizes) == 0:
            memory_efficiency = 0.0
        else:
            memory_efficiency = self.total_samples / (len(self.sequences) * max(chunk_sizes))
        return {
            "name": self.name,
            "total_chunks": len(self.sequences),
            "total_duration": self.total_duration,
            "total_samples": self.total_samples,
            "chunk_sizes": chunk_sizes,
            "memory_efficiency": memory_efficiency,
            "metadata": self.metadata
        }


class BuildError(Exception):
    """Raised when sequence building fails."""
    pass


class OptimizationError(Exception):
    """Raised when sequence optimization fails."""
    pass
