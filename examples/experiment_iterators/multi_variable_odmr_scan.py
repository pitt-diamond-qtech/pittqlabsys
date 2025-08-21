#!/usr/bin/env python3
"""
Multi-Variable ODMR Scan Example using ExperimentIterator

This example demonstrates how to create a 2D parameter sweep using the
ExperimentIterator factory pattern. The scan sweeps:
1. Pulse duration (inner loop): 100ns to 1000ns, 10 steps
2. Microwave frequency (outer loop): 2.8GHz to 2.9GHz, 20 steps

Total scan points: 10 × 20 = 200 combinations

This approach enables complex multi-dimensional scans without writing
new experiment classes, using the existing ExperimentIterator framework.
"""

import sys
import time
from pathlib import Path
import numpy as np

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.experiment_iterator import ExperimentIterator
from src.Model.experiments.odmr_pulsed import ODMRPulsedExperiment


class MultiVariableODMRScan:
    """
    Example class demonstrating how to create multi-variable scans
    using ExperimentIterator programmatically.
    """
    
    def __init__(self):
        """Initialize the multi-variable scan system."""
        self.inner_iterator_info = None
        self.outer_iterator_info = None
        self.experiment_instance = None
        
    def create_inner_iterator(self):
        """
        Create the inner iterator for pulse duration sweep.
        
        This iterator will sweep the pulse duration parameter of the
        ODMR Pulsed experiment from 100ns to 1000ns in 10 steps.
        """
        print("🔧 Creating inner iterator (pulse duration sweep)...")
        
        # Define the inner iterator configuration
        inner_config = {
            'name': 'Pulse_Duration_Sweep',
            'class': 'ExperimentIterator',
            'package': 'src.Model',
            'experiments': {
                'odmr_pulsed': ODMRPulsedExperiment
            },
            'settings': {
                'experiment_order': {'odmr_pulsed': 1},
                'experiment_execution_freq': {'odmr_pulsed': 1},
                'iterator_type': 'Parameter Sweep',
                'sweep_param': 'odmr_pulsed.sequence.pulse_duration',
                'sweep_range': {
                    'min_value': 100e-9,    # 100ns
                    'max_value': 1000e-9,   # 1000ns
                    'N/value_step': 10,     # 10 steps
                    'randomize': False
                },
                'stepping_mode': 'N'
            }
        }
        
        # Create the inner iterator class dynamically
        try:
            self.inner_iterator_info, _ = ExperimentIterator.create_dynamic_experiment_class(
                inner_config, verbose=True
            )
            print(f"✅ Inner iterator created: {self.inner_iterator_info['class']}")
            return True
        except Exception as e:
            print(f"❌ Failed to create inner iterator: {e}")
            return False
    
    def create_outer_iterator(self):
        """
        Create the outer iterator for frequency sweep.
        
        This iterator will sweep the microwave frequency parameter
        from 2.8GHz to 2.9GHz in 20 steps, and for each frequency
        it will run the inner iterator (pulse duration sweep).
        """
        print("🔧 Creating outer iterator (frequency sweep)...")
        
        if not self.inner_iterator_info:
            print("❌ Inner iterator must be created first")
            return False
        
        # Define the outer iterator configuration
        outer_config = {
            'name': 'Frequency_Pulse_2D_Scan',
            'class': 'ExperimentIterator',
            'package': 'src.Model',
            'experiments': {
                'pulse_duration_sweep': self.inner_iterator_info['class'],
                # You could add other experiments here, e.g., data collection
                # 'data_collection': DataCollectionExperiment
            },
            'settings': {
                'experiment_order': {
                    'pulse_duration_sweep': 1,
                    # 'data_collection': 2  # If you add more experiments
                },
                'experiment_execution_freq': {
                    'pulse_duration_sweep': 1,
                    # 'data_collection': 1
                },
                'iterator_type': 'Parameter Sweep',
                'sweep_param': 'pulse_duration_sweep.microwave.frequency',
                'sweep_range': {
                    'min_value': 2.8e9,     # 2.8 GHz
                    'max_value': 2.9e9,     # 2.9 GHz
                    'N/value_step': 20,     # 20 steps
                    'randomize': False
                },
                'stepping_mode': 'N'
            }
        }
        
        # Create the outer iterator class dynamically
        try:
            self.outer_iterator_info, _ = ExperimentIterator.create_dynamic_experiment_class(
                outer_config, verbose=True
            )
            print(f"✅ Outer iterator created: {self.outer_iterator_info['class']}")
            return True
        except Exception as e:
            print(f"❌ Failed to create outer iterator: {e}")
            return False
    
    def create_experiment_instance(self):
        """
        Create an instance of the multi-variable scan experiment.
        """
        print("🔧 Creating experiment instance...")
        
        if not self.outer_iterator_info:
            print("❌ Outer iterator must be created first")
            return False
        
        try:
            # Get the module containing the dynamically created class
            module_name = self.outer_iterator_info['class'].split('.')[0]
            class_name = self.outer_iterator_info['class'].split('.')[-1]
            
            # Import the module dynamically
            module = __import__(module_name)
            
            # Get the experiment class
            experiment_class = getattr(module, class_name)
            
            # Create an instance
            self.experiment_instance = experiment_class(
                name='2D_ODMR_Scan',
                settings={
                    'tag': '2D_ODMR_Scan',
                    'description': '2D scan: frequency × pulse duration'
                }
            )
            
            print(f"✅ Experiment instance created: {self.experiment_instance}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to create experiment instance: {e}")
            return False
    
    def run_scan(self, dry_run=True):
        """
        Run the multi-variable scan.
        
        Args:
            dry_run (bool): If True, only simulate the scan without running
                           actual experiments. Useful for testing configuration.
        """
        print("🚀 Running multi-variable scan...")
        
        if not self.experiment_instance:
            print("❌ Experiment instance must be created first")
            return False
        
        if dry_run:
            print("🔍 DRY RUN MODE - Simulating scan configuration...")
            self._simulate_scan()
        else:
            print("🔬 RUNNING ACTUAL SCAN - This will execute experiments...")
            try:
                # Run the experiment
                self.experiment_instance.run()
                print("✅ Scan completed successfully!")
                return True
            except Exception as e:
                print(f"❌ Scan failed: {e}")
                return False
    
    def _simulate_scan(self):
        """
        Simulate the scan to show what would happen without running
        actual experiments.
        """
        print("\n📊 Scan Configuration Summary:")
        print("=" * 50)
        
        # Inner loop details
        inner_steps = 10
        inner_range = "100ns to 1000ns"
        
        # Outer loop details  
        outer_steps = 20
        outer_range = "2.8GHz to 2.9GHz"
        
        # Total scan points
        total_points = inner_steps * outer_steps
        
        print(f"🔹 Inner Loop (Pulse Duration):")
        print(f"   Parameter: odmr_pulsed.sequence.pulse_duration")
        print(f"   Range: {inner_range}")
        print(f"   Steps: {inner_steps}")
        
        print(f"\n🔹 Outer Loop (Microwave Frequency):")
        print(f"   Parameter: pulse_duration_sweep.microwave.frequency")
        print(f"   Range: {outer_range}")
        print(f"   Steps: {outer_steps}")
        
        print(f"\n🔹 Total Scan Points: {total_points}")
        print(f"🔹 Estimated Time: {total_points * 2:.0f} seconds (assuming 2s per point)")
        
        print(f"\n🔹 Data Organization:")
        print(f"   - Each frequency point will contain {inner_steps} pulse duration measurements")
        print(f"   - Data will be organized by both sweep parameters")
        print(f"   - Scan info will be stored with each data point")
        
        print(f"\n🔹 Execution Flow:")
        print(f"   1. Set frequency to 2.8GHz")
        print(f"   2. Sweep pulse duration: 100ns → 1000ns (10 points)")
        print(f"   3. Set frequency to 2.8GHz + step")
        print(f"   4. Repeat pulse duration sweep")
        print(f"   5. Continue for all 20 frequency points")
    
    def get_scan_info(self):
        """
        Get information about the configured scan.
        """
        if not self.experiment_instance:
            return None
        
        return {
            'name': self.experiment_instance.name,
            'iterator_type': getattr(self.experiment_instance, 'iterator_type', 'Unknown'),
            'settings': self.experiment_instance.settings,
            'total_experiments': len(self.experiment_instance.experiments)
        }


