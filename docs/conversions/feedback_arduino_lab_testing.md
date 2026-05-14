# Feedback Arduino Lab PC Testing Guide

**Date:** 2026-05-14  
**Branch:** matlab-conversion  
**Hardware:** Arduino Due with feedback controller firmware

This document provides a minimal testing strategy for validating the FeedbackArduino device driver and experiment classes on the lab PC with real hardware.

## Prerequisites

- Arduino Due connected via USB
- Firmware: SIS Arduino_Analog_I/O
- Lab PC: Windows with correct COM port identified
- Python environment: pittqlabsys/.venv activated

---

## 1. Pre-flight: Config Setup (2 minutes)

### Verify COM Port
Check Device Manager (Windows) or run:
```bash
ls /dev/tty*  # Linux/macOS
```

### Update config.json
Ensure your `config.json` contains the Arduino entry with the correct COM port:

```json
{
  "devices": {
    "feedback_arduino": {
      "class": "FeedbackArduino",
      "settings": {
        "com_port": "COM10"  // ← Update this to match your system
      }
    }
  }
}
```

**Common ports:**
- Windows: `COM3`, `COM10`, etc.
- Linux: `/dev/ttyACM0`, `/dev/ttyUSB0`
- macOS: `/dev/tty.usbmodem*`

---

## 2. Core Hardware Tests (5 minutes)

From the `pittqlabsys` root directory:

```bash
source .venv/bin/activate  # Or: .venv\Scripts\activate on Windows

# Test 1: Basic connection and device ID
pytest tests/test_feedback_arduino.py::test_real_hardware_connection -v -s

# Test 2: Status probe query
pytest tests/test_feedback_arduino.py::test_hardware_status_probe -v -s

# Test 3: Info probe query
pytest tests/test_feedback_arduino.py::test_hardware_info_probe -v -s
```

### Expected Results

**Test 1 (Connection):**
```
assert 'SIS Arduino_Analog_I/O' in response
PASSED
```

**Test 2 (Status):**
```python
{
    'is_acquiring': False,
    'mode': 0,  # or 2
    'uptime_ms': <some value>,
    # ...
}
PASSED
```

**Test 3 (Info):**
```python
{
    'adc_n_channels': 4,
    'adc_sample_rate_hz': <sample rate>,
    'dac_n_channels': 2,
    # ...
}
PASSED
```

### Troubleshooting

| Issue | Likely Cause | Fix |
|-------|--------------|-----|
| `Could not open port` | Wrong COM port or permissions | Check Device Manager, update config.json |
| `Timeout` | Arduino not responding | Check USB cable, restart Arduino |
| `Checksum mismatch` | Baud rate wrong or cable issue | Verify 115200 baud in driver |
| Device ID not found | Wrong firmware | Flash correct firmware to Arduino |

**⚠️ Stop here if any test fails** — indicates serial/firmware issue that must be resolved before proceeding.

---

## 3. Basic Acquisition Test (3 minutes)

Run the integration example script:

```bash
python examples/test_feedback_arduino_acquisition.py --real-hardware --com-port COM10
```

### Test Sequence

From the menu, select:

**Test 3: Acquire Block (Single-shot triggered acquisition)**

This runs `FeedbackArduinoAcquireBlock` experiment with real hardware.

### Expected Results

**Terminal output:**
```
Block acquired: 64 samples × 4 channels
Samples shape: (64, 4)
Sample range: [-2048, 2047] (12-bit ADC)
```

**Plot display:**
- Matplotlib window opens with 4 subplots (Channels A, B, C, D)
- Each subplot shows ADC waveform with 64 samples
- Waveforms should show noise or signal depending on inputs
- No timeout or `kind='none'` errors

### Trigger Considerations

If acquisition times out:
- **Trigger threshold too high:** Lower `trig_level` in experiment settings
- **No signal on trigger channel:** Connect signal source or use different channel
- **Trigger mode disabled:** Verify `mode=2` (scope mode) in device

---

## 4. (Optional) Live Streaming Test (2 minutes)

From the same example script menu, select:

**Test 4: Live Plot (Continuous streaming)**

This runs `FeedbackArduinoLivePlot` experiment in filter mode (mode 0).

### Expected Results

**Terminal output:**
```
Starting live data acquisition
Entering acquisition loop (max_runtime=5.0s)
Acquisition complete: 150 blocks in 5.0s (30.00 blocks/s)
'None' responses: 12
```

**Behavior:**
- Rolling history updates smoothly in real-time
- Block acquisition rate: 20-40 blocks/s typical
- `'None' responses` should be < 20% of total polls
- No excessive timeouts or crashes

### Performance Notes

- **High 'None' count (>50%):** USB bandwidth issue or decimator too low
- **Low block rate (<10/s):** Increase `pause_dt` or reduce `usb_data_n`
- **Plot lag:** Reduce `history_blocks` to decrease plot update overhead

Let it run for 5-10 seconds, then stop with Ctrl+C or let it complete.

---

## What This Validates

✅ **Serial communication** — Checksum calculation, command framing, response parsing  
✅ **Binary data parsing** — Little-endian int16 conversion, channel deinterleaving  
✅ **Trigger detection** — Scope mode (mode 2) with level/channel/slope config  
✅ **Continuous streaming** — Filter mode (mode 0) with rolling history buffers  
✅ **Config.json integration** — Device registration and settings override  
✅ **Experiment framework** — _function()/_plot() lifecycle, self.data storage  

---

## Full Regression Suite (Optional)

Once the above tests pass, you can run the full hardware-marked test suite:

```bash
# All hardware tests for device driver
pytest tests/test_feedback_arduino.py -m hardware -v

# All hardware tests for experiments
pytest tests/test_feedback_arduino_experiments.py -m hardware -v
```

This is recommended before merging to main, but not required for initial validation.

---

## Next Steps After Validation

1. **If all tests pass:**
   - Document any hardware-specific quirks (trigger levels, polling rates)
   - Merge matlab-conversion branch to main
   - Add Arduino to production config.json

2. **If issues found:**
   - Log errors and device responses
   - Check firmware version compatibility
   - Verify ADC input ranges and connections
   - Consult MATLAB scripts for expected behavior

---

## Contact

For issues or questions about this testing procedure:
- Check: `docs/conversions/matlab_to_python_2026-05-14.md` for conversion details
- Review: MATLAB originals in `/Users/gurudevdutt/ClaudeProjects/matlab-feedback-arduinos`
- Hardware specs: Arduino Due datasheet, firmware documentation

**Testing completed:** ___________  
**Hardware validated:** ☐ Yes  ☐ No  
**Issues found:** _________________________________________________
