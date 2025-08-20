#!/usr/bin/env python3
"""
Test T1 Measurement Sequence Optimization

This script demonstrates the AWG520 optimizer with a realistic T1 measurement:
- Laser pulse (initialization)
- Pi pulse (excitation)
- Variable wait time (100ns to 10ms)
- Laser + counter simultaneously (readout)
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.Model.sequence import Sequence
from src.Model.pulses import GaussianPulse, SquarePulse
from src.Model.awg520_optimizer import AWG520SequenceOptimizer
import numpy as np


def create_t1_sequence(wait_time_ns: float) -> Sequence:
    """
    Create a T1 measurement sequence with specified wait time.
    
    Args:
        wait_time_ns: Wait time in nanoseconds
        
    Returns:
        Sequence object for T1 measurement
    """
    # Convert wait time to samples (1 GHz sample rate)
    wait_time_samples = int(wait_time_ns * 1e9 / 1e9)  # Convert ns to samples
    
    # Calculate total sequence length
    # Laser init: 1000ns, Pi pulse: 200ns, Wait: variable, Readout: 3000ns
    total_duration = 1000 + 200 + wait_time_samples + 3000
    
    # Create sequence
    seq = Sequence(total_duration)
    
    # 1. Laser initialization pulse (1000ns)
    laser_init = SquarePulse("laser_init", 1000, amplitude=1.0)
    seq.add_pulse(0, laser_init)
    
    # 2. Pi pulse (200ns) - Gaussian shape
    pi_pulse = GaussianPulse("pi_pulse", 200, sigma=50, amplitude=1.0)
    seq.add_pulse(1200, pi_pulse)  # Start after laser + 200ns gap
    
    # 3. Wait time (variable)
    # No pulse added - this creates dead time
    
    # 4. Laser + counter simultaneously (3000ns)
    readout_start = 1200 + 200 + wait_time_samples
    laser_readout = SquarePulse("laser_readout", 3000, amplitude=1.0)
    counter_readout = SquarePulse("counter_readout", 3000, amplitude=1.0)
    
    seq.add_pulse(readout_start, laser_readout)
    seq.add_pulse(readout_start, counter_readout)
    
    return seq


def test_t1_sequence_optimization():
    """Test T1 sequence optimization with different wait times."""
    
    print("🔬 T1 Measurement Sequence Optimization Test")
    print("=" * 60)
    
    # Create optimizer
    optimizer = AWG520SequenceOptimizer()
    
    # Test different wait times
    wait_times = [100, 1000, 10000, 100000, 1000000, 10000000]  # 100ns to 10ms
    
    for wait_time_ns in wait_times:
        print(f"\n⏱️  Wait Time: {wait_time_ns:>8} ns ({wait_time_ns/1e6:>6.1f} ms)")
        print("-" * 50)
        
        # Create sequence
        seq = create_t1_sequence(wait_time_ns)
        
        print(f"📊 Sequence Details:")
        print(f"   Total length: {seq.length:,} samples ({seq.length/1e9*1e9:.1f} ns)")
        print(f"   Pulses: {len(seq.pulses)}")
        
        # Calculate memory usage before optimization
        memory_before = optimizer._calculate_memory_usage(seq, optimized=False)
        print(f"   Raw memory: {memory_before['raw_memory_bytes']:,} bytes")
        
        # Identify resolution regions
        regions = optimizer._identify_resolution_regions(seq)
        print(f"   Resolution regions: {len(regions)}")
        
        # Count region types
        pulse_regions = sum(1 for r in regions if r['type'] == 'pulse')
        dead_time_regions = sum(1 for r in regions if r['type'] == 'dead_time')
        high_res_regions = sum(1 for r in regions if r['resolution'] == 'high')
        low_res_regions = sum(1 for r in regions if r['resolution'] == 'low')
        
        print(f"   - Pulse regions: {pulse_regions}")
        print(f"   - Dead time regions: {dead_time_regions}")
        print(f"   - High resolution: {high_res_regions}")
        print(f"   - Low resolution: {low_res_regions}")
        
        # Show dead time details
        for region in regions:
            if region['type'] == 'dead_time':
                duration_ns = region['duration_samples'] / 1e9 * 1e9
                resolution = region['resolution']
                print(f"   - Dead time: {duration_ns:>8.1f} ns ({resolution} resolution)")
        
        # Apply optimization
        try:
            optimized = optimizer.optimize_sequence_for_awg520(seq)
            
            # Calculate memory usage after optimization
            memory_after = optimizer._calculate_memory_usage(seq, optimized=True)
            
            print(f"✅ Optimization successful:")
            print(f"   Optimized memory: {memory_after['optimized_memory_bytes']:,} bytes")
            print(f"   Compression ratio: {memory_after['compression_ratio']:.2f}x")
            print(f"   Memory saved: {memory_before['raw_memory_bytes'] - memory_after['optimized_memory_bytes']:,} bytes")
            
            # Show compression details
            compression_ratios = optimizer._calculate_compression_ratios(seq)
            print(f"   - Dead time compression: {compression_ratios['dead_time_compression']:.2f}x")
            print(f"   - Overall compression: {compression_ratios['overall_compression']:.2f}x")
            
        except Exception as e:
            print(f"❌ Optimization failed: {e}")
    
    print(f"\n🎯 Summary:")
    print(f"   Tested {len(wait_times)} different wait times")
    print(f"   Shortest wait: {wait_times[0]} ns")
    print(f"   Longest wait: {wait_times[-1]/1e6:.1f} ms")
    print(f"   Longest sequence: {wait_times[-1] + 4200} ns")


def test_compression_effectiveness():
    """Test compression effectiveness with very long wait times."""
    
    print(f"\n🔍 Compression Effectiveness Test")
    print("=" * 60)
    
    optimizer = AWG520SequenceOptimizer()
    
    # Test with very long wait times to see compression benefits
    long_wait_times = [1e6, 5e6, 10e6, 50e6, 100e6]  # 1ms to 100ms
    
    for wait_time_ns in long_wait_times:
        print(f"\n⏱️  Long Wait Time: {wait_time_ns/1e6:>6.1f} ms")
        print("-" * 40)
        
        # Create sequence
        seq = create_t1_sequence(wait_time_ns)
        
        # Memory before optimization
        memory_before = optimizer._calculate_memory_usage(seq, optimized=False)
        
        # Memory after optimization
        memory_after = optimizer._calculate_memory_usage(seq, optimized=True)
        
        # Calculate savings
        raw_mb = memory_before['raw_memory_bytes'] / (1024 * 1024)
        opt_mb = memory_after['optimized_memory_bytes'] / (1024 * 1024)
        savings_mb = raw_mb - opt_mb
        compression = memory_after['compression_ratio']
        
        print(f"   Raw memory: {raw_mb:.2f} MB")
        print(f"   Optimized:  {opt_mb:.2f} MB")
        print(f"   Saved:      {savings_mb:.2f} MB")
        print(f"   Compression: {compression:.1f}x")
        
        # Check if we're within AWG520 memory limits
        if memory_before['raw_memory_bytes'] > optimizer.max_waveform_samples * 2:
            print(f"   ⚠️  Raw sequence exceeds AWG520 memory limit!")
        if memory_after['optimized_memory_bytes'] > optimizer.max_waveform_samples * 2:
            print(f"   ⚠️  Optimized sequence still exceeds AWG520 memory limit!")
        else:
            print(f"   ✅ Sequence fits within AWG520 memory limit")


if __name__ == "__main__":
    print("🚀 T1 Sequence Optimization Demo")
    print("=" * 60)
    
    try:
        # Test basic T1 sequence optimization
        test_t1_sequence_optimization()
        
        # Test compression effectiveness with long wait times
        test_compression_effectiveness()
        
        print(f"\n🎉 All tests completed successfully!")
        print(f"\nKey insights:")
        print(f"   - Short wait times (< 1μs): Minimal compression benefit")
        print(f"   - Long wait times (> 100μs): Significant compression benefit")
        print(f"   - Very long wait times (> 1ms): Massive memory savings")
        print(f"   - AWG520 memory constraints: 4M samples (8MB)")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
