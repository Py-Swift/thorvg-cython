#!/usr/bin/env python3
"""
setup.py for thorvg-cython.

Platform-aware linking:
  - iOS   (sys.platform == "ios"):   link via -framework against thorvg.xcframework
  - macOS (sys.platform == "darwin"): link against libthorvg dylib / static lib
  - Linux / other:                    link against libthorvg shared lib

Designed to work with cibuildwheel for automated wheel builds.
"""
import os
import sys
import subprocess
import sysconfig
from pathlib import Path

from setuptools import Extension, find_packages, setup
from Cython.Build import cythonize

# ---------------------------------------------------------------------------
#  Auto-detect SDKROOT on Apple platforms (macOS / iOS)
#
#  cibuildwheel and `uv build --python-platform` inject sys.platform:
#    "darwin" → macOS,  "ios" → iOS device/simulator
#  We pick the right SDK so callers never need to export SDKROOT manually.
# ---------------------------------------------------------------------------
if sys.platform in ("darwin", "ios") and "SDKROOT" not in os.environ:
    # Map platform → xcrun SDK name
    _SDK_MAP = {
        "darwin": "macosx",
        "ios":    "iphoneos",
    }
    # PLATFORM_NAME is set by Xcode / xcodebuild; prefer it for simulator
    _xcode_pn = os.environ.get("PLATFORM_NAME", "")
    if "simulator" in _xcode_pn.lower():
        _sdk_name = "iphonesimulator"
    else:
        _sdk_name = _SDK_MAP.get(sys.platform, "macosx")
    try:
        sdk = subprocess.check_output(
            ["xcrun", "--sdk", _sdk_name, "--show-sdk-path"], text=True
        ).strip()
        if sdk:
            os.environ["SDKROOT"] = sdk
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

# ---------------------------------------------------------------------------
#  Resolve paths
# ---------------------------------------------------------------------------
HERE = Path(__file__).resolve().parent
THORVG_ROOT = Path(os.environ.get("THORVG_ROOT", HERE / "thorvg"))
# Ensure THORVG_ROOT is absolute so include / lib paths survive cwd changes
# (e.g. when python -m build invokes the compiler from a temp directory).
if not THORVG_ROOT.is_absolute():
    THORVG_ROOT = (HERE / THORVG_ROOT).resolve()

# Where the C API header lives (thorvg_capi.h)
THORVG_INCLUDE = os.environ.get(
    "THORVG_INCLUDE",
    str(THORVG_ROOT / "inc"),
)

# Where the built libraries live — check common build dirs
def _resolve_lib_dir() -> str:
    env_val = os.environ.get("THORVG_LIB_DIR")
    if env_val:
        p = Path(env_val)
        if not p.is_absolute():
            p = (HERE / p).resolve()
        return str(p)
    # Prefer builddir_capi (built with -Dbindings=capi)
    for candidate in [
        THORVG_ROOT / "builddir_capi" / "src",
        THORVG_ROOT / "builddir" / "src",
        THORVG_ROOT / "build" / "src",
        THORVG_ROOT / "output",
    ]:
        if candidate.exists():
            return str(candidate)
    return str(THORVG_ROOT / "output")

THORVG_LIB_DIR = _resolve_lib_dir()

# Path to the XCFramework (iOS / macOS when using framework)
THORVG_XCFRAMEWORK = os.environ.get(
    "THORVG_XCFRAMEWORK",
    str(THORVG_ROOT / "output" / "thorvg.xcframework"),
)

# Also look for the CAPI header inside the thorvg source tree
THORVG_CAPI_INCLUDE = os.environ.get(
    "THORVG_CAPI_INCLUDE",
    str(THORVG_ROOT / "src" / "bindings" / "capi"),
)

