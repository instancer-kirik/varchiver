# Default recipe to run when just is called without arguments
default:
    @just --list

# Install LÖVR CLI globally
install-lovr:
    #!/usr/bin/env bash
    mkdir -p ~/.local/bin
    cp ~/Applications/lovr-v0.18.0-x86_64_2af8cc856613f6b4bdfe2a2a4ff9bcd2.AppImage ~/.local/bin/lovr
    chmod +x ~/.local/bin/lovr
    echo "LÖVR CLI installed to ~/.local/bin/lovr"
    echo "Make sure ~/.local/bin is in your PATH"

# Run LÖVR project in current directory
run:
    lovr .

# Clean build artifacts
clean:
    rm -rf build/
    rm -rf dist/
    rm -rf *.egg-info/
    find . -type d -name "__pycache__" -exec rm -rf {} +
    find . -type f -name "*.pyc" -delete

# Build the project
build: clean
    python -m build

# Install development dependencies
install-dev:
    uv pip install -e ".[dev]"

# Run tests
test:
    python -m pytest tests/

# Update dependencies
update-deps:
    uv pip install --upgrade -r requirements.txt 