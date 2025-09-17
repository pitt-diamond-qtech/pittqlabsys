# ExperimentIterator Guide: Multi-Variable Scans

## Overview

The `ExperimentIterator` class provides a powerful framework for creating complex multi-variable scans and experiment sequences. It works as a **factory class** that dynamically creates experiment iterator classes at runtime, enabling sophisticated experimental workflows without writing new code.

## 🎯 **Key Concepts**

### **Factory Pattern**
- `ExperimentIterator` is **not directly inherited** by experiments
- Instead, it **creates new classes** at runtime based on configuration
- Each configuration generates a unique, specialized iterator class

### **Multi-Level Support**
- Supports **nested iterators** (iterators within iterators)
- Enables **multi-dimensional parameter sweeps**
- Handles **complex execution sequences** with data inheritance

### **Data Organization**
- Automatically organizes data by scan parameters
- Supports **data inheritance** between experiments
- Provides **progress tracking** through all dimensions

## 🚀 **Two Approaches to Multi-Variable Scans**

### **Option 1: GUI-Based Creation (Recommended for Users)**

The easiest way to create multi-variable scans is through the AQuISS GUI interface.

#### **Step-by-Step GUI Process**

1. **Load Experiments**
   - Open AQuISS and go to "Load" tab
   - Load the experiments you want to iterate over
   - Ensure experiments have the parameters you want to sweep

2. **Create Experiment Sequence**
   - Go to "Experiment Sequence" tab
   - Drag experiments from left panel to right panel
   - Set the execution order (1, 2, 3, etc.)

3. **Configure Iterator Type**
   - Choose "Parameter Sweep" from dropdown
   - Select the parameter to sweep (e.g., `odmr_pulsed.microwave.frequency`)
   - Set sweep range (min, max, steps)

4. **Create Nested Scans**
   - For multi-dimensional scans, create **multiple sequences**
   - First sequence: sweep inner parameter (e.g., pulse duration)
   - Second sequence: sweep outer parameter (e.g., frequency)
   - Include the first sequence as a sub-experiment in the second

5. **Run the Scan**
   - Save the configuration
   - Run the experiment sequence
   - Monitor progress through all dimensions

#### **GUI Example: 2D ODMR Scan**

```
Sequence 1: "Pulse Duration Sweep"
├── Experiment: ODMR Pulsed
├── Sweep Parameter: sequence.pulse_duration
├── Range: 100ns to 1000ns, 10 steps
└── Execution Order: 1

Sequence 2: "Frequency Sweep" 
├── Sub-experiment: Pulse Duration Sweep
├── Experiment: Data Collection
├── Sweep Parameter: pulse_duration_sweep.microwave.frequency
├── Range: 2.8GHz to 2.9GHz, 20 steps
└── Execution Order: 1, 2
```

**Result**: 10 × 20 = 200 total scan points

### **Option 2: Programmatic Creation (For Developers)**

Advanced users can create multi-variable scans programmatically using Python code.

#### **Programmatic Example: 2D ODMR Scan**

```python
from src.core.experiment_iterator import ExperimentIterator
from src.Model.experiments.odmr_pulsed import ODMRPulsedExperiment

# Step 1: Define inner iterator (pulse duration sweep)
inner_config = {
    'name': 'Pulse_Duration_Sweep',
    'class': 'ExperimentIterator',
    'package': 'src.Model',
    'experiments': {'odmr_pulsed': ODMRPulsedExperiment},
    'settings': {
        'experiment_order': {'odmr_pulsed': 1},
        'experiment_execution_freq': {'odmr_pulsed': 1},
        'iterator_type': 'Parameter Sweep',
        'sweep_param': 'odmr_pulsed.sequence.pulse_duration',
        'sweep_range': {
            'min_value': 100e-9,    # 100ns
            'max_value': 1000e-9,   # 1000ns
            'N/value_step': 10,     # 10 steps
            'randomize': False
        },
        'stepping_mode': 'N'
    }
}

# Step 2: Create inner iterator class
inner_iterator_info, _ = ExperimentIterator.create_dynamic_experiment_class(
    inner_config
)

# Step 3: Define outer iterator (frequency sweep)
outer_config = {
    'name': 'Frequency_Pulse_2D_Scan',
    'class': 'ExperimentIterator',
    'package': 'src.Model',
    'experiments': {
        'pulse_duration_sweep': inner_iterator_info['class'],
        'data_collection': DataCollectionExperiment
    },
    'settings': {
        'experiment_order': {
            'pulse_duration_sweep': 1,
            'data_collection': 2
        },
        'experiment_execution_freq': {
            'pulse_duration_sweep': 1,
            'data_collection': 1
        },
        'iterator_type': 'Parameter Sweep',
        'sweep_param': 'pulse_duration_sweep.microwave.frequency',
        'sweep_range': {
            'min_value': 2.8e9,     # 2.8 GHz
            'max_value': 2.9e9,     # 2.9 GHz
            'N/value_step': 20,     # 20 steps
            'randomize': False
        },
        'stepping_mode': 'N'
    }
}

# Step 4: Create and run the experiment
outer_iterator_info, _ = ExperimentIterator.create_dynamic_experiment_class(
    outer_config
)
```

## ⚙️ **Configuration Parameters**

