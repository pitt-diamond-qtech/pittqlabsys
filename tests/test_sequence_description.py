"""
Tests for the sequence description module.

This module tests the intermediate data structures used to represent
sequence descriptions between text parsing and sequence building.
"""

import pytest
import numpy as np
from src.Model.sequence_description import (
    PulseShape, TimingType, PulseDescription, MarkerDescription,
    LoopDescription, ConditionalDescription, VariableDescription,
    SequenceDescription
)


class TestPulseShape:
    """Test the PulseShape enum."""
    
    def test_pulse_shape_values(self):
        """Test that all expected pulse shapes are defined."""
        expected_shapes = ["gaussian", "sech", "lorentzian", "square", "sine", "loadfile"]
        for shape in expected_shapes:
            assert hasattr(PulseShape, shape.upper())
            assert getattr(PulseShape, shape.upper()).value == shape
    
    def test_pulse_shape_enumeration(self):
        """Test that we can iterate over pulse shapes."""
        shapes = list(PulseShape)
        assert len(shapes) == 6
        assert all(isinstance(shape, PulseShape) for shape in shapes)


class TestTimingType:
    """Test the TimingType enum."""
    
    def test_timing_type_values(self):
        """Test that all expected timing types are defined."""
        expected_types = ["absolute", "relative", "variable"]
        for timing_type in expected_types:
            assert hasattr(TimingType, timing_type.upper())
            assert getattr(TimingType, timing_type.upper()).value == timing_type


class TestPulseDescription:
    """Test the PulseDescription dataclass."""
    
    def test_valid_pulse_description(self):
        """Test creating a valid pulse description."""
        pulse = PulseDescription(
            name="test_pulse",
            pulse_type="pi/2",
            channel=1,
            shape=PulseShape.GAUSSIAN,
            duration=100e-9,  # 100ns
            amplitude=1.0,
            timing=0.0
        )
        
        assert pulse.name == "test_pulse"
        assert pulse.pulse_type == "pi/2"
        assert pulse.channel == 1
        assert pulse.shape == PulseShape.GAUSSIAN
        assert pulse.duration == 100e-9
        assert pulse.amplitude == 1.0
        assert pulse.timing == 0.0
        assert pulse.timing_type == TimingType.ABSOLUTE
        assert pulse.parameters == {}
        assert pulse.markers == []
    
    def test_pulse_description_with_markers(self):
        """Test creating a pulse description with markers."""
        marker = MarkerDescription(
            name="marker1",
            channel=1,
            start_time=0.0,
            duration=50e-9
        )
        
        pulse = PulseDescription(
            name="test_pulse",
            pulse_type="pi",
            channel=2,
            shape=PulseShape.SQUARE,
            duration=200e-9,
            amplitude=0.5,
            timing=1e-6,
            markers=[marker]
        )
        
        assert len(pulse.markers) == 1
        assert pulse.markers[0].name == "marker1"
        assert pulse.channel == 2
    
    def test_invalid_channel(self):
        """Test that invalid channel raises ValueError."""
        with pytest.raises(ValueError, match="Channel must be 1 or 2"):
            PulseDescription(
                name="test_pulse",
                pulse_type="pi/2",
                channel=3,  # Invalid channel
                shape=PulseShape.GAUSSIAN,
                duration=100e-9,
                amplitude=1.0
            )
    
    def test_invalid_duration(self):
        """Test that negative duration raises ValueError."""
        with pytest.raises(ValueError, match="Duration must be positive"):
            PulseDescription(
                name="test_pulse",
                pulse_type="pi/2",
                channel=1,
                shape=PulseShape.GAUSSIAN,
                duration=-100e-9,  # Negative duration
                amplitude=1.0
            )
    
    def test_invalid_amplitude(self):
        """Test that negative amplitude raises ValueError."""
        with pytest.raises(ValueError, match="Amplitude must be positive"):
            PulseDescription(
                name="test_pulse",
                pulse_type="pi/2",
                channel=1,
                shape=PulseShape.GAUSSIAN,
                duration=100e-9,
                amplitude=-1.0  # Negative amplitude
            )
    
    def test_zero_duration(self):
        """Test that zero duration raises ValueError."""
        with pytest.raises(ValueError, match="Duration must be positive"):
            PulseDescription(
                name="test_pulse",
                pulse_type="pi/2",
                channel=1,
                shape=PulseShape.GAUSSIAN,
                duration=0.0,  # Zero duration
                amplitude=1.0
            )


