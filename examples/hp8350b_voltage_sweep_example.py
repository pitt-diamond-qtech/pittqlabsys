#!/usr/bin/env python3
"""
HP8350B Voltage Sweep Example

Runs a stepped voltage sweep on an NI-DAQ analog output while counting photons.
The AO voltage controls HP8350B frequency in external sweep mode. Results are
saved as counts vs frequency.

Data is saved as .npz for now (same as other sweep examples on contributions).
Lab-wide HDF5 saving (struct_hdf5 / save_hdf5) arrives with PR #11; the goal
here is verifying hardware and software wiring, not the file format.

Lab setup: see docs/guides/hardware/hp8350b-lab-setup.md
  (summary also in config.template.json → lab_setup_notes)
  - PCI6229 AO0 -> HP8350B external frequency input
  - APD pulses   -> PCI6229 ctr0 (or PCI6601 if using external clock)
  - Photodiode   -> PCI6229 AI0  (use --analog-mode for bright signals)

Usage:
    python examples/hp8350b_voltage_sweep_example.py --mock-hardware
    python examples/hp8350b_voltage_sweep_example.py --real-hardware
    python examples/hp8350b_voltage_sweep_example.py --real-hardware --analog-mode
    python examples/hp8350b_voltage_sweep_example.py --real-hardware --config path/to/config.json
"""

import argparse
import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

