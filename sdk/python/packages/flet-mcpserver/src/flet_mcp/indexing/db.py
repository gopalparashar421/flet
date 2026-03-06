"""SQLite FTS5 database creation and access."""

from __future__ import annotations

import sqlite3
from pathlib import Path


def create_database(path: str | Path) -> sqlite3.Connection:
    """Create a new index database with FTS5 tables. Removes any existing file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()

    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE VIRTUAL TABLE docs_fts USING fts5(
            title,
            content,
            path,
            category,
            section,
            tokenize='porter unicode61'
        );

        CREATE VIRTUAL TABLE examples_fts USING fts5(
            path,
            control_name,
            category,
            content,
            tokenize='porter unicode61'
        );

        CREATE TABLE schemas (
            name        TEXT PRIMARY KEY,
            module      TEXT,
            doc         TEXT,
            category    TEXT,
            parent_classes TEXT,   -- JSON array
            properties  TEXT,     -- JSON array
            events      TEXT,     -- JSON array
            methods     TEXT      -- JSON array
        );

        CREATE TABLE metadata (
            key   TEXT PRIMARY KEY,
            value TEXT
        );
        """
    )
    return conn


def open_database(path: str | Path) -> sqlite3.Connection:
    """Open an existing index database read-only."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Index database not found: {path}")
    conn = sqlite3.connect(
        f"file:{path}?mode=ro", uri=True, check_same_thread=False
    )
    conn.row_factory = sqlite3.Row
    return conn
