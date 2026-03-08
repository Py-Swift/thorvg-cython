"""Tests for Shape: path ops, fill, stroke, transforms, paint basics."""
from thorvg_cython import (
    Result, Shape, Point, PathCommand, Matrix,
    StrokeCap, StrokeJoin, FillRule, BlendMethod, TvgType,
    ColorStop, LinearGradient,
)
from conftest import render


# ── Path operations ──────────────────────────────────────────────

def test_shape_append_rect(canvas):
    s = Shape()
    assert s.append_rect(0, 0, 100, 100) == Result.SUCCESS
    canvas.add(s)
    r1, r2 = render(canvas)
    assert r1 == Result.SUCCESS and r2 == Result.SUCCESS


def test_shape_append_rect_rounded(canvas):
    s = Shape()
    assert s.append_rect(10, 10, 80, 80, rx=10, ry=10) == Result.SUCCESS


def test_shape_append_circle(canvas):
    s = Shape()
    assert s.append_circle(50, 50, 40, 40) == Result.SUCCESS


def test_shape_move_line_close(canvas):
    s = Shape()
    assert s.move_to(0, 0) == Result.SUCCESS
    assert s.line_to(100, 0) == Result.SUCCESS
    assert s.line_to(100, 100) == Result.SUCCESS
    assert s.close() == Result.SUCCESS


def test_shape_cubic_to(canvas):
    s = Shape()
    s.move_to(0, 0)
    assert s.cubic_to(30, 0, 70, 100, 100, 100) == Result.SUCCESS


def test_shape_append_path():
    s = Shape()
    cmds = [PathCommand.MOVE_TO, PathCommand.LINE_TO,
            PathCommand.LINE_TO, PathCommand.CLOSE]
    pts = [Point(0, 0), Point(100, 0), Point(50, 100)]
    assert s.append_path(cmds, pts) == Result.SUCCESS

    r, out_cmds, out_pts = s.get_path()
    assert r == Result.SUCCESS
    assert len(out_cmds) == 4
    assert out_cmds[0] == PathCommand.MOVE_TO
    assert len(out_pts) >= 3


def test_shape_append_path_tuples():
    """append_path should accept (x, y) tuples as well as Point objects."""
    s = Shape()
    cmds = [PathCommand.MOVE_TO, PathCommand.LINE_TO, PathCommand.CLOSE]
    pts = [(0.0, 0.0), (50.0, 50.0)]
    assert s.append_path(cmds, pts) == Result.SUCCESS


def test_shape_reset():
    s = Shape()
    s.append_rect(0, 0, 10, 10)
    assert s.reset() == Result.SUCCESS
    r, cmds, pts = s.get_path()
    assert r == Result.SUCCESS
    assert len(cmds) == 0


# ── Fill ─────────────────────────────────────────────────────────

def test_shape_fill_color():
    s = Shape()
    assert s.set_fill_color(128, 64, 32, 200) == Result.SUCCESS
    r, rr, gg, bb, aa = s.get_fill_color()
    assert r == Result.SUCCESS
    assert (rr, gg, bb, aa) == (128, 64, 32, 200)


def test_shape_fill_color_default_alpha():
    s = Shape()
    s.set_fill_color(255, 0, 0)
    _, _, _, _, a = s.get_fill_color()
    assert a == 255


def test_shape_fill_rule():
    s = Shape()
    assert s.set_fill_rule(FillRule.EVEN_ODD) == Result.SUCCESS
    r, rule = s.get_fill_rule()
    assert r == Result.SUCCESS
    assert rule == FillRule.EVEN_ODD


def test_shape_gradient_fill():
    s = Shape()
    grad = LinearGradient(0, 0, 100, 100)
    grad.set_color_stops([ColorStop(0, 255, 0, 0), ColorStop(1, 0, 0, 255)])
    assert s.set_gradient(grad) == Result.SUCCESS
    r, g = s.get_gradient()
    assert r == Result.SUCCESS
    assert g is not None


# ── Stroke ───────────────────────────────────────────────────────

def test_stroke_width():
    s = Shape()
    assert s.set_stroke_width(5.0) == Result.SUCCESS
    r, w = s.get_stroke_width()
    assert r == Result.SUCCESS
    assert abs(w - 5.0) < 0.01


