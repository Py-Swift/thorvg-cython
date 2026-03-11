#!/usr/bin/env python3
"""
iOS Testbed – set up and run thorvg-cython tests on the iOS Simulator.

Downloads BeeWare Python-Apple-support, sets up the testbed Xcode project,
installs the thorvg-cython wheel + pytest, injects xcframeworks, and runs
tests with ``xcodebuild test`` on a Simulator device.

Usage
-----
    python ios_testbench.py setup [--wheel <path>] [--workdir <dir>]
    python ios_testbench.py run   [--workdir <dir>] [--simulator <name>] [-v]
    python ios_testbench.py test  [--wheel <path>] [--workdir <dir>] [-v]

The ``test`` subcommand is a shortcut for ``setup`` followed by ``run``.

Requirements
    macOS with Xcode (xcodebuild, xcrun simctl)
    pip install pbxproj
"""
from __future__ import annotations

import argparse
import platform as _plat
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path

# ---------------------------------------------------------------------------
#  Constants
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent                   # thorvg-cython/
TESTS_DIR = PROJECT_DIR / "tests"
WHEELHOUSE = PROJECT_DIR / "wheelhouse"

BEEWARE_TAG = "3.13-b13"
BEEWARE_PYTHON = "3.13"
BEEWARE_URL = (
    "https://github.com/beeware/Python-Apple-support/releases/download/"
    f"{BEEWARE_TAG}/Python-{BEEWARE_PYTHON}-iOS-support."
    f"{BEEWARE_TAG.split('-')[1]}.tar.gz"
)

DEFAULT_WORKDIR = PROJECT_DIR / "build" / "ios-testbed"

# Test artefacts to copy into the testbed's app/ directory.
TEST_FILES = [
    "conftest.py",
    "preload.py",
    "test_engine.py",
    "test_canvas.py",
    "test_shape.py",
    "test_gradient.py",
    "test_pixelbuffer.py",
]


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------
def _run(cmd: list[str] | str, *, cwd: str | Path | None = None,
         env: dict | None = None, check: bool = True,
         capture: bool = False) -> subprocess.CompletedProcess:
    """Run *cmd*, echo it, and raise on failure."""
    if isinstance(cmd, list):
        print(f"  $ {' '.join(str(c) for c in cmd)}")
    else:
        print(f"  $ {cmd}")
    return subprocess.run(
        cmd, cwd=cwd, env=env, check=check,
        capture_output=capture, text=True,
    )


def _host_arch() -> str:
    """Detect the host CPU architecture (arm64 | x86_64).

    The iOS Simulator always matches the host architecture.
    """
    m = _plat.machine()
    if m in ("arm64", "aarch64"):
        return "arm64"
    if m in ("x86_64", "AMD64", "x86_64h"):
        return "x86_64"
    sys.exit(f"ERROR: unsupported host architecture: {m}")


def _find_wheel(wheelhouse: Path, arch: str) -> Path:
    """Locate the newest thorvg-cython iOS-simulator wheel for *arch*."""
    pattern = f"thorvg_cython-*-cp*-cp*-ios_*_{arch}_iphonesimulator.whl"
    matches = sorted(wheelhouse.glob(pattern))
    if not matches:
        sys.exit(
            f"ERROR: no wheel matching '{pattern}' in {wheelhouse}\n"
            "Build the iOS wheel first (see tools/build-apple-wheels.sh)."
        )
    return matches[-1]


# ---------------------------------------------------------------------------
#  Download & extraction
# ---------------------------------------------------------------------------
def _download_support(workdir: Path) -> Path:
    """Download and extract BeeWare Python-Apple-support.

    Returns the path to the ``testbed/`` directory inside *workdir*.
    """
    testbed_dir = workdir / "testbed"
    if testbed_dir.is_dir():
        print(f"[download] {testbed_dir} already exists – skipping")
        return testbed_dir

    workdir.mkdir(parents=True, exist_ok=True)
    tarball = workdir / "Python-iOS-support.tar.gz"

    # ---- fetch ----
    if not tarball.exists():
        print(f"[download] {BEEWARE_URL}")
        urllib.request.urlretrieve(BEEWARE_URL, str(tarball))
        print(f"[download] saved → {tarball}")

    # ---- extract ----
    print("[download] Extracting …")
    with tarfile.open(tarball) as tf:
        try:
            tf.extractall(workdir, filter="data")
        except TypeError:                                       # Python < 3.12
            tf.extractall(workdir)                              # noqa: S202

    # If the tarball wrapped everything inside a single top-level directory,
    # hoist the contents so testbed/ sits directly inside *workdir*.
    if not testbed_dir.is_dir():
        for child in workdir.iterdir():
            if child.is_dir() and (child / "testbed").is_dir():
                for item in list(child.iterdir()):
                    dest = workdir / item.name
                    if dest.exists():
                        shutil.rmtree(dest) if dest.is_dir() else dest.unlink()
                    item.rename(dest)
                child.rmdir()
                break

    if not testbed_dir.is_dir():
        sys.exit("ERROR: could not locate testbed/ after extraction")

    print(f"[download] Testbed ready at {testbed_dir}")
    return testbed_dir


