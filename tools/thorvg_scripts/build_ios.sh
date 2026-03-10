#!/bin/bash
set -euo pipefail

# Build thorvg for iOS device and iOS Simulator
# Produces shared libraries and an XCFramework (iOS only, no macOS)
#
# Usage:  bash build_ios.sh <thorvg_source_dir>

ROOT_DIR=$1
cd "$ROOT_DIR"
ROOT_DIR="$(pwd)"
BUILD_ROOT="$ROOT_DIR/build_ios"
OUTPUT_DIR="$ROOT_DIR/output"
MESON_COMMON="--buildtype=release --default-library=shared -Dthreads=true -Dbindings=capi -Dloaders=svg,lottie,ttf -Dextra=lottie_exp,opengl_es -Dengines=sw,gl"

echo "=== ThorVG iOS Build ==="
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
build_target "ios_arm64"      "$ROOT_DIR/cross/ios_arm64.txt"            "$MESON_COMMON"
build_target "ios_sim_arm64"  "$ROOT_DIR/cross/ios_simulator_arm64.txt"  "$MESON_COMMON"
build_target "ios_sim_x86_64" "$ROOT_DIR/cross/ios_simulator_x86_64.txt" "$MESON_COMMON"

# ---------- copy / create fat libraries ----------
echo ">>> Creating fat libraries with lipo..."

# iOS device (single arch, just copy)
mkdir -p "$OUTPUT_DIR/ios_arm64"
cp "$BUILD_ROOT/ios_arm64/src/libthorvg-1.dylib" "$OUTPUT_DIR/ios_arm64/libthorvg-1.dylib"

# iOS Simulator fat (arm64 + x86_64)
mkdir -p "$OUTPUT_DIR/ios_sim_fat"
lipo -create \
    "$BUILD_ROOT/ios_sim_arm64/src/libthorvg-1.dylib" \
    "$BUILD_ROOT/ios_sim_x86_64/src/libthorvg-1.dylib" \
    -output "$OUTPUT_DIR/ios_sim_fat/libthorvg-1.dylib"

echo "<<< Fat libraries created"
echo ""

# ---------- create XCFramework ----------
echo ">>> Creating XCFramework..."

xcodebuild -create-xcframework \
    -library "$OUTPUT_DIR/ios_arm64/libthorvg-1.dylib" \
    -headers "$ROOT_DIR/inc" \
    -library "$OUTPUT_DIR/ios_sim_fat/libthorvg-1.dylib" \
    -headers "$ROOT_DIR/inc" \
    -output "$OUTPUT_DIR/thorvg.xcframework"

echo ""
echo "=== Build Complete ==="
echo "XCFramework: $OUTPUT_DIR/thorvg.xcframework"
echo ""
echo "Individual libraries:"
echo "  iOS arm64:           $OUTPUT_DIR/ios_arm64/libthorvg-1.dylib"
echo "  iOS Simulator (fat): $OUTPUT_DIR/ios_sim_fat/libthorvg-1.dylib"
