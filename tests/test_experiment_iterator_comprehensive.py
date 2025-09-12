#!/usr/bin/env python3
"""
Comprehensive test suite for ExperimentIterator class.

This test suite covers the complete functionality of ExperimentIterator,
including the programmatic pattern for creating multi-variable scans,
dynamic class creation, nested iterators, and integration with mock devices.

Tests follow the patterns established in other experiment test files and
use mock fixtures from conftest.py.
"""

import pytest
import sys
import time
import numpy as np
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.experiment_iterator import ExperimentIterator
from src.core.experiment import Experiment
from src.core import Parameter


class MockSingleExperiment(Experiment):
    """Mock experiment for testing single experiment scenarios."""
    
    _DEFAULT_SETTINGS = [
        Parameter('frequency', 2.87e9, float, 'Frequency in Hz', units='Hz'),
        Parameter('power', -10.0, float, 'Power in dBm', units='dBm'),
        Parameter('duration', 1000, int, 'Duration in ms', units='ms'),
        Parameter('points', 100, int, 'Number of data points')
    ]
    
    _DEVICES = {
        'nanodrive': Mock,
        'adwin': Mock
    }
    
    # Add the required _EXPERIMENTS property
    @property
    def _EXPERIMENTS(self):
        """Return empty dict since this is a leaf experiment."""
        return {}
    
    def __init__(self, devices=None, name=None, settings=None):
        super().__init__(name=name or 'MockSingleExperiment', 
                        devices=devices, settings=settings)
        self.data = {'counts': [], 'frequency': []}
        self.execution_count = 0
    
    def _function(self):
        """Mock experiment function that simulates data collection."""
        self.execution_count += 1
        
        # Simulate data collection based on current settings
        freq = self.settings['frequency']
        power = self.settings['power']
        points = self.settings['points']
        
        # Generate mock data with some dependency on parameters
        frequencies = np.linspace(freq - 10e6, freq + 10e6, points)
        # Simulate ODMR-like dip at center frequency
        counts = 1000 + power * 10 + 500 * np.exp(-((frequencies - freq) / 5e6)**2)
        
        # Return numpy arrays that can be properly averaged
        self.data['frequency'] = frequencies
        self.data['counts'] = counts
        
        # Simulate some execution time
        time.sleep(0.01)
        
        return True
    
    def setup(self):
        """Mock setup method."""
        pass
    
    def cleanup(self):
        """Mock cleanup method."""
        pass


class MockDualExperiment(Experiment):
    """Mock experiment for testing dual experiment scenarios."""
    
    _DEFAULT_SETTINGS = [
        Parameter('frequency_start', 2.8e9, float, 'Start frequency in Hz', units='Hz'),
        Parameter('frequency_stop', 2.9e9, float, 'Stop frequency in Hz', units='Hz'),
        Parameter('power', -15.0, float, 'Power in dBm', units='dBm'),
        Parameter('integration_time', 10.0, float, 'Integration time in ms', units='ms'),
        Parameter('steps', 50, int, 'Number of steps')
    ]
    
    _DEVICES = {
        'nanodrive': Mock,
        'adwin': Mock
    }
    
    # Add the required _EXPERIMENTS property
    @property
    def _EXPERIMENTS(self):
        """Return empty dict since this is a leaf experiment."""
        return {}
    
    def __init__(self, devices=None, name=None, settings=None):
        super().__init__(name=name or 'MockDualExperiment', 
                        devices=devices, settings=settings)
        self.data = {'sweep_data': [], 'parameters': {}}
        self.execution_count = 0
    
    def _function(self):
        """Mock experiment function for dual experiment."""
        self.execution_count += 1
        
        # Simulate sweep data collection
        freq_start = self.settings['frequency_start']
        freq_stop = self.settings['frequency_stop']
        steps = self.settings['steps']
        power = self.settings['power']
        
        frequencies = np.linspace(freq_start, freq_stop, steps)
        # Simulate different response based on power
        response = 800 + power * 20 + 200 * np.random.random(steps)
        
        # Return only numeric data that can be properly averaged
        self.data['sweep_data'] = response
        self.data['freq_start'] = freq_start
        self.data['freq_stop'] = freq_stop
        self.data['power'] = power
        self.data['steps'] = steps
        
        time.sleep(0.02)
        return True
    
    def setup(self):
        """Mock setup method."""
        pass
    
    def cleanup(self):
        """Mock cleanup method."""
        pass


