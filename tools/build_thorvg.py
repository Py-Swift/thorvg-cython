#!/usr/bin/env python3
"""
Unified build script for the thorvg C library.

Replaces the individual shell / batch scripts with a single Python
entry-point that works on every platform.

Usage
-----
    python build_thorvg.py <platform> [options]

Platforms
    linux           Native Linux build (x86_64 or aarch64)
    macos           macOS fat (arm64 + x86_64) via cross-compile + lipo
    ios             iOS device + simulator, produces .xcframework
    android         Android aarch64 + x86_64 via NDK cross-compile
    windows         Windows x64 (and optionally arm64)
    download-angle  Download pre-built ANGLE libraries

GPU support (optional)
    --gpu=gl        OpenGL          (linux, windows, android)
    --gpu=gles      OpenGL ES       (android)
    --gpu=angle     ANGLE (ES→Metal/D3D) (macos, ios, windows, android)
    --gpu=metal     Metal           (macos, ios) — not yet implemented

    If omitted, reads THORVG_GPU env var.  When neither is set the
    library is built with the software renderer only (-Dengines=sw).

Environment variable overrides
    THORVG_GPU          Default GPU backend (same values as --gpu)
    THORVG_GL_LIB       Path to custom OpenGL library
    THORVG_GLES_LIB     Path to custom OpenGL ES library
    THORVG_ANGLE_LIB    Path to custom ANGLE library directory
"""
from __future__ import annotations

import argparse
import os
import platform as _plat
import shutil
import subprocess
import sys
import tarfile
import tempfile
import textwrap
import urllib.request
from pathlib import Path

# ---------------------------------------------------------------------------
#  Constants
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
CROSS_DIR = SCRIPT_DIR / "cross"

ANGLE_VERSION = "chromium-6943_rev1"
ANGLE_BASE_URL = (
    f"https://github.com/kivy/angle-builder/releases/download/{ANGLE_VERSION}"
)

# Allowed GPU values per platform
_VALID_GPU: dict[str, set[str]] = {
    "linux":   {"gl"},
    "windows": {"gl", "angle"},
    "macos":   {"angle", "metal"},
    "ios":     {"angle", "metal"},
    "android": {"gl", "gles", "angle"},
}


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------
def _run(cmd: list[str] | str, *, cwd: str | Path | None = None,
         env: dict | None = None, shell: bool = False,
         capture: bool = False) -> subprocess.CompletedProcess:
    """Run a command, stream output, and raise on failure."""
    if not shell and isinstance(cmd, list):
        print(f"  $ {' '.join(str(c) for c in cmd)}")
    else:
        print(f"  $ {cmd}")
    return subprocess.run(
        cmd, cwd=cwd, env=env, shell=shell, check=True,
        capture_output=capture, text=True,
    )


def _ensure_tool(name: str) -> None:
    """Ensure *name* is on PATH, install via pip if possible."""
    if shutil.which(name):
        return
    if name in ("meson", "ninja"):
        print(f"[build] Installing {name} via pip ...")
        _run([sys.executable, "-m", "pip", "install", name])
    else:
        sys.exit(f"ERROR: '{name}' not found on PATH")


def _download_thorvg_source(version: str, dest: Path) -> None:
    """Download and extract the thorvg release tarball into *dest*.

    The tarball from GitHub unpacks as ``thorvg-<version>/``.  We rename
    it to *dest* so callers can rely on a stable path.
    """
    if dest.is_dir():
        print(f"[download] {dest} already exists – skipping download")
        return

    url = (
        f"https://github.com/thorvg/thorvg/archive/"
        f"refs/tags/v{version}.tar.gz"
    )
    parent = dest.parent
    parent.mkdir(parents=True, exist_ok=True)
    extracted = parent / f"thorvg-{version}"

    print(f"[download] Fetching thorvg v{version} …")
    print(f"  {url}")
    resp = urllib.request.urlopen(url, timeout=120)
    with tarfile.open(fileobj=resp, mode="r|gz") as tf:
        for member in tf:
            # Guard against path traversal
            resolved = (parent / member.name).resolve()
            if not str(resolved).startswith(str(parent.resolve())):
                raise RuntimeError(f"Unsafe tar member: {member.name}")
            tf.extract(member, path=str(parent))

    if not extracted.is_dir():
        sys.exit(f"ERROR: expected directory {extracted} after extraction")

    extracted.rename(dest)
    print(f"[download] thorvg source ready at {dest}")


