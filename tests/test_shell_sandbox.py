"""Tests for the per-session docker shell sandbox (Phase 9A / S7)."""

import subprocess

from aethon.config import SecurityConfig
from aethon.gateway.netsec import check_sandbox
from aethon.tools.shell_sandbox import (
    DockerSandbox,
    _container_name,
    _exec_argv,
    _run_argv,
)


class _Proc:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_container_name_is_docker_safe():
    # session ids carry colons (channel:sender) — illegal in container names.
    name = _container_name("telegram:12345")
    assert name.startswith("aethon-shell-telegram-12345-")
    assert ":" not in name


def test_container_name_no_collision():
    """Distinct sessions that sanitize to the same prefix must NOT collide."""
    a = _container_name("discord:9#9")
    b = _container_name("discord:9-9")
    assert a != b  # the hash suffix of the full id keeps them distinct


def test_run_argv_confines_the_container():
    cfg = SecurityConfig(sandbox="docker")
    argv = _run_argv(cfg, "aethon-shell-x", "/ws")
    joined = " ".join(argv)
    assert argv[:3] == ["docker", "run", "-d"]
    assert "--network" in argv and "none" in argv          # no host network
    assert "--memory" in argv and "512m" in argv           # resource caps
    assert "--pids-limit" in argv
    assert "-v" in argv and "/ws:/workspace" in argv        # workspace mounted
    assert "/root" not in joined                            # no host home mount


def test_run_argv_is_hardened():
    cfg = SecurityConfig(sandbox="docker")
    joined = " ".join(_run_argv(cfg, "c", "/ws"))
    assert "--cap-drop ALL" in joined
    assert "--security-opt no-new-privileges" in joined
    assert "--read-only" in joined
    assert "--label aethon-sandbox=1" in joined
    # Runs as a non-root host user where the platform supports it.
    import os
    if hasattr(os, "getuid"):
        assert f"--user {os.getuid()}:{os.getgid()}" in joined


def test_exec_argv():
    assert _exec_argv("c1", "ls -la") == ["docker", "exec", "c1", "sh", "-lc", "ls -la"]


def test_sandbox_runs_command_via_docker_exec():
    calls = []

    def fake_run(argv, timeout):
        calls.append(argv)
        if argv[1] == "run":
            return _Proc(returncode=0, stdout="container-id")
        return _Proc(returncode=0, stdout="hello\n")

    sb = DockerSandbox(SecurityConfig(sandbox="docker"), "/ws", runner=fake_run)
    result = sb.run("telegram:1", "echo hello")
    assert result["status"] == "success"
    assert "hello" in result["content"][0]["text"]
    # One `run` started the container, then `exec` ran the command in it.
    assert calls[0][1] == "run"
    assert calls[1][:2] == ["docker", "exec"]


def test_sandbox_reuses_container():
    runs = {"run": 0}

    def fake_run(argv, timeout):
        if argv[1] == "run":
            runs["run"] += 1
        return _Proc(returncode=0, stdout="")

    sb = DockerSandbox(SecurityConfig(sandbox="docker"), "/ws", runner=fake_run)
    sb.run("s1", "echo a")
    sb.run("s1", "echo b")
    assert runs["run"] == 1  # container created once, reused


def test_dead_container_is_recreated():
    """A container that died is recreated once instead of erroring forever."""
    seq = {"runs": 0, "execs": 0}

    def fake_run(argv, timeout):
        if argv[1] == "run":
            seq["runs"] += 1
            return _Proc(returncode=0)
        if argv[1] == "exec":
            seq["execs"] += 1
            if seq["execs"] == 1:  # first exec hits a dead container
                return _Proc(returncode=1, stderr="Error: No such container: x")
            return _Proc(returncode=0, stdout="recovered")
        return _Proc(returncode=0)

    sb = DockerSandbox(SecurityConfig(sandbox="docker"), "/ws", runner=fake_run)
    result = sb.run("s1", "echo a")
    assert result["status"] == "success"
    assert "recovered" in result["content"][0]["text"]
    assert seq["runs"] == 2  # recreated after the dead container


def test_reap_orphans_removes_labeled_containers():
    """A previous crashed run's labeled containers are removed (called at boot)."""
    removed = []

    def fake_run(argv, timeout):
        if argv[1] == "ps":
            return _Proc(returncode=0, stdout="abc123\ndef456\n")
        if argv[1] == "rm":
            removed.extend(argv[3:])
        return _Proc(returncode=0)

    sb = DockerSandbox(SecurityConfig(sandbox="docker"), "/ws", runner=fake_run)
    sb.reap_orphans()
    assert removed == ["abc123", "def456"]


