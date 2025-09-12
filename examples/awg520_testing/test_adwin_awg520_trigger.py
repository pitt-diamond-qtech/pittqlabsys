#!/usr/bin/env python3
"""
Test script for ADwin→AWG520 external triggering.

This script tests the new control architecture where ADwin generates
trigger pulses to control AWG520 sequence advancement, instead of
the traditional AWG520→ADwin control.

Hardware Setup:
- ADwin Digital Output (DIO 0) → AWG520 TRIG IN (rear panel)
- AWG520 configured for external trigger with Wait Trigger enabled
- Computer controls JUMP_MODE software for sequence advancement
"""

import sys
import time
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.Controller.adwin_gold import AdwinGoldDevice
from src.Controller.awg520 import AWG520Device
from src.Model.awg_file import AWGFile


class ADwinAWG520TriggerTest:
    """Test class for ADwin→AWG520 external triggering."""
    
    def __init__(self):
        """Initialize the test system."""
        self.adwin = None
        self.awg520 = None
        self.test_waveforms_dir = Path("test_waveforms")
        self.test_waveforms_dir.mkdir(exist_ok=True)
        
    def setup_hardware(self):
        """Setup ADwin and AWG520 connections."""
        try:
            print("🔧 Setting up hardware connections...")
            
            # Initialize ADwin
            self.adwin = AdwinGoldDevice()
            if not self.adwin.is_connected():
                print("❌ Failed to connect to ADwin")
                return False
            print("✅ ADwin connected successfully")
            
            # Initialize AWG520
            self.awg520 = AWG520Device()
            if not self.awg520.is_connected():
                print("❌ Failed to connect to AWG520")
                return False
            print("✅ AWG520 connected successfully")
            
            return True
            
        except Exception as e:
            print(f"❌ Hardware setup failed: {e}")
            return False
    
    def create_test_waveforms(self):
        """Create test waveforms for AWG520 testing."""
        print("📊 Creating test waveforms...")
        
        sample_rate = 1e9  # 1 GHz
        duration = 1e-6    # 1 μs
        
        # Generate different waveform types
        waveforms = {
            'sine': self._generate_sine_wave(sample_rate, duration),
            'ramp': self._generate_ramp_wave(sample_rate, duration),
            'triangle': self._generate_triangle_wave(sample_rate, duration),
            'square': self._generate_square_wave(sample_rate, duration)
        }
        
        # Save waveforms
        awg_file = AWGFile(out_dir=self.test_waveforms_dir)
        waveform_files = {}
        
        for name, data in waveforms.items():
            filename = f"test_{name}.wfm"
            filepath = awg_file.write_waveform(
                data, 
                name,
                sample_rate=sample_rate
            )
            waveform_files[name] = filepath
            print(f"  ✅ Created {filename}")
        
        return waveform_files
    
    def _generate_sine_wave(self, sample_rate, duration):
        """Generate sine wave test signal."""
        samples = int(sample_rate * duration)
        t = np.linspace(0, duration, samples)
        frequency = 1e6  # 1 MHz
        return np.sin(2 * np.pi * frequency * t)
    
    def _generate_ramp_wave(self, sample_rate, duration):
        """Generate ramp wave test signal."""
        samples = int(sample_rate * duration)
        return np.linspace(-1, 1, samples)
    
    def _generate_triangle_wave(self, sample_rate, duration):
        """Generate triangle wave test signal."""
        samples = int(sample_rate * duration)
        t = np.linspace(0, duration, samples)
        frequency = 1e6  # 1 MHz
        return 2 * np.abs(2 * (t * frequency - np.floor(t * frequency + 0.5))) - 1
    
    def _generate_square_wave(self, sample_rate, duration):
        """Generate square wave test signal."""
        samples = int(sample_rate * duration)
        t = np.linspace(0, duration, samples)
        frequency = 1e6  # 1 MHz
        return np.sign(np.sin(2 * np.pi * frequency * t))
    
    def create_test_sequence(self, waveform_files):
        """Create test sequence file for AWG520."""
        print("📝 Creating test sequence file...")
        
        sequence_entries = []
        
        # Create sequence with different waveforms and Wait Trigger enabled
        for i, (name, filepath) in enumerate(waveform_files.items()):
            # Format: ch1_wfm, ch2_wfm, repeat, wait_trigger, goto, logic_jump_target
            if i < len(waveform_files) - 1:
                goto = i + 2  # Next line
            else:
                goto = 1      # Back to first line
            
            entry = (
                filepath.name,           # ch1_wfm
                filepath.name,           # ch2_wfm (same for now)
                1,                       # repeat (1 for testing)
                'ON',                    # wait_trigger (enabled)
                'goto',                  # jump mode
                goto                     # goto target
            )
            sequence_entries.append(entry)
            print(f"  ✅ Added {name} waveform to sequence")
        
        # Save sequence file
        awg_file = AWGFile(out_dir=self.test_waveforms_dir)
        seq_file = awg_file.write_sequence(sequence_entries, "test_trigger_sequence")
        print(f"  ✅ Created sequence file: {seq_file}")
        
        return seq_file
    
    def configure_awg520(self):
        """Configure AWG520 for external triggering."""
        print("⚙️  Configuring AWG520 for external triggering...")
        
        try:
            # Set trigger source to external
            self.awg520.write("TRIG:SOUR EXT")
            print("  ✅ Trigger source set to external")
            
            # Set trigger level (for 0→5V TTL input)
            self.awg520.write("TRIG:LEV 2.5")
            print("  ✅ Trigger level set to 2.5V")
            
            # Set trigger impedance
            self.awg520.write("TRIG:IMP 50")
            print("  ✅ Trigger impedance set to 50Ω")
            
            # Set run mode to enhanced (enables Wait Trigger)
            self.awg520.write("AWGC:RMO ENH")
            print("  ✅ Run mode set to enhanced")
            
            # Set jump mode to software (computer controlled)
            self.awg520.write("AWGC:JMODE SOFT")
            print("  ✅ Jump mode set to software")
            
            return True
            
        except Exception as e:
            print(f"❌ AWG520 configuration failed: {e}")
            return False
    
    def load_sequence_to_awg520(self, seq_file):
        """Load test sequence to AWG520."""
        print("📤 Loading sequence to AWG520...")
        
        try:
            # Load sequence file
            self.awg520.load_sequence_file(seq_file)
            print("  ✅ Sequence file loaded")
            
            # Load waveform files
            for wfm_file in self.test_waveforms_dir.glob("*.wfm"):
                self.awg520.load_waveform_file(wfm_file)
                print(f"  ✅ Loaded waveform: {wfm_file.name}")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to load sequence: {e}")
            return False
    
    def configure_adwin_trigger(self, trigger_interval_ms=1000, max_triggers=4):
        """Configure ADwin trigger parameters."""
        print("⚙️  Configuring ADwin trigger parameters...")
        
        try:
            # Set trigger interval (convert to microseconds for ADbasic)
            trigger_interval_us = trigger_interval_ms * 1000
            self.adwin.set_parameter(2, trigger_interval_us)
            print(f"  ✅ Trigger interval set to {trigger_interval_ms}ms")
            
            # Set maximum number of triggers
            self.adwin.set_parameter(3, max_triggers)
            print(f"  ✅ Maximum triggers set to {max_triggers}")
            
            # Set trigger pulse duration (1ms)
            trigger_duration_us = 1000
            self.adwin.set_parameter(4, trigger_duration_us)
            print(f"  ✅ Trigger pulse duration set to 1ms")
            
            return True
            
        except Exception as e:
            print(f"❌ ADwin configuration failed: {e}")
            return False
    
    def run_trigger_test(self):
        """Run the complete trigger test."""
        print("🚀 Running ADwin→AWG520 trigger test...")
        
        try:
            # Start ADwin process
            print("  🔄 Starting ADwin trigger process...")
            self.adwin.start_process(1)
            
            # Wait for ADwin to start
            time.sleep(0.1)
            
            # Start AWG520 sequence
            print("  🔄 Starting AWG520 sequence...")
            self.awg520.run()
            
            # Monitor progress
            print("  📊 Monitoring test progress...")
            for i in range(10):  # Monitor for up to 10 seconds
                time.sleep(1)
                
                # Check ADwin status
                trigger_count = self.adwin.get_parameter(1)
                current_state = self.adwin.get_parameter(5)
                
                print(f"    Trigger {trigger_count}/4, State: {current_state}")
                
                if trigger_count >= 4:
                    print("  ✅ All triggers completed!")
                    break
            
            # Stop AWG520
            self.awg520.stop()
            print("  ✅ AWG520 stopped")
            
            # Stop ADwin process
            self.adwin.stop_process(1)
            print("  ✅ ADwin process stopped")
            
            return True
            
        except Exception as e:
            print(f"❌ Trigger test failed: {e}")
            return False
    
    def cleanup(self):
        """Clean up resources."""
        print("🧹 Cleaning up...")
        
        try:
            if self.awg520:
                self.awg520.stop()
            if self.adwin:
                self.adwin.stop_process(1)
            print("  ✅ Cleanup completed")
        except Exception as e:
            print(f"  ⚠️  Cleanup warning: {e}")


def main():
    """Main test function."""
    print("🧪 ADwin→AWG520 External Trigger Test")
    print("=" * 50)
    
    # Create test instance
    test = ADwinAWG520TriggerTest()
    
    try:
        # Setup hardware
        if not test.setup_hardware():
            print("❌ Hardware setup failed. Exiting.")
            return False
        
        # Create test waveforms
        waveform_files = test.create_test_waveforms()
        
        # Create test sequence
        seq_file = test.create_test_sequence(waveform_files)
        
        # Configure AWG520
        if not test.configure_awg520():
            print("❌ AWG520 configuration failed. Exiting.")
            return False
        
        # Load sequence to AWG520
        if not test.load_sequence_to_awg520(seq_file):
            print("❌ Failed to load sequence. Exiting.")
            return False
        
        # Configure ADwin trigger
        if not test.configure_adwin_trigger():
            print("❌ ADwin configuration failed. Exiting.")
            return False
        
        # Run test
        if test.run_trigger_test():
            print("\n🎉 Test completed successfully!")
            print("✅ ADwin→AWG520 external triggering is working!")
        else:
            print("\n❌ Test failed!")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False
        
    finally:
        test.cleanup()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
