#!/usr/bin/env python3
"""
Pytest version of ADwin→AWG520 external trigger test.

This provides a more structured testing approach with pytest fixtures
and assertions for automated testing.
"""

import pytest
import sys
import time
from pathlib import Path
import numpy as np

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.Controller.adwin_gold import AdwinGoldDevice
from src.Controller.awg520 import AWG520Device
from src.Model.awg_file import AWGFile


class TestADwinAWG520Trigger:
    """Test class for ADwin→AWG520 external triggering."""
    
    @pytest.fixture(scope="class")
    def test_setup(self):
        """Setup test environment and hardware."""
        print("\n🔧 Setting up test environment...")
        
        # Create test directory
        test_dir = Path("test_waveforms")
        test_dir.mkdir(exist_ok=True)
        
        # Initialize hardware
        adwin = AdwinGoldDevice()
        awg520 = AWG520Device()
        
        # Check connections
        if not adwin.is_connected():
            pytest.skip("ADwin not connected")
        if not awg520.is_connected():
            pytest.skip("AWG520 not connected")
        
        yield {
            'adwin': adwin,
            'awg520': awg520,
            'test_dir': test_dir
        }
        
        # Cleanup
        print("\n🧹 Cleaning up test environment...")
        try:
            awg520.stop()
            adwin.stop_process(1)
        except:
            pass
    
    def test_hardware_connections(self, test_setup):
        """Test that hardware connections are working."""
        adwin = test_setup['adwin']
        awg520 = test_setup['awg520']
        
        assert adwin.is_connected(), "ADwin should be connected"
        assert awg520.is_connected(), "AWG520 should be connected"
        
        print("✅ Hardware connections verified")
    
    def test_waveform_generation(self, test_setup):
        """Test that test waveforms can be generated."""
        test_dir = test_setup['test_dir']
        
        # Generate test waveforms
        sample_rate = 1e9  # 1 GHz
        duration = 1e-6    # 1 μs
        
        waveforms = {
            'sine': np.sin(2 * np.pi * 1e6 * np.linspace(0, duration, int(sample_rate * duration))),
            'ramp': np.linspace(-1, 1, int(sample_rate * duration)),
            'triangle': 2 * np.abs(2 * (np.linspace(0, duration, int(sample_rate * duration)) * 1e6 - 
                                      np.floor(np.linspace(0, duration, int(sample_rate * duration)) * 1e6 + 0.5))) - 1,
            'square': np.sign(np.sin(2 * np.pi * 1e6 * np.linspace(0, duration, int(sample_rate * duration))))
        }
        
        # Save waveforms
        awg_file = AWGFile(out_dir=test_dir)
        waveform_files = {}
        
        for name, data in waveforms.items():
            filepath = awg_file.write_waveform(data, f"test_{name}", sample_rate=sample_rate)
            waveform_files[name] = filepath
            assert filepath.exists(), f"Waveform file {name} should be created"
        
        test_setup['waveform_files'] = waveform_files
        print("✅ Test waveforms generated successfully")
    
    def test_sequence_creation(self, test_setup):
        """Test that test sequence can be created."""
        test_dir = test_setup['test_dir']
        waveform_files = test_setup['waveform_files']
        
        # Create sequence entries
        sequence_entries = []
        for i, (name, filepath) in enumerate(waveform_files.items()):
            goto = i + 2 if i < len(waveform_files) - 1 else 1
            entry = (
                filepath.name,           # ch1_wfm
                filepath.name,           # ch2_wfm
                1,                       # repeat
                'ON',                    # wait_trigger
                'goto',                  # jump mode
                goto                     # goto target
            )
            sequence_entries.append(entry)
        
        # Save sequence file
        awg_file = AWGFile(out_dir=test_dir)
        seq_file = awg_file.write_sequence(sequence_entries, "test_trigger_sequence")
        
        assert seq_file.exists(), "Sequence file should be created"
        test_setup['seq_file'] = seq_file
        print("✅ Test sequence created successfully")
    
    def test_awg520_configuration(self, test_setup):
        """Test AWG520 configuration for external triggering."""
        awg520 = test_setup['awg520']
        
        # Configure AWG520
        awg520.write("TRIG:SOUR EXT")
        awg520.write("TRIG:LEV 2.5")
        awg520.write("TRIG:IMP 50")
        awg520.write("AWGC:RMO ENH")
        awg520.write("AWGC:JMODE SOFT")
        
        # Verify configuration
        trigger_source = awg520.query("TRIG:SOUR?")
        run_mode = awg520.query("AWGC:RMO?")
        
        assert "EXT" in trigger_source, "Trigger source should be external"
        assert "ENH" in run_mode, "Run mode should be enhanced"
        
        print("✅ AWG520 configured for external triggering")
    
    def test_adwin_trigger_configuration(self, test_setup):
        """Test ADwin trigger parameter configuration."""
        adwin = test_setup['adwin']
        
        # Configure trigger parameters
        trigger_interval_us = 1000000  # 1 second
        max_triggers = 4
        trigger_duration_us = 1000     # 1ms
        
        adwin.set_parameter(2, trigger_interval_us)
        adwin.set_parameter(3, max_triggers)
        adwin.set_parameter(4, trigger_duration_us)
        
        # Verify parameters
        interval = adwin.get_parameter(2)
        max_trig = adwin.get_parameter(3)
        duration = adwin.get_parameter(4)
        
        assert interval == trigger_interval_us, "Trigger interval should be set correctly"
        assert max_trig == max_triggers, "Max triggers should be set correctly"
        assert duration == trigger_duration_us, "Trigger duration should be set correctly"
        
        print("✅ ADwin trigger parameters configured")
    
    def test_sequence_loading(self, test_setup):
        """Test loading sequence and waveforms to AWG520."""
        awg520 = test_setup['awg520']
        seq_file = test_setup['seq_file']
        test_dir = test_setup['test_dir']
        
        # Load sequence file
        awg520.load_sequence_file(seq_file)
        
        # Load waveform files
        for wfm_file in test_dir.glob("*.wfm"):
            awg520.load_waveform_file(wfm_file)
        
        print("✅ Sequence and waveforms loaded to AWG520")
    
    def test_trigger_sequence_execution(self, test_setup):
        """Test the complete trigger sequence execution."""
        adwin = test_setup['adwin']
        awg520 = test_setup['awg520']
        
        # Start ADwin process
        adwin.start_process(1)
        time.sleep(0.1)
        
        # Start AWG520 sequence
        awg520.run()
        
        # Monitor progress
        print("  📊 Monitoring trigger sequence...")
        for i in range(10):  # Monitor for up to 10 seconds
            time.sleep(1)
            
            trigger_count = adwin.get_parameter(1)
            current_state = adwin.get_parameter(5)
            
            print(f"    Trigger {trigger_count}/4, State: {current_state}")
            
            if trigger_count >= 4:
                print("  ✅ All triggers completed!")
                break
        
        # Verify completion
        final_trigger_count = adwin.get_parameter(1)
        assert final_trigger_count >= 4, "Should complete at least 4 triggers"
        
        # Stop hardware
        awg520.stop()
        adwin.stop_process(1)
        
        print("✅ Trigger sequence execution completed successfully")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
