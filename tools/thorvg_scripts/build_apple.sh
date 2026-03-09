#!/bin/bash
set -euo pipefail

# Build thorvg for iOS, iOS Simulator, and macOS (Intel + ARM64)
# Produces a universal XCFramework at the end.
#
# Usage:  bash build_apple.sh <thorvg_source_dir>

ROOT_DIR=$1
cd "$ROOT_DIR"
BUILD_ROOT="$ROOT_DIR/build_multiplatform"
OUTPUT_DIR="$ROOT_DIR/output"
MESON_COMMON="--buildtype=release --default-library=static -Dthreads=true -Dbindings=capi -Dloaders=svg,lottie,ttf -Dextra=lottie_exp"
MESON_MACOS="$MESON_COMMON"
MESON_IOS="$MESON_COMMON"

echo "=== ThorVG Multi-Platform Build ==="
echo "Root: $ROOT_DIR"
echo ""

rm -rf "$BUILD_ROOT" "$OUTPUT_DIR"
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
build_target "ios_arm64"            "$ROOT_DIR/cross/ios_arm64.txt"            "$MESON_IOS"
build_target "ios_sim_arm64"        "$ROOT_DIR/cross/ios_simulator_arm64.txt"  "$MESON_IOS"
build_target "ios_sim_x86_64"       "$ROOT_DIR/cross/ios_simulator_x86_64.txt" "$MESON_IOS"
build_target "macos_arm64"          "$ROOT_DIR/cross/macos_arm64.txt"          "$MESON_MACOS"
build_target "macos_x86_64"         "$ROOT_DIR/cross/macos_x86_64.txt"        "$MESON_MACOS"

# ---------- create fat libraries (lipo) ----------
echo ">>> Creating fat libraries with lipo..."

# iOS Simulator fat (arm64 + x86_64)
mkdir -p "$OUTPUT_DIR/ios_sim_fat"
lipo -create \
    "$BUILD_ROOT/ios_sim_arm64/src/libthorvg-1.a" \
    "$BUILD_ROOT/ios_sim_x86_64/src/libthorvg-1.a" \
    -output "$OUTPUT_DIR/ios_sim_fat/libthorvg.a"

# macOS fat (arm64 + x86_64)
mkdir -p "$OUTPUT_DIR/macos_fat"
lipo -create \
    "$BUILD_ROOT/macos_arm64/src/libthorvg-1.a" \
    "$BUILD_ROOT/macos_x86_64/src/libthorvg-1.a" \
    -output "$OUTPUT_DIR/macos_fat/libthorvg.a"

# iOS device (single arch, just copy)
mkdir -p "$OUTPUT_DIR/ios_arm64"
cp "$BUILD_ROOT/ios_arm64/src/libthorvg-1.a" "$OUTPUT_DIR/ios_arm64/libthorvg.a"

echo "<<< Fat libraries created"
echo ""

# ---------- create XCFramework ----------
echo ">>> Creating XCFramework..."

xcodebuild -create-xcframework \
    -library "$OUTPUT_DIR/ios_arm64/libthorvg.a" \
    -headers "$ROOT_DIR/inc" \
    -library "$OUTPUT_DIR/ios_sim_fat/libthorvg.a" \
    -headers "$ROOT_DIR/inc" \
    -library "$OUTPUT_DIR/macos_fat/libthorvg.a" \
    -headers "$ROOT_DIR/inc" \
    -output "$OUTPUT_DIR/thorvg.xcframework"

echo ""
echo "=== Build Complete ==="
echo "XCFramework: $OUTPUT_DIR/thorvg.xcframework"
echo ""
echo "Individual libraries:"
echo "  iOS arm64:           $OUTPUT_DIR/ios_arm64/libthorvg.a"
echo "  iOS Simulator (fat): $OUTPUT_DIR/ios_sim_fat/libthorvg.a"
echo "  macOS (fat):         $OUTPUT_DIR/macos_fat/libthorvg.a"
