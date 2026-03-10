#!/bin/bash
set -euo pipefail

# Build thorvg for iOS device and iOS Simulator
# Produces shared libraries and an XCFramework (iOS only, no macOS)
#
# Usage:  bash build_ios.sh <thorvg_source_dir>

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CROSS_DIR="$SCRIPT_DIR/../cross"

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
build_target "ios_arm64"      "$CROSS_DIR/ios_arm64.txt"            "$MESON_COMMON"
build_target "ios_sim_arm64"  "$CROSS_DIR/ios_simulator_arm64.txt"  "$MESON_COMMON"
build_target "ios_sim_x86_64" "$CROSS_DIR/ios_simulator_x86_64.txt" "$MESON_COMMON"

# ---------- helper: wrap dylib in a .framework bundle ----------
make_framework() {
    local dylib_path="$1"
    local output_dir="$2"
    local fw_dir="$output_dir/thorvg.framework"

    mkdir -p "$fw_dir/Headers"

    # Copy dylib and rename to framework binary name
    cp "$dylib_path" "$fw_dir/thorvg"

    # Set install name to @rpath/thorvg.framework/thorvg so the loader
    # resolves via the app's LD_RUNPATH_SEARCH_PATHS (= @executable_path/Frameworks)
    install_name_tool -id "@rpath/thorvg.framework/thorvg" "$fw_dir/thorvg"

    # Copy public header
    cp "$ROOT_DIR/inc/thorvg.h" "$fw_dir/Headers/"

    # Minimal Info.plist
    cat > "$fw_dir/Info.plist" << 'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleIdentifier</key>
    <string>org.thorvg.thorvg</string>
    <key>CFBundleName</key>
    <string>thorvg</string>
    <key>CFBundlePackageType</key>
    <string>FMWK</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>MinimumOSVersion</key>
    <string>13.0</string>
</dict>
</plist>
PLIST

    echo "    Created: $fw_dir"
}

# ---------- create .framework bundles ----------
echo ">>> Creating .framework bundles..."

# iOS device (single arch)
make_framework "$BUILD_ROOT/ios_arm64/src/libthorvg-1.dylib" "$OUTPUT_DIR/ios_arm64"

# iOS Simulator fat (arm64 + x86_64 → lipo → framework)
mkdir -p "$OUTPUT_DIR/ios_sim_fat"
lipo -create \
    "$BUILD_ROOT/ios_sim_arm64/src/libthorvg-1.dylib" \
    "$BUILD_ROOT/ios_sim_x86_64/src/libthorvg-1.dylib" \
    -output "$OUTPUT_DIR/ios_sim_fat/libthorvg-1.dylib"
make_framework "$OUTPUT_DIR/ios_sim_fat/libthorvg-1.dylib" "$OUTPUT_DIR/ios_sim_fat"
# Clean up intermediate fat dylib
rm "$OUTPUT_DIR/ios_sim_fat/libthorvg-1.dylib"

echo "<<< .framework bundles created"
echo ""

# ---------- create XCFramework from .framework bundles ----------
echo ">>> Creating XCFramework..."

rm -rf "$OUTPUT_DIR/thorvg.xcframework"
xcodebuild -create-xcframework \
    -framework "$OUTPUT_DIR/ios_arm64/thorvg.framework" \
    -framework "$OUTPUT_DIR/ios_sim_fat/thorvg.framework" \
    -output "$OUTPUT_DIR/thorvg.xcframework"

echo ""
echo "=== Build Complete ==="
echo "XCFramework: $OUTPUT_DIR/thorvg.xcframework"
echo ""
echo "Contents:"
echo "  Device:    thorvg.xcframework/ios-arm64/thorvg.framework/thorvg"
echo "  Simulator: thorvg.xcframework/ios-arm64_x86_64-simulator/thorvg.framework/thorvg"
echo ""
echo "Install name: @rpath/thorvg.framework/thorvg"
echo "In Xcode: embed thorvg.xcframework → loads at @executable_path/Frameworks/thorvg.framework/thorvg"
