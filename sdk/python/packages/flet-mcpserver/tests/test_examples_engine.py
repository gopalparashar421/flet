"""Tests for the ExamplesEngine."""

import pytest

from flet_mcp.engines.examples import ExamplesEngine
from flet_mcp.indexing.db import create_database


@pytest.fixture
def examples_db(tmp_path):
    db_path = tmp_path / "examples.db"
    conn = create_database(db_path)
    examples = [
        ("controls/text_field/basic.py", "TextField", "controls", "import flet as ft\nft.TextField(label='Name')"),
        ("controls/text_field/password.py", "TextField", "controls", "import flet as ft\nft.TextField(password=True)"),
        ("controls/button/click.py", "Button", "controls", "import flet as ft\nft.Button(text='Click me', on_click=handle)"),
        ("tutorials/todo/main.py", "ListView", "tutorials", "import flet as ft\ndef main(page):\n    page.add(ft.ListView())"),
    ]
    for path, control, category, content in examples:
        conn.execute("INSERT INTO examples_fts VALUES (?,?,?,?)", (path, control, category, content))
    conn.commit()
    conn.close()
    return db_path


def test_search_examples(examples_db):
    engine = ExamplesEngine(examples_db)
    results = engine.search("TextField")
    assert len(results) > 0


def test_search_control_filter(examples_db):
    engine = ExamplesEngine(examples_db)
    results = engine.search("flet", control_name="Button")
    assert all(r.control_name == "Button" for r in results)


def test_search_category_filter(examples_db):
    engine = ExamplesEngine(examples_db)
    results = engine.search("flet", category="tutorials")
    assert all(r.category == "tutorials" for r in results)


def test_get_example(examples_db):
    engine = ExamplesEngine(examples_db)
    content = engine.get("controls/text_field/basic.py")
    assert content is not None
    assert "TextField" in content


def test_get_example_not_found(examples_db):
    engine = ExamplesEngine(examples_db)
    assert engine.get("nonexistent/file.py") is None


def test_path_traversal_rejected(examples_db):
    engine = ExamplesEngine(examples_db)
    assert engine.get("../../etc/passwd") is None
    assert engine.get("/absolute/path.py") is None
    assert engine.get("C:\\windows\\system32") is None


def test_search_empty(examples_db):
    engine = ExamplesEngine(examples_db)
    results = engine.search("")
    assert len(results) == 0


def test_search_limit(examples_db):
    engine = ExamplesEngine(examples_db)
    results = engine.search("flet", limit=1)
    assert len(results) <= 1


def test_search_no_results(examples_db):
    engine = ExamplesEngine(examples_db)
    results = engine.search("xyznonexistent")
    assert len(results) == 0