# ---------------------------------------------------------------------------
#  Installation helpers
# ---------------------------------------------------------------------------
def _uv_platform(arch: str) -> str:
    """Return the ``--python-platform`` value for *arch* on iOS Simulator."""
    return f"{arch}-apple-ios-simulator"


def _install_wheel(wheel: Path, app_packages: Path, arch: str) -> None:
    """Install *wheel* into *app_packages* via ``uv pip install``.

    Uses ``--python-platform`` so uv resolves the correct iOS slice.
    This is the real validation: if the wheel was packaged correctly,
    ``.frameworks/`` with the xcframeworks will appear in *app_packages*.
    """
    app_packages.mkdir(parents=True, exist_ok=True)
    plat = _uv_platform(arch)
    print(f"[install] uv pip install {wheel.name}  (platform={plat})")
    _run([
        "uv", "pip", "install",
        str(wheel),
        "--python-platform", plat,
        "--target", str(app_packages),
    ])

    # Verify .frameworks/ was created by the wheel – this proves packaging
    dot_fw = app_packages / ".frameworks"
    if not dot_fw.is_dir():
        sys.exit(
            "ERROR: .frameworks/ not found after install.\n"
            "The wheel was not packaged with xcframeworks.\n"
            "Run tools/add-ios-frameworks.py on the wheel first."
        )


def _install_pytest(app_packages: Path, arch: str) -> None:
    """Install pytest (+ deps) into the testbed's *app_packages* via uv."""
    plat = _uv_platform(arch)
    print("[install] Installing pytest …")
    _run([
        "uv", "pip", "install",
        "pytest",
        "--python-platform", plat,
        "--target", str(app_packages),
    ])


def _copy_tests(app_dir: Path) -> None:
    """Copy project test files into the testbed's ``app/`` directory."""
    print("[setup] Copying tests → app/")
    app_dir.mkdir(parents=True, exist_ok=True)
    for name in TEST_FILES:
        src = TESTS_DIR / name
        if not src.exists():
            print(f"  SKIP (not found): {name}")
            continue
        shutil.copy2(src, app_dir / name)
        print(f"  {name}")


# ---------------------------------------------------------------------------
#  XCFramework handling
# ---------------------------------------------------------------------------
def _collect_xcframeworks(app_packages: Path) -> list[Path]:
    """Collect xcframeworks from ``app_packages/.frameworks/``.

    This directory is created by ``uv pip install`` from the wheel content.
    If it is missing or empty, the wheel was not packaged with xcframeworks
    and the test is considered a failure.
    """
    dot_fw = app_packages / ".frameworks"
    if not dot_fw.is_dir():
        sys.exit(
            "ERROR: .frameworks/ not found in app_packages.\n"
            "The wheel was not packaged correctly."
        )

    result: list[Path] = []
    for item in sorted(dot_fw.iterdir()):
        if item.suffix == ".xcframework" and item.is_dir():
            result.append(item)

    if not result:
        sys.exit(
            "ERROR: .frameworks/ exists but contains no .xcframework bundles.\n"
            "The wheel packaging is broken."
        )

    print(f"[xcfw] Found in wheel: {[p.name for p in result]}")
    return result


def _place_xcframeworks(testbed_dir: Path, xcframeworks: list[Path]) -> None:
    """Copy each xcframework into *testbed_dir* (beside Python.xcframework)."""
    for xcfw in xcframeworks:
        dest = testbed_dir / xcfw.name
        if dest.exists():
            shutil.rmtree(dest)
        print(f"[xcfw] {xcfw.name} → {testbed_dir.name}/")
        shutil.copytree(xcfw, dest, symlinks=True)


# ---------------------------------------------------------------------------
#  Xcode project patching (pbxproj)
# ---------------------------------------------------------------------------
def _ensure_pbxproj() -> None:
    """Install *pbxproj* if it is not already available."""
    try:
        import pbxproj  # noqa: F401
    except ImportError:
        print("[setup] Installing pbxproj …")
        _run([sys.executable, "-m", "pip", "install", "pbxproj", "--quiet"])


def _modify_xcodeproj(testbed_dir: Path) -> None:
    """Add thorvg + libomp xcframeworks to the iOSTestbed Xcode project."""
    _ensure_pbxproj()

    from pbxproj import XcodeProject
    from pbxproj.pbxextensions.ProjectFiles import FileOptions

    pbxproj_path = testbed_dir / "iOSTestbed.xcodeproj" / "project.pbxproj"
    if not pbxproj_path.exists():
        sys.exit(f"ERROR: {pbxproj_path} not found")

    print(f"[xcode] Patching {pbxproj_path.name} …")
    project = XcodeProject.load(str(pbxproj_path))

    options = FileOptions(
        create_build_files=True,
        weak=False,
        embed_framework=True,
        code_sign_on_copy=True,
    )

    for name in ("thorvg.xcframework", "libomp.xcframework"):
        if not (testbed_dir / name).is_dir():
            continue
        # Path is relative to the Xcode project source root (testbed_dir).
        project.add_file(name, file_options=options)
        print(f"  + {name}")

    project.save()
    print("[xcode] Saved.")