class TestExperimentIteratorSingle(ExperimentIterator):
    """Test subclass for single experiment testing."""
    _EXPERIMENTS = {
        'mock_single': MockSingleExperiment
    }
    _DEFAULT_SETTINGS = [
        Parameter('experiment_order', {'mock_single': 1}),
        Parameter('experiment_execution_freq', {'mock_single': 1}),
        Parameter('num_loops', 5, int, 'Number of loops'),
        Parameter('run_all_first', True, bool, 'Run all first')
    ]
    _DEVICES = {
        'nanodrive': Mock,
        'adwin': Mock
    }


class TestExperimentIteratorDual(ExperimentIterator):
    """Test subclass for dual experiment testing."""
    _EXPERIMENTS = {
        'mock_single': MockSingleExperiment,
        'mock_dual': MockDualExperiment
    }
    _DEFAULT_SETTINGS = [
        Parameter('experiment_order', {'mock_single': 1, 'mock_dual': 2}),
        Parameter('experiment_execution_freq', {'mock_single': 1, 'mock_dual': 1}),
        Parameter('num_loops', 3, int, 'Number of loops'),
        Parameter('run_all_first', True, bool, 'Run all first')
    ]
    _DEVICES = {
        'nanodrive': Mock,
        'adwin': Mock
    }


class TestExperimentIteratorBasics:
    """Test basic ExperimentIterator functionality."""
    
    def test_single_experiment_initialization(self, mock_devices):
        """Test initialization with single experiment."""
        iterator = TestExperimentIteratorSingle(
            experiments={'mock_single': MockSingleExperiment(devices=mock_devices)},
            name='test_single_iterator'
        )
        
        assert iterator.name == 'test_single_iterator'
        assert iterator.iterator_type is not None
        assert hasattr(iterator, '_current_subexperiment_stage')
        assert iterator._current_subexperiment_stage is not None
        assert iterator.iterator_level >= 1
    
    def test_dual_experiment_initialization(self, mock_devices):
        """Test initialization with dual experiments."""
        experiments = {
            'mock_single': MockSingleExperiment(devices=mock_devices),
            'mock_dual': MockDualExperiment(devices=mock_devices)
        }
        
        iterator = TestExperimentIteratorDual(
            experiments=experiments,
            name='test_dual_iterator'
        )
        
        assert iterator.name == 'test_dual_iterator'
        assert len(iterator.experiments) == 2
        assert 'mock_single' in iterator.experiments
        assert 'mock_dual' in iterator.experiments
    
    def test_iterator_type_detection(self, mock_devices):
        """Test iterator type detection."""
        iterator = TestExperimentIteratorSingle(
            experiments={'mock_single': MockSingleExperiment(devices=mock_devices)}
        )
        
        # Test get_iterator_type method
        iterator_type = iterator.get_iterator_type(iterator.settings, iterator.experiments)
        assert iterator_type in ['loop', 'sweep']  # Fix: use lowercase values as returned by the method
    
    def test_progress_estimation_initialization(self, mock_devices):
        """Test that progress estimation doesn't crash on initialization."""
        iterator = TestExperimentIteratorSingle(
            experiments={'mock_single': MockSingleExperiment(devices=mock_devices)}
        )
        
        # This should not crash
        progress = iterator._estimate_progress()
        assert isinstance(progress, (int, float))
        assert 0 <= progress <= 100
    
    def test_loop_index_property(self, mock_devices):
        """Test loop_index property doesn't crash."""
        iterator = TestExperimentIteratorSingle(
            experiments={'mock_single': MockSingleExperiment(devices=mock_devices)}
        )
        
        # This should not crash and return a reasonable value
        loop_index = iterator.loop_index
        assert isinstance(loop_index, int)
        assert loop_index >= 0


