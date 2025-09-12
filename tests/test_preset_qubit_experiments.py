"""
Tests for the preset experiments module.

This module tests the preset experiment configurations for common qubit experiments
like ODMR, Rabi oscillations, Spin Echo, and CPMG sequences.
"""

import pytest
from src.Model.preset_qubit_experiments import PresetExperiment, PresetQubitExperiments


class TestPresetExperiment:
    """Test the PresetExperiment dataclass."""
    
    def test_valid_preset_experiment(self):
        """Test creating a valid preset experiment."""
        experiment = PresetExperiment(
            name="test_experiment",
            description="A test experiment",
            parameters={"param1": 1.0, "param2": "test"},
            sequence_template="# Test sequence\npulse1\npulse2",
            metadata={"category": "test"}
        )
        
        assert experiment.name == "test_experiment"
        assert experiment.description == "A test experiment"
        assert experiment.parameters == {"param1": 1.0, "param2": "test"}
        assert experiment.sequence_template == "# Test sequence\npulse1\npulse2"
        assert experiment.metadata == {"category": "test"}
    
    def test_preset_experiment_defaults(self):
        """Test creating a preset experiment with default values."""
        experiment = PresetExperiment(
            name="test_experiment",
            description="A test experiment"
        )
        
        assert experiment.parameters == {}
        assert experiment.sequence_template == ""
        assert experiment.metadata == {}


class TestPresetQubitExperiments:
    """Test the PresetQubitExperiments class."""
    
    def test_initialization(self):
        """Test that PresetQubitExperiments initializes correctly."""
        presets = PresetQubitExperiments()
        assert hasattr(presets, 'experiments')
        assert isinstance(presets.experiments, dict)
        assert len(presets.experiments) > 0
    
    def test_available_experiments(self):
        """Test that all expected preset qubit experiments are available."""
        presets = PresetQubitExperiments()
        expected_experiments = ["odmr", "rabi", "spin_echo", "cpmg", "ramsey"]
        
        for exp_name in expected_experiments:
            assert exp_name in presets.experiments
            assert isinstance(presets.experiments[exp_name], PresetExperiment)
    
    def test_get_experiment_valid(self):
        """Test getting a valid preset qubit experiment."""
        presets = PresetQubitExperiments()
        experiment = presets.get_experiment("odmr")
        
        assert isinstance(experiment, PresetExperiment)
        assert experiment.name == "odmr"
        assert "microwave_frequency" in experiment.parameters
    
    def test_get_experiment_invalid(self):
        """Test that getting an invalid qubit experiment raises ValueError."""
        presets = PresetQubitExperiments()
        
        with pytest.raises(ValueError, match="Preset experiment 'invalid_experiment' not found"):
            presets.get_experiment("invalid_experiment")
    
    def test_list_experiments(self):
        """Test listing available qubit experiments."""
        presets = PresetQubitExperiments()
        experiment_list = presets.list_experiments()
        
        assert isinstance(experiment_list, list)
        assert len(experiment_list) > 0
        assert all(isinstance(name, str) for name in experiment_list)
        assert "odmr" in experiment_list
        assert "rabi" in experiment_list
        assert "spin_echo" in experiment_list
    
    def test_get_experiment_parameters(self):
        """Test getting qubit experiment parameters."""
        presets = PresetQubitExperiments()
        params = presets.get_experiment_parameters("odmr")
        
        assert isinstance(params, dict)
        assert "microwave_frequency" in params
        assert "sweep_range" in params
        assert "sweep_points" in params
        assert "laser_pulse_duration" in params
        assert "readout_delay" in params
        assert "microwave_power" in params
        assert "laser_power" in params
        assert "channel" in params
        assert "pulse_shape" in params
    
    def test_customize_experiment(self):
        """Test customizing a qubit experiment with new parameters."""
        presets = PresetQubitExperiments()
        custom_experiment = presets.customize_experiment(
            "odmr",
            microwave_frequency=3.0e9,
            sweep_points=200
        )
        
        assert isinstance(custom_experiment, PresetExperiment)
        assert custom_experiment.name == "odmr_custom"
        assert custom_experiment.parameters["microwave_frequency"] == 3.0e9
        assert custom_experiment.parameters["sweep_points"] == 200
        
        # Original parameters should still be there
        assert "laser_pulse_duration" in custom_experiment.parameters
        assert "readout_delay" in custom_experiment.parameters
    
    def test_customize_experiment_preserves_original(self):
        """Test that customizing doesn't modify the original qubit experiment."""
        presets = PresetQubitExperiments()
        original_params = presets.get_experiment_parameters("odmr").copy()
        
        custom_experiment = presets.customize_experiment("odmr", microwave_frequency=3.0e9)
        
        # Original should be unchanged
        current_params = presets.get_experiment_parameters("odmr")
        assert current_params == original_params
        
        # Custom should have new values
        assert custom_experiment.parameters["microwave_frequency"] == 3.0e9


