#!/usr/bin/env python3
"""
Command Line Experiment Export Tool

This tool allows you to convert Python experiment files to AQS/JSON format from the command line,
without needing to use the GUI.

Usage:
    # Export a single experiment
    python src/tools/export_experiments_cli.py src/Model/experiments/my_experiment.py
    
    # Export multiple experiments
    python src/tools/export_experiments_cli.py src/Model/experiments/experiment1.py src/Model/experiments/experiment2.py
    
    # Export all experiments in a directory
    python src/tools/export_experiments_cli.py --directory src/Model/experiments/
    
    # Export to specific output directory
    python src/tools/export_experiments_cli.py --output /path/to/output src/Model/experiments/my_experiment.py
    
    # Export devices instead of experiments
    python src/tools/export_experiments_cli.py --type device src/Controller/my_device.py

Examples:
    # Convert a new experiment you just wrote
    python src/tools/export_experiments_cli.py src/Model/experiments/odmr_pulsed.py
    
    # Convert multiple experiments at once
    python src/tools/export_experiments_cli.py src/Model/experiments/odmr_*.py
    
    # Convert all experiments in the experiments directory
    python src/tools/export_experiments_cli.py --directory src/Model/experiments/
"""

import sys
import argparse
import glob
import inspect
from pathlib import Path
from typing import List, Optional

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.tools.export_default import python_file_to_aqs, find_experiments_in_python_files, find_devices_in_python_files


def find_python_files(paths: List[str], directory: Optional[str] = None) -> List[str]:
    """
    Find Python files from the given paths and/or directory.
    
    Args:
        paths: List of file paths or glob patterns
        directory: Optional directory to search for Python files
        
    Returns:
        List of Python file paths
    """
    python_files = []
    
    # If directory is specified, find all Python files in it
    if directory:
        dir_path = Path(directory)
        if not dir_path.exists():
            print(f"❌ Directory not found: {directory}")
            return []
        
        # Find all Python files in directory and subdirectories
        for py_file in dir_path.rglob("*.py"):
            if py_file.name != "__init__.py" and "setup" not in py_file.name:
                python_files.append(str(py_file))
        
        print(f"🔍 Found {len(python_files)} Python files in {directory}")
    
    # Process individual file paths and glob patterns
    for path in paths:
        # Handle glob patterns
        if "*" in path or "?" in path:
            matches = glob.glob(path)
            if matches:
                python_files.extend(matches)
                print(f"🔍 Glob pattern '{path}' matched {len(matches)} files")
            else:
                print(f"⚠️  No files matched glob pattern: {path}")
        else:
            # Single file path
            file_path = Path(path)
            if file_path.exists():
                python_files.append(str(file_path))
            else:
                print(f"❌ File not found: {path}")
    
    # Remove duplicates while preserving order
    seen = set()
    unique_files = []
    for file_path in python_files:
        if file_path not in seen:
            seen.add(file_path)
            unique_files.append(file_path)
    
    return unique_files


