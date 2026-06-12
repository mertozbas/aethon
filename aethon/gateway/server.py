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
        """Start all enabled channel adapters under supervision.

        Registers SIGINT/SIGTERM handlers for graceful shutdown. Each adapter
        runs under a supervisor (H3): a crash is logged with traceback and
        restarted with backoff, degrading only that channel on permanent failure
        — one broken channel never tears down the gateway. Waits until a signal
        arrives or the interactive CLI exits.
        """
        # Channels that permanently failed (surfaced like Phase 8 _degraded_hooks).
        self._degraded_channels: list[str] = []
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
        # Clear any sandbox containers leaked by a previously-crashed run.
        if getattr(self.runtime, "_sandbox", None):
            self.runtime._sandbox.reap_orphans()

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
            logger.info(
                f"WebChat: http://{self.config.channels.webchat.host}:"
                f"{self.config.channels.webchat.port}"
            )

        if self.config.channels.cli.enabled:
            self.adapters["cli"] = CLIAdapter(self.config, self.router)
            logger.info("CLI: active")

        # Telegram
        if self.config.channels.telegram.enabled:
            try:
                from aethon.channels.telegram import TelegramAdapter

                self.adapters["telegram"] = TelegramAdapter(
                    self.config, self.router
                )
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
                # Restore runtime-added jobs persisted to SCHEDULE.json (H4),
                # recovering any one-shots missed while AETHON was down.
                self._scheduler.load_persisted()
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

        if not self.adapters:
            raise RuntimeError("No channels are enabled!")

        # Register signal handlers within the running event loop
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self._signal_handler)

        # Launch each adapter under a supervisor (H3) — a crash restarts that
        # channel with backoff instead of tearing down the gateway.
        self._tasks = [
            asyncio.create_task(self._supervise(name, adapter))
            for name, adapter in self.adapters.items()
        ]

        # Run until a shutdown signal (or the CLI exiting, which the supervisor
        # turns into a shutdown) OR every channel has ended/degraded (nothing
        # left to serve). A network bot looping forever keeps the gateway up.
        shutdown_task = asyncio.create_task(self._shutdown_event.wait())
        supervisors_done = asyncio.gather(*self._tasks)
        await asyncio.wait(
            {shutdown_task, supervisors_done},
            return_when=asyncio.FIRST_COMPLETED,
        )
        await self.shutdown()

    # Adapter supervision (H3): retry budget + backoff ceiling.
    _MAX_CHANNEL_RETRIES = 5
    _BACKOFF_CEILING = 30.0

    async def _supervise(self, name: str, adapter) -> None:
        """Keep one channel alive: log crashes with traceback, restart with
        exponential backoff, degrade the channel after the retry budget — never
        the whole gateway."""
        delay = 1.0
        attempt = 0
        while not self._shutdown_event.is_set():
            try:
                await adapter.start()
                # Clean return. The interactive CLI returning means the user
                # quit → bring the gateway down. A network bot looping forever
                # shouldn't return; if it does, just end that channel.
                if name == "cli":
                    self._shutdown_event.set()
                return
            except asyncio.CancelledError:
                raise
            except Exception as e:
                attempt += 1
                logger.error(
                    f"Channel '{name}' crashed (attempt {attempt}): "
                    f"{type(e).__name__}: {e}",
                    exc_info=True,
                )
                if attempt > self._MAX_CHANNEL_RETRIES:
                    self._degraded_channels.append(name)
                    logger.error(
                        f"Channel '{name}' DEGRADED — gave up after "
                        f"{attempt} attempts. The rest of AETHON keeps running."
                    )
                    return
                try:
                    await asyncio.sleep(delay)
                except asyncio.CancelledError:
                    raise
                delay = min(delay * 2, self._BACKOFF_CEILING)

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
