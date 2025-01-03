#!/bin/bash

set -e  # Exit immediately if a command exits with a non-zero status.

# Ensure we're in the project directory
cd "$(dirname "$0")"

# Check Python version
python_version=$(python --version 2>&1 | awk '{print $2}')
echo "Using Python version: $python_version"

# Install uv if not already installed
if ! command -v uv &> /dev/null; then
    pip install uv
fi

# Install dependencies
uv pip install -e .[dev]

# Clean previous builds (but preserve source)
rm -rf build/ dist/ __pycache__/ varchiver/__pycache__/

# Create single binary with PyInstaller
uv pip run pyinstaller \
    --clean \
    --onefile \
    --name varchiver \
    --hidden-import PyQt6 \
    --hidden-import rarfile \
    --hidden-import varchiver \
    --collect-submodules varchiver \
    varchiver/main.py

# Create dist directory if it doesn't exist
mkdir -p dist

# Package the binary with permissions preserved
cd dist
if [ -f varchiver ]; then
    tar czf varchiver-linux-x86_64.tar.gz varchiver
    echo "Build complete! Binary is packaged in dist/varchiver-linux-x86_64.tar.gz"
else
    echo "Error: varchiver binary not found. Build may have failed."
    exit 1
fi
