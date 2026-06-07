"""Tests for SystemPromptComposer."""

import pytest

from aethon.agent.prompt import SystemPromptComposer
from aethon.config import PromptConfig


def test_compose_empty_workspace(tmp_path):
    """Empty workspace produces minimal prompt."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    composer = SystemPromptComposer(str(workspace))
    prompt = composer.compose()
    # Should at least have timestamp
    assert "Time" in prompt


def test_compose_with_soul(workspace_dir):
    """SOUL.md content included in prompt."""
    composer = SystemPromptComposer(str(workspace_dir))
    prompt = composer.compose()
    assert "Test kisilik" in prompt
    assert "Personality" in prompt


def test_compose_with_tools(workspace_dir):
    """TOOLS.md content included in prompt."""
    composer = SystemPromptComposer(str(workspace_dir))
    prompt = composer.compose()
    assert "Test tercihler" in prompt
    assert "User Preferences" in prompt


def test_compose_with_context(workspace_dir):
    """CONTEXT.md content included in prompt."""
    composer = SystemPromptComposer(str(workspace_dir))
    prompt = composer.compose()
    assert "Test baglam" in prompt


def test_compose_with_session_id(workspace_dir):
    """Session ID included in prompt."""
    composer = SystemPromptComposer(str(workspace_dir))
    prompt = composer.compose(session_id="cli:local")
    assert "cli:local" in prompt
    assert "Active Session" in prompt


def test_compose_without_session_id(workspace_dir):
    """No session section when session_id is empty."""
    composer = SystemPromptComposer(str(workspace_dir))
    prompt = composer.compose(session_id="")
    assert "Active Session" not in prompt


def test_compose_with_sops(workspace_with_sops):
    """SOP list included in prompt."""
    composer = SystemPromptComposer(str(workspace_with_sops))
    prompt = composer.compose()
    assert "Available SOP Commands" in prompt
    assert "/morning-brief" in prompt
    assert "/weekly-report" in prompt


def test_compose_layers_separated(workspace_dir):
    """Layers are separated by ---."""
    composer = SystemPromptComposer(str(workspace_dir))
    prompt = composer.compose(session_id="test")
    assert "---" in prompt


def test_compose_includes_environment(workspace_dir):
    """Environment awareness layer present by default."""
    composer = SystemPromptComposer(str(workspace_dir))
    prompt = composer.compose()
    assert "System Environment" in prompt
    assert "- OS:" in prompt


def test_compose_environment_can_be_disabled(workspace_dir):
    """include_environment=False omits the environment layer."""
    composer = SystemPromptComposer(
        str(workspace_dir), config=PromptConfig(include_environment=False)
    )
    prompt = composer.compose()
    assert "System Environment" not in prompt


def test_compose_reads_learnings(tmp_path):
    """LEARNINGS.md is folded into the prompt when present and enabled."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "LEARNINGS.md").write_text("# Learnings\n### build\nuse make\n")
    composer = SystemPromptComposer(str(workspace), config=PromptConfig())
    assert "use make" in composer.compose()
    composer_off = SystemPromptComposer(
        str(workspace), config=PromptConfig(include_learnings=False)
    )
    assert "use make" not in composer_off.compose()


def test_compose_recent_logs(tmp_path):
    """Recent-logs layer reads aethon.log from the logs dir when enabled."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "aethon.log").write_text("2026-01-01 INFO aethon.x: started\n")
    composer = SystemPromptComposer(
        str(workspace), config=PromptConfig(), logs_dir=str(logs)
    )
    prompt = composer.compose()
    assert "Recent Activity Logs" in prompt
    assert "started" in prompt


def test_compose_shell_history_off_by_default(workspace_dir):
    """Shell history is omitted unless explicitly enabled (privacy)."""
    composer = SystemPromptComposer(str(workspace_dir), config=PromptConfig())
    assert "Recent Shell History" not in composer.compose()
