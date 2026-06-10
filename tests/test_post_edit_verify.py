"""Tests for PostEditVerifyHookProvider (Phase 8 / R7)."""

import shutil

import pytest

from aethon.config import ReliabilityConfig
from aethon.agent.hooks.post_edit_verify import PostEditVerifyHookProvider


class _Ev:
    """Minimal AfterToolCallEvent stand-in (same pattern as test_lsp.py)."""

    def __init__(self, tool_name, tool_input, status="success"):
        self.tool_use = {"name": tool_name, "input": tool_input}
        self.result = {"status": status, "content": []}


def _py_file(tmp_path, content="x = 1\n"):
    f = tmp_path / "sample.py"
    f.write_text(content, encoding="utf-8")
    return str(f)


def _hook(**cfg):
    hook = PostEditVerifyHookProvider(config=ReliabilityConfig(**cfg))
    # pytest tmp_path lives outside the user's home; lift the home boundary
    # so the hook sees the test files.
    hook._home = "/"
    return hook


def test_pass_appends_verify_block(tmp_path):
    hook = _hook(verify_cmd="true")
    ev = _Ev("file_write", {"path": _py_file(tmp_path)})
    hook._on_tool_complete(ev)

    texts = [b["text"] for b in ev.result["content"]]
    assert any("[Verify] PASS" in t for t in texts)
    assert hook.last_outcome == "pass"
    assert ev.result["status"] == "success"


def test_fail_appends_detail_and_stays_advisory(tmp_path):
    hook = _hook(verify_cmd="echo kirik-kod; exit 3")
    ev = _Ev("editor", {"path": _py_file(tmp_path)})
    hook._on_tool_complete(ev)

    texts = [b["text"] for b in ev.result["content"]]
    assert any("[Verify] FAIL (exit 3)" in t for t in texts)
    assert any("kirik-kod" in t for t in texts)
    assert hook.last_outcome == "fail"
    # Advisory by default: the result status is NOT escalated.
    assert ev.result["status"] == "success"


def test_fail_strict_marks_result_error(tmp_path):
    hook = _hook(verify_cmd="exit 1", strict=True)
    ev = _Ev("file_write", {"path": _py_file(tmp_path)})
    hook._on_tool_complete(ev)
    assert ev.result["status"] == "error"


def test_paths_placeholder_substitution(tmp_path):
    path = _py_file(tmp_path)
    hook = _hook(verify_cmd="ls {paths}")
    ev = _Ev("file_write", {"path": path})
    hook._on_tool_complete(ev)
    assert hook.last_outcome == "pass"


def test_non_file_tool_is_ignored(tmp_path):
    hook = _hook(verify_cmd="true")
    ev = _Ev("think", {"thought": "hmm"})
    hook._on_tool_complete(ev)
    assert ev.result["content"] == []
    assert hook.edits_seen == 0


def test_failed_edit_is_not_verified(tmp_path):
    """If the edit itself errored there is nothing to verify."""
    hook = _hook(verify_cmd="true")
    ev = _Ev("file_write", {"path": _py_file(tmp_path)}, status="error")
    hook._on_tool_complete(ev)
    assert ev.result["content"] == []


def test_edits_counted_even_without_verify_cmd(tmp_path, monkeypatch):
    """Edits with no verify command still open an evidence window for R6."""
    monkeypatch.setattr(shutil, "which", lambda _: None)  # no ruff auto-detect
    hook = _hook(verify_cmd="")
    ev = _Ev("file_write", {"path": _py_file(tmp_path)})
    hook._on_tool_complete(ev)
    assert hook.edits_seen == 1
    assert hook.last_outcome is None
    assert ev.result["content"] == []


@pytest.mark.skipif(shutil.which("ruff") is None, reason="ruff not on PATH")
def test_autodetect_runs_ruff_on_python_files(tmp_path):
    hook = _hook(verify_cmd="")
    ev = _Ev("file_write", {"path": _py_file(tmp_path, "import os\n")})  # unused import
    hook._on_tool_complete(ev)

    texts = [b["text"] for b in ev.result["content"]]
    assert any("[Verify] FAIL" in t for t in texts)
    assert hook.last_outcome == "fail"


def test_timeout_is_surfaced(tmp_path):
    hook = _hook(verify_cmd="sleep 5", verify_timeout=1)
    ev = _Ev("file_write", {"path": _py_file(tmp_path)})
    hook._on_tool_complete(ev)

    texts = [b["text"] for b in ev.result["content"]]
    assert any("[Verify] TIMEOUT" in t for t in texts)
    assert hook.last_outcome is None
