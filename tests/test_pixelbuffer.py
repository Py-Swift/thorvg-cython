"""Tests for the SwCanvas buffer protocol (PEP 3118).

SwCanvas owns its pixel memory -- no separate PixelBuffer to wire up.
Frameworks read pixels via ``bytes(canvas)``, ``memoryview(canvas)``,
or any API accepting buffer-protocol objects (e.g. Kivy blit_buffer).
"""
import struct
import pytest
from thorvg_cython import (
    Result, SwCanvas, Shape, Scene, Picture,
    Colorspace, LinearGradient, ColorStop,
)
from conftest import W, H, render


# == Canvas creation & properties ==================================

def test_canvas_with_buffer():
    c = SwCanvas(320, 240, Colorspace.ARGB8888)
    assert c.width == 320
    assert c.height == 240
    assert c.colorspace == Colorspace.ARGB8888
    assert len(c) == 320 * 240 * 4


def test_canvas_repr():
    c = SwCanvas(64, 64, Colorspace.ABGR8888)
    r = repr(c)
    assert "64x64" in r
    assert "ABGR8888" in r


def test_canvas_no_buffer():
    c = SwCanvas()
    assert c.width == 0
    assert c.height == 0
    assert len(c) == 0


def test_canvas_starts_zeroed():
    c = SwCanvas(4, 4)
    data = bytes(c)
    assert data == b"\x00" * (4 * 4 * 4)


# == Buffer protocol on SwCanvas ===================================

def test_memoryview_basic():
    c = SwCanvas(10, 10)
    mv = memoryview(c)
    assert mv.format == "B"
    assert mv.ndim == 1
    assert mv.readonly is False
    assert len(mv) == 10 * 10 * 4


def test_memoryview_writable():
    c = SwCanvas(2, 2)
    mv = memoryview(c)
    mv[0] = 0xFF
    mv[1] = 0xAB
    data = bytes(c)
    assert data[0] == 0xFF
    assert data[1] == 0xAB


def test_bytes_snapshot():
    """bytes(canvas) produces an independent copy of the pixel data."""
    c = SwCanvas(4, 4)
    snap1 = bytes(c)
    mv = memoryview(c)
    mv[0] = 42
    snap2 = bytes(c)
    assert snap1[0] == 0
    assert snap2[0] == 42


def test_bytearray_from_canvas():
    c = SwCanvas(4, 4)
    ba = bytearray(c)
    assert len(ba) == 4 * 4 * 4
    assert isinstance(ba, bytearray)


def test_buffer_error_no_buffer():
    """Requesting buffer from an empty canvas raises BufferError."""
    c = SwCanvas()
    with pytest.raises(BufferError):
        bytes(c)


# == Resize =========================================================

def test_resize():
    c = SwCanvas(10, 10)
    assert len(c) == 10 * 10 * 4
    c.resize(20, 30)
    assert c.width == 20
    assert c.height == 30
    assert len(c) == 20 * 30 * 4


# == Rendering -> bytes(canvas) =====================================

def _render_red_rect():
    """Render a full-size red rect, return the canvas."""
    c = SwCanvas(W, H, Colorspace.ARGB8888)
    s = Shape()
    s.append_rect(0, 0, W, H)
    s.set_fill_color(255, 0, 0, 255)
    c.add(s)
    c.draw(True)
    c.sync()
    return c


def test_render_produces_nonzero_bytes():
    c = _render_red_rect()
    data = bytes(c)
    assert any(b != 0 for b in data), "rendered buffer should have pixels"


