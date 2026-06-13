"""Tests for AethonRuntime."""

import pytest

from aethon.config import (
    AethonConfig, PathsConfig, ModelConfig, MultiAgentConfig, SOPConfig,
    ApprovalConfig,
)
from aethon.agent.runtime import AethonRuntime
from aethon.channels.base import InboundMessage


@pytest.fixture
def runtime_config(tmp_path):
    """Config with temp workspace for runtime tests."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "SOUL.md").write_text("Test kisilik")
    (workspace / "TOOLS.md").write_text("Test tercihler")
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    logs = tmp_path / "logs"
    logs.mkdir()

    return AethonConfig(
        model=ModelConfig(provider="fake", model_id="fake"),
        paths=PathsConfig(
            workspace=str(workspace),
            sessions=str(sessions),
            logs=str(logs),
            memory_db=str(tmp_path / "memory.sqlite"),
            credentials=str(tmp_path / "credentials"),
        ),
    )


def test_runtime_creation(runtime_config):
    """AethonRuntime creates without errors."""
    runtime = AethonRuntime(runtime_config)
    assert runtime.model is not None
    assert runtime.prompt_composer is not None
    assert runtime.agents == {}


def test_ask_scout_registered_as_tool(runtime_config):
    """E4: the scout delegate tool is available when multi-agent is on."""
    runtime = AethonRuntime(runtime_config)
    names = {
        getattr(t, "tool_name", getattr(t, "name", "?"))
        for t in runtime._get_tools("cli:u")
    }
    assert "ask_scout" in names


# --- Phase 10 C1: intake (chat vs work) ---


@pytest.fixture(autouse=True)
def _reset_delegate_globals():
    """Building a runtime wires the delegate module globals; reset them after
    each test so intake/planner state can't leak across tests."""
    yield
    import aethon.tools.delegate as delegate
    delegate.set_specialist_factory(None)
    delegate.set_plan_ledger(None)


class _PlanResult:
    def __init__(self, plan):
        self.structured_output = plan


class _Metrics:
    def __init__(self, usage):
        self.accumulated_usage = usage


class _StructPlanner:
    """A planner stub that returns a fixed structured plan (optionally carrying
    accumulated token usage on event_loop_metrics, like a real specialist)."""
    def __init__(self, plan, usage=None):
        self._plan = plan
        if usage is not None:
            self.event_loop_metrics = _Metrics(usage)

    def __call__(self, prompt, structured_output_model=None):
        return _PlanResult(self._plan)


def _intake_msg(text):
    # NOTE: a different _msg() helper already lives lower in this file — use a
    # distinct name so it isn't shadowed at module load.
    return InboundMessage(channel="cli", sender_id="u", sender_name="u", text=text)


def test_intake_disabled_is_normal_path(runtime_config):
    """With intake off (default), even a clear work message stays a normal turn."""
    runtime = AethonRuntime(runtime_config)
    assert runtime._maybe_intake(
        _intake_msg("Kullanıcı girişi olan bir blog API'si geliştir ve testleri yaz."),
        "cli:u",
    ) is None


def test_intake_chat_message_falls_through(runtime_config):
    runtime = AethonRuntime(runtime_config)
    runtime.config.core_loop.intake_enabled = True
    assert runtime._maybe_intake(_intake_msg("merhaba, bugün nasılsın?"), "cli:u") is None


def test_intake_work_message_opens_project(runtime_config):
    from aethon.agent.planning import PlanSchema, PlanTask

    runtime = AethonRuntime(runtime_config)
    runtime.config.core_loop.intake_enabled = True
    plan = PlanSchema(project_title="Blog API", tasks=[PlanTask(title="Şema tasarla")])
    runtime.specialist_factory._cache["planner"] = _StructPlanner(plan)

    reply = runtime._maybe_intake(
        _intake_msg("Kullanıcı girişi olan bir blog API'si geliştir ve testleri yaz."),
        "cli:u",
    )
    assert reply is not None
    assert "iş olarak" in reply           # acknowledgement
    assert "Blog API" in reply            # the plan summary
    # A project actually landed in the ledger.
    assert any(t["title"] == "Blog API" for t in runtime._task_ledger.list())
    # C4: the originating channel + sender were stamped on the project.
    proj = next(t for t in runtime._task_ledger.list() if t["title"] == "Blog API")
    assert proj["origin_channel"] == "cli"
    assert proj["origin_recipient"] == "u"


def test_intake_meters_planner_tokens(runtime_config):
    """C1 review fix: intake returns early, so it must meter the planner's spend
    itself — otherwise those tokens escape the E0 budget ceiling."""
    from aethon.agent.planning import PlanSchema, PlanTask

    runtime = AethonRuntime(runtime_config)
    runtime.config.core_loop.intake_enabled = True
    plan = PlanSchema(project_title="API", tasks=[PlanTask(title="şema")])
    runtime.specialist_factory._cache["planner"] = _StructPlanner(
        plan, usage={"inputTokens": 1200, "outputTokens": 600}
    )
    reply = runtime._maybe_intake(
        _intake_msg("Kullanıcı girişi olan bir blog API'si geliştir ve testleri yaz."),
        "cli:u",
    )
    assert reply is not None
    sess = runtime.token_meter._session.get("cli:u")
    assert sess and (sess["input"], sess["output"]) == (1200, 600)


