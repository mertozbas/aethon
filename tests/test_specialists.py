"""Tests for SpecialistFactory."""

import pytest

from aethon.agent.fake_model import EchoModel

from aethon.agent.specialists import SpecialistFactory, SPECIALIST_CONFIGS


@pytest.fixture
def model():
    return EchoModel()


@pytest.fixture
def factory(model):
    return SpecialistFactory(model)


def test_factory_creation(factory):
    """SpecialistFactory creates successfully."""
    assert factory._cache == {}


def test_get_coder(factory):
    """Can create coder specialist."""
    agent = factory.get("coder")
    assert agent.name == "Coder"


def test_get_researcher(factory):
    """Can create researcher specialist."""
    agent = factory.get("researcher")
    assert agent.name == "Researcher"


def test_get_analyst(factory):
    """Can create analyst specialist."""
    agent = factory.get("analyst")
    assert agent.name == "Analyst"


def test_get_planner(factory):
    """Can create planner specialist."""
    agent = factory.get("planner")
    assert agent.name == "Planner"


def test_unknown_specialist_raises(factory):
    """Unknown specialist name raises ValueError."""
    with pytest.raises(ValueError, match="Unknown specialist"):
        factory.get("nonexistent")


def test_cache_returns_same_agent(factory):
    """Cache returns the same agent instance."""
    agent1 = factory.get("coder")
    agent2 = factory.get("coder")
    assert agent1 is agent2


def test_get_all(factory):
    """get_all returns all 4 specialists."""
    all_agents = factory.get_all()
    assert len(all_agents) == 4
    assert set(all_agents.keys()) == {"coder", "researcher", "analyst", "planner"}


def test_specialist_configs_complete():
    """All 4 specialist configs are defined."""
    assert len(SPECIALIST_CONFIGS) == 4
    for name in ["coder", "researcher", "analyst", "planner"]:
        config = SPECIALIST_CONFIGS[name]
        assert "name" in config
        assert "system_prompt" in config
        assert "tools" in config
        assert len(config["tools"]) > 0


def test_specialists_have_conversation_manager(factory):
    """R8 regression: specialists are process-cached and reused for every
    delegation — without a conversation manager their history grows unbounded
    until the model rejects the request (context overflow)."""
    from strands.agent.conversation_manager import SummarizingConversationManager

    agent = factory.get("coder")
    assert isinstance(agent.conversation_manager, SummarizingConversationManager)


def test_factory_honors_session_config(model):
    """summary_ratio / preserve_recent_messages come from session config."""
    from aethon.config import SessionConfig

    factory = SpecialistFactory(
        model, session_config=SessionConfig(summary_ratio=0.5, preserve_recent_messages=4)
    )
    assert factory._summary_ratio == 0.5
    assert factory._preserve_recent == 4
