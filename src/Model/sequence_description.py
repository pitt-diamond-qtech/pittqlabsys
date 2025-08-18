"""
Sequence Description Module

This module defines the intermediate data structures used to represent
sequence descriptions between text parsing and sequence building.
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum


class PulseShape(Enum):
    """Supported pulse shapes."""
    GAUSSIAN = "gaussian"
    SECH = "sech"
    LORENTZIAN = "lorentzian"
    SQUARE = "square"
    SINE = "sine"
    LOADFILE = "loadfile"


class TimingType(Enum):
    """Types of timing specifications."""
    ABSOLUTE = "absolute"      # "at 1ms"
    RELATIVE = "relative"      # "wait 1ms"
    VARIABLE = "variable"      # "wait tau"


@dataclass
class PulseDescription:
    """Description of a single pulse in a sequence."""
    
    name: str
    pulse_type: str  # e.g., "pi/2", "pi", "custom"
    channel: int
    shape: PulseShape
    duration: float  # in seconds
    amplitude: float = 1.0
    timing: float = 0.0  # absolute time in seconds
    timing_type: TimingType = TimingType.ABSOLUTE
    parameters: Dict[str, Any] = field(default_factory=dict)
    markers: List[MarkerDescription] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate pulse description after initialization."""
        if self.channel not in [1, 2]:
            raise ValueError("Channel must be 1 or 2")
        if self.duration <= 0:
            raise ValueError("Duration must be positive")
        if self.amplitude <= 0:
            raise ValueError("Amplitude must be positive")


@dataclass
class MarkerDescription:
    """Description of a digital marker."""
    
    name: str
    channel: int
    start_time: float  # relative to pulse start
    duration: float
    state: bool = True  # True for ON, False for OFF


@dataclass
class LoopDescription:
    """Description of a loop block in a sequence."""
    
    name: str
    iterations: int
    start_time: float
    end_time: float
    pulses: List[PulseDescription] = field(default_factory=list)
    nested_loops: List[LoopDescription] = field(default_factory=list)
    conditionals: List[ConditionalDescription] = field(default_factory=list)


@dataclass
class ConditionalDescription:
    """Description of a conditional block in a sequence."""
    
    name: str
    condition: str  # e.g., "if marker_1", "if variable > 0"
    true_pulses: List[PulseDescription] = field(default_factory=list)
    false_pulses: List[PulseDescription] = field(default_factory=list)
    start_time: float = 0.0
    end_time: float = 0.0


@dataclass
class VariableDescription:
    """Description of a variable parameter."""
    
    name: str
    values: List[Any]
    current_index: int = 0
    
    def next_value(self) -> Any:
        """Get next value and advance index."""
        if self.current_index >= len(self.values):
            raise IndexError("No more values available")
        value = self.values[self.current_index]
        self.current_index += 1
        return value
    
    def reset(self):
        """Reset index to beginning."""
        self.current_index = 0


@dataclass
class SequenceDescription:
    """Complete description of a sequence experiment."""
    
    name: str
    experiment_type: str
    total_duration: float  # in seconds
    sample_rate: float     # in Hz
    pulses: List[PulseDescription] = field(default_factory=list)
    loops: List[LoopDescription] = field(default_factory=list)
    conditionals: List[ConditionalDescription] = field(default_factory=list)
    variables: Dict[str, VariableDescription] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate sequence description after initialization."""
        if self.total_duration <= 0:
            raise ValueError("Total duration must be positive")
        if self.sample_rate <= 0:
            raise ValueError("Sample rate must be positive")
    
    def add_pulse(self, pulse: PulseDescription):
        """Add a pulse to the sequence."""
        self.pulses.append(pulse)
    
    def add_loop(self, loop: LoopDescription):
        """Add a loop to the sequence."""
        self.loops.append(loop)
    
    def add_conditional(self, conditional: ConditionalDescription):
        """Add a conditional to the sequence."""
        self.conditionals.append(conditional)
    
    def add_variable(self, name: str, values: List[Any]):
        """Add a variable to the sequence."""
        self.variables[name] = VariableDescription(name=name, values=values)
    
    def get_total_pulses(self) -> int:
        """Get total number of pulses including loops and conditionals."""
        total = len(self.pulses)
        
        for loop in self.loops:
            total += len(loop.pulses) * loop.iterations
        
        for conditional in self.conditionals:
            total += len(conditional.true_pulses) + len(conditional.false_pulses)
        
        return total
    
    def validate(self) -> bool:
        """Validate the sequence description for consistency."""
        # Check that all pulses fit within total duration
        for pulse in self.pulses:
            if pulse.timing + pulse.duration > self.total_duration:
                return False
        
        # Check that loops and conditionals are valid
        for loop in self.loops:
            if loop.start_time < 0 or loop.end_time > self.total_duration:
                return False
            if loop.start_time >= loop.end_time:
                return False
        
        for conditional in self.conditionals:
            if conditional.start_time < 0 or conditional.end_time > self.total_duration:
                return False
            if conditional.start_time >= conditional.end_time:
                return False
        
        return True
