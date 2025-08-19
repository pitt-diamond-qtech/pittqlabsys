"""
Hardware Calibrator Module

This module handles hardware-specific timing calibrations, such as delays
between AWG outputs and physical experiment components (laser, IQ modulator, etc.).

The calibrator loads connection maps and applies appropriate timing shifts
to ensure pulses arrive at the experiment at the user-specified ideal times.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import logging

from .sequence import Sequence
from .pulses import Pulse

logger = logging.getLogger(__name__)


class HardwareCalibrator:
    """
    Applies hardware-specific timing calibrations to sequences.
    
    This class sits between SequenceBuilder and AWG520SequenceOptimizer,
    applying timing delays based on connection maps and calibration data.
    """
    
    def __init__(self, connection_file: Optional[str] = None, config_file: Optional[str] = None):
        """
        Initialize the hardware calibrator.
        
        Args:
            connection_file: Path to AWG520 connection map JSON file
            config_file: Path to lab configuration JSON file (for delays)
        """
        self.connection_file = connection_file
        self.config_file = config_file
        self.connection_map = {}
        self.calibration_delays = {}
        
        # Load connection and calibration data
        self._load_connection_map()
        self._load_calibration_delays()
    
    def _load_connection_map(self) -> None:
        """Load the AWG520 connection map from JSON file."""
        if not self.connection_file:
            logger.warning("No connection file specified, using default mapping")
            self._set_default_connection_map()
            return
        
        try:
            with open(self.connection_file, 'r') as f:
                data = json.load(f)
                self.connection_map = data.get('awg520_connections', {})
                logger.info(f"Loaded connection map from {self.connection_file}")
        except FileNotFoundError:
            logger.warning(f"Connection file {self.connection_file} not found, using default mapping")
            self._set_default_connection_map()
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in connection file: {e}")
            self._set_default_connection_map()
    
    def _load_calibration_delays(self) -> None:
        """Load calibration delays from config file or connection file."""
        # Try to load from config file first
        if self.config_file and Path(self.config_file).exists():
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    awg_config = config.get('awg520', {})
                    self.calibration_delays = awg_config.get('calibration_delays', {})
                    logger.info(f"Loaded calibration delays from config file")
                    return
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Could not load delays from config: {e}")
        
        # Fallback to connection file
        if self.connection_file and Path(self.connection_file).exists():
            try:
                with open(self.connection_file, 'r') as f:
                    data = json.load(f)
                    self.calibration_delays = data.get('calibration_delays', {})
                    logger.info(f"Loaded calibration delays from connection file")
                    return
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Could not load delays from connection file: {e}")
        
        # Use default delays
        self._set_default_calibration_delays()
    
    def _set_default_connection_map(self) -> None:
        """Set default connection mapping for typical qubit experiment."""
        self.connection_map = {
            "channels": {
                "1": {
                    "connection": "IQ_modulator_I_input",
                    "calibration_delays": ["iq_delay"]
                },
                "2": {
                    "connection": "IQ_modulator_Q_input", 
                    "calibration_delays": ["iq_delay"]
                }
            },
            "markers": {
                "ch1_marker1": {
                    "connection": "unassigned",
                    "calibration_delays": []
                },
                "ch1_marker2": {
                    "connection": "laser_switch",
                    "calibration_delays": ["laser_delay"]
                },
                "ch2_marker1": {
                    "connection": "unassigned",
                    "calibration_delays": []
                },
                "ch2_marker2": {
                    "connection": "counter_trigger",
                    "calibration_delays": ["counter_delay"]
                }
            },
            "experiment_types": {
                "odmr": {
                    "description": "ODMR experiment using IQ modulator and laser",
                    "required_connections": ["ch1", "ch2", "ch1_marker2", "ch2_marker2"],
                    "optional_connections": ["ch1_marker1", "ch2_marker1"]
                },
                "rabi": {
                    "description": "Rabi oscillation experiment",
                    "required_connections": ["ch1", "ch2", "ch1_marker2", "ch2_marker2"],
                    "optional_connections": ["ch1_marker1", "ch2_marker1"]
                },
                "spin_echo": {
                    "description": "Spin echo experiment",
                    "required_connections": ["ch1", "ch2", "ch1_marker2", "ch2_marker2"],
                    "optional_connections": ["ch1_marker1", "ch2_marker1"]
                }
            }
        }
        logger.info("Using default connection map")
    
    def _set_default_calibration_delays(self) -> None:
        """Set default calibration delay values."""
        self.calibration_delays = {
            "laser_delay": 50.0,
            "mw_delay": 25.0,
            "iq_delay": 30.0,
            "counter_delay": 15.0,
            "trigger_delay": 10.0,
            "units": "ns"
        }
        logger.info("Using default calibration delays")
    
    def get_delay_for_connection(self, connection_type: str, connection_id: str) -> float:
        """
        Get the calibration delay for a specific connection.
        
        Args:
            connection_type: 'channels' or 'markers'
            connection_id: Channel number or marker name (e.g., '1', 'ch1_marker2')
            
        Returns:
            Delay value in nanoseconds
        """
        if connection_type not in self.connection_map:
            return 0.0
        
        connection_info = self.connection_map[connection_type].get(connection_id, {})
        delay_names = connection_info.get('calibration_delays', [])
        
        if not delay_names:
            return 0.0
        
        # For now, use the first delay (could be enhanced to handle multiple delays)
        delay_name = delay_names[0]
        delay_value = self.calibration_delays.get(delay_name, 0.0)
        
        logger.debug(f"Delay for {connection_type}.{connection_id}: {delay_value}ns")
        return delay_value
    
    def calibrate_sequence(self, sequence: Sequence, sample_rate: float) -> Sequence:
        """
        Apply hardware calibration delays to a sequence.
        
        Args:
            sequence: Input sequence to calibrate
            sample_rate: Sample rate in Hz
            
        Returns:
            Calibrated sequence with adjusted timing
        """
        logger.info("Applying hardware calibration to sequence")
        
        # Create a copy of the sequence to avoid modifying the original
        calibrated_sequence = Sequence(sequence.length)
        
        # Process each pulse in the sequence
        for start_sample, pulse in sequence.pulses:
            # Determine connection type and ID
            connection_type, connection_id = self._get_pulse_connection(pulse)
            
            # Get the appropriate delay
            delay_ns = self.get_delay_for_connection(connection_type, connection_id)
            
            if delay_ns > 0:
                # Convert delay from nanoseconds to samples
                delay_samples = int(delay_ns * 1e-9 * sample_rate)
                
                # Shift the pulse timing backward (subtract delay)
                new_start_sample = max(0, start_sample - delay_samples)
                
                logger.debug(f"Shifting {pulse.name} from {start_sample} to {new_start_sample} "
                           f"(delay: {delay_ns}ns = {delay_samples} samples)")
                
                # Add the pulse at the new timing
                calibrated_sequence.add_pulse(new_start_sample, pulse)
            else:
                # No delay needed, add pulse at original timing
                calibrated_sequence.add_pulse(start_sample, pulse)
        
        logger.info("Hardware calibration completed")
        return calibrated_sequence
    
    def _get_pulse_connection(self, pulse: Pulse) -> Tuple[str, str]:
        """
        Determine the connection type and ID for a pulse.
        
        Args:
            pulse: Pulse object to analyze
            
        Returns:
            Tuple of (connection_type, connection_id)
        """
        # This is a simplified mapping - could be enhanced with more sophisticated logic
        pulse_name = pulse.name.lower()
        
        # Check for marker pulses first
        if 'laser' in pulse_name:
            return 'markers', 'ch1_marker2'
        elif 'counter' in pulse_name or 'trigger' in pulse_name:
            return 'markers', 'ch2_marker2'
        elif 'pi' in pulse_name or 'gaussian' in pulse_name or 'sech' in pulse_name:
            # Microwave pulses typically go to IQ modulator
            return 'channels', '1'  # Default to channel 1 for I
        else:
            # Default to channel 1 for unknown pulse types
            return 'channels', '1'
    
    def get_calibration_summary(self) -> Dict[str, Any]:
        """
        Get a summary of current calibration settings.
        
        Returns:
            Dictionary with calibration information
        """
        return {
            "connection_file": self.connection_file,
            "config_file": self.config_file,
            "connection_map": self.connection_map,
            "calibration_delays": self.calibration_delays,
            "total_connections": len(self.connection_map.get('channels', {})) + 
                               len(self.connection_map.get('markers', {}))
        }
    
    def validate_connections(self, experiment_type: str) -> Dict[str, List[str]]:
        """
        Validate that required connections are available for an experiment type.
        
        Args:
            experiment_type: Type of experiment (e.g., 'odmr', 'rabi')
            
        Returns:
            Dictionary with 'required' and 'missing' connection lists
        """
        if 'experiment_types' not in self.connection_map:
            return {"required": [], "missing": [], "error": "No experiment type definitions found"}
        
        exp_config = self.connection_map['experiment_types'].get(experiment_type, {})
        required_connections = exp_config.get('required_connections', [])
        
        missing_connections = []
        available_connections = []
        
        # Check channels
        for ch_id in self.connection_map.get('channels', {}):
            available_connections.append(ch_id)
        
        # Check markers  
        for marker_id in self.connection_map.get('markers', {}):
            available_connections.append(marker_id)
        
        # Find missing connections
        for req_conn in required_connections:
            if req_conn not in available_connections:
                missing_connections.append(req_conn)
        
        return {
            "required": required_connections,
            "missing": missing_connections,
            "available": available_connections,
            "experiment_type": experiment_type
        }
