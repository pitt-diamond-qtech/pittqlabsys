#!/bin/bash
# Offline package installer script for pittqlabsys

set -e  # Exit on any error

CACHE_DIR="wheels_cache"
REQUIREMENTS_FILE="requirements.txt"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -r|--requirements)
            REQUIREMENTS_FILE="$2"
            shift 2
            ;;
        -c|--cache-dir)
            CACHE_DIR="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  -r, --requirements FILE  Requirements file (default: requirements.txt)"
            echo "  -c, --cache-dir DIR      Cache directory (default: wheels_cache)"
            echo "  -h, --help              Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

echo "🔧 Offline Package Installer for pittqlabsys"
echo "=============================================="

# Check if cache directory exists
if [[ ! -d "$CACHE_DIR" ]]; then
    echo "❌ Error: Cache directory '$CACHE_DIR' not found!"
    echo "💡 Run this command first to create the cache:"
    echo "   pip download -r $REQUIREMENTS_FILE -d $CACHE_DIR"
    exit 1
fi

# Check if requirements file exists
if [[ ! -f "$REQUIREMENTS_FILE" ]]; then
    echo "❌ Error: Requirements file '$REQUIREMENTS_FILE' not found!"
    exit 1
fi

# Count wheel files
WHEEL_COUNT=$(find "$CACHE_DIR" -name "*.whl" -o -name "*.tar.gz" | wc -l | tr -d ' ')
echo "📦 Found $WHEEL_COUNT packages in cache directory"

if [[ $WHEEL_COUNT -eq 0 ]]; then
    echo "❌ Error: No wheel files found in '$CACHE_DIR'!"
    exit 1
fi

echo "🚀 Installing packages from local cache..."
echo "Command: pip install --no-index --find-links $CACHE_DIR -r $REQUIREMENTS_FILE"

# Install packages
if pip install --no-index --find-links "$CACHE_DIR" -r "$REQUIREMENTS_FILE"; then
    echo "✅ Packages installed successfully from local cache!"
else
    echo "❌ Installation failed!"
    exit 1
fi 