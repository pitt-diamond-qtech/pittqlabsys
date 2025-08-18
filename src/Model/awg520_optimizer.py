"""
AWG520 Optimizer Module

This module converts optimized sequences into AWG520-specific format,
including waveform generation and sequence file creation.
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional, Tuple, Union
from pathlib import Path
import numpy as np
import logging

from .sequence import Sequence
from .pulses import Pulse


class AWG520SequenceOptimizer:
    """
    Converts optimized sequences to AWG520 format.
    
    This class handles:
    - Creating .wfm waveform files
    - Creating .seq sequence files
    - Memory optimization for AWG520 hardware
    - Sequence repetition and looping
    """
    
    def __init__(self):
        """Initialize the AWG520 optimizer."""
        # AWG520-specific constants
        self.max_waveform_samples = 4_000_000  # 4M words
        self.max_sequence_entries = 1000       # Maximum sequence table entries
        self.sample_rate = 1e9                 # 1 GHz default
    
    def create_waveforms(self, sequence: Sequence) -> Dict[str, np.ndarray]:
        """
        Generate waveform data for a sequence.
        
        Args:
            sequence: Sequence object
            
        Returns:
            Dictionary mapping pulse names to waveform data
            
        Raises:
            ValueError: If waveform generation fails
        """
        if sequence is None:
            raise ValueError("Sequence cannot be None")
        
        waveforms = {}
        
        # Extract pulses from the sequence
        # Sequence.pulses is a list of (start_index, pulse) tuples
        for start_index, pulse in sequence.pulses:
            if pulse.length > 0:  # Skip zero-length pulses
                waveform_data = self._generate_waveform_data(pulse)
                waveforms[pulse.name] = waveform_data
        
        return waveforms
    
    def create_sequence_file(self, sequence: Sequence) -> List[Dict[str, Any]]:
        """
        Generate sequence file entries for a sequence.
        
        Args:
            sequence: Sequence object
            
        Returns:
            List of sequence table entries
            
        Raises:
            ValueError: If sequence file creation fails
        """
        if sequence is None:
            raise ValueError("Sequence cannot be None")
        
        # Create waveform files first
        waveforms = self.create_waveforms(sequence)
        
        # Create sequence table entries
        entries = self._create_sequence_table_entries(sequence, waveforms)
        
        return entries
    
    def optimize_sequence_for_awg520(self, sequence: Sequence) -> AWG520Sequence:
        """
        Further optimize a sequence specifically for AWG520 hardware.
        
        Args:
            sequence: Sequence object
            
        Returns:
            AWG520Sequence object with hardware-specific optimizations
            
        Raises:
            ValueError: If optimization fails
        """
        if sequence is None:
            raise ValueError("Sequence cannot be None")
        
        if not isinstance(sequence, Sequence):
            raise ValueError("Input must be a Sequence object")
        
        # Check if sequence has long dead times that could benefit from repetition
        has_long_dead_times = self._has_long_dead_times(sequence)
        
        # Use compression if sequence exceeds memory OR has long dead times
        if not self._validate_awg520_constraints(sequence) or has_long_dead_times:
            # Try to create compressed sequence
            compressed = self._create_compressed_sequence(sequence)
            if compressed is None:
                raise ValueError("Sequence cannot be optimized for AWG520 constraints")
            return compressed
        
        # Create waveforms and sequence entries
        waveforms = self.create_waveforms(sequence)
        sequence_entries = self.create_sequence_file(sequence)
        
        # Create AWG520Sequence
        waveform_files = [f"{name}.wfm" for name in waveforms.keys()]
        return AWG520Sequence("optimized_sequence", waveform_files, sequence_entries, waveforms)
    
    def create_repetition_patterns(self, dead_time_samples: int) -> Dict[str, Any]:
        """
        Create repetition patterns for dead times.
        
        Args:
            dead_time_samples: Number of samples for dead time
            
        Returns:
            Repetition pattern information
        """
        # Calculate optimal repetition
        repetition_count = self._calculate_optimal_repetition(dead_time_samples)
        
        return {
            "type": "repetition",
            "repetition_count": repetition_count,
            "dead_time_samples": dead_time_samples
        }
    
    def _generate_waveform_data(self, pulse: Pulse) -> np.ndarray:
        """
        Generate waveform data from a pulse.
        
        Args:
            pulse: Pulse object
            
        Returns:
            Waveform data array
            
        Raises:
            ValueError: If data generation fails
        """
        if pulse.length <= 0:
            raise ValueError("Pulse length must be positive")
        
        try:
            # Generate samples using the pulse's generate_samples method
            waveform_data = pulse.generate_samples()
            
            # Ensure the length matches
            if len(waveform_data) != pulse.length:
                # Pad or truncate to match expected length
                if len(waveform_data) < pulse.length:
                    # Pad with zeros
                    padded = np.zeros(pulse.length)
                    padded[:len(waveform_data)] = waveform_data
                    waveform_data = padded
                else:
                    # Truncate
                    waveform_data = waveform_data[:pulse.length]
            
            return waveform_data
            
        except Exception as e:
            raise ValueError(f"Failed to generate waveform data: {e}")
    
    def _create_sequence_table_entries(self, sequence: Sequence, 
                                     waveforms: Dict[str, np.ndarray]) -> List[Dict[str, Any]]:
        """
        Create sequence table entries for .seq file.
        
        Args:
            sequence: Sequence object
            waveforms: Dictionary of waveform data
            
        Returns:
            List of sequence table entries
        """
        entries = []
        
        # Create entries for each pulse
        # Sequence.pulses is a list of (start_index, pulse) tuples
        for start_index, pulse in sequence.pulses:
            if pulse.name in waveforms:
                entry = {
                    "waveform_name": pulse.name,
                    "start_time": start_index,  # Use the start_index from the tuple
                    "duration": pulse.length,
                    "amplitude": getattr(pulse, 'amplitude', 1.0),
                    "channel": getattr(pulse, 'channel', 1)
                }
                entries.append(entry)
        
        return entries
    
    def _calculate_optimal_repetition(self, dead_time_samples: int) -> int:
        """
        Calculate optimal repetition count for dead times.
        
        Args:
            dead_time_samples: Number of samples for dead time
            
        Returns:
            Optimal repetition count
        """
        # Simple heuristic: use repetition for dead times longer than 100μs
        if dead_time_samples <= 100_000:  # 100μs at 1GHz
            return 1
        
        # For longer dead times, use repetition to save memory
        # Calculate how many repetitions we can use
        max_repetition = min(dead_time_samples // 100_000, 1000)  # Cap at 1000
        
        return max(1, max_repetition)

    def _has_long_dead_times(self, sequence: Sequence) -> bool:
        """
        Check if a sequence has long dead times that would benefit from repetition.
        
        Args:
            sequence: Sequence to check
            
        Returns:
            True if sequence has long dead times
        """
        if not sequence.pulses:
            return False
        
        # Sort pulses by start time
        sorted_pulses = sorted(sequence.pulses, key=lambda x: x[0])
        
        # Check dead times between pulses
        current_time = 0
        for start_index, pulse in sorted_pulses:
            # Check if there's a long dead time before this pulse
            if start_index > current_time:
                dead_time_samples = start_index - current_time
                if dead_time_samples > 100_000:  # 100μs threshold
                    return True
            
            current_time = start_index + pulse.length
        
        # Check if there's a long dead time after the last pulse
        if current_time < sequence.length:
            dead_time_samples = sequence.length - current_time
            if dead_time_samples > 100_000:  # 100μs threshold
                return True
        
        return False

    def _validate_awg520_constraints(self, sequence: Sequence) -> bool:
        """
        Validate that a sequence meets AWG520 constraints.
        
        Args:
            sequence: Sequence to validate
            
        Returns:
            True if constraints are met
        """
        # Check if sequence length exceeds memory limit
        if sequence.length > self.max_waveform_samples:
            return False
        
        # Check if we have too many pulses (would create too many sequence entries)
        if len(sequence.pulses) > self.max_sequence_entries:
            return False
        
        return True
    
    def _create_compressed_sequence(self, sequence: Sequence) -> AWG520Sequence:
        """
        Create a compressed sequence using AWG520 repetition capabilities.
        
        Args:
            sequence: Sequence to compress
            
        Returns:
            Compressed AWG520Sequence object
        """
        # Analyze the sequence to find dead times and pulses
        pulses = []
        dead_times = []
        
        # Sort pulses by start time
        sorted_pulses = sorted(sequence.pulses, key=lambda x: x[0])
        
        # Find dead times between pulses
        current_time = 0
        for start_index, pulse in sorted_pulses:
            # Check if there's a dead time before this pulse
            if start_index > current_time:
                dead_time_samples = start_index - current_time
                dead_times.append((current_time, dead_time_samples))
            
            # Add the pulse
            pulses.append((start_index, pulse))
            current_time = start_index + pulse.length
        
        # Check if there's a dead time after the last pulse
        if current_time < sequence.length:
            dead_time_samples = sequence.length - current_time
            dead_times.append((current_time, dead_time_samples))
        
        # Create sequence entries with repetition for dead times
        sequence_entries = []
        
        # Add pulse entries
        for start_index, pulse in pulses:
            entry = {
                "waveform_name": pulse.name,
                "start_time": start_index,
                "duration": pulse.length,
                "amplitude": getattr(pulse, 'amplitude', 1.0),
                "channel": getattr(pulse, 'channel', 1),
                "type": "pulse"
            }
            sequence_entries.append(entry)
        
        # Add repetition entries for dead times
        for start_time, dead_time_samples in dead_times:
            if dead_time_samples > 100_000:  # Only use repetition for dead times > 100μs
                repetition_count = self._calculate_optimal_repetition(dead_time_samples)
                
                entry = {
                    "waveform_name": "dead_time",
                    "start_time": start_time,
                    "duration": dead_time_samples // repetition_count,  # Duration of single repetition
                    "repetition_count": repetition_count,
                    "type": "repetition"
                }
                sequence_entries.append(entry)
            else:
                # For short dead times, just add a simple entry
                entry = {
                    "waveform_name": "dead_time",
                    "start_time": start_time,
                    "duration": dead_time_samples,
                    "type": "dead_time"
                }
                sequence_entries.append(entry)
        
        # Create waveforms (only for actual pulses, not dead times)
        waveforms = {}
        for start_index, pulse in pulses:
            if pulse.length > 0:
                waveform_data = self._generate_waveform_data(pulse)
                waveforms[pulse.name] = waveform_data
        
        # Create AWG520Sequence
        waveform_files = [f"{name}.wfm" for name in waveforms.keys()]
        return AWG520Sequence("compressed_sequence", waveform_files, sequence_entries, waveforms)


class AWG520Sequence:
    """
    A sequence optimized specifically for AWG520 hardware.
    
    This class represents a sequence that has been:
    - Optimized for AWG520 memory constraints
    - Compressed using repetition patterns
    - Ready for .wfm and .seq file generation
    """
    
    def __init__(self, name: str, waveform_files: List[str], 
                 sequence_entries: List[Dict[str, Any]],
                 waveform_data: Optional[Dict[str, np.ndarray]] = None):
        """
        Initialize an AWG520-optimized sequence.
        
        Args:
            name: Name of the sequence
            waveform_files: List of waveform file names
            sequence_entries: List of sequence table entries
            waveform_data: Optional map from waveform base name to sample arrays
        """
        self.name = name
        self.waveform_files = waveform_files
        self.sequence_entries = sequence_entries
        self.waveform_data = waveform_data or {}
    
    def get_waveform_files(self) -> List[str]:
        """Get list of required .wfm files."""
        return self.waveform_files
    
    def get_sequence_entries(self) -> List[Dict[str, Any]]:
        """Get sequence table entries for .seq file."""
        return self.sequence_entries
    
    def get_waveform_data(self) -> Dict[str, np.ndarray]:
        """Get waveform sample arrays keyed by base name."""
        return self.waveform_data


class OptimizationError(Exception):
    """Raised when AWG520 optimization fails."""
    pass
