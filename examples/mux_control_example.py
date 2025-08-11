#!/usr/bin/env python3
"""
MUX Control Example Script

This script demonstrates the MUX Control Device functionality for Arduino-based
trigger multiplexing between confocal, ODMR(CW-ESR), and Pulsed ESR sources.
"""

import sys
import time
import argparse
import logging
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent / '..'))

from src.Controller.mux_control import MUXControlDevice, MUXControl


class MUXControlExample:
    """Example class demonstrating MUX Control Device functionality."""
    
    def __init__(self, port='COM3', baudrate=9600, timeout=5000):
        """Initialize the MUX control example."""
        self.settings = {
            'port': port,
            'baudrate': baudrate,
            'timeout': timeout,
            'auto_connect': False
        }
        
        # Set up logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Create device instance
        self.device = MUXControlDevice(settings=self.settings)
        
    def connect(self):
        """Connect to the MUX controller."""
        self.logger.info(f"Attempting to connect to MUX controller on {self.settings['port']}")
        
        if self.device.connect():
            self.logger.info("✓ Successfully connected to MUX controller")
            return True
        else:
            self.logger.error("✗ Failed to connect to MUX controller")
            return False
    
    def disconnect(self):
        """Disconnect from the MUX controller."""
        self.logger.info("Disconnecting from MUX controller...")
        self.device.disconnect()
        self.logger.info("✓ Disconnected from MUX controller")
    
    def print_status(self):
        """Print current device status."""
        if not self.device.is_connected:
            self.logger.warning("Device not connected")
            return
        
        probes = self.device.read_probes()
        self.logger.info("=== MUX Controller Status ===")
        self.logger.info(f"Port: {probes['port']}")
        self.logger.info(f"Connected: {probes['connected']}")
        self.logger.info(f"Current Selection: {probes['status'] or 'None'}")
        self.logger.info("=============================")
    
    def print_hardware_info(self):
        """Print hardware and firmware information."""
        self.logger.info("=== Hardware Information ===")
        
        # Get hardware mapping
        hw_map = self.device.get_hardware_mapping()
        self.logger.info(f"Multiplexer: {hw_map['multiplexer']}")
        self.logger.info(f"Arduino Pins: S0={hw_map['arduino_pins']['S0']}, S1={hw_map['arduino_pins']['S1']}, S2={hw_map['arduino_pins']['S2']}, Z={hw_map['arduino_pins']['Z']}")
        
        # Get Arduino info
        arduino_info = self.device.get_arduino_info()
        self.logger.info(f"Firmware: {arduino_info['firmware']['name']} v{arduino_info['firmware']['date']}")
        self.logger.info(f"Author: {arduino_info['firmware']['author']}")
        self.logger.info(f"Description: {arduino_info['firmware']['description']}")
        
        # Show channel mapping
        self.logger.info("Channel Mapping:")
        for trigger, info in hw_map['channel_mapping'].items():
            self.logger.info(f"  {trigger}: {info['channel']} (S0={info['pins']['S0']}, S1={info['pins']['S1']}, S2={info['pins']['S2']})")
        
        self.logger.info("===========================")
    
    def test_connection(self):
        """Test the connection to the Arduino."""
        self.logger.info("=== Testing Connection ===")
        
        # Test connection
        test_result = self.device.test_connection()
        if test_result['connected']:
            self.logger.info("✓ Connection test successful")
            if test_result['arduino_message']:
                self.logger.info(f"Arduino message: {test_result['arduino_message']}")
            self.logger.info(f"Port: {test_result['port']}")
            self.logger.info(f"Baudrate: {test_result['baudrate']}")
            self.logger.info(f"Current selection: {test_result['current_selection']}")
        else:
            self.logger.error(f"✗ Connection test failed: {test_result['error']}")
        
        self.logger.info("========================")
    
    def demonstrate_trigger_selection(self):
        """Demonstrate all trigger selection options."""
        if not self.device.is_connected:
            self.logger.error("Cannot demonstrate triggers: device not connected")
            return
        
        self.logger.info("=== Trigger Selection Demonstration ===")
        
        # Test confocal trigger
        self.logger.info("Selecting confocal trigger...")
        if self.device.select_trigger('confocal'):
            self.logger.info("✓ Confocal trigger selected")
            time.sleep(1)  # Give hardware time to switch
        else:
            self.logger.error("✗ Failed to select confocal trigger")
        
        # Test CW-ESR trigger
        self.logger.info("Selecting ODMR trigger...")
        if self.device.select_trigger('odmr'):
            self.logger.info("✓ ODMR trigger selected")
            time.sleep(1)
        else:
            self.logger.error("✗ Failed to select ODMR trigger")
        
        # Test pulsed ESR trigger
        self.logger.info("Selecting pulsed ESR trigger...")
        if self.device.select_trigger('pulsed'):
            self.logger.info("✓ Pulsed ESR trigger selected")
            time.sleep(1)
        else:
            self.logger.error("✗ Failed to select pulsed ESR trigger")
        
        # Return to confocal for safety
        self.logger.info("Returning to confocal trigger for safety...")
        if self.device.select_trigger('confocal'):
            self.logger.info("✓ Confocal trigger restored")
        else:
            self.logger.error("✗ Failed to restore confocal trigger")
        
        self.logger.info("=== Demonstration Complete ===")
    
    def run_sequence_demo(self, cycles=3):
        """Run a sequence of trigger selections."""
        if not self.device.is_connected:
            self.logger.error("Cannot run sequence: device not connected")
            return
        
        self.logger.info(f"=== Running Sequence Demo ({cycles} cycles) ===")
        
        for cycle in range(cycles):
            self.logger.info(f"--- Cycle {cycle + 1}/{cycles} ---")
            
            # Cycle through all triggers
            for trigger in ['confocal', 'odmr', 'pulsed']:
                self.logger.info(f"Selecting {trigger} trigger...")
                if self.device.select_trigger(trigger):
                    self.logger.info(f"✓ {trigger} selected")
                    time.sleep(0.5)  # Brief pause between selections
                else:
                    self.logger.error(f"✗ Failed to select {trigger}")
            
            # Return to confocal
            self.device.select_trigger('confocal')
            self.logger.info("✓ Returned to confocal")
            
            if cycle < cycles - 1:  # Don't sleep after last cycle
                time.sleep(1)
        
        self.logger.info("=== Sequence Demo Complete ===")
    
    def test_invalid_selection(self):
        """Test handling of invalid trigger selections."""
        if not self.device.is_connected:
            self.logger.error("Cannot test invalid selection: device not connected")
            return
        
        self.logger.info("=== Testing Invalid Selection Handling ===")
        
        # Try invalid selector
        result = self.device.select_trigger('invalid_trigger')
        if not result:
            self.logger.info("✓ Correctly rejected invalid trigger selection")
        else:
            self.logger.error("✗ Should have rejected invalid trigger selection")
        
        self.logger.info("=== Invalid Selection Test Complete ===")
    
    def run_demo(self):
        """Run the complete demonstration."""
        try:
            # Connect to device
            if not self.connect():
                return False
            
            # Print initial status
            self.print_status()
            
            # Show hardware information
            self.print_hardware_info()
            
            # Test connection
            self.test_connection()
            
            # Run demonstrations
            self.demonstrate_trigger_selection()
            time.sleep(1)
            
            self.run_sequence_demo(cycles=2)
            time.sleep(1)
            
            self.test_invalid_selection()
            
            # Print final status
            self.print_status()
            
            return True
            
        except KeyboardInterrupt:
            self.logger.info("Demo interrupted by user")
            return False
        except Exception as e:
            self.logger.error(f"Demo failed with error: {e}")
            return False
        finally:
            # Always disconnect
            self.disconnect()
    
    def cleanup(self):
        """Clean up resources."""
        self.device.cleanup()


def main():
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(
        description="MUX Control Device Example Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use default COM3 port
  python mux_control_example.py
  
  # Use custom port
  python mux_control_example.py --port COM5
  
  # Use custom settings
  python mux_control_example.py --port COM4 --baudrate 115200 --timeout 10000
        """
    )
    
    parser.add_argument(
        '--port', 
        default='COM3',
        help='Serial port for Arduino connection (default: COM3)'
    )
    
    parser.add_argument(
        '--baudrate', 
        type=int, 
        default=9600,
        help='Serial baudrate (default: 9600)'
    )
    
    parser.add_argument(
        '--timeout', 
        type=int, 
        default=5000,
        help='Serial timeout in milliseconds (default: 5000)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create and run example
    example = MUXControlExample(
        port=args.port,
        baudrate=args.baudrate,
        timeout=args.timeout
    )
    
    try:
        success = example.run_demo()
        if success:
            print("\n✓ MUX Control demo completed successfully!")
        else:
            print("\n✗ MUX Control demo failed!")
            sys.exit(1)
    finally:
        example.cleanup()


if __name__ == "__main__":
    main() 