class TestMarkerDescription:
    """Test the MarkerDescription dataclass."""
    
    def test_valid_marker_description(self):
        """Test creating a valid marker description."""
        marker = MarkerDescription(
            name="test_marker",
            channel=1,
            start_time=0.0,
            duration=100e-9
        )
        
        assert marker.name == "test_marker"
        assert marker.channel == 1
        assert marker.start_time == 0.0
        assert marker.duration == 100e-9
        assert marker.state is True  # Default value
    
    def test_marker_with_custom_state(self):
        """Test creating a marker with custom state."""
        marker = MarkerDescription(
            name="test_marker",
            channel=2,
            start_time=50e-9,
            duration=50e-9,
            state=False
        )
        
        assert marker.state is False
        assert marker.channel == 2


class TestLoopDescription:
    """Test the LoopDescription dataclass."""
    
    def test_valid_loop_description(self):
        """Test creating a valid loop description."""
        loop = LoopDescription(
            name="test_loop",
            iterations=10,
            start_time=0.0,
            end_time=1e-3
        )
        
        assert loop.name == "test_loop"
        assert loop.iterations == 10
        assert loop.start_time == 0.0
        assert loop.end_time == 1e-3
        assert loop.pulses == []
        assert loop.nested_loops == []
        assert loop.conditionals == []
    
    def test_loop_with_pulses(self):
        """Test creating a loop with pulses."""
        pulse = PulseDescription(
            name="loop_pulse",
            pulse_type="pi",
            channel=1,
            shape=PulseShape.GAUSSIAN,
            duration=100e-9,
            amplitude=1.0
        )
        
        loop = LoopDescription(
            name="test_loop",
            iterations=5,
            start_time=0.0,
            end_time=1e-3,
            pulses=[pulse]
        )
        
        assert len(loop.pulses) == 1
        assert loop.pulses[0].name == "loop_pulse"


class TestConditionalDescription:
    """Test the ConditionalDescription dataclass."""
    
    def test_valid_conditional_description(self):
        """Test creating a valid conditional description."""
        conditional = ConditionalDescription(
            name="test_conditional",
            condition="if marker_1",
            start_time=0.0,
            end_time=1e-3
        )
        
        assert conditional.name == "test_conditional"
        assert conditional.condition == "if marker_1"
        assert conditional.start_time == 0.0
        assert conditional.end_time == 1e-3
        assert conditional.true_pulses == []
        assert conditional.false_pulses == []


class TestVariableDescription:
    """Test the VariableDescription dataclass."""
    
    def test_valid_variable_description(self):
        """Test creating a valid variable description."""
        variable = VariableDescription(
            name="tau",
            values=[1e-6, 2e-6, 5e-6, 10e-6]
        )
        
        assert variable.name == "tau"
        assert variable.values == [1e-6, 2e-6, 5e-6, 10e-6]
        assert variable.current_index == 0
    
    def test_next_value(self):
        """Test getting next value from variable."""
        variable = VariableDescription(
            name="tau",
            values=[1e-6, 2e-6, 5e-6]
        )
        
        assert variable.next_value() == 1e-6
        assert variable.current_index == 1
        assert variable.next_value() == 2e-6
        assert variable.current_index == 2
        assert variable.next_value() == 5e-6
        assert variable.current_index == 3
    
    def test_next_value_exhausted(self):
        """Test that next_value raises IndexError when exhausted."""
        variable = VariableDescription(
            name="tau",
            values=[1e-6]
        )
        
        variable.next_value()  # Should work
        
        with pytest.raises(IndexError, match="No more values available"):
            variable.next_value()
    
    def test_reset(self):
        """Test resetting variable index."""
        variable = VariableDescription(
            name="tau",
            values=[1e-6, 2e-6, 5e-6]
        )
        
        variable.next_value()
        variable.next_value()
        assert variable.current_index == 2
        
        variable.reset()
        assert variable.current_index == 0
        assert variable.next_value() == 1e-6


