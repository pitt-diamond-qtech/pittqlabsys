#!/usr/bin/env python3
"""
Visualize T1 Sequence Compression Results

This script creates bar graphs showing the compression effectiveness
for different wait times in T1 measurement sequences.
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
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches


def create_t1_sequence(wait_time_ns: float) -> Sequence:
    """Create a T1 measurement sequence with specified wait time."""
    wait_time_samples = int(wait_time_ns * 1e9 / 1e9)
    total_duration = 1000 + 200 + wait_time_samples + 3000
    
    seq = Sequence(total_duration)
    
    # Laser initialization pulse (1000ns)
    laser_init = SquarePulse("laser_init", 1000, amplitude=1.0)
    seq.add_pulse(0, laser_init)
    
    # Pi pulse (200ns) - Gaussian shape
    pi_pulse = GaussianPulse("pi_pulse", 200, sigma=50, amplitude=1.0)
    seq.add_pulse(1200, pi_pulse)
    
    # Laser + counter simultaneously (3000ns)
    readout_start = 1200 + 200 + wait_time_samples
    laser_readout = SquarePulse("laser_readout", 3000, amplitude=1.0)
    counter_readout = SquarePulse("counter_readout", 3000, amplitude=1.0)
    
    seq.add_pulse(readout_start, laser_readout)
    seq.add_pulse(readout_start, counter_readout)
    
    return seq


def collect_compression_data():
    """Collect compression data for different wait times."""
    
    optimizer = AWG520SequenceOptimizer()
    
    # Test wait times from 100ns to 100ms
    wait_times_ns = np.logspace(2, 8, 20)  # 100ns to 100ms, 20 points
    
    data = {
        'wait_times_ns': wait_times_ns,
        'raw_memory_mb': [],
        'optimized_memory_mb': [],
        'compression_ratios': [],
        'memory_saved_mb': [],
        'fits_in_awg': []
    }
    
    print("📊 Collecting compression data...")
    
    for i, wait_time in enumerate(wait_times_ns):
        if i % 5 == 0:
            print(f"   Processing {i+1}/{len(wait_times_ns)}: {wait_time/1e6:.1f} ms")
        
        # Create sequence
        seq = create_t1_sequence(wait_time)
        
        # Calculate memory usage
        memory_before = optimizer._calculate_memory_usage(seq, optimized=False)
        memory_after = optimizer._calculate_memory_usage(seq, optimized=True)
        
        # Store data
        data['raw_memory_mb'].append(memory_before['raw_memory_bytes'] / (1024 * 1024))
        data['optimized_memory_mb'].append(memory_after['optimized_memory_bytes'] / (1024 * 1024))
        data['compression_ratios'].append(memory_after['compression_ratio'])
        data['memory_saved_mb'].append(
            (memory_before['raw_memory_bytes'] - memory_after['optimized_memory_bytes']) / (1024 * 1024)
        )
        data['fits_in_awg'].append(memory_after['optimized_memory_bytes'] <= optimizer.max_waveform_samples * 2)
    
    return data


def create_compression_plots(data):
    """Create comprehensive compression visualization plots."""
    
    wait_times_ms = data['wait_times_ns'] / 1e6
    
    # Create figure with subplots
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('T1 Sequence Compression Analysis', fontsize=16, fontweight='bold')
    
    # Plot 1: Memory Usage Comparison
    ax1.plot(wait_times_ms, data['raw_memory_mb'], 'r-', linewidth=2, label='Raw Memory', marker='o')
    ax1.plot(wait_times_ms, data['optimized_memory_mb'], 'g-', linewidth=2, label='Optimized Memory', marker='s')
    ax1.axhline(y=8, color='orange', linestyle='--', linewidth=2, label='AWG520 Limit (8MB)')
    ax1.set_xlabel('Wait Time (ms)')
    ax1.set_ylabel('Memory Usage (MB)')
    ax1.set_title('Memory Usage vs Wait Time')
    ax1.set_xscale('log')
    ax1.set_yscale('log')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Compression Ratio
    ax2.plot(wait_times_ms, data['compression_ratios'], 'b-', linewidth=2, marker='o')
    ax2.set_xlabel('Wait Time (ms)')
    ax2.set_ylabel('Compression Ratio')
    ax2.set_title('Compression Ratio vs Wait Time')
    ax2.set_xscale('log')
    ax2.set_yscale('log')
    ax2.grid(True, alpha=0.3)
    
    # Plot 3: Memory Saved
    ax3.bar(wait_times_ms, data['memory_saved_mb'], alpha=0.7, color='lightgreen', edgecolor='green')
    ax3.set_xlabel('Wait Time (ms)')
    ax3.set_ylabel('Memory Saved (MB)')
    ax3.set_title('Memory Savings vs Wait Time')
    ax3.set_xscale('log')
    ax3.grid(True, alpha=0.3)
    
    # Plot 4: Compression Effectiveness Heatmap
    # Create a scatter plot showing compression effectiveness
    colors = ['green' if fits else 'red' for fits in data['fits_in_awg']]
    sizes = [50 if ratio > 10 else 20 for ratio in data['compression_ratios']]
    
    scatter = ax4.scatter(wait_times_ms, data['compression_ratios'], 
                          c=colors, s=sizes, alpha=0.7, edgecolors='black')
    ax4.set_xlabel('Wait Time (ms)')
    ax4.set_ylabel('Compression Ratio')
    ax4.set_title('Compression Effectiveness')
    ax4.set_xscale('log')
    ax4.set_yscale('log')
    ax4.grid(True, alpha=0.3)
    
    # Add legend for colors
    green_patch = mpatches.Patch(color='green', label='Fits in AWG520')
    red_patch = mpatches.Patch(color='red', label='Exceeds AWG520')
    ax4.legend(handles=[green_patch, red_patch])
    
    plt.tight_layout()
    return fig


def create_detailed_analysis_plot(data):
    """Create a detailed analysis plot showing specific wait time ranges."""
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    wait_times_ms = data['wait_times_ns'] / 1e6
    
    # Plot 1: Short wait times (0.1ms to 1ms)
    short_mask = (wait_times_ms >= 0.1) & (wait_times_ms <= 1.0)
    if np.any(short_mask):
        short_indices = np.where(short_mask)[0]
        ax1.plot(wait_times_ms[short_indices], [data['raw_memory_mb'][i] for i in short_indices], 
                'r-o', linewidth=2, label='Raw Memory', markersize=8)
        ax1.plot(wait_times_ms[short_indices], [data['optimized_memory_mb'][i] for i in short_indices], 
                'g-s', linewidth=2, label='Optimized Memory', markersize=8)
        ax1.set_xlabel('Wait Time (ms)')
        ax1.set_ylabel('Memory Usage (MB)')
        ax1.set_title('Short Wait Times: 0.1ms - 1ms')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
    
    # Plot 2: Long wait times (1ms to 100ms)
    long_mask = (wait_times_ms >= 1.0) & (wait_times_ms <= 100.0)
    if np.any(long_mask):
        long_indices = np.where(long_mask)[0]
        ax2.plot(wait_times_ms[long_indices], [data['raw_memory_mb'][i] for i in long_indices], 
                'r-o', linewidth=2, label='Raw Memory', markersize=8)
        ax2.plot(wait_times_ms[long_indices], [data['optimized_memory_mb'][i] for i in long_indices], 
                'g-s', linewidth=2, label='Optimized Memory', markersize=8)
        ax2.axhline(y=8, color='orange', linestyle='--', linewidth=2, label='AWG520 Limit (8MB)')
        ax2.set_xlabel('Wait Time (ms)')
        ax2.set_ylabel('Memory Usage (MB)')
        ax2.set_title('Long Wait Times: 1ms - 100ms')
        ax2.set_xscale('log')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    return fig


def print_compression_summary(data):
    """Print a summary of compression results."""
    
    wait_times_ms = data['wait_times_ns'] / 1e6
    
    print("\n📊 Compression Summary")
    print("=" * 60)
    
    # Find key transition points
    compression_ratios = np.array(data['compression_ratios'])
    
    # Find where compression becomes significant (>2x)
    significant_compression = wait_times_ms[compression_ratios > 2]
    if len(significant_compression) > 0:
        print(f"🎯 Significant compression (>2x) starts at: {significant_compression[0]:.3f} ms")
    
    # Find where compression becomes massive (>10x)
    massive_compression = wait_times_ms[compression_ratios > 10]
    if len(massive_compression) > 0:
        print(f"🚀 Massive compression (>10x) starts at: {massive_compression[0]:.3f} ms")
    
    # Find where raw sequence exceeds AWG520 limit
    exceeds_limit = wait_times_ms[np.array(data['raw_memory_mb']) > 8]
    if len(exceeds_limit) > 0:
        print(f"⚠️  Raw sequence exceeds AWG520 limit at: {exceeds_limit[0]:.3f} ms")
    
    # Find where optimized sequence fits in AWG520
    fits_in_awg = wait_times_ms[np.array(data['fits_in_awg'])]
    if len(fits_in_awg) > 0:
        print(f"✅ Optimized sequence fits in AWG520 up to: {fits_in_awg[-1]:.1f} ms")
    
    # Show some specific examples
    print(f"\n📈 Example Compression Ratios:")
    example_indices = [0, 5, 10, 15, 19]  # Show 5 examples across the range
    for idx in example_indices:
        if idx < len(wait_times_ms):
            wait_ms = wait_times_ms[idx]
            ratio = compression_ratios[idx]
            raw_mb = data['raw_memory_mb'][idx]
            opt_mb = data['optimized_memory_mb'][idx]
            print(f"   {wait_ms:>6.3f} ms: {ratio:>6.1f}x compression, {raw_mb:>5.2f} MB → {opt_mb:>5.2f} MB")


def main():
    """Main function to run the compression visualization."""
    
    print("🚀 T1 Sequence Compression Visualization")
    print("=" * 60)
    
    try:
        # Collect compression data
        data = collect_compression_data()
        
        # Create plots
        print("\n📊 Creating compression plots...")
        
        # Main compression plots
        fig1 = create_compression_plots(data)
        fig1.savefig('t1_compression_analysis.png', dpi=300, bbox_inches='tight')
        print("   ✅ Saved: t1_compression_analysis.png")
        
        # Detailed analysis plots
        fig2 = create_detailed_analysis_plot(data)
        fig2.savefig('t1_detailed_analysis.png', dpi=300, bbox_inches='tight')
        print("   ✅ Saved: t1_detailed_analysis.png")
        
        # Print summary
        print_compression_summary(data)
        
        # Show plots
        plt.show()
        
        print(f"\n🎉 Visualization completed successfully!")
        print(f"   Generated 2 PNG files with comprehensive compression analysis")
        
    except Exception as e:
        print(f"❌ Visualization failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
