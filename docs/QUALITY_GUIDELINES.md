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

## 🔧 **Quality Assessment Tool Usage**

### **Overview**
The `scripts/assess_quality.py` tool provides objective quality metrics for your code and commits. It analyzes:
- **Commit message format** and content quality
- **Code documentation** coverage and completeness
- **Code style** issues (line length, complexity, etc.)
- **Overall quality score** (0-100 scale)

> **📋 Related Documentation**: For the complete lab workflow including individual forks, setup collaboration, and lab-wide contributions, see the **[Lab Workflow Guide](LAB_WORKFLOW_GUIDE.md)**.
> 
> **🤖 AI Assistant Context**: For AI assistants working on this project, see **[AI Context](AI_CONTEXT.md)** for key quality standards and workflow information.

### **Basic Usage**
```bash
# Check recent commits (default: 10 commits)
python scripts/assess_quality.py

# Check specific number of commits
python scripts/assess_quality.py --commits 5

# Check specific files or directories
python scripts/assess_quality.py --path src/Model/experiments/

# Check specific files with recent commits
python scripts/assess_quality.py --path src/core/ --commits 5
```

### **Understanding the Output**

#### **Commit Quality Metrics**
```
📝 **Commit Quality** (10 recent commits)
  ✅ Good format: 0/10 (0.0%)
  ✅ Has setup name: 0/10 (0.0%)
  ✅ Descriptive: 0/10 (0.0%)
  ✅ Mentions testing: 1/10 (10.0%)
```

**What it checks:**
- **Good format**: Follows `[setup-name] Description` format
- **Has setup name**: Includes setup identifier like `[cryo]`, `[confocal]`
- **Descriptive**: Contains detailed bullet points explaining changes
- **Mentions testing**: References mock/real hardware testing

#### **Code Quality Metrics**
```
📁 **File Analysis** (87 Python files)
  Total issues found: 3894

📋 **Issues by File:**
  src/config_paths.py:
    - Debug print on line 91: >>> print(paths["data_folder"])
    - Line 120 too long: 94 characters
```

**What it checks:**
- **Missing docstrings** in functions and classes
- **Long lines** (over 88 characters)
- **Debug print statements** left in code
- **Missing Args/Returns** in existing docstrings
- **Code complexity** and style issues

#### **Overall Quality Score**
```
🎯 **Overall Quality Score: 0.0/100**
  🔴 Poor quality, significant improvements needed
```

**Score interpretation:**
- **90-100**: Excellent quality, minimal issues
- **70-89**: Good quality, some minor improvements needed
- **50-69**: Fair quality, several issues to address
- **30-49**: Poor quality, significant improvements needed
- **0-29**: Very poor quality, major refactoring required

### **Usage by Collaboration Level**

#### **1. Individual Development (Your Fork)**
**Purpose**: Learning and self-improvement
**Frequency**: Occasional (weekly/monthly)
**Strictness**: Low - use as a guide, not a requirement

```bash
# Check your recent work occasionally
python scripts/assess_quality.py --commits 5

# Focus on major issues only
python scripts/assess_quality.py --path src/Model/experiments/
```

**What to focus on:**
- **Missing docstrings** in new functions
- **Debug print statements** before committing
- **Long lines** that hurt readability
- **Commit message format** for consistency

**What to ignore:**
- Perfect scores - focus on functionality first
- Minor style issues in experimental code
- Complex refactoring unless necessary

#### **2. Setup Collaboration (Team Work)**
**Purpose**: Team coordination and knowledge sharing
**Frequency**: Before merging feature branches
**Strictness**: Moderate - focus on major issues

```bash
# Check before merging to setup main
python scripts/assess_quality.py --path src/ --commits 5

# Use to guide team members
python scripts/assess_quality.py --path src/Model/experiments/
```

**What to focus on:**
- **Missing docstrings** in public functions
- **Long lines** that affect readability
- **Debug print statements** in production code
- **Commit message format** for team consistency

**What to be flexible about:**
- Minor style issues in working code
- Complex refactoring unless critical
- Perfect documentation in experimental features

