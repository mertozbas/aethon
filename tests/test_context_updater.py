"""Tests for ContextUpdater."""

import pytest

from aethon.agent.context_updater import ContextUpdater


def test_updater_creation(tmp_path):
    """ContextUpdater can be created."""
    updater = ContextUpdater(str(tmp_path))
    assert updater.context_file == tmp_path / "CONTEXT.md"


def test_update_creates_new_section(tmp_path):
    """Update creates new section in CONTEXT.md."""
    updater = ContextUpdater(str(tmp_path))
    result = updater.update("Proje", "AETHON AI Asistan")
    assert "guncellendi" in result
    content = (tmp_path / "CONTEXT.md").read_text()
    assert "### Proje" in content
    assert "AETHON AI Asistan" in content


def test_update_replaces_existing_section(tmp_path):
    """Update replaces existing section."""
    ctx = tmp_path / "CONTEXT.md"
    ctx.write_text("### Proje\nEski deger\n\n### Dil\nTurkce\n")
    updater = ContextUpdater(str(tmp_path))
    updater.update("Proje", "Yeni deger")
    content = ctx.read_text()
    assert "Yeni deger" in content
    assert "Eski deger" not in content
    assert "### Dil" in content


def test_get_retrieves_value(tmp_path):
    """Get retrieves existing section value."""
    ctx = tmp_path / "CONTEXT.md"
    ctx.write_text("### Proje\nAETHON AI\n\n### Dil\nTurkce\n")
    updater = ContextUpdater(str(tmp_path))
    assert updater.get("Proje") == "AETHON AI"
    assert updater.get("Dil") == "Turkce"


def test_get_returns_none_for_missing(tmp_path):
    """Get returns None for missing key."""
    ctx = tmp_path / "CONTEXT.md"
    ctx.write_text("### Proje\nAETHON\n")
    updater = ContextUpdater(str(tmp_path))
    assert updater.get("Yok") is None


def test_get_returns_none_for_missing_file(tmp_path):
    """Get returns None when CONTEXT.md doesn't exist."""
    updater = ContextUpdater(str(tmp_path))
    assert updater.get("Proje") is None


def test_list_keys(tmp_path):
    """list_keys returns all section keys."""
    ctx = tmp_path / "CONTEXT.md"
    ctx.write_text("### Proje\nAETHON\n\n### Dil\nTurkce\n\n### Durum\nAktif\n")
    updater = ContextUpdater(str(tmp_path))
    keys = updater.list_keys()
    assert keys == ["Proje", "Dil", "Durum"]


def test_list_keys_empty(tmp_path):
    """list_keys returns empty list for empty file."""
    ctx = tmp_path / "CONTEXT.md"
    ctx.write_text("# Mevcut Baglam\n")
    updater = ContextUpdater(str(tmp_path))
    assert updater.list_keys() == []


def test_list_keys_no_file(tmp_path):
    """list_keys returns empty list when file doesn't exist."""
    updater = ContextUpdater(str(tmp_path))
    assert updater.list_keys() == []


def test_multiple_updates(tmp_path):
    """Multiple updates work correctly."""
    updater = ContextUpdater(str(tmp_path))
    updater.update("A", "ilk")
    updater.update("B", "ikinci")
    updater.update("A", "guncellenmis")
    assert updater.get("A") == "guncellenmis"
    assert updater.get("B") == "ikinci"
    keys = updater.list_keys()
    assert len(keys) == 2


def test_unicode_content(tmp_path):
    """Unicode content handled correctly."""
    updater = ContextUpdater(str(tmp_path))
    updater.update("Dil", "Turkce: ozel karakterler")
    assert updater.get("Dil") == "Turkce: ozel karakterler"
