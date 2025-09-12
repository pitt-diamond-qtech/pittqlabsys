"""
Test the new variable parsing functionality for range-based scanning.
"""

import pytest
from src.Model.sequence_parser import SequenceTextParser
from src.Model.sequence_description import VariableDescription


class TestVariableParsing:
    """Test the new range-based variable parsing."""
    
    def test_parse_timing_variable(self):
        """Test parsing a timing variable with ns units."""
        parser = SequenceTextParser()
        text = """
sequence: name=test, duration=1ms, sample_rate=1GHz
variable pulse_duration, start=100ns, stop=1000ns, steps=50
pi/2 pulse on channel 1 at 0ms, square, {pulse_duration}, 1.0
"""
        desc = parser.parse_text(text)
        
        assert "pulse_duration" in desc.variables
        var = desc.variables["pulse_duration"]
        assert abs(var.start_value - 100e-9) < 1e-12  # 100ns in seconds
        assert abs(var.stop_value - 1000e-9) < 1e-12  # 1000ns in seconds
        assert var.steps == 50
        assert var.unit == "ns"
        assert len(var.values) == 50
        assert abs(var.values[0] - 100e-9) < 1e-12
        assert abs(var.values[-1] - 1000e-9) < 1e-12
    
    def test_parse_voltage_variable(self):
        """Test parsing a voltage variable."""
        parser = SequenceTextParser()
        text = """
sequence: name=test, duration=1ms, sample_rate=1GHz
variable laser_power, start=0.5V, stop=2.0V, steps=10
laser pulse on channel 2 at 1ms, square, 100ns, {laser_power}
"""
        desc = parser.parse_text(text)
        
        assert "laser_power" in desc.variables
        var = desc.variables["laser_power"]
        assert abs(var.start_value - 0.5) < 1e-12
        assert abs(var.stop_value - 2.0) < 1e-12
        assert var.steps == 10
        assert var.unit == "V"
        assert len(var.values) == 10
        assert abs(var.values[0] - 0.5) < 1e-12
        assert abs(var.values[-1] - 2.0) < 1e-12
    
    def test_parse_frequency_variable(self):
        """Test parsing a frequency variable."""
        parser = SequenceTextParser()
        text = """
sequence: name=test, duration=1ms, sample_rate=1GHz
variable freq, start=1MHz, stop=10MHz, steps=20
sine pulse on channel 1 at 0ms, sine, 1us, 1.0
"""
        desc = parser.parse_text(text)
        
        assert "freq" in desc.variables
        var = desc.variables["freq"]
        assert abs(var.start_value - 1e6) < 1e-12  # 1MHz in Hz
        assert abs(var.stop_value - 10e6) < 1e-12  # 10MHz in Hz
        assert var.steps == 20
        assert var.unit == "mhz"  # Units are converted to lowercase
        assert len(var.values) == 20
    
    def test_parse_unitless_variable(self):
        """Test parsing a variable without units."""
        parser = SequenceTextParser()
        text = """
sequence: name=test, duration=1ms, sample_rate=1GHz
variable amplitude, start=0.1, stop=1.0, steps=5
pulse on channel 1 at 0ms, square, 1us, {amplitude}
"""
        desc = parser.parse_text(text)
        
        assert "amplitude" in desc.variables
        var = desc.variables["amplitude"]
        assert abs(var.start_value - 0.1) < 1e-12
        assert abs(var.stop_value - 1.0) < 1e-12
        assert var.steps == 5
        assert var.unit == ""
        assert len(var.values) == 5
    
    def test_parse_multiple_variables(self):
        """Test parsing multiple variables in the same sequence."""
        parser = SequenceTextParser()
        text = """
sequence: name=test, duration=1ms, sample_rate=1GHz
variable pulse_duration, start=100ns, stop=1000ns, steps=10
variable laser_power, start=0.5V, stop=2.0V, steps=5
pi/2 pulse on channel 1 at 0ms, square, {pulse_duration}, 1.0
laser pulse on channel 2 at 1ms, square, 100ns, {laser_power}
"""
        desc = parser.parse_text(text)
        
        assert len(desc.variables) == 2
        assert desc.get_total_scan_points() == 10 * 5  # 50 total scan points
        
        # Check pulse_duration variable
        pulse_var = desc.variables["pulse_duration"]
        assert pulse_var.steps == 10
        
        # Check laser_power variable
        laser_var = desc.variables["laser_power"]
        assert laser_var.steps == 5
    
    def test_invalid_variable_syntax(self):
        """Test that invalid variable syntax is handled gracefully with warnings."""
        parser = SequenceTextParser()
        
        # Missing start parameter - should be handled gracefully
        text1 = """
sequence: name=test, duration=1ms, sample_rate=1GHz
variable pulse_duration, stop=1000ns, steps=50
"""
        # This should parse successfully but skip the invalid variable line
        desc = parser.parse_text(text1)
        assert "pulse_duration" not in desc.variables
        
        # Inconsistent units - should be handled gracefully
        text2 = """
sequence: name=test, duration=1ms, sample_rate=1GHz
variable pulse_duration, start=100ns, stop=1us, steps=50
"""
        # This should parse successfully but skip the invalid variable line
        desc = parser.parse_text(text2)
        assert "pulse_duration" not in desc.variables
    
    def test_variable_values_generation(self):
        """Test that variable values are generated correctly."""
        var = VariableDescription(
            name="test",
            start_value=0.0,
            stop_value=1.0,
            steps=5,
            unit="V"
        )
        
        expected_values = [0.0, 0.25, 0.5, 0.75, 1.0]
        assert var.values == expected_values
        
        # Test iteration
        for i, value in enumerate(var.values):
            var.current_index = i
            assert var.get_current_value() == value
        
        # Test reset
        var.reset()
        assert var.current_index == 0
        assert var.get_current_value() == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
