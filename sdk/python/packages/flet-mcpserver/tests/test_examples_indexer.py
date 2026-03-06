"""Tests for the examples indexer."""

import pytest

from flet_mcp.indexing.db import create_database
from flet_mcp.indexing.examples_indexer import (
    _derive_category,
    _derive_control_name,
    index_examples,
)
from pathlib import Path


def test_derive_control_name_snake():
    p = Path("controls/text_field/basic.py")
    assert _derive_control_name(p) == "TextField"


def test_derive_control_name_single():
    p = Path("controls/button/click.py")
    assert _derive_control_name(p) == "Button"


def test_derive_category_controls():
    root = Path("/examples")
    p = Path("/examples/controls/button/test.py")
    assert _derive_category(p, root) == "controls"


def test_derive_category_tutorials():
    root = Path("/examples")
    p = Path("/examples/tutorials/basic/app.py")
    assert _derive_category(p, root) == "tutorials"


@pytest.fixture
def examples_dir(tmp_path):
    controls = tmp_path / "controls" / "text_field"
    controls.mkdir(parents=True)
    (controls / "basic.py").write_text("import flet as ft\nft.TextField(label='Name')")
    (controls / "__init__.py").write_text("")  # should be skipped
    tutorials = tmp_path / "tutorials"
    tutorials.mkdir()
    (tutorials / "app.py").write_text("import flet as ft\ndef main(page): pass\nft.run(main)")
    return tmp_path


def test_index_examples_count(examples_dir):
    conn = create_database(examples_dir / "test.db")
    count = index_examples(conn, examples_dir)
    assert count == 2  # basic.py + app.py, __init__.py skipped
    conn.close()


def test_index_examples_skips_init(examples_dir):
    conn = create_database(examples_dir / "test.db")
    index_examples(conn, examples_dir)
    rows = conn.execute("SELECT path FROM examples_fts").fetchall()
    paths = [r["path"] for r in rows]
    assert not any("__init__" in p for p in paths)
    conn.close()


def test_index_examples_fts_search(examples_dir):
    conn = create_database(examples_dir / "test.db")
    index_examples(conn, examples_dir)
    rows = conn.execute("SELECT * FROM examples_fts WHERE examples_fts MATCH 'TextField'").fetchall()
    assert len(rows) > 0
    conn.close()


def test_index_examples_content_stored(examples_dir):
    conn = create_database(examples_dir / "test.db")
    index_examples(conn, examples_dir)
    row = conn.execute("SELECT content FROM examples_fts WHERE path LIKE '%basic%'").fetchone()
    assert "import flet" in row["content"]
    conn.close()
