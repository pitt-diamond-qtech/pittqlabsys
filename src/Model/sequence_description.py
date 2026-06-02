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
    DATA = "data"


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
    duration: float | str  # in seconds
    amplitude: float | str = 1.0
    timing: float | str  = 0.0  # absolute time in seconds
    timing_type: TimingType = TimingType.ABSOLUTE
    parameters: Dict[str, Any] = field(default_factory=dict)  # amplitude, phase, frequency, etc.
    markers: List[MarkerDescription] = field(default_factory=list)
    fixed_timing: bool = False  # [fixed] marker to prevent timing adjustment
    
    def __post_init__(self):
        """Validate pulse description after initialization."""
        if not isinstance(self.channel, int) or self.channel < 1:
            raise ValueError("Channel must be a positive integer")
        # allowing string: only raise for float
        if isinstance(self.duration, float) and self.duration <= 0:
            raise ValueError("Duration must be positive")
        if isinstance(self.amplitude, float) and self.amplitude < 0:
            raise ValueError("Amplitude must be non-negative")
        if isinstance(self.timing, float) and self.timing < 0:
            raise ValueError("Timing must be non-negative")
    
    def get_parameter(self, key: str, default: Any = None) -> Any:
        """Get a parameter value with default."""
        return self.parameters.get(key, default)
    
    def set_parameter(self, key: str, value: Any):
        """Set a parameter value."""
        self.parameters[key] = value
    
    def is_fixed_timing(self) -> bool:
        """Check if this pulse should not have its timing adjusted during scans."""
        return self.fixed_timing


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
    """Description of a variable parameter for scanning."""
    
    name: str
    start_value: float
    stop_value: float
    steps: int
    current_index: int = 0
    unit: str = ""
    
    def __post_init__(self):
        """Validate variable description after initialization."""
        if self.steps <= 0:
            raise ValueError("Steps must be positive")
        if self.start_value == self.stop_value and self.steps > 1:
            raise ValueError("Start and stop values are identical but steps > 1")
    
    @property
    def values(self) -> List[float]:
        """Generate the list of values for the scan."""
        if self.steps == 1:
            return [self.start_value]
        
        # Generate evenly spaced values
        step_size = (self.stop_value - self.start_value) / (self.steps - 1)
        return [self.start_value + i * step_size for i in range(self.steps)]
    
    def next_value(self) -> float:
        """Get next value and advance index."""
        if self.current_index >= len(self.values):
            raise IndexError("No more values available")
        value = self.values[self.current_index]
        self.current_index += 1
        return value
    
    def reset(self):
        """Reset index to beginning."""
        self.current_index = 0
    
    def get_current_value(self) -> float:
        """Get current value without advancing index."""
        if self.current_index >= len(self.values):
            raise IndexError("Index out of range")
        return self.values[self.current_index]
    
    def get_formatted_value(self, value: float) -> str:
        """Format value with unit for display."""
        if self.unit:
            return f"{value}{self.unit}"
        return str(value)


@dataclass
class SequenceDescription:
    """Complete description of a sequence experiment."""
    
    name: str
    experiment_type: str
    total_duration: float  # in seconds
    sample_rate: float     # in Hz
    pulses: List[PulseDescription] = field(default_factory=list)
    markers: List[MarkerDescription] = field(default_factory=list)
    loops: List[LoopDescription] = field(default_factory=list)
    conditionals: List[ConditionalDescription] = field(default_factory=list)
    variables: Dict[str, VariableDescription] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    repeat_count: int = 1
    
    def __post_init__(self):
        """Validate sequence description after initialization."""
        if self.total_duration < 0:
            raise ValueError("Total duration must be non-negative")
        # Allow zero duration for empty sequences
        if self.sample_rate <= 0:
            raise ValueError("Sample rate must be positive")
        if self.repeat_count <= 0:
            raise ValueError("Repeat count must be positive")
    
    def add_pulse(self, pulse: PulseDescription):
        """Add a pulse to the sequence."""
        self.pulses.append(pulse)

    def add_marker(self, marker: MarkerDescription):
        """Add a pulse to the sequence."""
        self.markers.append(marker)
    
    def add_loop(self, loop: LoopDescription):
        """Add a loop to the sequence."""
        print("inside add_loop")
        self.loops.append(loop)
        print(f"self.loops{self.loops}")
    
    def add_conditional(self, conditional: ConditionalDescription):
        """Add a conditional to the sequence."""
        self.conditionals.append(conditional)
    
    def add_variable(self, name: str, start_value: float, stop_value: float, steps: int, unit: str = ""):
        """Add a variable to the sequence."""
        self.variables[name] = VariableDescription(
            name=name, 
            start_value=start_value, 
            stop_value=stop_value, 
            steps=steps, 
            unit=unit
        )
    
    def get_total_pulses(self) -> int:
        """Get total number of pulses including loops and conditionals."""
        total = len(self.pulses)
        
        for loop in self.loops:
            total += len(loop.pulses) * loop.iterations
        
        for conditional in self.conditionals:
            total += len(conditional.true_pulses) + len(conditional.false_pulses)
        
        return total
    
    def get_total_scan_points(self) -> int:
        """Get total number of scan points across all variables."""
        if not self.variables:
            return 1
        
        total_points = 1
        for var in self.variables.values():
            total_points *= var.steps
        
        return total_points
    
    def validate(self) -> bool:
        """Validate the sequence description for consistency."""
        # For sequences with variables, timing validation is more flexible
        # since timing will be adjusted during scanning
        if self.variables:
            # Only check basic constraints for variable sequences
            for pulse in self.pulses:
                if pulse.timing < 0:
                    print("1")
                    return False
                if pulse.duration <= 0:
                    print("2")
                    return False
        else:
            # For fixed sequences, check that all pulses fit within total duration
            for pulse in self.pulses:
                if pulse.timing + pulse.duration > self.total_duration:
                    print(f"sequence: {self.name} pulse{pulse.name}")
                    print(f"pulse timing{pulse.timing}, pulse duration{pulse.duration}, total duration{self.total_duration}")
                    print("3")
                    return False
        
        # Check that loops and conditionals are valid
        for loop in self.loops:
            if loop.start_time < 0:
                print("4")
                return False
            if not self.variables and loop.end_time > self.total_duration:
                print("5")
                return False
            if loop.start_time >= loop.end_time:
                print("6")
                return False
        
        for conditional in self.conditionals:
            if conditional.start_time < 0:
                print("7")
                return False
            if not self.variables and conditional.end_time > self.total_duration:
                print("8")
                return False
            if conditional.start_time >= conditional.end_time:
                print("9")
                return False
        
        return True
