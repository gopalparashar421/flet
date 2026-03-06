"""Tests for database creation and schema."""

import sqlite3
import tempfile
from pathlib import Path

import pytest

from flet_mcp.indexing.db import create_database, open_database


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "test.db"


def test_create_database_returns_connection(db_path):
    conn = create_database(db_path)
    assert isinstance(conn, sqlite3.Connection)
    conn.close()


def test_create_database_file_exists(db_path):
    conn = create_database(db_path)
    conn.close()
    assert db_path.exists()


def test_docs_fts_table_exists(db_path):
    conn = create_database(db_path)
    conn.execute("INSERT INTO docs_fts (title, content, path, category, section) VALUES (?,?,?,?,?)",
                 ("Test", "Body", "test.md", "controls", ""))
    conn.commit()
    row = conn.execute("SELECT * FROM docs_fts WHERE docs_fts MATCH 'Test'").fetchone()
    assert row is not None
    conn.close()


def test_examples_fts_table_exists(db_path):
    conn = create_database(db_path)
    conn.execute("INSERT INTO examples_fts (path, control_name, category, content) VALUES (?,?,?,?)",
                 ("test.py", "Button", "controls", "import flet"))
    conn.commit()
    row = conn.execute("SELECT * FROM examples_fts WHERE examples_fts MATCH 'flet'").fetchone()
    assert row is not None
    conn.close()


def test_schemas_table_exists(db_path):
    conn = create_database(db_path)
    conn.execute("INSERT INTO schemas (name, module, doc, category, parent_classes, properties, events, methods) "
                 "VALUES (?,?,?,?,?,?,?,?)",
                 ("Button", "flet", "A button", "material", "[]", "[]", "[]", "[]"))
    conn.commit()
    row = conn.execute("SELECT * FROM schemas WHERE name = 'Button'").fetchone()
    assert row["name"] == "Button"
    conn.close()


def test_metadata_table_exists(db_path):
    conn = create_database(db_path)
    conn.execute("INSERT INTO metadata (key, value) VALUES (?, ?)", ("ver", "1.0"))
    conn.commit()
    row = conn.execute("SELECT value FROM metadata WHERE key = 'ver'").fetchone()
    assert row["value"] == "1.0"
    conn.close()


def test_open_database(db_path):
    conn = create_database(db_path)
    conn.close()
    conn2 = open_database(db_path)
    assert isinstance(conn2, sqlite3.Connection)
    conn2.close()


def test_open_database_missing():
    with pytest.raises(FileNotFoundError):
        open_database("/nonexistent/path.db")


def test_create_database_replaces_existing(db_path):
    conn = create_database(db_path)
    conn.execute("INSERT INTO metadata (key, value) VALUES ('x', 'y')")
    conn.commit()
    conn.close()

    conn2 = create_database(db_path)  # should replace
    row = conn2.execute("SELECT * FROM metadata").fetchone()
    assert row is None
    conn2.close()
