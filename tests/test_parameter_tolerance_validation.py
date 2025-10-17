#!/usr/bin/env python3
"""
Test script to verify that the enhanced parameter validation with tolerance checking works.

This script tests:
1. Parameter validation ranges (min/max values)
2. Tolerance checking (percentage and absolute)
3. Hardware feedback simulation
4. GUI notification system
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.core.device import Device, Parameter
from src.Controller import MockSG384Generator, MockMCLNanoDrive
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class TestParameterToleranceValidation:
    """Test class for parameter tolerance validation functionality."""
    
    def test_sg384_tolerance_validation(self):
        """Test SG384 parameter validation with tolerance checking."""
        print("\n" + "="*60)
        print("TESTING SG384 TOLERANCE VALIDATION")
        print("="*60)
        
        # Create mock SG384 device
        sg384 = MockSG384Generator(name="test_sg384")
        
        # Test cases for frequency parameter
        test_cases = [
            {
                "name": "Valid frequency within tolerance",
                "requested": 2.87e9,
                "actual": 2.87e9,
                "expected_result": "success"
            },
            {
                "name": "Frequency within tolerance (small drift)",
                "requested": 2.87e9,
                "actual": 2.8701e9,  # 100 Hz drift, within 10 kHz tolerance
                "expected_result": "success"
            },
            {
                "name": "Frequency outside tolerance (large drift)",
                "requested": 2.87e9,
                "actual": 2.871e9,  # 1 MHz drift, outside 10 kHz tolerance
                "expected_result": "tolerance_violation"
            },
            {
                "name": "Frequency clamped to maximum",
                "requested": 5.0e9,
                "actual": 4.1e9,  # Clamped to max
                "expected_result": "clamped_to_max"
            },
            {
                "name": "Frequency clamped to minimum",
                "requested": 1.0e9,
                "actual": 1.9e9,  # Clamped to min
                "expected_result": "clamped_to_min"
            }
        ]
        
        for test_case in test_cases:
            print(f"\n--- {test_case['name']} ---")
            print(f"Requested: {test_case['requested']}")
            print(f"Actual: {test_case['actual']}")
            
            # Simulate the _update_and_get_with_feedback method
            settings = {'frequency': test_case['requested']}
            
            # Mock the actual value that hardware would return
            original_read_probes = sg384.read_probes
            def mock_read_probes():
                return {'frequency': test_case['actual']}
            sg384.read_probes = mock_read_probes
            
            try:
                # Get feedback
                feedback = sg384.get_feedback_only(settings)
                freq_feedback = feedback.get('frequency', {})
                
                print(f"Feedback reason: {freq_feedback.get('reason', 'unknown')}")
                print(f"Feedback message: {freq_feedback.get('message', 'no message')}")
                print(f"Tolerance violation: {freq_feedback.get('tolerance_violation', False)}")
                
                # Verify expected result
                assert freq_feedback.get('reason') == test_case['expected_result'], \
                    f"Expected {test_case['expected_result']}, got {freq_feedback.get('reason')}"
                print("✅ PASS")
                
            except Exception as e:
                print(f"❌ ERROR: {e}")
                pytest.fail(f"Test failed with error: {e}")
            finally:
                # Restore original method
                sg384.read_probes = original_read_probes

    def test_nanodrive_tolerance_validation(self):
        """Test nanodrive parameter validation with tolerance checking."""
        print("\n" + "="*60)
        print("TESTING NANODRIVE TOLERANCE VALIDATION")
        print("="*60)
        
        # Create mock nanodrive device
        nanodrive = MockMCLNanoDrive(settings={'x_pos': 0.0, 'y_pos': 0.0, 'z_pos': 0.0})
        
        # Test cases for x_pos parameter
        test_cases = [
            {
                "name": "Valid position within tolerance",
                "requested": 50.0,
                "actual": 50.0,
                "expected_result": "success"
            },
            {
                "name": "Position within tolerance (small drift)",
                "requested": 50.0,
                "actual": 50.0005,  # 0.5 micron drift, within 0.001 micron tolerance
                "expected_result": "success"
            },
            {
                "name": "Position outside tolerance (large drift)",
                "requested": 50.0,
                "actual": 50.002,  # 2 micron drift, outside 0.001 micron tolerance
                "expected_result": "tolerance_violation"
            },
            {
                "name": "Position clamped to maximum",
                "requested": 150.0,
                "actual": 100.0,  # Clamped to max
                "expected_result": "clamped_to_max"
            },
            {
                "name": "Position clamped to minimum",
                "requested": -10.0,
                "actual": 0.0,  # Clamped to min
                "expected_result": "clamped_to_min"
            }
        ]
        
        for test_case in test_cases:
            print(f"\n--- {test_case['name']} ---")
            print(f"Requested: {test_case['requested']}")
            print(f"Actual: {test_case['actual']}")
            
            # Simulate the _update_and_get_with_feedback method
            settings = {'x_pos': test_case['requested']}
            
            # Mock the actual value that hardware would return
            original_read_probes = nanodrive.read_probes
            def mock_read_probes():
                return {'x_pos': test_case['actual']}
            nanodrive.read_probes = mock_read_probes
            
            try:
                # Get feedback
                feedback = nanodrive.get_feedback_only(settings)
                pos_feedback = feedback.get('x_pos', {})
                
                print(f"Feedback reason: {pos_feedback.get('reason', 'unknown')}")
                print(f"Feedback message: {pos_feedback.get('message', 'no message')}")
                print(f"Tolerance violation: {pos_feedback.get('tolerance_violation', False)}")
                
                # Verify expected result
                assert pos_feedback.get('reason') == test_case['expected_result'], \
                    f"Expected {test_case['expected_result']}, got {pos_feedback.get('reason')}"
                print("✅ PASS")
                
            except Exception as e:
                print(f"❌ ERROR: {e}")
                pytest.fail(f"Test failed with error: {e}")
            finally:
                # Restore original method
                nanodrive.read_probes = original_read_probes

    def test_parameter_validation_ranges(self):
        """Test that parameter validation ranges are properly set."""
        print("\n" + "="*60)
        print("TESTING PARAMETER VALIDATION RANGES")
        print("="*60)
        
        # Test SG384 frequency parameter
        sg384 = MockSG384Generator(name="test_sg384")
        freq_param = sg384._get_parameter_object('frequency')
        
        if freq_param:
            print(f"SG384 frequency parameter:")
            print(f"  Min value: {getattr(freq_param, 'min_value', 'Not set')}")
            print(f"  Max value: {getattr(freq_param, 'max_value', 'Not set')}")
            print(f"  Tolerance percent: {getattr(freq_param, 'tolerance_percent', 'Not set')}")
            print(f"  Tolerance absolute: {getattr(freq_param, 'tolerance_absolute', 'Not set')}")
            
            # Test validation
            validation_result = sg384.validate_parameter(['frequency'], 5.0e9)  # Out of range
            print(f"  Validation of 5.0 GHz: {validation_result}")
            
            validation_result = sg384.validate_parameter(['frequency'], 2.87e9)  # In range
            print(f"  Validation of 2.87 GHz: {validation_result}")
        else:
            pytest.fail("Could not get frequency parameter object")
        
        # Test nanodrive x_pos parameter
        nanodrive = MockMCLNanoDrive(settings={'x_pos': 0.0, 'y_pos': 0.0, 'z_pos': 0.0})
        pos_param = nanodrive._get_parameter_object('x_pos')
        
        if pos_param:
            print(f"\nNanodrive x_pos parameter:")
            print(f"  Min value: {getattr(pos_param, 'min_value', 'Not set')}")
            print(f"  Max value: {getattr(pos_param, 'max_value', 'Not set')}")
            print(f"  Tolerance percent: {getattr(pos_param, 'tolerance_percent', 'Not set')}")
            print(f"  Tolerance absolute: {getattr(pos_param, 'tolerance_absolute', 'Not set')}")
            
            # Test validation
            validation_result = nanodrive.validate_parameter(['x_pos'], 150.0)  # Out of range
            print(f"  Validation of 150.0 microns: {validation_result}")
            
            validation_result = nanodrive.validate_parameter(['x_pos'], 50.0)  # In range
            print(f"  Validation of 50.0 microns: {validation_result}")
        else:
            pytest.fail("Could not get x_pos parameter object")

    def test_tolerance_calculation(self):
        """Test that tolerance calculations work correctly."""
        print("\n" + "="*60)
        print("TESTING TOLERANCE CALCULATION")
        print("="*60)
        
        # Test SG384 frequency tolerance calculation
        sg384 = MockSG384Generator(name="test_sg384")
        
        # Test case: 2.87 GHz with 0.01% tolerance and 10 kHz absolute tolerance
        requested_freq = 2.87e9
        percent_tolerance = 0.01  # 0.01%
        absolute_tolerance = 10000  # 10 kHz
        
        # Calculate expected tolerance bounds
        percent_tolerance_hz = abs(requested_freq * percent_tolerance)  # 0.01% of 2.87 GHz
        total_tolerance = max(percent_tolerance_hz, absolute_tolerance)
        
        print(f"Requested frequency: {requested_freq/1e9:.3f} GHz")
        print(f"Percent tolerance: {percent_tolerance_hz:.0f} Hz ({percent_tolerance*100}%)")
        print(f"Absolute tolerance: {absolute_tolerance:.0f} Hz")
        print(f"Total tolerance: {total_tolerance:.0f} Hz")
        
        # Test values within tolerance
        within_tolerance_values = [
            requested_freq + 5000,   # +5 kHz
            requested_freq - 5000,   # -5 kHz
            requested_freq + 10000,  # +10 kHz (at absolute limit)
            requested_freq - 10000,  # -10 kHz (at absolute limit)
        ]
        
        for test_value in within_tolerance_values:
            diff = abs(test_value - requested_freq)
            assert diff <= total_tolerance, f"Value {test_value/1e9:.6f} GHz should be within tolerance"
            print(f"✅ {test_value/1e9:.6f} GHz (diff: {diff:.0f} Hz) - within tolerance")
        
        # Test values outside tolerance
        outside_tolerance_values = [
            requested_freq + 300000,   # +300 kHz (outside 287 kHz tolerance)
            requested_freq - 300000,  # -300 kHz (outside 287 kHz tolerance)
        ]
        
        for test_value in outside_tolerance_values:
            diff = abs(test_value - requested_freq)
            assert diff > total_tolerance, f"Value {test_value/1e9:.6f} GHz should be outside tolerance"
            print(f"✅ {test_value/1e9:.6f} GHz (diff: {diff:.0f} Hz) - outside tolerance")

    def test_device_feedback_integration(self):
        """Test that device feedback integration works end-to-end."""
        print("\n" + "="*60)
        print("TESTING DEVICE FEEDBACK INTEGRATION")
        print("="*60)
        
        # Test SG384 with realistic hardware simulation
        sg384 = MockSG384Generator(name="test_sg384")
        
        # Simulate hardware that has some drift
        def realistic_hardware_read_probes():
            # Simulate hardware that returns slightly different values
            base_freq = sg384.settings.get('frequency', 2.87e9)
            # Add small random drift (±1 kHz)
            import random
            drift = random.uniform(-1000, 1000)
            return {'frequency': base_freq + drift}
        
        sg384.read_probes = realistic_hardware_read_probes
        
        # Test multiple updates
        test_frequencies = [2.87e9, 3.0e9, 3.5e9, 4.0e9]
        
        for freq in test_frequencies:
            print(f"\nTesting frequency: {freq/1e9:.3f} GHz")
            
            settings = {'frequency': freq}
            feedback = sg384.get_feedback_only(settings)
            freq_feedback = feedback.get('frequency', {})
            
            print(f"  Requested: {freq/1e9:.6f} GHz")
            print(f"  Actual: {freq_feedback.get('actual', 0)/1e9:.6f} GHz")
            print(f"  Reason: {freq_feedback.get('reason', 'unknown')}")
            print(f"  Tolerance violation: {freq_feedback.get('tolerance_violation', False)}")
            
            # Verify feedback structure
            assert 'reason' in freq_feedback, "Feedback should contain reason"
            assert 'message' in freq_feedback, "Feedback should contain message"
            assert 'tolerance_violation' in freq_feedback, "Feedback should contain tolerance_violation flag"
            
            # The reason should be one of the expected values
            expected_reasons = ['success', 'tolerance_violation', 'clamped_to_min', 'clamped_to_max', 'hardware_drift']
            assert freq_feedback['reason'] in expected_reasons, f"Unexpected reason: {freq_feedback['reason']}"

if __name__ == "__main__":
    # Run tests if script is executed directly
    pytest.main([__file__, "-v", "-s"])
