"""
ADwin Helper Functions

This module provides helper functions for managing ADwin binary files and configurations
across different experiments. It centralizes the binary file path management to avoid
hardcoding paths in individual experiments.

Author: Gurudev Dutt <gdutt@pitt.edu>
Created: 2024
License: GPL v2
"""

from pathlib import Path
from typing import Optional, Dict, Any
from src.core.helper_functions import get_project_root


def get_adwin_binary_path(filename: str) -> Path:
    """
    Get the path to an ADwin binary file in the Controller/binary_files/ADbasic directory.
    
    Args:
        filename: Name of the binary file (e.g., 'ODMR_FM_Laser_Tracker.TB2')
        
    Returns:
        Path object pointing to the binary file
        
    Raises:
        FileNotFoundError: If the binary file doesn't exist
    """
    project_root = get_project_root()
    binary_path = project_root / 'src' / 'Controller' / 'binary_files' / 'ADbasic' / filename
    
    if not binary_path.exists():
        # Try to provide helpful error message
        print(f"Warning: ADwin binary file not found: {binary_path}")
        print(f"Project root: {project_root}")
        print(f"Expected location: {binary_path}")
        print(f"Available files in ADbasic directory:")
        adbasic_dir = project_root / 'src' / 'Controller' / 'binary_files' / 'ADbasic'
        if adbasic_dir.exists():
            for file in adbasic_dir.iterdir():
                if file.is_file():
                    print(f"  - {file.name}")
        else:
            print(f"  ADbasic directory does not exist: {adbasic_dir}")
        raise FileNotFoundError(f"ADwin binary file not found: {binary_path}")
    
    return binary_path


def get_available_adwin_binaries() -> Dict[str, Path]:
    """
    Get a dictionary of all available ADwin binary files.
    
    Returns:
        Dictionary mapping filename to Path object
    """
    project_root = get_project_root()
    adbasic_dir = project_root / 'src' / 'Controller' / 'binary_files' / 'ADbasic'
    
    binaries = {}
    if adbasic_dir.exists():
        for file in adbasic_dir.iterdir():
            if file.is_file() and file.suffix.lower() in ['.tb1', '.tb2', '.tb3', '.tb4']:
                binaries[file.name] = file
    
    return binaries


def validate_adwin_binary(filename: str) -> bool:
    """
    Check if an ADwin binary file exists and is valid.
    
    Args:
        filename: Name of the binary file to validate
        
    Returns:
        True if the file exists and is valid, False otherwise
    """
    try:
        binary_path = get_adwin_binary_path(filename)
        return binary_path.exists() and binary_path.is_file()
    except FileNotFoundError:
        return False


def get_adwin_process_config(process_number: int, binary_file: str, 
                           delay: int = 1000000, auto_start: bool = False) -> Dict[str, Any]:
    """
    Get a configuration dictionary for an ADwin process.
    
    Args:
        process_number: Process number (1-10)
        binary_file: Name of the binary file to load
        delay: Process delay in clock cycles (default: 1000000)
        auto_start: Whether to start the process automatically
        
    Returns:
        Configuration dictionary for the process
    """
    return {
        f'process_{process_number}': {
            'load': str(get_adwin_binary_path(binary_file)),
            'delay': delay,
            'running': auto_start
        }
    }


