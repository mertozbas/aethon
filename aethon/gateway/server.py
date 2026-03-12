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


logger = logging.getLogger("aethon.gateway")


class AethonGateway:
    """Main AETHON gateway server."""

    def __init__(self, config: AethonConfig):
        self.config = config
        self.runtime = AethonRuntime(config)
        self.router = MessageRouter(config, self.runtime)
        self.adapters: dict[str, object] = {}
        self._tasks: list[asyncio.Task] = []
        self._shutdown_event = asyncio.Event()

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
        """Gracefully stop all adapters and cancel remaining tasks."""
        logger.info("AETHON kapatiliyor...")

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
