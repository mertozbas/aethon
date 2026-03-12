"""Tests for SystemPromptComposer."""

import pytest

from aethon.agent.prompt import SystemPromptComposer


def test_compose_empty_workspace(tmp_path):
    """Empty workspace produces minimal prompt."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    composer = SystemPromptComposer(str(workspace))
    prompt = composer.compose()
    # Should at least have timestamp
    assert "Zaman" in prompt


def test_compose_with_soul(workspace_dir):
    """SOUL.md content included in prompt."""
    composer = SystemPromptComposer(str(workspace_dir))
    prompt = composer.compose()
    assert "Test kisilik" in prompt
    assert "Kisilik" in prompt


def test_compose_with_tools(workspace_dir):
    """TOOLS.md content included in prompt."""
    composer = SystemPromptComposer(str(workspace_dir))
    prompt = composer.compose()
    assert "Test tercihler" in prompt
    assert "Kullanici Tercihleri" in prompt


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
    assert "Aktif Session" in prompt


def test_compose_without_session_id(workspace_dir):
    """No session section when session_id is empty."""
    composer = SystemPromptComposer(str(workspace_dir))
    prompt = composer.compose(session_id="")
    assert "Aktif Session" not in prompt


def test_compose_with_sops(workspace_with_sops):
    """SOP list included in prompt."""
    composer = SystemPromptComposer(str(workspace_with_sops))
    prompt = composer.compose()
    assert "Kullanilabilir Komutlar" in prompt
    assert "/morning-brief" in prompt
    assert "/weekly-report" in prompt


def test_compose_layers_separated(workspace_dir):
    """Layers are separated by ---."""
    composer = SystemPromptComposer(str(workspace_dir))
    prompt = composer.compose(session_id="test")
    assert "---" in prompt
