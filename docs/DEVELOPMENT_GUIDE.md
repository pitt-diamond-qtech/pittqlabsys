# AQuISS Development Guide

This guide provides an overview of the professionalization improvements made to the AQuISS system and guidelines for future development.

> **📚 Documentation Index**: For a complete overview of all documentation, see [README.md](README.md)

## Related Guides

- **[Device Development Guide](DEVICE_DEVELOPMENT.md)** - Creating hardware device drivers
- **[Experiment Development Guide](EXPERIMENT_DEVELOPMENT.md)** - Creating scientific experiments
- **[Recent Updates](RECENT_UPDATES.md)** - Latest bug fixes and new features

## 🎯 Overview of Improvements

The AQuISS system has been significantly enhanced to meet professional software development standards while maintaining its scientific functionality. Key improvements include:

### 1. Documentation Enhancement
- **Comprehensive README**: Professional documentation with installation, usage, and development guidelines
- **API Documentation**: Detailed guides for device and experiment development
- **Code Documentation**: Enhanced docstrings and inline comments
- **Contributor Guidelines**: Clear contribution and development workflows

### 2. Code Quality Improvements
- **Type Hints**: Added throughout the codebase for better IDE support and error detection
- **Error Handling**: Robust exception handling and resource management
- **Code Style**: Consistent formatting and naming conventions
- **Modular Design**: Improved separation of concerns and reusability

### 3. Testing Infrastructure
- **Unit Tests**: Comprehensive test coverage for new functionality
- **Integration Tests**: End-to-end testing of experiment workflows
- **Mock Testing**: Hardware-independent testing capabilities
- **Test Documentation**: Clear test descriptions and expected outcomes

### 4. Project Management
- **Modern Python Packaging**: `pyproject.toml` for dependency management
- **Development Tools**: Black, flake8, mypy for code quality
- **CI/CD Ready**: Configuration for automated testing and deployment
- **Version Control**: Improved Git workflow and branching strategy

## 🏗️ Architecture Overview

### Core Components

```
AQuISS/
├── src/
│   ├── core/           # Framework classes (Device, Experiment, Parameter)
│   ├── Controller/     # Hardware device drivers
│   ├── Model/          # Experiment definitions and data processing
│   └── View/           # GUI components and visualization
├── tests/              # Test suite
├── docs/               # Documentation
└── examples/           # Example experiments and usage
```

### Design Principles

1. **Separation of Concerns**: Clear boundaries between device control, experiment logic, and user interface
2. **Extensibility**: Easy addition of new devices and experiments
3. **Reliability**: Robust error handling and resource management
4. **Usability**: Intuitive interface for scientific users
5. **Maintainability**: Clean, well-documented code

## 🚀 Getting Started with Development

### Prerequisites

- Python 3.8 or higher
- Git
- Virtual environment (recommended)

### Development Setup

1. **Clone and Setup**:
   ```bash
   git clone <repository-url>
   cd aquiss
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -e ".[dev]"
   ```

2. **Install Pre-commit Hooks**:
   ```bash
   pre-commit install
   ```

3. **Run Tests**:
   ```bash
   pytest tests/
   pytest --cov=src tests/  # With coverage
   ```

### Development Workflow

1. **Create Feature Branch**:
   ```bash
   git checkout -b feature/new-experiment
   ```

2. **Make Changes**: Follow coding standards and add tests

3. **Run Quality Checks**:
   ```bash
   black src/ tests/
   flake8 src/ tests/
   mypy src/
   pytest tests/
   ```

4. **Commit Changes**:
   ```bash
   git add .
   git commit -m "Add new ODMR experiment with comprehensive testing"
   ```

5. **Submit Pull Request**: Include description of changes and test results

## 📋 Coding Standards

### Python Style Guide

- Follow PEP 8 with Black formatting (88 character line length)
- Use type hints for all function parameters and return values
- Write comprehensive docstrings using Google or NumPy style
- Use meaningful variable and function names

### Code Organization

