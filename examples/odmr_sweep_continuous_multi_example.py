#!/usr/bin/env python3
"""
Example script for ODMR Multi-Waveform Phase Continuous Sweep Experiment

This script demonstrates how to run the new multi-waveform ODMR experiment
with support for different waveform types.

Usage:
    python odmr_sweep_continuous_multi_example.py [options]

Examples:
    # Triangle waveform (default, bidirectional)
    python odmr_sweep_continuous_multi_example.py --waveform 0

    # Sine waveform (unidirectional)
    python odmr_sweep_continuous_multi_example.py --waveform 2

    # Square waveform with custom setpoint
    python odmr_sweep_continuous_multi_example.py --waveform 3 --square-setpoint 0.5

    # Noise waveform with custom seed
    python odmr_sweep_continuous_multi_example.py --waveform 4 --noise-seed 54321

    # Custom waveform (user-defined table)
    python odmr_sweep_continuous_multi_example.py --waveform 100

Author: Gurudev Dutt <gdutt@pitt.edu>
Created: 2024
License: GPL v2
"""

import sys
import os
import argparse
import json
import time
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.Model.experiments.odmr_sweep_continuous_multi import ODMRSweepContinuousMultiExperiment
from src.Controller import create_mock_devices


def create_mock_devices():
    """Create mock devices for testing."""
    from src.Controller import MockSG384Generator, MockAdwinGoldDevice, MockMCLNanoDrive
    
    devices = {
        'sg384': {
            'instance': MockSG384Generator(),
            'name': 'SG384',
            'type': 'microwave_generator'
        },
        'adwin': {
            'instance': MockAdwinGoldDevice(),
            'name': 'ADwin Gold II',
            'type': 'adwin'
        },
        'nanodrive': {
            'instance': MockMCLNanoDrive(),
            'name': 'MCL NanoDrive',
            'type': 'nanodrive'
        }
    }
    
    return devices


def load_experiment_config(config_file):
    """Load experiment configuration from JSON file."""
    if not os.path.exists(config_file):
        print(f"❌ Config file not found: {config_file}")
        return None
    
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        print(f"✅ Loaded config from: {config_file}")
        return config
    except Exception as e:
        print(f"❌ Error loading config file: {e}")
        return None


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='ODMR Multi-Waveform Phase Continuous Sweep Experiment Example',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Waveform Types:
  0  = Triangle (bidirectional, original behavior)
  1  = Ramp/Saw (up only, sharp return)
  2  = Sine (one complete sine period)
  3  = Square (constant setpoint)
  4  = Noise (random step-to-step)
  100 = Custom (user-defined table)

