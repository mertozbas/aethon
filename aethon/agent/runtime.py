"""AETHON agent runtime.

Creates and manages Strands Agent instances per session.
"""

import asyncio
import logging
import os
from collections import OrderedDict
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
        # Bypass the interactive per-tool consent prompt from strands-tools by default
        # (AETHON runs headless and has its own guardrails). Must be set before any tool
        # runs. An explicit env var still wins if the user set one.
        if getattr(config.security, "bypass_tool_consent", True):
            os.environ.setdefault("BYPASS_TOOL_CONSENT", "true")
        self.model = create_model(config.model)
        self.prompt_composer = SystemPromptComposer(config.paths.workspace)
        self._session_cache_size = config.performance.session_cache_size
        self.agents: OrderedDict[str, Agent] = OrderedDict()
        self.memory = None
        self.specialist_factory = None
        self.sop_runner = None
        self.team_orchestrator = None
        self._telemetry_hook = None
        self._context_updater = None
        self._mcp_loader = None
        self._event_bus = None

        # VectorMemory
        if getattr(config, "memory", None) and config.memory.enabled:
            try:
                from aethon.memory.vector import VectorMemory

                emb_provider = getattr(config.memory, "embedding_provider", "ollama")
                emb_api_key = getattr(config.memory, "embedding_api_key", "")
                self.memory = VectorMemory(
                    db_path=config.memory.db_path,
                    ollama_host=getattr(config.memory, "embedding_host", "") or config.model.host,
                    model_id=config.memory.embedding_model,
                    embedding_cache_size=config.performance.embedding_cache_size,
                    embedding_provider=emb_provider,
                    embedding_api_key=emb_api_key,
                )
                logger.info(
                    f"VectorMemory: active ({emb_provider}/{config.memory.embedding_model})"
                )
            except Exception as e:
                logger.warning(f"VectorMemory startup error: {e}")
                self.memory = None

        # SpecialistFactory + delegate tools
        if config.multi_agent.enabled:
            try:
                from aethon.agent.specialists import SpecialistFactory
                from aethon.tools.delegate import set_specialist_factory

                self.specialist_factory = SpecialistFactory(self.model)
                set_specialist_factory(self.specialist_factory)
                logger.info("Multi-agent: active")
            except Exception as e:
                logger.warning(f"Multi-agent startup error: {e}")
                self.specialist_factory = None

        # SOPRunner
        if config.sops.enabled:
            try:
                from aethon.sops.runner import SOPRunner

                sop_dirs = [
                    str(Path(config.paths.workspace).expanduser() / "sops")
                ]
                self.sop_runner = SOPRunner(
                    sop_dirs, config.sops.builtin_sops_enabled
                )
                logger.info(
                    f"SOPs: {len(self.sop_runner.list_sops())} loaded"
                )
            except Exception as e:
                logger.warning(f"SOPRunner startup error: {e}")
                self.sop_runner = None

        # TelemetryHookProvider
        if config.telemetry.enabled:
            try:
                from aethon.agent.hooks.telemetry import TelemetryHookProvider

                self._telemetry_hook = TelemetryHookProvider(
                    max_history=config.telemetry.max_history,
                )
                logger.info("Telemetry: active")
            except Exception as e:
                logger.warning(f"Telemetry startup error: {e}")

        # ContextUpdater
        try:
            from aethon.agent.context_updater import ContextUpdater

            context_path = str(
                Path(config.paths.workspace).expanduser() / "CONTEXT.md"
            )
            self._context_updater = ContextUpdater(context_path)
            logger.info("ContextUpdater: active")
        except Exception as e:
            logger.warning(f"ContextUpdater startup error: {e}")

        # MCP Tool Loader
        if config.mcp.enabled and config.mcp.servers:
            try:
                from aethon.tools.mcp_integration import MCPToolLoader

                self._mcp_loader = MCPToolLoader(config.mcp.servers)
                self._mcp_loader.start()
                logger.info(
                    f"MCP: {len(self._mcp_loader.get_tools())} tools loaded"
                )
            except Exception as e:
                logger.warning(f"MCP startup error: {e}")
                self._mcp_loader = None

    def _sanitize_session(self, session_id: str) -> None:
        """Sanitize a session's message history for cross-provider compatibility.

        Converts toolUse/toolResult blocks into plain text so the conversation
        context is preserved when switching between model providers.
        The agent is evicted from cache so it gets recreated with clean history.
        """
        import json

        sessions_dir = Path(self.config.session.storage_dir).expanduser()
        messages_dir = (
            sessions_dir / f"session_{session_id}" / "agents" / "agent_main" / "messages"
        )

        if not messages_dir.exists():
            self.agents.pop(session_id, None)
            return

        sanitized = 0
        for msg_file in sorted(messages_dir.glob("message_*.json")):
            try:
                data = json.loads(msg_file.read_text())
                message = data.get("message", {})
                content = message.get("content", [])
                if not content:
                    continue

                new_content = []
                changed = False
                for block in content:
                    if "text" in block:
                        new_content.append(block)
                    elif "toolUse" in block:
                        tu = block["toolUse"]
                        tool_name = tu.get("name", "?")
                        tool_input = tu.get("input", {})
                        # Extract the first meaningful input value
                        input_summary = next(iter(tool_input.values()), "") if tool_input else ""
                        if len(str(input_summary)) > 200:
                            input_summary = str(input_summary)[:200] + "..."
                        new_content.append({"text": f"[{tool_name}: {input_summary}]"})
                        changed = True
                    elif "toolResult" in block:
                        tr = block["toolResult"]
                        result_texts = []
                        for rc in tr.get("content", []):
                            if "text" in rc:
                                result_texts.append(rc["text"])
                        result_summary = "\n".join(result_texts)
                        if len(result_summary) > 500:
                            result_summary = result_summary[:500] + "..."
                        status = tr.get("status", "")
                        new_content.append({"text": f"[Result ({status}): {result_summary}]"})
                        changed = True
                    else:
                        # Unknown block type — keep as-is
                        new_content.append(block)

                if changed and new_content:
                    data["message"]["content"] = new_content
                    msg_file.write_text(json.dumps(data, ensure_ascii=False))
                    sanitized += 1

            except Exception as e:
                logger.debug(f"Failed to sanitize message ({msg_file.name}): {e}")

        if sanitized:
            logger.warning(
                f"Session sanitized ({session_id}): "
                f"tool blocks in {sanitized} messages converted to text"
            )

        # Evict from cache so it gets recreated with clean history
        self.agents.pop(session_id, None)

    def _get_tools(self) -> list:
        """Tool list — includes memory, delegate, context, messaging, scheduler, MCP tools."""
        tools = [file_read, file_write, editor, shell, think, current_time]
        if self.memory:
            from aethon.tools.memory_tool import create_memory_tool

            tools.append(create_memory_tool(self.memory))
        if self.specialist_factory:
            from aethon.tools.delegate import (
                ask_coder, ask_researcher, ask_analyst, ask_planner,
            )

            tools.extend([ask_coder, ask_researcher, ask_analyst, ask_planner])
        if self._context_updater:
            from aethon.tools.context_tool import create_context_tool

            tools.append(create_context_tool(self._context_updater))
        # send_message tool
        try:
            from aethon.tools.messaging import send_message

            tools.append(send_message)
        except Exception:
            pass
        # Scheduler tools
        try:
            from aethon.tools.scheduler import (
                _scheduler_instance, schedule_task,
                list_scheduled_jobs, remove_scheduled_job,
            )

            if _scheduler_instance:
                tools.extend([schedule_task, list_scheduled_jobs, remove_scheduled_job])
        except Exception:
            pass
        # MCP tools
        if self._mcp_loader:
            tools.extend(self._mcp_loader.get_tools())
        return tools

    def _get_hooks(self) -> list:
        """Hook list — security + memory_guard + telemetry + optional approval.

        Hook order: Security -> MemoryGuard -> Telemetry -> Approval
        """
        hooks = [
            SecurityHookProvider(
                workspace=self.config.paths.workspace,
                blocked_commands=self.config.security.blocked_commands,
                workspace_only=self.config.security.workspace_only,
            ),
        ]
        # MemoryGuardHook
        if self.config.memory_guard.enabled:
            try:
                from aethon.agent.hooks.memory_guard import MemoryGuardHookProvider

                hooks.append(
                    MemoryGuardHookProvider(
                        custom_patterns=self.config.memory_guard.custom_patterns,
                    )
                )
            except Exception as e:
                logger.warning(f"MemoryGuard startup error: {e}")
        # TelemetryHook
        if self._telemetry_hook:
            hooks.append(self._telemetry_hook)
        # ApprovalHook
        if self.config.approval.enabled:
            from aethon.agent.hooks.approval import ApprovalHookProvider

            hooks.append(
                ApprovalHookProvider(self.config.approval.requires_approval)
            )
            logger.info("ApprovalHook: active")
        return hooks

    def get_or_create_agent(self, session_id: str) -> Agent:
        """Get or create agent for a session.

        Uses LRU cache: moves accessed session to end, evicts oldest when full.
        Evicted sessions persist on disk via FileSessionManager.
        """
        if session_id in self.agents:
            self.agents.move_to_end(session_id)
            return self.agents[session_id]

        # Evict oldest if cache full
        if len(self.agents) >= self._session_cache_size:
            evicted_id, _ = self.agents.popitem(last=False)
            logger.debug(f"Session evicted from cache: {evicted_id}")

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
            # Don't let Strands print to stdout — each channel renders the reply itself
            # (otherwise the CLI shows every answer twice).
            callback_handler=None,
        )

        return self.agents[session_id]

    def warm_up(self):
        """Warm up the model with a dummy request.

        Creates a temporary agent, sends 'Hi', discards.
        Helps reduce first-request latency.
        """
        try:
            logger.info("Model warm-up starting...")
            agent = Agent(
                model=self.model,
                system_prompt="Just say 'Hi!'.",
                tools=[],
                callback_handler=None,
            )
            agent("Hi")
            logger.info("Model warm-up complete")
        except Exception as e:
            logger.warning(f"Model warm-up error: {e}")

    def _process_sync(self, message: InboundMessage, session_id: str) -> str:
        """Process message synchronously (called from executor).

        If the model call fails due to incompatible session history (e.g. after
        switching providers), the session is automatically reset and retried once.
        """
        return self._try_process(message, session_id, allow_retry=True)

    def _try_process(
        self, message: InboundMessage, session_id: str, allow_retry: bool
    ) -> str:
        """Attempt to process message, with optional retry after session reset."""
        try:
            # SOP command check
            if self.sop_runner:
                is_sop, sop_name, sop_input = self.sop_runner.is_sop_command(
                    message.text
                )
                if is_sop:
                    agent = self.get_or_create_agent(session_id)
                    return self.sop_runner.run_sop(sop_name, agent, sop_input)

            # Normal message processing
            agent = self.get_or_create_agent(session_id)
            result = agent(message.text)

            try:
                content = result.message["content"]
                text_parts = [block["text"] for block in content if "text" in block]
                return "\n".join(text_parts) if text_parts else str(result)
            except (KeyError, TypeError, IndexError):
                return str(result)

        except Exception as e:
            if allow_retry and self._is_context_overflow_error(e):
                logger.warning(
                    f"Context window overflow ({session_id}); clearing the session "
                    f"history and retrying. Long-term memory and CONTEXT.md are kept. ({e})"
                )
                self._reset_session(session_id)
                return self._try_process(message, session_id, allow_retry=False)

            if allow_retry and self._is_session_format_error(e):
                logger.warning(
                    f"Session format mismatch ({session_id}), "
                    f"resetting history and retrying: {e}"
                )
                self._sanitize_session(session_id)
                return self._try_process(message, session_id, allow_retry=False)

            logger.error(f"Model error ({session_id}): {type(e).__name__}: {e}")
            raise

    @staticmethod
    def _is_session_format_error(exc: Exception) -> bool:
        """Check if an exception is caused by incompatible session message history."""
        msg = str(exc).lower()
        indicators = [
            "tool_calls",            # OpenAI: tool role without preceding tool_calls
            "tool_use",              # Anthropic: orphaned toolUse
            "toolresult",            # Strands: missing toolResult
            "tool_result",           # Strands variant
            "invalid parameter",     # OpenAI generic format error
            "messages with role",    # OpenAI: role ordering error
            "orphaned",              # Strands warning turned error
            "conversation history",  # Generic history error
        ]
        return any(ind in msg for ind in indicators)

    @staticmethod
    def _is_context_overflow_error(exc: Exception) -> bool:
        """Check if an exception is a model context-window overflow."""
        msg = str(exc).lower()
        return any(s in msg for s in [
            "context window",
            "context length",
            "context_length_exceeded",
            "exceeds the context",
            "maximum context",
            "too many tokens",
            "input is too long",
            "string too long",
        ])

    def _reset_session(self, session_id: str) -> None:
        """Clear a session's message history (e.g. after a context-window overflow) so
        the next turn starts fresh. Long-term memory and CONTEXT.md are unaffected."""
        sessions_dir = Path(self.config.session.storage_dir).expanduser()
        messages_dir = (
            sessions_dir / f"session_{session_id}" / "agents" / "agent_main" / "messages"
        )
        if messages_dir.exists():
            for msg_file in messages_dir.glob("message_*.json"):
                try:
                    msg_file.unlink()
                except Exception:
                    pass
        self.agents.pop(session_id, None)

    async def process(self, message: InboundMessage, session_id: str) -> str:
        """Process message asynchronously.

        Strands Agent.__call__() is synchronous, so we run it in a thread executor
        to avoid blocking the asyncio event loop.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._process_sync, message, session_id
        )