class TestODMRExperiment:
    """Test the ODMR preset experiment specifically."""
    
    def test_odmr_parameters(self):
        """Test ODMR qubit experiment parameters."""
        presets = PresetQubitExperiments()
        odmr = presets.get_experiment("odmr")
        
        assert odmr.description == "Optically Detected Magnetic Resonance (Qubit) - Microwave sweep with laser readout"
        assert odmr.parameters["microwave_frequency"] == 2.87e9  # 2.87 GHz
        assert odmr.parameters["sweep_range"] == [2.8e9, 2.9e9]  # 2.8-2.9 GHz
        assert odmr.parameters["sweep_points"] == 100
        assert odmr.parameters["laser_pulse_duration"] == 1e-6  # 1μs
        assert odmr.parameters["readout_delay"] == 100e-9  # 100ns
        assert odmr.parameters["microwave_power"] == 1.0  # 1V
        assert odmr.parameters["laser_power"] == 1.0  # 1V
        assert odmr.parameters["channel"] == 1
        assert odmr.parameters["pulse_shape"] == "gaussian"
    
    def test_odmr_sequence_template(self):
        """Test ODMR qubit sequence template."""
        presets = PresetQubitExperiments()
        odmr = presets.get_experiment("odmr")
        
        template = odmr.sequence_template
        assert "# ODMR Experiment Sequence" in template
        assert "microwave_pulse:" in template
        assert "laser_pulse:" in template
        assert "repeat {sweep_points} times" in template


class TestRabiExperiment:
    """Test the Rabi oscillations preset experiment."""
    
    def test_rabi_parameters(self):
        """Test Rabi qubit experiment parameters."""
        presets = PresetQubitExperiments()
        rabi = presets.get_experiment("rabi")
        
        assert rabi.description == "Rabi Oscillations (Qubit) - Variable pulse duration to measure Rabi frequency"
        assert rabi.parameters["pulse_duration_range"] == [10e-9, 1e-6]  # 10ns to 1μs
        assert rabi.parameters["pulse_duration_points"] == 50
        assert rabi.parameters["pulse_shape"] == "gaussian"
        assert rabi.parameters["pulse_amplitude"] == 1.0  # 1V
        assert rabi.parameters["repetition_rate"] == 1e3  # 1kHz
        assert rabi.parameters["channel"] == 1
        assert rabi.parameters["wait_time"] == 1e-3  # 1ms
    
    def test_rabi_sequence_template(self):
        """Test Rabi qubit sequence template."""
        presets = PresetQubitExperiments()
        rabi = presets.get_experiment("rabi")
        
        template = rabi.sequence_template
        assert "# Rabi Oscillations Sequence" in template
        assert "Variable pulse duration" in template
        assert "custom_pulse:" in template
        assert "repeat {pulse_duration_points} times" in template


class TestSpinEchoExperiment:
    """Test the Spin Echo preset experiment."""
    
    def test_spin_echo_parameters(self):
        """Test Spin Echo qubit experiment parameters."""
        presets = PresetQubitExperiments()
        spin_echo = presets.get_experiment("spin_echo")
        
        assert spin_echo.description == "Hahn Echo sequence for T2 measurement"
        assert spin_echo.parameters["echo_time"] == 10e-3  # 10ms
        assert spin_echo.parameters["pi_pulse_duration"] == 200e-9  # 200ns
        assert spin_echo.parameters["pi_2_pulse_duration"] == 100e-9  # 100ns
        assert spin_echo.parameters["pulse_shape"] == "gaussian"
        assert spin_echo.parameters["pulse_amplitude"] == 1.0  # 1V
        assert spin_echo.parameters["channel"] == 1
        assert spin_echo.parameters["repetition_rate"] == 1e3  # 1kHz
    
    def test_spin_echo_sequence_template(self):
        """Test Spin Echo qubit sequence template."""
        presets = PresetQubitExperiments()
        spin_echo = presets.get_experiment("spin_echo")
        
        template = spin_echo.sequence_template
        assert "# Spin Echo Sequence" in template
        assert "π/2 - τ - π - τ - π/2" in template
        assert "pi_2_pulse:" in template
        assert "pi_pulse:" in template


class TestCPMGExperiment:
    """Test the CPMG preset experiment."""
    
    def test_cpmg_parameters(self):
        """Test CPMG qubit experiment parameters."""
        presets = PresetQubitExperiments()
        cpmg = presets.get_experiment("cpmg")
        
        assert cpmg.description == "CPMG sequence - Multiple echo sequence for T2 measurement"
        assert cpmg.parameters["echo_time"] == 1e-3  # 1ms
        assert cpmg.parameters["num_echoes"] == 100
        assert cpmg.parameters["pi_pulse_duration"] == 200e-9  # 200ns
        assert cpmg.parameters["pi_2_pulse_duration"] == 100e-9  # 100ns
        assert cpmg.parameters["pulse_shape"] == "gaussian"
        assert cpmg.parameters["pulse_amplitude"] == 1.0  # 1V
        assert cpmg.parameters["channel"] == 1
        assert cpmg.parameters["repetition_rate"] == 1e3  # 1kHz
    
    def test_cpmg_sequence_template(self):
        """Test CPMG qubit sequence template."""
        presets = PresetQubitExperiments()
        cpmg = presets.get_experiment("cpmg")
        
        template = cpmg.sequence_template
        assert "# CPMG Sequence" in template
        assert "π/2 - τ - π - τ - π - τ - ... (multiple echoes)" in template
        assert "repeat {num_echoes} times:" in template


