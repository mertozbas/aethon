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


def test_cli_doctor_flags_world_readable_config(tmp_path):
    """S8: doctor reports a group/world-readable config.

    (doctor runs the provider check but never exits early on it, so no
    monkeypatch is needed — the ollama check just prints a red line.)
    """
    import os

    cfg = tmp_path / "config.yaml"
    AethonConfig.write({"model": {"provider": "ollama"}}, str(cfg))
    os.chmod(cfg, 0o644)  # make it world-readable (the bad state)

    result = CliRunner().invoke(main, ["doctor", "-c", str(cfg)])
    assert result.exit_code == 0, result.output
    assert "group/world-readable" in result.output


def test_cli_doctor_flags_literal_api_key(tmp_path):
    """S8: doctor nudges away from a literally-stored API key."""
    cfg = tmp_path / "config.yaml"
    AethonConfig.write(
        {"model": {"provider": "ollama", "api_key": "sk-literal-123"}}, str(cfg)
    )
    result = CliRunner().invoke(main, ["doctor", "-c", str(cfg)])
    assert "stored literally" in result.output


def test_cli_doctor_accepts_env_ref_key(tmp_path, monkeypatch):
    """An ${ENV_VAR} reference is not flagged as a literal key."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    cfg = tmp_path / "config.yaml"
    AethonConfig.write(
        {"model": {"provider": "ollama", "api_key": "${OPENAI_API_KEY}"}}, str(cfg)
    )
    result = CliRunner().invoke(main, ["doctor", "-c", str(cfg)])
    assert "stored literally" not in result.output


def test_cli_doctor_reports_unknown_keys(tmp_path):
    """H8: doctor flags config keys the schema doesn't recognize."""
    cfg = tmp_path / "config.yaml"
    cfg.write_text("model:\n  provider: ollama\nbananas: 3\n")
    result = CliRunner().invoke(main, ["doctor", "-c", str(cfg)])
    assert "Unknown config keys" in result.output
    assert "bananas" in result.output


def test_wizard_backs_up_existing_config(tmp_path, monkeypatch):
    """H8: re-running init backs up the previous config before overwriting."""
    import aethon.setup_wizard as wiz

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(wiz, "check_model_availability", lambda mc: (True, "OK (test)"))

    cfg = tmp_path / "config.yaml"
    cfg.write_text("model:\n  provider: openai\n  api_key: OLD-KEY\n")

    # init with --force to skip the overwrite confirm; provider 1, defaults, no key,
    # memory no, channels no x4, webhook no.
    result = CliRunner().invoke(
        main, ["init", "-c", str(cfg), "--force"],
        input="1\n\n\nsk-new\nn\nn\nn\nn\nn\nn\n",
    )
    assert result.exit_code == 0, result.output
    backups = list(tmp_path.glob("config.yaml.bak-*"))
    assert len(backups) == 1
    assert "OLD-KEY" in backups[0].read_text()  # the previous config preserved


def test_cli_doctor_survives_malformed_yaml(tmp_path):
    """S8 review: a malformed config must not crash doctor (YAMLError caught)."""
    cfg = tmp_path / "config.yaml"
    # Valid enough for AethonConfig.load (which tolerates it), but the raw
    # re-read for the literal-key check must not raise. Write broken YAML and
    # confirm doctor still exits 0.
    cfg.write_text("model: [unclosed\n")
    result = CliRunner().invoke(main, ["doctor", "-c", str(cfg)])
    assert result.exit_code == 0, result.output


def test_cli_init_writes_openai_config(tmp_path, monkeypatch):
    import aethon.setup_wizard as wiz

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)  # force the key prompt
    monkeypatch.setattr(wiz, "check_model_availability", lambda mc: (True, "OK (test)"))

    cfg = tmp_path / "config.yaml"
    # provider 1 (openai), default model, blank base URL, api key, memory no,
    # the four channel prompts (Telegram/Discord/Slack/WhatsApp): no x4,
    # webhook secret: no
    result = CliRunner().invoke(
        main, ["init", "-c", str(cfg)], input="1\n\n\nsk-test\nn\nn\nn\nn\nn\nn\n"
    )
    assert result.exit_code == 0, result.output
    assert cfg.exists()

    loaded = AethonConfig.load(str(cfg))
    assert loaded.model.provider == "openai"
    assert loaded.model.model_id == "gpt-4o"
    assert loaded.memory.enabled is False
    # S8: a prompted (literal) key prints the env-reference nudge.
    assert "OPENAI_API_KEY" in result.output and "environment" in result.output