def test_intake_work_but_no_structured_plan_falls_through(runtime_config):
    """Classified as work but the planner produced no structured tasks → don't
    claim a project was opened; fall through to the normal turn."""
    from aethon.agent.planning import PlanSchema

    runtime = AethonRuntime(runtime_config)
    runtime.config.core_loop.intake_enabled = True
    runtime.specialist_factory._cache["planner"] = _StructPlanner(PlanSchema(tasks=[]))

    assert runtime._maybe_intake(
        _intake_msg("Bir blog API'si geliştir ve testleri de yaz lütfen arkadaşım."),
        "cli:u",
    ) is None
    assert runtime._task_ledger.list() == []  # nothing opened


def test_planner_wiring_failure_does_not_null_ledger(runtime_config, monkeypatch):
    """C2 review fix: a failure wiring the planner→ledger pipeline must degrade
    only that pipeline, never the already-active TaskLedger."""
    import aethon.tools.delegate as delegate

    def boom(*a, **k):
        raise RuntimeError("wiring exploded")

    monkeypatch.setattr(delegate, "set_plan_ledger", boom)
    runtime = AethonRuntime(runtime_config)
    assert runtime._task_ledger is not None  # ledger survived the wiring failure


def test_get_or_create_agent(runtime_config):
    """Agent is created for a session."""
    runtime = AethonRuntime(runtime_config)
    agent = runtime.get_or_create_agent("test-session")
    assert agent is not None
    assert "test-session" in runtime.agents


def test_same_session_same_agent(runtime_config):
    """Same session returns same agent instance."""
    runtime = AethonRuntime(runtime_config)
    agent1 = runtime.get_or_create_agent("session-1")
    agent2 = runtime.get_or_create_agent("session-1")
    assert agent1 is agent2


def test_different_session_different_agent(runtime_config):
    """Different sessions return different agents."""
    runtime = AethonRuntime(runtime_config)
    agent1 = runtime.get_or_create_agent("session-1")
    agent2 = runtime.get_or_create_agent("session-2")
    assert agent1 is not agent2
    assert len(runtime.agents) == 2


def test_context_updater_writes_where_prompt_reads(runtime_config):
    """R1 regression: update_context must write the exact file compose() reads.

    runtime.py used to pass workspace/CONTEXT.md as the workspace dir, so the
    updater targeted CONTEXT.md/CONTEXT.md and every write raised
    NotADirectoryError.
    """
    from pathlib import Path

    runtime = AethonRuntime(runtime_config)
    workspace = Path(runtime_config.paths.workspace).expanduser()

    assert runtime._context_updater is not None
    assert runtime._context_updater.context_file == workspace / "CONTEXT.md"

    # Round-trip: the write must succeed and land in the prompt source file.
    runtime._context_updater.update("Aktif Gorev", "R1 regresyon")
    assert "R1 regresyon" in (workspace / "CONTEXT.md").read_text(encoding="utf-8")


def test_tools_list(runtime_config):
    """Runtime provides Phase 1 tools."""
    runtime = AethonRuntime(runtime_config)
    tools = runtime._get_tools()
    assert len(tools) > 0
    tool_names = [getattr(t, "__name__", str(t)) for t in tools]
    assert any("file_read" in name for name in tool_names)


def test_manage_tasks_tool_registered(runtime_config):
    """R9: the task ledger ships as a manage_tasks tool."""
    runtime = AethonRuntime(runtime_config)
    assert runtime._task_ledger is not None
    names = [
        getattr(t, "tool_name", getattr(t, "__name__", "")) for t in runtime._get_tools()
    ]
    assert any("manage_tasks" in str(n) for n in names)


def test_ledger_snapshot_survives_new_prompt_compose(runtime_config):
    """R9: open tasks surface in the system prompt of brand-new sessions."""
    runtime = AethonRuntime(runtime_config)
    runtime._task_ledger.create("Yarim kalan is", acceptance_criteria="test gecer")
    prompt = runtime.prompt_composer.compose("fresh-session")
    assert "## Open Tasks" in prompt
    assert "Yarim kalan is" in prompt


def test_volatile_prompt_refreshes_per_turn(runtime_config):
    """R10: mid-session context/ledger updates surface on the next turn."""
    runtime = AethonRuntime(runtime_config)
    agent = runtime.get_or_create_agent("refresh-session")
    assert "Sonradan eklenen gorev" not in (agent.system_prompt or "")

    runtime._task_ledger.create("Sonradan eklenen gorev")
    runtime._refresh_volatile_prompt(agent, "refresh-session")
    assert "Sonradan eklenen gorev" in agent.system_prompt