def _validate_gpu(platform: str, gpu: str) -> None:
    """Raise if *gpu* is invalid for *platform*."""
    if not gpu:
        return
    allowed = _VALID_GPU.get(platform, set())
    if gpu not in allowed:
        hints = {
            "metal": (
                "Metal backend is not yet implemented in ThorVG. "
                "Expected in a future release."
            ),
            "angle": {
                "linux": "ANGLE is not supported on Linux. Use --gpu=gl.",
            },
            "gl": {
                "macos": (
                    "Native OpenGL is deprecated on Apple platforms. "
                    "Use --gpu=angle."
                ),
                "ios": (
                    "Native OpenGL is deprecated on Apple platforms. "
                    "Use --gpu=angle."
                ),
            },
            "gles": {
                "macos": (
                    "OpenGL ES without ANGLE is not available on Apple "
                    "platforms. Use --gpu=angle."
                ),
                "ios": (
                    "OpenGL ES without ANGLE is not available on Apple "
                    "platforms. Use --gpu=angle."
                ),
            },
        }
        hint = hints.get(gpu)
        if isinstance(hint, dict):
            hint = hint.get(platform)
        if isinstance(hint, str):
            sys.exit(f"ERROR: {hint}")
        sys.exit(
            f"ERROR: --gpu={gpu} is not valid for {platform}. "
            f"Allowed: {', '.join(sorted(allowed)) or '(none)'}."
        )


# ---------------------------------------------------------------------------
#  Meson argument builder
# ---------------------------------------------------------------------------
def _meson_common(platform: str, gpu: str, *,
                  native: bool = False) -> list[str]:
    """Return the common meson setup arguments."""
    args = [
        "--buildtype=release",
        "--default-library=shared",
        "-Dthreads=true",
        "-Dbindings=capi",
        "-Dloaders=svg,lottie,ttf",
    ]

    # Engine + extra flags depend on GPU mode
    extras = ["lottie_exp"]

    if gpu:
        args.append("-Dengines=sw,gl")
        # OpenGL ES extra is needed for gles / angle backends
        if gpu in ("gles", "angle"):
            extras.append("opengl_es")
        # Linux native build needs -ldl for GL engine's dlopen/dlsym
        if native and platform == "linux":
            args.append("-Dcpp_link_args=-ldl")
    else:
        args.append("-Dengines=sw")

    args.append(f"-Dextra={','.join(extras)}")
    return args


# ---------------------------------------------------------------------------
#  Platform: Linux
# ---------------------------------------------------------------------------
def build_linux(root: Path, gpu: str) -> None:
    """Build thorvg for the native Linux architecture."""
    _ensure_tool("meson")
    _ensure_tool("ninja")

    build_root = root / "build_linux"
    output_dir = root / "output"
    arch = _plat.machine()

    print("=== ThorVG Linux Build ===")
    print(f"Root: {root}")
    print(f"Arch: {arch}")
    print(f"GPU:  {gpu or 'disabled'}")
    print()

    if build_root.exists():
        shutil.rmtree(build_root)
    output_dir.mkdir(parents=True, exist_ok=True)

    build_dir = build_root / arch
    out_dir = output_dir / f"linux_{arch}"

    meson_args = _meson_common("linux", gpu, native=True)

    print(f">>> Building: linux_{arch}")
    _run(["meson", "setup", str(build_dir)] + meson_args, cwd=root)
    _run(["ninja", "-C", str(build_dir)], cwd=root)
    print(f"<<< Done: linux_{arch}\n")

    out_dir.mkdir(parents=True, exist_ok=True)
    for f in build_dir.glob("src/libthorvg-1.so*"):
        if f.is_file():
            shutil.copy2(str(f), str(out_dir / f.name))

    print("=== Build Complete ===")
    print(f"Shared library: {out_dir / 'libthorvg-1.so'}")


