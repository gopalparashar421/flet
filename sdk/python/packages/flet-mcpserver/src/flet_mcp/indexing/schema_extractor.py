"""Extract control schemas from Flet class introspection and store in the database."""

from __future__ import annotations

import dataclasses
import enum
import inspect
import json
import re
import sqlite3
from typing import Any, Optional, get_type_hints

from flet_mcp.models import (
    ControlSchema,
    EventInfo,
    MethodInfo,
    PropertyInfo,
)


def _unwrap_optional(type_str: str) -> str:
    """Unwrap Optional[X] → X for cleaner display."""
    m = re.match(r"Optional\[(.+)\]", type_str)
    return m.group(1) if m else type_str


def _type_to_str(annotation: Any) -> str:
    """Convert a type annotation to a readable string."""
    if annotation is inspect.Parameter.empty or annotation is None:
        return "Any"
    if hasattr(annotation, "__name__"):
        return annotation.__name__
    return str(annotation).replace("typing.", "")


def _classify_field(name: str, type_str: str) -> str:
    """Classify a field as 'event' or 'property'."""
    if name.startswith("on_"):
        return "event"
    if "EventHandler" in type_str or "ControlEventHandler" in type_str:
        return "event"
    return "property"


def _extract_enum_values(annotation: Any) -> list[str]:
    """Extract string values from Enum subclasses."""
    origin = getattr(annotation, "__origin__", None)
    # Unwrap Optional
    if origin is type(None) or str(origin) == "typing.Union":
        args = getattr(annotation, "__args__", ())
        for arg in args:
            if arg is not type(None):
                annotation = arg
                break
    try:
        if isinstance(annotation, type) and issubclass(annotation, enum.Enum):
            return [str(member.value) for member in annotation]
    except TypeError:
        pass
    return []


def _derive_category_from_module(module_name: str) -> str:
    """Derive a category from the module path."""
    parts = module_name.split(".")
    for part in parts:
        if part == "material":
            return "material"
        elif part == "cupertino":
            return "cupertino"
        elif part == "charts":
            return "charts"
        elif part == "services":
            return "services"
    return "core"


