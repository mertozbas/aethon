"""Shared test fixtures."""

import pytest
import requests

from aethon.config import AethonConfig


def _ollama_available() -> bool:
    """Check if Ollama is running and accessible."""
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


_OLLAMA_UP = _ollama_available()


def pytest_collection_modifyitems(config, items):
    """Auto-skip tests marked with @pytest.mark.ollama when Ollama is down."""
    if _OLLAMA_UP:
        return
    skip = pytest.mark.skip(reason="Ollama not reachable — skipping")
    for item in items:
        if "ollama" in item.keywords:
            item.add_marker(skip)


@pytest.fixture
def default_config():
    """Default AethonConfig with default values."""
    return AethonConfig()


@pytest.fixture
def workspace_dir(tmp_path):
    """Temporary workspace directory with default files."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "SOUL.md").write_text("Test kisilik", encoding="utf-8")
    (workspace / "TOOLS.md").write_text("Test tercihler", encoding="utf-8")
    (workspace / "CONTEXT.md").write_text("Test baglam", encoding="utf-8")
    return workspace


@pytest.fixture
def workspace_with_sops(workspace_dir):
    """Workspace with SOP files."""
    sops_dir = workspace_dir / "sops"
    sops_dir.mkdir()
    (sops_dir / "morning-brief.sop.md").write_text("# Morning Brief SOP")
    (sops_dir / "weekly-report.sop.md").write_text("# Weekly Report SOP")
    return workspace_dir


@pytest.fixture
def config_with_workspace(tmp_path, workspace_dir):
    """Config pointing to temporary workspace."""
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()

    return AethonConfig(
        paths=AethonConfig.model_fields["paths"].default.__class__(
            workspace=str(workspace_dir),
            sessions=str(sessions_dir),
            memory_db=str(tmp_path / "memory.sqlite"),
            logs=str(logs_dir),
            credentials=str(tmp_path / "credentials"),
        )
    )
