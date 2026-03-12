"""Tests for model factory."""

import pytest

from aethon.config import ModelConfig
from aethon.agent.model_factory import create_model, check_model_availability


def test_create_model_ollama():
    """Ollama provider creates OllamaModel."""
    config = ModelConfig(provider="ollama", model_id="qwen3-coder-next")
    model = create_model(config)
    from strands.models.ollama import OllamaModel
    assert isinstance(model, OllamaModel)


def test_create_model_unknown_provider():
    """Unknown provider raises ValueError."""
    config = ModelConfig(provider="nonexistent")
    with pytest.raises(ValueError, match="Bilinmeyen model provider"):
        create_model(config)


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
        assert "erisilemez" in msg or "bulunamadi" in msg


def test_check_model_availability_openai_no_key():
    """OpenAI without API key returns False."""
    config = ModelConfig(provider="openai", model_id="gpt-4o", api_key="")
    available, msg = check_model_availability(config)
    assert available is False
    assert "API key gerekli" in msg


def test_check_model_availability_anthropic_no_key():
    """Anthropic without API key returns False."""
    config = ModelConfig(provider="anthropic", model_id="claude-sonnet-4-20250514", api_key="")
    available, msg = check_model_availability(config)
    assert available is False
    assert "API key gerekli" in msg


def test_check_model_availability_anthropic_with_key():
    """Anthropic with API key returns True."""
    config = ModelConfig(
        provider="anthropic",
        model_id="claude-sonnet-4-20250514",
        api_key="sk-ant-test-key",
    )
    available, msg = check_model_availability(config)
    assert available is True
    assert "API key mevcut" in msg


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
    assert "Bilinmeyen provider" in msg
