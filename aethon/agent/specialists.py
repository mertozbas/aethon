"""Specialist agent factory.

Creates and caches specialist agents for multi-agent delegation.
"""

import logging

from strands import Agent
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

    def __init__(self, model):
        self.model = model
        self._cache: dict[str, Agent] = {}

    def get(self, specialist_name: str) -> Agent:
        """Get or create a specialist agent."""
        if specialist_name not in self._cache:
            config = SPECIALIST_CONFIGS.get(specialist_name)
            if not config:
                raise ValueError(f"Unknown specialist: {specialist_name}")

            self._cache[specialist_name] = Agent(
                model=self.model,
                system_prompt=config["system_prompt"],
                tools=config["tools"],
                name=config["name"],
                agent_id=specialist_name,
            )
            # Session key for the dashboard pixel office (matches /api/agents/active).
            self._cache[specialist_name].__aethon_session__ = f"specialist:{specialist_name}"
            logger.info(f"Specialist agent created: {config['name']}")

        return self._cache[specialist_name]

    def get_all(self) -> dict[str, Agent]:
        """Get all specialist agents."""
        return {name: self.get(name) for name in SPECIALIST_CONFIGS}