```python
"""
Module docstring explaining purpose and usage.
"""

# Standard library imports
import os
import sys
from typing import List, Dict, Optional

# Third-party imports
import numpy as np
import pyqtgraph as pg

# Local imports
from src.core import Device, Parameter


class MyDevice(Device):
    """
    Device class docstring with detailed description.
    
    This device controls [specific hardware] and provides [functionality].
    
    Attributes:
        _DEFAULT_SETTINGS: Default device parameters
        _PROBES: Available device measurements
    """
    
    _DEFAULT_SETTINGS = [
        Parameter('frequency', 1e9, float, 'Frequency in Hz'),
        Parameter('power', 0.0, float, 'Power in dBm'),
    ]
    
    _PROBES = {
        'temperature': 'Device temperature in Celsius',
        'status': 'Device status string',
    }
    
    def __init__(self, name: Optional[str] = None, 
                 settings: Optional[Dict[str, Any]] = None):
        """
        Initialize the device.
        
        Args:
            name: Optional device name
            settings: Optional initial settings
        """
        super().__init__(name, settings)
        self._is_connected = False
    
    def update(self, settings: Dict[str, Any]) -> None:
        """
        Update device settings.
        
        Args:
            settings: Dictionary of settings to update
            
        Raises:
            ValueError: If settings are invalid
        """
        Device.update(self, settings)
        # Implementation here
```

### Error Handling

```python
def connect(self) -> bool:
    """
    Establish connection to the device.
    
    Returns:
        True if connection successful, False otherwise
    """
    try:
        # Connection logic
        self._device_handle = self._establish_connection()
        self._is_connected = True
        self.log("Device connected successfully")
        return True
    except ConnectionError as e:
        self.log(f"Connection failed: {e}")
        return False
    except Exception as e:
        self.log(f"Unexpected error during connection: {e}")
        raise
```

## 🧪 Testing Guidelines

### Test Structure

```python
"""
Tests for MyDevice class.
"""

import pytest
from unittest.mock import Mock, patch
from src.Controller.my_device import MyDevice


class TestMyDevice:
    """Test cases for MyDevice class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.device = MyDevice()
    
    def test_initialization(self):
        """Test device initialization."""
        assert self.device.name == "MyDevice"
        assert self.device.settings['frequency'] == 1e9
    
    def test_connection_success(self):
        """Test successful device connection."""
        with patch.object(self.device, '_establish_connection'):
            result = self.device.connect()
            assert result is True
            assert self.device.is_connected
    
    def test_connection_failure(self):
        """Test device connection failure."""
        with patch.object(self.device, '_establish_connection', 
                         side_effect=ConnectionError("Connection failed")):
            result = self.device.connect()
            assert result is False
            assert not self.device.is_connected
    
    @pytest.mark.integration
    def test_full_workflow(self):
        """Test complete device workflow."""
        # Integration test with real or simulated hardware
        pass
```

### Test Categories

- **Unit Tests**: Test individual methods and classes
- **Integration Tests**: Test device interactions and experiment workflows
- **Hardware Tests**: Test with actual hardware (marked with `@pytest.mark.hardware`)
- **GUI Tests**: Test user interface components (marked with `@pytest.mark.gui`)

## 🔧 Adding New Features

### Adding a New Device

1. **Create Device Class**:
   ```python
   # src/Controller/my_device.py
   from src.core import Device, Parameter
   
   class MyDevice(Device):
       _DEFAULT_SETTINGS = [...]
       _PROBES = {...}
       
       def update(self, settings):
           # Implementation
           pass
       
       def read_probes(self, key):
           # Implementation
           pass
   ```

2. **Add to Device Registry**:
   ```python
   # src/Controller/__init__.py
   from .my_device import MyDevice
   
   _DEVICE_REGISTRY = {
       # ... existing devices
       "my_device": MyDevice,
   }
   ```

3. **Write Tests**:
   ```python
   # tests/test_my_device.py
   class TestMyDevice:
       # Comprehensive test suite
       pass
   ```

### Adding a New Experiment

1. **Create Experiment Class**:
   ```python
   # src/Model/experiments/my_experiment.py
   from src.core import Experiment, Parameter
   
   class MyExperiment(Experiment):
       _DEFAULT_SETTINGS = [...]
       _DEVICES = {
           'microwave': 'sg384',  # Device name strings
           'adwin': 'adwin'
       }
       
       def _function(self):
           # Experiment logic
           pass
       
       def _plot(self, axes_list):
           # Plotting logic
           pass
   ```

2. **Add to Experiments Registry**:
   ```python
   # src/Model/experiments/__init__.py
   from .my_experiment import MyExperiment
   ```

