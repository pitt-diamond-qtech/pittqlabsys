# AWG520 + ADwin Integration Testing

This directory contains tools to test the integration between ADwin and AWG520 for external trigger control and compression testing.

## Files

### Test Scripts
- **`test_adwin_trigger.py`**: Tests ADwin's ability to generate precise trigger pulses
- **`generate_test_sequences.py`**: Generates test waveforms and sequence files for AWG520

### Documentation
- **`docs/AWG520_ADWIN_TESTING.md`**: Comprehensive testing guide with wiring diagrams

## Quick Start

### 1. Test ADwin Trigger Capability
```bash
cd examples/awg520_testing
python test_adwin_trigger.py
```

This will test:
- Basic trigger generation
- Precise timing accuracy
- Trigger sequences
- AWG520 simulation

### 2. Generate AWG520 Test Files
```bash
python generate_test_sequences.py
```

This will create:
- Test waveform files (.wfm)
- Test sequence files (.seq)
- Compression analysis
- Test instructions

### 3. Hardware Setup
Follow the wiring diagram in `docs/AWG520_ADWIN_TESTING.md`:
- Connect ADwin DIO output to AWG520 TRIG IN
- Use 50Ω BNC cable
- Connect grounds together

### 4. AWG520 Configuration
- Set Run Mode = Enhanced
- Set Trigger Source = External
- Set Trigger Level = 2.5V
- Set Input Impedance = 50Ω

## Test Sequences

### Basic Test (test_basic.seq)
Tests basic external trigger functionality with 3 different pulse types.

### Compression Test (test_compression.seq)
Tests repeat field compression for dead times:
- 1μs dead time × 10,000 reps = 10μs total
- 10μs dead time × 100,000 reps = 100μs total

### Memory Test (test_memory.seq)
Tests memory usage with 100 sequence lines.

## Expected Results

- **ADwin**: Should generate precise triggers with <100μs timing accuracy
- **AWG520**: Should respond to external triggers and execute sequences
- **Compression**: Should reduce memory usage significantly using repeat field
- **Memory**: Sequences should fit within 8MB AWG520 limit

## Troubleshooting

### Common Issues
1. **No trigger response**: Check trigger level, impedance, and source settings
2. **Waveform corruption**: Verify BNC connections and grounding
3. **Memory overflow**: Reduce repeat counts or sequence complexity
4. **Timing issues**: Check sample rate and sequence configuration

### Debug Steps
1. Use oscilloscope to verify trigger signal integrity
2. Check AWG520 error messages and status displays
3. Verify sequence file format and syntax
4. Test with simpler sequences to isolate issues

## Next Steps

After successful testing:
1. Implement full pulsed ODMR sequence
2. Optimize repeat field usage for maximum compression
3. Integrate with existing mux control architecture
4. Test with real quantum experiments

## Hardware Requirements

- ADwin Gold II with digital I/O capability
- AWG520 with external trigger support
- 50Ω BNC cable (male to male)
- Oscilloscope for signal monitoring (optional)
- Ground connection wire
