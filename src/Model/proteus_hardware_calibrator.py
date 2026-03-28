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

_DEFAULT_DELAY = 0.0

class ProteusHardwareCalibrator:
    """
    Applies hardware-specific timing calibrations to sequences.
    
    This class gets called after SequenceBuilder,
    applying timing delays based on connection maps and calibration data.
    """
    
    def __init__(self, connection_file: Optional[str] = None):
        """
        Initialize the hardware calibrator.
        
        Args:
            connection_file: Path to Proteus connection map JSON file
            config_file: Path to lab configuration JSON file (for delays)
        """
        self.connection_file = connection_file
        self.connection_map = {}
        self.calibration_delays = {}
        self.experiment_types = {}
        
        # Load connection and calibration data
        self._load_connection_map()
        self._load_calibration_delays()
        self._load_experiment_types()

    def _load_connection_map(self) -> None:
        """Load the Proteus connection map from JSON file."""
        if not self.connection_file:
            logger.warning("No connection file specified, using default mapping")
            self._set_default_connection_map()
            return
        
        try:
            with open(self.connection_file, 'r') as f:
                data = json.load(f)
                self.connection_map = data.get('proteus_connections', {})
                logger.info(f"Loaded connection map from {self.connection_file}")
        except FileNotFoundError:
            logger.warning(f"Connection file {self.connection_file} not found, using default mapping")
            self._set_default_connection_map()
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in connection file: {e}")
            self._set_default_connection_map()

    def _load_calibration_delays(self):
        """Load the calibration delays from JSON file."""
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

    def _load_experiment_types(self):
        """Load the experiment types from JSON file."""
        try:
            with open(self.connection_file, 'r') as f:
                data = json.load(f)
                self.experiment_types = data.get('experiment_types', {})
                logger.info(f"Loaded experiment types from connection file")
                return
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Could not load experiment types from connection file: {e}")

        # Use default delays
        self._set_default_experiment_types()
    
    def _set_default_connection_map(self) -> None:
        """Set default connection mapping for typical qubit experiment."""
        self.connection_map = {
            "channels": {
              "1": {
                "connection": "IQ_modulator_I_input",
                "type": "analog",
                "calibration_delays": ["iq_delay"],
                "description": "Microwave I quadrature input to IQ modulator",
                "voltage_range": "±1V",
                "impedance": "50Ω"
              },
              "2": {
                "connection": "IQ_modulator_Q_input",
                "type": "analog",
                "calibration_delays": ["iq_delay"],
                "description": "Microwave Q quadrature input to IQ modulator",
                "voltage_range": "±1V",
                "impedance": "50Ω"
              },
              "3": {
                "connection": "Dye_Laser_AOM",
                "type": "analog",
                "calibration_delays": ["orange_laser_delay"],
                "description": "Dye Laser AOM",
                "voltage_range": "±1V",
                "impedance": "50Ω"
              },
              "4": {
                "connection": "unassigned",
                "type": "analog",
                "calibration_delays": [],
                "description": "Available for future use",
                "voltage_range": "±1V",
                "impedance": "50Ω"
              }
            },
            "markers": {
              "ch1_marker1": {
                "connection": "green laser AOM",
                "type": "digital",
                "calibration_delays": ["green_laser_delay"],
                "description": "Available for future use",
                "voltage": "3.3V",
                "impedance": "50Ω"
              },
              "ch2_marker1": {
                "connection": "unassigned",
                "type": "digital",
                "calibration_delays": [],
                "description": "Available for future use",
                "voltage": "3.3V",
                "impedance": "50Ω"
              },
              "ch3_marker1": {
                "connection": "unassigned",
                "type": "digital",
                "calibration_delays": [],
                "description": "Available for future use",
                "voltage": "3.3V",
                "impedance": "50Ω"
              },
              "ch4_marker1": {
                "connection": "unassigned",
                "type": "digital",
                "calibration_delays": [],
                "description": "Available for future use",
                "voltage": "3.3V",
                "impedance": "50Ω"
              }
            }
        }
        logger.info("Using default connection map")
    
    def _set_default_calibration_delays(self) -> None:
        """Set default calibration delay values."""
        self.calibration_delays = {
            "green_laser_delay": 50.0,
            "orange_laser_delay": 10.0,
            "mw_delay": 25.0,
            "iq_delay": 30.0,
            "counter_delay": 15.0,
            "trigger_delay": 0.0,
            "units": "ns"
        }
        logger.info("Using default calibration delays")

    def _set_default_experiment_types(self):
        self.experiment_types = {
                "odmr": {
                  "description": "ODMR experiment using IQ modulator and laser",
                  "required_connections": ["ch1", "ch2", "ch1_marker1"],
                  "optional_connections": ["ch3", "ch4", "ch2_marker1", "ch3_marker1", "ch4_marker1"]
                },
                "rabi": {
                  "description": "Rabi oscillation experiment",
                  "required_connections": ["ch1", "ch2", "ch1_marker1"],
                  "optional_connections": ["ch3", "ch4", "ch2_marker1", "ch3_marker1", "ch4_marker1"]
                },
                "spin_echo": {
                  "description": "Spin echo experiment",
                  "required_connections": ["ch1", "ch2", "ch1_marker1"],
                  "optional_connections": ["ch3", "ch4", "ch2_marker1", "ch3_marker1", "ch4_marker1"]
                },
                "spin_charge_conversion": {
                  "description": "Spin Charge Conversion experiment",
                  "required_connections": ["ch1", "ch2", "ch3", "ch1_marker1"],
                  "optional_connections": ["ch4", "ch2_marker1", "ch3_marker1", "ch4_marker1"]
                }
              }
        logger.info("Using default calibration delays")

    def get_delay_for_connection(self, connection_type: str, connection_id: str) -> float:
        """
        Get the calibration delay for a specific connection.
        
        Args:
            connection_type: 'channels' or 'markers'
            connection_id: Channel number or marker name (e.g., '1', 'ch1_marker1')
            
        Returns:
            Delay value in nanoseconds
        """
        if connection_type not in self.connection_map:
            return 0.0
        #connection
        connection_info = self.connection_map[connection_type].get(connection_id, {})
        delay_names = connection_info.get('calibration_delays', [])
        
        if not delay_names:
            return 0.0
        
        # For now, use the first delay (could be enhanced to handle multiple delays)
        delay_name = delay_names[0]
        delay_value = self.calibration_delays.get(delay_name, _DEFAULT_DELAY)
        
        logger.debug(f"Delay for {connection_type}.{connection_id}: {delay_value}ns")
        return delay_value
    
    def calibrate_sequence(self, sequence: Sequence, sample_rate: float) -> Sequence:
        """
        This function makes the sequence longer as it sets new_sequence_length = old_sequence_length + max_delay
        This avoids clipping pulses to start at 0 under the assumption that the user knows about delays12a
        Apply hardware calibration delays to a sequence.
        
        Args:
            sequence: Input sequence to calibrate
            sample_rate: Sample rate in Hz
            
        Returns:
            Calibrated sequence with adjusted timing
        """
        logger.info("Applying hardware calibration to sequence")

        max_delay = 0

        # find max delay
        for start_sample, pulse in sequence.pulses:
            # Determine connection type and ID
            connection_type = 'channels'
            connection_id = str(pulse.name.split("_")[-1])

            # Get the appropriate delay
            delay_ns = self.get_delay_for_connection(connection_type, connection_id)
            delay_samples = int(delay_ns * 1e-9 * sample_rate)
            if delay_samples > max_delay:
                max_delay = delay_samples

        # we do the same for markers:
        for marker in sequence.markers:
            # Determine connection type and ID
            connection_type = 'markers'
            connection_id = f"ch{str(marker.name.split("_")[-1])}_marker{str(marker.name.split("_")[-2])}"

            # Get the appropriate delay
            delay_ns = self.get_delay_for_connection(connection_type, connection_id)
            delay_samples = int(delay_ns * 1e-9 * sample_rate)
            if delay_samples > max_delay:
                max_delay = delay_samples

        # Create a copy of the sequence to avoid modifying the original
        calibrated_sequence = Sequence(sequence.length + max_delay)

        # Process each pulse in the sequence
        for start_sample, pulse in sequence.pulses:
            # Determine connection type and ID
            connection_type = 'channels'
            connection_id = str(pulse.name.split("_")[-1])
            # Get the appropriate delay
            delay_ns = self.get_delay_for_connection(connection_type, connection_id)

            # if max delay then we start and end at the same time as before, else, we need to start later by max_delay - delay

            # Convert delay from nanoseconds to samples
            delay_samples = int(delay_ns * 1e-9 * sample_rate)

            # Shift the pulse timing backward (subtract delay)
            new_start_sample = max_delay + start_sample - delay_samples

            logger.debug(f"Shifting {pulse.name} from {start_sample} to {new_start_sample} "
                         f"(delay: {delay_ns}ns = {delay_samples} samples)")
            print(f"Shifting {pulse.name} from {start_sample} to {new_start_sample} delay: {delay_ns}ns = {delay_samples} samples")

            # Add the pulse at the new timing
            calibrated_sequence.add_pulse(new_start_sample, pulse)

        # add markers:
        for marker in sequence.markers:
            # Determine connection type and ID
            connection_type = 'markers'
            connection_id = f"ch{str(marker.name.split("_")[-1])}_marker{str(marker.name.split("_")[-2])}"
            # Get the appropriate delay
            delay_ns = self.get_delay_for_connection(connection_type, connection_id)

            # if max delay then we start and end at the same time as before, else, we need to start later by max_delay - delay
            # Convert delay from nanoseconds to samples
            delay_samples = int(delay_ns * 1e-9 * sample_rate)

            # Shift the pulse timing backward (subtract delay)
            new_on_index = max_delay + marker.on_index - delay_samples
            new_off_index = max_delay + marker.off_index - delay_samples

            logger.debug(f"Shifting {marker.name} marker from {marker.on_index} to {new_on_index} "
                         f"(delay: {delay_ns}ns = {delay_samples} samples)")
            print(f"Shifting {marker.name} marker from {marker.on_index} to {new_on_index}. max_delay = {max_delay}samples. delay: {delay_ns}ns = {delay_samples} samples")
            marker.length = sequence.length + max_delay
            marker.on_index = new_on_index
            marker.off_index = new_off_index
            # Add the marker at the new timing
            calibrated_sequence.add_marker(marker)

        logger.info("Hardware calibration completed")
        return calibrated_sequence
    
    def get_calibration_summary(self) -> Dict[str, Any]:
        """
        Get a summary of current calibration settings.
        
        Returns:
            Dictionary with calibration information
        """
        return {
            "connection_file": self.connection_file,
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
        if 'experiment_types' not in self.experiment_types:
            return {"required": [], "missing": [], "error": "No experiment type definitions found"}
        
        exp_config = self.experiment_types.get(experiment_type, {})
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

    def update_calibration_delays(self, delays: dict):
        self.calibration_delays = delays
        logger.info("Updating calibration delays")