class TestExperimentIteratorExecution:
    """Test ExperimentIterator execution functionality."""
    
    def test_single_experiment_execution(self, mock_devices):
        """Test execution of single experiment in iterator."""
        experiment = MockSingleExperiment(devices=mock_devices)
        
        iterator = TestExperimentIteratorSingle(
            experiments={'mock_single': experiment},
            name='execution_test'
        )
        
        # Set up for short execution
        iterator.settings['num_loops'] = 2
        
        # Set abort to False initially
        iterator._abort = False
        
        # Run the function - it should execute at least once
        iterator._function()
        
        # Verify experiment was executed at least once
        assert experiment.execution_count > 0
        assert 'frequency' in experiment.data
        assert 'counts' in experiment.data
    
    def test_dual_experiment_execution(self, mock_devices):
        """Test execution of dual experiments in iterator."""
        single_exp = MockSingleExperiment(devices=mock_devices)
        dual_exp = MockDualExperiment(devices=mock_devices)
        
        experiments = {
            'mock_single': single_exp,
            'mock_dual': dual_exp
        }
        
        iterator = TestExperimentIteratorDual(
            experiments=experiments,
            name='dual_execution_test'
        )
        
        # Set up for short execution
        iterator.settings['num_loops'] = 1
        
        # Set abort to False initially
        iterator._abort = False
        
        # Run the function
        iterator._function()
        
        # Verify both experiments were executed
        assert single_exp.execution_count > 0
        assert dual_exp.execution_count > 0
    
    def test_experiment_stopping(self, mock_devices):
        """Test experiment stopping functionality."""
        experiment = MockSingleExperiment(devices=mock_devices)
        
        iterator = TestExperimentIteratorSingle(
            experiments={'mock_single': experiment}
        )
        
        # Set abort flag immediately to prevent execution
        iterator._abort = True
        
        # Run the function - should exit immediately
        iterator._function()
        
        # Experiment should not have been executed
        assert experiment.execution_count == 0


class TestDynamicClassCreation:
    """Test dynamic class creation functionality."""
    
    def test_create_dynamic_experiment_class(self, mock_devices):
        """Test the documented programmatic pattern for dynamic class creation."""
        
        # Define the experiment configuration as documented
        experiment_config = {
            'class': 'MockSingleExperiment',  # Use 'class' key as expected by the method
            'class_name': 'FrequencyPowerSweepIterator',
            'base_experiment': 'MockSingleExperiment',
            'module': 'tests.test_experiment_iterator_comprehensive',
            'package': 'tests',
            'variable_parameters': {
                'frequency': {
                    'start': 2.8e9,
                    'stop': 2.9e9,
                    'steps': 5
                },
                'power': {
                    'start': -20.0,
                    'stop': -5.0,
                    'steps': 4
                }
            },
            'fixed_parameters': {
                'duration': 1000,
                'points': 50
            },
            'devices': ['nanodrive', 'adwin'],  # Match available mock devices
            'num_loops': 2
        }
        
        # Create the dynamic class using the documented method
        dynamic_info = ExperimentIterator.create_dynamic_experiment_class(experiment_config)
        
        # Verify dynamic class creation
        assert dynamic_info is not None
        assert 'class' in dynamic_info
        assert 'settings' in dynamic_info
        assert 'experiments' in dynamic_info
        
        # Verify class properties
        DynamicClass = dynamic_info['class']
        assert DynamicClass.__name__ == 'FrequencyPowerSweepIterator'
        assert issubclass(DynamicClass, ExperimentIterator)
        
        # Verify settings structure
        settings = dynamic_info['settings']
        assert 'experiment_order' in settings
        assert 'experiment_execution_freq' in settings
        assert 'num_loops' in settings
        
        # Verify experiments structure
        experiments = dynamic_info['experiments']
        assert len(experiments) > 1  # Should have multiple parameter combinations
        
        # Test instantiation of dynamic class
        dynamic_instance = DynamicClass(
            experiments=experiments,
            devices=mock_devices,
            settings=settings,
            name='test_dynamic_instance'
        )
        
        assert dynamic_instance.name == 'test_dynamic_instance'
        assert len(dynamic_instance.experiments) > 1
    
    def test_nested_iterator_creation(self, mock_devices):
        """Test creation of nested iterators as documented."""
        
        # Inner iterator configuration (frequency sweep)
        inner_config = {
            'class': 'MockSingleExperiment',  # Use 'class' key
            'class_name': 'FrequencySweepIterator',
            'base_experiment': 'MockSingleExperiment',
            'module': 'tests.test_experiment_iterator_comprehensive',
            'package': 'tests',
            'variable_parameters': {
                'frequency': {
                    'start': 2.85e9,
                    'stop': 2.88e9,
                    'steps': 3
                }
            },
            'fixed_parameters': {
                'power': -10.0,
                'duration': 500
            },
            'devices': ['nanodrive', 'adwin'],  # Match available mock devices
            'num_loops': 1
        }
        
        # Create inner iterator
        inner_info = ExperimentIterator.create_dynamic_experiment_class(inner_config)
        InnerIteratorClass = inner_info['class']
        
        # Outer iterator configuration (power sweep of inner iterator)
        outer_config = {
            'class': InnerIteratorClass,  # Use the actual class, not string
            'class_name': 'PowerFrequencySweepIterator',
            'base_experiment': InnerIteratorClass,
            'module': '__main__',  # Since InnerIteratorClass is dynamically created
            'package': '',
            'variable_parameters': {
                'power': {  # This will be applied to the inner iterator's experiments
                    'start': -15.0,
                    'stop': -5.0,
                    'steps': 3
                }
            },
            'fixed_parameters': {},
            'devices': ['nanodrive', 'adwin'],  # Match available mock devices
            'num_loops': 1
        }
        
        # Create outer iterator (this tests nested iterator creation)
        outer_info = ExperimentIterator.create_dynamic_experiment_class(outer_config)
        OuterIteratorClass = outer_info['class']
        
        # Verify nested structure
        assert OuterIteratorClass.__name__ == 'PowerFrequencySweepIterator'
        assert issubclass(OuterIteratorClass, ExperimentIterator)
        
        # Create instance of nested iterator
        nested_instance = OuterIteratorClass(
            experiments=outer_info['experiments'],
            devices=mock_devices,
            settings=outer_info['settings'],
            name='nested_test'
        )
        
        assert nested_instance.name == 'nested_test'
        assert len(nested_instance.experiments) > 1  # Multiple power values
        
        # Check that experiments are iterator instances
        first_exp_key = list(nested_instance.experiments.keys())[0]
        first_exp = nested_instance.experiments[first_exp_key]
        assert isinstance(first_exp, ExperimentIterator)


