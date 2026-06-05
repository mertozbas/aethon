"""Tests for model factory."""

import pytest

from aethon.config import ModelConfig
from aethon.agent.model_factory import create_model, check_model_availability


def test_create_model_meridian():
    """Meridian provider creates a MeridianModel pointed at the local proxy."""
    from strands_meridian import DEFAULT_BASE_URL, MeridianModel

    config = ModelConfig(provider="meridian", model_id="claude-sonnet-4-6")
    model = create_model(config)
    assert isinstance(model, MeridianModel)
    # host left at the Ollama default → Meridian uses its own default base_url
    assert model.base_url == DEFAULT_BASE_URL
    assert model.get_config()["model_id"] == "claude-sonnet-4-6"


def test_create_model_meridian_explicit_host():
    """An explicit (non-Ollama) host is used as the Meridian base_url."""
    from strands_meridian import MeridianModel

    config = ModelConfig(provider="meridian", model_id="opus[1m]", host="http://192.168.1.5:3456")
    model = create_model(config)
    assert isinstance(model, MeridianModel)
    assert model.base_url == "http://192.168.1.5:3456"


def test_check_model_availability_meridian():
    """Meridian availability returns (bool, str); the proxy may be up or down."""
    config = ModelConfig(provider="meridian")
    available, msg = check_model_availability(config)
    assert isinstance(available, bool)
    assert isinstance(msg, str)
    if available:
        assert "Meridian OK" in msg
    else:
        assert "not reachable" in msg or "not logged in" in msg


def test_create_model_ollama():
    """Ollama provider creates OllamaModel."""
    pytest.importorskip("ollama")  # OllamaModel needs the optional `ollama` package
    config = ModelConfig(provider="ollama", model_id="qwen3-coder-next")
    model = create_model(config)
    from strands.models.ollama import OllamaModel
    assert isinstance(model, OllamaModel)


def test_create_model_unknown_provider():
    """Unknown provider raises ValueError."""
    config = ModelConfig(provider="nonexistent")
    with pytest.raises(ValueError, match="Unknown model provider"):
        create_model(config)


def test_create_model_bedrock_wires_region_name():
    """Bedrock passes the AWS region via region_name (not the invalid 'region' kwarg)."""
    pytest.importorskip("boto3")
    import warnings

    from strands.models import BedrockModel

    config = ModelConfig(provider="bedrock", model_id="anthropic.claude-3-5-sonnet-20240620-v1:0", region="eu-west-1")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        model = create_model(config)
    assert isinstance(model, BedrockModel)
    # The region actually reaches the boto3 client (was silently dropped when passed as `region`).
    assert model.client.meta.region_name == "eu-west-1"
    invalid_region = [w for w in caught if "region" in str(w.message).lower() and "invalid" in str(w.message).lower()]
    assert not invalid_region, f"unexpected invalid-region warning: {[str(w.message) for w in invalid_region]}"


def test_create_model_gemini_max_tokens_in_params():
    """Gemini puts the token cap in params as max_output_tokens (GeminiConfig has no max_tokens)."""
    pytest.importorskip("google.genai")
    config = ModelConfig(provider="gemini", model_id="gemini-2.0-flash", api_key="k", max_tokens=1234)
    model = create_model(config)
    params = model.get_config().get("params", {})
    assert params.get("max_output_tokens") == 1234


def test_check_model_availability_ollama():
    """Check Ollama availability with real connection."""
    config = ModelConfig(provider="ollama")
    available, msg = check_model_availability(config)
    # Either Ollama is running or it's not — both are valid outcomes
    assert isinstance(available, bool)
    assert isinstance(msg, str)
    if available:
        assert "Ollama OK" in msg
    else:
        assert "not reachable" in msg or "not found" in msg


def test_check_model_availability_openai_no_key():
    """OpenAI without API key returns False."""
    config = ModelConfig(provider="openai", model_id="gpt-4o", api_key="")
    available, msg = check_model_availability(config)
    assert available is False
    assert "API key required" in msg


def test_check_model_availability_anthropic_no_key():
    """Anthropic without API key returns False."""
    config = ModelConfig(provider="anthropic", model_id="claude-sonnet-4-20250514", api_key="")
    available, msg = check_model_availability(config)
    assert available is False
    assert "API key required" in msg


def test_check_model_availability_anthropic_with_key():
    """Anthropic with API key returns True."""
    config = ModelConfig(
        provider="anthropic",
        model_id="claude-sonnet-4-20250514",
        api_key="sk-ant-test-key",
    )
    available, msg = check_model_availability(config)
    assert available is True
    assert "API key available" in msg


def test_check_model_availability_litellm():
    """LiteLLM always returns True."""
    config = ModelConfig(provider="litellm", model_id="gpt-4o")
    available, msg = check_model_availability(config)
    assert available is True
    assert "LiteLLM OK" in msg


def test_check_model_availability_unknown():
    """Unknown provider returns False."""
    config = ModelConfig(provider="nonexistent")
    available, msg = check_model_availability(config)
    assert available is False
    assert "Unknown provider" in msg
