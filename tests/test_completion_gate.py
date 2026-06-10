"""Tests for CompletionGateHookProvider (Phase 8 / R6)."""

from types import SimpleNamespace

from aethon.config import ReliabilityConfig
from aethon.agent.hooks.completion_gate import (
    CompletionGateHookProvider, DOD_REMINDER,
)


def _agent_with_reply(text):
    return SimpleNamespace(
        messages=[
            {"role": "user", "content": [{"text": "fix the bug"}]},
            {"role": "assistant", "content": [{"text": text}]},
        ]
    )


def _verify_stub(edits_seen=0, last_outcome=None):
    return SimpleNamespace(edits_seen=edits_seen, last_outcome=last_outcome)


def _event(agent):
    return SimpleNamespace(agent=agent)


def _gate(verify_hook, **cfg):
    return CompletionGateHookProvider(
        config=ReliabilityConfig(**cfg), verify_hook=verify_hook
    )


def test_unverified_success_claim_is_flagged():
    vh = _verify_stub(edits_seen=2, last_outcome=None)
    gate = _gate(vh)
    gate._on_after_invocation(_event(_agent_with_reply("All done, tests passed.")))

    assert gate.consume_note() == DOD_REMINDER
    assert gate.consume_note() is None  # consumed
    assert vh.edits_seen == 0  # flag once per edit window


def test_turkish_success_claim_is_flagged():
    vh = _verify_stub(edits_seen=1)
    gate = _gate(vh)
    gate._on_after_invocation(_event(_agent_with_reply("Görev tamamlandı, her şey geçti.")))
    assert gate.consume_note() == DOD_REMINDER


def test_verified_claim_passes_clean():
    vh = _verify_stub(edits_seen=3, last_outcome="pass")
    gate = _gate(vh)
    gate._on_after_invocation(_event(_agent_with_reply("Done — tests passed.")))

    assert gate.consume_note() is None
    assert vh.edits_seen == 0  # evidence consumed, fresh window


def test_failed_verify_claim_is_flagged():
    vh = _verify_stub(edits_seen=1, last_outcome="fail")
    gate = _gate(vh)
    gate._on_after_invocation(_event(_agent_with_reply("Fixed!")))
    assert gate.consume_note() == DOD_REMINDER


def test_conversational_done_without_edits_is_ignored():
    vh = _verify_stub(edits_seen=0)
    gate = _gate(vh)
    gate._on_after_invocation(_event(_agent_with_reply("Done — nothing to change.")))
    assert gate.consume_note() is None


def test_non_success_reply_is_ignored():
    vh = _verify_stub(edits_seen=5)
    gate = _gate(vh)
    gate._on_after_invocation(
        _event(_agent_with_reply("I am still investigating the failure."))
    )
    assert gate.consume_note() is None
    assert vh.edits_seen == 5  # window stays open


def test_no_verify_hook_is_safe():
    gate = _gate(None)
    gate._on_after_invocation(_event(_agent_with_reply("Done, tests passed.")))
    assert gate.consume_note() is None
