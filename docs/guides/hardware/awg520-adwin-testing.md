# AWG520 + ADwin Integration Testing Guide

## Overview
This document provides practical testing procedures to verify AWG520 external trigger capabilities and ADwin integration for our new approach to pulsed ODMR experiments that aneeds to be tested first. The idea here is that we currently have the AWG520 setup to provide a trigger to the Adwin. But this forces us to use the AWG520 in a way that is not suitable for long sequences, because of restrictions on the programming capabilities and its waveform memory limit. The alternate way is to use the Adwin to trigger the AWG520 which I believe would allow us to output long sequences more easily. But first this idea needs to be tested. The test wiring setup and the code are shown below. 

## Hardware Setup

### Wiring Diagram
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     ADwin       │    │    BNC Cable    │    │    AWG520       │
│                 │    │   (50Ω coax)    │    │                 │
│  Digital Out    │────│                 │────│  TRIG IN       │
│  (TTL 0→5V)    │    │                 │    │  (Rear Panel)  │
│                 │    │                 │    │                 │
│  GND           │────│                 │────│  Chassis GND   │
└─────────────────┘    └─────────────────┘    └─────────────────┘

Optional Monitoring:
┌─────────────────┐
│  Oscilloscope   │
│                 │
│  BNC T-connector│
│  (monitor both  │
│   signals)      │
└─────────────────┘
```

### Connection Details
- **ADwin Digital Output**: Any available DIO line (e.g., DIO 0)
- **BNC Cable**: 50Ω impedance, BNC male to BNC male
- **AWG520 TRIG IN**: Rear panel BNC connector
- **Ground Connection**: ADwin GND to AWG520 chassis ground
- **Optional**: BNC T-connector for oscilloscope monitoring

## AWG520 Configuration

### Front Panel Settings
1. **SETUP → Trigger → Source = External**
2. **SETUP → Trigger → Level = 2.5V** (for 0→5V TTL input)
3. **SETUP → Trigger → Impedance = 50Ω**
4. **SETUP → Run Mode = Enhanced** (enables Wait Trigger)

### Sequence Editor Settings
1. **Wait Trigger Column = ON** for lines that should wait
2. **Jump Mode = Goto** (simple sequential advancement)
3. **Timing = Sync** (finish current waveform before jumping)

## Test Sequence Files

### Basic Test Sequence (test_basic.seq)
```
# Test basic external trigger functionality
# Format: ch1_wfm, ch2_wfm, repeat, wait_trigger, goto, logic_jump_target

test_pulse_1.wfm, test_pulse_1.wfm, 1, ON, goto, 2
test_pulse_2.wfm, test_pulse_2.wfm, 1, ON, goto, 3
test_pulse_3.wfm, test_pulse_3.wfm, 1, ON, goto, 1
```

### Compression Test Sequence (test_compression.seq)
```
# Test repeat field compression for dead times
# Format: ch1_wfm, ch2_wfm, repeat, wait_trigger, goto, logic_jump_target