class TestSequenceDescription:
    """Test the SequenceDescription dataclass."""
    
    def test_valid_sequence_description(self):
        """Test creating a valid sequence description."""
        sequence = SequenceDescription(
            name="test_sequence",
            experiment_type="test",
            total_duration=1e-3,  # 1ms
            sample_rate=1e9  # 1GHz
        )
        
        assert sequence.name == "test_sequence"
        assert sequence.experiment_type == "test"
        assert sequence.total_duration == 1e-3
        assert sequence.sample_rate == 1e9
        assert sequence.pulses == []
        assert sequence.loops == []
        assert sequence.conditionals == []
        assert sequence.variables == {}
        assert sequence.metadata == {}
    
    def test_invalid_total_duration(self):
        """Test that negative total duration raises ValueError."""
        with pytest.raises(ValueError, match="Total duration must be positive"):
            SequenceDescription(
                name="test_sequence",
                experiment_type="test",
                total_duration=-1e-3,  # Negative duration
                sample_rate=1e9
            )
    
    def test_invalid_sample_rate(self):
        """Test that negative sample rate raises ValueError."""
        with pytest.raises(ValueError, match="Sample rate must be positive"):
            SequenceDescription(
                name="test_sequence",
                experiment_type="test",
                total_duration=1e-3,
                sample_rate=-1e9  # Negative sample rate
            )
    
    def test_add_pulse(self):
        """Test adding a pulse to the sequence."""
        sequence = SequenceDescription(
            name="test_sequence",
            experiment_type="test",
            total_duration=1e-3,
            sample_rate=1e9
        )
        
        pulse = PulseDescription(
            name="test_pulse",
            pulse_type="pi/2",
            channel=1,
            shape=PulseShape.GAUSSIAN,
            duration=100e-9,
            amplitude=1.0
        )
        
        sequence.add_pulse(pulse)
        assert len(sequence.pulses) == 1
        assert sequence.pulses[0].name == "test_pulse"
    
    def test_add_loop(self):
        """Test adding a loop to the sequence."""
        sequence = SequenceDescription(
            name="test_sequence",
            experiment_type="test",
            total_duration=1e-3,
            sample_rate=1e9
        )
        
        loop = LoopDescription(
            name="test_loop",
            iterations=10,
            start_time=0.0,
            end_time=1e-3
        )
        
        sequence.add_loop(loop)
        assert len(sequence.loops) == 1
        assert sequence.loops[0].name == "test_loop"
    
    def test_add_conditional(self):
        """Test adding a conditional to the sequence."""
        sequence = SequenceDescription(
            name="test_sequence",
            experiment_type="test",
            total_duration=1e-3,
            sample_rate=1e9
        )
        
        conditional = ConditionalDescription(
            name="test_conditional",
            condition="if marker_1",
            start_time=0.0,
            end_time=1e-3
        )
        
        sequence.add_conditional(conditional)
        assert len(sequence.conditionals) == 1
        assert sequence.conditionals[0].name == "test_conditional"
    
    def test_add_variable(self):
        """Test adding a variable to the sequence."""
        sequence = SequenceDescription(
            name="test_sequence",
            experiment_type="test",
            total_duration=1e-3,
            sample_rate=1e9
        )
        
        sequence.add_variable("tau", [1e-6, 2e-6, 5e-6])
        assert "tau" in sequence.variables
        assert len(sequence.variables["tau"].values) == 3
    
    def test_get_total_pulses_empty(self):
        """Test getting total pulses for empty sequence."""
        sequence = SequenceDescription(
            name="test_sequence",
            experiment_type="test",
            total_duration=1e-3,
            sample_rate=1e9
        )
        
        assert sequence.get_total_pulses() == 0
    
    def test_get_total_pulses_with_pulses(self):
        """Test getting total pulses with pulses."""
        sequence = SequenceDescription(
            name="test_sequence",
            experiment_type="test",
            total_duration=1e-3,
            sample_rate=1e9
        )
        
        # Add some pulses
        for i in range(3):
            pulse = PulseDescription(
                name=f"pulse_{i}",
                pulse_type="pi/2",
                channel=1,
                shape=PulseShape.GAUSSIAN,
                duration=100e-9,
                amplitude=1.0
            )
            sequence.add_pulse(pulse)
        
        assert sequence.get_total_pulses() == 3
    
    def test_get_total_pulses_with_loops(self):
        """Test getting total pulses with loops."""
        sequence = SequenceDescription(
            name="test_sequence",
            experiment_type="test",
            total_duration=1e-3,
            sample_rate=1e9
        )
        
        # Add a loop with pulses
        loop = LoopDescription(
            name="test_loop",
            iterations=5,
            start_time=0.0,
            end_time=1e-3
        )
        
        for i in range(2):
            pulse = PulseDescription(
                name=f"loop_pulse_{i}",
                pulse_type="pi",
                channel=1,
                shape=PulseShape.GAUSSIAN,
                duration=100e-9,
                amplitude=1.0
            )
            loop.pulses.append(pulse)
        
        sequence.add_loop(loop)
        
        # 2 pulses × 5 iterations = 10 pulses
        assert sequence.get_total_pulses() == 10
    
    def test_validate_empty_sequence(self):
        """Test validation of empty sequence."""
        sequence = SequenceDescription(
            name="test_sequence",
            experiment_type="test",
            total_duration=1e-3,
            sample_rate=1e9
        )
        
        assert sequence.validate() is True
    
    def test_validate_valid_pulses(self):
        """Test validation of sequence with valid pulses."""
        sequence = SequenceDescription(
            name="test_sequence",
            experiment_type="test",
            total_duration=1e-3,
            sample_rate=1e9
        )
        
        # Add pulse that fits within total duration
        pulse = PulseDescription(
            name="test_pulse",
            pulse_type="pi/2",
            channel=1,
            shape=PulseShape.GAUSSIAN,
            duration=500e-9,  # 500ns < 1ms
            amplitude=1.0,
            timing=0.0
        )
        
        sequence.add_pulse(pulse)
        assert sequence.validate() is True
    
    def test_validate_invalid_pulse_timing(self):
        """Test validation of sequence with invalid pulse timing."""
        sequence = SequenceDescription(
            name="test_sequence",
            experiment_type="test",
            total_duration=1e-3,
            sample_rate=1e9
        )
        
        # Add pulse that extends beyond total duration
        pulse = PulseDescription(
            name="test_pulse",
            pulse_type="pi/2",
            channel=1,
            shape=PulseShape.GAUSSIAN,
            duration=500e-9,
            amplitude=1.0,
            timing=600e-9  # 600ns + 500ns = 1.1μs, but we need > 1ms
        )
        
        sequence.add_pulse(pulse)
        # This should actually pass validation since 1.1μs < 1ms
        assert sequence.validate() is True
        
        # Now test with a pulse that actually extends beyond total duration
        invalid_pulse = PulseDescription(
            name="invalid_pulse",
            pulse_type="pi",
            channel=1,
            shape=PulseShape.GAUSSIAN,
            duration=500e-6,  # 500μs
            amplitude=1.0,
            timing=600e-6     # 600μs + 500μs = 1.1ms > 1ms
        )
        
        sequence.add_pulse(invalid_pulse)
        assert sequence.validate() is False
    
    def test_validate_invalid_loop_timing(self):
        """Test validation of sequence with invalid loop timing."""
        sequence = SequenceDescription(
            name="test_sequence",
            experiment_type="test",
            total_duration=1e-3,
            sample_rate=1e9
        )
        
        # Add loop with invalid timing
        loop = LoopDescription(
            name="test_loop",
            iterations=5,
            start_time=0.5e-3,  # 0.5ms
            end_time=0.3e-3     # 0.3ms < 0.5ms (invalid)
        )
        
        sequence.add_loop(loop)
        assert sequence.validate() is False
    
    def test_validate_invalid_conditional_timing(self):
        """Test validation of sequence with invalid conditional timing."""
        sequence = SequenceDescription(
            name="test_sequence",
            experiment_type="test",
            total_duration=1e-3,
            sample_rate=1e9
        )
        
        # Add conditional with invalid timing
        conditional = ConditionalDescription(
            name="test_conditional",
            condition="if marker_1",
            start_time=1.5e-3,  # 1.5ms > 1ms (invalid)
            end_time=2e-3
        )
        
        sequence.add_conditional(conditional)
        assert sequence.validate() is False

    def test_repeat_count_default_and_custom(self):
        """Repeat count defaults to 1 and accepts positive integers."""
        seq_default = SequenceDescription(
            name="seq",
            experiment_type="test",
            total_duration=1e-3,
            sample_rate=1e9,
        )
        assert seq_default.repeat_count == 1

        seq_custom = SequenceDescription(
            name="seq",
            experiment_type="test",
            total_duration=1e-3,
            sample_rate=1e9,
            repeat_count=50000,
        )
        assert seq_custom.repeat_count == 50000

    def test_repeat_count_validation_non_positive(self):
        """Non-positive repeat counts should raise ValueError."""
        import pytest
        with pytest.raises(ValueError, match="Repeat count must be positive"):
            SequenceDescription(
                name="seq",
                experiment_type="test",
                total_duration=1e-3,
                sample_rate=1e9,
                repeat_count=0,
            )
        with pytest.raises(ValueError, match="Repeat count must be positive"):
            SequenceDescription(
                name="seq",
                experiment_type="test",
                total_duration=1e-3,
                sample_rate=1e9,
                repeat_count=-10,
            )
