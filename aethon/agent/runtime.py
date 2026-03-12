"""AETHON agent runtime.

Creates and manages Strands Agent instances per session.
"""

import asyncio
import logging
from pathlib import Path

from strands import Agent
from strands.session import FileSessionManager
from strands.agent.conversation_manager import SummarizingConversationManager
from strands_tools import file_read, file_write, editor, shell, think, current_time

from aethon.config import AethonConfig
from aethon.agent.model_factory import create_model
from aethon.agent.prompt import SystemPromptComposer
from aethon.agent.hooks.security import SecurityHookProvider
from aethon.channels.base import InboundMessage


logger = logging.getLogger("aethon.runtime")


class AethonRuntime:
    """AETHON agent runtime — manages model and agent lifecycle."""

    def __init__(self, config: AethonConfig):
        self.config = config
        self.model = create_model(config.model)
        self.prompt_composer = SystemPromptComposer(config.paths.workspace)
        self.agents: dict[str, Agent] = {}
        self.memory = None

        if getattr(config, "memory", None) and config.memory.enabled:
            try:
                from aethon.memory.vector import VectorMemory

                self.memory = VectorMemory(
                    db_path=config.memory.db_path,
                    ollama_host=config.model.host,
                    model_id=config.memory.embedding_model,
                )
                logger.info(
                    f"VectorMemory: aktif (model={config.memory.embedding_model})"
                )
            except Exception as e:
                logger.warning(f"VectorMemory baslatma hatasi: {e}")
                self.memory = None

    def _get_tools(self) -> list:
        """Tool list — includes memory tool if VectorMemory is active."""
        tools = [file_read, file_write, editor, shell, think, current_time]
        if self.memory:
            from aethon.tools.memory_tool import create_memory_tool

            tools.append(create_memory_tool(self.memory))
        return tools

    def _get_hooks(self) -> list:
        """Phase 1 hook list."""
        return [
            SecurityHookProvider(
                workspace=self.config.paths.workspace,
                blocked_commands=self.config.security.blocked_commands,
            ),
        ]

    def get_or_create_agent(self, session_id: str) -> Agent:
        """Get or create agent for a session."""
        if session_id not in self.agents:
            system_prompt = self.prompt_composer.compose(session_id)

            session_mgr = FileSessionManager(
                session_id=session_id,
                storage_dir=str(
                    Path(self.config.session.storage_dir).expanduser()
                ),
            )

            conv_mgr = SummarizingConversationManager(
                summary_ratio=self.config.session.summary_ratio,
                preserve_recent_messages=self.config.session.preserve_recent_messages,
            )

            self.agents[session_id] = Agent(
                model=self.model,
                system_prompt=system_prompt,
                tools=self._get_tools(),
                session_manager=session_mgr,
                conversation_manager=conv_mgr,
                hooks=self._get_hooks(),
                agent_id="main",
                name="AETHON",
            )

        return self.agents[session_id]

    def _process_sync(self, message: InboundMessage, session_id: str) -> str:
        """Process message synchronously (called from executor)."""
        agent = self.get_or_create_agent(session_id)
        result = agent(message.text)

        try:
            content = result.message["content"]
            text_parts = [block["text"] for block in content if "text" in block]
            return "\n".join(text_parts) if text_parts else str(result)
        except (KeyError, TypeError, IndexError):
            return str(result)

    async def process(self, message: InboundMessage, session_id: str) -> str:
        """Process message asynchronously.

        Strands Agent.__call__() is synchronous, so we run it in a thread executor
        to avoid blocking the asyncio event loop.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._process_sync, message, session_id
        )
