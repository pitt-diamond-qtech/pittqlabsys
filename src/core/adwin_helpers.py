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
        filename: Name of the binary file (e.g., 'ODMR_Counter.TB2')
        
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
    Setup ADwin for ODMR experiments with the ODMR_Counter script.
    
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
    
    # Load ODMR counter script
    odmr_binary_path = get_adwin_binary_path('ODMR_Counter.TB2')
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