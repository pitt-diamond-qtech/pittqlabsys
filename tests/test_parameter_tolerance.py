"""
Tests for Parameter class tolerance validation functionality.

This module tests the enhanced Parameter class with tolerance support, including:
- Tolerance parameter initialization
- Tolerance validation logic
- Percentage and absolute tolerance calculations
- Warning threshold handling
- Edge cases and error handling
"""

import pytest
import numpy as np
from src.core.parameter import Parameter, ValidationError


class TestParameterTolerance:
    """Test Parameter class tolerance functionality."""
    
    def test_parameter_with_tolerance_percent(self):
        """Test parameter creation with percentage tolerance."""
        p = Parameter(
            'frequency', 
            2.85e9, 
            float, 
            'Microwave frequency',
            tolerance_percent=0.1,
            validation_enabled=True
        )
        
        assert p['frequency'] == 2.85e9
        assert hasattr(p, '_tolerance_percent')
        assert p._tolerance_percent['frequency'] == 0.1
        assert p._validation_enabled['frequency'] is True
    
    def test_parameter_with_tolerance_absolute(self):
        """Test parameter creation with absolute tolerance."""
        p = Parameter(
            'power', 
            -10.0, 
            float, 
            'Power in dBm',
            tolerance_absolute=0.5,
            validation_enabled=True
        )
        
        assert p['power'] == -10.0
        assert hasattr(p, '_tolerance_absolute')
        assert p._tolerance_absolute['power'] == 0.5
        assert p._validation_enabled['power'] is True
    
    def test_parameter_with_both_tolerances(self):
        """Test parameter creation with both percentage and absolute tolerance."""
        p = Parameter(
            'position', 
            50.0, 
            float, 
            'Position in μm',
            tolerance_percent=1.0,
            tolerance_absolute=0.5,
            validation_enabled=True
        )
        
        assert p['position'] == 50.0
        assert p._tolerance_percent['position'] == 1.0
        assert p._tolerance_absolute['position'] == 0.5
        assert p._validation_enabled['position'] is True
    
    def test_parameter_tolerance_disabled(self):
        """Test parameter creation with tolerance validation disabled."""
        p = Parameter(
            'test_param', 
            100, 
            int, 
            'Test parameter',
            tolerance_percent=5.0,
            validation_enabled=False
        )
        
        assert p._validation_enabled['test_param'] is False
    
    def test_parameter_tolerance_defaults(self):
        """Test parameter creation with default tolerance values."""
        p = Parameter('test_param', 100, int, 'Test parameter')
        
        # Should have tolerance attributes with None values
        assert hasattr(p, '_tolerance_percent')
        assert hasattr(p, '_tolerance_absolute')
        assert hasattr(p, '_validation_enabled')
        assert p._tolerance_percent['test_param'] is None
        assert p._tolerance_absolute['test_param'] is None
        assert p._validation_enabled['test_param'] is True  # Default enabled


