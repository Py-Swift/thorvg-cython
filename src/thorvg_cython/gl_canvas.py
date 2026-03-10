"""
GlCanvas stub — used when THORVG_GPU is NOT set at build time.

When GPU support is enabled, gl_canvas.pyx is compiled to gl_canvas.so
which takes import precedence over this .py file.
"""


class GlCanvas:
    """Stub GlCanvas — GPU support was not enabled at build time."""

    def __init__(self, *args, **kwargs):
        raise RuntimeError(
            "GPU support is not enabled, build thorvg-cython with "
            "gpu mode enabled, if GlCanvas is required"
        )
