"""thorvg-cython — Cython bindings for the ThorVG C API."""

__version__ = "1.0.0"

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
    SwCanvas,
    GlCanvas,
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
