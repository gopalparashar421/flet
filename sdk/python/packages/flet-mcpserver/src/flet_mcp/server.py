"""Flet MCP Server – exposes documentation, schemas, validation, and examples."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Optional

from fastmcp import FastMCP

from flet_mcp.engines.examples import ExamplesEngine
from flet_mcp.engines.schema import SchemaEngine
from flet_mcp.engines.search import SearchEngine
from flet_mcp.engines.validator import ValidatorEngine

mcp = FastMCP("Flet MCP Server")

# Lazy engine singletons — initialised via init_engines()
_search_engine: SearchEngine | None = None
_schema_engine: SchemaEngine | None = None
_validator_engine: ValidatorEngine | None = None
_examples_engine: ExamplesEngine | None = None


def init_engines(db_path: str | Path) -> None:
    """Initialise all engine singletons from a built index database."""
    global _search_engine, _schema_engine, _validator_engine, _examples_engine
    db_path = str(db_path)
    _search_engine = SearchEngine(db_path)
    _schema_engine = SchemaEngine(db_path)
    _validator_engine = ValidatorEngine(_schema_engine)
    _examples_engine = ExamplesEngine(db_path)


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def ping() -> dict:
    """Health check. Returns server status."""
    return {"status": "ok", "server": "Flet MCP Server"}


@mcp.tool()
def search_docs(
    query: str,
    category: Optional[str] = None,
    limit: int = 10,
) -> dict:
    """Search Flet documentation. Returns matching doc sections with highlighted snippets.

    Args:
        query: Search terms (e.g. "TextField validation", "navigation routing")
        category: Optional filter — one of: controls, types, services, cookbook, tutorials, etc.
        limit: Max results (1-50, default 10)
    """
    if _search_engine is None:
        return {"error": "Index not loaded. Run build_index first."}
    results = _search_engine.search(query, category=category, limit=limit)
    return {"results": [asdict(r) for r in results], "count": len(results)}


@mcp.tool()
def get_control_schema(
    name: str,
    exclude_inherited: bool = False,
) -> dict:
    """Get the full schema for a Flet control — properties, events, methods.

    Args:
        name: Control name (e.g. "TextField", "ft.Container", "elevated_button")
        exclude_inherited: If True, omit properties inherited from parent classes
    """
    if _schema_engine is None:
        return {"error": "Index not loaded. Run build_index first."}
    schema = _schema_engine.get_schema(name, exclude_inherited=exclude_inherited)
    if schema is None:
        suggestions = _schema_engine.suggest(name)
        msg = f"Control '{name}' not found."
        if suggestions:
            msg += f" Did you mean: {', '.join(suggestions)}?"
        return {"error": msg}
    return asdict(schema)


@mcp.tool()
def list_controls() -> dict:
    """List all available Flet control names."""
    if _schema_engine is None:
        return {"error": "Index not loaded. Run build_index first."}
    controls = _schema_engine.list_controls()
    return {"controls": controls, "count": len(controls)}


@mcp.tool()
def validate_snippet(code: str) -> dict:
    """Validate a Flet code snippet using AST analysis.

    Checks: syntax errors, unknown controls, invalid properties, missing entry point.

    Args:
        code: Python source code to validate
    """
    if _validator_engine is None:
        return {"error": "Index not loaded. Run build_index first."}
    result = _validator_engine.validate(code)
    return asdict(result)


@mcp.tool()
def search_examples(
    query: str,
    control_name: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 10,
) -> dict:
    """Search Flet example code. Returns matching examples with highlighted snippets.

    Args:
        query: Search terms (e.g. "drag and drop", "login form")
        control_name: Filter by control name (e.g. "TextField")
        category: Filter by category (e.g. "controls", "tutorials")
        limit: Max results (1-50, default 10)
    """
    if _examples_engine is None:
        return {"error": "Index not loaded. Run build_index first."}
    results = _examples_engine.search(
        query, control_name=control_name, category=category, limit=limit
    )
    return {"results": [asdict(r) for r in results], "count": len(results)}


@mcp.tool()
def get_example(path: str) -> dict:
    """Get the full source code of a specific example.

    Args:
        path: Relative path from search results (e.g. "controls/text_field/basic.py")
    """
    if _examples_engine is None:
        return {"error": "Index not loaded. Run build_index first."}
    content = _examples_engine.get(path)
    if content is None:
        return {"error": f"Example not found or invalid path: {path}"}
    return {"path": path, "content": content}
