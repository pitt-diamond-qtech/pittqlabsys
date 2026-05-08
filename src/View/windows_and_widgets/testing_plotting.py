from src.core.struct_hdf5 import load_data
import numpy as np
import matplotlib.pyplot as plt

print("start")
path = "odmr_pulsed_output_05_04_2026_20_27_41.h5"
if not path:
    print("File does not exist")
structure = load_data(path)
print(f"structure loaded successfully")

# Extract the data
signal_counts = structure.data.signal_counts[0]  # First row (shape is 1x20)
reference_counts = structure.data.reference_counts[0]  # First row
total_counts = structure.data.total_counts[0]  # First row

# Extract metadata for wait times
sequence_duration = structure.meta.sequence_duration
number_of_iterations = structure.meta.number_of_iterations

# Calculate wait times
# Based on the sequence_text, the pulse_duration varies
wait_times_ns = np.linspace(0, 15000000, number_of_iterations)

# Calculate the Change: (100*(signal - reference))/reference
# This represents the percentage change relative to the reference
Change = 100 * (signal_counts - reference_counts) / reference_counts

print("\nData summary:")
print(f"Signal counts: {signal_counts}")
print(f"Reference counts: {reference_counts}")
print(f"Change (%): {Change}")
print(f"Wait times (ns): {wait_times_ns}")

# Print additional information from metadata
print(f"\nExperiment metadata:")
print(f"Start time: {structure.meta.start_time}")
print(f"End time: {structure.meta.end_time}")
print(f"Sequence duration: {structure.meta.sequence_duration} ns")
print(f"Number of iterations: {structure.meta.number_of_iterations}")
print(f"Count time: {structure.meta.count_time} ns")
print(f"Microwave power: {structure.meta.microwave_power} dBm")
print(f"MW delay: {structure.meta.mw_delay} ns")
print(f"Green laser delay: {structure.meta.green_laser_delay} ns")
print(f"Green laser power: {structure.meta.green_laser_power} W")
print(f"Green laser wavelength: {structure.meta.green_laser_wavelength} nm")
print(f"Frequency range: {structure.meta.frequency_range[0]} Hz")

plt.figure(figsize=(12, 5))

# Subplot 1: Raw counts
plt.subplot(1, 2, 1)
plt.plot(wait_times_ns, signal_counts, 'r-', label='Signal', linewidth=2)
plt.plot(wait_times_ns, reference_counts, 'b-', label='Reference', linewidth=2)
plt.xlabel('Wait Time (ns)')
plt.ylabel('Counts')
plt.title('Raw Signal and Reference Counts')
plt.legend()
plt.grid(True, alpha=0.3)

# Subplot 2: Change
plt.subplot(1, 2, 2)
plt.plot(wait_times_ns, Change, 'g-', linewidth=2, markersize=6, marker='o')
plt.xlabel('Wait Time (ns)')
plt.ylabel('Change (%)')
plt.title('% Change VS Wait Time (ns)')
plt.grid(True, alpha=0.3)
plt.axhline(y=0, color='k', linestyle='--', linewidth=0.5, alpha=0.5)

plt.tight_layout()
plt.show()

# Print the data as a table for reference
print("\nDetailed data table:")
print("Wait Time (ns)\tSignal\tReference\tChange (%)")
print("-" * 60)
for wt, sig, ref, con in zip(wait_times_ns, signal_counts, reference_counts, Change):
    print(f"{wt:.0f}\t\t{sig}\t{ref}\t\t{con:.2f}")