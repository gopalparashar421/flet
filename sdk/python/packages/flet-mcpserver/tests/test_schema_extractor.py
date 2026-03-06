"""Tests for the schema extractor using mock classes (no flet dependency)."""

import dataclasses
import enum
import json

import pytest

from flet_mcp.indexing.db import create_database
from flet_mcp.indexing.schema_extractor import (
    _classify_field,
    _derive_category_from_module,
    _extract_enum_values,
    _extract_schema,
    _unwrap_optional,
    index_schemas,
)


# --- Mock classes for testing ---

class Color(enum.Enum):
    RED = "red"
    BLUE = "blue"
    GREEN = "green"


@dataclasses.dataclass(kw_only=True)
class MockBaseControl:
    key: str = ""
    data: object = None

    def update(self) -> None:
        """Update the control."""

    def _private(self):
        pass


@dataclasses.dataclass(kw_only=True)
class MockButton(MockBaseControl):
    text: str = ""
    color: Color = Color.RED
    on_click: object = None  # event handler

    def focus(self) -> None:
        """Focus the button."""


MockButton.__module__ = "flet.controls.material.button"


# --- Unit tests ---

def test_classify_property():
    assert _classify_field("text", "str") == "property"


def test_classify_event_on_prefix():
    assert _classify_field("on_click", "object") == "event"


def test_classify_event_handler_type():
    assert _classify_field("handler", "ControlEventHandler") == "event"


def test_unwrap_optional():
    assert _unwrap_optional("Optional[str]") == "str"
    assert _unwrap_optional("str") == "str"


def test_extract_enum_values():
    vals = _extract_enum_values(Color)
    assert set(vals) == {"red", "blue", "green"}


def test_extract_enum_values_non_enum():
    assert _extract_enum_values(str) == []


def test_derive_category_material():
    assert _derive_category_from_module("flet.controls.material.button") == "material"


def test_derive_category_cupertino():
    assert _derive_category_from_module("flet.controls.cupertino.slider") == "cupertino"


def test_derive_category_core():
    assert _derive_category_from_module("flet.controls.something") == "core"


# --- Schema extraction tests ---

def test_extract_schema_name():
    schema = _extract_schema(MockButton, MockBaseControl)
    assert schema.name == "MockButton"


def test_extract_schema_module():
    schema = _extract_schema(MockButton, MockBaseControl)
    assert schema.module == "flet.controls.material.button"


def test_extract_schema_category():
    schema = _extract_schema(MockButton, MockBaseControl)
    assert schema.category == "material"


def test_extract_schema_properties():
    schema = _extract_schema(MockButton, MockBaseControl)
    prop_names = [p.name for p in schema.properties]
    assert "text" in prop_names
    assert "color" in prop_names


def test_extract_schema_events():
    schema = _extract_schema(MockButton, MockBaseControl)
    event_names = [e.name for e in schema.events]
    assert "on_click" in event_names


def test_extract_schema_methods():
    schema = _extract_schema(MockButton, MockBaseControl)
    method_names = [m.name for m in schema.methods]
    assert "focus" in method_names
    assert "update" in method_names
    assert "_private" not in method_names


def test_extract_schema_inherited_from():
    schema = _extract_schema(MockButton, MockBaseControl)
    key_prop = next((p for p in schema.properties if p.name == "key"), None)
    assert key_prop is not None
    assert key_prop.inherited_from == "MockBaseControl"


def test_extract_schema_enum_values():
    schema = _extract_schema(MockButton, MockBaseControl)
    color_prop = next((p for p in schema.properties if p.name == "color"), None)
    assert color_prop is not None
    assert "red" in color_prop.enum_values


def test_extract_schema_parent_classes():
    schema = _extract_schema(MockButton, MockBaseControl)
    assert "MockBaseControl" in schema.parent_classes


# --- DB integration ---

def test_index_schemas_stores_data(tmp_path):
    conn = create_database(tmp_path / "test.db")
    count = index_schemas(conn, [MockButton], MockBaseControl)
    assert count == 1
    row = conn.execute("SELECT * FROM schemas WHERE name = 'MockButton'").fetchone()
    assert row is not None
    props = json.loads(row["properties"])
    prop_names = [p["name"] for p in props]
    assert "text" in prop_names
    conn.close()