def main():
    """Main function to demonstrate multi-variable scan creation."""
    print("🧪 Multi-Variable ODMR Scan Example")
    print("=" * 50)
    
    # Create the scan system
    scan_system = MultiVariableODMRScan()
    
    try:
        # Step 1: Create inner iterator
        if not scan_system.create_inner_iterator():
            print("❌ Failed to create inner iterator. Exiting.")
            return False
        
        # Step 2: Create outer iterator
        if not scan_system.create_outer_iterator():
            print("❌ Failed to create outer iterator. Exiting.")
            return False
        
        # Step 3: Create experiment instance
        if not scan_system.create_experiment_instance():
            print("❌ Failed to create experiment instance. Exiting.")
            return False
        
        # Step 4: Run scan (dry run by default)
        scan_system.run_scan(dry_run=True)
        
        # Step 5: Show scan information
        scan_info = scan_system.get_scan_info()
        if scan_info:
            print(f"\n📋 Final Scan Configuration:")
            print(f"   Name: {scan_info['name']}")
            print(f"   Type: {scan_info['iterator_type']}")
            print(f"   Sub-experiments: {scan_info['total_experiments']}")
        
        print(f"\n🎉 Multi-variable scan setup completed successfully!")
        print(f"💡 To run the actual scan, call: scan_system.run_scan(dry_run=False)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during scan setup: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
