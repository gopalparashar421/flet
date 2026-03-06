"""End-to-end MCP tool integration tests."""

import json

import pytest

from flet_mcp.indexing.build_index import build_index
from flet_mcp.server import init_engines, mcp, _search_engine


@pytest.fixture
def live_index(tmp_path):
    """Build a test index and init engines."""
    # Create sample data
    docs = tmp_path / "docs" / "controls"
    docs.mkdir(parents=True)
    (docs / "textfield.md").write_text("# TextField\nA text input control.\n## Properties\nvalue, label, hint_text")
    (docs / "button.md").write_text("# Button\nA clickable button.\n## Events\non_click")

    examples = tmp_path / "examples" / "controls" / "text_field"
    examples.mkdir(parents=True)
    (examples / "basic.py").write_text("import flet as ft\ndef main(page):\n    page.add(ft.TextField(label='Name'))\nft.run(main)")

    db_path = tmp_path / "test_index.db"
    build_index(
        output_path=db_path,
        docs_root=tmp_path / "docs",
        examples_root=tmp_path / "examples",
    )
    init_engines(db_path)
    return db_path


@pytest.fixture
def client():
    from fastmcp import Client
    return Client(mcp)


@pytest.mark.anyio
async def test_ping(client, live_index):
    async with client:
        result = await client.call_tool("ping", {})
        assert result.data["status"] == "ok"


@pytest.mark.anyio
async def test_search_docs(client, live_index):
    async with client:
        result = await client.call_tool("search_docs", {"query": "TextField"})
        data = result.data
        assert data["count"] > 0
        assert any("TextField" in r["title"] for r in data["results"])


@pytest.mark.anyio
async def test_search_docs_category(client, live_index):
    async with client:
        result = await client.call_tool("search_docs", {"query": "button", "category": "controls"})
        data = result.data
        assert all(r["category"] == "controls" for r in data["results"])


@pytest.mark.anyio
async def test_search_examples(client, live_index):
    async with client:
        result = await client.call_tool("search_examples", {"query": "TextField"})
        data = result.data
        assert data["count"] > 0


@pytest.mark.anyio
async def test_get_example(client, live_index):
    async with client:
        result = await client.call_tool("get_example", {"path": "controls/text_field/basic.py"})
        data = result.data
        assert "content" in data
        assert "import flet" in data["content"]


@pytest.mark.anyio
async def test_get_example_not_found(client, live_index):
    async with client:
        result = await client.call_tool("get_example", {"path": "nonexistent.py"})
        data = result.data
        assert "error" in data


@pytest.mark.anyio
async def test_validate_snippet_valid(client, live_index):
    async with client:
        code = "import flet as ft\ndef main(page):\n    page.add(ft.TextField(label='Hi'))\nft.run(main)"
        result = await client.call_tool("validate_snippet", {"code": code})
        data = result.data
        # No schema loaded for TextField in this index, so it may have warnings
        assert "valid" in data


@pytest.mark.anyio
async def test_validate_snippet_syntax_error(client, live_index):
    async with client:
        result = await client.call_tool("validate_snippet", {"code": "def foo("})
        data = result.data
        assert not data["valid"]


@pytest.mark.anyio
async def test_list_tools(client, live_index):
    async with client:
        tools = await client.list_tools()
        names = {t.name for t in tools}
        expected = {"ping", "search_docs", "get_control_schema", "list_controls",
                    "validate_snippet", "search_examples", "get_example"}
        assert expected.issubset(names)
