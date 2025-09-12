# AQuISS Documentation

Welcome to the AQuISS (Automated Quantum Information Science System) documentation. This is your central hub for understanding, developing, and using the AQuISS system.

## 🎯 Quick Start

### For Users
- **[Installation Guide](#installation)** - Get AQuISS running on your system
- **[User Manual](#user-manual)** - Learn how to use the GUI and run experiments
- **[Configuration Guide](#configuration)** - Set up devices and experiments

### For Developers
- **[Development Overview](#development-overview)** - Architecture and development practices
- **[Device Development](#device-development)** - Create new hardware device drivers
- **[Experiment Development](#experiment-development)** - Create new scientific experiments
- **[API Reference](#api-reference)** - Detailed class and method documentation

## 📚 Documentation Structure

### Core Documentation

| Document | Purpose | Audience |
|----------|---------|----------|
| **[Installation Guide](INSTALLATION.md)** | System setup and installation | All users |
| **[User Manual](USER_MANUAL.md)** | GUI usage and experiment execution | End users |
| **[Configuration Guide](CONFIGURATION_FILES.md)** | Device and experiment configuration | Lab administrators |

### Development Documentation

| Document | Purpose | Audience |
|----------|---------|----------|
| **[Development Guide](DEVELOPMENT_GUIDE.md)** | General development practices and standards | All developers |
| **[Device Development Guide](DEVICE_DEVELOPMENT.md)** | Creating hardware device drivers | Device developers |
| **[Experiment Development Guide](EXPERIMENT_DEVELOPMENT.md)** | Creating scientific experiments | Experiment developers |
| **[API Reference](API_REFERENCE.md)** | Detailed class and method documentation | All developers |

### Specialized Documentation

| Document | Purpose | Audience |
|----------|---------|----------|
| **[Recent Updates](RECENT_UPDATES.md)** | Latest bug fixes and new features | All users |
| **[Parameter Class Analysis](PARAMETER_CLASS_SUMMARY.md)** | Deep dive into Parameter class | Advanced developers |
| **[Troubleshooting Guide](TROUBLESHOOTING.md)** | Common issues and solutions | All users |

## 🚀 Getting Started

### Installation

1. **Prerequisites**: Python 3.8+, Git, Virtual environment
2. **Clone Repository**: `git clone <repository-url>`
3. **Setup Environment**: Follow [Installation Guide](INSTALLATION.md)
4. **Configure System**: See [Configuration Guide](CONFIGURATION_FILES.md)

### First Steps

1. **Launch AQuISS**: `python src/app.py`
2. **Configure Devices**: Add your hardware in the device tree
3. **Run Example Experiment**: Try the built-in examples
4. **Check Logs**: Monitor the log window for any issues

## 🏗️ System Architecture

### Core Components

```
AQuISS/
├── src/
│   ├── core/           # Framework classes (Device, Experiment, Parameter)
│   ├── Controller/     # Hardware device drivers
│   ├── Model/          # Experiment definitions and data processing
│   └── View/           # GUI components and visualization
├── tests/              # Comprehensive test suite
├── docs/               # This documentation
└── examples/           # Example experiments and usage
```

### Key Classes

- **`Device`**: Base class for all hardware devices
- **`Experiment`**: Base class for all scientific experiments
- **`Parameter`**: Configuration parameter management
- **`ExperimentManager`**: Experiment execution and management

## 🔧 Development Workflow

### 1. Setting Up Development Environment

```bash
# Clone and setup
git clone <repository-url>
cd aquiss
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### 2. Creating New Devices

See [Device Development Guide](DEVICE_DEVELOPMENT.md) for detailed instructions:

```python
from src.core import Device, Parameter

class MyDevice(Device):
    _DEFAULT_SETTINGS = [
        Parameter('frequency', 1e9, float, 'Frequency in Hz'),
        Parameter('power', 0.0, float, 'Power in dBm'),
    ]
    
    def update(self, settings):
        # Device-specific update logic
        pass
```

### 3. Creating New Experiments

See [Experiment Development Guide](EXPERIMENT_DEVELOPMENT.md) for detailed instructions:

```python
from src.core import Experiment, Parameter

class MyExperiment(Experiment):
    _DEFAULT_SETTINGS = [
        Parameter('duration', 10.0, float, 'Experiment duration'),
    ]
    
    _DEVICES = {
        'device1': 'device1',  # Maps to config.json
    }
    
    def _function(self):
        # Experiment logic
        pass
```

### 4. Testing Your Code

```bash
# Run all tests
pytest tests/

# Run specific test categories
pytest tests/test_device_inheritance.py -v
pytest tests/test_experiment_base_class.py -v

# Run with coverage
pytest --cov=src tests/
```

## 📋 Common Tasks

### Adding a New Device

1. **Create Device Class**: Follow [Device Development Guide](DEVICE_DEVELOPMENT.md)
2. **Add to Registry**: Update `src/Controller/__init__.py`
3. **Write Tests**: Create comprehensive test suite
4. **Update Documentation**: Add device-specific docs

### Adding a New Experiment

1. **Create Experiment Class**: Follow [Experiment Development Guide](EXPERIMENT_DEVELOPMENT.md)
2. **Define Device Requirements**: Specify in `_DEVICES`
3. **Implement Core Methods**: `_function()`, `_plot()`, `_update()`
4. **Write Tests**: Test with mock devices
5. **Add to GUI**: Update experiment list

### Configuring the System

1. **Copy Sample Config**: `cp config.sample.json src/config.json`
2. **Edit Device Settings**: Configure your hardware
3. **Set Data Paths**: Specify where to save data
4. **Test Configuration**: Verify all devices connect

## 🔍 Troubleshooting

### Common Issues

| Issue | Solution | Documentation |
|-------|----------|---------------|
| Device connection fails | Check hardware connections and drivers | [Troubleshooting Guide](TROUBLESHOOTING.md) |
| Experiment won't run | Verify device requirements and settings | [Experiment Development Guide](EXPERIMENT_DEVELOPMENT.md) |
| Import errors | Check Python path and dependencies | [Installation Guide](INSTALLATION.md) |
| GUI crashes | Check PyQt5 installation and display settings | [User Manual](USER_MANUAL.md) |

### Getting Help

1. **Check Documentation**: Search this index for relevant guides
2. **Review Recent Updates**: See [Recent Updates](RECENT_UPDATES.md) for latest fixes
3. **Run Tests**: Verify system functionality with `pytest tests/`
4. **Check Logs**: Look for error messages in the GUI log window

## 📈 Recent Updates

### Version 1.1.0 - Lab PC Compatibility and Path Configuration

**Key Improvements:**
- ✅ Fixed module import errors during experiment export
- ✅ Implemented proper device parameter inheritance
- ✅ Added configurable data path system
- ✅ Enhanced base experiment class with robust path management
- ✅ Comprehensive testing with 26+ new tests

**For Details:** See [Recent Updates](RECENT_UPDATES.md)

## 🤝 Contributing

### How to Contribute

1. **Fork Repository**: Create your own fork
2. **Create Feature Branch**: `git checkout -b feature/my-feature`
3. **Follow Standards**: See [Development Guide](DEVELOPMENT_GUIDE.md)
4. **Write Tests**: Include tests for new functionality
5. **Submit Pull Request**: Include description and test results

### Development Standards

- **Code Style**: Follow PEP 8 with Black formatting
- **Type Hints**: Use type hints for all functions
- **Documentation**: Write comprehensive docstrings
- **Testing**: Include unit and integration tests
- **Error Handling**: Implement robust exception handling

## 📞 Support and Resources

### Documentation Links

- **[Installation Guide](INSTALLATION.md)** - System setup
- **[User Manual](USER_MANUAL.md)** - GUI usage
- **[Configuration Guide](CONFIGURATION_FILES.md)** - System configuration
- **[Development Guide](DEVELOPMENT_GUIDE.md)** - Development practices
- **[Device Development Guide](DEVICE_DEVELOPMENT.md)** - Hardware drivers
- **[Experiment Development Guide](EXPERIMENT_DEVELOPMENT.md)** - Scientific experiments
- **[Recent Updates](RECENT_UPDATES.md)** - Latest changes
- **[Troubleshooting Guide](TROUBLESHOOTING.md)** - Common issues

### External Resources

- **PyQt5 Documentation**: GUI framework
- **PyQtGraph Documentation**: Plotting library
- **NumPy Documentation**: Numerical computing
- **SciPy Documentation**: Scientific computing

## 📊 System Status

### Test Coverage
- **Unit Tests**: 50+ tests covering core functionality
- **Integration Tests**: End-to-end experiment workflows
- **Device Tests**: Hardware-independent testing
- **All Tests Passing**: ✅

### Supported Platforms
- **Windows**: 10/11 with Python 3.8+
- **macOS**: 10.15+ with Python 3.8+
- **Linux**: Ubuntu 18.04+ with Python 3.8+

### Hardware Support
- **Microwave Generators**: SG384, AWG520
- **Data Acquisition**: NI DAQ, PXI systems
- **Positioning**: Nanodrive, Adwin systems
- **Optics**: Confocal microscopes, spectrometers

---

## 📝 Documentation Index

### Quick Reference

| Need Help With | Go To |
|----------------|-------|
| Installing AQuISS | [Installation Guide](INSTALLATION.md) |
| Using the GUI | [User Manual](USER_MANUAL.md) |
| Configuring devices | [Configuration Guide](CONFIGURATION_FILES.md) |
| Creating devices | [Device Development Guide](DEVICE_DEVELOPMENT.md) |
| Creating experiments | [Experiment Development Guide](EXPERIMENT_DEVELOPMENT.md) |
| Development practices | [Development Guide](DEVELOPMENT_GUIDE.md) |
| Latest updates | [Recent Updates](RECENT_UPDATES.md) |
| Troubleshooting | [Troubleshooting Guide](TROUBLESHOOTING.md) |

### Detailed Guides

- **[Installation Guide](INSTALLATION.md)** - Complete setup instructions
- **[User Manual](USER_MANUAL.md)** - GUI usage and experiment execution
- **[Configuration Guide](CONFIGURATION_FILES.md)** - Device and experiment configuration
- **[Development Guide](DEVELOPMENT_GUIDE.md)** - Development practices and standards
- **[Device Development Guide](DEVICE_DEVELOPMENT.md)** - Creating hardware device drivers
- **[Experiment Development Guide](EXPERIMENT_DEVELOPMENT.md)** - Creating scientific experiments
- **[API Reference](API_REFERENCE.md)** - Detailed class and method documentation
- **[Recent Updates](RECENT_UPDATES.md)** - Latest bug fixes and new features
- **[Troubleshooting Guide](TROUBLESHOOTING.md)** - Common issues and solutions

---

*This documentation is maintained by the AQuISS development team. For questions or contributions, please see the [Contributing](#contributing) section above.*

*Last updated: September 2025*
