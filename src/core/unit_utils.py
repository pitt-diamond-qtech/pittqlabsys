#!/usr/bin/env python3
"""
Unit utilities for handling common unit conversions and prefixes.

This module provides utilities for working with pint units, including:
- Common unit prefixes (kHz, MHz, GHz, etc.)
- Unit conversion helpers
- Unit display formatting
"""

from src import ur


def get_common_units_for_dimensionality(dimensionality):
    """
    Get common units for a given dimensionality.
    
    Args:
        dimensionality: pint dimensionality object
        
    Returns:
        list: List of common unit names for this dimensionality
    """
    common_units = []
    
    # Frequency units
    if dimensionality == ur.Hz.dimensionality:
        common_units = ['Hz', 'kHz', 'MHz', 'GHz', 'THz']
    
    # Temperature units
    elif dimensionality == ur.K.dimensionality:
        common_units = ['K', 'degC', 'degF', 'degR']
    
    # Voltage units
    elif dimensionality == ur.V.dimensionality:
        common_units = ['V', 'mV', 'kV']
    
    # Power units
    elif dimensionality == ur.W.dimensionality:
        common_units = ['W', 'mW', 'kW']
    
    # Current units
    elif dimensionality == ur.A.dimensionality:
        common_units = ['A', 'mA', 'kA']
    
    # Resistance units
    elif dimensionality == ur.ohm.dimensionality:
        common_units = ['ohm', 'mohm', 'kohm', 'Mohm']
    
    return common_units


def convert_to_common_unit(value, target_unit_name):
    """
    Convert a pint quantity to a common unit.
    
    Args:
        value: pint.Quantity to convert
        target_unit_name: Target unit name (e.g., 'MHz', 'mV')
        
    Returns:
        pint.Quantity: Converted value in target units
    """
    if not hasattr(value, 'magnitude') or not hasattr(value, 'units'):
        return value
    
    # Handle common frequency prefixes
    if target_unit_name == 'kHz':
        return value.to(1e3 * ur.Hz)
    elif target_unit_name == 'MHz':
        return value.to(1e6 * ur.Hz)
    elif target_unit_name == 'GHz':
        return value.to(1e9 * ur.Hz)
    elif target_unit_name == 'THz':
        return value.to(1e12 * ur.Hz)
    
    # Handle common voltage prefixes
    elif target_unit_name == 'mV':
        return value.to(1e-3 * ur.V)
    elif target_unit_name == 'kV':
        return value.to(1e3 * ur.V)
    
    # Handle common power prefixes
    elif target_unit_name == 'mW':
        return value.to(1e-3 * ur.W)
    elif target_unit_name == 'kW':
        return value.to(1e3 * ur.W)
    
    # Handle common current prefixes
    elif target_unit_name == 'mA':
        return value.to(1e-3 * ur.A)
    elif target_unit_name == 'kA':
        return value.to(1e3 * ur.A)
    
    # Handle common resistance prefixes
    elif target_unit_name == 'mohm':
        return value.to(1e-3 * ur.ohm)
    elif target_unit_name == 'kohm':
        return value.to(1e3 * ur.ohm)
    elif target_unit_name == 'Mohm':
        return value.to(1e6 * ur.ohm)
    
    # Try to get from ur module
    try:
        target_unit = getattr(ur, target_unit_name)
        return value.to(target_unit)
    except AttributeError:
        raise ValueError(f"Unknown unit: {target_unit_name}")


def format_unit_display(value, target_unit_name=None):
    """
    Format a pint quantity for display.
    
    Args:
        value: pint.Quantity to format
        target_unit_name: Optional target unit name for conversion
        
    Returns:
        str: Formatted string for display
    """
    if not hasattr(value, 'magnitude') or not hasattr(value, 'units'):
        return str(value)
    
    if target_unit_name:
        try:
            converted = convert_to_common_unit(value, target_unit_name)
            return f"{converted.magnitude:.6g} {target_unit_name}"
        except (ValueError, AttributeError):
            pass
    
    # Default formatting
    return f"{value.magnitude:.6g} {value.units}"


def get_best_display_unit(value):
    """
    Get the best unit for displaying a value.
    
    Args:
        value: pint.Quantity to analyze
        
    Returns:
        str: Best unit name for display
    """
    if not hasattr(value, 'magnitude') or not hasattr(value, 'units'):
        return None
    
    magnitude = abs(value.magnitude)
    
    # Frequency units
    if value.dimensionality == ur.Hz.dimensionality:
        if magnitude >= 1e12:
            return 'THz'
        elif magnitude >= 1e9:
            return 'GHz'
        elif magnitude >= 1e6:
            return 'MHz'
        elif magnitude >= 1e3:
            return 'kHz'
        else:
            return 'Hz'
    
    # Voltage units
    elif value.dimensionality == ur.V.dimensionality:
        if magnitude >= 1e3:
            return 'kV'
        elif magnitude < 1:
            return 'mV'
        else:
            return 'V'
    
    # Power units
    elif value.dimensionality == ur.W.dimensionality:
        if magnitude >= 1e3:
            return 'kW'
        elif magnitude < 1:
            return 'mW'
        else:
            return 'W'
    
    # Current units
    elif value.dimensionality == ur.A.dimensionality:
        if magnitude >= 1e3:
            return 'kA'
        elif magnitude < 1:
            return 'mA'
        else:
            return 'A'
    
    # Default to original units
    return str(value.units) 