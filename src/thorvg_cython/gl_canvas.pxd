# cython: language_level=3
"""
Companion .pxd for gl_canvas.pyx — allows other Cython code (e.g. Kivy)
to ``cimport`` GlCanvas and access the underlying C canvas handle.

This enables frameworks like Kivy to interleave their own OpenGL
draw calls with ThorVG rendering on the same GL context / FBO,
without the overhead of blitting through a CPU-side pixel buffer.

Example (Kivy integration — shared GL context)::

    from thorvg_cython.gl_canvas cimport GlCanvas
    cimport thorvg_cython.cthorvg as tvg

    cdef GlCanvas canvas = GlCanvas()
    # Point ThorVG at Kivy's current FBO
    canvas.target(0, 0, 0, kivy_fbo_id, width, height, cs)

    # Add vector content, draw, sync — ThorVG renders into the
    # same FBO that Kivy's canvas instructions target.
    canvas.add(shape)
    canvas.draw()
    canvas.sync()

    # Kivy continues issuing GL instructions on the same FBO
    # — no blit_buffer / Texture round-trip needed.
"""
from thorvg_cython.thorvg cimport Canvas


cdef class GlCanvas(Canvas):
    pass
