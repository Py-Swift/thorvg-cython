"""Tests for SwCanvas, Scene, Picture rendering pipeline."""
from thorvg_cython import (
    Result, SwCanvas, Shape, Scene, Picture, Colorspace,
    MaskMethod,
)
from conftest import W, H, render


# ── SwCanvas basics ──────────────────────────────────────────────

def test_canvas_create():
    c = SwCanvas()
    assert c is not None


def test_canvas_draw_empty(canvas):
    r1, r2 = render(canvas)
    assert r1 == Result.SUCCESS
    assert r2 == Result.SUCCESS


def test_canvas_add_remove(canvas):
    s = Shape()
    s.append_rect(0, 0, 50, 50)
    s.set_fill_color(255, 0, 0)
    assert canvas.add(s) == Result.SUCCESS
    render(canvas)
    assert canvas.remove(s) == Result.SUCCESS


def test_canvas_viewport(canvas):
    assert canvas.set_viewport(10, 10, 100, 100) == Result.SUCCESS


# ── Scene ────────────────────────────────────────────────────────

def test_scene_add_shapes(canvas):
    scene = Scene()
    s1 = Shape()
    s1.append_rect(0, 0, 50, 50)
    s1.set_fill_color(255, 0, 0)

    s2 = Shape()
    s2.append_circle(100, 100, 30, 30)
    s2.set_fill_color(0, 255, 0)

    assert scene.add(s1) == Result.SUCCESS
    assert scene.add(s2) == Result.SUCCESS
    assert canvas.add(scene) == Result.SUCCESS
    r1, r2 = render(canvas)
    assert r1 == Result.SUCCESS


def test_scene_remove(canvas):
    scene = Scene()
    s = Shape()
    s.append_rect(0, 0, 10, 10)
    s.set_fill_color(0, 0, 255)
    scene.add(s)
    assert scene.remove(s) == Result.SUCCESS


def test_scene_effects(canvas):
    scene = Scene()
    s = Shape()
    s.append_rect(10, 10, 80, 80)
    s.set_fill_color(200, 100, 50)
    scene.add(s)
    canvas.add(scene)

    assert scene.add_effect_gaussian_blur(3.0) == Result.SUCCESS
    render(canvas)
    assert scene.clear_effects() == Result.SUCCESS


# ── Picture (SVG data) ───────────────────────────────────────────

SVG_DATA = b'''<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
  <rect width="100" height="100" fill="red"/>
</svg>'''


def test_picture_load_data(canvas):
    pic = Picture()
    r = pic.load_data(SVG_DATA, mimetype="image/svg+xml")
    assert r == Result.SUCCESS

    r, w, h = pic.get_size()
    assert r == Result.SUCCESS
    assert w > 0 and h > 0

    canvas.add(pic)
    r1, r2 = render(canvas)
    assert r1 == Result.SUCCESS


def test_picture_set_size():
    pic = Picture()
    pic.load_data(SVG_DATA, mimetype="image/svg+xml")
    assert pic.set_size(200, 200) == Result.SUCCESS
    r, w, h = pic.get_size()
    assert abs(w - 200) < 0.01


def test_picture_origin():
    pic = Picture()
    pic.load_data(SVG_DATA, mimetype="image/svg+xml")
    assert pic.set_origin(10, 20) == Result.SUCCESS
    r, x, y = pic.get_origin()
    assert r == Result.SUCCESS
    assert abs(x - 10) < 0.01
    assert abs(y - 20) < 0.01


# ── Masking ──────────────────────────────────────────────────────

def test_mask_method(canvas):
    s1 = Shape()
    s1.append_rect(0, 0, 100, 100)
    s1.set_fill_color(255, 0, 0)

    s2 = Shape()
    s2.append_circle(50, 50, 40, 40)
    s2.set_fill_color(255, 255, 255)

    assert s1.set_mask_method(s2, MaskMethod.ALPHA) == Result.SUCCESS
    r, method = s1.get_mask_method()
    assert r == Result.SUCCESS
    assert method == MaskMethod.ALPHA
