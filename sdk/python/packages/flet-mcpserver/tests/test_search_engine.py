"""Tests for the SearchEngine."""

import pytest

from flet_mcp.engines.search import SearchEngine
from flet_mcp.indexing.db import create_database


@pytest.fixture
def search_db(tmp_path):
    """Create a database with sample docs for search testing."""
    db_path = tmp_path / "search.db"
    conn = create_database(db_path)
    docs = [
        ("TextField", "A text input field for entering text values.", "controls/textfield.md", "controls", "Overview"),
        ("TextField - Properties", "label, hint_text, value, multiline, read_only", "controls/textfield.md", "controls", "Properties"),
        ("Button", "A clickable button control.", "controls/button.md", "controls", "Overview"),
        ("Navigation", "How to implement routing and navigation in Flet.", "tutorials/navigation.md", "tutorials", ""),
        ("Getting Started", "Install Flet and create your first app.", "getting-started/index.md", "getting-started", ""),
    ]
    for title, content, path, category, section in docs:
        conn.execute("INSERT INTO docs_fts VALUES (?,?,?,?,?)", (title, content, path, category, section))
    conn.commit()
    conn.close()
    return db_path


def test_search_engine_init(search_db):
    engine = SearchEngine(search_db)
    assert engine is not None


def test_search_textfield(search_db):
    engine = SearchEngine(search_db)
    results = engine.search("TextField")
    assert len(results) > 0
    assert any("TextField" in r.title for r in results)


def test_search_navigation(search_db):
    engine = SearchEngine(search_db)
    results = engine.search("routing navigation")
    assert len(results) > 0


def test_search_category_filter(search_db):
    engine = SearchEngine(search_db)
    results = engine.search("TextField", category="controls")
    assert all(r.category == "controls" for r in results)


def test_search_limit(search_db):
    engine = SearchEngine(search_db)
    results = engine.search("text", limit=1)
    assert len(results) <= 1


def test_search_empty_query(search_db):
    engine = SearchEngine(search_db)
    results = engine.search("")
    assert len(results) == 0


def test_search_no_results(search_db):
    engine = SearchEngine(search_db)
    results = engine.search("xyznonexistent")
    assert len(results) == 0


def test_search_snippet_content(search_db):
    engine = SearchEngine(search_db)
    results = engine.search("button")
    assert len(results) > 0
    # Snippet should have content
    assert any(r.snippet for r in results)


def test_search_ranking(search_db):
    engine = SearchEngine(search_db)
    results = engine.search("TextField")
    # Title match should rank higher
    assert results[0].title.startswith("TextField")


def test_search_limit_clamped(search_db):
    engine = SearchEngine(search_db)
    results = engine.search("text", limit=100)
    assert len(results) <= 50
