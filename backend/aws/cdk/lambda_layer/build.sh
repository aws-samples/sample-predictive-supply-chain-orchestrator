#!/bin/bash
# Build script for Lambda Layer
# Packages Python dependencies for AWS Lambda Python 3.11 runtime

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="${SCRIPT_DIR}/build"
PYTHON_DIR="${BUILD_DIR}/python"

echo "Building Lambda Layer for Python 3.11..."

# Clean previous build
if [ -d "${BUILD_DIR}" ]; then
    echo "Cleaning previous build..."
    rm -rf "${BUILD_DIR}"
fi

# Create build directory structure
mkdir -p "${PYTHON_DIR}"

# Install dependencies
echo "Installing dependencies..."
pip3 install \
    --platform manylinux2014_x86_64 \
    --target="${PYTHON_DIR}" \
    --implementation cp \
    --python-version 3.11 \
    --only-binary=:all: \
    --upgrade \
    -r "${SCRIPT_DIR}/requirements.txt"

# Remove unnecessary files to reduce size
echo "Cleaning up unnecessary files..."
find "${PYTHON_DIR}" -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
find "${PYTHON_DIR}" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "${PYTHON_DIR}" -type f -name "*.pyc" -delete
find "${PYTHON_DIR}" -type f -name "*.pyo" -delete
find "${PYTHON_DIR}" -type f -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true

# Check layer size
LAYER_SIZE=$(du -sh "${BUILD_DIR}" | cut -f1)
echo "Layer size: ${LAYER_SIZE}"

# Verify size is under 250MB (cross-platform check)
if command -v du &> /dev/null; then
    # Try GNU du first (Linux)
    LAYER_SIZE_BYTES=$(du -sb "${BUILD_DIR}" 2>/dev/null | cut -f1 || du -sk "${BUILD_DIR}" | cut -f1 | awk '{print $1 * 1024}')
    MAX_SIZE_BYTES=$((250 * 1024 * 1024))
    
    if [ "${LAYER_SIZE_BYTES}" -gt "${MAX_SIZE_BYTES}" ]; then
        echo "ERROR: Layer size exceeds 250MB limit"
        exit 1
    fi
fi

echo "Lambda Layer built successfully at ${BUILD_DIR}"
echo "Layer size: ${LAYER_SIZE}"
