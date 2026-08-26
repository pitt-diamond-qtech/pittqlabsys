# HP8350B External-Sweep Lab Setup

Guide for wiring and configuring the HP8350B sweep oscillator with NI-DAQ (PCI6229 / PCI6601) for stepped voltage ODMR sweeps.

This setup uses an **NI analog output voltage** to control microwave frequency on the HP8350B in **external sweep mode** (commands `SX` + `T3`), while photon counts are acquired on each voltage step.

## Hardware in this bench

| Device | Role |
|--------|------|
| **HP8350B** | Microwave source, external-sweep frequency control |
| **PCI6229** | Analog output (frequency voltage), counter and/or analog input |
| **PCI6601** (optional) | External sample clock when AO and counter both run on PCI6229 |
| **APD / photon counter** | Pulse input to DAQ counter (`count_mode=counter`) |
| **Photodiode** (optional) | Bright-signal readout on AI (`count_mode=analog`) |

## Wiring

```
PCI6229 AO0  ──────────────────────►  HP8350B external frequency input
APD pulses   ──────────────────────►  PCI6229 PFI1  (ctr0, counter mode)
Photodiode   ──────────────────────►  PCI6229 AI0    (analog mode, optional)
PCI6601 PFI31 (clock out) ─────────►  PCI6229 PFI0   (external clock, optional)
HP8350B GPIB ──────────────────────►  GPIB interface (e.g. GPIB0::19::INSTR)
```

### Notes

- **AO voltage span**: HP8350B external input is often 0–10 V. Match `voltage_min` / `voltage_max` in config to what the instrument expects.
- **Frequency span**: Set `start_frequency` / `stop_frequency` (FA / FB) to the sweep range you want in Hz.
- **Counter PFI**: Default template assumes APD on **PFI1** for `ctr0`. Change `counter_PFI_channel` in `config.json` if your wiring differs.
- **External clock**: When PCI6229 drives both AO and counter, use PCI6601 as the clock source (same pattern as `GalvoScan` with PCI6229 + PCI6601).

## Software setup

### 1. Sync from upstream

Pull the latest `contributions` branch before starting. See [Lab Workflow Guide](../development/lab-workflow.md) for fork/upstream instructions.

```bash
git fetch upstream
git checkout contributions
git pull upstream contributions
```

### 2. Create `config.json`

Copy the template and edit device names and addresses for your bench:

```bash
cp src/config.template.json config.json
```

Key sections in `config.json`:

- `devices.hp8350b` — GPIB address, frequency span, voltage calibration
- `devices.pci6229` — NI-MAX device name (`Dev1`), AO/counter/AI PFI mapping
- `devices.pci6601` — NI-MAX device name (`Dev2`), counter clock PFI mapping

### 3. Verify NI-MAX device names

Open **NI-MAX** and note the exact names (e.g. `Dev1`, `Dev2`). Update:

- `pci6229.settings.device`
- `pci6229.settings.external_daq` (usually the PCI6601 name)
- `pci6601.settings.device`

### 4. Verify HP8350B GPIB address

Check the address on the instrument front panel and set:

```json
"visa_resource": "GPIB0::19::INSTR"
```

## Running the test sweep

Start with mock hardware (no bench required):

```bash
python examples/hp8350b_voltage_sweep_example.py --mock-hardware
```

Then on the lab PC:

```bash
python examples/hp8350b_voltage_sweep_example.py --real-hardware
```

Use a custom config path if needed:

```bash
python examples/hp8350b_voltage_sweep_example.py --real-hardware --config path/to/config.json
```

### Count modes

| Mode | When to use | Config / flag |
|------|-------------|---------------|
| **Counter** (default) | Normal APD photon counting | `count_mode=counter` |
| **Analog** | Bright ensemble NV / photodiode | `--analog-mode` |

## What to verify on the bench

1. HP8350B connects over GPIB (`*IDN?` succeeds).
2. AO voltage on PCI6229 changes as expected during the sweep.
3. HP8350B output frequency tracks AO voltage (external sweep mode enabled).
4. Photon counts (or AI voltage in analog mode) vary with frequency.
5. RF output turns off after the sweep when `turn_off_after=True`.

## Related code and tests

| Path | Purpose |
|------|---------|
| `src/Controller/hp8350b.py` | HP8350B device driver |
| `src/Model/experiments/hp8350b_voltage_sweep.py` | Stepped sweep experiment |
| `examples/hp8350b_voltage_sweep_example.py` | Student runnable example |
| `tests/test_hp8350b.py` | Device unit tests (mock GPIB) |
| `tests/test_hp8350b_voltage_sweep.py` | Experiment tests (mock DAQ) |
| `tests/test_pci_daq_devices.py` | PCI6229 / PCI6601 mock tests |
| `src/config.template.json` | Device templates (`lab_setup_notes` summary) |

Run unit tests:

```bash
pytest tests/test_hp8350b.py tests/test_hp8350b_voltage_sweep.py tests/test_pci_daq_devices.py -v
```

## Data saving (interim)

Results are saved as **`.npz`** for now, consistent with other sweep examples on `contributions`. Lab-wide **HDF5** saving (`struct_hdf5` / `save_hdf5`) will arrive with **PR #11**. The current goal is confirming hardware and software wiring, not standardizing the file format.

## Troubleshooting

| Symptom | Things to check |
|---------|-----------------|
| HP8350B not found | GPIB cable, address in `visa_resource`, NI-VISA / Keysight driver |
| No counts | APD wiring to correct PFI, `counter_PFI_channel`, counter task in NI-MAX test panel |
| AO not sweeping | PCI6229 device name, AO channel in experiment settings |
| Timing glitches | Enable external clock via PCI6601; set `counter_daq=secondary` |
| Frequency doesn't track voltage | HP8350B in external sweep mode; FA/FB and voltage span match bench |

## See also

- [Lab Workflow Guide](../development/lab-workflow.md) — pulling from upstream, opening PRs
- [Hardware Connections](hardware-connections.md) — general DAQ wiring patterns
- [Device Configuration Reference](../../reference/device-configuration.md) — config.json structure
- [Testing with Mock](../development/testing-with-mock.md) — development without hardware