# ---------------------------------------------------------------------------
#  Subcommands
# ---------------------------------------------------------------------------
def cmd_setup(args: argparse.Namespace) -> Path:
    """Prepare the iOS testbed (download → install → patch)."""
    workdir = Path(args.workdir).resolve()
    arch = _host_arch()

    # ---- wheel ----
    if args.wheel:
        wheel = Path(args.wheel).resolve()
        if not wheel.exists():
            sys.exit(f"ERROR: wheel not found: {wheel}")
    else:
        wheel = _find_wheel(WHEELHOUSE, arch)

    print("=" * 50)
    print("  iOS testbed setup")
    print("=" * 50)
    print(f"  arch    : {arch}")
    print(f"  wheel   : {wheel.name}")
    print(f"  workdir : {workdir}")
    print()

    # 1 – Download BeeWare Python-Apple-support
    testbed_dir = _download_support(workdir)

    # 2 – Key paths inside the testbed
    app_dir = testbed_dir / "iOSTestbed" / "app"
    app_packages = testbed_dir / "iOSTestbed" / "app_packages"

    # 3 – Install the thorvg-cython wheel via uv pip
    #     This is part of the test: .frameworks/ must appear after install.
    _install_wheel(wheel, app_packages, arch)

    # 4 – Install pytest (+ transitive deps)
    _install_pytest(app_packages, arch)

    # 5 – Copy test suite into app/
    _copy_tests(app_dir)

    # 6 – Collect xcframeworks that the wheel placed in .frameworks/
    #     and move them beside Python.xcframework in the testbed root.
    xcframeworks = _collect_xcframeworks(app_packages)
    _place_xcframeworks(testbed_dir, xcframeworks)

    #   Clean .frameworks/ from app_packages (contents now live at testbed root)
    shutil.rmtree(app_packages / ".frameworks")

    # 7 – Patch the Xcode project
    _modify_xcodeproj(testbed_dir)

    print()
    print(f"Testbed ready: {testbed_dir}")
    print(f"Run tests:     python {Path(__file__).name} run --workdir {workdir}")
    return testbed_dir


def cmd_run(args: argparse.Namespace) -> None:
    """Run ``pytest -v`` on the iOS Simulator via the BeeWare testbed."""
    workdir = Path(args.workdir).resolve()
    testbed_dir = workdir / "testbed"

    if not (testbed_dir / "__main__.py").exists():
        sys.exit(
            f"ERROR: testbed not found at {testbed_dir}\n"
            f"Run setup first:  python {Path(__file__).name} setup"
        )

    cmd: list[str] = [sys.executable, str(testbed_dir), "run"]
    if getattr(args, "simulator", None):
        cmd += ["--simulator", args.simulator]
    if getattr(args, "verbose", False):
        cmd += ["--verbose"]
    cmd += ["--", "pytest", "-v"]

    print("=" * 50)
    print("  iOS testbed run")
    print("=" * 50)
    _run(cmd)


def cmd_test(args: argparse.Namespace) -> None:
    """Setup, then immediately run (convenience wrapper)."""
    cmd_setup(args)
    cmd_run(args)


# ---------------------------------------------------------------------------
#  CLI
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="iOS Testbed – test thorvg-cython on the iOS Simulator.",
    )
    sub = parser.add_subparsers(dest="command")

    # -- setup ---------------------------------------------------------------
    p_setup = sub.add_parser("setup",
                             help="Download, install, and patch the testbed")
    p_setup.add_argument("--wheel",
                         help="Path to the iOS wheel (auto-detected from wheelhouse/)")
    p_setup.add_argument("--workdir", default=str(DEFAULT_WORKDIR),
                         help="Working directory (default: build/ios-testbed)")

    # -- run -----------------------------------------------------------------
    p_run = sub.add_parser("run", help="Run tests on the Simulator")
    p_run.add_argument("--workdir", default=str(DEFAULT_WORKDIR))
    p_run.add_argument("--simulator",
                       help="Simulator device name (e.g. 'iPhone SE (3rd generation)')")
    p_run.add_argument("-v", "--verbose", action="store_true")

    # -- test (setup + run) --------------------------------------------------
    p_test = sub.add_parser("test", help="Setup and run in one shot")
    p_test.add_argument("--wheel",
                        help="Path to the iOS wheel")
    p_test.add_argument("--workdir", default=str(DEFAULT_WORKDIR))
    p_test.add_argument("--simulator",
                        help="Simulator device name")
    p_test.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args()

    if args.command == "setup":
        cmd_setup(args)
    elif args.command == "run":
        cmd_run(args)
    elif args.command == "test":
        cmd_test(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
