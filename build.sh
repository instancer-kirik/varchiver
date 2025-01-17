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

# Ensure pyinstaller is installed
uv pip install pyinstaller

# Clean previous builds (but preserve source)
rm -rf build/ dist/ __pycache__/ varchiver/__pycache__/

# Create single binary with PyInstaller
python -m pyinstaller \
    --clean \
    --onefile \
    --name varchiver \
    --hidden-import PyQt6 \
    --hidden-import rarfile \
    --hidden-import varchiver \
    --collect-submodules varchiver \
    varchiver/bootstrap.py

# Create dist directory if it doesn't exist
mkdir -p dist

# Package the binary with permissions preserved
cd dist
if [ -f varchiver ]; then
    tar czf varchiver-linux-x86_64.tar.gz varchiver
    echo "Binary packaged in dist/varchiver-linux-x86_64.tar.gz"
    
    # Create AppImage
    echo "Creating AppImage..."
    cd ..
    
    # Download linuxdeploy if not present
    if [ ! -f linuxdeploy-x86_64.AppImage ]; then
        wget https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage
        chmod +x linuxdeploy-x86_64.AppImage
    fi
    
    # Create AppDir structure
    mkdir -p AppDir/usr/{bin,share/{applications,icons/hicolor/scalable/apps}}
    cp dist/varchiver AppDir/usr/bin/
    cp varchiver.desktop AppDir/usr/share/applications/
    cp resources/icons/archive.svg AppDir/usr/share/icons/hicolor/scalable/apps/varchiver.svg
    
    # Create AppImage
    VERSION=$(grep '^pkgver=' PKGBUILD | cut -d'=' -f2)
    ./linuxdeploy-x86_64.AppImage \
        --appdir AppDir \
        --output appimage \
        --desktop-file=varchiver.desktop \
        --icon-file=resources/icons/archive.svg
    
    # Move AppImage to dist
    mv Varchiver*.AppImage dist/varchiver-${VERSION}-x86_64.AppImage
    echo "AppImage created at dist/varchiver-${VERSION}-x86_64.AppImage"
    
    cd dist
else
    echo "Error: varchiver binary not found. Build may have failed."
    exit 1
fi
