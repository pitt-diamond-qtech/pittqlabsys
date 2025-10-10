# Dutt-Features Branch Roadmap

This document outlines the planned features and improvements for the `dutt-features` branch, building on the successful parameter validation feedback system.

## 🎯 **Priority Features**

### 1. **Sub-Experiments & Bidirectional Data Flow**
**Status**: Planning Phase  
**Description**: Implement advanced experiment composition where experiments can call other experiments and share data bidirectionally.

**Key Components**:
- **ExperimentIterator Framework**: Support for nested iterators and complex multi-variable scans
- **Bidirectional Data Flow**: Parent ↔ Child experiment data sharing
- **Dynamic Experiment Composition**: Programmatic creation and arrangement of experiment sequences
- **GUI Integration**: Visual representation of sub-experiments with composition controls
- **SharedDataStore**: Centralized data management with versioning and real-time synchronization

**Technical Approach**:
- Design `EnhancedExperiment` base class with sub-experiment support
- Implement `SharedDataStore` for data persistence (HDF5 for arrays, JSON/AQS for metadata)
- Create GUI components for experiment composition and data flow visualization
- Add persistence backend pattern to separate storage logic from data

### 2. **Parameter Tolerance System**
**Status**: Planning Phase  
**Description**: Implement device-specific tolerance handling for parameter validation to avoid flagging insignificant differences.

**Key Components**:
- **Device-Specific Tolerances**: Different tolerance levels for different device types
- **Tolerance Types**: Absolute and relative tolerance support
- **Smart Comparison**: Avoid false positives for "device_different" feedback
- **Configuration**: Easy tolerance adjustment per device/parameter

**Technical Approach**:
- Extend device validation to include tolerance-aware comparison
- Add tolerance configuration to device JSON files
- Implement tolerance-based "device_different" detection
- Update GUI to show tolerance-aware feedback

### 3. **Enhanced GUI Input Formatting**
**Status**: Planning Phase  
**Description**: Make parameter input more user-friendly with intelligent unit parsing and scientific notation support.

**Key Components**:
- **Unit Parsing**: Support for GHz, MHz, kHz, Hz, ns, μs, ms, s, etc.
- **Scientific Notation**: Automatic conversion (3.87 GHz → 3.87e9 Hz)
- **Smart Input**: Context-aware parsing based on parameter type
- **Display Formatting**: Show values in appropriate units (GHz instead of Hz)

**Technical Approach**:
- Enhance `_parse_number()` function with unit parsing
- Add unit conversion utilities
- Implement context-aware input parsing
- Update GUI display to show values in user-friendly units
- Add unit hints/labels in the GUI

### 4. **Dataset Tab Functionality**
**Status**: Investigation Phase  
**Description**: Restore and enhance the dataset tab functionality for loading and displaying experiment data.

**Key Components**:
- **Data Loading**: Ability to load and display datasets in the GUI
- **Data Visualization**: Basic plotting and data exploration
- **Data Management**: Organize and browse experiment results
- **Export/Import**: Save and load dataset configurations

**Technical Approach**:
- Investigate existing dataset tab implementation
- Restore dataset loading functionality
- Add data visualization capabilities
- Implement data browsing and management features

## 🔧 **Technical Infrastructure**

### **Data Storage Strategy**
- **HDF5**: For large experiment data (arrays, time-series)
- **JSON/AQS**: For settings, metadata, and relationships
- **Hybrid Approach**: Separate data storage from metadata storage

### **Architecture Patterns**
- **Persistence Backend**: Separate data storage logic from data itself
- **SharedDataStore**: Centralized data management with versioning
- **EnhancedExperiment**: Base class with sub-experiment support

## 📋 **Implementation Phases**

### **Phase 1: Foundation** (Current)
- ✅ Parameter validation feedback system
- ✅ Visual feedback (orange/green/red backgrounds)
- ✅ Auto-clear timers
- ✅ GUI history integration

### **Phase 2: Enhanced Input** (Next)
- 🔄 Unit parsing and scientific notation
- 🔄 Smart input formatting
- 🔄 Context-aware validation

### **Phase 3: Tolerance System**
- 🔄 Device-specific tolerance configuration
- 🔄 Tolerance-aware validation
- 🔄 Smart "device_different" detection

### **Phase 4: Sub-Experiments**
- 🔄 ExperimentIterator framework
- 🔄 Bidirectional data flow
- 🔄 Dynamic experiment composition
- 🔄 GUI integration

### **Phase 5: Dataset Management**
- 🔄 Dataset tab restoration
- 🔄 Data visualization
- 🔄 Data management features

## 🎨 **GUI Enhancements**

### **Parameter Input**
- Unit-aware input fields
- Scientific notation support
- Context-sensitive validation
- Real-time unit conversion

### **Experiment Composition**
- Visual experiment builder
- Data flow visualization
- Sub-experiment management
- Composition controls

### **Data Visualization**
- Dataset browsing
- Basic plotting capabilities
- Data exploration tools
- Export/import functionality

## 📝 **Notes & Ideas**

### **Future Considerations**
- **Real-time Collaboration**: Multiple users working on same experiment
- **Experiment Templates**: Pre-built experiment configurations
- **Advanced Visualization**: 3D plotting, interactive graphs
- **Plugin System**: Extensible architecture for custom devices/experiments
- **Cloud Integration**: Remote experiment execution and data storage

### **User Experience**
- **Intuitive Workflows**: Streamlined experiment creation and execution
- **Clear Feedback**: Visual indicators for all system states
- **Error Prevention**: Proactive validation and helpful error messages
- **Documentation**: In-app help and tutorials

## 🚀 **Success Metrics**

- **User Adoption**: Increased usage of advanced features
- **Error Reduction**: Fewer parameter validation errors
- **Workflow Efficiency**: Faster experiment setup and execution
- **Data Quality**: Better experiment data organization and accessibility

---

**Last Updated**: October 10, 2025  
**Branch**: `dutt-features`  
**Status**: Active Development
