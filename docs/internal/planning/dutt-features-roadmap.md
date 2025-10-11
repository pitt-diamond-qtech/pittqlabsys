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

### 2. **Device Parameter Tolerance and Validation System** (HIGH PRIORITY)
**Status**: Ready for Implementation  
**Description**: Comprehensive device parameter tolerance and validation system to ensure device values are within acceptable ranges and provide honest feedback about actual vs requested values.

**Key Components**:
- **Tolerance Configuration**: JSON-based tolerance settings per device and parameter
- **Base Validation Framework**: Enhanced Device class with tolerance validation methods
- **Actual Value Checking**: Call `device.update_and_get()` after validation
- **Device-Specific Tolerances**: Different tolerance levels for different device types and parameters
- **Visual Feedback**: New `'device_different'` state (yellow background) for out-of-tolerance values
- **Honest Reporting**: Show both requested and actual values in GUI history
- **Parameter Enhancement**: Extended Parameter class with tolerance support

**Technical Approach**:
- **Config Structure**: Add `tolerance_settings` section to device JSON configs
- **Base Device Class**: Add `validate_parameter_tolerance()` and `check_all_parameters_tolerance()` methods
- **Parameter Class**: Extend with `tolerance_percent`, `tolerance_absolute`, `validation_enabled` parameters
- **Device Integration**: Update specific device classes to use tolerance validation
- **GUI Integration**: Add `'device_different'` visual state to NumberClampDelegate
- **Tolerance Logic**: Implement both percentage and absolute tolerance checking

**Configuration Example**:
```json
{
    "devices": {
        "sg384": {
            "tolerance_settings": {
                "frequency": {
                    "tolerance_percent": 0.1,
                    "tolerance_absolute": 1000,
                    "validation_enabled": true,
                    "warning_threshold": 0.05
                },
                "power": {
                    "tolerance_percent": 2.0,
                    "tolerance_absolute": 0.5,
                    "validation_enabled": true,
                    "warning_threshold": 1.0
                }
            }
        }
    }
}
```

**Validation Flow**:
1. User sets parameter value
2. Device applies value to hardware
3. Device reads back actual value using `update_and_get()`
4. Compare target vs actual using tolerance settings
5. Flag if outside tolerance with appropriate visual feedback
6. Provide detailed user feedback about requested vs actual values

**Example**:
- User requests: 50.0 μm
- Device reports: 49.5 μm  
- Tolerance: ±1% (0.5 μm)
- Current: Shows green "success" (misleading!)
- New: Shows yellow "device_different" with message "Requested 50.0 μm, device reported 49.5 μm (within 1% tolerance)"

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

### **Phase 2: Device Actual Value Reporting** (Next - After Weekend)
- 🔄 Actual value checking after validation
- 🔄 Device-specific tolerance system
- 🔄 "device_different" visual state (yellow background)
- 🔄 Honest reporting of requested vs actual values

### **Phase 3: Enhanced Input**
- 🔄 Unit parsing and scientific notation
- 🔄 Smart input formatting
- 🔄 Context-aware validation

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
