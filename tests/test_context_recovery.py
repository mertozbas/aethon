"""Tests for context-window-overflow recovery in AethonRuntime."""

import json

from aethon.agent.runtime import AethonRuntime


def test_detects_context_overflow_errors():
    """The proxy/OpenAI 'context window exceeded' messages are recognised."""
    samples = [
        "Codex API error (502): Your input exceeds the context window of this model.",
        "This model's maximum context length is 128000 tokens",
        "context_length_exceeded",
        "input is too long for the model",
    ]
    for s in samples:
        assert AethonRuntime._is_context_overflow_error(Exception(s)), s


def test_ignores_unrelated_errors():
    assert not AethonRuntime._is_context_overflow_error(Exception("connection refused"))
    assert not AethonRuntime._is_context_overflow_error(Exception("401 invalid api key"))


def test_reset_session_clears_message_history(tmp_path):
    """_reset_session deletes a session's persisted messages and evicts the agent."""
    rt = AethonRuntime.__new__(AethonRuntime)  # no model/backend needed

    class _Cfg:
        class session:
            storage_dir = str(tmp_path)
    rt.config = _Cfg()
    rt.agents = {"cli:local": object()}

    # Lay down a couple of fake persisted messages.
    msgs = tmp_path / "session_cli:local" / "agents" / "agent_main" / "messages"
    msgs.mkdir(parents=True)
    (msgs / "message_0.json").write_text(json.dumps({"message": {"content": [{"text": "hi"}]}}))
    (msgs / "message_1.json").write_text(json.dumps({"message": {"content": [{"text": "yo"}]}}))

    rt._reset_session("cli:local")

    assert list(msgs.glob("message_*.json")) == []   # history cleared from the live dir
    assert "cli:local" not in rt.agents              # agent evicted (reloads fresh)
    # Not deleted — moved to a backup batch so nothing is lost.
    backed_up = list((msgs.parent / "cleared").glob("batch_*/message_*.json"))
    assert len(backed_up) == 2