def test_reset_session_writes_handoff_checkpoint(runtime_config, tmp_path):
    """R11: a session reset distills a checkpoint instead of wiping orientation."""
    import json as _json

    runtime_config.session.storage_dir = str(tmp_path / "sessions")
    runtime = AethonRuntime(runtime_config)
    sessions_dir = tmp_path / "sessions"
    msgs = sessions_dir / "session_s1" / "agents" / "agent_main" / "messages"
    msgs.mkdir(parents=True)
    (msgs / "message_0.json").write_text(_json.dumps(
        {"message": {"role": "user", "content": [{"text": "raporu bitir"}]}}
    ))
    (msgs / "message_1.json").write_text(_json.dumps(
        {"message": {"role": "assistant", "content": [{"text": "yarisini yaptim"}]}}
    ))

    runtime._reset_session("s1")

    handoff = (tmp_path / "workspace" / "HANDOFF.md").read_text(encoding="utf-8")
    assert "raporu bitir" in handoff
    assert "yarisini yaptim" in handoff
    # The checkpoint is read back as a prompt layer.
    assert "## Handoff" in runtime.prompt_composer.compose("s2")


# --- Phase 10 E5.2: automatic recall ---


class _FakeMem:
    """A stand-in VectorMemory whose search returns canned results (no Ollama)."""

    def __init__(self, results):
        self.results = results
        self.queries = []

    def search(self, text, top_k=3, category=None):
        self.queries.append((text, top_k))
        return self.results[:top_k]


def test_recall_disabled_is_noop(runtime_config):
    """auto_recall defaults OFF — the message is not even embedded."""
    import types

    runtime = AethonRuntime(runtime_config)
    runtime.memory = _FakeMem([{"content": "x", "score": 0.9}])
    agent = types.SimpleNamespace()
    runtime._apply_recall(agent, "s", "merhaba")
    assert runtime.memory.queries == []          # never queried
    assert not hasattr(agent, "system_prompt")   # prompt untouched


def test_recall_injects_when_enabled(runtime_config):
    """With auto_recall on, matching memories become a prompt layer."""
    import types

    runtime_config.memory.auto_recall = True
    runtime = AethonRuntime(runtime_config)
    runtime.memory = _FakeMem([{"content": "Mert asyncio tercih eder", "score": 0.88}])
    agent = types.SimpleNamespace()
    runtime._apply_recall(agent, "s", "asyncio")
    assert "## Recalled Memories" in agent.system_prompt
    assert "Mert asyncio tercih eder" in agent.system_prompt
    assert agent.__aethon_recall__                # recorded on the agent
    # S9 hardening: recalled memories are framed as untrusted reference data,
    # not instructions — so saved attacker text can't act as system commands.
    assert "untrusted" in agent.system_prompt.lower()
    assert "not as instructions" in agent.system_prompt


def test_recall_unchanged_set_skips_recompose(runtime_config):
    """Same recalled set on the next turn → no recompose (cache stays warm)."""
    import types

    runtime_config.memory.auto_recall = True
    runtime = AethonRuntime(runtime_config)
    runtime.memory = _FakeMem([{"content": "sabit kayıt", "score": 0.5}])
    agent = types.SimpleNamespace()
    runtime._apply_recall(agent, "s", "soru bir")
    agent.system_prompt = "SENTINEL"             # overwritten only if recomposed
    runtime._apply_recall(agent, "s", "soru iki")  # same memory → same render
    assert agent.system_prompt == "SENTINEL"


def test_recall_min_score_filters(runtime_config):
    """Matches below recall_min_score are dropped before injection."""
    import types

    runtime_config.memory.auto_recall = True
    runtime_config.memory.recall_min_score = 0.7
    runtime = AethonRuntime(runtime_config)
    runtime.memory = _FakeMem([
        {"content": "yuksek skor", "score": 0.9},
        {"content": "dusuk skor", "score": 0.3},
    ])
    agent = types.SimpleNamespace()
    runtime._apply_recall(agent, "s", "q")
    assert "yuksek skor" in agent.system_prompt
    assert "dusuk skor" not in agent.system_prompt


def test_recall_is_fail_soft(runtime_config):
    """A recall failure logs and leaves the turn untouched — never raises."""
    import types

    runtime_config.memory.auto_recall = True
    runtime = AethonRuntime(runtime_config)

    class _Boom:
        def search(self, *a, **k):
            raise RuntimeError("ollama down")

    runtime.memory = _Boom()
    agent = types.SimpleNamespace()
    runtime._apply_recall(agent, "s", "q")        # must not raise
    assert not hasattr(agent, "system_prompt")    # turn untouched


def test_recall_compose_failure_self_heals(runtime_config):
    """Review fix: a compose() failure must NOT cache the recall key as success.

    Otherwise the next turn with the same recalled set short-circuits and the
    agent runs forever on a prompt missing its recall. The cache key is only
    committed after a successful compose, so the next turn retries."""
    import types

    runtime_config.memory.auto_recall = True
    runtime = AethonRuntime(runtime_config)
    runtime.memory = _FakeMem([{"content": "hatirlanan", "score": 0.9}])
    agent = types.SimpleNamespace()

    # Turn N: compose blows up (e.g. a transient workspace read error).
    calls = {"n": 0}
    real_compose = runtime.prompt_composer.compose

    def _flaky_compose(session_id="", recalled=""):
        calls["n"] += 1
        if calls["n"] == 1:
            raise OSError("transient read error")
        return real_compose(session_id, recalled=recalled)

    runtime.prompt_composer.compose = _flaky_compose
    runtime._apply_recall(agent, "s", "soru")          # must not raise
    assert not hasattr(agent, "system_prompt")          # recall not applied
    assert getattr(agent, "__aethon_recall__", None) is None  # key NOT cached

    # Turn N+1: SAME recalled set — must retry compose (not short-circuit).
    runtime._apply_recall(agent, "s", "soru")
    assert "## Recalled Memories" in agent.system_prompt  # healed on retry
    assert "hatirlanan" in agent.system_prompt


