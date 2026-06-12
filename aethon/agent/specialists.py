"""Specialist agent factory.

Creates and caches specialist agents for multi-agent delegation.
"""

import json
import logging
import re
import threading
from pathlib import Path

from strands import Agent
from strands.agent.conversation_manager import SummarizingConversationManager
from strands_tools import (
    file_read, file_write, editor, shell, think, current_time,
    python_repl, http_request, calculator,
)


logger = logging.getLogger("aethon.specialists")

# Tools a dynamically-created specialist (C5) may be granted. A persisted
# specialist stores its tools as NAME STRINGS; they are resolved back to
# callables ONLY through this allowlist — never via arbitrary import — so an
# injected agent can't grant itself a weapon it wasn't meant to have. ``shell``
# is allowed but gated separately (it can mutate).
DYNAMIC_TOOL_ALLOWLIST = {
    "file_read": file_read, "file_write": file_write, "editor": editor,
    "shell": shell, "think": think, "current_time": current_time,
    "python_repl": python_repl, "http_request": http_request,
    "calculator": calculator,
}
# The always-safe subset (read-only / pure compute). Everything else in the
# allowlist is "powerful" — it can execute code, mutate files, or reach the
# network (shell AND python_repl can run arbitrary code; file_write/editor
# mutate; http_request reaches out) — so a dynamic specialist may only be granted
# those when allow_powerful is on (the gate is enforced at tool RESOLUTION, which
# both create and disk-load go through — a hand-written JSON can't smuggle them).
SAFE_DYNAMIC_TOOLS = {"file_read", "think", "current_time", "calculator"}


SPECIALIST_CONFIGS = {
    "coder": {
        "name": "Coder",
        "system_prompt": (
            "You are a software development specialist.\n"
            "Your responsibilities: writing code, testing, debugging, refactoring.\n"
            "Follow TDD principles: write the test first, then implement.\n"
            "Write concise, clean code without comments.\n"
            "When you finish, report the result clearly."
        ),
        "tools": [file_read, file_write, editor, shell, python_repl, think],
    },
    "researcher": {
        "name": "Researcher",
        "system_prompt": (
            "You are a research specialist.\n"
            "Your responsibilities: web research, reading documentation, gathering information.\n"
            "Cite your sources. Present findings with a summary and analysis.\n"
            "Provide clear, verifiable information."
        ),
        "tools": [http_request, file_read, think, current_time],
    },
    "analyst": {
        "name": "Analyst",
        "system_prompt": (
            "You are a data analyst and report writer.\n"
            "Your responsibilities: data analysis, calculations, creating charts, writing reports.\n"
            "Present clear, measurable results.\n"
            "Show numerical data in table format."
        ),
        "tools": [python_repl, calculator, file_read, file_write, think],
    },
    "planner": {
        "name": "Planner",
        "system_prompt": (
            "You are a project planner.\n"
            "Break the request into a project with ordered, concrete, actionable "
            "steps. For each step give a clear title, an acceptance_criteria "
            "(how to verify it is done), and a priority "
            "(critical|high|medium|low). Express ordering with depends_on as the "
            "1-based positions of earlier steps it needs (e.g. [\"1\",\"2\"]).\n"
            "Call out dependencies and risks; prefer the smallest correct plan."
        ),
        "tools": [file_read, file_write, think],
    },
    "scout": {
        "name": "Scout",
        "system_prompt": (
            "You are a scout. The caller points you at sources (files, code, "
            "logs) and asks a question; you read what you need and return ONLY a "
            "concise conclusion — the answer plus the few file:line references "
            "that matter.\n"
            "NEVER paste raw file contents, long excerpts, or full dumps back: "
            "the caller wants the conclusion, not the material (the bulk stays "
            "with you, out of their context). Be brief, specific, and honest "
            "about what you could not determine."
        ),
        # shell is for SEARCH (grep/find across many files) — the scout has no
        # file_write/editor, so it's read-leaning, not read-PROOF: shell can
        # still mutate, contained by the same layer every specialist's shell gets
        # (sandbox in docker mode + the command blocklist tripwire). Its value is
        # context isolation, not write protection.
        "tools": [file_read, shell, think],
    },
}


