"""Expose AETHON's tools to MCP clients (e.g. Claude Desktop) over stdio.

``aethon mcp`` builds the runtime's tool set, wraps each Strands tool as an MCP
tool (schema taken from its ``tool_spec``), and serves them over stdio. Every
call is routed through AETHON's ``SecurityHookProvider`` (hard block); tools that
would require interactive approval are denied, since stdio has no
human-in-the-loop approval channel.

Requires the ``mcp`` extra (``pip install aethon-ai[mcp]``).
"""

import logging

logger = logging.getLogger("aethon.mcp")


class _GateEvent:
    """Minimal stand-in for BeforeToolCallEvent so AETHON's hooks can be reused."""

    def __init__(self, name: str, arguments: dict):
        self.tool_use = {"name": name, "input": arguments or {}}
        self.cancel_tool = None
        self.interrupted = False

    def interrupt(self, **kwargs) -> None:
        self.interrupted = True


def _extract_text(result) -> str:
    """Render a Strands tool result (or anything) as plain text for MCP."""
    if isinstance(result, dict):
        content = result.get("content")
        if isinstance(content, list):
            parts = [
                b.get("text", "")
                for b in content
                if isinstance(b, dict) and b.get("text")
            ]
            text = "\n".join(p for p in parts if p)
            status = result.get("status")
            if status and status != "success":
                return f"[{status}] {text}" if text else f"[{status}]"
            return text or str(result)
        return str(result)
    return str(result)


def _find_hook(hooks: list, class_name: str):
    return next((h for h in hooks if h.__class__.__name__ == class_name), None)


def build_server(runtime):
    """Build (without running) an MCP ``Server`` exposing the runtime's tools.

    A lightweight Strands ``Agent`` is constructed purely to normalize tool specs
    (across decorated and module tools) and to invoke them through AETHON's hook
    chain — so the SecurityHookProvider runs automatically and a blocked call
    comes back as an error result. Interactive approval has no channel over stdio,
    so approval-required calls are denied up front. Returns a ``mcp.server.Server``.
    """
    from strands import Agent
    from mcp.server import Server
    import mcp.types as types

    hooks = runtime._get_hooks()
    agent = Agent(
        model=runtime.model,
        tools=runtime._get_tools(),
        hooks=hooks,
        callback_handler=None,
    )
    # Config-aware tools (e.g. manage_tools) read their gates from this.
    agent.__aethon_config__ = runtime.config
    approval = _find_hook(hooks, "ApprovalHookProvider")

    specs: list = []
    for name, spec in agent.tool_registry.get_all_tools_config().items():
        input_schema = spec.get("inputSchema") or {}
        json_schema = (
            input_schema.get("json", {}) if isinstance(input_schema, dict) else {}
        ) or {"type": "object", "properties": {}}
        specs.append(
            types.Tool(
                name=name,
                description=spec.get("description", "") or "",
                inputSchema=json_schema,
            )
        )
    valid_names = {s.name for s in specs}

    server = Server("aethon")

    @server.list_tools()
    async def _list_tools():
        return specs

    @server.call_tool()
    async def _call_tool(name: str, arguments: dict):
        if name not in valid_names:
            return [types.TextContent(type="text", text=f"Unknown tool: {name}")]
        args = arguments or {}

        # Approval gate — no interactive channel over stdio, so deny rather than
        # hang on an interrupt that can never be answered.
        if approval is not None:
            ev = _GateEvent(name, args)
            try:
                approval.check_approval(ev)
            except Exception:
                pass
            if ev.interrupted:
                return [
                    types.TextContent(
                        type="text",
                        text=(
                            f"DENIED: '{name}' requires interactive approval, which is "
                            f"unavailable over MCP. Disable the approval hook or call it "
                            f"through an AETHON channel."
                        ),
                    )
                ]

        # Invoke through the agent — the SecurityHookProvider runs here, so a
        # blocked call returns an error result rather than executing.
        # Some tools print rich output to stdout; over stdio that is the JSON-RPC
        # protocol stream, so divert any stray stdout to stderr during the call.
        import contextlib
        import sys

        try:
            with contextlib.redirect_stdout(sys.stderr):
                result = getattr(agent.tool, name)(**args)
        except Exception as e:
            logger.warning(f"MCP tool {name} error: {type(e).__name__}: {e}")
            return [
                types.TextContent(type="text", text=f"Error: {type(e).__name__}: {e}")
            ]
        return [types.TextContent(type="text", text=_extract_text(result))]

    return server


def run_mcp_server(config_path: str = "~/.aethon/config.yaml") -> None:
    """Load config, build the runtime, and serve tools over MCP stdio (blocks).

    NOTE: stdio is the MCP transport — nothing may be written to stdout here.
    """
    import asyncio

    from aethon.config import AethonConfig
    from aethon.agent.runtime import AethonRuntime

    config = AethonConfig.load(config_path)
    runtime = AethonRuntime(config)
    server = build_server(runtime)
    logger.info("MCP server starting (stdio)")

    async def _serve():
        from mcp.server.stdio import stdio_server

        async with stdio_server() as (read, write):
            await server.run(read, write, server.create_initialization_options())

    asyncio.run(_serve())
