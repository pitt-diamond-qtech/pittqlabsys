"""
Tests for the sequence parser module.

This module tests the parsing of human-readable text sequences and preset experiments
into structured data that can be processed by the sequence builder.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.Model.sequence_parser import (
    SequenceTextParser, ParseError, ParameterError, ValidationError
)
from src.Model.sequence_description import (
    SequenceDescription, PulseDescription, PulseShape, TimingType
)


class TestSequenceTextParser:
    """Test the SequenceTextParser class."""
    
    def test_initialization(self):
        """Test that SequenceTextParser initializes correctly."""
        parser = SequenceTextParser()
        
        assert hasattr(parser, 'preset_qubit_experiments')
        assert isinstance(parser.preset_qubit_experiments, dict)
    
    def test_parse_file_not_implemented(self):
        """Test that parse_file raises NotImplementedError."""
        parser = SequenceTextParser()
        
        with pytest.raises(NotImplementedError, match="parse_file method not implemented"):
            parser.parse_file("test.txt")
    
    def test_parse_preset_not_implemented(self):
        """Test that parse_preset raises NotImplementedError."""
        parser = SequenceTextParser()
        
        with pytest.raises(NotImplementedError, match="parse_preset method not implemented"):
            parser.parse_preset("odmr")
    
    def test_parse_text_not_implemented(self):
        """Test that parse_text raises NotImplementedError."""
        parser = SequenceTextParser()
        
        with pytest.raises(NotImplementedError, match="parse_text method not implemented"):
            parser.parse_text("pi/2 pulse on channel 1")
    
    def test_load_preset_experiments_not_implemented(self):
        """Test that _load_preset_qubit_experiments raises NotImplementedError."""
        parser = SequenceTextParser()
        
        with pytest.raises(NotImplementedError, match="_load_preset_qubit_experiments method not implemented"):
            parser._load_preset_qubit_experiments()
    
    def test_parse_pulse_line_not_implemented(self):
        """Test that _parse_pulse_line raises NotImplementedError."""
        parser = SequenceTextParser()
        
        with pytest.raises(NotImplementedError, match="_parse_pulse_line method not implemented"):
            parser._parse_pulse_line("pi/2 pulse on channel 1")
    
    def test_parse_timing_expression_not_implemented(self):
        """Test that _parse_timing_expression raises NotImplementedError."""
        parser = SequenceTextParser()
        
        with pytest.raises(NotImplementedError, match="_parse_timing_expression method not implemented"):
            parser._parse_timing_expression("1ms")
    
    def test_parse_loop_block_not_implemented(self):
        """Test that _parse_loop_block raises NotImplementedError."""
        parser = SequenceTextParser()
        
        lines = ["repeat 10 times:", "  pi/2 pulse", "  wait 1ms"]
        
        with pytest.raises(NotImplementedError, match="_parse_loop_block method not implemented"):
            parser._parse_loop_block(lines)
    
    def test_parse_conditional_block_not_implemented(self):
        """Test that _parse_conditional_block raises NotImplementedError."""
        parser = SequenceTextParser()
        
        lines = ["if marker_1:", "  pi/2 pulse", "else:", "  wait 100ns"]
        
        with pytest.raises(NotImplementedError, match="_parse_conditional_block method not implemented"):
            parser._parse_conditional_block(lines)
    
    def test_validate_sequence_not_implemented(self):
        """Test that validate_sequence raises NotImplementedError."""
        parser = SequenceTextParser()
        
        description = SequenceDescription(
            name="test_sequence",
            experiment_type="test",
            total_duration=1e-3,
            sample_rate=1e9
        )
        
        with pytest.raises(NotImplementedError, match="validate_sequence method not implemented"):
            parser.validate_sequence(description)


class TestParseError:
    """Test the ParseError exception."""
    
    def test_parse_error_creation(self):
        """Test creating a ParseError."""
        error = ParseError("Test parse error")
        assert str(error) == "Test parse error"
    
    def test_parse_error_inheritance(self):
        """Test that ParseError inherits from Exception."""
        error = ParseError("Test")
        assert isinstance(error, Exception)


class TestParameterError:
    """Test the ParameterError exception."""
    
    def test_parameter_error_creation(self):
        """Test creating a ParameterError."""
        error = ParameterError("Test parameter error")
        assert str(error) == "Test parameter error"
    
    def test_parameter_error_inheritance(self):
        """Test that ParameterError inherits from Exception."""
        error = ParameterError("Test")
        assert isinstance(error, Exception)


class TestValidationError:
    """Test the ValidationError exception."""
    
    def test_validation_error_creation(self):
        """Test creating a ValidationError."""
        error = ValidationError("Test validation error")
        assert str(error) == "Test validation error"
    
    def test_validation_error_inheritance(self):
        """Test that ValidationError inherits from Exception."""
        error = ValidationError("Test")
        assert isinstance(error, Exception)


class TestSequenceTextParserIntegration:
    """Integration tests for SequenceTextParser."""
    
    def test_parser_with_mock_preset_experiments(self):
        """Test SequenceTextParser with mock preset experiments."""
        parser = SequenceTextParser()
        
        # Test that preset experiments are loaded (even if empty)
        assert hasattr(parser, 'preset_qubit_experiments')
        
        # Test that methods are not implemented (as expected)
        with pytest.raises(NotImplementedError):
            parser.parse_file("test.txt")
        
        with pytest.raises(NotImplementedError):
            parser.parse_preset("odmr")
        
        with pytest.raises(NotImplementedError):
            parser.parse_text("test sequence")
    
    def test_parser_error_handling(self):
        """Test that parser properly handles errors."""
        parser = SequenceTextParser()
        
        # Test that NotImplementedError is raised for all methods
        methods_to_test = [
            ('parse_file', ["test.txt"]),
            ('parse_preset', ["odmr"]),
            ('parse_text', ["test sequence"]),
            ('_parse_pulse_line', ["pi/2 pulse"]),
            ('_parse_timing_expression', ["1ms"]),
            ('_parse_loop_block', [["repeat 10 times:"]]),
            ('_parse_conditional_block', [["if marker_1:"]]),
            ('validate_sequence', [Mock(spec=SequenceDescription)])
        ]
        
        for method_name, args in methods_to_test:
            method = getattr(parser, method_name)
            with pytest.raises(NotImplementedError):
                method(*args)
    
    def test_parser_initialization_consistency(self):
        """Test that parser initialization is consistent."""
        parser1 = SequenceTextParser()
        parser2 = SequenceTextParser()
        
        # Both should have the same structure
        assert hasattr(parser1, 'preset_qubit_experiments')
        assert hasattr(parser2, 'preset_qubit_experiments')
        
        # Both should have the same methods
        methods = [
            'parse_file', 'parse_preset', 'parse_text',
            '_load_preset_qubit_experiments', '_parse_pulse_line',
            '_parse_timing_expression', '_parse_loop_block',
            '_parse_conditional_block', 'validate_sequence'
        ]
        
        for method in methods:
            assert hasattr(parser1, method)
            assert hasattr(parser2, method)


class TestSequenceParserTextFormat:
    """Test the expected text format parsing capabilities."""
    
    def test_expected_pulse_syntax(self):
        """Test that parser will handle expected pulse syntax."""
        parser = SequenceTextParser()
        
        # These are the expected text formats that will be implemented
        expected_formats = [
            "pi/2 pulse on channel 1 at 0ms, gaussian shape, 100ns duration",
            "pi pulse on channel 2 at 1ms, sech shape, 200ns duration",
            "wait 2ms",
            "pi/2 pulse on channel 1 at 3ms, gaussian shape, 100ns duration"
        ]
        
        # Currently all should raise NotImplementedError
        for text in expected_formats:
            with pytest.raises(NotImplementedError):
                parser.parse_text(text)
    
    def test_expected_preset_syntax(self):
        """Test that parser will handle expected preset syntax."""
        parser = SequenceTextParser()
        
        # These are the expected preset formats that will be implemented
        expected_presets = [
            "odmr",
            "rabi",
            "spin_echo",
            "cpmg",
            "ramsey"
        ]
        
        # Currently all should raise NotImplementedError
        for preset in expected_presets:
            with pytest.raises(NotImplementedError):
                parser.parse_preset(preset)
    
    def test_expected_timing_expressions(self):
        """Test that parser will handle expected timing expressions."""
        parser = SequenceTextParser()
        
        # These are the expected timing formats that will be implemented
        expected_timings = [
            "0ms",
            "1ms",
            "100ns",
            "0.5s",
            "1.5μs"
        ]
        
        # Currently all should raise NotImplementedError
        for timing in expected_timings:
            with pytest.raises(NotImplementedError):
                parser._parse_timing_expression(timing)
    
    def test_expected_loop_syntax(self):
        """Test that parser will handle expected loop syntax."""
        parser = SequenceTextParser()
        
        # These are the expected loop formats that will be implemented
        expected_loops = [
            ["repeat 100 times:", "  pi/2 at 0ms", "  wait 1ms", "  pi at 2ms"],
            ["for tau in [1ms, 2ms, 5ms]:", "  pi/2 at 0ms", "  wait tau"]
        ]
        
        # Currently all should raise NotImplementedError
        for loop_lines in expected_loops:
            with pytest.raises(NotImplementedError):
                parser._parse_loop_block(loop_lines)
    
    def test_expected_conditional_syntax(self):
        """Test that parser will handle expected conditional syntax."""
        parser = SequenceTextParser()
        
        # These are the expected conditional formats that will be implemented
        expected_conditionals = [
            ["if marker_1:", "  pi/2 at 0ms", "else:", "  wait 100ns"],
            ["if variable > 0:", "  pi pulse", "else:", "  wait 1ms"]
        ]
        
        # Currently all should raise NotImplementedError
        for conditional_lines in expected_conditionals:
            with pytest.raises(NotImplementedError):
                parser._parse_conditional_block(conditional_lines)


class TestSequenceParserFileHandling:
    """Test the expected file handling capabilities."""
    
    def test_file_parsing_capabilities(self):
        """Test that parser will handle expected file formats."""
        parser = SequenceTextParser()
        
        # Create a temporary file with test content
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("# Test sequence\n")
            f.write("pi/2 pulse on channel 1 at 0ms\n")
            f.write("wait 1ms\n")
            f.write("pi pulse on channel 1 at 1ms\n")
            temp_file = f.name
        
        try:
            # Currently should raise NotImplementedError
            with pytest.raises(NotImplementedError):
                parser.parse_file(temp_file)
        finally:
            # Clean up
            Path(temp_file).unlink()
    
    def test_file_not_found_handling(self):
        """Test that parser will handle file not found errors."""
        parser = SequenceTextParser()
        
        # Currently should raise NotImplementedError before file handling
        with pytest.raises(NotImplementedError):
            parser.parse_file("nonexistent_file.txt")
    
    def test_file_parsing_error_handling(self):
        """Test that parser will handle file parsing errors."""
        parser = SequenceTextParser()
        
        # Create a temporary file with invalid content
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("invalid syntax here\n")
            f.write("this should cause a parse error\n")
            temp_file = f.name
        
        try:
            # Currently should raise NotImplementedError
            with pytest.raises(NotImplementedError):
                parser.parse_file(temp_file)
        finally:
            # Clean up
            Path(temp_file).unlink()


class TestSequenceParserValidation:
    """Test the expected validation capabilities."""
    
    def test_sequence_validation_capabilities(self):
        """Test that parser will validate sequences correctly."""
        parser = SequenceTextParser()
        
        # Create a valid sequence description
        valid_sequence = SequenceDescription(
            name="test_sequence",
            experiment_type="test",
            total_duration=1e-3,
            sample_rate=1e9
        )
        
        # Add a valid pulse
        pulse = PulseDescription(
            name="test_pulse",
            pulse_type="pi/2",
            channel=1,
            shape=PulseShape.GAUSSIAN,
            duration=100e-9,
            amplitude=1.0,
            timing=0.0
        )
        valid_sequence.add_pulse(pulse)
        
        # Currently should raise NotImplementedError
        with pytest.raises(NotImplementedError):
            parser.validate_sequence(valid_sequence)
    
    def test_sequence_validation_error_handling(self):
        """Test that parser will handle validation errors correctly."""
        parser = SequenceTextParser()
        
        # Create an invalid sequence description
        invalid_sequence = SequenceDescription(
            name="test_sequence",
            experiment_type="test",
            total_duration=1e-3,
            sample_rate=1e9
        )
        
        # Add a pulse that extends beyond total duration
        invalid_pulse = PulseDescription(
            name="test_pulse",
            pulse_type="pi/2",
            channel=1,
            shape=PulseShape.GAUSSIAN,
            duration=500e-9,
            amplitude=1.0,
            timing=600e-9  # 600ns + 500ns = 1.1ms > 1ms
        )
        invalid_sequence.add_pulse(invalid_pulse)
        
        # Currently should raise NotImplementedError
        with pytest.raises(NotImplementedError):
            parser.validate_sequence(invalid_sequence)


class TestSequenceParserPresetIntegration:
    """Test the integration between parser and preset experiments."""
    
    def test_preset_experiment_parsing(self):
        """Test that parser will handle preset experiments correctly."""
        parser = SequenceTextParser()
        
        # Test that preset experiments are accessible
        assert hasattr(parser, 'preset_qubit_experiments')
        
        # Test that preset parsing methods exist
        assert hasattr(parser, 'parse_preset')
        assert hasattr(parser, '_load_preset_qubit_experiments')
        
        # Currently all should raise NotImplementedError
        with pytest.raises(NotImplementedError):
            parser.parse_preset("odmr")
        
        with pytest.raises(NotImplementedError):
            parser._load_preset_qubit_experiments()
    
    def test_preset_customization_parsing(self):
        """Test that parser will handle preset customization correctly."""
        parser = SequenceTextParser()
        
        # Test that preset parsing with custom parameters will work
        # Currently should raise NotImplementedError
        with pytest.raises(NotImplementedError):
            parser.parse_preset("odmr", microwave_frequency=3.0e9)
        
        with pytest.raises(NotImplementedError):
            parser.parse_preset("rabi", pulse_duration_points=100)
    
    def test_preset_validation_integration(self):
        """Test that parser will validate preset experiments correctly."""
        parser = SequenceTextParser()
        
        # Test that preset validation will work
        # Currently should raise NotImplementedError
        with pytest.raises(NotImplementedError):
            parser.parse_preset("invalid_preset")
        
        # Test that preset parameter validation will work
        with pytest.raises(NotImplementedError):
            parser.parse_preset("odmr", invalid_parameter="invalid_value")