3. **Write Tests**:
   ```python
   # tests/test_my_experiment.py
   class TestMyExperiment:
       # Comprehensive test suite
       pass
   ```

**For detailed experiment development guidance, see [Experiment Development Guide](EXPERIMENT_DEVELOPMENT.md).**

## 📊 Data Management

### Data Formats

- **AQS Format**: Native format with experiment metadata
- **MATLAB**: `.mat` files for compatibility
- **CSV**: Tabular data export
- **Images**: Plot exports in various formats

### Data Organization

```
data/
├── raw_data/           # Raw experimental data
├── processed_data/     # Analyzed results
├── experiments/        # Experiment configurations
└── exports/           # Exported data and plots
```

## 🔍 Debugging and Troubleshooting

### Common Issues

1. **Device Connection Problems**:
   - Check hardware connections
   - Verify device drivers
   - Check network/GPIB settings

2. **Experiment Failures**:
   - Review experiment logs
   - Check device status
   - Verify parameter ranges

3. **GUI Issues**:
   - Check PyQt5 installation
   - Verify display settings
   - Review error logs

### Debugging Tools

- **Logging**: Use `self.log()` for debugging information
- **Progress Updates**: Implement progress reporting for long experiments
- **Error Handling**: Comprehensive exception handling with meaningful messages
- **Unit Tests**: Use tests to verify functionality

## 📚 Documentation Standards

### Code Documentation

- **Module Docstrings**: Explain purpose and usage
- **Class Docstrings**: Describe functionality and attributes
- **Method Docstrings**: Document parameters, returns, and exceptions
- **Inline Comments**: Explain complex logic

### User Documentation

- **Installation Guide**: Step-by-step setup instructions
- **User Manual**: GUI usage and experiment setup
- **API Reference**: Detailed class and method documentation
- **Examples**: Working examples for common use cases

## 🚀 Deployment and Distribution

### Building the Package

```bash
# Build distribution
python -m build

# Install in development mode
pip install -e .

# Install with hardware dependencies
pip install -e ".[hardware]"
```

### Distribution

- **PyPI**: For public distribution (if desired)
- **GitHub Releases**: For versioned releases
- **Docker**: For containerized deployment
- **Conda**: For scientific computing environments

## 🤝 Contributing

### Contribution Guidelines

1. **Fork the Repository**: Create your own fork
2. **Create Feature Branch**: Work on isolated features
3. **Follow Standards**: Adhere to coding and documentation standards
4. **Write Tests**: Include tests for new functionality
5. **Submit Pull Request**: Include description and test results

### Review Process

1. **Code Review**: All changes reviewed by maintainers
2. **Testing**: Automated tests must pass
3. **Documentation**: Documentation updated as needed
4. **Integration**: Changes integrated into main branch

## 📈 Future Development

### Planned Improvements

1. **Enhanced GUI**: Modern interface with better user experience
2. **Cloud Integration**: Remote experiment monitoring and data storage
3. **Machine Learning**: Automated data analysis and experiment optimization
4. **Multi-User Support**: Concurrent experiment execution
5. **Plugin System**: Extensible architecture for custom experiments

### Development Roadmap

- **Phase 1**: Core system stabilization and documentation
- **Phase 2**: Advanced experiments and analysis tools
- **Phase 3**: Cloud integration and remote access
- **Phase 4**: AI-powered experiment optimization

## 📞 Support and Resources

### Getting Help

- **Documentation**: Comprehensive guides and API reference
- **Issues**: GitHub issues for bug reports and feature requests
- **Discussions**: GitHub discussions for questions and ideas
- **Email**: Direct contact for urgent issues

### Resources

- **Scientific Papers**: References for implemented experiments
- **Hardware Manuals**: Device-specific documentation
- **Community**: User community and collaboration opportunities
- **Training**: Workshops and tutorials for new users

## Related Guides

- [Experiment Development Guide](EXPERIMENT_DEVELOPMENT.md) - Detailed guide for creating new experiments
- [Device Development Guide](DEVICE_DEVELOPMENT.md) - Guide for creating new hardware devices
- [Configuration Files Guide](CONFIGURATION_FILES.md) - How to configure the system

---

This development guide provides a foundation for professional software development practices while maintaining the scientific rigor required for quantum physics research. Regular updates and improvements ensure the system remains cutting-edge and user-friendly. 