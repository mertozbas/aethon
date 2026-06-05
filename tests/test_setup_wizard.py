"""Tests for the first-run setup wizard and the init/doctor/version CLI."""

from click.testing import CliRunner

from aethon.__main__ import main
from aethon.config import AethonConfig
from aethon.setup_wizard import (
    PROVIDERS,
    build_memory_config,
    build_model_config,
    meridian_status,
)


def test_providers_include_meridian_default():
    assert "meridian" in PROVIDERS
    # meridian default model is the latest Opus, needs no API key
    desc, default_model, needs_key, _env = PROVIDERS["meridian"]
    assert default_model == "claude-opus-4-8"
    assert needs_key is False


def test_build_model_config_meridian():
    assert build_model_config("meridian", model_id="claude-opus-4-8") == {
        "provider": "meridian",
        "model_id": "claude-opus-4-8",
    }


def test_build_model_config_ollama_host():
    m = build_model_config("ollama", model_id="llama3.1", host="http://h:11434")
    assert m["provider"] == "ollama"
    assert m["host"] == "http://h:11434"


def test_build_model_config_api_key():
    m = build_model_config("openai", model_id="gpt-4o", api_key="sk-test")
    assert m["api_key"] == "sk-test"


def test_build_memory_config():
    assert build_memory_config("meridian", False) == {"enabled": False}
    openai_mem = build_memory_config("openai", True, api_key="sk-test")
    assert openai_mem["embedding_provider"] == "openai"
    assert openai_mem["embedding_api_key"] == "sk-test"
    assert build_memory_config("meridian", True)["embedding_provider"] == "ollama"


def test_config_write_roundtrip(tmp_path):
    path = tmp_path / "config.yaml"
    data = {"model": {"provider": "meridian", "model_id": "claude-opus-4-8"}}
    written = AethonConfig.write(data, str(path))
    assert written == path and path.exists()

    cfg = AethonConfig.load(str(path))
    assert cfg.model.provider == "meridian"
    assert cfg.model.model_id == "claude-opus-4-8"


def test_meridian_status_shape():
    up, msg = meridian_status()
    assert isinstance(up, bool)
    assert isinstance(msg, str)


def test_cli_version():
    result = CliRunner().invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "aethon" in result.output


def test_cli_doctor_no_config(tmp_path):
    result = CliRunner().invoke(main, ["doctor", "-c", str(tmp_path / "missing.yaml")])
    assert result.exit_code == 0
    assert "aethon init" in result.output


def test_cli_init_writes_meridian_config(tmp_path, monkeypatch):
    import aethon.setup_wizard as wiz

    # Make the wizard hermetic (no network for provider/meridian checks).
    monkeypatch.setattr(wiz, "meridian_status", lambda: (True, "running (test)"))
    monkeypatch.setattr(wiz, "check_model_availability", lambda mc: (True, "OK (test)"))

    cfg = tmp_path / "config.yaml"
    # provider #1 (meridian), accept default model, memory: no
    result = CliRunner().invoke(main, ["init", "-c", str(cfg)], input="1\n\nn\n")
    assert result.exit_code == 0, result.output
    assert cfg.exists()

    loaded = AethonConfig.load(str(cfg))
    assert loaded.model.provider == "meridian"
    assert loaded.model.model_id == "claude-opus-4-8"
    assert loaded.memory.enabled is False
