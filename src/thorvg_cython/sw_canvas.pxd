# cython: language_level=3
"""
Companion .pxd for sw_canvas.pyx — allows other Cython code (e.g. Kivy)
to ``cimport`` SwCanvas and access C-level attributes directly.

Example (Kivy integration)::

    from thorvg_cython.sw_canvas cimport SwCanvas
    from thorvg_cython.thorvg cimport PixelBuffer

    cdef SwCanvas canvas = SwCanvas(800, 600)
    cdef PixelBuffer buf = canvas._buf
    # Direct pointer access for zero-copy blitting
    cdef uint32_t* pixel_data = buf._data
"""
from thorvg_cython.thorvg cimport Canvas, PixelBuffer


cdef class SwCanvas(Canvas):
    cdef PixelBuffer _buf