def _extract_schema(
    cls: type,
    base_cls: type | None = None,
) -> ControlSchema:
    """Extract a ControlSchema from a class via introspection."""
    # Try get_type_hints first, fall back to __annotations__ aggregation
    hints = {}
    try:
        hints = get_type_hints(cls)
    except Exception:
        # Forward reference resolution can fail (e.g. Flet's @control classes).
        # Aggregate __annotations__ from MRO instead.
        for klass in reversed(cls.__mro__):
            if klass is object:
                continue
            hints.update(getattr(klass, "__annotations__", {}))

    # Determine parent classes
    parent_classes = []
    for parent in cls.__mro__[1:]:
        if parent is object:
            continue
        if base_cls and parent is base_cls:
            parent_classes.append(parent.__name__)
            break
        parent_classes.append(parent.__name__)

    # Get dataclass fields if available
    dc_fields: dict[str, dataclasses.Field] = {}
    if dataclasses.is_dataclass(cls):
        dc_fields = {f.name: f for f in dataclasses.fields(cls)}

    # Determine which class owns each field
    field_owners: dict[str, str] = {}
    for klass in reversed(cls.__mro__):
        if klass is object:
            continue
        klass_own_annotations = getattr(klass, "__annotations__", {})
        for fname in klass_own_annotations:
            field_owners[fname] = klass.__name__

    # Decide which names to iterate: prefer resolved hints, but also cover dc_fields
    all_field_names = list(dict.fromkeys(list(hints.keys()) + list(dc_fields.keys())))

    properties: list[PropertyInfo] = []
    events: list[EventInfo] = []

    for name in all_field_names:
        if name.startswith("_"):
            continue

        annotation = hints.get(name)
        # For type_str, prefer the resolved annotation; fall back to the string from dc_field
        if annotation is not None:
            type_str = _type_to_str(annotation)
        elif name in dc_fields:
            # Use the raw annotation string
            raw = dc_fields[name].type
            type_str = str(raw) if raw else "Any"
        else:
            type_str = "Any"

        kind = _classify_field(name, type_str)

        # Get default value
        default = None
        if name in dc_fields:
            f = dc_fields[name]
            if f.default is not dataclasses.MISSING:
                default = repr(f.default)
            elif f.default_factory is not dataclasses.MISSING:
                try:
                    default = repr(f.default_factory())
                except Exception:
                    default = "..."

        # Get docstring from field metadata or class source
        doc = ""
        skip = False
        if name in dc_fields:
            meta = dc_fields[name].metadata
            if meta:
                doc = meta.get("doc", "")
                skip = meta.get("skip", False)

        if skip:
            continue

        # Determine ownership
        owner = field_owners.get(name, cls.__name__)
        inherited_from = owner if owner != cls.__name__ else None

        if kind == "event":
            events.append(EventInfo(name=name, type_str=type_str, doc=doc))
        else:
            enum_values = _extract_enum_values(annotation) if annotation else []
            properties.append(
                PropertyInfo(
                    name=name,
                    type_str=_unwrap_optional(type_str),
                    default=default,
                    doc=doc,
                    inherited_from=inherited_from,
                    enum_values=enum_values,
                )
            )

    # Extract public methods
    methods: list[MethodInfo] = []
    for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
        if name.startswith("_"):
            continue
        try:
            sig = str(inspect.signature(method))
        except (ValueError, TypeError):
            sig = "()"
        doc = inspect.getdoc(method) or ""
        methods.append(MethodInfo(name=name, signature=sig, doc=doc))

    return ControlSchema(
        name=cls.__name__,
        module=cls.__module__,
        doc=inspect.getdoc(cls) or "",
        category=_derive_category_from_module(cls.__module__),
        parent_classes=parent_classes,
        properties=properties,
        events=events,
        methods=methods,
    )


def _load_flet_classes() -> tuple[list[type], type]:
    """Dynamically import flet and find all @control-decorated classes.
    Returns (classes, base_cls).
    """
    import flet  # noqa: F811 – deferred import

    from flet.controls.base_control import BaseControl

    classes: list[type] = []

    def _walk_module(mod: Any, visited: set) -> None:
        mod_name = getattr(mod, "__name__", "")
        if mod_name in visited:
            return
        visited.add(mod_name)
        for attr_name in dir(mod):
            attr = getattr(mod, attr_name, None)
            if (
                isinstance(attr, type)
                and issubclass(attr, BaseControl)
                and attr is not BaseControl
                and attr not in classes
            ):
                classes.append(attr)

    _walk_module(flet, set())
    return classes, BaseControl


def index_schemas(
    conn: sqlite3.Connection,
    classes: list[type] | None = None,
    base_cls: type | None = None,
) -> int:
    """Extract schemas from classes and store in the database. Returns count."""
    if classes is None:
        classes, base_cls = _load_flet_classes()

    count = 0
    for cls in classes:
        schema = _extract_schema(cls, base_cls)
        conn.execute(
            "INSERT OR REPLACE INTO schemas "
            "(name, module, doc, category, parent_classes, properties, events, methods) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                schema.name,
                schema.module,
                schema.doc,
                schema.category,
                json.dumps(schema.parent_classes),
                json.dumps(
                    [
                        {
                            "name": p.name,
                            "type_str": p.type_str,
                            "default": p.default,
                            "doc": p.doc,
                            "deprecated": p.deprecated,
                            "inherited_from": p.inherited_from,
                            "enum_values": p.enum_values,
                        }
                        for p in schema.properties
                    ]
                ),
                json.dumps(
                    [
                        {"name": e.name, "type_str": e.type_str, "doc": e.doc}
                        for e in schema.events
                    ]
                ),
                json.dumps(
                    [
                        {"name": m.name, "signature": m.signature, "doc": m.doc}
                        for m in schema.methods
                    ]
                ),
            ),
        )
        count += 1

    conn.commit()
    return count
