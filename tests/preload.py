"""Pre-load libthorvg shared library on platforms where rpath is unreliable.

Android's classloader-namespace (clns-*) blocks ``$ORIGIN`` rpath resolution
inside the testbed APK, so we must ``ctypes.CDLL`` the library by its full
path *before* importing any Cython extension that links against it.

Usage (in conftest.py, before any thorvg_cython import)::

    from preload import ensure_libthorvg
    ensure_libthorvg()
"""

import sys
from os import environ
from os.path import join, exists


def ensure_libthorvg() -> None:
    """Load ``libthorvg-1.so`` into the process on Android."""
    if sys.platform == "android":
        

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

    elif sys.platform == "ios":
        from platform import ios_ver
        if not ios_ver().is_simulator:
            # On real iOS devices, the .so is inside an .xcframework and rpath works fine.
            return
        
        # cibuildwheel passes THORVG_LIB_DIR in the environment
        # once thorvg is built, then we got
        # {project}/thorvg/output/thorvg.xcframework/ios-arm64_x86_64-simulator/thorvg.framework/thorvg

        # Installed layout:
        #   site-packages/thorvg_cython/
        #   site-packages/.frameworks/thorvg.xcframework/
        #       ios-arm64_x86_64-simulator/thorvg.framework/thorvg
        import ctypes
        import importlib.util
        from pathlib import Path

        # spec = importlib.util.find_spec("thorvg_cython")
        # if spec and spec.submodule_search_locations:
        #     pkg_dir = Path(spec.submodule_search_locations[0])
        # else:
        #     pkg_dir = Path(__file__).resolve().parent.parent

        # frameworks = pkg_dir.parent / ".frameworks"
        # xcfw = frameworks / "thorvg.xcframework"

        # The simulator slice is named ios-arm64_x86_64-simulator
        #sim_fw = xcfw / "ios-arm64_x86_64-simulator" / "thorvg.framework" / "thorvg"
        thor_lib_dir = environ.get("THORVG_LIB_DIR")
        thor_bin = join(thor_lib_dir, "thorvg.xcframework/ios-arm64_x86_64-simulator/thorvg.framework/thorvg") 
        if exists(thor_bin):
            ctypes.CDLL(str(thor_bin), mode=ctypes.RTLD_GLOBAL)