class SpecialistFactory:
    """Create and cache specialist agents."""

    def __init__(
        self, model, session_config=None, hooks_factory=None, sandbox=None,
        workspace=None, allow_powerful=False,
    ):
        self.model = model
        # Whether a dynamic specialist may hold a powerful tool (shell, python_repl,
        # file_write, editor, http_request). Enforced at tool resolution below.
        self._allow_powerful = allow_powerful
        self._cache: dict[str, Agent] = {}
        self._summary_ratio = getattr(session_config, "summary_ratio", 0.3)
        self._preserve_recent = getattr(
            session_config, "preserve_recent_messages", 10
        )
        # Optional callable returning a fresh hooks list per specialist —
        # specialists edit files with their own tools, so they must not
        # bypass the security/reliability layer the main agent runs under.
        self._hooks_factory = hooks_factory
        # Execution sandbox (S7) — when set, a specialist's `shell` runs in a
        # per-specialist container too, so delegation can't escape the sandbox.
        self._sandbox = sandbox
        # C5 dynamic specialists: name -> {name, system_prompt, tools:[callables]}.
        self._dynamic: dict[str, dict] = {}
        self._lock = threading.Lock()
        self._workspace = Path(workspace).expanduser() if workspace else None
        if self._workspace:
            self._load_dynamic()

    @staticmethod
    def _slug(name: str) -> str:
        """A safe specialist key/filename — lowercase alnum/_/- only (so a name
        can't path-traverse or inject when it becomes a file name)."""
        return re.sub(r"[^a-z0-9_-]", "", str(name or "").strip().lower())[:40]

    def _spec_dir(self) -> Path:
        return self._workspace / "specialists"

    def _config_from_spec(self, spec: dict) -> dict | None:
        """Build a specialist config from a persisted/requested spec, resolving
        tool-name strings through the allowlist (unknown names dropped, loudly)."""
        key = self._slug(spec.get("name", ""))
        if not key:
            return None
        tools = []
        for tn in spec.get("tools") or []:
            tn = str(tn)
            cb = DYNAMIC_TOOL_ALLOWLIST.get(tn)
            if cb is None:
                logger.warning(
                    f"Dynamic specialist {key!r}: tool {tn!r} not in allowlist — dropped."
                )
                continue
            if tn not in SAFE_DYNAMIC_TOOLS and not self._allow_powerful:
                # The load-path gate: a persisted/crafted powerful tool is dropped
                # unless allow_powerful is on — config drift and hand-written JSON
                # can't grant a capability the config forbids.
                logger.warning(
                    f"Dynamic specialist {key!r}: powerful tool {tn!r} requires "
                    f"allow_powerful_specialists — dropped."
                )
                continue
            tools.append(cb)
        if not tools:
            tools = [think]  # a specialist always has at least one (safe) tool
        prompt = str(spec.get("system_prompt", "")).strip() or (
            f"You are {key}, a specialist. Do the task and report the result clearly."
        )
        return {"key": key, "name": key, "system_prompt": prompt, "tools": tools}

    def _load_dynamic(self) -> None:
        d = self._spec_dir()
        if not d.exists():
            return
        for f in sorted(d.glob("*.json")):
            try:
                cfg = self._config_from_spec(json.loads(f.read_text(encoding="utf-8")))
                if cfg:
                    self._dynamic[cfg["key"]] = cfg
            except Exception as e:
                logger.warning(f"Skipping unreadable specialist file {f.name}: {e}")

    def add_specialist(self, name, system_prompt, tool_names, *, persist=True) -> str:
        """Register (and optionally persist) a dynamic specialist. Returns its
        slugged key. Evicts any cached agent so the next get() rebuilds fresh."""
        cfg = self._config_from_spec(
            {"name": name, "system_prompt": system_prompt, "tools": tool_names}
        )
        if cfg is None:
            raise ValueError("A specialist needs a non-empty name.")
        key = cfg["key"]
        with self._lock:
            self._dynamic[key] = cfg
            self._cache.pop(key, None)
            if persist and self._workspace:
                self._spec_dir().mkdir(parents=True, exist_ok=True)
                # Persist the requested tool NAMES (strings), re-resolved on load.
                allowed = [n for n in (tool_names or []) if str(n) in DYNAMIC_TOOL_ALLOWLIST]
                (self._spec_dir() / f"{key}.json").write_text(
                    json.dumps(
                        {"name": key, "system_prompt": cfg["system_prompt"], "tools": allowed},
                        ensure_ascii=False, indent=2,
                    ),
                    encoding="utf-8",
                )
        return key

    def remove_specialist(self, name) -> bool:
        key = self._slug(name)
        with self._lock:
            existed = self._dynamic.pop(key, None) is not None
            self._cache.pop(key, None)
            if self._workspace:
                f = self._spec_dir() / f"{key}.json"
                if f.exists():
                    f.unlink()
                    existed = True
        return existed

    def list_specialists(self) -> dict:
        """All specialist keys → 'built-in' | 'custom'."""
        out = {n: "built-in" for n in SPECIALIST_CONFIGS}
        out.update({n: "custom" for n in self._dynamic})
        return out

    def get(self, specialist_name: str) -> Agent:
        """Get or create a specialist agent (built-in or dynamic)."""
        if specialist_name not in self._cache:
            config = SPECIALIST_CONFIGS.get(specialist_name) or self._dynamic.get(
                specialist_name
            )
            if not config:
                raise ValueError(f"Unknown specialist: {specialist_name}")

            hooks = self._hooks_factory() if self._hooks_factory else []
            tools = self._sandboxed_tools(specialist_name, config["tools"])
            self._cache[specialist_name] = Agent(
                model=self.model,
                system_prompt=config["system_prompt"],
                tools=tools,
                name=config["name"],
                agent_id=specialist_name,
                hooks=hooks,
                # Specialists are process-cached and reused for every
                # delegation; without a conversation manager their in-memory
                # history grows unbounded until the model rejects the request.
                conversation_manager=SummarizingConversationManager(
                    summary_ratio=self._summary_ratio,
                    preserve_recent_messages=self._preserve_recent,
                ),
            )
            # Session key for the dashboard pixel office (matches /api/agents/active).
            self._cache[specialist_name].__aethon_session__ = f"specialist:{specialist_name}"
            logger.info(f"Specialist agent created: {config['name']}")

        return self._cache[specialist_name]

    def _sandboxed_tools(self, specialist_name: str, tools: list) -> list:
        """Swap a specialist's host `shell` for a per-specialist sandboxed shell
        when the docker sandbox is on — so delegation can't escape it (S7)."""
        if self._sandbox is None or shell not in tools:
            return list(tools)
        from aethon.tools.shell_sandbox import make_sandboxed_shell

        sandboxed = make_sandboxed_shell(f"specialist:{specialist_name}", self._sandbox)
        return [sandboxed if t is shell else t for t in tools]

    def get_all(self) -> dict[str, Agent]:
        """Get all specialist agents (built-in + dynamic)."""
        names = list(SPECIALIST_CONFIGS) + [
            n for n in self._dynamic if n not in SPECIALIST_CONFIGS
        ]
        return {name: self.get(name) for name in names}