# --- DEBUG: print resolved paths so CI logs show what's happening ----------
_capi_header = Path(THORVG_CAPI_INCLUDE) / "thorvg_capi.h"
print(f"[setup.py] HERE              = {HERE}")
print(f"[setup.py] THORVG_ROOT       = {THORVG_ROOT}  (exists={THORVG_ROOT.exists()})")
print(f"[setup.py] THORVG_INCLUDE    = {THORVG_INCLUDE}")
print(f"[setup.py] THORVG_CAPI_INCLUDE = {THORVG_CAPI_INCLUDE}")
print(f"[setup.py] thorvg_capi.h     = {_capi_header}  (exists={_capi_header.exists()})")
print(f"[setup.py] THORVG_LIB_DIR    = {THORVG_LIB_DIR}  (exists={Path(THORVG_LIB_DIR).exists()})")
if THORVG_ROOT.exists():
    print(f"[setup.py] THORVG_ROOT ls    = {list(THORVG_ROOT.iterdir())}")
# --- END DEBUG -------------------------------------------------------------

# ---------------------------------------------------------------------------
#  Platform detection
# ---------------------------------------------------------------------------
# sys.platform values:
#   "ios"    – CPython for iOS (PEP 730, Python 3.13+)
#   "darwin" – macOS
#   "linux"  – Linux
#   "win32"  – Windows
#   "android"– Android (PEP 738, Python 3.13+)
PLATFORM = sys.platform

# For cross-compilation via cibuildwheel, _PYTHON_HOST_PLATFORM or
# ARCHFLAGS may hint at the target.  Also check the Xcode PLATFORM_NAME
# env var set by Xcode / xcodebuild.
_xcode_platform = os.environ.get("PLATFORM_NAME", "")
_host_platform = os.environ.get("_PYTHON_HOST_PLATFORM", "")
_archflags = os.environ.get("ARCHFLAGS", "")

def _is_ios_build() -> bool:
    """Detect whether we are cross-compiling for iOS."""
    if PLATFORM == "ios":
        return True
    if "iphone" in _xcode_platform.lower():
        return True
    if "ios" in _host_platform.lower():
        return True
    return False

def _is_macos_build() -> bool:
    if PLATFORM == "darwin":
        return True
    if "macos" in _xcode_platform.lower():
        return True
    return False

def _get_arch() -> str:
    """Best-effort target architecture."""
    if _archflags:
        for part in _archflags.split():
            if part in ("arm64", "x86_64", "aarch64"):
                return "arm64" if part == "aarch64" else part
    machine = sysconfig.get_config_var("HOST_GNU_TYPE") or ""
    if "aarch64" in machine or "arm64" in machine:
        return "arm64"
    if "x86_64" in machine:
        return "x86_64"
    import platform as _plat
    return _plat.machine()

# ---------------------------------------------------------------------------
#  Build the Extension kwargs per platform
# ---------------------------------------------------------------------------
include_dirs = [
    THORVG_INCLUDE,
    THORVG_CAPI_INCLUDE,
    str(HERE / "src" / "thorvg_cython"),
]

extra_compile_args = ["-std=c++17"]
extra_link_args = []
libraries = []
library_dirs = []

if _is_ios_build():
    # -----------------------------------------------------------------------
    #  iOS: link against the thorvg.xcframework static lib.
    #
    #  The XCFramework has slices like:
    #    thorvg.xcframework/ios-arm64/libthorvg.a
    #    thorvg.xcframework/ios-arm64_x86_64-simulator/libthorvg.a
    #
    #  Detect simulator vs device using platform.ios_ver() (PEP 730),
    #  falling back to sysconfig SOABI/MULTIARCH and env vars.
    # -----------------------------------------------------------------------
    arch = _get_arch()
    xcfw = Path(THORVG_XCFRAMEWORK)

    # Detect simulator - same approach as Kivy
    _is_simulator = False
    try:
        from platform import ios_ver
        _is_simulator = ios_ver().is_simulator
    except (ImportError, AttributeError):
        pass
    if not _is_simulator:
        _soabi = sysconfig.get_config_var("SOABI") or ""
        _multiarch = sysconfig.get_config_var("MULTIARCH") or ""
        if "simulator" in _soabi or "simulator" in _multiarch:
            _is_simulator = True
    if not _is_simulator:
        if "simulator" in _xcode_platform.lower() or "simulator" in _host_platform.lower():
            _is_simulator = True

    if _is_simulator:
        candidates = [
            xcfw / "ios-arm64_x86_64-simulator",
            xcfw / f"ios-{arch}-simulator",
        ]
    else:
        candidates = [
            xcfw / "ios-arm64",
            xcfw / f"ios-{arch}",
        ]

    lib_path = None
    for c in candidates:
        static = c / "libthorvg.a"
        if static.exists():
            lib_path = str(static)
            break

    if lib_path:
        extra_link_args.extend([lib_path])
    else:
        # Fallback: let the linker search
        library_dirs.append(str(xcfw))
        libraries.append("thorvg")

    # iOS needs these system frameworks
    extra_link_args.extend([
        "-framework", "Foundation",
        "-framework", "CoreGraphics",
    ])

    # Minimum deployment target
    ios_target = os.environ.get("IPHONEOS_DEPLOYMENT_TARGET", "13.0")
    extra_compile_args.append(f"-mios-version-min={ios_target}")
    extra_link_args.append(f"-mios-version-min={ios_target}")

