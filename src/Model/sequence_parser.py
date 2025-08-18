"""
Sequence Parser Module

This module handles parsing human-readable text sequences and preset experiments
into structured data that can be processed by the sequence builder.
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import re
from dataclasses import dataclass

from .sequence_description import (
    SequenceDescription, PulseDescription, LoopDescription, ConditionalDescription,
    PulseShape, TimingType, MarkerDescription
)
from .preset_qubit_experiments import PresetQubitExperiments, PresetExperiment


class SequenceTextParser:
    """
    Parses human-readable text sequences into structured data.
    
    Supports:
    - Simple pulse sequences
    - Preset experiments with customization
    - Loops and conditional logic
    - Variable parameters
    """
    
    def __init__(self):
        """Initialize the parser with default settings."""
        # Lazy-load presets to avoid raising during initialization in tests
        self.preset_qubit_experiments: Dict[str, Dict[str, Any]] = {}
        self._preset_loader = None  # Will be initialized when needed
    
    def parse_file(self, filename: Union[str, Path]) -> SequenceDescription:
        """
        Parse a text file into a sequence description.
        
        Args:
            filename: Path to the text file containing sequence description
            
        Returns:
            SequenceDescription object with parsed sequence data
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            ParseError: If the file contains invalid syntax
        """
        file_path = Path(filename)
        if not file_path.exists():
            raise FileNotFoundError(f"Sequence file not found: {filename}")
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            return self.parse_text(content)
        except Exception as e:
            raise ParseError(f"Failed to parse file {filename}: {e}")
    
    def parse_preset(self, preset_name: str, **parameters) -> SequenceDescription:
        """
        Load and customize a preset experiment.
        
        Args:
            preset_name: Name of the preset experiment
            **parameters: Custom parameters to override defaults
            
        Returns:
            SequenceDescription object for the preset experiment
            
        Raises:
            ValueError: If preset_name is not found
            ParameterError: If invalid parameters are provided
        """
        # Load presets if not already loaded
        if not self.preset_qubit_experiments:
            self._load_preset_qubit_experiments()
        
        if preset_name not in self.preset_qubit_experiments:
            raise ValueError(f"Preset experiment '{preset_name}' not found")
        
        preset_dict = self.preset_qubit_experiments[preset_name]
        
        # Customize parameters if provided
        if parameters:
            # Validate parameters
            for param_name, param_value in parameters.items():
                if param_name not in preset_dict["parameters"]:
                    raise ParameterError(f"Unknown parameter '{param_name}' for preset '{preset_name}'")
            
            # Create customized preset
            custom_params = {**preset_dict["parameters"], **parameters}
            preset = PresetExperiment(
                name=f"{preset_name}_custom",
                description=preset_dict["description"],
                parameters=custom_params,
                sequence_template=preset_dict["sequence_template"],
                metadata=preset_dict["metadata"]
            )
        else:
            # Use original preset
            preset = PresetExperiment(
                name=preset_dict["name"],
                description=preset_dict["description"],
                parameters=preset_dict["parameters"],
                sequence_template=preset_dict["sequence_template"],
                metadata=preset_dict["metadata"]
            )
        
        # Parse the sequence template
        return self.parse_text(preset.sequence_template)
    
    def parse_text(self, text: str) -> SequenceDescription:
        """
        Parse a text string directly into a sequence description.
        
        Args:
            text: Text string containing sequence description
            
        Returns:
            SequenceDescription object with parsed sequence data
            
        Raises:
            ParseError: If the text contains invalid syntax
        """
        try:
            lines = [line.strip() for line in text.split('\n') if line.strip() and not line.startswith('#')]
            
            # Parse sequence header
            sequence_name = "parsed_sequence"
            experiment_type = "custom"
            total_duration = 0.0
            sample_rate = 1e9  # Default 1 GHz
            repeat_count = 1

            pulses = []
            loops = []
            conditionals = []
            variables = {}

            # Parse the text line by line
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                
                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    i += 1
                    continue
                
                # Parse different types of lines
                if line.startswith("sequence:"):
                    header_info = self._parse_sequence_header(line)
                    sequence_name = header_info.get("name", sequence_name)
                    experiment_type = header_info.get("type", experiment_type)
                    total_duration = header_info.get("duration", total_duration)
                    sample_rate = header_info.get("sample_rate", sample_rate)
                    repeat_count = header_info.get("repeat_count", repeat_count)
                    i += 1
                elif line.startswith("loop:"):
                    loop_desc, skip_lines = self._parse_loop_block(lines[i:])
                    loops.append(loop_desc)
                    i += skip_lines
                elif line.startswith("if ") or line.startswith("else:"):
                    cond_desc, skip_lines = self._parse_conditional_block(lines[i:])
                    conditionals.append(cond_desc)
                    i += skip_lines
                elif line.startswith("variable "):
                    try:
                        var_name, start_val, stop_val, steps, unit = self._parse_variable_line(line)
                        # Store variable info to add later
                        variables[var_name] = (start_val, stop_val, steps, unit)
                    except ParseError as e:
                        print(f"Warning: Skipping invalid variable line: {line} - {e}")
                    except ValueError as e:
                        print(f"Warning: Skipping invalid variable line: {line} - {e}")
                    i += 1
                else:
                    # Parse as pulse line
                    try:
                        pulse_desc = self._parse_pulse_line(line)
                        pulses.append(pulse_desc)
                        # Update total duration if this pulse extends beyond current duration
                        pulse_end = pulse_desc.timing + pulse_desc.duration
                        total_duration = max(total_duration, pulse_end)
                    except ParseError as e:
                        # Skip invalid lines but log warning
                        print(f"Warning: Skipping invalid line '{line}': {e}")
                    except ValueError as e:
                        # Skip lines that fail validation (e.g., template variables)
                        print(f"Warning: Skipping invalid line '{line}' due to validation: {e}")
                    i += 1
            
            # Create sequence description
            sequence_desc = SequenceDescription(
                name=sequence_name,
                experiment_type=experiment_type,
                total_duration=total_duration,
                sample_rate=sample_rate,
                pulses=pulses,
                loops=loops,
                conditionals=conditionals,
                repeat_count=repeat_count
            )
            
            # Add variables to the description
            for var_name, (start_val, stop_val, steps, unit) in variables.items():
                sequence_desc.add_variable(var_name, start_val, stop_val, steps, unit)
            
            # Validate the sequence
            if not self.validate_sequence(sequence_desc):
                raise ValidationError("Generated sequence description is invalid")
            
            return sequence_desc
            
        except Exception as e:
            if isinstance(e, (ParseError, ValidationError)):
                raise
            raise ParseError(f"Failed to parse sequence text: {e}")
    
    def _load_preset_qubit_experiments(self) -> Dict[str, Dict[str, Any]]:
        """
        Load preset qubit experiment definitions.
        
        Returns:
            Dictionary mapping preset names to their definitions
        """
        if self._preset_loader is None:
            self._preset_loader = PresetQubitExperiments()
        
        # Convert to the expected format
        presets = {}
        for name, experiment in self._preset_loader.experiments.items():
            presets[name] = {
                "name": experiment.name,
                "description": experiment.description,
                "parameters": experiment.parameters,
                "sequence_template": experiment.sequence_template,
                "metadata": experiment.metadata
            }
        
        self.preset_qubit_experiments = presets
        return presets
    
    def _parse_pulse_line(self, line: str) -> PulseDescription:
        """
        Parse a single pulse line from the text.
        
        Expected format: "pulse_type on channel N at time, shape, duration, amplitude"
        Examples:
        - "pi/2 on channel 1 at 0ms, gaussian, 100ns, 1.0"
        - "pi pulse on channel 2 at 1ms, square, 200ns"
        - "wait 2ms"
        
        Args:
            line: Text line describing a pulse
            
        Returns:
            PulseDescription object
            
        Raises:
            ParseError: If the line contains invalid syntax
        """
        line = line.strip()
        
        # Handle wait/empty lines
        if line.startswith("wait") or line == "":
            # Parse wait time
            wait_match = re.match(r"wait\s+([\d.]+[mun]?s)", line)
            if wait_match:
                wait_time = self._parse_timing_expression(wait_match.group(1))
                return PulseDescription(
                    name="wait",
                    pulse_type="wait",
                    channel=1,  # Default channel for wait
                    shape=PulseShape.SQUARE,
                    duration=wait_time,
                    amplitude=0.0,  # No output during wait
                    timing=0.0,
                    timing_type=TimingType.RELATIVE
                )
            else:
                return PulseDescription(
                    name="empty",
                    pulse_type="empty",
                    channel=1,
                    shape=PulseShape.SQUARE,
                    duration=0.0,
                    amplitude=0.0,
                    timing=0.0
                )
        
        # Parse pulse line
        # Pattern: "pulse_type on channel N at time, shape, duration, amplitude"
        # Also handle: "pulse_type pulse on channel N at time"
        pulse_pattern = r"(\w+(?:/\d+)?)\s+(?:pulse\s+)?on\s+channel\s+(\d+)\s+at\s+([\d.]+[mun]?s)(?:,\s*(\w+)(?:,\s*([\d.]+[mun]?s))?(?:,\s*([\d.]+))?)?"
        
        match = re.match(pulse_pattern, line)
        if not match:
            raise ParseError(f"Invalid pulse line format: {line}")
        
        pulse_type = match.group(1)
        channel = int(match.group(2))
        timing_str = match.group(3)
        shape_str = match.group(4) or "gaussian"  # Default to gaussian
        duration_str = match.group(5) or "100ns"  # Default to 100ns
        amplitude_str = match.group(6) or "1.0"   # Default to 1.0
        
        # Parse timing
        timing = self._parse_timing_expression(timing_str)
        
        # Parse duration
        duration = self._parse_timing_expression(duration_str)
        
        # Parse amplitude
        try:
            amplitude = float(amplitude_str)
        except ValueError:
            raise ParseError(f"Invalid amplitude: {amplitude_str}")
        
        # Parse shape
        try:
            shape = PulseShape(shape_str.lower())
        except ValueError:
            raise ParseError(f"Unsupported pulse shape: {shape_str}")
        
        # Validate channel
        if channel not in [1, 2]:
            raise ParseError(f"Invalid channel: {channel}. Must be 1 or 2.")
        
        return PulseDescription(
            name=f"{pulse_type.replace('/', '_')}_{channel}",
            pulse_type=pulse_type,
            channel=channel,
            shape=shape,
            duration=duration,
            amplitude=amplitude,
            timing=timing,
            timing_type=TimingType.ABSOLUTE
        )
    
    def _parse_timing_expression(self, timing: str) -> float:
        """
        Parse timing expressions (e.g., "1ms", "100ns", "0.5s").
        
        Args:
            timing: String timing expression
            
        Returns:
            Time in seconds
            
        Raises:
            ParseError: If timing expression is invalid
        """
        timing = timing.strip().lower()
        
        # Pattern: number + unit (ns, μs, us, ms, s)
        timing_pattern = r"([\d.]+)\s*(ns|μs|us|ms|s)"
        match = re.match(timing_pattern, timing)
        
        if not match:
            raise ParseError(f"Invalid timing expression: {timing}")
        
        value = float(match.group(1))
        unit = match.group(2)
        
        # Convert to seconds
        unit_multipliers = {
            "ns": 1e-9,
            "μs": 1e-6,
            "us": 1e-6,
            "ms": 1e-3,
            "s": 1.0
        }
        
        if unit not in unit_multipliers:
            raise ParseError(f"Unknown time unit: {unit}")
        
        return value * unit_multipliers[unit]
    
    def _parse_loop_block(self, lines: List[str]) -> tuple[LoopDescription, int]:
        """
        Parse a loop block from the text.
        
        Expected format:
        loop: iterations
          pulse1
          pulse2
        end
        
        Args:
            lines: List of text lines in the loop block
            
        Returns:
            Tuple of (LoopDescription object, number of lines to skip)
            
        Raises:
            ParseError: If the loop block contains invalid syntax
        """
        if not lines or not lines[0].startswith("loop:"):
            raise ParseError("Invalid loop block start")
        
        # Parse loop header
        header = lines[0]
        loop_match = re.match(r"loop:\s*(\d+)", header)
        if not loop_match:
            raise ParseError(f"Invalid loop header: {header}")
        
        iterations = int(loop_match.group(1))
        
        # Find end of loop block
        end_index = -1
        for i, line in enumerate(lines[1:], 1):
            if line.strip() == "end":
                end_index = i
                break
        
        if end_index == -1:
            raise ParseError("Loop block not properly closed with 'end'")
        
        # Parse pulses within the loop
        loop_pulses = []
        for line in lines[1:end_index]:
            if line.strip() and not line.startswith("#"):
                try:
                    pulse = self._parse_pulse_line(line)
                    loop_pulses.append(pulse)
                except ParseError as e:
                    print(f"Warning: Skipping invalid pulse in loop: {line} - {e}")
        
        # Calculate timing for the loop
        start_time = 0.0
        end_time = sum(pulse.duration for pulse in loop_pulses) if loop_pulses else 0.0
        
        return LoopDescription(
            name=f"loop_{iterations}",
            iterations=iterations,
            start_time=start_time,
            end_time=end_time,
            pulses=loop_pulses
        ), end_index + 1  # Return the description and number of lines to skip
    
    def _parse_conditional_block(self, lines: List[str]) -> tuple[ConditionalDescription, int]:
        """
        Parse a conditional block from the text.
        
        Expected format:
        if condition
          pulse1
          pulse2
        else
          pulse3
        end
        
        Args:
            lines: List of text lines in the conditional block
            
        Returns:
            Tuple of (ConditionalDescription object, number of lines to skip)
            
        Raises:
            ParseError: If the conditional block contains invalid syntax
        """
        if not lines or not lines[0].startswith("if "):
            raise ParseError("Invalid conditional block start")
        
        # Parse condition
        condition = lines[0][3:].strip()  # Remove "if "
        
        # Find else and end
        else_index = -1
        end_index = -1
        
        for i, line in enumerate(lines[1:], 1):
            if line.strip() == "else":
                else_index = i
            elif line.strip() == "end":
                end_index = i
                break
        
        if end_index == -1:
            raise ParseError("Conditional block not properly closed with 'end'")
        
        # Parse true pulses (before else)
        true_end = else_index if else_index != -1 else end_index
        true_pulses = []
        for line in lines[1:true_end]:
            if line.strip() and not line.startswith("#"):
                try:
                    pulse = self._parse_pulse_line(line)
                    true_pulses.append(pulse)
                except ParseError as e:
                    print(f"Warning: Skipping invalid pulse in conditional true block: {line} - {e}")
        
        # Parse false pulses (after else)
        false_pulses = []
        if else_index != -1:
            for line in lines[else_index + 1:end_index]:
                if line.strip() and not line.startswith("#"):
                    try:
                        pulse = self._parse_pulse_line(line)
                        false_pulses.append(pulse)
                    except ParseError as e:
                        print(f"Warning: Skipping invalid pulse in conditional false block: {line} - {e}")
        
        # Calculate timing
        start_time = 0.0
        end_time = max(
            sum(pulse.duration for pulse in true_pulses) if true_pulses else 0.0,
            sum(pulse.duration for pulse in false_pulses) if false_pulses else 0.0
        )
        
        return ConditionalDescription(
            name=f"conditional_{condition}",
            condition=condition,
            true_pulses=true_pulses,
            false_pulses=false_pulses,
            start_time=start_time,
            end_time=end_time
        ), end_index + 1  # Return the description and number of lines to skip
    
    def _parse_sequence_header(self, line: str) -> Dict[str, Any]:
        """
        Parse sequence header information.
        
        Expected format: "sequence: name=value, name=value"
        
        Args:
            line: Header line to parse
            
        Returns:
            Dictionary of header parameters
        """
        header_info = {}
        
        # Remove "sequence:" prefix
        if line.startswith("sequence:"):
            line = line[9:].strip()
        
        # Parse key=value pairs
        pairs = line.split(",")
        for pair in pairs:
            pair = pair.strip()
            if "=" in pair:
                key, value = pair.split("=", 1)
                key = key.strip()
                value = value.strip()
                
                # Convert value to appropriate type
                if key == "duration":
                    header_info[key] = self._parse_timing_expression(value)
                elif key == "sample_rate":
                    # Parse sample rate with units (e.g., "1GHz", "100MHz")
                    numeric_value, unit = self._parse_value_with_unit(value)
                    header_info[key] = numeric_value
                elif key in ("repeat", "repeat_count"):
                    try:
                        header_info["repeat_count"] = int(value)
                    except ValueError:
                        raise ParseError(f"Invalid repeat count: {value}")
                else:
                    header_info[key] = value
        
        return header_info
    
    def _parse_variable_line(self, line: str) -> tuple[str, float, float, int, str]:
        """
        Parse a variable definition line.
        
        Expected format: "variable name, start=value, stop=value, steps=number"
        Examples:
        - "variable pulse_duration, start=100ns, stop=1000ns, steps=50"
        - "variable laser_power, start=0.5, stop=2.0, steps=10"
        
        Args:
            line: Variable definition line
            
        Returns:
            Tuple of (variable_name, start_value, stop_value, steps, unit)
        """
        # Remove "variable " prefix
        if line.startswith("variable "):
            line = line[9:].strip()
        
        # Parse name and parameters
        if "," not in line:
            raise ParseError(f"Invalid variable definition: {line}")
        
        parts = [part.strip() for part in line.split(",")]
        if len(parts) != 4:
            raise ParseError(f"Variable definition must have 4 parts: {line}")
        
        # Parse variable name
        name = parts[0]
        
        # Parse start parameter
        if not parts[1].startswith("start="):
            raise ParseError(f"Second parameter must start with 'start=': {parts[1]}")
        start_str = parts[1][6:].strip()
        
        # Parse stop parameter
        if not parts[2].startswith("stop="):
            raise ParseError(f"Third parameter must start with 'stop=': {parts[2]}")
        stop_str = parts[2][5:].strip()
        
        # Parse steps parameter
        if not parts[3].startswith("steps="):
            raise ParseError(f"Fourth parameter must start with 'steps=': {parts[3]}")
        steps_str = parts[3][6:].strip()
        
        # Parse values, handling units
        start_value, start_unit = self._parse_value_with_unit(start_str)
        stop_value, stop_unit = self._parse_value_with_unit(stop_str)
        
        # Ensure units are consistent
        if start_unit != stop_unit:
            raise ParseError(f"Inconsistent units: {start_unit} vs {stop_unit}")
        
        try:
            steps = int(steps_str)
        except ValueError:
            raise ParseError(f"Invalid steps value: {steps_str}")
        
        return name, start_value, stop_value, steps, start_unit
    
    def _parse_value_with_unit(self, value_str: str) -> tuple[float, str]:
        """
        Parse a value that may have a unit.
        
        Args:
            value_str: String like "100ns", "0.5V", "1.0"
            
        Returns:
            Tuple of (numeric_value, unit_string)
        """
        # Check for timing units first
        timing_pattern = r"([\d.]+)\s*(ns|μs|us|ms|s)"
        match = re.match(timing_pattern, value_str.lower())
        if match:
            value = float(match.group(1))
            unit = match.group(2)
            # Convert timing to seconds
            unit_multipliers = {
                "ns": 1e-9, "μs": 1e-6, "us": 1e-6, "ms": 1e-3, "s": 1.0
            }
            return value * unit_multipliers[unit], unit
        
        # Check for voltage units
        voltage_pattern = r"([\d.]+)\s*V"
        match = re.match(voltage_pattern, value_str)
        if match:
            value = float(match.group(1))
            return value, "V"
        
        # Check for frequency units
        freq_pattern = r"([\d.]+)\s*(Hz|kHz|MHz|GHz|hz|khz|mhz|ghz)"
        match = re.match(freq_pattern, value_str)
        if match:
            value = float(match.group(1))
            unit = match.group(2).lower()
            # Convert frequency to Hz
            unit_multipliers = {
                "hz": 1, "khz": 1e3, "mhz": 1e6, "ghz": 1e9
            }
            return value * unit_multipliers[unit], unit
        
        # No unit, just a number
        try:
            value = float(value_str)
            return value, ""
        except ValueError:
            raise ParseError(f"Invalid value: {value_str}")
    
    def validate_sequence(self, description: SequenceDescription) -> bool:
        """
        Validate a sequence description for consistency.
        
        Args:
            description: SequenceDescription to validate
            
        Returns:
            True if valid, False otherwise
            
        Raises:
            ValidationError: If validation fails with details
        """
        try:
            # Basic validation
            if not description.name:
                raise ValidationError("Sequence must have a name")
            
            if description.total_duration < 0:
                raise ValidationError("Total duration must be non-negative")
            # Allow zero duration for empty sequences
            
            if description.sample_rate <= 0:
                raise ValidationError("Sample rate must be positive")
            
            # Validate pulses
            for pulse in description.pulses:
                if pulse.timing < 0:
                    raise ValidationError(f"Pulse '{pulse.name}' has negative timing")
                
                if pulse.timing + pulse.duration > description.total_duration:
                    raise ValidationError(f"Pulse '{pulse.name}' extends beyond total duration")
                
                if pulse.channel not in [1, 2]:
                    raise ValidationError(f"Pulse '{pulse.name}' has invalid channel: {pulse.channel}")
            
            # Validate loops
            for loop in description.loops:
                if loop.iterations <= 0:
                    raise ValidationError(f"Loop '{loop.name}' must have positive iterations")
                
                if loop.start_time < 0 or loop.end_time < loop.start_time:
                    raise ValidationError(f"Loop '{loop.name}' has invalid timing")
            
            # Validate conditionals
            for conditional in description.conditionals:
                if conditional.start_time < 0 or conditional.end_time < conditional.start_time:
                    raise ValidationError(f"Conditional '{conditional.name}' has invalid timing")
            
            return True
            
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"Validation failed with unexpected error: {e}")


class ParseError(Exception):
    """Raised when sequence parsing fails."""
    pass


class ParameterError(Exception):
    """Raised when invalid parameters are provided."""
    pass


class ValidationError(Exception):
    """Raised when sequence validation fails."""
    pass
