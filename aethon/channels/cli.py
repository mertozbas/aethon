"""CLI channel adapter.

Terminal-based chat interface using prompt_toolkit and rich.
"""

import asyncio
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from rich.console import Console
from rich.markdown import Markdown

from aethon.channels.base import ChannelAdapter, InboundMessage, OutboundMessage


class CLIAdapter(ChannelAdapter):
    """Terminal-based chat interface."""

    def __init__(self, config, router):
        super().__init__(config, router)
        self.console = Console()
        self.running = False

        history_path = Path("~/.aethon/cli_history").expanduser()
        history_path.parent.mkdir(parents=True, exist_ok=True)
        self.prompt_session = PromptSession(
            history=FileHistory(str(history_path))
        )

    async def start(self) -> None:
        """Start CLI input loop."""
        self.running = True
        self.console.print("[bold cyan]AETHON[/] is ready. Type 'exit' to quit.\n")

        while self.running:
            try:
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.prompt_session.prompt("you > ")
                )

                if not user_input or not user_input.strip():
                    continue

                if user_input.strip().lower() in ("exit", "quit", "q"):
                    self.console.print("[dim]See you![/]")
                    self.running = False
                    break

                inbound = InboundMessage(
                    channel="cli",
                    sender_id="local",
                    sender_name="User",
                    text=user_input.strip(),
                )

                self.console.print("[dim]Thinking...[/]")

                try:
                    response = await self.router.handle(inbound)

                    if response:
                        self.console.print()
                        self.console.print(Markdown(response.text))
                        self.console.print()
                except Exception as e:
                    self.console.print(f"\n[red]ERROR:[/] {type(e).__name__}: {e}\n")

            except (KeyboardInterrupt, EOFError):
                self.console.print("\n[dim]See you![/]")
                self.running = False
                break

    async def stop(self) -> None:
        self.running = False

    async def send(self, message: OutboundMessage) -> None:
        """Display message in terminal."""
        self.console.print(Markdown(message.text))
