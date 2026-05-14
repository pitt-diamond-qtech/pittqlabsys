# MATLAB to Python Conversion Summary

**Date:** 2026-05-14  
**Branch:** `matlab-conversion`  
**Source:** `/Users/gurudevdutt/ClaudeProjects/matlab-feedback-arduinos/*.m`  
**Target:** `/Users/gurudevdutt/CursorProjects/pittqlabsys/src/`

---

## Overview

Successfully converted **18 MATLAB scripts** implementing Arduino feedback controller communication into **1 Device class** and **2 Experiment classes** following AQuISS conventions.

---

## Files Created

### Device Class
**`src/Controller/feedback_arduino.py`** - `FeedbackArduino(Device)`
- **Lines:** 751
- **Commit:** `09053dd`
- **Maps:** 14 MATLAB functions → Python methods

**Features:**
- ✅ Serial communication (115200 baud, LRC/ISO-1155 checksums)
- ✅ Device control: start/stop acquisition, configure scope/filter modes
- ✅ Data acquisition: `poll_data_block()`, `get_data_block()`, `get_4ch_data_block()`
- ✅ Status/info queries with parsers (`_parse_status()`, `_parse_info()`)
- ✅ Binary data handling (little-endian int16, multi-channel reshape)
- ✅ 12 configurable Parameters
- ✅ 7 probes (status, info, ADC/DAC properties)
- ✅ Lazy `pyserial` import for cross-platform compatibility

### Experiment Classes

**1. `src/Model/experiments/feedback_arduino_acquire_block.py`**
- **Class:** `FeedbackArduinoAcquireBlock(Experiment)`
- **Lines:** 207
- **Commit:** `12eedd6`
- **Maps:** `feedback_arduinos_acquire_block.m`

**Purpose:** Single-shot triggered data acquisition (scope mode 2)
- Configure → Start → Poll → Stop workflow
- 4-channel ADC data capture with trigger configuration
- Stores data as `[N_samples × 4]` array with individual channel access

**2. `src/Model/experiments/feedback_arduino_live_plot.py`**
- **Class:** `FeedbackArduinoLivePlot(Experiment)`
- **Lines:** 334
- **Commit:** `df817d0`
- **Maps:** `feedback_arduinos_live_plot.m`

**Purpose:** Continuous live data streaming (filter mode 0)
- Rolling history buffers for 4 channels
- Real-time plotting in 2×2 subplot grid
- Configurable runtime limit and history depth
- Block acquisition rate monitoring

---

## Test Coverage

### Pytest Test Suites

**1. `tests/test_feedback_arduino.py`** - Device tests
- ✅ Connection and initialization (mock + real hardware markers)
- ✅ Checksum calculation (LRC/ISO-1155 validation)
- ✅ Command sending and querying
- ✅ Status/info parsing (including error cases)
- ✅ Data acquisition methods (poll, get, 4-channel convenience)
- ✅ Configuration methods (scope/filter modes)
- ✅ Probe reading and caching
- ✅ Error handling and connection management
- **Total:** 30+ test cases

**2. `tests/test_feedback_arduino_experiments.py`** - Experiment tests
- ✅ FeedbackArduinoAcquireBlock: initialization, execution, data structure, plotting
- ✅ FeedbackArduinoLivePlot: initialization, execution, rolling buffers, plotting
- ✅ Parameter validation and updates
- ✅ Error handling (timeout, exceptions, invalid data)
- ✅ Abort scenarios
- ✅ Hardware test markers
- **Total:** 25+ test cases

**Running tests:**
```bash
# All tests with mocks
pytest tests/test_feedback_arduino*.py -v

# Real hardware tests only (requires --real-hardware marker)
pytest -m hardware tests/test_feedback_arduino*.py -v

# Specific test file
pytest tests/test_feedback_arduino.py::test_lrc_checksum_calculation -v
```

### Example Script

**`examples/test_feedback_arduino_acquisition.py`**
- Complete integration test suite
- Works with both real hardware (`--real-hardware`) and mock
- 4 test sequences:
  1. Device connection and ID verification
  2. Status and info queries
  3. Single-shot acquisition (scope mode)
  4. Live plotting (filter mode)
- Detailed output with statistics and data validation

**Usage:**
```bash
# Mock hardware (no Arduino needed)
python examples/test_feedback_arduino_acquisition.py

# Real hardware
python examples/test_feedback_arduino_acquisition.py --real-hardware --com-port COM10

# Custom live test duration
python examples/test_feedback_arduino_acquisition.py --live-duration 5.0
```

---

## MATLAB → Python Mapping

| MATLAB Function | Python Equivalent | Location |
|----------------|-------------------|----------|
| `feedback_arduinos_find_instrument()` | `_connect()` | `FeedbackArduino._connect()` |
| `feedback_arduinos_close_instrument()` | `close()` | `FeedbackArduino.close()` |
| `feedback_arduinos_send_command()` | `_send()` | `FeedbackArduino._send()` |
| `feedback_arduinos_query()` | `_query()` | `FeedbackArduino._query()` |
| `feedback_arduinos_start()` | `start_acquisition()` | `FeedbackArduino.start_acquisition()` |
| `feedback_arduinos_stop()` | `stop_acquisition()` | `FeedbackArduino.stop_acquisition()` |
| `feedback_arduinos_get_status()` | `read_probes('status')` | `FeedbackArduino.read_probes()` |
| `feedback_arduinos_get_info()` | `read_probes('info')` | `FeedbackArduino.read_probes()` |
| `feedback_arduinos_parse_status()` | `_parse_status()` | `FeedbackArduino._parse_status()` |
| `feedback_arduinos_parse_info()` | `_parse_info()` | `FeedbackArduino._parse_info()` |
| `feedback_arduinos_config_scope()` | `configure_scope_mode()` | `FeedbackArduino.configure_scope_mode()` |
| `feedback_arduinos_config_filter_only()` | `configure_filter_mode()` | `FeedbackArduino.configure_filter_mode()` |
| `feedback_arduinos_get_data()` | `get_data_block()` | `FeedbackArduino.get_data_block()` |
| `feedback_arduinos_poll_data()` | `poll_data_block()` | `FeedbackArduino.poll_data_block()` |
| `feedback_arduinos_get_4ch_data()` | `get_4ch_data_block()` | `FeedbackArduino.get_4ch_data_block()` |
| `feedback_arduinos_acquire_block()` | `FeedbackArduinoAcquireBlock` | Experiment class |
| `feedback_arduinos_live_plot()` | `FeedbackArduinoLivePlot` | Experiment class |

