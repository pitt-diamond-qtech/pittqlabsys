# ADwin→AWG520 External Trigger Testing

This directory contains test files to verify the new control architecture where **ADwin generates trigger pulses to control AWG520 sequence advancement**, instead of the traditional AWG520→ADwin control.

## 🎯 **Test Objective**

Verify that the ADwin can successfully control AWG520 sequence progression using external triggers, enabling:
- **Longer sequences** that fit within AWG520 memory limits
- **Better memory optimization** using repeat field compression
- **Computer-controlled sequence advancement** via JUMP_MODE software

## 🔌 **Hardware Setup**

### Wiring Diagram
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     ADwin       │    │    BNC Cable    │    │    AWG520       │
│                 │    │   (50Ω coax)    │    │                 │
│  Digital Out    │────│                 │────│  TRIG IN       │
│  (DIO 0)       │    │                 │    │  (Rear Panel)  │
│                 │    │                 │    │                 │
│  GND           │────│                 │────│  Chassis GND   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Connection Details
- **ADwin Digital Output**: DIO 0 (configurable in ADbasic)
- **BNC Cable**: 50Ω impedance, BNC male to BNC male
- **AWG520 TRIG IN**: Rear panel BNC connector
- **Ground Connection**: ADwin GND to AWG520 chassis ground

## 📁 **Test Files**

### 1. ADbasic Trigger Program
- **File**: `awg520_trigger_test.bas`
- **Purpose**: Generates trigger pulses at specified intervals
- **Process**: Process 1, Timer-based, High Priority
- **Output**: Digital output on DIO 0

### 2. Python Test Script
- **File**: `test_adwin_awg520_trigger.py`
- **Purpose**: Complete end-to-end test with hardware control
- **Features**: Waveform generation, sequence creation, hardware configuration

### 3. Pytest Version
- **File**: `test_adwin_awg520_trigger_pytest.py`
- **Purpose**: Structured testing with pytest fixtures and assertions
- **Features**: Automated testing, better error reporting

## 🚀 **Running the Tests**

### Prerequisites
1. **Hardware connected** as per wiring diagram
2. **ADwin Gold II** with ADbasic development environment
3. **AWG520** with external trigger support
4. **Python environment** with required packages

### Step 1: Load ADbasic Program
1. Open ADbasic development environment
2. Load `awg520_trigger_test.bas`
3. Compile and download to ADwin
4. Verify process 1 is loaded

### Step 2: Run Python Test
```bash
cd examples/awg520_testing
python test_adwin_awg520_trigger.py
```

### Step 3: Run Pytest Version (Optional)
```bash
cd examples/awg520_testing
python -m pytest test_adwin_awg520_trigger_pytest.py -v
```

## 📊 **Test Waveforms**

The test generates 4 different waveform types:
- **Sine wave**: 1MHz frequency, 1μs duration
- **Ramp wave**: Linear ramp from -1V to +1V, 1μs duration
- **Triangle wave**: 1MHz triangle wave, 1μs duration
- **Square wave**: 1MHz square wave, 1μs duration

## ⚙️ **AWG520 Configuration**

The test automatically configures AWG520 for external triggering:
- **Trigger Source**: External
- **Trigger Level**: 2.5V (for 0→5V TTL input)
- **Trigger Impedance**: 50Ω
- **Run Mode**: Enhanced (enables Wait Trigger)
- **Jump Mode**: Software (computer controlled)

## 🔄 **Test Sequence**

1. **ADwin generates trigger pulse** (1ms duration)
2. **AWG520 receives trigger** and outputs first waveform
3. **AWG520 waits** for next trigger (Wait Trigger enabled)
4. **ADwin generates next trigger** after 1 second interval
5. **AWG520 advances** to next sequence line
6. **Process repeats** for all 4 waveforms
7. **Sequence loops back** to first waveform

## 📈 **Expected Results**

### Success Criteria
- ✅ **AWG520 responds** to external triggers within 100ns
- ✅ **Waveforms output correctly** after each trigger
- ✅ **Sequence advances** through all 4 waveforms
- ✅ **Timing preserved** for all waveform components
- ✅ **No memory overflow** or sequence errors

### Monitoring
- **ADwin parameters** show trigger count and state
- **AWG520 display** shows current sequence line
- **Oscilloscope** (optional) shows trigger signals and waveforms

## 🐛 **Troubleshooting**

### Common Issues
1. **No trigger response**: Check trigger level, impedance, and source settings
2. **Waveform corruption**: Verify BNC connections and grounding
3. **Sequence not advancing**: Check Wait Trigger column in sequence file
4. **Timing issues**: Verify sample rate and sequence configuration

### Debug Steps
1. **Use oscilloscope** to verify trigger signal integrity
2. **Check AWG520 error messages** and status displays
3. **Verify ADwin process** is running and parameters are set
4. **Test with simpler sequences** to isolate issues

## 🔮 **Next Steps After Testing**

### If External Trigger Works
1. **Implement full pulsed ODMR sequence** with this architecture
2. **Optimize repeat field usage** for maximum memory compression
3. **Integrate with existing mux control architecture**
4. **Test with real quantum experiments**

### If External Trigger Fails
1. **Investigate alternative AWG520 control methods**
2. **Consider software jump commands** over GPIB/Ethernet
3. **Explore different compression strategies**
4. **Reassess hardware architecture** requirements

## 📚 **Additional Resources**

- **AWG520 User Manual**: External trigger configuration
- **ADwin Gold II Manual**: Digital I/O and process control
- **Hardware Connection System**: `docs/HARDWARE_CONNECTION_SYSTEM.md`
- **AWG520 Testing Guide**: `docs/AWG520_ADWIN_TESTING.md`

## 🤝 **Support**

For issues or questions:
1. Check the troubleshooting section above
2. Review hardware connections and configuration
3. Consult the AWG520 and ADwin manuals
4. Check system logs and error messages