# ---------------------------------------------------------------------------
#  Platform: macOS
# ---------------------------------------------------------------------------
def build_macos(root: Path, gpu: str) -> None:
    """Build thorvg for macOS (arm64, x86_64, fat binary)."""
    _ensure_tool("meson")
    _ensure_tool("ninja")

    build_root = root / "build_macos"
    output_dir = root / "output"
    meson_args = _meson_common("macos", gpu)

    print("=== ThorVG macOS Build ===")
    print(f"Root: {root}")
    print(f"GPU:  {gpu or 'disabled'}")
    print()

    if build_root.exists():
        shutil.rmtree(build_root)
    output_dir.mkdir(parents=True, exist_ok=True)

    def _build(name: str, cross_file: Path) -> None:
        bd = build_root / name
        print(f">>> Building: {name}")
        _run(
            ["meson", "setup", str(bd), "--cross-file", str(cross_file)]
            + meson_args,
            cwd=root,
        )
        _run(["ninja", "-C", str(bd)], cwd=root)
        print(f"<<< Done: {name}\n")

    _build("macos_arm64", CROSS_DIR / "macos_arm64.txt")
    _build("macos_x86_64", CROSS_DIR / "macos_x86_64.txt")

    # Copy individual arch outputs
    for name in ("macos_arm64", "macos_x86_64"):
        dst = output_dir / name
        dst.mkdir(parents=True, exist_ok=True)
        shutil.copy2(
            str(build_root / name / "src" / "libthorvg-1.dylib"),
            str(dst / "libthorvg-1.dylib"),
        )

    # Fat binary via lipo
    print(">>> Creating macOS fat dylib with lipo...")
    fat_dir = output_dir / "macos_fat"
    fat_dir.mkdir(parents=True, exist_ok=True)
    _run([
        "lipo", "-create",
        str(build_root / "macos_arm64" / "src" / "libthorvg-1.dylib"),
        str(build_root / "macos_x86_64" / "src" / "libthorvg-1.dylib"),
        "-output", str(fat_dir / "libthorvg-1.dylib"),
    ])
    print("<<< Fat dylib created\n")

    print("=== Build Complete ===")
    print(f"  macOS arm64:  {output_dir / 'macos_arm64' / 'libthorvg-1.dylib'}")
    print(f"  macOS x86_64: {output_dir / 'macos_x86_64' / 'libthorvg-1.dylib'}")
    print(f"  macOS fat:    {fat_dir / 'libthorvg-1.dylib'}")