def setup_adwin_for_odmr(adwin_instance, integration_time_ms: float = 10.0, 
                        num_averages: int = 1, enable_laser_tracking: bool = False,
                        enable_fm_modulation: bool = False, fm_frequency: float = 1000.0,
                        fm_amplitude: float = 1.0) -> None:
    """
    Setup ADwin for ODMR experiments with the ODMR_FM_Laser_Tracker script.
    
    Args:
        adwin_instance: ADwinGold instance
        integration_time_ms: Integration time in milliseconds
        num_averages: Number of samples to average
        enable_laser_tracking: Whether to enable laser power tracking
        enable_fm_modulation: Whether to enable FM modulation
        fm_frequency: FM modulation frequency in Hz
        fm_amplitude: FM modulation amplitude in volts
    """
    # Stop and clear process 2
    adwin_instance.stop_process(2)
    
    # Load ODMR FM Laser Tracker script
    odmr_binary_path = get_adwin_binary_path('ODMR_FM_Laser_Tracker.TB2')
    adwin_instance.update({
        'process_2': {
            'load': str(odmr_binary_path),
            'delay': 1000000,  # 1ms base delay
            'running': False
        }
    })
    
    # Set parameters for the ODMR script
    # Par_2: Integration time in microseconds
    integration_time_us = int(integration_time_ms * 1000)
    adwin_instance.set_int_var(2, integration_time_us)
    
    # Par_4: Number of samples to average
    adwin_instance.set_int_var(4, num_averages)
    
    # Par_10: Enable laser power tracking (0=disabled, 1=enabled)
    laser_tracking_enabled = 1 if enable_laser_tracking else 0
    adwin_instance.set_int_var(10, laser_tracking_enabled)
    
    # Par_11: Enable FM modulation (0=disabled, 1=enabled)
    fm_enabled = 1 if enable_fm_modulation else 0
    adwin_instance.set_int_var(11, fm_enabled)
    
    # Par_12: FM modulation frequency in Hz
    adwin_instance.set_float_var(12, fm_frequency)
    
    # Par_13: FM modulation amplitude in volts
    adwin_instance.set_float_var(13, fm_amplitude)


def setup_adwin_for_simple_odmr(adwin_instance, integration_time_ms: float = 10.0) -> None:
    """
    Setup ADwin for simple ODMR experiments with the Trial_Counter script.
    
    This is a simplified version that just counts photons without any averaging,
    FM modulation, or laser tracking. Perfect for simple ODMR where the microwave
    frequency setting is the slow operation.
    
    Args:
        adwin_instance: ADwinGold instance
        integration_time_ms: Integration time in milliseconds
    """
    # Stop and clear process 1 (Trial_Counter uses process 1)
    adwin_instance.stop_process(1)
    
    # Load Trial counter script
    trial_binary_path = get_adwin_binary_path('Trial_Counter.TB1')
    adwin_instance.update({
        'process_1': {
            'load': str(trial_binary_path),
            'delay': int(integration_time_ms * 1000),  # Convert to microseconds
            'running': False
        }
    })


def setup_adwin_for_sweep_odmr(adwin_instance, integration_time_ms: float = 10.0, 
                              settle_time_ms: float = 0.1, num_steps: int = 100, 
                              bidirectional: bool = False) -> None:
    """
    Setup ADwin for enhanced ODMR sweep experiments with the ODMR_Sweep_Counter script.
    
    This script generates a voltage ramp on AO1 for SG384 modulation input and
    counts photons synchronously during the sweep.
    
    Args:
        adwin_instance: ADwinGold instance
        integration_time_ms: Integration time per step in milliseconds
        settle_time_ms: Settle time after voltage step in milliseconds
        num_steps: Number of steps in the sweep
        bidirectional: Whether to do bidirectional sweeps (forward/reverse)
    """
    # Stop and clear process 1 (ODMR_Sweep_Counter uses process 1)
    adwin_instance.stop_process(1)
    
    # Load ODMR Sweep Counter script
    sweep_binary_path = get_adwin_binary_path('ODMR_Sweep_Counter.TB1')
    adwin_instance.update({
        'process_1': {
            'load': str(sweep_binary_path),
            'delay': 1000000,  # 1ms base delay
            'running': False
        }
    })
    
    # Set parameters for the sweep script
    # Par_2: Integration time per step in microseconds
    integration_time_us = int(integration_time_ms * 1000)
    adwin_instance.set_int_var(2, integration_time_us)
    
    # Par_3: Number of steps in sweep
    adwin_instance.set_int_var(3, num_steps)
    
    # Par_5: Sweep direction (0=unidirectional, 1=bidirectional)
    sweep_direction = 1 if bidirectional else 0
    adwin_instance.set_int_var(5, sweep_direction)
    
    # Par_11: Settle time after voltage step in microseconds
    settle_time_us = int(settle_time_ms * 1000)
    adwin_instance.set_int_var(11, settle_time_us)