def test_hooks_list(runtime_config):
    """Runtime provides security hooks."""
    runtime = AethonRuntime(runtime_config)
    hooks = runtime._get_hooks()
    assert len(hooks) > 0
    from aethon.agent.hooks.security import SecurityHookProvider
    assert isinstance(hooks[0], SecurityHookProvider)


def test_reliability_hooks_registered_by_default(runtime_config):
    """R6+R7: PostEditVerify and CompletionGate ship enabled (advisory)."""
    from aethon.agent.hooks.post_edit_verify import PostEditVerifyHookProvider
    from aethon.agent.hooks.completion_gate import CompletionGateHookProvider

    runtime = AethonRuntime(runtime_config)
    hooks = runtime._get_hooks()
    assert any(isinstance(h, PostEditVerifyHookProvider) for h in hooks)
    assert any(isinstance(h, CompletionGateHookProvider) for h in hooks)

    # The gate is wired to the verify hook (its evidence source).
    gate = next(h for h in hooks if isinstance(h, CompletionGateHookProvider))
    assert isinstance(gate.verify_hook, PostEditVerifyHookProvider)


def test_reliability_hooks_can_be_disabled(runtime_config):
    runtime_config.reliability.post_edit_verify = False
    runtime_config.reliability.completion_gate = False
    runtime = AethonRuntime(runtime_config)
    names = [type(h).__name__ for h in runtime._get_hooks()]
    assert "PostEditVerifyHookProvider" not in names
    assert "CompletionGateHookProvider" not in names


# --- S6: answerable approval (interrupt→question→resume) --------------------


class _FakeInterrupt:
    def __init__(self, iid, reason):
        self.id = iid
        self.reason = reason


class _Result:
    def __init__(self, stop_reason, interrupts=None, text="done"):
        self.stop_reason = stop_reason
        self.interrupts = interrupts or []
        self.message = {"content": [{"text": text}]}


class _FakeAgent:
    """Returns an interrupt on the first call, a normal result on resume."""

    def __init__(self, rounds=1):
        self.calls = []
        self._rounds = rounds

    def __call__(self, prompt):
        self.calls.append(prompt)
        if len(self.calls) <= self._rounds:
            return _Result("interrupt", [
                _FakeInterrupt(
                    f"itr-{len(self.calls)}",
                    {"tool": "shell", "parameters": {"command": "ls"}, "message": "Onayla?"},
                )
            ])
        return _Result("end_turn", text="tamam")


def _msg(channel="telegram"):
    return InboundMessage(
        channel=channel, sender_id="u1", sender_name="U", text="çalıştır"
    )


def test_run_with_interrupts_resumes_with_decision(runtime_config, monkeypatch):
    """The loop resumes the agent with the channel's decision until it completes."""
    runtime = AethonRuntime(runtime_config)
    monkeypatch.setattr(
        runtime, "_resolve_approval_decision",
        lambda message, session_id, itr: {"approved": True, "reason": ""},
    )
    agent = _FakeAgent(rounds=1)
    result = runtime._run_with_interrupts(agent, _msg(), "telegram:u1", "çalıştır")
    assert result.stop_reason == "end_turn"
    assert len(agent.calls) == 2  # initial + one resume
    # The resume carried the interrupt response payload.
    resume = agent.calls[1]
    assert resume[0]["interruptResponse"]["interruptId"] == "itr-1"
    assert resume[0]["interruptResponse"]["response"]["approved"] is True


def test_run_with_interrupts_caps_runaway(runtime_config, monkeypatch):
    """A tool that re-interrupts forever is capped and denied, not hung."""
    runtime = AethonRuntime(runtime_config)
    monkeypatch.setattr(
        runtime, "_resolve_approval_decision",
        lambda message, session_id, itr: {"approved": True, "reason": ""},
    )
    # Always interrupts → exercises the MAX_INTERRUPT_ROUNDS guard.
    agent = _FakeAgent(rounds=10_000)
    runtime._run_with_interrupts(agent, _msg(), "telegram:u1", "x")
    from aethon.agent.runtime import MAX_INTERRUPT_ROUNDS
    # initial call + MAX rounds of resume + one final deny-all resume.
    assert len(agent.calls) == MAX_INTERRUPT_ROUNDS + 2


# --- H1: per-session serialization -----------------------------------------