# ---------------------------------------------------------------------------
#  Platform: iOS
# ---------------------------------------------------------------------------
def build_ios(root: Path, gpu: str) -> None:
    """Build thorvg for iOS device + simulator, produce XCFramework."""
    _ensure_tool("meson")
    _ensure_tool("ninja")

    build_root = root / "build_ios"
    output_dir = root / "output"
    meson_args = _meson_common("ios", gpu)

    print("=== ThorVG iOS Build ===")
    print(f"Root: {root}")
    print(f"GPU:  {gpu or 'disabled'}")
    print()

    if build_root.exists():
        shutil.rmtree(build_root)
    output_dir.mkdir(parents=True, exist_ok=True)

    def _build(name: str, cross_file: Path) -> None:
        bd = build_root / name
        print(f">>> Building: {name}")
        _run(
            ["meson", "setup", str(bd), "--cross-file", str(cross_file)]
            + meson_args,
            cwd=root,
        )
        _run(["ninja", "-C", str(bd)], cwd=root)
        print(f"<<< Done: {name}\n")

    _build("ios_arm64", CROSS_DIR / "ios_arm64.txt")
    _build("ios_sim_arm64", CROSS_DIR / "ios_simulator_arm64.txt")
    _build("ios_sim_x86_64", CROSS_DIR / "ios_simulator_x86_64.txt")

    # --- .framework bundles ---
    def _make_framework(dylib_path: Path, fw_output_dir: Path) -> None:
        fw_dir = fw_output_dir / "thorvg.framework"
        fw_dir.mkdir(parents=True, exist_ok=True)
        (fw_dir / "Headers").mkdir(exist_ok=True)

        shutil.copy2(str(dylib_path), str(fw_dir / "thorvg"))
        _run([
            "install_name_tool", "-id",
            "@rpath/thorvg.framework/thorvg",
            str(fw_dir / "thorvg"),
        ])
        shutil.copy2(
            str(root / "inc" / "thorvg.h"),
            str(fw_dir / "Headers" / "thorvg.h"),
        )
        # Info.plist
        (fw_dir / "Info.plist").write_text(textwrap.dedent("""\
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
        """))
        print(f"    Created: {fw_dir}")

    print(">>> Creating .framework bundles...")

    # Device
    _make_framework(
        build_root / "ios_arm64" / "src" / "libthorvg-1.dylib",
        output_dir / "ios_arm64",
    )

    # Simulator fat (arm64 + x86_64)
    sim_fat_dir = output_dir / "ios_sim_fat"
    sim_fat_dir.mkdir(parents=True, exist_ok=True)

    _run([
        "lipo", "-create",
        str(build_root / "ios_sim_arm64" / "src" / "libthorvg-1.dylib"),
        str(build_root / "ios_sim_x86_64" / "src" / "libthorvg-1.dylib"),
        "-output", str(sim_fat_dir / "libthorvg-1.dylib"),
    ])
    _make_framework(sim_fat_dir / "libthorvg-1.dylib", sim_fat_dir)
    (sim_fat_dir / "libthorvg-1.dylib").unlink()

    print("<<< .framework bundles created\n")

    # --- XCFramework ---
    print(">>> Creating XCFramework...")
    xcfw = output_dir / "thorvg.xcframework"
    if xcfw.exists():
        shutil.rmtree(xcfw)
    _run([
        "xcodebuild", "-create-xcframework",
        "-framework", str(output_dir / "ios_arm64" / "thorvg.framework"),
        "-framework", str(sim_fat_dir / "thorvg.framework"),
        "-output", str(xcfw),
    ])

    print()
    print("=== Build Complete ===")
    print(f"XCFramework: {xcfw}")
    print()
    print("Contents:")
    print("  Device:    thorvg.xcframework/ios-arm64/thorvg.framework/thorvg")
    print("  Simulator: thorvg.xcframework/ios-arm64_x86_64-simulator/"
          "thorvg.framework/thorvg")
    print()
    print("Install name: @rpath/thorvg.framework/thorvg")


