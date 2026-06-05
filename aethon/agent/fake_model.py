"""A no-network, no-dependency Strands model.

`EchoModel` returns a fixed canned reply without calling any backend. It exists so
that tests, CI, offline smoke checks, and the first-run experience work without a
configured provider or network access. Select it via provider ``"fake"`` (alias
``"echo"``) in the model factory, or construct it directly.
"""

from __future__ import annotations

from typing import Any, AsyncGenerator, Optional, Type, TypeVar

from strands.models.model import Model

T = TypeVar("T")

DEFAULT_REPLY = (
    "This is aethon's built-in fake model — no AI backend is configured. "
    "Run `aethon init` to connect Meridian (Claude) or another provider."
)


class EchoModel(Model):
    """Minimal Strands ``Model`` that streams a fixed reply. No network, no deps."""

    def __init__(self, *, model_id: str = "fake", reply: str = DEFAULT_REPLY, **_: Any) -> None:
        self.config: dict[str, Any] = {"model_id": model_id, "reply": reply}

    def update_config(self, **model_config: Any) -> None:
        self.config.update(model_config)

    def get_config(self) -> dict[str, Any]:
        return dict(self.config)

    async def stream(
        self,
        messages: Any,
        tool_specs: Optional[Any] = None,
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[dict, None]:
        text = self.config.get("reply", DEFAULT_REPLY)
        yield {"messageStart": {"role": "assistant"}}
        yield {"contentBlockStart": {"start": {}}}
        yield {"contentBlockDelta": {"delta": {"text": text}}}
        yield {"contentBlockStop": {}}
        yield {"messageStop": {"stopReason": "end_turn"}}
        yield {
            "metadata": {
                "usage": {"inputTokens": 0, "outputTokens": 0, "totalTokens": 0},
                "metrics": {"latencyMs": 0},
            }
        }

    async def structured_output(
        self,
        output_model: Type[T],
        prompt: Any,
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[dict, None]:
        # Best effort: construct a default instance. The fake model has no real
        # content, so this only works for models whose fields all have defaults.
        try:
            yield {"output": output_model()}
        except Exception as exc:  # noqa: BLE001 — surface a clear, actionable error
            raise NotImplementedError(
                "EchoModel cannot synthesize structured output; configure a real provider."
            ) from exc