elif _is_macos_build():
    # -----------------------------------------------------------------------
    #  macOS: link against static lib or dylib.
    #
    #  Priority:
    #    1. THORVG_LIB_DIR / libthorvg-1.a  (static, CAPI build)
    #    2. THORVG_LIB_DIR / libthorvg.a    (static)
    #    3. XCFramework macOS slice
    #    4. THORVG_LIB_DIR / libthorvg-1.dylib (shared)
    #    5. System search path
    # -----------------------------------------------------------------------
    arch = _get_arch()
    xcfw = Path(THORVG_XCFRAMEWORK)

    local_static_1 = Path(THORVG_LIB_DIR) / "libthorvg-1.a"
    local_static = Path(THORVG_LIB_DIR) / "libthorvg.a"
    macos_slice = xcfw / "macos-arm64_x86_64"
    macos_static = macos_slice / "libthorvg.a"
    local_dylib = Path(THORVG_LIB_DIR) / "libthorvg-1.dylib"

    if local_static_1.exists():
        extra_link_args.append(str(local_static_1))
    elif local_static.exists():
        extra_link_args.append(str(local_static))
    elif macos_static.exists():
        extra_link_args.append(str(macos_static))
    elif local_dylib.exists():
        library_dirs.append(THORVG_LIB_DIR)
        libraries.append("thorvg-1")
        extra_link_args.append(f"-Wl,-rpath,{THORVG_LIB_DIR}")
    else:
        # Fallback: hope the system can find it
        libraries.append("thorvg")

    macos_target = os.environ.get("MACOSX_DEPLOYMENT_TARGET", "11.0")
    extra_compile_args.append(f"-mmacosx-version-min={macos_target}")
    extra_link_args.append(f"-mmacosx-version-min={macos_target}")

elif sys.platform.startswith("win"):
    # -----------------------------------------------------------------------
    #  Windows: link against thorvg static lib.
    #
    #  build_windows.bat produces:
    #    output/windows_x64/thorvg.lib   (from meson static build)
    #  or the raw meson output:
    #    builddir_win/src/thorvg-1.lib
    #    builddir_win/src/libthorvg-1.a  (MinGW)
    #
    #  Search order:
    #    1. THORVG_LIB_DIR / thorvg.lib       (build_windows.bat output)
    #    2. THORVG_LIB_DIR / thorvg-1.lib     (raw meson MSVC output)
    #    3. THORVG_LIB_DIR / libthorvg-1.a    (raw meson MinGW output)
    #    4. output/windows_x64/thorvg.lib     (default build_windows.bat)
    #    5. Fallback: let linker search for "thorvg"
    # -----------------------------------------------------------------------
    _lib_dir = Path(THORVG_LIB_DIR)
    _win_static = _lib_dir / "thorvg.lib"
    _win_meson = _lib_dir / "thorvg-1.lib"
    _win_mingw = _lib_dir / "libthorvg-1.a"
    _win_default = THORVG_ROOT / "output" / "windows_x64" / "thorvg.lib"

    if _win_static.exists():
        library_dirs.append(THORVG_LIB_DIR)
        libraries.append("thorvg")
    elif _win_meson.exists():
        library_dirs.append(THORVG_LIB_DIR)
        libraries.append("thorvg-1")
    elif _win_mingw.exists():
        library_dirs.append(THORVG_LIB_DIR)
        libraries.append("thorvg-1")
    elif _win_default.exists():
        library_dirs.append(str(_win_default.parent))
        libraries.append("thorvg")
    else:
        library_dirs.append(THORVG_LIB_DIR)
        libraries.append("thorvg")

    extra_compile_args = ["/std:c++17", "/EHsc", "/DTVG_STATIC"]

