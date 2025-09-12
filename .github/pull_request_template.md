# Pull Request

## 📋 **Quality Checklist**

### **Code Quality**
- [ ] **Code follows PEP 8** style guidelines
- [ ] **Functions have docstrings** with proper format
- [ ] **Classes have docstrings** explaining purpose and usage
- [ ] **Type hints** added for function parameters and returns
- [ ] **Meaningful variable names** used throughout
- [ ] **No hardcoded values** - all configurable via parameters
- [ ] **Error handling** implemented for device operations
- [ ] **No TODO/FIXME** comments left in code

### **Testing**
- [ ] **Mock hardware testing** completed
- [ ] **Real hardware testing** completed (if available)
- [ ] **All existing tests pass** (`python -m pytest tests/`)
- [ ] **New functionality tested** with example scripts
- [ ] **No regressions** introduced

### **Documentation**
- [ ] **README.md updated** if adding new features
- [ ] **CHANGELOG.md updated** for significant changes
- [ ] **Example scripts added** in `examples/` directory
- [ ] **Hardware requirements documented** in experiment docstrings
- [ ] **Usage examples included** in documentation

### **Commit Quality**
- [ ] **Commit messages follow format**: `[setup-name] Brief description`
- [ ] **Each commit is atomic** - one logical change per commit
- [ ] **Descriptive commit messages** explain what and why
- [ ] **No merge commits** in feature branch (use rebase if needed)

## 📝 **PR Description**

### **Summary**
Brief description of what this PR adds/fixes.

### **Changes**
- List of specific changes made
- New features added
- Bugs fixed
- Documentation updated

### **Testing**
- [ ] Tested with mock hardware
- [ ] Tested with real hardware (if available)
- [ ] All existing tests pass
- [ ] New functionality tested

### **Benefits**
How this benefits the lab (for lab-wide contributions) or setup (for setup contributions).

### **Breaking Changes**
List any breaking changes (should be minimal).

### **Screenshots**
Include screenshots if GUI changes.

## 🔍 **Reviewer Notes**

### **For @gurudevdutt Review:**
- [ ] **Code quality** meets lab standards
- [ ] **Documentation** is comprehensive and clear
- [ ] **Testing** is thorough and appropriate
- [ ] **Commit messages** are descriptive and follow format
- [ ] **Benefits** clearly explained and justified
- [ ] **No breaking changes** without good reason

### **Areas of Concern:**
- [ ] Code complexity too high
- [ ] Missing error handling
- [ ] Inadequate documentation
- [ ] Insufficient testing
- [ ] Poor commit message quality
- [ ] Unclear benefits or purpose

## 📚 **Documentation Examples**

### **Good Commit Message:**
```
[cryo] Add Lakeshore 336 cryostat temperature controller

- Implements RS232 communication protocol
- Adds temperature setpoint and readback functions
- Includes safety interlocks for temperature limits
- Tested with mock hardware
```

### **Good Function Docstring:**
```python
def set_temperature(self, temp_kelvin: float) -> bool:
    """
    Set target temperature for cryostat.
    
    Args:
        temp_kelvin (float): Target temperature in Kelvin (4.2 to 300 K)
        
    Returns:
        bool: True if command sent successfully, False otherwise
        
    Raises:
        ValueError: If temperature is outside valid range
        ConnectionError: If communication with device fails
        
    Example:
        >>> cryostat.set_temperature(4.2)
        True
    """
```

### **Good Class Docstring:**
```python
class CryoODMRExperiment(Experiment):
    """
    ODMR experiment with temperature control for cryogenic measurements.
    
    This experiment implements optically detected magnetic resonance (ODMR)
    measurements at controlled temperatures using a Lakeshore 336 temperature
    controller. It integrates microwave frequency sweeps with temperature
    stabilization for studying NV centers at cryogenic temperatures.
    
    Hardware Dependencies:
    - cryostat: Lakeshore 336 temperature controller for temperature control
    - microwave: SG384 generator for frequency sweeps
    - adwin: Adwin Gold II for data acquisition and timing
    
    Example:
        >>> experiment = CryoODMRExperiment(devices, settings={'temperature': 4.2})
        >>> experiment.run()
    """
```
