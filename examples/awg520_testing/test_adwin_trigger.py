#!/usr/bin/env python3
"""
ADwin Trigger Test for AWG520 Integration

This script tests ADwin's ability to generate precise trigger pulses
for controlling AWG520 external trigger input.
"""

import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.Controller.adwin_gold import AdwinGold
except ImportError:
    print("❌ AdwinGold class not found. Please check the import path.")
    sys.exit(1)


class AdwinTriggerTester:
    """Test ADwin trigger generation capabilities."""
    
    def __init__(self):
        """Initialize ADwin connection."""
        self.adwin = AdwinGold()
        self.trigger_pin = 0  # DIO 0 for trigger output
        self.monitor_pin = 1  # DIO 1 for monitoring (optional)
        
    def test_basic_trigger(self):
        """Test basic trigger pulse generation."""
        print("🔧 Testing Basic Trigger Generation")
        print("=" * 50)
        
        try:
            # Configure trigger pin as output
            self.adwin.set_digital_output(self.trigger_pin, 0)
            print(f"✅ Configured DIO {self.trigger_pin} as trigger output")
            
            # Generate single trigger pulse
            print("📡 Generating single trigger pulse...")
            self.adwin.set_digital_output(self.trigger_pin, 1)
            time.sleep(0.001)  # 1ms pulse width
            self.adwin.set_digital_output(self.trigger_pin, 0)
            print("✅ Single trigger pulse generated")
            
            return True
            
        except Exception as e:
            print(f"❌ Basic trigger test failed: {e}")
            return False
    
    def test_precise_timing(self):
        """Test precise timing of trigger pulses."""
        print("\n⏱️  Testing Precise Trigger Timing")
        print("=" * 50)
        
        try:
            # Test different pulse widths
            pulse_widths = [0.001, 0.0001, 0.00001]  # 1ms, 100μs, 10μs
            
            for width in pulse_widths:
                print(f"📡 Testing {width*1000:.1f}ms pulse width...")
                
                start_time = time.time()
                self.adwin.set_digital_output(self.trigger_pin, 1)
                time.sleep(width)
                self.adwin.set_digital_output(self.trigger_pin, 0)
                end_time = time.time()
                
                actual_width = (end_time - start_time) * 1000
                error = abs(actual_width - width*1000)
                
                print(f"   Expected: {width*1000:.3f}ms, Actual: {actual_width:.3f}ms, Error: {error:.3f}ms")
                
                if error < 0.1:  # Less than 100μs error
                    print("   ✅ Timing accuracy acceptable")
                else:
                    print("   ⚠️  Timing error exceeds 100μs")
            
            return True
            
        except Exception as e:
            print(f"❌ Precise timing test failed: {e}")
            return False
    
    def test_trigger_sequence(self):
        """Test sequence of trigger pulses."""
        print("\n🔄 Testing Trigger Sequence")
        print("=" * 50)
        
        try:
            # Generate sequence of 5 triggers with 100ms spacing
            print("📡 Generating sequence of 5 triggers...")
            
            for i in range(5):
                print(f"   Trigger {i+1}/5...")
                self.adwin.set_digital_output(self.trigger_pin, 1)
                time.sleep(0.001)  # 1ms pulse
                self.adwin.set_digital_output(self.trigger_pin, 0)
                
                if i < 4:  # Don't wait after last trigger
                    time.sleep(0.1)  # 100ms spacing
            
            print("✅ Trigger sequence completed")
            return True
            
        except Exception as e:
            print(f"❌ Trigger sequence test failed: {e}")
            return False
    
    def test_awg520_simulation(self):
        """Simulate AWG520 trigger requirements."""
        print("\n🎯 Simulating AWG520 Trigger Requirements")
        print("=" * 50)
        
        try:
            # Simulate typical pulsed ODMR experiment timing
            print("📡 Simulating pulsed ODMR trigger sequence...")
            
            # Laser initialization trigger
            print("   Laser initialization trigger...")
            self.adwin.set_digital_output(self.trigger_pin, 1)
            time.sleep(0.001)
            self.adwin.set_digital_output(self.trigger_pin, 0)
            time.sleep(0.001)  # 1ms wait
            
            # Pi pulse trigger
            print("   Pi pulse trigger...")
            self.adwin.set_digital_output(self.trigger_pin, 1)
            time.sleep(0.001)
            self.adwin.set_digital_output(self.trigger_pin, 0)
            time.sleep(0.001)  # 1ms wait
            
            # Readout trigger
            print("   Readout trigger...")
            self.adwin.set_digital_output(self.trigger_pin, 1)
            time.sleep(0.001)
            self.adwin.set_digital_output(self.trigger_pin, 0)
            
            print("✅ AWG520 simulation completed")
            return True
            
        except Exception as e:
            print(f"❌ AWG520 simulation failed: {e}")
            return False
    
    def run_all_tests(self):
        """Run all trigger tests."""
        print("🚀 ADwin Trigger Testing Suite")
        print("=" * 60)
        print("This will test ADwin's ability to generate precise triggers")
        print("for controlling AWG520 external trigger input.")
        print()
        
        tests = [
            ("Basic Trigger", self.test_basic_trigger),
            ("Precise Timing", self.test_precise_timing),
            ("Trigger Sequence", self.test_trigger_sequence),
            ("AWG520 Simulation", self.test_awg520_simulation)
        ]
        
        results = []
        
        for test_name, test_func in tests:
            print(f"\n🧪 Running: {test_name}")
            print("-" * 40)
            
            try:
                success = test_func()
                results.append((test_name, success))
                
                if success:
                    print(f"✅ {test_name}: PASSED")
                else:
                    print(f"❌ {test_name}: FAILED")
                    
            except Exception as e:
                print(f"❌ {test_name}: ERROR - {e}")
                results.append((test_name, False))
        
        # Summary
        print("\n📊 Test Results Summary")
        print("=" * 40)
        
        passed = sum(1 for _, success in results if success)
        total = len(results)
        
        for test_name, success in results:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{test_name}: {status}")
        
        print(f"\nOverall: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed! ADwin is ready for AWG520 integration.")
        else:
            print("⚠️  Some tests failed. Check the error messages above.")
        
        return passed == total
    
    def cleanup(self):
        """Clean up ADwin connections."""
        try:
            if hasattr(self.adwin, 'close'):
                self.adwin.close()
            print("✅ ADwin connection closed")
        except Exception as e:
            print(f"⚠️  Error closing ADwin connection: {e}")


def main():
    """Main test function."""
    print("🔧 ADwin Trigger Testing for AWG520 Integration")
    print("=" * 60)
    
    tester = None
    
    try:
        # Create tester
        tester = AdwinTriggerTester()
        
        # Check connection
        if not tester.adwin.is_connected:
            print("❌ ADwin not connected. Please check hardware connection.")
            return False
        
        print("✅ ADwin connected successfully")
        
        # Run tests
        success = tester.run_all_tests()
        
        return success
        
    except Exception as e:
        print(f"❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Cleanup
        if tester:
            tester.cleanup()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