@pytest.mark.asyncio
async def test_session_lock_serializes_same_session(runtime_config, monkeypatch):
    """Two concurrent turns for ONE session run sequentially; different sessions
    run in parallel."""
    import asyncio

    runtime = AethonRuntime(runtime_config)
    state = {"active": {}, "max": {}}

    def fake_sync(message, session_id):
        # Runs in the executor thread; record peak concurrency per session.
        import time

        state["active"][session_id] = state["active"].get(session_id, 0) + 1
        state["max"][session_id] = max(
            state["max"].get(session_id, 0), state["active"][session_id]
        )
        time.sleep(0.03)
        state["active"][session_id] -= 1
        return "ok"

    monkeypatch.setattr(runtime, "_process_sync", fake_sync)
    msg = InboundMessage(channel="cli", sender_id="u", sender_name="u", text="hi")

    # Same session twice + a different session once, all concurrent.
    await asyncio.gather(
        runtime.process(msg, "s1"),
        runtime.process(msg, "s1"),
        runtime.process(msg, "s2"),
    )
    assert state["max"]["s1"] == 1  # same session never overlapped
    assert state["max"]["s2"] == 1


@pytest.mark.asyncio
async def test_different_sessions_run_in_parallel(runtime_config, monkeypatch):
    import asyncio

    runtime = AethonRuntime(runtime_config)
    overlap = {"active": 0, "max": 0}

    def fake_sync(message, session_id):
        import time

        overlap["active"] += 1
        overlap["max"] = max(overlap["max"], overlap["active"])
        time.sleep(0.03)
        overlap["active"] -= 1
        return "ok"

    monkeypatch.setattr(runtime, "_process_sync", fake_sync)
    msg = InboundMessage(channel="cli", sender_id="u", sender_name="u", text="hi")
    await asyncio.gather(*(runtime.process(msg, f"s{i}") for i in range(4)))
    assert overlap["max"] >= 2  # distinct sessions ran concurrently


def test_agent_cache_thread_safe_under_concurrency(runtime_config):
    """Review fix: concurrent distinct-session turns hit the REAL
    get_or_create_agent on many threads; the LRU bound must hold (no overflow,
    no lost/double agents)."""
    import threading

    runtime = AethonRuntime(runtime_config)
    runtime._session_cache_size = 5

    barrier = threading.Barrier(20)

    def worker(i):
        barrier.wait()  # maximize the interleaving
        for _ in range(3):
            runtime.get_or_create_agent(f"sess-{i}")

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # The cache never exceeds its bound despite the concurrent check-then-act.
    assert len(runtime.agents) <= runtime._session_cache_size


def test_resolve_approval_fails_closed_without_gateway(runtime_config, monkeypatch):
    """No gateway/adapter/responder → deny with the 'can't answer' message."""
    import aethon.tools.messaging as messaging

    runtime = AethonRuntime(runtime_config)
    monkeypatch.setattr(messaging, "get_gateway", lambda: None)
    itr = _FakeInterrupt("i1", {"tool": "shell", "parameters": {}, "message": "?"})
    decision = runtime._resolve_approval_decision(_msg(), "telegram:u1", itr)
    assert decision["approved"] is False
    assert "yanıtlayamıyor" in decision["reason"]


def test_resolve_approval_uses_channel_responder(runtime_config, monkeypatch):
    """A channel that answers True is dispatched on the gateway loop and approved."""
    import asyncio
    import threading
    import aethon.tools.messaging as messaging

    runtime = AethonRuntime(runtime_config)

    # A real loop running on a background thread (mirrors the gateway loop).
    loop = asyncio.new_event_loop()
    t = threading.Thread(target=loop.run_forever, daemon=True)
    t.start()

    class _Adapter:
        async def ask_approval(self, request):
            assert request.tool == "shell"
            return True

    class _GW:
        adapters = {"telegram": _Adapter()}

    gw = _GW()
    gw.loop = loop
    monkeypatch.setattr(messaging, "get_gateway", lambda: gw)
    try:
        itr = _FakeInterrupt("i1", {"tool": "shell", "parameters": {}, "message": "?"})
        decision = runtime._resolve_approval_decision(_msg(), "telegram:u1", itr)
        assert decision["approved"] is True
    finally:
        loop.call_soon_threadsafe(loop.stop)
        t.join(timeout=2)


def test_resolve_approval_times_out_to_deny(runtime_config, monkeypatch):
    """A responder that never answers is denied at the timeout, not hung."""
    import asyncio
    import threading
    import aethon.tools.messaging as messaging

    runtime_config.approval.timeout_seconds = 0.2
    runtime = AethonRuntime(runtime_config)

    loop = asyncio.new_event_loop()
    t = threading.Thread(target=loop.run_forever, daemon=True)
    t.start()

    class _Adapter:
        async def ask_approval(self, request):
            await asyncio.sleep(60)  # never answers within the timeout
            return True

    class _GW:
        adapters = {"telegram": _Adapter()}

    gw = _GW()
    gw.loop = loop
    monkeypatch.setattr(messaging, "get_gateway", lambda: gw)
    try:
        itr = _FakeInterrupt("i1", {"tool": "shell", "parameters": {}, "message": "?"})
        decision = runtime._resolve_approval_decision(_msg(), "telegram:u1", itr)
        assert decision["approved"] is False
        assert "zaman aşımı" in decision["reason"]
    finally:
        loop.call_soon_threadsafe(loop.stop)
        t.join(timeout=2)


