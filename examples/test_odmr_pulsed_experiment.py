#!/usr/bin/env python3
"""
Test script for ODMR Pulsed Experiment

This script tests the basic functionality of the ODMR Pulsed experiment
without requiring hardware connections.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.Model.experiments.odmr_pulsed import ODMRPulsedExperiment
    print("✅ ODMR Pulsed Experiment imported successfully")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)


def test_basic_functionality():
    """Test basic experiment functionality."""
    print("\n🧪 Testing Basic Functionality")
    print("=" * 40)
    
    # Create experiment
    experiment = ODMRPulsedExperiment()
    print("✅ Experiment created")
    
    # Set parameters
    experiment.set_microwave_parameters(2.87e9, -10.0, 25.0)
    experiment.set_laser_parameters(1.0, 532)
    experiment.set_delay_parameters(25.0, 50.0, 15.0)
    print("✅ Parameters set")
    
    # Get experiment summary
    summary = experiment.get_experiment_summary()
    print("✅ Experiment summary generated")
    
    print(f"\n📊 Experiment Summary:")
    print(f"   Name: {summary['name']}")
    print(f"   Microwave: {summary['microwave_frequency_ghz']:.3f} GHz, {summary['microwave_power_dbm']} dBm")
    print(f"   Laser: {summary['laser_power_mw']} mW, {summary['laser_wavelength_nm']} nm")
    print(f"   Delays: MW={summary['delays_ns']['mw']}ns, AOM={summary['delays_ns']['aom']}ns, Counter={summary['delays_ns']['counter']}ns")
    
    return True


def test_sequence_loading():
    """Test sequence loading functionality."""
    print("\n🧪 Testing Sequence Loading")
    print("=" * 40)
    
    # Create experiment
    experiment = ODMRPulsedExperiment()
    
    # Try to load the example sequence
    sequence_file = Path(__file__).parent / "odmr_pulsed_example_sequence.txt"
    
    if not sequence_file.exists():
        print(f"❌ Example sequence file not found: {sequence_file}")
        return False
    
    print(f"📁 Loading sequence from: {sequence_file}")
    
    # Load sequence
    if experiment.load_sequence_from_file(sequence_file):
        print("✅ Sequence loaded successfully")
        
        # Show sequence info
        desc = experiment.sequence_description
        print(f"   Sequence name: {desc.name}")
        print(f"   Variables: {len(desc.variables)}")
        print(f"   Pulses: {len(desc.pulses)}")
        print(f"   Sample rate: {desc.sample_rate}")
        print(f"   Repeat count: {desc.repeat_count}")
        
        # Show variables
        for var in desc.variables:
            print(f"   Variable: {var.name} = {var.start_value} to {var.stop_value} ({var.steps} steps)")
        
        # Show pulses
        for pulse in desc.pulses:
            print(f"   Pulse: {pulse.name} on channel {pulse.channel} at {pulse.start_time}")
        
        return True
    else:
        print("❌ Sequence loading failed")
        return False


def test_sequence_building():
    """Test sequence building functionality."""
    print("\n🧪 Testing Sequence Building")
    print("=" * 40)
    
    # Create experiment
    experiment = ODMRPulsedExperiment()
    
    # Load sequence first
    sequence_file = Path(__file__).parent / "odmr_pulsed_example_sequence.txt"
    if not experiment.load_sequence_from_file(sequence_file):
        print("❌ Cannot test building without loaded sequence")
        return False
    
    # Build scan sequences
    print("🔨 Building scan sequences...")
    if experiment.build_scan_sequences():
        print(f"✅ Built {len(experiment.scan_sequences)} scan sequences")
        
        # Show first sequence info
        if experiment.scan_sequences:
            first_seq = experiment.scan_sequences[0]
            print(f"   First sequence length: {first_seq.length} samples")
            print(f"   First sequence pulses: {len(first_seq.pulses)}")
            
            # Show pulse details
            for start_sample, pulse in first_seq.pulses[:3]:  # Show first 3 pulses
                print(f"     Pulse: {pulse.name} at {start_sample} samples, length {pulse.length}")
        
        return True
    else:
        print("❌ Sequence building failed")
        return False


def test_awg_file_generation():
    """Test AWG file generation."""
    print("\n🧪 Testing AWG File Generation")
    print("=" * 40)
    
    # Create experiment
    experiment = ODMRPulsedExperiment()
    
    # Load and build sequences
    sequence_file = Path(__file__).parent / "odmr_pulsed_example_sequence.txt"
    if not experiment.load_sequence_from_file(sequence_file):
        print("❌ Cannot test AWG generation without loaded sequence")
        return False
    
    if not experiment.build_scan_sequences():
        print("❌ Cannot test AWG generation without built sequences")
        return False
    
    # Generate AWG files
    print("🔨 Generating AWG files...")
    if experiment.generate_awg_files():
        print("✅ AWG files generated successfully")
        
        # Check output directory
        output_dir = experiment.output_dir
        if output_dir.exists():
            wfm_files = list(output_dir.glob("*.wfm"))
            seq_files = list(output_dir.glob("*.seq"))
            
            print(f"   Waveform files: {len(wfm_files)}")
            print(f"   Sequence files: {len(seq_files)}")
            
            if wfm_files:
                print(f"   First waveform: {wfm_files[0].name}")
            if seq_files:
                print(f"   Sequence file: {seq_files[0].name}")
        
        return True
    else:
        print("❌ AWG file generation failed")
        return False


def run_all_tests():
    """Run all tests."""
    print("🚀 ODMR Pulsed Experiment Test Suite")
    print("=" * 60)
    
    tests = [
        ("Basic Functionality", test_basic_functionality),
        ("Sequence Loading", test_sequence_loading),
        ("Sequence Building", test_sequence_building),
        ("AWG File Generation", test_awg_file_generation)
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
            import traceback
            traceback.print_exc()
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
        print("🎉 All tests passed! ODMR Pulsed Experiment is ready to use.")
        print("\n📋 Next steps:")
        print("   1. Configure hardware parameters")
        print("   2. Load sequence files")
        print("   3. Run experiments")
        print("   4. Integrate with AWG520 and ADwin")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