def test_sandbox_failed_start_is_hard_error():
    def fake_run(argv, timeout):
        return _Proc(returncode=1, stderr="no such image")

    sb = DockerSandbox(SecurityConfig(sandbox="docker"), "/ws", runner=fake_run)
    result = sb.run("s1", "echo a")
    assert result["status"] == "error"
    assert "no such image" in result["content"][0]["text"]


def test_sandbox_timeout_is_error():
    def fake_run(argv, timeout):
        if argv[1] == "run":
            return _Proc(returncode=0)
        raise subprocess.TimeoutExpired(argv, timeout)

    sb = DockerSandbox(SecurityConfig(sandbox="docker"), "/ws", runner=fake_run)
    result = sb.run("s1", "sleep 999")
    assert result["status"] == "error"
    assert "timed out" in result["content"][0]["text"]


def test_command_error_status_reported():
    def fake_run(argv, timeout):
        if argv[1] == "run":
            return _Proc(returncode=0)
        return _Proc(returncode=2, stderr="command not found")

    sb = DockerSandbox(SecurityConfig(sandbox="docker"), "/ws", runner=fake_run)
    result = sb.run("s1", "nope")
    assert result["status"] == "error"
    assert "command not found" in result["content"][0]["text"]


def test_cleanup_removes_containers():
    removed = []

    def fake_run(argv, timeout):
        if argv[:3] == ["docker", "rm", "-f"]:
            removed.append(argv[3])
        return _Proc(returncode=0)

    sb = DockerSandbox(SecurityConfig(sandbox="docker"), "/ws", runner=fake_run)
    sb.run("s1", "echo a")
    sb.cleanup()
    assert len(removed) == 1 and removed[0].startswith("aethon-shell-s1-")


# --- startup gate + tool swap ----------------------------------------------


def test_check_sandbox_none_always_ok():
    ok, _ = check_sandbox(_cfg_holder("none"))
    assert ok is True


def test_check_sandbox_docker_missing_refuses(monkeypatch):
    import aethon.tools.shell_sandbox as ss

    monkeypatch.setattr(ss, "docker_available", lambda: False)
    ok, msg = check_sandbox(_cfg_holder("docker"))
    assert ok is False
    assert "docker" in msg and "security.sandbox" in msg


def test_check_sandbox_docker_present_ok(monkeypatch):
    import aethon.tools.shell_sandbox as ss

    monkeypatch.setattr(ss, "docker_available", lambda: True)
    ok, _ = check_sandbox(_cfg_holder("docker"))
    assert ok is True


class _CfgHolder:
    def __init__(self, sandbox):
        self.security = SecurityConfig(sandbox=sandbox)


def _cfg_holder(sandbox):
    return _CfgHolder(sandbox)


def _runtime(tmp_path, sandbox="none"):
    from aethon.agent.runtime import AethonRuntime
    from aethon.config import (
        AethonConfig, ModelConfig, PathsConfig, MemoryConfig, MCPConfig,
    )

    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "SOUL.md").write_text("x")
    cfg = AethonConfig(
        model=ModelConfig(provider="fake", model_id="fake"),
        memory=MemoryConfig(enabled=False),
        mcp=MCPConfig(enabled=False),
        paths=PathsConfig(
            workspace=str(ws), sessions=str(tmp_path / "s"), logs=str(tmp_path / "l"),
            memory_db=str(tmp_path / "m.sqlite"), credentials=str(tmp_path / "c"),
        ),
    )
    cfg.security.sandbox = sandbox
    return AethonRuntime(cfg)


def _tool_name(t):
    return getattr(t, "tool_name", getattr(t, "__name__", str(t)))


def test_sandbox_none_uses_host_shell(tmp_path):
    rt = _runtime(tmp_path, sandbox="none")
    assert rt._sandbox is None
    from strands_tools import shell as host_shell

    assert host_shell in rt._get_tools("s1")  # the plain host shell, unchanged


def test_sandbox_docker_swaps_shell_per_session(tmp_path):
    rt = _runtime(tmp_path, sandbox="docker")
    assert rt._sandbox is not None
    from strands_tools import shell as host_shell

    tools = rt._get_tools("telegram:42")
    assert host_shell not in tools                       # host shell removed
    shells = [t for t in tools if _tool_name(t) == "shell"]
    assert len(shells) == 1                              # exactly one shell tool
    # Without a session id (schema introspection) the host shell is kept.
    assert host_shell in rt._get_tools()
