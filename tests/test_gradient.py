"""Tests for LinearGradient, RadialGradient, color stops, spread."""
from thorvg_cython import (
    Result, LinearGradient, RadialGradient,
    ColorStop, StrokeFill, TvgType, Matrix,
)


# ── LinearGradient ───────────────────────────────────────────────

def test_linear_gradient_create():
    g = LinearGradient(10, 20, 110, 120)
    r, x1, y1, x2, y2 = g.get()
    assert r == Result.SUCCESS
    assert abs(x1 - 10) < 0.01
    assert abs(y2 - 120) < 0.01


def test_linear_gradient_set():
    g = LinearGradient()
    assert g.set(0, 0, 200, 200) == Result.SUCCESS
    r, x1, y1, x2, y2 = g.get()
    assert abs(x2 - 200) < 0.01


def test_linear_gradient_type():
    g = LinearGradient()
    r, t = g.get_type()
    assert r == Result.SUCCESS
    assert t == TvgType.LINEAR_GRAD


# ── RadialGradient ───────────────────────────────────────────────

def test_radial_gradient_create():
    g = RadialGradient(50, 50, 40, 45, 45, 5)
    r, cx, cy, rad, fx, fy, fr = g.get()
    assert r == Result.SUCCESS
    assert abs(cx - 50) < 0.01
    assert abs(rad - 40) < 0.01
    assert abs(fx - 45) < 0.01
    assert abs(fr - 5) < 0.01


def test_radial_gradient_set():
    g = RadialGradient()
    assert g.set(100, 100, 80) == Result.SUCCESS
    r, cx, cy, rad, fx, fy, fr = g.get()
    assert abs(cx - 100) < 0.01
    assert abs(rad - 80) < 0.01


def test_radial_gradient_type():
    g = RadialGradient()
    r, t = g.get_type()
    assert r == Result.SUCCESS
    assert t == TvgType.RADIAL_GRAD


# ── Color stops ──────────────────────────────────────────────────

def test_color_stops():
    g = LinearGradient(0, 0, 100, 0)
    stops = [
        ColorStop(0.0, 255, 0, 0),
        ColorStop(0.5, 0, 255, 0, 128),
        ColorStop(1.0, 0, 0, 255),
    ]
    assert g.set_color_stops(stops) == Result.SUCCESS
    r, out = g.get_color_stops()
    assert r == Result.SUCCESS
    assert len(out) == 3
    assert out[0].r == 255
    assert out[1].g == 255
    assert out[1].a == 128
    assert out[2].b == 255


def test_color_stops_default_alpha():
    cs = ColorStop(0.0, 10, 20, 30)
    assert cs.a == 255


# ── Spread ───────────────────────────────────────────────────────

def test_gradient_spread():
    g = LinearGradient()
    assert g.set_spread(StrokeFill.REFLECT) == Result.SUCCESS
    r, sp = g.get_spread()
    assert r == Result.SUCCESS
    assert sp == StrokeFill.REFLECT


# ── Transform ────────────────────────────────────────────────────

def test_gradient_transform():
    g = LinearGradient()
    m = Matrix(2, 0, 0, 0, 2, 0, 0, 0, 1)
    assert g.set_transform(m) == Result.SUCCESS
    r, m2 = g.get_transform()
    assert r == Result.SUCCESS
    assert abs(m2.e11 - 2.0) < 0.001


# ── Duplicate ────────────────────────────────────────────────────

def test_gradient_duplicate():
    g = LinearGradient(0, 0, 100, 100)
    g.set_color_stops([ColorStop(0, 255, 0, 0), ColorStop(1, 0, 255, 0)])
    dup = g.duplicate()
    assert dup is not None
    assert isinstance(dup, LinearGradient)
    r, stops = dup.get_color_stops()
    assert len(stops) == 2


def test_radial_gradient_duplicate():
    g = RadialGradient(50, 50, 30)
    dup = g.duplicate()
    assert dup is not None
    assert isinstance(dup, RadialGradient)
