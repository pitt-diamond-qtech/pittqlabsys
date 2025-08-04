#!/usr/bin/env python3
"""
Offline package installer for pittqlabsys

This script installs packages from the local wheels_cache directory
when internet access is not available.

Usage:
    python install_offline.py [--requirements requirements.txt]
"""

import argparse
import subprocess
import sys
from pathlib import Path


def install_from_cache(requirements_file="requirements.txt", cache_dir="wheels_cache"):
    """Install packages from local wheel cache."""
    
    cache_path = Path(cache_dir)
    if not cache_path.exists():
        print(f"Error: Cache directory '{cache_dir}' not found!")
        print("Run 'pip download -r requirements.txt -d wheels_cache' first to create the cache.")
        return False
    
    # Check if cache has any wheel files
    wheel_files = list(cache_path.glob("*.whl")) + list(cache_path.glob("*.tar.gz"))
    if not wheel_files:
        print(f"Error: No wheel files found in '{cache_dir}'!")
        return False
    
    print(f"Found {len(wheel_files)} packages in cache directory")
    
    try:
        # Install from local cache
        cmd = [
            sys.executable, "-m", "pip", "install",
            "--no-index",  # Don't use PyPI
            "--find-links", str(cache_path),  # Use local directory
            "-r", requirements_file
        ]
        
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True)
        
        print("✅ Packages installed successfully from local cache!")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Installation failed: {e}")
        return False
    except FileNotFoundError:
        print("❌ pip not found. Make sure pip is installed and in your PATH.")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Install packages from local wheel cache",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python install_offline.py
  python install_offline.py --requirements requirements.txt
  python install_offline.py --cache-dir my_wheels
        """
    )
    
    parser.add_argument(
        "--requirements", "-r",
        default="requirements.txt",
        help="Requirements file to install (default: requirements.txt)"
    )
    
    parser.add_argument(
        "--cache-dir", "-c",
        default="wheels_cache",
        help="Directory containing wheel files (default: wheels_cache)"
    )
    
    args = parser.parse_args()
    
    # Check if requirements file exists
    if not Path(args.requirements).exists():
        print(f"Error: Requirements file '{args.requirements}' not found!")
        return 1
    
    success = install_from_cache(args.requirements, args.cache_dir)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main()) 