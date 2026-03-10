"""Type stubs for thorvg_cython.gl_canvas."""

from __future__ import annotations

from .thorvg import Canvas, Colorspace, Result


class GlCanvas(Canvas):
    """OpenGL-accelerated canvas for GPU rendering."""
    def __init__(self, engine_option: int = 1) -> None: ...
    def target(
        self,
        display: int,
        surface: int,
        context: int,
        fbo_id: int,
        w: int,
        h: int,
        cs: int = 0,
    ) -> Result: ...
    def __repr__(self) -> str: ...