# ---------------------------------------------------------------------------
#  Platform: Android
# ---------------------------------------------------------------------------
def build_android(root: Path, gpu: str, *, ndk: str = "",
                  api: int = 24) -> None:
    """Build thorvg for Android (aarch64 + x86_64)."""
    _ensure_tool("meson")
    _ensure_tool("ninja")

    ndk_path = ndk or os.environ.get("ANDROID_NDK_HOME") or os.environ.get(
        "ANDROID_NDK", ""
    )
    if not ndk_path:
        sys.exit(
            "ERROR: Android NDK path not specified.\n"
            "Pass --ndk=<path> or set ANDROID_NDK_HOME env var."
        )
    ndk_dir = Path(ndk_path)
    if not ndk_dir.is_dir():
        sys.exit(f"ERROR: NDK path does not exist: {ndk_dir}")

    # Detect host tag
    os_name = _plat.system()
    machine = _plat.machine()
    if os_name == "Linux":
        host_tag = "linux-x86_64" if machine == "x86_64" else "linux-aarch64"
    elif os_name == "Darwin":
        host_tag = "darwin-x86_64"  # NDK ships x86_64 on macOS
    else:
        host_tag = "linux-x86_64"

    build_root = root / "build_android"
    output_dir = root / "output"
    meson_args = _meson_common("android", gpu)

    print("=== ThorVG Android Build ===")
    print(f"Root:      {root}")
    print(f"NDK:       {ndk_dir}")
    print(f"HOST_TAG:  {host_tag}")
    print(f"API level: {api}")
    print(f"GPU:       {gpu or 'disabled'}")
    print()

    if build_root.exists():
        shutil.rmtree(build_root)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate cross files from templates
    gen_cross_dir = build_root / "cross"
    gen_cross_dir.mkdir(parents=True, exist_ok=True)

    def _generate_cross(template: Path, out: Path) -> None:
        content = template.read_text()
        content = content.replace("NDK", str(ndk_dir))
        content = content.replace("HOST_TAG", host_tag)
        content = content.replace("API", str(api))
        # Inject -ldl into cpp_link_args when GPU is enabled (needs dlopen)
        if gpu:
            # The template already may have -ldl; if not, add it
            if "-ldl" not in content:
                content = content.replace(
                    "cpp_link_args = []",
                    "cpp_link_args = ['-ldl']",
                )
        else:
            # Strip -ldl when no GPU (not needed for SW-only)
            content = content.replace(
                "cpp_link_args = ['-ldl']",
                "cpp_link_args = []",
            )
        out.write_text(content)
        print(f"  Generated cross file: {out}")

    _generate_cross(
        CROSS_DIR / "android_aarch64.txt",
        gen_cross_dir / "android_aarch64.txt",
    )
    _generate_cross(
        CROSS_DIR / "android_x86_64.txt",
        gen_cross_dir / "android_x86_64.txt",
    )
    print()

    def _build(name: str, cross_file: Path) -> None:
        bd = build_root / name
        print(f">>> Building: {name}")
        _run(
            ["meson", "setup", str(bd), "--cross-file", str(cross_file)]
            + meson_args,
            cwd=root,
        )
        _run(["ninja", "-C", str(bd)], cwd=root)
        print(f"<<< Done: {name}\n")

    _build("android_aarch64", gen_cross_dir / "android_aarch64.txt")
    _build("android_x86_64", gen_cross_dir / "android_x86_64.txt")

    # Copy outputs
    for arch_name in ("android_aarch64", "android_x86_64"):
        dst = output_dir / arch_name
        dst.mkdir(parents=True, exist_ok=True)
        shutil.copy2(
            str(build_root / arch_name / "src" / "libthorvg-1.so"),
            str(dst / "libthorvg-1.so"),
        )

    print("=== Build Complete ===")
    print(f"  Android aarch64: {output_dir / 'android_aarch64' / 'libthorvg-1.so'}")
    print(f"  Android x86_64:  {output_dir / 'android_x86_64' / 'libthorvg-1.so'}")


# ---------------------------------------------------------------------------
#  Platform: Windows
# ---------------------------------------------------------------------------
def build_windows(root: Path, gpu: str, *, arch: str = "x64") -> None:
    """Build thorvg for Windows."""
    _ensure_tool("meson")
    _ensure_tool("ninja")

    build_root = root / "build_windows"
    output_dir = root / "output"

    # Remove Strawberry Perl from PATH (its ccache intercepts cl.exe)
    env = os.environ.copy()
    for strawberry in (
        r"C:\Strawberry\c\bin",
        r"C:\Strawberry\perl\site\bin",
        r"C:\Strawberry\perl\bin",
    ):
        env["PATH"] = env.get("PATH", "").replace(strawberry + ";", "")

    meson_args = ["--vsenv"] + _meson_common("windows", gpu)

    print("=== ThorVG Windows Build ===")
    print(f"Root: {root}")
    print(f"Arch: {arch}")
    print(f"GPU:  {gpu or 'disabled'}")
    print()

    if build_root.exists():
        shutil.rmtree(build_root)
    output_dir.mkdir(parents=True, exist_ok=True)

    arches = ["x64", "arm64"] if arch == "all" else [arch]

    for a in arches:
        bd = build_root / a
        out = output_dir / f"windows_{a}"

        setup_args = ["meson", "setup", str(bd)] + meson_args
        if a == "arm64":
            setup_args.extend([
                "--cross-file", str(CROSS_DIR / "windows_arm64.txt")
            ])

        print(f">>> Building: windows_{a}")
        _run(setup_args, cwd=root, env=env)
        _run(["meson", "compile", "-C", str(bd)], cwd=root, env=env)
        print(f"<<< Done: windows_{a}\n")

        out.mkdir(parents=True, exist_ok=True)
        dll = bd / "src" / "thorvg-1.dll"
        lib = bd / "src" / "thorvg-1.lib"
        if dll.exists():
            shutil.copy2(str(dll), str(out / "thorvg-1.dll"))
        else:
            sys.exit(f"FAILED: Could not find thorvg-1.dll in {bd / 'src'}")
        if lib.exists():
            shutil.copy2(str(lib), str(out / "thorvg-1.lib"))
        else:
            print(f"WARNING: Could not find import lib thorvg-1.lib")

    print("=== Build Complete ===")
    for a in arches:
        out = output_dir / f"windows_{a}"
        if (out / "thorvg-1.dll").exists():
            print(f"  {a}: {out / 'thorvg-1.dll'}")


