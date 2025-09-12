# Experiment Iterator Examples

This directory contains practical examples demonstrating how to use the `ExperimentIterator` class for creating complex multi-variable scans and experiment sequences.

## 🎯 **What These Examples Show**

The examples demonstrate how to use `ExperimentIterator` as a **factory class** to create sophisticated experimental workflows without writing new experiment classes.

## 📁 **Available Examples**

### **1. Multi-Variable ODMR Scan** (`multi_variable_odmr_scan.py`)

**Purpose**: Demonstrates creating a 2D parameter sweep using nested iterators.

**What it does**:
- **Inner loop**: Sweeps pulse duration (100ns → 1000ns, 10 steps)
- **Outer loop**: Sweeps microwave frequency (2.8GHz → 2.9GHz, 20 steps)
- **Total scan points**: 200 combinations
- **Data organization**: Automatically organized by both sweep parameters

**Key features**:
- Dynamic class creation at runtime
- Nested iterator support
- Automatic data organization
- Progress tracking through all dimensions

## 🚀 **How to Run the Examples**

### **Prerequisites**
1. **Python environment** with required packages
2. **Project dependencies** installed
3. **Experiments loaded** (e.g., `ODMRPulsedExperiment`)

### **Running the Multi-Variable ODMR Scan**

```bash
cd examples/experiment_iterators
python multi_variable_odmr_scan.py
```

**Expected Output**:
```
🧪 Multi-Variable ODMR Scan Example
==================================================
🔧 Creating inner iterator (pulse duration sweep)...
✅ Inner iterator created: src.Model.dynamic_experiment_iterator0
🔧 Creating outer iterator (frequency sweep)...
✅ Outer iterator created: src.Model.dynamic_experiment_iterator1
🔧 Creating experiment instance...
✅ Experiment instance created: <experiment_instance>
🚀 Running multi-variable scan...
🔍 DRY RUN MODE - Simulating scan configuration...

📊 Scan Configuration Summary:
==================================================
🔹 Inner Loop (Pulse Duration):
   Parameter: odmr_pulsed.sequence.pulse_duration
   Range: 100ns to 1000ns
   Steps: 10

🔹 Outer Loop (Microwave Frequency):
   Parameter: pulse_duration_sweep.microwave.frequency
   Range: 2.8GHz to 2.9GHz
   Steps: 20

🔹 Total Scan Points: 200
🔹 Estimated Time: 400 seconds (assuming 2s per point)

🎉 Multi-variable scan setup completed successfully!
💡 To run the actual scan, call: scan_system.run_scan(dry_run=False)
```

## 🔧 **Understanding the Code**

### **Key Components**

1. **Inner Iterator Creation**
   ```python
   inner_config = {
       'name': 'Pulse_Duration_Sweep',
       'class': 'ExperimentIterator',
       'experiments': {'odmr_pulsed': ODMRPulsedExperiment},
       'settings': {
           'iterator_type': 'Parameter Sweep',
           'sweep_param': 'odmr_pulsed.sequence.pulse_duration',
           'sweep_range': {...}
       }
   }
   ```

2. **Dynamic Class Creation**
   ```python
   inner_iterator_info, _ = ExperimentIterator.create_dynamic_experiment_class(
       inner_config, verbose=True
   )
   ```

3. **Nested Iterator Configuration**
   ```python
   outer_config = {
       'experiments': {
           'pulse_duration_sweep': inner_iterator_info['class'],  # Use inner iterator
           # ... other experiments
       }
   }
   ```

### **How It Works**

1. **Factory Pattern**: `ExperimentIterator.create_dynamic_experiment_class()` creates new classes at runtime
2. **Nested Structure**: Outer iterator includes inner iterator as a sub-experiment
3. **Parameter Sweeping**: Each level sweeps different parameters
4. **Data Organization**: Data is automatically organized by all sweep parameters

## 🎨 **Customizing the Examples**

### **Modifying Scan Parameters**

To change the scan ranges or steps:

```python
# Modify inner loop (pulse duration)
'sweep_range': {
    'min_value': 50e-9,     # 50ns instead of 100ns
    'max_value': 500e-9,    # 500ns instead of 1000ns
    'N/value_step': 20,     # 20 steps instead of 10
}

# Modify outer loop (frequency)
'sweep_range': {
    'min_value': 2.7e9,     # 2.7GHz instead of 2.8GHz
    'max_value': 3.0e9,     # 3.0GHz instead of 2.9GHz
    'N/value_step': 30,     # 30 steps instead of 20
}
```

### **Adding More Experiments**

To include additional experiments in the sequence:

```python
'experiments': {
    'pulse_duration_sweep': inner_iterator_info['class'],
    'data_collection': DataCollectionExperiment,
    'analysis': DataAnalysisExperiment
},
'settings': {
    'experiment_order': {
        'pulse_duration_sweep': 1,
        'data_collection': 2,
        'analysis': 3
    },
    'experiment_execution_freq': {
        'pulse_duration_sweep': 1,
        'data_collection': 1,
        'analysis': 1
    }
}
```

### **Changing Iterator Types**

To switch between parameter sweep and loop modes:

```python
# For parameter sweep
'iterator_type': 'Parameter Sweep',
'sweep_param': 'experiment.parameter.path',
'sweep_range': {...}

# For loop iteration
'iterator_type': 'Loop',
'num_loops': 100
```

## 🔍 **Debugging and Troubleshooting**

### **Enable Verbose Mode**

```python
ExperimentIterator.create_dynamic_experiment_class(
    config, verbose=True  # Shows detailed creation process
)
```

### **Check Configuration**

```python
# Print the created iterator info
print(f"Inner iterator: {inner_iterator_info}")
print(f"Outer iterator: {outer_iterator_info}")

# Check experiment instance
print(f"Experiment: {scan_system.experiment_instance}")
print(f"Settings: {scan_system.experiment_instance.settings}")
```

### **Common Issues**

1. **Parameter Not Found**
   - Ensure parameter path is correct: `experiment.param.subparam`
   - Check that experiment has the specified parameter

2. **Import Errors**
   - Verify experiment classes are properly imported
   - Check module paths and dependencies

3. **Configuration Errors**
   - Validate all required settings are present
   - Check parameter types and ranges

## 🚀 **Next Steps**

After running the examples:

1. **Modify parameters** to match your experimental needs
2. **Add more experiments** to the sequence
3. **Create custom iterator configurations** for your specific use case
4. **Integrate with GUI** using the same configuration structure

## 📚 **Related Documentation**

- [ExperimentIterator Guide](../docs/EXPERIMENT_ITERATOR_GUIDE.md) - Comprehensive guide
- [Experiment Development Guide](../docs/EXPERIMENT_DEVELOPMENT.md) - Creating new experiments
- [Parameter Class Analysis](../docs/PARAMETER_CLASS_ANALYSIS.md) - Understanding parameters

## 🤝 **Contributing**

To add new examples:

1. **Create a new Python file** with descriptive name
2. **Include comprehensive comments** explaining the code
3. **Add to this README** with description and usage instructions
4. **Test thoroughly** before committing

## 💡 **Tips for Success**

1. **Start simple** - Begin with single-parameter sweeps
2. **Test configurations** - Use dry-run mode to verify setup
3. **Monitor progress** - Watch console output for debugging
4. **Document configurations** - Save working configurations for reuse
5. **Plan data flow** - Consider how data will be organized and inherited
