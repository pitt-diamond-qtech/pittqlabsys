# ADwin Hardware Tests

This document explains how to use the ADwin hardware integration tests that can run with either mock or real hardware.

## Overview

The `tests/test_adwin_hardware.py` file provides comprehensive tests for ADwin functionality that can operate in two modes:

1. **Mock Mode (Default)** - Uses mocked ADwin hardware for testing without physical hardware
2. **Real Hardware Mode** - Uses actual ADwin hardware when available

## Usage Options

### 1. Run with Mock Hardware (Default)

```bash
# Run all tests with mock hardware
pytest tests/test_adwin_hardware.py -v

# Run specific test with mock
pytest tests/test_adwin_hardware.py::test_adwin_connection -v
```

### 2. Run with Real Hardware

```bash
# Set environment variable to use real hardware
RUN_HARDWARE_TESTS=1 pytest tests/test_adwin_hardware.py -v

# Or export the variable first
export RUN_HARDWARE_TESTS=1
pytest tests/test_adwin_hardware.py -v
```

### 3. Skip Hardware Tests

```bash
# Skip all hardware tests (useful for CI/CD)
pytest tests/test_adwin_hardware.py -m "not hardware" -v
```

### 4. Run Only Hardware Tests

```bash
# Run only hardware tests
pytest tests/test_adwin_hardware.py -m hardware -v
```

### 5. Direct Script Execution

```bash
# Run with mock (default)
python tests/test_adwin_hardware.py

# Run with real hardware
python tests/test_adwin_hardware.py --real-hardware
```

## Available Tests

The test suite includes the following tests:

- **`test_adwin_connection`** - Tests basic connection and functionality
- **`test_adwin_process_loading`** - Tests loading binary files into ADwin processes
- **`test_adwin_process_control`** - Tests starting and stopping processes
- **`test_adwin_variable_operations`** - Tests setting and reading integer/float variables
- **`test_adwin_array_operations`** - Tests reading arrays and strings from ADwin
- **`test_adwin_helpers_integration`** - Tests integration with `adwin_helpers.py` module
- **`test_adwin_error_handling`** - Tests error handling for invalid operations
- **`test_adwin_cleanup`** - Tests proper resource cleanup

## Configuration

### Environment Variables

- `RUN_HARDWARE_TESTS` - Set to `'1'` to enable hardware tests, unset to disable (default)

### Mock Configuration

When using mock hardware, the tests provide realistic mock responses for:
- Process control methods (`Load_Process`, `Start_Process`, `Stop_Process`, etc.)
- Variable operations (`Set_Par`, `Get_Par`, `Set_FPar`, `Get_FPar`, etc.)
- Array operations (`GetData_Long`, `GetData_Float`, `GetData_String`, etc.)
- FIFO operations (`GetFifo_Long`, `Fifo_Empty`, etc.)
- Error handling and status methods

## Hardware Requirements

To run tests with real hardware, you need:

1. **ADwin Gold II** hardware connected to the system
2. **ADwin drivers** installed and properly configured
3. **Binary files** available in the expected locations (see `adwin_helpers.py`)

## Integration with CI/CD

For continuous integration, you can:

```bash
# Run only mock tests (no hardware required)
pytest tests/test_adwin_hardware.py -m "not hardware" --tb=short

# Or skip the entire file if hardware tests are not needed
pytest --ignore=tests/test_adwin_hardware.py
```

## Troubleshooting

### Mock Tests Failing

- Ensure all required mock methods are properly configured
- Check that mock return values match expected test assertions
- Verify that the `RUN_HARDWARE_TESTS` environment variable is not set to `'1'`

### Real Hardware Tests Skipped

- Check that ADwin hardware is properly connected
- Verify that ADwin drivers are installed and accessible
- Ensure the `RUN_HARDWARE_TESTS` environment variable is set to `'1'`

### Import Errors

- Make sure the virtual environment is activated
- Verify that all required dependencies are installed
- Check that the project structure is correct

## Comparison with SG384 Tests

This approach follows the same pattern as the SG384 hardware tests (`tests/test_sg384_hardware.py`):

- Both use the `RUN_HARDWARE_TESTS` environment variable to control hardware vs mock mode
- Both provide comprehensive mock fixtures
- Both support pytest markers for selective test execution
- Both include proper cleanup and error handling

## Example Workflow

```bash
# 1. Development with mock (no hardware needed)
pytest tests/test_adwin_hardware.py -v

# 2. Test with real hardware when available
RUN_HARDWARE_TESTS=1 pytest tests/test_adwin_hardware.py -v

# 3. Run specific test with real hardware
RUN_HARDWARE_TESTS=1 pytest tests/test_adwin_hardware.py::test_adwin_process_control -v

# 4. CI/CD pipeline (mock only)
pytest tests/test_adwin_hardware.py -m "not hardware" --tb=short
```

This flexible approach allows developers to work effectively both with and without physical hardware, while maintaining comprehensive test coverage. 