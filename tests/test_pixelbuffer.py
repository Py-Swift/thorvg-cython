"""Tests for PixelBuffer and the buffer protocol (PEP 3118).

These tests verify that PixelBuffer works as a zero-copy backing store
for SwCanvas and that frameworks can read pixels via ``bytes(buf)``,
``memoryview(buf)``, or any API accepting buffer-protocol objects.
"""
import struct
from thorvg_cython import (
    Result, SwCanvas, Shape, Scene, Picture, PixelBuffer,
    Colorspace, LinearGradient, ColorStop,
)
from conftest import W, H, render


# ── PixelBuffer creation ─────────────────────────────────────────

def test_pixelbuf_create():
    buf = PixelBuffer(320, 240, Colorspace.ARGB8888)
    assert buf.width == 320
    assert buf.height == 240
    assert buf.stride == 320
    assert buf.colorspace == Colorspace.ARGB8888
    assert buf.nbytes == 320 * 240 * 4
    assert len(buf) == buf.nbytes


def test_pixelbuf_custom_stride():
    buf = PixelBuffer(100, 100, Colorspace.ARGB8888, stride=128)
    assert buf.stride == 128
    assert buf.nbytes == 128 * 100 * 4


def test_pixelbuf_repr():
    buf = PixelBuffer(64, 64, Colorspace.ABGR8888)
    r = repr(buf)
    assert "64x64" in r
    assert "ABGR8888" in r


def test_pixelbuf_ptr():
    buf = PixelBuffer(10, 10)
    assert isinstance(buf.ptr, int)
    assert buf.ptr > 0


def test_pixelbuf_starts_zeroed():
    buf = PixelBuffer(4, 4)
    data = bytes(buf)
    assert data == b"\x00" * (4 * 4 * 4)


# ── Buffer protocol ─────────────────────────────────────────────

def test_memoryview_basic():
    buf = PixelBuffer(10, 10)
    mv = memoryview(buf)
    assert mv.format == "B"
    assert mv.ndim == 1
    assert mv.readonly is False
    assert len(mv) == 10 * 10 * 4


def test_memoryview_writable():
    buf = PixelBuffer(2, 2)
    mv = memoryview(buf)
    # write directly into the pixel buffer
    mv[0] = 0xFF
    mv[1] = 0xAB
    data = bytes(buf)
    assert data[0] == 0xFF
    assert data[1] == 0xAB


def test_bytes_copy():
    """bytes(buf) produces an independent copy of the pixel data."""
    buf = PixelBuffer(4, 4)
    snap1 = bytes(buf)
    # mutate via memoryview
    mv = memoryview(buf)
    mv[0] = 42
    snap2 = bytes(buf)
    assert snap1[0] == 0
    assert snap2[0] == 42


def test_bytearray_from_buffer():
    buf = PixelBuffer(4, 4)
    ba = bytearray(buf)
    assert len(ba) == 4 * 4 * 4
    assert isinstance(ba, bytearray)


# ── SwCanvas + PixelBuffer integration ───────────────────────────

def test_set_target_buffer():
    buf = PixelBuffer(W, H, Colorspace.ARGB8888)
    c = SwCanvas()
    assert c.set_target_buffer(buf) == Result.SUCCESS
    assert c.buffer is buf


def test_buffer_ref_kept():
    """SwCanvas keeps the PixelBuffer alive."""
    c = SwCanvas()
    buf = PixelBuffer(W, H, Colorspace.ARGB8888)
    c.set_target_buffer(buf)
    assert c.buffer is buf
    # overwrite with a new buffer
    buf2 = PixelBuffer(W, H, Colorspace.ARGB8888)
    c.set_target_buffer(buf2)
    assert c.buffer is buf2


def test_set_target_raw_clears_ref():
    """set_target (raw ptr) should release the PixelBuffer ref."""
    c = SwCanvas()
    buf = PixelBuffer(W, H, Colorspace.ARGB8888)
    c.set_target_buffer(buf)
    assert c.buffer is buf
    # switching to a different PixelBuffer should drop the old ref
    buf2 = PixelBuffer(W, H, Colorspace.ARGB8888)
    c.set_target_buffer(buf2)
    assert c.buffer is buf2
    assert c.buffer is not buf


# ── Rendering into PixelBuffer → bytes(buf) ─────────────────────

def _render_red_rect():
    """Render a full-size red rect into a PixelBuffer, return buf."""
    buf = PixelBuffer(W, H, Colorspace.ARGB8888)
    c = SwCanvas()
    c.set_target_buffer(buf)

    s = Shape()
    s.append_rect(0, 0, W, H)
    s.set_fill_color(255, 0, 0, 255)
    c.add(s)
    c.draw(True)
    c.sync()
    return buf


def test_render_produces_nonzero_bytes():
    buf = _render_red_rect()
    data = bytes(buf)
    assert any(b != 0 for b in data), "rendered buffer should have pixels"


