"""Shared data models for the Flet MCP server."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PropertyInfo:
    name: str
    type_str: str = "Any"
    default: str | None = None
    doc: str = ""
    deprecated: bool = False
    inherited_from: str | None = None
    enum_values: list[str] = field(default_factory=list)


@dataclass
class EventInfo:
    name: str
    type_str: str = "Any"
    doc: str = ""


@dataclass
class MethodInfo:
    name: str
    signature: str = ""
    doc: str = ""


@dataclass
class ControlSchema:
    name: str
    module: str = ""
    doc: str = ""
    category: str = ""
    parent_classes: list[str] = field(default_factory=list)
    properties: list[PropertyInfo] = field(default_factory=list)
    events: list[EventInfo] = field(default_factory=list)
    methods: list[MethodInfo] = field(default_factory=list)


@dataclass
class DocResult:
    title: str
    path: str
    category: str
    snippet: str
    score: float = 0.0


@dataclass
class ExampleResult:
    path: str
    control_name: str
    category: str
    snippet: str
    score: float = 0.0


@dataclass
class Diagnostic:
    line: int
    col: int
    severity: str  # "error" | "warning" | "info"
    message: str


@dataclass
class ValidationResult:
    valid: bool
    diagnostics: list[Diagnostic] = field(default_factory=list)
