#!/bin/bash
set -euo pipefail

# Download prebuilt ANGLE libraries from kivy/angle-builder.
# ANGLE translates OpenGL ES → Metal on Apple platforms.
#
# Usage:  bash download_angle.sh <platform> [output_dir]
#
# Platforms:
#   macos-arm64     - macOS arm64 dylibs
#   macos-x64       - macOS x86_64 dylibs
#   macos-universal - macOS fat (arm64+x86_64) dylibs
#   ios             - iOS xcframeworks (device + simulator)
#
# Output:
#   <output_dir>/angle/libEGL.dylib          (macOS)
#   <output_dir>/angle/libGLESv2.dylib       (macOS)
#   <output_dir>/angle/include/              (macOS)
#   <output_dir>/angle/libEGL.xcframework/   (iOS)
#   <output_dir>/angle/libGLESv2.xcframework/(iOS)
#   <output_dir>/angle/include/              (iOS)

ANGLE_VERSION="chromium-6943_rev1"
ANGLE_BASE_URL="https://github.com/kivy/angle-builder/releases/download/${ANGLE_VERSION}"

PLATFORM="${1:?Usage: download_angle.sh <platform> [output_dir]}"
OUTPUT_DIR="${2:-$(pwd)/output}"
ANGLE_DIR="$OUTPUT_DIR/angle"

# Map platform to artifact name
case "$PLATFORM" in
    macos-arm64)
        ARTIFACT="angle-macos-arm64"
        ;;
    macos-x64|macos-x86_64)
        ARTIFACT="angle-macos-x64"
        ;;
    macos-universal|macos-fat)
        ARTIFACT="angle-macos-universal"
        ;;
    ios|iphoneall)
        ARTIFACT="angle-iphoneall-universal"
        ;;
    *)
        echo "ERROR: Unknown platform: $PLATFORM"
        echo "Valid: macos-arm64, macos-x64, macos-universal, ios"
        exit 1
        ;;
esac

TARBALL="${ARTIFACT}.tar.gz"
URL="${ANGLE_BASE_URL}/${TARBALL}"

echo "=== ANGLE Download ==="
echo "Version:  $ANGLE_VERSION"
echo "Platform: $PLATFORM"
echo "Artifact: $TARBALL"
echo "Output:   $ANGLE_DIR"
echo ""

# Download
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

echo ">>> Downloading $URL ..."
curl -fsSL "$URL" -o "$TMPDIR/$TARBALL"
echo "<<< Downloaded"

# Extract
echo ">>> Extracting..."
mkdir -p "$TMPDIR/extracted"
tar -xzf "$TMPDIR/$TARBALL" -C "$TMPDIR/extracted"
echo "<<< Extracted"

# The tarball extracts to a folder named like the artifact
EXTRACTED="$TMPDIR/extracted/$ARTIFACT"
if [[ ! -d "$EXTRACTED" ]]; then
    # Some tarballs extract flat — check for files directly
    EXTRACTED="$TMPDIR/extracted"
fi

# Place files
rm -rf "$ANGLE_DIR"
mkdir -p "$ANGLE_DIR"

case "$PLATFORM" in
    macos-*)
        # Copy dylibs and headers
        cp "$EXTRACTED"/*.dylib "$ANGLE_DIR/" 2>/dev/null || true
        if [[ -d "$EXTRACTED/include" ]]; then
            cp -r "$EXTRACTED/include" "$ANGLE_DIR/"
        fi
        echo ""
        echo "=== ANGLE macOS Download Complete ==="
        ls -lh "$ANGLE_DIR"/*.dylib 2>/dev/null || echo "(no dylibs found)"
        ;;
    ios|iphoneall)
        # Copy xcframeworks and headers
        cp -r "$EXTRACTED"/*.xcframework "$ANGLE_DIR/" 2>/dev/null || true
        if [[ -d "$EXTRACTED/include" ]]; then
            cp -r "$EXTRACTED/include" "$ANGLE_DIR/"
        fi
        echo ""
        echo "=== ANGLE iOS Download Complete ==="
        ls -d "$ANGLE_DIR"/*.xcframework 2>/dev/null || echo "(no xcframeworks found)"
        ;;
esac
