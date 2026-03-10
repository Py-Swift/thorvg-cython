# cython: language_level=3
"""
SwCanvas — software-rasterized canvas with built-in pixel buffer.
"""
from libc.stdint cimport uint8_t, uint32_t

cimport thorvg_cython.cthorvg as tvg
from thorvg_cython.thorvg cimport Canvas, PixelBuffer
from thorvg_cython.thorvg import Result, Colorspace


cdef class SwCanvas(Canvas):
    """Software-rasterized canvas with built-in pixel buffer.

    Pass width/height to get an integrated buffer that supports the
    Python buffer protocol (PEP 3118)::

        canvas = SwCanvas(800, 600)
        canvas.add(shape)
        canvas.draw()
        canvas.sync()
        texture.blit_buffer(canvas)   # zero-copy
        data = bytes(canvas)          # snapshot
    """

    def __cinit__(self, uint32_t w=0, uint32_t h=0, int cs=0,
                  int engine_option=1):
        self._c = tvg.tvg_swcanvas_create(<tvg.Tvg_Engine_Option>engine_option)
        self._buf = None
        if w > 0 and h > 0:
            self._buf = PixelBuffer(w, h, cs)
            tvg.tvg_swcanvas_set_target(
                self._c, self._buf._data, self._buf._stride,
                self._buf._w, self._buf._h, <tvg.Tvg_Colorspace>self._buf._cs)

    def resize(self, uint32_t w, uint32_t h, int cs=-1):
        """Resize the internal pixel buffer (reallocates)."""
        cdef int actual_cs = cs if cs >= 0 else (self._buf._cs if self._buf is not None else 0)
        self._buf = PixelBuffer(w, h, actual_cs)
        return Result(tvg.tvg_swcanvas_set_target(
            self._c, self._buf._data, self._buf._stride,
            self._buf._w, self._buf._h, <tvg.Tvg_Colorspace>self._buf._cs))

    # ---- buffer protocol (delegates to internal PixelBuffer) ----

    def __getbuffer__(self, Py_buffer *view, int flags):
        if self._buf is None:
            raise BufferError("SwCanvas has no pixel buffer - pass w, h to constructor")
        view.buf        = <void*>self._buf._data
        view.len        = self._buf._nbytes
        view.readonly   = 0
        view.format     = "B"
        view.ndim       = 1
        view.shape      = self._buf._shape
        view.strides    = self._buf._strides
        view.suboffsets = NULL
        view.itemsize   = 1
        view.obj        = self

    def __releasebuffer__(self, Py_buffer *view):
        pass

    # ---- pixel access -------------------------------------------

    @property
    def buffer(self):
        """The internal PixelBuffer, or None."""
        return self._buf

    @property
    def width(self):
        return self._buf._w if self._buf is not None else 0

    @property
    def height(self):
        return self._buf._h if self._buf is not None else 0

    @property
    def colorspace(self):
        return Colorspace(self._buf._cs) if self._buf is not None else Colorspace.UNKNOWN

    def clear(self):
        """Zero out all pixels."""
        if self._buf is not None:
            self._buf.clear()

    def __len__(self):
        return self._buf._nbytes if self._buf is not None else 0

    def __repr__(self):
        if self._buf is not None:
            return (f"SwCanvas({self._buf._w}x{self._buf._h}, "
                    f"cs={Colorspace(self._buf._cs).name})")
        return "SwCanvas(no buffer)"
