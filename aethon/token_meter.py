"""Token measurement + spend ceiling (Phase 9B / E0).

You can't optimize what you can't see: this tracks per-turn / per-session /
per-day token usage and converts it to a USD estimate via a config-overridable
pricing table, and enforces an optional daily ceiling. Measurement is the
foundation every later token-economy item is judged against.
"""

import logging
from datetime import date

logger = logging.getLogger("aethon.budget")

# Built-in pricing — USD per 1M tokens, AS OF 2026-06. Approximate and
# config-overridable (budget.pricing). Matched by substring of the model id.
PRICING_AS_OF = "2026-06"
DEFAULT_PRICING: dict[str, dict[str, float]] = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "claude-opus": {"input": 15.0, "output": 75.0},
    "claude-sonnet": {"input": 3.0, "output": 15.0},
    "claude-haiku": {"input": 0.80, "output": 4.0},
}
# Fallback when no table entry matches — keeps a non-zero, honest estimate.
_FALLBACK = {"input": 1.0, "output": 3.0}


class TokenMeter:
    """Accumulates token usage and cost; answers budget questions."""

    def __init__(self, budget_config=None):
        self.budget = budget_config
        self._pricing = dict(DEFAULT_PRICING)
        if budget_config is not None:
            self._pricing.update(getattr(budget_config, "pricing", {}) or {})
        # day (ISO) -> {"input", "output", "cost"}
        self._daily: dict[str, dict] = {}
        self._session: dict[str, dict] = {}
        self._turns = 0

    def _rate(self, model: str) -> dict:
        m = (model or "").lower()
        # Longest matching key wins (so "gpt-4o-mini" beats "gpt-4o").
        best = None
        for key, rate in self._pricing.items():
            if key.lower() in m and (best is None or len(key) > len(best[0])):
                best = (key, rate)
        return best[1] if best else _FALLBACK

    def cost(self, input_tokens: int, output_tokens: int, model: str) -> float:
        rate = self._rate(model)
        return input_tokens / 1e6 * rate["input"] + output_tokens / 1e6 * rate["output"]

    def record(self, input_tokens: int, output_tokens: int, model: str,
               session_id: str = "") -> float:
        """Record one turn's usage; returns the turn's USD cost."""
        if input_tokens <= 0 and output_tokens <= 0:
            return 0.0
        c = self.cost(input_tokens, output_tokens, model)
        self._turns += 1
        day = date.today().isoformat()
        d = self._daily.setdefault(day, {"input": 0, "output": 0, "cost": 0.0})
        d["input"] += input_tokens
        d["output"] += output_tokens
        d["cost"] += c
        if session_id:
            s = self._session.setdefault(session_id, {"input": 0, "output": 0, "cost": 0.0})
            s["input"] += input_tokens
            s["output"] += output_tokens
            s["cost"] += c
        return c

    def today(self) -> dict:
        return self._daily.get(date.today().isoformat(), {"input": 0, "output": 0, "cost": 0.0})

    def daily_cost(self) -> float:
        return self.today()["cost"]

    @property
    def _ceiling(self) -> float:
        return float(getattr(self.budget, "daily_usd", 0.0) or 0.0)

    def over_budget(self) -> bool:
        return self._ceiling > 0 and self.daily_cost() >= self._ceiling

    def near_budget(self) -> bool:
        if self._ceiling <= 0:
            return False
        ratio = float(getattr(self.budget, "warn_ratio", 0.8) or 0.8)
        return self.daily_cost() >= self._ceiling * ratio

    def summary(self) -> dict:
        t = self.today()
        return {
            "turns": self._turns,
            "today_input": t["input"],
            "today_output": t["output"],
            "today_cost_usd": round(t["cost"], 4),
            "daily_ceiling_usd": self._ceiling,
            "pricing_as_of": PRICING_AS_OF,
        }
