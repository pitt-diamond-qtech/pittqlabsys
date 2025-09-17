# Hardware Setup and Configuration

This section contains guides for setting up and configuring hardware devices in PittQLabSys.

## 🖥️ Device Setup Guides

### Signal Generators
- [AWG520 Setup](awg520-setup.md) - AWG520 signal generator configuration
- [SG384 Setup](sg384-setup.md) - SG384 microwave generator setup

### Control Systems
- [MUX Control Setup](mux-control-setup.md) - Multiplexer control configuration
- [Hardware Connections](hardware-connections.md) - General hardware connection setup

### Development Tools
- [ADbasic Compiler Setup](adbasic-compiler-setup.md) - Setting up ADbasic compiler
- [AWG520-ADwin Testing](awg520-adwin-testing.md) - Testing AWG520 with ADwin

## 🚀 Quick Start

### 1. Basic Setup
1. Start with [Hardware Connections](hardware-connections.md) for general setup
2. Configure specific devices using their individual guides
3. Test connections using [Testing with Mock](../development/testing-with-mock.md)

### 2. Device-Specific Setup
1. **AWG520**: Follow [AWG520 Setup](awg520-setup.md)
2. **SG384**: Follow [SG384 Setup](sg384-setup.md)
3. **MUX Control**: Follow [MUX Control Setup](mux-control-setup.md)

### 3. Testing
1. Use [Testing with Mock](../development/testing-with-mock.md) for development
2. Test with real hardware when available
3. Use device-specific testing guides

## 📋 Prerequisites

Before setting up hardware, ensure you have:

- **Device drivers** installed
- **Physical connections** made
- **Power supplies** connected
- **Network access** (for network devices)
- **Serial/USB ports** available (for serial devices)

## 🔧 Common Setup Tasks

### Signal Generators
- Install device drivers
- Configure network settings
- Set up frequency and power ranges
- Test signal output

### Control Systems
- Install control software
- Configure communication protocols
- Set up safety interlocks
- Test control functions

### Data Acquisition
- Install ADwin drivers
- Set up ADbasic compiler
- Configure input/output channels
- Test data acquisition

## 🎯 Troubleshooting

### Common Issues
1. **Device not detected**: Check drivers and connections
2. **Communication errors**: Verify network/serial settings
3. **Permission errors**: Check user permissions
4. **Port conflicts**: Ensure ports are not in use

### Debugging Steps
1. **Check connections** - Physical and logical
2. **Verify drivers** - Install latest versions
3. **Test communication** - Use device-specific tools
4. **Check logs** - Look for error messages
5. **Ask for help** - Contact experienced team members

## 🔗 Related Resources

### Development
- [Testing with Mock](../development/testing-with-mock.md) - Testing without hardware
- [Development Guide](../development/development-guide.md) - General development

### Technical Reference
- [Configuration Reference](../../reference/configuration.md) - System configuration
- [Device Configuration](../../reference/device-configuration.md) - Device settings

### Examples
- [ODMR Experiments](../examples/odmr-experiments.md) - Example experiments
- [Hardware Examples](../examples/) - More examples

## 📝 Adding New Hardware Guides

When creating new hardware guides:

1. **Follow the existing format** and structure
2. **Include prerequisites** and setup steps
3. **Add troubleshooting** section
4. **Include testing** instructions
5. **Update this README** to include your guide

## 🔄 Recent Updates

- **2024-09-17**: Reorganized hardware guides into logical structure
- **2024-09-17**: Added troubleshooting section
- **2024-09-17**: Improved cross-references to related guides

---

*These guides help you set up and configure hardware for PittQLabSys. For technical details, check the [Reference](../../reference/) section.*
