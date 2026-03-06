"""Tests for the ValidatorEngine."""

import json

import pytest

from flet_mcp.engines.schema import SchemaEngine
from flet_mcp.engines.validator import ValidatorEngine
from flet_mcp.indexing.db import create_database


@pytest.fixture
def validator(tmp_path):
    """Create a ValidatorEngine backed by a test schema database."""
    db_path = tmp_path / "val.db"
    conn = create_database(db_path)
    conn.execute(
        "INSERT INTO schemas VALUES (?,?,?,?,?,?,?,?)",
        (
            "TextField", "flet.controls.material", "Text input.", "material",
            json.dumps(["BaseControl"]),
            json.dumps([
                {"name": "value", "type_str": "str", "default": "''", "doc": "", "deprecated": False, "inherited_from": None, "enum_values": []},
                {"name": "label", "type_str": "str", "default": "None", "doc": "", "deprecated": False, "inherited_from": None, "enum_values": []},
            ]),
            json.dumps([{"name": "on_change", "type_str": "EventHandler", "doc": ""}]),
            json.dumps([{"name": "focus", "signature": "()", "doc": ""}]),
        ),
    )
    conn.execute(
        "INSERT INTO schemas VALUES (?,?,?,?,?,?,?,?)",
        (
            "Button", "flet.controls.material", "A button.", "material",
            json.dumps(["BaseControl"]),
            json.dumps([{"name": "text", "type_str": "str", "default": "''", "doc": "", "deprecated": False, "inherited_from": None, "enum_values": []}]),
            json.dumps([{"name": "on_click", "type_str": "EventHandler", "doc": ""}]),
            json.dumps([]),
        ),
    )
    conn.commit()
    conn.close()

    schema_engine = SchemaEngine(db_path)
    return ValidatorEngine(schema_engine)


def test_syntax_error(validator):
    result = validator.validate("def foo(")
    assert not result.valid
    assert any("Syntax error" in d.message for d in result.diagnostics)


def test_syntax_error_line(validator):
    result = validator.validate("x = 1\ndef foo(")
    assert result.diagnostics[0].line == 2


def test_detect_flet_alias(validator):
    code = "import flet as ft\nft.TextField(label='Name')\nft.run(lambda p: None)"
    result = validator.validate(code)
    assert result.valid


def test_detect_flet_no_alias(validator):
    code = "import flet\nflet.TextField(label='Name')\nflet.run(lambda p: None)"
    result = validator.validate(code)
    assert result.valid


def test_valid_code(validator):
    code = "import flet as ft\ndef main(page):\n    page.add(ft.TextField(label='Hi'))\nft.run(main)"
    result = validator.validate(code)
    assert result.valid


def test_unknown_control(validator):
    code = "import flet as ft\nft.SuperWidget()\nft.run(lambda p: None)"
    result = validator.validate(code)
    assert any("Unknown control" in d.message for d in result.diagnostics)


def test_unknown_property(validator):
    code = "import flet as ft\nft.TextField(labeel='typo')\nft.run(lambda p: None)"
    result = validator.validate(code)
    assert any("Unknown property" in d.message for d in result.diagnostics)


def test_missing_run(validator):
    code = "import flet as ft\nft.TextField(label='Hi')"
    result = validator.validate(code)
    assert any("run()" in d.message or "app()" in d.message for d in result.diagnostics)


def test_empty_code(validator):
    result = validator.validate("")
    assert not result.valid


def test_no_flet_import(validator):
    code = "x = 1 + 2"
    result = validator.validate(code)
    assert any("No 'import flet'" in d.message for d in result.diagnostics)
