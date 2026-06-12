"""AETHON gateway server.

Manages channel adapters and coordinates startup/shutdown.
Uses signal handlers for graceful shutdown within the same event loop.
"""

import asyncio
import logging
import signal

from aethon.config import AethonConfig
from aethon.agent.runtime import AethonRuntime
from aethon.gateway.router import MessageRouter
from aethon.channels.cli import CLIAdapter
from aethon.channels.webchat import WebChatAdapter
from aethon.ui.event_bus import DashboardEventBus


logger = logging.getLogger("aethon.gateway")


class AethonGateway:
    """Main AETHON gateway server."""

    def __init__(self, config: AethonConfig, *, insecure_bind: bool = False):
        self.config = config
        # Skip the non-loopback-bind auth refusal (S4) — for deployments behind
        # their own authenticating reverse proxy. Never skips the webhook gate.
        self._insecure_bind = insecure_bind
        self.runtime = AethonRuntime(config)
        self.event_bus = DashboardEventBus()
        self.router = MessageRouter(config, self.runtime, event_bus=self.event_bus)
        self.runtime._event_bus = self.event_bus
        # Wire event bus into telemetry hook for real-time dashboard events
        if self.runtime._telemetry_hook:
            self.runtime._telemetry_hook._event_bus = self.event_bus
        # Session recorder (single instance shared across agents; may be None)
        self._recorder = self.runtime._session_recorder_hook
        # Ambient mode manager (opt-in; wired before any agent is created so its
        # tools register). Fully dormant unless config.ambient.enabled.
        self._ambient_manager = None
        if getattr(config, "ambient", None) and config.ambient.enabled:
            try:
                from aethon.agent.ambient import AmbientModeManager

                self._ambient_manager = AmbientModeManager(
                    self.runtime, config, self.event_bus
                )
                self.runtime._ambient_manager = self._ambient_manager
            except Exception as e:
                logger.warning(f"Ambient manager init error: {e}")
        self.adapters: dict[str, object] = {}
        self._tasks: list[asyncio.Task] = []
        self._shutdown_event = asyncio.Event()
        self._scheduler = None
        # The gateway event loop — set in start(). Lets worker threads (tool
        # executor) dispatch sends onto the loop the adapters live on and wait
        # for the real outcome (see aethon/tools/messaging.py).
        self.loop: asyncio.AbstractEventLoop | None = None

        # Set global gateway reference for send_message tool
        from aethon.tools.messaging import set_gateway
        set_gateway(self)

    async def start(self):
        """Start all enabled channel adapters.

        Registers SIGINT/SIGTERM handlers for graceful shutdown.
        Waits until a signal arrives or any adapter exits (e.g. CLI 'exit').
        """
        coroutines = []
        self.loop = asyncio.get_running_loop()

        # Fail closed BEFORE any side effect (recorder, adapters, scheduler):
        # an exposed bind without auth must never come up (Phase 9A / S4).
        from aethon.gateway.netsec import (
            allowlist_gaps, check_bind_security, check_sandbox,
        )

        bind_ok, bind_msg = check_bind_security(self.config)
        if not bind_ok:
            if not self._insecure_bind:
                raise RuntimeError(bind_msg)
            logger.warning(f"--insecure-bind: {bind_msg}")

        # Fail closed when the docker sandbox is configured but unavailable (S7).
        sandbox_ok, sandbox_msg = check_sandbox(self.config)
        if not sandbox_ok:
            raise RuntimeError(sandbox_msg)

        # Default-deny senders (S5): a bot without an allowlist rejects ALL
        # senders — safe, but shout the exact config key at boot, not silence.
        for channel in allowlist_gaps(self.config):
            logger.error(
                f"{channel}: enabled with an EMPTY allowlist — every sender "
                f"will be rejected. Add allowed sender ids to "
                f"security.allowed_senders.{channel} in config.yaml."
            )

        # Start session recording (if enabled) before any channels accept messages.
        if self._recorder:
            try:
                self._recorder.start_recording()
                logger.info("Session recording started")
            except Exception as e:
                logger.warning(f"Session recording start error: {e}")

        # Bind the ambient manager to the running loop; auto-start only if configured.
        if self._ambient_manager:
            try:
                self._ambient_manager.set_loop(asyncio.get_running_loop())
                if getattr(self.config.ambient, "auto_start", False):
                    await self._ambient_manager.start()
                    logger.info("Ambient mode auto-started")
            except Exception as e:
                logger.warning(f"Ambient start error: {e}")

        if self.config.channels.webchat.enabled:
            self.adapters["webchat"] = WebChatAdapter(self.config, self.router)
            coroutines.append(self.adapters["webchat"].start())
            logger.info(
                f"WebChat: http://{self.config.channels.webchat.host}:"
                f"{self.config.channels.webchat.port}"
            )

        if self.config.channels.cli.enabled:
            self.adapters["cli"] = CLIAdapter(self.config, self.router)
            coroutines.append(self.adapters["cli"].start())
            logger.info("CLI: active")

        # Telegram
        if self.config.channels.telegram.enabled:
            try:
                from aethon.channels.telegram import TelegramAdapter

                self.adapters["telegram"] = TelegramAdapter(
                    self.config, self.router
                )
                coroutines.append(self.adapters["telegram"].start())
                logger.info("Telegram: active")
            except ImportError:
                logger.warning(
                    "Telegram: aiogram is not installed — pip install aethon[channels]"
                )
            except ValueError as e:
                logger.warning(f"Telegram: {e}")

        # Discord
        if self.config.channels.discord.enabled:
            try:
                from aethon.channels.discord_adapter import DiscordAdapter

                self.adapters["discord"] = DiscordAdapter(
                    self.config, self.router
                )
                coroutines.append(self.adapters["discord"].start())
                logger.info("Discord: active")
            except ImportError:
                logger.warning(
                    "Discord: discord.py is not installed — pip install aethon[channels]"
                )
            except ValueError as e:
                logger.warning(f"Discord: {e}")

        # Slack
        if self.config.channels.slack.enabled:
            try:
                from aethon.channels.slack_adapter import SlackAdapter

                self.adapters["slack"] = SlackAdapter(
                    self.config, self.router
                )
                coroutines.append(self.adapters["slack"].start())
                logger.info("Slack: active")
            except ImportError:
                logger.warning(
                    "Slack: slack-bolt is not installed — pip install aethon[channels]"
                )
            except ValueError as e:
                logger.warning(f"Slack: {e}")

        # WhatsApp (experimental)
        if self.config.channels.whatsapp.enabled:
            try:
                from aethon.channels.whatsapp import WhatsAppAdapter

                self.adapters["whatsapp"] = WhatsAppAdapter(
                    self.config, self.router
                )
                coroutines.append(self.adapters["whatsapp"].start())
                logger.info("WhatsApp: active (experimental)")
            except ImportError:
                logger.warning(
                    "WhatsApp: neonize is not installed — pip install neonize"
                )
            except ValueError as e:
                logger.warning(f"WhatsApp: {e}")

        # Scheduler
        if self.config.scheduler.enabled and self.runtime.sop_runner:
            try:
                from aethon.tools.scheduler import AethonScheduler, set_scheduler

                self._scheduler = AethonScheduler(
                    self.runtime.sop_runner,
                    self.runtime,
                    self.config.scheduler.default_channel,
                )
                # Load pre-configured jobs from config
                for job_id, job_cfg in self.config.scheduler.jobs.items():
                    self._scheduler.add_job(
                        job_id,
                        job_cfg.get("cron", "0 9 * * *"),
                        job_cfg.get("sop_name", ""),
                        job_cfg.get("channel", ""),
                        job_cfg.get("recipient", ""),
                    )
                set_scheduler(self._scheduler)
                self._scheduler.start()
                logger.info("Scheduler: active")
            except Exception as e:
                logger.warning(f"Scheduler error: {e}")

        # Webhook support on WebChat app
        if self.config.webhook.enabled and "webchat" in self.adapters:
            try:
                from aethon.gateway.webhooks import setup_webhooks

                if setup_webhooks(
                    self.adapters["webchat"].app,
                    self.router,
                    self.config.webhook.secret,
                    host=self.config.channels.webchat.host,
                ):
                    logger.info("Webhook: active")
            except Exception as e:
                logger.warning(f"Webhook error: {e}")

        # Dashboard on WebChat app
        if self.config.dashboard.enabled and "webchat" in self.adapters:
            try:
                from aethon.ui.dashboard import setup_dashboard

                setup_dashboard(
                    self.adapters["webchat"].app,
                    self.runtime,
                    self.config,
                    event_bus=self.event_bus,
                )
                logger.info("Dashboard: active")
            except Exception as e:
                logger.warning(f"Dashboard error: {e}")

        # Model warm-up
        if self.config.performance.model_warmup:
            try:
                self.runtime.warm_up()
            except Exception as e:
                logger.warning(f"Warm-up error: {e}")

        if not coroutines:
            raise RuntimeError("No channels are enabled!")

        # Register signal handlers within the running event loop
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self._signal_handler)

        # Launch all adapter coroutines as tasks
        self._tasks = [asyncio.create_task(c) for c in coroutines]
        shutdown_task = asyncio.create_task(self._shutdown_event.wait())

        # Wait until shutdown signal OR any adapter exits (e.g. CLI 'exit')
        done, _pending = await asyncio.wait(
            self._tasks + [shutdown_task],
            return_when=asyncio.FIRST_COMPLETED,
        )

        # Graceful shutdown
        await self.shutdown()

    def _signal_handler(self):
        """Called on SIGINT/SIGTERM — triggers graceful shutdown."""
        if not self._shutdown_event.is_set():
            logger.info("Received shutdown signal")
            self._shutdown_event.set()

    async def shutdown(self):
        """Gracefully stop all adapters, scheduler, and MCP clients."""
        logger.info("Shutting down AETHON...")

        # Stop ambient mode (if running)
        if self._ambient_manager:
            try:
                await self._ambient_manager.stop()
            except Exception as e:
                logger.warning(f"Ambient stop error: {e}")

        # Export the session recording (if active)
        if self._recorder:
            try:
                export_path = self._recorder.stop_and_export()
                if export_path:
                    logger.info(f"Session recording exported: {export_path}")
                    self.event_bus.emit(
                        "sessions",
                        {"event": "recording_exported", "path": export_path},
                    )
            except Exception as e:
                logger.warning(f"Session export error: {e}")

        # Stop scheduler
        if self._scheduler:
            try:
                self._scheduler.stop()
                logger.info("Scheduler stopped")
            except Exception as e:
                logger.warning(f"Scheduler stop error: {e}")

        # Stop MCP clients
        if self.runtime._mcp_loader:
            try:
                self.runtime._mcp_loader.stop()
                logger.info("MCP servers stopped")
            except Exception as e:
                logger.warning(f"MCP stop error: {e}")

        # Tear down sandbox containers (S7)
        if getattr(self.runtime, "_sandbox", None):
            try:
                self.runtime._sandbox.cleanup()
                logger.info("Sandbox containers removed")
            except Exception as e:
                logger.warning(f"Sandbox cleanup error: {e}")

        # Stop each adapter with a timeout
        for name, adapter in self.adapters.items():
            try:
                await asyncio.wait_for(adapter.stop(), timeout=5.0)
                logger.info(f"Stopped: {name}")
            except asyncio.TimeoutError:
                logger.warning(f"Timeout: {name}")
            except Exception as e:
                logger.warning(f"Error ({name}): {e}")

        # Let tasks finish gracefully first — adapter.stop() above already signalled
        # uvicorn via should_exit. Only force-cancel stragglers after a short grace
        # period; cancelling uvicorn mid-serve spews CancelledError tracebacks.
        if self._tasks:
            _done, pending = await asyncio.wait(self._tasks, timeout=3.0)
            for task in pending:
                task.cancel()
            if pending:
                await asyncio.gather(*pending, return_exceptions=True)

        self._tasks.clear()
        logger.info("AETHON shut down.")