#### **3. Lab-wide Contributions (Main Repository)**
**Purpose**: Quality control and maintainability
**Frequency**: Before creating pull requests
**Strictness**: High - address major issues before submitting

```bash
# Run before creating PRs
python scripts/assess_quality.py --commits 10

# Fix major issues before submitting
python scripts/assess_quality.py --path src/Model/experiments/
```

**What to focus on:**
- **All missing docstrings** in public functions
- **All long lines** and style issues
- **All debug print statements**
- **Proper commit message format**
- **Comprehensive error handling**

**What to address:**
- **Everything** - this is the main repository
- **Quality score** should be 70+ before submitting
- **All issues** should be addressed or justified

### **Common Issues and How to Fix Them**

#### **Commit Message Issues**
```bash
# ❌ Bad: Missing format
Add cryostat controller

# ✅ Good: Proper format
[cryo] Add Lakeshore 336 cryostat temperature controller

- Implements RS232 communication protocol
- Adds safety interlocks for temperature limits
- Tested with mock hardware
```

#### **Code Documentation Issues**
```python
# ❌ Bad: Missing docstring
def set_temperature(self, temp, rate=1.0):
    pass

# ✅ Good: Comprehensive docstring
def set_temperature(self, temp_kelvin: float, ramp_rate: float = 1.0) -> bool:
    """
    Set target temperature for cryostat with optional ramp rate control.
    
    Args:
        temp_kelvin (float): Target temperature in Kelvin (4.2-300 K)
        ramp_rate (float): Temperature ramp rate in K/min (0.1-10.0 K/min)
        
    Returns:
        bool: True if command sent successfully, False if failed
        
    Tested with mock hardware
    """
```

#### **Code Style Issues**
```python
# ❌ Bad: Long line (94 characters)
very_long_variable_name = some_function_call_with_many_parameters(param1, param2, param3, param4)

# ✅ Good: Break into multiple lines
very_long_variable_name = some_function_call_with_many_parameters(
    param1, param2, param3, param4
)
```

#### **Debug Print Issues**
```python
# ❌ Bad: Debug print left in code
def process_data(data):
    print(f"Processing data: {data}")  # Remove this
    return processed_data

# ✅ Good: Use proper logging
def process_data(data):
    self.log(f"Processing data: {data}")
    return processed_data
```

### **Quality Improvement Workflow**

#### **Step 1: Run Assessment**
```bash
python scripts/assess_quality.py --commits 5
```

#### **Step 2: Identify Priority Issues**
- **High Priority**: Missing docstrings, debug prints, long lines
- **Medium Priority**: Style issues, minor documentation gaps
- **Low Priority**: Minor formatting, optional improvements

#### **Step 3: Fix Issues Systematically**
1. **Start with high priority** - missing docstrings and debug prints
2. **Address medium priority** - style issues and documentation gaps
3. **Consider low priority** - minor formatting improvements

#### **Step 4: Re-run Assessment**
```bash
python scripts/assess_quality.py --commits 5
```

#### **Step 5: Commit Improvements**
```bash
git add .
git commit -m "[setup-name] Improve code quality

- Add missing docstrings to public functions
- Remove debug print statements
- Fix long lines and style issues
- Tested with mock hardware"
```

### **Quality Goals by Collaboration Level**

#### **Individual Development**
- **Target Score**: 40-60
- **Focus**: Functionality first, quality second
- **Frequency**: Monthly assessment

#### **Setup Collaboration**
- **Target Score**: 60-80
- **Focus**: Major issues, team consistency
- **Frequency**: Before merging feature branches

#### **Lab-wide Contributions**
- **Target Score**: 80-100
- **Focus**: All issues, production quality
- **Frequency**: Before creating pull requests

### **Tips for Effective Use**

1. **Start Small**: Don't try to fix everything at once
2. **Focus on Impact**: Address issues that affect maintainability
3. **Use as Learning**: The tool teaches good practices
4. **Be Consistent**: Use the same standards across your team
5. **Document Decisions**: Explain why you're ignoring certain issues

Remember: **Quality is not about perfection, it's about making code maintainable and understandable for your lab team!**
