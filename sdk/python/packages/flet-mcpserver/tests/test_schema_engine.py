"""Tests for the SchemaEngine."""

import json

import pytest

from flet_mcp.engines.schema import SchemaEngine
from flet_mcp.indexing.db import create_database


def _insert_schema(conn, name, module="flet.controls.material", properties=None, events=None, methods=None):
    """Helper to insert a test schema."""
    conn.execute(
        "INSERT INTO schemas (name, module, doc, category, parent_classes, properties, events, methods) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (
            name, module, f"A {name} control.", "material",
            json.dumps(["BaseControl"]),
            json.dumps(properties or [{"name": "value", "type_str": "str", "default": "''", "doc": "", "deprecated": False, "inherited_from": None, "enum_values": []}]),
            json.dumps(events or [{"name": "on_click", "type_str": "EventHandler", "doc": ""}]),
            json.dumps(methods or [{"name": "focus", "signature": "()", "doc": ""}]),
        ),
    )
    conn.commit()


@pytest.fixture
def schema_db(tmp_path):
    db_path = tmp_path / "schema.db"
    conn = create_database(db_path)
    _insert_schema(conn, "TextField", properties=[
        {"name": "value", "type_str": "str", "default": "''", "doc": "", "deprecated": False, "inherited_from": None, "enum_values": []},
        {"name": "label", "type_str": "str", "default": "None", "doc": "", "deprecated": False, "inherited_from": None, "enum_values": []},
        {"name": "key", "type_str": "str", "default": "None", "doc": "", "deprecated": False, "inherited_from": "BaseControl", "enum_values": []},
    ], events=[
        {"name": "on_change", "type_str": "EventHandler", "doc": ""},
        {"name": "on_submit", "type_str": "EventHandler", "doc": ""},
    ])
    _insert_schema(conn, "Button")
    _insert_schema(conn, "Container")
    _insert_schema(conn, "ElevatedButton")
    conn.close()
    return db_path


def test_schema_exact_match(schema_db):
    engine = SchemaEngine(schema_db)
    schema = engine.get_schema("TextField")
    assert schema is not None
    assert schema.name == "TextField"


def test_schema_case_insensitive(schema_db):
    engine = SchemaEngine(schema_db)
    schema = engine.get_schema("textfield")
    assert schema is not None
    assert schema.name == "TextField"


def test_schema_prefix_strip_ft(schema_db):
    engine = SchemaEngine(schema_db)
    schema = engine.get_schema("ft.TextField")
    assert schema is not None


def test_schema_prefix_strip_flet(schema_db):
    engine = SchemaEngine(schema_db)
    schema = engine.get_schema("flet.Button")
    assert schema is not None


def test_schema_snake_case(schema_db):
    engine = SchemaEngine(schema_db)
    schema = engine.get_schema("elevated_button")
    assert schema is not None
    assert schema.name == "ElevatedButton"


def test_schema_not_found(schema_db):
    engine = SchemaEngine(schema_db)
    schema = engine.get_schema("NonexistentWidget")
    assert schema is None


def test_schema_exclude_inherited(schema_db):
    engine = SchemaEngine(schema_db)
    schema = engine.get_schema("TextField", exclude_inherited=True)
    prop_names = [p.name for p in schema.properties]
    assert "key" not in prop_names  # inherited from BaseControl
    assert "value" in prop_names


def test_schema_suggest(schema_db):
    engine = SchemaEngine(schema_db)
    suggestions = engine.suggest("TextFeld")
    assert "TextField" in suggestions


def test_list_controls(schema_db):
    engine = SchemaEngine(schema_db)
    controls = engine.list_controls()
    assert "TextField" in controls
    assert "Button" in controls
    assert len(controls) == 4


def test_has_control(schema_db):
    engine = SchemaEngine(schema_db)
    assert engine.has_control("TextField")
    assert not engine.has_control("Nonexistent")


def test_get_event_names(schema_db):
    engine = SchemaEngine(schema_db)
    events = engine.get_event_names("TextField")
    assert "on_change" in events
    assert "on_submit" in events


def test_get_property_names(schema_db):
    engine = SchemaEngine(schema_db)
    props = engine.get_property_names("TextField")
    assert "value" in props
    assert "label" in props
