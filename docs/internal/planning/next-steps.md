# Next Steps for Dutt-Features Branch

## 🎯 **Immediate Next Steps** (This Weekend/Next Week)

### 1. **Device Parameter Tolerance and Validation System** (HIGH PRIORITY - After Weekend)
**Why**: Critical for precision devices like nanodrives where actual position differs from requested. Provides honest feedback about device behavior and ensures parameters are within acceptable tolerances.
**Effort**: Medium-High
**Impact**: High

**Problem**: Current system only shows green "success" even when device reports different actual value. No tolerance checking or honest reporting of device behavior.

**Core Tasks**:

#### **Phase 1: Configuration System**
- [ ] Design and implement `tolerance_settings` structure in main device JSON configs
- [ ] Add tolerance configuration to existing device configs (sg384, awg520, nanodrive, etc.)
- [ ] Create tolerance configuration validation and loading system
- [ ] Implement inline tolerance settings approach (Phase 1)
- [ ] Design extensible architecture for future modular file support (Phase 2)

#### **Phase 2: Base Framework**
- [ ] Extend `Parameter` class with tolerance support (`tolerance_percent`, `tolerance_absolute`, `validation_enabled`)
- [ ] Add `validate_parameter_tolerance()` method to base `Device` class
- [ ] Add `check_all_parameters_tolerance()` method to base `Device` class
- [ ] Implement tolerance comparison logic (percentage and absolute)

#### **Phase 3: Device Integration**
- [ ] Update device classes to load tolerance settings from config
- [ ] Implement device-specific tolerance validation methods
- [ ] Add actual value checking using `device.update_and_get()`
- [ ] Test with precision devices (nanodrive, sg384)

#### **Phase 4: GUI Integration**
- [ ] Add `'device_different'` visual state (yellow background) to NumberClampDelegate
- [ ] Update feedback messages to show requested vs actual values
- [ ] Add tolerance information to GUI history
- [ ] Implement warning thresholds for near-tolerance values

**Files to Modify**:
- `src/core/device.py` (base device class - tolerance methods)
- `src/core/parameter.py` (tolerance support)
- `src/View/windows_and_widgets/widgets.py` (NumberClampDelegate - visual states)
- `config.sample.json` and `src/config.template.json` (tolerance settings)
- Device implementations (sg384.py, nanodrive.py, awg520.py, etc.)

**Configuration Example (Phase 1 - Main Config)**:
```json
{
    "devices": {
        "sg384": {
            "class": "SG384Generator",
            "filepath": "src/Controller/sg384.py",
            "settings": { /* existing settings */ },
            "tolerance_settings": {
                "frequency": {
                    "tolerance_percent": 0.1,
                    "tolerance_absolute": 1000,
                    "validation_enabled": true,
                    "warning_threshold": 0.05
                }
            }
        }
    }
}
```

**Future Enhancement (Phase 2 - Modular Files)**:
```json
{
    "devices": {
        "sg384": {
            "tolerance_settings_file": "device_tolerances/sg384_tolerance.json"
        }
    }
}
```

**Configuration Strategy**:
- **Phase 1**: Inline tolerance settings in main config.json (recommended for initial implementation)
- **Phase 2**: Support for external device-specific tolerance files (future enhancement)

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