def main():
    """Main function for the command-line export tool."""
    parser = argparse.ArgumentParser(
        description="Convert Python experiment/device files to AQS/JSON format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "files",
        nargs="*",
        help="Python files to convert (supports glob patterns like *.py)"
    )
    
    parser.add_argument(
        "--directory", "-d",
        help="Directory to search for Python files"
    )
    
    parser.add_argument(
        "--output", "-o",
        default="./exported",
        help="Output directory for AQS/JSON files (default: ./exported)"
    )
    
    parser.add_argument(
        "--type", "-t",
        choices=["experiment", "device"],
        default="experiment",
        help="Type of files to convert (default: experiment)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    parser.add_argument(
        "--skip-device-required",
        action="store_true",
        help="Skip experiments that require devices (useful for CLI testing)"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.files and not args.directory:
        print("❌ Error: You must specify either files or a directory to convert")
        print("Use --help for usage information")
        sys.exit(1)
    
    # Find Python files
    python_files = find_python_files(args.files, args.directory)
    
    if not python_files:
        print("❌ No Python files found to convert")
        sys.exit(1)
    
    print(f"🔧 Converting {len(python_files)} {args.type} files...")
    print(f"📁 Output directory: {args.output}")
    print("=" * 60)
    
    # Create output directory if it doesn't exist
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Convert files
    try:
        if args.type == "experiment":
            # For experiments, we need to create a metadata dict
            experiment_metadata = {}
            for file_path in python_files:
                # Try to find the actual experiment class name in the file
                exp_name = Path(file_path).stem
                
                # First, try to import the module to find experiment classes
                try:
                    # Add src to path for import
                    sys.path.insert(0, 'src')
                    
                    # Convert file path to module path
                    forward_path = file_path.replace('\\', '/')
                    if 'src/' in forward_path:
                        src_index = forward_path.find('src/')
                        module_path = forward_path[src_index + 4:-3].replace('/', '.')
                    else:
                        module_path = forward_path.replace('.py', '').replace('/', '.').replace('\\', '.')
                    
                    # Import the module
                    module = __import__(module_path, fromlist=['*'])
                    
                    # Find experiment classes in the module
                    from src.core import Experiment
                    experiment_classes = []
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name, None)
                        if (inspect.isclass(attr) and 
                            issubclass(attr, Experiment) and 
                            attr != Experiment):
                            experiment_classes.append(attr_name)
                    
                    if experiment_classes:
                        # Use the first experiment class found
                        actual_class_name = experiment_classes[0]
                        if len(experiment_classes) > 1:
                            print(f"⚠️  Multiple experiment classes found in {file_path}: {experiment_classes}")
                            print(f"  Using: {actual_class_name}")
                        
                        # Check if experiment requires devices
                        experiment_class = getattr(module, actual_class_name)
                        requires_devices = hasattr(experiment_class, '_DEVICES') and experiment_class._DEVICES
                        
                        if requires_devices and args.skip_device_required:
                            print(f"⏭️  Skipping {actual_class_name} (requires devices: {list(experiment_class._DEVICES.keys())})")
                            continue
                        
                        experiment_metadata[actual_class_name] = {
                            'filepath': file_path,
                            'info': f"Experiment loaded from {file_path}"
                        }
                    else:
                        # Fallback to filename
                        experiment_metadata[exp_name] = {
                            'filepath': file_path,
                            'info': f"Experiment loaded from {file_path}"
                        }
                        print(f"⚠️  No experiment classes found in {file_path}, using filename: {exp_name}")
                        
                except Exception as e:
                    # Fallback to filename if import fails
                    experiment_metadata[exp_name] = {
                        'filepath': file_path,
                        'info': f"Experiment loaded from {file_path}"
                    }
                    print(f"⚠️  Could not analyze {file_path}: {e}, using filename: {exp_name}")
            
            loaded, failed = python_file_to_aqs(
                list_of_python_files=experiment_metadata,
                target_folder=str(output_dir),
                class_type='Experiment',
                raise_errors=False,
                existing_devices=None  # No devices for CLI usage
            )
        else:
            # For devices, create metadata dict
            device_metadata = {}
            for file_path in python_files:
                # Extract device name from filename
                device_name = Path(file_path).stem
                device_metadata[device_name] = {
                    'filepath': file_path,
                    'info': f"Device loaded from {file_path}"
                }
            
            loaded, failed = python_file_to_aqs(
                list_of_python_files=device_metadata,
                target_folder=str(output_dir),
                class_type='Device',
                raise_errors=False,
                existing_devices=None
            )
        
        # Report results
        print("\n" + "=" * 60)
        print("📊 CONVERSION RESULTS")
        print("=" * 60)
        
        if loaded:
            print(f"✅ Successfully converted {len(loaded)} {args.type}s:")
            for name in loaded.keys():
                print(f"  ✅ {name}")
        
        if failed:
            print(f"\n❌ Failed to convert {len(failed)} {args.type}s:")
            for name, error in failed.items():
                print(f"  ❌ {name}: {error}")
        
        print(f"\n📁 Files saved to: {output_dir.absolute()}")
        
        if loaded:
            print(f"\n🎉 Conversion completed! {len(loaded)} {args.type}(s) ready to use.")
        else:
            print(f"\n⚠️  No {args.type}s were successfully converted.")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Conversion failed with error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
