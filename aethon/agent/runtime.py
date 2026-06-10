"""AETHON agent runtime.

Creates and manages Strands Agent instances per session.
"""

import asyncio
import logging
import os
import platform
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
        # Tools run headless inside the gateway. Stop strands-tools from taking
        # over the TTY (PTY/termios) or drawing interactive rich panels — both
        # corrupt the CLI and other channels (boxes drift, ANSI codes leak). The
        # command output is still captured and returned to the agent.
        os.environ["STRANDS_NON_INTERACTIVE"] = "true"
        if os.environ.get("STRANDS_TOOL_CONSOLE_MODE") == "enabled":
            os.environ["STRANDS_TOOL_CONSOLE_MODE"] = "disabled"
        # AETHON keeps full edit history via its own FileSessionManager; the
        # strands editor's FILE.bak sidecars are pure noise that leaks into
        # workspaces and commits ('git add .'). An explicit env var still wins.
        os.environ.setdefault("EDITOR_DISABLE_BACKUP", "true")
        self.model = create_model(config.model)
        self.prompt_composer = SystemPromptComposer(
            config.paths.workspace,
            config=getattr(config, "prompt", None),
            logs_dir=getattr(config.paths, "logs", None),
        )
        self._session_cache_size = config.performance.session_cache_size
        self.agents: OrderedDict[str, Agent] = OrderedDict()
        self.memory = None
        self.specialist_factory = None
        self.sop_runner = None
        self.team_orchestrator = None
        self._telemetry_hook = None
        self._session_recorder_hook = None
        self._ambient_manager = None  # wired by the gateway when ambient is enabled
        self._context_updater = None
        self._mcp_loader = None
        self._event_bus = None
        # Per-session CompletionGate instances (R6) — read after each turn so a
        # success claim with no verification evidence doesn't return clean.
        self._completion_gates: dict[str, object] = {}

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

                self.specialist_factory = SpecialistFactory(
                    self.model, session_config=config.session
                )
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
                # Single source of truth for the prompt's SOP layer (R18).
                self.prompt_composer.sop_runner = self.sop_runner
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

        # SessionRecorderHookProvider (single instance shared across agents)
        if getattr(config, "session_recorder", None) and config.session_recorder.enabled:
            try:
                from aethon.agent.hooks.session_recorder import (
                    SessionRecorderHookProvider,
                )

                self._session_recorder_hook = SessionRecorderHookProvider(
                    config=config.session_recorder,
                    recordings_dir=getattr(config.paths, "recordings", None),
                )
                logger.info("SessionRecorder: active")
            except Exception as e:
                logger.warning(f"SessionRecorder startup error: {e}")

        # ContextUpdater
        try:
            from aethon.agent.context_updater import ContextUpdater

            # ContextUpdater expects the workspace *directory* and appends
            # CONTEXT.md itself — passing the file path here used to produce
            # CONTEXT.md/CONTEXT.md and break every update_context write.
            workspace_dir = str(Path(config.paths.workspace).expanduser())
            self._context_updater = ContextUpdater(workspace_dir)
            logger.info("ContextUpdater: active")
        except Exception as e:
            logger.warning(f"ContextUpdater startup error: {e}")

        # Task ledger (R9) — durable, machine-readable working state.
        try:
            from aethon.agent.task_ledger import TaskLedger

            self._task_ledger = TaskLedger(
                str(Path(config.paths.workspace).expanduser())
            )
            logger.info("TaskLedger: active")
        except Exception as e:
            logger.warning(f"TaskLedger startup error: {e}")
            self._task_ledger = None

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
            self._completion_gates.pop(session_id, None)
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
        self._completion_gates.pop(session_id, None)

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
        if self._task_ledger:
            from aethon.tools.task_tool import create_task_tool

            tools.append(create_task_tool(self._task_ledger))
        # send_message tool
        try:
            from aethon.tools.messaging import send_message

            tools.append(send_message)
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"Tool load error (send_message): {e}")
        # Scheduler tools
        try:
            from aethon.tools.scheduler import (
                _scheduler_instance, schedule_task,
                list_scheduled_jobs, remove_scheduled_job,
            )

            if _scheduler_instance:
                tools.extend([schedule_task, list_scheduled_jobs, remove_scheduled_job])
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"Tool load error (scheduler): {e}")
        # MCP tools
        if self._mcp_loader:
            tools.extend(self._mcp_loader.get_tools())
        # Vendored capability tools (config-gated; import-guarded so a missing
        # optional dependency just skips the tool rather than breaking startup).
        caps = getattr(self.config, "capabilities", None)
        if caps:
            if caps.scraper.enabled:
                try:
                    from aethon.tools.vendor.scraper import scraper

                    tools.append(scraper)
                except ImportError:
                    pass
                except Exception as e:
                    logger.warning(f"Tool load error (scraper): {e}")
            if caps.github.enabled:
                try:
                    from aethon.tools.vendor.use_github import use_github

                    tools.append(use_github)
                except ImportError:
                    pass
                except Exception as e:
                    logger.warning(f"Tool load error (use_github): {e}")
            if caps.jsonrpc.enabled:
                try:
                    from aethon.tools.vendor.jsonrpc import jsonrpc

                    tools.append(jsonrpc)
                except ImportError:
                    pass
                except Exception as e:
                    logger.warning(f"Tool load error (jsonrpc): {e}")
            if caps.notify.enabled:
                try:
                    from aethon.tools.vendor.notify import notify

                    tools.append(notify)
                except ImportError:
                    pass
                except Exception as e:
                    logger.warning(f"Tool load error (notify): {e}")
            # use_computer — high-risk; only when enabled AND pyautogui is present.
            if getattr(caps, "computer", None) and caps.computer.enabled:
                import importlib.util as _ilu

                if _ilu.find_spec("pyautogui") is not None:
                    try:
                        from aethon.tools.vendor.use_computer import use_computer

                        tools.append(use_computer)
                    except ImportError:
                        pass
                    except Exception as e:
                        logger.warning(f"Tool load error (use_computer): {e}")
        # macOS native tools (Darwin-only; config-gated; import-guarded). The
        # security hook hard-blocks disabled action groups (Messages/Keychain
        # default off); apple_notes registers only when macos.enable_notes is set.
        macos_cfg = getattr(self.config, "macos", None)
        if macos_cfg and macos_cfg.enabled and platform.system() == "Darwin":
            try:
                from aethon.tools.vendor.use_mac import use_mac

                tools.append(use_mac)
            except ImportError:
                pass
            except Exception as e:
                logger.warning(f"Tool load error (use_mac): {e}")
            if macos_cfg.enable_notes:
                try:
                    from aethon.tools.vendor.apple_notes import apple_notes

                    tools.append(apple_notes)
                except ImportError:
                    pass
                except Exception as e:
                    logger.warning(f"Tool load error (apple_notes): {e}")
        # LSP tool — opt-in (avoid spawning language servers on boot).
        lsp_cfg = getattr(self.config, "lsp", None)
        if lsp_cfg and lsp_cfg.enabled:
            try:
                from aethon.tools.lsp_tool import lsp

                tools.append(lsp)
            except ImportError:
                pass
            except Exception as e:
                logger.warning(f"Tool load error (lsp): {e}")
        # record_learning — persists discoveries to LEARNINGS.md (read back into
        # the prompt by SystemPromptComposer when prompt.include_learnings).
        prompt_cfg = getattr(self.config, "prompt", None)
        if prompt_cfg is None or prompt_cfg.include_learnings:
            try:
                from aethon.tools.learning import create_learning_tool

                tools.append(create_learning_tool(self.config.paths.workspace))
            except ImportError:
                pass
            except Exception as e:
                logger.warning(f"Tool load error (record_learning): {e}")
        # manage_messages — introspective only (reads message history; no mutation,
        # no gating needed). Always available when importable.
        try:
            from aethon.tools.manage_messages import manage_messages

            tools.append(manage_messages)
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"Tool load error (manage_messages): {e}")
        # Ambient mode tools — only when enabled AND the gateway wired a manager.
        if (
            getattr(self.config, "ambient", None)
            and self.config.ambient.enabled
            and self._ambient_manager is not None
        ):
            try:
                from aethon.tools.ambient import create_ambient_tools

                tools.extend(create_ambient_tools(self._ambient_manager))
            except ImportError:
                pass
            except Exception as e:
                logger.warning(f"Tool load error (ambient): {e}")
        # manage_tools — dynamic tool loading. Opt-in; the security/approval hooks
        # and the tool's own config check gate the dangerous actions.
        rt_cfg = getattr(self.config, "runtime_tools", None)
        if rt_cfg and rt_cfg.enabled:
            try:
                from aethon.tools.manage_tools import manage_tools

                tools.append(manage_tools)
            except ImportError:
                pass
            except Exception as e:
                logger.warning(f"Tool load error (manage_tools): {e}")
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
                macos=getattr(self.config, "macos", None),
                runtime_tools=getattr(self.config, "runtime_tools", None),
            ),
        ]
        # Tool-input validator (R16) — turn malformed calls into
        # self-describing cancellations instead of opaque pydantic errors.
        try:
            from aethon.agent.hooks.input_validator import (
                InputValidatorHookProvider,
            )

            hooks.append(InputValidatorHookProvider())
        except Exception as e:
            logger.warning(f"InputValidator startup error: {e}")
        # Tool-output guard — cap oversized tool results before they reach the
        # model (prevents a single huge command from overflowing the context).
        max_out = getattr(self.config.performance, "max_tool_output_chars", 0)
        if max_out and max_out > 0:
            try:
                from aethon.agent.hooks.output_guard import ToolOutputGuardHookProvider

                hooks.append(ToolOutputGuardHookProvider(max_chars=max_out))
            except Exception as e:
                logger.warning(f"ToolOutputGuard startup error: {e}")
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
        # LSP diagnostics hook (opt-in; only when the LSP tool is also enabled)
        lsp_cfg = getattr(self.config, "lsp", None)
        if lsp_cfg and lsp_cfg.enabled and lsp_cfg.auto_diagnostics:
            try:
                from aethon.agent.hooks.lsp import LSPDiagnosticsHookProvider

                hooks.append(
                    LSPDiagnosticsHookProvider(
                        config=lsp_cfg, workspace=self.config.paths.workspace
                    )
                )
                logger.info("LSPDiagnosticsHook: active")
            except Exception as e:
                logger.warning(f"LSP diagnostics hook startup error: {e}")
        # Anglicization guard (R14) — existing non-English text must not be
        # silently rewritten to English. Advisory: pauses the edit once with
        # a reminder; an identical re-issue passes (strict always blocks).
        rel_cfg_guard = getattr(self.config, "reliability", None)
        if rel_cfg_guard is None or getattr(
            rel_cfg_guard, "anglicization_guard", True
        ):
            try:
                from aethon.agent.hooks.anglicization_guard import (
                    AnglicizationGuardHookProvider,
                )

                hooks.append(
                    AnglicizationGuardHookProvider(
                        strict=bool(getattr(rel_cfg_guard, "strict", False))
                    )
                )
            except Exception as e:
                logger.warning(f"AnglicizationGuard startup error: {e}")
        # Reliability hooks (Phase 8): PostEditVerify (R7) + CompletionGate (R6).
        # Advisory by default; reliability.strict flips them to hard gates.
        rel_cfg = getattr(self.config, "reliability", None)
        verify_hook = None
        if rel_cfg and rel_cfg.post_edit_verify:
            try:
                from aethon.agent.hooks.post_edit_verify import (
                    PostEditVerifyHookProvider,
                )

                verify_hook = PostEditVerifyHookProvider(
                    config=rel_cfg, workspace=self.config.paths.workspace
                )
                hooks.append(verify_hook)
            except Exception as e:
                # Reliability hooks are the safety net — escalate, don't whisper.
                logger.error(f"PostEditVerify startup error: {e}")
        if rel_cfg and rel_cfg.completion_gate:
            try:
                from aethon.agent.hooks.completion_gate import (
                    CompletionGateHookProvider,
                )

                hooks.append(
                    CompletionGateHookProvider(
                        config=rel_cfg, verify_hook=verify_hook
                    )
                )
            except Exception as e:
                logger.error(f"CompletionGate startup error: {e}")
        # TelemetryHook
        if self._telemetry_hook:
            hooks.append(self._telemetry_hook)
        # SessionRecorderHook (after telemetry, before approval)
        if self._session_recorder_hook:
            hooks.append(self._session_recorder_hook)
        # ApprovalHook — active when globally enabled, or when use_computer (a
        # high-risk capability) is enabled with require_approval.
        caps = getattr(self.config, "capabilities", None)
        computer_cfg = getattr(caps, "computer", None) if caps else None
        computer_needs_approval = bool(
            computer_cfg and computer_cfg.enabled and computer_cfg.require_approval
        )
        if self.config.approval.enabled or computer_needs_approval:
            try:
                from aethon.agent.hooks.approval import ApprovalHookProvider

                req = (
                    set(self.config.approval.requires_approval)
                    if self.config.approval.enabled
                    else set()
                )
                if computer_needs_approval:
                    req.add("use_computer")
                hooks.append(
                    ApprovalHookProvider(
                        list(req),
                        macos=getattr(self.config, "macos", None),
                        computer=computer_cfg,
                    )
                )
                logger.info("ApprovalHook: active")
            except Exception as e:
                # A failed safety gate must not vanish silently.
                logger.error(f"ApprovalHook startup error: {e}")
        return hooks

    def get_tools_schemas(self) -> dict:
        """Return ``{tool_name: {"description", "inputSchema"}}`` for every tool.

        Used by the MCP server to advertise AETHON's tools to external clients.
        Schemas come from a Strands tool registry, so decorated and module tools
        are normalized uniformly.
        """
        agent = Agent(model=self.model, tools=self._get_tools(), callback_handler=None)
        schemas: dict = {}
        for name, spec in agent.tool_registry.get_all_tools_config().items():
            input_schema = spec.get("inputSchema") or {}
            json_schema = (
                input_schema.get("json", {}) if isinstance(input_schema, dict) else {}
            )
            schemas[name] = {
                "description": spec.get("description", "") or "",
                "inputSchema": json_schema or {"type": "object", "properties": {}},
            }
        return schemas

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
            self._completion_gates.pop(evicted_id, None)
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

        hooks = self._get_hooks()
        self.agents[session_id] = Agent(
            model=self.model,
            system_prompt=system_prompt,
            tools=self._get_tools(),
            session_manager=session_mgr,
            conversation_manager=conv_mgr,
            hooks=hooks,
            agent_id="main",
            name="AETHON",
            # Don't let Strands print to stdout — each channel renders the reply itself
            # (otherwise the CLI shows every answer twice).
            callback_handler=None,
        )
        # Track this session's CompletionGate so _try_process can gate the reply.
        try:
            from aethon.agent.hooks.completion_gate import CompletionGateHookProvider

            for hook in hooks:
                if isinstance(hook, CompletionGateHookProvider):
                    self._completion_gates[session_id] = hook
                    break
        except ImportError:
            pass
        # Inject config so config-aware tools (e.g. manage_tools) can read their gates,
        # and the session id so telemetry maps activity to the dashboard pixel office.
        self.agents[session_id].__aethon_config__ = self.config
        self.agents[session_id].__aethon_session__ = session_id

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
            self._refresh_volatile_prompt(agent, session_id)
            result = agent(message.text)
            response = self._extract_text(result)
            return self._apply_completion_gate(agent, session_id, response)

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

    def _refresh_volatile_prompt(self, agent, session_id: str) -> None:
        """R10: recompose the system prompt before each turn.

        compose() otherwise runs once per cached agent, so CONTEXT.md /
        task-ledger / handoff updates never surface mid-session.
        """
        prompt_cfg = getattr(self.config, "prompt", None)
        if prompt_cfg is not None and not getattr(
            prompt_cfg, "refresh_per_turn", True
        ):
            return
        try:
            agent.system_prompt = self.prompt_composer.compose(session_id)
        except Exception as e:
            logger.warning(f"Prompt refresh error: {e}")

    @staticmethod
    def _extract_text(result) -> str:
        """Extract plain text from an agent invocation result."""
        try:
            content = result.message["content"]
            text_parts = [block["text"] for block in content if "text" in block]
            return "\n".join(text_parts) if text_parts else str(result)
        except (KeyError, TypeError, IndexError):
            return str(result)

    def _apply_completion_gate(self, agent, session_id: str, response: str) -> str:
        """R6: a success claim with no verification evidence doesn't return clean.

        Advisory mode appends the gate's Definition-of-Done reminder to the
        reply; strict mode re-prompts the agent once to verify or retract.
        """
        gate = self._completion_gates.get(session_id)
        if gate is None:
            return response
        note = gate.consume_note()
        if not note:
            return response

        rel = getattr(self.config, "reliability", None)
        if rel is not None and rel.strict:
            try:
                follow_up = agent(
                    f"{note}\nVerify the claim now by running the relevant "
                    f"checks, or explicitly retract it."
                )
                gate.consume_note()  # don't carry a second nag into next turn
                return response + "\n\n" + self._extract_text(follow_up)
            except Exception as e:
                logger.warning(f"CompletionGate strict re-prompt failed: {e}")
                return response + "\n\n" + note
        return response + "\n\n" + note

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
        """Clear a session's message history (e.g. after a context-window overflow) so the
        next turn starts fresh. The old messages are MOVED to a ``cleared/batch_N`` backup
        (not deleted) so nothing is lost; long-term memory and CONTEXT.md are unaffected."""
        sessions_dir = Path(self.config.session.storage_dir).expanduser()
        agent_dir = sessions_dir / f"session_{session_id}" / "agents" / "agent_main"
        messages_dir = agent_dir / "messages"
        if not messages_dir.exists():
            self.agents.pop(session_id, None)
            self._completion_gates.pop(session_id, None)
            return
        files = sorted(messages_dir.glob("message_*.json"))
        if files:
            # R11: distill a checkpoint to HANDOFF.md BEFORE clearing, so a
            # reset doesn't wipe live orientation (read back as a prompt layer).
            self._write_reset_checkpoint(session_id, files)
            try:
                backup_root = agent_dir / "cleared"
                backup_root.mkdir(exist_ok=True)
                batch = backup_root / f"batch_{len(list(backup_root.glob('batch_*')))}"
                batch.mkdir()
                for f in files:
                    f.rename(batch / f.name)  # preserve history for recovery
            except Exception:
                for f in files:
                    try:
                        f.unlink()
                    except Exception:
                        pass
        self.agents.pop(session_id, None)
        self._completion_gates.pop(session_id, None)

    def _write_reset_checkpoint(self, session_id: str, files: list) -> None:
        """Append a compact state checkpoint to workspace/HANDOFF.md.

        Mechanical distillation (no model call): the last user message and the
        tail of the last assistant reply — enough to re-orient after a reset.
        Only the most recent checkpoints are kept.
        """
        import json as _json

        def _last_text(role: str) -> str:
            for path in reversed(files):
                try:
                    msg = _json.loads(path.read_text(encoding="utf-8")).get(
                        "message", {}
                    )
                    if msg.get("role") != role:
                        continue
                    texts = [
                        b["text"] for b in msg.get("content", []) if "text" in b
                    ]
                    if texts:
                        return "\n".join(texts).strip()
                except Exception:
                    continue
            return ""

        try:
            from datetime import datetime

            user_text = _last_text("user")[:500]
            assistant_text = _last_text("assistant")[-500:]
            checkpoint = (
                f"### Checkpoint {datetime.now().isoformat(timespec='seconds')}"
                f" — session {session_id} (history reset)\n"
                f"- Last user message: {user_text or '(none)'}\n"
                f"- Last assistant reply (tail): {assistant_text or '(none)'}\n"
            )

            handoff = Path(self.config.paths.workspace).expanduser() / "HANDOFF.md"
            existing = (
                handoff.read_text(encoding="utf-8") if handoff.exists() else ""
            )
            sections = [
                s for s in existing.split("### ") if s.strip()
            ]
            kept = sections[-4:]  # keep the last few checkpoints, never grow unbounded
            body = "".join(f"### {s}" for s in kept) + "\n" + checkpoint
            handoff.write_text(body.strip() + "\n", encoding="utf-8")
            logger.info(f"Reset checkpoint written to HANDOFF.md ({session_id})")
        except Exception as e:
            logger.warning(f"Reset checkpoint write failed ({session_id}): {e}")

    async def process(self, message: InboundMessage, session_id: str) -> str:
        """Process message asynchronously.

        Strands Agent.__call__() is synchronous, so we run it in a thread executor
        to avoid blocking the asyncio event loop.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._process_sync, message, session_id
        )
