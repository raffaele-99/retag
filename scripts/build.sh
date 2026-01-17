#!/bin/bash
# Build Retagger executable for the current platform
# Usage: ./scripts/build.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "=== Retagger Build Script ==="
echo "Project directory: $PROJECT_DIR"

# Check for virtual environment
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Install dependencies
echo "Installing dependencies..."
pip install ".[dev]"

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build dist

# Build with PyInstaller
echo "Building executable..."
pyinstaller retagger.spec --clean

echo ""
echo "=== Build Complete ==="
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "Output: dist/Retagger.app"
    echo "Run with: open dist/Retagger.app"
else
    echo "Output: dist/Retagger"
    echo "Run with: ./dist/Retagger"
fi
