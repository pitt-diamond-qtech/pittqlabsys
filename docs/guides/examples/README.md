# Examples and Tutorials

This section contains example experiments and tutorials for learning PittQLabSys.

## 📚 Example Experiments

### ODMR Experiments
- [ODMR Experiments Overview](odmr-experiments.md) - Overview of ODMR experiments
- [ODMR Pulsed](odmr-pulsed.md) - Pulsed ODMR experiments

### Confocal Experiments
- [Confocal Experiments](confocal-experiments.md) - Confocal microscopy experiments *(coming soon)*

## 🚀 Getting Started with Examples

### 1. Choose an Example
1. Browse the available examples
2. Read the overview to understand what it does
3. Check prerequisites and requirements

### 2. Run the Example
1. Follow the setup instructions
2. Use [Testing with Mock](../development/testing-with-mock.md) for development
3. Test with real hardware when available

### 3. Modify and Learn
1. Study the code structure
2. Make small modifications
3. Understand how it works
4. Create your own variations

## 📋 Prerequisites

Before running examples, ensure you have:

- **PittQLabSys installed** and configured
- **Required hardware** (if using real hardware)
- **Basic Python knowledge** (for modifications)
- **Understanding of the experiment type** (for customizations)

## 🎯 Learning Path

### Beginner
1. Start with [ODMR Experiments Overview](odmr-experiments.md)
2. Run the basic examples
3. Understand the structure
4. Make small modifications

### Intermediate
1. Study the code in detail
2. Modify parameters and settings
3. Add new features
4. Test with different hardware

### Advanced
1. Create your own experiments
2. Integrate with other systems
3. Optimize for your hardware
4. Share with the community

## 🔧 Example Structure

### Typical Example Includes
- **Overview** - What the example does
- **Prerequisites** - What you need
- **Setup** - How to configure
- **Running** - How to execute
- **Results** - What to expect
- **Modifications** - How to customize

### Code Organization
- **Main script** - Entry point
- **Configuration** - Settings and parameters
- **Functions** - Reusable code
- **Documentation** - Comments and docstrings

## 🔗 Related Resources

### Development
- [Experiment Development](../development/experiment-development.md) - Creating experiments
- [Testing with Mock](../development/testing-with-mock.md) - Testing without hardware

### Hardware
- [Hardware Setup](../hardware/) - Device configuration
- [Device Guides](../hardware/) - Specific device setup

### Technical Reference
- [API Reference](../../reference/) - Technical details
- [Configuration](../../reference/configuration.md) - System configuration

## 📝 Adding New Examples

When creating new examples:

1. **Follow the existing format** and structure
2. **Include clear documentation** and comments
3. **Add setup instructions** and prerequisites
4. **Include testing instructions** for both mock and real hardware
5. **Update this README** to include your example

### Example Template
```python
#!/usr/bin/env python3
"""
Example Name

Brief description of what this example does.

Prerequisites:
- List of requirements
- Hardware needed
- Software needed

Usage:
    python example_name.py --mock-hardware
    python example_name.py --real-hardware
"""

# Your code here
```

## 🔄 Recent Updates

- **2024-09-17**: Reorganized examples into logical structure
- **2024-09-17**: Added learning path section
- **2024-09-17**: Improved cross-references to related guides

---

*These examples help you learn PittQLabSys through hands-on experience. For technical details, check the [Reference](../../reference/) section.*