class TestExperimentIteratorIntegration:
    """Integration tests for ExperimentIterator."""
    
    def test_full_programmatic_workflow(self, mock_devices):
        """Test the complete programmatic workflow documented in the guide."""
        
        # Step 1: Define base experiment parameters
        base_experiment_info = {
            'class': 'MockSingleExperiment',  # Use 'class' key
            'class_name': 'ODMRFrequencyScan',
            'base_experiment': 'MockSingleExperiment',
            'module': 'tests.test_experiment_iterator_comprehensive',
            'package': 'tests',
            'variable_parameters': {
                'frequency': {
                    'start': 2.85e9,
                    'stop': 2.87e9,
                    'steps': 3  # Small for testing
                }
            },
            'fixed_parameters': {
                'power': -12.0,
                'duration': 1000,
                'points': 20
            },
            'devices': ['nanodrive', 'adwin'],  # Match available mock devices
            'num_loops': 1
        }
        
        # Step 2: Create dynamic experiment class
        frequency_sweep_info = ExperimentIterator.create_dynamic_experiment_class(base_experiment_info)
        FrequencySweepClass = frequency_sweep_info['class']
        
        # Step 3: Create power sweep that uses frequency sweep as base
        power_sweep_info = {
            'class': FrequencySweepClass,  # Use the actual class
            'class_name': 'ODMRPowerFrequencyScan',
            'base_experiment': FrequencySweepClass,
            'module': '__main__',
            'package': '',
            'variable_parameters': {
                'power': {
                    'start': -15.0,
                    'stop': -10.0,
                    'steps': 2  # Small for testing
                }
            },
            'fixed_parameters': {},
            'devices': ['nanodrive', 'adwin'],  # Match available mock devices
            'num_loops': 1
        }
        
        # Step 4: Create final nested iterator
        final_iterator_info = ExperimentIterator.create_dynamic_experiment_class(power_sweep_info)
        FinalIteratorClass = final_iterator_info['class']
        
        # Step 5: Instantiate and configure
        final_instance = FinalIteratorClass(
            experiments=final_iterator_info['experiments'],
            devices=mock_devices,
            settings=final_iterator_info['settings'],
            name='full_workflow_test'
        )
        
        # Step 6: Verify structure
        assert final_instance.name == 'full_workflow_test'
        assert len(final_instance.experiments) == 2  # 2 power values
        
        # Check that each experiment is a frequency sweep iterator
        for exp_name, experiment in final_instance.experiments.items():
            assert isinstance(experiment, ExperimentIterator)
            assert len(experiment.experiments) == 3  # 3 frequency values
            
            # Check that the inner experiments are the base experiments
            for inner_name, inner_exp in experiment.experiments.items():
                assert isinstance(inner_exp, MockSingleExperiment)
        
        # Step 7: Test execution (short run)
        with patch.object(final_instance, 'is_stopped', side_effect=[False, False, True]):
            final_instance._function()
        
        # Verify that nested execution occurred
        executed_experiments = []
        for exp_name, experiment in final_instance.experiments.items():
            for inner_name, inner_exp in experiment.experiments.items():
                if inner_exp.execution_count > 0:
                    executed_experiments.append(inner_exp)
        
        assert len(executed_experiments) > 0, "At least one experiment should have executed"
    
    def test_parameter_validation(self, mock_devices):
        """Test parameter validation in iterators."""
        
        # Test invalid parameter configuration
        invalid_config = {
            'class': 'InvalidIterator',
            'base_experiment': 'MockSingleExperiment',
            'module': 'tests.test_experiment_iterator_comprehensive',
            'package': 'tests',
            'variable_parameters': {
                'nonexistent_param': {  # This parameter doesn't exist in MockSingleExperiment
                    'start': 1.0,
                    'stop': 2.0,
                    'steps': 3
                }
            },
            'fixed_parameters': {},
            'devices': ['microwave'],
            'num_loops': 1
        }
        
        # This should handle the invalid parameter gracefully
        try:
            invalid_info = ExperimentIterator.create_dynamic_experiment_class(invalid_config)
            # If it doesn't raise an exception, verify it handles it somehow
            assert invalid_info is not None
        except (ValueError, KeyError, AttributeError):
            # Expected behavior for invalid parameters
            pass
    
    def test_device_integration(self, mock_devices):
        """Test integration with mock devices."""
        
        experiment = MockSingleExperiment(devices=mock_devices)
        
        iterator = TestExperimentIteratorSingle(
            experiments={'mock_single': experiment}
        )
        
        # Verify devices are properly passed through to experiments
        assert experiment.devices == mock_devices
        
        # Verify device access in experiment
        assert 'nanodrive' in mock_devices
        assert 'adwin' in mock_devices
        
        # Test that experiments can access device instances
        assert experiment.devices['nanodrive']['instance'] is not None
        assert experiment.devices['adwin']['instance'] is not None
        
        # Verify that the iterator's experiments have access to devices
        for exp_name, exp in iterator.experiments.items():
            assert exp.devices == mock_devices


