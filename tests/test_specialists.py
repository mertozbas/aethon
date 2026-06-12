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


# --- S7 review fix: specialists must not escape the sandbox -----------------


def test_specialist_shell_unsandboxed_without_sandbox(model):
    """No sandbox → coder keeps the plain host shell."""
    from strands_tools import shell

    factory = SpecialistFactory(model)
    tools = factory._sandboxed_tools("coder", SPECIALIST_CONFIGS["coder"]["tools"])
    assert shell in tools


def test_specialist_shell_sandboxed_when_enabled(model):
    """Sandbox on → the coder's host shell is swapped for the sandboxed one."""
    from strands_tools import shell
    from aethon.config import SecurityConfig
    from aethon.tools.shell_sandbox import DockerSandbox

    sandbox = DockerSandbox(SecurityConfig(sandbox="docker"), "/ws", runner=lambda *a: None)
    factory = SpecialistFactory(model, sandbox=sandbox)
    tools = factory._sandboxed_tools("coder", SPECIALIST_CONFIGS["coder"]["tools"])
    assert shell not in tools                       # host shell removed
    names = [getattr(t, "tool_name", getattr(t, "__name__", "")) for t in tools]
    assert "shell" in names                         # replaced by a sandboxed shell


def test_specialist_without_shell_untouched(model):
    """A specialist that has no shell (researcher) is unchanged by sandboxing."""
    from aethon.config import SecurityConfig
    from aethon.tools.shell_sandbox import DockerSandbox

    sandbox = DockerSandbox(SecurityConfig(sandbox="docker"), "/ws", runner=lambda *a: None)
    factory = SpecialistFactory(model, sandbox=sandbox)
    before = SPECIALIST_CONFIGS["researcher"]["tools"]
    after = factory._sandboxed_tools("researcher", before)
    assert after == list(before)


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


def test_specialists_receive_hooks_from_factory(model):
    """Review fix: delegated specialists must not bypass the security and
    reliability layer — the factory injects fresh hooks per specialist."""
    calls = []

    def fake_hooks():
        calls.append(1)
        return []

    factory = SpecialistFactory(model, hooks_factory=fake_hooks)
    factory.get("coder")
    factory.get("planner")
    assert len(calls) == 2  # fresh hooks per specialist


def test_runtime_wires_specialist_hooks(tmp_path):
    """Runtime's specialist hook set: security + validator + guard + verify."""
    from aethon.config import (
        AethonConfig, ModelConfig, PathsConfig, MultiAgentConfig,
    )
    from aethon.agent.runtime import AethonRuntime

    workspace = tmp_path / "ws"
    workspace.mkdir()
    config = AethonConfig(
        model=ModelConfig(provider="fake", model_id="fake"),
        multi_agent=MultiAgentConfig(enabled=True),
        paths=PathsConfig(
            workspace=str(workspace), sessions=str(tmp_path / "s"),
            logs=str(tmp_path / "l"), memory_db=str(tmp_path / "m.sqlite"),
            credentials=str(tmp_path / "c"),
        ),
    )
    runtime = AethonRuntime(config)
    names = [type(h).__name__ for h in runtime._get_specialist_hooks()]
    assert "SecurityHookProvider" in names
    assert "InputValidatorHookProvider" in names
    assert "AnglicizationGuardHookProvider" in names
    assert "PostEditVerifyHookProvider" in names
    assert "CompletionGateHookProvider" not in names  # runtime-coupled; excluded
