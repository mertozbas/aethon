"""Tests for the token meter + budget ceiling (Phase 9B / E0)."""

import pytest

from aethon.config import BudgetConfig
from aethon.token_meter import TokenMeter


def test_cost_uses_pricing_table():
    m = TokenMeter(BudgetConfig())
    # gpt-4o: input 2.5/1M, output 10/1M.
    cost = m.cost(1_000_000, 1_000_000, "gpt-4o")
    assert cost == pytest.approx(12.5)


def test_longest_model_match_wins():
    m = TokenMeter(BudgetConfig())
    # 'gpt-4o-mini' must beat the 'gpt-4o' substring.
    assert m.cost(1_000_000, 0, "gpt-4o-mini") == pytest.approx(0.15)


def test_pricing_override():
    m = TokenMeter(BudgetConfig(pricing={"mymodel": {"input": 1.0, "output": 2.0}}))
    assert m.cost(1_000_000, 1_000_000, "mymodel-v2") == pytest.approx(3.0)


def test_unknown_model_uses_fallback():
    m = TokenMeter(BudgetConfig())
    assert m.cost(1_000_000, 0, "exotic-llm") == pytest.approx(1.0)  # fallback input 1.0


def test_record_accumulates_daily_and_session():
    m = TokenMeter(BudgetConfig())
    m.record(1_000_000, 0, "gpt-4o", session_id="s1")
    m.record(0, 1_000_000, "gpt-4o", session_id="s1")
    today = m.today()
    assert today["input"] == 1_000_000 and today["output"] == 1_000_000
    assert today["cost"] == pytest.approx(12.5)
    s = m.summary()
    assert s["turns"] == 2 and s["today_cost_usd"] == pytest.approx(12.5)


def test_zero_usage_not_recorded():
    m = TokenMeter(BudgetConfig())
    assert m.record(0, 0, "gpt-4o") == 0.0
    assert m.summary()["turns"] == 0


def test_budget_unlimited_by_default():
    m = TokenMeter(BudgetConfig())  # daily_usd=0 → unlimited
    m.record(10_000_000, 10_000_000, "claude-opus")
    assert m.over_budget() is False
    assert m.near_budget() is False


def test_over_and_near_budget():
    m = TokenMeter(BudgetConfig(daily_usd=10.0, warn_ratio=0.8))
    m.record(1_000_000, 0, "gpt-4o")  # $2.50 — under 80% of $10
    assert not m.near_budget() and not m.over_budget()
    m.record(2_000_000, 0, "gpt-4o")  # +$5.00 → $7.50 ≥ $8? no, 7.5 < 8
    assert not m.near_budget()
    m.record(1_000_000, 0, "gpt-4o")  # +$2.50 → $10.00 ≥ ceiling
    assert m.over_budget() and m.near_budget()


# --- runtime budget gate ---------------------------------------------------


def _runtime(tmp_path, **budget_kw):
    from aethon.agent.runtime import AethonRuntime
    from aethon.config import (
        AethonConfig, ModelConfig, PathsConfig, MemoryConfig, MCPConfig,
    )

    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "SOUL.md").write_text("x")
    return AethonRuntime(AethonConfig(
        model=ModelConfig(provider="fake", model_id="gpt-4o"),
        memory=MemoryConfig(enabled=False),
        mcp=MCPConfig(enabled=False),
        budget=BudgetConfig(**budget_kw),
        paths=PathsConfig(
            workspace=str(ws), sessions=str(tmp_path / "s"), logs=str(tmp_path / "l"),
            memory_db=str(tmp_path / "m.sqlite"), credentials=str(tmp_path / "c"),
        ),
    ))


@pytest.mark.asyncio
async def test_runtime_blocks_turn_over_budget(tmp_path, monkeypatch):
    from aethon.channels.base import InboundMessage

    rt = _runtime(tmp_path, daily_usd=1.0)
    # Push spend over the ceiling.
    rt.token_meter.record(1_000_000, 0, "gpt-4o")  # $2.50 ≥ $1
    assert rt.token_meter.over_budget()

    ran = {"v": False}
    monkeypatch.setattr(rt, "_process_sync", lambda m, s: ran.__setitem__("v", True) or "ok")
    out = await rt.process(
        InboundMessage(channel="cli", sender_id="u", sender_name="u", text="hello"),
        "cli:u",
    )
    assert ran["v"] is False                 # the turn was NOT run
    assert "budget exceeded" in out.lower()  # user told why


@pytest.mark.asyncio
async def test_runtime_blocks_turn_turkish(tmp_path, monkeypatch):
    from aethon.channels.base import InboundMessage

    rt = _runtime(tmp_path, daily_usd=1.0)
    rt.token_meter.record(1_000_000, 0, "gpt-4o")
    monkeypatch.setattr(rt, "_process_sync", lambda m, s: "ok")
    out = await rt.process(
        InboundMessage(channel="cli", sender_id="u", sender_name="u", text="merhaba günaydın"),
        "cli:u",
    )
    assert "bütçesi aşıldı" in out


def test_capture_usage_meters_sop_turn_without_result(tmp_path):
    """SOP turns hand _capture_usage no AgentResult (result=None); usage must
    still be metered off the agent's own event_loop_metrics, and the per-agent
    baseline advanced so the NEXT turn only diffs the new tokens (review fix).
    Without it, SOP tokens go uncounted and inflate the next normal turn."""

    class _Metrics:
        def __init__(self, usage):
            self.accumulated_usage = usage

    class _Agent:
        def __init__(self, usage):
            self.event_loop_metrics = _Metrics(usage)

    rt = _runtime(tmp_path)
    agent = _Agent({"inputTokens": 1000, "outputTokens": 500})

    # First SOP turn — result=None like the SOP branch of _try_process.
    rt._capture_usage(agent, None, "scheduler:cron")
    sess = rt.token_meter._session["scheduler:cron"]
    assert (sess["input"], sess["output"]) == (1000, 500)
    assert rt.token_meter._turns == 1

    # Second SOP turn — accumulated_usage grows; only the delta is charged.
    agent.event_loop_metrics.accumulated_usage = {"inputTokens": 1500, "outputTokens": 700}
    rt._capture_usage(agent, None, "scheduler:cron")
    sess = rt.token_meter._session["scheduler:cron"]
    assert (sess["input"], sess["output"]) == (1500, 700)  # 1000+500, not 2500+1200
    assert rt.token_meter._turns == 2
