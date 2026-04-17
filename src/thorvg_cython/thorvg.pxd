# cython: language_level=3
"""
Companion .pxd for thorvg.pyx — exposes cdef classes so that
sw_canvas.pyx and gl_canvas.pyx can cimport and subclass them.

Methods declared ``cpdef`` here keep their ``def`` in the .pyx but
Cython generates a C-callable fast-path so that Cython-to-Cython
calls (e.g. from ThorKivy) skip the Python dispatch overhead.
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

    cpdef clear(self)


# ── Internal helpers ─────────────────────────────────────────────
cdef int _check(tvg.Tvg_Result r) except -1
cdef tvg.Tvg_Matrix _mat_to_c(m)
cdef object _mat_from_c(tvg.Tvg_Matrix cm)


# ── Paint ────────────────────────────────────────────────────────
cdef class Paint:
    cdef tvg.Tvg_Paint _p
    cdef bint _owned
    cdef void _set(self, tvg.Tvg_Paint p, bint owned=*)

    cpdef ref(self)
    cpdef deref(self, bint free=*)
    cpdef get_ref(self)
    cpdef set_visible(self, bint visible)
    cpdef get_visible(self)
    cpdef scale(self, float factor)
    cpdef rotate(self, float degree)
    cpdef translate(self, float x, float y)
    cpdef set_transform(self, m)
    cpdef get_transform(self)
    cpdef set_opacity(self, uint8_t opacity)
    cpdef get_opacity(self)
    cpdef duplicate(self)
    cpdef intersects(self, int x, int y, int w, int h)
    cpdef get_aabb(self)
    cpdef get_obb(self)
    cpdef set_mask_method(self, Paint target, int method)
    cpdef get_mask_method(self)
    cpdef set_clip(self, Paint clipper)
    cpdef get_clip(self)
    cpdef get_parent(self)
    cpdef get_type(self)
    cpdef set_blend_method(self, int method)
    cpdef _rel(self)


# ── Canvas ───────────────────────────────────────────────────────
cdef class Canvas:
    cdef tvg.Tvg_Canvas _c
    cdef void _set(self, tvg.Tvg_Canvas c)

    cpdef destroy(self)
    cpdef add(self, Paint paint)
    cpdef insert(self, Paint target, Paint at=*)
    cpdef remove(self, Paint paint=*)
    cpdef update(self)
    cpdef draw(self, bint clear=*)
    cpdef sync(self)
    cpdef set_viewport(self, int x, int y, int w, int h)


# ── Gradient ─────────────────────────────────────────────────────
cdef class Gradient:
    cdef tvg.Tvg_Gradient _g
    cdef void _set(self, tvg.Tvg_Gradient g)

    cpdef set_color_stops(self, stops)
    cpdef get_color_stops(self)
    cpdef set_spread(self, int spread)
    cpdef get_spread(self)
    cpdef set_transform(self, m)
    cpdef get_transform(self)
    cpdef get_type(self)
    cpdef duplicate(self)
    cpdef _del(self)


cdef class LinearGradient(Gradient):
    cpdef set(self, float x1, float y1, float x2, float y2)
    cpdef get(self)


cdef class RadialGradient(Gradient):
    cpdef set(self, float cx, float cy, float r,
              float fx=*, float fy=*, float fr=*)
    cpdef get(self)


# ── Shape ────────────────────────────────────────────────────────
cdef class Shape(Paint):
    cpdef reset(self)
    cpdef move_to(self, float x, float y)
    cpdef line_to(self, float x, float y)
    cpdef cubic_to(self, float cx1, float cy1, float cx2, float cy2,
                   float x, float y)
    cpdef close(self)
    cpdef append_rect(self, float x, float y, float w, float h,
                      float rx=*, float ry=*, bint cw=*)
    cpdef append_circle(self, float cx, float cy, float rx, float ry,
                        bint cw=*)
    cpdef append_path(self, commands, points)
    cpdef get_path(self)
    cpdef set_stroke_width(self, float width)
    cpdef get_stroke_width(self)
    cpdef set_stroke_color(self, uint8_t r, uint8_t g, uint8_t b,
                           uint8_t a=*)
    cpdef get_stroke_color(self)
    cpdef set_stroke_gradient(self, Gradient grad)
    cpdef get_stroke_gradient(self)
    cpdef set_stroke_dash(self, pattern, float offset=*)
    cpdef get_stroke_dash(self)
    cpdef set_stroke_cap(self, int cap)
    cpdef get_stroke_cap(self)
    cpdef set_stroke_join(self, int join)
    cpdef get_stroke_join(self)
    cpdef set_stroke_miterlimit(self, float ml)
    cpdef get_stroke_miterlimit(self)
    cpdef set_trimpath(self, float begin, float end,
                       bint simultaneous=*)
    cpdef set_fill_color(self, uint8_t r, uint8_t g, uint8_t b,
                         uint8_t a=*)
    cpdef get_fill_color(self)
    cpdef set_fill_rule(self, int rule)
    cpdef get_fill_rule(self)
    cpdef set_paint_order(self, bint stroke_first)
    cpdef set_gradient(self, Gradient grad)
    cpdef get_gradient(self)


# ── Picture ──────────────────────────────────────────────────────
cdef class Picture(Paint):
    @staticmethod
    cdef Picture _wrap(tvg.Tvg_Paint p, bint owned)

    cpdef load(self, str path)
    cpdef load_raw(self, unsigned long data_ptr, uint32_t w, uint32_t h,
                   int cs=*, bint copy=*)
    cpdef load_data(self, bytes data, str mimetype=*, str rpath=*,
                    bint copy=*)
    cpdef set_size(self, float w, float h)
    cpdef get_size(self)
    cpdef set_origin(self, float x, float y)
    cpdef get_origin(self)
    cpdef get_paint(self, uint32_t id)
    cpdef set_accessible(self, bint accessible)


# ── Scene ────────────────────────────────────────────────────────
cdef class Scene(Paint):
    cpdef add(self, Paint paint)
    cpdef insert(self, Paint target, Paint at=*)
    cpdef remove(self, Paint paint=*)
    cpdef clear_effects(self)
    cpdef add_effect_gaussian_blur(self, double sigma, int direction=*,
                                   int border=*, int quality=*)
    cpdef add_effect_drop_shadow(self, int r, int g, int b, int a,
                                 double angle=*, double distance=*,
                                 double sigma=*, int quality=*)
    cpdef add_effect_fill(self, int r, int g, int b, int a)
    cpdef add_effect_tint(self, int black_r, int black_g, int black_b,
                          int white_r, int white_g, int white_b,
                          double intensity=*)
    cpdef add_effect_tritone(self, int sr, int sg, int sb,
                             int mr, int mg, int mb,
                             int hr, int hg, int hb,
                             double blend=*)


# ── Text ─────────────────────────────────────────────────────────
cdef class Text(Paint):
    cpdef set_font(self, str name)
    cpdef set_size(self, float size)
    cpdef set_text(self, str utf8)
    cpdef align(self, float x, float y)
    cpdef layout(self, float w, float h)
    cpdef wrap_mode(self, int mode)
    cpdef spacing(self, float letter, float line)
    cpdef set_italic(self, float shear)
    cpdef set_outline(self, float width, uint8_t r, uint8_t g, uint8_t b)
    cpdef set_color(self, uint8_t r, uint8_t g, uint8_t b)
    cpdef set_gradient(self, Gradient grad)
    cpdef get_text_metrics(self)


# ── Animation ────────────────────────────────────────────────────
cdef class Animation:
    cdef tvg.Tvg_Animation _a

    cpdef set_frame(self, float no)
    cpdef get_picture(self)
    cpdef get_frame(self)
    cpdef get_total_frame(self)
    cpdef get_duration(self)
    cpdef set_segment(self, float begin, float end)
    cpdef get_segment(self)
    cpdef _del(self)


cdef class LottieAnimation(Animation):
    cpdef gen_slot(self, str slot)
    cpdef apply_slot(self, uint32_t id)
    cpdef del_slot(self, uint32_t id)
    cpdef set_marker(self, str marker)
    cpdef get_markers_cnt(self)
    cpdef get_marker(self, uint32_t idx)
    cpdef tween(self, float from_, float to, float progress)
    cpdef assign(self, str layer, uint32_t ix, str var, float val)
    cpdef set_quality(self, uint8_t value)


# ── Saver ────────────────────────────────────────────────────────
cdef class Saver:
    cdef tvg.Tvg_Saver _s

    cpdef save_paint(self, Paint paint, str path, uint32_t quality=*)
    cpdef save_animation(self, Animation animation, str path,
                         uint32_t quality=*, uint32_t fps=*)
    cpdef sync(self)
    cpdef _del(self)


# ── Accessor ─────────────────────────────────────────────────────
cdef class Accessor:
    cdef tvg.Tvg_Accessor _acc

    cpdef _del(self)
    cpdef get_name(self, uint32_t id)