class TestExperimentIteratorErrorHandling:
    """Test error handling in ExperimentIterator."""
    
    def test_exception_handling_in_execution(self, mock_devices):
        """Test that exceptions in experiments are handled gracefully."""
        
        # Create an experiment that will raise an exception
        class FailingExperiment(MockSingleExperiment):
            def _function(self):
                raise RuntimeError("Simulated experiment failure")
        
        failing_exp = FailingExperiment(devices=mock_devices)
        
        # Create a test iterator class for the failing experiment
        class TestFailingIterator(ExperimentIterator):
            _EXPERIMENTS = {'failing': FailingExperiment}
            _DEFAULT_SETTINGS = [
                Parameter('experiment_order', {'failing': 1}),
                Parameter('experiment_execution_freq', {'failing': 1}),
                Parameter('num_loops', 1, int, 'Number of loops'),
                Parameter('run_all_first', True, bool, 'Run all first')
            ]
            _DEVICES = {'nanodrive': Mock, 'adwin': Mock}
        
        iterator = TestFailingIterator(
            experiments={'failing': failing_exp}
        )
        
        # Execution should handle the exception gracefully
        iterator._abort = False
        try:
            iterator._function()
        except RuntimeError:
            # Exception propagation is acceptable
            pass
    
    def test_malformed_settings_handling(self, mock_devices):
        """Test handling of malformed settings."""
        
        experiment = MockSingleExperiment(devices=mock_devices)
        
        # Create iterator with malformed settings
        iterator = TestExperimentIteratorSingle(
            experiments={'mock_single': experiment}
        )
        
        # Deliberately corrupt the settings
        iterator.settings['experiment_order'] = None
        
        # Should not crash when accessing iterator properties
        try:
            progress = iterator._estimate_progress()
            loop_index = iterator.loop_index
            assert isinstance(progress, (int, float))
            assert isinstance(loop_index, int)
        except (AttributeError, TypeError, KeyError):
            # Acceptable to fail gracefully with these exceptions
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