def read_adwin_odmr_data(adwin_instance) -> Dict[str, float]:
    """
    Read ODMR data from ADwin process 2.
    
    Args:
        adwin_instance: ADwinGold instance
        
    Returns:
        Dictionary containing the read data:
        - 'counts': Average counts
        - 'laser_power': Average laser power (if enabled)
        - 'raw_counts': Raw counter value
        - 'sample_index': Current sample index
    """
    # Read parameters from ADwin
    # Par_1: Raw counter value
    raw_counts = adwin_instance.read_probes('Par_1', 1, 1)[0]
    
    # Par_8: Final averaged counts
    avg_counts = adwin_instance.read_probes('Par_8', 1, 1)[0]
    
    # Par_9: Final averaged laser power
    avg_laser_power = adwin_instance.read_probes('Par_9', 1, 1)[0]
    
    # Par_5: Current sample index
    sample_index = adwin_instance.read_probes('Par_5', 1, 1)[0]
    
    return {
        'counts': avg_counts,
        'laser_power': avg_laser_power,
        'raw_counts': raw_counts,
        'sample_index': sample_index
    }


def read_adwin_simple_odmr_data(adwin_instance) -> float:
    """
    Read data from ADwin simple ODMR experiment using Trial_Counter.
    
    Args:
        adwin_instance: ADwinGold instance
        
    Returns:
        Counts for the integration period (float)
    """
    # Read the counts (Par_1) - Trial_Counter only has one parameter
    counts = adwin_instance.get_int_var(1)
    return float(counts)


def read_adwin_sweep_odmr_data(adwin_instance) -> Dict[str, Any]:
    """
    Read data from ADwin sweep ODMR experiment using ODMR_Sweep_Counter.
    
    This function reads the separate forward and reverse sweep data arrays
    with clear synchronization between voltage/frequency and counts.
    
    Args:
        adwin_instance: ADwinGold instance
        
    Returns:
        Dictionary containing:
        - 'counts': Current counts (Par_1)
        - 'step_index': Current step index (Par_4)
        - 'voltage': Current voltage output (Par_6)
        - 'sweep_complete': Sweep complete flag (Par_7)
        - 'total_counts': Total counts for current step (Par_8)
        - 'sweep_cycle': Sweep cycle (0=forward, 1=reverse, 2=complete) (Par_9)
        - 'data_ready': Data ready flag (Par_10)
        - 'forward_counts': Array of forward sweep counts (Data_1)
        - 'reverse_counts': Array of reverse sweep counts (Data_2)
        - 'forward_voltages': Array of forward sweep voltages (Data_3)
        - 'reverse_voltages': Array of reverse sweep voltages (Data_4)
        - 'sweep_direction': Current sweep direction (Par_5)
    """
    try:
        # Read parameters from ADwin using the correct method
        # Par_1: Current counter value
        counts = adwin_instance.get_int_var(1)
        
        # Par_4: Current step index
        step_index = adwin_instance.get_int_var(4)
        
        # Par_5: Current sweep direction
        sweep_direction = adwin_instance.get_int_var(5)
        
        # Par_6: Current voltage output (as integer, needs conversion)
        voltage_raw = adwin_instance.get_int_var(6)
        voltage = float(voltage_raw) / 1000.0  # Convert from millivolts to volts
        
        # Par_7: Sweep complete flag
        sweep_complete = adwin_instance.get_int_var(7)
        
        # Par_8: Total counts for current step
        total_counts = adwin_instance.get_int_var(8)
        
        # Par_9: Sweep cycle counter
        sweep_cycle = adwin_instance.get_int_var(9)
        
        # Par_10: Data ready flag
        data_ready = adwin_instance.get_int_var(10)
        
        # Read data arrays if sweep is complete
        forward_counts = None
        reverse_counts = None
        forward_voltages = None
        reverse_voltages = None
        
        if sweep_complete and data_ready:
            # Get number of steps from Par_3
            num_steps = adwin_instance.get_int_var(3)
            
            # Read forward sweep data
            forward_counts = adwin_instance.read_probes('int_array', 1, num_steps)
            forward_voltages = adwin_instance.read_probes('int_array', 3, num_steps)
            
            # Read reverse sweep data
            reverse_counts = adwin_instance.read_probes('int_array', 2, num_steps)
            reverse_voltages = adwin_instance.read_probes('int_array', 4, num_steps)
            
            # Convert voltages from millivolts to volts
            forward_voltages = [float(v) / 1000.0 for v in forward_voltages]
            reverse_voltages = [float(v) / 1000.0 for v in reverse_voltages]
        
        return {
            'counts': counts,
            'step_index': step_index,
            'voltage': voltage,
            'sweep_complete': bool(sweep_complete),
            'total_counts': total_counts,
            'sweep_cycle': sweep_cycle,
            'data_ready': bool(data_ready),
            'forward_counts': forward_counts,
            'reverse_counts': reverse_counts,
            'forward_voltages': forward_voltages,
            'reverse_voltages': reverse_voltages,
            'sweep_direction': sweep_direction
        }
        
    except Exception as e:
        # Return default values if reading fails
        print(f"Warning: Failed to read Adwin data: {e}")
        return {
            'counts': 0,
            'step_index': 0,
            'voltage': 0.0,
            'sweep_complete': False,
            'total_counts': 0,
            'sweep_cycle': 0,
            'data_ready': False,
            'forward_counts': None,
            'reverse_counts': None,
            'forward_voltages': None,
            'reverse_voltages': None,
            'sweep_direction': 1
        }