def test_render_red_rect_pixel_value():
    """In ARGB8888 a fully opaque red pixel is 0xFFFF0000."""
    buf = _render_red_rect()
    data = bytes(buf)
    # sample pixel at (W//2, H//2)
    offset = ((H // 2) * W + (W // 2)) * 4
    pixel = struct.unpack_from("<I", data, offset)[0]
    assert pixel == 0xFFFF0000, f"expected 0xFFFF0000, got 0x{pixel:08X}"


def test_render_green_circle():
    buf = PixelBuffer(W, H, Colorspace.ARGB8888)
    c = SwCanvas()
    c.set_target_buffer(buf)

    s = Shape()
    s.append_circle(W // 2, H // 2, W // 4, H // 4)
    s.set_fill_color(0, 255, 0, 255)
    c.add(s)
    c.draw(True)
    c.sync()

    data = bytes(buf)
    # center pixel should be green (0xFF00FF00)
    offset = ((H // 2) * W + (W // 2)) * 4
    pixel = struct.unpack_from("<I", data, offset)[0]
    assert pixel == 0xFF00FF00, f"expected 0xFF00FF00, got 0x{pixel:08X}"


def test_render_gradient_has_varied_pixels():
    buf = PixelBuffer(W, H, Colorspace.ARGB8888)
    c = SwCanvas()
    c.set_target_buffer(buf)

    s = Shape()
    s.append_rect(0, 0, W, H)
    grad = LinearGradient(0, 0, W, 0)
    grad.set_color_stops([ColorStop(0, 255, 0, 0), ColorStop(1, 0, 0, 255)])
    s.set_gradient(grad)
    c.add(s)
    c.draw(True)
    c.sync()

    data = bytes(buf)
    # left edge and right edge should have different pixel values
    px_left = struct.unpack_from("<I", data, 0)[0]
    last_row_start = (H - 1) * W * 4
    px_right = struct.unpack_from("<I", data, last_row_start + (W - 1) * 4)[0]
    assert px_left != px_right, "gradient should produce varying pixels"


def test_render_svg_into_buffer():
    """Load SVG data, render into PixelBuffer, read pixels via bytes()."""
    svg = b'''<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
      <circle cx="50" cy="50" r="40" fill="blue"/>
    </svg>'''

    buf = PixelBuffer(100, 100, Colorspace.ARGB8888)
    c = SwCanvas()
    c.set_target_buffer(buf)

    pic = Picture()
    assert pic.load_data(svg, mimetype="image/svg+xml") == Result.SUCCESS
    c.add(pic)
    c.draw(True)
    c.sync()

    data = bytes(buf)
    assert len(data) == 100 * 100 * 4
    # center should be blue
    offset = (50 * 100 + 50) * 4
    pixel = struct.unpack_from("<I", data, offset)[0]
    assert (pixel & 0xFF000000) != 0, "center pixel should be non-transparent"


def test_render_scene_into_buffer():
    buf = PixelBuffer(W, H, Colorspace.ARGB8888)
    c = SwCanvas()
    c.set_target_buffer(buf)

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

    data = bytes(buf)
    # left half: red, right half: blue
    px_left = struct.unpack_from("<I", data, (H // 2 * W + W // 4) * 4)[0]
    px_right = struct.unpack_from("<I", data, (H // 2 * W + 3 * W // 4) * 4)[0]
    assert px_left != px_right


# ── Clear ────────────────────────────────────────────────────────

def test_clear_zeros_buffer():
    buf = _render_red_rect()
    assert any(b != 0 for b in bytes(buf))
    buf.clear()
    assert bytes(buf) == b"\x00" * buf.nbytes


def test_rerender_after_clear():
    """Clear, re-render, verify pixels come back."""
    buf = PixelBuffer(W, H, Colorspace.ARGB8888)
    c = SwCanvas()
    c.set_target_buffer(buf)

    s = Shape()
    s.append_rect(0, 0, W, H)
    s.set_fill_color(0, 0, 255, 255)
    c.add(s)
    c.draw(True)
    c.sync()

    snap1 = bytes(buf)
    buf.clear()
    assert bytes(buf) == b"\x00" * buf.nbytes

    # re-render
    c.update()
    c.draw(True)
    c.sync()
    snap2 = bytes(buf)
    assert snap1 == snap2


# ── Multiple colorspaces ────────────────────────────────────────

def test_abgr8888_colorspace():
    buf = PixelBuffer(W, H, Colorspace.ABGR8888)
    c = SwCanvas()
    c.set_target_buffer(buf)

    s = Shape()
    s.append_rect(0, 0, W, H)
    s.set_fill_color(255, 0, 0, 255)
    c.add(s)
    c.draw(True)
    c.sync()

    data = bytes(buf)
    offset = (H // 2 * W + W // 2) * 4
    pixel = struct.unpack_from("<I", data, offset)[0]
    # ABGR8888: red = 0xFF0000FF
    assert pixel == 0xFF0000FF, f"expected ABGR red 0xFF0000FF, got 0x{pixel:08X}"