class TestRamseyExperiment:
    """Test the Ramsey interference preset experiment."""
    
    def test_ramsey_parameters(self):
        """Test Ramsey qubit experiment parameters."""
        presets = PresetQubitExperiments()
        ramsey = presets.get_experiment("ramsey")
        
        assert ramsey.description == "Ramsey Interference - Two π/2 pulses with variable delay"
        assert ramsey.parameters["delay_range"] == [100e-9, 10e-3]  # 100ns to 10ms
        assert ramsey.parameters["delay_points"] == 100
        assert ramsey.parameters["pi_2_pulse_duration"] == 100e-9  # 100ns
        assert ramsey.parameters["pulse_shape"] == "gaussian"
        assert ramsey.parameters["pulse_amplitude"] == 1.0  # 1V
        assert ramsey.parameters["channel"] == 1
        assert ramsey.parameters["repetition_rate"] == 1e3  # 1kHz
    
    def test_ramsey_sequence_template(self):
        """Test Ramsey qubit sequence template."""
        presets = PresetQubitExperiments()
        ramsey = presets.get_experiment("ramsey")
        
        template = ramsey.sequence_template
        assert "# Ramsey Interference Sequence" in template
        assert "π/2 - τ - π/2" in template
        assert "repeat {delay_points} times" in template


class TestExperimentHelp:
    """Test the experiment help functionality."""
    
    def test_get_experiment_help_all(self):
        """Test getting help for all experiments."""
        presets = PresetQubitExperiments()
        help_text = presets.get_experiment_help()
        
        assert "Available Preset Experiments:" in help_text
        assert "odmr:" in help_text
        assert "rabi:" in help_text
        assert "spin_echo:" in help_text
        assert "cpmg:" in help_text
        assert "ramsey:" in help_text
    
    def test_get_experiment_help_specific(self):
        """Test getting help for a specific experiment."""
        presets = PresetQubitExperiments()
        help_text = presets.get_experiment_help("odmr")
        
        assert "Experiment: odmr" in help_text
        assert "Description:" in help_text
        assert "Default Parameters:" in help_text
        assert "microwave_frequency:" in help_text
        assert "Sequence Template:" in help_text
        assert "# ODMR Experiment Sequence" in help_text
    
    def test_get_experiment_help_invalid(self):
        """Test getting help for an invalid experiment."""
        presets = PresetQubitExperiments()
        
        with pytest.raises(ValueError, match="Preset experiment 'invalid_experiment' not found"):
            presets.get_experiment_help("invalid_experiment")


class TestParameterValidation:
    """Test parameter validation and customization."""
    
    def test_parameter_types(self):
        """Test that parameters have correct types."""
        presets = PresetQubitExperiments()
        odmr = presets.get_experiment("odmr")
        
        # Check numeric parameters
        assert isinstance(odmr.parameters["microwave_frequency"], (int, float))
        assert isinstance(odmr.parameters["sweep_points"], int)
        assert isinstance(odmr.parameters["laser_pulse_duration"], (int, float))
        assert isinstance(odmr.parameters["readout_delay"], (int, float))
        assert isinstance(odmr.parameters["microwave_power"], (int, float))
        assert isinstance(odmr.parameters["laser_power"], (int, float))
        assert isinstance(odmr.parameters["channel"], int)
        
        # Check string parameters
        assert isinstance(odmr.parameters["pulse_shape"], str)
        
        # Check list parameters
        assert isinstance(odmr.parameters["sweep_range"], list)
        assert len(odmr.parameters["sweep_range"]) == 2
    
    def test_parameter_ranges(self):
        """Test that parameters have reasonable ranges."""
        presets = PresetQubitExperiments()
        
        # Test ODMR parameters
        odmr = presets.get_experiment("odmr")
        assert 1e9 <= odmr.parameters["microwave_frequency"] <= 10e9  # 1-10 GHz
        assert odmr.parameters["sweep_points"] > 0
        assert odmr.parameters["laser_pulse_duration"] > 0
        assert odmr.parameters["readout_delay"] > 0
        assert odmr.parameters["channel"] in [1, 2]
        
        # Test Rabi parameters
        rabi = presets.get_experiment("rabi")
        duration_range = rabi.parameters["pulse_duration_range"]
        assert duration_range[0] > 0 and duration_range[1] > duration_range[0]
        assert rabi.parameters["pulse_duration_points"] > 0
        
        # Test Spin Echo parameters
        spin_echo = presets.get_experiment("spin_echo")
        assert spin_echo.parameters["echo_time"] > 0
        assert spin_echo.parameters["pi_pulse_duration"] > 0
        assert spin_echo.parameters["pi_2_pulse_duration"] > 0
