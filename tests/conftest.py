"""Shared fixtures for thorvg-cython tests."""
import pytest
from thorvg_cython import Engine, SwCanvas, Colorspace

W, H = 200, 200


@pytest.fixture(scope="session", autouse=True)
def engine():
    """Initialize the ThorVG engine once for the whole test session."""
    eng = Engine(0)
    yield eng
    eng.term()


@pytest.fixture()
def canvas():
    """SwCanvas with integrated pixel buffer, ready to draw."""
    return SwCanvas(W, H, Colorspace.ARGB8888)


def render(canvas):
    """Helper: draw + sync a canvas and return Result pair."""
    r1 = canvas.draw(True)
    r2 = canvas.sync()
    return r1, r2