short_pulse.wfm, short_pulse.wfm, 1000, ON, goto, 2      # 1000 reps = 1μs
dead_time_1us.wfm, dead_time_1us.wfm, 10000, ON, goto, 3 # 10000 reps = 10μs
long_pulse.wfm, long_pulse.wfm, 1000, ON, goto, 4        # 1000 reps = 1μs
dead_time_10us.wfm, dead_time_10us.wfm, 100000, ON, goto, 1 # 100000 reps = 100μs
```

## Test Waveforms

### Simple Test Waveforms
- **test_pulse_1.wfm**: 100ns square pulse, amplitude 1V
- **test_pulse_2.wfm**: 200ns Gaussian pulse, amplitude 0.8V
- **test_pulse_3.wfm**: 150ns sech pulse, amplitude 0.9V

### Compression Test Waveforms
- **short_pulse.wfm**: 1ns square pulse, amplitude 1V
- **dead_time_1us.wfm**: 1μs of zeros (1000 samples at 1GHz)
- **long_pulse.wfm**: 1μs square pulse, amplitude 1V
- **dead_time_10us.wfm**: 10μs of zeros (10000 samples at 1GHz)

## Test Procedures

### Test 1: Basic External Trigger
1. **Load test_basic.seq** into AWG520
2. **Press RUN** on AWG520
3. **Verify AWG520 displays "Waiting"**
4. **Send trigger pulse from ADwin**
5. **Verify AWG520 outputs test_pulse_1.wfm**
6. **Verify AWG520 returns to "Waiting"**
7. **Send second trigger pulse**
8. **Verify AWG520 outputs test_pulse_2.wfm**
9. **Continue for all test pulses**

### Test 2: Repeat Field Compression
1. **Load test_compression.seq** into AWG520
2. **Press RUN** on AWG520
3. **Send trigger pulse from ADwin**
4. **Verify AWG520 outputs short_pulse × 1000 reps**
5. **Verify AWG520 outputs dead_time_1us × 10000 reps**
6. **Send second trigger pulse**
7. **Verify AWG520 outputs long_pulse × 1000 reps**
8. **Verify AWG520 outputs dead_time_10us × 100000 reps**

### Test 3: Memory Usage Verification
1. **Check AWG520 memory usage** before loading sequence
2. **Load test_compression.seq**
3. **Check memory usage** after loading
4. **Calculate compression ratio**: Original vs. Compressed memory
5. **Verify sequence fits** within 8MB limit

### Test 4: Timing Accuracy
1. **Use oscilloscope** to measure trigger timing
2. **Verify AWG520 response time** to external trigger
3. **Check waveform timing accuracy** after trigger
4. **Measure jitter** between trigger and waveform start

## Expected Results

### Success Criteria
- **AWG520 responds** to external triggers within 100ns
- **Waveforms output correctly** after each trigger
- **Memory usage reduced** by repeat field compression
- **Timing preserved** for all waveform components
- **Sequence fits** within AWG520 memory limits

### Failure Modes
- **AWG520 doesn't respond** to external triggers
- **Waveforms corrupted** or timing incorrect
- **Memory usage not reduced** by compression
- **Sequence exceeds** memory limits
- **Timing jitter** exceeds acceptable limits

## Troubleshooting

### Common Issues
1. **No trigger response**: Check trigger level, impedance, and source settings
2. **Waveform corruption**: Verify BNC connections and grounding
3. **Memory overflow**: Reduce repeat counts or sequence complexity
4. **Timing issues**: Check sample rate and sequence configuration

### Debug Steps
1. **Use oscilloscope** to verify trigger signal integrity
2. **Check AWG520 error messages** and status displays
3. **Verify sequence file format** and syntax
4. **Test with simpler sequences** to isolate issues

## Next Steps After Testing

### If External Trigger Works
1. **Implement full pulsed ODMR sequence**
2. **Optimize repeat field usage** for maximum compression
3. **Integrate with existing mux control architecture**
4. **Test with real quantum experiments**

### If External Trigger Fails
1. **Investigate alternative AWG520 control methods**
2. **Consider software jump commands** over GPIB/Ethernet
3. **Explore different compression strategies**
4. **Reassess hardware architecture** requirements

## Hardware Requirements Checklist

- [ ] ADwin Gold II with digital I/O capability
- [ ] AWG520 with external trigger support
- [ ] 50Ω BNC cable (male to male)
- [ ] Oscilloscope for signal monitoring (optional)
- [ ] BNC T-connector for monitoring (optional)
- [ ] Ground connection wire

## Software Requirements Checklist

- [ ] ADwin development environment
- [ ] AWG520 sequence editor
- [ ] Test sequence files (.seq)
- [ ] Test waveform files (.wfm)
- [ ] Monitoring and analysis tools
