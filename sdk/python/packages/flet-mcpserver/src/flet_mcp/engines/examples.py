"""Examples search and retrieval engine."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path, PurePosixPath

from flet_mcp.indexing.db import open_database
from flet_mcp.models import ExampleResult


def _sanitize_query(query: str) -> str:
    tokens = re.findall(r"\w+", query)
    if not tokens:
        return '""'
    return " ".join(f'"{t}"' for t in tokens)


def _is_path_safe(path: str) -> bool:
    """Reject path traversal attempts."""
    if ".." in path:
        return False
    if path.startswith("/") or path.startswith("\\"):
        return False
    # Windows drive letters
    if re.match(r"^[a-zA-Z]:", path):
        return False
    # Ensure it stays within bounds
    try:
        resolved = PurePosixPath(path)
        for part in resolved.parts:
            if part == "..":
                return False
    except Exception:
        return False
    return True


class ExamplesEngine:
    """Search and retrieve Flet examples."""

    def __init__(self, db_path: str | Path):
        self._conn = open_database(db_path)

    def search(
        self,
        query: str,
        control_name: str | None = None,
        category: str | None = None,
        limit: int = 10,
    ) -> list[ExampleResult]:
        limit = max(1, min(limit, 50))

        if not query or not query.strip():
            return []

        safe_query = _sanitize_query(query)

        sql = (
            "SELECT path, control_name, category, "
            "snippet(examples_fts, 3, '<mark>', '</mark>', '…', 64) AS snippet, "
            "bm25(examples_fts, 1.0, 5.0, 1.0, 1.0) AS score "
            "FROM examples_fts WHERE examples_fts MATCH ? "
        )
        params: list = [safe_query]

        if control_name:
            sql += "AND control_name = ? "
            params.append(control_name)
        if category:
            sql += "AND category = ? "
            params.append(category)

        sql += "ORDER BY score LIMIT ?"
        params.append(limit)

        rows = self._conn.execute(sql, params).fetchall()
        return [
            ExampleResult(
                path=row["path"],
                control_name=row["control_name"],
                category=row["category"],
                snippet=row["snippet"],
                score=row["score"],
            )
            for row in rows
        ]

    def get(self, path: str) -> str | None:
        """Get full example source code by path. Returns None if not found or unsafe."""
        if not _is_path_safe(path):
            return None

        row = self._conn.execute(
            "SELECT content FROM examples_fts WHERE path = ?", (path,)
        ).fetchone()
        return row["content"] if row else None
