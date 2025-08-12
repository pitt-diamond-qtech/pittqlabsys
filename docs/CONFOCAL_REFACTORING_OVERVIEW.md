# Confocal Module Refactoring Overview

## **Overview**

The confocal module has been refactored from a single monolithic file containing three experiment classes into three separate, focused modules with hardware-specific naming. This refactoring improves code organization, maintainability, and clarity about hardware dependencies.

## **Why This Refactoring Was Needed**

### **1. Hardware-Specific Naming**
- **Before**: `confocal.py` (generic name, unclear hardware dependencies)
- **After**: 
  - `nanodrive_adwin_confocal_scan_fast.py` (clearly indicates MCL NanoDrive + ADwin)
  - `nanodrive_adwin_confocal_scan_slow.py` (clearly indicates MCL NanoDrive + ADwin)
  - `nanodrive_adwin_confocal_point.py` (clearly indicates MCL NanoDrive + ADwin)

### **2. Single Responsibility Principle**
- **Before**: One file with 3+ experiment classes
- **After**: One file per experiment class
- **Benefits**: Cleaner imports, better maintainability, easier to find specific functionality

### **3. Hardware Distinction**
- **NI-DAQ approach** (galvo_scan) vs **ADwin + Nanodrive approach** (confocal)
- **Different timing** and control mechanisms
- **Different data acquisition** strategies
- **Clear separation** by hardware platform

## **New Module Structure**

### **1. `nanodrive_adwin_confocal_scan_fast.py`**
- **Purpose**: Fast raster scanning using waveform-based approach
- **Hardware**: MCL NanoDrive + ADwin Gold II
- **Binary File**: `One_D_Scan.TB2`
- **Key Features**: 
  - Waveform-based scanning for speed
  - Warm-up/cool-down compensation
  - Optimized for larger images
  - Resolution: 0.001 - 2.0 μm

### **2. `nanodrive_adwin_confocal_scan_slow.py`**
- **Purpose**: Slow, high-precision point-by-point scanning
- **Hardware**: MCL NanoDrive + ADwin Gold II
- **Binary File**: `Trial_Counter.TB1`
- **Key Features**:
  - Point-by-point scanning for maximum precision
  - Settle time control for accuracy
  - Raster pattern optimization
  - Best image quality (slower execution)

### **3. `nanodrive_adwin_confocal_point.py`**
- **Purpose**: Single-point measurements and continuous counting
- **Hardware**: MCL NanoDrive + ADwin Gold II
- **Binary File**: `Averagable_Trial_Counter.TB1`
- **Key Features**:
  - Single point measurements
  - Continuous counting mode
  - Averaging over multiple cycles
  - Real-time plotting

## **Migration Guide**

### **For Existing Code**

#### **Option 1: Update Imports (Recommended)**
```python
# Before
from src.Model.experiments.confocal import ConfocalScan_Fast, ConfocalScan_Slow, Confocal_Point

# After
from src.Model.experiments.nanodrive_adwin_confocal_scan_fast import NanodriveAdwinConfocalScanFast
from src.Model.experiments.nanodrive_adwin_confocal_scan_slow import NanodriveAdwinConfocalScanSlow
from src.Model.experiments.nanodrive_adwin_confocal_point import NanodriveAdwinConfocalPoint
```

#### **Option 2: Keep Legacy Imports (Deprecated)**
```python
# Still works but generates deprecation warnings
from src.Model.experiments.confocal import ConfocalScan_Fast, ConfocalScan_Slow, Confocal_Point
```

### **For New Code**

Always use the new, focused modules:

```python
# Fast scanning for large areas
fast_scanner = NanodriveAdwinConfocalScanFast(devices=devices)

# Slow scanning for high precision
slow_scanner = NanodriveAdwinConfocalScanSlow(devices=devices)

# Single point measurements
point_measurement = NanodriveAdwinConfocalPoint(devices=devices)
```

## **Hardware Dependencies**

### **MCL NanoDrive**
- **Purpose**: Sample stage positioning (X, Y, Z)
- **Control**: Waveform-based or point-by-point
- **Range**: 0-100 μm (hardware limited)
- **Resolution**: Configurable (0.001 - 2.0 μm)

### **ADwin Gold II**
- **Purpose**: Photon counting and timing
- **Processes**: 
  - Process 1: Trial counter operations
  - Process 2: Array-based counting
- **Timing**: 3.3 ns resolution
- **Data**: Integer arrays and variables

### **ADbasic Binary Files**
- **`One_D_Scan.TB2`**: Fast scanning with array data
- **`Trial_Counter.TB1`**: Simple counter operations
- **`Averagable_Trial_Counter.TB1`**: Averaging over cycles

## **Performance Characteristics**

| Experiment Type | Speed | Precision | Use Case |
|----------------|-------|-----------|----------|
| **Fast Scan** | High | Good | Large area surveys, quick overview |
| **Slow Scan** | Low | Excellent | High-resolution imaging, publication quality |
| **Point** | N/A | Excellent | Single point analysis, optimization |

## **File Organization**

```
src/Model/experiments/
├── confocal.py                    # Legacy file (deprecated)
├── nanodrive_adwin_confocal_scan_fast.py    # New fast scanning
├── nanodrive_adwin_confocal_scan_slow.py    # New slow scanning
└── nanodrive_adwin_confocal_point.py        # New point measurements
```

## **Benefits of New Structure**

### **1. Clear Hardware Dependencies**
- Filenames immediately indicate hardware requirements
- Easier to understand system architecture
- Better documentation of dependencies

### **2. Improved Maintainability**
- One experiment per file
- Easier to locate specific functionality
- Reduced merge conflicts
- Cleaner git history

### **3. Better Code Organization**
- Logical separation of concerns
- Easier to extend individual experiments
- Clearer import structure
- Reduced cognitive load

### **4. Future-Proofing**
- Easier to add new hardware platforms
- Clear migration path for other experiments
- Consistent naming conventions
- Better scalability

## **Deprecation Timeline**

### **Phase 1: Current (Immediate)**
- ✅ New modules created and functional
- ✅ Legacy modules marked as deprecated
- ✅ Deprecation warnings added
- ✅ Documentation updated

### **Phase 2: Short Term (Next Release)**
- 🔄 Encourage migration to new modules
- 🔄 Update examples and tutorials
- 🔄 Monitor usage patterns

### **Phase 3: Long Term (Future Release)**
- 🗑️ Remove legacy modules
- 🗑️ Clean up deprecated code
- 🗑️ Finalize new architecture

## **Testing and Validation**

### **Backward Compatibility**
- ✅ All existing functionality preserved
- ✅ Same API and behavior
- ✅ Same hardware integration
- ✅ Same data output format

### **New Features**
- ✅ Hardware-specific naming
- ✅ Better documentation
- ✅ Cleaner code structure
- ✅ Improved maintainability

## **Conclusion**

This refactoring represents a significant improvement in code organization and maintainability while preserving all existing functionality. The new structure provides:

1. **Clear hardware dependencies** in filenames
2. **Better separation of concerns** with one experiment per file
3. **Improved maintainability** and easier debugging
4. **Consistent architecture** with other refactored modules
5. **Future-proof design** for additional hardware platforms

The migration is straightforward and backward-compatible, making it easy for existing users to adopt the new structure while maintaining their current workflows. 