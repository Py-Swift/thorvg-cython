"""thorvg-cython — Cython bindings for the ThorVG C API."""

__version__ = "1.0.0"

# ---------------------------------------------------------------------------
#  Pre-load the bundled thorvg shared library before importing Cython
#  extensions.  On Android the classloader-namespace blocks $ORIGIN rpath
#  resolution, so we must load the library explicitly first.  This also
#  serves as a safety net on other platforms.
# ---------------------------------------------------------------------------
def _preload_thorvg() -> None:
    import ctypes
    import sys
    from pathlib import Path

    _pkg_dir = Path(__file__).resolve().parent

    if sys.platform == "android":
        _lib_name = "libthorvg-1.so"
    elif sys.platform == "darwin":
        _lib_name = "libthorvg-1.dylib"
    elif sys.platform == "ios":
        return  # framework loaded via @rpath at link time
    elif sys.platform == "win32":
        _lib_name = "thorvg-1.dll"
    else:
        _lib_name = "libthorvg-1.so"

    _lib_path = _pkg_dir / _lib_name
    if _lib_path.exists():
        ctypes.CDLL(str(_lib_path))

_preload_thorvg()
del _preload_thorvg

from .thorvg import (  # noqa: F401
    # Enums
    Result,
    Colorspace,
    EngineOption,
    MaskMethod,
    BlendMethod,
    TvgType,
    PathCommand,
    StrokeCap,
    StrokeJoin,
    StrokeFill,
    FillRule,
    TextWrap,
    FilterMethod,
    # Data classes
    ColorStop,
    Point,
    Matrix,
    TextMetrics,
    # Buffer
    PixelBuffer,
    # Core
    Engine,
    Canvas,
    Paint,
    Shape,
    Picture,
    Scene,
    Text,
    # Gradients
    Gradient,
    LinearGradient,
    RadialGradient,
    # Animation
    Animation,
    LottieAnimation,
    # Utilities
    Saver,
    Accessor,
)

from .sw_canvas import SwCanvas  # noqa: F401
from .gl_canvas import GlCanvas  # noqa: F401