def test_render_red_rect_pixel_value():
    """In ARGB8888 a fully opaque red pixel is 0xFFFF0000."""
    c = _render_red_rect()
    data = bytes(c)
    offset = ((H // 2) * W + (W // 2)) * 4
    pixel = struct.unpack_from("<I", data, offset)[0]
    assert pixel == 0xFFFF0000, f"expected 0xFFFF0000, got 0x{pixel:08X}"


def test_render_green_circle():
    c = SwCanvas(W, H, Colorspace.ARGB8888)
    s = Shape()
    s.append_circle(W // 2, H // 2, W // 4, H // 4)
    s.set_fill_color(0, 255, 0, 255)
    c.add(s)
    c.draw(True)
    c.sync()

    data = bytes(c)
    offset = ((H // 2) * W + (W // 2)) * 4
    pixel = struct.unpack_from("<I", data, offset)[0]
    assert pixel == 0xFF00FF00, f"expected 0xFF00FF00, got 0x{pixel:08X}"


def test_render_gradient_varied_pixels():
    c = SwCanvas(W, H, Colorspace.ARGB8888)
    s = Shape()
    s.append_rect(0, 0, W, H)
    grad = LinearGradient(0, 0, W, 0)
    grad.set_color_stops([ColorStop(0, 255, 0, 0), ColorStop(1, 0, 0, 255)])
    s.set_gradient(grad)
    c.add(s)
    c.draw(True)
    c.sync()

    data = bytes(c)
    px_left = struct.unpack_from("<I", data, 0)[0]
    last_row_start = (H - 1) * W * 4
    px_right = struct.unpack_from("<I", data, last_row_start + (W - 1) * 4)[0]
    assert px_left != px_right, "gradient should produce varying pixels"


def test_render_svg_into_canvas():
    """Load SVG data, render, read pixels via bytes(canvas)."""
    svg  = b'<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">'
    svg += b'<circle cx="50" cy="50" r="40" fill="blue"/></svg>'

    c = SwCanvas(100, 100, Colorspace.ARGB8888)
    pic = Picture()
    assert pic.load_data(svg, mimetype="image/svg+xml") == Result.SUCCESS
    c.add(pic)
    c.draw(True)
    c.sync()

    data = bytes(c)
    assert len(data) == 100 * 100 * 4
    offset = (50 * 100 + 50) * 4
    pixel = struct.unpack_from("<I", data, offset)[0]
    assert (pixel & 0xFF000000) != 0, "center pixel should be non-transparent"


def test_render_scene_into_canvas():
    c = SwCanvas(W, H, Colorspace.ARGB8888)

    scene = Scene()
    s1 = Shape()
    s1.append_rect(0, 0, W // 2, H)
    s1.set_fill_color(255, 0, 0, 255)
    scene.add(s1)

    s2 = Shape()
    s2.append_rect(W // 2, 0, W // 2, H)
    s2.set_fill_color(0, 0, 255, 255)
    scene.add(s2)

    c.add(scene)
    c.draw(True)
    c.sync()

    data = bytes(c)
    px_left = struct.unpack_from("<I", data, (H // 2 * W + W // 4) * 4)[0]
    px_right = struct.unpack_from("<I", data, (H // 2 * W + 3 * W // 4) * 4)[0]
    assert px_left != px_right


# == Clear & re-render ==============================================

def test_clear_zeros_buffer():
    c = _render_red_rect()
    assert any(b != 0 for b in bytes(c))
    c.clear()
    assert bytes(c) == b"\x00" * len(c)


def test_rerender_after_clear():
    """Clear, re-render, verify pixels come back."""
    c = SwCanvas(W, H, Colorspace.ARGB8888)
    s = Shape()
    s.append_rect(0, 0, W, H)
    s.set_fill_color(0, 0, 255, 255)
    c.add(s)
    c.draw(True)
    c.sync()

    snap1 = bytes(c)
    c.clear()
    assert bytes(c) == b"\x00" * len(c)

    c.update()
    c.draw(True)
    c.sync()
    snap2 = bytes(c)
    assert snap1 == snap2


# == ABGR colorspace ================================================

def test_abgr8888_colorspace():
    c = SwCanvas(W, H, Colorspace.ABGR8888)
    s = Shape()
    s.append_rect(0, 0, W, H)
    s.set_fill_color(255, 0, 0, 255)
    c.add(s)
    c.draw(True)
    c.sync()

    data = bytes(c)
    offset = (H // 2 * W + W // 2) * 4
    pixel = struct.unpack_from("<I", data, offset)[0]
    assert pixel == 0xFF0000FF, f"expected ABGR red 0xFF0000FF, got 0x{pixel:08X}"