_spec = importlib.util.spec_from_file_location(
    "hp8350b_voltage_sweep",
    Path(__file__).parent.parent / "src/Model/experiments/hp8350b_voltage_sweep.py",
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
HP8350BVoltageSweep = _mod.HP8350BVoltageSweep


def load_devices_from_config(config_path: Path, use_mock: bool):
    """Load device instances from config.json or use mocks."""
    if use_mock:
        from src.Controller import MockHP8350B, MockNI6229, MockPCI6601
        return {
            'hp8350b': {'instance': MockHP8350B()},
            'daq': {'instance': MockNI6229()},
            'daq2': {'instance': MockPCI6601()},
        }

    from src.core.device_config import load_devices_from_config as load_cfg
    loaded, failed = load_cfg(config_path, raise_errors=False)
    if failed:
        print(f"Warning: failed to load devices: {failed}")

    required = ['hp8350b', 'pci6229']
    mapping = {
        'hp8350b': 'hp8350b',
        'pci6229': 'daq',
        'pci6601': 'daq2',
    }
    devices = {}
    for cfg_key, role in mapping.items():
        if cfg_key in loaded:
            devices[role] = {'instance': loaded[cfg_key]}
        elif cfg_key == 'pci6601' and role == 'daq2':
            continue
        elif cfg_key in required:
            raise RuntimeError(
                f"Required device '{cfg_key}' not found in config. "
                f"Copy config.template.json to config.json and update lab settings."
            )
    return devices


def run_sweep(
    use_mock=False,
    config_path=None,
    analog_mode=False,
    num_points=50,
    start_ghz=2.80,
    stop_ghz=2.95,
    save_data=True,
):
    print("=" * 60)
    print("HP8350B VOLTAGE SWEEP")
    print("=" * 60)
    print(f"Mode: {'mock' if use_mock else 'real'} hardware")
    print(f"Count mode: {'analog (photodiode)' if analog_mode else 'counter (APD)'}")

    cfg_path = Path(config_path) if config_path else Path(__file__).parent.parent / "config.json"
    devices = load_devices_from_config(cfg_path, use_mock)

    settings = {
        'sweep': {
            'start_frequency': start_ghz * 1e9,
            'stop_frequency': stop_ghz * 1e9,
            'num_points': num_points,
            'voltage_min': 0.0,
            'voltage_max': 10.0,
        },
        'count_mode': 'analog' if analog_mode else 'counter',
        'counter_daq': 'secondary' if 'daq2' in devices else 'same',
        'use_external_counter_clock': 'daq2' in devices,
        'microwave': {'power': -10.0, 'turn_off_after': True},
        'timing': {'time_per_pt': 0.010, 'settle_time': 0.002},
    }

    experiment = HP8350BVoltageSweep(
        devices=devices,
        name="HP8350B_Voltage_Sweep",
        settings=settings,
    )

    print(f"\nSweep: {start_ghz:.3f} - {stop_ghz:.3f} GHz, {num_points} points")
    print("Running sweep...")
    experiment.run()

    data = experiment.data
    print(f"\nResults ({len(data['counts'])} points):")
    print(f"  Mean counts: {np.mean(data['counts']):.2f}")
    print(f"  Frequency range: {data['frequency_ghz'][0]:.4f} - {data['frequency_ghz'][-1]:.4f} GHz")

    if save_data:
        save_results(data, settings, use_mock)

    plot_results(data, analog_mode)
    return data


def save_results(data, settings, use_mock):
    # Interim .npz format until PR #11 (struct_hdf5) lands on contributions.
    output_dir = Path.home() / "Experiments" / "hp8350b_sweeps"
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    tag = "mock" if use_mock else "real"

    npz_file = output_dir / f"hp8350b_sweep_{tag}_{timestamp}.npz"
    np.savez(
        npz_file,
        voltages=data['voltages'],
        frequencies=data['frequencies'],
        counts=data['counts'],
        count_mode=data['count_mode'],
    )

    meta_file = output_dir / f"hp8350b_sweep_{tag}_{timestamp}_settings.json"
    with open(meta_file, 'w') as f:
        json.dump(settings, f, indent=2)

    print(f"\nSaved data to {npz_file}")
    print(f"Saved settings to {meta_file}")


def plot_results(data, analog_mode):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

    ylabel = 'AI voltage (V)' if analog_mode else 'Counts (kcps)'
    ax1.plot(data['frequency_ghz'], data['counts'], 'b.-')
    ax1.set_ylabel(ylabel)
    ax1.set_title('HP8350B sweep: signal vs frequency')
    ax1.grid(True, alpha=0.3)

    ax2.plot(data['voltages'], data['counts'], 'r.-')
    ax2.set_xlabel('AO voltage (V)')
    ax2.set_ylabel(ylabel)
    ax2.set_title('Signal vs AO voltage')
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    try:
        out = Path.home() / "Experiments" / "hp8350b_sweeps" / "hp8350b_sweep_preview.png"
        out.parent.mkdir(parents=True, exist_ok=True)
    except (PermissionError, OSError):
        out = Path(__file__).parent / "hp8350b_sweep_preview.png"
    fig.savefig(out, dpi=150)
    print(f"Plot saved to {out}")


def main():
    parser = argparse.ArgumentParser(description='HP8350B voltage sweep example')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--real-hardware', action='store_true', help='Use real lab hardware')
    group.add_argument('--mock-hardware', action='store_true', help='Use mock devices (default)')
    parser.add_argument('--config', type=str, default=None, help='Path to config.json')
    parser.add_argument('--analog-mode', action='store_true',
                        help='Use analog input (photodiode) instead of counter')
    parser.add_argument('--num-points', type=int, default=50, help='Number of sweep points')
    parser.add_argument('--start-ghz', type=float, default=2.80, help='Start frequency (GHz)')
    parser.add_argument('--stop-ghz', type=float, default=2.95, help='Stop frequency (GHz)')
    parser.add_argument('--no-save', action='store_true', help='Do not save data files')
    args = parser.parse_args()

    use_mock = not args.real_hardware
    run_sweep(
        use_mock=use_mock,
        config_path=args.config,
        analog_mode=args.analog_mode,
        num_points=args.num_points,
        start_ghz=args.start_ghz,
        stop_ghz=args.stop_ghz,
        save_data=not args.no_save,
    )
    return 0


if __name__ == '__main__':
    sys.exit(main())
