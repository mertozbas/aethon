"""Tests for E2 message-history compaction (Phase 10)."""

from aethon.agent.hooks.compaction import (
    _SENTINEL,
    CompactionHookProvider,
    compact_messages,
)


def _user(text):
    return {"role": "user", "content": [{"text": text}]}


def _tooluse(tid, name="shell"):
    return {"role": "assistant", "content": [{"toolUse": {"toolUseId": tid, "name": name, "input": {}}}]}


def _toolresult(tid, text):
    return {
        "role": "user",
        "content": [{"toolResult": {"toolUseId": tid, "status": "success",
                                     "content": [{"text": text}]}}],
    }


def _reply(text):
    return {"role": "assistant", "content": [{"text": text}]}


def _turn(i, result_text):
    """A complete user→toolUse→toolResult→reply turn."""
    tid = f"tool_{i}"
    return [_user(f"soru {i}"), _tooluse(tid), _toolresult(tid, result_text), _reply(f"cevap {i}")]


def _conversation(n, result_text):
    msgs = []
    for i in range(n):
        msgs.extend(_turn(i, result_text))
    return msgs


def _result_texts(messages):
    out = []
    for m in messages:
        for b in m.get("content", []):
            tr = b.get("toolResult")
            if isinstance(tr, dict):
                out.extend(cb.get("text", "") for cb in tr.get("content", []))
    return out


BIG = "x" * 1000


def test_compacts_old_large_results_when_bulk_exceeds_trigger():
    msgs = _conversation(6, BIG)
    n = compact_messages(msgs, keep_last_n_turns=2, min_chars=100, trigger_chars=1000)
    assert n == 4                              # turns 0..3 compacted (6 - keep 2)
    texts = _result_texts(msgs)
    # First four results compacted, last two (recent turns) full.
    assert all(t.startswith(_SENTINEL) for t in texts[:4])
    assert texts[-1] == BIG and texts[-2] == BIG


def test_below_trigger_does_nothing():
    """Cache protection: not enough old bulk → no message edits at all."""
    msgs = _conversation(6, BIG)
    before = _result_texts(msgs)
    n = compact_messages(msgs, keep_last_n_turns=2, min_chars=100, trigger_chars=100_000)
    assert n == 0
    assert _result_texts(msgs) == before       # untouched → cache stays warm


def test_recent_turns_are_never_touched():
    msgs = _conversation(5, BIG)
    compact_messages(msgs, keep_last_n_turns=3, min_chars=100, trigger_chars=500)
    texts = _result_texts(msgs)
    assert texts[0].startswith(_SENTINEL) and texts[1].startswith(_SENTINEL)
    assert texts[2] == BIG and texts[3] == BIG and texts[4] == BIG  # last 3 kept


def test_pairing_preserved_no_blocks_removed():
    msgs = _conversation(6, BIG)
    uses_before = sum(1 for m in msgs for b in m.get("content", []) if "toolUse" in b)
    res_before = sum(1 for m in msgs for b in m.get("content", []) if "toolResult" in b)
    compact_messages(msgs, keep_last_n_turns=2, min_chars=100, trigger_chars=500)
    uses_after = sum(1 for m in msgs for b in m.get("content", []) if "toolUse" in b)
    res_after = sum(1 for m in msgs for b in m.get("content", []) if "toolResult" in b)
    assert (uses_before, res_before) == (uses_after, res_after)  # nothing removed


def test_small_results_below_min_chars_are_kept():
    msgs = _conversation(6, "ok")            # tiny results
    n = compact_messages(msgs, keep_last_n_turns=2, min_chars=100, trigger_chars=1)
    assert n == 0
    assert all(t == "ok" for t in _result_texts(msgs))


def test_thinking_blocks_are_left_untouched():
    msgs = _conversation(5, BIG)
    # Put a thinking block in the message that ALSO holds an old toolResult.
    msgs[2]["content"].insert(0, {"thinking": {"text": "düşünce"}})
    compact_messages(msgs, keep_last_n_turns=2, min_chars=100, trigger_chars=500)
    # The thinking-bearing toolResult (turn 0) is skipped; its text stays full.
    assert _result_texts(msgs)[0] == BIG


def test_compact_once_stable_second_pass_is_noop():
    msgs = _conversation(6, BIG)
    n1 = compact_messages(msgs, keep_last_n_turns=2, min_chars=100, trigger_chars=500)
    snapshot = _result_texts(msgs)
    n2 = compact_messages(msgs, keep_last_n_turns=2, min_chars=100, trigger_chars=500)
    assert n1 == 4 and n2 == 0                 # nothing re-churned
    assert _result_texts(msgs) == snapshot     # byte-stable → cache not re-poisoned


def test_short_conversation_not_compacted():
    msgs = _conversation(2, BIG)
    assert compact_messages(msgs, keep_last_n_turns=4, min_chars=1, trigger_chars=1) == 0


def test_hook_registers_before_model_call():
    from strands.hooks.events import BeforeModelCallEvent

    registered = {}

    class _Reg:
        def add_callback(self, event_type, cb):
            registered[event_type] = cb

    CompactionHookProvider().register_hooks(_Reg())
    assert BeforeModelCallEvent in registered
