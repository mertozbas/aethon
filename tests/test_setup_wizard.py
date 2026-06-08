"""Tests for the first-run setup wizard and the init/doctor/version CLI."""

from click.testing import CliRunner

from aethon.__main__ import main
from aethon.config import AethonConfig
from aethon.setup_wizard import (
    PROVIDERS,
    build_memory_config,
    build_model_config,
)


def test_providers_include_openai_default():
    # openai is the first/default provider; it needs an API key.
    assert list(PROVIDERS)[0] == "openai"
    _desc, default_model, needs_key, env = PROVIDERS["openai"]
    assert default_model == "gpt-4o"
    assert needs_key is True
    assert env == "OPENAI_API_KEY"
    assert "meridian" not in PROVIDERS


def test_build_model_config_anthropic():
    assert build_model_config("anthropic", model_id="claude-opus-4-8") == {
        "provider": "anthropic",
        "model_id": "claude-opus-4-8",
    }


def test_build_model_config_ollama_host():
    m = build_model_config("ollama", model_id="llama3.1", host="http://h:11434")
    assert m["provider"] == "ollama"
    assert m["host"] == "http://h:11434"


def test_build_model_config_openai_base_url():
    # An OpenAI-compatible endpoint (e.g. a local proxy) is stored as host.
    m = build_model_config("openai", model_id="gpt-4o", api_key="sk-test", host="http://localhost:8080/v1")
    assert m["provider"] == "openai"
    assert m["host"] == "http://localhost:8080/v1"
    assert m["api_key"] == "sk-test"


def test_build_model_config_api_key():
    m = build_model_config("openai", model_id="gpt-4o", api_key="sk-test")
    assert m["api_key"] == "sk-test"


def test_build_memory_config():
    assert build_memory_config("anthropic", False) == {"enabled": False}
    openai_mem = build_memory_config("openai", True, api_key="sk-test")
    assert openai_mem["embedding_provider"] == "openai"
    assert openai_mem["embedding_api_key"] == "sk-test"
    assert build_memory_config("anthropic", True)["embedding_provider"] == "ollama"


def test_config_write_roundtrip(tmp_path):
    path = tmp_path / "config.yaml"
    data = {"model": {"provider": "openai", "model_id": "gpt-4o"}}
    written = AethonConfig.write(data, str(path))
    assert written == path and path.exists()

    cfg = AethonConfig.load(str(path))
    assert cfg.model.provider == "openai"
    assert cfg.model.model_id == "gpt-4o"


def test_cli_version():
    result = CliRunner().invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "aethon" in result.output


def test_cli_doctor_no_config(tmp_path):
    result = CliRunner().invoke(main, ["doctor", "-c", str(tmp_path / "missing.yaml")])
    assert result.exit_code == 0
    assert "aethon init" in result.output


def test_cli_init_writes_openai_config(tmp_path, monkeypatch):
    import aethon.setup_wizard as wiz

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)  # force the key prompt
    monkeypatch.setattr(wiz, "check_model_availability", lambda mc: (True, "OK (test)"))

    cfg = tmp_path / "config.yaml"
    # provider 1 (openai), default model, blank base URL, api key, memory no,
    # then the three channel prompts (Telegram/Discord/Slack): no/no/no
    result = CliRunner().invoke(
        main, ["init", "-c", str(cfg)], input="1\n\n\nsk-test\nn\nn\nn\nn\n"
    )
    assert result.exit_code == 0, result.output
    assert cfg.exists()

    loaded = AethonConfig.load(str(cfg))
    assert loaded.model.provider == "openai"
    assert loaded.model.model_id == "gpt-4o"
    assert loaded.memory.enabled is False


def test_cli_init_enables_telegram_channel(tmp_path, monkeypatch):
    import aethon.setup_wizard as wiz

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(wiz, "check_model_availability", lambda mc: (True, "OK (test)"))

    cfg = tmp_path / "config.yaml"
    # openai, default model, blank base URL, api key, memory no,
    # Telegram YES + token + chat id + lock-down yes, Discord no, Slack no.
    # CliRunner has no TTY, so chat-id auto-detect is skipped (manual prompt only).
    result = CliRunner().invoke(
        main,
        ["init", "-c", str(cfg)],
        input="1\n\n\nsk-test\nn\ny\nMYTOKEN\n123456\ny\nn\nn\n",
    )
    assert result.exit_code == 0, result.output

    loaded = AethonConfig.load(str(cfg))
    assert loaded.channels.telegram.enabled is True
    assert loaded.channels.telegram.token == "MYTOKEN"
    assert loaded.channels.telegram.chat_id == "123456"
    assert loaded.security.allowed_senders.get("telegram") == ["123456"]
    assert loaded.channels.discord.enabled is False