def test_stroke_color():
    s = Shape()
    s.set_stroke_width(1)
    assert s.set_stroke_color(10, 20, 30, 40) == Result.SUCCESS
    r, rr, gg, bb, aa = s.get_stroke_color()
    assert r == Result.SUCCESS
    assert (rr, gg, bb, aa) == (10, 20, 30, 40)


def test_stroke_cap_join():
    s = Shape()
    s.set_stroke_width(1)
    assert s.set_stroke_cap(StrokeCap.ROUND) == Result.SUCCESS
    r, cap = s.get_stroke_cap()
    assert cap == StrokeCap.ROUND

    assert s.set_stroke_join(StrokeJoin.BEVEL) == Result.SUCCESS
    r, join = s.get_stroke_join()
    assert join == StrokeJoin.BEVEL


def test_stroke_dash():
    s = Shape()
    s.set_stroke_width(2)
    assert s.set_stroke_dash([10.0, 5.0], offset=2.0) == Result.SUCCESS
    r, pat, off = s.get_stroke_dash()
    assert r == Result.SUCCESS
    assert len(pat) == 2
    assert abs(pat[0] - 10.0) < 0.01
    assert abs(off - 2.0) < 0.01


def test_stroke_miterlimit():
    s = Shape()
    s.set_stroke_width(1)
    assert s.set_stroke_miterlimit(8.0) == Result.SUCCESS
    r, ml = s.get_stroke_miterlimit()
    assert r == Result.SUCCESS
    assert abs(ml - 8.0) < 0.01


def test_stroke_gradient():
    s = Shape()
    s.set_stroke_width(3)
    grad = LinearGradient(0, 0, 50, 50)
    grad.set_color_stops([ColorStop(0, 0, 255, 0), ColorStop(1, 255, 0, 0)])
    assert s.set_stroke_gradient(grad) == Result.SUCCESS
    r, g = s.get_stroke_gradient()
    assert r == Result.SUCCESS
    assert g is not None


# ── Paint base (via Shape) ───────────────────────────────────────

def test_paint_opacity():
    s = Shape()
    assert s.set_opacity(128) == Result.SUCCESS
    r, op = s.get_opacity()
    assert r == Result.SUCCESS
    assert op == 128


def test_paint_visible():
    s = Shape()
    assert s.set_visible(False) == Result.SUCCESS
    assert s.get_visible() is False
    s.set_visible(True)
    assert s.get_visible() is True


def test_paint_transforms():
    s = Shape()
    assert s.translate(10, 20) == Result.SUCCESS
    assert s.scale(2.0) == Result.SUCCESS
    assert s.rotate(45.0) == Result.SUCCESS


def test_paint_set_get_transform():
    s = Shape()
    m = Matrix(2, 0, 10, 0, 2, 20, 0, 0, 1)
    assert s.set_transform(m) == Result.SUCCESS
    r, m2 = s.get_transform()
    assert r == Result.SUCCESS
    assert abs(m2.e11 - 2.0) < 0.001
    assert abs(m2.e13 - 10.0) < 0.001


def test_paint_id():
    s = Shape()
    assert s.set_id(42) == Result.SUCCESS
    assert s.get_id() == 42


def test_paint_type():
    s = Shape()
    r, t = s.get_type()
    assert r == Result.SUCCESS
    assert t == TvgType.SHAPE


def test_paint_blend():
    s = Shape()
    assert s.set_blend_method(BlendMethod.MULTIPLY) == Result.SUCCESS


def test_paint_duplicate():
    s = Shape()
    s.set_fill_color(100, 200, 50)
    s.append_rect(0, 0, 50, 50)
    dup = s.duplicate()
    assert dup is not None
    # duplicate returns Paint (base), check paint-level attrs
    r, op = dup.get_opacity()
    assert r == Result.SUCCESS
    assert op == 255  # default opacity


def test_paint_order():
    s = Shape()
    assert s.set_paint_order(True) == Result.SUCCESS


def test_trimpath():
    s = Shape()
    s.append_rect(0, 0, 100, 100)
    assert s.set_trimpath(0.0, 0.5) == Result.SUCCESS