class TestToleranceValidation:
    """Test tolerance validation logic."""
    
    def test_validate_tolerance_percent_only(self):
        """Test validation with percentage tolerance only."""
        p = Parameter(
            'frequency', 
            2.85e9, 
            float, 
            'Frequency',
            tolerance_percent=0.1,
            validation_enabled=True
        )
        
        # Test within tolerance
        result = p.validate_tolerance('frequency', 2.85e9, 2.85e9)
        assert result['within_tolerance'] is True
        assert result['deviation_percent'] == 0.0
        
        # Test within tolerance (small deviation)
        result = p.validate_tolerance('frequency', 2.85e9, 2.851e9)
        assert result['within_tolerance'] is True
        assert result['deviation_percent'] < 0.1
        
        # Test outside tolerance
        result = p.validate_tolerance('frequency', 2.85e9, 2.9e9)
        assert result['within_tolerance'] is False
        assert result['deviation_percent'] > 0.1
    
    def test_validate_tolerance_absolute_only(self):
        """Test validation with absolute tolerance only."""
        p = Parameter(
            'power', 
            -10.0, 
            float, 
            'Power',
            tolerance_absolute=0.5,
            validation_enabled=True
        )
        
        # Test within tolerance
        result = p.validate_tolerance('power', -10.0, -10.0)
        assert result['within_tolerance'] is True
        assert result['deviation_absolute'] == 0.0
        
        # Test within tolerance (small deviation)
        result = p.validate_tolerance('power', -10.0, -10.3)
        assert result['within_tolerance'] is True
        assert result['deviation_absolute'] < 0.5
        
        # Test outside tolerance
        result = p.validate_tolerance('power', -10.0, -11.0)
        assert result['within_tolerance'] is False
        assert result['deviation_absolute'] > 0.5
    
    def test_validate_tolerance_both_percent_and_absolute(self):
        """Test validation with both percentage and absolute tolerance."""
        p = Parameter(
            'position', 
            50.0, 
            float, 
            'Position',
            tolerance_percent=1.0,
            tolerance_absolute=0.5,
            validation_enabled=True
        )
        
        # Test within both tolerances
        result = p.validate_tolerance('position', 50.0, 50.2)
        assert result['within_tolerance'] is True
        
        # Test within percentage but outside absolute
        result = p.validate_tolerance('position', 50.0, 50.6)
        assert result['within_tolerance'] is False
        
        # Test within absolute but outside percentage
        result = p.validate_tolerance('position', 50.0, 51.5)
        assert result['within_tolerance'] is False
    
    def test_validate_tolerance_warning_threshold(self):
        """Test warning threshold functionality."""
        p = Parameter(
            'frequency', 
            2.85e9, 
            float, 
            'Frequency',
            tolerance_percent=1.0,
            validation_enabled=True
        )
        
        # Test warning threshold (80% of tolerance)
        result = p.validate_tolerance('frequency', 2.85e9, 2.85e9 * 1.008)  # 0.8% deviation
        assert result['within_tolerance'] is True
        assert result['warning_threshold_exceeded'] is True
        
        # Test no warning
        result = p.validate_tolerance('frequency', 2.85e9, 2.85e9 * 1.005)  # 0.5% deviation
        assert result['within_tolerance'] is True
        assert result['warning_threshold_exceeded'] is False
    
    def test_validate_tolerance_zero_target_value(self):
        """Test tolerance validation with zero target value."""
        p = Parameter(
            'offset', 
            0.0, 
            float, 
            'Offset',
            tolerance_percent=1.0,
            tolerance_absolute=0.1,
            validation_enabled=True
        )
        
        # Test with zero target value
        result = p.validate_tolerance('offset', 0.0, 0.05)
        assert result['within_tolerance'] is True
        assert result['deviation_percent'] == 0.0  # Should be 0 for zero target
        assert result['deviation_absolute'] == 0.05
    
    def test_validate_tolerance_negative_values(self):
        """Test tolerance validation with negative values."""
        p = Parameter(
            'power', 
            -10.0, 
            float, 
            'Power',
            tolerance_percent=5.0,
            validation_enabled=True
        )
        
        # Test with negative values
        result = p.validate_tolerance('power', -10.0, -10.5)
        assert result['within_tolerance'] is True
        assert result['deviation_percent'] == 5.0
    
    def test_validate_tolerance_disabled(self):
        """Test tolerance validation when disabled."""
        p = Parameter(
            'test_param', 
            100, 
            int, 
            'Test parameter',
            tolerance_percent=1.0,
            validation_enabled=False
        )
        
        # Should return None when validation is disabled
        result = p.validate_tolerance('test_param', 100, 200)
        assert result is None
    
    def test_validate_tolerance_nonexistent_parameter(self):
        """Test tolerance validation for non-existent parameter."""
        p = Parameter('test_param', 100, int, 'Test parameter')
        
        # Should raise KeyError for non-existent parameter
        with pytest.raises(KeyError):
            p.validate_tolerance('nonexistent', 100, 200)