def setup_adwin_for_fm_odmr(adwin_instance, integration_time_ms: float = 1.0, 
                           num_cycles: int = 10, modulation_rate_hz: float = 1000.0) -> None:
    """
    Setup ADwin for frequency modulation ODMR experiments.
    
    This function adapts the ODMR_Sweep_Counter for FM experiments by configuring
    it for unidirectional sweeps with cycle-based averaging.
    
    Args:
        adwin_instance: ADwinGold instance
        integration_time_ms: Integration time per point in milliseconds
        num_cycles: Number of modulation cycles to average
        modulation_rate_hz: Frequency of the modulation in Hz
    """
    # Use the sweep setup as a base, but configure for FM
    setup_adwin_for_sweep_odmr(
        adwin_instance,
        integration_time_ms,
        0.001,  # 1 ms settle time
        int(1.0 / (modulation_rate_hz * integration_time_ms * 1e-3)),  # points per cycle
        False  # unidirectional for FM
    )
    
    # Set FM-specific parameters
    # Par_10: Number of cycles per average
    adwin_instance.set_int_var(10, num_cycles)
    
    # Par_12: Modulation rate (stored for reference)
    adwin_instance.set_float_var(12, modulation_rate_hz)


def read_adwin_fm_odmr_data(adwin_instance) -> Dict[str, Any]:
    """
    Read data from ADwin FM ODMR experiment.
    
    This function reads FM-specific data from the adapted sweep counter.
    
    Args:
        adwin_instance: ADwinGold instance
        
    Returns:
        Dictionary containing:
        - 'counts': Current counts (Par_1)
        - 'step_index': Current step index (Par_4)
        - 'voltage': Current voltage output (Par_6)
        - 'cycle_complete': Cycle complete flag (Par_7)
        - 'total_counts': Total counts for current step (Par_8)
        - 'cycle_count': Current cycle count (Par_9)
        - 'data_ready': Data ready flag (Par_10)
        - 'modulation_cycles': Array of cycle counts (Data_1)
        - 'cycle_voltages': Array of cycle voltages (Data_3)
        - 'modulation_rate': Stored modulation rate (Par_12)
    """
    # Use the sweep data reader as a base
    sweep_data = read_adwin_sweep_odmr_data(adwin_instance)
    
    # Extract FM-specific data
    fm_data = {
        'counts': sweep_data['counts'],
        'step_index': sweep_data['step_index'],
        'voltage': sweep_data['voltage'],
        'cycle_complete': sweep_data['sweep_complete'],
        'total_counts': sweep_data['total_counts'],
        'cycle_count': sweep_data['sweep_cycle'],
        'data_ready': sweep_data['data_ready'],
        'modulation_cycles': sweep_data['forward_counts'],  # Use forward as cycle data
        'cycle_voltages': sweep_data['forward_voltages'],   # Use forward as voltage data
        'modulation_rate': adwin_instance.get_float_var(12) if sweep_data['data_ready'] else None
    }
    
    return fm_data 