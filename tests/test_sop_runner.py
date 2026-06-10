"""Tests for SOPRunner."""

import pytest

from aethon.sops.runner import SOPRunner


@pytest.fixture
def sop_workspace(tmp_path):
    """Create a workspace with custom SOPs."""
    sops_dir = tmp_path / "sops"
    sops_dir.mkdir()
    (sops_dir / "morning-brief.sop.md").write_text(
        "# Morning Brief\n\n"
        "## Overview\nSabah brifing SOP'u.\n\n"
        "## Steps\n1. Hava durumu\n2. Takvim\n",
        encoding="utf-8",
    )
    (sops_dir / "weekly-report.sop.md").write_text(
        "# Weekly Report\n\n"
        "## Overview\nHaftalik rapor olusturma.\n\n"
        "## Steps\n1. Istatistikler\n2. Ozet\n",
        encoding="utf-8",
    )
    return sops_dir


def test_runner_creation(sop_workspace):
    """SOPRunner creates with custom SOPs."""
    runner = SOPRunner([str(sop_workspace)], builtin_enabled=False)
    assert len(runner._sops) == 2


def test_builtin_sops_loaded():
    """Built-in SOPs load from strands-agents-sops."""
    runner = SOPRunner([], builtin_enabled=True)
    names = [s["name"] for s in runner.list_sops()]
    assert "code-assist" in names
    assert "pdd" in names
    assert "codebase-summary" in names


def test_builtin_sops_disabled():
    """Built-in SOPs are skipped when disabled."""
    runner = SOPRunner([], builtin_enabled=False)
    assert len(runner._sops) == 0


def test_custom_sops_loaded(sop_workspace):
    """Custom SOP files are loaded from directory."""
    runner = SOPRunner([str(sop_workspace)], builtin_enabled=False)
    names = [s["name"] for s in runner.list_sops()]
    assert "morning-brief" in names
    assert "weekly-report" in names


def test_list_sops_with_description(sop_workspace):
    """list_sops returns name and description."""
    runner = SOPRunner([str(sop_workspace)], builtin_enabled=False)
    sops = runner.list_sops()
    brief = next(s for s in sops if s["name"] == "morning-brief")
    assert "Sabah brifing" in brief["description"]


def test_get_sop(sop_workspace):
    """get_sop returns SOP content."""
    runner = SOPRunner([str(sop_workspace)], builtin_enabled=False)
    content = runner.get_sop("morning-brief")
    assert content is not None
    assert "Morning Brief" in content


def test_get_sop_nonexistent(sop_workspace):
    """get_sop returns None for unknown SOP."""
    runner = SOPRunner([str(sop_workspace)], builtin_enabled=False)
    assert runner.get_sop("nonexistent") is None


def test_is_sop_command_valid(sop_workspace):
    """is_sop_command recognizes valid SOP command."""
    runner = SOPRunner([str(sop_workspace)], builtin_enabled=False)
    is_sop, name, user_input = runner.is_sop_command("/morning-brief sabah guncesi")
    assert is_sop is True
    assert name == "morning-brief"
    assert user_input == "sabah guncesi"


def test_is_sop_command_no_args(sop_workspace):
    """is_sop_command works without arguments."""
    runner = SOPRunner([str(sop_workspace)], builtin_enabled=False)
    is_sop, name, user_input = runner.is_sop_command("/morning-brief")
    assert is_sop is True
    assert name == "morning-brief"
    assert user_input == ""


def test_is_sop_command_normal_message(sop_workspace):
    """is_sop_command rejects normal messages."""
    runner = SOPRunner([str(sop_workspace)], builtin_enabled=False)
    is_sop, name, user_input = runner.is_sop_command("normal mesaj")
    assert is_sop is False


def test_is_sop_command_unknown_command(sop_workspace):
    """is_sop_command rejects unknown SOP commands."""
    runner = SOPRunner([str(sop_workspace)], builtin_enabled=False)
    is_sop, name, user_input = runner.is_sop_command("/nonexistent")
    assert is_sop is False


def test_custom_overrides_builtin(sop_workspace):
    """Custom SOP overrides built-in with same name."""
    # Create a custom code-assist SOP
    (sop_workspace / "code-assist.sop.md").write_text(
        "# Custom Code Assist\n\n## Overview\nCustom version.\n",
        encoding="utf-8",
    )
    runner = SOPRunner([str(sop_workspace)], builtin_enabled=True)
    content = runner.get_sop("code-assist")
    assert "Custom Code Assist" in content


def test_nonexistent_directory():
    """SOPRunner handles nonexistent directories gracefully."""
    runner = SOPRunner(["/tmp/nonexistent_sop_dir_12345"], builtin_enabled=False)
    assert len(runner._sops) == 0
