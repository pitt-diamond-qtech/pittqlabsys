# Quality Guidelines

This document provides specific examples and standards for code quality, documentation, and commit messages in the PittQLabSys project.

## 📝 **Commit Message Standards**

### **Format**
```
[setup-name] Brief description

- Bullet point explaining what was changed
- Another bullet point explaining why
- Additional details if needed
- Tested with mock/real hardware
```

### **Examples**

#### ✅ **Good Commit Messages**
```bash
[cryo] Add Lakeshore 336 cryostat temperature controller

- Implements RS232 communication protocol for temperature control
- Adds safety interlocks to prevent temperature overshoot
- Includes comprehensive error handling and logging
- Tested with mock hardware

[confocal] Fix nanodrive positioning accuracy issue

- Corrects coordinate transformation in scan parameters
- Adds calibration verification before each scan
- Improves positioning accuracy from ±0.5μm to ±0.1μm
- Tested with real hardware

[odmr] Update sweep parameters for better resolution

- Changes step_freq from 1MHz to 100kHz for finer resolution
- Adds automatic parameter validation
- Updates example scripts with new defaults
- Tested with both mock and real hardware
```

#### ❌ **Bad Commit Messages**
```bash
# Too vague
Fixed bug

# Missing setup name
Add cryostat controller

# No details
Updated code

# No testing info
Added experiment
```

## 📚 **Documentation Standards**

### **Function Docstrings**

#### ✅ **Good Function Docstring**
```python
def set_temperature(self, temp_kelvin: float, ramp_rate: float = 1.0) -> bool:
    """
    Set target temperature for cryostat with optional ramp rate control.
    
    This function sends a temperature setpoint command to the Lakeshore 336
    temperature controller. It includes safety checks to ensure the temperature
    is within valid limits and implements proper error handling for communication
    failures.
    
    Args:
        temp_kelvin (float): Target temperature in Kelvin. Must be between
            4.2 and 300 K for safety reasons.
        ramp_rate (float, optional): Temperature ramp rate in K/min. 
            Defaults to 1.0 K/min. Must be between 0.1 and 10.0 K/min.
            
    Returns:
        bool: True if command sent successfully, False if communication failed
            or parameters are invalid.
            
    Raises:
        ValueError: If temperature or ramp_rate is outside valid range
        ConnectionError: If communication with device fails
        TimeoutError: If device doesn't respond within timeout period
        
    Example:
        >>> cryostat = CryostatController({'serial_port': 'COM3'})
        >>> success = cryostat.set_temperature(4.2, ramp_rate=0.5)
        >>> print(f"Temperature set: {success}")
        Temperature set: True
        
    Note:
        The device will automatically ramp to the target temperature at the
        specified rate. Use read_temperature() to monitor progress.
    """
```

#### ❌ **Bad Function Docstring**
```python
def set_temperature(self, temp, rate=1.0):
    """Set temperature."""
    # No type hints, no parameter descriptions, no examples
    pass
```

### **Class Docstrings**

#### ✅ **Good Class Docstring**
```python
class CryoODMRExperiment(Experiment):
    """
    ODMR experiment with temperature control for cryogenic measurements.
    
    This experiment implements optically detected magnetic resonance (ODMR)
    measurements at controlled temperatures using a Lakeshore 336 temperature
    controller. It integrates microwave frequency sweeps with temperature
    stabilization for studying NV centers at cryogenic temperatures.
    
    The experiment automatically handles temperature stabilization, microwave
    frequency sweeps, and data acquisition timing. It includes safety checks
    to prevent damage to the cryostat and sample.
    
    Hardware Dependencies:
    - cryostat: Lakeshore 336 temperature controller for temperature control
    - microwave: SG384 generator for frequency sweeps and power control
    - adwin: Adwin Gold II for data acquisition and timing control
    
    Typical Usage:
        >>> devices = create_devices(use_real_hardware=True)
        >>> experiment = CryoODMRExperiment(
        ...     devices=devices,
        ...     settings={
        ...         'temperature': 4.2,
        ...         'start_freq': 2.87e9,
        ...         'stop_freq': 2.88e9,
        ...         'step_freq': 1e6
        ...     }
        ... )
        >>> experiment.run()
        
    Safety Features:
    - Temperature limits enforced (4.2 K to 300 K)
    - Ramp rate limits to prevent thermal shock
    - Automatic return to room temperature after experiment
    - Emergency stop functionality
    """
```

#### ❌ **Bad Class Docstring**
```python
class CryoODMRExperiment(Experiment):
    """ODMR experiment with temperature control."""
    # Too brief, no usage examples, no hardware info
    pass
```

## 🧪 **Testing Standards**

### **Mock Hardware Testing**
```python
def test_cryostat_controller_mock():
    """Test cryostat controller with mock hardware."""
    # Test basic functionality
    cryostat = MockCryostatController()
    assert cryostat.set_temperature(4.2) == True
    assert cryostat.read_temperature() == 4.2
    
    # Test error handling
    with pytest.raises(ValueError):
        cryostat.set_temperature(-1.0)  # Invalid temperature
    
    # Test communication failure
    cryostat.simulate_communication_error()
    assert cryostat.set_temperature(4.2) == False
```

