"""Tests for Engine, version, init/term and context-manager."""
from thorvg_cython import Engine, Result


def test_engine_init_result(engine):
    assert engine.init_result == Result.SUCCESS


def test_engine_version(engine):
    r, major, minor, micro, ver_str = engine.version()
    assert r == Result.SUCCESS
    assert isinstance(major, int) and major >= 0
    assert isinstance(minor, int)
    assert isinstance(micro, int)
    assert isinstance(ver_str, str) and len(ver_str) > 0


def test_engine_context_manager():
    with Engine(0) as eng:
        r, *_ = eng.version()
        assert r == Result.SUCCESS
