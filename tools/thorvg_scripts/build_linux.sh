#!/bin/bash
set -euo pipefail

# Build thorvg for Linux (native architecture)
# Produces a shared library at output/linux_<arch>/libthorvg-1.so
#
# Usage:  bash build_linux.sh <thorvg_source_dir>

ROOT_DIR=$1
cd "$ROOT_DIR"
ROOT_DIR="$(pwd)"
BUILD_ROOT="$ROOT_DIR/build_linux"
OUTPUT_DIR="$ROOT_DIR/output"
MESON_COMMON="--buildtype=release --default-library=shared -Dthreads=true -Dbindings=capi -Dloaders=svg,lottie,ttf -Dextra=lottie_exp -Dengines=sw,gl"

ARCH="$(uname -m)"

# Ensure meson and ninja are available
command -v meson >/dev/null 2>&1 || pip install meson
command -v ninja >/dev/null 2>&1 || pip install ninja

echo "=== ThorVG Linux Build ==="
echo "Root: $ROOT_DIR"
echo "Arch: $ARCH"
echo ""

rm -rf "$BUILD_ROOT"
mkdir -p "$OUTPUT_DIR"

BUILD_DIR="$BUILD_ROOT/$ARCH"
OUT_DIR="$OUTPUT_DIR/linux_$ARCH"

echo ">>> Building: linux_$ARCH"
meson setup "$BUILD_DIR" $MESON_COMMON 2>&1 | tail -5
ninja -C "$BUILD_DIR" 2>&1
echo "<<< Done: linux_$ARCH"
echo ""

# Copy output (shared lib + symlinks)
mkdir -p "$OUT_DIR"
cp -P "$BUILD_DIR/src/libthorvg-1.so"* "$OUT_DIR/"

echo "=== Build Complete ==="
echo "Shared library: $OUT_DIR/libthorvg-1.so"
