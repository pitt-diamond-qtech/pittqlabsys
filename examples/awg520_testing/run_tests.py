#!/usr/bin/env python3
"""
AWG520 + ADwin Integration Test Runner

This script provides a simple interface to run both ADwin and AWG520 tests.
"""

import sys
import subprocess
from pathlib import Path

def run_adwin_tests():
    """Run ADwin trigger tests."""
    print("🧪 Running ADwin Trigger Tests")
    print("=" * 50)
    
    try:
        result = subprocess.run([
            sys.executable, "test_adwin_trigger.py"
        ], capture_output=True, text=True, cwd=Path(__file__).parent)
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ Failed to run ADwin tests: {e}")
        return False

def run_awg520_tests():
    """Run AWG520 test sequence generation."""
    print("\n🧪 Running AWG520 Test Generation")
    print("=" * 50)
    
    try:
        result = subprocess.run([
            sys.executable, "generate_test_sequences.py"
        ], capture_output=True, text=True, cwd=Path(__file__).parent)
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ Failed to run AWG520 tests: {e}")
        return False

def show_test_summary():
    """Show summary of what tests do."""
    print("📋 Test Summary")
    print("=" * 50)
    print("This test suite will:")
    print()
    print("1. 🧪 ADwin Trigger Tests")
    print("   • Test basic trigger generation")
    print("   • Verify precise timing accuracy")
    print("   • Test trigger sequences")
    print("   • Simulate AWG520 requirements")
    print()
    print("2. 🧪 AWG520 Test Generation")
    print("   • Create test waveform files (.wfm)")
    print("   • Generate test sequence files (.seq)")
    print("   • Analyze compression effectiveness")
    print("   • Create test instructions")
    print()
    print("3. 🔧 Hardware Setup Required")
    print("   • ADwin DIO output → AWG520 TRIG IN")
    print("   • 50Ω BNC cable connection")
    print("   • Ground connection between devices")
    print()

def main():
    """Main test runner."""
    print("🚀 AWG520 + ADwin Integration Test Runner")
    print("=" * 60)
    
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        show_test_summary()
        return
    
    if len(sys.argv) > 1 and sys.argv[1] == "--adwin-only":
        print("Running ADwin tests only...")
        success = run_adwin_tests()
        return success
    
    if len(sys.argv) > 1 and sys.argv[1] == "--awg520-only":
        print("Running AWG520 tests only...")
        success = run_awg520_tests()
        return success
    
    # Run both tests by default
    print("Running complete test suite...")
    print()
    
    adwin_success = run_adwin_tests()
    awg520_success = run_awg520_tests()
    
    # Summary
    print("\n📊 Test Results Summary")
    print("=" * 50)
    
    if adwin_success:
        print("✅ ADwin tests: PASSED")
    else:
        print("❌ ADwin tests: FAILED")
    
    if awg520_success:
        print("✅ AWG520 tests: PASSED")
    else:
        print("❌ AWG520 tests: FAILED")
    
    overall_success = adwin_success and awg520_success
    
    if overall_success:
        print("\n🎉 All tests passed!")
        print("\n📋 Next steps:")
        print("   1. Set up hardware connections (see docs/AWG520_ADWIN_TESTING.md)")
        print("   2. Configure AWG520 for external trigger")
        print("   3. Transfer test files to AWG520")
        print("   4. Test actual hardware integration")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
    
    return overall_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
