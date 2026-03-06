"""Tests for the build_index orchestrator."""

import pytest

from flet_mcp.indexing.build_index import build_index
from flet_mcp.indexing.db import open_database


@pytest.fixture
def sample_data(tmp_path):
    """Create sample docs and examples for testing."""
    docs = tmp_path / "docs" / "controls"
    docs.mkdir(parents=True)
    (docs / "button.md").write_text("# Button\nA clickable button control.")

    examples = tmp_path / "examples" / "controls" / "button"
    examples.mkdir(parents=True)
    (examples / "basic.py").write_text("import flet as ft\nft.Button(text='Click')")

    return tmp_path


def test_build_index_creates_db(sample_data, tmp_path):
    out = tmp_path / "out.db"
    build_index(out, docs_root=sample_data / "docs", examples_root=sample_data / "examples")
    assert out.exists()


def test_build_index_has_docs(sample_data, tmp_path):
    out = tmp_path / "out.db"
    build_index(out, docs_root=sample_data / "docs", examples_root=sample_data / "examples")
    conn = open_database(out)
    rows = conn.execute("SELECT * FROM docs_fts").fetchall()
    assert len(rows) > 0
    conn.close()


def test_build_index_has_examples(sample_data, tmp_path):
    out = tmp_path / "out.db"
    build_index(out, docs_root=sample_data / "docs", examples_root=sample_data / "examples")
    conn = open_database(out)
    rows = conn.execute("SELECT * FROM examples_fts").fetchall()
    assert len(rows) > 0
    conn.close()


def test_build_index_metadata(sample_data, tmp_path):
    out = tmp_path / "out.db"
    build_index(out, docs_root=sample_data / "docs", examples_root=sample_data / "examples",
                flet_version="0.99.0")
    conn = open_database(out)
    row = conn.execute("SELECT value FROM metadata WHERE key = 'flet_version'").fetchone()
    assert row["value"] == "0.99.0"
    conn.close()


def test_build_index_replaces_existing(sample_data, tmp_path):
    out = tmp_path / "out.db"
    build_index(out, docs_root=sample_data / "docs")
    build_index(out, docs_root=sample_data / "docs")  # should not fail
    assert out.exists()