# ---------------------------------------------------------------------------
#  Download ANGLE
# ---------------------------------------------------------------------------
def download_angle(platform_name: str, output_dir: Path) -> None:
    """Download pre-built ANGLE libraries from kivy/angle-builder."""
    artifact_map = {
        "macos-arm64": "angle-macos-arm64",
        "macos-x64": "angle-macos-x64",
        "macos-x86_64": "angle-macos-x64",
        "macos-universal": "angle-macos-universal",
        "macos-fat": "angle-macos-universal",
        "ios": "angle-iphoneall-universal",
        "iphoneall": "angle-iphoneall-universal",
        # Windows ANGLE — kivy/angle-builder releases these as well
        "windows-x64": "angle-windows-x64",
        "windows": "angle-windows-x64",
    }

    artifact = artifact_map.get(platform_name)
    if not artifact:
        sys.exit(
            f"ERROR: Unknown ANGLE platform: {platform_name}\n"
            f"Valid: {', '.join(sorted(artifact_map.keys()))}"
        )

    tarball = f"{artifact}.tar.gz"
    url = f"{ANGLE_BASE_URL}/{tarball}"
    angle_dir = output_dir / "angle"

    print("=== ANGLE Download ===")
    print(f"Version:  {ANGLE_VERSION}")
    print(f"Platform: {platform_name}")
    print(f"Artifact: {tarball}")
    print(f"Output:   {angle_dir}")
    print()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        dl_path = tmp / tarball

        print(f">>> Downloading {url} ...")
        _run(["curl", "-fsSL", url, "-o", str(dl_path)])
        print("<<< Downloaded")

        print(">>> Extracting...")
        extract_dir = tmp / "extracted"
        extract_dir.mkdir()
        _run(["tar", "-xzf", str(dl_path), "-C", str(extract_dir)])
        print("<<< Extracted")

        # The tarball may extract to a folder named like the artifact
        extracted = extract_dir / artifact
        if not extracted.is_dir():
            extracted = extract_dir

        # Place files
        if angle_dir.exists():
            shutil.rmtree(angle_dir)
        angle_dir.mkdir(parents=True, exist_ok=True)

        if platform_name.startswith("ios") or platform_name == "iphoneall":
            # Copy xcframeworks and headers
            for xcfw in extracted.glob("*.xcframework"):
                shutil.copytree(str(xcfw), str(angle_dir / xcfw.name))
            inc = extracted / "include"
            if inc.is_dir():
                shutil.copytree(str(inc), str(angle_dir / "include"))
            print()
            print("=== ANGLE iOS Download Complete ===")
            for xcfw in sorted(angle_dir.glob("*.xcframework")):
                print(f"  {xcfw.name}")
        elif platform_name.startswith("windows"):
            # Copy DLLs, libs, and headers
            for dll in extracted.glob("*.dll"):
                shutil.copy2(str(dll), str(angle_dir / dll.name))
            for lib in extracted.glob("*.lib"):
                shutil.copy2(str(lib), str(angle_dir / lib.name))
            inc = extracted / "include"
            if inc.is_dir():
                shutil.copytree(str(inc), str(angle_dir / "include"))
            print()
            print("=== ANGLE Windows Download Complete ===")
            for f in sorted(angle_dir.glob("*.*")):
                if f.is_file():
                    print(f"  {f.name}")
        else:
            # macOS: copy dylibs and headers
            for dylib in extracted.glob("*.dylib"):
                shutil.copy2(str(dylib), str(angle_dir / dylib.name))
            inc = extracted / "include"
            if inc.is_dir():
                shutil.copytree(str(inc), str(angle_dir / "include"))
            print()
            print("=== ANGLE macOS Download Complete ===")
            for f in sorted(angle_dir.glob("*.dylib")):
                print(f"  {f.name}")


