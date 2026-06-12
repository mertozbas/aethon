"""Tests for the scout specialist (Phase 10 E4)."""

from aethon.agent.specialists import SPECIALIST_CONFIGS
from aethon.tools import delegate


def test_scout_config_is_read_oriented():
    cfg = SPECIALIST_CONFIGS["scout"]
    assert cfg["name"] == "Scout"
    # Its whole point: return a conclusion, never dump raw material.
    prompt = cfg["system_prompt"].lower()
    assert "conclusion" in prompt and "never" in prompt
    # Read-oriented: no file_write / editor among its tools.
    from strands_tools import file_write, editor
    assert file_write not in cfg["tools"]
    assert editor not in cfg["tools"]


def test_ask_scout_delegates_and_returns_conclusion():
    class _FakeScout:
        def __call__(self, query):
            return "kısa sonuç: X, aethon/foo.py:42'de ele alınıyor."

    class _Factory:
        def __init__(self):
            self.asked = None

        def get(self, name):
            self.asked = name
            return _FakeScout()

    factory = _Factory()
    delegate.set_specialist_factory(factory)
    try:
        out = delegate.ask_scout._tool_func(query="X nerede ele alınıyor?")
        assert factory.asked == "scout"
        assert "kısa sonuç" in out
    finally:
        delegate.set_specialist_factory(None)


def test_ask_scout_without_factory():
    delegate.set_specialist_factory(None)
    assert "not started" in delegate.ask_scout._tool_func(query="x").lower()
