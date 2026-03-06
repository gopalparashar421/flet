"""Schema lookup engine for Flet controls."""

from __future__ import annotations

import difflib
import json
import re
import sqlite3
from pathlib import Path

from flet_mcp.indexing.db import open_database
from flet_mcp.models import (
    ControlSchema,
    EventInfo,
    MethodInfo,
    PropertyInfo,
)


class SchemaEngine:
    """Lookup Flet control schemas with fuzzy name resolution."""

    def __init__(self, db_path: str | Path):
        self._conn = open_database(db_path)
        self._name_map: dict[str, str] = {}
        self._build_name_map()

    def _build_name_map(self) -> None:
        """Build a lowercase → canonical name mapping."""
        rows = self._conn.execute("SELECT name FROM schemas").fetchall()
        for row in rows:
            name = row["name"]
            self._name_map[name.lower()] = name

    def _resolve_name(self, name: str) -> str | None:
        """Resolve a user-provided name to a canonical schema name."""
        # Strip common prefixes
        cleaned = re.sub(r"^(ft\.|flet\.)", "", name, flags=re.IGNORECASE)

        # Direct lowercase match
        lower = cleaned.lower()
        if lower in self._name_map:
            return self._name_map[lower]

        # Try snake_case → PascalCase
        pascal = re.sub(r"(?:^|_)([a-z])", lambda m: m.group(1).upper(), cleaned)
        if pascal.lower() in self._name_map:
            return self._name_map[pascal.lower()]

        return None

    def get_schema(
        self,
        name: str,
        exclude_inherited: bool = False,
    ) -> ControlSchema | None:
        """Get a control schema by name."""
        canonical = self._resolve_name(name)
        if not canonical:
            return None

        row = self._conn.execute(
            "SELECT * FROM schemas WHERE name = ?", (canonical,)
        ).fetchone()
        if not row:
            return None

        properties = [
            PropertyInfo(**p) for p in json.loads(row["properties"])
        ]
        events = [EventInfo(**e) for e in json.loads(row["events"])]
        methods = [MethodInfo(**m) for m in json.loads(row["methods"])]

        if exclude_inherited:
            properties = [p for p in properties if p.inherited_from is None]

        return ControlSchema(
            name=row["name"],
            module=row["module"],
            doc=row["doc"],
            category=row["category"],
            parent_classes=json.loads(row["parent_classes"]),
            properties=properties,
            events=events,
            methods=methods,
        )

    def suggest(self, name: str, n: int = 5) -> list[str]:
        """Suggest similar control names using fuzzy matching."""
        all_names = list(self._name_map.values())
        cleaned = re.sub(r"^(ft\.|flet\.)", "", name, flags=re.IGNORECASE)
        return difflib.get_close_matches(cleaned, all_names, n=n, cutoff=0.5)

    def list_controls(self) -> list[str]:
        """Return all available control names sorted."""
        return sorted(self._name_map.values())

    def has_control(self, name: str) -> bool:
        return self._resolve_name(name) is not None

    def get_property_names(self, name: str) -> list[str]:
        """Get property names for a control."""
        schema = self.get_schema(name)
        if not schema:
            return []
        return [p.name for p in schema.properties]

    def get_event_names(self, name: str) -> list[str]:
        """Get event names for a control."""
        schema = self.get_schema(name)
        if not schema:
            return []
        return [e.name for e in schema.events]
