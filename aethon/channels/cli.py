"""CLI channel adapter.

Terminal-based chat interface using prompt_toolkit and rich.
"""

import asyncio
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from rich.console import Console
from rich.markdown import Markdown

from aethon.channels.base import (
    ApprovalRequest,
    ChannelAdapter,
    InboundMessage,
    OutboundMessage,
    build_error_reply,
)


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
                except Exception as e:
                    # H2: never silent — show a short localized error line.
                    response = build_error_reply(inbound, e)
                if response:
                    self.console.print()
                    self.console.print(Markdown(response.text))
                    self.console.print()

            except (KeyboardInterrupt, EOFError):
                self.console.print("\n[dim]See you![/]")
                self.running = False
                break

    async def stop(self) -> None:
        self.running = False

    async def send(self, message: OutboundMessage) -> None:
        """Display message in terminal."""
        self.console.print(Markdown(message.text))

    async def ask_approval(self, request: ApprovalRequest) -> bool:
        """Inline y/n approval on the terminal (Phase 9A / S6).

        Runs the blocking read on an executor thread so the gateway loop stays
        free. The turn owns the terminal at this point (the main input prompt
        has already returned the user's message), so a direct read is safe.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._blocking_approval, request)

    def _blocking_approval(self, request: ApprovalRequest) -> bool:
        self.console.print()
        self.console.print(f"[yellow]Onay gerekiyor:[/] {request.message}")
        if request.parameters:
            self.console.print(f"  [dim]{request.tool}: {request.parameters}[/]")
        try:
            answer = input("  Onayla? [e/h] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return False
        return answer in ("e", "evet", "y", "yes")
