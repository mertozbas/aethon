"""Multi-provider model factory.

Creates the appropriate Strands Model based on config provider setting.
Supported: meridian (Claude on your Claude Max quota — default), ollama, openai,
anthropic, bedrock, gemini, litellm, mistral, fake (offline no-op for tests/CI).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from strands.models import Model

if TYPE_CHECKING:
    from aethon.config import ModelConfig

# `host` defaults to the Ollama URL. For Meridian we treat that default (and an
# empty value) as "unset" so the proxy falls back to MERIDIAN_BASE_URL or its
# own 127.0.0.1:3456 default.
_OLLAMA_DEFAULT_HOST = "http://localhost:11434"


def _meridian_base_url(config: ModelConfig) -> str | None:
    """Resolve the Meridian base URL from config.host, or None to use defaults."""
    host = config.host
    if host and host != _OLLAMA_DEFAULT_HOST:
        return host
    return None


def _anthropic_params(config: ModelConfig) -> dict:
    """Build Anthropic ``params``. Opus 4.7+ (and the Meridian ``opus`` / ``opus[1m]``
    aliases that resolve to the latest Opus) reject ``temperature``/``top_p``/``top_k``
    with a 400, so omit sampling params for those models."""
    model = (config.model_id or "").lower()
    rejects_sampling = model in ("opus", "opus[1m]") or "opus-4-7" in model or "opus-4-8" in model
    if rejects_sampling:
        return {}
    return {"temperature": config.temperature}


def create_model(config: ModelConfig) -> Model:
    """Create model instance based on provider config.

    Args:
        config: ModelConfig with provider, model_id, and provider-specific params.

    Returns:
        Strands Model instance ready for use with Agent.

    Raises:
        ValueError: If provider is not supported.
    """
    provider = config.provider.lower()

    if provider == "meridian":
        # Claude on your Claude Max subscription quota, via the local Meridian proxy.
        # Native Anthropic transport, so prompt caching, structured output and
        # streaming are preserved. See https://github.com/mertozbas/strands-meridian
        from strands_meridian import MeridianModel

        return MeridianModel(
            model_id=config.model_id,
            base_url=_meridian_base_url(config),
            max_tokens=config.max_tokens,
            params=_anthropic_params(config),
        )

    elif provider in ("fake", "echo"):
        # No-network, no-dependency model — used by tests/CI and as a safe fallback
        # when no real provider is configured. Streams a fixed canned reply.
        from aethon.agent.fake_model import EchoModel

        kwargs = {}
        if isinstance(config.extra, dict) and config.extra.get("reply"):
            kwargs["reply"] = config.extra["reply"]
        return EchoModel(model_id=config.model_id, **kwargs)

    elif provider == "ollama":
        from strands.models.ollama import OllamaModel

        return OllamaModel(
            host=config.host,
            model_id=config.model_id,
            temperature=config.temperature,
            top_p=config.top_p,
            options={"top_k": config.top_k, **config.extra},
        )

    elif provider == "openai":
        from strands.models.openai import OpenAIModel

        client_args = {}
        if config.api_key:
            client_args["api_key"] = config.api_key
        if config.host and config.host != "http://localhost:11434":
            client_args["base_url"] = config.host
        return OpenAIModel(
            client_args=client_args or None,
            model_id=config.model_id,
            params={"temperature": config.temperature, "max_completion_tokens": config.max_tokens},
        )

    elif provider == "anthropic":
        from strands.models.anthropic import AnthropicModel

        client_args = {}
        if config.api_key:
            client_args["api_key"] = config.api_key
        return AnthropicModel(
            client_args=client_args or None,
            model_id=config.model_id,
            max_tokens=config.max_tokens,
            params=_anthropic_params(config),
        )

    elif provider == "bedrock":
        from strands.models import BedrockModel

        return BedrockModel(
            model_id=config.model_id,
            region_name=config.region,  # BedrockModel uses region_name, not region
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )

    elif provider == "gemini":
        from strands.models.gemini import GeminiModel

        # GeminiConfig only has model_id + params; generation settings (incl. the
        # token cap, which Gemini calls max_output_tokens) go inside params.
        return GeminiModel(
            model_id=config.model_id,
            client_args={"api_key": config.api_key} if config.api_key else None,
            params={
                "max_output_tokens": config.max_tokens,
                "temperature": config.temperature,
            },
        )

    elif provider == "litellm":
        from strands.models.litellm import LiteLLMModel

        return LiteLLMModel(
            model_id=config.model_id,
        )

    elif provider == "mistral":
        from strands.models.mistral import MistralModel

        # MistralModel takes api_key as a dedicated arg (not via client_args);
        # max_tokens is a MistralConfig field.
        return MistralModel(
            api_key=config.api_key or None,
            model_id=config.model_id,
            max_tokens=config.max_tokens,
        )

    else:
        raise ValueError(
            f"Unknown model provider: '{provider}'. "
            f"Supported: meridian, ollama, openai, anthropic, bedrock, gemini, litellm, mistral, fake"
        )


def check_model_availability(config: ModelConfig) -> tuple[bool, str]:
    """Check if the configured model is accessible.

    Returns:
        (available, message) tuple.
    """
    provider = config.provider.lower()

    if provider == "meridian":
        from strands_meridian import MeridianError, health_check

        try:
            info = health_check(_meridian_base_url(config))
        except MeridianError as e:
            return False, (
                f"Meridian not reachable: {e}\n"
                f"  Start: meridian (first: claude login)"
            )
        auth = info.get("auth", {})
        if auth.get("loggedIn"):
            sub = auth.get("subscriptionType", "?")
            email = auth.get("email", "?")
            return True, f"Meridian OK: {config.model_id} ({sub} quota, {email})"
        return False, "Meridian is running but you are not logged in. Run: claude login"

    elif provider in ("fake", "echo"):
        return True, f"Fake/echo provider OK: {config.model_id} (offline, no backend)"

    elif provider == "ollama":
        import requests

        try:
            r = requests.get(f"{config.host}/api/tags", timeout=5)
            models = [m["name"] for m in r.json().get("models", [])]
            if any(config.model_id in m for m in models):
                return True, f"Ollama OK: {config.model_id}"
            return False, (
                f"Model '{config.model_id}' not found in Ollama.\n"
                f"  Available models: {', '.join(models)}\n"
                f"  Download: ollama pull {config.model_id}"
            )
        except Exception:
            return False, (
                f"Ollama ({config.host}) not reachable.\n"
                f"  Start: ollama serve"
            )

    elif provider in ("openai", "anthropic", "gemini", "mistral"):
        if not config.api_key:
            return False, (
                f"API key required for {provider}.\n"
                f"  config.yaml: model.api_key: 'sk-...'\n"
                f"  or: AETHON_{provider.upper()}_API_KEY environment variable"
            )
        return True, f"{provider} OK: {config.model_id} (API key available)"

    elif provider == "bedrock":
        try:
            import boto3

            boto3.client("bedrock-runtime", region_name=config.region)
            return True, f"Bedrock OK: {config.model_id} ({config.region})"
        except Exception as e:
            return False, f"AWS Bedrock access error: {e}"

    elif provider == "litellm":
        return True, f"LiteLLM OK: {config.model_id}"

    return False, f"Unknown provider: {provider}"
