"""Tests for delegate tools."""

import pytest

from aethon.agent.fake_model import EchoModel

from aethon.agent.specialists import SpecialistFactory
from aethon.tools.delegate import (
    set_specialist_factory,
    ask_coder,
    ask_researcher,
    ask_analyst,
    ask_planner,
)
import aethon.tools.delegate as delegate_module


@pytest.fixture
def model():
    return EchoModel()


@pytest.fixture
def factory(model):
    return SpecialistFactory(model)


def test_set_specialist_factory(factory):
    """set_specialist_factory sets the global reference."""
    set_specialist_factory(factory)
    assert delegate_module._specialist_factory is factory
    # Cleanup
    set_specialist_factory(None)


def test_ask_coder_without_factory():
    """ask_coder returns error without factory."""
    set_specialist_factory(None)
    # DecoratedFunctionTool wraps the function — call the inner function
    result = ask_coder._tool_func(task="test")
    assert "Error" in result


def test_ask_researcher_without_factory():
    """ask_researcher returns error without factory."""
    set_specialist_factory(None)
    result = ask_researcher._tool_func(query="test")
    assert "Error" in result


def test_ask_analyst_without_factory():
    """ask_analyst returns error without factory."""
    set_specialist_factory(None)
    result = ask_analyst._tool_func(data_task="test")
    assert "Error" in result


def test_ask_planner_without_factory():
    """ask_planner returns error without factory."""
    set_specialist_factory(None)
    result = ask_planner._tool_func(planning_task="test")
    assert "Error" in result


@pytest.mark.ollama
def test_ask_coder_with_factory(factory):
    """ask_coder delegates to coder specialist (real Ollama)."""
    set_specialist_factory(factory)
    result = ask_coder._tool_func(task="2+2 kac eder? Sadece sayiyi yaz.")
    assert result  # Should return something non-empty
    set_specialist_factory(None)


@pytest.mark.ollama
def test_ask_planner_with_factory(factory):
    """ask_planner delegates to planner specialist (real Ollama)."""
    set_specialist_factory(factory)
    result = ask_planner._tool_func(planning_task="Merhaba de.")
    assert result
    set_specialist_factory(None)