### **Core Iterator Settings**

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `iterator_type` | str | Type of iteration: 'Parameter Sweep' or 'Loop' | `'Parameter Sweep'` |
| `experiment_order` | dict | Execution order of sub-experiments | `{'exp1': 1, 'exp2': 2}` |
| `experiment_execution_freq` | dict | How often each experiment runs | `{'exp1': 1, 'exp2': 2}` |

### **Parameter Sweep Settings**

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `sweep_param` | str | Parameter path to sweep | `'odmr_pulsed.microwave.frequency'` |
| `sweep_range.min_value` | float | Minimum parameter value | `2.8e9` |
| `sweep_range.max_value` | float | Maximum parameter value | `2.9e9` |
| `sweep_range.N/value_step` | int | Number of steps or step size | `50` |
| `sweep_range.randomize` | bool | Randomize sweep order | `False` |
| `stepping_mode` | str | 'N' for steps, 'value_step' for step size | `'N'` |

### **Loop Settings**

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `num_loops` | int | Number of times to repeat sequence | `100` |
| `run_all_first` | bool | Run all experiments in first pass | `True` |

## 🔄 **Execution Flow**

### **Parameter Sweep Flow**

1. **Initialize**: Load experiments and set initial parameters
2. **Sweep Loop**: For each parameter value:
   - Update the target parameter
   - Execute experiments in order
   - Collect data and store with parameter value
   - Pass data to next iteration if inheritance enabled
3. **Complete**: Organize all data by sweep parameters

### **Loop Flow**

1. **Initialize**: Set up experiment sequence
2. **Loop**: For each iteration:
   - Execute experiments in order
   - Collect data
   - Accumulate for averaging
3. **Average**: Calculate average of all iterations

## 📊 **Data Organization**

### **Sweep Iterator Data Structure**

```python
{
    'sweep_1_frequency_2.800e+09': [
        experiment_data,           # Data from experiment
        experiment_settings,       # Settings used
        {
            'scan_parameter_iterator_1': 'frequency',
            'scan_current_value_iterator_1': 2.8e9,
            'scan_all_values_iterator_1': [2.8e9, 2.9e9, ...]
        }
    ],
    'sweep_1_frequency_2.900e+09': [
        # ... next iteration
    ]
}
```

### **Loop Iterator Data Structure**

```python
{
    'data_key_1': averaged_data,      # Average of all iterations
    'data_key_2': averaged_data,      # Average of all iterations
    # ... other averaged data
}
```

## 🎨 **Advanced Features**

### **Data Inheritance**

Enable data inheritance between experiments:

```python
'settings': {
    'inherit_data': True,  # Inherit data from previous experiment
    # ... other settings
}
```

**Use Case**: Pass NV locations from `SelectPoints` to `ODMR` experiments.

### **Execution Frequency Control**

Control how often each experiment runs:

```python
'experiment_execution_freq': {
    'select_points': 1,      # Run every iteration
    'odmr_scan': 5,          # Run every 5th iteration
    'data_save': 10          # Run every 10th iteration
}
```

### **Randomized Sweeps**

Randomize parameter order for better statistics:

```python
'sweep_range': {
    'randomize': True,        # Randomize sweep order
    # ... other settings
}
```

## 🐛 **Troubleshooting**

### **Common Issues**

1. **Parameter Not Found**
   - Ensure parameter path is correct: `experiment.param.subparam`
   - Check that experiment has the specified parameter

2. **Memory Issues**
   - Reduce number of sweep steps
   - Use execution frequency to run experiments less often

3. **Progress Not Updating**
   - Check that experiments emit progress signals
   - Verify `_current_subexperiment_stage` is initialized

### **Debug Tips**

1. **Enable Verbose Mode**
   ```python
   ExperimentIterator.create_dynamic_experiment_class(
       config, verbose=True
   )
   ```

2. **Check Data Structure**
   ```python
   print(experiment._current_subexperiment_stage)
   print(experiment.iterator_type)
   print(experiment.settings)
   ```

3. **Monitor Progress**
   - Watch progress bar in GUI
   - Check console output for iteration progress

## 🚀 **Best Practices**

### **Design Principles**

1. **Single Responsibility**: Each experiment should do one thing well
2. **Data Flow**: Plan how data flows between experiments
3. **Memory Management**: Consider memory usage for large scans
4. **Error Handling**: Ensure experiments handle errors gracefully

### **Performance Tips**

1. **Efficient Experiments**: Optimize individual experiment performance
2. **Smart Frequency**: Use execution frequency to reduce unnecessary runs
3. **Data Inheritance**: Reuse data when possible instead of regenerating
4. **Progress Updates**: Emit progress signals for better user experience

### **Maintenance**

1. **Documentation**: Document complex iterator configurations
2. **Testing**: Test iterator configurations with small parameter ranges first
3. **Version Control**: Save iterator configurations in version control
4. **Backup**: Keep backups of important iterator configurations

## 📚 **Examples Repository**

See `examples/experiment_iterators/` for working examples of:
- Basic parameter sweeps
- Multi-dimensional scans
- Loop iterations
- Data inheritance patterns
- Complex experimental workflows

## 🔗 **Related Documentation**

- [Experiment Development Guide](EXPERIMENT_DEVELOPMENT.md)
- [Parameter Class Analysis](PARAMETER_CLASS_ANALYSIS.md)
- [Hardware Connection System](HARDWARE_CONNECTION_SYSTEM.md)
- [AWG520 Testing Guide](AWG520_ADWIN_TESTING.md)