# ---------------------------------------------------------------------------
#  CLI
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the thorvg shared library for various platforms.",
    )
    sub = parser.add_subparsers(dest="platform", required=True)

    # --- common options added to every subcommand ---
    def _add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "--thorvg-root", default=None,
            help="Path to thorvg source (default: THORVG_ROOT env or ../thorvg)",
        )
        p.add_argument(
            "--version", default=None, dest="thorvg_version",
            help=(
                "ThorVG release version (e.g. 1.0.1).  When supplied and "
                "--thorvg-root does not yet exist, the source tarball is "
                "downloaded and extracted automatically."
            ),
        )
        p.add_argument(
            "--gpu", default=None,
            choices=["gl", "gles", "angle", "metal", ""],
            help="GPU backend (default: THORVG_GPU env var, or disabled)",
        )

    # linux
    p_linux = sub.add_parser("linux", help="Build for Linux (native arch)")
    _add_common(p_linux)

    # macos
    p_macos = sub.add_parser("macos", help="Build for macOS (fat binary)")
    _add_common(p_macos)

    # ios
    p_ios = sub.add_parser("ios", help="Build for iOS (XCFramework)")
    _add_common(p_ios)

    # android
    p_android = sub.add_parser("android", help="Build for Android")
    _add_common(p_android)
    p_android.add_argument("--ndk", default="", help="Android NDK path")
    p_android.add_argument(
        "--api", type=int, default=24, help="Android API level (default: 24)"
    )

    # windows
    p_win = sub.add_parser("windows", help="Build for Windows")
    _add_common(p_win)
    p_win.add_argument(
        "--arch", default="x64", choices=["x64", "arm64", "all"],
        help="Target architecture (default: x64)",
    )

    # download-angle
    p_angle = sub.add_parser(
        "download-angle", help="Download pre-built ANGLE libraries"
    )
    p_angle.add_argument(
        "angle_platform",
        choices=[
            "macos-arm64", "macos-x64", "macos-x86_64",
            "macos-universal", "macos-fat",
            "ios", "iphoneall",
            "windows-x64", "windows",
        ],
        help="Target platform for ANGLE download",
    )
    p_angle.add_argument(
        "--output", default=None,
        help="Output directory (default: <thorvg-root>/output)",
    )
    p_angle.add_argument(
        "--thorvg-root", default=None,
        help="Path to thorvg source (used for default output dir)",
    )

    args = parser.parse_args()

    # --- resolve thorvg root ---
    if args.thorvg_root:
        root = Path(args.thorvg_root).resolve()
    else:
        env_root = os.environ.get("THORVG_ROOT")
        if env_root:
            root = Path(env_root).resolve()
        else:
            root = SCRIPT_DIR.parent / "thorvg"

    # --- auto-download when --version is given and root is missing ---
    version = getattr(args, "thorvg_version", None) or os.environ.get(
        "THORVG_VERSION", ""
    )
    if not root.is_dir() and version:
        _download_thorvg_source(version, root)

    if not root.is_dir():
        sys.exit(f"ERROR: thorvg root not found: {root}")

    # --- resolve GPU setting ---
    if args.platform != "download-angle":
        gpu = args.gpu if args.gpu is not None else os.environ.get(
            "THORVG_GPU", ""
        )
        gpu = gpu.strip().lower()
        _validate_gpu(args.platform, gpu)
    else:
        gpu = ""

    # --- dispatch ---
    if args.platform == "linux":
        build_linux(root, gpu)
    elif args.platform == "macos":
        build_macos(root, gpu)
    elif args.platform == "ios":
        build_ios(root, gpu)
    elif args.platform == "android":
        build_android(root, gpu, ndk=args.ndk, api=args.api)
    elif args.platform == "windows":
        build_windows(root, gpu, arch=args.arch)
    elif args.platform == "download-angle":
        out = Path(args.output).resolve() if args.output else root / "output"
        download_angle(args.angle_platform, out)


if __name__ == "__main__":
    main()