Examples:
  # Triangle waveform (default)
  python odmr_sweep_continuous_multi_example.py --waveform 0

  # Sine waveform with custom parameters
  python odmr_sweep_continuous_multi_example.py --waveform 2 --start-freq 2.8e9 --stop-freq 3.0e9

  # Square waveform with setpoint
  python odmr_sweep_continuous_multi_example.py --waveform 3 --square-setpoint 0.5

  # Noise waveform with seed
  python odmr_sweep_continuous_multi_example.py --waveform 4 --noise-seed 12345
        """
    )
    
    # Frequency range arguments
    parser.add_argument('--start-freq', type=float, default=None,
                       help='Start frequency in Hz (default: from config)')
    parser.add_argument('--stop-freq', type=float, default=None,
                       help='Stop frequency in Hz (default: from config)')
    parser.add_argument('--step-freq', type=float, default=None,
                       help='Frequency step size in Hz (default: from config)')
    
    # Microwave arguments
    parser.add_argument('--power', type=float, default=None,
                       help='Microwave power in dBm (default: from config)')
    parser.add_argument('--waveform', type=int, default=0,
                       choices=[0, 1, 2, 3, 4, 100],
                       help='Waveform type: 0=Triangle, 1=Ramp, 2=Sine, 3=Square, 4=Noise, 100=Custom (default: 0)')
    parser.add_argument('--square-setpoint', type=float, default=0.0,
                       help='Square wave setpoint in V (for waveform=3, default: 0.0)')
    parser.add_argument('--noise-seed', type=int, default=12345,
                       help='Random seed for noise waveform (for waveform=4, default: 12345)')
    
    # Acquisition arguments
    parser.add_argument('--integration-time', type=float, default=None,
                       help='Integration time per point in seconds (default: from config)')
    parser.add_argument('--averages', type=int, default=None,
                       help='Number of sweep averages (default: from config)')
    parser.add_argument('--settle-time', type=float, default=None,
                       help='Settle time between sweeps in seconds (default: from config)')
    parser.add_argument('--bidirectional', action='store_true', default=None,
                       help='Enable bidirectional sweeps (only for Triangle waveform)')
    
    # Config file argument
    parser.add_argument('--experiment-config', type=str, default='examples/odmr_sweep_config.json',
                       help='Path to experiment configuration JSON file (default: examples/odmr_sweep_config.json)')
    
    # Mock hardware argument
    parser.add_argument('--mock-hardware', action='store_true',
                       help='Use mock hardware instead of real devices')
    
    args = parser.parse_args()
    
    print("🚀 ODMR Multi-Waveform Phase Continuous Sweep Experiment Example")
    print("=" * 70)
    
    # Load configuration
    config = load_experiment_config(args.experiment_config)
    if config is None:
        print("❌ Failed to load configuration. Exiting.")
        return 1
    
    # Create devices
    if args.mock_hardware:
        print("🔧 Using mock hardware for testing")
        devices = create_mock_devices()
    else:
        print("🔧 Using real hardware")
        # TODO: Implement real device creation
        print("❌ Real hardware not implemented yet. Use --mock-hardware for testing.")
        return 1
    
    # Build experiment settings from config and command line arguments
    settings = {}
    
    # Frequency range
    freq_range = config.get('frequency_range', {})
    settings['frequency_range'] = {
        'start': args.start_freq if args.start_freq is not None else freq_range.get('start', 2.7e9),
        'stop': args.stop_freq if args.stop_freq is not None else freq_range.get('stop', 3.0e9)
    }
    
    # Microwave settings
    microwave = config.get('microwave', {})
    settings['microwave'] = {
        'power': args.power if args.power is not None else microwave.get('power', -10.0),
        'step_freq': args.step_freq if args.step_freq is not None else microwave.get('step_freq', 1e6),
        'waveform': args.waveform,
        'square_setpoint': args.square_setpoint,
        'noise_seed': args.noise_seed
    }
    
    # Acquisition settings
    acquisition = config.get('acquisition', {})
    settings['acquisition'] = {
        'integration_time': args.integration_time if args.integration_time is not None else acquisition.get('integration_time', 0.001),
        'averages': args.averages if args.averages is not None else acquisition.get('averages', 10),
        'settle_time': args.settle_time if args.settle_time is not None else acquisition.get('settle_time', 0.01),
        'bidirectional': args.bidirectional if args.bidirectional is not None else acquisition.get('bidirectional', True)
    }
    
    # Other settings from config
    settings['laser'] = config.get('laser', {'power': 1.0, 'wavelength': 532.0})
    settings['magnetic_field'] = config.get('magnetic_field', {'enabled': False, 'strength': 0.0, 'direction': [0.0, 0.0, 1.0]})
    settings['analysis'] = config.get('analysis', {'auto_fit': True, 'smoothing': True, 'smooth_window': 5, 'background_subtraction': True})
    
    # Print configuration
    waveform_names = {0: "Triangle", 1: "Ramp", 2: "Sine", 3: "Square", 4: "Noise", 100: "Custom"}
    waveform_name = waveform_names.get(args.waveform, "Unknown")
    
    print(f"📋 Experiment Configuration:")
    print(f"   Frequency range: {settings['frequency_range']['start']/1e9:.3f} - {settings['frequency_range']['stop']/1e9:.3f} GHz")
    print(f"   Step frequency: {settings['microwave']['step_freq']/1e6:.2f} MHz")
    print(f"   Power: {settings['microwave']['power']} dBm")
    print(f"   Waveform: {args.waveform} ({waveform_name})")
    if args.waveform == 3:
        print(f"   Square setpoint: {args.square_setpoint} V")
    if args.waveform == 4:
        print(f"   Noise seed: {args.noise_seed}")
    print(f"   Integration time: {settings['acquisition']['integration_time']*1e3:.1f} ms")
    print(f"   Averages: {settings['acquisition']['averages']}")
    print(f"   Bidirectional: {settings['acquisition']['bidirectional']}")
    
    # Create and run experiment
    try:
        print(f"\n🔬 Creating experiment...")
        experiment = ODMRSweepContinuousMultiExperiment(
            devices=devices,
            name="ODMR Multi-Waveform Example",
            settings=settings,
            log_function=print
        )
        
        print(f"✅ Experiment created successfully")
        
        # Run the experiment
        print(f"\n▶️  Running experiment...")
        start_time = time.time()
        
        experiment.run()
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"✅ Experiment completed successfully in {duration:.2f} seconds")
        
        # Print results summary
        if hasattr(experiment, 'counts_averaged') and experiment.counts_averaged is not None:
            print(f"\n📊 Results Summary:")
            print(f"   Data points: {len(experiment.counts_averaged)}")
            print(f"   Count range: {experiment.counts_averaged.min():.1f} - {experiment.counts_averaged.max():.1f}")
            print(f"   Average count: {experiment.counts_averaged.mean():.1f}")
            
            if hasattr(experiment, 'resonance_frequencies') and experiment.resonance_frequencies:
                print(f"   Resonances found: {len(experiment.resonance_frequencies)}")
                for i, freq in enumerate(experiment.resonance_frequencies):
                    print(f"     Resonance {i+1}: {freq/1e9:.3f} GHz")
        
        print(f"\n🎉 Multi-waveform ODMR experiment completed successfully!")
        return 0
        
    except Exception as e:
        print(f"❌ Experiment failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