def test_cli_start_refuses_nonloopback_bind_without_token(tmp_path):
    """`aethon start` fails closed on an exposed bind without a token (S4)."""
    cfg = tmp_path / "config.yaml"
    AethonConfig.write(
        {"channels": {"webchat": {"enabled": True, "host": "0.0.0.0"}}}, str(cfg)
    )
    result = CliRunner().invoke(main, ["start", "-c", str(cfg)])
    assert result.exit_code == 0, result.output
    assert "Refusing to start" in result.output
    assert "dashboard.auth_token" in result.output


def test_cli_start_insecure_bind_flag_skips_refusal(tmp_path, monkeypatch):
    """--insecure-bind continues past the bind gate (then stops at the provider
    check — a clean, deterministic exit that proves the gate was skipped)."""
    import aethon.agent.model_factory as mf

    monkeypatch.setattr(
        mf, "check_model_availability", lambda mc: (False, "unavailable (test)")
    )
    cfg = tmp_path / "config.yaml"
    AethonConfig.write(
        {
            "channels": {"webchat": {"enabled": True, "host": "0.0.0.0"}},
            "memory": {"enabled": False},
            # keep workspace/log side effects inside tmp_path
            "paths": {
                "workspace": str(tmp_path / "ws"),
                "sessions": str(tmp_path / "sessions"),
                "logs": str(tmp_path / "logs"),
            },
        },
        str(cfg),
    )
    result = CliRunner().invoke(main, ["start", "-c", str(cfg), "--insecure-bind"])
    assert result.exit_code == 0, result.output
    assert "Refusing to start" not in result.output
    assert "Provider not ready" in result.output


def test_cli_init_enables_telegram_channel(tmp_path, monkeypatch):
    import aethon.setup_wizard as wiz

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(wiz, "check_model_availability", lambda mc: (True, "OK (test)"))

    cfg = tmp_path / "config.yaml"
    # openai, default model, blank base URL, api key, memory no,
    # Telegram YES + token + chat id + lock-down yes, Discord no, Slack no,
    # WhatsApp no, webhook secret no.
    # CliRunner has no TTY, so chat-id auto-detect is skipped (manual prompt only).
    result = CliRunner().invoke(
        main,
        ["init", "-c", str(cfg)],
        input="1\n\n\nsk-test\nn\ny\nMYTOKEN\n123456\ny\nn\nn\nn\nn\n",
    )
    assert result.exit_code == 0, result.output

    loaded = AethonConfig.load(str(cfg))
    assert loaded.channels.telegram.enabled is True
    assert loaded.channels.telegram.token == "MYTOKEN"
    assert loaded.channels.telegram.chat_id == "123456"
    assert loaded.security.allowed_senders.get("telegram") == ["123456"]
    assert loaded.channels.discord.enabled is False


def test_cli_init_enables_whatsapp_with_allowlist(tmp_path, monkeypatch):
    """WhatsApp wizard parity (S5): enable + default chat + allowlist confirm."""
    import aethon.setup_wizard as wiz

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(wiz, "check_model_availability", lambda mc: (True, "OK (test)"))

    cfg = tmp_path / "config.yaml"
    # openai, default model, blank base URL, api key, memory no,
    # Telegram/Discord/Slack no, WhatsApp YES + number + restrict yes,
    # webhook secret no.
    result = CliRunner().invoke(
        main,
        ["init", "-c", str(cfg)],
        input="1\n\n\nsk-test\nn\nn\nn\nn\ny\n905551112233\ny\nn\n",
    )
    assert result.exit_code == 0, result.output

    loaded = AethonConfig.load(str(cfg))
    assert loaded.channels.whatsapp.enabled is True
    assert loaded.channels.whatsapp.chat == "905551112233"
    assert loaded.security.allowed_senders.get("whatsapp") == ["905551112233"]


def test_cli_init_writes_webhook_secret(tmp_path, monkeypatch):
    """Accepting the webhook prompt writes a generated HMAC secret (S3)."""
    import aethon.setup_wizard as wiz

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(wiz, "check_model_availability", lambda mc: (True, "OK (test)"))

    cfg = tmp_path / "config.yaml"
    # openai, default model, blank base URL, api key, memory no,
    # Telegram/Discord/Slack/WhatsApp no, webhook secret YES (generated).
    result = CliRunner().invoke(
        main, ["init", "-c", str(cfg)], input="1\n\n\nsk-test\nn\nn\nn\nn\nn\ny\n"
    )
    assert result.exit_code == 0, result.output

    loaded = AethonConfig.load(str(cfg))
    secret = loaded.webhook.secret
    assert len(secret) == 32  # secrets.token_hex(16)
    int(secret, 16)  # hex-parsable
    assert secret in result.output  # shown once so the user can copy it
