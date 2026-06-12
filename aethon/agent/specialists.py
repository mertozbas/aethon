"""Specialist agent factory.

Creates and caches specialist agents for multi-agent delegation.
"""

import logging

from strands import Agent
from strands.agent.conversation_manager import SummarizingConversationManager
from strands_tools import (
    file_read, file_write, editor, shell, think, current_time,
    python_repl, http_request, calculator,
)


logger = logging.getLogger("aethon.specialists")


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
            "Your responsibilities: breaking complex tasks into steps, prioritization.\n"
            "Make each step clear, concrete, and actionable.\n"
            "Call out dependencies and risks."
        ),
        "tools": [file_read, file_write, think],
    },
}


class SpecialistFactory:
    """Create and cache specialist agents."""

    def __init__(self, model, session_config=None, hooks_factory=None, sandbox=None):
        self.model = model
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

    def get(self, specialist_name: str) -> Agent:
        """Get or create a specialist agent."""
        if specialist_name not in self._cache:
            config = SPECIALIST_CONFIGS.get(specialist_name)
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
        """Get all specialist agents."""
        return {name: self.get(name) for name in SPECIALIST_CONFIGS}
