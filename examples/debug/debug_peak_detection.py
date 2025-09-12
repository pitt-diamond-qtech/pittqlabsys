#!/usr/bin/env python3
"""
Debug script to visualize the peak detection issue in the ODMR sweep experiment.
"""

import numpy as np
import matplotlib.pyplot as plt
from src.Model.experiments.odmr_sweep_enhanced import EnhancedODMRSweepExperiment
from unittest.mock import MagicMock

def create_test_data():
    """Create the same test data as in the test, but with a dip instead of a peak."""
    frequencies = np.linspace(2.8e9, 2.9e9, 100)
    center_freq = 2.85e9
    width = 10e6  # 10 MHz

    # Create Lorentzian dip (ODMR typically shows a dip in fluorescence at resonance)
    # Start with high background fluorescence, then subtract the Lorentzian
    background = 1000  # High fluorescence background
    dip_amplitude = 800  # Depth of the dip
    data = background - dip_amplitude / (1 + ((frequencies - center_freq) / (width/2))**2)
    
    return frequencies, data

def analyze_peak_detection(frequencies, data):
    """Analyze the peak detection logic step by step."""
    # Create a mock experiment instance
    mock_microwave = MagicMock()
    mock_adwin = MagicMock()
    
    devices = {
        'microwave': {'instance': mock_microwave},
        'adwin': {'instance': mock_adwin}
    }
    
    experiment = EnhancedODMRSweepExperiment(devices)
    
    # Set the same parameters as in the test
    experiment.settings['analysis']['contrast_factor'] = 1.1
    experiment.settings['analysis']['minimum_counts'] = 0.5
    
    # Calculate the same values as the peak detection algorithm
    mean_data = np.mean(data)
    threshold = mean_data * experiment.settings['analysis']['contrast_factor']
    min_counts = experiment.settings['analysis']['minimum_counts']
    
    print(f"Analysis parameters:")
    print(f"  mean_data = {mean_data:.1f}")
    print(f"  contrast_factor = {experiment.settings['analysis']['contrast_factor']}")
    print(f"  threshold = {threshold:.1f}")
    print(f"  min_counts = {min_counts}")
    print(f"  max_data = {np.max(data):.1f}")
    print(f"  min_data = {np.min(data):.1f}")
    
    # Check each point for dip detection criteria (looking for local minima)
    dips_found = []
    for i in range(1, len(data) - 1):
        # For dips, we want to find local minima that are below the threshold
        # and above the minimum counts
        below_threshold = data[i] < threshold
        above_min_counts = data[i] > min_counts
        local_min = data[i] < data[i-1] and data[i] < data[i+1]
        
        if below_threshold and above_min_counts and local_min:
            dips_found.append(i)
            print(f"  Dip found at index {i}: freq={frequencies[i]/1e9:.3f} GHz, value={data[i]:.1f}")
    
    print(f"  Total dips found: {len(dips_found)}")
    
    return dips_found

def plot_data(frequencies, data, dips_found):
    """Plot the data with peak detection visualization."""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
    
    # Calculate analysis parameters
    mean_data = np.mean(data)
    threshold = mean_data * 1.1  # contrast_factor = 1.1
    min_counts = 0.5
    
    # Plot 1: Full data with thresholds
    ax1.plot(frequencies / 1e9, data, 'b-', linewidth=2, label='ODMR Data')
    ax1.axhline(y=threshold, color='r', linestyle='--', label=f'Threshold ({threshold:.1f})')
    ax1.axhline(y=mean_data, color='g', linestyle='--', label=f'Mean ({mean_data:.1f})')
    ax1.axhline(y=min_counts, color='orange', linestyle='--', label=f'Min Counts ({min_counts})')
    
    # Mark found dips
    if dips_found:
        dip_freqs = frequencies[dips_found] / 1e9
        dip_values = data[dips_found]
        ax1.plot(dip_freqs, dip_values, 'ro', markersize=10, label=f'Detected Dips ({len(dips_found)})')
    
    ax1.set_xlabel('Frequency (GHz)')
    ax1.set_ylabel('Intensity')
    ax1.set_title('ODMR Data with Dip Detection Analysis')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Zoomed in around the dip
    center_idx = len(frequencies) // 2
    zoom_range = 20
    start_idx = max(0, center_idx - zoom_range)
    end_idx = min(len(frequencies), center_idx + zoom_range)
    
    ax2.plot(frequencies[start_idx:end_idx] / 1e9, data[start_idx:end_idx], 'b-', linewidth=2, label='ODMR Data')
    ax2.axhline(y=threshold, color='r', linestyle='--', label=f'Threshold ({threshold:.1f})')
    
    # Mark the minimum point
    min_idx = np.argmin(data)
    min_freq = frequencies[min_idx] / 1e9
    min_value = data[min_idx]
    ax2.plot(min_freq, min_value, 'go', markersize=10, label=f'Global Min ({min_value:.1f})')
    
    # Show the values around the minimum
    for i in range(max(0, min_idx-2), min(len(data), min_idx+3)):
        ax2.annotate(f'{data[i]:.1f}', 
                    (frequencies[i]/1e9, data[i]), 
                    textcoords="offset points", 
                    xytext=(0,10), 
                    ha='center',
                    fontsize=8)
    
    ax2.set_xlabel('Frequency (GHz)')
    ax2.set_ylabel('Intensity')
    ax2.set_title('Zoomed View Around Dip (showing discrete sampling issue)')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('dip_detection_debug.png', dpi=150, bbox_inches='tight')
    print("Plot saved as 'dip_detection_debug.png'")
    plt.show()

def main():
    """Main function to run the analysis."""
    print("=== ODMR Dip Detection Debug Analysis ===\n")
    
    # Create test data
    frequencies, data = create_test_data()
    
    # Analyze peak detection
    dips_found = analyze_peak_detection(frequencies, data)
    
    # Plot the data
    plot_data(frequencies, data, dips_found)
    
    print(f"\n=== Summary ===")
    print(f"The dip detection algorithm found {len(dips_found)} dips.")
    print(f"The issue is likely due to discrete sampling creating a flat top on the Lorentzian dip.")
    print(f"At the minimum point, the data has the same value for multiple consecutive points,")
    print(f"which violates the strict local minimum requirement (data[i] < data[i+1]).")

if __name__ == "__main__":
    main() 