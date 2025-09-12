"""
AWG520 Optimizer Module

This module converts calibrated sequences into AWG520-specific format,
including waveform generation and sequence file creation with proper
waveform-level memory optimization.
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
    Converts calibrated sequences to AWG520 format with waveform-level optimization.
    
    This class handles:
    - Identifying high/low resolution regions
    - Applying waveform-level compression (mathematical, RLE, delta encoding)
    - Creating optimized .wfm waveform files
    - Creating .seq sequence files
    - Memory optimization for AWG520 hardware constraints
    """
    
    def __init__(self):
        """Initialize the AWG520 optimizer."""
        # AWG520-specific constants
        self.max_waveform_samples = 4_000_000  # 4M words
        self.max_sequence_entries = 1000       # Maximum sequence table entries
        self.sample_rate = 1e9                 # 1 GHz default
        
        # Compression thresholds
        self.dead_time_threshold = 100_000     # 100μs - use compression above this
        self.high_resolution_threshold = 1000  # 1μs - high resolution below this
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
    
    def _identify_resolution_regions(self, sequence: Sequence) -> List[Dict[str, Any]]:
        """
        Identify high and low resolution regions in a sequence.
        
        Args:
            sequence: Sequence to analyze
            
        Returns:
            List of region dictionaries with type, start, end, and duration
        """
        if not sequence.pulses:
            return []
        
        regions = []
        
        # Sort pulses by start time
        sorted_pulses = sorted(sequence.pulses, key=lambda x: x[0])
        
        current_time = 0
        
        for start_index, pulse in sorted_pulses:
            # Check if there's a dead time before this pulse
            if start_index > current_time:
                dead_time_samples = start_index - current_time
                dead_time_region = {
                    'start_sample': current_time,
                    'end_sample': start_index,
                    'duration_samples': dead_time_samples,
                    'type': 'dead_time',
                    'resolution': 'low' if dead_time_samples > self.high_resolution_threshold else 'high'
                }
                regions.append(dead_time_region)
            
            # Add the pulse region
            pulse_region = {
                'start_sample': start_index,
                'end_sample': start_index + pulse.length,
                'duration_samples': pulse.length,
                'type': 'pulse',
                'resolution': 'high',  # Pulses always need high resolution
                'pulse_name': pulse.name
            }
            regions.append(pulse_region)
            
            current_time = start_index + pulse.length
        
        # Check if there's a dead time after the last pulse
        if current_time < sequence.length:
            dead_time_samples = sequence.length - current_time
            dead_time_region = {
                'start_sample': current_time,
                'end_sample': sequence.length,
                'duration_samples': dead_time_samples,
                'type': 'dead_time',
                'resolution': 'low' if dead_time_samples > self.high_resolution_threshold else 'high'
            }
            regions.append(dead_time_region)
        
        return regions
    
    def _calculate_memory_usage(self, sequence: Sequence, optimized: bool = False) -> Dict[str, Any]:
        """
        Calculate memory usage for a sequence.
        
        Args:
            sequence: Sequence to analyze
            optimized: Whether optimization has been applied
            
        Returns:
            Dictionary with memory usage information
        """
        total_samples = sequence.length
        raw_memory_bytes = total_samples * 2  # 2 bytes per sample (16-bit)
        
        if not optimized:
            return {
                'total_samples': total_samples,
                'raw_memory_bytes': raw_memory_bytes,
                'optimization_applied': False,
                'compression_ratio': 1.0
            }
        
        # Calculate optimized memory usage
        regions = self._identify_resolution_regions(sequence)
        optimized_samples = 0
        
        for region in regions:
            if region['type'] == 'pulse':
                # Pulses keep full resolution
                optimized_samples += region['duration_samples']
            elif region['type'] == 'dead_time':
                if region['duration_samples'] > self.dead_time_threshold:
                    # Long dead times use mathematical representation
                    optimized_samples += 100  # Minimal samples for math representation
                else:
                    # Short dead times keep full resolution
                    optimized_samples += region['duration_samples']
        
        optimized_memory_bytes = optimized_samples * 2
        compression_ratio = raw_memory_bytes / optimized_memory_bytes if optimized_memory_bytes > 0 else 1.0
        
        return {
            'total_samples': total_samples,
            'raw_memory_bytes': raw_memory_bytes,
            'optimized_samples': optimized_samples,
            'optimized_memory_bytes': optimized_memory_bytes,
            'optimization_applied': True,
            'compression_ratio': compression_ratio
        }
    
    def _apply_waveform_compression(self, sequence: Sequence) -> Sequence:
        """
        Apply waveform-level compression to a sequence.
        
        Args:
            sequence: Sequence to compress
            
        Returns:
            Compressed sequence
        """
        # Create a copy of the sequence for compression
        compressed_seq = Sequence(sequence.length)
        
        # Get resolution regions
        regions = self._identify_resolution_regions(sequence)
        
        for region in regions:
            if region['type'] == 'pulse':
                # Find the original pulse and add it
                for start_sample, pulse in sequence.pulses:
                    if (start_sample == region['start_sample'] and 
                        pulse.name == region['pulse_name']):
                        compressed_seq.add_pulse(start_sample, pulse)
                        break
            elif region['type'] == 'dead_time':
                if region['duration_samples'] > self.dead_time_threshold:
                    # Create a compressed dead time pulse
                    compressed_pulse = self._create_compressed_dead_time_pulse(
                        region['duration_samples']
                    )
                    compressed_seq.add_pulse(region['start_sample'], compressed_pulse)
                else:
                    # Keep short dead times as-is
                    pass  # No pulse added for dead time
        
        return compressed_seq
    
    def _create_compressed_dead_time_pulse(self, duration_samples: int) -> Pulse:
        """
        Create a compressed dead time pulse.
        
        Args:
            duration_samples: Duration in samples
            
        Returns:
            Compressed dead time pulse
        """
        # Create a minimal pulse that represents the dead time
        # This will be expanded during waveform generation
        from .pulses import SquarePulse
        
        compressed_pulse = SquarePulse(
            name=f"dead_time_{duration_samples}",
            length=min(100, duration_samples // 100),  # Compress to max 100 samples
            amplitude=0.0
        )
        
        # Store compression metadata
        compressed_pulse.compression_metadata = {
            'original_duration': duration_samples,
            'compression_type': 'mathematical',
            'compression_ratio': duration_samples / compressed_pulse.length
        }
        
        return compressed_pulse
    
    def _generate_mathematical_dead_time(self, dead_time_region: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate mathematical representation for dead time regions.
        
        Args:
            dead_time_region: Dead time region information
            
        Returns:
            Mathematical representation dictionary
        """
        duration_samples = dead_time_region['duration_samples']
        
        if duration_samples <= self.dead_time_threshold:
            # Use simple zero representation
            return {
                'type': 'mathematical',
                'formula': 'zeros',
                'parameters': {'length': duration_samples},
                'compressed_samples': duration_samples,
                'compression_ratio': 1.0
            }
        
        # Use mathematical compression for long dead times
        compressed_samples = min(100, duration_samples // 1000)
        
        return {
            'type': 'mathematical',
            'formula': 'zeros',
            'parameters': {'length': duration_samples, 'compressed': True},
            'compressed_samples': compressed_samples,
            'compression_ratio': duration_samples / compressed_samples
        }
    
    def _apply_rle_compression(self, sequence: Sequence) -> Sequence:
        """
        Apply Run-Length Encoding compression.
        
        Args:
            sequence: Sequence to compress
            
        Returns:
            RLE-compressed sequence
        """
        # For now, return the sequence as-is
        # RLE compression would be implemented for repetitive patterns
        return sequence
    
    def _apply_delta_encoding(self, sequence: Sequence) -> Sequence:
        """
        Apply delta encoding for smooth waveforms.
        
        Args:
            sequence: Sequence to compress
            
        Returns:
            Delta-encoded sequence
        """
        # For now, return the sequence as-is
        # Delta encoding would be implemented for smooth waveforms
        return sequence
    
    def _create_optimized_waveforms(self, sequence: Sequence) -> Dict[str, np.ndarray]:
        """
        Create optimized waveform files.
        
        Args:
            sequence: Sequence to optimize
            
        Returns:
            Dictionary mapping pulse names to waveform data
        """
        waveforms = {}
        
        # Extract pulses from the sequence
        for start_index, pulse in sequence.pulses:
            if pulse.length > 0:
                if hasattr(pulse, 'compression_metadata'):
                    # Handle compressed pulses
                    waveform_data = self._generate_compressed_waveform(pulse)
                else:
                    # Handle regular pulses
                    waveform_data = self._generate_waveform_data(pulse)
                
                waveforms[pulse.name] = waveform_data
        
        return waveforms
    
    def _generate_compressed_waveform(self, pulse: Pulse) -> np.ndarray:
        """
        Generate waveform data for a compressed pulse.
        
        Args:
            pulse: Compressed pulse with metadata
            
        Returns:
            Expanded waveform data
        """
        metadata = pulse.compression_metadata
        
        if metadata['compression_type'] == 'mathematical':
            # Expand mathematical representation
            original_duration = metadata['original_duration']
            return np.zeros(original_duration)
        
        # Fallback to regular generation
        return self._generate_waveform_data(pulse)
    
    def _generate_sequence_file_entries(self, sequence: Sequence) -> List[Dict[str, Any]]:
        """
        Generate .seq file entries.
        
        Args:
            sequence: Sequence to convert
            
        Returns:
            List of sequence table entries
        """
        entries = []
        
        # Create entries for each pulse
        for start_index, pulse in sequence.pulses:
            entry = {
                "waveform_name": pulse.name,
                "start_time": start_index,
                "duration": pulse.length,
                "amplitude": getattr(pulse, 'amplitude', 1.0),
                "channel": getattr(pulse, 'channel', 1),
                "type": "pulse"
            }
            
            # Add compression metadata if available
            if hasattr(pulse, 'compression_metadata'):
                entry["compression"] = pulse.compression_metadata
            
            entries.append(entry)
        
        return entries
    
    def _handle_variable_sampling_regions(self, sequence: Sequence) -> Sequence:
        """
        Handle variable sampling regions.
        
        Args:
            sequence: Sequence to process
            
        Returns:
            Sequence with variable sampling applied
        """
        # For now, return the sequence as-is
        # Variable sampling would be implemented for mixed-resolution sequences
        return sequence
    
    def _calculate_compression_ratios(self, sequence: Sequence) -> Dict[str, float]:
        """
        Calculate compression ratios for different region types.
        
        Args:
            sequence: Sequence to analyze
            
        Returns:
            Dictionary with compression ratios
        """
        regions = self._identify_resolution_regions(sequence)
        
        dead_time_compression = 1.0
        pulse_compression = 1.0
        
        for region in regions:
            if region['type'] == 'dead_time' and region['duration_samples'] > self.dead_time_threshold:
                # Calculate potential compression for dead time
                potential_compression = region['duration_samples'] / 100  # Assume 100 sample compression
                dead_time_compression = max(dead_time_compression, potential_compression)
        
        # Calculate overall compression
        memory_before = self._calculate_memory_usage(sequence, optimized=False)
        memory_after = self._calculate_memory_usage(sequence, optimized=True)
        overall_compression = memory_before['compression_ratio']
        
        return {
            'dead_time_compression': dead_time_compression,
            'pulse_compression': pulse_compression,
            'overall_compression': overall_compression
        }
    
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
        
        return self._create_optimized_waveforms(sequence)
    
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
        entries = self._generate_sequence_file_entries(sequence)
        
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
        
        # Apply waveform compression
        compressed_sequence = self._apply_waveform_compression(sequence)
        
        # Create waveforms and sequence entries
        waveforms = self.create_waveforms(compressed_sequence)
        sequence_entries = self.create_sequence_file(compressed_sequence)
        
        # Create AWG520Sequence
        waveform_files = [f"{name}.wfm" for name in waveforms.keys()]
        return AWG520Sequence("optimized_sequence", waveform_files, sequence_entries, waveforms)
    
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


class AWG520Sequence:
    """
    A sequence optimized specifically for AWG520 hardware.
    
    This class represents a sequence that has been:
    - Optimized for AWG520 memory constraints
    - Compressed using waveform-level optimization
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
