"""
Preset Qubit Experiments Module

This module defines preset experiment configurations specifically for qubit experiments
like ODMR, Rabi oscillations, Spin Echo, and CPMG sequences.

Note: This module is specifically for qubit experiments. For other experiment types
(confocal, spectrometer, etc.), see their respective preset modules.
"""

from __future__ import annotations
from typing import Dict, Any, List
from dataclasses import dataclass, field


@dataclass
class PresetExperiment:
    """Base class for preset experiment definitions."""

    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    sequence_template: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class PresetQubitExperiments:
    """Collection of preset qubit experiment definitions."""
    
    def __init__(self):
        """Initialize with all available preset qubit experiments."""
        self.experiments = self._load_preset_qubit_experiments()
    
    def get_experiment(self, name: str) -> PresetExperiment:
        """
        Get a preset experiment by name.
        
        Args:
            name: Name of the preset experiment
            
        Returns:
            PresetExperiment object
            
        Raises:
            ValueError: If experiment name not found
        """
        if name not in self.experiments:
            raise ValueError(f"Preset experiment '{name}' not found")
        return self.experiments[name]
    
    def list_experiments(self) -> List[str]:
        """Get list of available preset experiment names."""
        return list(self.experiments.keys())
    
    def get_experiment_parameters(self, name: str) -> Dict[str, Any]:
        """
        Get default parameters for a preset experiment.
        
        Args:
            name: Name of the preset experiment
            
        Returns:
            Dictionary of default parameters
        """
        experiment = self.get_experiment(name)
        return experiment.parameters.copy()
    
    def customize_experiment(self, name: str, **custom_parameters) -> PresetExperiment:
        """
        Get a preset experiment with custom parameters.
        
        Args:
            name: Name of the preset experiment
            **custom_parameters: Parameters to override defaults
            
        Returns:
            PresetExperiment with custom parameters
        """
        experiment = self.get_experiment(name)
        custom_experiment = PresetExperiment(
            name=f"{experiment.name}_custom",
            description=experiment.description,
            parameters={**experiment.parameters, **custom_parameters},
            sequence_template=experiment.sequence_template,
            metadata=experiment.metadata
        )
        return custom_experiment
    
    def _load_preset_qubit_experiments(self) -> Dict[str, PresetExperiment]:
        """
        Load all preset qubit experiment definitions.
        
        Returns:
            Dictionary mapping experiment names to PresetExperiment objects
        """
        experiments = {}
        
        # ODMR Experiment (Qubit)
        experiments["odmr"] = PresetExperiment(
            name="odmr",
            description="Optically Detected Magnetic Resonance (Qubit) - Microwave sweep with laser readout",
            parameters={
                "microwave_frequency": 2.87e9,  # Hz
                "sweep_range": [2.8e9, 2.9e9],  # Hz
                "sweep_points": 100,
                "laser_pulse_duration": 1e-6,  # 1μs
                "readout_delay": 100e-9,  # 100ns
                "microwave_power": 1.0,  # V
                "laser_power": 1.0,  # V
                "channel": 1,
                "pulse_shape": "gaussian"
            },
            sequence_template="""
                # ODMR Experiment Sequence
                # Microwave sweep with laser readout
                microwave_pulse: {pulse_shape} shape, {microwave_power}V, {microwave_frequency}Hz
                wait {readout_delay}
                laser_pulse: square shape, {laser_power}V, {laser_pulse_duration} duration
                wait 1ms
                repeat {sweep_points} times
            """
        )
        
        # Rabi Oscillations (Qubit)
        experiments["rabi"] = PresetExperiment(
            name="rabi",
            description="Rabi Oscillations (Qubit) - Variable pulse duration to measure Rabi frequency",
            parameters={
                "pulse_duration_range": [10e-9, 1e-6],  # 10ns to 1μs
                "pulse_duration_points": 50,
                "pulse_shape": "gaussian",
                "pulse_amplitude": 1.0,  # V
                "repetition_rate": 1e3,  # 1kHz
                "channel": 1,
                "wait_time": 1e-3  # 1ms
            },
            sequence_template="""
                # Rabi Oscillations Sequence
                # Variable pulse duration
                custom_pulse: {pulse_shape} shape, {pulse_amplitude}V, variable duration
                wait {wait_time}
                repeat {pulse_duration_points} times
            """
        )
        
        # Spin Echo (Hahn Echo)
        experiments["spin_echo"] = PresetExperiment(
            name="spin_echo",
            description="Hahn Echo sequence for T2 measurement",
            parameters={
                "echo_time": 10e-3,  # 10ms
                "pi_pulse_duration": 200e-9,  # 200ns
                "pi_2_pulse_duration": 100e-9,  # 100ns
                "pulse_shape": "gaussian",
                "pulse_amplitude": 1.0,  # V
                "channel": 1,
                "repetition_rate": 1e3  # 1kHz
            },
            sequence_template="""
                # Spin Echo Sequence
                # π/2 - τ - π - τ - π/2
                pi_2_pulse: {pulse_shape} shape, {pulse_amplitude}V, {pi_2_pulse_duration} duration
                wait {echo_time}
                pi_pulse: {pulse_shape} shape, {pulse_amplitude}V, {pi_pulse_duration} duration
                wait {echo_time}
                pi_2_pulse: {pulse_shape} shape, {pulse_amplitude}V, {pi_2_pulse_duration} duration
                wait 1ms
            """
        )
        
        # CPMG (Carr-Purcell-Meiboom-Gill)
        experiments["cpmg"] = PresetExperiment(
            name="cpmg",
            description="CPMG sequence - Multiple echo sequence for T2 measurement",
            parameters={
                "echo_time": 1e-3,  # 1ms
                "num_echoes": 100,
                "pi_pulse_duration": 200e-9,  # 200ns
                "pi_2_pulse_duration": 100e-9,  # 100ns
                "pulse_shape": "gaussian",
                "pulse_amplitude": 1.0,  # V
                "channel": 1,
                "repetition_rate": 1e3  # 1kHz
            },
            sequence_template="""
                # CPMG Sequence
                # π/2 - τ - π - τ - π - τ - ... (multiple echoes)
                pi_2_pulse: {pulse_shape} shape, {pulse_amplitude}V, {pi_2_pulse_duration} duration
                repeat {num_echoes} times:
                    wait {echo_time}
                    pi_pulse: {pulse_shape} shape, {pulse_amplitude}V, {pi_pulse_duration} duration
                    wait {echo_time}
                wait 1ms
            """
        )
        
        # Ramsey Interference
        experiments["ramsey"] = PresetExperiment(
            name="ramsey",
            description="Ramsey Interference - Two π/2 pulses with variable delay",
            parameters={
                "delay_range": [100e-9, 10e-3],  # 100ns to 10ms
                "delay_points": 100,
                "pi_2_pulse_duration": 100e-9,  # 100ns
                "pulse_shape": "gaussian",
                "pulse_amplitude": 1.0,  # V
                "channel": 1,
                "repetition_rate": 1e3  # 1kHz
            },
            sequence_template="""
                # Ramsey Interference Sequence
                # π/2 - τ - π/2
                pi_2_pulse: {pulse_shape} shape, {pulse_amplitude}V, {pi_2_pulse_duration} duration
                wait variable_delay
                pi_2_pulse: {pulse_shape} shape, {pulse_amplitude}V, {pi_2_pulse_duration} duration
                wait 1ms
                repeat {delay_points} times
            """
        )
        
        return experiments
    
    def get_experiment_help(self, name: str = None) -> str:
        """
        Get help information for preset experiments.
        
        Args:
            name: Specific experiment name, or None for all experiments
            
        Returns:
            Help string with experiment information
        """
        if name is None:
            help_text = "Available Preset Experiments:\n\n"
            for exp_name, experiment in self.experiments.items():
                help_text += f"{exp_name}: {experiment.description}\n"
                help_text += f"  Parameters: {list(experiment.parameters.keys())}\n\n"
            return help_text
        else:
            experiment = self.get_experiment(name)
            help_text = f"Experiment: {experiment.name}\n"
            help_text += f"Description: {experiment.description}\n\n"
            help_text += "Default Parameters:\n"
            for param, value in experiment.parameters.items():
                help_text += f"  {param}: {value}\n"
            help_text += f"\nSequence Template:\n{experiment.sequence_template}"
            return help_text
