"""Index Flet Python examples into the FTS5 database."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path


def _derive_control_name(path: Path) -> str:
    """Derive a PascalCase control name from path (e.g. text_field → TextField)."""
    # Use parent directory name as the control name source
    name = path.parent.name
    if not name or name == ".":
        name = path.stem
    # snake_case → PascalCase
    return re.sub(r"(?:^|_)([a-z])", lambda m: m.group(1).upper(), name)


def _derive_category(path: Path, examples_root: Path) -> str:
    """Derive category from the top-level directory under examples_root."""
    try:
        rel = path.relative_to(examples_root)
        parts = rel.parts
        if len(parts) > 1:
            return parts[0].lower()
    except ValueError:
        pass
    return "other"


def index_examples(conn: sqlite3.Connection, examples_root: str | Path) -> int:
    """Walk examples_root and insert all .py files into examples_fts. Returns count."""
    examples_root = Path(examples_root)
    count = 0

    for py_file in sorted(examples_root.rglob("*.py")):
        if py_file.name == "__init__.py":
            continue

        content = py_file.read_text(encoding="utf-8", errors="replace")
        if not content.strip():
            continue

        rel_path = py_file.relative_to(examples_root).as_posix()
        control_name = _derive_control_name(py_file)
        category = _derive_category(py_file, examples_root)

        conn.execute(
            "INSERT INTO examples_fts (path, control_name, category, content) "
            "VALUES (?, ?, ?, ?)",
            (rel_path, control_name, category, content),
        )
        count += 1

    conn.commit()
    return count
