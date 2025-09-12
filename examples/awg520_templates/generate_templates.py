#!/usr/bin/env python3
"""
Generate AWG520 Template Waveforms

This script creates small template waveform files (.wfm) for common signal types.
These templates serve as starting points for experiments.
"""

import numpy as np
from pathlib import Path
import sys

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from src.Model.awg_file import AWGFile

def generate_sine_wave(freq: float, duration: float, sample_rate: float, amplitude: float = 1.0):
    """Generate a sine wave with specified parameters."""
    t = np.linspace(0, duration, int(sample_rate * duration))
    return amplitude * np.sin(2 * np.pi * freq * t)

def generate_square_wave(freq: float, duration: float, sample_rate: float, amplitude: float = 1.0, duty_cycle: float = 0.5):
    """Generate a square wave with specified parameters."""
    t = np.linspace(0, duration, int(sample_rate * duration))
    signal = np.zeros_like(t)
    
    # Create square wave
    period = 1.0 / freq
    for i, time in enumerate(t):
        phase = (time % period) / period
        if phase < duty_cycle:
            signal[i] = amplitude
        else:
            signal[i] = -amplitude
    
    return signal

def generate_ramp(freq: float, duration: float, sample_rate: float, amplitude: float = 1.0):
    """Generate a ramp wave with specified parameters."""
    t = np.linspace(0, duration, int(sample_rate * duration))
    return amplitude * (2 * (t / duration) - 1)

def generate_gaussian_pulse(width_ns: float, duration: float, sample_rate: float, amplitude: float = 1.0):
    """Generate a Gaussian pulse with specified parameters."""
    t = np.linspace(0, duration, int(sample_rate * duration))
    center = duration / 2
    sigma = width_ns / (2.355 * 1e9)  # Convert to seconds
    return amplitude * np.exp(-0.5 * ((t - center) / sigma) ** 2)

def main():
    """Generate template waveform files."""
    print("=" * 60)
    print("GENERATING AWG520 TEMPLATE WAVEFORMS")
    print("=" * 60)
    
    # Create waveforms directory
    waveforms_dir = Path(__file__).parent / "waveforms"
    waveforms_dir.mkdir(exist_ok=True)
    
    # Initialize AWG file writer
    awg = AWGFile(ftype="WFM", timeres_ns=1, out_dir=str(waveforms_dir))
    
    # Generate template waveforms
    templates = [
        {
            "name": "sine_10MHz",
            "func": generate_sine_wave,
            "params": {"freq": 10e6, "duration": 1e-6, "sample_rate": 1e9, "amplitude": 1.0},
            "description": "10 MHz sine wave for microwave generation"
        },
        {
            "name": "square_1MHz",
            "func": generate_square_wave,
            "params": {"freq": 1e6, "duration": 1e-6, "sample_rate": 1e9, "amplitude": 1.0, "duty_cycle": 0.5},
            "description": "1 MHz square wave for timing signals"
        },
        {
            "name": "ramp_100kHz",
            "func": generate_ramp,
            "params": {"freq": 100e3, "duration": 2e-6, "sample_rate": 1e9, "amplitude": 1.0},
            "description": "100 kHz ramp for scanning applications"
        },
        {
            "name": "gaussian_pulse",
            "func": generate_gaussian_pulse,
            "params": {"width_ns": 100, "duration": 1e-6, "sample_rate": 1e9, "amplitude": 2.0},
            "description": "Gaussian pulse for laser control"
        }
    ]
    
    print(f"Generating {len(templates)} template waveforms...")
    
    for template in templates:
        try:
            print(f"Generating {template['name']}...")
            
            # Generate waveform data
            waveform = template["func"](**template["params"])
            
            # Write waveform file
            awg.write_waveform(waveform, template["name"])
            
            # Check file size
            wfm_file = waveforms_dir / f"{template['name']}.wfm"
            file_size = wfm_file.stat().st_size
            
            print(f"  ✓ {template['name']}.wfm created ({file_size} bytes)")
            print(f"    Description: {template['description']}")
            
        except Exception as e:
            print(f"  ✗ Failed to generate {template['name']}: {e}")
    
    print("\n" + "=" * 60)
    print("TEMPLATE GENERATION COMPLETE")
    print("=" * 60)
    print(f"Generated {len(templates)} template files in: {waveforms_dir}")
    print("\nNext steps:")
    print("1. Review the generated .wfm files")
    print("2. Test loading them in your AWG520 device")
    print("3. Use them as references in your sequence files")
    print("4. Modify parameters as needed for your experiments")

if __name__ == "__main__":
    main()
