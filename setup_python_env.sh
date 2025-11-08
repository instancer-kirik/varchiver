#!/bin/bash

# Setup script for varchiver Python environment on openSUSE
# This script installs Python 3.11, uv, and sets up the virtual environment

set -e  # Exit on error

echo "=== Varchiver Python Environment Setup for openSUSE ==="
echo ""

# Step 1: Check if running on openSUSE
if ! command -v zypper &> /dev/null; then
    echo "Error: This script is designed for openSUSE systems with zypper package manager."
    exit 1
fi

# Step 2: Install Python 3.11 if not already installed
echo "Checking for Python 3.11..."
if ! command -v python3.11 &> /dev/null; then
    echo "Python 3.11 not found. Installing..."
    sudo zypper install -y python311 python311-pip python311-devel
else
    echo "Python 3.11 is already installed: $(python3.11 --version)"
fi

# Step 3: Install/Update uv
echo ""
echo "Installing/updating uv..."
if ! command -v uv &> /dev/null || [ ! -f "$HOME/.local/bin/uv" ]; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
else
    echo "uv is already installed: $(uv --version)"
    echo "To update uv, run: uv self update"
fi

# Step 4: Navigate to project directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo ""
echo "Working in directory: $(pwd)"

# Step 5: Clean up old virtual environment if it exists
if [ -d ".venv" ]; then
    echo "Removing old virtual environment..."
    rm -rf .venv
fi

# Step 6: Create new virtual environment with Python 3.11
echo ""
echo "Creating new virtual environment with Python 3.11..."
if [ -f "$HOME/.local/bin/uv" ]; then
    UV_BIN="$HOME/.local/bin/uv"
else
    UV_BIN="uv"
fi

$UV_BIN venv --python python3.11 .venv

# Step 7: Sync dependencies
echo ""
echo "Installing project dependencies..."
$UV_BIN sync

# Step 8: Verify installation
echo ""
echo "Verifying installation..."
source .venv/bin/activate
echo "Python version in venv: $(python --version)"
echo "Python path: $(which python)"

# Step 9: Test import of main dependencies
echo ""
echo "Testing main dependencies..."
python -c "import PyQt6; print(f'PyQt6 version: {PyQt6.QtCore.QT_VERSION_STR}')" 2>/dev/null || echo "PyQt6 import test failed"
python -c "import rarfile; print('rarfile imported successfully')" 2>/dev/null || echo "rarfile import test failed"
python -c "import psutil; print(f'psutil version: {psutil.__version__}')" 2>/dev/null || echo "psutil import test failed"

deactivate

echo ""
echo "=== Setup Complete ==="
echo ""
echo "To activate the virtual environment, run:"
echo "  source .venv/bin/activate"
echo ""
echo "To run varchiver:"
echo "  source .venv/bin/activate"
echo "  python -m varchiver.main"
echo ""
echo "Or using uv directly:"
echo "  uv run python -m varchiver.main"
