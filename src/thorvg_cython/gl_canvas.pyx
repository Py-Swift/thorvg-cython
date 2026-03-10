# cython: language_level=3
"""
GlCanvas — OpenGL-accelerated canvas for GPU rendering.

This module is compiled only when THORVG_GPU is set at build time.
When GPU support is disabled, the plain Python gl_canvas.py stub
provides a GlCanvas class that raises RuntimeError on instantiation.

Other Cython projects (e.g. Kivy) can ``cimport`` GlCanvas to access
the underlying C canvas handle directly, enabling zero-overhead
interleaving of ThorVG vector rendering with their own OpenGL
draw calls on the same GL context / FBO.
"""
from libc.stdint cimport uint8_t, uint32_t, int32_t, uintptr_t

from thorvg_cython.thorvg cimport (Canvas,
                                    _create_gl_canvas, _set_gl_target)
from thorvg_cython.thorvg import Result


cdef class GlCanvas(Canvas):
    """OpenGL-accelerated canvas for GPU rendering.

    Unlike SwCanvas, GlCanvas does not manage a pixel buffer.
    The caller must provide an active OpenGL (ES) context and
    target surface via :meth:`target`.

    Example with an externally managed GL context::

        canvas = GlCanvas()
        # Caller creates/binds the GL context (e.g., via EGL, ANGLE, GLFW)
        canvas.target(0, 0, 0, fbo_id, width, height, Colorspace.ABGR8888S)
        canvas.add(shape)
        canvas.draw()
        canvas.sync()

    Args:
        engine_option: Engine quality option (default: Quality).

    Notes:
        - On macOS/iOS, thorvg uses ANGLE (OpenGL ES → Metal translation).
          Ensure ANGLE dylibs (libEGL.dylib, libGLESv2.dylib) are loadable.
        - On Windows/Linux, thorvg loads native OpenGL at runtime.
        - On Android, thorvg loads native OpenGL ES at runtime.
        - If display and surface are 0 (NULL), thorvg assumes the GL
          context is already current and will not manage it.
    """

    def __cinit__(self, int engine_option=1):
        self._c = _create_gl_canvas(engine_option)

    def target(self, uintptr_t display, uintptr_t surface,
               uintptr_t context, int32_t fbo_id,
               uint32_t w, uint32_t h, int cs=0):
        """Set the GL render target.

        Args:
            display:  EGLDisplay handle (0 for no EGL management).
            surface:  EGLSurface handle (0 for no EGL management).
            context:  OpenGL context handle (0 for no context management).
            fbo_id:   Framebuffer Object ID (0 = default/main surface).
            w:        Render target width in pixels.
            h:        Render target height in pixels.
            cs:       Colorspace (default: ABGR8888).
        """
        return Result(_set_gl_target(
            self._c,
            <void*>display,
            <void*>surface,
            <void*>context,
            fbo_id, w, h, cs))

    def __repr__(self):
        return "GlCanvas()"
