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

    def __init__(self, config: AethonConfig):
        self.config = config
        self.runtime = AethonRuntime(config)
        self.event_bus = DashboardEventBus()
        self.router = MessageRouter(config, self.runtime, event_bus=self.event_bus)
        self.runtime._event_bus = self.event_bus
        # Wire event bus into telemetry hook for real-time dashboard events
        if self.runtime._telemetry_hook:
            self.runtime._telemetry_hook._event_bus = self.event_bus
        self.adapters: dict[str, object] = {}
        self._tasks: list[asyncio.Task] = []
        self._shutdown_event = asyncio.Event()
        self._scheduler = None

        # Set global gateway reference for send_message tool
        from aethon.tools.messaging import set_gateway
        set_gateway(self)

    async def start(self):
        """Start all enabled channel adapters.

        Registers SIGINT/SIGTERM handlers for graceful shutdown.
        Waits until a signal arrives or any adapter exits (e.g. CLI 'exit').
        """
        coroutines = []

        if self.config.channels.webchat.enabled:
            self.adapters["webchat"] = WebChatAdapter(self.config, self.router)
            coroutines.append(self.adapters["webchat"].start())
            logger.info(
                f"WebChat: http://127.0.0.1:{self.config.channels.webchat.port}"
            )

        if self.config.channels.cli.enabled:
            self.adapters["cli"] = CLIAdapter(self.config, self.router)
            coroutines.append(self.adapters["cli"].start())
            logger.info("CLI: aktif")

        # Telegram
        if self.config.channels.telegram.enabled:
            try:
                from aethon.channels.telegram import TelegramAdapter

                self.adapters["telegram"] = TelegramAdapter(
                    self.config, self.router
                )
                coroutines.append(self.adapters["telegram"].start())
                logger.info("Telegram: aktif")
            except ImportError:
                logger.warning(
                    "Telegram: aiogram yuklu degil — pip install aethon[channels]"
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
                logger.info("Discord: aktif")
            except ImportError:
                logger.warning(
                    "Discord: discord.py yuklu degil — pip install aethon[channels]"
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
                logger.info("Slack: aktif")
            except ImportError:
                logger.warning(
                    "Slack: slack-bolt yuklu degil — pip install aethon[channels]"
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
                logger.info("WhatsApp: aktif (deneysel)")
            except ImportError:
                logger.warning(
                    "WhatsApp: neonize yuklu degil — pip install neonize"
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
                    )
                set_scheduler(self._scheduler)
                self._scheduler.start()
                logger.info("Zamanlayici: aktif")
            except Exception as e:
                logger.warning(f"Zamanlayici hatasi: {e}")

        # Webhook support on WebChat app
        if self.config.webhook.enabled and "webchat" in self.adapters:
            try:
                from aethon.gateway.webhooks import setup_webhooks

                setup_webhooks(
                    self.adapters["webchat"].app,
                    self.router,
                    self.config.webhook.secret,
                )
                logger.info("Webhook: aktif")
            except Exception as e:
                logger.warning(f"Webhook hatasi: {e}")

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
                logger.info("Dashboard: aktif")
            except Exception as e:
                logger.warning(f"Dashboard hatasi: {e}")

        # Model warm-up
        if self.config.performance.model_warmup:
            try:
                self.runtime.warm_up()
            except Exception as e:
                logger.warning(f"Warm-up hatasi: {e}")

        if not coroutines:
            raise RuntimeError("Hicbir kanal etkin degil!")

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
        logger.info("AETHON kapatiliyor...")

        # Stop scheduler
        if self._scheduler:
            try:
                self._scheduler.stop()
                logger.info("Zamanlayici durduruldu")
            except Exception as e:
                logger.warning(f"Zamanlayici durdurma hatasi: {e}")

        # Stop MCP clients
        if self.runtime._mcp_loader:
            try:
                self.runtime._mcp_loader.stop()
                logger.info("MCP sunuculari durduruldu")
            except Exception as e:
                logger.warning(f"MCP durdurma hatasi: {e}")

        # Stop each adapter with a timeout
        for name, adapter in self.adapters.items():
            try:
                await asyncio.wait_for(adapter.stop(), timeout=5.0)
                logger.info(f"Kapatildi: {name}")
            except asyncio.TimeoutError:
                logger.warning(f"Zaman asimi: {name}")
            except Exception as e:
                logger.warning(f"Hata ({name}): {e}")

        # Cancel any remaining tasks
        for task in self._tasks:
            if not task.done():
                task.cancel()

        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

        self._tasks.clear()
        logger.info("AETHON kapatildi.")
