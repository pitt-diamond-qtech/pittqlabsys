# AQuISS - Advanced Quantum Information Science System

[![License: GPL v2](https://img.shields.io/badge/License-GPL%20v2-blue.svg)](https://www.gnu.org/licenses/old-licenses/gpl-2.0.en.html)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![PyQt5](https://img.shields.io/badge/PyQt5-5.15+-green.svg)](https://pypi.org/project/PyQt5/)

AQuISS is a comprehensive Python-based laboratory automation and data acquisition system designed for quantum information science experiments, with particular focus on nitrogen-vacancy (NV) center research in diamond.

## 🎯 Overview

AQuISS provides a modular, extensible framework for controlling scientific instruments and automating complex quantum physics experiments. The system features:

- **Real-time data acquisition** with live plotting using PyQtGraph
- **Modular device drivers** for various scientific instruments
- **Experiment automation** with parameterized experiment definitions
- **Professional GUI** built with PyQt5
- **Comprehensive data analysis** and export capabilities

## 🏗️ Architecture

AQuISS follows a Model-View-Controller (MVC) architecture:

```
src/
├── Controller/          # Hardware device drivers and control interfaces
├── Model/              # Experiment definitions, data processing, and analysis
├── View/               # PyQt5 GUI components and plotting
└── core/               # Core framework classes and utilities
```

### Key Components

- **Device Layer**: Abstracted hardware control through device classes
- **Experiment Layer**: Modular experiment definitions with parameter management
- **GUI Layer**: Configurable interface with real-time data visualization
- **Data Layer**: Flexible data storage and export capabilities

## 🚀 Installation

### Prerequisites

- Python 3.8 or higher
- Git

### Quick Start

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-org/pittqlabsys.git
cd pittqlabsys
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Launch the GUI**:
   ```bash
   python src/app.py
   ```

## 🔧 Cross-Platform Setup Notes

### macOS Setup

When setting up AQuISS on macOS, you may encounter the following issues and solutions:

#### Configuration File Paths
**Issue**: Hardcoded Windows paths in configuration files
**Solution**: Update `src/View/gui_config.json` to use macOS-compatible paths:
```json
{
    "last_save_path": "/Users/your-username/Experiments/AQuISS_default_save_location/workspace_config.json"
}
```

#### Missing Dependencies
**Issue**: Missing packages like `h5py` and `sympy` not in requirements.txt
**Solution**: Install additional dependencies:
```bash
pip install h5py sympy
```

#### Python Path Issues
**Issue**: Module import errors when running `src/app.py`
**Solution**: Set the PYTHONPATH environment variable:
```bash
PYTHONPATH=/path/to/pittqlabsys python src/app.py
```

### Windows Setup

On Windows systems, the setup is typically more straightforward as most dependencies are pre-compiled. However, ensure you have:

## ⚙️ Configuration

### Configuration Files

AQuISS uses several configuration files for different purposes:

#### 1. `src/config.json` - Application Defaults ✅
- **Purpose**: Contains system-wide default paths, settings, and environment configuration
- **Status**: Tracked in git (shared across all installations)
- **Content**: Default folder locations, application settings, environment flags
- **Location**: `src/config.json`

#### 2. `src/View/gui_config.json` - User Settings ❌
- **Purpose**: Stores user-specific preferences and paths
- **Status**: NOT tracked in git (personal to each user)
- **Content**: Last save paths, personal folder preferences
- **Location**: `src/View/gui_config.json`

#### 3. `src/View/gui_config.template.json` - Template for New Installations ✅
- **Purpose**: Template file for new users to create their own `gui_config.json`
- **Status**: Tracked in git (template for new installations)
- **Content**: Empty structure with placeholder values
- **Location**: `src/View/gui_config.template.json`

### First-Time Setup

When setting up AQuISS for the first time:

1. **Copy the template**:
   ```bash
   cp src/View/gui_config.template.json src/View/gui_config.json
   ```

2. **Customize the paths** for your system:
   ```json
   {
       "gui_settings": {
           "experiments_folder": "/path/to/your/experiments",
           "data_folder": "/path/to/your/data",
           "probes_folder": "/path/to/your/probes"
       }
   }
   ```

3. **The GUI will automatically** populate these paths when you use the application

### Environment Configuration

AQuISS uses environment-specific configuration files to avoid git conflicts between different machines:

#### **Environment-Specific Config Files:**

- **`src/config.lab.json`** - Lab PC configuration (real hardware) ❌ NOT tracked in git
- **`src/config.dev.json`** - Development machine configuration (mock devices) ❌ NOT tracked in git  
- **`src/config.json`** - Base configuration (shared defaults) ✅ Tracked in git
- **`src/config.template.json`** - Template for new installations ✅ Tracked in git

#### **Setup Instructions:**

**For Lab PC (real hardware):**
```bash
# Copy the lab-specific config
cp src/config.lab.json src/config.json
```

**For Development Machine (mock devices):**
```bash
# Copy the development-specific config
cp src/config.dev.json src/config.json
```

**For New Installation:**
```bash
# Copy the template and customize
cp src/config.template.json src/config.json
# Edit config.json to set your environment
```

#### **Environment Flags:**

- **`is_development`**: Set to `true` for development machines using mock devices
- **`is_mock`**: Set to `true` to force mock device usage
- **`force_mock_devices`**: Set to `true` to override hardware detection
- **`hardware_detection_enabled`**: Set to `false` to disable automatic hardware detection

#### **Benefits:**

✅ **No git conflicts** - Each machine has its own config  
✅ **Easy setup** - Just copy the appropriate config file  
✅ **Flexible** - Easy to switch between environments  
✅ **Maintainable** - Clear separation of concerns

### Important Notes

- **Never commit** `gui_config.json` - it contains personal settings
- **Always commit** `config.json` - it contains application defaults
- **Each lab PC** should have its own `gui_config.json`
- **Template file** provides starting point for new installations

- Visual Studio Build Tools (if compiling from source)
- Proper Python environment variables set
- Git Bash or similar for command-line operations

### Linux Setup

For Linux systems, you may need to install system-level dependencies:

```bash
# Ubuntu/Debian
sudo apt-get install python3-dev libpq-dev

# CentOS/RHEL
sudo yum install python3-devel postgresql-devel
```

## 📋 Supported Hardware

AQuISS includes drivers for the following instruments:

### Positioning Systems
- **MCL NanoDrive**: 3D nanopositioning stages
- **Galvo Scanners**: 2D scanning mirrors

### Data Acquisition
- **ADwin Gold II**: Real-time data acquisition and processing
- **NI DAQ Cards**: Various National Instruments data acquisition cards
  - PXI6733
  - NI6281
  - PCI6229
  - PCI6601

### Signal Generation
- **Microwave Generators**: SRS385, Windfreak Synth USB II
- **Arbitrary Waveform Generators**: AWG520
- **Pulse Blasters**: Digital pulse generation

### Other Instruments
- **USB RF Generators**: RF signal generation
- **SpinCore Drivers**: Specialized quantum control hardware

## 🔬 Available Experiments

### Confocal Microscopy
- **ConfocalScan_Fast**: High-speed 2D scanning for large images
- **ConfocalScan_Slow**: Precise point-by-point scanning
- **Confocal_Point**: Single-point fluorescence measurements

### Quantum Sensing
- **ODMR**: Optically Detected Magnetic Resonance
- **NV Location**: Automated NV center finding algorithms

### Data Acquisition
- **DAQ Read Counter**: Photon counting experiments
- **Galvo Scan**: Galvanometer-based scanning

### Utility
- **Select Points**: Interactive point selection for experiments
- **Example Experiments**: Templates for new experiment development

## 🛠️ Development

### Adding New Devices

1. Create a new device class in `src/Controller/`
2. Inherit from the base `Device` class
3. Define `_DEFAULT_SETTINGS` and `_PROBES`
4. Implement required methods: `update()`, `read_probes()`, `is_connected`

Example:
```python
from src.core import Device, Parameter

class MyDevice(Device):
    _DEFAULT_SETTINGS = [
        Parameter('frequency', 1e9, float, 'Frequency in Hz'),
        Parameter('power', 0.0, float, 'Power in dBm')
    ]
    
    _PROBES = {
        'temperature': 'Device temperature in Celsius',
        'status': 'Device status string'
    }
    
    def update(self, settings):
        # Update device parameters
        pass
    
    def read_probes(self, key):
        # Read device values
        pass
    
    @property
    def is_connected(self):
        return self._is_connected
```

### Adding New Experiments

1. Create a new experiment class in `src/Model/experiments/`
2. Inherit from the base `Experiment` class
3. Define `_DEFAULT_SETTINGS`, `_DEVICES`, and `_EXPERIMENTS`
4. Implement the `_function()` method for experiment logic
5. Implement `_plot()` and `_update()` for visualization

Example:
```python
from src.core import Experiment, Parameter

class MyExperiment(Experiment):
    _DEFAULT_SETTINGS = [
        Parameter('duration', 10.0, float, 'Experiment duration in seconds'),
        Parameter('samples', 1000, int, 'Number of data points')
    ]
    
    _DEVICES = {'my_device': MyDevice()}
    _EXPERIMENTS = {}
    
    def _function(self):
        # Implement experiment logic
        pass
    
    def _plot(self, axes_list):
        # Implement plotting
        pass
```

### Code Style Guidelines

- Follow PEP 8 style guidelines
- Use type hints where appropriate
- Include comprehensive docstrings
- Write unit tests for new functionality
- Use meaningful variable and function names

## 📊 Data Management

AQuISS supports multiple data formats:

- **AQS Format**: Native format with experiment metadata
- **MATLAB**: `.mat` files for compatibility with MATLAB
- **CSV**: Tabular data export
- **Images**: Plot exports in various formats

### Data Organization

```
data/
├── raw_data/           # Raw experimental data
├── processed_data/     # Analyzed results
└── experiments/        # Experiment configurations
```

## 🧪 Testing

Run the test suite:

```bash
pytest tests/
```

Generate coverage reports:

```bash
pytest --cov=src tests/
```

## 📚 Documentation

- **API Documentation**: Generated from docstrings
- **User Manual**: GUI usage and experiment setup
- **Developer Guide**: Architecture and extension guidelines
- **Hardware Manual**: Device connection and configuration
- **[Configuration Files](docs/CONFIGURATION_FILES.md)**: Complete guide to configuration file structure and management

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and add tests
4. Commit your changes: `git commit -am 'Add feature'`
5. Push to the branch: `git push origin feature-name`
6. Submit a pull request

## 📄 License

This project is licensed under the GNU General Public License v2.0 - see the [LICENSE](LICENSE) file for details.

## 👥 Authors

- **Gurudev Dutt** - *Initial development* - [gdutt@pitt.edu](mailto:gdutt@pitt.edu)
- **Contributors** - See [CONTRIBUTORS.md](CONTRIBUTORS.md)

## 🙏 Acknowledgments

- **pylabcontrol**: This project has been heavily influenced by the excellent laboratory automation framework [pylabcontrol](https://github.com/BBN-Q/pylabcontrol) developed by the BBN-Q group. Many architectural decisions and design patterns in AQuISS are inspired by their work.

- **b26-toolkit**: The [LISE-B26/b26-toolkit](https://github.com/LISE-B26/b26-toolkit) project has provided valuable insights into quantum control and measurement techniques that have informed the development of several experiments in AQuISS.

- **Quantum Information Science community**: The broader QIS community for ongoing collaboration and knowledge sharing
- **National Science Foundation (NSF)**: For funding support of quantum research infrastructure
- **University of Pittsburgh**: For infrastructure support and research facilities

## 📞 Support

For questions, bug reports, or feature requests:

- **Issues**: [GitHub Issues](https://github.com/your-org/pittqlabsys/issues)
- **Email**: [gdutt@pitt.edu](mailto:gdutt@pitt.edu)
- **Documentation**: [Wiki](https://github.com/your-org/pittqlabsys/wiki)

---

**Note**: This software is designed for research use. Always verify experimental results independently and follow proper laboratory safety protocols.
