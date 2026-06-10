"""Tests for AnglicizationGuardHookProvider (Phase 8 / R14)."""

from unittest.mock import MagicMock

from aethon.agent.hooks.anglicization_guard import AnglicizationGuardHookProvider


def _event(tool_name, tool_input):
    event = MagicMock()
    event.tool_use = {"name": tool_name, "input": tool_input}
    event.cancel_tool = None
    return event


def test_tr_to_en_replacement_is_paused():
    hook = AnglicizationGuardHookProvider()
    event = _event("editor", {
        "command": "str_replace",
        "old_str": "# Kullanıcı tercihlerini yükle",
        "new_str": "# Load user preferences",
    })
    hook.check_edit(event)
    assert event.cancel_tool
    assert "anglicize" in event.cancel_tool


def test_identical_reissue_passes_in_advisory_mode():
    """After the one-time reminder, an identical edit is an explicit decision."""
    hook = AnglicizationGuardHookProvider()
    tool_input = {
        "old_str": "# Görev tamamlandı",
        "new_str": "# Task is complete",
    }
    first = _event("editor", tool_input)
    hook.check_edit(first)
    assert first.cancel_tool

    second = _event("editor", tool_input)
    hook.check_edit(second)
    assert not second.cancel_tool


def test_strict_mode_always_blocks():
    hook = AnglicizationGuardHookProvider(strict=True)
    tool_input = {"old_str": "çalışıyor", "new_str": "it works"}
    for _ in range(2):
        event = _event("editor", tool_input)
        hook.check_edit(event)
        assert event.cancel_tool


def test_tr_to_tr_replacement_passes():
    hook = AnglicizationGuardHookProvider()
    event = _event("editor", {
        "old_str": "# Eski açıklama",
        "new_str": "# Yeni ve daha iyi açıklama",
    })
    hook.check_edit(event)
    assert not event.cancel_tool


def test_en_to_en_replacement_passes():
    hook = AnglicizationGuardHookProvider()
    event = _event("editor", {
        "old_str": "# old comment",
        "new_str": "# new comment",
    })
    hook.check_edit(event)
    assert not event.cancel_tool


def test_pure_deletion_passes():
    """Removing text entirely is not anglicization."""
    hook = AnglicizationGuardHookProvider()
    event = _event("editor", {"old_str": "# Geçici kod", "new_str": ""})
    hook.check_edit(event)
    assert not event.cancel_tool


def test_alternative_key_names_are_guarded():
    hook = AnglicizationGuardHookProvider()
    event = _event("edit", {
        "old_string": "değişken adı",
        "new_string": "variable name",
    })
    hook.check_edit(event)
    assert event.cancel_tool


def test_non_edit_tools_are_ignored():
    hook = AnglicizationGuardHookProvider()
    event = _event("shell", {"command": "echo 'çalışıyor' > x && echo done"})
    hook.check_edit(event)
    assert not event.cancel_tool


# --- review fixes: file_write overwrite guard + defensive paths ---


def test_file_write_tr_to_en_overwrite_is_paused(tmp_path):
    """file_write replaces whole files — compare against what is on disk."""
    target = tmp_path / "notlar.md"
    target.write_text("# Önemli notlar\nyarın toplantı var", encoding="utf-8")

    hook = AnglicizationGuardHookProvider()
    event = _event("file_write", {
        "path": str(target),
        "content": "# Important notes\nmeeting tomorrow",
    })
    hook.check_edit(event)
    assert event.cancel_tool

    # Identical re-issue is an explicit decision (advisory mode).
    second = _event("file_write", {
        "path": str(target),
        "content": "# Important notes\nmeeting tomorrow",
    })
    hook.check_edit(second)
    assert not second.cancel_tool


def test_file_write_new_file_passes(tmp_path):
    hook = AnglicizationGuardHookProvider()
    event = _event("file_write", {
        "path": str(tmp_path / "yeni.md"),
        "content": "# brand new english file",
    })
    hook.check_edit(event)
    assert not event.cancel_tool


def test_existing_cancellation_is_preserved():
    hook = AnglicizationGuardHookProvider()
    event = _event("editor", {"old_str": "çalışıyor", "new_str": "works"})
    event.cancel_tool = "BLOCKED by security"
    hook.check_edit(event)
    assert event.cancel_tool == "BLOCKED by security"


def test_non_dict_input_does_not_crash():
    hook = AnglicizationGuardHookProvider()
    event = _event("editor", "garip girdi")
    hook.check_edit(event)
    assert not event.cancel_tool