### **Real Hardware Testing**
```python
def test_cryostat_controller_real():
    """Test cryostat controller with real hardware."""
    if not has_real_hardware():
        pytest.skip("Real hardware not available")
    
    cryostat = CryostatController({'serial_port': 'COM3'})
    
    # Test temperature setting
    assert cryostat.set_temperature(4.2) == True
    time.sleep(5)  # Wait for temperature to stabilize
    temp = cryostat.read_temperature()
    assert abs(temp - 4.2) < 0.1  # Within 0.1 K tolerance
```

## 📊 **Code Quality Metrics**

### **Function Complexity**
- **Keep functions under 20 lines** when possible
- **Maximum 10 complexity** (cyclomatic complexity)
- **Single responsibility** - one function, one purpose

### **Documentation Coverage**
- **100% of public functions** must have docstrings
- **All classes** must have docstrings
- **All modules** must have module docstrings
- **All parameters** must be documented

### **Error Handling**
- **All device operations** must have try/catch blocks
- **Meaningful error messages** for debugging
- **Graceful degradation** when possible
- **Logging** for important events

## 🔍 **Review Checklist for @gurudevdutt**

### **Code Quality**
- [ ] **Functions are focused** - single responsibility
- [ ] **Variable names are descriptive** - no abbreviations
- [ ] **No hardcoded values** - all configurable
- [ ] **Error handling is comprehensive** - covers edge cases
- [ ] **Code is readable** - clear logic flow
- [ ] **No code duplication** - DRY principle followed

### **Documentation Quality**
- [ ] **Docstrings are comprehensive** - explains what, why, how
- [ ] **Examples are included** - shows real usage
- [ ] **Parameter types are documented** - with valid ranges
- [ ] **Return values are clear** - what to expect
- [ ] **Error conditions are documented** - when things go wrong
- [ ] **Hardware requirements are clear** - what devices needed

### **Testing Quality**
- [ ] **Mock hardware tests** - basic functionality covered
- [ ] **Real hardware tests** - when available
- [ ] **Error condition tests** - edge cases covered
- [ ] **Integration tests** - works with other components
- [ ] **Performance tests** - reasonable execution time

### **Commit Quality**
- [ ] **Messages are descriptive** - explains what and why
- [ ] **Format is consistent** - follows lab standards
- [ ] **Commits are atomic** - one logical change per commit
- [ ] **Testing is mentioned** - mock/real hardware
- [ ] **Breaking changes are noted** - if any

## 🎯 **Quality Examples by Category**

### **Device Controllers**
```python
class SG384Generator(Device):
    """
    Stanford Research Systems SG384 RF/Microwave Signal Generator.
    
    Provides frequency and amplitude control for microwave experiments.
    Supports both continuous wave and modulated output modes.
    """
    
    def set_frequency(self, freq_hz: float) -> bool:
        """
        Set output frequency.
        
        Args:
            freq_hz: Frequency in Hz (1e6 to 20e9)
            
        Returns:
            bool: True if successful
        """
        # Implementation with error handling
        pass
```

### **Experiments**
```python
class ODMRExperiment(Experiment):
    """
    Optically Detected Magnetic Resonance experiment.
    
    Measures NV center spin resonance by sweeping microwave frequency
    while monitoring photoluminescence intensity.
    """
    
    _DEFAULT_SETTINGS = [
        Parameter('start_freq', 2.87e9, float, 'Start frequency (Hz)'),
        Parameter('stop_freq', 2.88e9, float, 'Stop frequency (Hz)'),
        Parameter('step_freq', 1e6, float, 'Frequency step (Hz)'),
    ]
```

### **Example Scripts**
```python
#!/usr/bin/env python3
"""
ODMR Experiment Example

This script demonstrates how to run an ODMR experiment with the SG384
microwave generator and Adwin data acquisition system.

Usage:
    python odmr_example.py [--real-hardware] [--no-plot]

Examples:
    # Run with mock hardware (default)
    python odmr_example.py
    
    # Run with real hardware
    python odmr_example.py --real-hardware
"""

def main():
    """Main function to run ODMR experiment."""
    # Implementation with proper argument parsing
    pass
```

## 🚨 **Common Quality Issues to Avoid**

### **Code Issues**
- ❌ **Hardcoded values** instead of parameters
- ❌ **Missing error handling** for device operations
- ❌ **Vague variable names** like `data`, `result`, `temp`
- ❌ **Functions doing too much** - multiple responsibilities
- ❌ **No type hints** for function parameters

### **Documentation Issues**
- ❌ **Missing docstrings** for public functions
- ❌ **Incomplete parameter descriptions** - no types or ranges
- ❌ **No usage examples** in docstrings
- ❌ **Outdated documentation** - doesn't match code
- ❌ **Missing hardware requirements** in experiment docstrings

### **Testing Issues**
- ❌ **No mock hardware testing** - only real hardware
- ❌ **No error condition testing** - only happy path
- ❌ **Tests that are too slow** - should be fast for CI
- ❌ **Tests that depend on external state** - not isolated
- ❌ **No integration testing** - only unit tests

### **Commit Issues**
- ❌ **Vague commit messages** - "Fixed bug", "Updated code"
- ❌ **Missing setup name** - no `[cryo]` prefix
- ❌ **No testing information** - didn't mention mock/real hardware
- ❌ **Multiple changes in one commit** - not atomic
- ❌ **Merge commits in feature branches** - should use rebase

Remember: **Quality is not about perfection, it's about making code maintainable and understandable for your lab team!**
