"""AETHON agent runtime.

Creates and manages Strands Agent instances per session.
"""

import asyncio
import concurrent.futures
import logging
import os
import platform
import threading
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
from aethon.channels.base import ApprovalRequest, InboundMessage


logger = logging.getLogger("aethon.runtime")

# Safety cap against a pathological tool that re-interrupts forever (S6).
MAX_INTERRUPT_ROUNDS = 25


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
            runtime_tools_enabled=getattr(
                getattr(config, "runtime_tools", None), "enabled", False
            ),
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
        # Execution sandbox (S7) — a per-session docker shell when enabled.
        self._sandbox = None
        if getattr(config.security, "sandbox", "none") == "docker":
            from aethon.tools.shell_sandbox import DockerSandbox

            self._sandbox = DockerSandbox(
                config.security, str(Path(config.paths.workspace).expanduser())
            )
            logger.info("Execution sandbox: docker")
        # Per-session CompletionGate instances (R6) — read after each turn so a
        # success claim with no verification evidence doesn't return clean.
        self._completion_gates: dict[str, object] = {}
        # Per-session turn locks (H1) — at most one turn per session_id at a
        # time, so two messages to one session can't race the same Agent and
        # corrupt its session file. Different sessions stay parallel. Created
        # lazily on the event loop; pruned (when unheld) as sessions are evicted.
        self._session_locks: dict[str, "asyncio.Lock"] = {}
        # Token measurement + budget ceiling (E0).
        from aethon.token_meter import TokenMeter

        self.token_meter = TokenMeter(getattr(config, "budget", None))
        # Guards the shared agent LRU (self.agents) — get_or_create_agent runs in
        # executor threads (different-session turns in parallel, H1) AND on the
        # loop thread (scheduler), so an asyncio lock can't protect it. A thread
        # lock keeps the check-then-act of the cache (and its pop sites) atomic so
        # concurrent distinct-session turns can't overflow the LRU or evict an
        # agent another thread is mid-invocation on (review fix).
        self._cache_lock = threading.RLock()

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
                    self.model,
                    session_config=config.session,
                    hooks_factory=self._get_specialist_hooks,
                    sandbox=self._sandbox,
                    workspace=config.paths.workspace,
                    allow_powerful=config.core_loop.allow_powerful_specialists,
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

        # Phase 10 C2: let ask_planner persist its structured plan into the
        # ledger as a project tree (multi-agent must be on for ask_planner). In
        # its OWN try/except — a wiring failure here must degrade only the
        # planner pipeline, never null the already-active ledger (review fix).
        if self._task_ledger is not None and config.multi_agent.enabled:
            try:
                from aethon.tools.delegate import set_plan_ledger

                set_plan_ledger(self._task_ledger, config.core_loop.plan_approval)
            except Exception as e:
                logger.warning(f"Planner→ledger wiring skipped: {e}")

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
            self._evict(session_id)
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
        self._evict(session_id)

    def _get_tools(self, session_id: str | None = None) -> list:
        """Tool list — includes memory, delegate, context, messaging, scheduler, MCP tools.

        When the docker sandbox is enabled (S7) and a session_id is given, the
        host `shell` is swapped for a per-session containerized shell.
        """
        shell_tool = shell
        if session_id is not None and self._sandbox is not None:
            from aethon.tools.shell_sandbox import make_sandboxed_shell

            shell_tool = make_sandboxed_shell(session_id, self._sandbox)
        tools = [file_read, file_write, editor, shell_tool, think, current_time]
        if self.memory:
            from aethon.tools.memory_tool import create_memory_tool

            tools.append(create_memory_tool(self.memory))
        if self.specialist_factory:
            from aethon.tools.delegate import (
                ask_coder, ask_researcher, ask_analyst, ask_planner, ask_scout,
                ask_specialist,
            )

            tools.extend([
                ask_coder, ask_researcher, ask_analyst, ask_planner, ask_scout,
                ask_specialist,
            ])
            # C5: dynamic specialist management (opt-in). ask_specialist (above)
            # can already reach any custom specialist; this tool creates them.
            if getattr(self.config.core_loop, "dynamic_specialists", False):
                from aethon.tools.specialist_tool import create_manage_specialists_tool

                tools.append(
                    create_manage_specialists_tool(
                        self.specialist_factory,
                        allow_powerful=self.config.core_loop.allow_powerful_specialists,
                    )
                )
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
        degraded_hooks: list[str] = []
        rel_cfg_iv = getattr(self.config, "reliability", None)
        if rel_cfg_iv is None or getattr(rel_cfg_iv, "input_validator", True):
            try:
                from aethon.agent.hooks.input_validator import (
                    InputValidatorHookProvider,
                )

                hooks.append(InputValidatorHookProvider())
            except Exception as e:
                degraded_hooks.append("InputValidator")
                logger.warning(f"InputValidator startup error: {e}")
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
                degraded_hooks.append("MemoryGuard")
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
                degraded_hooks.append("LSPDiagnostics")
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
                degraded_hooks.append("AnglicizationGuard")
                logger.warning(f"AnglicizationGuard startup error: {e}")
        # Reliability hooks (Phase 8): PostEditVerify (R7) + CompletionGate (R6).
        # E2 history compaction (Phase 10) — trim old, large tool outputs out of
        # the model's input each turn (opt-in). Registered before the model-call
        # guards so the compacted history is what they (and the model) see. This
        # lives in the MAIN agent hook list, so it covers the main + scheduler +
        # executor sessions but NOT specialists (they build via
        # _get_specialist_hooks) — the planner's structured output stays untouched.
        if getattr(self.config.session, "compact_enabled", False):
            try:
                from aethon.agent.hooks.compaction import CompactionHookProvider

                hooks.append(
                    CompactionHookProvider(
                        keep_last_n_turns=self.config.session.compact_keep_last_n_turns,
                        min_chars=self.config.session.compact_min_chars,
                        trigger_chars=self.config.session.compact_trigger_chars,
                    )
                )
            except Exception as e:
                degraded_hooks.append("Compaction")
                logger.warning(f"Compaction startup error: {e}")

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
                degraded_hooks.append("PostEditVerify")
                logger.error(f"PostEditVerify startup error: {e}")
        if rel_cfg and rel_cfg.completion_gate:
            if verify_hook is None and self._task_ledger is None:
                # Without any evidence source the gate can never fire — say
                # so loudly instead of registering a silently inert guard.
                logger.warning(
                    "CompletionGate skipped: it needs reliability."
                    "post_edit_verify or the task ledger as an evidence source."
                )
            else:
                try:
                    from aethon.agent.hooks.completion_gate import (
                        CompletionGateHookProvider,
                    )

                    hooks.append(
                        CompletionGateHookProvider(
                            config=rel_cfg,
                            verify_hook=verify_hook,
                            task_ledger=self._task_ledger,
                        )
                    )
                except Exception as e:
                    degraded_hooks.append("CompletionGate")
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
                degraded_hooks.append("Approval")
                logger.error(f"ApprovalHook startup error: {e}")
        # Untrusted-content marking (S9) — wrap external tool results in
        # [UNTRUSTED EXTERNAL CONTENT] markers. Registered just BEFORE the output
        # guard so (AfterToolCallEvent fires in REVERSE order) it runs AFTER
        # truncation — the markers wrap the final, capped text rather than being
        # truncated away.
        if getattr(self.config.security, "mark_untrusted_content", True):
            try:
                from aethon.agent.hooks.untrusted_content import (
                    UntrustedContentHookProvider,
                )

                hooks.append(UntrustedContentHookProvider())
            except Exception as e:
                degraded_hooks.append("UntrustedContent")
                logger.warning(f"UntrustedContent startup error: {e}")
        # Tool-output guard — cap oversized tool results before they reach the
        # model. Registered LAST on purpose: AfterToolCallEvent callbacks run
        # in REVERSE registration order, so this truncates the raw output
        # FIRST and the feedback appended by LSP/Verify/Telemetry survives.
        max_out = getattr(self.config.performance, "max_tool_output_chars", 0)
        if max_out and max_out > 0:
            try:
                from aethon.agent.hooks.output_guard import ToolOutputGuardHookProvider

                hooks.append(ToolOutputGuardHookProvider(max_chars=max_out))
            except Exception as e:
                degraded_hooks.append("ToolOutputGuard")
                logger.warning(f"ToolOutputGuard startup error: {e}")
        # R18: aggregate degraded hooks into one loud, greppable health record
        # (and keep it on the runtime for status surfacing).
        self._degraded_hooks = degraded_hooks
        if degraded_hooks:
            logger.error(
                f"Hook startup DEGRADED — running without: "
                f"{', '.join(degraded_hooks)}"
            )
        return hooks

    def _get_specialist_hooks(self) -> list:
        """Hooks for delegated specialist agents.

        Specialists edit files with their own tools; without these they
        bypass the security and reliability layer entirely. The
        CompletionGate is intentionally absent — its pending note is consumed
        by the runtime reply path, which specialists don't go through.
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
        try:
            from aethon.agent.hooks.input_validator import (
                InputValidatorHookProvider,
            )

            hooks.append(InputValidatorHookProvider())
        except Exception as e:
            logger.warning(f"Specialist InputValidator startup error: {e}")
        rel_cfg = getattr(self.config, "reliability", None)
        if rel_cfg is None or getattr(rel_cfg, "anglicization_guard", True):
            try:
                from aethon.agent.hooks.anglicization_guard import (
                    AnglicizationGuardHookProvider,
                )

                hooks.append(
                    AnglicizationGuardHookProvider(
                        strict=bool(getattr(rel_cfg, "strict", False))
                    )
                )
            except Exception as e:
                logger.warning(f"Specialist AnglicizationGuard startup error: {e}")
        if rel_cfg and rel_cfg.post_edit_verify:
            try:
                from aethon.agent.hooks.post_edit_verify import (
                    PostEditVerifyHookProvider,
                )

                hooks.append(
                    PostEditVerifyHookProvider(
                        config=rel_cfg, workspace=self.config.paths.workspace
                    )
                )
            except Exception as e:
                logger.error(f"Specialist PostEditVerify startup error: {e}")
        # Untrusted-content marking (S9) — the researcher fetches web content via
        # http_request; without this its results would reach the model unmarked.
        if getattr(self.config.security, "mark_untrusted_content", True):
            try:
                from aethon.agent.hooks.untrusted_content import (
                    UntrustedContentHookProvider,
                )

                hooks.append(UntrustedContentHookProvider())
            except Exception as e:
                logger.warning(f"Specialist UntrustedContent startup error: {e}")
        max_out = getattr(self.config.performance, "max_tool_output_chars", 0)
        if max_out and max_out > 0:
            try:
                from aethon.agent.hooks.output_guard import (
                    ToolOutputGuardHookProvider,
                )

                hooks.append(ToolOutputGuardHookProvider(max_chars=max_out))
            except Exception as e:
                logger.warning(f"Specialist ToolOutputGuard startup error: {e}")
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

    def get_or_create_agent(self, session_id: str, hint: str = "") -> Agent:
        """Get or create agent for a session.

        Uses LRU cache: moves accessed session to end, evicts oldest when full.
        Evicted sessions persist on disk via FileSessionManager. The whole
        check-then-act is under the cache lock so concurrent distinct-session
        turns (run in parallel on executor threads) can't overflow the LRU or
        evict an agent another thread is mid-invocation on (review fix).

        ``hint`` (the building message text) is used ONCE, when a fresh agent is
        built, to choose the capability diet (C6); a cached agent ignores it.
        """
        with self._cache_lock:
            if session_id in self.agents:
                self.agents.move_to_end(session_id)
                return self.agents[session_id]

            # Evict oldest if cache full
            if len(self.agents) >= self._session_cache_size:
                evicted_id, _ = self.agents.popitem(last=False)
                self._completion_gates.pop(evicted_id, None)
                _lk = self._session_locks.get(evicted_id)
                if _lk is not None and not _lk.locked():
                    self._session_locks.pop(evicted_id, None)
                logger.debug(f"Session evicted from cache: {evicted_id}")

            return self._build_agent(session_id, hint)

    def _evict(self, session_id: str) -> None:
        """Drop a session's cached agent + gate under the cache lock (review fix)."""
        with self._cache_lock:
            self.agents.pop(session_id, None)
        self._completion_gates.pop(session_id, None)

    def _build_agent(self, session_id: str, hint: str = ""):
        """Construct and cache a fresh Agent (called under the cache lock)."""
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
        tools = self._get_tools(session_id)
        # C6 capability diet: choose the heavy/domain tools once, from the message
        # that builds this agent, and keep that set stable for its lifetime (a
        # per-turn change would invalidate the provider's tool cache every turn).
        if getattr(self.config.core_loop, "capability_diet", False):
            from aethon.agent.capability_diet import select_tools

            tools = select_tools(tools, hint)
        self.agents[session_id] = Agent(
            model=self.model,
            system_prompt=system_prompt,
            tools=tools,
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
        # The prompt was composed just now — record the volatile-source
        # fingerprint so the first turn doesn't immediately recompose (R10).
        self.agents[session_id].__aethon_prompt_fp__ = self._volatile_fingerprint()

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
                    agent = self.get_or_create_agent(session_id, hint=message.text)
                    self._discard_stale_gate_note(session_id)
                    # R10 applies to SOP turns too — they were running
                    # against a stale system prompt on cached agents.
                    self._refresh_volatile_prompt(agent, session_id)
                    # Route SOP turns through the interrupt resolver too, so a
                    # gated tool inside a SOP asks for approval (or fails closed)
                    # rather than being silently dropped (S6).
                    sop_reply = self.sop_runner.run_sop(
                        sop_name, agent, sop_input,
                        invoke=lambda a, p: self._run_with_interrupts(
                            a, message, session_id, p
                        ),
                    )
                    # Meter SOP turns too (E0) — their usage accrued on the agent.
                    self._capture_usage(agent, None, session_id)
                    # Gate SOP replies too — otherwise a pending DoD note
                    # would leak into the next unrelated turn.
                    return self._apply_completion_gate(agent, session_id, sop_reply)

            # C1 intake (advisory, opt-in): a clear unit of work becomes a
            # planned project instead of a normal chat turn. Returns None (and
            # leaves the normal path untouched) for chat, when disabled, or if a
            # project can't actually be opened.
            intake_reply = self._maybe_intake(message, session_id)
            if intake_reply is not None:
                return intake_reply

            # Normal message processing
            agent = self.get_or_create_agent(session_id, hint=message.text)
            self._discard_stale_gate_note(session_id)
            self._refresh_volatile_prompt(agent, session_id)
            result = self._run_with_interrupts(agent, message, session_id, message.text)
            self._capture_usage(agent, result, session_id)
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

    def _run_with_interrupts(self, agent, message: InboundMessage, session_id: str, text):
        """Invoke the agent, resolving any approval interrupts (S6).

        strands stops the agent loop and returns ``stop_reason == "interrupt"``
        when the approval hook raises. We resolve each interrupt via the
        originating channel (fail-closed deny if it can't answer) and resume the
        agent with the decisions, looping until the turn completes.
        """
        result = agent(text)
        rounds = 0
        while getattr(result, "stop_reason", None) == "interrupt":
            rounds += 1
            if rounds > MAX_INTERRUPT_ROUNDS:
                logger.error(
                    f"Approval interrupt loop exceeded {MAX_INTERRUPT_ROUNDS} "
                    f"rounds ({message.channel}); denying the rest."
                )
                # Resume one last time denying everything so the turn can finish.
                result = agent(self._deny_all(result.interrupts))
                break
            responses = [
                {
                    "interruptResponse": {
                        "interruptId": itr.id,
                        "response": self._resolve_approval_decision(message, session_id, itr),
                    }
                }
                for itr in result.interrupts
            ]
            result = agent(responses)
        return result

    @staticmethod
    def _deny_all(interrupts) -> list:
        return [
            {
                "interruptResponse": {
                    "interruptId": itr.id,
                    "response": {"approved": False, "reason": "onay döngüsü iptal edildi."},
                }
            }
            for itr in interrupts
        ]

    def _resolve_approval_decision(
        self, message: InboundMessage, session_id: str, interrupt
    ) -> dict:
        """Ask the originating channel to approve a tool call; deny on any doubt.

        Returns the resume payload ``{"approved": bool, "reason": str}`` the
        approval hook reads. Fails closed (deny) when the channel can't answer,
        times out, or errors — never wedges the turn.
        """
        reason = interrupt.reason if isinstance(interrupt.reason, dict) else {}
        request = ApprovalRequest(
            interrupt_id=interrupt.id,
            tool=str(reason.get("tool", "")),
            parameters=reason.get("parameters", {}) or {},
            message=str(reason.get("message", "")),
            session_id=session_id,
            recipient_id=message.sender_id,
        )
        unanswerable = {
            "approved": False,
            "reason": (
                "Onay gerekli ama bu kanal yanıtlayamıyor — CLI/WebChat kullanın "
                "ya da approval'ı kapatın."
            ),
        }

        from aethon.tools.messaging import get_gateway

        gateway = get_gateway()
        adapter = gateway.adapters.get(message.channel) if gateway else None
        loop = getattr(gateway, "loop", None) if gateway else None
        ask = getattr(adapter, "ask_approval", None)
        if not (adapter and loop and loop.is_running() and callable(ask)):
            logger.warning(
                f"Approval can't be answered on {message.channel} — denying "
                f"({request.tool})."
            )
            return unanswerable

        timeout = getattr(self.config.approval, "timeout_seconds", 120.0)
        future = asyncio.run_coroutine_threadsafe(ask(request), loop)
        try:
            decision = future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            # run_coroutine_threadsafe(...).result() raises THIS, not
            # asyncio.TimeoutError (they are only aliased on Python ≥3.11; the
            # project floor is 3.10, where they are distinct classes).
            future.cancel()
            logger.warning(
                f"Approval timed out after {timeout}s on {message.channel} — "
                f"denying ({request.tool})."
            )
            return {"approved": False, "reason": "onay zaman aşımına uğradı."}
        except Exception as e:
            logger.error(f"Approval responder error ({message.channel}): {e}")
            return {"approved": False, "reason": "onay alınamadı."}

        if decision is None:
            return unanswerable
        if decision:
            return {"approved": True, "reason": ""}
        return {"approved": False, "reason": "kullanıcı reddetti."}

    def _capture_usage(self, agent, result, session_id: str) -> None:
        """Record the turn's token usage (E0). strands accumulates usage on the
        agent across its lifetime, so we diff against the last-seen total."""
        try:
            # SOP turns hand us no AgentResult, but usage accumulates on the
            # agent itself (result.metrics IS agent.event_loop_metrics), so fall
            # back to the agent's own metrics — otherwise SOP turns go unmetered
            # and their tokens silently inflate the next normal turn's diff.
            metrics = getattr(result, "metrics", None) or getattr(
                agent, "event_loop_metrics", None
            )
            usage = getattr(metrics, "accumulated_usage", None) if metrics else None
            if not usage:
                return
            cur_in = int(usage.get("inputTokens", 0) or 0)
            cur_out = int(usage.get("outputTokens", 0) or 0)
            prev_in, prev_out = getattr(agent, "__aethon_usage__", (0, 0))
            d_in = max(0, cur_in - prev_in)
            d_out = max(0, cur_out - prev_out)
            agent.__aethon_usage__ = (cur_in, cur_out)
            self.token_meter.record(
                d_in, d_out, model=self.config.model.model_id, session_id=session_id
            )
            if self.token_meter.near_budget() and not self.token_meter.over_budget():
                logger.warning(
                    f"Token budget at {self.token_meter.daily_cost():.2f} USD "
                    f"(ceiling {self.token_meter._ceiling:.2f}) — approaching limit."
                )
        except Exception as e:
            logger.debug(f"Usage capture skipped: {e}")

    def _maybe_intake(self, message: InboundMessage, session_id: str) -> str | None:
        """C1 intake: classify the message and, on a clear unit of work, open a
        planned project and return an acknowledgement + plan summary. Returns
        ``None`` to leave the normal turn path untouched — when intake is off,
        the message reads as chat, or a project can't be opened (no ledger /
        planner, or the planner produced nothing structured).

        Deliberately fail-safe: anything short of a confidently-opened project
        falls through to ordinary processing, so chat is never hijacked.
        """
        cfg = getattr(self.config, "core_loop", None)
        if cfg is None or not getattr(cfg, "intake_enabled", False):
            return None
        if self._task_ledger is None or getattr(self, "specialist_factory", None) is None:
            return None
        from aethon.agent.intake import classify_intake

        verdict = classify_intake(
            message.text,
            work_phrases=getattr(cfg, "intake_work_phrases", []),
            chat_phrases=getattr(cfg, "intake_chat_phrases", []),
        )
        if verdict != "work":
            return None

        from aethon.tools.delegate import plan_into_ledger

        # Remember where the work came from so C4 can pulse + deliver the receipt
        # back to this channel/sender.
        result = plan_into_ledger(
            message.text,
            origin_channel=message.channel,
            origin_recipient=message.sender_id,
        )
        if not result:
            # Classified as work but no project could be opened — don't claim to
            # have started one; let the normal turn answer instead.
            return None
        # Meter the planner's spend (E0): intake returns early, so without this
        # the planner's tokens would escape the budget ceiling. (Specialist
        # usage on the ask_* tool paths is still a broader, pending E0 gap.)
        try:
            self._capture_usage(
                self.specialist_factory.get("planner"), None, session_id
            )
        except Exception as e:
            logger.debug(f"Intake planner usage capture skipped: {e}")
        logger.info(f"Intake opened project {result.get('project_id')} from a work message.")
        ack = "Anladım — bunu bir iş olarak ele alıp planını çıkardım:"
        return f"{ack}\n\n{result['summary']}"

    def _discard_stale_gate_note(self, session_id: str) -> None:
        """Drop a gate note left over from an earlier turn.

        AfterInvocationEvent fires even when the turn later fails (strands
        runs it in a finally block), so a note set during a failed turn
        would otherwise attach to the next unrelated reply.
        """
        gate = self._completion_gates.get(session_id)
        if gate is not None and gate.consume_note():
            logger.debug(f"Stale completion-gate note discarded ({session_id})")

    # Volatile prompt sources watched for per-turn refresh (R10). aethon.log
    # is deliberately absent: it changes every turn, and recomposing for it
    # would make the prompt unique per turn — defeating provider prompt
    # caching for zero orientation value.
    _VOLATILE_PROMPT_FILES = (
        "CONTEXT.md", "TASKS.json", "HANDOFF.md", "LEARNINGS.md",
    )

    def _volatile_fingerprint(self) -> tuple:
        workspace = Path(self.config.paths.workspace).expanduser()
        fingerprint = []
        for name in self._VOLATILE_PROMPT_FILES:
            try:
                fingerprint.append((workspace / name).stat().st_mtime_ns)
            except OSError:
                fingerprint.append(None)
        return tuple(fingerprint)

    def _refresh_volatile_prompt(self, agent, session_id: str) -> None:
        """R10: recompose the system prompt when its volatile sources changed.

        compose() otherwise runs once per cached agent, so CONTEXT.md /
        task-ledger / handoff updates never surface mid-session. The mtime
        gate keeps the prompt byte-stable across unchanged turns so provider
        prompt caching stays effective.
        """
        prompt_cfg = getattr(self.config, "prompt", None)
        if prompt_cfg is not None and not getattr(
            prompt_cfg, "refresh_per_turn", True
        ):
            return
        fingerprint = self._volatile_fingerprint()
        if getattr(agent, "__aethon_prompt_fp__", None) == fingerprint:
            return
        try:
            agent.system_prompt = self.prompt_composer.compose(session_id)
            agent.__aethon_prompt_fp__ = fingerprint
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
            self._evict(session_id)
            return
        # Numeric sort — strands names files message_<int>.json unpadded, so
        # a lexicographic sort would order message_10 before message_9 and
        # the checkpoint would distill the wrong "last" messages.
        def _msg_index(path):
            stem = path.stem.removeprefix("message_")
            return (0, int(stem)) if stem.isdigit() else (1, stem)

        files = sorted(messages_dir.glob("message_*.json"), key=_msg_index)
        if files:
            # R11: distill a checkpoint to HANDOFF.md BEFORE clearing, so a
            # reset doesn't wipe live orientation (read back as a prompt layer).
            self._write_reset_checkpoint(session_id, files)
            try:
                backup_root = agent_dir / "cleared"
                backup_root.mkdir(exist_ok=True)
                batch = self._next_batch_dir(backup_root)
                for f in files:
                    f.rename(batch / f.name)  # preserve history for recovery
            except Exception as e:
                # Fail loud: the delete-instead-of-backup fallback exists only so
                # an overflow can still be recovered when the backup genuinely
                # can't be written — it must never be silent (it loses history).
                logger.error(
                    f"Session reset backup failed ({session_id}); clearing "
                    f"history without a recoverable backup to break the "
                    f"overflow: {type(e).__name__}: {e}"
                )
                for f in files:
                    try:
                        f.unlink()
                    except Exception:
                        pass
        self._evict(session_id)

    def _next_batch_dir(self, backup_root: Path) -> Path:
        """Allocate a fresh ``cleared/batch_N`` dir.

        Numbered by max-existing+1 (NOT count): retention prunes the
        lowest-numbered batches, so a count-based name shrinks after pruning and
        collides with a surviving ``batch_N`` — that collision used to raise and
        divert into the delete-instead-of-backup path, silently losing session
        history. The while-loop keeps the allocation collision-proof even if a
        same-numbered dir somehow already exists.
        """
        nums = [
            int(p.name.split("_")[-1])
            for p in backup_root.glob("batch_*")
            if p.is_dir() and p.name.split("_")[-1].isdigit()
        ]
        n = (max(nums) + 1) if nums else 0
        while True:
            batch = backup_root / f"batch_{n}"
            try:
                batch.mkdir()
                return batch
            except FileExistsError:
                n += 1

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
            import re as _re
            from datetime import datetime

            def _flatten(text: str) -> str:
                # Collapse newlines — checkpoint excerpts land in the system
                # prompt, and raw multi-line user text could fabricate prompt
                # layers or fake checkpoint headers.
                return _re.sub(r"\s+", " ", text).strip()

            user_text = _flatten(_last_text("user"))[:500]
            assistant_text = _flatten(_last_text("assistant"))[-500:]
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
            # Anchored split: only real checkpoint headers at line starts
            # count — '### ' inside an excerpt must not break the rotation.
            sections = [
                s for s in _re.split(r"(?m)^### Checkpoint ", existing)
                if s.strip()
            ]
            kept = sections[-4:]  # keep the last few checkpoints, never grow unbounded
            body = (
                "\n".join(f"### Checkpoint {s.strip()}" for s in kept)
                + "\n\n" + checkpoint
            )
            handoff.write_text(body.strip() + "\n", encoding="utf-8")
            logger.info(f"Reset checkpoint written to HANDOFF.md ({session_id})")
        except Exception as e:
            logger.warning(f"Reset checkpoint write failed ({session_id}): {e}")

    async def process(self, message: InboundMessage, session_id: str) -> str:
        """Process message asynchronously.

        Strands Agent.__call__() is synchronous, so we run it in a thread executor
        to avoid blocking the asyncio event loop. A per-session lock (H1) serializes
        turns for one session_id — concurrent same-session messages can't race the
        shared Agent / session file — while different sessions run in parallel.
        """
        # Budget ceiling (E0): once the daily spend is breached, block turns —
        # including ambient/scheduler turns, which run through here too.
        if self.token_meter.over_budget():
            logger.error(
                f"Daily token budget exceeded "
                f"({self.token_meter.daily_cost():.2f} USD ≥ "
                f"{self.token_meter._ceiling:.2f}) — turn blocked."
            )
            return self._budget_blocked_message(message)

        lock = self._session_locks.get(session_id)
        if lock is None:
            lock = asyncio.Lock()
            self._session_locks[session_id] = lock
        async with lock:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None, self._process_sync, message, session_id
            )

    def _budget_blocked_message(self, message: InboundMessage) -> str:
        """Localized 'budget exceeded' reply (E0)."""
        import re

        tr = bool(re.search(r"[çğışüöÇĞİŞÜÖ]", message.text or ""))
        spend = self.token_meter.daily_cost()
        ceiling = self.token_meter._ceiling
        if tr:
            return (
                f"Günlük token bütçesi aşıldı ({spend:.2f}$ ≥ {ceiling:.2f}$). "
                "Yarın sıfırlanır; acilse budget.daily_usd değerini artırın."
            )
        return (
            f"Daily token budget exceeded (${spend:.2f} ≥ ${ceiling:.2f}). "
            "It resets tomorrow; raise budget.daily_usd if you need more now."
        )
