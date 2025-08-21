#!/usr/bin/env python3
"""
Test file to verify ExperimentIterator bug fixes.

This tests the critical fixes we made to prevent crashes:
1. Proper initialization of _current_subexperiment_stage
2. Safe access to attributes in _estimate_progress
3. Robust loop_index property
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.experiment_iterator import ExperimentIterator
from src.core import Parameter


class MockExperiment:
    """Mock experiment class for testing."""
    
    def __init__(self, name="mock_experiment"):
        self.name = name
        self.settings = {}
        self.data = {}
        self.is_running = False
        self._abort = False
    
    def run(self):
        """Mock run method."""
        self.is_running = True
        return True
    
    def stop(self):
        """Mock stop method."""
        self.is_running = False


class TestExperimentIteratorSingle(ExperimentIterator):
    """Test subclass for single experiment testing."""
    
    _EXPERIMENTS = {
        'mock1': MockExperiment
    }
    
    _DEFAULT_SETTINGS = [
        Parameter('experiment_order', {'mock1': 1}),
        Parameter('experiment_execution_freq', {'mock1': 1}),
        Parameter('num_loops', 5, int, 'Number of loops'),
        Parameter('run_all_first', True, bool, 'Run all first')
    ]
    
    _DEVICES = {}


class TestExperimentIteratorDouble(ExperimentIterator):
    """Test subclass for two experiments testing."""
    
    _EXPERIMENTS = {
        'mock1': MockExperiment,
        'mock2': MockExperiment
    }
    
    _DEFAULT_SETTINGS = [
        Parameter('experiment_order', {'mock1': 1, 'mock2': 2}),
        Parameter('experiment_execution_freq', {'mock1': 1, 'mock2': 1}),
        Parameter('num_loops', 5, int, 'Number of loops'),
        Parameter('run_all_first', True, bool, 'Run all first')
    ]
    
    _DEVICES = {}


class TestExperimentIteratorFixes:
    """Test class for ExperimentIterator bug fixes."""
    
    def test_proper_initialization(self):
        """Test that _current_subexperiment_stage is properly initialized."""
        # Create a simple iterator with mock experiments
        experiments = {'mock1': MockExperiment('mock1'), 'mock2': MockExperiment('mock2')}
        settings = {
            'experiment_order': {'mock1': 1, 'mock2': 2},
            'experiment_execution_freq': {'mock1': 1, 'mock2': 1},
            'iterator_type': 'Loop',
            'num_loops': 5
        }
        
        # Create iterator instance
        iterator = TestExperimentIteratorDouble(experiments, settings=settings)
        
        # Check that _current_subexperiment_stage is properly initialized
        assert hasattr(iterator, '_current_subexperiment_stage')
        assert iterator._current_subexperiment_stage is not None
        assert 'current_subexperiment' in iterator._current_subexperiment_stage
        assert 'subexperiment_exec_duration' in iterator._current_subexperiment_stage
        assert 'subexperiment_exec_count' in iterator._current_subexperiment_stage
        
        print("✅ _current_subexperiment_stage properly initialized")
    
    def test_safe_loop_index_access(self):
        """Test that loop_index property handles missing data safely."""
        experiments = {'mock1': MockExperiment('mock1')}
        settings = {
            'experiment_order': {'mock1': 1},
            'experiment_execution_freq': {'mock1': 1},
            'iterator_type': 'Loop',
            'num_loops': 3
        }
        
        iterator = TestExperimentIteratorSingle(experiments, settings=settings)
        
        # Test that loop_index doesn't crash
        try:
            loop_index = iterator.loop_index
            assert isinstance(loop_index, int)
            assert loop_index >= 1  # Should return at least 1
            print(f"✅ loop_index safely accessed: {loop_index}")
        except Exception as e:
            pytest.fail(f"loop_index access failed: {e}")
    
    def test_safe_progress_estimation(self):
        """Test that _estimate_progress handles missing data safely."""
        experiments = {'mock1': MockExperiment('mock1')}
        settings = {
            'experiment_order': {'mock1': 1},
            'experiment_execution_freq': {'mock1': 1},
            'iterator_type': 'Loop',
            'num_loops': 2
        }
        
        iterator = TestExperimentIteratorSingle(experiments, settings=settings)
        
        # Test that _estimate_progress doesn't crash
        try:
            progress = iterator._estimate_progress()
            assert isinstance(progress, (int, float))
            assert 0 <= progress <= 100
            print(f"✅ Progress estimation safe: {progress}%")
        except Exception as e:
            pytest.fail(f"Progress estimation failed: {e}")
    
    def test_sweep_iterator_initialization(self):
        """Test that sweep iterator initializes properly."""
        experiments = {'mock1': MockExperiment('mock1')}
        settings = {
            'experiment_order': {'mock1': 1},
            'experiment_execution_freq': {'mock1': 1},
            'iterator_type': 'Parameter Sweep',
            'sweep_param': 'mock1.some_param',
            'sweep_range': {
                'min_value': 0,
                'max_value': 10,
                'N/value_step': 5,
                'randomize': False
            },
            'stepping_mode': 'N'
        }
        
        iterator = TestExperimentIteratorSingle(experiments, settings=settings)
        
        # Check iterator type detection
        assert iterator.iterator_type == 'sweep'
        
        # Check that data structures are initialized
        assert hasattr(iterator, '_current_subexperiment_stage')
        assert iterator._current_subexperiment_stage is not None
        
        print("✅ Sweep iterator properly initialized")
    
    def test_iterator_depth_detection(self):
        """Test that iterator depth detection works correctly."""
        experiments = {'mock1': MockExperiment('mock1')}
        settings = {
            'experiment_order': {'mock1': 1},
            'experiment_execution_freq': {'mock1': 1},
            'iterator_type': 'Loop',
            'num_loops': 1
        }
        
        iterator = TestExperimentIteratorSingle(experiments, settings=settings)
        
        # Check iterator level detection
        assert hasattr(iterator, 'iterator_level')
        assert isinstance(iterator.iterator_level, int)
        assert iterator.iterator_level >= 1
        
        print(f"✅ Iterator level detected: {iterator.iterator_level}")
    
    def test_abort_handling(self):
        """Test that abort functionality works without crashing."""
        experiments = {'mock1': MockExperiment('mock1')}
        settings = {
            'experiment_order': {'mock1': 1},
            'experiment_execution_freq': {'mock1': 1},
            'iterator_type': 'Loop',
            'num_loops': 10
        }
        
        iterator = TestExperimentIteratorSingle(experiments, settings=settings)
        
        # Test abort functionality
        try:
            iterator._abort = True
            iterator.skip_next()
            print("✅ Abort functionality works without crashing")
        except Exception as e:
            pytest.fail(f"Abort functionality failed: {e}")


def test_dynamic_class_creation():
    """Test that dynamic experiment iterator classes can be created."""
    from src.core.experiment_iterator import ExperimentIterator
    
    # Test configuration for dynamic class creation
    experiment_information = {
        'name': 'TestIterator',
        'class': 'ExperimentIterator',
        'package': 'src.core',  # Use correct package
        'experiments': {},
        'settings': {
            'experiment_order': {},
            'experiment_execution_freq': {},
            'iterator_type': 'Loop',
            'num_loops': 5
        }
    }
    
    try:
        # This should not crash with our fixes
        result, _ = ExperimentIterator.create_dynamic_experiment_class(
            experiment_information, verbose=False
        )
        
        assert 'class' in result
        print(f"✅ Dynamic class creation successful: {result['class']}")
        
    except Exception as e:
        pytest.fail(f"Dynamic class creation failed: {e}")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
