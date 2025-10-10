# Next Steps for Dutt-Features Branch

## 🎯 **Immediate Next Steps** (This Weekend/Next Week)

### 1. **Device Actual Value Reporting** (HIGH PRIORITY - After Weekend)
**Why**: Critical for precision devices like nanodrives where actual position differs from requested
**Effort**: Medium
**Impact**: High

**Problem**: Current system only shows green "success" even when device reports different actual value
**Example**: User requests 50.0 μm, device moves to 49.5 μm → Currently shows green (misleading!)

**Tasks**:
- [ ] Add `'device_different'` visual state (yellow background?)
- [ ] Implement device tolerance system to avoid flagging tiny differences
- [ ] Add actual value checking after validation passes
- [ ] Call `device.update_and_get()` to get real device values
- [ ] Show both requested and actual values in GUI history
- [ ] Update feedback messages to be honest about what happened

**Files to Modify**:
- `src/View/windows_and_widgets/widgets.py` (NumberClampDelegate)
- `src/core/device.py` (base device class)
- Device implementations (add tolerance methods)

### 2. **Enhanced GUI Input Formatting** (High Priority)
**Why**: Most user-friendly improvement, builds on current validation system
**Effort**: Medium
**Impact**: High

**Tasks**:
- [ ] Enhance `_parse_number()` function in `widgets.py` to support units
- [ ] Add unit conversion utilities (GHz ↔ Hz, ns ↔ s, etc.)
- [ ] Update GUI to show parameter values in user-friendly units
- [ ] Add unit hints/labels in parameter display
- [ ] Test with various input formats (3.87 GHz, 500 ns, etc.)

**Files to Modify**:
- `src/View/windows_and_widgets/widgets.py` (NumberClampDelegate)
- `src/core/parameter.py` (if needed for unit handling)
- `src/View/windows_and_widgets/main_window.py` (display formatting)

### 2. **Dataset Tab Investigation** (Medium Priority)
**Why**: Team members need this functionality
**Effort**: Low-Medium (investigation first)
**Impact**: Medium

**Tasks**:
- [ ] Investigate existing dataset tab implementation
- [ ] Identify why datasets aren't loading
- [ ] Restore basic dataset loading functionality
- [ ] Add simple data display capabilities

**Files to Investigate**:
- `src/View/windows_and_widgets/main_window.py` (dataset tab)
- Look for existing dataset loading code
- Check for any dataset-related classes or methods

### 3. **Parameter Tolerance System** (Lower Priority)
**Why**: Improves validation accuracy
**Effort**: Medium
**Impact**: Medium

**Tasks**:
- [ ] Design tolerance configuration system
- [ ] Implement device-specific tolerance handling
- [ ] Update validation logic to use tolerances
- [ ] Add tolerance configuration to device JSON files

## 🔍 **Investigation Tasks**

### **Dataset Tab Mystery**
- Search codebase for "dataset" references
- Check GUI layout files for dataset tab
- Look for any dataset loading/display methods
- Check if there are any dataset-related classes

### **Unit Parsing Research**
- Research best practices for scientific unit parsing
- Look at existing scientific Python libraries
- Consider edge cases (compound units, prefixes)

## 📋 **Weekend Brainstorming Ideas**

Feel free to add any new ideas that come up:

- [ ] **Experiment Templates**: Pre-built experiment configurations
- [ ] **Real-time Collaboration**: Multiple users on same experiment
- [ ] **Advanced Visualization**: 3D plotting, interactive graphs
- [ ] **Plugin System**: Extensible architecture
- [ ] **Cloud Integration**: Remote experiment execution
- [ ] **Auto-save**: Prevent data loss during experiments
- [ ] **Experiment Scheduling**: Queue experiments for later execution
- [ ] **Data Export**: Multiple export formats (CSV, HDF5, etc.)

## 🎨 **GUI Polish Ideas**

- [ ] **Dark Mode**: Alternative color scheme
- [ ] **Keyboard Shortcuts**: Power user features
- [ ] **Drag & Drop**: Experiment composition
- [ ] **Search**: Find parameters/experiments quickly
- [ ] **Favorites**: Bookmark frequently used settings
- [ ] **Recent**: Quick access to recent experiments

---

**Remember**: Start with the most user-friendly improvements first! The enhanced input formatting will have immediate impact on daily usage.

**Next Session**: Focus on unit parsing and input formatting improvements.
