"""Shared fixtures for thorvg-cython tests."""
import pytest
from thorvg_cython import Engine, SwCanvas, PixelBuffer, Colorspace

W, H = 200, 200


@pytest.fixture(scope="session", autouse=True)
def engine():
    """Initialize the ThorVG engine once for the whole test session."""
    eng = Engine(0)
    yield eng
    eng.term()


@pytest.fixture()
def pixel_buffer():
    """Fresh 200x200 ARGB8888 PixelBuffer."""
    return PixelBuffer(W, H, Colorspace.ARGB8888)


@pytest.fixture()
def canvas(pixel_buffer):
    """SwCanvas bound to a PixelBuffer, ready to draw."""
    c = SwCanvas()
    c.set_target_buffer(pixel_buffer)
    return c


def render(canvas):
    """Helper: draw + sync a canvas and return Result pair."""
    r1 = canvas.draw(True)
    r2 = canvas.sync()
    return r1, r2
