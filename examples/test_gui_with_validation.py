#!/usr/bin/env python3
"""
Test GUI with Enhanced Validation Features

This script launches the GUI with mock hardware that supports all the new
validation and feedback features, allowing you to test:

- Units validation with pint
- Parameter clamping and error detection  
- Enhanced feedback system
- Visual GUI updates
- Text box corrections
- Popup notifications for errors

Usage:
    python test_gui_with_validation.py
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Mock hardware before importing GUI
from unittest.mock import patch, MagicMock

# Mock the hardware devices
def mock_hardware_devices():
    """Mock all hardware devices with enhanced validation support."""
    
    # Import our mock devices
    from examples.mock_hardware_for_gui_testing import MockStageDevice, MockRFGenerator
    
    # Create mock devices
    mock_devices = {
        'stage': MockStageDevice(),
        'rf_generator': MockRFGenerator(),
    }
    
    # Mock the device loading
    def mock_load_device(device_name, config=None):
        if device_name in mock_devices:
            return mock_devices[device_name]
        else:
            # Return a basic mock device for other devices
            from src.core.device import Device
            from src.core.parameter import Parameter
            
            class BasicMockDevice(Device):
                def __init__(self, name=device_name):
                    super().__init__()
                    self.name = name
                    self._settings = Parameter([
                        Parameter('value', 0.0, float, f'{device_name} value'),
                    ])
                    self._probes = {'value': f'{device_name} value'}
                
                @property
                def _PROBES(self):
                    return self._probes
                
                def read_probes(self, name=None):
                    return self._settings
                
                def _update_and_get_with_feedback(self, settings):
                    # Basic implementation for other devices
                    original_values = {}
                    for key in settings.keys():
                        if key in self._settings:
                            original_values[key] = self._settings[key]
                    
                    self.update(settings)
                    actual_values = self.read_probes()
                    
                    feedback = {}
                    for key, requested_value in settings.items():
                        if key in actual_values:
                            actual_value = actual_values[key]
                            changed = requested_value != actual_value
                            
                            feedback[key] = {
                                'changed': changed,
                                'requested': requested_value,
                                'actual': actual_value,
                                'reason': 'success' if not changed else 'unknown',
                                'message': 'Value set successfully' if not changed else f'Value changed from {requested_value} to {actual_value}'
                            }
                    
                    return {
                        'actual_values': actual_values,
                        'feedback': feedback
                    }
            
            return BasicMockDevice(device_name)
    
    return mock_load_device

# Apply the mocks
mock_load_device = mock_hardware_devices()

# Mock the device loading function only for specific devices
def enhanced_load_device(device_name, config=None):
    """Enhanced device loader that uses mocks for testing but allows real hardware."""
    # Use mock for specific devices that we want to test
    if device_name in ['stage', 'rf_generator']:
        return mock_load_device(device_name, config)
    else:
        # For other devices, try to load normally
        try:
            from src.tools.device_loader import load_device as real_load_device
            return real_load_device(device_name, config)
        except:
            # Fallback to mock if real device fails
            return mock_load_device(device_name, config)

with patch('src.tools.device_loader.load_device', side_effect=enhanced_load_device):
    # Now import and run the GUI
    try:
        from PyQt5.QtWidgets import QApplication
        from src.View.windows_and_widgets.main_window import MainWindow
        import sys
        
        def main():
            """Launch GUI with mock hardware."""
            print("🚀 Launching GUI with Enhanced Validation Features")
            print("=" * 60)
            print("Mock devices loaded:")
            print("  - Stage Device (with position/speed/acceleration validation)")
            print("  - RF Generator (with frequency/power/phase validation)")
            print()
            print("Test scenarios you can try:")
            print("  📍 Stage Position:")
            print("    - Type '5.0' → Should work normally")
            print("    - Type '15.0' → Should clamp to 10.0mm (yellow background)")
            print("    - Type '50.0' → Should show error (red background + popup)")
            print()
            print("  📡 RF Frequency:")
            print("    - Type '2.85e9' → Should work normally")
            print("    - Type '8e9' → Should clamp to 6e9 Hz (yellow background)")
            print("    - Type '2.85 GHz' → Should convert units (green background)")
            print()
            print("  ⚡ RF Power:")
            print("    - Type '10.0' → Should work normally")
            print("    - Type '25.0' → Should clamp to 20.0 mW (yellow background)")
            print("    - Type '10 mW' → Should convert units (green background)")
            print()
            print("🎯 Watch for:")
            print("  - Text boxes updating to show actual values")
            print("  - Colored backgrounds (green/yellow/red)")
            print("  - Popup dialogs for hardware errors")
            print("  - Log messages in the console")
            print()
            
            app = QApplication(sys.argv)
            window = MainWindow()
            window.show()
            
            print("✅ GUI launched! Try the test scenarios above.")
            print("   Close the GUI window to exit.")
            
            return app.exec_()
        
        if __name__ == "__main__":
            sys.exit(main())
            
    except ImportError as e:
        print(f"❌ Error importing GUI components: {e}")
        print("Make sure PyQt5 is installed and the project structure is correct.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error launching GUI: {e}")
        sys.exit(1)
