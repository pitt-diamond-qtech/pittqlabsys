"""
Test ctypes import updates in Controller files

This module tests that the explicit ctypes imports work correctly
and don't break functionality in the Controller files.
"""

import pytest
import platform
from pathlib import Path


def test_nanodrive_ctypes_imports():
    """Test that nanodrive.py uses explicit ctypes imports correctly"""
    # Test that the file can be imported without errors
    from src.Controller.nanodrive import MCLNanoDrive
    
    # Test that the file uses explicit imports
    nanodrive_file = Path('src/Controller/nanodrive.py')
    assert nanodrive_file.exists(), "nanodrive.py not found"
    
    content = nanodrive_file.read_text()
    
    # Check for explicit ctypes imports
    assert 'from ctypes import (' in content, "explicit ctypes imports not found"
    
    # Check that wildcard import is removed
    assert 'from ctypes import *' not in content, "wildcard ctypes import still present"
    
    # Check for specific ctypes types being used
    required_types = ['c_int', 'c_double', 'c_uint', 'byref']
    for ctype in required_types:
        assert ctype in content, f"{ctype} usage not found"
    
    # Check for cross-platform windll handling
    assert 'platform.system()' in content, "cross-platform windll handling not found"
    assert 'cdll as windll' in content, "cross-platform windll handling not found"


def test_pulse_blaster_ctypes_imports():
    """Test that pulse_blaster.py uses explicit ctypes imports correctly"""
    # Test that the file can be imported without errors
    from src.Controller.pulse_blaster import PulseBlaster
    
    # Test that the file uses explicit imports
    pulse_blaster_file = Path('src/Controller/pulse_blaster.py')
    assert pulse_blaster_file.exists(), "pulse_blaster.py not found"
    
    content = pulse_blaster_file.read_text()
    
    # Check for explicit ctypes imports
    assert 'from ctypes import cdll, c_char_p, c_double, c_uint, c_int' in content, "explicit ctypes imports not found"
    
    # Check that wildcard import is removed
    assert 'from ctypes import *' not in content, "wildcard ctypes import still present"
    
    # Check for specific ctypes types being used
    required_types = ['cdll', 'c_char_p', 'c_double', 'c_uint', 'c_int']
    for ctype in required_types:
        assert ctype in content, f"{ctype} usage not found"


def test_spincore_driver_imports():
    """Test that spincore_driver.py doesn't have ctypes issues"""
    # Test that the file can be imported without errors
    try:
        from src.Controller.spincore_driver import SpinCoreDriver, SpinCoreDevice
    except (OSError, ImportError) as e:
        # Hardware-related errors are expected on non-Windows systems
        if "hardware" in str(e).lower() or "device" in str(e).lower() or "DAQ" in str(e).upper():
            pytest.skip(f"Hardware not available: {e}")
        else:
            raise
    
    # Test that the file doesn't use wildcard imports
    spincore_file = Path('src/Controller/spincore_driver.py')
    assert spincore_file.exists(), "spincore_driver.py not found"
    
    content = spincore_file.read_text()
    
    # Check that no wildcard imports are used
    assert 'from ctypes import *' not in content, "wildcard ctypes import found"


def test_ctypes_functionality():
    """Test that ctypes functionality still works"""
    # Test basic ctypes functionality
    from ctypes import c_int, c_double, c_uint, byref
    
    # Test creating ctypes objects
    test_int = c_int(42)
    test_double = c_double(3.14)
    test_uint = c_uint(100)
    
    assert test_int.value == 42
    assert test_double.value == 3.14
    assert test_uint.value == 100
    
    # Test byref functionality
    ref_int = byref(test_int)
    assert ref_int is not None
    
    # Test windll/cdll availability (cross-platform)
    if platform.system() == 'Windows':
        from ctypes import windll
        assert windll is not None
    else:
        from ctypes import cdll
        assert cdll is not None


def test_controller_import_stability():
    """Test that all Controller files can be imported without errors"""
    controller_files = [
        'src.Controller.nanodrive',
        'src.Controller.pulse_blaster', 
        'src.Controller.spincore_driver',
        'src.Controller.adwin',
        'src.Controller.microwave_generator',
        'src.Controller.ni_daq',
        'src.Controller.usb_rf_generator',
        'src.Controller.example_device',
        'src.Controller.awg520'
    ]
    
    failed_imports = []
    
    for module_name in controller_files:
        try:
            __import__(module_name)
        except ImportError as e:
            failed_imports.append(f"{module_name}: {e}")
        except Exception as e:
            # Don't count hardware-related errors as failures
            if "hardware" not in str(e).lower() and "device" not in str(e).lower():
                failed_imports.append(f"{module_name}: {e}")
    
    if failed_imports:
        pytest.fail(f"Import failures: {failed_imports}")


def test_no_wildcard_ctypes_imports():
    """Test that no Controller files use wildcard ctypes imports"""
    controller_dir = Path('src/Controller')
    assert controller_dir.exists(), "Controller directory not found"
    
    python_files = list(controller_dir.glob('*.py'))
    assert python_files, "No Python files found in Controller directory"
    
    files_with_wildcard_imports = []
    
    for py_file in python_files:
        content = py_file.read_text()
        # Check each line to ignore commented imports
        lines = content.split('\n')
        for line in lines:
            stripped_line = line.strip()
            if stripped_line.startswith('from ctypes import *') and not stripped_line.startswith('#'):
                files_with_wildcard_imports.append(py_file.name)
                break
    
    if files_with_wildcard_imports:
        pytest.fail(f"Files with wildcard ctypes imports: {files_with_wildcard_imports}") 