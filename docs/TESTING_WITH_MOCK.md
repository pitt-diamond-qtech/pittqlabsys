# Testing with MagicMock and pytest Fixtures

This document explains how we use `unittest.mock.MagicMock` and pytest fixtures to test hardware communication without requiring actual hardware.

## Table of Contents

1. [What is MagicMock?](#what-is-magicmock)
2. [Creating Mock VISA Instruments](#creating-mock-visa-instruments)
3. [The patch_transports Fixture](#the-patch_transports-fixture)
4. [How It All Works Together](#how-it-all-works-together)
5. [Real vs Mock Comparison](#real-vs-mock-comparison)
6. [Benefits of This Approach](#benefits-of-this-approach)

## What is MagicMock?

`MagicMock` is a powerful tool from Python's `unittest.mock` module that creates "fake" objects for testing. It automatically creates attributes and methods when you try to access them, and it can record how it's been used.

### Key Features

- **Automatic Attribute Creation**: If you access `mock_inst.some_attribute`, it creates it automatically
- **Method Recording**: It remembers what methods were called and with what arguments
- **Flexible Behavior**: You can make it return different values, raise exceptions, or execute custom code
- **Easy Assertions**: You can check if methods were called, how many times, and with what arguments

## Creating Mock VISA Instruments

### Basic Mock Creation

```python
@pytest.fixture
def mock_visa_instrument():
    """Create a mock VISA instrument for testing"""
    mock_inst = MagicMock()
    mock_inst.written = []
    mock_inst.write = MagicMock(side_effect=lambda cmd: mock_inst.written.append(cmd))
    mock_inst.query = MagicMock(return_value="DUMMY_IDN\n")
    mock_inst.close = MagicMock()
    return mock_inst
```

### Breaking Down the Code

**1. Creating the Base Mock:**
```python
mock_inst = MagicMock()
```
- Creates a blank mock object that can pretend to be any object

**2. Adding a Real List for Recording:**
```python
mock_inst.written = []
```
- Adds a real list to store commands that would be sent to hardware

**3. Mocking the `write` Method:**
```python
mock_inst.write = MagicMock(side_effect=lambda cmd: mock_inst.written.append(cmd))
```
- `side_effect` tells the mock what to do when the method is called
- `lambda cmd: mock_inst.written.append(cmd)` is a function that takes a command and adds it to the `written` list
- When your code calls `mock_inst.write("FREQ 1GHz")`, it adds "FREQ 1GHz" to the `written` list

**4. Mocking the `query` Method:**
```python
mock_inst.query = MagicMock(return_value="DUMMY_IDN\n")
```
- `return_value` tells the mock what to return when the method is called
- When your code calls `mock_inst.query("*IDN?")`, it always returns "DUMMY_IDN\n"

**5. Mocking the `close` Method:**
```python
mock_inst.close = MagicMock()
```
- Creates a mock `close` method that does nothing when called

### Resource Manager Mock

```python
@pytest.fixture
def mock_resource_manager(mock_visa_instrument):
    """Create a mock resource manager"""
    mock_rm = MagicMock()
    mock_rm.open_resource = MagicMock(return_value=mock_visa_instrument)
    return mock_rm
```

This creates a mock resource manager that always returns our mock instrument when `open_resource()` is called.

## The patch_transports Fixture

The `patch_transports` fixture uses `monkeypatch` (a pytest feature) to temporarily replace real system functions with our mock versions during testing.

### Complete Fixture Code

```python
@pytest.fixture(autouse=True)
def patch_transports(monkeypatch, mock_resource_manager):
    """Automatically patch all transport mechanisms for testing"""
    import socket
    monkeypatch.setattr(socket, 'socket', lambda *args, **kwargs: DummySocket())
    import pyvisa
    monkeypatch.setattr(pyvisa, 'ResourceManager', lambda: mock_resource_manager)
```

### Breaking Down the Fixture

**1. `@pytest.fixture(autouse=True)`**
- `autouse=True` means this fixture runs **automatically** for every test
- You don't need to explicitly call it in your test functions
- It's like a "setup" that happens before every test

**2. `monkeypatch` Parameter**
- `monkeypatch` is a pytest fixture that lets you temporarily change Python modules and objects
- It automatically restores the original values after each test
- It's safer than manually patching because it cleans up automatically

**3. Patching Socket Communication:**
```python
monkeypatch.setattr(socket, 'socket', lambda *args, **kwargs: DummySocket())
```
- Replaces the real `socket.socket` function with a lambda that returns our `DummySocket`
- When your code calls `socket.socket()`, it gets our dummy instead
- The `lambda *args, **kwargs` means it accepts any arguments but ignores them

**4. Patching VISA Communication:**
```python
monkeypatch.setattr(pyvisa, 'ResourceManager', lambda: mock_resource_manager)
```
- Replaces the real `pyvisa.ResourceManager()` with a lambda that returns our mock
- When your code calls `pyvisa.ResourceManager()`, it gets our mock instead

### The DummySocket Class

```python
class DummySocket:
    def __init__(self, *args, **kwargs):
        self._recv_buffer = b""
        self.sent = []
    def connect(self, addr):
        pass  # Pretend to connect
    def sendall(self, data):
        self.sent.append(data)  # Record what was sent
    def recv(self, num):
        return b"DUMMY_IDN\n"  # Return fake response
    def close(self):
        pass  # Pretend to close
```

**What this simulates:**
- `connect()`: Pretends to connect to a network device
- `sendall()`: Records what data would be sent
- `recv()`: Returns fake response data
- `close()`: Pretends to close the connection

## How It All Works Together

### The Chain of Mocking

1. **Test starts** → `patch_transports` runs automatically
2. **Code tries to create socket** → Gets `DummySocket` instead
3. **Code tries to create VISA manager** → Gets our mock instead
4. **Code calls `rm.open_resource()`** → Gets our `mock_visa_instrument`
5. **Code calls `inst.write()`** → Commands get recorded in `mock_inst.written`

### Example Flow

```python
def test_sg384():
    # patch_transports has already run automatically
    
    # This would normally create a real VISA connection
    sg = SG384Generator(settings={'connection_type':'GPIB', 'visa_resource':'GPIB0::20::INSTR'})
    
    # This would normally send a real command to hardware
    sg.set_frequency(1e9)
    
    # But instead, the command gets recorded in our mock
    assert "FREQ 1000000000HZ" in sg._inst.written
```

### Why Use `autouse=True`?

**Without `autouse=True`:**
```python
def test_something(patch_transports):  # Need to explicitly request it
    # test code here
```

**With `autouse=True`:**
```python
def test_something():  # Automatically gets the fixture
    # test code here
```

## Real vs Mock Comparison

### Real Hardware Communication

```python
# This would connect to real hardware
rm = pyvisa.ResourceManager()
inst = rm.open_resource("GPIB0::20::INSTR")
inst.write("FREQ 1GHz")  # Actually sends to hardware
response = inst.query("*IDN?")  # Actually gets response from hardware
```

### Mocked Communication (Our Tests)

```python
# This gets our mocks instead
rm = pyvisa.ResourceManager()  # Returns mock_resource_manager
inst = rm.open_resource("anything")  # Returns mock_visa_instrument
inst.write("FREQ 1GHz")  # Records command in mock_inst.written
response = inst.query("*IDN?")  # Returns "DUMMY_IDN\n"
print(mock_inst.written)  # ['FREQ 1GHz']
```

### Practical Example

```python
def test_frequency_setting():
    # Create device with mock
    sg = SG384Generator(settings={'connection_type':'GPIB', 'visa_resource':'GPIB0::20::INSTR'})
    
    # Set frequency
    sg.set_frequency(1e9)
    
    # Check that the right command was sent
    assert "FREQ 1000000000HZ" in sg._inst.written
```

## Benefits of This Approach

### 1. No Hardware Required
- You can test your code without real hardware
- Tests run faster and don't require expensive equipment
- No risk of damaging hardware during testing

### 2. Predictable Behavior
- You know exactly what the mock will return
- No surprises from hardware failures or network issues
- Consistent test results across different environments

### 3. Record What Happened
- You can check what commands were sent
- You can verify your code is calling the right methods
- Easy to debug communication issues

### 4. Easy to Debug
- If something goes wrong, you can inspect the mock
- You can see exactly what was called and with what arguments
- Better error messages and debugging information

### 5. Automatic Cleanup
- `monkeypatch` automatically restores original functions after each test
- No risk of leaving mocks in place for other tests
- Clean test isolation

### 6. Comprehensive Coverage
- All transport mechanisms (socket and VISA) are mocked
- No real hardware communication can happen
- Complete control over the testing environment

### 7. Easy to Extend
- Easy to add more mocks or change mock behavior
- Can add different mocks for different test scenarios
- Flexible and maintainable testing approach

## Best Practices

1. **Use `autouse=True`** for fixtures that should run for every test
2. **Keep mocks simple** and focused on the behavior you need to test
3. **Use descriptive names** for your mock objects and methods
4. **Document your mocks** so other developers understand what they simulate
5. **Test the behavior, not the implementation** - focus on what your code should do, not how it does it

This approach gives you the best of both worlds: clean production code and comprehensive testing capabilities! 