def test_completion_gate_note_appended_to_reply(runtime_config):
    """R6: the runtime appends the gate's pending reminder to the response."""
    runtime = AethonRuntime(runtime_config)
    agent = runtime.get_or_create_agent("gate-session")
    gate = runtime._completion_gates["gate-session"]

    # No pending note — reply returns clean.
    assert runtime._apply_completion_gate(agent, "gate-session", "ok") == "ok"

    gate._pending_note = "[Completion Gate] test reminder"
    gated = runtime._apply_completion_gate(agent, "gate-session", "Done.")
    assert gated.startswith("Done.")
    assert "[Completion Gate] test reminder" in gated


def test_runtime_with_multi_agent(tmp_path):
    """Runtime creates with multi-agent enabled."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "SOUL.md").write_text("Test")
    sops_dir = workspace / "sops"
    sops_dir.mkdir()
    sessions = tmp_path / "sessions"
    sessions.mkdir()

    config = AethonConfig(
        model=ModelConfig(provider="fake", model_id="fake"),
        multi_agent=MultiAgentConfig(enabled=True),
        sops=SOPConfig(enabled=True),
        paths=PathsConfig(
            workspace=str(workspace),
            sessions=str(sessions),
            logs=str(tmp_path / "logs"),
            memory_db=str(tmp_path / "memory.sqlite"),
            credentials=str(tmp_path / "credentials"),
        ),
    )
    runtime = AethonRuntime(config)
    assert runtime.specialist_factory is not None
    assert runtime.sop_runner is not None


def test_tools_include_delegate(tmp_path):
    """_get_tools includes delegate tools when multi-agent enabled."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "SOUL.md").write_text("Test")
    sops_dir = workspace / "sops"
    sops_dir.mkdir()
    sessions = tmp_path / "sessions"
    sessions.mkdir()

    config = AethonConfig(
        model=ModelConfig(provider="fake", model_id="fake"),
        multi_agent=MultiAgentConfig(enabled=True),
        paths=PathsConfig(
            workspace=str(workspace),
            sessions=str(sessions),
            logs=str(tmp_path / "logs"),
            memory_db=str(tmp_path / "memory.sqlite"),
            credentials=str(tmp_path / "credentials"),
        ),
    )
    runtime = AethonRuntime(config)
    tools = runtime._get_tools()
    tool_names = [getattr(t, "__name__", getattr(t, "tool_name", str(t))) for t in tools]
    assert any("ask_coder" in str(name) for name in tool_names)


def test_tools_no_delegate_when_disabled(tmp_path):
    """_get_tools excludes delegate tools when multi-agent disabled."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "SOUL.md").write_text("Test")
    sessions = tmp_path / "sessions"
    sessions.mkdir()

    config = AethonConfig(
        model=ModelConfig(provider="fake", model_id="fake"),
        multi_agent=MultiAgentConfig(enabled=False),
        paths=PathsConfig(
            workspace=str(workspace),
            sessions=str(sessions),
            logs=str(tmp_path / "logs"),
            memory_db=str(tmp_path / "memory.sqlite"),
            credentials=str(tmp_path / "credentials"),
        ),
    )
    runtime = AethonRuntime(config)
    tools = runtime._get_tools()
    tool_names = [getattr(t, "__name__", getattr(t, "tool_name", str(t))) for t in tools]
    assert not any("ask_coder" in str(name) for name in tool_names)


def test_hooks_include_approval_when_enabled(tmp_path):
    """_get_hooks includes ApprovalHookProvider when enabled."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "SOUL.md").write_text("Test")
    sessions = tmp_path / "sessions"
    sessions.mkdir()

    config = AethonConfig(
        model=ModelConfig(provider="fake", model_id="fake"),
        approval=ApprovalConfig(enabled=True),
        paths=PathsConfig(
            workspace=str(workspace),
            sessions=str(sessions),
            logs=str(tmp_path / "logs"),
            memory_db=str(tmp_path / "memory.sqlite"),
            credentials=str(tmp_path / "credentials"),
        ),
    )
    runtime = AethonRuntime(config)
    hooks = runtime._get_hooks()
    from aethon.agent.hooks.approval import ApprovalHookProvider
    assert any(isinstance(h, ApprovalHookProvider) for h in hooks)


@pytest.mark.ollama
@pytest.mark.asyncio
async def test_process_returns_response(runtime_config):
    """Process method returns a string response from real Ollama model."""
    runtime = AethonRuntime(runtime_config)
    msg = InboundMessage(
        channel="cli",
        sender_id="local",
        sender_name="User",
        text="Merhaba, 2+2 kac yapar? Sadece sayiyi soyler misin?",
    )
    response = await runtime.process(msg, "test-session")
    assert isinstance(response, str)
    assert len(response) > 0


# --- review fixes: hook ordering, inert gate, SOP gating ---


