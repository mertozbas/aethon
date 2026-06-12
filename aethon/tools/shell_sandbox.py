"""Per-session docker sandbox for the `shell` tool (Phase 9A / S7).

The blocklist (SecurityHook) is a last-resort tripwire, not a boundary — it is
substring-based and bypassable. The real "military-grade" move is a real OS
boundary: route `shell` through a disposable per-session container so bypassing
the blocklist no longer matters — the blast radius is a throwaway container with
the workspace mounted, no host home, no host network by default, and resource
caps.

Staged (v1): only `shell` is sandboxed; file tools stay host-side under the
existing path rules (documented in SECURITY.md). Broader confinement is future
work.
"""

import hashlib
import logging
import os
import re
import shutil
import subprocess
from typing import Any, Callable

logger = logging.getLogger("aethon.sandbox")

# Marks every container we create so orphans from a crashed run can be reaped.
SANDBOX_LABEL = "aethon-sandbox=1"


def docker_available() -> bool:
    """True when a docker CLI is on PATH (the S7 startup gate checks this)."""
    return shutil.which("docker") is not None


def _container_name(session_id: str) -> str:
    """A collision-free, docker-safe container name for a session.

    A readable sanitized prefix PLUS a hash of the FULL id, so two distinct
    sessions that sanitize to the same prefix (e.g. ``a:b`` and ``a-b``) still
    get distinct containers — no cross-session shell access.
    """
    safe = re.sub(r"[^a-zA-Z0-9_.-]", "-", session_id)[:48]
    digest = hashlib.sha256(session_id.encode()).hexdigest()[:12]
    return f"aethon-shell-{safe or 'x'}-{digest}"


def _run_argv(cfg, name: str, workspace: str) -> list[str]:
    """`docker run` argv that starts a long-lived, confined session container.

    Least privilege: runs as the host user (so workspace files stay owned by the
    user, not root), drops all capabilities, forbids privilege escalation, and
    optionally a read-only rootfs with a writable /tmp + the workspace mount.
    """
    argv = [
        "docker", "run", "-d", "--rm",
        "--name", name,
        "--label", SANDBOX_LABEL,
        "--network", cfg.sandbox_network,
        "--memory", cfg.sandbox_memory,
        "--cpus", str(cfg.sandbox_cpus),
        "--pids-limit", str(cfg.sandbox_pids_limit),
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges",
    ]
    # Run as the host user where the platform supports it (Linux/macOS), so the
    # container cannot create root-owned files in the bind-mounted workspace.
    getuid = getattr(os, "getuid", None)
    getgid = getattr(os, "getgid", None)
    if getuid and getgid:
        argv += ["--user", f"{getuid()}:{getgid()}"]
    if getattr(cfg, "sandbox_read_only", True):
        argv += ["--read-only", "--tmpfs", "/tmp"]
    argv += [
        "-v", f"{workspace}:/workspace",
        "-w", "/workspace",
        cfg.sandbox_image,
        "sleep", "infinity",
    ]
    return argv


def _exec_argv(name: str, command: str) -> list[str]:
    """`docker exec` argv that runs one shell command in the session container."""
    return ["docker", "exec", name, "sh", "-lc", command]


class DockerSandbox:
    """Manages per-session shell containers (lazy create, reuse, cleanup)."""

    def __init__(self, cfg, workspace: str, runner: Callable | None = None):
        self.cfg = cfg
        self.workspace = workspace
        # Injectable for tests; defaults to subprocess.run.
        self._run = runner or self._default_run
        self._started: set[str] = set()

    def reap_orphans(self) -> None:
        """Force-remove any labeled containers left by a previous (crashed) run."""
        try:
            proc = self._run(
                ["docker", "ps", "-aq", "--filter", f"label={SANDBOX_LABEL}"], 30
            )
            ids = [x for x in (getattr(proc, "stdout", "") or "").split() if x]
            if ids:
                self._run(["docker", "rm", "-f", *ids], 30)
                logger.info(f"Reaped {len(ids)} orphan sandbox container(s)")
        except Exception as e:
            logger.warning(f"Sandbox orphan reap error: {e}")

    @staticmethod
    def _default_run(argv, timeout):
        return subprocess.run(
            argv, capture_output=True, text=True, timeout=timeout
        )

    def _ensure_container(self, session_id: str) -> str:
        name = _container_name(session_id)
        if name in self._started:
            return name
        argv = _run_argv(self.cfg, name, self.workspace)
        proc = self._run(argv, 60)
        if getattr(proc, "returncode", 1) != 0:
            # A container that won't start is a hard failure — the alternative
            # (silently running on the host) would defeat the whole point.
            raise RuntimeError(
                f"sandbox container failed to start: "
                f"{getattr(proc, 'stderr', '') or getattr(proc, 'stdout', '')}"
            )
        self._started.add(name)
        logger.info(f"Sandbox container started: {name}")
        return name

    def run(self, session_id: str, command: str) -> dict[str, Any]:
        """Run one command in the session container; strands tool-result shape."""
        try:
            name = self._ensure_container(session_id)
            proc = self._run(_exec_argv(name, command), self.cfg.sandbox_timeout)
            # Self-heal: a container that died (crash/OOM) leaves a stale entry —
            # recreate once instead of erroring on every later command.
            if _is_dead_container(proc):
                self._started.discard(name)
                name = self._ensure_container(session_id)
                proc = self._run(_exec_argv(name, command), self.cfg.sandbox_timeout)
        except subprocess.TimeoutExpired:
            return _result(
                f"Command timed out after {self.cfg.sandbox_timeout}s.", error=True
            )
        except Exception as e:
            return _result(f"Sandbox error: {e}", error=True)
        out = (getattr(proc, "stdout", "") or "") + (getattr(proc, "stderr", "") or "")
        return _result(out or "(no output)", error=getattr(proc, "returncode", 0) != 0)

    def cleanup(self) -> None:
        """Force-remove every container this sandbox started."""
        for name in list(self._started):
            try:
                self._run(["docker", "rm", "-f", name], 30)
            except Exception as e:
                logger.warning(f"Sandbox cleanup error ({name}): {e}")
        self._started.clear()


def _result(text: str, error: bool = False) -> dict[str, Any]:
    return {"status": "error" if error else "success", "content": [{"text": text}]}


def _is_dead_container(proc) -> bool:
    """True when `docker exec` failed because the container is gone/stopped."""
    if getattr(proc, "returncode", 0) == 0:
        return False
    err = (getattr(proc, "stderr", "") or "").lower()
    return "no such container" in err or "is not running" in err


def make_sandboxed_shell(session_id: str, sandbox: "DockerSandbox"):
    """Return a @tool `shell` that runs in the session's container instead of the
    host. Same name/shape as strands_tools.shell so it is a drop-in replacement."""
    from strands import tool

    @tool(name="shell")
    def shell(command: str) -> dict[str, Any]:
        """Execute a shell command inside this session's sandboxed container.

        The command runs in an isolated container (workspace mounted at
        /workspace, no host home, no host network by default), not on the host.
        """
        return sandbox.run(session_id, command)

    return shell
