#!/bin/bash

set -e  # Exit immediately if a command exits with a non-zero status.

# Ensure we're in the project directory
cd "$(dirname "$0")"

# Check Python version
python_version=$(python --version 2>&1 | awk '{print $2}')
echo "Using Python version: $python_version"

# Install dependencies
poetry install

# Clean previous builds (but preserve source)
rm -rf build/ dist/ __pycache__/ varchiver/__pycache__/ .pyarmor/

# Create obfuscated package with PyArmor 8
poetry run pyarmor gen \
    --platform linux.x86_64 \
    --output dist/obfuscated \
    varchiver/bootstrap.py

# Create single binary with PyInstaller
poetry run pyinstaller \
    --clean \
    --onefile \
    --name varchiver \
    --add-data "dist/obfuscated/pyarmor_runtime_000000:pyarmor_runtime_000000" \
    --hidden-import PyQt6 \
    --hidden-import rarfile \
    --hidden-import varchiver \
    --collect-submodules varchiver \
    dist/obfuscated/bootstrap.py

# Clean up intermediate files (but preserve source)
rm -rf build/ dist/obfuscated/ varchiver/__pycache__/

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
