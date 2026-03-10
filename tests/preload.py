"""Pre-load libthorvg shared library on platforms where rpath is unreliable.

Android's classloader-namespace (clns-*) blocks ``$ORIGIN`` rpath resolution
inside the testbed APK, so we must ``ctypes.CDLL`` the library by its full
path *before* importing any Cython extension that links against it.

Usage (in conftest.py, before any thorvg_cython import)::

    from preload import ensure_libthorvg
    ensure_libthorvg()
"""

import sys


def ensure_libthorvg() -> None:
    """Load ``libthorvg-1.so`` into the process on Android."""
    if sys.platform != "android":
        return

    import ctypes
    from pathlib import Path

    # The .so sits next to the Cython extensions inside the installed package.
    pkg_dir = Path(__file__).resolve().parent.parent  # tests/ → project root
    # At test-time the wheel is already installed; find the package location.
    try:
        import importlib.util

        spec = importlib.util.find_spec("thorvg_cython")
        if spec and spec.submodule_search_locations:
            pkg_dir = Path(spec.submodule_search_locations[0])
    except Exception:
        pass

    lib = pkg_dir / "libthorvg-1.so"
    if lib.exists():
        ctypes.CDLL(str(lib), mode=ctypes.RTLD_GLOBAL)
