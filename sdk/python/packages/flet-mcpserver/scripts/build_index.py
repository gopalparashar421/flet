#!/usr/bin/env python3
"""Standalone script to build the Flet MCP index database."""

from __future__ import annotations

import logging
import sys
from pathlib import Path


def _find_repo_root() -> Path | None:
    """Walk up from cwd to find the repo root (has sdk/ and README.md)."""
    cur = Path.cwd()
    for _ in range(10):
        if (cur / "sdk" / "python").is_dir() and (cur / "README.md").exists():
            return cur
        parent = cur.parent
        if parent == cur:
            break
        cur = parent
    return None


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    logger = logging.getLogger(__name__)

    root = _find_repo_root()
    if root is None:
        logger.error("Cannot find repo root. Run from inside the flet repository.")
        sys.exit(1)

    docs_root = root / "sdk" / "python" / "packages" / "flet" / "docs"
    examples_root = root / "sdk" / "python" / "examples"
    output_path = (
        root
        / "sdk"
        / "python"
        / "packages"
        / "flet-mcpserver"
        / "src"
        / "flet_mcp"
        / "data"
        / "flet_index.db"
    )

    logger.info("Docs root: %s (exists=%s)", docs_root, docs_root.is_dir())
    logger.info("Examples root: %s (exists=%s)", examples_root, examples_root.is_dir())
    logger.info("Output: %s", output_path)

    from flet_mcp.indexing.build_index import build_index

    build_index(
        output_path=output_path,
        docs_root=docs_root if docs_root.is_dir() else None,
        examples_root=examples_root if examples_root.is_dir() else None,
    )

    logger.info("Done. Index at %s", output_path)


if __name__ == "__main__":
    main()
