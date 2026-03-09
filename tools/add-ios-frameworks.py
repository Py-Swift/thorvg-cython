#!/usr/bin/env python3
"""
Post-build script: inject thorvg.xcframework into iOS wheels.

Supports two modes:

1) repair-wheel-command (cibuildwheel):
     python tools/add-ios-frameworks.py <wheel> <dest_dir> --xcframework <path>
   Copies the wheel to dest_dir and injects the xcframework.

2) batch (manual / CI post-step):
     python tools/add-ios-frameworks.py <wheels_dir> --xcframework <path>
   Patches every .whl in the directory in-place.

After patching, each iOS wheel contains:
    .frameworks/thorvg.xcframework/...

This follows the BeeWare convention where .frameworks/ at
site-packages level is discovered by the host Xcode project.
"""
import argparse
import os
import shutil
import zipfile


def _resolve_xcframework(cli_path: str | None) -> str:
    """Resolve the xcframework path from CLI arg, env var, or default."""
    if cli_path:
        return cli_path
    if "THORVG_XCFRAMEWORK" in os.environ:
        return os.environ["THORVG_XCFRAMEWORK"]
    root = os.environ.get("THORVG_ROOT", "thorvg")
    return os.path.join(root, "output", "thorvg.xcframework")


def _inject_xcframework(whl_path: str, xcfw: str) -> int:
    """Open a wheel and inject xcframework files. Returns number of files added."""
    count = 0
    with zipfile.ZipFile(whl_path, "a", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as whl:
        for root, _dirs, files in os.walk(xcfw):
            for fname in files:
                file_path = os.path.join(root, fname)
                arcname = os.path.join(
                    ".frameworks",
                    os.path.relpath(file_path, os.path.dirname(xcfw)),
                )
                whl.write(file_path, arcname)
                count += 1
    return count


def repair_single_wheel(wheel: str, dest_dir: str, xcfw: str) -> None:
    """cibuildwheel repair-wheel-command mode: copy wheel to dest_dir, then inject."""
    if not os.path.isfile(wheel):
        raise FileNotFoundError(f"Wheel not found: {wheel}")
    if not os.path.isdir(xcfw):
        raise FileNotFoundError(
            f"thorvg.xcframework not found at: {xcfw}\n"
            "Pass --xcframework or set THORVG_XCFRAMEWORK env var."
        )
    os.makedirs(dest_dir, exist_ok=True)
    dest_wheel = os.path.join(dest_dir, os.path.basename(wheel))
    shutil.copy2(wheel, dest_wheel)
    n = _inject_xcframework(dest_wheel, xcfw)
    print(f"  -> added {n} framework files to {os.path.basename(dest_wheel)}")


def patch_wheels_dir(wheels_dir: str, xcfw: str) -> None:
    """Batch mode: patch every .whl in a directory in-place."""
    if not os.path.isdir(wheels_dir):
        raise FileNotFoundError(f"Wheels directory not found: {wheels_dir}")
    if not os.path.isdir(xcfw):
        raise FileNotFoundError(
            f"thorvg.xcframework not found at: {xcfw}\n"
            "Pass --xcframework or set THORVG_XCFRAMEWORK env var."
        )
    for whl_name in sorted(os.listdir(wheels_dir)):
        if not whl_name.endswith(".whl"):
            continue
        whl_path = os.path.join(wheels_dir, whl_name)
        print(f"Patching {whl_name} ...")
        n = _inject_xcframework(whl_path, xcfw)
        print(f"  -> added {n} framework files")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Inject thorvg.xcframework into iOS wheels (.frameworks/ folder)."
    )
    parser.add_argument(
        "positional",
        nargs="+",
        help="Either <wheel> <dest_dir> (repair mode) or <wheels_dir> (batch mode).",
    )
    parser.add_argument(
        "--xcframework",
        default=None,
        help="Path to thorvg.xcframework (default: $THORVG_XCFRAMEWORK or $THORVG_ROOT/output/thorvg.xcframework).",
    )
    args = parser.parse_args()
    xcfw = _resolve_xcframework(args.xcframework)

    if len(args.positional) == 2 and args.positional[0].endswith(".whl"):
        # repair-wheel-command mode: <wheel> <dest_dir>
        repair_single_wheel(args.positional[0], args.positional[1], xcfw)
    elif len(args.positional) == 1 and os.path.isdir(args.positional[0]):
        # batch mode: <wheels_dir>
        patch_wheels_dir(args.positional[0], xcfw)
    else:
        parser.error(
            "Usage: script.py <wheel.whl> <dest_dir> [--xcframework ...]\n"
            "       script.py <wheels_dir> [--xcframework ...]"
        )
