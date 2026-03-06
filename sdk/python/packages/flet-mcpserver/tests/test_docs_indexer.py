"""Tests for the docs indexer."""

import pytest

from flet_mcp.indexing.db import create_database
from flet_mcp.indexing.docs_indexer import (
    _derive_category,
    _extract_title,
    _split_sections,
    _strip_mkdocs_syntax,
    index_docs,
)


# --- strip tests ---

def test_strip_frontmatter():
    text = "---\ntitle: Test\n---\nHello"
    assert _strip_mkdocs_syntax(text) == "Hello"


def test_strip_jinja_block():
    text = "Before {% block x %}stuff{% endblock %} After"
    assert "block" not in _strip_mkdocs_syntax(text)


def test_strip_jinja_expr():
    text = 'Before {{ class_summary("X") }} After'
    assert "class_summary" not in _strip_mkdocs_syntax(text)


def test_strip_snippet_include():
    text = 'Some text\n--8<-- "examples/foo.py"\nMore text'
    result = _strip_mkdocs_syntax(text)
    assert "--8<--" not in result


def test_strip_admonition():
    text = "!!! note\n    This is a note.\nRegular text."
    result = _strip_mkdocs_syntax(text)
    assert "!!!" not in result


def test_strip_annotation():
    text = "This is a link [(c).] and [(c)] markers"
    result = _strip_mkdocs_syntax(text)
    assert "[(c).]" not in result


# --- category tests ---

def test_derive_category_controls():
    assert _derive_category("controls/button.md") == "controls"


def test_derive_category_tutorials():
    assert _derive_category("tutorials/intro.md") == "tutorials"


def test_derive_category_unknown():
    assert _derive_category("random/stuff.md") == "other"


# --- section split tests ---

def test_split_sections_basic():
    text = "Intro\n## Section A\nContent A\n## Section B\nContent B"
    sections = _split_sections(text)
    assert len(sections) == 3
    assert sections[0][0] == ""  # intro has no heading
    assert sections[1][0] == "Section A"
    assert sections[2][0] == "Section B"


# --- title extraction ---

def test_extract_title_from_heading():
    assert _extract_title("# My Title\nBody", "file.md") == "My Title"


def test_extract_title_fallback():
    assert _extract_title("No heading here", "my-control.md") == "My Control"


# --- full indexer ---

@pytest.fixture
def docs_dir(tmp_path):
    controls = tmp_path / "controls"
    controls.mkdir()
    (controls / "button.md").write_text("---\ntitle: Button\n---\n# Button\n## Properties\ncolor, size\n## Events\non_click")
    (controls / "text.md").write_text("# Text\nA text display control.\n## Styling\nBold, italic")
    tutorials = tmp_path / "tutorials"
    tutorials.mkdir()
    (tutorials / "intro.md").write_text("# Getting Started\nLearn the basics.")
    return tmp_path


def test_index_docs_count(docs_dir):
    conn = create_database(docs_dir / "test.db")
    count = index_docs(conn, docs_dir)
    assert count > 0
    conn.close()


def test_index_docs_fts_search(docs_dir):
    conn = create_database(docs_dir / "test.db")
    index_docs(conn, docs_dir)
    rows = conn.execute("SELECT * FROM docs_fts WHERE docs_fts MATCH 'Button'").fetchall()
    assert len(rows) > 0
    conn.close()
