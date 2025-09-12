#!/usr/bin/env python3
"""
Debug script to test matplotlib display.
"""

import matplotlib
print(f"Matplotlib backend: {matplotlib.get_backend()}")
print(f"Matplotlib version: {matplotlib.__version__}")

import matplotlib.pyplot as plt
import numpy as np

print("Creating simple test plot...")

# Create a simple plot
x = np.linspace(0, 10, 100)
y = np.sin(x)

fig, ax = plt.subplots(figsize=(8, 6))
ax.plot(x, y, 'b-', linewidth=2, label='sin(x)')
ax.set_xlabel('x')
ax.set_ylabel('y')
ax.set_title('Simple Test Plot')
ax.legend()
ax.grid(True)

print("Plot created. Attempting to show...")

# Try different ways to display
try:
    plt.show(block=True)  # This should block until window is closed
    print("✓ plt.show(block=True) worked")
except Exception as e:
    print(f"❌ plt.show(block=True) failed: {e}")

try:
    plt.show()  # Non-blocking
    print("✓ plt.show() worked")
except Exception as e:
    print(f"❌ plt.show() failed: {e}")

try:
    fig.show()  # Figure-specific show
    print("✓ fig.show() worked")
except Exception as e:
    print(f"❌ fig.show() failed: {e}")

print("If you still don't see plots, try:")
print("1. Check if plot windows are minimized or behind other windows")
print("2. Try switching to a different matplotlib backend")
print("3. Check your display environment")

# Keep the script running to see if plots appear
input("Press Enter to close plots and exit...")
plt.close(fig)
print("Script finished.")