def test_output_guard_registered_last(runtime_config):
    """AfterToolCallEvent callbacks run in REVERSE registration order, so the
    output guard must be registered last — it then truncates the raw output
    FIRST and the [Verify]/LSP feedback appended by earlier-registered hooks
    survives."""
    from aethon.agent.hooks.output_guard import ToolOutputGuardHookProvider

    runtime = AethonRuntime(runtime_config)
    hooks = runtime._get_hooks()
    assert isinstance(hooks[-1], ToolOutputGuardHookProvider)


def test_completion_gate_skipped_without_evidence_source(runtime_config, caplog):
    """A gate with NO evidence source (no verify hook, no ledger) can never
    fire — skip it loudly instead of registering a silently inert guard."""
    import logging

    runtime_config.reliability.post_edit_verify = False
    runtime_config.reliability.completion_gate = True
    runtime = AethonRuntime(runtime_config)
    runtime._task_ledger = None  # remove the second evidence source too
    with caplog.at_level(logging.WARNING, logger="aethon.runtime"):
        hooks = runtime._get_hooks()
    names = [type(h).__name__ for h in hooks]
    assert "CompletionGateHookProvider" not in names
    assert any("CompletionGate skipped" in rec.message for rec in caplog.records)


def test_completion_gate_runs_on_ledger_alone(runtime_config):
    """R6 design: the ledger is an evidence source in its own right — the
    gate must register even when post_edit_verify is disabled."""
    runtime_config.reliability.post_edit_verify = False
    runtime = AethonRuntime(runtime_config)
    gates = [
        h for h in runtime._get_hooks()
        if type(h).__name__ == "CompletionGateHookProvider"
    ]
    assert len(gates) == 1
    assert gates[0].task_ledger is runtime._task_ledger


def test_sop_replies_are_gated(runtime_config):
    """A DoD note raised DURING the SOP turn must attach to the SOP reply,
    not leak into the next unrelated turn."""
    runtime = AethonRuntime(runtime_config)
    runtime.get_or_create_agent("sop-session")

    class _StubSOP:
        def is_sop_command(self, text):
            return True, "rapor", ""

        def run_sop(self, name, agent, user_input="", invoke=None):
            # Simulates the gate firing on AfterInvocationEvent inside
            # run_sop's agent(prompt) call.
            runtime._completion_gates["sop-session"]._pending_note = (
                "[Completion Gate] nag"
            )
            return "SOP bitti"

    runtime.sop_runner = _StubSOP()
    reply = runtime._try_process(
        InboundMessage(channel="cli", sender_id="u", sender_name="u", text="/rapor"),
        "sop-session", allow_retry=False,
    )
    assert reply.startswith("SOP bitti")
    assert "[Completion Gate] nag" in reply
    # Consumed — nothing leaks into the next turn.
    assert runtime._completion_gates["sop-session"]._pending_note is None


def test_sop_turn_routes_gated_tool_through_interrupts(runtime_config, monkeypatch):
    """S6 regression: a gated tool inside a SOP is resolved via the interrupt
    loop (approved/denied), not silently dropped."""
    runtime = AethonRuntime(runtime_config)
    captured = {}

    class _StubSOP:
        def is_sop_command(self, text):
            return True, "demo", ""

        def run_sop(self, name, agent, user_input="", invoke=None):
            captured["invoke"] = invoke
            # Drive a fake interrupting agent through the runtime's invoke —
            # this is exactly what a real SOP that calls a gated tool produces.
            result = invoke(_FakeAgent(rounds=1), "sop-prompt")
            return runtime._extract_text(result)

    runtime.sop_runner = _StubSOP()
    decisions = []
    monkeypatch.setattr(
        runtime, "_resolve_approval_decision",
        lambda m, s, itr: decisions.append((m.channel, s)) or {"approved": True, "reason": ""},
    )
    reply = runtime._try_process(
        InboundMessage(channel="cli", sender_id="u", sender_name="u", text="/demo"),
        "cli:u", allow_retry=False,
    )
    assert captured["invoke"] is not None           # SOP got the interrupt-aware invoke
    assert decisions == [("cli", "cli:u")]           # the interrupt was resolved via the channel
    assert "tamam" in reply


def test_stale_gate_note_discarded_at_turn_start(runtime_config):
    """Review fix: AfterInvocationEvent fires even on turns that later fail
    (strands runs it in a finally block) — a note from such a turn must not
    attach to the next unrelated reply."""
    runtime = AethonRuntime(runtime_config)
    runtime.get_or_create_agent("stale-session")
    runtime._completion_gates["stale-session"]._pending_note = (
        "[Completion Gate] eski turdan kalan nag"
    )

    reply = runtime._try_process(
        InboundMessage(channel="cli", sender_id="u", sender_name="u", text="merhaba"),
        "stale-session", allow_retry=False,
    )
    assert "[Completion Gate] eski turdan kalan nag" not in reply


# --- review fixes round 2: checkpoint sort, prompt stability, R10 wiring ---


