#!/bin/bash
set -euo pipefail

# Build macOS and iOS wheels for thorvg-cython.
# Requires: Xcode, cibuildwheel, meson, ninja

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
OUTPUT_DIR="${1:-${PROJECT_DIR}/wheelhouse}"

cd "$PROJECT_DIR"

echo "=== Building macOS wheels ==="
uvx cibuildwheel --platform macos --output-dir "$OUTPUT_DIR"

echo ""
echo "=== Building iOS wheels ==="
uvx cibuildwheel --platform ios \
    --archs "arm64_iphoneos arm64_iphonesimulator x86_64_iphonesimulator" \
    --output-dir "$OUTPUT_DIR"

echo ""
echo "=== Injecting xcframework into iOS wheels ==="
python3 "$SCRIPT_DIR/add-ios-frameworks.py" "$OUTPUT_DIR" \
    --xcframework "$PROJECT_DIR/thorvg/output/thorvg.xcframework"

echo ""
echo "=== Done ==="
ls -lh "$OUTPUT_DIR"/*.whl