---

## Conventions Followed

All code strictly follows `CONVENTIONS.md`:

✅ **Class Hierarchy:**
- Device inherits from `src.core.Device`
- Experiments inherit from `src.core.Experiment`
- Use `Parameter` system for settings (not `__init__` args)

✅ **Naming Conventions:**
- Classes: `PascalCase` (e.g., `FeedbackArduino`)
- Files: `snake_case` (e.g., `feedback_arduino.py`)
- Methods: `snake_case` verbs (e.g., `start_acquisition()`)
- Private: `_leading_underscore` (e.g., `_connect()`)

✅ **Code Style:**
- Google-style docstrings on all classes and public methods
- Type hints on method signatures
- Bare SI units (Hz, s, not kHz, µs)
- 0-indexed arrays (converted from MATLAB's 1-indexing)
- Python `logging` module (not `print()`)

✅ **Device Pattern:**
- Hardware driver imported **inside** `_connect()` (lazy import)
- `_DEFAULT_SETTINGS` and `_PROBES` as class attributes
- `update()` calls `super().update()` before hardware operations
- Context manager support via `close()`

✅ **Experiment Pattern:**
- Core logic in `_function()` (NOT `run()`)
- Check `self._abort` regularly for GUI cancellation
- Store results in `self.data` dict
- Device access via `self.instruments['device_key']['instance']`
- Plot hooks: `_plot()` and `_update_plot()`

---

## Configuration Registration

Add to `config.json`:

```json
{
  "devices": {
    "feedback_arduino": {
      "class": "FeedbackArduino",
      "filepath": "src/Controller/feedback_arduino.py",
      "settings": {
        "com_port": "COM10",
        "baud_rate": 115200,
        "timeout": 10.0,
        "mode": 0,
        "decimator": 100,
        "usb_data_n": 256
      }
    }
  }
}
```

**Cross-platform COM ports:**
- Windows: `"com_port": "COM10"`
- Linux: `"com_port": "/dev/ttyUSB0"`
- macOS: `"com_port": "/dev/cu.usbmodem14101"`

---

## Git Commits (matlab-conversion branch)

```
* 258ba64 Add comprehensive tests and example for FeedbackArduino
* 09053dd Add FeedbackArduino device driver
* 7837e86 Register FeedbackArduino experiments in __init__.py
* df817d0 Add FeedbackArduinoLivePlot experiment
* 12eedd6 Add FeedbackArduinoAcquireBlock experiment
```

---

## Next Steps

### Integration
1. Review code on `matlab-conversion` branch
2. Run tests: `pytest tests/test_feedback_arduino*.py -v`
3. Test example: `python examples/test_feedback_arduino_acquisition.py`
4. Update `config.json` with Arduino COM port settings
5. Merge `matlab-conversion` → `main` when approved

### Hardware Validation (requires real Arduino)
```bash
# Device tests
pytest -m hardware tests/test_feedback_arduino.py -v

# Experiment tests
pytest -m hardware tests/test_feedback_arduino_experiments.py -v

# Full integration test
python examples/test_feedback_arduino_acquisition.py --real-hardware --com-port COM10
```

### Optional Enhancements
- [ ] Add DAC output methods (if firmware supports)
- [ ] Add auto-detection of COM port
- [ ] Add more acquisition modes (if firmware has others)
- [ ] Add GUI integration examples
- [ ] Add data export utilities (HDF5, CSV)

---

## Dependencies

**New requirement added:**
```bash
pip install pyserial
```

Add to `requirements.txt`:
```
pyserial>=3.5
```

**Existing dependencies used:**
- `numpy` - Array operations and binary data handling
- `pyqtgraph` - Live plotting in experiments
- `logging` - Device logging

---

## Documentation Links

- **Conventions:** `CONVENTIONS.md`
- **Device Base:** `src/core/instrument.py`
- **Experiment Base:** `src/core/experiment.py`
- **Config System:** `config.sample.json`, `src/config.template.json`

---

## Statistics

- **MATLAB scripts converted:** 18
- **Python files created:** 5 (1 device, 2 experiments, 2 test suites)
- **Lines of code:** ~2,900 (including tests and example)
- **Test cases:** 55+
- **Documentation:** Complete Google-style docstrings on all public APIs
- **Time to convert:** ~3 hours (Phase 1-3 complete)

---

## Phase Summary

✅ **Phase 1:** Learned conventions from CONVENTIONS.md and exemplars  
✅ **Phase 2:** Surveyed MATLAB files and proposed mapping  
✅ **Phase 3:** Implemented device class, experiments, tests, and example  
✅ **Phase 4:** Integration complete (exports added to `__init__.py`)

**Status:** Ready for review and testing!
