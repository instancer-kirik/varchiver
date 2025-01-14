#!/bin/bash

# Ensure we're in the project directory
cd "$(dirname "$0")"

# Install uv if not already installed
if ! command -v uv &> /dev/null; then
    pip install uv
fi

# Install dependencies
uv pip install -e .[dev]

# Ensure pyinstaller is installed
uv pip install pyinstaller

# Function to build for Linux
build_linux() {
    echo "Building Linux executable..."
    python -m pyinstaller --clean \
        --onefile \
        --name varchiver-linux \
        --add-data "varchiver:varchiver" \
        --hidden-import PyQt6 \
        --hidden-import rarfile \
        varchiver/bootstrap.py
}

# Function to build for Windows
build_windows() {
    echo "Building Windows executable..."
    python -m pyinstaller --clean \
        --onefile \
        --name varchiver-windows \
        --add-data "varchiver;varchiver" \
        --hidden-import PyQt6 \
        --hidden-import rarfile \
        varchiver/bootstrap.py
}

# Create dist directory if it doesn't exist
mkdir -p dist

# Build based on platform
case "$(uname -s)" in
    Linux*)
        build_linux
        # Build Windows version if wine is available
        if command -v wine &> /dev/null; then
            build_windows
        else
            echo "Wine not found. Skipping Windows build."
        fi
        ;;
    MINGW*|MSYS*|CYGWIN*)
        build_windows
        ;;
    *)
        echo "Unsupported platform"
        exit 1
        ;;
esac

# Create release directory
mkdir -p release

# Package Linux version
if [ -f "dist/varchiver-linux" ]; then
    echo "Packaging Linux version..."
    cp dist/varchiver-linux release/
    # Create a modified desktop file with the correct Exec path
    sed "s|^Exec=.*|Exec=/usr/bin/varchiver-linux %f|" varchiver.desktop > release/varchiver.desktop
    tar -czf release/varchiver-linux.tar.gz -C release varchiver-linux varchiver.desktop
fi

# Package Windows version
if [ -f "dist/varchiver-windows.exe" ]; then
    echo "Packaging Windows version..."
    cp dist/varchiver-windows.exe release/
    zip -j release/varchiver-windows.zip release/varchiver-windows.exe
fi

echo "Build complete! Check the release directory for the packages."
