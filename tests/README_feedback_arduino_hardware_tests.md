# Feedback Arduino Hardware Tests

This document explains how to run the Feedback Arduino tests with **mocked serial** (default) versus **real USB hardware**, using the same `RUN_HARDWARE_TESTS` pattern as `tests/README_adwin_hardware_tests.md`.

For a **step-by-step lab checklist** (COM port, example script, expected output), see [docs/conversions/feedback_arduino_lab_testing.md](../docs/conversions/feedback_arduino_lab_testing.md).

## Overview

Two test modules cover the driver and experiments:

| File | Mock tests (default) | Hardware tests (`@pytest.mark.hardware`) |
|------|----------------------|------------------------------------------|
| `tests/test_feedback_arduino.py` | Serial mocked; no Arduino | Opens a real serial port via fixture |
| `tests/test_feedback_arduino_experiments.py` | `FeedbackArduino` mocked | Loads `FeedbackArduino` from `src/config.json` |

Hardware-marked tests are **skipped unless** `RUN_HARDWARE_TESTS` is set to `1`. This is enforced in `tests/conftest.py` (same mechanism as ADwin hardware tests).

## Environment variable (lab PCs are Windows / PowerShell)

Set the variable in the **same shell** before `pytest`:

**Windows PowerShell (typical lab PC):**

```powershell
$env:RUN_HARDWARE_TESTS="1"
```

**macOS / Linux:**

```bash
export RUN_HARDWARE_TESTS=1
```

**Windows CMD:** `set RUN_HARDWARE_TESTS=1`

There is **no** `pytest --real-hardware` flag for these files; use the environment variable only.

## Usage

### 1. Mock mode (default, no hardware)

```bash
pytest tests/test_feedback_arduino.py -v
pytest tests/test_feedback_arduino_experiments.py -v
```

### 2. Real hardware — driver tests (`test_feedback_arduino.py`)

The `real_arduino_device` fixture uses **`com_port: "COM10"`** by default. If your Arduino is on another port, change that fixture or align your Windows COM port before running.

**PowerShell:**

```powershell
.venv\Scripts\Activate.ps1
$env:RUN_HARDWARE_TESTS="1"
pytest tests/test_feedback_arduino.py -m hardware -v
```

**bash:**

```bash
source .venv/bin/activate
export RUN_HARDWARE_TESTS=1
pytest tests/test_feedback_arduino.py -m hardware -v
```

### 3. Real hardware — experiment tests (`test_feedback_arduino_experiments.py`)

These tests call `load_devices_from_config` on **`src/config.json`**. Ensure a `feedback_arduino` device entry exists with the correct `com_port`. If the device is missing from config, the tests **skip** with a clear message.

**PowerShell:**

```powershell
$env:RUN_HARDWARE_TESTS="1"
pytest tests/test_feedback_arduino_experiments.py -m hardware -v
```

### 4. Run only non-hardware tests

```bash
pytest tests/test_feedback_arduino.py -m "not hardware" -v
pytest tests/test_feedback_arduino_experiments.py -m "not hardware" -v
```

### 5. Integration example (separate from pytest)

The script `examples/test_feedback_arduino_acquisition.py` uses its **own** `--real-hardware` flag (argparse), not pytest. See the lab testing guide above for menu-driven checks.

## Hardware-marked tests (names)

**Driver (`test_feedback_arduino.py`):**

- `test_real_hardware_connection`
- `test_real_hardware_status_query`
- `test_real_hardware_info_query`

**Experiments (`test_feedback_arduino_experiments.py`):**

- `test_acquire_block_real_hardware`
- `test_live_plot_real_hardware`

## Hardware requirements

- Arduino Due (or supported board) with **SIS Arduino_Analog_I/O** firmware
- USB cable; correct COM port in fixture and/or `src/config.json`
- Python deps from `requirements.txt` (including `pyserial`)

## Troubleshooting

### Hardware tests always skipped

- Confirm `RUN_HARDWARE_TESTS` is exactly `1` in the **current** terminal session.
- On PowerShell, use `$env:RUN_HARDWARE_TESTS="1"` with **no space** after `$env:`.

### `Could not open port` / connection errors

- Wrong COM port: update `src/config.json` for experiment tests, or the `real_arduino_device` fixture for driver tests.
- Port in use by another program (Serial Monitor, another Python process).

### Experiment hardware tests skipped (“not configured”)

- Add `feedback_arduino` under `devices` in `src/config.json` (file is gitignored; use your local lab copy).

## CI / development

CI and normal `pytest tests/` runs should leave `RUN_HARDWARE_TESTS` **unset** so hardware tests stay skipped. For a full suite without hardware markers in these files:

```bash
pytest tests/test_feedback_arduino.py tests/test_feedback_arduino_experiments.py -m "not hardware" -v
```

## Related documentation

- [docs/conversions/feedback_arduino_lab_testing.md](../docs/conversions/feedback_arduino_lab_testing.md) — lab PC procedure, example script, expected results
- [docs/conversions/matlab_to_python_2026-05-14.md](../docs/conversions/matlab_to_python_2026-05-14.md) — MATLAB to Python conversion notes
