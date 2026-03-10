#!/bin/bash
set -euo pipefail

# Build thorvg for macOS (ARM64, x86_64, and universal fat binary)
# Produces shared libraries at output/macos_arm64, macos_x86_64, macos_fat
#
# Usage:  bash build_macos.sh <thorvg_source_dir>

ROOT_DIR=$1
cd "$ROOT_DIR"
ROOT_DIR="$(pwd)"
BUILD_ROOT="$ROOT_DIR/build_macos"
OUTPUT_DIR="$ROOT_DIR/output"
MESON_COMMON="--buildtype=release --default-library=shared -Dthreads=true -Dbindings=capi -Dloaders=svg,lottie,ttf -Dextra=lottie_exp,opengl_es -Dengines=sw,gl"

echo "=== ThorVG macOS Build ==="
echo "Root: $ROOT_DIR"
echo ""

rm -rf "$BUILD_ROOT"
mkdir -p "$OUTPUT_DIR"

# ---------- helper ----------
build_target() {
    local name="$1"
    local cross_file="$2"
    local meson_opts="$3"
    local build_dir="$BUILD_ROOT/$name"

    echo ">>> Building: $name"
    meson setup "$build_dir" \
        --cross-file "$cross_file" \
        $meson_opts \
        2>&1 | tail -5
    ninja -C "$build_dir" 2>&1
    echo "<<< Done: $name"
    echo ""
}

# ---------- build each slice ----------
build_target "macos_arm64"  "$ROOT_DIR/cross/macos_arm64.txt"  "$MESON_COMMON"
build_target "macos_x86_64" "$ROOT_DIR/cross/macos_x86_64.txt" "$MESON_COMMON"

# ---------- copy individual arch outputs ----------
mkdir -p "$OUTPUT_DIR/macos_arm64"
cp "$BUILD_ROOT/macos_arm64/src/libthorvg-1.dylib" "$OUTPUT_DIR/macos_arm64/libthorvg-1.dylib"

mkdir -p "$OUTPUT_DIR/macos_x86_64"
cp "$BUILD_ROOT/macos_x86_64/src/libthorvg-1.dylib" "$OUTPUT_DIR/macos_x86_64/libthorvg-1.dylib"

# ---------- create fat library (lipo) ----------
echo ">>> Creating macOS fat dylib with lipo..."

mkdir -p "$OUTPUT_DIR/macos_fat"
lipo -create \
    "$BUILD_ROOT/macos_arm64/src/libthorvg-1.dylib" \
    "$BUILD_ROOT/macos_x86_64/src/libthorvg-1.dylib" \
    -output "$OUTPUT_DIR/macos_fat/libthorvg-1.dylib"

echo "<<< Fat dylib created"
echo ""

echo "=== Build Complete ==="
echo "  macOS arm64:  $OUTPUT_DIR/macos_arm64/libthorvg-1.dylib"
echo "  macOS x86_64: $OUTPUT_DIR/macos_x86_64/libthorvg-1.dylib"
echo "  macOS fat:    $OUTPUT_DIR/macos_fat/libthorvg-1.dylib"
