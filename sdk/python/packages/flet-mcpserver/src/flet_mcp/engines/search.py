"""Full-text search engine over indexed Flet documentation."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from flet_mcp.indexing.db import open_database
from flet_mcp.models import DocResult


def _sanitize_query(query: str) -> str:
    """Wrap user query tokens in quotes to prevent FTS5 syntax injection."""
    tokens = re.findall(r"\w+", query)
    if not tokens:
        return '""'
    return " ".join(f'"{t}"' for t in tokens)


class SearchEngine:
    """Search Flet documentation using FTS5."""

    def __init__(self, db_path: str | Path):
        self._conn = open_database(db_path)

    def search(
        self,
        query: str,
        category: str | None = None,
        limit: int = 10,
    ) -> list[DocResult]:
        limit = max(1, min(limit, 50))

        if not query or not query.strip():
            return []

        safe_query = _sanitize_query(query)

        sql = (
            "SELECT title, path, category, "
            "snippet(docs_fts, 1, '<mark>', '</mark>', '…', 64) AS snippet, "
            "bm25(docs_fts, 10.0, 1.0, 1.0, 1.0, 1.0) AS score "
            "FROM docs_fts WHERE docs_fts MATCH ? "
        )
        params: list = [safe_query]

        if category:
            sql += "AND category = ? "
            params.append(category)

        sql += "ORDER BY score LIMIT ?"
        params.append(limit)

        rows = self._conn.execute(sql, params).fetchall()
        return [
            DocResult(
                title=row["title"],
                path=row["path"],
                category=row["category"],
                snippet=row["snippet"],
                score=row["score"],
            )
            for row in rows
        ]
