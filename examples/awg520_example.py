#!/usr/bin/env python3
"""
AWG520 Example Script with Laser Control

This script demonstrates the operation of the Tektronix AWG520 arbitrary waveform generator,
including:
- Basic SCPI communication and clock configuration
- Sequence setup and control
- File operations via FTP
- Laser control via CH2 Marker 2 (CH2M2)
- Real-time monitoring and status checking

Usage:
    python examples/awg520_example.py [--ip-address IP] [--scpi-port PORT] [--ftp-port PORT] [--ftp-user USER] [--ftp-pass PASS]

Examples:
    # Default connection (172.17.39.2:4000)
    python examples/awg520_example.py
    
    # Custom IP address
    python examples/awg520_example.py --ip-address 192.168.1.100
    
    # Custom connection settings
    python examples/awg520_example.py --ip-address 192.168.1.100 --scpi-port 4000 --ftp-port 21
"""

import sys
import time
import argparse
import logging
from pathlib import Path
from datetime import datetime

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / '..'))

from src.Controller.awg520 import AWG520Driver, AWG520Device


class AWG520Example:
    """Example class for AWG520 operation with laser control."""
    
    def __init__(self, connection_settings):
        """Initialize AWG520 with connection settings."""
        self.settings = connection_settings
        self.driver = None
        self.device = None
        
        # Setup logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
        
        # Create output directory for data
        self.output_dir = Path(__file__).parent / "awg520_data"
        self.output_dir.mkdir(exist_ok=True)
        
        print("=" * 60)
        print("AWG520 ARBITRARY WAVEFORM GENERATOR EXAMPLE")
        print("=" * 60)
        print(f"IP Address: {connection_settings['ip_address']}")
        print(f"SCPI Port: {connection_settings['scpi_port']}")
        print(f"FTP Port: {connection_settings['ftp_port']}")
        print(f"FTP User: {connection_settings['ftp_user']}")
        print("=" * 60)
    
    def connect(self):
        """Connect to the AWG520 device."""
        try:
            print("Connecting to AWG520...")
            self.driver = AWG520Driver(
                ip_address=self.settings['ip_address'],
                scpi_port=self.settings['scpi_port'],
                ftp_port=self.settings['ftp_port'],
                ftp_user=self.settings['ftp_user'],
                ftp_pass=self.settings['ftp_pass']
            )
            
            # Test connection
            idn = self.driver.send_command('*IDN?', query=True)
            print(f"✓ Connected to: {idn}")
            
            # Get device status
            self._print_device_status()
            
            return True
            
        except Exception as e:
            print(f"✗ Connection failed: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from the AWG520 device."""
        if self.driver:
            print("Disconnecting from AWG520...")
            self.driver.cleanup()
            print("✓ Disconnected")
    
    def _print_device_status(self):
        """Print current device status."""
        print("\n--- Device Status ---")
        try:
            # Get clock source
            clock_source = self.driver.send_command('AWGC:CLOC:SOUR?', query=True)
            print(f"Clock Source: {clock_source}")
            
            # Get run mode
            run_mode = self.driver.send_command('AWGC:RMOD?', query=True)
            print(f"Run Mode: {run_mode}")
            
            # Get output status
            out1_status = self.driver.send_command('OUTP1:STAT?', query=True)
            out2_status = self.driver.send_command('OUTP2:STAT?', query=True)
            print(f"Output 1: {'ON' if out1_status == '1' else 'OFF'}")
            print(f"Output 2: {'ON' if out2_status == '1' else 'OFF'}")
            
            # Get marker voltages for CH1 and CH2
            ch1_m1_low = self.driver.send_command('SOUR1:MARK1:VOLT:LOW?', query=True)
            ch1_m1_high = self.driver.send_command('SOUR1:MARK1:VOLT:HIGH?', query=True)
            ch1_m2_low = self.driver.send_command('SOUR1:MARK2:VOLT:LOW?', query=True)
            ch1_m2_high = self.driver.send_command('SOUR1:MARK2:VOLT:HIGH?', query=True)
            ch2_m1_low = self.driver.send_command('SOUR2:MARK1:VOLT:LOW?', query=True)
            ch2_m1_high = self.driver.send_command('SOUR2:MARK1:VOLT:HIGH?', query=True)
            ch2_m2_low = self.driver.send_command('SOUR2:MARK2:VOLT:LOW?', query=True)
            ch2_m2_high = self.driver.send_command('SOUR2:MARK2:VOLT:HIGH?', query=True)
            
            print(f"CH1 Marker 1: LOW={ch1_m1_low}V, HIGH={ch1_m1_high}V")
            print(f"CH1 Marker 2: LOW={ch1_m2_low}V, HIGH={ch1_m2_high}V (LASER CONTROL)")
            print(f"CH2 Marker 1: LOW={ch2_m1_low}V, HIGH={ch2_m1_high}V")
            print(f"CH2 Marker 2: LOW={ch2_m2_low}V, HIGH={ch2_m2_high}V")
            
        except Exception as e:
            print(f"Could not read device status: {e}")
    
    def basic_operation_demo(self):
        """Demonstrate basic AWG520 operation."""
        print("\n" + "=" * 40)
        print("BASIC OPERATION DEMONSTRATION")
        print("=" * 40)
        
        # Test clock configuration
        print("\n1. Clock Configuration Test")
        print("   Setting external clock...")
        result = self.driver.set_clock_external()
        if result is None:
            print("   ✓ External clock set successfully")
        else:
            print(f"   ⚠️  External clock setting returned: {result}")
        
        time.sleep(0.1)
        
        print("   Setting internal clock...")
        result = self.driver.set_clock_internal()
        if result is None:
            print("   ✓ Internal clock set successfully")
        else:
            print(f"   ⚠️  Internal clock setting returned: {result}")
        
        time.sleep(0.1)
        
        # Test reference clock configuration
        print("\n2. Reference Clock Configuration Test")
        print("   Setting external reference clock...")
        result = self.driver.set_ref_clock_external()
        if result is None:
            print("   ✓ External reference clock set successfully")
        else:
            print(f"   ⚠️  External reference clock setting returned: {result}")
        
        time.sleep(0.1)
        
        # Test enhanced run mode
        print("\n3. Enhanced Run Mode Test")
        print("   Setting enhanced run mode...")
        result = self.driver.set_enhanced_run_mode()
        if result is None:
            print("   ✓ Enhanced run mode set successfully")
        else:
            print(f"   ⚠️  Enhanced run mode setting returned: {result}")
        
        print("\n✓ Basic operation demonstration completed")
    
    def laser_control_demo(self):
        """Demonstrate laser control via CH2 Marker 2."""
        print("\n" + "=" * 40)
        print("LASER CONTROL DEMONSTRATION")
        print("=" * 40)
        
        print("This demonstration controls the laser via CH1 Marker 2")
        print("The laser is turned on by setting the marker voltage to 5V")
        print("The laser is turned off by setting the marker voltage to 0V")
        
        # Test laser off
        print("\n1. Turning laser OFF...")
        result = self.driver.set_ch1_marker2_laser_off()
        if result:
            print("   ✓ Laser turned off successfully")
        else:
            print("   ✗ Failed to turn off laser")
        
        time.sleep(0.2)
        
        # Verify laser is off
        is_on = self.driver.is_ch1_marker2_laser_on()
        print(f"   Laser status: {'ON' if is_on else 'OFF'}")
        
        # Get current voltage
        low_v, high_v = self.driver.get_ch1_marker2_voltage()
        if low_v is not None and high_v is not None:
            print(f"   Current voltage: LOW={low_v}V, HIGH={high_v}V")
        else:
            print("   Could not read voltage")
        
        # Test laser on
        print("\n2. Turning laser ON...")
        result = self.driver.set_ch1_marker2_laser_on()
        if result:
            print("   ✓ Laser turned on successfully")
        else:
            print("   ✗ Failed to turn on laser")
        
        time.sleep(0.2)
        
        # Verify laser is on
        is_on = self.driver.is_ch1_marker2_laser_on()
        print(f"   Laser status: {'ON' if is_on else 'OFF'}")
        
        # Get current voltage
        low_v, high_v = self.driver.get_ch1_marker2_voltage()
        if low_v is not None and high_v is not None:
            print(f"   Current voltage: LOW={low_v}V, HIGH={high_v}V")
        else:
            print("   Could not read voltage")
        
        # Test custom voltage
        print("\n3. Setting custom laser voltage (3.3V)...")
        result = self.driver.set_ch1_marker2_voltage(3.3)
        if result:
            print("   ✓ Custom voltage set successfully")
        else:
            print("   ✗ Failed to set custom voltage")
        
        time.sleep(0.2)
        
        # Verify custom voltage
        low_v, high_v = self.driver.get_ch1_marker2_voltage()
        if low_v is not None and high_v is not None:
            print(f"   Current voltage: LOW={low_v}V, HIGH={high_v}V")
            if abs(low_v - 3.3) < 0.1 and abs(high_v - 3.3) < 0.1:
                print("   ✓ Custom voltage verified")
            else:
                print("   ⚠️  Voltage verification failed")
        else:
            print("   Could not read voltage")
        
        # Test different low/high voltages
        print("\n4. Setting different low/high voltages (2.5V/5.0V)...")
        result = self.driver.set_ch1_marker2_voltage(2.5, 5.0)
        if result:
            print("   ✓ Different voltages set successfully")
        else:
            print("   ✗ Failed to set different voltages")
        
        time.sleep(0.2)
        
        # Verify different voltages
        low_v, high_v = self.driver.get_ch1_marker2_voltage()
        if low_v is not None and high_v is not None:
            print(f"   Current voltage: LOW={low_v}V, HIGH={high_v}V")
            if abs(low_v - 2.5) < 0.1 and abs(high_v - 5.0) < 0.1:
                print("   ✓ Different voltages verified")
            else:
                print("   ⚠️  Voltage verification failed")
        else:
            print("   Could not read voltage")
        
        # Turn laser off for safety
        print("\n5. Turning laser OFF for safety...")
        result = self.driver.set_ch1_marker2_laser_off()
        if result:
            print("   ✓ Laser turned off successfully")
        else:
            print("   ✗ Failed to turn off laser")
        
        time.sleep(0.2)
        
        # Final verification
        is_on = self.driver.is_ch1_marker2_laser_on()
        print(f"   Final laser status: {'ON' if is_on else 'OFF'}")
        
        print("\n✓ Laser control demonstration completed")
    
    def sequence_control_demo(self):
        """Demonstrate sequence control functionality."""
        print("\n" + "=" * 40)
        print("SEQUENCE CONTROL DEMONSTRATION")
        print("=" * 40)
        
        # Test sequence control commands
        print("\n1. Testing sequence control commands...")
        
        # Test stop (in case something is running)
        print("   Stopping any running sequence...")
        result = self.driver.stop()
        if result is None:
            print("   ✓ Stop command sent successfully")
        else:
            print(f"   ⚠️  Stop command returned: {result}")
        
        time.sleep(0.1)
        
        # Test run
        print("   Starting sequence...")
        result = self.driver.run()
        if result is None:
            print("   ✓ Run command sent successfully")
        else:
            print(f"   ⚠️  Run command returned: {result}")
        
        time.sleep(0.1)
        
        # Test stop again
        print("   Stopping sequence...")
        result = self.driver.stop()
        if result is None:
            print("   ✓ Stop command sent successfully")
        else:
            print(f"   ⚠️  Stop command returned: {result}")
        
        time.sleep(0.1)
        
        # Test trigger
        print("   Sending trigger...")
        result = self.driver.trigger()
        if result is None:
            print("   ✓ Trigger command sent successfully")
        else:
            print(f"   ⚠️  Trigger command returned: {result}")
        
        time.sleep(0.1)
        
        # Test event
        print("   Sending event...")
        result = self.driver.event()
        if result is None:
            print("   ✓ Event command sent successfully")
        else:
            print(f"   ⚠️  Event command returned: {result}")
        
        time.sleep(0.1)
        
        # Test jump
        print("   Testing jump to line 5...")
        result = self.driver.jump(5)
        if result is None:
            print("   ✓ Jump command sent successfully")
        else:
            print(f"   ⚠️  Jump command returned: {result}")
        
        print("\n✓ Sequence control demonstration completed")
    
    def function_generator_demo(self):
        """Demonstrate function generator and IQ modulation functionality."""
        print("\n" + "=" * 40)
        print("FUNCTION GENERATOR & IQ MODULATION DEMO")
        print("=" * 40)
        
        print("This demonstration shows function generator capabilities")
        print("including I/Q modulation with sine and cosine waves")
        
        # Test single channel function generator
        print("\n1. Testing single channel function generator...")
        print("   Setting CH1 to 5MHz sine wave at 3.0V...")
        
        result = self.driver.set_function_generator(1, 'SIN', '5MHz', 3.0, 0.0, True)
        if result:
            print("   ✓ Function generator configured successfully")
        else:
            print("   ✗ Failed to configure function generator")
        
        time.sleep(0.2)
        
        # Get status
        status = self.driver.get_function_generator_status(1)
        if status:
            print(f"   Current status: {status['function']} at {status['frequency']}, {status['voltage']}V, {status['phase']}°")
        else:
            print("   Could not read function generator status")
        
        # Test IQ modulation
        print("\n2. Testing I/Q modulation...")
        print("   Enabling I/Q modulation at 10MHz, 2.0V...")
        
        result = self.driver.enable_iq_modulation('10MHz', 2.0)
        if result:
            print("   ✓ I/Q modulation enabled successfully")
        else:
            print("   ✗ Failed to enable I/Q modulation")
        
        time.sleep(0.2)
        
        # Get status for both channels
        ch1_status = self.driver.get_function_generator_status(1)
        ch2_status = self.driver.get_function_generator_status(2)
        
        if ch1_status and ch2_status:
            print(f"   CH1 (I): {ch1_status['function']} at {ch1_status['frequency']}, {ch1_status['voltage']}V, {ch1_status['phase']}°")
            print(f"   CH2 (Q): {ch2_status['function']} at {ch2_status['frequency']}, {ch2_status['voltage']}V, {ch2_status['phase']}°")
        else:
            print("   Could not read I/Q modulation status")
        
        # Test MW on/off with IQ modulation
        print("\n3. Testing MW on/off with IQ modulation...")
        print("   Turning on MW with I/Q modulation...")
        
        result = self.driver.mw_on_sb10MHz(enable_iq=True)
        if result:
            print("   ✓ MW turned on with I/Q modulation")
        else:
            print("   ✗ Failed to turn on MW")
        
        time.sleep(0.5)
        
        print("   Turning off MW...")
        result = self.driver.mw_off_sb10MHz(enable_iq=True)
        if result:
            print("   ✓ MW turned off")
        else:
            print("   ✗ Failed to turn off MW")
        
        time.sleep(0.2)
        
        # Test different waveform types
        print("\n4. Testing different waveform types...")
        waveforms = ['SIN', 'SQU', 'TRI', 'RAMP']
        
        for waveform in waveforms:
            print(f"   Setting CH1 to {waveform} wave at 1kHz, 1.5V...")
            result = self.driver.set_function_generator(1, waveform, '1kHz', 1.5, 0.0, True)
            if result:
                print(f"   ✓ {waveform} wave configured successfully")
            else:
                print(f"   ✗ Failed to configure {waveform} wave")
            time.sleep(0.1)
        
        # Turn off function generator
        print("\n5. Turning off function generator...")
        result = self.driver.disable_iq_modulation()
        if result:
            print("   ✓ Function generator turned off")
        else:
            print("   ✗ Failed to turn off function generator")
        
        print("\n✓ Function generator demonstration completed")
    
    def file_operations_demo(self):
        """Demonstrate file operations via FTP."""
        print("\n" + "=" * 40)
        print("FILE OPERATIONS DEMONSTRATION")
        print("=" * 40)
        
        # Test listing files
        print("\n1. Listing files on AWG520...")
        try:
            files = self.driver.list_files()
            if files:
                print(f"   ✓ Found {len(files)} files:")
                for i, file in enumerate(files[:10]):  # Show first 10 files
                    print(f"      {i+1}. {file}")
                if len(files) > 10:
                    print(f"      ... and {len(files) - 10} more files")
            else:
                print("   ⚠️  No files found")
        except Exception as e:
            print(f"   ✗ Failed to list files: {e}")
        
        # Test file operations (read-only for safety)
        print("\n2. Testing file operations...")
        
        # Check if we can read a file (won't modify anything)
        if files:
            test_file = files[0]  # Use first available file
            print(f"   Testing download of: {test_file}")
            
            try:
                # Create a temporary local path
                local_path = self.output_dir / f"temp_{test_file}"
                
                # Test download
                result = self.driver.download_file(test_file, str(local_path))
                if result:
                    print(f"   ✓ Successfully downloaded {test_file}")
                    
                    # Check file size
                    if local_path.exists():
                        file_size = local_path.stat().st_size
                        print(f"   File size: {file_size} bytes")
                        
                        # Clean up temporary file
                        local_path.unlink()
                        print("   Temporary file cleaned up")
                else:
                    print(f"   ✗ Failed to download {test_file}")
                    
            except Exception as e:
                print(f"   ⚠️  File operation test failed: {e}")
        else:
            print("   ⚠️  No files available for testing")
        
        print("\n✓ File operations demonstration completed")
    
    def sequence_setup_demo(self):
        """Demonstrate sequence setup functionality."""
        print("\n" + "=" * 40)
        print("SEQUENCE SETUP DEMONSTRATION")
        print("=" * 40)
        
        print("This demonstration shows how to set up a sequence file")
        print("Note: This is a demonstration of the setup process")
        print("No actual sequence file will be loaded")
        
        # Test sequence setup (with a dummy filename)
        print("\n1. Testing sequence setup process...")
        
        try:
            # This will test the setup process but won't actually load a file
            print("   Setting up sequence 'demo_sequence.seq'...")
            
            # Test the setup method (this will fail gracefully without a real file)
            result = self.driver.setup_sequence('demo_sequence.seq', enable_iq=False)
            
            if result is None:
                print("   ✓ Sequence setup process completed")
            else:
                print(f"   ⚠️  Sequence setup returned: {result}")
                
        except Exception as e:
            print(f"   ⚠️  Sequence setup test failed (expected without real file): {e}")
        
        print("\n✓ Sequence setup demonstration completed")
    
    def run_demo(self):
        """Run the complete AWG520 demonstration."""
        if not self.connect():
            return False
        
        try:
            # Run demonstrations
            self.basic_operation_demo()
            self.laser_control_demo()
            self.sequence_control_demo()
            self.function_generator_demo()
            self.file_operations_demo()
            self.sequence_setup_demo()
            
            print("\n" + "=" * 60)
            print("ALL DEMONSTRATIONS COMPLETED SUCCESSFULLY!")
            print("=" * 60)
            
            # Final device status
            self._print_device_status()
            
            return True
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Demo interrupted by user")
            return False
        except Exception as e:
            print(f"\n\n✗ Demo failed with error: {e}")
            return False
        finally:
            # Always cleanup
            self.cleanup()
    
    def cleanup(self):
        """Clean up and set device to safe state."""
        if not self.driver:
            return
        
        print("\n--- Cleanup and Safety ---")
        
        try:
            # Stop any running sequences
            self.driver.stop()
            time.sleep(0.1)
            
            # Turn off laser for safety
            self.driver.set_ch1_marker2_laser_off()
            time.sleep(0.1)
            
            # Set safe marker voltages
            self.driver.send_command('SOUR1:MARK2:VOLT:LOW 0.0')
            time.sleep(0.05)
            self.driver.send_command('SOUR1:MARK2:VOLT:HIGH 0.0')
            time.sleep(0.05)
            
            print("✓ Device set to safe state")
            print("✓ Laser turned off")
            
        except Exception as e:
            print(f"⚠️  Cleanup error: {e}")
        
        # Disconnect
        self.disconnect()


def main():
    """Main function to run the AWG520 example."""
    parser = argparse.ArgumentParser(description='AWG520 Example Script with Laser Control')
    parser.add_argument('--ip-address', default='172.17.39.2', 
                       help='IP address of the AWG520 (default: 172.17.39.2)')
    parser.add_argument('--scpi-port', type=int, default=4000, 
                       help='SCPI port of the AWG520 (default: 4000)')
    parser.add_argument('--ftp-port', type=int, default=21, 
                       help='FTP port of the AWG520 (default: 21)')
    parser.add_argument('--ftp-user', default='usr', 
                       help='FTP username (default: usr)')
    parser.add_argument('--ftp-pass', default='pw', 
                       help='FTP password (default: pw)')
    
    args = parser.parse_args()
    
    # Build connection settings
    settings = {
        'ip_address': args.ip_address,
        'scpi_port': args.scpi_port,
        'ftp_port': args.ftp_port,
        'ftp_user': args.ftp_user,
        'ftp_pass': args.ftp_pass
    }
    
    # Create and run example
    example = AWG520Example(settings)
    success = example.run_demo()
    
    if success:
        print("\n🎉 AWG520 example completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ AWG520 example failed!")
        sys.exit(1)


if __name__ == "__main__":
    main() 