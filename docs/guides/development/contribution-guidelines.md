# Contribution Guidelines

This document outlines the standards and requirements for contributing to the PittQLabSys project.

## 🎯 **Types of Contributions**

### **Individual Fork Development**
- **No formal requirements** - work however you want
- **Maximum freedom** to experiment and iterate
- **Your fork, your rules**

### **Lab-wide Contributions**
- **Strict quality standards** - must benefit entire lab
- **Comprehensive testing** required
- **Code review** by @gurudevdutt
- **Documentation updates** mandatory

## 🔒 **Lab-wide Contribution Requirements**

### **Code Quality Standards**
- **Follow PEP 8** Python style guidelines
- **Add type hints** for function parameters
- **Write comprehensive docstrings** for all functions and classes
- **Use meaningful variable names** and comments
- **Follow existing code patterns** and conventions

### **Testing Requirements**
- **Must run full test suite**: `python -m pytest tests/`
- **Must test with mock hardware**: `python examples/your_experiment.py --test-only`
- **Must test with real hardware** if available
- **Must not break existing functionality**
- **Must add tests** for new functionality

### **Documentation Requirements**
- **Update README.md** if adding new features
- **Add example scripts** in `examples/` directory
- **Update CHANGELOG.md** for significant changes
- **Document hardware requirements** in experiment docstrings
- **Include usage examples** in documentation

### **Code Structure Requirements**
- **Follow existing experiment patterns** (see examples in `src/Model/experiments/`)
- **Use Parameter class** for all settings
- **Implement proper device access** via `devices` parameter
- **Include proper error handling** and logging
- **Use device config manager** for hardware initialization

## 📝 **Pull Request Process**

### **Before Creating PR**
1. **Test thoroughly** with mock and real hardware
2. **Update all relevant documentation**
3. **Ensure no breaking changes** to existing functionality
4. **Run full test suite** and fix any failures
5. **Check code style** and formatting

### **PR Description Template**
```markdown
## Summary
Brief description of what this PR adds/fixes.

## Changes
- List of specific changes made
- New features added
- Bugs fixed
- Documentation updated

## Testing
- [ ] Tested with mock hardware
- [ ] Tested with real hardware (if available)
- [ ] All existing tests pass
- [ ] New functionality tested

## Benefits
How this benefits the entire lab.

## Breaking Changes
List any breaking changes (should be minimal).

## Screenshots
Include screenshots if GUI changes.
```

### **Review Process**
1. **Automated checks** must pass (tests, linting)
2. **Code review** by @gurudevdutt
3. **Testing verification** on lab hardware
4. **Documentation review** for completeness
5. **Approval** before merging

## 🧪 **Testing Guidelines**

### **Mock Hardware Testing**
```bash
# Test experiment creation
python examples/your_experiment.py --test-only

# Test with mock hardware
python examples/your_experiment.py

# Test specific functionality
python -m pytest tests/test_your_experiment.py
```

### **Real Hardware Testing**
```bash
# Test with real hardware
python examples/your_experiment.py --real-hardware

# Test specific hardware configurations
python examples/your_experiment.py --real-hardware --config custom_config.json
```

### **Test Coverage**
- **Unit tests** for individual functions
- **Integration tests** for experiment workflows
- **Hardware tests** for device interactions
- **Error handling tests** for edge cases

## 📚 **Documentation Standards**

### **Code Documentation**
```python
def your_function(param1: float, param2: str) -> bool:
    """
    Brief description of what this function does.
    
    Args:
        param1 (float): Description of parameter 1
        param2 (str): Description of parameter 2
        
    Returns:
        bool: Description of return value
        
    Raises:
        ValueError: When invalid parameters are provided
        
    Example:
        >>> result = your_function(1.0, "test")
        >>> print(result)
        True
    """
    # Function implementation
    pass
```

### **Experiment Documentation**
```python
class YourExperiment(Experiment):
    """
    Brief description of what this experiment does.
    
    This experiment implements [specific functionality] for [specific use case].
    It uses [hardware devices] to [achieve specific goal].
    
    Hardware Dependencies:
    - Device1: What it's used for and why
    - Device2: What it's used for and why
    
    Example:
        >>> experiment = YourExperiment(devices, settings=your_settings)
        >>> experiment.run()
    """
```

