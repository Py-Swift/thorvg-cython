#!/bin/bash
set -euo pipefail

# Build thorvg for Android (aarch64 and x86_64)
# Produces shared libraries at output/android_aarch64 and output/android_x86_64
#
# Usage:  bash build_android.sh <thorvg_source_dir> [ndk_path] [api_level]
#
# Arguments:
#   $1  - thorvg source directory (required)
#   $2  - Android NDK path (default: $ANDROID_NDK_HOME or $ANDROID_NDK)
#   $3  - Android API level (default: 24)

ROOT_DIR=$1
cd "$ROOT_DIR"
ROOT_DIR="$(pwd)"
BUILD_ROOT="$ROOT_DIR/build_android"
OUTPUT_DIR="$ROOT_DIR/output"
MESON_COMMON="--buildtype=release --default-library=shared -Dthreads=true -Dbindings=capi -Dloaders=svg,lottie,ttf -Dextra=lottie_exp,opengl_es -Dengines=sw,gl"

# Resolve NDK path
NDK="${2:-${ANDROID_NDK_HOME:-${ANDROID_NDK:-}}}"
if [[ -z "$NDK" ]]; then
    echo "ERROR: Android NDK path not specified."
    echo "Pass as \$2 or set ANDROID_NDK_HOME / ANDROID_NDK env var."
    exit 1
fi
if [[ ! -d "$NDK" ]]; then
    echo "ERROR: NDK path does not exist: $NDK"
    exit 1
fi

API="${3:-24}"

# Detect host tag (linux-x86_64, darwin-x86_64, darwin-arm64, etc.)
case "$(uname -s)-$(uname -m)" in
    Linux-x86_64)   HOST_TAG="linux-x86_64" ;;
    Linux-aarch64)   HOST_TAG="linux-aarch64" ;;
    Darwin-x86_64)  HOST_TAG="darwin-x86_64" ;;
    Darwin-arm64)   HOST_TAG="darwin-x86_64" ;;  # NDK ships x86_64 on macOS
    *)              HOST_TAG="linux-x86_64" ;;
esac

echo "=== ThorVG Android Build ==="
echo "Root:      $ROOT_DIR"
echo "NDK:       $NDK"
echo "HOST_TAG:  $HOST_TAG"
echo "API level: $API"
echo ""

rm -rf "$BUILD_ROOT"
mkdir -p "$OUTPUT_DIR"

# ---------- helper: generate cross file from template ----------
generate_cross_file() {
    local template="$1"
    local output="$2"
    sed \
        -e "s|NDK|$NDK|g" \
        -e "s|HOST_TAG|$HOST_TAG|g" \
        -e "s|API|$API|g" \
        "$template" > "$output"
    echo "  Generated cross file: $output"
}

# ---------- helper: build a target ----------
build_target() {
    local name="$1"
    local cross_file="$2"
    local build_dir="$BUILD_ROOT/$name"

    echo ">>> Building: $name"
    meson setup "$build_dir" \
        --cross-file "$cross_file" \
        $MESON_COMMON \
        2>&1 | tail -5
    ninja -C "$build_dir" 2>&1
    echo "<<< Done: $name"
    echo ""
}

# ---------- generate cross files ----------
echo ">>> Generating cross files..."
CROSS_DIR="$BUILD_ROOT/cross"
mkdir -p "$CROSS_DIR"
generate_cross_file "$ROOT_DIR/cross/android_aarch64.txt" "$CROSS_DIR/android_aarch64.txt"
generate_cross_file "$ROOT_DIR/cross/android_x86_64.txt"  "$CROSS_DIR/android_x86_64.txt"
echo ""

# ---------- build each arch ----------
build_target "android_aarch64" "$CROSS_DIR/android_aarch64.txt"
build_target "android_x86_64"  "$CROSS_DIR/android_x86_64.txt"

# ---------- copy outputs ----------
mkdir -p "$OUTPUT_DIR/android_aarch64"
cp "$BUILD_ROOT/android_aarch64/src/libthorvg-1.so" "$OUTPUT_DIR/android_aarch64/libthorvg-1.so"

mkdir -p "$OUTPUT_DIR/android_x86_64"
cp "$BUILD_ROOT/android_x86_64/src/libthorvg-1.so" "$OUTPUT_DIR/android_x86_64/libthorvg-1.so"

echo "=== Build Complete ==="
echo "  Android aarch64: $OUTPUT_DIR/android_aarch64/libthorvg-1.so"
echo "  Android x86_64:  $OUTPUT_DIR/android_x86_64/libthorvg-1.so"