def test_reset_checkpoint_sorts_messages_numerically(runtime_config, tmp_path):
    """Review fix: message_10.json sorted lexicographically before
    message_9.json, so the checkpoint distilled the wrong 'last' messages."""
    import json as _json

    runtime_config.session.storage_dir = str(tmp_path / "sessions")
    runtime = AethonRuntime(runtime_config)
    msgs = tmp_path / "sessions" / "session_s1" / "agents" / "agent_main" / "messages"
    msgs.mkdir(parents=True)
    for i in range(12):
        (msgs / f"message_{i}.json").write_text(_json.dumps(
            {"message": {"role": "user" if i % 2 == 0 else "assistant",
                         "content": [{"text": f"mesaj-{i}"}]}}
        ))

    runtime._reset_session("s1")
    handoff = (tmp_path / "workspace" / "HANDOFF.md").read_text(encoding="utf-8")
    assert "mesaj-10" in handoff  # last user message (index 10, not 8)
    assert "mesaj-11" in handoff  # last assistant message


def test_checkpoint_excerpts_cannot_fabricate_headers(runtime_config, tmp_path):
    """Review fix: '### ' inside user text must not corrupt the rotation."""
    import json as _json

    runtime_config.session.storage_dir = str(tmp_path / "sessions")
    runtime = AethonRuntime(runtime_config)
    msgs = tmp_path / "sessions" / "session_s1" / "agents" / "agent_main" / "messages"
    msgs.mkdir(parents=True)
    (msgs / "message_0.json").write_text(_json.dumps(
        {"message": {"role": "user",
                     "content": [{"text": "su markdown'a bak:\n### Checkpoint sahte\nve devami"}]}}
    ))

    runtime._reset_session("s1")
    handoff = (tmp_path / "workspace" / "HANDOFF.md").read_text(encoding="utf-8")
    import re as _re
    real_headers = _re.findall(r"(?m)^### Checkpoint ", handoff)
    assert len(real_headers) == 1  # the excerpt was flattened, not a new header


def test_prompt_stays_byte_stable_when_nothing_changed(runtime_config):
    """Review fix: per-turn recompose embedded a fresh timestamp every turn,
    defeating provider prompt caching. Unchanged sources → unchanged prompt."""
    runtime = AethonRuntime(runtime_config)
    agent = runtime.get_or_create_agent("stable-session")
    before = agent.system_prompt
    runtime._refresh_volatile_prompt(agent, "stable-session")
    assert agent.system_prompt == before  # byte-identical, cache stays warm


def test_r10_wiring_through_try_process(runtime_config):
    """Review fix: the regression test must pin the _try_process call site,
    not just the helper — removing the wiring used to pass the suite."""
    runtime = AethonRuntime(runtime_config)
    runtime.get_or_create_agent("wired-session")  # compose once, fp recorded

    runtime._task_ledger.create("Tur ortasinda eklenen is")
    runtime._try_process(
        InboundMessage(channel="cli", sender_id="u", sender_name="u", text="selam"),
        "wired-session", allow_retry=False,
    )
    agent = runtime.agents["wired-session"]
    assert "Tur ortasinda eklenen is" in agent.system_prompt


def test_r10_can_be_disabled(runtime_config):
    runtime_config.prompt.refresh_per_turn = False
    runtime = AethonRuntime(runtime_config)
    agent = runtime.get_or_create_agent("frozen-session")
    before = agent.system_prompt
    runtime._task_ledger.create("Gorunmemesi gereken is")
    runtime._refresh_volatile_prompt(agent, "frozen-session")
    assert agent.system_prompt == before


def test_input_validator_can_be_disabled(runtime_config):
    """Review fix: R16 now honors a config flag like every other new hook."""
    runtime_config.reliability.input_validator = False
    runtime = AethonRuntime(runtime_config)
    names = [type(h).__name__ for h in runtime._get_hooks()]
    assert "InputValidatorHookProvider" not in names


def test_strict_gate_reprompts_once(runtime_config):
    """Review fix: the strict-mode re-prompt path was untested."""
    runtime_config.reliability.strict = True
    runtime = AethonRuntime(runtime_config)
    agent = runtime.get_or_create_agent("strict-session")
    gate = runtime._completion_gates["strict-session"]
    gate._pending_note = "[Completion Gate] kanit yok"

    reply = runtime._apply_completion_gate(agent, "strict-session", "Bitti.")
    assert reply.startswith("Bitti.")
    assert len(reply) > len("Bitti.")  # follow-up text appended
    assert gate._pending_note is None  # no second nag carried over


def test_strict_gate_falls_back_to_note_on_error(runtime_config):
    runtime_config.reliability.strict = True
    runtime = AethonRuntime(runtime_config)
    runtime.get_or_create_agent("strict-err")
    gate = runtime._completion_gates["strict-err"]
    gate._pending_note = "[Completion Gate] kanit yok"

    class _Boom:
        def __call__(self, *a, **k):
            raise RuntimeError("model down")

    reply = runtime._apply_completion_gate(_Boom(), "strict-err", "Bitti.")
    assert "[Completion Gate] kanit yok" in reply


def test_degraded_hooks_empty_on_clean_startup(runtime_config):
    """R18: hook failures aggregate into a runtime health record."""
    runtime = AethonRuntime(runtime_config)
    runtime._get_hooks()
    assert runtime._degraded_hooks == []
