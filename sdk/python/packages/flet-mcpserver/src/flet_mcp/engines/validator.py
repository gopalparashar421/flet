"""AST-based code validator for Flet snippets."""

from __future__ import annotations

import ast
import difflib

from flet_mcp.engines.schema import SchemaEngine
from flet_mcp.models import Diagnostic, ValidationResult


class ValidatorEngine:
    """Validate Flet code snippets using AST analysis."""

    def __init__(self, schema_engine: SchemaEngine):
        self._schema = schema_engine

    def validate(self, code: str) -> ValidationResult:
        if not code or not code.strip():
            return ValidationResult(
                valid=False,
                diagnostics=[
                    Diagnostic(line=0, col=0, severity="error", message="Empty code snippet")
                ],
            )

        diagnostics: list[Diagnostic] = []

        # Pass 1: Syntax check
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return ValidationResult(
                valid=False,
                diagnostics=[
                    Diagnostic(
                        line=e.lineno or 0,
                        col=e.offset or 0,
                        severity="error",
                        message=f"Syntax error: {e.msg}",
                    )
                ],
            )

        # Pass 2: Find flet import alias
        alias = self._find_flet_alias(tree)
        if alias is None:
            diagnostics.append(
                Diagnostic(
                    line=0,
                    col=0,
                    severity="info",
                    message="No 'import flet' statement found",
                )
            )
            return ValidationResult(valid=len(diagnostics) == 0, diagnostics=diagnostics)

        # Pass 3-4: Check controls and properties
        diagnostics.extend(self._check_controls(tree, alias))
        diagnostics.extend(self._check_keywords(tree, alias))

        # Pass 5: Check entry point
        diagnostics.extend(self._check_entry_point(tree, alias))

        has_errors = any(d.severity == "error" for d in diagnostics)
        return ValidationResult(valid=not has_errors, diagnostics=diagnostics)

    @staticmethod
    def _find_flet_alias(tree: ast.Module) -> str | None:
        """Find the alias for 'import flet as ...'."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    if a.name == "flet":
                        return a.asname or "flet"
            elif isinstance(node, ast.ImportFrom):
                if node.module == "flet":
                    # from flet import ... — not an alias-style import
                    return "__from_import__"
        return None

    def _check_controls(self, tree: ast.Module, alias: str) -> list[Diagnostic]:
        """Check that referenced controls exist."""
        diagnostics: list[Diagnostic] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                if node.value.id == alias:
                    control_name = node.attr
                    # Skip non-control attributes (functions, constants, enums)
                    if control_name[0:1].isupper() and not self._schema.has_control(control_name):
                        suggestions = self._schema.suggest(control_name, n=3)
                        msg = f"Unknown control: {alias}.{control_name}"
                        if suggestions:
                            msg += f". Did you mean: {', '.join(suggestions)}?"
                        diagnostics.append(
                            Diagnostic(
                                line=node.lineno,
                                col=node.col_offset,
                                severity="warning",
                                message=msg,
                            )
                        )
        return diagnostics

    def _check_keywords(self, tree: ast.Module, alias: str) -> list[Diagnostic]:
        """Check that keyword arguments to controls are valid properties."""
        diagnostics: list[Diagnostic] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            # Pattern: ft.ControlName(...)
            func = node.func
            if not (
                isinstance(func, ast.Attribute)
                and isinstance(func.value, ast.Name)
                and func.value.id == alias
                and func.attr[0:1].isupper()
            ):
                continue

            control_name = func.attr
            if not self._schema.has_control(control_name):
                continue

            valid_props = self._schema.get_property_names(control_name)
            valid_events = self._schema.get_event_names(control_name)
            all_valid = set(valid_props + valid_events)

            for kw in node.keywords:
                if kw.arg and kw.arg not in all_valid:
                    suggestions = difflib.get_close_matches(
                        kw.arg, list(all_valid), n=3, cutoff=0.5
                    )
                    msg = f"Unknown property '{kw.arg}' on {control_name}"
                    if suggestions:
                        msg += f". Did you mean: {', '.join(suggestions)}?"
                    diagnostics.append(
                        Diagnostic(
                            line=kw.value.lineno if hasattr(kw.value, "lineno") else node.lineno,
                            col=kw.col_offset if hasattr(kw, "col_offset") else 0,
                            severity="warning",
                            message=msg,
                        )
                    )
        return diagnostics

    @staticmethod
    def _check_entry_point(tree: ast.Module, alias: str) -> list[Diagnostic]:
        """Check for ft.run() or ft.app() call."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
                    if func.value.id == alias and func.attr in ("run", "app"):
                        return []
        return [
            Diagnostic(
                line=0,
                col=0,
                severity="info",
                message=f"No {alias}.run() or {alias}.app() call found — is this a complete app?",
            )
        ]