### **README Updates**
- **Add new features** to appropriate sections
- **Update installation instructions** if needed
- **Add new examples** to examples list
- **Update hardware requirements** if changed

### **CHANGELOG Updates**
```markdown
## [Version] - YYYY-MM-DD

### Added
- New feature 1
- New feature 2

### Changed
- Modified existing feature
- Updated documentation

### Fixed
- Bug fix 1
- Bug fix 2

### Removed
- Deprecated feature (if any)
```

## 🔧 **Code Style Guidelines**

### **Python Style**
- **Follow PEP 8** guidelines
- **Use 4 spaces** for indentation
- **Line length** of 88 characters (Black formatter)
- **Use type hints** for function parameters and return values
- **Use descriptive variable names**

### **Import Organization**
```python
# Standard library imports
import os
import sys
from pathlib import Path

# Third-party imports
import numpy as np
import matplotlib.pyplot as plt

# Local imports
from src.core import Experiment, Parameter
from src.Model.experiments.your_experiment import YourExperiment
```

### **Error Handling**
```python
try:
    # Risky operation
    result = device.operation()
except SpecificException as e:
    self.log(f"Specific error occurred: {e}")
    # Handle specific error
except Exception as e:
    self.log(f"Unexpected error: {e}")
    # Handle general error
    raise
```

## 🚨 **Common Mistakes to Avoid**

### **Code Issues**
- ❌ **Hardcoded values** instead of parameters
- ❌ **Missing error handling** for device operations
- ❌ **Inconsistent naming** conventions
- ❌ **Missing docstrings** for public functions
- ❌ **Breaking existing functionality** without good reason

### **Testing Issues**
- ❌ **Not testing with mock hardware** first
- ❌ **Not testing error conditions**
- ❌ **Not updating tests** when changing functionality
- ❌ **Not testing with real hardware** when available

### **Documentation Issues**
- ❌ **Not updating README** when adding features
- ❌ **Missing example scripts** for new experiments
- ❌ **Incomplete docstrings** for functions
- ❌ **Not updating CHANGELOG** for significant changes

## 🎯 **Best Practices**

### **Development Process**
1. **Start with mock hardware** - test ideas quickly
2. **Write tests early** - before implementing complex features
3. **Document as you go** - don't leave it for later
4. **Test incrementally** - verify each change works
5. **Get feedback early** - share work in progress

### **Code Organization**
1. **Follow existing patterns** - consistency is key
2. **Use appropriate abstractions** - don't over-engineer
3. **Keep functions focused** - single responsibility
4. **Use meaningful names** - code should be self-documenting
5. **Handle errors gracefully** - provide useful error messages

### **Collaboration**
1. **Communicate changes** - let team know what you're working on
2. **Ask for help** - don't struggle alone
3. **Share knowledge** - document solutions to common problems
4. **Be respectful** - constructive feedback only
5. **Help others** - contribute to team success

## ❓ **Getting Help**

### **Code Issues**
- **Check existing examples** in `examples/` directory
- **Look at similar experiments** in `src/Model/experiments/`
- **Ask @gurudevdutt** for guidance
- **Search existing issues** in repository

### **Hardware Issues**
- **Check device documentation** in `docs/`
- **Look at device config** in `src/config.json`
- **Test with mock hardware** first
- **Ask hardware-specific questions** to relevant team members

### **Git/GitHub Issues**
- **Check workflow guide** in `docs/LAB_WORKFLOW_GUIDE.md`
- **Ask experienced team members** for help
- **Use GitHub issues** for bug reports
- **Use discussions** for questions and ideas

## 🔄 **Review Checklist**

Before submitting a lab-wide contribution, ensure:

- [ ] **Code follows style guidelines** (PEP 8, type hints, docstrings)
- [ ] **All tests pass** (mock and real hardware)
- [ ] **Documentation is updated** (README, CHANGELOG, docstrings)
- [ ] **Example script included** in `examples/` directory
- [ ] **No breaking changes** to existing functionality
- [ ] **Error handling** is comprehensive
- [ ] **Code is well-commented** and readable
- [ ] **PR description** is complete and clear
- [ ] **Screenshots included** if GUI changes
- [ ] **Benefits to lab** are clearly explained

Remember: **Quality over speed. It's better to take time and do it right than to rush and create problems for the team.**
