"""Entry point for ``python -m flet_mcp``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _find_index_path() -> Path | None:
    """Auto-detect the pre-built index database."""
    # 1. Bundled with the package (data/flet_index.db)
    pkg_data = Path(__file__).parent / "data" / "flet_index.db"
    if pkg_data.exists():
        return pkg_data

    # 2. Built into the repo root
    here = Path.cwd()
    for candidate in [
        here / "flet_index.db",
        here / "sdk" / "python" / "packages" / "flet-mcpserver" / "src" / "flet_mcp" / "data" / "flet_index.db",
    ]:
        if candidate.exists():
            return candidate

    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Flet MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "http"],
        default="stdio",
        help="MCP transport (default: stdio)",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host for sse/http")
    parser.add_argument("--port", type=int, default=8080, help="Port for sse/http")
    parser.add_argument("--index-path", type=str, default=None, help="Path to index DB")
    args = parser.parse_args()

    from flet_mcp.server import init_engines, mcp

    index_path = Path(args.index_path) if args.index_path else _find_index_path()
    if index_path and index_path.exists():
        init_engines(index_path)
        print(f"Loaded index: {index_path}", file=sys.stderr)
    else:
        print("Warning: No index database found. Tools will return errors.", file=sys.stderr)
        print("Run the build_index script first, or pass --index-path.", file=sys.stderr)

    transport = args.transport
    if transport == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.run(transport=transport, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
