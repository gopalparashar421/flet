"""Tests for server ping and tool listing."""

import pytest


@pytest.mark.anyio
async def test_ping_tool(mcp_client):
    async with mcp_client:
        result = await mcp_client.call_tool("ping", {})
        assert result.data["status"] == "ok"


@pytest.mark.anyio
async def test_list_tools(mcp_client):
    async with mcp_client:
        tools = await mcp_client.list_tools()
        tool_names = {t.name for t in tools}
        assert "ping" in tool_names
        assert "search_docs" in tool_names
        assert "get_control_schema" in tool_names
        assert "list_controls" in tool_names
        assert "validate_snippet" in tool_names
        assert "search_examples" in tool_names
        assert "get_example" in tool_names
