"""Tests for the MCP server exposure (aethon mcp)."""

import pytest

from aethon.config import (
    AethonConfig, PathsConfig, ModelConfig, MemoryConfig, MCPConfig, ApprovalConfig,
)
from aethon.agent.runtime import AethonRuntime
from aethon.tools.mcp_server import build_server, _extract_text
from mcp.shared.memory import create_connected_server_and_client_session as connect


def _runtime(tmp_path, approval=None):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "SOUL.md").write_text("x")
    kwargs = dict(
        model=ModelConfig(provider="fake", model_id="fake"),
        memory=MemoryConfig(enabled=False),
        mcp=MCPConfig(enabled=False),
        paths=PathsConfig(
            workspace=str(workspace),
            sessions=str(tmp_path / "s"),
            logs=str(tmp_path / "l"),
            memory_db=str(tmp_path / "m.sqlite"),
            credentials=str(tmp_path / "c"),
        ),
    )
    if approval is not None:
        kwargs["approval"] = approval
    return AethonRuntime(AethonConfig(**kwargs))


def test_extract_text():
    assert _extract_text({"status": "success", "content": [{"text": "hi"}]}) == "hi"
    assert _extract_text({"status": "error", "content": [{"text": "boom"}]}).startswith("[error]")
    assert _extract_text("plain") == "plain"


def test_get_tools_schemas(tmp_path):
    schemas = _runtime(tmp_path).get_tools_schemas()
    # Decorated tools and module tools alike are present.
    for name in ("scraper", "notify", "shell"):
        assert name in schemas
        assert schemas[name]["inputSchema"].get("type") == "object"


@pytest.mark.asyncio
async def test_list_tools(tmp_path):
    server = build_server(_runtime(tmp_path))
    async with connect(server) as client:
        names = {t.name for t in (await client.list_tools()).tools}
    assert {"scraper", "notify", "jsonrpc", "shell"} <= names


@pytest.mark.asyncio
async def test_call_tool_dispatch(tmp_path):
    server = build_server(_runtime(tmp_path))
    async with connect(server) as client:
        res = await client.call_tool(
            "scraper",
            {"action": "extract_text", "content": "<html><body><h1>Hi</h1></body></html>"},
        )
    assert res.isError is False
    assert "".join(getattr(c, "text", "") for c in res.content)


@pytest.mark.asyncio
async def test_security_block_over_mcp(tmp_path):
    server = build_server(_runtime(tmp_path))
    async with connect(server) as client:
        res = await client.call_tool("shell", {"command": "sudo ls"})
    assert "BLOCKED" in "".join(getattr(c, "text", "") for c in res.content)


@pytest.mark.asyncio
async def test_approval_denied_over_mcp(tmp_path):
    runtime = _runtime(
        tmp_path, approval=ApprovalConfig(enabled=True, requires_approval=["shell"])
    )
    server = build_server(runtime)
    async with connect(server) as client:
        res = await client.call_tool("shell", {"command": "echo hi"})
    text = "".join(getattr(c, "text", "") for c in res.content)
    assert "DENIED" in text and "approval" in text.lower()