class TestToleranceEdgeCases:
    """Test edge cases and error handling for tolerance validation."""
    
    def test_tolerance_very_small_values(self):
        """Test tolerance validation with very small values."""
        p = Parameter(
            'small_value', 
            1e-9, 
            float, 
            'Very small value',
            tolerance_percent=0.1,
            tolerance_absolute=1e-12,
            validation_enabled=True
        )
        
        result = p.validate_tolerance('small_value', 1e-9, 1.1e-9)
        assert result['within_tolerance'] is False
        assert result['deviation_percent'] == 10.0
    
    def test_tolerance_very_large_values(self):
        """Test tolerance validation with very large values."""
        p = Parameter(
            'large_value', 
            1e9, 
            float, 
            'Very large value',
            tolerance_percent=0.01,
            tolerance_absolute=1e6,
            validation_enabled=True
        )
        
        result = p.validate_tolerance('large_value', 1e9, 1.01e9)
        assert result['within_tolerance'] is False
        assert result['deviation_percent'] == 1.0
    
    def test_tolerance_identical_values(self):
        """Test tolerance validation with identical values."""
        p = Parameter(
            'exact_value', 
            100.0, 
            float, 
            'Exact value',
            tolerance_percent=0.1,
            validation_enabled=True
        )
        
        result = p.validate_tolerance('exact_value', 100.0, 100.0)
        assert result['within_tolerance'] is True
        assert result['deviation_percent'] == 0.0
        assert result['deviation_absolute'] == 0.0
    
    def test_tolerance_nan_values(self):
        """Test tolerance validation with NaN values."""
        p = Parameter(
            'nan_value', 
            100.0, 
            float, 
            'NaN value',
            tolerance_percent=0.1,
            validation_enabled=True
        )
        
        # Test with NaN actual value
        result = p.validate_tolerance('nan_value', 100.0, float('nan'))
        assert result['within_tolerance'] is False
        assert np.isnan(result['deviation_percent'])
        assert np.isnan(result['deviation_absolute'])
    
    def test_tolerance_infinity_values(self):
        """Test tolerance validation with infinity values."""
        p = Parameter(
            'inf_value', 
            100.0, 
            float, 
            'Infinity value',
            tolerance_percent=0.1,
            validation_enabled=True
        )
        
        # Test with infinity actual value
        result = p.validate_tolerance('inf_value', 100.0, float('inf'))
        assert result['within_tolerance'] is False
        assert result['deviation_percent'] == float('inf')
        assert result['deviation_absolute'] == float('inf')


class TestToleranceMultipleParameters:
    """Test tolerance validation with multiple parameters."""
    
    def test_multiple_parameters_with_tolerances(self):
        """Test multiple parameters with different tolerance settings."""
        p = Parameter([
            Parameter('frequency', 2.85e9, float, 'Frequency', 
                     tolerance_percent=0.1, validation_enabled=True),
            Parameter('power', -10.0, float, 'Power', 
                     tolerance_absolute=0.5, validation_enabled=True),
            Parameter('mode', 'CW', str, 'Mode', 
                     validation_enabled=False)
        ])
        
        # Test frequency parameter
        result = p.validate_tolerance('frequency', 2.85e9, 2.86e9)
        assert result['within_tolerance'] is True
        
        # Test power parameter
        result = p.validate_tolerance('power', -10.0, -10.3)
        assert result['within_tolerance'] is True
        
        # Test disabled parameter
        result = p.validate_tolerance('mode', 'CW', 'PULSE')
        assert result is None
    
    def test_validate_all_parameters_tolerance(self):
        """Test validating all parameters at once."""
        p = Parameter([
            Parameter('frequency', 2.85e9, float, 'Frequency', 
                     tolerance_percent=0.1, validation_enabled=True),
            Parameter('power', -10.0, float, 'Power', 
                     tolerance_absolute=0.5, validation_enabled=True),
            Parameter('mode', 'CW', str, 'Mode', 
                     validation_enabled=False)
        ])
        
        # Test with all parameters within tolerance
        target_values = {'frequency': 2.85e9, 'power': -10.0, 'mode': 'CW'}
        actual_values = {'frequency': 2.85e9, 'power': -10.0, 'mode': 'CW'}
        
        results = p.validate_all_parameters_tolerance(target_values, actual_values)
        
        assert 'frequency' in results
        assert 'power' in results
        assert 'mode' not in results  # Disabled parameter
        
        assert results['frequency']['within_tolerance'] is True
        assert results['power']['within_tolerance'] is True


if __name__ == '__main__':
    pytest.main([__file__])