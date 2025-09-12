# Project Root Detection in Python

This document explains the robust project root detection system implemented in AQuISS to solve the common Python path resolution problem.

## The Problem

Python's `__file__` variable always refers to the location of the current file, not the calling script. This causes issues when:

- Running scripts from different directories
- Importing modules from various locations
- Writing tests and examples
- Deploying to different environments

## The Solution

We've implemented multiple strategies in `src/core/helper_functions.py`:

### 1. `get_project_root()` - Comprehensive Detection

```python
from src.core.helper_functions import get_project_root

project_root = get_project_root()
```

**Strategies used (in order):**
1. **Project markers**: Looks for `setup.py`, `pyproject.toml`, `.git`, `src`, `requirements.txt`
2. **Calling script location**: Walks up from the script that called the function
3. **Current working directory**: Walks up from `os.getcwd()`
4. **Fallback**: Uses the helper_functions.py location

### 2. `get_project_root_simple()` - Lightweight Detection

```python
from src.core.helper_functions import get_project_root_simple

project_root = get_project_root_simple()
```

**Strategy:** Simply walks up from current working directory until it finds a `src` folder.

### 3. `find_project_root_from_file()` - File-Based Detection

```python
from src.core.helper_functions import find_project_root_from_file

project_root = find_project_root_from_file(__file__)
```

**Strategy:** Walks up from a specific file path until it finds project markers.

## Usage Examples

### In Scripts

```python
#!/usr/bin/env python3
"""Any script in the project"""

import sys
from pathlib import Path

# Add project root to Python path
from src.core.helper_functions import get_project_root
project_root = get_project_root()
sys.path.insert(0, str(project_root))

# Now you can import anything
from src.Model.experiments.odmr_pulsed import ODMRPulsedExperiment
```

### In Tests

```python
"""tests/test_something.py"""

import sys
from pathlib import Path

# Ensure project root is in path
from src.core.helper_functions import get_project_root
project_root = get_project_root()
sys.path.insert(0, str(project_root))

# Import and test
from src.Model.experiments.odmr_pulsed import ODMRPulsedExperiment
```

### In Examples

```python
"""examples/some_example.py"""

import sys
from pathlib import Path

# Add project root to path
from src.core.helper_functions import get_project_root
project_root = get_project_root()
sys.path.insert(0, str(project_root))

# Use project modules
from src.Controller.awg520 import AWG520Device
```

### In Module Files

```python
"""src/Model/experiments/odmr_pulsed.py"""

from pathlib import Path
from src.core.helper_functions import get_project_root

# Get project root for relative paths
project_root = get_project_root()
config_path = project_root / "src" / "config.json"
```

## Best Practices

### 1. Always Use Helper Functions

❌ **Don't do this:**
```python
# This will break when run from different directories
project_root = Path(__file__).parent.parent.parent
```

✅ **Do this:**
```python
from src.core.helper_functions import get_project_root
project_root = get_project_root()
```

### 2. Add Project Root to sys.path Early

❌ **Don't do this:**
```python
# This might fail if run from wrong directory
from src.Model.experiments.odmr_pulsed import ODMRPulsedExperiment
```

✅ **Do this:**
```python
import sys
from src.core.helper_functions import get_project_root
sys.path.insert(0, str(get_project_root()))

from src.Model.experiments.odmr_pulsed import ODMRPulsedExperiment
```

### 3. Use Relative Paths from Project Root

```python
from src.core.helper_functions import get_project_root

project_root = get_project_root()
config_file = project_root / "src" / "config.json"
data_folder = project_root / "data"
output_folder = project_root / "output"
```

## Common Patterns

### Pattern 1: Script Boilerplate

```python
#!/usr/bin/env python3
"""
Any script that needs to import project modules
"""

import sys
from pathlib import Path

# Add project root to Python path
from src.core.helper_functions import get_project_root
project_root = get_project_root()
sys.path.insert(0, str(project_root))

# Now import project modules
from src.Model.experiments.odmr_pulsed import ODMRPulsedExperiment
from src.Controller.awg520 import AWG520Device

def main():
    # Your code here
    pass

if __name__ == "__main__":
    main()
```

### Pattern 2: Test Boilerplate

```python
"""
Test file boilerplate
"""

import sys
import unittest
from pathlib import Path

# Add project root to Python path
from src.core.helper_functions import get_project_root
project_root = get_project_root()
sys.path.insert(0, str(project_root))

# Import modules to test
from src.Model.experiments.odmr_pulsed import ODMRPulsedExperiment

class TestODMRPulsed(unittest.TestCase):
    def test_something(self):
        # Your test code here
        pass

if __name__ == "__main__":
    unittest.main()
```

### Pattern 3: Module Internal Paths

```python
"""
Module that needs to reference other project files
"""

from pathlib import Path
from src.core.helper_functions import get_project_root

class MyModule:
    def __init__(self):
        self.project_root = get_project_root()
        self.config_path = self.project_root / "src" / "config.json"
        self.data_path = self.project_root / "data"
```

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'src'"

**Cause:** Project root not in Python path

**Solution:**
```python
import sys
from src.core.helper_functions import get_project_root
sys.path.insert(0, str(get_project_root()))
```

### Issue: "FileNotFoundError: config.json not found"

**Cause:** Using relative paths that break from different directories

**Solution:**
```python
from src.core.helper_functions import get_project_root
project_root = get_project_root()
config_path = project_root / "src" / "config.json"
```

### Issue: Tests fail when run from different directories

**Cause:** Tests not using project root detection

**Solution:**
```python
# At the top of each test file
import sys
from src.core.helper_functions import get_project_root
sys.path.insert(0, str(get_project_root()))
```

## Migration Guide

### Step 1: Update Scripts

Find all scripts that use hardcoded paths:
```bash
grep -r "Path(__file__).parent" src/ examples/ tests/
```

Replace with:
```python
from src.core.helper_functions import get_project_root
project_root = get_project_root()
```

### Step 2: Update Imports

Find all files that import without project root:
```bash
grep -r "from src\." examples/ tests/
```

Add project root detection:
```python
import sys
from src.core.helper_functions import get_project_root
sys.path.insert(0, str(get_project_root()))
```

### Step 3: Test from Different Directories

```bash
# Test from project root
python src/Model/experiments/odmr_pulsed.py

# Test from subdirectory
cd src/Model/experiments
python odmr_pulsed.py

# Test from examples
cd examples
python some_example.py
```

## Performance Considerations

- `get_project_root()`: Most robust, slight overhead for multiple strategies
- `get_project_root_simple()`: Fastest, assumes you're in project structure
- `find_project_root_from_file()`: Good for specific file-based detection

Choose based on your needs:
- **Scripts/Examples**: Use `get_project_root()`
- **Tests**: Use `get_project_root_simple()`
- **Modules**: Use `find_project_root_from_file(__file__)`

## Future Improvements

1. **Caching**: Cache project root after first detection
2. **Environment variables**: Support `AQUISS_PROJECT_ROOT` env var
3. **Configuration**: Allow custom project markers
4. **Validation**: Verify project root contains expected structure

This system should eliminate the path resolution issues that plague Python projects!
