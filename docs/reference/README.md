# Technical Reference

This section contains detailed technical documentation for PittQLabSys.

## 📋 Configuration and Setup

### System Configuration
- [Configuration Files](configuration.md) - Configuration file structure and usage
- [Device Configuration](device-configuration.md) - Device configuration details

### Parameter System
- [Parameter Class Analysis](parameter-class-analysis.md) - Detailed parameter system analysis
- [Parameter Class Summary](parameter-class-summary.md) - Parameter system summary

## 🔧 API Reference

### Core Classes
- **Device** - Base class for all hardware devices
- **Experiment** - Base class for all experiments
- **Parameter** - Parameter management system

### Device Classes
- **AdwinGoldDevice** - ADwin Gold II data acquisition
- **SG384Generator** - SG384 microwave generator
- **AWG520Generator** - AWG520 signal generator
- **MCLNanoDrive** - MCL NanoDrive positioning

### Experiment Classes
- **ODMRSweepContinuousExperiment** - Continuous ODMR sweeps
- **NanodriveAdwinConfocalScanFast** - Fast confocal scanning
- **Custom experiments** - User-defined experiments

## 📊 Data Formats

### File Formats
- **JSON** - Configuration and data files
- **NPZ** - NumPy compressed data files
- **CSV** - Comma-separated value files
- **AQS** - Legacy AQuISS format (backward compatibility)

### Data Structures
- **Parameter objects** - Hierarchical parameter management
- **Device settings** - Device configuration structures
- **Experiment data** - Experiment result data structures

## 🔌 Hardware Interfaces

### Communication Protocols
- **Serial/RS232** - Serial communication
- **TCP/IP** - Network communication
- **USB** - USB device communication
- **GPIB** - IEEE 488.2 communication

### Device Drivers
- **ADwin drivers** - ADwin Gold II drivers
- **VISA drivers** - VISA instrument drivers
- **Custom drivers** - Device-specific drivers

## 📝 Code Standards

### Coding Conventions
- **PEP 8** - Python style guide
- **Type hints** - Type annotations
- **Docstrings** - Documentation strings
- **Error handling** - Exception management

### Testing Standards
- **Unit tests** - Individual component testing
- **Integration tests** - Component interaction testing
- **Hardware tests** - Real hardware testing
- **Mock testing** - Simulated hardware testing

## 🔍 Debugging and Troubleshooting

### Common Issues
- **Device connection errors** - Hardware communication problems
- **Parameter validation errors** - Parameter system issues
- **Configuration errors** - Setup and configuration problems
- **Performance issues** - System performance problems

### Debugging Tools
- **Logging system** - Comprehensive logging
- **Debug modes** - Debug output and tracing
- **Error reporting** - Detailed error information
- **Performance profiling** - Performance analysis tools
- [Debug ODMR Arrays Usage](debug-odmr-arrays-usage.md) - ADwin debugging tool

## 🔗 Related Resources

### Development Guides
- [Development Guide](../guides/development/development-guide.md) - General development
- [Quality Guidelines](../guides/development/quality-guidelines.md) - Code quality
- [Testing with Mock](../guides/development/testing-with-mock.md) - Testing

### Hardware Guides
- [Hardware Setup](../guides/hardware/) - Device configuration
- [Device Guides](../guides/hardware/) - Specific device setup

### Architecture
- [System Architecture](../architecture/) - High-level design
- [Device Architecture](../architecture/device-architecture.md) - Device system design

## 📝 Adding Reference Documentation

When adding reference documentation:

1. **Be comprehensive** - Include all relevant details
2. **Use clear examples** - Show how to use the features
3. **Keep it current** - Update when features change
4. **Cross-reference** - Link to related documentation
5. **Update this README** - Include your new documentation

## 🔄 Recent Updates

- **2024-09-17**: Reorganized reference documentation
- **2024-09-17**: Added API reference section
- **2024-09-17**: Improved cross-references to related guides

---

*This reference section provides detailed technical information for PittQLabSys. For user guides, check the [Guides](../guides/) section.*