elif sys.platform == "android":
    # -----------------------------------------------------------------------
    #  Android: link against static libthorvg.a
    #
    #  Priority:
    #    1. THORVG_LIB_DIR / libthorvg.a       (build_android.sh output)
    #    2. THORVG_LIB_DIR / libthorvg-1.a     (raw meson output)
    #    3. Fallback: let linker search for "thorvg"
    # -----------------------------------------------------------------------
    _lib_dir = Path(THORVG_LIB_DIR)
    _android_static = _lib_dir / "libthorvg.a"
    _android_static_1 = _lib_dir / "libthorvg-1.a"

    if _android_static.exists():
        extra_link_args.append(str(_android_static))
    elif _android_static_1.exists():
        extra_link_args.append(str(_android_static_1))
    else:
        library_dirs.append(THORVG_LIB_DIR)
        libraries.append("thorvg")

else:
    # -----------------------------------------------------------------------
    #  Linux / other: link against static libthorvg.a or shared .so
    #
    #  Priority:
    #    1. THORVG_LIB_DIR / libthorvg.a       (build_linux.sh output)
    #    2. THORVG_LIB_DIR / libthorvg-1.a     (raw meson output)
    #    3. Fallback: linker search with -Wl,-rpath
    # -----------------------------------------------------------------------
    _lib_dir = Path(THORVG_LIB_DIR)
    _linux_static = _lib_dir / "libthorvg.a"
    _linux_static_1 = _lib_dir / "libthorvg-1.a"

    if _linux_static.exists():
        extra_link_args.append(str(_linux_static))
    elif _linux_static_1.exists():
        extra_link_args.append(str(_linux_static_1))
    else:
        library_dirs.append(THORVG_LIB_DIR)
        libraries.append("thorvg")
        extra_link_args.append(f"-Wl,-rpath,{THORVG_LIB_DIR}")

# Append C++ standard library (macOS/iOS use libc++, Linux links libstdc++ automatically)
if sys.platform in ("darwin", "ios"):
    extra_link_args.append("-lc++")

# ---------------------------------------------------------------------------
#  Extension definition
# ---------------------------------------------------------------------------
ext_source = "src/thorvg_cython/thorvg.pyx"

extensions = cythonize(
    [
        Extension(
            name="thorvg_cython.thorvg",
            sources=[ext_source],
            include_dirs=include_dirs,
            library_dirs=library_dirs,
            libraries=libraries,
            extra_compile_args=extra_compile_args,
            extra_link_args=extra_link_args,
            language="c++",
        ),
    ],
    compiler_directives={
        "language_level": "3",
        "boundscheck": False,
        "wraparound": False,
    },
)

# ---------------------------------------------------------------------------
#  Setup
# ---------------------------------------------------------------------------
setup(
    name="thorvg-cython",
    version="1.0.0",
    description="Cython bindings for the ThorVG vector graphics library",
    long_description=(HERE / "README.md").read_text(encoding="utf-8")
        if (HERE / "README.md").exists() else "",
    long_description_content_type="text/markdown",
    author="ThorVG",
    license="MIT",
    url="https://github.com/thorvg/thorvg",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    exclude_package_data={"": ["*.cpp"]},
    ext_modules=extensions,
    python_requires=">=3.9",
    zip_safe=False,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Programming Language :: Cython",
        "Programming Language :: Python :: 3",
        "Operating System :: MacOS",
        "Operating System :: iOS",
        "Operating System :: POSIX :: Linux",
        "Operating System :: Microsoft :: Windows",
        "Topic :: Multimedia :: Graphics",
    ],
)
