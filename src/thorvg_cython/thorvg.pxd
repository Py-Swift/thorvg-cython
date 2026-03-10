# cython: language_level=3
"""
Companion .pxd for thorvg.pyx — exposes cdef classes so that
sw_canvas.pyx and gl_canvas.pyx can cimport and subclass them.
"""
from libc.stdint cimport uint8_t, uint16_t, uint32_t, int32_t, uintptr_t

cimport thorvg_cython.cthorvg as tvg


# ── PixelBuffer ──────────────────────────────────────────────────
cdef class PixelBuffer:
    cdef uint32_t* _data
    cdef uint32_t  _w, _h, _stride
    cdef int       _cs
    cdef Py_ssize_t _nbytes
    cdef Py_ssize_t _shape[1]
    cdef Py_ssize_t _strides[1]


# ── Internal helpers ─────────────────────────────────────────────
cdef int _check(tvg.Tvg_Result r) except -1
cdef tvg.Tvg_Matrix _mat_to_c(m)
cdef object _mat_from_c(tvg.Tvg_Matrix cm)


# ── Paint ────────────────────────────────────────────────────────
cdef class Paint:
    cdef tvg.Tvg_Paint _p
    cdef bint _owned
    cdef void _set(self, tvg.Tvg_Paint p, bint owned=*)


# ── Canvas ───────────────────────────────────────────────────────
cdef class Canvas:
    cdef tvg.Tvg_Canvas _c
    cdef void _set(self, tvg.Tvg_Canvas c)


# ── Gradient ─────────────────────────────────────────────────────
cdef class Gradient:
    cdef tvg.Tvg_Gradient _g
    cdef void _set(self, tvg.Tvg_Gradient g)


cdef class LinearGradient(Gradient):
    pass


cdef class RadialGradient(Gradient):
    pass


# ── Shape ────────────────────────────────────────────────────────
cdef class Shape(Paint):
    pass


# ── Picture ──────────────────────────────────────────────────────
cdef class Picture(Paint):
    @staticmethod
    cdef Picture _wrap(tvg.Tvg_Paint p, bint owned)


# ── Scene ────────────────────────────────────────────────────────
cdef class Scene(Paint):
    pass


# ── Text ─────────────────────────────────────────────────────────
cdef class Text(Paint):
    pass


# ── Animation ────────────────────────────────────────────────────
cdef class Animation:
    cdef tvg.Tvg_Animation _a


cdef class LottieAnimation(Animation):
    pass


# ── Saver ────────────────────────────────────────────────────────
cdef class Saver:
    cdef tvg.Tvg_Saver _s


# ── Accessor ─────────────────────────────────────────────────────
cdef class Accessor:
    cdef tvg.Tvg_Accessor _acc


# ── Canvas-creation helpers (called by sub-extensions via cimport) ─
# These thin wrappers keep all C-API symbol references inside thorvg.so,
# so sw_canvas.so / gl_canvas.so never need to link libthorvg directly.
cdef tvg.Tvg_Canvas _create_sw_canvas(int op)
cdef tvg.Tvg_Result _set_sw_target(tvg.Tvg_Canvas c, uint32_t* buf,
                                    uint32_t stride, uint32_t w, uint32_t h,
                                    int cs)
cdef tvg.Tvg_Canvas _create_gl_canvas(int op)
cdef tvg.Tvg_Result _set_gl_target(tvg.Tvg_Canvas c, void* display,
                                    void* surface, void* context,
                                    int32_t fbo_id, uint32_t w, uint32_t h,
                                    int cs)
